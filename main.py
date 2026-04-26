from __future__ import annotations

import traceback
import json
import threading
from typing import Optional, Any
import ctypes
import win32gui, win32con, win32api
import webbrowser
import webview
import os
import sys
import time
import psutil
from datetime import datetime
import logging
import shutil
import urllib.request

try:
    import numpy
    import cv2
    import pyautogui
except Exception as e:
    err_text = str(e)
    if "numpy" in err_text.lower() or "c-extension" in err_text.lower() or "dll" in err_text.lower() or "cv2" in err_text.lower():
        msg = (
            "Coteab Macro failed to load required components.\n\n"
            "This is because your computer is missing the standard 'Visual C++ Redistributable (x64)' (i think so).\n\n"
            "Please download and install it from Microsoft's official website and try open the macro again!\n\n"
            f"Error details: {err_text}"
        )
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, msg, "Missing Windows Component", 0x10 | 0x0)
        except Exception:
            pass
        sys.exit(1)
    else:
        raise

# i added this so we can easily change macro version upon releases without having to change multiple back-end & front-end behaviours
# for future people that is reading the open source code, hello :p
current_version = "v2.1.6-hotfix1"
os.environ["COTEAB_MACRO_VERSION"] = current_version
UPDATE_LATEST_RELEASE_API_URL = "https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest"
os.environ["COTEAB_UPDATE_API_URL"] = UPDATE_LATEST_RELEASE_API_URL
os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1" 

_wv2_user_data_base = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "CoteabMacro", "WebView2UserData"
)
try:
    if os.path.exists(_wv2_user_data_base):
        for _f in os.listdir(_wv2_user_data_base):
            try: shutil.rmtree(os.path.join(_wv2_user_data_base, _f), ignore_errors=True)
            except Exception: pass
except Exception:
    pass

_wv2_user_data = os.path.join(_wv2_user_data_base, f"Session_{int(time.time())}")
os.makedirs(_wv2_user_data, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = _wv2_user_data

try: psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
except Exception: pass

from biome_tracker.config import (
    ensure_workspace_files,
    sync_config,
    load_config,
    save_config,
    normalize_auto_pop_biomes,
)

def get_base_path(): return sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))

def _get_frontend_dist_dirs() -> list[str]:
    base_path = get_base_path()
    if getattr(sys, "frozen", False):
        return [os.path.join(base_path, "lib", "dist")]

    return [
        os.path.join(base_path, "frontend", "dist"),
        os.path.join(base_path, "lib", "dist"),
    ]


def get_frontend_entry_data():
    # I have temporarily  this frontend url load for the source code (since it will overrides your current index.html if you try to customize frontend layout)
    # frontend_url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/index.html"
    # try:
    #     req = urllib.request.Request(frontend_url, headers={'User-Agent': 'Mozilla/5.0'})
    #     with urllib.request.urlopen(req, timeout=4) as response:
    #         html_content = response.read().decode('utf-8')
    #         if html_content and len(html_content) > 1000:
    #             print("Fetched frontend entry from GitHub")
    #             return {"html": html_content}
    # except Exception as e:
    #     print(f"Failed to fetch frontend from GitHub: {e}, falling back to local files.")

    for dist_dir in _get_frontend_dist_dirs():
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    return {"html": f.read()}
            except Exception:
                pass
            
    return {"url": "http://localhost:5173"}

 
def get_frontend_entry_url():
    for dist_dir in _get_frontend_dist_dirs():
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            abs_path = os.path.abspath(index_file).replace("\\", "/")
            return f"file:///{abs_path}"
    return "http://localhost:5173"


def _read_cli_value(flag, default=""):
    try:
        if flag not in sys.argv: return default
        idx = sys.argv.index(flag)
        if idx + 1 >= len(sys.argv): return default
        return str(sys.argv[idx + 1]).strip()
    except Exception:
        return default


def _cfg_bool(cfg, key, default=False):
    try:
        if not isinstance(cfg, dict): return bool(default)
        val = cfg.get(key, default)
        if isinstance(val, str):
            val = val.strip().lower()
            return val in ("1", "true", "yes", "on")
        return bool(val)
    except Exception:
        return bool(default)


