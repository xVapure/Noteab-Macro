from __future__ import annotations

import traceback
import json
import threading
from typing import Optional, Any
import win32gui, win32con
import webbrowser
import keyboard
import webview
import os
import sys
import time
import psutil
from datetime import datetime
import logging

# i added this so we can easily change macro version upon releases without having to change multiple back-end & front-end behaviours
# for future people that is reading the open source code, hello :p
current_version = "v2.1.3"
os.environ["COTEAB_MACRO_VERSION"] = current_version
UPDATE_LATEST_RELEASE_API_URL = "https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest"
os.environ["COTEAB_UPDATE_API_URL"] = UPDATE_LATEST_RELEASE_API_URL
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--disable-gpu" # disable gpu for webview2
os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1" # disable gpu for webkit

try: psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception: pass

from biome_tracker.config import (
    ensure_workspace_files,
    sync_config,
    load_config,
    save_config,
    normalize_auto_pop_biomes,
)
from biome_tracker.core import BiomeTracker
from biome_tracker.base_support import CalibrationManager, rare_biomes

def get_base_path():
    return sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))


def _get_frontend_dist_dirs() -> list[str]:
    base_path = get_base_path()
    if getattr(sys, "frozen", False):
        return [os.path.join(base_path, "lib", "dist")]
    return [
        os.path.join(base_path, "frontend", "dist"),
        os.path.join(base_path, "lib", "dist"),
    ]


def get_frontend_entry_url() -> str:
    for dist_dir in _get_frontend_dist_dirs():
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            try:
                cache_bust = int(os.path.getmtime(index_file))
                return f"{index_file}?v={cache_bust}"
            except Exception:
                return index_file
    return "http://localhost:5173"


def _read_cli_value(flag: str, default: str = "") -> str:
    try:
        if flag not in sys.argv:
            return default
        idx = sys.argv.index(flag)
        if idx + 1 >= len(sys.argv):
            return default
        return str(sys.argv[idx + 1]).strip()
    except Exception:
        return default


def _read_config_bool(config_data: Any, key: str, default: bool) -> bool:
    try:
        if not isinstance(config_data, dict):
            return bool(default)
        value = config_data.get(key, default)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", ""}:
                return False
        return bool(value)
    except Exception:
        return bool(default)


