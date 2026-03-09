from .base_support import *
import cv2
import numpy as np

class ActionsMixin:
    def initialize_paths_and_files(self):
        try:
            paths_folder = os.path.join(os.getcwd(), "paths")
            if not os.path.exists(paths_folder):
                os.makedirs(paths_folder, exist_ok=True)
                self.append_log(f"Created paths folder: {paths_folder}")

            obby_file = os.path.join(paths_folder, "obby.json")
            if not os.path.exists(obby_file):
                self.append_log("Downloading obby.json file...")
                try:
                    response = requests.get(
                        "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/paths/obby.json",
                        timeout=15
                    )
                    response.raise_for_status()
                    with open(obby_file, "w", encoding="utf-8") as f:
                        f.write(response.text)
                    self.append_log(f"Downloaded obby.json to: {obby_file}")
                except Exception as e:
                    self.error_logging(e, "Failed to download obby.json file")
            else:
                self.append_log(f"obby.json already exists at: {obby_file}")
        except Exception as e:
            self.error_logging(e, "Error in initialize_paths_and_files")

    def extract_text_with_easyocr(self, region):
        try:
            x, y, width, height = region
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            image_rgb = np.array(screenshot)
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

            ocr_lock = getattr(self, "_easyocr_lock", None)
            if ocr_lock is None:
                ocr_lock = threading.Lock()
                self._easyocr_lock = ocr_lock

            ocr_cache = getattr(self, "_easyocr_cache", None)
            if ocr_cache is None:
                ocr_cache = {}
                self._easyocr_cache = ocr_cache

            response = None
            endpoints = ["https://cn-api.easyocr.org/ocr", "https://api.easyocr.org/ocr"]
            
            with ocr_lock:
                _, img_encoded = cv2.imencode(".png", image_bgr)
                file_bytes = img_encoded.tobytes()
                
                import hashlib
                img_hash = hashlib.sha256(file_bytes).hexdigest()
                if img_hash in ocr_cache:
                    cached_text = ocr_cache[img_hash]
                    self.append_log(f"[EasyOCR - Cache] Cached text: '{cached_text}'")
                    return cached_text
                file_bytes = img_encoded.tobytes()

                for endpoint in endpoints:
                    try:
                        #self.append_log(f"[DEBUG] Sending request to {endpoint}...")
                        response = requests.post(
                            endpoint,
                            files={"file": ("screenshot.png", file_bytes, "image/png")},
                            timeout=5,
                        )
                        #self.append_log(f"[DEBUG] {endpoint} returned status: {response.status_code}")
                        if response.status_code == 200:
                            break
                        else:
                            self.append_log(f"[EasyOCR - API] Endpoint {endpoint} returned non-200. We're cooked...")
                    except requests.exceptions.Timeout:
                        self.append_log(f"[EasyOCR - API] {endpoint} timed out. Trying next...")
                    except Exception as e:
                        self.append_log(f"[EasyOCR - API] {endpoint} failed: {e}. Trying next...")

            if response is not None and response.status_code == 200:
                data = response.json()
                words = data.get("words", [])
                if words:
                    def _safe_text(w):
                        t = str(w.get("text", "")).strip()
                        try:
                            t.encode("ascii")
                        except UnicodeEncodeError:
                            t = "".join(c if ord(c) < 128 else "" for c in t)
                        return t
                    
                    try:
                        safe_words = [{"text": _safe_text(w)} for w in words]
                        self.append_log(f"[EasyOCR - API] Extracted text: {safe_words}")
                    except Exception:
                        pass
                    
                    final_text = " ".join([_safe_text(w) for w in words if _safe_text(w)]).strip()
                    if len(ocr_cache) > 100:
                        ocr_cache.clear()
                    ocr_cache[img_hash] = final_text
                    return final_text

            if len(ocr_cache) > 100:
                ocr_cache.clear()
            ocr_cache[img_hash] = ""
            return ""
        except Exception as e:
            try:
                self.error_logging(e, "Error extracting text with EasyOCR API")
            except (UnicodeEncodeError, UnicodeDecodeError):
                self.error_logging(e, "Error extracting text with EasyOCR API (unicode)")
            return ""

    def load_notice_tab(self):
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/noticetabcontents.txt"
        data = ""
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.text
        except Exception as e:
            print(f"Error loading noticetabcontents.txt from {url}: {e}")
            self.error_logging(e, f"Error loading noticetabcontents.txt from {url}")

        return data

    def is_roblox_focused(self):
        try:
            w = gw.getActiveWindow()
            if not w:
                return False
            title = (w.title or "").lower()
            return "roblox" in title
        except Exception:
            return False

    def _is_fishing_blocked(self) -> bool:
        try:
            return (
                bool(self.is_fishing_mode_enabled())
                and not bool(getattr(self, "_remote_running", False))
                and not bool(getattr(self, "_fishing_br_sc_override", False))
            )
        except Exception:
            return False

    def _sleep_with_cancel(self, seconds: float, poll: float = 0.05) -> bool:
        end = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < end:
            if (not self.detection_running
                    or self._is_fishing_blocked()
                    or bool(getattr(self, "auto_pop_state", False))):
                return False
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll, remaining))
        return (self.detection_running
                and not self._is_fishing_blocked()
                and not bool(getattr(self, "auto_pop_state", False)))

    def update_theme(self, theme_name):
        self.root.style.theme_use(theme_name)
        self.config["selected_theme"] = theme_name
        self.save_config()

    def _get_update_api_url(self):
        return os.environ.get(
            "COTEAB_UPDATE_API_URL",
            "https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest",
        )

    def _normalize_version(self, value):
        try:
            v = str(value or "").strip().lower()
            if v.startswith("v"):
                v = v[1:]
            return v
        except Exception:
            return ""

    def _is_same_version(self, a, b):
        return self._normalize_version(a) == self._normalize_version(b)

    def _fetch_latest_release(self):
        try:
            response = requests.get(self._get_update_api_url(), timeout=12)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
        except Exception as e:
            print(f"Failed to fetch latest release metadata: {e}")
        return None

    def _pick_update_exe_asset(self, release_payload):
        assets = release_payload.get("assets", []) if isinstance(release_payload, dict) else []
        if not isinstance(assets, list):
            return "", ""

        preferred = {
            "coteabmacro.exe",
            "coteab macro.exe",
            "coteab_macro.exe",
            "coteab-macro.exe",
        }
        exe_candidates = []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", "")).strip()
            url = str(asset.get("browser_download_url", "")).strip()
            if not name or not url:
                continue
            lower_name = name.lower()
            if lower_name in preferred:
                return name, url
            if lower_name.endswith(".exe"):
                exe_candidates.append((name, url))

        if exe_candidates:
            return exe_candidates[0]
        return "", ""

    def _spawn_detached_exe(self, exe_path, extra_args=None):
        try:
            cmd = [os.path.abspath(exe_path)]
            if extra_args:
                cmd.extend([str(x) for x in extra_args])

            creationflags = 0
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(
                cmd,
                creationflags=creationflags,
                close_fds=True,
            )
            return True
        except Exception as e:
            print(f"Failed to spawn detached EXE: {e}")
            return False

    def _download_and_stage_exe_update(self, download_url, asset_name="CoteabMacro.exe"):
        if not getattr(sys, "frozen", False):
            return False

        current_dir = os.path.dirname(os.path.abspath(sys.executable))
        temp_exe = os.path.join(current_dir, "CoteabMacro1.exe")

        try:
            if os.path.exists(temp_exe):
                os.remove(temp_exe)
        except Exception:
            pass

        response = requests.get(download_url, timeout=120, stream=True)
        response.raise_for_status()

        with open(temp_exe, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

        if not os.path.exists(temp_exe) or os.path.getsize(temp_exe) <= 0:
            raise RuntimeError("Downloaded update file is empty")

        canonical_exe = os.path.join(current_dir, "CoteabMacro.exe")
        args = [
            "--coteab-finalize-update",
            "--coteab-target",
            canonical_exe,
            "--coteab-old-pid",
            str(os.getpid()),
        ]
        if not self._spawn_detached_exe(temp_exe, args):
            raise RuntimeError("Failed to launch downloaded update executable")
        return True

    def _is_pid_alive(self, pid):
        try:
            pid_i = int(pid)
            if pid_i <= 0:
                return False
            proc = psutil.Process(pid_i)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except Exception:
            return False

    def maybe_self_rename_to_canonical_exe(self, canonical_target="CoteabMacro.exe", old_pid=None):
        try:
            if not getattr(sys, "frozen", False):
                return False

            current_exe = os.path.abspath(sys.executable)
            current_dir = os.path.dirname(current_exe)
            current_name = os.path.basename(current_exe)
            if not current_name.lower().endswith(".exe"):
                return False

            canonical_raw = str(canonical_target or "CoteabMacro.exe").strip() or "CoteabMacro.exe"
            if not canonical_raw.lower().endswith(".exe"):
                canonical_raw += ".exe"

            canonical_path = canonical_raw if os.path.isabs(canonical_raw) else os.path.join(current_dir, canonical_raw)
            canonical_path = os.path.abspath(canonical_path)

            if current_exe.lower() == canonical_path.lower():
                return False

            deadline = time.monotonic() + 120.0
            while time.monotonic() < deadline:
                if old_pid and self._is_pid_alive(old_pid):
                    time.sleep(0.2)
                    continue

                try:
                    if os.path.exists(canonical_path):
                        os.remove(canonical_path)
                except Exception:
                    pass

                try:
                    os.replace(current_exe, canonical_path)
                    self._spawn_detached_exe(canonical_path)
                    return True
                except Exception:
                    time.sleep(0.25)

            print("Failed to rename current executable to canonical name within timeout.")
            return False
        except Exception as e:
            print(f"Failed to normalize executable name: {e}")
            return False

    def _download_exe_to_folder(self, download_url, target_dir, asset_name="CoteabMacro.exe"):
        os.makedirs(target_dir, exist_ok=True)

        base_name = os.path.basename(str(asset_name or "").strip()) or "CoteabMacro.exe"
        if not base_name.lower().endswith(".exe"):
            base_name += ".exe"

        target_path = os.path.join(target_dir, base_name)
        if os.path.exists(target_path):
            stem, ext = os.path.splitext(base_name)
            target_path = os.path.join(target_dir, f"{stem}_downloaded{ext}")

        response = requests.get(download_url, timeout=120, stream=True)
        response.raise_for_status()

        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

        if not os.path.exists(target_path) or os.path.getsize(target_path) <= 0:
            raise RuntimeError("Downloaded update file is empty")

        return target_path

    def apply_startup_auto_update(self):
        try:
            if not getattr(sys, "frozen", False):
                return False

            latest_release = self._fetch_latest_release()
            if not latest_release:
                return False

            latest_version = str(latest_release.get("tag_name", "")).strip()
            if not latest_version or self._is_same_version(latest_version, current_ver):
                return False

            asset_name, download_url = self._pick_update_exe_asset(latest_release)
            if not download_url:
                print("Update available, but no .exe asset was found in latest release.")
                return False

            print("hold up downloading the new Coteab Macro update bro")
            if self._download_and_stage_exe_update(download_url, asset_name=asset_name):
                print(f"Update {latest_version} downloaded. Restarting into the new executable...")
                return True
            return False
        except Exception as e:
            print(f"Startup auto-update failed: {e}")
            return False

    def check_for_updates(self):
        current_version = current_ver

        try:
            latest_release = self._fetch_latest_release()
            if not latest_release:
                return

            latest_version = str(latest_release.get("tag_name", "")).strip()
            if latest_version and not self._is_same_version(latest_version, current_version):
                asset_name, download_url = self._pick_update_exe_asset(latest_release)
                if not download_url:
                    return

                if hasattr(self, "on_update_available") and callable(self.on_update_available):
                    self.on_update_available(latest_version, download_url)

        except Exception as e:
            print(f"Failed to check for updates: {e}")

    def download_and_apply_update(self, download_url, version=""):
        try:
            if not download_url:
                if hasattr(self, "on_update_status") and callable(self.on_update_status):
                    self.on_update_status("failed")
                return False

            if hasattr(self, "on_update_status") and callable(self.on_update_status):
                self.on_update_status("downloading")

            guessed_name = os.path.basename(str(download_url).split("?", 1)[0]) or "CoteabMacro.exe"
            if getattr(sys, "frozen", False):
                self._download_and_stage_exe_update(download_url, asset_name=guessed_name)

                if hasattr(self, "on_update_status") and callable(self.on_update_status):
                    self.on_update_status("done|restarting")

                # allow status callback to flush before terminating process
                time.sleep(0.25)
                os._exit(0)
            else:
                try:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(base_dir)
                except Exception:
                    project_root = os.getcwd()

                downloaded_path = self._download_exe_to_folder(
                    download_url,
                    project_root,
                    asset_name=guessed_name,
                )

                if hasattr(self, "on_update_status") and callable(self.on_update_status):
                    self.on_update_status(f"done|{os.path.basename(downloaded_path)}")
                return True
        except Exception as e:
            print(f"Failed to download/apply update: {e}")
            if hasattr(self, "on_update_status") and callable(self.on_update_status):
                self.on_update_status("failed")
            return False


    def take_inventory_screenshot_now(self):
        try:
            if not getattr(self, "periodical_inventory_var", None) or not self.periodical_inventory_var.get():
                return
            if self.config.get("enable_idle_mode", False):
                return
            if not self.check_roblox_procs():
                return
            
            for _ in range(4):
                self.activate_roblox_window()
                time.sleep(0.35)

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
                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = os.path.join(screenshot_dir, f"inventory_screenshot_{int(time.time())}.png")
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
            
    def perform_glitched_enable_buff(self):
        try:
            if not self.config.get("enable_buff_glitched", False):
                return
            if self.config.get("enable_idle_mode", False):
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
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
                if not getattr(self, "_br_sc_running", False) and not getattr(self, "_mt_running", False) and not getattr(self, "auto_pop_state", False) and not getattr(self, "on_auto_merchant_state", False) and not self.config.get("enable_potion_crafting", False):
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

    def _reset_on_rare_impl(self):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if not self.detection_running or self.reconnecting_state:
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            for _ in range(4):
                if not self.detection_running:
                    return
                self.activate_roblox_window()
                time.sleep(0.15)
            keyboard.press_and_release('esc')
            time.sleep(0.3)
            keyboard.press_and_release('r')
            time.sleep(0.3)
            keyboard.press_and_release('enter')
        except Exception:
            pass

    def _teleport_crack_impl(self):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if not self.detection_running or self.reconnecting_state:
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            search_bar = self.config.get("search_bar", [855, 358])
            first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
            use_button = self.config.get("use_button", [710, 573])
            inventory_close = self.config.get("inventory_close_button", [1418, 298])
            amount_box = self.config.get("amount_box", [954, 429])

            self.activate_roblox_window()
            time.sleep(0.15)
            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            time.sleep(0.3 + float(self.click_delay_var.get()))
            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.3 + float(self.click_delay_var.get()))
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.3 + float(self.click_delay_var.get()))
            self.Global_MouseClick(amount_box[0], amount_box[1], click=2)
            time.sleep(0.3 + float(self.click_delay_var.get()))
            keyboard.send("ctrl+a")
            time.sleep(0.06 + float(self.click_delay_var.get()))
            keyboard.send("backspace")
            time.sleep(0.3 + float(self.click_delay_var.get()))
            autoit.send("crack")
            time.sleep(0.45 + float(self.click_delay_var.get()))
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            time.sleep(0.25 + float(self.click_delay_var.get()))
            self.Global_MouseClick(use_button[0], use_button[1])
            time.sleep(0.3 + float(self.click_delay_var.get()))
            self.Global_MouseClick(inventory_close[0], inventory_close[1])
            time.sleep(0.2 + float(self.click_delay_var.get()))
        except Exception as e:
            self.error_logging(e, "Error in _teleport_crack_impl")

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


    def perform_quest_claim_sequence_sync(self):
        try:
            self._action_scheduler.enqueue_action(self._perform_quest_claim_sequence_impl, name="quest_claim", priority=5)
        except Exception:
            try:
                self._perform_quest_claim_sequence_impl()
            except Exception:
                pass

    def _perform_quest_claim_sequence_impl(self):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if self._is_fishing_blocked():
                return
            if not getattr(self, "auto_claim_quests_var", None) or not self.auto_claim_quests_var.get():
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            if not self.check_roblox_procs():
                return
            self.activate_roblox_window()
            quest_menu = self.config.get("quest_menu", [0, 0])
            quest1 = self.config.get("quest1_button", [0, 0])
            quest2 = self.config.get("quest2_button", [0, 0])
            quest3 = self.config.get("quest3_button", [0, 0])
            claim_btn = self.config.get("claim_quest_button", [0, 0])

            for _ in range(4):
                if not self.detection_running or self._is_fishing_blocked():
                    return
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.15):
                    return

            if quest_menu and quest_menu[0]:
                try:
                    autoit.mouse_click("left", quest_menu[0], quest_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest_menu[0], quest_menu[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5):
                    return

            try:
                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = os.path.join(screenshot_dir, f"quest_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_quest_screenshot_webhook(filename)
            except Exception as e:
                self.error_logging(e, "Error taking/sending quest screenshot")

            if not self._sleep_with_cancel(0.5):
                return

            if quest1 and quest1[0]:
                try:
                    autoit.mouse_click("left", quest1[0], quest1[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest1[0], quest1[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5):
                    return
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5):
                    return

            if quest2 and quest2[0]:
                try:
                    autoit.mouse_click("left", quest2[0], quest2[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest2[0], quest2[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5):
                    return
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5):
                    return

            if quest3 and quest3[0]:
                try:
                    autoit.mouse_click("left", quest3[0], quest3[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest3[0], quest3[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5):
                    return
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5):
                    return
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
                    self._sleep_with_cancel(0.3)
            except Exception:
                pass

        except Exception as e:
            self.error_logging(e, "Error in perform_quest_claim_sequence_sync")

    def obby_path_loop(self):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
        except Exception as e:
            self.error_logging(e, "Error in obby_path_loop")

        while self.detection_running:
            try:
                if self.is_fishing_mode_enabled():
                    time.sleep(2)
                    continue
                if not getattr(self, "enable_obby_var", None) or not self.enable_obby_var.get():
                    time.sleep(2)
                    continue

                try:
                    interval_min = float(self.obby_claim_interval_var.get())
                except Exception:
                    interval_min = 15.0

                if (datetime.now() - self.last_obby_claim) < timedelta(minutes=interval_min):
                    time.sleep(2)
                    continue

                if (getattr(self, "_br_sc_running", False) or
                    getattr(self, "_mt_running", False) or
                    getattr(self, "auto_pop_state", False) or
                    getattr(self, "on_auto_merchant_state", False) or
                    getattr(self, "config", {}).get("enable_potion_crafting", False)):
                    time.sleep(2)
                    continue

                self._action_scheduler.enqueue_action(
                    self._perform_obby_path_sequence_impl,
                    name="obby_path",
                    priority=0
                )

                self.last_obby_claim = datetime.now()

            except Exception as e:
                self.error_logging(e, "Error in obby_path_loop")
            time.sleep(1)

    def _perform_obby_path_sequence_impl(self):
        try:
            if self._is_fishing_blocked():
                return
            if not getattr(self, "enable_obby_var", None) or not self.enable_obby_var.get():
                return
            if not self.check_roblox_procs():
                return

            self._obby_running = True

            print("[Obby] Activating Roblox...")

            for _ in range(4):
                if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                    self._obby_running = False
                    return
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.15):
                    self._obby_running = False
                    return

            # 2. Reset Character
            print("[Obby] Resetting Character...")
            keyboard.press_and_release('esc')
            if not self._sleep_with_cancel(0.3):
                return
            keyboard.press_and_release('r')
            if not self._sleep_with_cancel(0.3):
                return
            keyboard.press_and_release('enter')
            if not self._sleep_with_cancel(6):
                return

            if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                return

            # 3. Click Collection Buttons
            collections_button = self.config.get("collections_button", [0, 0])
            if collections_button and collections_button[0]:
                try:
                    autoit.mouse_click("left", collections_button[0], collections_button[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(collections_button[0], collections_button[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.3):
                    return

            exit_collections_button = self.config.get("exit_collections_button", [0, 0])
            if exit_collections_button and exit_collections_button[0]:
                try:
                    autoit.mouse_click("left", exit_collections_button[0], exit_collections_button[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(exit_collections_button[0], exit_collections_button[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.3):
                    return

            if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                return

            # 4. Camera Adjustment
            start_x = exit_collections_button[0] if exit_collections_button and exit_collections_button[0] else 500
            start_y = exit_collections_button[1] if exit_collections_button and exit_collections_button[1] else 500

            autoit.mouse_move(start_x, start_y, 0)
            autoit.mouse_down("right")
            if not self._sleep_with_cancel(0.1):
                return
            autoit.mouse_move(start_x, start_y + 75, 0)
            if not self._sleep_with_cancel(0.1):
                return
            autoit.mouse_up("right")
            try:
                autoit.mouse_wheel("up", max(1, int(round(5000 / 120.0))))
            except Exception:
                try:
                    pyautogui.scroll(5000)
                except Exception:
                    pass
            if not self._sleep_with_cancel(3.0):
                return
            try:
                autoit.mouse_wheel("down", max(1, int(round(1500 / 120.0))))
            except Exception:
                try:
                    pyautogui.scroll(-1500)
                except Exception:
                    pass
            if not self._sleep_with_cancel(0.2):
                return

            # 4.5 Equip Float Aura if enabled
            use_float_aura = self.config.get("use_float_aura", False)
            if use_float_aura:
                aura_name = self.config.get("float_aura_name", "").strip()
                if aura_name:
                    # Check if already equipped to avoid unequip loop
                    current_aura = getattr(self, "last_aura_found", None)
                    if current_aura and current_aura == aura_name:
                        print(f"[Obby] Float Aura '{aura_name}' already equipped. Skipping.")
                    else:
                        print(f"[Obby] Equipping Float Aura: {aura_name}")
                        inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
                        aura_menu = self.config.get("aura_menu", [0, 0])
                        search_bar = self.config.get(
                            "aura_search_bar",
                            self.config.get("search_bar", [834, 364]),
                        )
                        close_btn = self.config.get("inventory_close_button", [0, 0])

                        if aura_menu and aura_menu[0] > 0:
                            self.Global_MouseClick(aura_menu[0], aura_menu[1])
                            if not self._sleep_with_cancel(0.7 + inventory_click_delay):
                                return

                            if search_bar and search_bar[0] > 0:
                                self.Global_MouseClick(search_bar[0], search_bar[1])
                                if not self._sleep_with_cancel(0.5 + inventory_click_delay):
                                    return
                                try:
                                    autoit.send(aura_name)
                                except Exception:
                                    try:
                                        keyboard.write(aura_name.lower())
                                    except Exception:
                                        pass
                                if not self._sleep_with_cancel(0.8 + inventory_click_delay):
                                    return

                                first_aura_slot = self.config.get("first_aura_slot_pos", [0, 0])
                                if first_aura_slot and first_aura_slot[0] > 0:
                                    self.Global_MouseClick(first_aura_slot[0], first_aura_slot[1])
                                    if not self._sleep_with_cancel(0.5 + inventory_click_delay):
                                        return

                                    # Click "Equip" button
                                    equip_btn = self.config.get("equip_aura_button", [0, 0])
                                    if equip_btn and equip_btn[0] > 0:
                                        self.Global_MouseClick(equip_btn[0], equip_btn[1])
                                        if not self._sleep_with_cancel(0.3 + inventory_click_delay):
                                            return

                            if close_btn and close_btn[0] > 0:
                                self.Global_MouseClick(close_btn[0], close_btn[1])
                                if not self._sleep_with_cancel(0.5 + inventory_click_delay):
                                    return

            if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                return

            # 5. Run Obby recording file
            obby_file = os.path.join(os.getcwd(), "paths", "obby.json")
            if os.path.exists(obby_file):
                print("[Obby] Starting obby macro playback...")
                self._run_obby_macro(obby_file)
            else:
                print("[Obby] Macro file not found: " + obby_file)

        except Exception as e:
            self.error_logging(e, "Error in _perform_obby_path_sequence_impl")
        finally:
            self._obby_running = False

    def _run_obby_macro(self, json_file_path):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.error_logging(e, f"Failed to load obby macro from {json_file_path}")
            return

        events = data.get("events", [])
        if not events:
            return
        events.sort(key=lambda ev: ev.get("t", 0.0))

        start_time = time.perf_counter()
        pressed_keys = set()

        def _cancelled():
            return (
                not self.detection_running
                or not getattr(self, "enable_obby_var", None)
                or not self.enable_obby_var.get()
                or self._is_fishing_blocked()
                or self.reconnecting_state
                or self.auto_pop_state
            )

        def _release_all():
            if pressed_keys:
                print(f"[Obby] Releasing {len(pressed_keys)} stuck keys...")
                for k in list(pressed_keys):
                    try:
                        keyboard.release(k)
                    except Exception:
                        pass
                pressed_keys.clear()

        for ev in events:
            if _cancelled():
                print("[Obby] Cancelled during macro playback.")
                _release_all()
                return

            t = float(ev.get("t", 0.0))
            target_time = start_time + t
            now = time.perf_counter()

            if target_time > now:
                diff = target_time - now
                if diff > 0.02:
                    sleep_ms = int((diff - 0.015) * 1000)
                    chunks = sleep_ms // 50
                    for _ in range(chunks):
                        if _cancelled():
                            print("[Obby] Cancelled during sleep.")
                            _release_all()
                            return
                        time.sleep(0.05)
                    rem = (sleep_ms % 50) / 1000.0
                    if rem > 0:
                        time.sleep(rem)
                        if _cancelled():
                            print("[Obby] Cancelled during sleep.")
                            _release_all()
                            return
                
                while time.perf_counter() < target_time:
                    if _cancelled():
                        print("[Obby] Cancelled during wait.")
                        _release_all()
                        return
                    time.sleep(0.001)

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
                    if k and k not in ("f1", "f2", "f3", "f4"):
                        keyboard.press(k)
                        pressed_keys.add(k)
                elif typ == "key_up":
                    k = ev.get("key")
                    if k and k not in ("f1", "f2", "f3", "f4"):
                        keyboard.release(k)
                        pressed_keys.discard(k)
            except Exception:
                pass

        _release_all()
        print("[Obby] Macro finished.")

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
                if self.is_fishing_mode_enabled():
                    time.sleep(2)
                    continue
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
                    self._action_scheduler.enqueue_action(self.perform_periodic_aura_screenshot_sync, name="periodical:aura", priority=2)
                    time.sleep(0.5)
                    self._action_scheduler.enqueue_action(self.perform_periodic_inventory_screenshot_sync, name="periodical:inventory", priority=3)
                    time.sleep(0.5)
                    self._action_scheduler.enqueue_action(self.perform_quest_claim_sequence_sync, name="periodic:quest_claim", priority=4)
                    last_claim_time = datetime.now()
            except Exception as e:
                self.error_logging(e, "Error in quest_claim_loop")
            time.sleep(1)


    def _potion_thread_launcher(self, file_name, potions_directory="crafting_files_do_not_open", stop_after=None, cancel_if=None):
        """Replicate Rust run_potion_macro: prep sequence then replay loop."""
        try:
            final_name = file_name if file_name.endswith(".json") else f"{file_name}.json"
            path = os.path.join(os.getcwd(), potions_directory, final_name)
            if not os.path.exists(path):
                print(f"[Potion] File not found: {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.error_logging(e, "Failed to load potion file")
            return

        events = data.get("events", [])
        if not events:
            return
        events.sort(key=lambda ev: ev.get("t", 0.0))

        potion_name = os.path.splitext(os.path.basename(final_name))[0]
        print(f"[Potion] Starting preparation sequence for {potion_name}")

        def _cancelled():
            try:
                if callable(cancel_if) and cancel_if():
                    return True
            except Exception:
                pass
            return (
                not self.detection_running
                or not self.enable_potion_crafting_var.get()
                or self.is_fishing_mode_enabled()
            )


        try:
            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            tab_pos = self.config.get("potion_items_tab", [0, 0])
            search_pos = self.config.get("potion_search_bar", [0, 0])
            first_slot_pos = self.config.get("potion_first_potion_slot_pos", [0, 0])
            auto_btn = self.config.get(
                "potion_auto_add_button",
                self.config.get("potion_auto_button", [0, 0]),
            )
            recipe_btn = self.config.get("potion_recipe_button", [0, 0])

            self.activate_roblox_window()
            time.sleep(0.5)

            # Press F 4 times (open crafting menu)
            for _ in range(4):
                if _cancelled(): return
                autoit.send("f")
                time.sleep(0.45)

            # Click items tab 5 times
            if tab_pos and tab_pos[0] > 0:
                for _ in range(5):
                    if _cancelled(): return
                    self.Global_MouseClick(tab_pos[0], tab_pos[1])
                    time.sleep(0.3)

            # Search bar: clear and type potion name
            if search_pos and search_pos[0] > 0:
                if _cancelled(): return
                self.Global_MouseClick(search_pos[0], search_pos[1])
                time.sleep(0.6 + inventory_click_delay)
                autoit.send("^{a}")
                time.sleep(0.6 + inventory_click_delay)
                autoit.send("{BACKSPACE}")
                time.sleep(0.6 + inventory_click_delay)
                if potion_name:
                    autoit.send(potion_name)
                    time.sleep(0.6 + inventory_click_delay)
                autoit.send("{ENTER}")
                time.sleep(1.5 + inventory_click_delay)

            # Click first potion slot 3 times
            if first_slot_pos and first_slot_pos[0] > 0:
                for _ in range(3):
                    if _cancelled(): return
                    self.Global_MouseClick(first_slot_pos[0], first_slot_pos[1])
                    time.sleep(0.3)

            # Click Auto Add button (must happen before opening recipe)
            if auto_btn and auto_btn[0] > 0:
                if _cancelled(): return
                self.Global_MouseClick(auto_btn[0], auto_btn[1])
                time.sleep(0.5)

            # Click recipe button
            if recipe_btn and recipe_btn[0] > 0:
                if _cancelled(): return
                self.Global_MouseClick(recipe_btn[0], recipe_btn[1])
                time.sleep(2.0)

        except Exception as e:
            self.error_logging(e, "Potion prep sequence failed")
            return

        # ── Replay loop  ──
        overall_start = time.perf_counter()

        while not _cancelled():
            if stop_after is not None and time.perf_counter() - overall_start >= float(stop_after):
                print("[Potion] Switching interval reached. Stopping for next potion.")
                break

            loop_start = time.perf_counter()
            pressed_keys = set()
            print("[Potion] Starting loop iteration...")

            for ev in events:
                if _cancelled(): break
                if stop_after is not None and time.perf_counter() - overall_start >= float(stop_after):
                    break

                t = max(float(ev.get("t", 0.0)), 0.0)
                target_time = loop_start + t
                now = time.perf_counter()

                if target_time > now:
                    diff = target_time - now
                    if diff > 0.02:
                        sleep_ms = int((diff - 0.015) * 1000)
                        chunks = sleep_ms // 50
                        for _ in range(chunks):
                            if _cancelled(): break
                            if stop_after is not None and time.perf_counter() - overall_start >= float(stop_after):
                                break
                            time.sleep(0.05)
                        rem = (sleep_ms % 50) / 1000.0
                        if rem > 0:
                            time.sleep(rem)
                    while time.perf_counter() < target_time:
                        pass

                typ = ev.get("type", "")
                try:
                    if typ == "mouse_move":
                        autoit.mouse_move(int(ev.get("x", 0)), int(ev.get("y", 0)), speed=0)
                    elif typ == "mouse_down":
                        autoit.mouse_down(ev.get("button", "left"))
                    elif typ == "mouse_up":
                        autoit.mouse_up(ev.get("button", "left"))
                    elif typ == "mouse_wheel":
                        delta = int(ev.get("delta", 0))
                        if delta != 0:
                            mouse.wheel(delta)
                    elif typ == "key_down":
                        k = ev.get("key", "")
                        if k and k not in ("f1", "f2", "f3", "f4"):
                            keyboard.press(k)
                            pressed_keys.add(k)
                    elif typ == "key_up":
                        k = ev.get("key", "")
                        if k and k not in ("f1", "f2", "f3", "f4"):
                            keyboard.release(k)
                            pressed_keys.discard(k)
                except Exception:
                    pass

            # Release stuck keys at end of each iteration
            if pressed_keys:
                print(f"[Potion] Releasing {len(pressed_keys)} stuck keys...")
                for k in list(pressed_keys):
                    try:
                        keyboard.release(k)
                    except Exception:
                        pass

            print("[Potion] Loop iteration finished.")
            time.sleep(0.1)

    def start_potion_crafting(self):
        if not hasattr(self, '_potion_gen'):
            self._potion_gen = 0
        self._potion_gen += 1
        my_gen = self._potion_gen

        def _potion_craft_loop():
            try:
                while self.detection_running and self._potion_gen == my_gen:
                    try:
                        if self.is_fishing_mode_enabled():
                            time.sleep(1)
                            continue
                        if not getattr(self, "enable_potion_crafting_var", None) or not self.enable_potion_crafting_var.get():
                            time.sleep(1)
                            continue

                        if (self.reconnecting_state or self.auto_pop_state or
                            self.on_auto_merchant_state or
                            self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE") or
                            getattr(self, '_mt_running', False)):
                            time.sleep(2)
                            continue

                        if self.config.get("enable_idle_mode", False):
                            time.sleep(2)
                            continue

                        switching_enabled = self.config.get("enable_potion_switching", False)

                        if switching_enabled:
                            current_index = 0
                            slot_keys = [
                                "selected_potion_file",
                                "potion_file_1",
                                "potion_file_2",
                                "potion_file_3",
                            ]
                            while self.detection_running and self.enable_potion_crafting_var.get() and self._potion_gen == my_gen:
                                if not bool(self.config.get("enable_potion_switching", False)): break
                                interval = float(self.config.get("potion_switch_interval", "60"))
                                target_file = self.config.get(slot_keys[current_index], "").strip()

                                if not target_file or target_file.lower() == "none":
                                    print(f"[Potion] Slot #{current_index} is empty. Skipping.")
                                    current_index = (current_index + 1) % 4
                                    time.sleep(0.5)
                                    continue

                                print(f"[Potion] Starting Auto Craft: {target_file} (Index: {current_index})")
                                self._potion_thread_launcher(
                                    target_file,
                                    "crafting_files_do_not_open",
                                    stop_after=interval,
                                    cancel_if=lambda: not bool(self.config.get("enable_potion_switching", False)),
                                )
                                current_index = (current_index + 1) % 4
                        else:
                            file_name = self.config.get("selected_potion_file", "").strip()
                            if not file_name or file_name.lower() == "none":
                                time.sleep(2)
                                continue

                            print(f"[Potion] Starting Auto Craft: {file_name}")
                            self._potion_thread_launcher(
                                file_name,
                                cancel_if=lambda: bool(self.config.get("enable_potion_switching", False)),
                            )
                            self.config["potion_last_file"] = file_name
                            self.save_config()

                        time.sleep(0.5)

                    except Exception as e:
                        self.error_logging(e, "Error in potion craft loop iteration")
                        time.sleep(2)

            except Exception as e:
                self.error_logging(e, "Error in potion craft loop")

        threading.Thread(target=_potion_craft_loop, daemon=True).start()


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

    def update_stats(self):
        total_biomes = sum(self.biome_counts.values())

        if hasattr(self, "stats_labels"):
            for biome, label in self.stats_labels.items():
                try:
                    label.config(text=f"{biome}: {self.biome_counts[biome]}")
                except Exception:
                    pass

        if hasattr(self, "total_biomes_label"):
            try:
                self.total_biomes_label.config(text=f"Total Biomes Found: {total_biomes}", foreground="light green")
            except Exception:
                pass

        if hasattr(self, "session_label"):
            try:
                self.session_label.config(text=f"Running Session: {self.get_total_session_time()}")
            except Exception:
                pass

        self.save_config()
        
        if hasattr(self, "on_stats_update") and callable(self.on_stats_update):
            try:
                self.on_stats_update()
            except Exception:
                pass

    def format_seconds_to_hhmmss(self, total_seconds):
        total_seconds = int(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


    def start_capture_thread(self, config_key, coord_vars):
        snipping_tool = SnippingWidget(self.root, config_key=config_key,
                                       callback=lambda region: self.update_coordinates(config_key, region, coord_vars))
        snipping_tool.start()

    def update_coordinates(self, config_key, region, coord_vars):
        x, y = region[0], region[1]
        coord_vars[config_key][0].set(x)
        coord_vars[config_key][1].set(y)
        self.save_config()

    def validate_and_save_ps_link(self):
        private_server_link = self.private_server_link_entry.get()
        if not self.validate_private_server_link(private_server_link):
            messagebox.showwarning(
                "Invalid PS Link!",
                "The link you provided is not a valid Roblox link. It could be either a share link or a private server code link. "
                "Please ensure the link is correct and try again.\n\n"
                "Valid links should look like:\n"
                "- Share link: https://www.roblox.com/share?code=1234567899abcdefxyz&type=Server\n"
                "- Private server code link: https://www.roblox.com/games/15532962292/Sols-RNG?privateServerLinkCode=xxxxxxxx"
            )
            return

        self.save_config()

    def validate_private_server_link(self, link):
        try:
            from urllib.parse import parse_qs, urlparse

            raw_link = str(link or "").strip()
            if not raw_link:
                return False

            # Backward compatible support for old raw PS-code format
            if re.search(r"privateserverlinkcode=", raw_link, flags=re.IGNORECASE):
                return True

            parsed = urlparse(raw_link)
            if parsed.scheme not in ("http", "https"):
                return False

            host = (parsed.netloc or "").lower()
            if host not in ("roblox.com", "www.roblox.com"):
                return False

            path = parsed.path or ""
            query = parse_qs(parsed.query)
            query_ci = {str(k).strip().lower(): v for k, v in query.items()}

            # Private-server-code links
            if query_ci.get("privateserverlinkcode") and str(query_ci["privateserverlinkcode"][0]).strip():
                return True

            # Share links
            if path.startswith("/share"):
                has_code = bool(query_ci.get("code") and str(query_ci["code"][0]).strip())
                link_type = str(query_ci.get("type", [""])[0]).strip().lower()
                return has_code and link_type in ("", "server")

            return False
        except Exception:
            return False

    def _build_reconnect_deep_links(self, link):
        try:
            from urllib.parse import parse_qs, quote, urlparse

            raw_link = str(link or "").strip()
            if not raw_link:
                return []

            parsed = urlparse(raw_link)
            query = parse_qs(parsed.query)
            query_ci = {str(k).strip().lower(): v for k, v in query.items()}
            path = parsed.path or ""
            is_roblox_protocol = parsed.scheme.lower() == "roblox"
            path_l = path.lower()
            raw_l = raw_link.lower()

            # roblox://placeID=...&linkCode=... does not parse query normally
            raw_place_match = re.search(r"placeID=(\d+)", raw_link, flags=re.IGNORECASE)
            raw_place_id = raw_place_match.group(1) if raw_place_match else ""

            place_match = re.search(r"/games/(\d+)", path, flags=re.IGNORECASE)
            place_id = place_match.group(1) if place_match else (raw_place_id or "15532962292")

            link_code = ""
            source_type = ""
            if query_ci.get("privateserverlinkcode"):
                link_code = str(query_ci["privateserverlinkcode"][0]).strip()
                source_type = "private"
            elif query_ci.get("linkcode"):
                link_code = str(query_ci["linkcode"][0]).strip()
                source_type = "private"
            elif query_ci.get("code"):
                link_type = str(query_ci.get("type", [""])[0]).strip().lower()
                if link_type in ("", "server"):
                    link_code = str(query_ci["code"][0]).strip()
                    source_type = "share"

            # Backward-compat support for old raw format:
            # Sols-RNG?privateServerLinkCode=xxxxxxxx
            if not link_code:
                m = re.search(r"privateServerLinkCode=([^&\s]+)", raw_link, flags=re.IGNORECASE)
                if m:
                    link_code = str(m.group(1)).strip()
                    source_type = "private"
            if not link_code:
                m = re.search(r"linkCode=([^&\s]+)", raw_link, flags=re.IGNORECASE)
                if m:
                    link_code = str(m.group(1)).strip()
                    source_type = "private"
            if not link_code:
                m = re.search(r"code=([^&\s]+)", raw_link, flags=re.IGNORECASE)
                if m:
                    link_code = str(m.group(1)).strip()
                    if "navigation/share_links" in raw_l or path_l.startswith("/share"):
                        source_type = "share"

            # Keep explicit roblox:// input as the first launch candidate.
            candidates = []
            if is_roblox_protocol:
                candidates.append(raw_link)

            if not link_code:
                return candidates

            encoded_code = quote(link_code, safe="")
            share_deep_link = f"roblox://navigation/share_links?code={encoded_code}&type=Server"
            private_deep_link = f"roblox://placeID={place_id}&linkCode={encoded_code}"
            if source_type == "private":
                candidates.extend([private_deep_link, share_deep_link])
            else:
                candidates.extend([share_deep_link, private_deep_link])

            deduped = []
            for candidate in candidates:
                if candidate not in deduped:
                    deduped.append(candidate)
            return deduped
        except Exception:
            return []

    def _check_disconnect_in_logs(self):
        try:
            log_file = self.get_latest_log_file()
            if not log_file or not os.path.exists(log_file):
                return False

            if not hasattr(self, "_disconnect_log_file"):
                self._disconnect_log_file = None
                self._last_position_disconnect = 0
                self._last_disconnect_time = 0
                self._disconnect_handled = False

            if self._disconnect_handled: return False

            if log_file != self._disconnect_log_file:
                self._disconnect_log_file = log_file
                try: self._last_position_disconnect = os.path.getsize(log_file)
                except Exception: self._last_position_disconnect = 0
                return False

            # cooldown
            if (time.time() - self._last_disconnect_time) < 30: return False

            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._last_position_disconnect)
                new_lines = f.readlines()
                self._last_position_disconnect = f.tell()

            if not new_lines: return False

            for line in reversed(new_lines):
                if "[FLog::Network] Client:Disconnect" in line:
                    self.append_log(f"[Disconnect] Detected client disconnect in logs: {line.strip()}")
                    self._last_disconnect_time = time.time()
                    self._disconnect_handled = True
                    return True

        except Exception as e:
            self.error_logging(e, "Error checking disconnect in logs")
        return False

    def check_disconnect_loop(self, current_attempt=1):
        if not hasattr(self, 'has_sent_disconnected_message'):
            self.has_sent_disconnected_message = False

        while self.detection_running:
            try:
                is_process_dead = not self.check_roblox_procs()
                log_disconnect = False
                if not is_process_dead:
                    log_disconnect = self._check_disconnect_in_logs()

                if is_process_dead or log_disconnect:
                    reason = "Roblox instance closed!" if is_process_dead else "Disconnected from server (detected in Roblox logs)"
                    self._pause_timer_for_disconnect(reason)
                    time.sleep(4.5)

                    if self.config.get("auto_reconnect"):
                        private_server_link = self.config.get("private_server_link")
                        reconnect_deep_links = self._build_reconnect_deep_links(private_server_link)
                        if reconnect_deep_links:
                            max_retries = 3
                            for attempt in range(current_attempt, max_retries + 1):
                                if not self.detection_running:
                                    break
                                self.terminate_roblox_processes()
                                self.send_webhook_status(f"Reconnecting to your server. hold on bro", color=0xffff00)
                                self.set_title_threadsafe(
                                    f"""Coteab Macro {current_ver} (Reconnecting)""")
                                launched = False
                                launch_err = None
                                for deep_link in reconnect_deep_links:
                                    try:
                                        os.startfile(deep_link)
                                        launched = True
                                        break
                                    except Exception as e:
                                        launch_err = e

                                if not launched:
                                    if launch_err is not None:
                                        self.error_logging(launch_err, "Failed to launch reconnect link")
                                    time.sleep(2)
                                    continue
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
                                    self._disconnect_handled = False
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
                            self._disconnect_handled = False
                else:
                    time.sleep(0.5)
            except Exception as e:
                self.error_logging(e, "Error in check_disconnect_loop function.")
                time.sleep(1)

    def reconnect_check_start_button(self):
        try:
            self.set_title_threadsafe(
                f"""Coteab Macro {current_ver} (Reconnecting - In Main Menu)""")
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
                    self.set_title_threadsafe(f"""Coteab Macro {current_ver} (Running)""")
                    return True  # weii joins!!!!!!!!!!

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
                f"""Coteab Macro {current_ver} (Roblox Disconnected :c )""")
            if reason and not getattr(self, 'has_sent_disconnected_message', False):
                try:
                    self.send_webhook_status(reason, color=0xff0000)
                except Exception:
                    pass
                self.has_sent_disconnected_message = True
            self.save_config()
        except Exception as e:
            self.error_logging(e, "_pause_timer_for_disconnect")

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

    def _parse_iso_ts(self, s):
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except:
            return datetime.now(timezone.utc)

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

    def perform_periodic_inventory_screenshot_sync(self):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if self._is_fishing_blocked():
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            if not getattr(self, "periodical_inventory_var", None) or not self.periodical_inventory_var.get():
                return
            if not self.detection_running or self.reconnecting_state: return
            try:
                interval_min = float(self.periodical_inventory_interval_var.get())
            except Exception:
                interval_min = 5.0
            if (datetime.now() - getattr(self, "last_inventory_screenshot_time", datetime.min)) < timedelta(minutes=interval_min):
                return
            if not self.check_roblox_procs(): return
            for _ in range(4):
                if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                    return
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.8):
                    return
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
                if not self._sleep_with_cancel(0.35):
                    return
            if items_tab and items_tab[0]:
                try:
                    autoit.mouse_click("left", items_tab[0], items_tab[1], 1, speed=3)
                    if not self._sleep_with_cancel(1):
                        return
                    autoit.mouse_click("left", search_bar[0], search_bar[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(items_tab[0], items_tab[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.35):
                    return
            try:
                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = os.path.join(screenshot_dir, f"inventory_screenshot_{int(time.time())}.png")
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
                    self._sleep_with_cancel(0.22)
            except Exception as e:
                self.error_logging(e, "Error while closing inventory after screenshot")
        except Exception as e:
            self.error_logging(e, "Error in perform_periodic_inventory_screenshot_sync")

    def Global_MouseClick(self, x, y, click=1):
        time.sleep(0.335)
        autoit.mouse_click("left", x, y, click, speed=3)

    def use_br_sc(self, item_name):
        try:
            self._action_scheduler.enqueue_action(lambda: self._use_br_sc_impl(item_name), name=f"use_br_sc:{item_name}", priority=6)
        except Exception:
            try:
                self._use_br_sc_impl(item_name)
            except Exception:
                pass

    def _use_br_sc_impl(self, item_name):
        self._br_sc_running = True
        try:
            def _cancelled():
                return (
                    not self.detection_running
                    or self.reconnecting_state
                    or self.auto_pop_state
                    or self.on_auto_merchant_state
                    or self._is_fishing_blocked()
                    or self.config.get("enable_potion_crafting")
                    or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE")
                    or getattr(self, "_mt_running", False)
                    or (getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get())
                )

            if _cancelled():
                return
            if not self._sleep_with_cancel(1.3):
                return

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            search_bar = self.config.get("search_bar", [855, 358])
            first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
            amount_box = self.config.get("amount_box", [594, 570])
            use_button = self.config.get("use_button", [710, 573])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])

            for _ in range(5):
                if _cancelled():
                    return
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.15):
                    return

            print(f"Using {item_name.capitalize()}")

            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            if not self._sleep_with_cancel(0.2 + inventory_click_delay):
                return
            self.Global_MouseClick(items_tab[0], items_tab[1])
            if not self._sleep_with_cancel(0.23):
                return
            self.Global_MouseClick(items_tab[0], items_tab[1])
            if not self._sleep_with_cancel(0.23):
                return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not self._sleep_with_cancel(0.2 + inventory_click_delay):
                return
            if _cancelled():
                return

            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not self._sleep_with_cancel(0.23):
                return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not self._sleep_with_cancel(0.23):
                return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not self._sleep_with_cancel(0.2 + inventory_click_delay):
                return
            if _cancelled():
                return
            autoit.send(item_name)
            if not self._sleep_with_cancel(0.4 + inventory_click_delay):
                return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not self._sleep_with_cancel(0.4 + inventory_click_delay):
                return
            try:
                if not self._ocr_first_slot_matches(item_name):
                    inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    self._sleep_with_cancel(0.15 + inventory_click_delay)
                    return
            except Exception:
                pass
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not self._sleep_with_cancel(0.4 + inventory_click_delay):
                return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not self._sleep_with_cancel(0.3 + inventory_click_delay):
                return
            if _cancelled():
                return
            self.Global_MouseClick(amount_box[0], amount_box[1])
            if not self._sleep_with_cancel(0.16 + inventory_click_delay):
                return
            autoit.send("^{a}")
            if not self._sleep_with_cancel(0.13 + inventory_click_delay):
                return
            autoit.send("{BACKSPACE}")
            if not self._sleep_with_cancel(0.13 + inventory_click_delay):
                return
            autoit.send('1')
            if not self._sleep_with_cancel(0.13 + inventory_click_delay):
                return

            if _cancelled():
                return
            self.Global_MouseClick(use_button[0], use_button[1])
            if not self._sleep_with_cancel(0.22 + inventory_click_delay):
                return

            if _cancelled():
                return
            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
            self._sleep_with_cancel(0.22 + inventory_click_delay)

        except Exception as e:
            self.error_logging(e, "Error in use_br_sc function.")
        finally:
            self._br_sc_running = False

    def Merchant_Handler(self):
        try:
            def _cancelled():
                return (
                    not self.detection_running
                    or self.reconnecting_state
                    or self.auto_pop_state
                    or self._is_fishing_blocked()
                    or self.config.get("enable_potion_crafting")
                    or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE")
                )

            if _cancelled():
                return False

            self.on_auto_merchant_state = True
            merchant_name_ocr_pos = self.config["merchant_name_ocr_pos"]
            merchant_open_button = self.config["merchant_open_button"]
            first_item_slot_pos = self.config.get("first_item_merchant_slot_pos", [954, 696])
            item_name_ocr_pos = self.config["item_name_ocr_pos"]
            merchant_dialogue_box = self.config["merchant_dialogue_box"]
            merchant_extra_slot = int(self.config.get("merchant_extra_slot", "0"))

            merchant_name = ""
            ocrMisdetect_Key = {
                "heavenly potion": "heavenly potion",
                "rune of galaxy": "rune of galaxy",
                "rune of rainstorm": "rune of rainstorm",
                "strange potion": "strange potion",
                "stella's candle": "stella's candle",
                "merchant tracker": "merchant tracker",
                "random potion sack": "random potion sack",
                "gear a": "gear a",
                "gear b": "gear b",
                "lucky potion": "lucky potion",
                "void coin": "void coin",
                "lucky penny": "lucky penny",
                "mixed potion": "mixed potion",
                "lucky potion l": "lucky potion l",
                "lucky potion xl": "lucky potion xl",
                "speed potion": "speed potion",
                "speed potion l": "speed potion l",
                "speed potion xl": "speed potion xl",
                "oblivion potion": "oblivion potion",
                "potion of bound": "potion of bound",
                "rune of everything": "rune of everything",
                "rune of dust": "rune of dust",
                "rune of nothing": "rune of nothing",
                "rune of corruption": "rune of corruption",
                "rune of hell": "rune of hell",
                "rune of frost": "rune of frost",
                "rune of wind": "rune of wind"
            }

            if not hasattr(self, 'last_merchant_interaction'):
                self.last_merchant_interaction = 0

            if not hasattr(self, 'last_merchant_sent'):
                self.last_merchant_sent = {}

            merchant_cooldown_time = 300
            current_time = time.time()

            if current_time - self.last_merchant_interaction < merchant_cooldown_time:
                return False

            for _ in range(6):
                if _cancelled():
                    return
                autoit.send("e")
                if not self._sleep_with_cancel(0.55):
                    return

            if not self._sleep_with_cancel(0.65):
                return

            # Click through merchant dialogue (no hold)
            for _ in range(8):
                if _cancelled():
                    return
                autoit.mouse_click("left", merchant_dialogue_box[0], merchant_dialogue_box[1], 2, speed=2)
                if not self._sleep_with_cancel(0.55):
                    return

            for _ in range(6):
                if _cancelled():
                    return

                x, y, w, h = merchant_name_ocr_pos
                screenshot = pyautogui.screenshot(region=(x, y, w, h))
                merchant_name_text = self.extract_text_with_easyocr((x, y, w, h)).strip()

                mari_candidates = ["Mari", "Mori", "Marl", "Mar1", "MarI", "Mar!", "Maori"]
                jester_candidates = ["Jester", "Dester", "Jostor", "Jestor", "Joster", "Destor", "Doster", "Dostor", "jester", "dester"]
                rin_candidates = ["Rin", "R1n", "R1N", "RIN", "RiN"]
                try:
                    if fuzzy_match_any(merchant_name_text, mari_candidates, threshold=0.6):
                        merchant_name = "Mari"
                        print("[Merchant Detection]: Mari name found!")
                        break
                    elif fuzzy_match_any(merchant_name_text, jester_candidates, threshold=0.6):
                        merchant_name = "Jester"
                        print("[Merchant Detection]: Jester name found!")
                        break
                    elif fuzzy_match_any(merchant_name_text, rin_candidates, threshold=0.6):
                        merchant_name = "Rin"
                        print("[Merchant Detection]: Rin name found!")
                        break
                except Exception as e:
                    try:
                        if any(name in merchant_name_text for name in mari_candidates):
                            merchant_name = "Mari"
                            print("[Merchant Detection - fallback]: Mari name found!")
                            break
                        if any(name in merchant_name_text for name in jester_candidates):
                            merchant_name = "Jester"
                            print("[Merchant Detection - fallback]: Jester name found!")
                            break
                        if any(name in merchant_name_text for name in rin_candidates):
                            merchant_name = "Rin"
                            print("[Merchant Detection - fallback]: Rin name found!")
                            break
                    except Exception:
                        pass

                if not self._sleep_with_cancel(0.12):
                    return

            if merchant_name:
                last_sent_time = self.last_merchant_sent.get((merchant_name, 'ocr'), 0)
                if current_time - last_sent_time < merchant_cooldown_time:
                    print(f"Merchant {merchant_name} already sent recently lol")
                    return False

                print(f"Opening merchant interface for {merchant_name}")

                x, y = merchant_open_button
                autoit.mouse_click("left", x, y, 3)
                inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
                if not self._sleep_with_cancel(7 + inventory_click_delay):
                    return

                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)

                item_screenshot = pyautogui.screenshot()
                screenshot_path = os.path.join(screenshot_dir,
                                               f"merchant_{merchant_name.lower()}_{int(current_time)}.png")
                item_screenshot.save(screenshot_path)

                self.send_merchant_webhook(merchant_name, screenshot_path, source='ocr')
                self.last_merchant_sent[(merchant_name, 'ocr')] = current_time

                if "merchant_counts" not in self.config:
                    self.config["merchant_counts"] = {"Jester": 0, "Mari": 0, "Rin": 0}
                self.config["merchant_counts"][merchant_name] = self.config["merchant_counts"].get(merchant_name, 0) + 1
                self.save_config()
                self.append_log(f"[Merchant Detection] {merchant_name} count: {self.config['merchant_counts'][merchant_name]}")

                auto_buy_items = self.config.get(f"{merchant_name}_Items", {})
                if not isinstance(auto_buy_items, dict):
                    auto_buy_items = {}
                purchased_items = {}

                total_slots = 5 + merchant_extra_slot
                for slot_index in range(total_slots):
                    if _cancelled():
                        return

                    x, y = first_item_slot_pos
                    slot_x = x + (slot_index * 193)
                    autoit.mouse_click("left", slot_x, y, 2)
                    if not self._sleep_with_cancel(0.15):
                        return

                    x, y, w, h = item_name_ocr_pos
                    screenshot = pyautogui.screenshot(region=(x, y, w, h))
                    item_text = self.extract_text_with_easyocr((x, y, w, h)).strip().lower()

                    self.append_log(f"[Merchant Detection - {merchant_name}] Detected item text: {item_text}")

                    corrected_item_name = item_text.split('|')[0].strip()
                    corrected_candidate = fuzzy_correct_item_name(corrected_item_name, ocrMisdetect_Key, threshold=0.6)
                    if isinstance(corrected_candidate, str) and corrected_candidate != corrected_item_name:
                        print(f"Corrected OCR misdetection: '{item_text}' -> '{corrected_candidate}'")
                        corrected_item_name = corrected_candidate
                    else:
                        for misdetect, correct in ocrMisdetect_Key.items():
                            try:
                                if misdetect in corrected_item_name.lower():
                                    corrected_item_name = correct
                                    print(f"Corrected OCR misdetection (fallback): '{item_text}' -> '{correct}'")
                                    break
                            except Exception:
                                pass

                    print(f"Detected item text: {item_text} | Corrected: {corrected_item_name}")

                    for item_name, (enabled, quantity, rebuy) in auto_buy_items.items():
                        if enabled and corrected_item_name == item_name.lower():
                            purchased_count = purchased_items.get(item_name, 0)

                            if rebuy or purchased_count == 0:
                                self.append_log(
                                    f"[Merchant Detection - {merchant_name}] - Item {item_name} found. Proceeding to buy {quantity}")

                                purchase_amount_button = self.config["purchase_amount_button"]
                                purchase_button = self.config["purchase_button"]

                                autoit.mouse_click("left", *purchase_amount_button)
                                autoit.send(str(quantity))
                                if not self._sleep_with_cancel(0.23):
                                    return

                                autoit.mouse_click("left", *purchase_button, 3)
                                if not self._sleep_with_cancel(3.67):
                                    return

                                purchased_items[item_name] = purchased_count + 1
                                break

                merchant_close_button = self.config.get("merchant_close_button", [1086, 342])
                self.Global_MouseClick(merchant_close_button[0], merchant_close_button[1], click=3)
                self.last_merchant_interaction = current_time
                return True
            else:    
                print("No merchant detected.")
                if not self._sleep_with_cancel(0.67):
                    return False
                self.Global_MouseClick(merchant_open_button[0], merchant_open_button[1], click=3)
                return False

        except Exception as e:
            self.error_logging(e,
                               "Error in Merchant_Handler function \n (If it say valueError: not enough values to unpack (expect 3 got 2) then open both mari and jester setting and click save selection again!)")
            return False
        finally:
            self.on_auto_merchant_state = False

    def _ocr_first_slot_matches(self, expected):
        if not self.config.get("enable_ocr_failsafe", False):
            return True
        ocr_pos = self.config.get("first_item_slot_ocr_pos", [0, 0, 80, 80])
        try:
            x, y, w, h = int(ocr_pos[0]), int(ocr_pos[1]), int(ocr_pos[2]), int(ocr_pos[3])
            img = pyautogui.screenshot(region=(x, y, w, h))
            text = self.extract_text_with_easyocr((x, y, w, h)).strip().lower()
            self.append_log(f"[DEBUG] ocr item first slot failsafe: '{text}'")
        except Exception as e:
            text = ""
            self.append_log(f"[DEBUG] ocr item first slot failsafe exception: {e}")
        expected_lower = (expected or "").lower()
        if expected_lower and expected_lower in text:
            return True
        tokens = re.findall(r'\w{4,}', expected_lower)
        for t in tokens:
            if t in text:
                return True
        try:
            threshold = float(self.config.get("ocr_failsafe_match_threshold", 0.7))
        except Exception:
            threshold = 0.7
        threshold = max(0.0, min(1.0, threshold))
        candidates = [expected_lower] if expected_lower else []
        candidates.extend(tokens)
        if candidates and fuzzy_match_any(text, candidates, threshold=threshold):
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
            if self.is_fishing_mode_enabled():
                return
            if not getattr(self, "anti_afk_var", None) or not self.anti_afk_var.get(): return
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
        interval = 6.7 * 40
        while self.detection_running:
            time.sleep(interval)
            if not self.detection_running:
                break
            try:
                if self.is_fishing_mode_enabled():
                    continue
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

    def _get_auto_pop_biome_entry(self, biome_name):
        try:
            all_biomes = self.config.get("auto_pop_biomes", {})
            if not isinstance(all_biomes, dict):
                return {"enabled": False, "buffs": {}}
            entry = all_biomes.get(biome_name, {})
            if not isinstance(entry, dict):
                return {"enabled": False, "buffs": {}}
            buffs = entry.get("buffs", {})
            if not isinstance(buffs, dict):
                buffs = {}
            return {
                "enabled": bool(entry.get("enabled", False)),
                "buffs": buffs,
            }
        except Exception:
            return {"enabled": False, "buffs": {}}

    def _build_auto_pop_buffs_to_use(self, buff_config):
        buffs_to_use = []
        priority_order = [
            "Xyz Potion",
            "Transcendent Potion",
            "Warp Potion",
            "Heavenly Potion",
            "Godlike Potion",
            "Potion of bound",
            "Oblivion Potion",
        ]

        if not isinstance(buff_config, dict):
            return buffs_to_use

        def _read_buff_state(raw_value):
            try:
                if isinstance(raw_value, (list, tuple)) and len(raw_value) >= 2:
                    return bool(raw_value[0]), max(1, int(raw_value[1]))
            except Exception:
                pass
            return False, 1

        for buff_name in priority_order:
            enabled, amount = _read_buff_state(buff_config.get(buff_name))
            if enabled:
                buffs_to_use.append((buff_name, amount))

        for buff_name, raw_value in buff_config.items():
            if buff_name in priority_order:
                continue
            enabled, amount = _read_buff_state(raw_value)
            if enabled:
                buffs_to_use.append((buff_name, amount))

        return buffs_to_use

    def auto_pop_buffs_for_current_biome(self):
        try:
            self._action_scheduler.enqueue_action(
                self._auto_pop_buffs_for_current_biome_impl,
                name="auto_pop_current_biome",
                priority=0,
            )
        except Exception:
            try:
                self._auto_pop_buffs_for_current_biome_impl()
            except Exception:
                pass

    def _auto_pop_buffs_for_current_biome_impl(self):
        self.auto_pop_state = True
        target_biome = self.current_biome
        try:
            if not target_biome or target_biome == "NORMAL":
                return
            if self.config.get("enable_idle_mode", False):
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get():
                return

            biome_entry = self._get_auto_pop_biome_entry(target_biome)
            if not biome_entry.get("enabled", False):
                return

            buffs_to_use = self._build_auto_pop_buffs_to_use(biome_entry.get("buffs", {}))
            if not buffs_to_use:
                return

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            warp_enabled = any(buff in ("Warp Potion", "Transcendent Potion") for buff, _ in buffs_to_use)

            if (
                self.is_fishing_mode_enabled()
                or bool(getattr(self, "on_auto_merchant_state", False))
                or bool(getattr(self, "_mt_running", False))
                or bool(getattr(self, "_br_sc_running", False))
            ):
                time.sleep(0.3)

            for buff, amount in buffs_to_use:
                if not self.detection_running or self.reconnecting_state:
                    return
                if self.current_biome != target_biome:
                    self.append_log(f"[Auto Pop] Biome changed to {self.current_biome}, stopping auto pop...")
                    self.send_webhook_status(
                        f"Biome changed to {self.current_biome}, stopping auto pop...",
                        color=0x34ebab,
                    )
                    return

                self.append_log(f"[Auto Pop] Using {buff} x{amount} in {target_biome}")
                self.send_webhook_status(f"Using x{amount} {buff} in {target_biome}", color=0x34ebab)

                additional_wait_time = 0
                if buff == "Oblivion Potion":
                    additional_wait_time = 0.85 * amount
                    if warp_enabled:
                        additional_wait_time *= 0.12

                for _ in range(5):
                    if not self.detection_running or self.reconnecting_state:
                        return
                    self.activate_roblox_window()
                    time.sleep(0.35)

                time.sleep(0.57)

                inventory_menu = self.config.get("inventory_menu", [36, 535])
                inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                items_tab = self.config.get("items_tab", [1272, 329])
                search_bar = self.config.get("search_bar", [855, 358])
                first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
                amount_box = self.config.get("amount_box", [594, 570])
                use_button = self.config.get("use_button", [710, 573])

                self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                time.sleep(0.22 + inventory_click_delay)
                self.Global_MouseClick(items_tab[0], items_tab[1])
                time.sleep(0.22 + inventory_click_delay)
                self.Global_MouseClick(search_bar[0], search_bar[1], click=2)
                time.sleep(0.23 + inventory_click_delay)

                if not self.detection_running or self.reconnecting_state:
                    return
                if self.current_biome != target_biome:
                    self.append_log(f"[Auto Pop] Biome changed mid-inventory, closing and stopping")
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    time.sleep(0.15 + inventory_click_delay)
                    return

                keyboard.write(buff.lower())
                time.sleep(0.22 + inventory_click_delay)
                self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
                time.sleep(0.22 + inventory_click_delay)

                try:
                    if not self._ocr_first_slot_matches(buff):
                        self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        time.sleep(0.15 + inventory_click_delay)
                        continue
                except Exception:
                    pass

                self.Global_MouseClick(amount_box[0], amount_box[1])
                time.sleep(0.22 + inventory_click_delay)

                if not self.detection_running or self.reconnecting_state:
                    return

                autoit.send("^{a}")
                time.sleep(0.285 + inventory_click_delay)
                autoit.send("{BACKSPACE}")
                time.sleep(0.285 + inventory_click_delay)
                autoit.send(str(amount))
                time.sleep(0.285 + inventory_click_delay)

                self.Global_MouseClick(use_button[0], use_button[1])
                time.sleep(0.3 + inventory_click_delay)
                self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                time.sleep(0.32 + inventory_click_delay)

                if additional_wait_time > 0:
                    time.sleep(additional_wait_time)

        except Exception as e:
            self.error_logging(e, "Error in auto_pop_buffs_for_current_biome function")
        finally:
            self.auto_pop_state = False

    def auto_pop_buffs(self):
        self.auto_pop_buffs_for_current_biome()

    def auto_pop_buffs_individual(self):
        self.auto_pop_buffs_for_current_biome()