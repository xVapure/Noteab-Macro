from __future__ import annotations
import copy
import traceback
import json
import threading
import queue
from typing import Optional, Any
import ctypes
import win32gui, win32con, win32api
import webbrowser
import webview
import os
import sys

# i added this so we can easily change macro version upon releases without having to change multiple back-end & front-end behaviours
# for future people that is reading the open source code, hello :p
current_version = "v2.2.1_test32"
os.environ["COTEAB_MACRO_VERSION"] = current_version
UPDATE_LATEST_RELEASE_API_URL = "https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest"
os.environ["COTEAB_UPDATE_API_URL"] = UPDATE_LATEST_RELEASE_API_URL
os.environ["WEBKIT_DISABLE_COMPOSITING_MODE"] = "1"
import time
import psutil
from datetime import datetime, timedelta
import logging
import shutil
import urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import socket
import random
from pathlib import Path
from biome_tracker.config import APPDATA_BASE
import keyboard
from tkinter import filedialog as FileDialog
ORIGINAL_ABS_FILE = os.path.abspath(__file__)
os.environ['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'] = '--disable-gpu'
debug_mode = False # This mode should only be used by people who knows what they're doing.


# paths crafting_files_do_not_open and macoroni logs go into appdata/local instead of next to the EXE (maybe)
APPDATA_BASE.mkdir(parents=True, exist_ok=True)
os.chdir(APPDATA_BASE)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p)
kernel32.CreateMutexW.restype = ctypes.c_void_p
kernel32.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
kernel32.WaitForSingleObject.restype = ctypes.c_uint32
ctypes.set_last_error(0)
macro_mutex = kernel32.CreateMutexW(None, True, "CoteabMacroSingleInstance")
mutexerror = ctypes.get_last_error()
if not macro_mutex:
    ctypes.windll.user32.MessageBoxW(0, "Coteab Macro could not create its single-instance lock.", "Coteab Macro", 0x30)
    sys.exit(1)
if mutexerror == 183:
    oldpidarg = None
    try:
        if "--coteab-old-pid" in sys.argv:
            idx = sys.argv.index("--coteab-old-pid")
            if idx + 1 < len(sys.argv): oldpidarg = int(sys.argv[idx + 1])
    except Exception:
        pass

    if oldpidarg is not None:
        waitresult = kernel32.WaitForSingleObject(macro_mutex, 60000)
        if waitresult not in (0, 0x80):
            ctypes.windll.user32.MessageBoxW(0, "Coteab Macro could not finish restarting. Please close it and try again.", "Coteab Macro", 0x30)
            sys.exit(1)
    else:
        ctypes.windll.user32.MessageBoxW(0, "Coteab Macro is already running!\n\nPlease close the existing instance before opening a new one.", "Coteab Macro", 0x30)
        sys.exit(0)

try:
    import numpy
    import pyautogui
except Exception as e:
    err_text = str(e)
    if "numpy" in err_text.lower() or "c-extension" in err_text.lower() or "dll" in err_text.lower():
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
from biome_tracker.core import BiomeTracker

def get_base_path(): return sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(ORIGINAL_ABS_FILE)

def _get_frontend_dist_dirs() -> list[str]:
    base_path = get_base_path()
    from biome_tracker.config import APPDATA_BASE

    dirs = [
        os.path.join(str(APPDATA_BASE), "dist"),
        os.path.join(str(APPDATA_BASE), "frontend", "dist"),
        os.path.join(os.getcwd(), "frontend", "dist"),
        os.path.join(os.getcwd(), "dist"),
    ]

    if getattr(sys, "frozen", False):
        dirs.append(os.path.join(base_path, "lib", "dist"))
        dirs.append(os.path.join(base_path, "dist"))
    else:
        dirs.append(os.path.join(base_path, "frontend", "dist"))
        dirs.append(os.path.join(base_path, "lib", "dist"))
        dirs.append(os.path.join(base_path, "dist"))

    return [d for d in dirs if os.path.exists(d)]