class Api:
    def __init__(self, tracker=None):
        self._tracker = tracker
        self._window = None
        self._calib_mgr = CalibrationManager()
        self._fishing_stop_event = threading.Event()
        self._fishing_thread = None
        self._fishing_lock = threading.Lock()
        self._fishing_runtime_state = {
            "fish_caught_count": 0,
            "fish_caught_since_merchant": 0,
            "fish_caught_since_br_sc": 0,
            "rejoin_in_progress": False,
            "force_sell_on_next_cycle": False,
            "merchant_requires_reset": False,
        }
        self._biome_confirm_evt = threading.Event()
        self._biome_confirm_result = None

    def set_window(self, window):
        self._window = window
        self._calib_mgr.set_refs(
            window=window,
            tracker=self._tracker,
            save_fn=save_config,
            emit_fn=self.emit_calibration_result
        )

    def get_config(self):
        if self._tracker and hasattr(self._tracker, 'config') and isinstance(self._tracker.config, dict) and self._tracker.config:
            return self._tracker.config
        return load_config()

    def save_config(self, config_data):
        normalized_config = dict(config_data) if isinstance(config_data, dict) else dict(self.get_config())
        biome_names = []
        if self._tracker and hasattr(self._tracker, "biome_data") and isinstance(self._tracker.biome_data, dict):
            biome_names = list(self._tracker.biome_data.keys())
        normalized_config["auto_pop_biomes"] = normalize_auto_pop_biomes(normalized_config, biome_names=biome_names)
        if (
            _read_config_bool(normalized_config, "fishing_failsafe_rejoin", False)
            and not _read_config_bool(normalized_config, "auto_reconnect", False)
        ):
            normalized_config["fishing_failsafe_rejoin"] = False

        save_config(normalized_config)
        if self._tracker:
            if not hasattr(self._tracker, "config") or not isinstance(self._tracker.config, dict):
                self._tracker.config = {}
            self._tracker.config.update(normalized_config)
            if 'webhook_url' in normalized_config:
                self._tracker.webhook_urls = normalized_config['webhook_url']
            if self._tracker.detection_running:
                if self._is_fishing_mode_enabled():
                    self._start_fishing_worker()
                else:
                    self._stop_fishing_worker()

    def import_config(self):
        try:
            if not self._window:
                return {"success": False, "error": "Window not available"}

            result = self._window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=("JSON Files (*.json)",),
            )

            if not result:
                return {"success": False, "error": "No file selected"}

            file_path = result[0] if isinstance(result, (list, tuple)) else result

            with open(file_path, "r", encoding="utf-8") as f:
                imported = json.loads(f.read())

            if not isinstance(imported, dict):
                return {"success": False, "error": "Invalid config file: must be a JSON object"}

            save_config(imported)

            if self._tracker:
                if not hasattr(self._tracker, "config") or not isinstance(self._tracker.config, dict):
                    self._tracker.config = {}
                self._tracker.config.update(imported)
                if 'webhook_url' in imported:
                    self._tracker.webhook_urls = imported['webhook_url']

            return {"success": True, "config": imported}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_window(self):
        self._stop_fishing_worker()
        if self._window:
            self._window.destroy()

    def minimize_window(self):
        if self._window:
            self._window.minimize()

    def toggle_maximize_window(self):
        if self._window:
            self._window.toggle_fullscreen()

    def set_always_on_top(self, enabled: bool):
        if self._window:
            try:
                hwnd = None
                if hasattr(self._window.gui, 'hwnd'):
                     hwnd = self._window.gui.hwnd
                else:
                     hwnd = win32gui.FindWindow(None, self._window.title)
                     
                if hwnd:
                     flag = win32con.HWND_TOPMOST if enabled else win32con.HWND_NOTOPMOST
                     win32gui.SetWindowPos(hwnd, flag, 0, 0, 0, 0,
                                           win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
            except Exception as e:
                print(f"Failed to set always on top via win32gui: {e}")
                self._window.on_top = enabled

    def open_url(self, url: str):
        webbrowser.open(url)

    def get_macro_status(self):
        if self._tracker and getattr(self._tracker, 'detection_running', False):
            return "RUNNING"
        return "STOPPED"

    def get_macro_version(self):
        return current_version

    def _is_fishing_mode_enabled(self) -> bool:
        if not self._tracker or not hasattr(self._tracker, "config"):
            return False
        cfg = getattr(self._tracker, "config", {})
        if not isinstance(cfg, dict):
            return False
        if bool(cfg.get("enable_idle_mode", False)):
            return False
        return bool(cfg.get("fishing_mode", False))

    def _fishing_can_run(self) -> bool:
        if not self._tracker:
            return False
        if not getattr(self._tracker, "detection_running", False):
            return False
        if not self._is_fishing_mode_enabled():
            return False
        if getattr(self._tracker, "reconnecting_state", False):
            self._fishing_runtime_state["rejoin_in_progress"] = True
            return False
        if bool(self._fishing_runtime_state.get("rejoin_in_progress", False)):
            self._fishing_runtime_state["rejoin_in_progress"] = False
            self._fishing_runtime_state["force_sell_on_next_cycle"] = True
        if getattr(self._tracker, "auto_pop_state", False):
            return False
        return True

    def _fishing_config_provider(self) -> dict[str, Any]:
        if self._tracker and hasattr(self._tracker, "config") and isinstance(self._tracker.config, dict):
            return dict(self._tracker.config)
        return load_config()

    def _on_fishing_failsafe_timeout(self) -> None:
        if not self._tracker:
            return
        current_biome = str(getattr(self._tracker, "current_biome", "") or "").upper().strip()
        if current_biome in rare_biomes:
            setattr(self._tracker, "_pending_fishing_failsafe_rejoin", True)
            try:
                self._tracker.append_log(
                    f"[FishingMode] Failsafe timed out during rare biome {current_biome}; delaying rejoin until the biome ends."
                )
                self._tracker.send_webhook_status(
                    f"Fishing failsafe timed out during {current_biome}. Rejoin is delayed until the rare biome ends.",
                    color=0xffcc00,
                )
            except Exception:
                pass
            return
        try:
            self._tracker.terminate_roblox_processes()
        except Exception as e:
            print(f"Fishing failsafe close Roblox failed: {e}")

        cfg = self._fishing_config_provider()
        if not bool(cfg.get("auto_reconnect", False)):
            self._emit_fishing_failsafe_warning(
                "Fishing failsafe timeout: Roblox was closed after 60 seconds without a minigame. "
                "Enable Private Server reconnection in Misc so it can recover automatically."
            )

    def _run_fishing_br_sc_sequence(self) -> bool:
        if not self._tracker:
            return False

        tracker = self._tracker
        prior_override = bool(getattr(tracker, "_fishing_br_sc_override", False))
        setattr(tracker, "_fishing_br_sc_override", True)
        ran_any = False

        try:
            try:
                tracker.activate_roblox_window()
            except Exception:
                pass

            try:
                tracker._use_br_sc_impl("strange controller")
                tracker.last_sc_time = datetime.now()
                ran_any = True
            except Exception as e:
                print(f"Fishing BR/SC strange controller step failed: {e}")

            try:
                tracker._use_br_sc_impl("biome randomizer")
                tracker.last_br_time = datetime.now()
                ran_any = True
            except Exception as e:
                print(f"Fishing BR/SC biome randomizer step failed: {e}")
        except Exception as e:
            print(f"Fishing BR/SC sequence failed: {e}")
        finally:
            setattr(tracker, "_fishing_br_sc_override", prior_override)

        return ran_any

    def _run_fishing_merchant_sequence(self) -> bool:
        if not self._tracker:
            return False

        tracker = self._tracker
        if isinstance(self._fishing_runtime_state, dict):
            self._fishing_runtime_state["merchant_requires_reset"] = False
        prior_override = bool(getattr(tracker, "_fishing_br_sc_override", False))
        setattr(tracker, "_fishing_br_sc_override", True)
        ran_any = False

        try:
            try:
                tracker.activate_roblox_window()
            except Exception:
                pass

            merchant_impl = getattr(tracker, "_merchant_teleporter_impl", None)
            if not callable(merchant_impl):
                print(
                    "Fishing merchant sequence skipped: full auto-merchant implementation "
                    "('_merchant_teleporter_impl') is unavailable."
                )
                return False

            # Use the full merchant implementation so fishing mode preserves
            # merchant teleporter, merchant detection/buy, webhook, and limbo logic.
            merchant_impl()
            ran_any = bool(getattr(tracker, "_last_merchant_sequence_ran", False))
            merchant_requires_reset = bool(
                getattr(tracker, "_last_merchant_sequence_requires_reset", False)
            )
            if isinstance(self._fishing_runtime_state, dict):
                self._fishing_runtime_state["merchant_requires_reset"] = merchant_requires_reset
            if ran_any:
                tracker.last_mt_time = datetime.now()
        except Exception as e:
            print(f"Fishing merchant teleporter sequence failed: {e}")
        finally:
            setattr(tracker, "_fishing_br_sc_override", prior_override)

        return ran_any

    def _start_fishing_worker(self) -> None:
        if not self._tracker:
            return
        with self._fishing_lock:
            if self._fishing_thread and self._fishing_thread.is_alive():
                return
            self._fishing_stop_event.clear()

            def _run_fishing():
                try:
                    from biome_tracker.fishing import run_fishing_loop
                    run_fishing_loop(
                        stop_event=self._fishing_stop_event,
                        can_run_cb=self._fishing_can_run,
                        config_provider=self._fishing_config_provider,
                        log_prefix="[FishingMode]",
                        print_start_stop=True,
                        on_failsafe_timeout=self._on_fishing_failsafe_timeout,
                        run_br_sc_sequence_cb=self._run_fishing_br_sc_sequence,
                        run_merchant_sequence_cb=self._run_fishing_merchant_sequence,
                        activate_roblox_cb=self._tracker.activate_roblox_window,
                        runtime_state=self._fishing_runtime_state,
                    )
                except Exception as e:
                    print(f"Fishing worker failed: {e}")

            self._fishing_thread = threading.Thread(target=_run_fishing, daemon=True)
            self._fishing_thread.start()

    def _stop_fishing_worker(self) -> None:
        with self._fishing_lock:
            self._fishing_stop_event.set()
            t = self._fishing_thread
            if t and t.is_alive():
                t.join(timeout=1.0)
            if not t or not t.is_alive():
                self._fishing_thread = None

    def set_biome_detection(self, enabled: bool):
        if not self._tracker:
            return
        if enabled:
            if not self._tracker.detection_running:
                threading.Thread(target=self._tracker.start_detection, daemon=True).start()
            if self._is_fishing_mode_enabled():
                self._start_fishing_worker()
            else:
                self._stop_fishing_worker()
                try:
                    self._tracker.start_potion_crafting()
                except Exception:
                    pass
        else:
            self._stop_fishing_worker()
            self._tracker.stop_detection()

        # Push the new status to the frontend
        self._emit_macro_status()

    def _emit_macro_status(self):
        status = self.get_macro_status()
        if self._window:
            self._window.evaluate_js(f'if(window.onMacroStatus) window.onMacroStatus("{status}");')
            
    def _emit_config_update(self):
        if self._window:
            self._window.evaluate_js(f'if(window.onConfigUpdated) window.onConfigUpdated();')

    def _emit_biome_update(self, biome: str):
        if self._window:
            self._window.evaluate_js(f'if(window.onBiomeUpdate) window.onBiomeUpdate("{biome}");')

    def _emit_shortcut(self, key: str):
        if self._window:
            self._window.evaluate_js(f'if(window.onShortcutEvent) window.onShortcutEvent("{key}");')

    def _emit_update_available(self, version: str, url: str):
        if self._window:
            self._window.evaluate_js(
                f'if(window.onUpdateAvailable) window.onUpdateAvailable("{version}", "{url}");'
            )

    def _emit_update_status(self, status: str):
        if self._window:
            self._window.evaluate_js(
                f'if(window.onUpdateStatus) window.onUpdateStatus("{status}");'
            )

    def _emit_fishing_failsafe_warning(self, message: str):
        if self._window:
            self._window.evaluate_js(
                f"if(window.onFishingFailsafeWarning) window.onFishingFailsafeWarning({json.dumps(str(message))});"
            )

    def _request_biome_confirm(self, biome: str):
        if not self._window:
            return None
        self._biome_confirm_evt.clear()
        self._biome_confirm_result = None
        try:
            print(f"[BiomeConfirm] Sending confirm request for biome: {biome}")
            self._window.evaluate_js(
                f"if(window.onBiomeConfirmRequest) window.onBiomeConfirmRequest({json.dumps(biome)});"
            )
        except Exception as e:
            print(f"[BiomeConfirm] evaluate_js failed: {e}")
            return None
        responded = self._biome_confirm_evt.wait(timeout=10)
        if not responded:
            return None
        return self._biome_confirm_result

    def confirm_biome_response(self, confirmed: bool):
        self._biome_confirm_result = bool(confirmed)
        self._biome_confirm_evt.set()

    def apply_update(self, download_url: str, version: str = ""):
        if self._tracker:
            def _do_update():
                try:
                    self._emit_update_status("downloading")
                    self._tracker.download_and_apply_update(download_url, version=version)
                except Exception as e:
                    self._emit_update_status("failed")
            threading.Thread(target=_do_update, daemon=True).start()
            return True
        return False

    def check_for_updates(self):
        if not self._tracker:
            return False

        def _do_check():
            try:
                self._tracker.check_for_updates()
            except Exception as e:
                print(f"Update check failed: {e}")

        threading.Thread(target=_do_check, daemon=True).start()
        return True

    def get_update_available(self):
        if not self._tracker:
            return None
        try:
            latest_release = self._tracker._fetch_latest_release()
            if not isinstance(latest_release, dict):
                return None

            latest_version = str(latest_release.get("tag_name", "")).strip()
            if not latest_version:
                return None
            if self._tracker._is_same_version(latest_version, current_version):
                return None

            _asset_name, download_url = self._tracker._pick_update_exe_asset(latest_release)
            if not download_url:
                return None

            return {"version": latest_version, "url": download_url}
        except Exception as e:
            print(f"Direct update query failed: {e}")
            return None

    def send_webhook_status(self, status: str, color: int):
        if self._tracker and hasattr(self._tracker, 'send_webhook_status'):
            self._tracker.send_webhook_status(status, color)

    def test_webhook(self, url: str) -> bool:
         return True

    def get_recorder_status(self) -> bool:
         return getattr(self._tracker, "_is_recording", False) if self._tracker else False

    def start_macro_recording(self):
         if self._tracker:
             self._tracker.start_recording_path()

    def stop_macro_recording(self):
         if self._tracker:
             return self._tracker.stop_recording_path("obby", save_dir="paths")
         return "No tracker"

    def stop_macro_recording_potion(self, name: str):
         if self._tracker:
             return self._tracker.stop_recording_path(name, save_dir="crafting_files_do_not_open")
         return "No tracker"

    def _get_frontend_url(self):
         return get_frontend_entry_url()

    def _open_recorder(self, mode: str = "obby"):
         base = self._get_frontend_url()
         sep = "&" if "?" in base else "?"
         url = f"{base}{sep}window=recorder"
         if mode == "potion":
             url += "&mode=potion"
         title = "Potion Recorder" if mode == "potion" else "Obby Recorder"
         webview.create_window(
             title=title,
             url=url,
             js_api=self,
             width=380,
             height=320,
             resizable=True,
             on_top=True,
         )

    def open_recorder_window(self):
         self._open_recorder("obby")

    def open_recorder_window_potion(self):
         self._open_recorder("potion")

    def list_potion_files(self):
         try:
             rec_dir = "crafting_files_do_not_open"
             if os.path.isdir(rec_dir):
                 return sorted([f for f in os.listdir(rec_dir) if f.lower().endswith(".json")])
         except Exception:
             pass
         return []

    def replay_recording(self):
         if self._tracker:
             return self._tracker.replay_path_recording("obby", save_dir="paths")
         return "No tracker"

    def replay_potion_recording(self, name: str):
         if self._tracker:
             return self._tracker.replay_path_recording(name, save_dir="crafting_files_do_not_open")
         return "No tracker"

    def align_camera(self):
         if self._tracker:
             self._tracker.align_camera()

    def emit_calibration_result(self, data):
         if self._window:
             self._window.evaluate_js(f"if(window.onCalibrationResult) window.onCalibrationResult({json.dumps(data)}); else if (window.onCalibrationResultMisc) window.onCalibrationResultMisc({json.dumps(data)});")

    def create_calibration_window(self, key="unknown", window_type="point"):
        self._calib_mgr.request_calibration(config_key=key, window_type=window_type)

    def display_calibration_on_screen(self, key: str, label: str = "", duration_ms: int = 2500):
        try:
            self._calib_mgr.request_display(
                config_key=key,
                label=label or key,
                duration_ms=duration_ms
            )
            return True
        except Exception:
            return False

    def display_all_fishing_calibrations_on_screen(self, duration_ms: int = 3000):
        try:
            cfg = self.get_config() if callable(getattr(self, "get_config", None)) else {}
            if not isinstance(cfg, dict):
                cfg = {}

            items = [
                {"key": "fishing_detect_pixel", "label": "Fishing Detect Pixel", "value": cfg.get("fishing_detect_pixel", [1176, 836])},
                {"key": "fishing_click_position", "label": "Start Fishing Button", "value": cfg.get("fishing_click_position", [862, 843])},
                {"key": "fishing_midbar_sample_pos", "label": "Mid Bar Sample Position", "value": cfg.get("fishing_midbar_sample_pos", [955, 767])},
                {"key": "fishing_close_button_pos", "label": "Fishing Close Button", "value": cfg.get("fishing_close_button_pos", [1113, 342])},
                {"key": "fishing_bar_region", "label": "Fishing Bar Region", "value": cfg.get("fishing_bar_region", [757, 762, 405, 21])},
                {"key": "fishing_flarg_dialogue_box", "label": "Captain Flarg Dialogue Box", "value": cfg.get("fishing_flarg_dialogue_box", [1046, 782])},
                {"key": "fishing_shop_open_button", "label": "Open Fishing Shop", "value": cfg.get("fishing_shop_open_button", [616, 938])},
                {"key": "fishing_shop_sell_tab", "label": "Fishing Shop Sell Tab", "value": cfg.get("fishing_shop_sell_tab", [1285, 312])},
                {"key": "fishing_shop_close_button", "label": "Close Fishing Shop", "value": cfg.get("fishing_shop_close_button", [1458, 269])},
                {"key": "fishing_shop_first_fish", "label": "First Fish In Shop", "value": cfg.get("fishing_shop_first_fish", [827, 404])},
                {"key": "fishing_shop_sell_all_button", "label": "Sell All Button", "value": cfg.get("fishing_shop_sell_all_button", [662, 799])},
                {"key": "fishing_confirm_sell_all_button", "label": "Confirm Sell All Button", "value": cfg.get("fishing_confirm_sell_all_button", [800, 619])},
            ]
            self._calib_mgr.request_display_many(items=items, duration_ms=duration_ms)
            return True
        except Exception:
            return False


def launch_app(api_class, tracker: Optional[BiomeTracker] = None) -> BiomeTracker:
    tracker = tracker or BiomeTracker()
    api = api_class(tracker)
    tracker.on_stats_update = api._emit_config_update
    tracker.on_biome_update = api._emit_biome_update
    tracker.on_update_available = api._emit_update_available
    tracker.on_update_status = api._emit_update_status
    tracker.on_biome_confirm_request = api._request_biome_confirm

    url = get_frontend_entry_url()

    window = webview.create_window(
        title=f"Coteab Macro {current_version}",
        url=url,
        js_api=api,
        width=950,
        height=550,
        min_size=(550, 500),
        resizable=True,
        frameless=False
    )
    api.set_window(window)

    # Register global F1/F2 hotkeys (work even when app is not focused)
    def on_f1():
        if not api._tracker.detection_running:
            api.set_biome_detection(True)
            api._emit_shortcut("START")

    def on_f2():
        if api._tracker.detection_running:
            api.set_biome_detection(False)
            api._emit_shortcut("STOP")

    keyboard.add_hotkey('f1', on_f1, suppress=False)
    keyboard.add_hotkey('f2', on_f2, suppress=False)


    class _WebviewLogHandler(logging.Handler):
        def emit(self, record):
            try:
                tracker.append_log(f"[pywebview] {record.getMessage()}")
            except Exception:
                pass
    _wv_handler = _WebviewLogHandler()
    _wv_handler.setLevel(logging.WARNING)
    logging.getLogger("pywebview").addHandler(_wv_handler)


    try:
        tracker.append_log("Starting pywebview with edgechromium")
        webview.start(debug=False, gui="edgechromium", private_mode=False)
    except Exception as e:
        print(f"[Webview] edgechromium failed: {e}")
        tracker.append_log(f"edgechromium backend failed: {e} — retrying with default backend...")
        try:
            window = webview.create_window(
                title=f"Coteab Macro {current_version}",
                url=url,
                js_api=api,
                width=950,
                height=550,
                min_size=(550, 500),
                resizable=True,
                frameless=False
            )
            api.set_window(window)
            webview.start(debug=False, private_mode=False)
        except Exception as e2:
            print(f"[Webview] Default backend also failed: {e2}")
            tracker.append_log(f"Default backend also failed: {e2}")

    return tracker


def bind_global_hotkeys(tracker: BiomeTracker) -> None:
    _ = tracker


def stop_app(tracker: Optional[BiomeTracker]) -> None:
    if tracker is not None and getattr(tracker, "detection_running", False):
        tracker.stop_detection()


def main() -> int:
    ensure_workspace_files()

    tracker = None
    try:
        tracker = BiomeTracker()
        is_finalize_launch = "--coteab-finalize-update" in sys.argv

        canonical_target = _read_cli_value("--coteab-target", "CoteabMacro.exe")
        old_pid_raw = _read_cli_value("--coteab-old-pid", "")
        try:
            old_pid = int(old_pid_raw) if old_pid_raw else None
        except Exception:
            old_pid = None

        if tracker.maybe_self_rename_to_canonical_exe(canonical_target, old_pid=old_pid):
            return 0

        auto_update_enabled = _read_config_bool(
            getattr(tracker, "config", {}),
            "auto_update_enabled",
            True,
        )
        if auto_update_enabled and tracker.apply_startup_auto_update():
            return 0

        tracker = launch_app(Api, tracker=tracker)
        return 0
    except KeyboardInterrupt:
        print("Exited (Keyboard interrupted)")
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}")
        traceback.print_exc()
        return 1
    finally:
        try:
            stop_app(tracker)
        except Exception:
            pass
        try:
            sync_config()
        except Exception:
            pass
        try:
            keyboard.unhook_all()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