class Api:
    def __init__(self, tracker=None):
        self._tracker = tracker
        self._window = None
        self._calib_mgr = None

        # fishing mode stuff
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

        # rare biome pop up confirmation
        self._biome_confirm_evt = threading.Event()
        self._biome_confirm_result = None

    def set_window(self, window):
        self._window = window
        if self._calib_mgr is None:
            from biome_tracker.base_support import CalibrationManager
            self._calib_mgr = CalibrationManager()
        self._calib_mgr.set_refs(
            window=window,
            tracker=self._tracker,
            save_fn=save_config,
            emit_fn=self.emit_calibration_result
        )

    def get_config(self):
        t = self._tracker
        if t and isinstance(getattr(t, 'config', None), dict) and t.config:
            return t.config
        return load_config()

    def save_config(self, config_data):
        prev_anti_afk = False
        if self._tracker and isinstance(getattr(self._tracker, "config", None), dict):
            prev_anti_afk = bool(self._tracker.config.get("anti_afk", False))

        cfg = dict(config_data) if isinstance(config_data, dict) else dict(self.get_config())

        # normalize auto pop biomes with whatever biome list we have
        biome_names = []
        if self._tracker and isinstance(getattr(self._tracker, "biome_data", None), dict):
            biome_names = list(self._tracker.biome_data.keys())
        cfg["auto_pop_biomes"] = normalize_auto_pop_biomes(cfg, biome_names=biome_names)


        if _cfg_bool(cfg, "fishing_failsafe_rejoin") and not _cfg_bool(cfg, "auto_reconnect"):
            cfg["fishing_failsafe_rejoin"] = False

        save_config(cfg)
        if self._tracker:
            if not isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config = {}
            self._tracker.config.update(cfg)

            # sync webhook urls to the tracker
            if 'webhook_url' in cfg:
                self._tracker.webhook_urls = cfg['webhook_url']
                try:
                    if hasattr(self._tracker, "refresh_active_webhook_channels"):
                        self._tracker.refresh_active_webhook_channels(force=True)
                except Exception:
                    pass

            if self._tracker.detection_running:
                # hot-swap fishing mode
                if self._is_fishing_mode_enabled():
                    self._start_fishing_worker()
                else:
                    self._stop_fishing_worker()

                if not prev_anti_afk and self._tracker.config.get("anti_afk", False):
                    try:
                        threading.Thread(target=self._tracker.perform_anti_afk_action, daemon=True).start()
                    except Exception:
                        pass

    def import_config(self):
        try:
            if not self._window:
                return {"success": False, "error": "Window not available"}

            result = self._window.create_file_dialog(
                webview.FileDialog.OPEN, allow_multiple=False,
                file_types=("JSON Files (*.json)",),
            )
            if not result:
                return {"success": False, "error": "No file selected"}

            path = result[0] if isinstance(result, (list, tuple)) else result
            with open(path, "r", encoding="utf-8") as f:
                imported = json.loads(f.read())
            if not isinstance(imported, dict):
                return {"success": False, "error": "Invalid config file: must be a JSON object"}

            save_config(imported)

            if self._tracker:
                if not isinstance(getattr(self._tracker, "config", None), dict):
                    self._tracker.config = {}
                self._tracker.config.update(imported)
                if 'webhook_url' in imported:
                    self._tracker.webhook_urls = imported['webhook_url']
                try:
                    if hasattr(self._tracker, "refresh_active_webhook_channels"):
                        self._tracker.refresh_active_webhook_channels(force=True)
                except Exception: pass

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

    def _is_fishing_mode_enabled(self):
        cfg = getattr(self._tracker, "config", None) if self._tracker else None
        if not isinstance(cfg, dict): return False
        if cfg.get("enable_idle_mode", False): return False
        return bool(cfg.get("fishing_mode", False))

    def _fishing_can_run(self):
        t = self._tracker
        if not t or not getattr(t, "detection_running", False): return False
        if not self._is_fishing_mode_enabled(): return False

        # pause during reconnect, but mark that we need to sell when we come back
        if getattr(t, "reconnecting_state", False):
            self._fishing_runtime_state["rejoin_in_progress"] = True
            return False
        if self._fishing_runtime_state.get("rejoin_in_progress"):
            self._fishing_runtime_state["rejoin_in_progress"] = False
            self._fishing_runtime_state["force_sell_on_next_cycle"] = True

        _STALE_TIMEOUT = 240
        now = time.time()
        blocking_flags = ("_egg_collecting", "_egg_collection_pending", "auto_pop_state")
        any_blocking = False

        for flag_name in blocking_flags:
            if getattr(t, flag_name, False):
                ts_key = f"_fishing_block_ts_{flag_name}"
                first_seen = self._fishing_runtime_state.get(ts_key, 0)
                if first_seen == 0:
                    self._fishing_runtime_state[ts_key] = now
                    any_blocking = True
                elif (now - first_seen) >= _STALE_TIMEOUT:
                    setattr(t, flag_name, False)
                    self._fishing_runtime_state[ts_key] = 0
                    try:
                        t.append_log(
                            f"[FishingMode] Force cleared stale '{flag_name}' flag "
                            f"after {_STALE_TIMEOUT}s — was blocking fishing."
                        )
                    except Exception: pass
                else:
                    any_blocking = True
            else:
                ts_key = f"_fishing_block_ts_{flag_name}"
                if self._fishing_runtime_state.get(ts_key, 0): self._fishing_runtime_state[ts_key] = 0

        if any_blocking: return False
        return True

    def _fishing_config_provider(self):
        t = self._tracker
        if t and isinstance(getattr(t, "config", None), dict):
            return dict(t.config)
        return load_config()

    def _on_fishing_failsafe_timeout(self):
        if not self._tracker: return
        biome = str(getattr(self._tracker, "current_biome", "") or "").upper().strip()

        # dont kill roblox during a rare biome lol, wait for it to end
        from biome_tracker.base_support import rare_biomes
        if biome in rare_biomes:
            self._tracker._pending_fishing_failsafe_rejoin = True
            try:
                self._tracker.append_log(f"[FishingMode] Failsafe timed out during {biome}; delaying rejoin.")
                self._tracker.send_webhook_status(
                    f"Fishing failsafe timed out during {biome}. Rejoin delayed until biome ends.",
                    color=0xffcc00,
                )
            except Exception: pass
            return

        try: self._tracker.terminate_roblox_processes()
        except Exception as e: print(f"Fishing failsafe close Roblox failed: {e}")

        if not self._fishing_config_provider().get("auto_reconnect", False):
            self._emit_fishing_failsafe_warning(
                "Fishing failsafe timeout: Roblox closed after 60s with no minigame. "
                "Enable PS reconnect in Misc so it can recover automatically."
            )

    def _run_fishing_br_sc_sequence(self):
        if not self._tracker: return False
        t = self._tracker
        old_override = getattr(t, "_fishing_br_sc_override", False)
        t._fishing_br_sc_override = True
        ran = False
        try:
            try: t.activate_roblox_window()
            except Exception: pass

            try:
                t._use_br_sc_impl("strange controller")
                t.last_sc_time = datetime.now()
                ran = True
            except Exception as e:
                print(f"Fishing SC step failed: {e}")
            try:
                t._use_br_sc_impl("biome randomizer")
                t.last_br_time = datetime.now()
                ran = True
            except Exception as e:
                print(f"Fishing BR step failed: {e}")
        except Exception as e:
            print(f"Fishing BR/SC sequence failed: {e}")
        finally:
            t._fishing_br_sc_override = old_override
        return ran

    def _run_fishing_merchant_sequence(self):
        if not self._tracker: return False
        t = self._tracker
        self._fishing_runtime_state["merchant_requires_reset"] = False
        old_override = getattr(t, "_fishing_br_sc_override", False)
        t._fishing_br_sc_override = True
        ran = False
        try:
            try: t.activate_roblox_window()
            except Exception: pass

            merchant_fn = getattr(t, "_merchant_teleporter_impl", None)
            if not callable(merchant_fn):
                print("Fishing merchant sequence skipped: _merchant_teleporter_impl unavailable")
                return False

            # reuse the same merchant logic so we get buy, webhook, limbo, everything
            merchant_fn()
            ran = bool(getattr(t, "_last_merchant_sequence_ran", False))
            self._fishing_runtime_state["merchant_requires_reset"] = bool(
                getattr(t, "_last_merchant_sequence_requires_reset", False)
            )
            if ran: t.last_mt_time = datetime.now()
        except Exception as e:
            print(f"Fishing merchant sequence failed: {e}")
        finally:
            t._fishing_br_sc_override = old_override
        return ran

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
                        close_chat_fn=self._tracker.close_chat_if_open,
                        runtime_state=self._fishing_runtime_state,
                        set_fishing_busy_cb=lambda busy: setattr(self._tracker, "_fishing_busy", busy),
                        on_f2_pressed_cb=lambda: (self.set_biome_detection(False), self._emit_shortcut("STOP")),
                        egg_ocr_check_cb=self._tracker._perform_egg_ocr_check,
                        merchant_ocr_check_cb=getattr(self._tracker, "_scheduled_merchant_ocr_check", None),
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

    def set_biome_detection(self, enabled):
        if not self._tracker: return
        if enabled:
            if not self._tracker.detection_running:
                threading.Thread(target=self._tracker.start_detection, daemon=True).start()
            if self._is_fishing_mode_enabled():
                self._start_fishing_worker()
            else:
                self._stop_fishing_worker()
                try: self._tracker.start_potion_crafting()
                except Exception: pass
        else:
            self._stop_fishing_worker()
            self._tracker.stop_detection()
        self._emit_macro_status()

    # --- frontend event emitters (JS bridge) ---

    def _safe_eval_js(self, js_code):
        if not self._window: return
        try:
            self._window.evaluate_js(js_code)
        except Exception: pass

    def _emit_macro_status(self):
        self._safe_eval_js(f'if(window.onMacroStatus) window.onMacroStatus("{self.get_macro_status()}");')

    def _emit_config_update(self):
        self._safe_eval_js('if(window.onConfigUpdated) window.onConfigUpdated();')

    def _emit_biome_update(self, biome):
        self._safe_eval_js(f'if(window.onBiomeUpdate) window.onBiomeUpdate("{biome}");')

    def _emit_shortcut(self, key):
        self._safe_eval_js(f'if(window.onShortcutEvent) window.onShortcutEvent("{key}");')

    def _emit_update_available(self, version, url):
        self._safe_eval_js(f'if(window.onUpdateAvailable) window.onUpdateAvailable("{version}", "{url}");')

    def _emit_update_status(self, status):
        self._safe_eval_js(f'if(window.onUpdateStatus) window.onUpdateStatus("{status}");')

    def _emit_fishing_failsafe_warning(self, msg):
        self._safe_eval_js(f"if(window.onFishingFailsafeWarning) window.onFishingFailsafeWarning({json.dumps(str(msg))});")

    def _request_biome_confirm(self, biome: str):
        self._biome_confirm_evt.clear()
        self._biome_confirm_result = None
        popup_window = None
        try:
            print(f"[BiomeConfirm] Spawning independent popup for biome: {biome}")
            fe = get_frontend_entry_data()
            popup_w, popup_h = 480, 400
            try:
                screen_w = win32api.GetSystemMetrics(0)
                screen_h = win32api.GetSystemMetrics(1)
                popup_x = (screen_w - popup_w) // 2
                popup_y = (screen_h - popup_h) // 2
            except Exception:
                popup_x, popup_y = 300, 200

            win_kwargs = {
                "title": f"\u26a0\ufe0f Rare Biome Detected \u2014 {biome} \u26a0\ufe0f",
                "js_api": self,
                "width": popup_w,
                "height": popup_h,
                "x": popup_x,
                "y": popup_y,
                "resizable": False,
            }

            if "html" in fe:
                injected_script = f'''<script>
                const _OrigSearchParams = window.URLSearchParams;
                window.URLSearchParams = class extends _OrigSearchParams {{
                    constructor(init) {{
                        if (init === window.location.search || !init) {{
                            init = "?window=biome_confirm&biome={biome}";
                        }}
                        super(init);
                    }}
                }};
                </script>'''
                html = fe["html"].replace("<head>", f"<head>{injected_script}", 1)
                win_kwargs["html"] = html
            else:
                base = fe["url"]
                sep = "&" if "?" in base else "?"
                win_kwargs["url"] = f"{base}{sep}window=biome_confirm&biome={biome}"

            popup_window = webview.create_window(**win_kwargs)

            try:
                def _flash():
                    time.sleep(1.0)
                    try:
                        hwnd = win32gui.FindWindow(None, f"⚠️ Rare Biome Detected — {biome} ⚠️")
                        if hwnd:
                            win32gui.FlashWindowEx(hwnd, win32con.FLASHW_ALL | win32con.FLASHW_TIMERNOFG, 5, 0)
                    except Exception:
                        pass
                threading.Thread(target=_flash, daemon=True).start()
            except Exception:
                pass

        except Exception as e:
            print(f"[BiomeConfirm] Failed to create popup window: {e}")
            return None

        responded = self._biome_confirm_evt.wait(timeout=10)

        # Close the popup window
        try:
            if popup_window:
                popup_window.destroy()
        except Exception:
            pass

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

    def check_winocr_status(self):
        try:
            import winocr
            return {"installed": True, "version": getattr(winocr, "__version__", "unknown")}
        except ImportError:
            return {"installed": False, "version": None}
        except Exception as e:
            return {"installed": False, "version": None, "error": str(e)}

    def test_webhook(self, url): return True  # placeholder

    def get_recorder_status(self):
        return getattr(self._tracker, "_is_recording", False) if self._tracker else False

    def start_macro_recording(self):
        if self._tracker: self._tracker.start_recording_path()

    def stop_macro_recording(self):
        if self._tracker: return self._tracker.stop_recording_path("obby", save_dir="paths")
        return "No tracker"

    def stop_macro_recording_potion(self, name: str):
         if self._tracker:
             return self._tracker.stop_recording_path(name, save_dir="crafting_files_do_not_open")
         return "No tracker"

    def _get_frontend_url(self):
         return get_frontend_entry_url()

    def _open_recorder(self, mode: str = "obby"):
         fe = get_frontend_entry_data()
         query = "window=recorder"
         if mode == "potion":
             query += "&mode=potion"
         title = "Potion Recorder" if mode == "potion" else "Obby Recorder"

         win_kwargs = {
             "title": title,
             "js_api": self,
             "width": 380,
             "height": 320,
             "resizable": True,
             "on_top": True,
         }

         if "html" in fe:
             injected_script = f'''<script>
             const _OrigSearchParams = window.URLSearchParams;
             window.URLSearchParams = class extends _OrigSearchParams {{
                 constructor(init) {{
                     if (init === window.location.search || !init) {{
                         init = "?{query}";
                     }}
                     super(init);
                 }}
             }};
             </script>'''
             html = fe["html"].replace("<head>", f"<head>{injected_script}", 1)
             win_kwargs["html"] = html
         else:
             base = fe["url"]
             sep = "&" if "?" in base else "?"
             win_kwargs["url"] = f"{base}{sep}{query}"

         webview.create_window(**win_kwargs)

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

    def check_obby_path_exists(self):
        try:
            obby_file = os.path.join(os.getcwd(), "paths", "obby.json")
            if not os.path.isfile(obby_file):
                return False
            with open(obby_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return bool(data)
        except Exception:
            return False

    def replay_recording(self):
         if self._tracker:
             return self._tracker.replay_path_recording("obby", save_dir="paths")
         return "No tracker"

    def replay_potion_recording(self, name: str):
         if self._tracker:
             return self._tracker.replay_path_recording(name, save_dir="crafting_files_do_not_open")
         return "No tracker"

    def test_aura_keybind(self):
         if self._tracker:
             def test_record():
                 try:
                    keybind = self._tracker.aura_record_keybind_var.get()
                    if not keybind: return
                    keys = [key.strip() for key in keybind.split('+')]
                    time.sleep(2)
                    pyautogui.hotkey(*keys)
                 except Exception as e:
                    print(f"Error testing aura keybind: {e}")
             threading.Thread(target=test_record, daemon=True).start()

    def test_biome_keybind(self):
         if self._tracker:
             def test_record():
                 try:
                    keybind = self._tracker.rarest_biome_keybind_var.get()
                    if not keybind: return
                    keys = [key.strip() for key in keybind.split('+')]
                    time.sleep(2)
                    pyautogui.hotkey(*keys)
                 except Exception as e:
                    print(f"Error testing biome keybind: {e}")
             threading.Thread(target=test_record, daemon=True).start()

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


def launch_app(api_class, tracker=None):
    tracker = tracker or BiomeTracker()
    api = api_class(tracker)
    tracker.on_stats_update = api._emit_config_update
    tracker.on_biome_update = api._emit_biome_update
    tracker.on_update_available = api._emit_update_available
    tracker.on_update_status = api._emit_update_status
    tracker.on_biome_confirm_request = api._request_biome_confirm
    tracker.on_status_change = lambda status: api._emit_macro_status()

    fe = get_frontend_entry_data()
    win_args = {
        "title": f"Coteab Macro {current_version}",
        "js_api": api,
        "width": 985, "height": 550,
        "min_size": (550, 500),
        "resizable": True, "frameless": False
    }
    if "html" in fe: win_args["html"] = fe["html"]
    else: win_args["url"] = fe["url"]

    window = webview.create_window(**win_args)
    api.set_window(window)

    # F1 = start, F2 = stop
    _VK_F1 = 0x70
    _VK_F2 = 0x71
    _hotkey_stop = threading.Event()
    _user32 = ctypes.windll.user32

    def _hotkey_poll_loop():
        f1_was = False
        f2_was = False
        while not _hotkey_stop.is_set():
            try:
                f1_now = bool(_user32.GetAsyncKeyState(_VK_F1) & 0x8000)
                f2_now = bool(_user32.GetAsyncKeyState(_VK_F2) & 0x8000)

                if f1_now and not f1_was:
                    def _do_start():
                        try:
                            if not api._tracker.detection_running:
                                api.set_biome_detection(True)
                                api._emit_shortcut("START")
                        except Exception:
                            pass
                    threading.Thread(target=_do_start, daemon=True).start()

                if f2_now and not f2_was:
                    def _do_stop():
                        try:
                            if api._tracker.detection_running:
                                api.set_biome_detection(False)
                                api._emit_shortcut("STOP")
                        except Exception:
                            pass
                    threading.Thread(target=_do_stop, daemon=True).start()

                f1_was = f1_now
                f2_was = f2_now
            except Exception:
                pass
            _hotkey_stop.wait(0.05)

    _hotkey_thread = threading.Thread(target=_hotkey_poll_loop, name="HotkeyPoll", daemon=True)
    _hotkey_thread.start()

    class _WvLog(logging.Handler):
        def emit(self, record):
            try: tracker.append_log(f"[pywebview] {record.getMessage()}")
            except Exception: pass
    logging.getLogger("pywebview").addHandler(_WvLog())

    # try edgechromium first, fall back to whatever else is available
    try:
        tracker.append_log("Starting pywebview (edgechromium)")
        webview.start(debug=False, gui="edgechromium", private_mode=False)
    except Exception as e:
        print(f"[Webview] edgechromium failed: {e}")
        tracker.append_log(f"edgechromium failed: {e}, retrying default...")
        try: webview.start(debug=False, private_mode=False)
        except Exception as e2:
            print(f"[Webview] Default backend also failed: {e2}")
            tracker.append_log(f"Default backend also failed: {e2}")

    return tracker

_LOADING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #0f172a;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    display: flex; align-items: center; justify-content: center;
    height: 100vh; overflow: hidden; color: #e2e8f0;
  }
  .wrap { text-align: center; }
  .spinner {
    width: 38px; height: 38px; margin: 0 auto 18px;
    border: 3px solid rgba(255,255,255,0.08);
    border-top-color: #f59e0b;
    border-radius: 50%;
    animation: spin .7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  h1 { font-size: 17px; font-weight: 600; margin-bottom: 6px; color: #f1f5f9; }
  p  { font-size: 12px; color: #64748b; }
</style>
</head>
<body>
  <div class="wrap">
    <div class="spinner"></div>
    <h1>Tysm for using Coteab Macro!!</h1>
    <p>Loading macro dependencies plss wait :3 (it should be quick)\u2026</p>
  </div>
</body>
</html>
"""

def stop_app(tracker):
    if tracker and getattr(tracker, "detection_running", False): tracker.stop_detection()

def main():
    ensure_workspace_files()
    tracker = None
    api = Api(tracker=None)
    try:
        win_args = {
            "title": f"Coteab Macro {current_version}",
            "js_api": api,
            "html": _LOADING_HTML,
            "width": 985, "height": 550,
            "min_size": (550, 500),
            "resizable": True, "frameless": False,
        }
        loading_window = webview.create_window(**win_args)
        api._window = loading_window

        def _background_init():
            nonlocal tracker
            try:
                from biome_tracker.core import BiomeTracker
                tracker = BiomeTracker()
                canonical = _read_cli_value("--coteab-target", "CoteabMacro.exe")
                old_pid_raw = _read_cli_value("--coteab-old-pid", "")
                try: old_pid = int(old_pid_raw) if old_pid_raw else None
                except Exception: old_pid = None

                if tracker.maybe_self_rename_to_canonical_exe(canonical, old_pid=old_pid):
                    loading_window.destroy()
                    return

                if _cfg_bool(getattr(tracker, "config", {}), "auto_update_enabled", True):
                    if tracker.apply_startup_auto_update():
                        loading_window.destroy()
                        return


                api._tracker = tracker
                tracker.on_stats_update = api._emit_config_update
                tracker.on_biome_update = api._emit_biome_update
                tracker.on_update_available = api._emit_update_available
                tracker.on_update_status = api._emit_update_status
                tracker.on_biome_confirm_request = api._request_biome_confirm
                tracker.on_status_change = lambda status: api._emit_macro_status()
                api.set_window(loading_window)

                fe = get_frontend_entry_data()
                if "html" in fe:
                    loading_window.load_html(fe["html"])
                else:
                    loading_window.load_url(fe["url"])

            except Exception as exc:
                print(f"Background init error: {exc}")
                traceback.print_exc()

        # ---- F1/F2 hotkeys ----
        _VK_F1 = 0x70
        _VK_F2 = 0x71
        _hotkey_stop = threading.Event()
        _user32 = ctypes.windll.user32

        def _hotkey_poll_loop():
            f1_was = False
            f2_was = False
            while not _hotkey_stop.is_set():
                try:
                    if api._tracker is None:
                        _hotkey_stop.wait(0.2)
                        continue

                    f1_now = bool(_user32.GetAsyncKeyState(_VK_F1) & 0x8000)
                    f2_now = bool(_user32.GetAsyncKeyState(_VK_F2) & 0x8000)

                    if f1_now and not f1_was:
                        def _do_start():
                            try:
                                if not api._tracker.detection_running:
                                    api.set_biome_detection(True)
                                    api._emit_shortcut("START")
                            except Exception:
                                pass
                        threading.Thread(target=_do_start, daemon=True).start()

                    if f2_now and not f2_was:
                        def _do_stop():
                            try:
                                if api._tracker.detection_running:
                                    api.set_biome_detection(False)
                                    api._emit_shortcut("STOP")
                            except Exception:
                                pass
                        threading.Thread(target=_do_stop, daemon=True).start()

                    f1_was = f1_now
                    f2_was = f2_now
                except Exception:
                    pass
                _hotkey_stop.wait(0.05)

        threading.Thread(target=_hotkey_poll_loop, name="HotkeyPoll", daemon=True).start()

        class _WvLog(logging.Handler):
            def emit(self, record):
                try:
                    if tracker: tracker.append_log(f"[pywebview] {record.getMessage()}")
                except Exception: pass
        logging.getLogger("pywebview").addHandler(_WvLog())

        try:
            webview.start(func=_background_init, debug=False, gui="edgechromium", private_mode=False)
        except Exception as e:
            print(f"[Webview] edgechromium failed: {e}")
            try: webview.start(func=_background_init, debug=False, private_mode=False)
            except Exception as e2:
                print(f"[Webview] Default backend also failed: {e2}")

        return 0

    except KeyboardInterrupt:
        print("Exited (Ctrl+C)")
        return 130
    except Exception as exc:
        print(f"Fatal error: {exc}")
        traceback.print_exc()
        return 1
    finally:
        try: stop_app(tracker)
        except Exception: pass
        try: sync_config()
        except Exception: pass
        try: _hotkey_stop.set()
        except Exception: pass


if __name__ == "__main__":
    raise SystemExit(main())
