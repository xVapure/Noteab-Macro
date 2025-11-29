import traceback
import pygetwindow as gw
from tkinter import messagebox, filedialog, simpledialog
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime, timedelta, timezone
import ttkbootstrap as ttk
import logging
import shutil, glob
import atexit
import difflib
import json, requests, time, os, threading, re, webbrowser, random, keyboard, pyautogui, pytesseract, autoit, psutil, \
    locale, win32gui, win32process, win32con, ctypes, queue, mouse, sys

def apply_fast_flags(version=None, force=False):
    config_paths = [
        "config.json",
        "source_code/config.json",
        os.path.join(os.path.dirname(__file__), "config.json"),
        os.path.join(os.path.dirname(__file__), "source_code/config.json")
    ]
    config = {}
    config_path = None
    for p in config_paths:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as cf:
                    config = json.load(cf)
                config_path = p
                break
            except Exception:
                config = {}
                config_path = p
                break

    if config_path is None:
        config_path = "config.json"
        config = {}

    applied_versions = set(config.get("fastflags_applied_versions", []))

    versions_directory = os.path.expandvars(r"%localappdata%\Roblox\Versions")
    if not os.path.exists(versions_directory):
        logging.error("Roblox Versions directory not found: %s", versions_directory)
        print(f"Roblox versions directory not found: {versions_directory}")
        return

    version_folders = [d for d in os.listdir(versions_directory)
                       if os.path.isdir(os.path.join(versions_directory, d)) and d.lower().startswith("version-")]
    version_folders.sort()

    if not version_folders:
        logging.error("No valid Roblox version folders found in %s", versions_directory)
        print(f"No Roblox versions found in {versions_directory}")
        return

    target_folders = []
    if version:
        if version in version_folders or os.path.isdir(os.path.join(versions_directory, version)):
            target_folders = [version]
        else:
            target_folders = version_folders[:]
    else:
        target_folders = version_folders[:]
    if not force:
        to_apply = [ver for ver in target_folders if ver not in applied_versions]
    else:
        to_apply = target_folders[:]

    if not to_apply:
        print("FastFlags: nothing to do — all target versions already patched (per config).")
        return

    flags = {
        "DFFlagDebugPerfMode": "True",
        "FFlagHandleAltEnterFullscreenManually": "False",
        "FStringDebugLuaLogPattern": "ExpChat/mountClientApp",
        "FStringDebugLuaLogLevel": "trace"
    }

    keep_backups = 5
    success_count = 0
    failures = []

    for ver in to_apply:
        clientsettings_directory = os.path.join(versions_directory, ver, "ClientSettings")
        try:
            os.makedirs(clientsettings_directory, exist_ok=True)
        except Exception as e:
            logging.exception("Failed to create ClientSettings directory %s: %s", clientsettings_directory, e)
            failures.append(ver)
            continue

        settings_path = os.path.join(clientsettings_directory, "ClientAppSettings.json")
        ts = datetime.now().strftime("%Y%m%d%H%M%S")

        try:
            if os.path.exists(settings_path):
                try:
                    backup_name = settings_path + ".bak." + ts
                    shutil.copy2(settings_path, backup_name)
                    backups = sorted(glob.glob(settings_path + ".bak.*"), key=os.path.getmtime, reverse=True)
                    for old in backups[keep_backups:]:
                        try:
                            os.remove(old)
                        except Exception:
                            pass
                except Exception as e:
                    logging.exception("Failed to create/rotate backup for %s: %s", settings_path, e)

            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except json.JSONDecodeError:
                try:
                    corrupt_name = settings_path + ".corrupt." + ts
                    shutil.copy2(settings_path, corrupt_name)
                except Exception:
                    pass
                existing_data = {}
            except FileNotFoundError:
                existing_data = {}
            except Exception as e:
                logging.exception("Error reading %s: %s", settings_path, e)
                failures.append(ver)
                continue
            existing_data.update(flags)

            tmp_path = settings_path + ".tmp." + ts
            try:
                with open(tmp_path, "w", encoding="utf-8") as tf:
                    json.dump(existing_data, tf, indent=4)
                    tf.write("\n")
                os.replace(tmp_path, settings_path)
            finally:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

            success_count += 1
            applied_versions.add(ver)

        except Exception as e:
            logging.exception("Failed to apply FastFlags to %s: %s", ver, e)
            failures.append(ver)
    try:
        config["fastflags_applied_versions"] = sorted(list(applied_versions))
        config["fastflags_last_applied"] = datetime.now().isoformat()
        tmp_cfg = config_path + ".tmp"
        with open(tmp_cfg, "w", encoding="utf-8") as tf:
            json.dump(config, tf, indent=4)
            tf.write("\n")
        os.replace(tmp_cfg, config_path)
    except Exception as e:
        logging.exception("Failed to save config.json with fastflags_applied_versions: %s", e)
        print("Warning: failed to persist fastflags_applied_versions to config file:", e)

    print(f"Applied FastFlags to {success_count} of {len(to_apply)} targeted Roblox version(s).")
    if failures:
        print("Failed to patch:", ", ".join(failures))
        logging.error("Failed to patch versions: %s", failures)

    if success_count > 0:
        try:
            restart_approve = messagebox.askyesno(
                "Restart?",
                f"FastFlags have been applied to {success_count} Roblox version(s).\nRoblox needs to restart for these changes to apply. Without these FFlags merchant detections log based & Eden detection won't work 😔\nRestart now?"
            )
            if restart_approve:
                try:
                    for p in psutil.process_iter(['name']):
                        try:
                            if p.info.get('name') == 'RobloxPlayerBeta.exe':
                                p.kill()
                        except Exception:
                            pass
                except Exception as e:
                    logging.exception("Error terminating Roblox processes: %s", e)
                latest = version_folders[-1] if version_folders else None
                if latest:
                    exe_path = os.path.join(versions_directory, latest, "RobloxPlayerBeta.exe")
                    try:
                        if os.path.exists(exe_path):
                            os.startfile(exe_path)
                    except Exception as e:
                        logging.exception("Failed to restart Roblox player: %s", e)
                messagebox.showinfo(
                    "Patched",
                    "Patched Roblox ClientAppSettings.json files. Roblox should have restarted. If it didn't, please restart Roblox manually."
                )
            else:
                messagebox.showwarning(
                    "Reminder",
                    "Roblox will need to restart to apply the new flags. Please restart Roblox and the macro as soon as convenient."
                )
        except Exception as e:
            logging.exception("Error prompting restart: %s", e)


class SnippingWidget:
    def __init__(self, root, config_key=None, callback=None):
        self.root = root
        self.config_key = config_key
        self.callback = callback
        self.snipping_window = None
        self.begin_x = None
        self.begin_y = None
        self.end_x = None
        self.end_y = None

    def start(self):
        self.snipping_window = ttk.Toplevel(self.root)
        self.snipping_window.attributes('-fullscreen', True)
        self.snipping_window.attributes('-alpha', 0.3)
        self.snipping_window.configure(bg="lightblue")

        self.snipping_window.bind("<Button-1>", self.on_mouse_press)
        self.snipping_window.bind("<B1-Motion>", self.on_mouse_drag)
        self.snipping_window.bind("<ButtonRelease-1>", self.on_mouse_release)

        self.canvas = ttk.Canvas(self.snipping_window, bg="lightblue", highlightthickness=0)
        self.canvas.pack(fill=ttk.BOTH, expand=True)

    # hi im tea (ffffffffff)

    def on_mouse_press(self, event):
        self.begin_x = event.x
        self.begin_y = event.y
        self.canvas.delete("selection_rect")

    def on_mouse_drag(self, event):
        self.end_x, self.end_y = event.x, event.y
        self.canvas.delete("selection_rect")
        self.canvas.create_rectangle(self.begin_x, self.begin_y, self.end_x, self.end_y,
                                     outline="white", width=2, tag="selection_rect")

    def on_mouse_release(self, event):
        self.end_x = event.x
        self.end_y = event.y

        x1, y1 = min(self.begin_x, self.end_x), min(self.begin_y, self.end_y)
        x2, y2 = max(self.begin_x, self.end_x), max(self.begin_y, self.end_y)

        self.capture_region(x1, y1, x2, y2)
        self.snipping_window.destroy()

    def capture_region(self, x1, y1, x2, y2):
        if self.config_key:
            region = [x1, y1, x2 - x1, y2 - y1]
            print(f"Region for '{self.config_key}' set to {region}")

            if self.callback:
                self.callback(region)
import itertools

class ActionScheduler:
    def __init__(self, owner, worker_name="ActionScheduler"):
        self.owner = owner
        self._pq = queue.PriorityQueue()
        self._counter = itertools.count()
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, name=worker_name, daemon=True)
        self._worker_thread.start()
        self._action_lock = threading.RLock()

    def enqueue_action(self, fn, name=None, priority=5, block=False, timeout=None):
        idx = next(self._counter)
        qname = name or f"action-{idx}"
        self._pq.put((priority, idx, qname, fn))
        if block:
            start = time.time()
            while True:
                with self._action_lock:
                    pass
                if timeout is not None and (time.time() - start) > timeout:
                    break
                time.sleep(0.08)
            return True
        return True

    def _worker(self):
        while self._running:
            try:
                priority, idx, name, fn = self._pq.get(timeout=0.7)
            except Exception:
                continue
            try:
                acquired = False
                try:
                    self._action_lock.acquire()
                    acquired = True
                except Exception:
                    acquired = False
                try:
                    try:
                        fn()
                    except Exception:
                        try:
                            self.owner.error_logging(sys.exc_info(), f"Error executing scheduled action {name}")
                        except Exception:
                            pass
                finally:
                    if acquired:
                        try:
                            self._action_lock.release()
                        except Exception:
                            pass
            except Exception:
                pass

    def stop(self):
        self._running = False
        try:
            while not self._pq.empty():
                self._pq.get_nowait()
        except Exception:
            pass

