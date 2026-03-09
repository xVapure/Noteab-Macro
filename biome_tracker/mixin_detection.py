from .base_support import *

class DetectionMixin:
    def load_logs(self):
        if os.path.exists('macro_logs.txt'):
            with open('macro_logs.txt', 'r', encoding='utf-8', errors='ignore') as file:
                lines = file.read().splitlines()
                return lines
        return []

    def load_biome_data(self):
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/biomes_data.json"
        eventUrl = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/active_events.json"

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

    def error_logging(self, exception, custom_message=None, max_log_size=3 * 1024 * 1024):
        log_file = "error_logs.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_type = type(exception).__name__
        error_message = str(exception)
        stack_trace = traceback.format_exc()

        if not os.path.exists(log_file):
            with open(log_file, "w", encoding="utf-8") as log:
                log.write("Error Log File Created\n")
                log.write("-" * 40 + "\n")

        if os.path.exists(log_file) and os.path.getsize(log_file) > max_log_size:
            with open(log_file, "r", encoding="utf-8") as log:
                lines = log.readlines()
            with open(log_file, "w", encoding="utf-8") as log:
                log.writelines(lines[-1000:])

        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"\n[{timestamp}] ERROR LOG\n")
            log.write(f"Error Type: {error_type}\n")
            log.write(f"Error Message: {error_message}\n")
            if custom_message:
                log.write(f"Custom Message: {custom_message}\n")
            log.write(f"Traceback:\n{stack_trace}\n")
            log.write("-" * 40 + "\n")

        print(f"Error logged to {log_file}.")

    def save_logs(self):
        log_file_path = 'macro_logs.txt'

        if os.path.exists(log_file_path) and os.path.getsize(log_file_path) > 2 * 1024 * 1024:
            with open(log_file_path, 'w', encoding='utf-8') as file:
                file.write("")
        else:
            with open(log_file_path, 'a', encoding='utf-8') as file:
                for log in self.logs:
                    file.write(log + "\n")

    def take_aura_screenshot_now(self, force=False):
        try:
            if not force:
                if not getattr(self, "periodical_aura_var", None) or not self.periodical_aura_var.get():
                    return
                if self.config.get("enable_idle_mode", False):
                    return
            if not self.check_roblox_procs():
                return

            for _ in range(4):
                self.activate_roblox_window()
                time.sleep(0.35)

            aura_menu = self.config.get("aura_menu", [0, 0])
            search_bar = self.config.get(
                "aura_search_bar",
                self.config.get("search_bar", [834, 364]),
            )
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
            if aura_menu and aura_menu[0]:
                try:
                    autoit.mouse_click("left", aura_menu[0], aura_menu[1], 1, speed=3)
                    time.sleep(0.67)
                    autoit.mouse_click("left", search_bar[0], search_bar[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(aura_menu[0], aura_menu[1])
                    except Exception:
                        pass
                time.sleep(0.67)
                try:
                    screenshot_dir = os.path.join(os.getcwd(), "images")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    filename = os.path.join(screenshot_dir, f"aura_screenshot_{int(time.time())}.png")
                    img = pyautogui.screenshot()
                    img.save(filename)
                    self.send_aura_screenshot_webhook(filename)
                    self.last_aura_screenshot_time = datetime.now()
                    autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    time.sleep(0.67)
                except Exception as e:
                    self.error_logging(e, "Error taking/sending forced aura screenshot")
        except Exception as e:
            self.error_logging(e, "Error in take_aura_screenshot_now")

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

    def confirm_biome_popup(self, biome):
        cb = getattr(self, "on_biome_confirm_request", None)
        if callable(cb):
            try:
                result = cb(biome)
                if result is None:
                    return None
                result = bool(result)
                return result
            except Exception as e:
                self.error_logging(e, "Error in confirm_biome_popup callback")
                return None
        return None


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
            session_str = self.get_total_session_time()
            if hasattr(self, "session_label"):
                self.session_label.config(text=f"Running Session: {session_str}")
            if getattr(self, "_session_window_reset_performed", False):
                try:
                    self.save_config()
                except Exception:
                    pass
                self._session_window_reset_performed = False
        except Exception as e:
            self.error_logging(e, "Error in update_session_time function.")

    def display_logs(self, logs=None):
        if not hasattr(self, "logs_text"):
            return
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
        timestamp = datetime.now().strftime("%d/%m/%y %H:%M:%S")
        stamped = f"[{timestamp}] {message}"
        self.logs.append(stamped)
        try:
            print(f"[log] {stamped}")
        except (UnicodeEncodeError, UnicodeDecodeError):
            print(f"[log] {stamped.encode('ascii', 'replace').decode('ascii')}")
        self.save_logs()
        if hasattr(self, "logs_text"):
            self.display_logs()
            self.logs_text.see(ttk.END)

    def show_reconnect_info(self):
        messagebox.showinfo(
            "Auto Reconnect Info",
            "(?) This feature only able to reconnect if:\n \n"
            "(1) Your private server link is valid. Supported formats include:\n"
            "    - Private server code links (privateServerLinkCode=...)\n"
            "    - Share links (https://www.roblox.com/share?code=...&type=Server)\n \n"
            "(2) Make sure to calibrate mouse click for 'Start' button in 'Assign Inventory Click' \n \n"
            "(3) If reconnect fails, try a different link format (share link or private server code link). \n \n"
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

            # reset disconnect tracking so the macro doesnt log old disconnect 
            self._disconnect_log_file = None
            self._last_position_disconnect = 0
            self._last_disconnect_time = 0
            self._disconnect_handled = False
            self.has_sent_disconnected_message = False

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
            self.set_title_threadsafe(f"""Coteab Macro {current_ver} (Running)""")
            self.send_webhook_status("Macro started!", color=0x64ff5e)

            threads = [
                (self.check_disconnect_loop, "Disconnect Check"),
                (self.biome_loop_check, "Biome Check"),
                (self.biome_itemchange_loop, "Item Change"),
                (self.aura_loop_check, "Aura Check"),
                (self.anti_afk_loop, "Anti-AFK"),
                (self.quest_claim_loop, "Quest Claim"),
                (self.obby_path_loop, "Obby Path"),
            ]

            for thread_func, name in threads:
                thread = threading.Thread(target=thread_func, name=name, daemon=True)
                thread.start()

            self.perform_anti_afk_action()
            
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
            self.set_title_threadsafe(f"Coteab Macro {current_ver} (Stopped)")
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
                    "[Merchant]: Jester has arrived on the island!!"
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
                            "[Merchant]: Jester has arrived on the island!!"
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
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/auras.json"
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
                                    if getattr(self, "aura_screenshot_var", None) and self.aura_screenshot_var.get() and not self.is_fishing_mode_enabled():
                                        for _ in range(5):
                                            self.activate_roblox_window()
                                            time.sleep(0.75)

                                        screenshot_dir = os.path.join(os.getcwd(), "images")
                                        os.makedirs(screenshot_dir, exist_ok=True)
                                        filename = os.path.join(screenshot_dir, f"aura_{int(time.time())}.png")
                                        img = pyautogui.screenshot()
                                        img.save(filename)
                                        screenshot_path = filename
                                        self.append_log(f"[Aura Screenshot] Saved to: {screenshot_path}, exists: {os.path.exists(screenshot_path)}")
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
                                    if getattr(self, "aura_screenshot_var", None) and self.aura_screenshot_var.get() and not self.is_fishing_mode_enabled():
                                        for _ in range(5):
                                            self.activate_roblox_window()
                                            time.sleep(0.75)

                                        screenshot_dir = os.path.join(os.getcwd(), "images")
                                        os.makedirs(screenshot_dir, exist_ok=True)
                                        filename = os.path.join(screenshot_dir, f"aura_{int(time.time())}.png")
                                        img = pyautogui.screenshot()
                                        img.save(filename)
                                        screenshot_path = filename
                                        self.append_log(f"[Aura Screenshot] Saved to: {screenshot_path}, exists: {os.path.exists(screenshot_path)}")
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
                        if biome != self.current_biome:
                            last_biome = self.current_biome
                            self.current_biome = biome
                            threading.Thread(target=self.handle_biome_detection, args=(biome, last_biome)).start()
                        return

        except Exception as e:
            self.error_logging(e, "Error in check_biome_in_logs function :skull:")

    def handle_biome_detection(self, biome, last_biome=None):
        try:
            if last_biome is None:
                last_biome = self.current_biome

            if last_biome and last_biome != biome and last_biome != "NORMAL":
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

            # son im crine - this is to send the current biome to frontend 
            if hasattr(self, "on_biome_update") and callable(self.on_biome_update):
                self.on_biome_update(biome)

            if (
                last_biome in rare_biomes
                and biome not in rare_biomes
                and bool(getattr(self, "_pending_fishing_failsafe_rejoin", False))
            ):
                self._pending_fishing_failsafe_rejoin = False
                self.append_log(
                    f"[FishingMode] Rare biome ended with deferred failsafe pending. Rejoining from {biome}."
                )
                self.send_webhook_status(
                    "Rare biome ended. Running the delayed fishing failsafe rejoin now.",
                    color=0xffcc00,
                )
                threading.Thread(target=self.terminate_roblox_processes, daemon=True).start()
                return

            message_type = self.config["biome_notifier"].get(biome, "None")

            if biome in rare_biomes:
                message_type = "Ping"
                if self.config.get("record_rare_biome", False):
                    self.trigger_biome_record()
                try:
                    if getattr(self, "reset_on_rare_var", None) and self.reset_on_rare_var.get() and not (self.config.get("enable_idle_mode", False)) and not self.is_fishing_mode_enabled():
                        self._action_scheduler.enqueue_action(self._reset_on_rare_impl, name="reset_rare", priority=0)
                except Exception:
                    pass

            if biome != "NORMAL":
                popup_window_active = False
                if getattr(self, "just_reconnected", False):
                    deadline = getattr(self, "reconnect_confirm_deadline", None)
                    if isinstance(deadline, (int, float)):
                        popup_window_active = time.monotonic() <= deadline
                    else:
                        # Backward-safe fallback for states created before this field exists.
                        popup_window_active = True
                    if not popup_window_active:
                        self.just_reconnected = False
                        self.reconnect_confirm_deadline = None

                if biome in rare_biomes and popup_window_active:
                    try:
                        confirmed = self.confirm_biome_popup(biome)
                    except Exception:
                        confirmed = None
                    self.just_reconnected = False
                    self.reconnect_confirm_deadline = None
                    if confirmed is False:
                        self.stop_detection()
                        return
                    if confirmed is None:
                        try:
                            self.send_webhook_status(
                                f"No response to rare-biome popup within 10 seconds ({biome}). Continuing macro.",
                                color=0xffcc00
                            )
                        except Exception:
                            pass
                # rare biome sshot       
                screenshot_path = None
                if biome in rare_biomes and self.config.get("rare_biome_screenshot", False):
                    try:
                        for _ in range(5):
                            self.activate_roblox_window()
                            time.sleep(0.75)
                        screenshot_dir = os.path.join(os.getcwd(), "images")
                        os.makedirs(screenshot_dir, exist_ok=True)
                        screenshot_path = os.path.join(screenshot_dir, f"rare_biome_{biome.lower()}_{int(time.time())}.png")
                        img = pyautogui.screenshot()
                        img.save(screenshot_path)
                        self.append_log(f"[Rare Biome Screenshot] Saved screenshot: {screenshot_path}")
                    except Exception as e:
                        self.error_logging(e, "Error taking rare biome screenshot")
                        screenshot_path = None

                self.send_webhook(biome, message_type, "start", screenshot_path=screenshot_path)

            if last_biome in rare_biomes and biome not in rare_biomes:
                try:
                    if getattr(self, "teleport_back_to_limbo_var", None) and self.teleport_back_to_limbo_var.get() and not (self.config.get("enable_idle_mode", False)) and not self.is_fishing_mode_enabled():
                        self._action_scheduler.enqueue_action(self._teleport_crack_impl, name="teleport_back", priority=0)
                except Exception:
                    pass

            auto_pop_biomes = self.config.get("auto_pop_biomes", {})
            auto_pop_entry = auto_pop_biomes.get(biome, {}) if isinstance(auto_pop_biomes, dict) else {}
            if isinstance(auto_pop_entry, dict) and bool(auto_pop_entry.get("enabled", False)):
                with self.lock:
                    if not self.config.get("enable_idle_mode", False):
                        self.auto_pop_buffs_for_current_biome()

            if biome == "GLITCHED":
                with self.lock:
                    if self.config.get("enable_buff_glitched", False) and not self.is_fishing_mode_enabled():
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
            self.just_reconnected = True
            self.reconnect_confirm_deadline = time.monotonic() + 60
            self.set_title_threadsafe(f"""Coteab Macro {current_ver} (Running)""")
            self.save_config()
        except Exception as e:
            self.error_logging(e, "_resume_timer_after_reconnect")

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

    def auto_biome_change(self):
        if self.is_fishing_mode_enabled():
            return

        try:
            mt_cooldown = timedelta(minutes=int(self.mt_duration_var.get()) if self.mt_duration_var.get() else 1)
        except ValueError:
            mt_cooldown = timedelta(minutes=1)

        try:
            if (not self.reconnecting_state
                and not (self.config.get("enable_idle_mode", False))
                and not (getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get())
                and getattr(self, "periodical_aura_var", None) and self.periodical_aura_var.get()):
                try:
                    interval_min = float(self.periodical_aura_interval_var.get())
                except Exception:
                    interval_min = 5.0
                if (datetime.now() - getattr(self, "last_aura_screenshot_time", datetime.min)) >= timedelta(minutes=interval_min):
                    self._action_scheduler.enqueue_action(self.perform_periodic_aura_screenshot_sync, name="periodical:aura", priority=2)
        except Exception:
            pass

        try:
            if (not self.reconnecting_state
                and not (self.config.get("enable_idle_mode", False))
                and not (getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get())
                and getattr(self, "periodical_inventory_var", None) and self.periodical_inventory_var.get()):
                try:
                    interval_min = float(self.periodical_inventory_interval_var.get())
                except Exception:
                    interval_min = 5.0
                if (datetime.now() - getattr(self, "last_inventory_screenshot_time", datetime.min)) >= timedelta(minutes=interval_min):
                    self._action_scheduler.enqueue_action(self.perform_periodic_inventory_screenshot_sync, name="periodical:inventory", priority=3)
        except Exception:
            pass

        if self.mt_var.get() and datetime.now() - self.last_mt_time >= mt_cooldown and not getattr(self,
                                                                                                    '_br_sc_running',
                                                                                                    False) and not getattr(
                        self, '_mt_running', False) and not getattr(self, '_remote_running', False) and datetime.now() >= getattr(self, '_cancel_next_actions_until',
                                                                                datetime.min) and not (self.config.get("enable_idle_mode", False)):
            self.use_merchant_teleporter()
            self.last_mt_time = datetime.now()

        try:
            sc_cooldown = timedelta(minutes=int(self.sc_duration_var.get()) if self.sc_duration_var.get() else 20)
        except ValueError:
            sc_cooldown = timedelta(minutes=20)

        if self.sc_var.get() and datetime.now() - self.last_sc_time >= sc_cooldown and not getattr(self,
                                                                                                    '_br_sc_running',
                                                                                                    False) and not getattr(
                        self, '_mt_running', False) and not getattr(self, '_remote_running', False) and datetime.now() >= getattr(self, '_cancel_next_actions_until',
                                                                                datetime.min) and not (self.config.get("enable_idle_mode", False)):
            self.use_br_sc('strange controller')
            self.last_sc_time = datetime.now()

        try:
            br_cooldown = timedelta(minutes=int(self.br_duration_var.get()) if self.br_duration_var.get() else 35)
        except ValueError:
            br_cooldown = timedelta(minutes=35)

        if self.br_var.get() and datetime.now() - self.last_br_time >= br_cooldown and not getattr(self,
                                                                                                    '_br_sc_running',
                                                                                                    False) and not getattr(
                        self, '_mt_running', False) and not getattr(self, '_remote_running', False) and datetime.now() >= getattr(self, '_cancel_next_actions_until',
                                                                                datetime.min) and not (self.config.get("enable_idle_mode", False)):
            self.use_br_sc('biome randomizer')
            self.last_br_time = datetime.now()

    def perform_periodic_aura_screenshot_sync(self):
        if not self.detection_running or self.reconnecting_state: 
            return
        if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get():
            return 
        inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if not getattr(self, "periodical_aura_var", None) or not self.periodical_aura_var.get():
                return
            try:
                interval_min = float(self.periodical_aura_interval_var.get())
            except Exception:
                interval_min = 5.0
            if (datetime.now() - getattr(self, "last_aura_screenshot_time", datetime.min)) < timedelta(minutes=interval_min):
                return
            if not self.check_roblox_procs(): return
            
            for _ in range(4):
                self.activate_roblox_window()
                time.sleep(0.8)
            
            aura_menu = self.config.get("aura_menu", [0, 0])
            search_bar = self.config.get(
                "aura_search_bar",
                self.config.get("search_bar", [834, 364]),
            )
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
                    screenshot_dir = os.path.join(os.getcwd(), "images")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    filename = os.path.join(screenshot_dir, f"aura_screenshot_{int(time.time())}.png")
                    img = pyautogui.screenshot()
                    img.save(filename)
                    self.send_aura_screenshot_webhook(filename)
                    self.last_aura_screenshot_time = datetime.now()
                    autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    time.sleep(0.67)
                except Exception as e:
                    self.error_logging(e, "Error taking/sending aura screenshot")
        except Exception as e:
            self.error_logging(e, "Error in perform_periodic_aura_screenshot_sync")

    def use_merchant_teleporter(self):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            self._action_scheduler.enqueue_action(self._merchant_teleporter_impl, name="merchant_tele", priority=5)
        except Exception:
            try:
                if self.config.get("enable_idle_mode", False):
                    return
                self._merchant_teleporter_impl()
            except Exception:
                pass

    def _merchant_teleporter_impl(self):
        if getattr(self, '_br_sc_running', False): return
        if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
        self._last_merchant_sequence_ran = False
        self._last_merchant_sequence_requires_reset = False
        self._mt_running = True
        try:
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return

            if hasattr(self, 'last_merchant_interaction') and self.last_merchant_interaction:
                merchant_cooldown_time = 300
                if time.time() - self.last_merchant_interaction < merchant_cooldown_time: return

            time.sleep(0.75)

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            search_bar = self.config.get("search_bar", [855, 358])
            first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
            amount_box = self.config.get("amount_box", [594, 570])
            use_button = self.config.get("use_button", [710, 573])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])

            for _ in range(4):
                if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                    "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return
                self.activate_roblox_window()
                time.sleep(0.3)

            current_x, current_y = autoit.mouse_get_pos()
            autoit.mouse_down("right")
            time.sleep(0.1)
            autoit.mouse_move(current_x, current_y + 75, 0)
            time.sleep(0.1)
            autoit.mouse_up("right")
            time.sleep(0.92)

            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            time.sleep(0.24 + inventory_click_delay)

            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.23)
            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.23)
            self.Global_MouseClick(items_tab[0], items_tab[1])
            time.sleep(0.24 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return

            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.23)
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.23)
            self.Global_MouseClick(search_bar[0], search_bar[1])
            time.sleep(0.27 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return
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
                "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return

            time.sleep(0.17 + inventory_click_delay)
            self.Global_MouseClick(amount_box[0], amount_box[1])
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return
            autoit.send("^{a}")
            time.sleep(0.15 + inventory_click_delay)
            autoit.send("{BACKSPACE}")
            time.sleep(0.15 + inventory_click_delay)
            autoit.send('1')
            time.sleep(0.14 + inventory_click_delay)
            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return
            autoit.mouse_click("left", use_button[0], use_button[1], 3)
            time.sleep(0.23 + inventory_click_delay)

            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
            time.sleep(0.23 + inventory_click_delay)
            self._last_merchant_sequence_ran = True
            merchant_completed = bool(self.Merchant_Handler())
            self._last_merchant_sequence_requires_reset = merchant_completed

            if not self.detection_running or self.reconnecting_state or self.auto_pop_state or self.on_auto_merchant_state or self.config.get(
                "enable_potion_crafting") or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"): return

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
            self._cancel_next_actions_until = datetime.min

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
