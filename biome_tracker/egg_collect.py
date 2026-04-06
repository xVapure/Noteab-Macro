import json
import threading
import time
import ctypes
from pathlib import Path
from typing import Any, Callable
import os
import sys
import collections.abc

_autoit_lock = threading.Lock()

from .fishing import (
    _run_respawn_sequence,
    _autoit_key_tap,
    _autoit_key_down,
    _autoit_key_up,
    NON_VIP_WALK_SPEED_MULTIPLIER,
    _MOVEMENT_KEYS,
    _coerce_point,
    _coerce_region,
    _coerce_int,
    _coerce_float,
)

try:
    import autoit
except Exception:
    autoit = None 


def _get_screen_resolution() -> tuple[int, int]:
    try:
        user32 = ctypes.windll.user32
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1920, 1080


_RECORD_WIDTH, _RECORD_HEIGHT = 1920, 1080
def _replay_egg_path(
    *,
    events: list[dict[str, Any]],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    speed_multiplier: float = 1.0,
    log_prefix: str = "[EggCollect]",
) -> bool:
    if not events: return True
    pressed_keys: set[str] = set()
    base_t = events[0].get("t", 0.0)
    start_wall = time.perf_counter()
    last_check = start_wall

    screen_w, screen_h = _get_screen_resolution()
    scale_x = screen_w / _RECORD_WIDTH
    scale_y = screen_h / _RECORD_HEIGHT
    if abs(scale_x - 1.0) < 0.01 and abs(scale_y - 1.0) < 0.01:
        scale_x = scale_y = 1.0  # no scaling
    else:
        print(f"{log_prefix} Resolution scaling: {_RECORD_WIDTH}x{_RECORD_HEIGHT} -> {screen_w}x{screen_h} (x={scale_x:.3f}, y={scale_y:.3f})")

    try:
        for ev in events:
            if not should_continue() or not can_run(): return False
            ev_t = float(ev.get("t", base_t)) - base_t
            if speed_multiplier != 1.0:
                ev_t *= speed_multiplier
            target_wall = start_wall + ev_t

            while True:
                now = time.perf_counter()
                if now >= target_wall: break
                remaining = target_wall - now
                if now - last_check >= 0.05:
                    last_check = now
                    if not should_continue() or not can_run(): return False
                if remaining > 0.002: time.sleep(min(remaining * 0.5, 0.005))

            typ = str(ev.get("type", ""))
            k = str(ev.get("key", "")).lower().strip()
            try:
                with _autoit_lock:
                    if typ == "key_down" and k:
                        _autoit_key_down(k)
                        pressed_keys.add(k)
                    elif typ == "key_up" and k:
                        _autoit_key_up(k)
                        pressed_keys.discard(k)
            except Exception:
                pass

        return should_continue() and can_run()
    finally:
        with _autoit_lock:
            for key_name in list(pressed_keys):
                try:
                    _autoit_key_up(key_name)
                except Exception:
                    pass
                
            for k in ("w", "a", "s", "d", "space"):
                try:
                    _autoit_key_up(k)
                except Exception:
                    pass
                time.sleep(0.02)


def _coerce_array_of_points(val: Any) -> list[tuple[int, int]]:
    if not isinstance(val, collections.abc.Iterable) or isinstance(val, (str, bytes)): return []
    res = []
    for item in val:
        pt = _coerce_point(item, [0, 0])
        if pt[0] > 0 or pt[1] > 0: res.append((pt[0], pt[1]))
    return res