def get_frontend_entry():
    for dist_dir in _get_frontend_dist_dirs():
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            try:
                abs_path = os.path.abspath(index_file).replace("\\", "/")
                with open(index_file, "r", encoding="utf-8") as f:
                    html_content = f.read()
                print(f"Loading frontend from local: {abs_path}")
                return {"html": html_content, "url": f"file:///{abs_path}"}
            except Exception as e:
                print(f"Error reading local index.html: {e}")

    frontend_url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/index.html"
    try:
        from biome_tracker.config import APPDATA_BASE
        appdata_dist = os.path.join(str(APPDATA_BASE), "dist")
        os.makedirs(appdata_dist, exist_ok=True)

        req = urllib.request.Request(frontend_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as response:
            html_content = response.read().decode('utf-8')
            if html_content and len(html_content) > 1000:
                saved_path = os.path.join(appdata_dist, "index.html")
                with open(saved_path, "w", encoding="utf-8") as f: f.write(html_content)
                abs_path = os.path.abspath(saved_path).replace("\\", "/")
                print(f"Fetched frontend from GitHub -> saved to: {abs_path}")
                return {"html": html_content, "url": f"file:///{abs_path}"}
    except Exception as e:
        print(f"Failed to fetch frontend from GitHub: {e}")

    return {"url": "http://localhost:5173"}


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

class LoggerWriter:
    def __init__(self, filename="macro_logs.txt", original_stream=None):
        self.terminal = original_stream
        self.filename = filename

    def write(self, message):
        if self.terminal is not None:
            try:
                self.terminal.write(message)
                self.terminal.flush()
            except UnicodeEncodeError:
                try:
                    self.terminal.write(message.encode("ascii", "replace").decode("ascii"))
                    self.terminal.flush()
                except Exception:
                    pass
            except Exception:
                pass
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(message)
        except Exception:
            pass

    def flush(self):
        if self.terminal is not None:
            try:
                self.terminal.flush()
            except Exception:
                pass

sys.stdout = LoggerWriter("macro_logs.txt", sys.stdout)
sys.stderr = LoggerWriter("macro_logs.txt", sys.stderr)

class Api:
    def __init__(self, tracker=None):
        self._tracker = tracker
        config = tracker.config if tracker and isinstance(getattr(tracker, "config", None), dict) else load_config()
        self.config_baseline = self.config_snapshot(config)
        self.config_dirty = False
        if tracker is not None:
            tracker._fishing_api = self
        self._window = None
        self._calib_mgr = None

        # fishing mode stuff
        self._fishing_stop_event = threading.Event()
        self._fishing_thread = None
        self._fishing_lock = threading.Lock()
        self._macro_toggle_lock = threading.Lock()
        self._start_hotkey_lock = threading.Lock()
        self._restart_pending = False
        self._merchant_event_lock = threading.Lock()
        self._fishing_runtime_state = {
            "fish_caught_count": 0,
            "fish_caught_since_merchant": 0,
            "fish_caught_since_br_sc": 0,
            "rejoin_in_progress": False,
            "force_sell_on_next_cycle": False,
            "initial_start_pending": False,
            "merchant_requires_reset": False,
            "merchant_event_pending": False,
            "merchant_event_queue": [],
            "merchant_event_active_name": "",
            "merchant_reset_pending": False,
            "fish_sale_remaining": 0,
            "merchant_retry_delay": 0.0,
            "merchant_retry_after": 0.0,
        }

        # rare biome pop up confirmation
        self._biome_confirm_evt = threading.Event()
        self._biome_confirm_result = None
        self.emergency_port = None

    def config_snapshot(self, config):
        ignored = {
            "session_time", "session_window_start", "macro_last_start",
            "biome_counts", "merchant_counts", "potion_last_file",
            "custom_theme_data", "custom_labels", "custom_icons",
            "custom_macro_title", "custom_macro_version",
        }
        if not isinstance(config, dict):
            return {}
        return {key: copy.deepcopy(value) for key, value in config.items() if key not in ignored}

    def reset_config_baseline(self):
        config = self._tracker.config if self._tracker and isinstance(getattr(self._tracker, "config", None), dict) else load_config()
        self.config_baseline = self.config_snapshot(config)
        self.config_dirty = False

    def mark_config_dirty(self, config):
        self.config_dirty = self.config_snapshot(config) != self.config_baseline

    def set_window(self, window):
        self._window = window
        if self._calib_mgr is None:
            from biome_tracker.base_support import CalibrationManager
            self._calib_mgr = CalibrationManager()
        self._calib_mgr.set_refs(
            window=window,
            tracker=self._tracker,
            save_fn=self.save_config,
            emit_fn=self.emit_calibration_result
        )

    def get_config(self):
        t = self._tracker
        if t and isinstance(getattr(t, 'config', None), dict) and t.config:
            return t.config
        return load_config()

    def get_screen_resolution(self):
        try:
            import ctypes
            user32 = ctypes.windll.user32
            user32.SetProcessDPIAware()
            width = user32.GetSystemMetrics(0)
            height = user32.GetSystemMetrics(1)
            scale = user32.GetDpiForSystem() / 96.0
            return {"width": width, "height": height, "resolution": f"{width}x{height}", "scale": scale}
        except Exception as e:
            print(f"get_screen_resolution error: {e}")
            return {"width": 0, "height": 0, "resolution": "unknown", "scale": 1.0}

    def get_biome_data(self):
        if self._tracker and isinstance(getattr(self._tracker, "biome_data", None), dict):
            result = {}
            for biome, data in self._tracker.biome_data.items():
                color = data.get("color", "0xffffff")
                if isinstance(color, str) and color.startswith("0x"): color = "#" + color[2:]
                result[biome] = color
            return result
        return {}

    def get_full_biome_data(self):
        if self._tracker and isinstance(getattr(self._tracker, "biome_data", None), dict):
            return self._tracker.biome_data
        return {}

    def open_appdata(self):
        try:
            os.startfile(str(APPDATA_BASE))
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config_patch(self, key, value):
        if not save_config({key: value}):
            raise RuntimeError("Failed to write config.json")
        if self._tracker:
            previous = dict(self._tracker.config)
            self._tracker.config[key] = value
            self.mark_config_dirty(load_config())
            self._apply_runtime_config(previous)
        else:
            self.mark_config_dirty(load_config())

    def save_config(self, config_data):
        previous = dict(self._tracker.config) if self._tracker and isinstance(getattr(self._tracker, "config", None), dict) else {}
        cfg = dict(config_data) if isinstance(config_data, dict) else dict(self.get_config())

        biome_names = []
        if self._tracker and isinstance(getattr(self._tracker, "biome_data", None), dict):
            biome_names = list(self._tracker.biome_data.keys())
        cfg["auto_pop_biomes"] = normalize_auto_pop_biomes(cfg, biome_names=biome_names)

        if _cfg_bool(cfg, "fishing_failsafe_rejoin") and not _cfg_bool(cfg, "auto_reconnect"):
            cfg["fishing_failsafe_rejoin"] = False

        if not save_config(cfg):
            raise RuntimeError("Failed to write config.json")
        self.mark_config_dirty(load_config())
        if self._tracker:
            if not isinstance(getattr(self._tracker, "config", None), dict):
                self._tracker.config = {}
            self._tracker.config.update(cfg)
            if "webhook_url" in cfg:
                self._tracker.webhook_urls = cfg["webhook_url"]
                try:
                    if hasattr(self._tracker, "refresh_active_webhook_channels"):
                        self._tracker.refresh_active_webhook_channels(force=True)
                except Exception:
                    pass
            self._apply_runtime_config(previous)

    def _apply_runtime_config(self, previous):
        tracker = self._tracker
        if not tracker:
            return
        was_remote = bool(previous.get("remote_access_enabled", False))
        remote = bool(tracker.config.get("remote_access_enabled", False))
        remote_thread = getattr(tracker, "remote_bot_thread", None)
        if not remote:
            if was_remote or (remote_thread and remote_thread.is_alive()):
                tracker.stop_remote_bot()
        elif (not was_remote or previous.get("remote_bot_token") != tracker.config.get("remote_bot_token")) and not (remote_thread and remote_thread.is_alive()):
            tracker.start_remote_bot()
        if not tracker.detection_running:
            return
        if self._is_fishing_mode_enabled():
            tracker.stop_potion_crafting()
            self._start_fishing_worker()
        else:
            self._stop_fishing_worker()
            tracker.start_potion_crafting()
        if previous.get("anti_afk") != tracker.config.get("anti_afk") or previous.get("anti_afk_interval") != tracker.config.get("anti_afk_interval"):
            wake = getattr(tracker, "_anti_afk_wake_event", None)
            if wake:
                wake.set()

    def restart_app(self, start_macro=False):
        import subprocess
        if getattr(sys, "frozen", False):
            args = [sys.executable] + sys.argv[1:]
        else:
            args = [sys.executable] + sys.argv
        index = 0
        while index < len(args):
            if args[index] == "--coteab-old-pid":
                del args[index:index + 2]
            elif args[index] == "--coteab-start-after-restart":
                del args[index]
            else:
                index += 1
        args.extend(["--coteab-old-pid", str(os.getpid())])
        if start_macro:
            args.append("--coteab-start-after-restart")
        if not getattr(sys, "frozen", False):
            args[1] = ORIGINAL_ABS_FILE
        env = os.environ.copy()
        if getattr(sys, "frozen", False):
            env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        try:
            subprocess.Popen(args, env=env)
        except Exception as e:
            print(f"Failed to spawn restart process: {e}")
            return False
        threading.Thread(target=lambda: (time.sleep(0.5), os._exit(0)), daemon=True).start()
        return True

    def start_from_hotkey(self):
        if not self._tracker:
            return
        with self._start_hotkey_lock:
            if self._tracker.detection_running or self._restart_pending:
                return
            if self.config_dirty:
                self._restart_pending = True
                if not self.restart_app(start_macro=True):
                    self._restart_pending = False
                    self.set_biome_detection(True)
                    self._emit_shortcut("START")
                return
            self.set_biome_detection(True)
            self._emit_shortcut("START")

    def run_git_cmd(self, cmd_str):
        try:
            import subprocess
            res = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
            return {"stdout": res.stdout, "stderr": res.stderr, "returncode": res.returncode}
        except Exception as e:
            return {"error": str(e)}

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
            previous = dict(self._tracker.config) if self._tracker and isinstance(getattr(self._tracker, "config", None), dict) else {}
            if not save_config(imported):
                return {"success": False, "error": "Failed to write config.json"}
            if self._tracker:
                self._tracker.config.update(imported)
                if "webhook_url" in imported:
                    self._tracker.webhook_urls = imported["webhook_url"]
                try:
                    if hasattr(self._tracker, "refresh_active_webhook_channels"):
                        self._tracker.refresh_active_webhook_channels(force=True)
                except Exception:
                    pass
                self.mark_config_dirty(self._tracker.config)
                self._apply_runtime_config(previous)
            else:
                self.mark_config_dirty(load_config())
            return {"success": True, "config": imported}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON file"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    def export_calibration_data_to_downloads(self, calibration_data=None):
        try:
            export_data = dict(calibration_data) if isinstance(calibration_data, dict) else {}
            if not export_data:
                export_data = self.get_config() or {}

            downloads_dir = Path(os.path.expanduser("~/Downloads"))
            downloads_dir.mkdir(parents=True, exist_ok=True)
            selected_dir = FileDialog.askdirectory(initialdir=str(downloads_dir), title="Select Downloads Folder")
            if not selected_dir:
                return {"success": False, "error": "No directory selected"}
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(selected_dir) / f"macro_calibrations_{timestamp}.json"
            with open(output_path, "w", encoding="utf-8") as handle:
                json.dump({
                    "presets": [
                        {
                            "resolution": "",
                            "scale": "",
                            "mode": "",
                            "calibrations": export_data,
                        }
                    ]
                }, handle, indent=4)

            return {"success": True, "path": str(output_path)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def import_calibration_data_from_file(self):
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
                return {"success": False, "error": "Invalid calibration file: must be a JSON object"}

            return {"success": True, "calibrations": imported}
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON file"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_theme(self, theme_data, filename="coteab_theme.json"):
        try:
            if not self._window:
                return {"success": False, "error": "Window not available"}

            result = self._window.create_file_dialog(
                webview.FileDialog.SAVE, save_filename=filename,
                file_types=("JSON Files (*.json)",)
            )
            if not result:
                return {"success": False, "error": "Cancelled"}

            path = result[0] if isinstance(result, (list, tuple)) else result
            with open(path, "w", encoding="utf-8") as f:
                json.dump(theme_data, f, indent=4)

            return {"success": True, "path": path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def close_window(self):
        self._stop_fishing_worker()
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass

        def delayed_exit():
            time.sleep(1.5)
            os._exit(0)
        threading.Thread(target=delayed_exit, daemon=True).start()
        return {"success": True}

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

    def _setup_emergency_server(self):
        class SafeModeHandler(BaseHTTPRequestHandler):
            api = self

            def do_GET(self):
                if self.path == "/health":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"OK")
                else:
                    # Serve files from any valid dist directory
                    file_path = self.path.split('?')[0].lstrip('/')
                    if not file_path or file_path == 'index.html':
                        file_path = 'index.html'

                    found_full_path = None
                    for dist_dir in _get_frontend_dist_dirs():
                        full_path = os.path.join(dist_dir, file_path)
                        if os.path.exists(full_path) and os.path.isfile(full_path):
                            found_full_path = full_path
                            break

                    if found_full_path:
                        self.send_response(200)
                        if file_path.endswith('.js'): self.send_header('Content-type', 'application/javascript')
                        elif file_path.endswith('.css'): self.send_header('Content-type', 'text/css')
                        elif file_path.endswith('.html'): self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        with open(found_full_path, 'rb') as f:
                            self.wfile.write(f.read())
                    else:
                        self.send_response(404)
                        self.end_headers()

            def do_POST(self):
                if self.path.startswith("/api/"):
                    method_name = self.path.replace("/api/", "")
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    try:
                        args = json.loads(post_data) if post_data else []
                    except:
                        args = []

                    method = getattr(self.api, method_name, None)
                    if method and callable(method):
                        try:
                            if isinstance(args, list): result = method(*args)
                            elif isinstance(args, dict): result = method(**args)
                            else: result = method()

                            self.send_response(200)
                            self.send_header('Content-type', 'application/json')
                            self.send_header('Access-Control-Allow-Origin', '*')
                            self.end_headers()
                            self.wfile.write(json.dumps(result).encode())
                        except Exception as e:
                            self.send_response(500)
                            self.end_headers()
                            self.wfile.write(str(e).encode())

            def do_OPTIONS(self):
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()

            def log_message(self, format, *args): pass

        self.emergency_port = random.randint(18000, 19000)
        def _run():
            try:
                server = ThreadingHTTPServer(('127.0.0.1', self.emergency_port), SafeModeHandler)
                print(f"Browser mode running on http://127.0.0.1:{self.emergency_port}")
                server.serve_forever()
            except Exception as e:
                print(f"Server failed: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _setup_emergency_hotkey(self):
        def trigger():
            print("Emergency UI Triggered! Hiding main window...")
            if hasattr(self, '_window') and self._window:
                try:
                    self._window.hide()
                    print("Main window hidden.")
                except Exception as e:
                    print(f"Note: Could not hide window: {e}")

            url = f"http://127.0.0.1:{self.emergency_port}/index.html?safe_mode=1"
            webbrowser.open(url)
            print(f"Emergency UI opened in browser: {url}")

        keyboard.add_hotkey('ctrl+shift+f10', trigger)

    def get_active_modules(self):
        if not self._tracker: return {}
        t = self._tracker
        cfg = t.config

        modules = {}
        det = t.detection_running

        categories = {
            "Core Features": {
                "Biome Detection": {"active": det, "enabled": True},
                "Aura Detection": {"active": det and _cfg_bool(cfg, "enable_aura_detection"), "enabled": _cfg_bool(cfg, "enable_aura_detection")},
                "Macro Idle Mode": {"active": _cfg_bool(cfg, "enable_idle_mode"), "enabled": _cfg_bool(cfg, "enable_idle_mode")},
                "Anti-AFK": {"active": det and _cfg_bool(cfg, "anti_afk", True), "enabled": _cfg_bool(cfg, "anti_afk", True)},
                "Auto Reconnect": {"active": det and _cfg_bool(cfg, "auto_reconnect"), "enabled": _cfg_bool(cfg, "auto_reconnect")},
                "OCR Failsafe": {"active": det and _cfg_bool(cfg, "enable_ocr_failsafe"), "enabled": _cfg_bool(cfg, "enable_ocr_failsafe")},
                "Remote Control (Discord)": {"active": bool(getattr(t, "_remote_bot_running", False)), "enabled": _cfg_bool(cfg, "remote_access_enabled")},
                "Player Logger": {"active": det and _cfg_bool(cfg, "player_logger", True), "enabled": _cfg_bool(cfg, "player_logger", True)},
            },
            "Fishing": {
                "Fishing Mode": {"active": det and self._is_fishing_mode_enabled(), "enabled": _cfg_bool(cfg, "fishing_mode")},
                "Fishing Selling": {"active": _cfg_bool(cfg, "fishing_enable_selling") and _cfg_bool(cfg, "fishing_mode"), "enabled": _cfg_bool(cfg, "fishing_enable_selling")},
                "Fishing Failsafe (rejoin)": {"active": _cfg_bool(cfg, "fishing_failsafe_rejoin") and _cfg_bool(cfg, "fishing_mode"), "enabled": _cfg_bool(cfg, "fishing_failsafe_rejoin")},
                "Fishing UI Nav Close": {"active": _cfg_bool(cfg, "fishing_ui_nav_close") and _cfg_bool(cfg, "fishing_mode"), "enabled": _cfg_bool(cfg, "fishing_ui_nav_close")},
                "Fishing Aura Equip": {"active": _cfg_bool(cfg, "fishing_equip_aura_before_movement") and _cfg_bool(cfg, "fishing_mode"), "enabled": _cfg_bool(cfg, "fishing_equip_aura_before_movement")},
            },
            "Pathing & Movement": {
                "Eden Path": {"active": bool(getattr(t, "_eden_running", False)), "enabled": _cfg_bool(cfg, "go_to_eden_spawn")},
                "Eden Detection": {"active": det and _cfg_bool(cfg, "eden_detection"), "enabled": _cfg_bool(cfg, "eden_detection")},
                "Auto Eden Contract": {"active": bool(getattr(t, "_eden_running", False)) and _cfg_bool(cfg, "auto_eden_contract"), "enabled": _cfg_bool(cfg, "auto_eden_contract")},
                "Basic Obby": {"active": bool(getattr(t, "_obby_running", False)), "enabled": _cfg_bool(cfg, "enable_obby_path") or _cfg_bool(cfg, "enable_auto_obby")},
                "Easter Egg Path": {"active": bool(getattr(t, "_egg_running", False)), "enabled": _cfg_bool(cfg, "collect_easter_egg")},
                "Reset on Rare Biomes": {"active": det and _cfg_bool(cfg, "reset_on_rare"), "enabled": _cfg_bool(cfg, "reset_on_rare")},
                "Teleport Back to Limbo": {"active": det and _cfg_bool(cfg, "teleport_back_to_limbo"), "enabled": _cfg_bool(cfg, "teleport_back_to_limbo")},
                "Auto Roblox Fullscreen": {"active": det and _cfg_bool(cfg, "auto_roblox_fullscreen"), "enabled": _cfg_bool(cfg, "auto_roblox_fullscreen")},
                "Auto Chat Close": {"active": det and _cfg_bool(cfg, "auto_chat_close"), "enabled": _cfg_bool(cfg, "auto_chat_close")},
            },
            "Item Usage & Buffs": {
                "Auto Pop Buff": {"active": bool(getattr(t, "auto_pop_state", False)), "enabled": True}, # It's a dict of settings so generally enabled
                "Auto Pop Glitched": {"active": det and _cfg_bool(cfg, "auto_pop_glitched"), "enabled": _cfg_bool(cfg, "auto_pop_glitched")},
                "Auto Pop Dreamspace": {"active": det and _cfg_bool(cfg, "auto_pop_dreamspace"), "enabled": _cfg_bool(cfg, "auto_pop_dreamspace")},
                "Auto Pop Cyberspace": {"active": det and _cfg_bool(cfg, "auto_pop_cyberspace"), "enabled": _cfg_bool(cfg, "auto_pop_cyberspace")},
                "Cyberspace Only Warp": {"active": det and _cfg_bool(cfg, "cyberspace_only_warp"), "enabled": _cfg_bool(cfg, "cyberspace_only_warp")},
                "Glitched Buff Enable": {"active": det and _cfg_bool(cfg, "enable_buff_glitched"), "enabled": _cfg_bool(cfg, "enable_buff_glitched")},
                "BR / SC Sequence": {"active": bool(getattr(t, "_br_sc_running", False)), "enabled": _cfg_bool(cfg, "biome_randomizer") or _cfg_bool(cfg, "strange_controller")},
                "Float Aura": {"active": det and _cfg_bool(cfg, "use_float_aura"), "enabled": _cfg_bool(cfg, "use_float_aura")},
            },
            "Merchants & Economy": {
                "Auto Merchant": {"active": bool(getattr(t, "on_auto_merchant_state", False)), "enabled": _cfg_bool(cfg, "merchant_teleporter")},
                "Merchant OCR": {"active": det and _cfg_bool(cfg, "merchant_ocr"), "enabled": _cfg_bool(cfg, "merchant_ocr")},
                "Auto Merchant in Limbo": {"active": det and _cfg_bool(cfg, "auto_merchant_in_limbo"), "enabled": _cfg_bool(cfg, "auto_merchant_in_limbo")},
                "Daily Quests": {"active": det and _cfg_bool(cfg, "auto_claim_daily_quests"), "enabled": _cfg_bool(cfg, "auto_claim_daily_quests")},
            },
            "Crafting": {
                "Potion Crafting": {"active": bool(getattr(t, "_potion_thread_active", False)), "enabled": _cfg_bool(cfg, "enable_potion_crafting")},
                "Potion Switching": {"active": _cfg_bool(cfg, "enable_potion_switching") and _cfg_bool(cfg, "enable_potion_crafting"), "enabled": _cfg_bool(cfg, "enable_potion_switching")},
            },
            "Recording & Screenshots": {
                "Aura Recording": {"active": det and _cfg_bool(cfg, "enable_aura_record"), "enabled": _cfg_bool(cfg, "enable_aura_record")},
                "Aura Screenshot": {"active": det and _cfg_bool(cfg, "aura_detection_screenshot"), "enabled": _cfg_bool(cfg, "aura_detection_screenshot")},
                "Rare Biome Recording": {"active": det and _cfg_bool(cfg, "record_rare_biome"), "enabled": _cfg_bool(cfg, "record_rare_biome")},
                "Periodic Aura Screenshot": {"active": det and _cfg_bool(cfg, "periodical_aura_screenshot"), "enabled": _cfg_bool(cfg, "periodical_aura_screenshot")},
                "Periodic Inventory Screenshot": {"active": det and _cfg_bool(cfg, "periodical_inventory_screenshot"), "enabled": _cfg_bool(cfg, "periodical_inventory_screenshot")},
                "Glitch Effect UI": {"active": det and _cfg_bool(cfg, "enable_glitch_effect"), "enabled": _cfg_bool(cfg, "enable_glitch_effect")},
            }
        }

        for cat_name, cat_modules in categories.items():
            for mod_name, mod_data in cat_modules.items():
                modules[mod_name] = mod_data

        incompatibilities = []
        if _cfg_bool(cfg, "enable_idle_mode"):
            incompatibilities.append("Idle Mode is ON: Most automated actions are paused infinitely.")

        if _cfg_bool(cfg, "go_to_eden_spawn") and _cfg_bool(cfg, "fishing_mode"):
            incompatibilities.append("Conflict: Both Eden Path and Fishing Mode are enabled. Fishing will take priority unless blocked.")

        if _cfg_bool(cfg, "enable_potion_crafting") and _cfg_bool(cfg, "fishing_mode"):
            incompatibilities.append("Potion Crafting is enabled: It has the highest priority take over from Fishing Mode and cancels any automated actions.")

        return {
            "modules": modules,
            "incompatibilities": incompatibilities
        }

    def get_macro_logs(self, max_lines=100):
        try:
            log_path = os.path.join(os.getcwd(), "macro_logs.txt")
            if not os.path.exists(log_path):
                return {"lines": []}
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                all_lines = f.readlines()
            tail = all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines
            cleaned = [line.rstrip("\n\r") for line in tail if line.strip()]
            return {"lines": cleaned}
        except Exception as e:
            return {"lines": [f"[Error reading logs: {e}]"]}

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
            self._fishing_runtime_state["initial_start_pending"] = False
            return False
        if self._fishing_runtime_state.get("rejoin_in_progress"):
            self._fishing_runtime_state["rejoin_in_progress"] = False
            self._fishing_runtime_state["force_sell_on_next_cycle"] = True

        _STALE_TIMEOUT = 240
        now = time.time()
        blocking_flags = ("auto_pop_state",)
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

    def queue_fishing_action(self, fn, name="fishing_action"):
        t = self._tracker
        if not t or not getattr(t, "_fishing_worker_active", False):
            return fn()
        with t._fishing_action_lock:
            if name in t._fishing_action_pending:
                return False
            t._fishing_action_pending.add(name)
            t._fishing_action_queue.put((fn, name))
        return True

    def _clear_fishing_actions(self):
        t = self._tracker
        if not t:
            return
        with t._fishing_action_lock:
            t._fishing_action_pending.clear()
            while True:
                try:
                    t._fishing_action_queue.get_nowait()
                except queue.Empty:
                    break
                except Exception:
                    break

    def _run_fishing_action_request(self):
        t = self._tracker
        if not t:
            return False
        try:
            fn, name = t._fishing_action_queue.get_nowait()
        except Exception:
            return False
        t._fishing_action_override = True
        t._fishing_busy = False
        try:
            fn()
        except Exception as e:
            print(f"Fishing action {name} failed: {e}")
        finally:
            t._fishing_action_override = False
            with t._fishing_action_lock:
                t._fishing_action_pending.discard(name)
        return True

    def _on_fishing_event(self, event):
        t = self._tracker
        if not t or event not in ("catch", "sale") or not self._is_fishing_mode_enabled():
            return
        if not getattr(t, "periodical_inventory_var", None) or not t.periodical_inventory_var.get():
            return
        try:
            interval = float(t.periodical_inventory_interval_var.get())
        except Exception:
            interval = float(t.config.get("periodical_inventory_interval", "5"))
        if (datetime.now() - getattr(t, "last_inventory_screenshot_time", datetime.min)) < timedelta(minutes=max(0.0, interval)):
            return
        self.queue_fishing_action(
            lambda: t.take_inventory_screenshot_now(fishing_safe=True),
            "inventory_screenshot"
        )


    def _set_fishing_busy(self, busy):
        t = self._tracker
        if not t:
            return
        t._fishing_busy = bool(busy)
        t._daily_reward_wake_event.set()

    def _pause_fishing_for_daily_reward(self):
        t = self._tracker
        if not t or not t._daily_reward_pause_requested.is_set():
            return False
        t._fishing_busy = False
        t._daily_reward_fishing_paused.set()
        t._daily_reward_wake_event.set()
        while t._daily_reward_pause_requested.is_set() and t.detection_running and not t._daily_reward_stop_event.is_set():
            time.sleep(0.05)
        t._daily_reward_fishing_paused.clear()
        t._daily_reward_wake_event.set()
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

    def _on_merchant_cache_event(self, name):
        t = self._tracker
        if not t or not getattr(t, "detection_running", False):
            return
        cfg = getattr(t, "config", {})
        if self._is_fishing_mode_enabled():
            if cfg.get("fishing_auto_merchant", False) or cfg.get("merchant_teleporter", False):
                with self._merchant_event_lock:
                    events = self._fishing_runtime_state.setdefault("merchant_event_queue", [])
                    if not isinstance(events, list):
                        events = []
                        self._fishing_runtime_state["merchant_event_queue"] = events
                    events.append(str(name))
                    self._fishing_runtime_state["merchant_event_pending"] = True
                    if not self._fishing_runtime_state.get("merchant_event_active_name"):
                        self._fishing_runtime_state["merchant_event_name"] = str(events[0])
                    self._fishing_runtime_state["merchant_event_pending_name"] = str(events[0])
            return
        if not cfg.get("merchant_teleporter", False):
            return
        t._merchant_log_event_pending_name = str(name)
        lock = getattr(t, "_merchant_log_event_lock", None)
        if lock is None:
            lock = threading.Lock()
            t._merchant_log_event_lock = lock
        with lock:
            if getattr(t, "_merchant_log_event_queued", False):
                t._merchant_log_event_pending = True
                return
            t._merchant_log_event_queued = True
            t._merchant_log_event_pending = False

        def run():
            try:
                while t.detection_running and not t.reconnecting_state:
                    if not (
                        getattr(t, "_br_sc_running", False)
                        or getattr(t, "_mt_running", False)
                        or getattr(t, "_portable_crack_running", False)
                        or getattr(t, "_remote_running", False)
                        or getattr(t, "_fishing_busy", False)
                        or getattr(t, "auto_pop_state", False)
                        or getattr(t, "on_auto_merchant_state", False)
                        or getattr(t, "_egg_collecting", False)
                        or getattr(t, "_eden_running", False)
                        or getattr(t, "_potion_thread_active", False)
                    ):
                        break
                    time.sleep(0.1)
                if not t.detection_running or t.reconnecting_state or not t.config.get("merchant_teleporter", False):
                    return
                t._merchant_log_event_override = True
                try:
                    t.activate_roblox_window()
                except Exception:
                    pass
                t._merchant_teleporter_impl(merchant_name=str(name))
                if getattr(t, "_last_merchant_sequence_ran", False):
                    t.last_mt_time = datetime.now()
            except Exception as e:
                print(f"Merchant log auto-merchant failed: {e}")
            finally:
                t._merchant_log_event_override = False
                with lock:
                    pending = bool(getattr(t, "_merchant_log_event_pending", False))
                    t._merchant_log_event_queued = False
                    t._merchant_log_event_pending = False
                if pending and t.detection_running and not t.reconnecting_state and t.config.get("merchant_teleporter", False):
                    self._on_merchant_cache_event(getattr(t, "_merchant_log_event_pending_name", ""))

        try:
            t._action_scheduler.enqueue_action(run, name="merchant_log_event", priority=0)
        except Exception:
            run()
    def _run_fishing_merchant_sequence(self):
        if not self._tracker: return False
        t = self._tracker
        self._fishing_runtime_state["merchant_requires_reset"] = False
        old_override = getattr(t, "_fishing_br_sc_override", False)
        old_log_override = getattr(t, "_merchant_log_event_override", False)
        t._fishing_br_sc_override = True
        t._merchant_log_event_override = True
        merchant_name = (
            self._fishing_runtime_state.get("merchant_event_active_name")
            or self._fishing_runtime_state.get("merchant_event_name", "")
        )
        ran = False
        try:
            try: t.activate_roblox_window()
            except Exception: pass

            t._last_merchant_sequence_ran = False
            t._last_merchant_sequence_requires_reset = False
            t._last_merchant_sequence_skipped = False

            merchant_fn = getattr(t, "_merchant_teleporter_impl", None)
            if not callable(merchant_fn):
                print("Fishing merchant sequence skipped: _merchant_teleporter_impl unavailable")
                return False

            # reuse the same merchant logic so we get buy, webhook, limbo, everything
            merchant_fn(merchant_name=merchant_name)
            ran = bool(getattr(t, "_last_merchant_sequence_ran", False))
            if getattr(t, "_last_merchant_sequence_skipped", False):
                print(f"Fishing merchant sequence deferred for {merchant_name}: merchant cooldown active")
            self._fishing_runtime_state["merchant_requires_reset"] = bool(
                getattr(t, "_last_merchant_sequence_requires_reset", False)
            )
            if ran:
                t.last_mt_time = datetime.now()
        except Exception as e:
            print(f"Fishing merchant sequence failed: {e}")
        finally:
            t._fishing_br_sc_override = old_override
            t._merchant_log_event_override = old_log_override
        return ran

    def _start_fishing_worker(self) -> None:
        if not self._tracker:
            return
        with self._fishing_lock:
            if self._fishing_thread and self._fishing_thread.is_alive():
                if not self._fishing_stop_event.is_set():
                    return
                if self._fishing_thread is not threading.current_thread():
                    self._fishing_thread.join()
            self._fishing_thread = None
            self._fishing_stop_event.clear()
            stop_event = self._fishing_stop_event

            def _run_fishing():
                self._tracker._fishing_worker_active = True
                try:
                    from biome_tracker.fishing import run_fishing_loop
                    run_fishing_loop(
                        stop_event=stop_event,
                        can_run_cb=self._fishing_can_run,
                        config_provider=self._fishing_config_provider,
                        log_prefix="[FishingMode]",
                        print_start_stop=True,
                        on_failsafe_timeout=self._on_fishing_failsafe_timeout,
                        run_br_sc_sequence_cb=self._run_fishing_br_sc_sequence,
                        run_merchant_sequence_cb=self._run_fishing_merchant_sequence,
                        activate_roblox_cb=self._tracker.activate_roblox_window,
                        runtime_state=self._fishing_runtime_state,
                        set_fishing_busy_cb=self._set_fishing_busy,
                        pause_daily_reward_cb=self._pause_fishing_for_daily_reward,
                        run_fishing_action_cb=self._run_fishing_action_request,
                        on_fishing_event_cb=self._on_fishing_event,
                        merchant_event_lock=self._merchant_event_lock,
                        on_f2_pressed_cb=lambda: (self.set_biome_detection(False), self._emit_shortcut("STOP")),
                        is_failsafe_ignored_cb=lambda: getattr(self._tracker, "_br_sc_running", False) or getattr(self._tracker, "_mt_running", False) or getattr(self._tracker, "auto_pop_state", False) or getattr(self._tracker, "on_auto_merchant_state", False) or getattr(self._tracker, "_egg_collecting", False),
                    )
                except Exception as e:
                    print(f"Fishing worker failed: {e}")
                finally:
                    self._tracker._fishing_worker_active = False
                    self._clear_fishing_actions()
                    self._tracker._daily_reward_wake_event.set()

            self._fishing_thread = threading.Thread(target=_run_fishing, daemon=True)
            self._fishing_thread.start()

    def _stop_fishing_worker(self) -> None:
        self._fishing_stop_event.set()
        t = self._fishing_thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join()
        if not t or not t.is_alive():
            self._fishing_thread = None

    def set_biome_detection(self, enabled):
        if not self._tracker:
            return
        was_running = self._tracker.detection_running
        with self._macro_toggle_lock:
            if enabled:
                if not was_running and self._is_fishing_mode_enabled():
                    self._fishing_runtime_state["initial_start_pending"] = True
                self._stop_fishing_worker()
                if not self._tracker.detection_running:
                    self._tracker.start_detection()
                if self._is_fishing_mode_enabled():
                    self._tracker.stop_potion_crafting()
                    self._start_fishing_worker()
                else:
                    try:
                        self._tracker.start_potion_crafting()
                    except Exception:
                        pass
                if not was_running and self._tracker.detection_running:
                    self.reset_config_baseline()
            else:
                self._fishing_runtime_state["initial_start_pending"] = False
                self._tracker.stop_detection()
                self._stop_fishing_worker()
        self._emit_macro_status()
    # --- frontend event emitters (JS bridge) ---

    def _safe_eval_js(self, js_code):
        if not self._window: return
        try:
            self._window.evaluate_js(js_code)
        except Exception: pass

    def _emit_macro_status(self):
        self._safe_eval_js(f'if(window.onMacroStatus) window.onMacroStatus("{self.get_macro_status()}");')

    def _emit_stats_update(self):
        self._safe_eval_js('if(window.onStatsUpdated) window.onStatsUpdated();')

    def get_stats(self):
        t = self._tracker
        if not t:
            return {}
        r = {"biome_counts": t.biome_counts, "merchant_counts": t.config.get("merchant_counts", {})}
        st = getattr(t, "get_total_session_time", None)
        if callable(st):
            r["session_time"] = st()
        return r

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
            fe = get_frontend_entry()
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

            if fe and "html" in fe:
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
                base = fe["url"] if fe else "http://localhost:5173"
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

    def check_rapidocr_status(self):
        try:
            import rapidocr_onnxruntime
            try:
                from importlib.metadata import version
                ver = version("rapidocr-onnxruntime")
            except Exception:
                ver = "bundled"
            return {"installed": True, "version": ver}
        except Exception:
            return {"installed": False, "version": None}

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
         res = get_frontend_entry()
         return res["url"] if res else "http://localhost:5173"

    def _open_recorder(self, mode: str = "obby"):
         fe = get_frontend_entry()
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
                    time.sleep(2)
                    self._tracker._press_hotkey_via_pynput(keybind)
                 except Exception as e:
                    print(f"Error testing aura keybind: {e}")
             threading.Thread(target=test_record, daemon=True).start()

    def test_biome_keybind(self):
         if self._tracker:
             def test_record():
                 try:
                    keybind = self._tracker.rarest_biome_keybind_var.get()
                    if not keybind: return
                    time.sleep(2)
                    self._tracker._press_hotkey_via_pynput(keybind)
                 except Exception as e:
                    print(f"Error testing biome keybind: {e}")
             threading.Thread(target=test_record, daemon=True).start()

    def align_camera(self):
         if self._tracker:
             self._tracker.align_camera()

    def emit_calibration_result(self, data):
         if self._window:
             js_data = json.dumps(data)
             self._window.evaluate_js(
                 f"if(window.onCalibrationResult) window.onCalibrationResult({js_data});"
                 f"if(window.onCalibrationResultMisc) window.onCalibrationResultMisc({js_data});"
             )

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
                {"key": "fishing_bugged_ui_pos", "label": "Bugged Fishing UI (click when stuck)", "value": cfg.get("fishing_bugged_ui_pos", [1167, 477])},
            ]
            self._calib_mgr.request_display_many(items=items, duration_ms=duration_ms)
            return True
        except Exception:
            return False


def launch_app(api_class, tracker=None):
    tracker = tracker or BiomeTracker()
    tracker.debug_mode = debug_mode
    api = api_class(tracker)
    tracker.on_stats_update = api._emit_stats_update
    tracker.on_biome_update = api._emit_biome_update
    tracker.on_update_available = api._emit_update_available
    tracker.on_update_status = api._emit_update_status
    tracker.on_biome_confirm_request = api._request_biome_confirm
    tracker.on_status_change = lambda status: api._emit_macro_status()
    tracker.on_merchant_cache_event = api._on_merchant_cache_event

    fe = get_frontend_entry()
    win_args = {
        "title": f"Coteab Macro {current_version}",
        "js_api": api,
        "width": 985, "height": 550,
        "min_size": (550, 500),
        "resizable": True, "frameless": False
    }
    if fe and "html" in fe: win_args["html"] = fe["html"]
    else: win_args["url"] = fe["url"] if fe else "http://localhost:5173"

    window = webview.create_window(**win_args)
    api.set_window(window)
    if "--coteab-start-after-restart" in sys.argv:
        threading.Timer(1.0, api.start_from_hotkey).start()

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
                                api.start_from_hotkey()
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

def stop_app(tracker):
    if tracker and getattr(tracker, "detection_running", False): tracker.stop_detection()

def main():
    ensure_workspace_files()

    # ---- Beta whitelist----
    # try:
    #     from biome_tracker.beta_auth import show_auth_popup
    #     if not show_auth_popup():
    #         print("[BetaAuth] Access denied or cancelled. Exiting.")
    #         return 0
    # except Exception as e:
    #     print(f"[BetaAuth] Auth module error: {e}")
    #     traceback.print_exc()

    tracker = None
    api = Api(tracker=None)
    api._setup_emergency_server()
    api._setup_emergency_hotkey()
    try:
        fe = get_frontend_entry()
        win_args = {
            "title": f"Coteab Macro {current_version}",
            "js_api": api,
            "width": 985, "height": 550,
            "min_size": (550, 500),
            "resizable": True, "frameless": False,
        }
        if "html" in fe: win_args["html"] = fe["html"]
        else: win_args["url"] = fe["url"]

        window = webview.create_window(**win_args)
        api._window = window
        def _background_init():
            nonlocal tracker
            try:
                from biome_tracker.core import BiomeTracker
                tracker = BiomeTracker()
                tracker.debug_mode = debug_mode
                canonical = _read_cli_value("--coteab-target", "CoteabMacro.exe")
                old_pid_raw = _read_cli_value("--coteab-old-pid", "")
                try: old_pid = int(old_pid_raw) if old_pid_raw else None
                except Exception: old_pid = None

                if tracker.maybe_self_rename_to_canonical_exe(canonical, old_pid=old_pid):
                    window.destroy()
                    return

                if _cfg_bool(getattr(tracker, "config", {}), "auto_update_enabled", True):
                    if tracker.apply_startup_auto_update():
                        window.destroy()
                        return

                api._tracker = tracker
                if not api.config_dirty:
                    api.reset_config_baseline()
                tracker.on_stats_update = api._emit_stats_update
                tracker.on_biome_update = api._emit_biome_update
                tracker.on_update_available = api._emit_update_available
                tracker.on_update_status = api._emit_update_status
                tracker.on_biome_confirm_request = api._request_biome_confirm
                tracker.on_status_change = lambda status: api._emit_macro_status()
                tracker.on_merchant_cache_event = api._on_merchant_cache_event
                tracker.on_remote_start = lambda: api.set_biome_detection(True)
                tracker.on_remote_stop = lambda: api.set_biome_detection(False)
                tracker._fishing_api = api
                api.set_window(window)
                if "--coteab-start-after-restart" in sys.argv:
                    threading.Timer(1.0, api.start_from_hotkey).start()

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
                    if f1_now and not f1_was and api._tracker and not api._tracker.detection_running:
                        try:
                            api.start_from_hotkey()
                        except Exception as e:
                            print(f"[Hotkey] Start failed: {e}")
                    if f2_now and not f2_was and api._tracker and api._tracker.detection_running:
                        try:
                            api.set_biome_detection(False)
                            api._emit_shortcut("STOP")
                        except Exception as e:
                            print(f"[Hotkey] Stop failed: {e}")
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
