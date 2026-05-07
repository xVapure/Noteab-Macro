
from .base_support import *

class GuiMixin:
    def init_gui(self):
        selected_theme = self.config.get("selected_theme", "solar")
        abslt_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(abslt_path, "NoteabBiomeTracker.ico")

        self.root = ttk.Window(themename=selected_theme)
        self.set_title_threadsafe(f"Coteab Macro {current_ver} (Idle)")
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
        macro_calibrations_frame = ttk.Frame(content_frame) 
        pathing_frame = ttk.Frame(content_frame)
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
            "Macro Calibrations": macro_calibrations_frame, 
            "Remote Access": remote_access_frame,
            "Use item/mouse actions": misc_frame,
            "Movements": pathing_frame,
            "Merchant": merchant_frame,
            "Potion Crafting": hp_craft_frame,
            "Auras": aura_webhook_frame,
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
        self.create_macro_calibrations_tab(macro_calibrations_frame)  
        self.create_pathing_tab(pathing_frame)
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

    def open_biome_settings(self):
        settings_window = ttk.Toplevel(self.root)
        settings_window.title("Biome Settings")

        silly_note_label = ttk.Label(settings_window,
                                     text="GLITCHED, DREAMSPACE & CYBERSPACE are both forced 'everyone' ping grrr >:((",
                                     foreground="red")
        silly_note_label.grid(row=0, columnspan=2, padx=(10, 0), pady=(10, 0))

        biomes = [biome for biome in self.biome_data.keys() if biome not in rare_biomes + ["NORMAL"]]
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

    def create_macro_calibrations_tab(self, frame):
        container = ttk.Frame(frame)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = ttk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Label(scrollable_frame, text="Macro Calibrations (all the calibrations required inside the macro are listed here)", font=("Segoe UI", 12, "bold")).pack(pady=(0, 15))
        ttk.Label(scrollable_frame, text="You don't need to redo your calibrations, it's here for easier navigation :)", font=("Segoe UI", 9)).pack(pady=(0, 15))
        placeholder_link = ttk.Label(
            scrollable_frame, 
            text="Click me if you have no idea on how to calibrate! (Tutorial)", 
            foreground="royalblue", 
            cursor="hand2",
            font=('Segoe UI', 9, 'underline')
        )
        placeholder_link.pack(anchor="w", pady=(0, 15))
        placeholder_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.youtube.com/watch?v=s2S7Bncx9ns"))

        calib_frame = ttk.Frame(scrollable_frame)
        calib_frame.pack(fill="x", padx=10)

        calib_frame = ttk.Frame(scrollable_frame)
        calib_frame.pack(fill="x", padx=10)

        pathing_btn = ttk.Button(
            calib_frame,
            text="Movements Calibration",
            command=self.open_pathing_calibration_window,
            width=30
        )
        pathing_btn.grid(row=0, column=0, padx=5, pady=10, sticky="w")
        ttk.Label(calib_frame, text="Calibrate movements related menu positions").grid(row=0, column=1, padx=10, pady=10, sticky="w")

        quest_btn = ttk.Button(
            calib_frame,
            text="Quest Claim Calibration",
            command=self.open_quest_calibration_window,
            width=30
        )
        quest_btn.grid(row=1, column=0, padx=5, pady=10, sticky="w")
        ttk.Label(calib_frame, text="Calibrate daily quest positions").grid(row=1, column=1, padx=10, pady=10, sticky="w")

        merchant_btn = ttk.Button(
            calib_frame,
            text="Merchant Calibrations",
            command=self.open_merchant_calibration_window,
            width=30
        )
        merchant_btn.grid(row=2, column=0, padx=5, pady=10, sticky="w")
        ttk.Label(calib_frame, text="Calibrate merchant positions and OCR regions").grid(row=2, column=1, padx=10, pady=10, sticky="w")

        potion_btn = ttk.Button(
            calib_frame,
            text="Potion Craft Calibration",
            command=self.open_potion_craft_calibration_window,
            width=30
        )
        potion_btn.grid(row=3, column=0, padx=5, pady=10, sticky="w")
        ttk.Label(calib_frame, text="Calibrate potion crafting positions").grid(row=3, column=1, padx=10, pady=10, sticky="w")

        glitched_btn = ttk.Button(
            calib_frame,
            text="Enable Buff Calibration",
            command=self.open_glitched_buff_calibration_window,
            width=30
        )
        glitched_btn.grid(row=4, column=0, padx=5, pady=10, sticky="w")
        ttk.Label(calib_frame, text="Calibrate enable buff when Glitched positions").grid(row=4, column=1, padx=10, pady=10, sticky="w")

        inventory_btn = ttk.Button(
            calib_frame,
            text="Inventory Click Calibration",
            command=self.open_assign_inventory_window,
            width=30
        )
        inventory_btn.grid(row=5, column=0, padx=5, pady=10, sticky="w")
        ttk.Label(calib_frame, text="Calibrate inventory and item usage positions").grid(row=5, column=1, padx=10, pady=10, sticky="w")
        calib_frame.grid_columnconfigure(0, weight=0)
        calib_frame.grid_columnconfigure(1, weight=1)

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
        link.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.youtube.com/watch?v=s2S7Bncx9ns"))
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
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/appreciation_list.txt"
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
                            text="Player logger",
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

        self.reset_on_rare_var = ttk.BooleanVar(value=self.config.get("reset_on_rare", False))
        reset_on_rare_check = ttk.Checkbutton(frame,
                                            text="Reset character when there's a rare biome",
                                            variable=self.reset_on_rare_var,
                                            command=self.toggle_reset_rare_frame)
        reset_on_rare_check.pack(anchor="w", padx=10, pady=10)

        self.teleport_back_to_limbo_var = ttk.BooleanVar(value=self.config.get("teleport_back_to_limbo", False))
        self.teleport_back_to_limbo_check = ttk.Checkbutton(frame,
                                                            text="Teleport back to Limbo when rare biome ends",
                                                            variable=self.teleport_back_to_limbo_var,
                                                            command=self.save_config)
        self.teleport_back_to_limbo_check.pack(anchor="w", padx=10, pady=10)
        if not self.reset_on_rare_var.get():
            self.teleport_back_to_limbo_check.pack_forget()

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

    def create_notice_tab(self, frame):
        txt = ttk.Text(frame, height=14, wrap="word")
        txt.pack(fill="both", expand=True, padx=5, pady=(5, 90))
        notice_url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/noticetabcontents.txt"
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
            current_version = current_ver
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

    def create_pathing_tab(self, frame):
        path_frame = ttk.LabelFrame(frame, text="Pathing")
        path_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        self.enable_snowman_var = ttk.BooleanVar(value=self.config.get("enable_snowman_path", False))
        snowman_row = ttk.Frame(path_frame)
        snowman_row.pack(fill="x", padx=3, pady=3)

        snowman_check = ttk.Checkbutton(
            snowman_row,
            text="Enable snowman path",
            variable=self.enable_snowman_var,
            command=self.save_config
        )
        snowman_check.pack(side="left", padx=(0,200))
        ttk.Label(snowman_row, text="Claiming interval (minutes):").pack(side="left")
        self.snowman_claim_interval_var = ttk.StringVar(value=str(self.config.get("snowman_claim_interval", "15")))
        interval_entry = ttk.Entry(snowman_row, textvariable=self.snowman_claim_interval_var, width=6)
        interval_entry.pack(side="left", padx=3)
        interval_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.enable_obby_var = ttk.BooleanVar(value=self.config.get("enable_obby_path", False))
        obby_row = ttk.Frame(path_frame)
        obby_row.pack(fill="x", padx=3, pady=3)

        obby_check = ttk.Checkbutton(
            obby_row,
            text="Enable Auto complete obby",
            variable=self.enable_obby_var,
            command=self.save_config
        )
        obby_check.pack(side="left", padx=(0,200))
        ttk.Label(obby_row, text="Claiming interval (minutes):").pack(side="left")
        self.obby_claim_interval_var = ttk.StringVar(value=str(self.config.get("obby_claim_interval", "15")))
        obby_interval_entry = ttk.Entry(obby_row, textvariable=self.obby_claim_interval_var, width=6)
        obby_interval_entry.pack(side="left", padx=3)
        obby_interval_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.pathing_coord_vars = {}

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
        ttk.Label(hp2_frame, text="### MACRO IDLE MODE ###").grid(row=12, column=0, padx=5, sticky="w")
        self.macro_idle_mode_var = ttk.BooleanVar(value=self.config.get("macro_idle_mode", False))
        macro_idle_mode_check = ttk.Checkbutton(
            hp2_frame,
            text="Enable macro idle mode (it will disable all mouse actions and make the macro do nothing aside from detecting biomes/auras)",
            variable=self.macro_idle_mode_var,
            command=self.save_config
        )
        macro_idle_mode_check.grid(row=13, column=0, columnspan=3, padx=5, sticky="w")

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

    def create_merchant_tab(self, frame):
        mari_frame = ttk.LabelFrame(frame, text="Mari")
        mari_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        mari_button = ttk.Button(mari_frame, text="Mari Item Settings", command=self.open_mari_settings)
        mari_button.pack(padx=3, pady=3)

        jester_frame = ttk.LabelFrame(frame, text="Jester")
        jester_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        jester_button = ttk.Button(jester_frame, text="Jester Item Settings", command=self.open_jester_settings)
        jester_button.pack(padx=3, pady=3)

        rin_frame = ttk.LabelFrame(frame, text="Rin")
        rin_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        rin_button = ttk.Button(rin_frame, text="Rin Item Settings", command=self.open_rin_settings)
        rin_button.pack(padx=3, pady=3)

        ttk.Label(frame,
                  text="Merchant item extra slot\n(extra slot if your mouse missed/cannot reach to merchant's 5th slot):").grid(
            row=2, column=0, padx=5, sticky="w")
        self.merchant_extra_slot_var = ttk.StringVar(value=self.config.get("merchant_extra_slot", "0"))
        merchant_extra_slot_entry = ttk.Entry(frame, textvariable=self.merchant_extra_slot_var, width=15)
        merchant_extra_slot_entry.grid(row=2, column=1, padx=0, pady=3, sticky="w")
        merchant_extra_slot_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.mt_var = ttk.BooleanVar(value=self.config.get("merchant_teleporter", False))
        mt_check = ttk.Checkbutton(
            frame,
            text="Enable Auto Merchant (requires merchant teleporter)",
            variable=self.mt_var,
            command=self.save_config
        )
        mt_check.grid(row=3, column=0, padx=5, pady=3, sticky="w")

        ttk.Label(frame, text="Usage Duration (minutes):").grid(row=3, column=1, padx=5, sticky="w")
        self.mt_duration_var = ttk.StringVar(value=self.config.get("mt_duration", "1"))
        mt_duration_entry = ttk.Entry(frame, textvariable=self.mt_duration_var, width=10)
        mt_duration_entry.grid(row=3, column=2, padx=5, sticky="w")
        mt_duration_entry.bind("<FocusOut>", lambda event: self.save_config())

        self.auto_merchant_in_limbo_var = ttk.BooleanVar(value=self.config.get("auto_merchant_in_limbo", False))
        self.auto_merchant_in_limbo_check = ttk.Checkbutton(
            frame,
            text="Auto Merchant in Limbo",
            variable=self.auto_merchant_in_limbo_var,
            command=self.save_config
        )

        def update_auto_merchant_in_limbo_visibility(*args):
            if self.mt_var.get():
                self.auto_merchant_in_limbo_check.grid(row=4, column=0, padx=5, pady=3, sticky="w")
            else:
                try:
                    self.auto_merchant_in_limbo_check.grid_remove()
                except Exception:
                    pass

        update_auto_merchant_in_limbo_visibility()
        try:
            self.mt_var.trace_add('write', update_auto_merchant_in_limbo_visibility)
        except Exception:
            try:
                self.mt_var.trace('w', update_auto_merchant_in_limbo_visibility)
            except Exception:
                pass

        # Ping Mari
        self.ping_mari_var = ttk.BooleanVar(value=self.config.get("ping_mari", False))
        ping_mari_check = ttk.Checkbutton(
            frame, text="Ping if Mari found? (Custom Ping UserID/RoleID: &roleid)",
            variable=self.ping_mari_var, command=self.save_config)
        ping_mari_check.grid(row=5, column=0, padx=5, pady=3, sticky="w")

        self.mari_user_id_var = ttk.StringVar(value=self.config.get("mari_user_id", ""))
        mari_user_id_entry = ttk.Entry(frame, textvariable=self.mari_user_id_var, width=15)
        mari_user_id_entry.grid(row=5, column=1, padx=0, pady=3, sticky="w")
        mari_user_id_entry.bind("<FocusOut>", lambda event: self.save_config())

        mari_label = ttk.Label(frame, text="")
        mari_label.grid(row=5, column=2, padx=5, pady=3, sticky="w")

        # Ping Jester
        self.ping_jester_var = ttk.BooleanVar(value=self.config.get("ping_jester", False))
        ping_jester_check = ttk.Checkbutton(
            frame, text="Ping if Jester found? (Custom Ping UserID/RoleID: &roleid)",
            variable=self.ping_jester_var, command=self.save_config)
        ping_jester_check.grid(row=6, column=0, padx=5, pady=3, sticky="w")

        self.jester_user_id_var = ttk.StringVar(value=self.config.get("jester_user_id", ""))
        jester_user_id_entry = ttk.Entry(frame, textvariable=self.jester_user_id_var, width=15)
        jester_user_id_entry.grid(row=6, column=1, padx=0, pady=3, sticky="w")
        jester_user_id_entry.bind("<FocusOut>", lambda event: self.save_config())

        jester_label = ttk.Label(frame, text="")
        jester_label.grid(row=6, column=2, padx=5, pady=3, sticky="w")

        # Ping Rin
        self.ping_rin_var = ttk.BooleanVar(value=self.config.get("ping_rin", False))
        ping_rin_check = ttk.Checkbutton(
            frame, text="Ping if Rin found? (Custom Ping UserID/RoleID: &roleid)",
            variable=self.ping_rin_var, command=self.save_config)
        ping_rin_check.grid(row=7, column=0, padx=5, pady=3, sticky="w")

        self.rin_user_id_var = ttk.StringVar(value=self.config.get("rin_user_id", ""))
        rin_user_id_entry = ttk.Entry(frame, textvariable=self.rin_user_id_var, width=15)
        rin_user_id_entry.grid(row=7, column=1, padx=0, pady=3, sticky="w")
        rin_user_id_entry.bind("<FocusOut>", lambda event: self.save_config())

        rin_label = ttk.Label(frame, text="")
        rin_label.grid(row=7, column=2, padx=5, pady=3, sticky="w")

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
            "rnd.xy, imsomeone - For doing external works that I was too lazy to do tysm.",
            "Finnerinch - Former developer.",
            """All the testers that made the update possible with as less flaws as possible. Notably: "imsomeone", "cheshington", "tilesdrop", "kira_drago2", "gummyballer", "retelteel", "mightbeanormalguest", "gonebon" and others."""
        ]

        credits_text.config(state='normal')
        credits_text.delete("1.0", "end")
        for person in extra_credits:
            credits_text.insert("end", f"- {person}\n")
        credits_text.config(state='disabled')