def load_egg_config(raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = raw_config if isinstance(raw_config, dict) else {}
    return {
        "egg_click_failsafe": _coerce_array_of_points(raw.get("egg_click_failsafe")),
        "fishing_mode": bool(raw.get("fishing_mode", False)),
        "collect_easter_egg": bool(raw.get("collect_easter_egg", False)),
        "egg_collect_interval_min": _coerce_int(raw.get("egg_collect_interval_min"), 5, 1, 1440),
        "egg_playback_multiplier": _coerce_float(raw.get("egg_playback_multiplier"), 1.0, 1.0, 2.0),
        "egg_ocr_detect_special": bool(raw.get("egg_ocr_detect_special", False)),
        "egg_ocr_discord_userid": str(raw.get("egg_ocr_discord_userid", "")).strip(),
        "non_vip_movement_path": bool(raw.get("non_vip_movement_path", False)),
        "equip_aura_before_egg_collect": bool(raw.get("equip_aura_before_egg_collect", False)),
        "egg_collect_aura_name": str(raw.get("egg_collect_aura_name", "")).strip(),
        "collections_button": _coerce_point(raw.get("collections_button"), [33, 443]),
        "exit_collections_button": _coerce_point(raw.get("exit_collections_button"), [385, 164]),
        "aura_menu": _coerce_point(raw.get("aura_menu"), [1200, 500]),
        "aura_search_bar": _coerce_point(raw.get("aura_search_bar"), [834, 364]),
        "first_aura_slot_pos": _coerce_point(raw.get("first_aura_slot_pos"), [0, 0]),
        "equip_aura_button": _coerce_point(raw.get("equip_aura_button"), [0, 0]),
        "inventory_close_button": _coerce_point(raw.get("inventory_close_button"), [1418, 298]),
        "fishing_close_button_pos": _coerce_point(raw.get("fishing_close_button_pos"), [1113, 342]),
        "chat_box_ocr_pos": _coerce_region(raw.get("chat_box_ocr_pos"), [0, 0, 400, 300]),
        "chat_close_button": _coerce_point(raw.get("chat_close_button"), [174, 40]),
    }


def _run_equip_aura_before_egg_collect(
    *,
    cfg: dict[str, Any],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
) -> bool:
    if not bool(cfg.get("equip_aura_before_egg_collect", False)):
        return True

    aura_name = str(cfg.get("egg_collect_aura_name", "")).strip()
    if not aura_name:
        return True

    if not should_continue() or not can_run():
        return False

    step_delay = 0.67 # 6767676767676767 TUFFFFFFFFFF
    aura_menu_x, aura_menu_y = cfg["aura_menu"]
    aura_search_x, aura_search_y = cfg["aura_search_bar"]
    first_slot_x, first_slot_y = cfg["first_aura_slot_pos"]
    equip_x, equip_y = cfg["equip_aura_button"]
    close_x, close_y = cfg["inventory_close_button"]
    fish_close_x, fish_close_y = cfg["fishing_close_button_pos"]

    if aura_menu_x > 0:
        autoit.mouse_click("left", aura_menu_x, aura_menu_y, 1, speed=3)
    if not sleep_interruptible(step_delay, 0.02):
        return False

    if first_slot_x > 0:
        autoit.mouse_move(first_slot_x, first_slot_y, speed=3)
        if not sleep_interruptible(step_delay, 0.02): return False
        try:
            autoit.mouse_wheel("up", max(1, int(round(5000 / 120.0))))
        except Exception:
            pass
        if not sleep_interruptible(step_delay, 0.02): return False
        autoit.mouse_click("left", first_slot_x, first_slot_y, 1, speed=3)
        
    if not sleep_interruptible(step_delay, 0.02): return False

    if aura_search_x > 0:
        autoit.mouse_click("left", aura_search_x, aura_search_y, 1, speed=3)
    if not sleep_interruptible(step_delay, 0.02):
        return False

    try:
        autoit.send(aura_name)
    except Exception:
        pass
    if not sleep_interruptible(step_delay, 0.02):
        return False

    _autoit_key_tap("enter")
    if not sleep_interruptible(step_delay, 0.02):
        return False

    if first_slot_x > 0:
        autoit.mouse_click("left", first_slot_x, first_slot_y, 1, speed=3)
    if not sleep_interruptible(step_delay, 0.02):
        return False

    if equip_x > 0:
        autoit.mouse_click("left", equip_x, equip_y, 1, speed=3)
    if not sleep_interruptible(step_delay, 0.02):
        return False

    if close_x > 0:
        autoit.mouse_click("left", close_x, close_y, 1, speed=3)
        if not sleep_interruptible(step_delay, 0.02): return False

    return True


def _load_egg_route_events(route_file: Path, log_prefix: str = "[EggCollect]") -> list[dict[str, Any]] | None:
    if not route_file.exists():
        return None
    try:
        with open(route_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        if isinstance(raw_data, dict) and "events" in raw_data:
            all_events = raw_data["events"]
        elif isinstance(raw_data, list):
            all_events = raw_data
        else:
            print(f"{log_prefix} {route_file.name} has unexpected format. Skipping.")
            return None

        _ALLOWED_KEYS = {"w", "a", "s", "d", "space"}
        filtered: list[dict[str, Any]] = [
            e for e in all_events
            if e.get("type") in ("key_down", "key_up") and e.get("key", "").lower() in _ALLOWED_KEYS
        ]
        if not filtered:
            print(f"{log_prefix} {route_file.name} has no usable events. Skipping.")
            return None
        return filtered
    except Exception as e:
        print(f"{log_prefix} Failed to load {route_file.name}: {e}")
        return None


def _run_single_egg_route(
    *,
    route_name: str,
    egg_events: list[dict[str, Any]],
    cfg: dict[str, Any],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    is_first_route: bool,
    activate_roblox_cb: Callable[[], None] | None = None,
    close_chat_fn: Callable[[], None] | None = None,
    egg_ocr_check_cb: Callable[[], None] | None = None,
    log_prefix: str = "[EggCollect]",
) -> bool:
    if not should_continue() or not can_run(): return False

    print(f"{log_prefix} Running {route_name} ({len(egg_events)} events)...")

    if activate_roblox_cb is not None:
        try:
            activate_roblox_cb()
        except Exception:
            pass
    
    if not sleep_interruptible(1, 0.02): return False

    if is_first_route:
        fish_close_x, fish_close_y = cfg["fishing_close_button_pos"]
        if bool(cfg.get("fishing_mode", False)) and fish_close_x > 0 and fish_close_y > 0:
            try:
                autoit.mouse_click("left", fish_close_x, fish_close_y, 1, speed=3)
            except Exception:
                pass

    if egg_ocr_check_cb is not None and bool(cfg.get("egg_ocr_detect_special", False)):
        try:
            egg_ocr_check_cb()
        except Exception as e:
            print(f"{log_prefix} egg_ocr_check_cb error: {e}")

    if not _run_respawn_sequence(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        action_delay_seconds=0.0,
        activate_roblox_cb=activate_roblox_cb,
    ):
        return False

    if not sleep_interruptible(3.5, 0.02): return False

    # Close chat if open (egg OCR may have left it open)
    if close_chat_fn is not None:
        try:
            print(f"{log_prefix} Closing chat if open...")
            close_chat_fn()
        except Exception as e:
            print(f"{log_prefix} close_chat_fn error: {e}")

    if not sleep_interruptible(0.5, 0.02): return False

    # Click collections button -> exit collections (camera reset)
    collections_x, collections_y = cfg["collections_button"]
    if collections_x > 0:
        autoit.mouse_click("left", collections_x, collections_y, speed=3)
    if not sleep_interruptible(1.0, 0.02):
        return False

    exit_x, exit_y = cfg["exit_collections_button"]
    if exit_x > 0:
        autoit.mouse_click("left", exit_x, exit_y, speed=3)
    if not sleep_interruptible(0.3, 0.02):
        return False

    cam_x = exit_x if exit_x > 0 else 500
    cam_y = exit_y if exit_y > 0 else 500
    try:
        autoit.mouse_move(cam_x, cam_y, speed=0)
        autoit.mouse_down("right")
        if not sleep_interruptible(0.1, 0.02):
            autoit.mouse_up("right")
            return False
        autoit.mouse_move(cam_x, cam_y + 75, speed=0)
        if not sleep_interruptible(0.1, 0.02):
            autoit.mouse_up("right")
            return False
        autoit.mouse_up("right")
    except Exception as e:
        print(f"{log_prefix} Camera adjustment error: {e}")
        try:
            autoit.mouse_up("right")
        except Exception:
            pass
    if not sleep_interruptible(0.2, 0.02):
        return False

    # Zoom out
    try:
        _autoit_key_down("o")
        if not sleep_interruptible(3.2, 0.05):
            _autoit_key_up("o")
            return False
        _autoit_key_up("o")
    except Exception:
        try: _autoit_key_up("o")
        except Exception: pass
    if not sleep_interruptible(0.3, 0.02):
        return False

    if not _run_equip_aura_before_egg_collect(
        cfg=cfg,
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
    ):
        return False

    if not sleep_interruptible(0.75, 0.02): return False

    non_vip = bool(cfg.get("non_vip_movement_path", False))
    custom_mult = _coerce_float(cfg.get("egg_playback_multiplier", 1.0), 1.0, 1.0, 2.0)
    walk_mult = (NON_VIP_WALK_SPEED_MULTIPLIER if non_vip else 1.0) * custom_mult

    if not sleep_interruptible(2.25, 0.02): return False

    # spam 'e' while path is running (to collect da egg)
    _e_spam_stop = threading.Event()
    def _spam_e():
        while not _e_spam_stop.is_set():
            try:
                with _autoit_lock:
                    _autoit_key_tap("e")
            except Exception:
                pass
            _e_spam_stop.wait(0.65)

    e_thread = threading.Thread(target=_spam_e, daemon=True)
    e_thread.start()

    print(f"{log_prefix} Walking {route_name} (speed_multiplier={walk_mult:.2f})...")
    try:
        path_ok = _replay_egg_path(
            events=egg_events,
            should_continue=should_continue,
            can_run=can_run,
            speed_multiplier=walk_mult,
            log_prefix=log_prefix,
        )

        if not sleep_interruptible(8.5, 0.05):
            path_ok = False
    finally:
        _e_spam_stop.set()
        e_thread.join(timeout=2.0)

    for k in ("w", "a", "s", "d", "space"):
        try:
            _autoit_key_up(k)
        except Exception:
            pass
        time.sleep(0.02)

    if not sleep_interruptible(1.25, 0.02): return False

    # Reset camera zoom
    try:
        _autoit_key_down("i")
        if not sleep_interruptible(4.0, 0.05):
            _autoit_key_up("i")
        else:
            _autoit_key_up("i")
    except Exception:
        try: _autoit_key_up("i")
        except Exception: pass
    sleep_interruptible(0.3, 0.02)
    try:
        _autoit_key_down("o")
        if not sleep_interruptible(0.65, 0.05):
            _autoit_key_up("o")
        else:
            _autoit_key_up("o")
    except Exception:
        try: _autoit_key_up("o")
        except Exception: pass
    sleep_interruptible(0.3, 0.02)

    if not path_ok:
        print(f"{log_prefix} {route_name} was interrupted.")
        return False

    print(f"{log_prefix} {route_name} complete.")

    if not sleep_interruptible(1, 0.02): return False

    # Egg failsafe click at the end of the route
    failsafes = cfg.get("egg_click_failsafe", [])
    if failsafes:
        print(f"{log_prefix} Executing {len(failsafes)} egg failsafe click(s)...")
        for fx, fy in failsafes:
            try:
                autoit.mouse_click("left", fx, fy, 1, speed=3)
            except Exception:
                pass
            sleep_interruptible(0.55, 0.02)

    return True


def run_egg_collect_once(
    *,
    cfg: dict[str, Any],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    activate_roblox_cb: Callable[[], None] | None = None,
    close_chat_fn: Callable[[], None] | None = None,
    egg_ocr_check_cb: Callable[[], None] | None = None,
    log_prefix: str = "[EggCollect]",
) -> bool:
    if not should_continue() or not can_run():
        return False


    base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(os.getcwd())
    paths_folder = base_dir / "paths"
    route_files: list[Path] = sorted(paths_folder.glob("egg_route*.json"))

    if not route_files:
        print(f"{log_prefix} No egg route files found in {paths_folder}. Skipping.")
        return True

    routes: list[tuple[str, list[dict[str, Any]]]] = []
    for rf in route_files:
        events = _load_egg_route_events(rf, log_prefix)
        if events:
            routes.append((rf.name, events))

    if not routes:
        print(f"{log_prefix} No usable egg route events found. Skipping.")
        return True

    print(f"{log_prefix} Starting egg collection cycle ({len(routes)} route{'s' if len(routes) > 1 else ''} found)...")

    # each route with full pre-collect + path + post-cleanup (yes im cool son)
    for i, (route_name, egg_events) in enumerate(routes):
        if not should_continue() or not can_run(): return False

        print(f"{log_prefix} Route {i + 1}/{len(routes)}: {route_name}")
        if not _run_single_egg_route(
            route_name=route_name,
            egg_events=egg_events,
            cfg=cfg,
            sleep_interruptible=sleep_interruptible,
            should_continue=should_continue,
            can_run=can_run,
            is_first_route=(i == 0),
            activate_roblox_cb=activate_roblox_cb,
            close_chat_fn=close_chat_fn,
            egg_ocr_check_cb=egg_ocr_check_cb,
            log_prefix=log_prefix,
        ):
            return False

    print(f"{log_prefix} All egg collection routes complete.")
    return True