class BiomePresence():
    def __init__(self):
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, '')

        self.logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox', 'logs')
        self.config = self.load_config()
        self.config["enable_auto_craft"] = False
        raw_webhook = self.config.get("webhook_url", "")
        if isinstance(raw_webhook, list):
            self.webhook_urls = [u for u in raw_webhook if isinstance(u, str) and u.strip()]
        elif isinstance(raw_webhook, str):
            rw = raw_webhook.strip()
            if rw.startswith("[") and rw.endswith("]"):
                try:
                    parsed = json.loads(rw)
                    if isinstance(parsed, list):
                        self.webhook_urls = [u for u in parsed if isinstance(u, str) and u.strip()]
                    else:
                        self.webhook_urls = [rw] if rw else []
                except Exception:
                    self.webhook_urls = [rw] if rw else []
            else:
                self.webhook_urls = [rw] if rw else []
        else:
            self.webhook_urls = []
        self.auras_data = self.load_auras_json()
        self.biome_data = self.load_biome_data()

        self.current_biome = None
        self.last_sent = {biome: datetime.min for biome in self.biome_data}

        self.biome_counts = self.config.get("biome_counts", {})
        for biome in self.biome_data.keys():
            if biome not in self.biome_counts:
                self.biome_counts[biome] = 0

        self.start_time = None
        self.saved_session = self.parse_session_time(self.config.get("session_time", "0:00:00"))
        self._session_window_reset_performed = False
        self.current_session = 0
        self.session_window_start = None
        session_window_str = self.config.get("session_window_start", "")
        if session_window_str:
            try:
                self.session_window_start = datetime.fromisoformat(session_window_str)
            except Exception:
                self.session_window_start = None
        self.has_started_once = False
        self.stop_sent = False

        self.last_position = 0
        self.detection_running = False
        self._stop_player_logger_thread()
        self.detection_thread = None
        self.lock = threading.Lock()
        self.logs = self.load_logs()
        self.player_log_queue = queue.Queue()
        self.player_log_send_delay = float(self.config.get("player_log_send_delay", 2.0))
        self.biome_history = []
        self.player_log_sender_running = False

        # item use
        self.last_br_time = datetime.min
        self.last_sc_time = datetime.min
        self.last_mt_time = datetime.min
        self.on_auto_merchant_state = False
        self._merchant_pending_from_logs = False
        self._merchant_pending_name = None
        self._br_sc_running = False
        self._cancel_next_actions_until = datetime.min
        self._merchant_condition = threading.Condition()
        self._remote_running = False
        self._mt_running = getattr(self, "_mt_running", False)
        self.auto_pop_state = getattr(self, "auto_pop_state", False)
        self._action_scheduler = ActionScheduler(self)
        # Buff variables
        self.auto_pop_state = False
        self.buff_vars = {}
        self.buff_amount_vars = {}

        # Reconnect state
        self.reconnecting_state = False
        self.timer_paused_by_disconnect = False
        self.register_shutdown_handler()
        screenshot_dir = os.path.join(os.getcwd(), "images")
        try:
            if os.path.exists(screenshot_dir):
                for fname in os.listdir(screenshot_dir):
                    if fname.startswith(("merchant_", "aura_", "inventory_", "quest", "remote_")):
                        try:
                            os.remove(os.path.join(screenshot_dir, fname))
                        except Exception:
                            pass
        except Exception as e:
            try:
                self.error_logging(e, "Error deleting merchant images on startup")
            except Exception:
                pass

        # start gui
        self.variables = {}
        apply_fast_flags()
        self.init_gui()
        try:
            keyboard.add_hotkey('f1', lambda: self.start_detection() if not self.detection_running else None)
            keyboard.add_hotkey('f3', lambda: self.stop_detection() if self.detection_running else None)
        except Exception:
             pass

        # aura detection:
        self.last_aura_found = None
        self.last_aura_screenshot_time = datetime.min

        # notice tab
        self.notice_data = self.load_notice_tab()

    def load_logs(self):
        if os.path.exists('macro_logs.txt'):
            with open('macro_logs.txt', 'r') as file:
                lines = file.read().splitlines()
                return lines
        return []

    def load_biome_data(self):
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/biomes_data.json"
        eventUrl = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/main/active_events.json"

        default_biome_data = {
            "NORMAL": {
                "color": "0xffffff",
                "thumbnail_url": "fuck is this for??"
            },
            "WINDY": {
                "color": "0x9ae5ff",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/WINDY.png"
            },
            "RAINY": {
                "color": "0x027cbd",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/RAINY.png"
            },
            "SNOWY": {
                "color": "0xDceff9",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SNOWY.png"
            },
            "SAND STORM": {
                "color": "0x8F7057",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SAND%20STORM.png"
            },
            "HELL": {
                "color": "0xff4719",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/HELL.png"
            },
            "STARFALL": {
                "color": "0x011ab7",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/STARFALL.png"
            },
            "CORRUPTION": {
                "color": "0x6d32a8",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/CORRUPTION.png"
            },
            "NULL": {
                "color": "0x838383",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/NULL.png"
            },
            "GLITCHED": {
                "color": "0xbfff00",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/GLITCHED.png"
            },
            "DREAMSPACE": {
                "color": "0xea9dda",
                "thumbnail_url": "https://maxstellar.github.io/biome_thumb/DREAMSPACE.png"
            },
            "CYBERSPACE": {
                "color": "0x0A1A3D",
                "thumbnail_url": "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/images/CYBERSPACE.png"
            }
        }

        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict) or not data:
                data = default_biome_data
        except Exception as e:
            print(f"Error loading biomes_data.json from {url}: {e}")
            self.error_logging(e, f"Error loading biomes_data.json from {url}")
            data = default_biome_data

        try:
            r_events = requests.get(eventUrl, timeout=10)
            r_events.raise_for_status()
            events = r_events.json()
        except Exception as e:
            print(f"Error loading {eventUrl}: {e}")
            self.error_logging(e, f"Error loading active_events.json from {eventUrl}")
            events = {"april_fools": False}

        if events.get("april_fools"):
            glitched = data.get("GLITCHED", {})
            for biome in data:
                data[biome]["color"] = glitched.get("color", data[biome]["color"])
                data[biome]["thumbnail_url"] = glitched.get("thumbnail_url", data[biome]["thumbnail_url"])

        custom_overrides = self.config.get("custom_biome_overrides", {})
        if isinstance(custom_overrides, dict):
            for biome_name, overrides in custom_overrides.items():
                try:
                    if biome_name in data and isinstance(overrides, dict):
                        if "color" in overrides and overrides["color"]:
                            data[biome_name]["color"] = overrides["color"]
                        if "thumbnail_url" in overrides and overrides["thumbnail_url"]:
                            data[biome_name]["thumbnail_url"] = overrides["thumbnail_url"]
                except Exception:
                    pass

        return data

    def load_notice_tab(self):
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/noticetabcontents.txt"
        data = ""
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.text
        except Exception as e:
            print(f"Error loading noticetabcontents.txt from {url}: {e}")
            self.error_logging(e, f"Error loading noticetabcontents.txt from {url}")

        return data

    def error_logging(self, exception, custom_message=None, max_log_size=3 * 1024 * 1024):
        log_file = "error_logs.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_type = type(exception).__name__
        error_message = str(exception)
        stack_trace = traceback.format_exc()

        if not os.path.exists(log_file):
            with open(log_file, "w") as log:
                log.write("Error Log File Created\n")
                log.write("-" * 40 + "\n")

        if os.path.exists(log_file) and os.path.getsize(log_file) > max_log_size:
            with open(log_file, "r") as log:
                lines = log.readlines()
            with open(log_file, "w") as log:
                log.writelines(lines[-1000:])

        with open(log_file, "a") as log:
            log.write(f"\n[{timestamp}] ERROR LOG\n")
            log.write(f"Error Type: {error_type}\n")
            log.write(f"Error Message: {error_message}\n")
            if custom_message:
                log.write(f"Custom Message: {custom_message}\n")
            log.write(f"Traceback:\n{stack_trace}\n")
            log.write("-" * 40 + "\n")

        print(f"Error logged to {log_file}.")

    def set_title_threadsafe(self, title_text):
        try:
            if threading.current_thread() is threading.main_thread():
                self.root.title(title_text)
            else:
                self.root.after(0, lambda: self.root.title(title_text))
        except Exception as e:
            self.error_logging(e, "Error in set_title_threadsafe")

    def _on_exit_handler(self):
        try:
            self.detection_running = False
            self.player_log_sender_running = False
            self.player_logger_running = False
            try:
                if hasattr(self, "player_log_queue") and self.player_log_queue:
                    self.player_log_queue.put(None)
            except Exception:
                pass
            if getattr(self, 'has_started_once', False):
                if self.start_time:
                    now = datetime.now()
                    elapsed = int((now - self.start_time).total_seconds())
                    self.saved_session += elapsed
                    self.start_time = None
                self.save_config()
        except Exception:
            pass

    def save_logs(self):
        log_file_path = 'macro_logs.txt'

        if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 2 * 1024 * 1024:
            with open(log_file_path, 'w') as file:
                file.write("")
        else:
            with open(log_file_path, 'a') as file:
                for log in self.logs:
                    file.write(log + "\n")

    def save_config(self):
        try:
            with open("config.json", "r") as file:
                config = json.load(file)
        except FileNotFoundError:
            config = {}
        auto_buff_glitched = config.get("auto_buff_glitched", self.config.get("auto_buff_glitched", {}))
        session_time = self.get_total_session_time()
        if hasattr(self, "webhook_urls") and self.webhook_urls:
            webhook_save_val = self.webhook_urls
        else:
            webhook_save_val = self.config.get("webhook_url", "")
        macro_last_start_val = self.config.get("macro_last_start", "")
        if self.start_time:
            macro_last_start_val = self.start_time.isoformat()
        session_window_start_val = self.session_window_start.isoformat() if self.session_window_start else self.config.get(
            "session_window_start", "")
        config.update({
            "webhook_url": webhook_save_val,
            "private_server_link": self.private_server_link_entry.get(),
            "auto_reconnect": self.auto_reconnect_var.get(),
            "biome_notifier": {biome: self.variables[biome].get() for biome in self.biome_data},
            "biome_counts": self.biome_counts,
            "session_time": session_time,
            "session_window_start": session_window_start_val,
            "macro_last_start": macro_last_start_val,
            "biome_randomizer": self.br_var.get(),
            "br_duration": self.br_duration_var.get(),
            "strange_controller": self.sc_var.get(),
            "sc_duration": self.sc_duration_var.get(),
            "auto_pop_glitched": self.auto_pop_glitched_var.get(),
            "enable_buff_glitched": self.enable_buff_glitched_var.get() if hasattr(self, "enable_buff_glitched_var") else self.config.get("enable_buff_glitched", False),
            "glitched_menu_button": self.config.get("glitched_menu_button", [0, 0]),
            "glitched_settings_button": self.config.get("glitched_settings_button", [0, 0]),
            "glitched_buff_enable_button": self.config.get("glitched_buff_enable_button", [0, 0]),
            "auto_buff_glitched": {
                buff: (self.buff_vars[buff].get(), int(self.buff_amount_vars[buff].get()))
                for buff in self.buff_vars
            },
            "selected_theme": self.root.style.theme.name,
            "dont_ask_for_update": self.config.get("dont_ask_for_update", False),
            "merchant_teleporter": self.mt_var.get(),
            "auto_merchant_in_limbo": self.auto_merchant_in_limbo_var.get(),
            "mt_duration": self.mt_duration_var.get(),
            "merchant_extra_slot": self.merchant_extra_slot_var.get(),
            "Mari_Items": self.config.get("Mari_Items", {}),
            "Jester_Items": self.config.get("Jester_Items", {}),
            "ping_mari": self.ping_mari_var.get(),
            "mari_user_id": self.mari_user_id_var.get(),
            "ping_jester": self.ping_jester_var.get(),
            "jester_user_id": self.jester_user_id_var.get(),
            "merchant_open_button": self.config.get("merchant_open_button", [579, 906]),
            "merchant_dialogue_box": self.config.get("merchant_dialogue_box", [1114, 796]),
            "purchase_amount_button": self.config.get("purchase_amount_button", [700, 584]),
            "purchase_button": self.config.get("purchase_button", [739, 635]),
            "first_item_slot_pos": self.config.get("first_item_slot_pos", [571, 704]),
            "merchant_name_ocr_pos": self.config.get("merchant_name_ocr_pos", [746, 680, 103, 32]),
            "item_name_ocr_pos": self.config.get("item_name_ocr_pos", [728, 731, 218, 24]),
            "enable_aura_detection": self.enable_aura_detection_var.get(),
            "ping_minimum": self.ping_minimum_var.get(),
            "aura_user_id": self.aura_user_id_var.get(),
            "enable_aura_record": self.enable_aura_record_var.get(),
            "aura_record_keybind": self.aura_record_keybind_var.get(),
            "aura_record_minimum": self.aura_record_minimum_var.get(),
            "inventory_menu": self.config.get("inventory_menu", [36, 535]),
            "items_tab": self.config.get("items_tab", [1272, 329]),
            "search_bar": self.config.get("search_bar", [855, 358]),
            "first_item_slot": self.config.get("first_item_slot", [839, 434]),
            "amount_box": self.config.get("amount_box", [594, 570]),
            "use_button": self.config.get("use_button", [710, 573]),
            "inventory_close_button": self.config.get("inventory_close_button", [1418, 298]),
            "reconnect_start_button": self.config.get("reconnect_start_button", [954, 876]),
            "inventory_click_delay": self.click_delay_var.get(),
            "record_rare_biome": self.record_rarest_biome_var.get(),
            "rare_biome_record_keybind": self.rarest_biome_keybind_var.get(),
            "detect_merchant_no_mt": self.detect_merchant_no_mt_var.get(),
            "player_logger": self.player_logger_var.get(),
            "first_item_slot_ocr_pos": self.config.get("first_item_slot_ocr_pos", [0, 0, 80, 80]),
            "enable_ocr_failsafe": self.enable_ocr_failsafe_var.get(),
            "anti_afk": self.anti_afk_var.get(),
            "aura_menu": self.config.get("aura_menu", [1200, 500]),
            "periodical_aura_screenshot": self.periodical_aura_var.get() if hasattr(self, "periodical_aura_var") else self.config.get("periodical_aura_screenshot", False),
            "periodical_aura_interval": self.periodical_aura_interval_var.get() if hasattr(self, "periodical_aura_interval_var") else self.config.get("periodical_aura_interval", "5"),
            "periodical_inventory_screenshot": self.periodical_inventory_var.get() if hasattr(self, "periodical_inventory_var") else self.config.get("periodical_inventory_screenshot", False),
            "periodical_inventory_interval": self.periodical_inventory_interval_var.get() if hasattr(self, "periodical_inventory_interval_var") else self.config.get("periodical_inventory_interval", "5"),
            "aura_detection_screenshot": self.aura_screenshot_var.get(),
            "auto_claim_daily_quests": self.auto_claim_quests_var.get() if hasattr(self, "auto_claim_quests_var") else self.config.get("auto_claim_daily_quests", False),
            "auto_claim_interval": self.auto_claim_interval_var.get() if hasattr(self, "auto_claim_interval_var") else self.config.get("auto_claim_interval", "30"),
            "quest_menu": self.config.get("quest_menu", self.config.get("quest_menu", [0, 0])),
            "quest1_button": self.config.get("quest1_button", self.config.get("quest1_button", [0, 0])),
            "quest2_button": self.config.get("quest2_button", self.config.get("quest2_button", [0, 0])),
            "quest3_button": self.config.get("quest3_button", self.config.get("quest3_button", [0, 0])),
            "claim_quest_button": self.config.get("claim_quest_button", self.config.get("claim_quest_button", [0, 0])),
            "quest_reroll_button": self.config.get("quest_reroll_button", self.config.get("quest_reroll_button", [0, 0])),
            "enable_potion_crafting": self.enable_potion_crafting_var.get(),
            "potion_button1": [self.potion_button1_x.get(), self.potion_button1_y.get()],
            "potion_search_bar1": [self.potion_search_x.get(), self.potion_search_y.get()],
            "potion_button2": [self.potion_button2_x.get(), self.potion_button2_y.get()],
            "potion_last_file": self.config.get("potion_last_file", ""),
            "enable_potion_crafting": self.enable_potion_crafting_var.get(),
            "potion_button1": [self.potion_button1_x.get(), self.potion_button1_y.get()],
            "potion_search_bar1": [self.potion_search_x.get(), self.potion_search_y.get()],
            "potion_button2": [self.potion_button2_x.get(), self.potion_button2_y.get()],
            "potion_last_file": self.config.get("potion_last_file", ""),
            "enable_potion_switching": self.enable_potion_switching_var.get() if hasattr(self, "enable_potion_switching_var") else self.config.get("enable_potion_switching", False),
            "potion_switch_interval": self.potion_switch_interval_var.get() if hasattr(self, "potion_switch_interval_var") else self.config.get("potion_switch_interval", "60"),
            "potion_file2": self.potion2_var.get() if hasattr(self, "potion2_var") else self.config.get("potion_file2", ""),
            "potion_file3": self.potion3_var.get() if hasattr(self, "potion3_var") else self.config.get("potion_file3", ""),
            "remote_access_enabled": self.remote_access_var.get() if hasattr(self, "remote_access_var") else self.config.get("remote_access_enabled", False),
            "remote_bot_token": self.remote_bot_token_var.get() if hasattr(self, "remote_bot_token_var") else self.config.get("remote_bot_token", ""),
            "remote_allowed_user_id": self.remote_allowed_user_id_var.get() if hasattr(self, "remote_allowed_user_id_var") else self.config.get("remote_allowed_user_id", ""),
        })

        if not config["auto_buff_glitched"]:
            config["auto_buff_glitched"] = auto_buff_glitched
        with open("config.json", "w") as file:
            json.dump(config, file, indent=4)
        self.config = config

    def is_roblox_focused(self):
        try:
            w = gw.getActiveWindow()
            if not w:
                return False
            title = (w.title or "").lower()
            return "roblox" in title
        except Exception:
            return False

    def load_config(self):
        try:
            config_paths = [
                "config.json",
                "source_code/config.json",
                os.path.join(os.path.dirname(__file__), "config.json"),
                os.path.join(os.path.dirname(__file__), "source_code/config.json")
            ]

            for path in config_paths:
                if os.path.exists(path):
                    with open(path, "r") as file:
                        config = json.load(file)
                        return config

            return {"biome_counts": {biome: 0 for biome in self.biome_data}, "session_time": "0:00:00"}

        except Exception as e:
            self.error_logging(e,
                               "Error at loading config.json. Try adding empty: '{}' into config.json to fix this error!")

    def import_config(self):
        try:
            file_path = filedialog.askopenfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                title="Select CONFIG.JSON please!"
            )

            if not file_path: return
            with open(file_path, "r") as file:
                config = json.load(file)
            self.config = config

            # da webhook
            raw = config.get("webhook_url", "")
            if isinstance(raw, list):
                self.webhook_urls = [u for u in raw if u]
                entry_val = raw[0] if len(raw) == 1 else f"{len(raw)} webhooks configured"
            else:
                self.webhook_urls = [raw] if raw else []
                entry_val = raw
            if hasattr(self, "webhook_display_label"):
                self.webhook_display_label.config(text=entry_val)

            self.private_server_link_entry.delete(0, 'end')
            self.private_server_link_entry.insert(0, config.get("private_server_link", ""))

            # misc
            self.auto_pop_glitched_var.set(config.get("auto_pop_glitched", False))
            self.record_rarest_biome_var.set(config.get("record_rare_biome", False))
            self.rarest_biome_keybind_var.set(config.get("rare_biome_record_keybind", "shift + F8"))
            self.br_var.set(config.get("biome_randomizer", False))
            self.br_duration_var.set(config.get("br_duration", "30"))
            self.sc_var.set(config.get("strange_controller", False))
            self.sc_duration_var.set(config.get("sc_duration", "15"))
            self.mt_var.set(config.get("merchant_teleporter", False))
            self.mt_duration_var.set(config.get("mt_duration", "1"))
            if hasattr(self, "auto_merchant_in_limbo_var"):
                self.auto_merchant_in_limbo_var.set(config.get("auto_merchant_in_limbo", False))
            self.auto_reconnect_var.set(config.get("auto_reconnect", False))
            self.player_logger_var.set(config.get("player_logger", True))
            self.anti_afk_var.set(config.get("anti_afk", True))
            self.click_delay_var.set(config.get("inventory_click_delay", "0"))
            auto_buff_glitched = config.get("auto_buff_glitched", {})
            for buff, (enabled, amount) in auto_buff_glitched.items():
                if buff in self.buff_vars:
                    self.buff_vars[buff].set(enabled)
                    self.buff_amount_vars[buff].set(amount)
            # aura
            self.enable_aura_detection_var.set(config.get("enable_aura_detection", False))
            self.aura_user_id_var.set(config.get("aura_user_id", ""))
            self.ping_minimum_var.set(config.get("ping_minimum", "100000"))
            self.enable_aura_record_var.set(config.get("enable_aura_record", False))
            self.aura_record_keybind_var.set(config.get("aura_record_keybind", "shift + F8"))
            if hasattr(self, "periodical_aura_var"): self.periodical_aura_var.set(config.get("periodical_aura_screenshot", False))
            if hasattr(self, "aura_screenshot_var"): self.aura_screenshot_var.set(config.get("aura_detection_screenshot", False))
            if hasattr(self, "periodical_aura_interval_var"): self.periodical_aura_interval_var.set(str(config.get("periodical_aura_interval", "5")))
            if hasattr(self, "periodical_inventory_var"): self.periodical_inventory_var.set(config.get("periodical_inventory_screenshot", False))
            if hasattr(self, "periodical_inventory_interval_var"): self.periodical_inventory_interval_var.set(str(config.get("periodical_inventory_interval", "5")))
            if hasattr(self, "auto_claim_quests_var"): self.auto_claim_quests_var.set(config.get("auto_claim_daily_quests", False))
            if hasattr(self, "auto_claim_interval_var"): self.auto_claim_interval_var.set(str(config.get("auto_claim_interval", "30")))
            # merchant
            self.merchant_extra_slot_var.set(config.get("merchant_extra_slot", "0"))
            self.ping_mari_var.set(config.get("ping_mari", False))
            self.mari_user_id_var.set(config.get("mari_user_id", ""))
            self.ping_jester_var.set(config.get("ping_jester", False))
            self.jester_user_id_var.set(config.get("jester_user_id", ""))
            self.detect_merchant_no_mt_var.set(config.get("detect_merchant_no_mt", True))
            try:
                if "potion_button1" in config:
                    b1 = config.get("potion_button1", [0, 0])
                    if hasattr(self, "potion_button1_x"): self.potion_button1_x.set(b1[0])
                    if hasattr(self, "potion_button1_y"): self.potion_button1_y.set(b1[1])
                if "potion_search_bar1" in config:
                    s = config.get("potion_search_bar1", [0, 0])
                    if hasattr(self, "potion_search_x"): self.potion_search_x.set(s[0])
                    if hasattr(self, "potion_search_y"): self.potion_search_y.set(s[1])
                if "potion_button2" in config:
                    b2 = config.get("potion_button2", [0, 0])
                    if hasattr(self, "potion_button2_x"): self.potion_button2_x.set(b2[0])
                    if hasattr(self, "potion_button2_y"): self.potion_button2_y.set(b2[1])
                if "potion_last_file" in config:
                    if hasattr(self, "potion_file_var"):
                        self.potion_file_var.set(config.get("potion_last_file", ""))
                try:
                    self._refresh_potion_files("crafting_files_do_not_open")
                except Exception:
                    pass
            except Exception:
                pass
                if "potion_file2" in config:
                    if hasattr(self, "potion2_var"): self.potion2_var.set(config.get("potion_file2", ""))
                if "potion_file3" in config:
                    if hasattr(self, "potion3_var"): self.potion3_var.set(config.get("potion_file3", ""))
                if "enable_potion_switching" in config:
                    if hasattr(self, "enable_potion_switching_var"): self.enable_potion_switching_var.set(config.get("enable_potion_switching", False))
                if "potion_switch_interval" in config:
                    if hasattr(self, "potion_switch_interval_var"): self.potion_switch_interval_var.set(str(config.get("potion_switch_interval", "60")))
            # biome count
            self.biome_counts = config.get("biome_counts", {biome: 0 for biome in self.biome_data})
            for biome, count in self.biome_counts.items():
                if biome in self.stats_labels:
                    self.stats_labels[biome].config(text=f"{biome}: {count}")

            total_biomes = sum(self.biome_counts.values())
            self.total_biomes_label.config(text=f"Total Biomes Found: {total_biomes}")

            session_time = config.get("session_time")
            self.session_label.config(text=f"Running Session: {session_time}")
            self.save_config()
            messagebox.askokcancel("Ok imported!!", "Your selected config.json imported and saved successfully!")
        except Exception as e:
            self.error_logging(e, "Error at importing config.json")

    def init_gui(self):
        selected_theme = self.config.get("selected_theme", "solar")
        abslt_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(abslt_path, "NoteabBiomeTracker.ico")

        self.root = ttk.Window(themename=selected_theme)
        self.set_title_threadsafe("Coteab Macro v2.0.1 (Idle)")
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)
        try:
            self.root.iconbitmap(icon_path)
        except Exception:
            pass

        self.variables = {
            biome: ttk.StringVar(master=self.root, value=self.config.get("biome_notifier", {}).get(biome, "Message"))
            for biome in self.biome_data
        }

        header = ttk.Frame(self.root)
        header.pack(side="top", fill="x", padx=10, pady=8)

        header_left = ttk.Frame(header)
        header_left.pack(side="left", anchor="w")

        def _start_wrapper():
            try:
                self.start_detection()
            finally:
                try:
                    self.status_label.config(text="Status: Running")
                except Exception:
                    pass
            try:
                self.start_potion_crafting()
            except Exception:
                pass

        def _stop_wrapper():
            try:
                self.stop_detection()
            finally:
                try:
                    self.status_label.config(text="Status: Idle")
                except Exception:
                    pass

        start_btn = ttk.Button(header_left, text="Start (F1)", command=_start_wrapper, bootstyle="success")
        stop_btn = ttk.Button(header_left, text="Stop (F2)", command=_stop_wrapper, bootstyle="danger")
        start_btn.pack(side="left", padx=(0, 6))
        stop_btn.pack(side="left", padx=(0, 6))

        header_center = ttk.Frame(header)
        header_center.pack(side="left", expand=True)
        self.status_label = ttk.Label(header_center, text="Status: Idle", anchor="center")
        self.status_label.pack()

        header_right = ttk.Frame(header)
        header_right.pack(side="right", anchor="e")
        theme_label = ttk.Label(header_right, text="Macro Theme:")
        theme_label.pack(side="left", padx=(0, 6))
        theme_combobox = ttk.Combobox(header_right, values=ttk.Style().theme_names(), state="readonly", width=18)
        theme_combobox.set(selected_theme)
        theme_combobox.pack(side="left")
        theme_combobox.bind("<<ComboboxSelected>>", lambda e: self.update_theme(theme_combobox.get()))

        body_pane = ttk.PanedWindow(self.root, orient="horizontal")
        body_pane.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        nav_frame = ttk.Frame(body_pane, width=220)
        nav_frame.pack_propagate(False)
        body_pane.add(nav_frame, weight=0)

        content_frame = ttk.Frame(body_pane)
        body_pane.add(content_frame, weight=1)

        notice_frame = ttk.Frame(content_frame)
        webhook_frame = ttk.Frame(content_frame)
        misc_frame = ttk.Frame(content_frame)
        merchant_frame = ttk.Frame(content_frame)
        aura_webhook_frame = ttk.Frame(content_frame)
        hp_craft_frame = ttk.Frame(content_frame)
        stats_frame = ttk.Frame(content_frame)
        other_features_frame = ttk.Frame(content_frame)
        customizations_frame = ttk.Frame(content_frame)
        credits_frame = ttk.Frame(content_frame)
        donations_frame = ttk.Frame(content_frame)
        remote_access_frame = ttk.Frame(content_frame)

        frames = {
            "Notice": notice_frame,
            "Webhook": webhook_frame,
            "Remote Access": remote_access_frame,
            "Misc": misc_frame,
            "Merchant": merchant_frame,
            "Auras": aura_webhook_frame,
            "Potion Crafting": hp_craft_frame,
            "Stats": stats_frame,
            "Other Features": other_features_frame,
            "Customizations": customizations_frame,
            "Credits": credits_frame,
            "Donations <3": donations_frame
        }

        for f in frames.values():
            f.pack(fill="both", expand=True)
            f.pack_forget()

        self.create_notice_tab(notice_frame)
        self.create_webhook_tab(webhook_frame)
        self.create_misc_tab(misc_frame)
        self.create_other_features_tab(other_features_frame)
        self.create_customizations_tab(customizations_frame)
        self.create_auras_tab(aura_webhook_frame)
        self.create_merchant_tab(merchant_frame)
        self.create_stats_tab(stats_frame)
        self.create_credit_tab(credits_frame)
        self.create_donations_tab(donations_frame)
        self.create_potion_craft_tab(hp_craft_frame)
        self.create_remote_access_tab(remote_access_frame)

        nav_buttons = {}

        def show_frame(name):
            try:
                for btn_name, btn in nav_buttons.items():
                    try:
                        btn.configure(bootstyle="outline-secondary")
                    except Exception:
                        pass
                nav_buttons[name].configure(bootstyle="primary")
            except Exception:
                pass
            for nm, fr in frames.items():
                try:
                    if nm == name:
                        fr.pack(fill="both", expand=True)
                        fr.tkraise()
                    else:
                        fr.pack_forget()
                except Exception:
                    pass
            try:
                self.status_label.config(text=f"Status: Viewing — {name}")
            except Exception:
                pass

        for i, name in enumerate(frames.keys()):
            b = ttk.Button(nav_frame, text=name, width=22, command=lambda n=name: show_frame(n))
            b.pack(pady=6, padx=8)
            nav_buttons[name] = b

        nav_footer = ttk.Frame(nav_frame)
        nav_footer.pack(side="bottom", fill="x", padx=6, pady=8)
        total_biomes = sum(self.biome_counts.values()) if getattr(self, "biome_counts", None) else 0
        total_label = ttk.Label(nav_footer, text=f"Total Biomes: {total_biomes}")
        total_label.pack(side="left", padx=(0, 4))
        sess_label = ttk.Label(nav_footer, text=f"Session: {self.get_total_session_time()}")
        sess_label.pack(side="right", padx=(4, 0))
        self.total_biomes_label = total_label
        self.session_label = sess_label

        show_frame("Notice")

        keyboard.add_hotkey("F1", lambda: (_start_wrapper()))
        keyboard.add_hotkey("F2", lambda: (_stop_wrapper()))

        self.check_for_updates()
        self.root.mainloop()

    def update_theme(self, theme_name):
        self.root.style.theme_use(theme_name)
        self.config["selected_theme"] = theme_name
        self.save_config()

    def check_for_updates(self):
        current_version = "v2.0.1"
        dont_ask_again = self.config.get("dont_ask_for_update", False)

        if dont_ask_again: return

        try:
            response = requests.get("https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest")
            response.raise_for_status()
            latest_release = response.json()
            latest_version = latest_release['tag_name']

            if latest_version != current_version:
                message = f"New update of this macro {latest_version} is available. Do you want to download the newest version?"
                if messagebox.askyesno("Update Available!!", message):
                    download_url = latest_release['assets'][0]['browser_download_url']
                    self.download_update(download_url)
                else:
                    if messagebox.askyesno("Don't Ask Again", "Would you like to stop receiving update notifications?"):
                        self.config["dont_ask_for_update"] = True
                        self.save_config()

        except requests.RequestException as e:
            print(f"Failed to fetch the latest version from GitHub: {e}")

    # this cro was here (funny easter egg)

    def download_update(self, download_url):
        try:
            zip_filename = os.path.basename(download_url)
            save_path = filedialog.asksaveasfilename(defaultextension=".zip", initialfile=zip_filename, title="Save As")

            if not save_path: return

            response = requests.get(download_url)
            response.raise_for_status()

            with open(save_path, 'wb') as file:
                file.write(response.content)

            messagebox.showinfo("Download Complete",
                                f"The latest version has been downloaded as {save_path}. Make sure to turn off antivirus and extract it manually.")
        except requests.RequestException as e:
            print(f"Failed to download the update: {e}")

    def open_biome_settings(self):
        settings_window = ttk.Toplevel(self.root)
        settings_window.title("Biome Settings")

        silly_note_label = ttk.Label(settings_window,
                                     text="GLITCHED, DREAMSPACE & CYBERSPACE are both forced 'everyone' ping grrr >:((",
                                     foreground="red")
        silly_note_label.grid(row=0, columnspan=2, padx=(10, 0), pady=(10, 0))

        biomes = [biome for biome in self.biome_data.keys() if biome not in ["GLITCHED", "DREAMSPACE", "CYBERSPACE", "NORMAL"]]
        window_height = max(475, len(biomes) * 43)
        settings_window.geometry(f"465x{window_height}")

        options = ["None", "Message"]

        for i, biome in enumerate(biomes):
            ttk.Label(settings_window, text=f"{biome}:").grid(row=i + 1, column=0, sticky="e")

            if biome not in self.variables:
                self.variables[biome] = ttk.StringVar(value="Message")

            dropdown = ttk.Combobox(settings_window, textvariable=self.variables[biome], values=options,
                                    state="readonly")
            dropdown.grid(row=i + 1, column=1, pady=5)

        def save_biome_setting():
            self.save_config()
            settings_window.destroy()

        ttk.Button(settings_window, text="Save", command=save_biome_setting).grid(row=len(biomes) + 2, column=1,
                                                                                  pady=10)

    def open_buff_selections_window(self):
        buff_window = ttk.Toplevel(self.root)
        buff_window.title("Buff Selections")
        buff_window.geometry("440x370")

        buffs = {
            "Xyz Potion": 1,
            "Oblivion Potion": 1,
            "Godlike Potion": 1,
            "Heavenly Potion": 1,
            "Potion of bound": 1,
            "Fortune Potion III": 1,
            "Fortune Potion II": 1,
            "Fortune Potion I": 1,
            "Haste Potion III": 1,
            "Haste Potion II": 1,
            "Haste Potion I": 1,
            "Warp Potion": 1,
            "Strange Potion I": 1,
            "Strange Potion II": 1,
            "Stella's Candle": 1,
            "Speed Potion": 1,
            "Lucky Potion": 1,
        }

        if "auto_buff_glitched" not in self.config:
            self.config["auto_buff_glitched"] = {}

        num_columns = 2
        for i, (buff, default_amount) in enumerate(buffs.items()):
            buff_config = self.config["auto_buff_glitched"].get(buff, (False, default_amount))
            buff_enabled, buff_amount = buff_config

            self.buff_vars[buff] = ttk.BooleanVar(value=buff_enabled)
            self.buff_amount_vars[buff] = ttk.StringVar(value=str(buff_amount))

            row = i // num_columns
            col = (i % num_columns) * 2

            ttk.Checkbutton(
                buff_window,
                text=buff,
                variable=self.buff_vars[buff],
                command=self.save_config
            ).grid(row=row, column=col, sticky="w", padx=10, pady=5)

            entry = ttk.Entry(
                buff_window,
                textvariable=self.buff_amount_vars[buff],
                width=5
            )
            entry.grid(row=row, column=col + 1, padx=10, pady=5)
            entry.bind("<FocusOut>", lambda event: self.save_config())

    def create_webhook_tab(self, frame):
        ttk.Label(frame, text="Webhook settings:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Button(frame, text="Open Webhooks settings", command=self.open_webhooks_settings).grid(row=0, column=1,
                                                                                                   sticky="w", padx=5,
                                                                                                   pady=5)
        self.webhook_display_label = ttk.Label(frame, text="")
        self.webhook_display_label.grid(row=0, column=2, sticky="w", padx=5, pady=5)

        ttk.Label(frame, text="Private Server Link:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.private_server_link_entry = ttk.Entry(frame, width=50)
        self.private_server_link_entry.grid(row=1, column=1, columnspan=2, sticky="we", pady=5)
        self.private_server_link_entry.insert(0, self.config.get("private_server_link", ""))
        self.private_server_link_entry.bind("<FocusOut>", lambda event: self.validate_and_save_ps_link())

        frame.grid_columnconfigure(1, weight=1)

        ttk.Button(frame, text="Configure Biomes", command=self.open_biome_settings).grid(row=2, column=1, pady=10,
                                                                                          sticky="e", padx=10)
        ttk.Button(frame, text="Import Config", command=self.import_config).grid(row=2, column=2, pady=10, sticky="w",
                                                                                 padx=10)
    def create_remote_access_tab(self, frame):
        self.remote_access_var = ttk.BooleanVar(value=self.config.get("remote_access_enabled", False))
        en_cb = ttk.Checkbutton(frame, text="Enable Remote Access Control", variable=self.remote_access_var, command=self._remote_access_toggle)
        en_cb.pack(anchor="w", padx=8, pady=(8,4))
        token_frame = ttk.Frame(frame)
        token_frame.pack(fill="x", padx=8, pady=4)
        ttk.Label(token_frame, text="Discord Bot Token:").pack(side="left", padx=(0,6))
        self.remote_bot_token_var = ttk.StringVar(value=self.config.get("remote_bot_token", ""))
        self.remote_bot_token_entry = ttk.Entry(token_frame, textvariable=self.remote_bot_token_var, width=48)
        self.remote_bot_token_entry.pack(side="left", padx=(0,6))
        self.remote_bot_token_entry.bind("<FocusOut>", lambda e: self.save_config())
        id_frame = ttk.Frame(frame)
        id_frame.pack(fill="x", padx=8, pady=4)
        ttk.Label(id_frame, text="Allowed User ID:").pack(side="left", padx=(0,6))
        self.remote_allowed_user_id_var = ttk.StringVar(value=self.config.get("remote_allowed_user_id", ""))
        self.remote_allowed_user_id_entry = ttk.Entry(id_frame, textvariable=self.remote_allowed_user_id_var, width=24)
        self.remote_allowed_user_id_entry.pack(side="left", padx=(0,6))
        self.remote_allowed_user_id_entry.bind("<FocusOut>", lambda e: self.save_config())
        link = ttk.Label(frame, text="Setup tutorial", foreground="royalblue", cursor="hand2")
        link.configure(font=('Segoe UI', 9, 'underline'))
        link.pack(anchor="w", padx=8, pady=(6,0))
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://youtu.be/y3gocH9Hd18"))
        self.remote_status_label = ttk.Label(frame, text="Bot: stopped")
        self.remote_status_label.pack(anchor="w", padx=8, pady=(6,0))
        self.remote_command_queue = queue.Queue()
        self._remote_check_merchant_results = {}
        self._help_command_list = [
            ("screenshot", "", "Take current ingame screenshot and send to webhooks. For inventory/aura screenshot, you'll need periodical inventory screenshot/aura enabled. For full screenshot you need neither of them."),
            ("reroll_quest", "{quest name}", "Reroll a daily quest. Quest 1 is the first quest on the list and so on."),
            ("check_merchant", "", "Use merchant teleporter immediately and check whether if a merchant has spawned or not."),
            ("use", "{item_name} {amount}", "Use item remotely."),
            ("rejoin", "", "Close Roblox to force rejoin (requires Auto Reconnect enabled)."),
        ]
        self.remote_worker_running = False
        self.remote_bot_thread = None
        self.remote_bot_obj = None
        self._remote_running = False


    def _remote_access_toggle(self):
        self.save_config()
        if self.remote_access_var.get():
            try:
                token = self.remote_bot_token_var.get().strip()
                if token:
                    self.start_remote_bot()
            except Exception:
                pass
        else:
            try:
                self.stop_remote_bot()
            except Exception:
                pass

    def start_remote_bot(self):
        if getattr(self, "remote_bot_thread", None) and self.remote_bot_thread and self.remote_bot_thread.is_alive():
            return
        token = self.remote_bot_token_var.get().strip()
        if not token:
            messagebox.showwarning("Remote Access", "Please enter a bot token first.")
            return
        self.remote_worker_running = True
        self.remote_bot_thread = threading.Thread(target=self._remote_bot_thread_func, daemon=True)
        self.remote_bot_thread.start()
        self.save_config()

    def stop_remote_bot(self):
        try:
            self.remote_worker_running = False
            if getattr(self, "remote_bot_obj", None):
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.remote_bot_obj.close())
                except Exception:
                    pass
            self.remote_bot_obj = None
            self.remote_status_label.config(text="Bot: stopped")
        except Exception:
            pass

    def _remote_bot_thread_func(self):
        try:
            token = self.remote_bot_token_var.get().strip()
            allowed_id = self.remote_allowed_user_id_var.get().strip()
            try:
                allowed_id_int = int(allowed_id) if allowed_id else None
            except Exception:
                allowed_id_int = None
            import asyncio
            import discord
            from discord import Option
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            bot = discord.Bot()
            self.remote_bot_obj = bot
            @bot.slash_command(name="rejoin", description="Close Roblox to force rejoin (requires Auto Reconnect enabled)")
            async def rejoin(ctx):
                try:
                    if allowed_id_int and getattr(ctx.author, "id", None) != allowed_id_int:
                        try:
                            await ctx.respond("Unauthorized", ephemeral=True)
                        except Exception:
                            pass
                        return
                    try:
                        if not self.config.get("auto_reconnect"):
                            try:
                                await ctx.respond("Auto Reconnect is disabled. Enable it in settings to use /rejoin.", ephemeral=True)
                            except Exception:
                                pass
                            return
                    except Exception:
                        pass
                    try:
                        self.remote_command_queue.put(("__rejoin__", ""))
                        try:
                            await ctx.respond("Queued rejoin — will close Roblox if running.", ephemeral=False)
                        except Exception:
                            pass
                    except Exception:
                        try:
                            await ctx.respond("Queue error", ephemeral=True)
                        except Exception:
                            pass
                except Exception:
                    pass

            @bot.slash_command(name="help", description="Helping u out with remote access features")
            async def help_cmd(ctx, page: Option(int, "Page number", required=False, default=1)):
                try:
                    cmds = getattr(self, "_help_command_list", [])
                    per = 5
                    total = (len(cmds) + per - 1) // per if cmds else 1
                    p = (page or 1)
                    try:
                        p = int(p)
                    except Exception:
                        p = 1
                    if p < 1:
                        p = 1
                    if p > total:
                        p = total
                    start = (p - 1) * per
                    end = start + per
                    page_items = cmds[start:end]
                    lines = []
                    for idx, cmd in enumerate(page_items, start=1):
                        name = cmd[0] if len(cmd) > 0 else ""
                        usage = cmd[1] if len(cmd) > 1 else ""
                        desc = cmd[2] if len(cmd) > 2 else ""
                        lines.append(f"`/{name} {usage}` - {desc}")
                    content = f"Help page {p}/{total}\n" + ("\n".join(lines) if lines else "No commands on this page")
                    try:
                        await ctx.respond(content, ephemeral=False)
                    except Exception:
                        pass
                except Exception:
                    pass
            @bot.slash_command(name="use", description="Use an item remotely")
            async def use(ctx, item: Option(str, "Item name"), amount: Option(int, "Amount", default=1)):
                try:
                    if allowed_id_int and getattr(ctx.author, "id", None) != allowed_id_int:
                        try:
                            await ctx.respond("Unauthorized", ephemeral=True)
                        except Exception:
                            pass
                        return
                    try:
                        self.remote_command_queue.put((str(item), int(amount)))
                        try:
                            await ctx.respond(f"Queued {item}, amount: {amount}", ephemeral=False)
                        except Exception:
                            pass
                    except Exception:
                        try:
                            await ctx.respond("Queue error", ephemeral=True)
                        except Exception:
                            pass
                except Exception:
                    pass
            @bot.slash_command(name="check_merchant", description="Use merchant teleporter and check for merchant")
            async def check_merchant(ctx):
                try:
                    if allowed_id_int and getattr(ctx.author, "id", None) != allowed_id_int:
                        try:
                            await ctx.respond("Unauthorized", ephemeral=True)
                        except Exception:
                            pass
                        return
                    try:
                        uid = str(time.time()).replace(".", "")
                        self._remote_check_merchant_results[uid] = None
                        try:
                            await ctx.respond("Carrying out auto merchants and checking whether if a merchant has spawned...", ephemeral=False)
                        except Exception:
                            pass
                        try:
                            self.remote_command_queue.put(("__check_merchant__", uid))
                        except Exception:
                            pass
                        try:
                            import asyncio
                            asyncio.create_task(self._remote_check_merchant_wait_and_edit(ctx, uid))
                        except Exception:
                            pass
                    except Exception:
                        try:
                            await ctx.respond("Queue error", ephemeral=True)
                        except Exception:
                            pass
                except Exception:
                    pass
            @bot.slash_command(name="screenshot", description="Take current ingame screenshot and send to webhooks")
            async def screenshot(ctx, target: Option(str, """arguments: 'inventory' or 'aura', leave blank for full screen screenshot.""", required=False)):
                try:
                    if allowed_id_int and getattr(ctx.author, "id", None) != allowed_id_int:
                        try:
                            await ctx.respond("Unauthorized", ephemeral=True)
                        except Exception:
                            pass
                        return
                    try:
                        t = (str(target) or "").strip().lower()
                        if not t:
                            t = "full"
                        if t not in ("full", "inventory", "aura"):
                            t = "full"
                        self.remote_command_queue.put(("__screenshot__", t))
                        try:
                            await ctx.respond(f"Queued screenshot ({t})", ephemeral=False)
                        except Exception:
                            pass
                    except Exception:
                        try:
                            await ctx.respond("Queue error", ephemeral=True)
                        except Exception:
                            pass
                except Exception:
                    pass
            @bot.slash_command(name="reroll_quest", description="Reroll a selected daily quest")
            async def reroll_quest(ctx, quest: Option(str, "Quest to reroll", choices=["Quest 1", "Quest 2", "Quest 3"])):
                try:
                    if allowed_id_int and getattr(ctx.author, "id", None) != allowed_id_int:
                        try:
                            await ctx.respond("Unauthorized", ephemeral=True)
                        except Exception:
                            pass
                        return
                    try:
                        q = (quest or "").strip().lower()
                        if q in ("quest 1", "quest1", "1"):
                            self.remote_command_queue.put(("__reroll__", "1"))
                        elif q in ("quest 2", "quest2", "2"):
                            self.remote_command_queue.put(("__reroll__", "2"))
                        elif q in ("quest 3", "quest3", "3"):
                            self.remote_command_queue.put(("__reroll__", "3"))
                        else:
                            self.remote_command_queue.put(("__reroll__", "1"))
                        try:
                            await ctx.respond(f"Queued reroll {quest}", ephemeral=False)
                        except Exception:
                            pass
                    except Exception:
                        try:
                            await ctx.respond("Queue error", ephemeral=True)
                        except Exception:
                            pass
                except Exception:
                    pass
            try:
                self.set_title_threadsafe("Coteab Macro v2.0.1 (Remote bot starting)")
            except Exception:
                pass
            try:
                self.remote_status_label.config(text="Bot: running")
            except Exception:
                pass
            worker = threading.Thread(target=self._remote_queue_worker, daemon=True)
            worker.start()
            try:
                bot.run(token)
            except Exception:
                pass
        except Exception:
            pass
        finally:
            try:
                self.remote_status_label.config(text="Bot: stopped")
            except Exception:
                pass
            self.remote_bot_obj = None
            self.remote_worker_running = False

    async def _remote_check_merchant_wait_and_edit(self, ctx, uid):
        try:
            import asyncio
            timeout = 20.0
            waited = 0.0
            interval = 0.5
            result = None
            while waited < timeout:
                try:
                    result = self._remote_check_merchant_results.get(uid) if isinstance(self._remote_check_merchant_results, dict) else None
                except Exception:
                    result = None
                if result is not None:
                    break
                await asyncio.sleep(interval)
                waited += interval
            if result is True:
                try:
                    try:
                        await ctx.interaction.edit_original_response(content="Merchant found!")
                    except Exception:
                        try:
                            await ctx.respond("Merchant found!", ephemeral=False)
                        except Exception:
                            pass
                except Exception:
                    pass
            elif result is False:
                try:
                    try:
                        await ctx.interaction.edit_original_response(content="No merchant was found")
                    except Exception:
                        try:
                            await ctx.respond("No merchant was found", ephemeral=False)
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                try:
                    try:
                        await ctx.interaction.edit_original_response(content="No merchant was found")
                    except Exception:
                        try:
                            await ctx.respond("No merchant was found", ephemeral=False)
                        except Exception:
                            pass
                except Exception:
                    pass
            try:
                if isinstance(self._remote_check_merchant_results, dict) and uid in self._remote_check_merchant_results:
                    try:
                        del self._remote_check_merchant_results[uid]
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

    def _remote_queue_worker(self):
        while getattr(self, "remote_worker_running", False):
            try:
                cmd = None
                try:
                    cmd = self.remote_command_queue.get(timeout=1)
                except Exception:
                    continue
                if cmd is None:
                    continue
                item_name, amount = cmd[0], cmd[1]
                if item_name == "__reroll__":
                    if not self.detection_running or self.reconnecting_state:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False):
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    def _reroll_action():
                        try:
                            self._remote_running = True
                            try:
                                self.remote_status_label.config(text=f"Bot: rerolling quest {amount}")
                            except Exception:
                                pass
                            try:
                                self.perform_quest_reroll(amount)
                            except Exception:
                                pass
                        finally:
                            self._remote_running = False
                            try:
                                self.remote_status_label.config(text="Bot: running")
                            except Exception:
                                pass

                    try:
                        self._action_scheduler.enqueue_action(_reroll_action, name=f"remote:reroll:{amount}", priority=6)
                    except Exception:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                    continue

                if item_name == "__check_merchant__":
                    uid = (amount or "")
                    if not self.detection_running or self.reconnecting_state:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, uid))
                        except Exception:
                            pass
                        continue

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False):
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, uid))
                        except Exception:
                            pass
                        continue

                    def _check_merchant_action():
                        try:
                            self._remote_running = True
                            try:
                                self.remote_status_label.config(text="Bot: checking merchant")
                            except Exception:
                                pass
                            try:
                                snapshot = {}
                                try:
                                    snapshot = dict(self.last_merchant_sent) if hasattr(self, "last_merchant_sent") else {}
                                except Exception:
                                    snapshot = {}
                                try:
                                    if hasattr(self, "_merchant_teleporter_impl"):
                                        try:
                                            self._merchant_teleporter_impl()
                                        except Exception:
                                            try:
                                                self.use_merchant_teleporter()
                                            except Exception:
                                                pass
                                    else:
                                        try:
                                            self.use_merchant_teleporter()
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                found = False
                                try:
                                    if hasattr(self, "last_merchant_sent"):
                                        for k, v in (self.last_merchant_sent.items() if isinstance(self.last_merchant_sent, dict) else []):
                                            if k not in snapshot or snapshot.get(k) != v:
                                                try:
                                                    if isinstance(k, tuple) and len(k) > 1 and k[1] == "ocr":
                                                        found = True
                                                        break
                                                except Exception:
                                                    pass
                                except Exception:
                                    found = False
                                try:
                                    self._remote_check_merchant_results[uid] = True if found else False
                                except Exception:
                                    pass
                            except Exception:
                                try:
                                    self._remote_check_merchant_results[uid] = False
                                except Exception:
                                    pass
                        finally:
                            self._remote_running = False
                            try:
                                self.remote_status_label.config(text="Bot: running")
                            except Exception:
                                pass

                    try:
                        self._action_scheduler.enqueue_action(_check_merchant_action, name=f"remote:check_merchant:{uid}", priority=3)
                    except Exception:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, uid))
                        except Exception:
                            pass
                    continue

                if item_name == "__rejoin__":
                    if not self.detection_running or self.reconnecting_state:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False):
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    def remote_rejoin_action():
                        try:
                            self._remote_running = True
                            try:
                                self.remote_status_label.config(text="Bot: performing rejoin")
                            except Exception:
                                pass
                            try:
                                if self.check_roblox_procs():
                                    try:
                                        self.terminate_roblox_processes()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        finally:
                            self._remote_running = False
                            try:
                                self.remote_status_label.config(text="Bot: running")
                            except Exception:
                                pass

                    try:
                        self._action_scheduler.enqueue_action(remote_rejoin_action, name="remote:rejoin", priority=2)
                    except Exception:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                    continue

                if item_name == "__screenshot__":
                    if not self.detection_running or self.reconnecting_state:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False):
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    requested = str(amount or "").lower()
                    if requested not in ("full", "inventory", "aura"):
                        requested = "full"

                    if requested == "full":
                        def _screenshot_action():
                            try:
                                self._remote_running = True
                                try:
                                    self.remote_status_label.config(text="Bot: taking screenshot")
                                except Exception:
                                    pass
                                try:
                                    self.remote_take_and_send_screenshot()
                                except Exception:
                                    pass
                            finally:
                                self._remote_running = False
                                try:
                                    self.remote_status_label.config(text="Bot: running")
                                except Exception:
                                    pass

                        try:
                            self._action_scheduler.enqueue_action(_screenshot_action, name="remote:screenshot", priority=8)
                        except Exception:
                            try:
                                time.sleep(0.35)
                                self.remote_command_queue.put((item_name, amount))
                            except Exception:
                                pass
                        continue

                    if requested == "inventory":
                        def _inv_action():
                            try:
                                self._remote_running = True
                                try:
                                    self.remote_status_label.config(text="Bot: taking inventory screenshot")
                                except Exception:
                                    pass
                                try:
                                    self.take_inventory_screenshot_now()
                                except Exception:
                                    pass
                            finally:
                                self._remote_running = False
                                try:
                                    self.remote_status_label.config(text="Bot: running")
                                except Exception:
                                    pass

                        try:
                            self._action_scheduler.enqueue_action(_inv_action, name="remote:screenshot:inventory", priority=7)
                        except Exception:
                            try:
                                time.sleep(0.35)
                                self.remote_command_queue.put((item_name, amount))
                            except Exception:
                                pass
                        continue

                    if requested == "aura":
                        def _aura_action():
                            try:
                                self._remote_running = True
                                try:
                                    self.remote_status_label.config(text="Bot: taking aura screenshot")
                                except Exception:
                                    pass
                                try:
                                    self.take_aura_screenshot_now()
                                except Exception:
                                    pass
                            finally:
                                self._remote_running = False
                                try:
                                    self.remote_status_label.config(text="Bot: running")
                                except Exception:
                                    pass

                        try:
                            self._action_scheduler.enqueue_action(_aura_action, name="remote:screenshot:aura", priority=7)
                        except Exception:
                            try:
                                time.sleep(0.35)
                                self.remote_command_queue.put((item_name, amount))
                            except Exception:
                                pass
                        continue
                if not self.detection_running or self.reconnecting_state:
                    try:
                        time.sleep(0.35)
                        self.remote_command_queue.put((item_name, amount))
                    except Exception:
                        pass
                    continue

                if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False):
                    try:
                        time.sleep(0.35)
                        self.remote_command_queue.put((item_name, amount))
                    except Exception:
                        pass
                    continue

                def _remote_action():
                    try:
                        self._remote_running = True
                        try:
                            self.remote_status_label.config(text=f"Bot: executing {item_name} x{amount}")
                        except Exception:
                            pass
                        try:
                            self.remote_use_item(item_name, amount)
                        except Exception:
                            pass
                    finally:
                        self._remote_running = False
                        try:
                            self.remote_status_label.config(text="Bot: running")
                        except Exception:
                            pass

                try:
                    self._action_scheduler.enqueue_action(_remote_action, name=f"remote:{item_name}", priority=6)
                except Exception:
                    try:
                        time.sleep(0.35)
                        self.remote_command_queue.put((item_name, amount))
                    except Exception:
                        pass

            except Exception:
                time.sleep(0.2)
                continue

    def take_inventory_screenshot_now(self):
        try:
            if not getattr(self, "periodical_inventory_var", None) or not self.periodical_inventory_var.get():
                return
            if not self.check_roblox_procs():
                return
            self.activate_roblox_window()
            search_bar = self.config.get("search_bar", [855, 358])
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
            if inventory_menu and inventory_menu[0]:
                try:
                    autoit.mouse_click("left", inventory_menu[0], inventory_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                    except Exception:
                        pass
                time.sleep(0.35)
            if items_tab and items_tab[0]:
                try:
                    autoit.mouse_click("left", items_tab[0], items_tab[1], 1, speed=3)
                    time.sleep(1)
                    autoit.mouse_click("left", search_bar[0], search_bar[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(items_tab[0], items_tab[1])
                    except Exception:
                        pass
                time.sleep(0.35)
            try:
                os.makedirs("images", exist_ok=True)
                filename = os.path.join("images", f"inventory_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_inventory_screenshot_webhook(filename)
                self.last_inventory_screenshot_time = datetime.now()
            except Exception as e:
                self.error_logging(e, "Error taking/sending forced inventory screenshot")
            try:
                if inventory_close_button and inventory_close_button[0]:
                    try:
                        autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        except Exception:
                            pass
                    time.sleep(0.22)
            except Exception as e:
                self.error_logging(e, "Error while closing inventory after forced screenshot")
        except Exception as e:
            self.error_logging(e, "Error in take_inventory_screenshot_now")

    def take_aura_screenshot_now(self):
        try:
            if not getattr(self, "periodical_aura_var", None) or not self.periodical_aura_var.get():
                return
            if not self.check_roblox_procs():
                return
            self.activate_roblox_window()
            aura_menu = self.config.get("aura_menu", [0, 0])
            if aura_menu and aura_menu[0]:
                try:
                    autoit.mouse_click("left", aura_menu[0], aura_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(aura_menu[0], aura_menu[1])
                    except Exception:
                        pass
                time.sleep(0.67)
                try:
                    os.makedirs("images", exist_ok=True)
                    filename = os.path.join("images", f"aura_screenshot_{int(time.time())}.png")
                    img = pyautogui.screenshot()
                    img.save(filename)
                    self.send_aura_screenshot_webhook(filename)
                    self.last_aura_screenshot_time = datetime.now()
                except Exception as e:
                    self.error_logging(e, "Error taking/sending forced aura screenshot")
        except Exception as e:
            self.error_logging(e, "Error in take_aura_screenshot_now")

    def remote_use_item(self, item_name, amount):
        if not self.detection_running or self.reconnecting_state:
            return
        inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
        for _ in range(4):
            if not self.detection_running or self.reconnecting_state:
                return
            self.activate_roblox_window()
            time.sleep(0.35)
        time.sleep(0.57)
        inventory_menu = self.config.get("inventory_menu", [36, 535])
        inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
        self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
        time.sleep(0.22 + inventory_click_delay)
        search_bar = self.config.get("search_bar", [855, 358])
        self.Global_MouseClick(search_bar[0], search_bar[1], click=2)
        time.sleep(0.23 + inventory_click_delay)
        try:
            autoit.send(item_name)
        except Exception:
            try:
                keyboard.write(item_name.lower())
            except Exception:
                pass
        time.sleep(0.22 + inventory_click_delay)
        first_item_slot = self.config.get("first_item_slot", [839, 434])
        self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
        time.sleep(0.27 + inventory_click_delay)
        amount_box = self.config.get("amount_box", [954, 429])
        self.Global_MouseClick(amount_box[0], amount_box[1], click=2)
        time.sleep(0.09 + inventory_click_delay)
        try:
            keyboard.send("ctrl+a")
            time.sleep(0.06 + inventory_click_delay)
            keyboard.send("backspace")
            time.sleep(0.06 + inventory_click_delay)
        except Exception:
            try:
                keyboard.send("backspace")
                time.sleep(0.06 + inventory_click_delay)
            except Exception:
                pass
        try:
            autoit.send(str(amount))
        except Exception:
            try:
                keyboard.write(str(amount))
            except Exception:
                pass
        time.sleep(0.12 + inventory_click_delay)
        use_button = self.config.get("use_button", [995, 498])
        self.Global_MouseClick(use_button[0], use_button[1])
        time.sleep(0.25)
        self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
        time.sleep(0.12)

    def send_screen_screenshot_webhook(self, screenshot_path):
        try:
            urls = self.get_webhook_list()
            if not urls:
                return
            content = ""
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)
            embed = {
                "description": f"> ## Remote Screenshot",
                "color": 0xffffff,
                "footer": {"text": "Coteab Macro v2.0.1", "icon_url": icon_url},
                "timestamp": current_utc_time
            }
            for webhook_url in urls:
                try:
                    embed_copy = dict(embed)
                    embed_copy["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}
                    with open(screenshot_path, "rb") as image_file:
                        files = {"file": (os.path.basename(screenshot_path), image_file, "image/png")}
                        data = {"payload_json": json.dumps({"content": content, "embeds": [embed_copy]})}
                        requests.post(webhook_url, data=data, files=files, timeout=10)
                except Exception as e:
                    try:
                        print(f"Failed to send screenshot to {webhook_url}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            self.error_logging(e, "Error in send_screen_screenshot_webhook")

    def remote_take_and_send_screenshot(self):
        try:
            if not self.detection_running or self.reconnecting_state:
                return
            for _ in range(4):
                if not self.detection_running or self.reconnecting_state:
                    return
                self.activate_roblox_window()
                time.sleep(0.35)
            time.sleep(0.5)
            try:
                os.makedirs("images", exist_ok=True)
                filename = os.path.join("images", f"remote_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_screen_screenshot_webhook(filename)
            except Exception as e:
                self.error_logging(e, "Error taking/sending remote screenshot")
        except Exception:
            pass

    def create_donations_tab(self, frame):
        t1 = "Our projects are 100% free to use and you're allowed to recycle any fraction of our code with proper credits. However, if you want to support our team, you can help us by purchasing any of the gamepasses below :)"
        t2 = """It helps us out a lot mentally, any donations above 100 Robux will get you on the appreciation list below, 500 Robux will give you the permission to leave a special message on the appreciation list (must be sfw though) & 1000 Robux will give you access to early Coteab macro releases (beta vers) :D Normally we will check donations history daily, but if your Roblox username isn't displayed here please DM "@criticize." on Discord. The appreciation list also takes up to 5 minutes to update due to Github."""
        link = "https://www.roblox.com/games/18203398779/Medival-castle#!/store"
        ttk.Label(frame, text=t1, justify="left", wraplength=700).pack(padx=10, pady=(12, 6), anchor="w")
        ttk.Label(frame, text=t2, justify="left", wraplength=700).pack(padx=10, pady=(0, 6), anchor="w")
        link_label = ttk.Label(frame, text=link, foreground="royalblue", cursor="hand2", wraplength=700)
        link_label.configure(font=('Segoe UI', 9, 'underline'))
        link_label.pack(padx=10, pady=(0, 12), anchor="w")
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new(link))
        hall = ttk.LabelFrame(frame, text="Donators hall of fame (it automatically updates)")
        hall.pack(fill='both', expand=True, padx=5, pady=5)
        txt = ttk.Text(hall, height=14, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/appreciation_list.txt"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            body = r.text.strip() or "(No entries yet)"
        except Exception:
            body = "Unable to load appreciation list."
        txt.insert("1.0", body)
        txt.config(state="disabled")

    def create_other_features_tab(self, frame):
        self.player_logger_var = ttk.BooleanVar(value=self.config.get("player_logger", True))
        c = ttk.Checkbutton(frame,
                            text="Player logger (Requires FFlags, the macro should auto apply it. If not, please refer to README.md)",
                            variable=self.player_logger_var, command=self.save_config)
        c.pack(anchor="w", padx=10, pady=10)
        self.anti_afk_var = ttk.BooleanVar(value=self.config.get("anti_afk", True))
        anti_afk_check = ttk.Checkbutton(frame,
                                        text="Anti-AFK (prevents Roblox disconnection even when Roblox isn't focused)",
                                        variable=self.anti_afk_var, command=self.save_config)
        anti_afk_check.pack(anchor="w", padx=10, pady=10)

        self.enable_buff_glitched_var = ttk.BooleanVar(value=self.config.get("enable_buff_glitched", False))
        enable_buff_glitched_check = ttk.Checkbutton(
            frame,
            text="Enable buff when Glitched (ONLY use this feature when you have your buffs DISABLED while hunting for Glitched)",
            variable=self.enable_buff_glitched_var,
            command=self.toggle_glitched_buff_frame
        )
        enable_buff_glitched_check.pack(anchor="w", padx=10, pady=10)

        self.glitched_buff_frame = ttk.Frame(frame)
        if self.enable_buff_glitched_var.get():
            self.glitched_buff_frame.pack(anchor="w", padx=30, pady=5)

        self.glitched_coord_vars = {}
        keys = [
            ("Calibrate Menu Button", "glitched_menu_button"),
            ("Calibrate Settings Button", "glitched_settings_button"),
            ('Calibrate "Buff Enable"', "glitched_buff_enable_button")
        ]

        for i, (label_text, config_key) in enumerate(keys):
            x_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[0])
            y_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[1])
            self.glitched_coord_vars[config_key] = (x_var, y_var)

            btn = ttk.Button(self.glitched_buff_frame, text=label_text,
                            command=lambda k=config_key: self.capture_single_click(k))
            btn.grid(row=0, column=i, padx=5, pady=2)

            ttk.Entry(self.glitched_buff_frame, textvariable=x_var, width=8).grid(row=1, column=i, padx=5, pady=2)
            ttk.Entry(self.glitched_buff_frame, textvariable=y_var, width=8).grid(row=2, column=i, padx=5, pady=2)

    def create_customizations_tab(self, frame):
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(anchor="w", padx=10, pady=10)

        upload_btn = ttk.Button(btn_frame, text="Upload Background Image", command=self.upload_background_image)
        upload_btn.pack(side="left", padx=5)

        clear_btn = ttk.Button(btn_frame, text="Clear Background Image", command=self.clear_background_image)
        clear_btn.pack(side="left", padx=5)

        ttk.Label(frame, text="").pack(pady=(6,0))
        customize_btn = ttk.Button(frame, text="Customize Biome Embed", command=self.open_customize_biome_embed)
        customize_btn.pack(anchor="w", padx=10, pady=10)

        current_path = self.config.get("custom_background_image", "")
        lbl = ttk.Label(frame, text=f"Current background: {current_path or '(none)'}", wraplength=700)
        lbl.pack(anchor="w", padx=10, pady=(6,0))
        self._custom_bg_label = lbl

    def upload_background_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
        if not path:
            return
        try:
            img = Image.open(path).convert("RGBA")
            w = max(1, self.root.winfo_width())
            h = max(1, self.root.winfo_height())
            img = img.resize((max(100, w), max(100, h)), Image.LANCZOS)
            alpha_val = int(255 * 0.9)
            r, g, b, a = img.split()
            new_alpha = a.point(lambda p: alpha_val)
            img.putalpha(new_alpha)
            self._bg_tk = ImageTk.PhotoImage(img)
            if not hasattr(self, "bg_label") or self.bg_label is None:
                self.bg_label = ttk.Label(self.root, image=self._bg_tk)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                try:
                    self.bg_label.lower()
                except Exception:
                    pass
            else:
                self.bg_label.config(image=self._bg_tk)
            cfg = {}
            try:
                if os.path.exists("config.json"):
                    with open("config.json", "r", encoding="utf-8") as f:
                        cfg = json.load(f)
            except Exception:
                cfg = {}
            cfg["custom_background_image"] = path
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            self.config["custom_background_image"] = path
            if hasattr(self, "_custom_bg_label"):
                try:
                    self._custom_bg_label.config(text=f"Current background: {path}")
                except Exception:
                    pass
            messagebox.showinfo("Background", "Background image applied and saved.")
        except Exception as e:
            self.error_logging(e, "Error applying background image")
            messagebox.showerror("Background", f"Failed to apply background: {e}")

    def clear_background_image(self):
        try:
            if hasattr(self, "bg_label") and self.bg_label:
                try:
                    self.bg_label.destroy()
                except Exception:
                    pass
                self.bg_label = None
            cfg = {}
            try:
                if os.path.exists("config.json"):
                    with open("config.json", "r", encoding="utf-8") as f:
                        cfg = json.load(f)
            except Exception:
                cfg = {}
            if "custom_background_image" in cfg:
                try:
                    del cfg["custom_background_image"]
                except Exception:
                    pass
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            self.config.pop("custom_background_image", None)
            if hasattr(self, "_custom_bg_label"):
                try:
                    self._custom_bg_label.config(text="Current background: (none)")
                except Exception:
                    pass
            messagebox.showinfo("Background", "Background image cleared.")
        except Exception as e:
            self.error_logging(e, "Error clearing background image")
            messagebox.showerror("Background", f"Failed to clear background: {e}")

    def open_customize_biome_embed(self):
        event_url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/main/active_events.json"
        try:
            r = requests.get(event_url, timeout=5)
            r.raise_for_status()
            events = r.json()
        except Exception:
            events = {"april_fools": False}
        if events.get("april_fools"):
            messagebox.showinfo("April Fools Active", "Embed customization is disabled while the April Fools event is active.")
            return
        win = ttk.Toplevel(self.root)
        win.title("Customize Biome Embed")
        win.geometry("760x560")
        container = ttk.Frame(win)
        container.pack(fill="both", expand=True, padx=8, pady=8)
        canvas = ttk.Canvas(container)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        def on_config(e):
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass
        inner.bind("<Configure>", on_config)
        vars_map = {}
        for i, biome in enumerate(self.biome_data.keys()):
            ttk.Label(inner, text=biome).grid(row=i, column=0, sticky="w", padx=6, pady=6)
            color_val = self.biome_data.get(biome, {}).get("color", "")
            thumb_val = self.biome_data.get(biome, {}).get("thumbnail_url", "")
            cvar = ttk.StringVar(value=color_val)
            tvar = ttk.StringVar(value=thumb_val)
            vars_map[biome] = (cvar, tvar)
            ttk.Entry(inner, textvariable=cvar, width=20).grid(row=i, column=1, padx=6, pady=6)
            ttk.Entry(inner, textvariable=tvar, width=60).grid(row=i, column=2, padx=6, pady=6)
        link = "https://www.rapidtables.com/convert/color/index.html"
        link_label = ttk.Label(win, text="Click here to get colour code", foreground="royalblue", cursor="hand2")
        link_label.configure(font=('Segoe UI', 9, 'underline'))
        link_label.pack(side="bottom", pady=8)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new(link))
        def save_and_close():
            overrides = {}
            for biome, (cvar, tvar) in vars_map.items():
                color_val = cvar.get().strip()
                thumb_val = tvar.get().strip()
                overrides[biome] = {"color": color_val, "thumbnail_url": thumb_val}
                try:
                    if biome in self.biome_data:
                        if color_val:
                            self.biome_data[biome]["color"] = color_val
                        if thumb_val:
                            self.biome_data[biome]["thumbnail_url"] = thumb_val
                except Exception:
                    pass
            cfg = {}
            try:
                if os.path.exists("config.json"):
                    with open("config.json", "r", encoding="utf-8") as f:
                        cfg = json.load(f)
            except Exception:
                cfg = {}
            cfg["custom_biome_overrides"] = overrides
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4)
            self.config["custom_biome_overrides"] = overrides
            messagebox.showinfo("Saved", "Biome embed customizations saved.")
            win.destroy()
        ttk.Button(win, text="Save & Close", command=save_and_close).pack(side="bottom", pady=6)

    def toggle_glitched_buff_frame(self):
        if self.enable_buff_glitched_var.get():
            self.glitched_buff_frame.pack(anchor="w", padx=30, pady=5)
        else:
            self.glitched_buff_frame.pack_forget()
        self.save_config()

    def toggle_ocr_failsafe(self):
        try:
            if getattr(self, "enable_ocr_failsafe_var", None) and self.enable_ocr_failsafe_var.get():
                if hasattr(self, "ocr_cal_btn"):
                    try:
                        self.ocr_cal_btn.grid(row=8, column=0, padx=5, pady=5, sticky="w")
                    except Exception:
                        pass
                if hasattr(self, "first_item_slot_ocr_label"):
                    try:
                        self.first_item_slot_ocr_label.grid(row=8, column=1, padx=5, sticky="w")
                    except Exception:
                        pass
            else:
                if hasattr(self, "ocr_cal_btn"):
                    try:
                        self.ocr_cal_btn.grid_forget()
                    except Exception:
                        pass
                if hasattr(self, "first_item_slot_ocr_label"):
                    try:
                        self.first_item_slot_ocr_label.grid_forget()
                    except Exception:
                        pass
        except Exception:
            pass
        self.save_config()

    def capture_single_click(self, config_key):
        win = ttk.Toplevel(self.root)
        win.attributes("-fullscreen", True)
        win.attributes("-alpha", 0.01)
        win.configure(bg="black")
        win.focus_force()
        try:
            win.grab_set()
        except Exception:
            pass
        def on_click(e):
            x, y = e.x_root, e.y_root
            self.config[config_key] = [x, y]
            try:
                if config_key == "potion_button1":
                    if hasattr(self, "potion_button1_x"):
                        self.potion_button1_x.set(x)
                    if hasattr(self, "potion_button1_y"):
                        self.potion_button1_y.set(y)
                elif config_key == "potion_search_bar1":
                    if hasattr(self, "potion_search_x"):
                        self.potion_search_x.set(x)
                    if hasattr(self, "potion_search_y"):
                        self.potion_search_y.set(y)
                elif config_key == "potion_button2":
                    if hasattr(self, "potion_button2_x"):
                        self.potion_button2_x.set(x)
                    if hasattr(self, "potion_button2_y"):
                        self.potion_button2_y.set(y)
                if hasattr(self, "glitched_coord_vars") and config_key in self.glitched_coord_vars:
                    self.glitched_coord_vars[config_key][0].set(x)
                    self.glitched_coord_vars[config_key][1].set(y)
            except Exception:
                pass
            self.save_config()
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()
            messagebox.showinfo("Calibration Saved", f"Saved {config_key}: {[x, y]}")
        win.bind("<Button-1>", on_click)

    def perform_glitched_enable_buff(self):
        try:
            if not self.config.get("enable_buff_glitched", False):
                return
            menu = self.config.get("glitched_menu_button", [0, 0])
            buff_enable = self.config.get("glitched_buff_enable_button", [0, 0])
            settings = self.config.get("glitched_settings_button", [0, 0])
            for _ in range(4):
                if not self.detection_running or self.reconnecting_state:
                    return
                self.activate_roblox_window()
                time.sleep(0.15)
            while True:
                if not self.detection_running or self.reconnecting_state:
                    return
                if not getattr(self, "_br_sc_running", False) and not getattr(self, "_mt_running", False) and not getattr(self, "auto_pop_state", False) and not getattr(self, "on_auto_merchant_state", False) and not self.config.get("enable_auto_craft", False):
                    break
                time.sleep(0.67)
            if menu and menu[0]:
                self.Global_MouseClick(menu[0], menu[1])
                time.sleep(0.67)
            if settings and settings[0]:
                self.Global_MouseClick(settings[0], settings[1])
                time.sleep(0.67)
            if buff_enable and buff_enable[0]:
                self.Global_MouseClick(buff_enable[0], buff_enable[1])
                time.sleep(0.67)
        except Exception as e:
            self.error_logging(e, "Error in perform_glitched_enable_buff")

    def open_webhooks_settings(self):
        win = ttk.Toplevel(self.root)
        win.title("Webhooks settings")
        win.geometry("520x360")
        ttk.Label(win,
                  text="Active Webhooks (input your webhook(s) in the small field below and click 'add webhook'):").pack(
            padx=10, pady=5, anchor="w")
        urls_text = ttk.Text(win, height=12)
        urls_text.pack(fill="both", expand=True, padx=10, pady=5)
        urls_text.insert("1.0", "\n".join(self.webhook_urls))
        entry = ttk.Entry(win, width=60)
        entry.pack(padx=10, pady=5)

        def add_url():
            v = entry.get().strip()
            if v:
                current = urls_text.get("1.0", "end").strip()
                new = f"{current}\n{v}" if current else v
                urls_text.delete("1.0", "end")
                urls_text.insert("1.0", new)
                entry.delete(0, "end")

        def save_close():
            lines = [ln.strip() for ln in urls_text.get("1.0", "end").splitlines() if ln.strip()]
            self.webhook_urls = lines
            display = ""
            if self.webhook_urls:
                display = self.webhook_urls[0] if len(
                    self.webhook_urls) == 1 else f"{len(self.webhook_urls)} webhooks configured"
            if hasattr(self, "webhook_display_label"):
                self.webhook_display_label.config(text=display)
            self.save_config()
            win.destroy()

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="Add webhook", command=add_url).pack(side="left")
        ttk.Button(btn_frame, text="Save & Close", command=save_close).pack(side="right")

    def get_webhook_list(self):
        try:
            if hasattr(self, "webhook_urls") and isinstance(self.webhook_urls, list):
                return [u for u in self.webhook_urls if isinstance(u, str) and u.strip()]
            raw = self.config.get("webhook_url", "")
            if isinstance(raw, list):
                return [u for u in raw if isinstance(u, str) and u.strip()]
            if isinstance(raw, str):
                s = raw.strip()
                if not s:
                    return []
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, list):
                        return [u for u in parsed if isinstance(u, str) and u.strip()]
                except Exception:
                    return [s]
            return []
        except Exception:
            return []

    def _make_player_embed(self, kind, name, pid, ts_iso, duration_text=None, join_biome=None, left_biome=None):
        color = 3066993 if kind == "join" else 15158332
        title = "Player Joined" if kind == "join" else "Player Left"
        if kind == "join" and join_biome:
            title = f"Player Joined during {join_biome} biome"
        elif kind == "leave" and left_biome:
            title = f"Player Left during {left_biome} biome"    
        desc = f"**{name}**\n`{pid}`"
        fields = []
        if duration_text:
            fields.append({"name": "Stayed", "value": duration_text, "inline": True})
        if kind == "leave" and join_biome:
            fields.append({"name": "Joined During", "value": f"{join_biome} biome", "inline": True})
        embed = {
            "title": title,
            "description": desc,
            "color": color,
            "timestamp": ts_iso,
            "footer": {"text": "Coteab Macro • Player Logger"},
            "fields": fields
        }
        return embed

    def _send_embeds_to_all(self, embeds):
        urls = self.get_webhook_list()
        if not urls:
            return
        payload = {"embeds": embeds}
        for url in urls:
            try:
                requests.post(url, json=payload, timeout=5)
            except Exception:
                pass

    def create_notice_tab(self, frame):
        txt = ttk.Text(frame, height=14, wrap="word")
        txt.pack(fill="both", expand=True, padx=5, pady=(5, 90))
        notice_url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/noticetabcontents.txt"
        try:
            r = requests.get(notice_url, timeout=10)
            r.raise_for_status()
            content = r.text.strip() or ""
        except Exception:
            content = "Unable to load notice."
        txt.insert("1.0", content)
        txt.config(state="disabled")

        bottom_frame = ttk.Frame(frame)
        bottom_frame.pack(side="bottom", fill="x", padx=5, pady=5)

        discord_link = "https://discord.gg/fw6q274Nrt"
        discord_label = ttk.Label(
            bottom_frame,
            text="JOIN OUR DEVELOPMENT SERVER TO KEEP IN TOUCH WITH THE LATEST 'C'OTEAB MACRO UPDATES, WE OFFER AN ACTIVE COMMUNITY AND MACRO SUPPORT! (CLICK HERE)",
            foreground="royalblue",
            cursor="hand2",
            wraplength=700
        )
        discord_label.configure(font=('Segoe UI', 9, 'underline'))
        discord_label.pack(side="top", fill="x", anchor="w", padx=(0, 10))
        discord_label.bind("<Button-1>", lambda e: webbrowser.open_new(discord_link))

        update_label = ttk.Label(bottom_frame, text="Checking for updates...", wraplength=400, cursor="hand2")
        update_label.pack(side="top", fill="x", anchor="w", padx=5)

        def _open_releases(_=None):
            webbrowser.open_new("https://github.com/xVapure/Noteab-Macro/releases/latest")

        def _check_latest():
            current_version = "v2.0.1"
            try:
                response = requests.get("https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest", timeout=10)
                response.raise_for_status()
                latest_release = response.json()
                latest_version = latest_release.get("tag_name") or latest_release.get("name") or ""
                if latest_version and latest_version != current_version:
                    txt = f"Please update your macro, latest version: {latest_version}. Click here to download!"
                    update_label.config(text=txt, foreground="blue")
                    update_label.bind("<Button-1>", _open_releases)
                else:
                    update_label.config(text="You're on the latest macro release :D", foreground="green")
            except Exception:
                update_label.config(text="Unable to check updates", foreground="red")

        threading.Thread(target=_check_latest, daemon=True).start()

    def create_misc_tab(self, frame):
        hp2_frame = ttk.Frame(frame)
        hp2_frame.pack(pady=10)

        # Auto Pop
        self.auto_pop_glitched_var = ttk.BooleanVar(value=self.config.get("auto_pop_glitched", False))
        auto_pop_glitched_check = ttk.Checkbutton(
            hp2_frame,
            text="Auto Pop (in glitched biome)",
            variable=self.auto_pop_glitched_var,
            command=self.save_config
        )
        auto_pop_glitched_check.grid(row=0, column=0, padx=5, sticky="w")

        # Glitched/Dreamspace biome record keybind
        self.record_rarest_biome_var = ttk.BooleanVar(value=self.config.get("record_rare_biome", False))
        record_rarest_biome_check = ttk.Checkbutton(
            hp2_frame,
            text="Glitched/Dreamspace Biome clip keybind\n(require 1 of 2 recorders: Medal, Xbox Gaming Bar)",
            variable=self.record_rarest_biome_var,
            command=self.save_config
        )
        record_rarest_biome_check.grid(row=1, column=0, padx=5, sticky="w")

        self.rarest_biome_keybind_var = ttk.StringVar(value=self.config.get("rare_biome_record_keybind", "shift + F8"))
        rarest_biome_keybind_entry = ttk.Entry(hp2_frame, textvariable=self.rarest_biome_keybind_var, width=10)
        rarest_biome_keybind_entry.grid(row=1, column=1, pady=5)
        rarest_biome_keybind_entry.bind("<FocusOut>", lambda event: self.save_config())

        # Buff Selections
        buff_selections_button = ttk.Button(
            hp2_frame,
            text="Buff Selections",
            command=self.open_buff_selections_window
        )
        buff_selections_button.grid(row=0, column=1, padx=5)

        # Biome Randomizer
        self.br_var = ttk.BooleanVar(value=self.config.get("biome_randomizer", False))
        br_check = ttk.Checkbutton(
            hp2_frame,
            text="Biome Randomizer (BR)",
            variable=self.br_var,
            command=self.save_config
        )
        br_check.grid(row=2, column=0, padx=5, sticky="w")

        ttk.Label(hp2_frame, text="Usage Duration (minutes):").grid(row=2, column=1, padx=5)
        self.br_duration_var = ttk.StringVar(value=self.config.get("br_duration", "30"))
        br_duration_entry = ttk.Entry(hp2_frame, textvariable=self.br_duration_var, width=10)
        br_duration_entry.grid(row=2, column=2, padx=5)
        br_duration_entry.bind("<FocusOut>", lambda event: self.save_config())

        # Strange Controller
        self.sc_var = ttk.BooleanVar(value=self.config.get("strange_controller", False))
        sc_check = ttk.Checkbutton(
            hp2_frame,
            text="Strange Controller (SC)",
            variable=self.sc_var,
            command=self.save_config
        )
        sc_check.grid(row=3, column=0, padx=5, sticky="w")

        ttk.Label(hp2_frame, text="Usage Duration (minutes):").grid(row=3, column=1, padx=5)
        self.sc_duration_var = ttk.StringVar(value=self.config.get("sc_duration", "15"))
        sc_duration_entry = ttk.Entry(hp2_frame, textvariable=self.sc_duration_var, width=10)
        sc_duration_entry.grid(row=3, column=2, padx=5)
        sc_duration_entry.bind("<FocusOut>", lambda event: self.save_config())

        # Merchant Teleporter
        self.mt_var = ttk.BooleanVar(value=self.config.get("merchant_teleporter", False))
        mt_check = ttk.Checkbutton(
            hp2_frame,
            text="Merchant Teleporter (Auto Merchant)",
            variable=self.mt_var,
            command=self.save_config
        )
        mt_check.grid(row=4, column=0, padx=5, sticky="w")

        ttk.Label(hp2_frame, text="Usage Duration (minutes):").grid(row=4, column=1, padx=5)
        self.mt_duration_var = ttk.StringVar(value=self.config.get("mt_duration", "1"))
        mt_duration_entry = ttk.Entry(hp2_frame, textvariable=self.mt_duration_var, width=10)
        mt_duration_entry.grid(row=4, column=2, padx=5)
        mt_duration_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.auto_merchant_in_limbo_var = ttk.BooleanVar(value=self.config.get("auto_merchant_in_limbo", False))
        self.auto_merchant_in_limbo_check = ttk.Checkbutton(
            hp2_frame,
            text="Auto Merchant in Limbo",
            variable=self.auto_merchant_in_limbo_var,
            command=self.save_config
        )
        def _update_auto_merchant_in_limbo_visibility(*args):
            if self.mt_var.get():
                self.auto_merchant_in_limbo_check.grid(row=5, column=0, padx=5, sticky="w")
            else:
                try:
                    self.auto_merchant_in_limbo_check.grid_remove()
                except Exception:
                    pass
        _update_auto_merchant_in_limbo_visibility()
        try:
            self.mt_var.trace_add('write', _update_auto_merchant_in_limbo_visibility)
        except Exception:
            try:
                self.mt_var.trace('w', _update_auto_merchant_in_limbo_visibility)
            except Exception:
                pass

        # Auto Reconnect
        self.auto_reconnect_var = ttk.BooleanVar(value=self.config.get("auto_reconnect", False))
        auto_reconnect_check = ttk.Checkbutton(
            hp2_frame,
            text="Auto reconnect to your PS (experimental)",
            variable=self.auto_reconnect_var,
            command=self.save_config
        )
        auto_reconnect_check.grid(row=6, column=0, padx=5, sticky="w")
        auto_reconnect_check.bind("<FocusOut>", lambda event: self.save_config())

        reconnect_question_button = ttk.Button(
            hp2_frame,
            text="?",
            command=self.show_reconnect_info
        )
        reconnect_question_button.grid(row=6, column=1, padx=5, sticky="w")

        # Inventory Mouse Click Delay
        ttk.Label(hp2_frame, text="Inventory Mouse Click Delay (milliseconds):").grid(
            row=7, column=0, padx=5, pady=5, sticky="w"
        )
        self.click_delay_var = ttk.StringVar(value=self.config.get("inventory_click_delay", "0"))
        click_delay_entry = ttk.Entry(hp2_frame, textvariable=self.click_delay_var, width=10)
        click_delay_entry.grid(row=7, column=1, padx=5, pady=5, sticky="w")
        click_delay_entry.bind("<FocusOut>", lambda event: self.save_config())

        assign_inventory_button = ttk.Button(
            hp2_frame,
            text="Assign Inventory Click",
            command=self.open_assign_inventory_window
        )
        assign_inventory_button.grid(row=7, column=2, pady=0, sticky="w")

        self.enable_ocr_failsafe_var = ttk.BooleanVar(value=self.config.get("enable_ocr_failsafe", False))
        enable_ocr_failsafe_check = ttk.Checkbutton(
            hp2_frame,
            text="Click me to prevent wrong item usage",
            variable=self.enable_ocr_failsafe_var,
            command=self.toggle_ocr_failsafe
        )
        enable_ocr_failsafe_check.grid(row=8, column=2, padx=5, pady=5, sticky="w")

        self.ocr_cal_btn = ttk.Button(
            hp2_frame,
            text="OCR failsafe calibration (drag ur mouse to first item slot)",
            command=lambda: SnippingWidget(self.root, config_key='first_item_slot_ocr_pos', callback=self._set_first_item_slot_ocr_pos).start()
        )
        self.first_item_slot_ocr_label = ttk.Label(hp2_frame, text=str(self.config.get("first_item_slot_ocr_pos", [0, 0, 80, 80])))

        if self.enable_ocr_failsafe_var.get():
            try:
                self.ocr_cal_btn.grid(row=8, column=0, padx=5, pady=5, sticky="w")
            except Exception:
                pass
            try:
                self.first_item_slot_ocr_label.grid(row=8, column=1, padx=5, sticky="w")
            except Exception:
                pass
        else:
            try:
                self.ocr_cal_btn.grid_forget()
            except Exception:
                pass
            try:
                self.first_item_slot_ocr_label.grid_forget()
            except Exception:
                pass

        self.periodical_aura_var = ttk.BooleanVar(value=self.config.get("periodical_aura_screenshot", False))
        periodical_aura_check = ttk.Checkbutton(
            hp2_frame,
            text="Periodical Aura Screenshot",
            variable=self.periodical_aura_var,
            command=self.save_config
        )
        periodical_aura_check.grid(row=9, column=0, padx=5, pady=5, sticky="w")

        ttk.Label(hp2_frame, text="Interval (minutes):").grid(row=9, column=1, sticky="w", padx=4)
        self.periodical_aura_interval_var = ttk.StringVar(value=str(self.config.get("periodical_aura_interval", "5")))
        periodical_aura_interval_entry = ttk.Entry(hp2_frame, textvariable=self.periodical_aura_interval_var, width=6)
        periodical_aura_interval_entry.grid(row=9, column=2, padx=5, pady=5, sticky="w")
        periodical_aura_interval_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.periodical_inventory_var = ttk.BooleanVar(value=self.config.get("periodical_inventory_screenshot", False))
        periodical_inventory_check = ttk.Checkbutton(
            hp2_frame,
            text="Periodical Inventory Screenshot",
            variable=self.periodical_inventory_var,
            command=self.save_config
        )
        periodical_inventory_check.grid(row=10, column=0, padx=5, pady=5, sticky="w")

        ttk.Label(hp2_frame, text="Inventory Interval (minutes):").grid(row=10, column=1, sticky="w", padx=4)
        self.periodical_inventory_interval_var = ttk.StringVar(value=str(self.config.get("periodical_inventory_interval", "5")))
        periodical_inventory_interval_entry = ttk.Entry(hp2_frame, textvariable=self.periodical_inventory_interval_var, width=6)
        periodical_inventory_interval_entry.grid(row=10, column=2, padx=5, pady=5, sticky="w")
        periodical_inventory_interval_entry.bind("<FocusOut>", lambda event: self.save_config())
        self.auto_claim_quests_var = ttk.BooleanVar(value=self.config.get("auto_claim_daily_quests", False))
        auto_claim_check = ttk.Checkbutton(
            hp2_frame,
            text="Auto claim daily quests",
            variable=self.auto_claim_quests_var,
            command=self.save_config
        )
        auto_claim_check.grid(row=11, column=0, padx=5, pady=5, sticky="w")

        ttk.Label(hp2_frame, text="Claim Interval (minutes):").grid(row=11, column=1, sticky="w", padx=4)
        self.auto_claim_interval_var = ttk.StringVar(value=str(self.config.get("auto_claim_interval", "30")))
        auto_claim_interval_entry = ttk.Entry(hp2_frame, textvariable=self.auto_claim_interval_var, width=6)
        auto_claim_interval_entry.grid(row=11, column=2, padx=5, pady=5, sticky="w")
        auto_claim_interval_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.quest_cal_frame = ttk.LabelFrame(hp2_frame, text="Quest Claim Calibration")
        self.quest_cal_frame.grid(row=12, column=0, columnspan=3, sticky="w", padx=5, pady=6)

        positions = [
            ("Quest Menu (open quests)", "quest_menu"),
            ("Quest 1 button", "quest1_button"),
            ("Quest 2 button", "quest2_button"),
            ("Quest 3 button", "quest3_button"),
            ("Claim Quest button", "claim_quest_button"), 
            ("Quest Reroll button", "quest_reroll_button"),
        ]

        self.quest_coord_vars = {}
        for i, (label_text, config_key) in enumerate(positions):
            lbl = ttk.Label(self.quest_cal_frame, text=f"{label_text} (X, Y):")
            lbl.grid(row=i, column=0, padx=5, pady=3, sticky="w")
            x_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[0])
            y_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[1])
            self.quest_coord_vars[config_key] = (x_var, y_var)
            x_entry = ttk.Entry(self.quest_cal_frame, textvariable=x_var, width=6)
            x_entry.grid(row=i, column=1, padx=5, pady=3)
            y_entry = ttk.Entry(self.quest_cal_frame, textvariable=y_var, width=6)
            y_entry.grid(row=i, column=2, padx=5, pady=3)
            select_btn = ttk.Button(self.quest_cal_frame, text="Assign Click",
                                    command=lambda key=config_key: self.capture_single_click(key))
            select_btn.grid(row=i, column=3, padx=5, pady=3)

        def _update_quest_cal_visibility(*args):
            if self.auto_claim_quests_var.get():
                try:
                    self.quest_cal_frame.grid()
                except Exception:
                    pass
            else:
                try:
                    self.quest_cal_frame.grid_remove()
                except Exception:
                    pass
        self.auto_claim_quests_var.trace_add('write', _update_quest_cal_visibility)
        if not self.auto_claim_quests_var.get():
            try:
                self.quest_cal_frame.grid_remove()
            except Exception:
                pass

    def send_quest_screenshot_webhook(self, screenshot_path):
        try:
            urls = self.get_webhook_list()
            if not urls:
                return
            content = ""
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)
            embed = {
                "description": f"> ## Daily Quests Screenshot",
                "color": 0xffffff,
                "footer": {"text": "Coteab Macro v2.0.1", "icon_url": icon_url},
                "timestamp": current_utc_time
            }
            for webhook_url in urls:
                try:
                    embed_copy = dict(embed)
                    embed_copy["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}
                    with open(screenshot_path, "rb") as image_file:
                        files = {"file": (os.path.basename(screenshot_path), image_file, "image/png")}
                        data = {"payload_json": json.dumps({"content": content, "embeds": [embed_copy]})}
                        requests.post(webhook_url, data=data, files=files, timeout=10)
                except Exception as e:
                    try:
                        print(f"Failed to send quest screenshot to {webhook_url}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            self.error_logging(e, "Error in send_quest_screenshot_webhook")

    def perform_quest_claim_sequence_sync(self):
        try:
            self._action_scheduler.enqueue_action(self._perform_quest_claim_sequence_impl, name="quest_claim", priority=2)
        except Exception:
            try:
                self._perform_quest_claim_sequence_impl()
            except Exception:
                pass

    def _perform_quest_claim_sequence_impl(self):
        try:
            if not getattr(self, "auto_claim_quests_var", None) or not self.auto_claim_quests_var.get():
                return
            if not self.check_roblox_procs():
                return
            self.activate_roblox_window()
            quest_menu = self.config.get("quest_menu", [0, 0])
            quest1 = self.config.get("quest1_button", [0, 0])
            quest2 = self.config.get("quest2_button", [0, 0])
            quest3 = self.config.get("quest3_button", [0, 0])
            claim_btn = self.config.get("claim_quest_button", [0, 0])

            for _ in range(4):
                if not self.detection_running:
                    return
                self.activate_roblox_window()
                time.sleep(0.15)

            if quest_menu and quest_menu[0]:
                try:
                    autoit.mouse_click("left", quest_menu[0], quest_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest_menu[0], quest_menu[1])
                    except Exception:
                        pass
                time.sleep(0.5)

            try:
                os.makedirs("images", exist_ok=True)
                filename = os.path.join("images", f"quest_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_quest_screenshot_webhook(filename)
            except Exception as e:
                self.error_logging(e, "Error taking/sending quest screenshot")

            time.sleep(0.5)

            if quest1 and quest1[0]:
                try:
                    autoit.mouse_click("left", quest1[0], quest1[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest1[0], quest1[1])
                    except Exception:
                        pass
                time.sleep(0.5)
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                time.sleep(0.5)

            if quest2 and quest2[0]:
                try:
                    autoit.mouse_click("left", quest2[0], quest2[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest2[0], quest2[1])
                    except Exception:
                        pass
                time.sleep(0.5)
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                time.sleep(0.5)

            if quest3 and quest3[0]:
                try:
                    autoit.mouse_click("left", quest3[0], quest3[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest3[0], quest3[1])
                    except Exception:
                        pass
                time.sleep(0.5)
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                time.sleep(0.5)
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
            try:
                if inventory_close_button and inventory_close_button[0]:
                    try:
                        autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        except Exception:
                            pass
                    time.sleep(0.3)
            except Exception:
                pass

        except Exception as e:
            self.error_logging(e, "Error in perform_quest_claim_sequence_sync")

    def perform_quest_reroll(self, quest_index):
        try:
            if not getattr(self, "auto_claim_quests_var", None):
                pass
            if not self.check_roblox_procs():
                return
            for _ in range(4):
                if not self.detection_running:
                    return
                self.activate_roblox_window()
                time.sleep(0.15)
            quest_menu = self.config.get("quest_menu", [0, 0])
            quest1 = self.config.get("quest1_button", [0, 0])
            quest2 = self.config.get("quest2_button", [0, 0])
            quest3 = self.config.get("quest3_button", [0, 0])
            reroll_btn = self.config.get("quest_reroll_button", [0, 0])
            if quest_menu and quest_menu[0]:
                try:
                    autoit.mouse_click("left", quest_menu[0], quest_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest_menu[0], quest_menu[1])
                    except Exception:
                        pass
                time.sleep(0.5)
            try:
                qbtn = quest1
                if str(quest_index) == "2":
                    qbtn = quest2
                elif str(quest_index) == "3":
                    qbtn = quest3
                if qbtn and qbtn[0]:
                    try:
                        autoit.mouse_click("left", qbtn[0], qbtn[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(qbtn[0], qbtn[1])
                        except Exception:
                            pass
                    time.sleep(0.4)
                if reroll_btn and reroll_btn[0]:
                    try:
                        autoit.mouse_click("left", reroll_btn[0], reroll_btn[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(reroll_btn[0], reroll_btn[1])
                        except Exception:
                            pass
                    time.sleep(0.45)

                inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                try:
                    if inventory_close_button and inventory_close_button[0]:
                        try:
                            autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                        except Exception:
                            try:
                                self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                            except Exception:
                                pass
                        time.sleep(0.3)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as e:
            try:
                self.error_logging(e, "Error in perform_quest_reroll")
            except Exception:
                pass

    def quest_claim_loop(self):
        last_claim_time = datetime.min
        while self.detection_running:
            try:
                if not getattr(self, "auto_claim_quests_var", None) or not self.auto_claim_quests_var.get():
                    time.sleep(2)
                    continue
                try:
                    interval_min = float(self.auto_claim_interval_var.get())
                except Exception:
                    interval_min = 30.0
                if (datetime.now() - last_claim_time) < timedelta(minutes=interval_min):
                    time.sleep(2)
                    continue
                with self.lock:
                    if not self.detection_running:
                        break
                    self.perform_periodic_aura_screenshot_sync()
                    time.sleep(0.5)
                    self.perform_periodic_inventory_screenshot_sync()
                    time.sleep(0.5)
                    self.perform_quest_claim_sequence_sync()
                    last_claim_time = datetime.now()
            except Exception as e:
                self.error_logging(e, "Error in quest_claim_loop")
            time.sleep(1)

    def create_auras_tab(self, frame):
        self.enable_aura_detection_var = ttk.BooleanVar(value=self.config.get("enable_aura_detection", False))
        enable_aura_detection_check = ttk.Checkbutton(
            frame,
            text="Enable Aura Detection",
            variable=self.enable_aura_detection_var,
            command=self.save_config
        )
        enable_aura_detection_check.pack(anchor="w", padx=5, pady=5)

        aura_frame = ttk.LabelFrame(frame, text="Aura Detection")
        aura_frame.pack(fill='x', padx=5, pady=5)

        # Discord UserID (Aura Ping)
        ttk.Label(aura_frame, text="Discord UserID (Aura Ping):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.aura_user_id_var = ttk.StringVar(value=self.config.get("aura_user_id", ""))
        aura_id_entry = ttk.Entry(aura_frame, textvariable=self.aura_user_id_var, width=25)
        aura_id_entry.grid(row=1, column=1, padx=5, pady=5)
        aura_id_entry.bind("<FocusOut>", lambda event: self.save_config())

        # Ping Minimum
        ttk.Label(aura_frame, text="Aura Ping Minimum:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.ping_minimum_var = ttk.StringVar(value=self.config.get("ping_minimum", "100000"))
        ping_minimum_entry = ttk.Entry(aura_frame, textvariable=self.ping_minimum_var, width=25)
        ping_minimum_entry.grid(row=3, column=1, padx=5, pady=5)
        ping_minimum_entry.bind("<FocusOut>", lambda event: self.save_config())

        # aura rec bool
        self.enable_aura_record_var = ttk.BooleanVar(value=self.config.get("enable_aura_record", False))
        enable_aura_record_check = ttk.Checkbutton(
            aura_frame,
            text="Aura Clipping Keybind\n(require 1 of 2 recorders: Medal, Xbox Gaming Bar)",
            variable=self.enable_aura_record_var,
            command=self.save_config
        )
        enable_aura_record_check.grid(row=4, column=0, sticky="w", padx=5, pady=5)

        # Aura rec keybind
        self.aura_record_keybind_var = ttk.StringVar(value=self.config.get("aura_record_keybind", "shift + F8"))
        aura_record_keybind_entry = ttk.Entry(aura_frame, textvariable=self.aura_record_keybind_var, width=25)
        aura_record_keybind_entry.grid(row=4, column=1, padx=5, pady=5)
        aura_record_keybind_entry.bind("<FocusOut>", lambda event: self.save_config())

        # Aura rec minimum
        ttk.Label(aura_frame, text="Aura minimum rarity to record:").grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self.aura_record_minimum_var = ttk.StringVar(value=self.config.get("aura_record_minimum", "500000"))
        aura_record_minimum_entry = ttk.Entry(aura_frame, textvariable=self.aura_record_minimum_var, width=25)
        aura_record_minimum_entry.grid(row=5, column=1, padx=5, pady=5)
        aura_record_minimum_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.aura_screenshot_var = ttk.BooleanVar(value=self.config.get("aura_detection_screenshot", False))
        enable_aura_screenshot_check = ttk.Checkbutton(
            aura_frame,
            text="Screenshot for aura detections (only works when Roblox is focused)",
            variable=self.aura_screenshot_var,
            command=self.save_config
        )
        enable_aura_screenshot_check.grid(row=6, column=0, columnspan=2, sticky="w", padx=5, pady=5)

    def create_potion_craft_tab(self, frame):
        potions_directory = "crafting_files_do_not_open"
        os.makedirs(potions_directory, exist_ok=True)
        frame_label = ttk.LabelFrame(frame, text="Auto Potion Crafting")
        frame_label.pack(fill='both', expand=True, padx=5, pady=5)
        top_row = ttk.Frame(frame_label)
        top_row.pack(fill="x", pady=(6, 8), padx=6)
        self.enable_potion_crafting_var = ttk.BooleanVar(value=self.config.get("enable_potion_crafting", False))
        enable_cb = ttk.Checkbutton(top_row, text="Enable potion crafting", variable=self.enable_potion_crafting_var,
                                    command=self.save_config)
        enable_cb.pack(side="left", padx=(0, 12))
        calib_frame = ttk.Frame(frame_label)
        calib_frame.pack(fill="x", padx=6, pady=(0, 8))

        ttk.Label(calib_frame, text="Calibrate:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        ttk.Label(calib_frame, text="Calibrate:").grid(row=0, column=0, padx=4, pady=4, sticky="w")
        ttk.Label(calib_frame, text="Potion menu search bar(X,Y):").grid(row=0, column=1, padx=4, pady=4, sticky="e")
        self.potion_search_x = ttk.IntVar(value=self.config.get("potion_search_bar1", [0, 0])[0])
        self.potion_search_y = ttk.IntVar(value=self.config.get("potion_search_bar1", [0, 0])[1])
        ttk.Entry(calib_frame, textvariable=self.potion_search_x, width=6).grid(row=0, column=2, padx=4, pady=4)
        ttk.Entry(calib_frame, textvariable=self.potion_search_y, width=6).grid(row=0, column=3, padx=4, pady=4)
        ttk.Button(calib_frame, text="Assign", command=lambda k="potion_search_bar1": self.capture_single_click(k)).grid(row=0, column=4, padx=6)

        btn1_text = ttk.Label(calib_frame, text="Potion first slot (X,Y):")
        btn1_text.grid(row=1, column=1, padx=4, pady=4, sticky="e")
        self.potion_button1_x = ttk.IntVar(value=self.config.get("potion_button1", [0, 0])[0])
        self.potion_button1_y = ttk.IntVar(value=self.config.get("potion_button1", [0, 0])[1])
        ttk.Entry(calib_frame, textvariable=self.potion_button1_x, width=6).grid(row=1, column=2, padx=4, pady=4)
        ttk.Entry(calib_frame, textvariable=self.potion_button1_y, width=6).grid(row=1, column=3, padx=4, pady=4)
        ttk.Button(calib_frame, text="Assign", command=lambda k="potion_button1": self.capture_single_click(k)).grid(row=1, column=4, padx=6)

        ttk.Label(calib_frame, text="Auto add button (X,Y):").grid(row=2, column=1, padx=4, pady=4, sticky="e")
        self.potion_button2_x = ttk.IntVar(value=self.config.get("potion_button2", [0, 0])[0])
        self.potion_button2_y = ttk.IntVar(value=self.config.get("potion_button2", [0, 0])[1])
        ttk.Entry(calib_frame, textvariable=self.potion_button2_x, width=6).grid(row=2, column=2, padx=4, pady=4)
        ttk.Entry(calib_frame, textvariable=self.potion_button2_y, width=6).grid(row=2, column=3, padx=4, pady=4)
        ttk.Button(calib_frame, text="Assign", command=lambda k="potion_button2": self.capture_single_click(k)).grid(row=2, column=4, padx=6)
        ttk.Button(calib_frame, text="Assign", command=lambda k="potion_button2": self.capture_single_click(k)).grid(row=2, column=4, padx=6)

        file_frame = ttk.Frame(frame_label)
        file_frame.pack(fill="x", padx=6, pady=(6, 8))
        ttk.Label(file_frame, text="Select potion macro file:").pack(side="left")
        self.potion_file_var = ttk.StringVar(value=self.config.get("potion_last_file", ""))
        self.potion_combo = ttk.Combobox(file_frame, textvariable=self.potion_file_var, state="readonly", width=40)
        self.potion_combo.pack(side="left", padx=(6, 6))
        ttk.Button(file_frame, text="Refresh", command=lambda: self._refresh_potion_files(potions_directory)).pack(side="left", padx=(0,6))

        rec_frame = ttk.Frame(frame_label)
        rec_frame.pack(fill="x", padx=6, pady=(0, 8))
        self.potion_mode_var = ttk.StringVar(value="Idle")
        self.potion_rec_status = ttk.StringVar(value="Ready")
        ttk.Label(rec_frame, textvariable=self.potion_rec_status).pack(side="left", padx=(0,12))

        self.potion_start_rec_btn = ttk.Button(rec_frame, text="Start Recording (F3)", command=self._potion_handle_f1)
        self.potion_stop_rec_btn  = ttk.Button(rec_frame, text="Stop Recording & Save (F4)", command=self._potion_handle_f3)
        self.potion_start_rec_btn.pack(side="left", padx=(0,6))
        self.potion_stop_rec_btn.pack(side="left")
        self._refresh_potion_files(potions_directory)
        keyboard.add_hotkey('f3', lambda: self._potion_handle_f1(), suppress=False)
        keyboard.add_hotkey('f4', lambda: self._potion_handle_f3(), suppress=False)
        switch_frame = ttk.Frame(frame_label)
        switch_frame.pack(fill="x", padx=6, pady=(4,8))

        self.enable_potion_switching_var = ttk.BooleanVar(value=self.config.get("enable_potion_switching", False))
        enable_switch_cb = ttk.Checkbutton(switch_frame, text="Enable potion switching", variable=self.enable_potion_switching_var, command=self.save_config)
        enable_switch_cb.grid(row=0, column=0, sticky="w", padx=(0,6))

        ttk.Label(switch_frame, text="Switch interval (seconds):").grid(row=0, column=1, sticky="e", padx=6)
        self.potion_switch_interval_var = ttk.StringVar(value=str(self.config.get("potion_switch_interval", "60")))
        interval_entry = ttk.Entry(switch_frame, textvariable=self.potion_switch_interval_var, width=8)
        interval_entry.grid(row=0, column=2, padx=4)
        interval_entry.bind("<FocusOut>", lambda e: self.save_config())

        ttk.Label(switch_frame, text="Select potion #2:").grid(row=1, column=0, sticky="w", padx=4, pady=(6,0))
        self.potion2_var = ttk.StringVar(value=self.config.get("potion_file2", ""))
        self.potion2_combo = ttk.Combobox(switch_frame, textvariable=self.potion2_var, state="readonly", width=36)
        self.potion2_combo.grid(row=1, column=1, columnspan=2, sticky="w", padx=6, pady=(6,0))
        self.potion2_combo.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        ttk.Label(switch_frame, text="Select potion #3:").grid(row=2, column=0, sticky="w", padx=4, pady=(6,0))
        self.potion3_var = ttk.StringVar(value=self.config.get("potion_file3", ""))
        self.potion3_combo = ttk.Combobox(switch_frame, textvariable=self.potion3_var, state="readonly", width=36)
        self.potion3_combo.grid(row=2, column=1, columnspan=2, sticky="w", padx=6, pady=(6,0))
        self.potion3_combo.bind("<<ComboboxSelected>>", lambda e: self.save_config())
        self._refresh_potion_files(potions_directory)

    def _refresh_potion_files(self, potions_directory="crafting_files_do_not_open"):
        try:
            os.makedirs(potions_directory, exist_ok=True)
            files = sorted([f for f in os.listdir(potions_directory) if f.lower().endswith(".json")])
            try:
                values_with_none = ["None"] + files

                # main potion combo
                if hasattr(self, "potion_combo"):
                    self.potion_combo["values"] = values_with_none
                    cfg_main = self.config.get("potion_last_file", "")
                    if cfg_main and cfg_main in files:
                        self.potion_file_var.set(cfg_main)
                    else:
                        if not self.potion_file_var.get() or self.potion_file_var.get() not in values_with_none:
                            self.potion_file_var.set(files[0] if files else "None")
                if hasattr(self, "potion2_combo"):
                    self.potion2_combo["values"] = values_with_none
                    cfg2 = self.config.get("potion_file2", "")
                    if cfg2 and cfg2 in files:
                        self.potion2_var.set(cfg2)
                    else:
                        if not self.potion2_var.get() or self.potion2_var.get() not in values_with_none:
                            self.potion2_var.set("None")
                if hasattr(self, "potion3_combo"):
                    self.potion3_combo["values"] = values_with_none
                    cfg3 = self.config.get("potion_file3", "")
                    if cfg3 and cfg3 in files:
                        self.potion3_var.set(cfg3)
                    else:
                        if not self.potion3_var.get() or self.potion3_var.get() not in values_with_none:
                            self.potion3_var.set("None")
            except Exception:
                pass
            if self.potion_file_var.get() and self.potion_file_var.get() != "None":
                self.config["potion_last_file"] = self.potion_file_var.get()
                self.save_config()
        except Exception as e:
            self.error_logging(e, "Error refreshing potion files")

    def _potion_handle_f1(self):
        if getattr(self, "potion_mode_var", None) and self.potion_mode_var.get() == "Idle":
            self._potion_start_recording()
        else:
            pass

    def _potion_handle_f3(self):
        if getattr(self, "potion_mode_var", None) and self.potion_mode_var.get() == "Recording":
            self._potion_stop_recording()

    def _potion_start_recording(self):
        try:
            if getattr(self, "potion_mode_var", None) and self.potion_mode_var.get() != "Idle":
                return
            self.potion_mode_var.set("Recording")
            self.potion_rec_status.set("Recording.")
            self.potion_rec_events = []
            self.potion_rec_start = time.perf_counter()
            self.potion_last_move_time = 0.0
            self.potion_last_move_pos = (None, None)

            def kcb(e):
                if e.name in ("f3", "f4"):
                    return
                et = time.perf_counter() - self.potion_rec_start
                typ = "key_down" if e.event_type == "down" else "key_up"
                self.potion_rec_events.append({"t": et, "type": typ, "key": e.name})

            def mcb(e):
                et = time.perf_counter() - self.potion_rec_start
                if isinstance(e, mouse.MoveEvent):
                    x, y = int(e.x), int(e.y)
                    lt = self.potion_last_move_time
                    lx, ly = self.potion_last_move_pos
                    record = False
                    if lx is None:
                        record = True
                    elif et - lt >= 0.008:
                        record = True
                    else:
                        dx = x - lx
                        dy = y - ly
                        if dx*dx + dy*dy >= 4:
                            record = True
                    if record:
                        self.potion_rec_events.append({"t": et, "type": "mouse_move", "x": x, "y": y})
                        self.potion_last_move_time = et
                        self.potion_last_move_pos = (x, y)
                elif isinstance(e, mouse.ButtonEvent):
                    pos = mouse.get_position()
                    typ = "mouse_down" if e.event_type == "down" else "mouse_up"
                    self.potion_rec_events.append({"t": et, "type": typ, "button": e.button, "x": int(pos[0]), "y": int(pos[1])})
                elif isinstance(e, mouse.WheelEvent):
                    self.potion_rec_events.append({"t": et, "type": "mouse_wheel", "delta": int(e.delta)})

            self._potion_kbd_hook = kcb
            self._potion_mouse_hook = mcb
            keyboard.hook(self._potion_kbd_hook)
            mouse.hook(self._potion_mouse_hook)
        except Exception as e:
            self.error_logging(e, "Error starting potion recording")

    def _potion_stop_recording(self):
        try:
            if getattr(self, "_potion_kbd_hook", None):
                try:
                    keyboard.unhook(self._potion_kbd_hook)
                except Exception:
                    pass
            if getattr(self, "_potion_mouse_hook", None):
                try:
                    mouse.unhook(self._potion_mouse_hook)
                except Exception:
                    pass
        except Exception:
            pass

        self._potion_kbd_hook = None
        self._potion_mouse_hook = None
        try:
            self.potion_mode_var.set("Idle")
        except Exception:
            pass
        try:
            self.potion_rec_status.set("Stopped. Saving.")
        except Exception:
            pass

        pot_dir = "crafting_files_do_not_open"
        try:
            os.makedirs(pot_dir, exist_ok=True)
        except Exception:
            pass
        pot_dir = "crafting_files_do_not_open"
        os.makedirs(pot_dir, exist_ok=True)

        try:
            initialfile = self.config.get("potion_last_file", "")
            if not initialfile:
                initialfile = "potion_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"

            save_path = filedialog.asksaveasfilename(
                title="Save Potion Macro",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
                initialdir=os.path.abspath(pot_dir),
                initialfile=initialfile
            )
        except Exception:
            save_path = ""
        if not save_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"potion_{ts}.json"
            final_path = os.path.join(pot_dir, filename)
        else:
            if os.path.isdir(save_path) or os.path.basename(save_path) == "":
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"potion_{ts}.json"
                final_path = os.path.join(pot_dir, filename)
            else:
                final_path = save_path
                filename = os.path.basename(final_path)

        try:
            if os.path.exists(final_path):
                i = 1
                while True:
                    candidate = f"{base}({i}).json"
                    candidate_path = os.path.join(pot_dir, candidate)
                    if not os.path.exists(candidate_path):
                        final_path = candidate_path
                        filename = candidate
                        break
                    i += 1
        except Exception:
            pass

        data = {
            "created": time.time(),
            "screen": {"w": getattr(self.root, "winfo_screenwidth", lambda: 0)(), "h": getattr(self.root, "winfo_screenheight", lambda: 0)()},
            "events": sorted(getattr(self, "potion_rec_events", []), key=lambda ev: ev.get("t", 0.0))
        }

        try:
            tmp = final_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                f.write("\n")
            os.replace(tmp, final_path)
            try:
                self._refresh_potion_files(pot_dir)
            except Exception:
                pass
            try:
                if hasattr(self, "potion_file_var"):
                    self.potion_file_var.set(os.path.basename(final_path))
            except Exception:
                pass
            try:
                self.config["potion_last_file"] = os.path.basename(final_path)
                self.save_config()
            except Exception:
                pass
            try:
                messagebox.showinfo("Potion Recorder", f"Saved: {os.path.basename(final_path)}")
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror("Potion Recorder", f"Failed to save:\n{e}")
            except Exception:
                pass

        try:
            self.potion_rec_events = []
        except Exception:
            self.potion_rec_events = []
        try:
            self.potion_rec_status.set("Ready")
        except Exception:
            pass

    def _potion_thread_launcher(self, file_name, potions_directory="crafting_files_do_not_open", stop_after=None):
        try:
            path = os.path.join(potions_directory, file_name)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.error_logging(e, "Failed to start potion loop")
            return

        events = data.get("events", [])
        if not events:
            return
        events.sort(key=lambda ev: ev.get("t", 0.0))

        potion_b1 = self.config.get("potion_button1", [0, 0])
        potion_search = self.config.get("potion_search_bar1", [0, 0])
        potion_b2 = self.config.get("potion_button2", [0, 0])
        potion_name = os.path.splitext(file_name)[0]

        try:
            def _click(xy, label="click", tries=3, pause_after=0.12):
                if not xy or not xy[0]:
                    return False
                x, y = xy[0], xy[1]
                last_exc = None
                for _ in range(tries):
                    try:
                        self.Global_MouseClick(x, y)
                        time.sleep(pause_after)
                        return True
                    except Exception as exc:
                        last_exc = exc
                        time.sleep(0.05)
                raise last_exc or RuntimeError(f"{label} failed at {x},{y}")

            pname = (potion_name or "").strip()
            if pname == "":
                self.error_logging(ValueError("Empty potion name"), "Potion setup: empty potion_name")
                return

            if potion_search and potion_search[0]:
                _click(potion_search, label="search_bar", tries=3, pause_after=0.18)
                time.sleep(0.08)
                autoit.send(pname)
                time.sleep(0.18)
            else:
                self.error_logging(RuntimeError("Missing potion_search coordinates"), "Potion setup warning")

            if potion_b1 and potion_b1[0]:
                _click(potion_b1, label="button1", tries=3, pause_after=0.28)
            else:
                self.error_logging(RuntimeError("Missing potion_b1 coordinates"), "Potion setup warning")

            if potion_b2 and potion_b2[0]:
                _click(potion_b2, label="button2", tries=3, pause_after=0.36)
            else:
                self.error_logging(RuntimeError("Missing potion_b2 coordinates"), "Potion setup warning")

        except Exception as e:
            self.error_logging(e, "Potion setup clicks failed")
            return

        start_time = time.perf_counter()
        while self.detection_running and self.enable_potion_crafting_var.get():
            if stop_after is not None:
                if time.perf_counter() - start_time >= float(stop_after):
                    break
            last_t = 0.0
            for ev in events:
                if not self.detection_running or not self.enable_potion_crafting_var.get():
                    break
                if stop_after is not None:
                    if time.perf_counter() - start_time >= float(stop_after):
                        break
                t = float(ev.get("t", 0.0))
                dt = t - last_t
                if dt > 0:
                    end = time.perf_counter() + dt
                    while True:
                        if not self.detection_running or not self.enable_potion_crafting_var.get():
                            break
                        if stop_after is not None and time.perf_counter() - start_time >= float(stop_after):
                            break
                        rem = end - time.perf_counter()
                        if rem <= 0:
                            break
                        time.sleep(min(rem, 0.01))
                typ = ev.get("type")
                try:
                    if typ == "mouse_move":
                        autoit.mouse_move(int(ev["x"]), int(ev["y"]), 0)
                    elif typ == "mouse_down":
                        b = ev.get("button", "left")
                        autoit.mouse_down(b)
                    elif typ == "mouse_up":
                        b = ev.get("button", "left")
                        autoit.mouse_up(b)
                    elif typ == "mouse_wheel":
                        delta = int(ev.get("delta", 0))
                        if delta != 0:
                            mouse.wheel(delta)
                    elif typ == "key_down":
                        k = ev.get("key")
                        if k not in ("f3", "f4"):
                            keyboard.press(k)
                    elif typ == "key_up":
                        k = ev.get("key")
                        if k not in ("f3", "f4"):
                            keyboard.release(k)
                except Exception:
                    pass
                last_t = t
            if stop_after is not None:
                if time.perf_counter() - start_time >= float(stop_after):
                    break
            time.sleep(0.25)

    def start_potion_crafting(self):
        try:
            if not getattr(self, "detection_running", False):
                return
            if not getattr(self, "enable_potion_crafting_var", None) or not self.enable_potion_crafting_var.get():
                return

            if getattr(self, "enable_potion_switching_var", None) and self.enable_potion_switching_var.get():
                def switcher():
                    try:
                        while self.detection_running and self.enable_potion_crafting_var.get() and self.enable_potion_switching_var.get():
                            interval = float(self.potion_switch_interval_var.get() or "60")

                            f1_raw = (self.potion_file_var.get().strip() or self.config.get("potion_last_file", ""))
                            f2_raw = (self.potion2_var.get().strip() or self.config.get("potion_file2", ""))
                            f3_raw = (self.potion3_var.get().strip() or self.config.get("potion_file3", ""))

                            # treat explicit "None" (case-insensitive) as disabled
                            def normalize(v):
                                if not v: return ""
                                return "" if str(v).strip().lower() == "none" else v

                            order = []
                            for v in (f1_raw, f2_raw, f3_raw):
                                nv = normalize(v)
                                if nv:
                                    order.append(nv)

                            if not order:
                                # nothing to run
                                time.sleep(0.5)
                                continue

                            idx = 0
                            while self.detection_running and self.enable_potion_crafting_var.get() and self.enable_potion_switching_var.get():
                                current_file = order[idx % len(order)]
                                if not current_file:
                                    break
                                t = threading.Thread(target=self._potion_thread_launcher, args=(current_file, "crafting_files_do_not_open", interval), daemon=True)
                                t.start()
                                t.join()
                                idx += 1
                    except Exception as e:
                        self.error_logging(e, "Error in potion switcher")
                t = threading.Thread(target=switcher, daemon=True)
                t.start()
                self.potion_run_status.set(f"Switching mode enabled")
            else:
                file_name = self.potion_file_var.get().strip() or self.config.get("potion_last_file", "")
                if file_name.lower() == "none" or not file_name:
                    return
                t = threading.Thread(target=self._potion_thread_launcher, args=(file_name,), daemon=True)
                t.start()
                self.potion_run_status.set(f"Looping: {file_name}")
                self.config["potion_last_file"] = file_name
                self.save_config()
        except Exception as e:
            self.error_logging(e, "Error launching potion loop")
    
    def create_merchant_tab(self, frame):
        mari_frame = ttk.LabelFrame(frame, text="Mari")
        mari_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        mari_button = ttk.Button(mari_frame, text="Mari Item Settings", command=self.open_mari_settings)
        mari_button.pack(padx=3, pady=3)

        jester_frame = ttk.LabelFrame(frame, text="Jester")
        jester_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        jester_button = ttk.Button(jester_frame, text="Jester Item Settings", command=self.open_jester_settings)
        jester_button.pack(padx=3, pady=3)

        calibration_button = ttk.Button(frame, text="Merchant Calibrations",
                                        command=self.open_merchant_calibration_window)
        calibration_button.grid(row=1, column=0, padx=5, pady=3, sticky="w")

        ttk.Label(frame,
                  text="Merchant item extra slot\n(extra slot if your mouse missed/cannot reach to merchant's 5th slot):").grid(
            row=2, column=0, padx=5, sticky="w")
        self.merchant_extra_slot_var = ttk.StringVar(value=self.config.get("merchant_extra_slot", "0"))
        merchant_extra_slot_entry = ttk.Entry(frame, textvariable=self.merchant_extra_slot_var, width=15)
        merchant_extra_slot_entry.grid(row=2, column=1, padx=0, pady=3, sticky="w")
        merchant_extra_slot_entry.bind("<FocusOut>", lambda event: self.save_config())

        # Ping Mari
        self.ping_mari_var = ttk.BooleanVar(value=self.config.get("ping_mari", False))
        ping_mari_check = ttk.Checkbutton(
            frame, text="Ping if Mari found? (Custom Ping UserID/RoleID: &roleid)",
            variable=self.ping_mari_var, command=self.save_config)
        ping_mari_check.grid(row=3, column=0, padx=5, pady=3, sticky="w")

        self.mari_user_id_var = ttk.StringVar(value=self.config.get("mari_user_id", ""))
        mari_user_id_entry = ttk.Entry(frame, textvariable=self.mari_user_id_var, width=15)
        mari_user_id_entry.grid(row=3, column=1, padx=0, pady=3, sticky="w")
        mari_user_id_entry.bind("<FocusOut>", lambda event: self.save_config())

        mari_label = ttk.Label(frame, text="")
        mari_label.grid(row=3, column=2, padx=5, pady=3, sticky="w")

        # Ping Jester
        self.ping_jester_var = ttk.BooleanVar(value=self.config.get("ping_jester", False))
        ping_jester_check = ttk.Checkbutton(
            frame, text="Ping if Jester found? (Custom Ping UserID/RoleID: &roleid)",
            variable=self.ping_jester_var, command=self.save_config)
        ping_jester_check.grid(row=4, column=0, padx=5, pady=3, sticky="w")

        self.jester_user_id_var = ttk.StringVar(value=self.config.get("jester_user_id", ""))
        self.detect_merchant_no_mt_var = ttk.BooleanVar(value=self.config.get("detect_merchant_no_mt", True))
        jester_user_id_entry = ttk.Entry(frame, textvariable=self.jester_user_id_var, width=15)
        jester_user_id_entry.grid(row=4, column=1, padx=0, pady=3, sticky="w")
        jester_user_id_entry.bind("<FocusOut>", lambda event: self.save_config())

        merchant_no_mt_check = ttk.Checkbutton(
            frame, text="Merchant detection without Merchant Teleporter gamepass.",
            variable=self.detect_merchant_no_mt_var, command=self.save_config
        )
        merchant_no_mt_check.grid(row=6, column=0, padx=5, pady=3, sticky="w")

        jester_label = ttk.Label(frame, text="")
        jester_label.grid(row=4, column=2, padx=5, pady=3, sticky="w")

        # Required Package Frame
        package_frame = ttk.LabelFrame(frame, text="Required Package For Auto Merchant")
        package_frame.grid(row=5, column=0, padx=5, pady=5, sticky="nsew")

        # Tesseract OCR Status
        ocr_status = self.check_tesseract_ocr()
        ocr_status_text = "Tesseract OCR Installed: Yes" if ocr_status else "Tesseract OCR Installed: No, click here to get OCR module"
        ocr_status_label = ttk.Label(package_frame, text=ocr_status_text, foreground="light blue", cursor="hand2")
        ocr_status_label.pack(anchor="w", padx=5, pady=3)
        if not ocr_status:
            ocr_status_label.bind("<Button-1>", lambda e: self.download_tesseract())

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, weight=1)

    def check_tesseract_ocr(self):
        tesseract_env_path = os.getenv('TESSERACT_PATH')
        if tesseract_env_path and os.path.exists(tesseract_env_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_env_path
            return True

        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            os.path.join(os.getenv('LOCALAPPDATA'), 'Programs', 'Tesseract-OCR', 'tesseract.exe'),
            os.path.join(os.getenv('LOCALAPPDATA'), 'Tesseract-OCR', 'tesseract.exe')
        ]

        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return True

        return False

    def download_tesseract(self):
        download_url = "https://github.com/tesseract-ocr/tesseract/releases/download/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe"
        try:
            exe_filename = os.path.basename(download_url)
            save_path = filedialog.asksaveasfilename(defaultextension=".exe", initialfile=exe_filename, title="Save As")

            if not save_path:
                messagebox.showwarning("Download Cancelled", "No file path selected. Download cancelled.")
                return

            response = requests.get(download_url)
            response.raise_for_status()

            with open(save_path, 'wb') as file:
                file.write(response.content)

            messagebox.showinfo("Download Complete",
                                f"Tesseract installer has been downloaded as {save_path}. Please run the installer to complete the setup. \n \n After installed tesseract, restart the macro to let it check if your ocr module is ready!")
        except requests.RequestException as e:
            messagebox.showerror("Download Failed", f"Failed to download Tesseract: {e}")
        except IOError as e:
            messagebox.showerror("File Error", f"Failed to save the file: {e}")

    def open_merchant_calibration_window(self):
        calibration_window = ttk.Toplevel(self.root)
        calibration_window.title("Merchant Calibration")
        calibration_window.geometry("765x345")

        positions = [
            ("Merchant Open Button", "merchant_open_button"),
            ("Merchant Dialogue Box", "merchant_dialogue_box"),
            ("Purchase Amount Button", "purchase_amount_button"),
            ("Purchase Button", "purchase_button"),
            ("First Item Slot Position", "first_item_slot_pos"),
            ("Merchant Name OCR Position", "merchant_name_ocr_pos"),
            ("Item Name OCR Position", "item_name_ocr_pos")
        ]

        self.coord_vars = {}

        for i, (label_text, config_key) in enumerate(positions):
            if "ocr" in config_key:
                label = ttk.Label(calibration_window, text=f"{label_text} (X, Y, W, H):")
                label.grid(row=i, column=0, padx=5, pady=5, sticky="w")

                x_var = ttk.IntVar(value=self.config.get(config_key, [0, 0, 0, 0])[0])
                y_var = ttk.IntVar(value=self.config.get(config_key, [0, 0, 0, 0])[1])
                w_var = ttk.IntVar(value=self.config.get(config_key, [0, 0, 0, 0])[2])
                h_var = ttk.IntVar(value=self.config.get(config_key, [0, 0, 0, 0])[3])
                self.coord_vars[config_key] = (x_var, y_var, w_var, h_var)

                ttk.Entry(calibration_window, textvariable=x_var, width=6).grid(row=i, column=1, padx=5, pady=5)
                ttk.Entry(calibration_window, textvariable=y_var, width=6).grid(row=i, column=2, padx=5, pady=5)
                ttk.Entry(calibration_window, textvariable=w_var, width=6).grid(row=i, column=3, padx=5, pady=5)
                ttk.Entry(calibration_window, textvariable=h_var, width=6).grid(row=i, column=4, padx=5, pady=5)

                select_button = ttk.Button(
                    calibration_window, text="Select Region (drag your mouse to select it)",
                    command=lambda key=config_key: self.merchant_snipping(key)
                )
            else:
                label = ttk.Label(calibration_window, text=f"{label_text} (X, Y):")
                label.grid(row=i, column=0, padx=5, pady=5, sticky="w")

                x_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[0])
                y_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[1])
                self.coord_vars[config_key] = (x_var, y_var)

                ttk.Entry(calibration_window, textvariable=x_var, width=6).grid(row=i, column=1, padx=5, pady=5)
                ttk.Entry(calibration_window, textvariable=y_var, width=6).grid(row=i, column=2, padx=5, pady=5)

                select_button = ttk.Button(
                    calibration_window, text="Select Pos",
                    command=lambda key=config_key: self.start_capture_thread(key, self.coord_vars)
                )

            select_button.grid(row=i, column=5, padx=5, pady=5)

        save_button = ttk.Button(calibration_window, text="Save Calibration",
                                 command=lambda: self.save_merchant_coordinates(calibration_window))
        save_button.grid(row=len(positions), column=0, columnspan=6, pady=10)

    def merchant_snipping(self, config_key):
        def on_region_selected(region):
            x, y, w, h = region
            x_var, y_var, w_var, h_var = self.coord_vars[config_key]
            x_var.set(x)
            y_var.set(y)
            w_var.set(w)
            h_var.set(h)

        snipping_tool = SnippingWidget(self.root, config_key=config_key, callback=on_region_selected)
        snipping_tool.start()

    def save_merchant_coordinates(self, calibration_window):
        for config_key, vars in self.coord_vars.items():
            if len(vars) == 4:
                self.config[config_key] = [var.get() for var in vars]
            else:
                self.config[config_key] = [vars[0].get(), vars[1].get()]
        self.save_config()
        calibration_window.destroy()

    def open_mari_settings(self):
        mari_window = ttk.Toplevel(self.root)
        mari_window.title("Mari Items")

        items = [
            "Void Coin", "Lucky Penny", "Mixed Potion", "Lucky Potion",
            "Lucky Potion L", "Lucky Potion XL", "Speed Potion",
            "Speed Potion L", "Speed Potion XL", "Gear A", "Gear B"
        ]

        item_frame = ttk.Frame(mari_window)
        item_frame.pack(padx=10, pady=10, fill='x')
        ttk.Label(item_frame, text="Item Name").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(item_frame, text="Amount").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(item_frame, text="Rebuy").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.mari_items_vars = {}
        self.mari_items_amounts = {}
        self.mari_items_rebuy = {}
        saved_mari_items = self.config.get("Mari_Items", {})

        for i, item in enumerate(items, start=1):
            saved_data = saved_mari_items.get(item, [False, 1, False])
            var = ttk.BooleanVar(value=saved_data[0])
            self.mari_items_vars[item] = var
            ttk.Checkbutton(item_frame, text=item, variable=var).grid(row=i, column=0, sticky="w", padx=5, pady=2)

            amount_var = ttk.StringVar(value=str(saved_data[1]))
            self.mari_items_amounts[item] = amount_var
            ttk.Entry(item_frame, textvariable=amount_var, width=5).grid(row=i, column=1, padx=5, pady=2)

            rebuy_var = ttk.BooleanVar(value=saved_data[2] if len(saved_data) > 2 else False)
            self.mari_items_rebuy[item] = rebuy_var
            ttk.Checkbutton(item_frame, variable=rebuy_var).grid(row=i, column=2, sticky="w", padx=5, pady=2)

        save_button = ttk.Button(mari_window, text="Save Selections",
                                 command=lambda: self.save_mari_selections(mari_window))
        save_button.pack(pady=10)

    def save_mari_selections(self, mari_window):
        mari_items = {
            item: [var.get(), int(self.mari_items_amounts[item].get()), self.mari_items_rebuy[item].get()]
            for item, var in self.mari_items_vars.items()
        }
        self.config["Mari_Items"] = mari_items
        self.save_config()
        mari_window.destroy()

    def open_jester_settings(self):
        jester_window = ttk.Toplevel(self.root)
        jester_window.title("Jester Items")

        items = [
            "Oblivion Potion", "Potion of bound", "Heavenly Potion", "Rune of Everything", "Rune of Dust",
            "Rune of Nothing", "Rune Of Corruption", "Rune Of Hell", "Rune of Galaxy",
            "Rune of Rainstorm", "Rune of Frost", "Rune of Wind", "Strange Potion", "Lucky Potion",
            "Stella's Candle", "Merchant Tracker", "Random Potion Sack", "Speed Potion"
        ]

        item_frame = ttk.Frame(jester_window)
        item_frame.pack(padx=10, pady=10, fill='x')
        ttk.Label(item_frame, text="Item Name").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(item_frame, text="Amount").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(item_frame, text="Rebuy").grid(row=0, column=2, padx=5, pady=5, sticky="w")

        self.jester_items_vars = {}
        self.jester_items_amounts = {}
        self.jester_items_rebuy = {}
        saved_jester_items = self.config.get("Jester_Items", {})

        for i, item in enumerate(items, start=1):
            saved_data = saved_jester_items.get(item, [False, 1, False])
            var = ttk.BooleanVar(value=saved_jester_items.get(item, [False, 1, False])[0])
            self.jester_items_vars[item] = var
            ttk.Checkbutton(item_frame, text=item, variable=var).grid(row=i, column=0, sticky="w", padx=5, pady=2)

            amount_var = ttk.StringVar(value=str(saved_jester_items.get(item, [False, 1, False])[1]))
            self.jester_items_amounts[item] = amount_var
            ttk.Entry(item_frame, textvariable=amount_var, width=5).grid(row=i, column=1, padx=5, pady=2)

            rebuy_var = ttk.BooleanVar(value=saved_data[2] if len(saved_data) > 2 else False)
            self.jester_items_rebuy[item] = rebuy_var
            ttk.Checkbutton(item_frame, variable=rebuy_var).grid(row=i, column=2, sticky="w", padx=5, pady=2)

        save_button = ttk.Button(jester_window, text="Save Selections",
                                 command=lambda: self.save_jester_selections(jester_window))
        save_button.pack(pady=10)

    def save_jester_selections(self, jester_window):
        jester_items = {
            item: [var.get(), int(self.jester_items_amounts[item].get()), self.jester_items_rebuy[item].get()]
            for item, var in self.jester_items_vars.items()
        }
        self.config["Jester_Items"] = jester_items
        self.save_config()
        jester_window.destroy()

    def create_stats_tab(self, frame):
        self.stats_labels = {}
        biomes = [biome for biome in self.biome_data.keys() if biome != "NORMAL"]

        columns = 5
        for i, biome in enumerate(biomes):
            color = f"#{int(self.biome_data[biome]['color'], 16):06x}"
            label = ttk.Label(frame, text=f"{biome}: {self.biome_counts[biome]}", foreground=color)

            row = i // columns
            col = i % columns

            label.grid(row=row, column=col, sticky="w", padx=2, pady=1)
            self.stats_labels[biome] = label

        # Total Biomes Found
        total_biomes = sum(self.biome_counts.values())
        self.total_biomes_label = ttk.Label(frame, text=f"Total Biomes Found: {total_biomes}", foreground="light green")
        self.total_biomes_label.grid(row=row + 1, column=0, columnspan=columns, sticky="w", padx=5, pady=5)

        # Running Session
        session_time = self.get_total_session_time()
        self.session_label = ttk.Label(frame, text=f"Running Session: {session_time}")
        self.session_label.grid(row=row + 2, column=0, columnspan=columns, sticky="w", padx=5, pady=10)

        # Biome Logs
        logs_frame = ttk.Frame(frame, borderwidth=2, relief="solid")
        logs_frame.grid(row=0, column=6, rowspan=5, sticky="nsew", padx=10, pady=2)
        logs_label = ttk.Label(logs_frame, text="Biome Logs")
        logs_label.pack(anchor="w", padx=5, pady=2)

        search_entry = ttk.Entry(logs_frame)
        search_entry.pack(anchor="w", padx=5, pady=1)
        search_entry.bind("<KeyRelease>", lambda event: self.filter_logs(search_entry.get()))

        self.logs_text = ttk.Text(logs_frame, height=8, width=25, wrap="word")
        self.logs_text.pack(expand=True, fill="both", padx=5, pady=5)
        self.logs_text.config(state="disabled")

        self.glitch_effect()

    def glitch_effect(self):
        glitch_texts = [
            "GLITCHED", "GlItChEd", "gLiTcHeD", "GL1TCHED", "g#lt#c%",
            "g!olitc3", "g$&*ct", "G1iTcHeD", "gL1tCh3d", "gL!tCh3d",
            "G1!tCh3D", "gL1tCh3D", "gL!tCh3D", "G1!tCh3d", "gL1tCh3d"]

        glitch_colors = [
            "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF",
            "#00FFFF", "#a6c9a3", "#ff69b4", "#8a2be2", "#7fff00",
            "#d2691e", "#ff7f50", "#6495ed", "#dc143c", "#00ced1"
        ]

        def update_glitch():
            glitchy_ahh_text = random.choice(glitch_texts)
            color = random.choice(glitch_colors)
            self.stats_labels["GLITCHED"].config(text=f"{glitchy_ahh_text}: {self.biome_counts['GLITCHED']}",
                                                 foreground=color)
            self.root.after(25, update_glitch)

        update_glitch()

    def create_credit_tab(self, credits_frame):
        current_dir = os.getcwd()
        images_dir = os.path.join(current_dir, "images")
        credit_paths = [
            os.path.join(images_dir, "tea.png"),
            os.path.join(images_dir, "devteam.png"),
            os.path.join(images_dir, "maxstellar.png")
        ]

        def load_image(filename, size):
            for path in credit_paths:
                if os.path.basename(path) == filename and os.path.exists(path):
                    try:
                        img = Image.open(path)
                        img = img.resize(size, Image.LANCZOS)
                        return ImageTk.PhotoImage(img)
                    except Exception as e:
                        print(f"Failed to load image: {path}, Error: {e}")
                        return None
            return None

        credits_frame_content = ttk.Frame(credits_frame)
        credits_frame_content.pack(pady=20, fill='both', expand=True)

        noteab_image = load_image("tea.png", (85, 85))
        dev_image = load_image("devteam.png", (70, 70))
        maxstellar_image = load_image("maxstellar.png", (85, 85))

        noteab_frame = ttk.Frame(credits_frame_content, borderwidth=2, relief="solid")
        noteab_frame.grid(row=0, column=0, padx=10, pady=2, sticky='nsew')

        maxstellar_frame = ttk.Frame(credits_frame_content, borderwidth=2, relief="solid")
        maxstellar_frame.grid(row=0, column=1, padx=10, pady=2, sticky='nsew')

        credits_frame_content.grid_columnconfigure(0, weight=1)
        credits_frame_content.grid_columnconfigure(1, weight=1)
        credits_frame_content.grid_rowconfigure(1, weight=1)

        top_inner = ttk.Frame(noteab_frame)
        top_inner.pack(pady=6, padx=6, anchor="n")

        if noteab_image:
            l = ttk.Label(top_inner, image=noteab_image)
            l.grid(row=0, column=0, rowspan=2, padx=(0,10))
            noteab_frame._img = noteab_image

        small_images_frame = ttk.Frame(top_inner)
        small_images_frame.grid(row=0, column=1, sticky='n')

        if dev_image:
            vlab = ttk.Label(small_images_frame, image=dev_image)
            vlab.grid(row=0, column=0, padx=2, pady=0)
            small_images_frame._vap = dev_image

        ttk.Label(noteab_frame, text="Developers:").pack(anchor="center")

        devs_frame = ttk.Frame(noteab_frame)
        devs_frame.pack(fill='x', padx=6, pady=(4,0))
        devs_frame.grid_columnconfigure(0, minsize=95)
        devs_frame.grid_columnconfigure(1, weight=1)

        dev_vap = ttk.Label(devs_frame, text='- Vapure/"@criticize."', foreground="#03cafc", cursor="hand2")
        dev_vap.grid(row=0, column=1, sticky='w')
        dev_vap.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/xVapure"))

        dev_max = ttk.Label(devs_frame, text='- Maxstellar', foreground="#03cafc", cursor="hand2")
        dev_max.grid(row=1, column=1, sticky='w')
        dev_max.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.youtube.com/@maxstellar_"))

        dev_til = ttk.Label(devs_frame, text='- Til/Comet', foreground="#03cafc", cursor="hand2")
        dev_til.grid(row=2, column=1, sticky='w')
        dev_til.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/sleepytil"))
        discord_label = ttk.Label(noteab_frame, text="""Join the Coteab Discord server!!!""", foreground="royalblue", cursor="hand2")
        discord_label.configure(font=('Segoe UI', 9, 'underline'))
        discord_label.pack()
        discord_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://discord.gg/fw6q274Nrt"))

        github_label = ttk.Label(noteab_frame, text="""GitHub: Coteab Macro!""", foreground="#03cafc", cursor="hand2")
        github_label.pack()
        github_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/xVapure/Noteab-Macro"))

        if maxstellar_image:
            ttk.Label(maxstellar_frame, image=maxstellar_image).pack(pady=5)
            maxstellar_frame._img = maxstellar_image
        ttk.Label(maxstellar_frame, text="Inspired Biome Macro Creator: maxstellar").pack()
        yt_label = ttk.Label(maxstellar_frame, text="Their YT channel", foreground="royalblue", cursor="hand2")
        yt_label.configure(font=('Segoe UI', 9, 'underline'))
        yt_label.pack()
        yt_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.youtube.com/"))

        extra_frame = ttk.LabelFrame(credits_frame_content, text="Extra Credits")
        extra_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', padx=10, pady=10)

        extra_inner = ttk.Frame(extra_frame)
        extra_inner.pack(fill='both', expand=True)

        scrollbar = ttk.Scrollbar(extra_inner, orient='vertical')
        credits_text = ttk.Text(extra_inner, height=6, wrap='word', yscrollcommand=scrollbar.set)
        scrollbar.config(command=credits_text.yview)
        scrollbar.pack(side='right', fill='y')
        credits_text.pack(side='left', fill='both', expand=True, padx=(5, 0), pady=5)

        extra_credits = [
            "Noteab - The original developer of the macro, this project is a fork of his.",
            "maxstellar - Inspiration and I used some of his logic.",
            "Vexthecoder - Thank you for the icons <3",
            "Cresqnt, Baz & the Scope Team - Anti-AFK inspiration.",
            "ManasAarohi - For teaching me how FFlag works",
            "rnd.xy, imsomeone - For doing external works that I was too lazy to do tysm.",
            "Finnerinch - Former developer.",
            """All the testers that made the update possible with as less flaws as possible. Notably: "imsomeone", "cheshington", "tilesdrop", "kira_drago2", "gummyballer", "retelteel", "mightbeanormalguest", "gonebon" and others."""
        ]

        credits_text.config(state='normal')
        credits_text.delete("1.0", "end")
        for person in extra_credits:
            credits_text.insert("end", f"- {person}\n")
        credits_text.config(state='disabled')

    def update_stats(self):
        total_biomes = sum(self.biome_counts.values())

        for biome, label in self.stats_labels.items():
            label.config(text=f"{biome}: {self.biome_counts[biome]}")

        self.total_biomes_label.config(text=f"Total Biomes Found: {total_biomes}", foreground="light green")
        self.session_label.config(text=f"Running Session: {self.get_total_session_time()}")
        self.save_config()

    def format_seconds_to_hhmmss(self, total_seconds):
        total_seconds = int(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def get_total_session_time(self):
        try:
            now = datetime.now()
            if self.start_time:
                elapsed_time = int((now - self.start_time).total_seconds())
                total_seconds = self.saved_session + elapsed_time
                self.current_session += 1
            else:
                total_seconds = self.saved_session

            if total_seconds >= 86400:
                overflow = total_seconds - 86400
                self.session_window_start = datetime.now()
                self.saved_session = overflow
                if self.start_time:
                    self.start_time = datetime.now()
                self._session_window_reset_performed = True
                total_seconds = overflow

            if total_seconds >= 86400:
                return self.format_seconds_to_hhmmss(86400)

            return self.format_seconds_to_hhmmss(total_seconds)

        except Exception as e:
            self.error_logging(e, "Error in get_total_session_time function.")
            return "00:00:00"

    def parse_session_time(self, session_time_str):
        try:
            parts = session_time_str.split(":")
            if len(parts) == 3:  # Format: hours:minutes:seconds
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                raise ValueError("Invalid session time format")

        except Exception as e:
            self.error_logging(e, "Error parsing session time.")
            return 0  # Return default value in case of error, well yeah

    def update_session_time(self):
        try:
            self.session_label.config(text=f"Running Session: {self.get_total_session_time()}")
            if getattr(self, "_session_window_reset_performed", False):
                try:
                    self.save_config()
                except Exception:
                    pass
                self._session_window_reset_performed = False
        except Exception as e:
            self.error_logging(e, "Error in update_session_time function.")

    def display_logs(self, logs=None):
        self.logs_text.config(state="normal")
        self.logs_text.delete(1.0, ttk.END)

        if logs is None:
            logs = self.logs

        last_logs = logs[-10:]

        for log in last_logs:
            self.logs_text.insert(ttk.END, log + "\n")
        self.logs_text.config(state="disabled")

    def filter_logs(self, keyword):
        filtered_logs = [log for log in self.logs if keyword.lower() in log.lower()]
        self.display_logs(filtered_logs)

    def append_log(self, message):
        self.logs.append(message)
        self.display_logs()
        self.save_logs()
        self.logs_text.see(ttk.END)

    ## INVENTORY SNIPPING ##

    def open_assign_inventory_window(self):
        assign_window = ttk.Toplevel(self.root)
        assign_window.title("Inventory Coordinates")
        assign_window.geometry("650x500")

        positions = [
            ("Inventory Menu", "inventory_menu"),
            ("Items Tab", "items_tab"),
            ("Search Bar", "search_bar"),
            ("First Item Slot", "first_item_slot"),
            ("Amount Box", "amount_box"),
            ("Use Button", "use_button"),
            ("Aura Menu", "aura_menu"),
            ("Inventory close button \"x\"", "inventory_close_button"),
            ("'START' button (for reconnect feature, \n the one above 'Update Logs' button)", "reconnect_start_button")
        ]

        coord_vars = {}

        for i, (label_text, config_key) in enumerate(positions):
            label = ttk.Label(assign_window, text=f"{label_text} (X, Y):")
            label.grid(row=i, column=0, padx=5, pady=5, sticky="w")

            x_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[0])
            y_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[1])
            coord_vars[config_key] = (x_var, y_var)

            x_entry = ttk.Entry(assign_window, textvariable=x_var, width=6)
            x_entry.grid(row=i, column=1, padx=5, pady=5)

            y_entry = ttk.Entry(assign_window, textvariable=y_var, width=6)
            y_entry.grid(row=i, column=2, padx=5, pady=5)

            select_button = ttk.Button(
                assign_window, text="Assign Click",
                command=lambda key=config_key: self.start_capture_thread(key, coord_vars)
            )
            select_button.grid(row=i, column=3, padx=5, pady=5)

        save_button = ttk.Button(assign_window, text="Save",
                                 command=lambda: self.save_inventory_coordinates(assign_window, coord_vars))
        save_button.grid(row=len(positions), column=0, columnspan=4, pady=10)

    def open_assign_potion_craft_window(self):
        assign_window = ttk.Toplevel(self.root)
        assign_window.title("Potion Craft Coordinates")
        assign_window.geometry("720x340")

        positions = [
            ("Craft Button", "craft_button"),
            ("Auto Button", "auto_button"),
            ("1st add button ('Lucky Potion' add button in Heavenly Potion craft recipe)", "1st_add_button"),
            ("2nd add button ('Celestial' add button in Heavenly Potion craft recipe)", "2nd_add_button"),
            ("3rd add button ('Exotic' add button in Heavenly Potion craft recipe as instance)", "3rd_add_button"),
            ("4th add button ('Quartz' add button in Heavenly Potion craft recipe as instance)", "4th_add_button"),
        ]

        coord_vars = {}

        for i, (label_text, config_key) in enumerate(positions):
            label = ttk.Label(assign_window, text=f"{label_text} (X, Y):")
            label.grid(row=i, column=0, padx=5, pady=5, sticky="w")

            x_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[0])
            y_var = ttk.IntVar(value=self.config.get(config_key, [0, 0])[1])
            coord_vars[config_key] = (x_var, y_var)

            x_entry = ttk.Entry(assign_window, textvariable=x_var, width=6)
            x_entry.grid(row=i, column=1, padx=5, pady=5)

            y_entry = ttk.Entry(assign_window, textvariable=y_var, width=6)
            y_entry.grid(row=i, column=2, padx=5, pady=5)

            select_button = ttk.Button(
                assign_window, text="Assign Click",
                command=lambda key=config_key: self.start_capture_thread(key, coord_vars)
            )
            select_button.grid(row=i, column=3, padx=5, pady=5)

        save_button = ttk.Button(assign_window, text="Save",
                                 command=lambda: self.save_inventory_coordinates(assign_window, coord_vars))
        save_button.grid(row=len(positions), column=0, columnspan=4, pady=10)

    def save_inventory_coordinates(self, window, coord_vars):
        for key, (x_var, y_var) in coord_vars.items():
            self.config[key] = [x_var.get(), y_var.get()]
        self.save_config()
        window.destroy()

    def start_capture_thread(self, config_key, coord_vars):
        snipping_tool = SnippingWidget(self.root, config_key=config_key,
                                       callback=lambda region: self.update_coordinates(config_key, region, coord_vars))
        snipping_tool.start()

    def update_coordinates(self, config_key, region, coord_vars):
        x, y = region[0], region[1]
        coord_vars[config_key][0].set(x)
        coord_vars[config_key][1].set(y)
        self.save_config()

        ## INVENTORY SNIPPING ^^ ##

    def validate_and_save_ps_link(self):
        private_server_link = self.private_server_link_entry.get()
        if not self.validate_private_server_link(private_server_link):
            messagebox.showwarning(
                "Invalid PS Link!",
                "The link you provided is not a valid Roblox link. It could be either a share link or a private server code link. "
                "Please ensure the link is correct and try again.\n\n"
                "Valid links should look like:\n"
                "- Share link: https://www.roblox.com/share?code=1234567899abcdefxyz&type=Server\n"
                "- Private server link: https://www.roblox.com/games/15532962292/"
            )
            return

        self.save_config()

    def validate_private_server_link(self, link):
        share_pattern = r"https://www\.roblox\.com/share\?code=\w+&type=Server"
        private_server_pattern = r"^https:\/\/www\.roblox\.com\/games\/(\d+)\/?$"
        second_ps_pattern = r"^https:\/\/www\.roblox\.com\/games\/(\d+)\/?$\?privateServerLinkCode=\w+$"

        return re.match(share_pattern, link) or re.match(private_server_pattern, link) or re.match(second_ps_pattern,
                                                                                                   link)

    def show_reconnect_info(self):
        messagebox.showinfo(
            "Auto Reconnect Info",
            "(?) This feature only able to reconnect if:\n \n"
            "(1) Your private server link is a private server code 'Sols-RNG?privateServerLinkCode=randomnumberhere', not a share link like this: 'https://www.roblox.com/share?code=...&type=Server' \n \n"
            "(2) Make sure to calibrate mouse click for 'Start' button in 'Assign Inventory Click' \n \n"
            "(3) You can find a tutorial on YouTube to see how to convert a share link to a private server code! \n \n"
            "(Note: This reconnect feature still on experimental phase, there's a chance it gonna be failed to reconnect back to your server!)"
        )

    def start_detection(self):
        if not self.detection_running:
            now = datetime.now()
            self.detection_running = True
            self._start_player_logger_thread()
            self.start_time = now
            self.current_session = 0
            self.has_started_once = True
            self._session_window_reset_performed = False
            self.stop_sent = False

            if not self.session_window_start:
                self.session_window_start = now
                self.saved_session = 0
            else:
                try:
                    if (now - self.session_window_start).total_seconds() >= 86400:
                        self.session_window_start = now
                        self.saved_session = 0
                except Exception:
                    self.session_window_start = now
                    self.saved_session = 0

            self.config["session_window_start"] = self.session_window_start.isoformat()
            self.config["macro_last_start"] = now.isoformat()
            self.save_config()

            threads = [
                (self.check_disconnect_loop, "Disconnect Check"),
                (self.biome_loop_check, "Biome Check"),
                (self.biome_itemchange_loop, "Item Change"),
                (self.aura_loop_check, "Aura Check"),
                (self.merchant_log_check, "Merchant Check"),
                (self.anti_afk_loop, "Anti-AFK"),
                (self.quest_claim_loop, "Quest Claim")
            ]

            for thread_func, name in threads:
                thread = threading.Thread(target=thread_func, name=name, daemon=True)
                thread.start()
            self.perform_anti_afk_action()

            self.set_title_threadsafe("""Coteab Macro v2.0.1 (Running)""")
            self.send_webhook_status("Macro started!", color=0x64ff5e)
            try:
                if getattr(self, "remote_access_var", None) and self.remote_access_var.get():
                    token = self.remote_bot_token_var.get().strip() if hasattr(self, "remote_bot_token_var") else ""
                    if token:
                        self.start_remote_bot()
            except Exception:
                pass
            print("Biome detection started.")

    def stop_detection(self):
        if self.detection_running:
            now = datetime.now()
            self.detection_running = False
            self._stop_player_logger_thread()
            if getattr(self, "timer_paused_by_disconnect", False):
                elapsed_time = 0
                self.timer_paused_by_disconnect = False
            else:
                if self.start_time:
                    elapsed_time = int((now - self.start_time).total_seconds())
                else:
                    elapsed_time = 0

            session_seconds = elapsed_time

            if self.session_window_start and (now - self.session_window_start).total_seconds() >= 86400:
                last24h_seconds = session_seconds
            else:
                last24h_seconds = self.saved_session + elapsed_time
                if last24h_seconds > 86400:
                    last24h_seconds = 86400

            self.saved_session += elapsed_time
            self.start_time = None
            self.stop_sent = True
            self.set_title_threadsafe("Coteab Macro v2.0.1 (Stopped)")
            try:
                self.stop_remote_bot()
            except Exception:
                pass
            self.send_macro_summary(last24h_seconds)
            print("closed", self.current_session)
            self.save_config()
            print("Biome detection stopped.")

    def get_latest_log_file(self):
        files = [os.path.join(self.logs_dir, f) for f in os.listdir(self.logs_dir) if f.endswith('.log')]
        latest_file = max(files, key=os.path.getmtime)
        return latest_file

    def read_log_file(self, log_file_path):
        if not os.path.exists(log_file_path):
            print(f"Log file not found: {log_file_path}")
            return []

        def is_chat_log(line):
            if "ExpChat" in line or "mountClientApp" in line or "Time record" in line or "[Server]" in line:
                excluded_phrases = [
                    "[Merchant]: Mari has arrived on the island...",
                    "[Merchant]: Jester has arrived on the island!!",
                    "The Devourer of the Void,"
                ]
                return not any(phrase in line for phrase in excluded_phrases)
            return False

        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as file:
            file.seek(self.last_position)
            lines = file.readlines()
            self.last_position = file.tell()
            return [line for line in lines if not is_chat_log(line)]

    def read_log_file_for_detector(self, log_file_path, pos_attr='last_position', filter_chat=False):
        if not os.path.exists(log_file_path):
            return []

        try:
            pos = getattr(self, pos_attr, 0)
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(pos)
                lines = f.readlines()
                setattr(self, pos_attr, f.tell())

            if filter_chat:
                def is_chat_log(line):
                    if "ExpChat" in line or "mountClientApp" in line:
                        excluded_phrases = [
                            "[Merchant]: Mari has arrived on the island...",
                            "[Merchant]: Jester has arrived on the island!!",
                            "The Devourer of the Void,"
                        ]
                        return not any(phrase in line for phrase in excluded_phrases)
                    return False

                return [line for line in lines if not is_chat_log(line)]

            return lines

        except Exception as e:
            self.error_logging(e, f"read_log_file_for_detector error ({pos_attr})")
            return []

    def read_full_log_file(self, log_file_path):
        if not os.path.exists(log_file_path):
            print(f"Log file not found: {log_file_path}")
            return []

        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.readlines()

    def load_auras_json(self):
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/auras.json"
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict):
                return data
            return {}
        except Exception as e:
            print(f"Error loading auras.json from {url}: {e}")
            self.error_logging(e, f"Error loading auras.json from {url}")
            return {}

    def check_aura_in_logs(self, log_file_path):
        try:
            if self.reconnecting_state: return

            if not hasattr(self, 'last_aura_found'):
                self.last_aura_found = None

            log_lines = self.read_full_log_file(log_file_path)

            for line in reversed(log_lines):
                try:
                    match = re.search(r'"state":"Equipped \\"(.*?)\\"', line)
                    if match:
                        aura = match.group(1)

                        if aura in self.auras_data:
                            aura_info = self.auras_data[aura]
                            rarity = aura_info["rarity"]
                            exclusive_biome, multiplier = aura_info["exclusive_biome"]

                            # Check if the current biome is GLITCHED
                            if self.current_biome == "GLITCHED":
                                rarity /= multiplier
                                biome_message = "[From GLITCHED!]"

                            # Check if the current biome is the aura's exclusive biome
                            elif self.current_biome == exclusive_biome:
                                rarity /= multiplier
                                biome_message = f"[From {exclusive_biome}!]"

                            else:
                                biome_message = ""

                            # Format rarity
                            formatted_rarity = f"{int(rarity):,}"

                            if aura != self.last_aura_found:
                                screenshot_path = None
                                try:
                                    if getattr(self, "aura_screenshot_var", None) and self.aura_screenshot_var.get():
                                        if self.is_roblox_focused():
                                            os.makedirs("images", exist_ok=True)
                                            filename = os.path.join("images", f"aura_{int(time.time())}.png")
                                            img = pyautogui.screenshot()
                                            img.save(filename)
                                            screenshot_path = filename
                                except Exception as e:
                                    self.error_logging(e, "Error taking aura screenshot")

                                self.send_aura_webhook(aura, formatted_rarity, biome_message, screenshot_path=screenshot_path)
                                self.last_aura_found = aura

                                if self.enable_aura_record_var.get() and rarity >= int(self.aura_record_minimum_var.get()):
                                    self.trigger_aura_record()
                        else:
                            # Aura not found in auras_data (biomes_data.json)
                            if aura != self.last_aura_found:
                                screenshot_path = None
                                try:
                                    if getattr(self, "aura_screenshot_var", None) and self.aura_screenshot_var.get():
                                        if self.is_roblox_focused():
                                            os.makedirs("images", exist_ok=True)
                                            filename = os.path.join("images", f"aura_{int(time.time())}.png")
                                            img = pyautogui.screenshot()
                                            img.save(filename)
                                            screenshot_path = filename
                                except Exception as e:
                                    self.error_logging(e, "Error taking aura screenshot")

                                self.send_aura_webhook(aura, None, "", screenshot_path=screenshot_path)
                                self.last_aura_found = aura
                        return

                except Exception as e:
                    self.error_logging(e, "Error processing specific aura in check_aura_in_logs.")

        except Exception as e:
            self.error_logging(e, "Error in main check_aura_in_logs function")

    def check_biome_in_logs(self):
        try:
            log_file_path = self.get_latest_log_file()
            log_lines = self.read_log_file(log_file_path)

            for line in reversed(log_lines):
                for biome in self.biome_data:
                    if biome in line and "[BloxstrapRPC]" in line:
                        threading.Thread(target=self.handle_biome_detection, args=(biome,)).start()
                        return

        except Exception as e:
            self.error_logging(e, "Error in check_biome_in_logs function :skull:")

    def merchant_log_check(self):
        last_log_file = None
        while self.detection_running:
            try:
                current_log_file = self.get_latest_log_file()
                if current_log_file != last_log_file:
                    last_log_file = current_log_file
                    # reset incremental cursors for these detectors so they read the new file from start
                    self.last_position_merchant = 0
                    self.last_position_eden = 0

                if self.detect_merchant_no_mt_var.get() or self.mt_var.get():
                    self.check_merchant_in_logs(current_log_file)
                self.check_eden_in_logs(current_log_file)
                time.sleep(0.8)
            except Exception as e:
                self.error_logging(e, "Error in merchant_log_check function.")

    def check_merchant_in_logs(self, log_file_path):
        try:
            if self.reconnecting_state:
                return

            if not hasattr(self, 'last_merchant_sent'):
                self.last_merchant_sent = {}

            merchant_cooldown_time = 300
            current_time = time.time()

            log_lines = self.read_log_file_for_detector(log_file_path, pos_attr='last_position_merchant',
                                                        filter_chat=False)
            if not log_lines:
                return

            max_lines = int(self.config.get("merchant_log_tail", 35))
            recent = log_lines[-max_lines:] if len(log_lines) > max_lines else log_lines

            for line in reversed(recent):
                if "[Merchant]" not in line:
                    continue

                l = line.strip()

                merchant_name = None
                if "Mari has arrived on the island" in l:
                    merchant_name = "Mari"
                elif "Jester has arrived on the island" in l:
                    merchant_name = "Jester"
                else:
                    if "Mari" in l and "has arrived" in l:
                        merchant_name = "Mari"
                    elif "Jester" in l and "has arrived" in l:
                        merchant_name = "Jester"

                if not merchant_name:
                    continue

                last_sent_time = self.last_merchant_sent.get((merchant_name, 'logs'), 0)
                if (current_time - last_sent_time) < merchant_cooldown_time:
                    return

                self.last_merchant_sent[(merchant_name, 'logs')] = current_time

                if self.detect_merchant_no_mt_var.get():
                    try:
                        self.send_merchant_webhook(merchant_name, None, source='logs')
                        self.append_log(f"[Merchant Detection (logs)] {merchant_name} detected from logs.")
                    except Exception as e:
                        self.error_logging(e, "Failed to send merchant webhook from log detection")

                if self.mt_var.get():
                    with self.lock:
                        self._cancel_next_actions_until = datetime.now() + timedelta(seconds=5)
                        self._merchant_pending_from_logs = True
                        self._merchant_pending_name = merchant_name
                        self.append_log(
                            f"[Merchant Detection] Merchant teleporter pending due to log detection for {merchant_name}.")

                        if not getattr(self, '_br_sc_running', False) and not getattr(self, '_mt_running',
                                                                                      False) and not self.on_auto_merchant_state and not self.auto_pop_state and not self.config.get(
                                "enable_auto_craft") and self.current_biome != "GLITCHED":
                            try:
                                self.append_log("[Merchant Detection] Using merchant teleporter immediately (logs).")
                                self.use_merchant_teleporter()
                                self._merchant_pending_from_logs = False
                                self._merchant_pending_name = None
                                self.last_mt_time = datetime.now()
                            except Exception as e:
                                self.error_logging(e, "Failed to use merchant teleporter after log detection")
                return

        except Exception as e:
            self.error_logging(e, "Error in check_merchant_in_logs function.")

    def handle_biome_detection(self, biome):
        try:
            last_biome = self.current_biome

            if self.current_biome != biome:
                if last_biome and last_biome != "NORMAL":
                    prev_message_type = self.config.get("biome_notifier", {}).get(last_biome, "None")
                    if prev_message_type != "None":
                        self.send_webhook(last_biome, prev_message_type, "end")

                biome_info = self.biome_data[biome]
                now = datetime.now(timezone.utc)    

                print(f"Detected Biome: {biome}, Color: {biome_info['color']}")
                self.append_log(f"Detected Biome: {biome}")

                self.current_biome = biome
                self.last_sent[biome] = now
                try:
                    self.biome_history.append((now, biome))
                    if len(self.biome_history) > 300:
                        self.biome_history = self.biome_history[-300:]
                except Exception:
                    pass
                if biome not in self.biome_counts: self.biome_counts[biome] = 0
                self.biome_counts[biome] += 1
                self.update_stats()

                message_type = self.config["biome_notifier"].get(biome, "None")

                if biome in ["GLITCHED", "DREAMSPACE", "CYBERSPACE"]:
                    message_type = "Ping"
                    if self.config.get("record_rare_biome", False):
                        self.trigger_biome_record()

                if biome != "NORMAL":
                    self.send_webhook(biome, message_type, "start")

                if biome == "GLITCHED":
                    with self.lock:
                        if self.config.get("auto_pop_glitched", False):
                            self.auto_pop_state = True
                            self.auto_pop_buffs()
                            self.auto_pop_state = False
                        if self.config.get("enable_buff_glitched", False):
                            threading.Thread(target=self.perform_glitched_enable_buff, daemon=True).start()

        except Exception as e:
            self.error_logging(e,
                               f"Error in handle_biome_detection for biome: {biome}. Hell naw go fix your ass macro noteab! - Wise greenie word")

    def biome_loop_check(self):
        last_log_file = None

        while self.detection_running:
            try:
                current_log_file = self.get_latest_log_file()
                if current_log_file != last_log_file:
                    self.last_position = 0
                    self.last_position_merchant = 0
                    self.last_position_eden = 0
                    last_log_file = current_log_file

                self.check_biome_in_logs()
                self.update_session_time()
                time.sleep(1)

            except Exception as e:
                self.error_logging(e, "Error in biome_loop_check function.")

    def aura_loop_check(self):
        last_log_file = None
        while self.detection_running:
            try:
                current_log_file = self.get_latest_log_file()
                if current_log_file != last_log_file:
                    self.last_position = 0
                    last_log_file = current_log_file

                if self.enable_aura_detection_var.get(): self.check_aura_in_logs(current_log_file)
                time.sleep(0.6)

            except Exception as e:
                self.error_logging(e, "Error in aura_loop_check function.")

    def biome_itemchange_loop(self):
        while self.detection_running:
            try:
                with self.lock:
                    self.auto_biome_change()
                time.sleep(1)

            except Exception as e:
                self.error_logging(e, "Error in biome_itemchange_loop function.")

    def check_disconnect_loop(self, current_attempt=1):
        if not hasattr(self, 'has_sent_disconnected_message'):
            self.has_sent_disconnected_message = False

        while self.detection_running:
            try:
                if not self.check_roblox_procs():
                    self._pause_timer_for_disconnect("Roblox instance closed!")
                    time.sleep(4.5)

                    if self.config.get("auto_reconnect"):
                        private_server_link = self.config.get("private_server_link")
                        if private_server_link:
                            private_server_code = private_server_link.split("privateServerLinkCode=")[-1]
                            roblox_deep_link = f"roblox://placeID=15532962292&linkCode={private_server_code}"
                            max_retries = 3
                            for attempt in range(current_attempt, max_retries + 1):
                                if not self.detection_running:
                                    break
                                self.terminate_roblox_processes()
                                self.send_webhook_status(f"Reconnecting to your server. hold on bro", color=0xffff00)
                                self.set_title_threadsafe(
                                    """Coteab Macro v2.0.1 (Reconnecting)""")
                                try:
                                    os.startfile(roblox_deep_link)
                                except Exception:
                                    pass
                                time.sleep(36)
                                if self.check_roblox_procs():
                                    self.send_webhook_status("Roblox opened. Loading into the games...", color=0x4aff65)
                                    self.has_sent_disconnected_message = False
                                    if not self.reconnect_check_start_button():
                                        self.send_webhook_status(
                                            "Stuck in 'In Main Menu' for too long. I might reconnect bro back to server again",
                                            color=0xff0000)
                                        continue
                                    self._resume_timer_after_reconnect()
                                    break
                                time.sleep(1)
                            if attempt == max_retries and not self.check_roblox_procs():
                                self.terminate_roblox_processes()
                                self.send_webhook_status("Max retries reached. Reconnecting to public server.",
                                                         color=0xff0000)
                    else:
                        while self.detection_running and not self.check_roblox_procs():
                            time.sleep(1)
                        if self.check_roblox_procs():
                            self._resume_timer_after_reconnect()
                else:
                    time.sleep(0.5)
            except Exception as e:
                self.error_logging(e, "Error in check_disconnect_loop function.")
                time.sleep(1)

    def _pause_timer_for_disconnect(self, reason=None):
        try:
            if not getattr(self, "timer_paused_by_disconnect", False):
                if self.start_time:
                    now = datetime.now()
                    elapsed = int((now - self.start_time).total_seconds())
                    self.saved_session += elapsed
                    self.start_time = None
                self.timer_paused_by_disconnect = True
                self.pause_reason = reason
            self.reconnecting_state = True
            self.set_title_threadsafe(
                """Coteab Macro v2.0.1 (Roblox Disconnected :c )""")
            if reason and not getattr(self, 'has_sent_disconnected_message', False):
                try:
                    self.send_webhook_status(reason, color=0xff0000)
                except Exception:
                    pass
                self.has_sent_disconnected_message = True
            self.save_config()
        except Exception as e:
            self.error_logging(e, "_pause_timer_for_disconnect")

    def _resume_timer_after_reconnect(self):
        try:
            if getattr(self, "timer_paused_by_disconnect", False):
                self.start_time = datetime.now()
                self.timer_paused_by_disconnect = False
                try:
                    delattr = False
                except Exception:
                    pass
                self.pause_reason = None
            else:
                if not self.start_time:
                    self.start_time = datetime.now()
            self.reconnecting_state = False
            self.has_sent_disconnected_message = False
            self.set_title_threadsafe("""Coteab Macro v2.0.1 (Running)""")
            self.save_config()
        except Exception as e:
            self.error_logging(e, "_resume_timer_after_reconnect")

    def register_shutdown_handler(self):
        try:
            atexit.register(self._on_exit_handler)
        except Exception:
            pass
        try:
            import win32api, win32con
            def _handler(ctrl_type):
                if ctrl_type in (win32con.CTRL_SHUTDOWN_EVENT, win32con.CTRL_LOGOFF_EVENT):
                    try:
                        self._pause_timer_for_disconnect("System Shutdown")
                    except Exception:
                        pass
                return False

            win32api.SetConsoleCtrlHandler(_handler, True)
        except Exception:
            pass

    def fallback_reconnect(self, current_attempt):
        print(f"Attempting fallback reconnect from attempt {current_attempt}...")
        self.reconnecting_state = True

        self.terminate_roblox_processes()
        self.check_disconnect_loop(current_attempt)
        self.reconnecting_state = False

    def _start_player_logger_thread(self):
        if hasattr(self, "player_logger_thread") and self.player_logger_thread and self.player_logger_thread.is_alive():
            return
        self.player_logger_running = True
        self._start_player_log_sender_thread()
        self.player_logger_thread = threading.Thread(target=self._player_logger_loop, daemon=True)
        self.player_logger_thread.start()

    def _stop_player_logger_thread(self):
        self.player_logger_running = False
        self._stop_player_log_sender_thread()

    def _start_player_log_sender_thread(self):
        if hasattr(self,
                   "player_log_sender_thread") and self.player_log_sender_thread and self.player_log_sender_thread.is_alive():
            return
        self.player_log_sender_running = True
        if not hasattr(self, "player_log_queue") or self.player_log_queue is None:
            self.player_log_queue = queue.Queue()
        self.player_log_sender_thread = threading.Thread(target=self._player_log_sender_loop, daemon=True)
        self.player_log_sender_thread.start()

    def _stop_player_log_sender_thread(self):
        self.player_log_sender_running = False
        try:
            if hasattr(self, "player_log_queue"):
                self.player_log_queue.put(None)
        except Exception:
            pass

    def _enqueue_player_embed(self, embed):
        if not hasattr(self, "player_log_queue") or self.player_log_queue is None:
            try:
                self.player_log_queue = queue.Queue()
            except Exception:
                return
        try:
            self.player_log_queue.put(embed)
        except Exception:
            pass

    def _player_log_sender_loop(self):
        while getattr(self, "player_log_sender_running", False):
            try:
                embed = self.player_log_queue.get(timeout=1)
            except Exception:
                continue
            if embed is None:
                continue
            urls = self.get_webhook_list()
            if not urls:
                continue
            payload = {"embeds": [embed]}
            for webhook_url in urls:
                try:
                    r = requests.post(webhook_url, json=payload, timeout=7)
                    if getattr(r, "status_code", None) == 429:
                        retry_after = r.headers.get("Retry-After")
                        try:
                            retry = int(retry_after)
                        except Exception:
                            retry = 5
                        time.sleep(retry)
                        try:
                            requests.post(webhook_url, json=payload, timeout=7)
                        except Exception:
                            pass
                except Exception:
                    pass
            delay = getattr(self, "player_log_send_delay", 2.0)
            start = time.time()
            while (time.time() - start) < delay:
                if not getattr(self, "player_log_sender_running", False):
                    break
                time.sleep(0.1)

    def _find_latest_log_file(self):
        try:
            if not os.path.isdir(self.logs_dir):
                return None
            files = [os.path.join(self.logs_dir, f) for f in os.listdir(self.logs_dir) if
                     os.path.isfile(os.path.join(self.logs_dir, f))]
            if not files:
                return None
            return max(files, key=os.path.getmtime)
        except:
            return None

    def _parse_iso_ts(self, s):
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except:
            return datetime.now(timezone.utc)

    def _biome_at(self, ts):
        try:
            if not hasattr(self, "biome_history") or not self.biome_history:
                return self.current_biome
            try:
                ts_utc = ts.astimezone(timezone.utc)
            except Exception:
                try:
                    ts_utc = ts.replace(tzinfo=timezone.utc)
                except Exception:
                    ts_utc = ts
            last = None
            for bt, b in self.biome_history:
                try:
                    bt_utc = bt.astimezone(timezone.utc)
                except Exception:
                    try:
                        bt_utc = bt.replace(tzinfo=timezone.utc)
                    except Exception:
                        bt_utc = bt
                if bt_utc <= ts_utc:
                    last = b
                else:
                    break
            return last if last is not None else self.current_biome
        except Exception:
            return self.current_biome

    def _player_logger_loop(self):
        last_file = None
        last_pos = 0
        sessions = {}
        while getattr(self, "player_logger_running", False):
            if not getattr(self, "player_logger_var", None) or not self.player_logger_var.get():
                time.sleep(0.5)
                continue
            path = self._find_latest_log_file()
            if not path:
                time.sleep(0.5)
                continue
            if path != last_file:
                last_file = path
                try:
                    last_pos = os.path.getsize(path)
                except:
                    last_pos = 0
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(last_pos)
                    line = f.readline()
                    if not line:
                        time.sleep(0.2)
                        continue
                    last_pos = f.tell()
            except:
                time.sleep(0.5)
                continue
            if "[ExpChat/mountClientApp (Trace)]" in line and ("Player added:" in line or "Player removed:" in line):
                ts_str = line.split(",", 1)[0].strip()
                ts = self._parse_iso_ts(ts_str)
                if "Player added:" in line:
                    m = re.search(r"Player added:\s+(\S+)\s+(\d+)", line)
                    if m:
                        name, pid = m.group(1), m.group(2)
                        join_biome = self._biome_at(ts)
                        sessions[pid] = {"ts": ts, "biome": join_biome}
                        self.logs.append(f"[Player] Joined {name} ({pid})")
                        self.save_logs()
                        ts_iso = ts.astimezone(timezone.utc).isoformat()
                        embed = self._make_player_embed("join", name, pid, ts_iso, None, join_biome)
                        self._enqueue_player_embed(embed)
                elif "Player removed:" in line:
                    m = re.search(r"Player removed:\s+(\S+)\s+(\d+)", line)
                    if m:
                        name, pid = m.group(1), m.group(2)
                        joined = sessions.pop(pid, None)
                        left_biome = self._biome_at(ts)
                        if joined and isinstance(joined, dict) and joined.get("ts"):
                            joined_ts = joined.get("ts")
                            joined_biome = joined.get("biome")
                            secs = int((ts - joined_ts).total_seconds())
                            h = secs // 3600
                            m_ = (secs % 3600) // 60
                            s_ = secs % 60
                            dur = f"{h:02d}:{m_:02d}:{s_:02d}"
                            self.logs.append(f"[Player] Left {name} ({pid}) after {dur}")
                            self.save_logs()
                            ts_iso = ts.astimezone(timezone.utc).isoformat()
                            embed = self._make_player_embed("leave", name, pid, ts_iso, dur, joined_biome, left_biome)
                            self._enqueue_player_embed(embed)
                        else:
                            self.logs.append(f"[Player] Left {name} ({pid})")
                            self.save_logs()
                            ts_iso = ts.astimezone(timezone.utc).isoformat()
                            embed = self._make_player_embed("leave", name, pid, ts_iso, None, None, left_biome)
                            self._enqueue_player_embed(embed)

    def reconnect_check_start_button(self):
        try:
            self.set_title_threadsafe(
                """Coteab Macro v2.0.1 (Reconnecting - In Main Menu)""")
            reconnect_start_button = self.config.get("reconnect_start_button", [954, 876])
            max_clicks = 25
            failed_clicks = 0

            for _ in range(8):
                if not self.detection_running: return
                self.activate_roblox_window()
                time.sleep(0.35)

            for _ in range(max_clicks):
                if not self.detection_running: return
                self.Global_MouseClick(reconnect_start_button[0], reconnect_start_button[1])
                time.sleep(0.95)

                # Check reconnect state in the logs
                if self.reconnect_logs_state():
                    self.send_webhook_status("Clicked 'Start' button and you are in the game now!!", color=0x4aff65)
                    print("Game has started, exiting click loop.")
                    self.detection_running = True
                    self.set_title_threadsafe("""Coteab Macro v2.0.1 (Running)""")
                    return True  # yay joins!!

                print("Still in Main Menu, clicking again...")
                failed_clicks += 1

                # Fallback if stuck in "In Main Menu" screen
                if failed_clicks >= 25:
                    print("Fallback: Stuck in 'In Main Menu' for too long. What is this skibidi")
                    return False

        except Exception as e:
            self.error_logging(e, "Error in reconnect_check_start_button function.")

        return False

    def reconnect_logs_state(self):
        try:
            log_file_path = self.get_latest_log_file()
            log_lines = self.read_full_log_file(log_file_path)

            for line in reversed(log_lines):
                if re.search(r'"state":"Equipped', line): return True

        except Exception as e:
            self.error_logging(e, "Error in reconnect_logs_state function.")

        return False

    def check_roblox_procs(self):
        try:
            current_user = psutil.Process().username()
            running_processes = psutil.process_iter(['pid', 'name', 'username'])
            roblox_processes = []

            for proc in running_processes:
                if proc.info['name'] in ['RobloxPlayerBeta.exe', 'Windows10Universal.exe'] and proc.info[
                    'username'] == current_user:
                    roblox_processes.append(proc.info)

            if roblox_processes: return True

        except Exception as e:
            self.error_logging(e, "Error in check_roblox_procs function.")

        return False  # no Roblox processes are found

    def terminate_roblox_processes(self):
        try:
            current_user = psutil.Process().username()
            running_processes = psutil.process_iter(['pid', 'name', 'username'])

            for proc in running_processes:
                if proc.info['name'] in ['RobloxPlayerBeta.exe', 'Windows10Universal.exe'] and proc.info[
                    'username'] == current_user:
                    print(f"Terminating process: {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.terminate()
                    proc.wait()

        except Exception as e:
            self.error_logging(e, "Error in terminate_roblox_processes function.")

    def auto_biome_change(self):
        try:
            mt_cooldown = timedelta(minutes=int(self.mt_duration_var.get()) if self.mt_duration_var.get() else 1)
        except ValueError:
            mt_cooldown = timedelta(minutes=1)

        try:
            self.perform_periodic_aura_screenshot_sync()
        except Exception:
            pass

        try:
            self.perform_periodic_inventory_screenshot_sync()
        except Exception:
            pass

        if self.mt_var.get() and datetime.now() - self.last_mt_time >= mt_cooldown and not getattr(self,
                                                                                                    '_br_sc_running',
                                                                                                    False) and not getattr(
                        self, '_mt_running', False) and not getattr(self, '_remote_running', False) and datetime.now() >= getattr(self, '_cancel_next_actions_until',
                                                                                datetime.min):
            self.use_merchant_teleporter()
            self.last_mt_time = datetime.now()

        try:
            sc_cooldown = timedelta(minutes=int(self.sc_duration_var.get()) if self.sc_duration_var.get() else 20)
        except ValueError:
            sc_cooldown = timedelta(minutes=20)

        if self.sc_var.get() and datetime.now() - self.last_sc_time >= sc_cooldown and not getattr(self,
                                                                                                        '_merchant_pending_from_logs',
                                                                                                        False) and not getattr(
                        self, '_mt_running', False) and not getattr(self, '_remote_running', False) and not self.on_auto_merchant_state and datetime.now() >= getattr(self,
                                                                                                                    '_cancel_next_actions_until',
                                                                                                                    datetime.min):
            self.use_br_sc('strange controller')
            self.last_sc_time = datetime.now()

        try:
            br_cooldown = timedelta(minutes=int(self.br_duration_var.get()) if self.br_duration_var.get() else 35)
        except ValueError:
            br_cooldown = timedelta(minutes=35)

        if self.br_var.get() and datetime.now() - self.last_br_time >= br_cooldown and not getattr(self,
                                                                                                   '_merchant_pending_from_logs',
                                                                                                   False) and not getattr(
                self, '_mt_running', False) and not self.on_auto_merchant_state and datetime.now() >= getattr(self,
                                                                                                              '_cancel_next_actions_until',
                                                                                                              datetime.min):
            self.use_br_sc('biome randomizer')
            self.last_br_time = datetime.now()

    def perform_periodic_aura_screenshot_sync(self):
        try:
            if not getattr(self, "periodical_aura_var", None) or not self.periodical_aura_var.get():
                return
            try:
                interval_min = float(self.periodical_aura_interval_var.get())
            except Exception:
                interval_min = 5.0
            if (datetime.now() - getattr(self, "last_aura_screenshot_time", datetime.min)) < timedelta(minutes=interval_min):
                return
            if not self.check_roblox_procs():
                return
            self.activate_roblox_window()
            aura_menu = self.config.get("aura_menu", [0, 0])
            search_bar = self.config.get("search_bar", [855, 358])
            if aura_menu and aura_menu[0]:
                try:
                    autoit.mouse_click("left", aura_menu[0], aura_menu[1], 1, speed=3)
                    time.sleep(0.67)
                    autoit.mouse_click("left", search_bar[0], search_bar[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(aura_menu[0], aura_menu[1])
                        time.sleep(0.67)
                        self.Global_MouseClick(search_bar[0], search_bar[1])
                    except Exception:
                        pass
                time.sleep(0.67)
                try:
                    os.makedirs("images", exist_ok=True)
                    filename = os.path.join("images", f"aura_screenshot_{int(time.time())}.png")
                    img = pyautogui.screenshot()
                    img.save(filename)
                    self.send_aura_screenshot_webhook(filename)
                    self.last_aura_screenshot_time = datetime.now()
                except Exception as e:
                    self.error_logging(e, "Error taking/sending aura screenshot")
        except Exception as e:
            self.error_logging(e, "Error in perform_periodic_aura_screenshot_sync")

    def perform_periodic_inventory_screenshot_sync(self):
        try:
            if not getattr(self, "periodical_inventory_var", None) or not self.periodical_inventory_var.get():
                return
            try:
                interval_min = float(self.periodical_inventory_interval_var.get())
            except Exception:
                interval_min = 5.0
            if (datetime.now() - getattr(self, "last_inventory_screenshot_time", datetime.min)) < timedelta(minutes=interval_min):
                return
            if not self.check_roblox_procs():
                return
            self.activate_roblox_window()
            search_bar = self.config.get("search_bar", [855, 358])
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
            if inventory_menu and inventory_menu[0]:
                try:
                    autoit.mouse_click("left", inventory_menu[0], inventory_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                    except Exception:
                        pass
                time.sleep(0.35)
            if items_tab and items_tab[0]:
                try:
                    autoit.mouse_click("left", items_tab[0], items_tab[1], 1, speed=3)
                    time.sleep(1)
                    autoit.mouse_click("left", search_bar[0], search_bar[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(items_tab[0], items_tab[1])
                    except Exception:
                        pass
                time.sleep(0.35)
            try:
                os.makedirs("images", exist_ok=True)
                filename = os.path.join("images", f"inventory_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_inventory_screenshot_webhook(filename)
                self.last_inventory_screenshot_time = datetime.now()
            except Exception as e:
                self.error_logging(e, "Error taking/sending inventory screenshot")
            try:
                if inventory_close_button and inventory_close_button[0]:
                    try:
                        autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        except Exception:
                            pass
                    time.sleep(0.22)
            except Exception as e:
                self.error_logging(e, "Error while closing inventory after screenshot")
        except Exception as e:
            self.error_logging(e, "Error in perform_periodic_inventory_screenshot_sync")

    def send_inventory_screenshot_webhook(self, screenshot_path):
        try:
            urls = self.get_webhook_list()
            if not urls:
                return
            content = ""
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)
            embed = {
                "description": f"> ## Periodical Inventory Screenshot",
                "color": 0xffffff,
                "footer": {"text": "Coteab Macro v2.0.1", "icon_url": icon_url},
                "timestamp": current_utc_time
            }
            for webhook_url in urls:
                try:
                    embed_copy = dict(embed)
                    embed_copy["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}
                    with open(screenshot_path, "rb") as image_file:
                        files = {"file": (os.path.basename(screenshot_path), image_file, "image/png")}
                        data = {"payload_json": json.dumps({"content": content, "embeds": [embed_copy]})}
                        requests.post(webhook_url, data=data, files=files, timeout=10)
                except Exception as e:
                    try:
                        print(f"Failed to send inventory screenshot to {webhook_url}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            self.error_logging(e, "Error in send_inventory_screenshot_webhook")

    def send_aura_screenshot_webhook(self, screenshot_path):
        try:
            urls = self.get_webhook_list()
            if not urls:
                return
            content = ""
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)
            embed = {
                "description": f"> ## Periodical Aura Screenshot",
                "color": 0xffffff,
                "footer": {"text": "Coteab Macro v2.0.1", "icon_url": icon_url},
                "timestamp": current_utc_time
            }
            for webhook_url in urls:
                try:
                    embed_copy = dict(embed)
                    embed_copy["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}
                    with open(screenshot_path, "rb") as image_file:
                        files = {"file": (os.path.basename(screenshot_path), image_file, "image/png")}
                        data = {"payload_json": json.dumps({"content": content, "embeds": [embed_copy]})}
                        requests.post(webhook_url, data=data, files=files, timeout=10)
                except Exception as e:
                    try:
                        print(f"Failed to send aura screenshot to {webhook_url}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            self.error_logging(e, "Error in send_aura_screenshot_webhook")

    def Global_MouseClick(self, x, y, click=1):
        time.sleep(0.335)
        autoit.mouse_click("left", x, y, click, speed=3)
        
    def use_br_sc(self, item_name):
        try:
            self._action_scheduler.enqueue_action(lambda: self._use_br_sc_impl(item_name), name=f"use_br_sc:{item_name}", priority=1)
        except Exception:
            try:
                self._use_br_sc_impl(item_name)
            except Exception:
                pass

    def _use_br_sc_impl(self, item_name):
        self._br_sc_running = True
        try:
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED" or getattr(self, '_merchant_pending_from_logs',
                                                                                    False) or getattr(self,
                                                                                                      '_mt_running',
                                                                                                      False): return
            time.sleep(1.3)

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            search_bar = self.config.get("search_bar", [855, 358])
            first_item_slot = self.config.get("first_item_slot", [839, 434])
            amount_box = self.config.get("amount_box", [594, 570])
            use_button = self.config.get("use_button", [710, 573])
            aura_menu = self.config.get("aura_menu", [1200, 500])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])

            for _ in range(5):
                if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                    "enable_auto_craft") or self.current_biome == "GLITCHED": return
                self.activate_roblox_window()
                time.sleep(0.15)

            print(f"Using {item_name.capitalize()}")

            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            time.sleep(0.2 + inventory_click_delay)
            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.23)
            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.23)
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.2 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return

            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.23)
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.23)
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.2 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            autoit.send(item_name)
            time.sleep(0.4 + inventory_click_delay)
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            time.sleep(0.4 + inventory_click_delay)
            try:
                if not self._ocr_first_slot_matches(item_name):
                    inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    time.sleep(0.15 + inventory_click_delay)
                    return
            except Exception:
                pass
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            time.sleep(0.4 + inventory_click_delay)
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            time.sleep(0.3 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            self.Global_MouseClick(amount_box[0], amount_box[1])
            time.sleep(0.16 + inventory_click_delay)
            autoit.send("^{a}")
            time.sleep(0.13 + inventory_click_delay)
            autoit.send("{BACKSPACE}")
            time.sleep(0.13 + inventory_click_delay)
            autoit.send('1')
            time.sleep(0.13 + inventory_click_delay)

            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            self.Global_MouseClick(use_button[0], use_button[1])
            time.sleep(0.22 + inventory_click_delay)

            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
            time.sleep(0.22 + inventory_click_delay)

        except Exception as e:
            self.error_logging(e, "Error in use_br_sc function.")
        finally:
            self._br_sc_running = False
            if getattr(self, '_merchant_pending_from_logs', False) and self.mt_var.get():
                try:
                    self.append_log("[Merchant Detection] Using pending merchant teleporter after BR/SC.")
                    self.use_merchant_teleporter()
                    self.last_mt_time = datetime.now()
                    self._merchant_pending_from_logs = False
                    self._merchant_pending_name = None
                except Exception as e:
                    self.error_logging(e, "Failed to use merchant teleporter after BR/SC")

    def use_merchant_teleporter(self):
        try:
            self._action_scheduler.enqueue_action(self._merchant_teleporter_impl, name="merchant_tele", priority=0)
        except Exception:
            try:
                self._merchant_teleporter_impl()
            except Exception:
                pass

    def _merchant_teleporter_impl(self):
        if getattr(self, '_br_sc_running', False): return
        self._mt_running = True
        try:
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            time.sleep(0.75)

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            search_bar = self.config.get("search_bar", [855, 358])
            first_item_slot = self.config.get("first_item_slot", [839, 434])
            amount_box = self.config.get("amount_box", [594, 570])
            use_button = self.config.get("use_button", [710, 573])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])

            for _ in range(3):
                if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                    "enable_auto_craft") or self.current_biome == "GLITCHED": return
                self.activate_roblox_window()
                time.sleep(0.3)

            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            time.sleep(0.24 + inventory_click_delay)

            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.23)
            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.23)
            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.24 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return

            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.23)
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.23)
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.27 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            autoit.send("teleport")
            time.sleep(0.4 + inventory_click_delay)
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            time.sleep(0.4 + inventory_click_delay)
            try:
                if not self._ocr_first_slot_matches("teleport"):
                    inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    time.sleep(0.15 + inventory_click_delay)
                    return
            except Exception:
                pass
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            time.sleep(0.4 + inventory_click_delay)
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            time.sleep(0.4 + inventory_click_delay)

            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return

            time.sleep(0.17 + inventory_click_delay)
            self.Global_MouseClick(amount_box[0], amount_box[1])
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            autoit.send("^{a}")
            time.sleep(0.15 + inventory_click_delay)
            autoit.send("{BACKSPACE}")
            time.sleep(0.15 + inventory_click_delay)
            autoit.send('1')
            time.sleep(0.14 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return
            autoit.mouse_click("left", use_button[0], use_button[1], 3)
            time.sleep(0.23 + inventory_click_delay)

            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
            time.sleep(0.23 + inventory_click_delay)
            self.Merchant_Handler()

            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return

            time.sleep(0.33 + inventory_click_delay)
            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            time.sleep(0.33 + inventory_click_delay)
            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
            if getattr(self, "auto_merchant_in_limbo_var", None) and self.auto_merchant_in_limbo_var.get():
                try:
                    time.sleep(0.33 + inventory_click_delay)
                    self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                    time.sleep(0.24 + inventory_click_delay)
                    self.Global_MouseClick(items_tab[0], items_tab[1])
                    time.sleep(0.23 + inventory_click_delay)
                    self.Global_MouseClick(search_bar[0], search_bar[1])
                    time.sleep(0.23 + inventory_click_delay)
                    self.Global_MouseClick(search_bar[0], search_bar[1])
                    time.sleep(0.15 + inventory_click_delay)
                    self.Global_MouseClick(search_bar[0], search_bar[1])
                    time.sleep(0.15 + inventory_click_delay)
                    autoit.send("crack")
                    time.sleep(0.4 + inventory_click_delay)
                    self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
                    time.sleep(0.4 + inventory_click_delay)
                    self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
                    time.sleep(0.4 + inventory_click_delay)
                    self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
                    time.sleep(0.3 + inventory_click_delay)
                    self.Global_MouseClick(amount_box[0], amount_box[1])
                    time.sleep(0.16 + inventory_click_delay)
                    autoit.send("^{a}")
                    time.sleep(0.13 + inventory_click_delay)
                    autoit.send("{BACKSPACE}")
                    time.sleep(0.13 + inventory_click_delay)
                    autoit.send('1')
                    time.sleep(0.13 + inventory_click_delay)
                    self.Global_MouseClick(use_button[0], use_button[1])
                    time.sleep(0.22 + inventory_click_delay)
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    time.sleep(0.22 + inventory_click_delay)
                except Exception as e:
                    self.error_logging(e, "Error using portable Crack after merchant teleporter")

        except Exception as e:
            self.error_logging(e, "Error in use_merchant_teleporter function.")
        finally:
            self._mt_running = False
            self._merchant_pending_from_logs = False
            self._merchant_pending_name = None
            self._cancel_next_actions_until = datetime.min

    def Merchant_Handler(self):
        try:
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.config.get(
                "enable_auto_craft") or self.current_biome == "GLITCHED": return

            self.on_auto_merchant_state = True
            merchant_name_ocr_pos = self.config["merchant_name_ocr_pos"]
            merchant_open_button = self.config["merchant_open_button"]
            first_item_slot_pos = self.config["first_item_slot_pos"]
            item_name_ocr_pos = self.config["item_name_ocr_pos"]
            merchant_dialogue_box = self.config["merchant_dialogue_box"]
            merchant_extra_slot = int(self.config.get("merchant_extra_slot", "0"))

            merchant_name = ""
            ocrMisdetect_Key = {
                "heovenly potion": "heavenly potion",
                "heovenly potion!": "heavenly potion",
                "heavenly potion": "heavenly potion",
                "heavenly potion!": "heavenly potion",
                "rune of goloxy": "rune of galaxy",
                "rune of roinstorm": "rune of rainstorm",
                "stronge potion": "strange potion",
                "stello's condle": "stella's candle",
                "merchont trocker": "merchant tracker",
                "rondom potion sock": "random potion sack",
                "geor a": "gear a",
                "geor b": "gear b"
            }

            if not hasattr(self, 'last_merchant_interaction'):
                self.last_merchant_interaction = 0

            if not hasattr(self, 'last_merchant_sent'):
                self.last_merchant_sent = {}

            merchant_cooldown_time = 300
            current_time = time.time()

            if current_time - self.last_merchant_interaction < merchant_cooldown_time: return

            for _ in range(6):
                if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.config.get(
                    "enable_auto_craft") or self.current_biome == "GLITCHED": return
                autoit.send("e")
                time.sleep(0.55)

            time.sleep(0.65)

            self.autoit_hold_left_click(merchant_dialogue_box[0], merchant_dialogue_box[1], holdTime=4250)

            for _ in range(6):
                if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.config.get(
                    "enable_auto_craft") or self.current_biome == "GLITCHED": return

                x, y, w, h = merchant_name_ocr_pos
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
                merchant_name_text = pytesseract.image_to_string(screenshot, config='--psm 6').strip()
                if any(name in merchant_name_text for name in
                       ["Mari", "Mori", "Marl", "Mar1", "MarI", "Mar!", "Maori"]):
                    merchant_name = "Mari"
                    print("[Merchant Detection]: Mari name found!")
                    break
                elif any(name in merchant_name_text for name in
                         ["Jester", "Dester", "Jostor", "Jestor", "Joster", "Destor", "Doster", "Dostor", "jester", "dester"]):
                    merchant_name = "Jester"
                    print("[Merchant Detection]: Jester name found!")
                    break

                time.sleep(0.12)

            if merchant_name:
                last_sent_time = self.last_merchant_sent.get((merchant_name, 'ocr'), 0)
                if current_time - last_sent_time < merchant_cooldown_time:
                    print(f"Merchant {merchant_name} already sent recently lol")
                    return

                print(f"Opening merchant interface for {merchant_name}")

                x, y = merchant_open_button
                autoit.mouse_click("left", x, y, 3)
                time.sleep(2)

                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)

                item_screenshot = pyautogui.screenshot()
                screenshot_path = os.path.join(screenshot_dir,
                                               f"merchant_{merchant_name.lower()}_{int(current_time)}.png")
                item_screenshot.save(screenshot_path)

                self.send_merchant_webhook(merchant_name, screenshot_path, source='ocr')
                self.last_merchant_sent[(merchant_name, 'ocr')] = current_time

                auto_buy_items = self.config.get(f"{merchant_name}_Items", {})
                if not auto_buy_items: return
                purchased_items = {}

                total_slots = 5 + merchant_extra_slot
                for slot_index in range(total_slots):
                    if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.config.get(
                        "enable_auto_craft") or self.current_biome == "GLITCHED": return

                    x, y = first_item_slot_pos
                    slot_x = x + (slot_index * 193)
                    autoit.mouse_click("left", slot_x, y, 2)
                    time.sleep(0.15)

                    x, y, w, h = item_name_ocr_pos
                    screenshot = pyautogui.screenshot(region=(x, y, w, h))
                    item_text = pytesseract.image_to_string(screenshot, config='--psm 6').strip().lower()

                    self.append_log(f"[Merchant Detection - {merchant_name}] Detected item text: {item_text}")

                    corrected_item_name = item_text.split('|')[0].strip()
                    for misdetect, correct in ocrMisdetect_Key.items():
                        if misdetect in corrected_item_name:
                            corrected_item_name = correct
                            print(f"Corrected OCR misdetection: '{item_text}' -> '{correct}'")
                            break

                    print(f"Detected item text: {item_text} | Corrected: {corrected_item_name}")

                    for item_name, (enabled, quantity, rebuy) in auto_buy_items.items():
                        if enabled and corrected_item_name == item_name.lower():
                            purchased_count = purchased_items.get(item_name, 0)

                            if rebuy or purchased_count == 0:
                                self.append_log(
                                    f"[Merchant Detection - {merchant_name}] - Item {item_name} found. Proceeding to buy {quantity}")

                                purchase_amount_button = self.config["purchase_amount_button"]
                                purchase_button = self.config["purchase_button"]
                                hold_time = 5250

                                autoit.mouse_click("left", *purchase_amount_button)
                                autoit.send(str(quantity))
                                time.sleep(0.23)

                                autoit.mouse_click("left", *purchase_button, 3)
                                time.sleep(3.67)  # 6 7 TUFF

                                if merchant_name == "Jester" and item_name.lower() == "oblivion potion": hold_time = 8300
                                self.autoit_hold_left_click(merchant_dialogue_box[0], merchant_dialogue_box[1],
                                                            holdTime=hold_time)

                                purchased_items[item_name] = purchased_count + 1
                                break

                self.last_merchant_interaction = current_time
            else:
                print("No merchant detected.")

        except Exception as e:
            self.error_logging(e,
                               "Error in Merchant_Handler function \n (If it say valueError: not enough values to unpack (expect 3 got 2) then open both mari and jester setting and click save selection again!)")
        finally:
            self.on_auto_merchant_state = False

    def send_webhook(self, biome, message_type, event_type):
        urls = self.get_webhook_list()
        if not urls:
            print("Webhook URL is missing/not included in the config.json")
            return
        if message_type == "None": return
        biome_info = self.biome_data[biome]
        biome_color = int(biome_info["color"], 16)
        current_utc_time = datetime.now(timezone.utc)
        current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
        current_utc_time = str(current_utc_time)
        icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
        content = ""
        if event_type == "start" and biome in ["GLITCHED", "DREAMSPACE", "CYBERSPACE"]:
            content = "@everyone"
        private_server_link = self.config.get("private_server_link").replace("\n", "")
        if private_server_link == "":
            description = f"> ## Biome Started - {biome} \nNo link provided (ManasAarohi ate the link blame him)" if event_type == "start" else f"> ### Biome Ended - {biome}"
        else:
            description = f"> ## Biome Started - {biome} \n> ### **[Join Server]({private_server_link})**" if event_type == "start" else f"> ### Biome Ended - {biome}"
        embed = {
            "description": description,
            "color": biome_color,
            "footer": {
                "text": """Coteab Macro v2.0.1""",
                "icon_url": icon_url
            },
            "timestamp": current_utc_time
        }
        if event_type == "start":
            embed["thumbnail"] = {"url": biome_info["thumbnail_url"]}
        payload = {
            "content": content,
            "embeds": [embed]
        }
        for webhook_url in urls:
            try:
                response = requests.post(webhook_url, json=payload)
                response.raise_for_status()
                print(f"[Line 1744] Sent {message_type} for {biome} - {event_type} to {webhook_url}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to send webhook to {webhook_url}: {e}")

    def send_merchant_webhook(self, merchant_name, screenshot_path=None, source='ocr'):
        urls = self.get_webhook_list()
        if not urls:
            print("Webhook URL is missing/not included in the config.json")
            return
        merchant_thumbnails = {
            "Mari": "https://raw.githubusercontent.com/vexthecoder/OysterDetector/refs/heads/main/mari.png",
            "Jester": "https://raw.githubusercontent.com/vexthecoder/OysterDetector/refs/heads/main/jester.png"
        }
        if merchant_name == "Mari":
            ping_id = self.mari_user_id_var.get() if hasattr(self, 'mari_user_id_var') else self.config.get(
                "mari_user_id", "")
            ping_enabled = self.ping_mari_var.get() if hasattr(self, 'ping_mari_var') else self.config.get("ping_mari",
                                                                                                           False)
        elif merchant_name == "Jester":
            ping_id = self.jester_user_id_var.get() if hasattr(self, 'jester_user_id_var') else self.config.get(
                "jester_user_id", "")
            ping_enabled = self.ping_jester_var.get() if hasattr(self, 'ping_jester_var') else self.config.get(
                "ping_jester", False)
        else:
            ping_id = ""
            ping_enabled = False
        content = f"<@{ping_id}>" if (source == 'logs', 'ocr' and ping_enabled and ping_id) else ""
        ps_link = self.config.get("private_server_link", "").replace("\n", "")
        icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
        current_utc_time = datetime.now(timezone.utc)
        current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
        current_utc_time = str(current_utc_time)
        embed = {
            "description": f"> ## {merchant_name} has arrived!\n> ### [Join Server]({ps_link})",
            "color": 11753 if merchant_name == "Mari" else 8595632,
            "thumbnail": {"url": merchant_thumbnails.get(merchant_name, "")},
            "timestamp": current_utc_time,
            "fields": [
                {"name": "Detection Source", "value": source.upper()}
            ],
            "footer": {
                "text": """Coteab Macro v2.0.1""",
                "icon_url": icon_url
            }
        }
        try:
            if screenshot_path and os.path.exists(screenshot_path):
                for webhook_url in urls:
                    embed["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}
                    with open(screenshot_path, "rb") as image_file:
                        files = {"file": (os.path.basename(screenshot_path), image_file, "image/png")}
                        response = requests.post(
                            webhook_url,
                            data={
                                "payload_json": json.dumps({
                                    "content": content,
                                    "embeds": [embed]
                                })
                            },
                            files=files
                        )
                        try:
                            response.raise_for_status()
                            print(
                                f"Webhook sent successfully for {merchant_name} to {webhook_url}: {response.status_code}")
                        except requests.exceptions.RequestException as e:
                            print(f"Failed to send merchant webhook to {webhook_url}: {e}")
            else:
                payload = {"content": content, "embeds": [embed]}
                for webhook_url in urls:
                    try:
                        response = requests.post(webhook_url, json=payload)
                        response.raise_for_status()
                        print(f"Webhook sent successfully for {merchant_name} to {webhook_url}: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        print(f"Failed to send merchant webhook to {webhook_url}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to send merchant webhook: {e}")

    def check_eden_in_logs(self, log_file_path):
        try:
            if self.reconnecting_state:
                return
            if not hasattr(self, 'last_eden_sent'):
                self.last_eden_sent = 0

            eden_phrase = "The Devourer of the Void,"
            cooldown = 300
            current_time = time.time()
            if (current_time - self.last_eden_sent) < cooldown:
                return
            log_lines = self.read_log_file_for_detector(log_file_path, pos_attr='last_position_eden', filter_chat=False)
            if not log_lines:
                return
            max_lines = int(self.config.get("eden_log_tail", 35))
            recent = log_lines[-max_lines:] if len(log_lines) > max_lines else log_lines

            for line in reversed(recent):
                if eden_phrase in line:
                    try:
                        self.send_eden_webhook()
                        self.last_eden_sent = current_time
                        self.append_log("[Eden Detection] Eden detected from logs.")
                    except Exception as e:
                        self.error_logging(e, "Failed to send eden webhook")
                    return

        except Exception as e:
            self.error_logging(e, "Error in check_eden_in_logs function")

    def send_eden_webhook(self):
        urls = self.get_webhook_list()
        if not urls:
            print("Webhook URL is missing/not included in the config.json")
            return
        eden_image = "https://raw.githubusercontent.com/vexthecoder/OysterDetector/refs/heads/main/eden.png"
        aura_user_id = self.aura_user_id_var.get() if hasattr(self, 'aura_user_id_var') else self.config.get(
            "aura_user_id", "")
        content = f"<@{aura_user_id}>" if aura_user_id else ""
        icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
        embed = {
            "title": "Eden Detected!",
            "description": f"The Devourer of the Void, Eden has appeared somewhere in The Limbo.",
            "color": 000000,
            "thumbnail": {"url": eden_image},
            "footer": {
                "text": """Coteab Macro v2.0.1""",
                "icon_url": icon_url
            }
        }
        payload = {"content": content, "embeds": [embed]}
        for webhook_url in urls:
            try:
                response = requests.post(webhook_url, json=payload)
                response.raise_for_status()
                print(f"Eden webhook sent to {webhook_url}")
            except requests.exceptions.RequestException as e:
                print(f"Failed to send eden webhook to {webhook_url}: {e}")

    def send_aura_webhook(self, aura_name, rarity, biome_message, screenshot_path=None):
        urls = self.get_webhook_list()
        if not urls:
            print("Webhook URL is missing/not included in the config.json")
            return
        icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
        ping_minimum = int(self.config.get("ping_minimum", "100000"))
        color = 0xffffff
        if rarity is not None:
            rarity_value = int(rarity.replace(',', ''))
            if 99000 <= rarity_value < 1000000:
                color = 0x3dd3e0
            elif 1000000 <= rarity_value < 10000000:
                color = 0xff73ec
            elif 10000000 <= rarity_value < 99000000:
                color = 0x2d30f7
            elif 99000000 <= rarity_value < 1000000000:
                color = 0xed2f59
            else:
                color = 0xff9447
            description = f"> ## Aura equipped: {aura_name} | 1 in {rarity} {biome_message}"
        else:
            description = f"> ## Aura equipped: {aura_name}"
        current_utc_time = datetime.now(timezone.utc)
        current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
        current_utc_time = str(current_utc_time)
        embed = {
            "title": "⭐ Aura Detection ⭐",
            "description": description,
            "color": color,
            "footer": {
                "text": """Coteab Macro v2.0.1""",
                "icon_url": icon_url
            },
            "timestamp": current_utc_time
        }
        content = ""
        if rarity is not None and 'rarity_value' in locals() and rarity_value >= ping_minimum:
            aura_user_id = self.config.get("aura_user_id", "")
            if aura_user_id:
                content = f"<@{aura_user_id}>"
        try:
            if screenshot_path and os.path.exists(screenshot_path):
                for webhook_url in urls:
                    embed_copy = dict(embed)
                    embed_copy["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}
                    with open(screenshot_path, "rb") as image_file:
                        files = {"file": (os.path.basename(screenshot_path), image_file, "image/png")}
                        data = {"payload_json": json.dumps({"content": content, "embeds": [embed_copy]})}
                        try:
                            response = requests.post(webhook_url, data=data, files=files, timeout=10)
                            response.raise_for_status()
                            print(f"Aura webhook with screenshot sent for {aura_name} to {webhook_url}")
                        except requests.exceptions.RequestException as e:
                            print(f"Failed to send aura webhook with screenshot to {webhook_url}: {e}")
            else:
                payload = {"content": content, "embeds": [embed]}
                for webhook_url in urls:
                    try:
                        response = requests.post(webhook_url, json=payload, timeout=10)
                        response.raise_for_status()
                        print(f"Aura webhook sent for {aura_name} to {webhook_url}")
                    except requests.exceptions.RequestException as e:
                        print(f"Failed to send aura webhook to {webhook_url}: {e}")
        except Exception as e:
            self.error_logging(e, "Error in send_aura_webhook")

    def send_webhook_status(self, status, color=None):
        try:
            urls = self.get_webhook_list()
            if not urls:
                print("Webhook URL is missing/not included in the config.json")
                return
            default_color = 3066993 if "started" in status.lower() else 15158332
            embed_color = color if color is not None else default_color
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            if "started" in status.lower():
                n = len(urls)
                status = f"{status} ({n} webhook{'s' if n != 1 else ''} active)"
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)
            embeds = [{
                "title": "== 🌟 Macro Status 🌟 ==",
                "description": f"> ## {status}",
                "color": embed_color,
                "timestamp": current_utc_time,
                "footer": {
                    "text": "Coteab Macro v2.0.1",
                    "icon_url": icon_url
                },
                "fields": [
                    {
                        "name": "Join our Discord:",
                        "value": "https://discord.gg/fw6q274Nrt",
                        "inline": False
                    }
                ]
            }]
            for webhook_url in urls:
                try:
                    response = requests.post(webhook_url, json={"embeds": embeds}, timeout=8)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    print(f"Failed to send webhook status to {webhook_url}: {e}")
        except Exception as e:
            print(f"An error occurred in webhook_status: {e}")

    def send_macro_summary(self, last24h_seconds, reason_text="Macro stopped!"):
        try:
            last24h_str = self.format_seconds_to_hhmmss(min(int(last24h_seconds), 86400))
            session_str = self.format_seconds_to_hhmmss(int(self.current_session))
            urls = self.get_webhook_list()
            if not urls:
                return
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)
            embed = {
                "title": "== 🌟 Macro Status 🌟 ==",
                "description": f"> ## {reason_text} Here is your session summary:",
                "color": 0xff0000,
                "timestamp": current_utc_time,
                "footer": {
                    "text": "Coteab Macro v2.0.1",
                    "icon_url": icon_url
                },
                "fields": [
                    {
                        "name": "Session Times",
                        "value": f"- in the last 24 hours: {last24h_str}\n- in this session: {session_str}",
                        "inline": False
                    },
                    {
                        "name": "Join our Discord:",
                        "value": "https://discord.gg/fw6q274Nrt",
                        "inline": False
                    }
                ]
            }
            payload = {"embeds": [embed]}
            for webhook_url in urls:
                try:
                    requests.post(webhook_url, json=payload, timeout=5)
                except Exception:
                    pass
        except Exception as e:
            self.error_logging(e, "Error in send_macro_summary")

    def _set_first_item_slot_ocr_pos(self, region):
        self.config["first_item_slot_ocr_pos"] = region
        try:
            self.first_item_slot_ocr_label.config(text=str(region))
        except Exception:
            pass
        self.save_config()

    def _ocr_first_slot_matches(self, expected):
        if not self.config.get("enable_ocr_failsafe", False):
            return True
        ocr_pos = self.config.get("first_item_slot_ocr_pos", [0, 0, 80, 80])
        try:
            x, y, w, h = int(ocr_pos[0]), int(ocr_pos[1]), int(ocr_pos[2]), int(ocr_pos[3])
            img = pyautogui.screenshot(region=(x, y, w, h))
            text = pytesseract.image_to_string(img).strip().lower()
        except Exception:
            text = ""
        expected_lower = (expected or "").lower()
        if expected_lower and expected_lower in text:
            return True
        tokens = re.findall(r'\w{4,}', expected_lower)
        for t in tokens:
            if t in text:
                return True
        return False

    def activate_roblox_window(self):
        windows = gw.getAllTitles()
        roblox_window = None

        for window in windows:
            if "Roblox" in window:
                roblox_window = gw.getWindowsWithTitle(window)[0]
                break

        if roblox_window:
            try:
                roblox_window.activate()
            except Exception as e:
                print(f"Failed to activate window: {e}")
        else:
            print("Roblox window not found.")

    def _find_roblox_hwnds(self):
        pids = set()
        try:
            current_user = psutil.Process().username()
        except Exception:
            current_user = None
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    if proc.info['name'] in ['RobloxPlayerBeta.exe', 'Windows10Universal.exe'] and (
                            current_user is None or proc.info.get('username') == current_user):
                        pids.add(proc.info['pid'])
                except Exception:
                    pass
        except Exception:
            pass
        hwnds = []
        try:
            def enum_cb(hwnd, lparam):
                try:
                    if not win32gui.IsWindowVisible(hwnd) or not win32gui.IsWindowEnabled(hwnd):
                        return True
                    tid, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid in pids:
                        hwnds.append(hwnd)
                except Exception:
                    pass
                return True

            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        return hwnds

    def _focus_window_hwnd(self, hwnd, max_attempts=20, sleep_between=0.25):
        attempt = 0
        while self.detection_running and attempt < max_attempts:
            attempt += 1
            try:
                if win32gui.IsIconic(hwnd):
                    try:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    except Exception:
                        pass
                fg = win32gui.GetForegroundWindow()
                if fg == hwnd:
                    return True
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    try:
                        fg_hwnd = win32gui.GetForegroundWindow()
                        foreground_tid = win32process.GetWindowThreadProcessId(fg_hwnd)[0]
                        target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
                        current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
                        try:
                            ctypes.windll.user32.AttachThreadInput(current_tid, foreground_tid, True)
                            ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, True)
                        except Exception:
                            pass
                        try:
                            win32gui.SetForegroundWindow(hwnd)
                        except Exception:
                            pass
                        try:
                            ctypes.windll.user32.AttachThreadInput(current_tid, foreground_tid, False)
                            ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, False)
                        except Exception:
                            pass
                    except Exception:
                        pass
                time.sleep(sleep_between)
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        try:
                            autoit.win_activate(title)
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(sleep_between)
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
                try:
                    pyautogui.keyDown('alt')
                    pyautogui.press('tab')
                    pyautogui.keyUp('alt')
                except Exception:
                    pass
                time.sleep(sleep_between)
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
            except Exception:
                pass
        return win32gui.GetForegroundWindow() == hwnd

    def perform_anti_afk_action(self):
        try:
            if not getattr(self, "anti_afk_var", None) or not self.anti_afk_var.get(): return
            if getattr(self, "br_var", None) and self.br_var.get(): return
            if getattr(self, "sc_var", None) and self.sc_var.get(): return
            if getattr(self, "mt_var", None) and self.mt_var.get(): return
            if getattr(self, "on_auto_merchant_state", False): return
            if getattr(self, "_br_sc_running", False): return
            if getattr(self, "_mt_running", False): return
            if not self.check_roblox_procs(): return
            try:
                hwnd_before = win32gui.GetForegroundWindow()
                title_before = win32gui.GetWindowText(hwnd_before)
            except Exception:
                hwnd_before = None
                title_before = ""
            roblox_hwnds = self._find_roblox_hwnds()
            if not roblox_hwnds:
                for t in gw.getAllTitles():
                    if "Roblox" in (t or ""):
                        wins = gw.getWindowsWithTitle(t)
                        if wins:
                            try:
                                if hasattr(wins[0], '_hWnd'):
                                    roblox_hwnds.append(wins[0]._hWnd)
                                else:
                                    h = win32gui.FindWindow(None, t)
                                    if h:
                                        roblox_hwnds.append(h)
                            except Exception:
                                pass
            if not roblox_hwnds:
                return
            target = roblox_hwnds[0]
            focused = False
            while self.detection_running and not focused:
                focused = self._focus_window_hwnd(target, max_attempts=4, sleep_between=0.35)
                if focused:
                    break
                time.sleep(0.35)
            if not focused:
                return
            try:
                autoit.send("{SPACE 3}")
            except Exception:
                try:
                    pyautogui.press("space", presses=3, interval=0.06)
                except Exception:
                    pass
            time.sleep(0.15)
            if hwnd_before and hwnd_before != win32gui.GetForegroundWindow():
                try:
                    win32gui.SetForegroundWindow(hwnd_before)
                except Exception:
                    try:
                        if title_before:
                            wins = gw.getWindowsWithTitle(title_before)
                            if wins:
                                wins[0].activate()
                    except Exception:
                        pass
        except Exception as e:
            try:
                self.error_logging(e, "Error in anti-afk")
            except Exception:
                pass

    def anti_afk_loop(self):
        interval = 6.7 * 60  # 67 TUFF
        while self.detection_running:
            time.sleep(interval)
            if not self.detection_running:
                break
            try:
                self.perform_anti_afk_action()
            except Exception as e:
                try:
                    self.error_logging(e, "Error in anti_afk_loop")
                except Exception:
                    pass

    def autoit_hold_left_click(self, posX, posY, holdTime=1):
        for _ in range(5):
            autoit.mouse_click("left", posX, posY, 2, speed=2)
            time.sleep(0.1)

    def get_scaled_coordinates(self, original_x, original_y):
        original_width = 1920
        original_height = 1080
        current_width, current_height = pyautogui.size()

        x_scale = current_width / original_width
        y_scale = current_height / original_height
        return int(original_x * x_scale), int(original_y * y_scale)

    def trigger_aura_record(self):
        def aura_record():
            try:
                # print("hi me running aura record")
                keybind = self.aura_record_keybind_var.get()
                keys = [key.strip() for key in keybind.split('+')]
                time.sleep(10)
                pyautogui.hotkey(*keys)
            except Exception as e:
                self.error_logging(e, "Error in trigger_aura_record")

        threading.Thread(target=aura_record).start()

    def trigger_biome_record(self):
        def record():
            try:
                # print("hi me running biome record")
                keybind = self.rarest_biome_keybind_var.get()
                keys = [key.strip() for key in keybind.split('+')]
                time.sleep(45)
                pyautogui.hotkey(*keys)
            except Exception as e:
                self.error_logging(e, "Error in trigger_biome_record")

        threading.Thread(target=record).start()

    # this dock was here

    def auto_pop_buffs(self):
        try:
            self._action_scheduler.enqueue_action(self._auto_pop_buffs_impl, name="auto_pop_buffs", priority=1)
        except Exception:
            try:
                self._auto_pop_buffs_impl()
            except Exception:
                pass

    def _auto_pop_buffs_impl(self):
        try:
            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0

            # Priority list for potions
            buffs_to_use = []
            priority_order = [
                "Xyz Potion",
                "Warp Potion",
                "Heavenly Potion",
                "Godlike Potion",
                "Potion of bound",
                "Oblivion Potion"
            ]

            # Priority potions
            for buff in priority_order:
                if buff in self.config.get("auto_buff_glitched", {}) and self.config["auto_buff_glitched"][buff][
                    0]:  # Check if enabled
                    amount = self.config["auto_buff_glitched"][buff][1]
                    buffs_to_use.append((buff, amount))

            # Remaining potions that are enabled but not in the priority order
            for buff, (enabled, amount) in self.config.get("auto_buff_glitched", {}).items():
                if enabled and buff not in priority_order:
                    buffs_to_use.append((buff, amount))

            warp_enabled = any(buff == "Warp Potion" for buff, _ in buffs_to_use)

            for buff, amount in buffs_to_use:
                if not self.detection_running or self.reconnecting_state: return
                print(f"Using {buff} x{amount}")

                self.send_webhook_status(f"Using x{amount} {buff} in GLITCHED", color=0x34ebab)

                additional_wait_time = 0
                if buff == "Oblivion Potion":
                    additional_wait_time = 0.85 * amount  # 0.85 seconds per potion
                    if warp_enabled:
                        additional_wait_time *= 0.12  # warp wait delay

                for _ in range(4):
                    if not self.detection_running or self.reconnecting_state: return
                    self.activate_roblox_window()
                    time.sleep(0.35)

                time.sleep(
                    0.57)  # wait atm before other macro actions like teleporter, biome random, strange controller stopped completely

                # Inventory menu
                inventory_menu = self.config.get("inventory_menu", [36, 535])
                inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                time.sleep(0.22 + inventory_click_delay)

                # Buff item
                search_bar = self.config.get("search_bar", [855, 358])
                self.Global_MouseClick(search_bar[0], search_bar[1], click=2)
                time.sleep(0.23 + inventory_click_delay)

                if not self.detection_running or self.reconnecting_state: return

                # name
                keyboard.write(buff.lower())
                time.sleep(0.22 + inventory_click_delay)

                first_item_slot = self.config.get("first_item_slot", [839, 434])
                self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
                time.sleep(0.22 + inventory_click_delay)
                try:
                    if not self._ocr_first_slot_matches(buff):
                        inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                        self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        time.sleep(0.15 + inventory_click_delay)
                        continue
                except Exception:
                    pass
                amount_box = self.config.get("amount_box", [594, 570])
                self.Global_MouseClick(amount_box[0], amount_box[1])
                time.sleep(0.22 + inventory_click_delay)


                if not self.detection_running or self.reconnecting_state: return

                # use cro
                autoit.send("^{a}")
                time.sleep(0.285 + inventory_click_delay)
                autoit.send("{BACKSPACE}")
                time.sleep(0.285 + inventory_click_delay)
                autoit.send(str(amount))
                time.sleep(0.285 + inventory_click_delay)

                # use??!
                use_button = self.config.get("use_button", [710, 573])
                self.Global_MouseClick(use_button[0], use_button[1])
                time.sleep(0.3 + inventory_click_delay)

                # close ts pmo icl :pray:
                self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                time.sleep(0.32 + inventory_click_delay)

                # additional wait time
                if additional_wait_time > 0: time.sleep(additional_wait_time)

        except Exception as e:
            self.error_logging(e, "Error in auto_pop_buffs function")

try:
    biome_presence = BiomePresence()
except KeyboardInterrupt:
    print("Exited (Keyboard Interrupted)")
finally:
    try:
        if 'biome_presence' in globals() and isinstance(biome_presence, BiomePresence):
            bp = biome_presence
            if getattr(bp, 'has_started_once', False):
                now = datetime.now()
                if bp.detection_running:
                    if bp.start_time:
                        elapsed = int((now - bp.start_time).total_seconds())
                    else:
                        elapsed = 0

                    session_seconds = elapsed

                    if bp.session_window_start and (now - bp.session_window_start).total_seconds() >= 86400:
                        last24h_seconds = session_seconds
                    else:
                        last24h_seconds = bp.saved_session + elapsed
                        if last24h_seconds > 86400:
                            last24h_seconds = 86400

                    bp.saved_session += elapsed
                    bp.start_time = None
                    bp.detection_running = False
                    bp.stop_sent = True
                    bp.set_title_threadsafe("""Coteab Macro v2.0.1 (Stopped)""")
                    bp.send_macro_summary(last24h_seconds)
                    bp.save_config()

                elif not getattr(bp, 'stop_sent', False):
                    session_seconds = 0
                    last24h_seconds = bp.saved_session
                    if last24h_seconds > 86400:
                        last24h_seconds = 86400
                    bp.stop_sent = True
                    bp.send_macro_summary(last24h_seconds)
                    bp.save_config()
    except Exception:
        pass
    finally:
        keyboard.unhook_all()
