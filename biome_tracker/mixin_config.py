"""Auto-extracted mixin methods from legacy tracker."""

from .base_support import *
from .config import load_config as core_load_config, save_config as core_save_config

class ConfigMixin:
    """Methods grouped under: config."""
    def save_config(self):
        try:
            config = core_load_config()
        except Exception:
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
            # ── Core / Session ──
            "webhook_url": webhook_save_val,
            "private_server_link": self.private_server_link_entry.get() if hasattr(self, "private_server_link_entry") else self.config.get("private_server_link", ""),
            "roblox_username": self.config.get("roblox_username", ""),
            "auto_reconnect": self.auto_reconnect_var.get(),
            "biome_notifier": {biome: self.variables[biome].get() for biome in self.biome_data} if self.variables else self.config.get("biome_notifier", {}),
            "biome_counts": self.biome_counts,
            "merchant_counts": getattr(self, "merchant_counts", self.config.get("merchant_counts", {"Jester": 0, "Mari": 0, "Rin": 0})),
            "custom_biome_overrides": self.config.get("custom_biome_overrides", {}),
            "session_time": session_time,
            "session_window_start": session_window_start_val,
            "macro_last_start": macro_last_start_val,
            "selected_theme": self.root.style.theme.name if hasattr(self, "root") and self.root is not None and hasattr(self.root, "style") else self.config.get("selected_theme", "solar"),
            "dont_ask_for_update": self.config.get("dont_ask_for_update", False),
            "auto_update_enabled": self.auto_update_enabled_var.get() if hasattr(self, "auto_update_enabled_var") else self.config.get("auto_update_enabled", True),
            "anti_afk": self.anti_afk_var.get(),
            "enable_idle_mode": self.macro_idle_mode_var.get() if hasattr(self, "macro_idle_mode_var") else self.config.get("enable_idle_mode", False),
            "auto_roblox_fullscreen": self.auto_roblox_fullscreen_var.get() if hasattr(self, "auto_roblox_fullscreen_var") else self.config.get("auto_roblox_fullscreen", False),
            "enable_glitch_effect": self.enable_glitch_effect_var.get() if hasattr(self, "enable_glitch_effect_var") else self.config.get("enable_glitch_effect", False),
            "auto_chat_close": self.config.get("auto_chat_close", False),
            "fishing_mode": self.config.get("fishing_mode", False),

            # ── Item Use (BR / SC / MT) ──
            "biome_randomizer": self.br_var.get(),
            "br_duration": self.br_duration_var.get(),
            "strange_controller": self.sc_var.get(),
            "sc_duration": self.sc_duration_var.get(),
            "merchant_teleporter": self.mt_var.get(),
            "mt_duration": self.mt_duration_var.get(),
            "auto_merchant_in_limbo": self.auto_merchant_in_limbo_var.get(),
            "merchant_extra_slot": self.merchant_extra_slot_var.get(),

            # ── Auto Pop / Glitched ──
            "auto_pop_glitched": self.auto_pop_glitched_var.get(),
            "auto_pop_dreamspace": self.auto_pop_dreamspace_var.get() if hasattr(self, "auto_pop_dreamspace_var") else self.config.get("auto_pop_dreamspace", False),
            "auto_pop_cyberspace": self.auto_pop_cyberspace_var.get() if hasattr(self, "auto_pop_cyberspace_var") else self.config.get("auto_pop_cyberspace", False),
            "auto_pop_biomes": self.config.get("auto_pop_biomes", {}),
            "cyberspace_only_warp": self.cyberspace_only_warp_var.get() if hasattr(self, "cyberspace_only_warp_var") else self.config.get("cyberspace_only_warp", False),
            "enable_buff_glitched": self.enable_buff_glitched_var.get() if hasattr(self, "enable_buff_glitched_var") else self.config.get("enable_buff_glitched", False),
            "glitched_menu_button": self.config.get("glitched_menu_button", [0, 0]),
            "glitched_settings_button": self.config.get("glitched_settings_button", [0, 0]),
            "glitched_buff_enable_button": self.config.get("glitched_buff_enable_button", [0, 0]),
            "auto_buff_glitched": {
                buff: (self.buff_vars[buff].get(), int(self.buff_amount_vars[buff].get()))
                for buff in self.buff_vars
            } if self.buff_vars else self.config.get("auto_buff_glitched", {}),
            "reset_on_rare": self.reset_on_rare_var.get() if hasattr(self, "reset_on_rare_var") else self.config.get("reset_on_rare", False),
            "teleport_back_to_limbo": self.teleport_back_to_limbo_var.get() if hasattr(self, "teleport_back_to_limbo_var") else self.config.get("teleport_back_to_limbo", False),

            # ── Merchant Calibration ──
            "Mari_Items": self.config.get("Mari_Items", {}),
            "Jester_Items": self.config.get("Jester_Items", {}),
            "Rin_Items": self.config.get("Rin_Items", {}),
            "ping_mari": self.ping_mari_var.get(),
            "mari_user_id": self.mari_user_id_var.get(),
            "ping_jester": self.ping_jester_var.get(),
            "jester_user_id": self.jester_user_id_var.get(),
            "ping_rin": self.ping_rin_var.get(),
            "rin_user_id": self.rin_user_id_var.get(),
            "merchant_open_button": self.config.get("merchant_open_button", [579, 906]),
            "merchant_dialogue_box": self.config.get("merchant_dialogue_box", [1114, 796]),
            "purchase_amount_button": self.config.get("purchase_amount_button", [700, 584]),
            "purchase_button": self.config.get("purchase_button", [739, 635]),
            "first_item_merchant_slot_pos": self.config.get("first_item_merchant_slot_pos", [954, 696]),
            "merchant_name_ocr_pos": self.config.get("merchant_name_ocr_pos", [746, 680, 103, 32]),
            "item_name_ocr_pos": self.config.get("item_name_ocr_pos", [728, 731, 218, 24]),
            "merchant_close_button": self.config.get("merchant_close_button", [1086, 342]),

            # ── Aura Detection ──
            "enable_aura_detection": self.enable_aura_detection_var.get(),
            "ping_minimum": self.ping_minimum_var.get(),
            "aura_user_id": self.aura_user_id_var.get(),
            "enable_aura_record": self.enable_aura_record_var.get(),
            "aura_record_keybind": self.aura_record_keybind_var.get(),
            "aura_record_minimum": self.aura_record_minimum_var.get(),
            "aura_detection_screenshot": self.aura_screenshot_var.get(),
            "record_rare_biome": self.record_rarest_biome_var.get(),
            "rare_biome_record_keybind": self.rarest_biome_keybind_var.get(),
            "rare_biome_screenshot": self.rare_biome_screenshot_var.get() if hasattr(self, "rare_biome_screenshot_var") else self.config.get("rare_biome_screenshot", False),

            # ── Periodical Screenshots ──
            "periodical_aura_screenshot": self.periodical_aura_var.get() if hasattr(self, "periodical_aura_var") else self.config.get("periodical_aura_screenshot", False),
            "periodical_aura_interval": self.periodical_aura_interval_var.get() if hasattr(self, "periodical_aura_interval_var") else self.config.get("periodical_aura_interval", "5"),
            "periodical_inventory_screenshot": self.periodical_inventory_var.get() if hasattr(self, "periodical_inventory_var") else self.config.get("periodical_inventory_screenshot", False),
            "periodical_inventory_interval": self.periodical_inventory_interval_var.get() if hasattr(self, "periodical_inventory_interval_var") else self.config.get("periodical_inventory_interval", "5"),

            # ── Inventory Calibration ──
            "inventory_menu": self.config.get("inventory_menu", [36, 535]),
            "items_tab": self.config.get("items_tab", [1272, 329]),
            "search_bar": self.config.get("search_bar", [855, 358]),
            "first_item_inventory_slot_pos": self.config.get("first_item_inventory_slot_pos", [845, 460]),
            "amount_box": self.config.get("amount_box", [594, 570]),
            "use_button": self.config.get("use_button", [710, 573]),
            "inventory_close_button": self.config.get("inventory_close_button", [1418, 298]),
            "reconnect_start_button": self.config.get("reconnect_start_button", [954, 876]),
            "inventory_click_delay": self.click_delay_var.get(),
            "first_item_slot_ocr_pos": self.config.get("first_item_slot_ocr_pos", [0, 0, 80, 80]),
            "enable_ocr_failsafe": self.enable_ocr_failsafe_var.get(),
            "aura_menu": self.config.get("aura_menu", [1200, 500]),
            "aura_search_bar": self.config.get("aura_search_bar", [834, 364]),
            "first_aura_slot_pos": self.config.get("first_aura_slot_pos", [0, 0]),
            "equip_aura_button": self.config.get("equip_aura_button", [0, 0]),

            # ── Float Aura ──
            "use_float_aura": self.config.get("use_float_aura", False),
            "float_aura_name": self.config.get("float_aura_name", ""),

            # ── Player Logger ──
            "player_logger": self.player_logger_var.get(),

            # ── Quest System ──
            "auto_claim_daily_quests": self.auto_claim_quests_var.get() if hasattr(self, "auto_claim_quests_var") else self.config.get("auto_claim_daily_quests", False),
            "auto_claim_interval": self.auto_claim_interval_var.get() if hasattr(self, "auto_claim_interval_var") else self.config.get("auto_claim_interval", "30"),
            "quest_menu": self.config.get("quest_menu", [0, 0]),
            "quest1_button": self.config.get("quest1_button", [0, 0]),
            "quest2_button": self.config.get("quest2_button", [0, 0]),
            "quest3_button": self.config.get("quest3_button", [0, 0]),
            "claim_quest_button": self.config.get("claim_quest_button", [0, 0]),
            "quest_reroll_button": self.config.get("quest_reroll_button", [0, 0]),

            # ── Pathing / Obby Paths ──
            "collections_button": self.config.get("collections_button", [30, 455]),
            "exit_collections_button": self.config.get("exit_collections_button", [375, 124]),
            "chat_hover_pos": self.config.get("chat_hover_pos", [272, 252]),
            "chat_tab_ocr_pos": self.config.get("chat_tab_ocr_pos", [341, 83, 210, 40]),
            "chat_close_button": self.config.get("chat_close_button", [174, 40]),
            "chat_box_ocr_pos": self.config.get("chat_box_ocr_pos", [14, 161, 587, 244]),
            "enable_obby_path": self.enable_obby_var.get() if hasattr(self, "enable_obby_var") else self.config.get("enable_obby_path", False),
            "obby_claim_interval": self.obby_claim_interval_var.get() if hasattr(self, "obby_claim_interval_var") else self.config.get("obby_claim_interval", "15"),
            "non_vip_movement_path": self.config.get("non_vip_movement_path", False),

            # ── Potion Crafting ──
            "potion_last_file": self.config.get("potion_last_file", ""),
            "enable_potion_crafting": self.enable_potion_crafting_var.get(),
            "enable_potion_switching": self.enable_potion_switching_var.get() if hasattr(self, "enable_potion_switching_var") else self.config.get("enable_potion_switching", False),
            "potion_switch_interval": self.potion_switch_interval_var.get() if hasattr(self, "potion_switch_interval_var") else self.config.get("potion_switch_interval", "60"),
            "potion_file_1": self.config.get("potion_file_1", ""),
            "potion_file_2": self.config.get("potion_file_2", ""),
            "potion_file_3": self.config.get("potion_file_3", ""),

            # ── Fishing Calibration ──
            "fishing_bar_region": self.config.get("fishing_bar_region", [757, 762, 405, 21]),
            "fishing_detect_pixel": self.config.get("fishing_detect_pixel", [1176, 836]),
            "fishing_click_position": self.config.get("fishing_click_position", [862, 843]),
            "fishing_midbar_sample_pos": self.config.get("fishing_midbar_sample_pos", [955, 767]),
            "fishing_close_button_pos": self.config.get("fishing_close_button_pos", [1113, 342]),
            "fishing_flarg_dialogue_box": self.config.get("fishing_flarg_dialogue_box", [1046, 782]),
            "fishing_shop_open_button": self.config.get("fishing_shop_open_button", [616, 938]),
            "fishing_shop_sell_tab": self.config.get("fishing_shop_sell_tab", [1285, 312]),
            "fishing_shop_close_button": self.config.get("fishing_shop_close_button", [1458, 269]),
            "fishing_shop_first_fish": self.config.get("fishing_shop_first_fish", [827, 404]),
            "fishing_shop_sell_all_button": self.config.get("fishing_shop_sell_all_button", [662, 799]),
            "fishing_confirm_sell_all_button": self.config.get("fishing_confirm_sell_all_button", [800, 619]),
            "fishing_failsafe_rejoin": self.config.get("fishing_failsafe_rejoin", False),
            "fishing_enable_selling": self.config.get("fishing_enable_selling", False),
            "fishing_sell_after_x_fish": self.config.get("fishing_sell_after_x_fish", "30"),
            "fishing_sell_how_many_fish": self.config.get("fishing_sell_how_many_fish", "1"),
            "fishing_equip_aura_before_movement": self.config.get("fishing_equip_aura_before_movement", False),
            "fishing_movement_aura_name": self.config.get("fishing_movement_aura_name", ""),
            "fishing_use_merchant_every_x_fish": self.config.get("fishing_use_merchant_every_x_fish", False),
            "fishing_merchant_every_x_fish": self.config.get("fishing_merchant_every_x_fish", "30"),
            "fishing_use_br_sc_every_x_fish": self.config.get("fishing_use_br_sc_every_x_fish", False),
            "fishing_br_sc_every_x_fish": self.config.get("fishing_br_sc_every_x_fish", "30"),
            "fishing_actions_delay_ms": self.config.get("fishing_actions_delay_ms", "100"),
            "fishing_playback_multiplier": self.config.get("fishing_playback_multiplier", 1.0),

            # ── Easter Egg Path  ──
            "collect_easter_egg": self.config.get("collect_easter_egg", False),
            "egg_collect_interval_min": self.config.get("egg_collect_interval_min", "30"),
            "egg_playback_multiplier": self.config.get("egg_playback_multiplier", 1.0),
            "egg_ocr_detect_special": self.config.get("egg_ocr_detect_special", False),
            "egg_ocr_discord_userid": self.config.get("egg_ocr_discord_userid", ""),
            
            # ── Remote Bot ──
            "remote_access_enabled": self.remote_access_var.get() if hasattr(self, "remote_access_var") else self.config.get("remote_access_enabled", False),
            "remote_bot_token": self.remote_bot_token_var.get() if hasattr(self, "remote_bot_token_var") else self.config.get("remote_bot_token", ""),
            "remote_allowed_user_id": self.remote_allowed_user_id_var.get() if hasattr(self, "remote_allowed_user_id_var") else self.config.get("remote_allowed_user_id", ""),
        })

        if not config["auto_buff_glitched"]: config["auto_buff_glitched"] = auto_buff_glitched
        core_save_config(config)
        self.config.clear()
        self.config.update(config)

    def load_config(self):
        try:
            from .config import load_config as core_load_config, save_config as core_save_config
            disk_config = core_load_config()
            default_config = {
                "Jester_Items": {
                    "Heavenly Potion": [ False, 1, False ],
                    "Lucky Potion": [ False, 1, False ],
                    "Merchant Tracker": [ False, 1, False ],
                    "Oblivion Potion": [ False, 1, False ],
                    "Potion of bound": [ False, 1, False ],
                    "Random Potion Sack": [ False, 1, False ],
                    "Rune Of Corruption": [ False, 1, False ],
                    "Rune Of Hell": [ False, 1, False ],
                    "Rune of Dust": [ False, 1, False ],
                    "Rune of Everything": [ False, 1, False ],
                    "Rune of Frost": [ False, 1, False ],
                    "Rune of Galaxy": [ False, 1, False ],
                    "Rune of Nothing": [ False, 1, False ],
                    "Rune of Rainstorm": [ False, 1, False ],
                    "Rune of Wind": [ False, 1, False ],
                    "Speed Potion": [ False, 1, False ],
                    "Stella's Candle": [ False, 1, False ],
                    "Strange Potion": [ False, 1, False ]
                },
                "Mari_Items": {
                    "Gear A": [ False, 1, False ],
                    "Gear B": [ False, 1, False ],
                    "Lucky Penny": [ False, 1, False ],
                    "Lucky Potion": [ False, 1, False ],
                    "Lucky Potion L": [ False, 1, False ],
                    "Lucky Potion XL": [ False, 1, False ],
                    "Mixed Potion": [ False, 1, False ],
                    "Speed Potion": [ False, 1, False ],
                    "Speed Potion L": [ False, 1, False ],
                    "Speed Potion XL": [ False, 1, False ],
                    "Void Coin": [ False, 1, False ]
                },
                "Rin_Items": {
                    "Day and Night Talisman": [ False, 1, False ],
                    "Moonstone Talisman": [ False, 1, False ],
                    "Overtime Talisman": [ False, 1, False ],
                    "Soul Collector's Talisman": [ False, 1, False ],
                    "Soul Master's Talisman": [ False, 1, False ],
                    "Sunstone Talisman": [ False, 1, False ]
                },
                "amount_box": [ 575, 557 ],
                "anti_afk": False,
                "aura_detection_screenshot": False,
                "aura_menu": [ 37, 387 ],
                "aura_search_bar": [ 834, 364 ],
                "aura_record_keybind": "F8",
                "aura_record_minimum": "200000",
                "aura_user_id": "",
                "auto_buff_glitched": {
                    "Fortune Potion I": [ False, 1 ],
                    "Fortune Potion II": [ False, 1 ],
                    "Fortune Potion III": [ False, 1 ],
                    "Godlike Potion": [ False, 1 ],
                    "Haste Potion I": [ False, 1 ],
                    "Haste Potion II": [ False, 1 ],
                    "Haste Potion III": [ False, 1 ],
                    "Heavenly Potion": [ False, 1 ],
                    "Lucky Potion": [ False, 1 ],
                    "Oblivion Potion": [ False, 1 ],
                    "Potion of bound": [ False, 1 ],
                    "Speed Potion": [ False, 1 ],
                    "Stella's Candle": [ False, 1 ],
                    "Strange Potion I": [ False, 1 ],
                    "Strange Potion II": [ False, 1 ],
                    "Transcendent Potion": [ False, 1 ],
                    "Warp Potion": [ False, 1 ],
                    "Xyz Potion": [ False, 1 ]
                },
                "auto_claim_daily_quests": False,
                "auto_claim_interval": "30",
                "auto_merchant_in_limbo": False,
                "auto_obby_interval": "25",
                "auto_pop_cyberspace": False,
                "auto_pop_dreamspace": False,
                "auto_pop_glitched": False,
                "auto_pop_biomes": {},
                "auto_reconnect": False,
                "biome_counts": {
                    "AURORA": 0, "CORRUPTION": 0, "CYBERSPACE": 0, "DREAMSPACE": 0,
                    "GLITCHED": 0, "HEAVEN": 0, "HELL": 0, "NORMAL": 0, "NULL": 0,
                    "RAINY": 0, "SAND STORM": 0, "SNOWY": 0, "STARFALL": 0, "WINDY": 0
                },
                "biome_notifier": {
                    "CORRUPTION": "Message", "CYBERSPACE": "Message", "DREAMSPACE": "Message",
                    "GLITCHED": "Message", "HELL": "Message", "NORMAL": "Message", "NULL": "Message",
                    "RAINY": "Message", "SAND STORM": "Message", "SNOWY": "Message",
                    "STARFALL": "Message", "WINDY": "Message", "HEAVEN": "Message"
                },
                "biome_randomizer": False,
                "br_duration": "36",
                "claim_quest_button": [ 618, 751 ],
                "collections_button": [ 33, 443 ],
                "custom_biome_overrides": {
                    "AURORA": { "color": "0x0047ab", "thumbnail_url": "https://raw.githubusercontent.com/vexthecoder/OysterDetector/main/assets/aurora.png" },
                    "CORRUPTION": { "color": "0x6d32a8", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/CORRUPTION.png" },
                    "CYBERSPACE": { "color": "0x0A1A3D", "thumbnail_url": "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/images/CYBERSPACE.png" },
                    "DREAMSPACE": { "color": "0xea9dda", "thumbnail_url": "http://github.com/xVapure/Noteab-Macro/blob/main/images/Screenshot_2026-01-03_021107.png?raw=true" },
                    "GLITCHED": { "color": "0xbfff00", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/GLITCHED.png" },
                    "HEAVEN": { "color": "0xFFE8A0", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/HEAVEN.png" },
                    "HELL": { "color": "0xff4719", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/HELL.png" },
                    "NORMAL": { "color": "0xffffff", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/NORMAL.png" },
                    "NULL": { "color": "0x838383", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/NULL.png" },
                    "RAINY": { "color": "0x027cbd", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/RAINY.png" },
                    "SAND STORM": { "color": "0x8F7057", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SAND%20STORM.png" },
                    "SNOWY": { "color": "0xDceff9", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/SNOWY.png" },
                    "STARFALL": { "color": "0x011ab7", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/STARFALL.png" },
                    "WINDY": { "color": "0xF2F6FF", "thumbnail_url": "https://maxstellar.github.io/biome_thumb/WINDY.png" }
                },
                "cyberspace_only_warp": False,
                "dont_ask_for_update": False,
                "auto_update_enabled": True,
                "enable_aura_detection": False,
                "enable_aura_record": False,
                "enable_auto_obby": False,
                "enable_buff_glitched": False,
                "enable_glitch_effect": False,
                "enable_ocr_failsafe": False,
                "enable_potion_crafting": False,
                "enable_potion_switching": False,
                "fishing_mode": False,
                "equip_aura_button": [ 625, 615 ],
                "exit_collections_button": [ 385, 164 ],
                "first_aura_slot_pos": [ 819, 420 ],
                "first_item_inventory_slot_pos": [ 845, 460 ],
                "first_item_merchant_slot_pos": [ 954, 696 ],
                "first_item_slot_ocr_pos": [ 786, 408, 113, 112 ],
                "fishing_bar_region": [ 757, 762, 405, 21 ],
                "fishing_detect_pixel": [ 1176, 836 ],
                "fishing_click_position": [ 862, 843 ],
                "fishing_midbar_sample_pos": [ 955, 767 ],
                "fishing_close_button_pos": [ 1113, 342 ],
                "fishing_flarg_dialogue_box": [ 1046, 782 ],
                "fishing_shop_open_button": [ 616, 938 ],
                "fishing_shop_sell_tab": [ 1285, 312 ],
                "fishing_shop_close_button": [ 1458, 269 ],
                "fishing_shop_first_fish": [ 827, 404 ],
                "fishing_shop_sell_all_button": [ 662, 799 ],
                "fishing_confirm_sell_all_button": [ 800, 619 ],
                "fishing_failsafe_rejoin": False,
                "fishing_enable_selling": False,
                "fishing_sell_after_x_fish": "30",
                "fishing_sell_how_many_fish": "1",
                "fishing_equip_aura_before_movement": False,
                "fishing_movement_aura_name": "",
                "fishing_use_merchant_every_x_fish": False,
                "fishing_merchant_every_x_fish": "30",
                "fishing_use_br_sc_every_x_fish": False,
                "fishing_br_sc_every_x_fish": "30",
                "fishing_actions_delay_ms": "100",
                "fishing_playback_multiplier": 1.0,
                "collect_easter_egg": False,
                "egg_collect_interval_min": "30",
                "egg_playback_multiplier": 1.0,
                "egg_ocr_detect_special": False,
                "egg_ocr_discord_userid": "",
                "float_aura_name": "",
                "glitched_buff_enable_button": [ 932, 630 ],
                "glitched_menu_button": [ 41, 651 ],
                "glitched_settings_button": [ 958, 561 ],
                "inventory_click_delay": "650",
                "inventory_close_button": [ 1412, 281 ],
                "inventory_menu": [ 34, 493 ],
                "item_name_ocr_pos": [ 1095, 348, 389, 46 ],
                "items_tab": [ 1267, 313 ],
                "jester_user_id": "",
                "macro_last_start": "",
                "mari_user_id": "",
                "merchant_close_button_pos": [ 1811, 325 ],
                "merchant_counts": { "Jester": 0, "Mari": 0, "Rin": 0 },
                "merchant_dialogue_box": [ 1114, 796 ],
                "merchant_extra_slot": "0",
                "merchant_name_ocr_pos": [ 740, 651, 141, 54 ],
                "merchant_open_button": [ 629, 895 ],
                "merchant_teleporter": False,
                "mt_duration": "1",
                "periodical_aura_interval": "25",
                "periodical_aura_screenshot": False,
                "periodical_inventory_interval": "25",
                "periodical_inventory_screenshot": False,
                "ping_jester": False,
                "ping_mari": False,
                "ping_minimum": "200000000",
                "ping_rin": False,
                "potion_auto_button": [ 403, 781 ],
                "potion_auto_add_button": [ 403, 781 ],
                "potion_file_1": "",
                "potion_file_2": "",
                "potion_file_3": "",
                "potion_items_tab": [ 1548, 234 ],
                "potion_recipe_button": [ 194, 776 ],
                "potion_search_bar": [ 1515, 271 ],
                "potion_switch_interval": "180",
                "private_server_link": "",
                "roblox_username": "",
                "purchase_amount_button": [ 1101, 594 ],
                "purchase_button": [ 1172, 637 ],
                "quest1_button": [ 1042, 511 ],
                "quest2_button": [ 1062, 596 ],
                "quest3_button": [ 1138, 659 ],
                "quest_menu": [ 35, 607 ],
                "quest_reroll_button": [ 615, 534 ],
                "rare_biome_record_keybind": "F8",
                "rare_biome_screenshot": True,
                "reconnect_start_button": [ 271, 942 ],
                "record_rare_biome": False,
                "remote_access_enabled": False,
                "remote_allowed_user_id": "",
                "remote_bot_token": "",
                "reset_on_rare": False,
                "rin_user_id": "",
                "sc_duration": "21",
                "search_bar": [ 854, 350 ],
                "selected_potion_file": "",
                "selected_theme": "solar",
                "session_time": "",
                "session_window_start": "",
                "strange_controller": False,
                "teleport_back_to_limbo": False,
                "use_button": [ 678, 563 ],
                "use_float_aura": False,
                "enable_idle_mode": False,
                "auto_roblox_fullscreen": False,
                "auto_chat_close": False,
                "enable_obby_path": False,
                "obby_claim_interval": "15",
                "collect_easter_egg": False,
                "egg_collect_interval_sec": "60",
                "egg_collect_interval_min": "30",
                "egg_playback_multiplier": 1.0,
                "egg_ocr_detect_special": False,
                "merchant_close_button": [ 1086, 342 ],
                "player_logger": True,
                "webhook_url": [],
                "non_vip_movement_path": False,
            }

            # Override coordinate defaults with the current calibrated values from config.json.
            # This makes fresh/missing configs inherit your latest calibration baseline.
            calibration_defaults = {
                "collections_button": [41, 457],
                "exit_collections_button": [380, 128],
                "quest_menu": [30, 614],
                "quest1_button": [955, 540],
                "quest2_button": [894, 612],
                "quest3_button": [871, 668],
                "claim_quest_button": [616, 770],
                "quest_reroll_button": [622, 566],
                "merchant_open_button": [595, 942],
                "merchant_dialogue_box": [975, 810],
                "purchase_amount_button": [1055, 609],
                "purchase_button": [1180, 655],
                "first_item_merchant_slot_pos": [907, 716],
                "merchant_close_button": [1810, 347],
                "merchant_name_ocr_pos": [731, 682, 278, 52],
                "item_name_ocr_pos": [1106, 372, 708, 35],
                "glitched_menu_button": [37, 674],
                "glitched_settings_button": [964, 590],
                "glitched_buff_enable_button": [929, 653],
                "aura_menu": [37, 405],
                "aura_search_bar": [834, 364],
                "first_aura_slot_pos": [819, 434],
                "equip_aura_button": [602, 639],
                "inventory_menu": [38, 515],
                "items_tab": [1231, 338],
                "search_bar": [845, 368],
                "first_item_inventory_slot_pos": [858, 470],
                "amount_box": [560, 578],
                "use_button": [678, 581],
                "inventory_close_button": [1412, 299],
                "reconnect_start_button": [260, 1002],
                "first_item_slot_ocr_pos": [802, 431, 93, 92],
                "potion_items_tab": [1521, 222],
                "potion_search_bar": [1533, 267],
                "potion_first_potion_slot_pos": [1527, 354],
                "potion_recipe_button": [216, 820],
                "potion_auto_button": [424, 821],
                "potion_auto_add_button": [424, 821],
                "fishing_bar_region": [750, 753, 416, 38],
                "fishing_detect_pixel": [1175, 836],
                "fishing_click_position": [846, 835],
                "fishing_midbar_sample_pos": [942, 765],
                "fishing_close_button_pos": [1111, 342],
                "fishing_flarg_dialogue_box": [1046, 782],
                "fishing_shop_open_button": [616, 938],
                "fishing_shop_sell_tab": [1285, 312],
                "fishing_shop_close_button": [1458, 269],
                "fishing_shop_first_fish": [827, 404],
                "fishing_shop_sell_all_button": [662, 799],
                "fishing_confirm_sell_all_button": [801, 626],
            }
            default_config.update(calibration_defaults)
             
            # If the disk_config is completely missing or completely empty (e.g. `{}`), write the fresh defaults to disk right now
            needs_save = False
            if not disk_config:
                needs_save = True

            # Merge disk_config into default_config (1 level deep overwrite is fine for our usage here, but we will preserve nested dicts like biome_counts)
            for k, v in disk_config.items():
                if isinstance(v, dict) and k in default_config and isinstance(default_config[k], dict):
                    default_config[k].update(v)
                else:
                    default_config[k] = v
            
            # Optional backwards-compatibility hook for very old biome counts or webhook logic
            raw_webhook = default_config.get("webhook_url", [])
            if isinstance(raw_webhook, str):
                default_config["webhook_url"] = [raw_webhook] if raw_webhook else []

            deprecated_keys = ()
            for key in deprecated_keys:
                if key in default_config:
                    default_config.pop(key, None)
                    needs_save = True

            # Legacy merchant key compatibility
            if "merchant_close_button" not in disk_config:
                legacy_close = default_config.get("merchant_close_button_pos")
                if isinstance(legacy_close, list) and len(legacy_close) >= 2:
                    try:
                        default_config["merchant_close_button"] = [int(legacy_close[0]), int(legacy_close[1])]
                    except Exception:
                        pass

            if "potion_auto_add_button" not in disk_config:
                legacy_auto_add = default_config.get("potion_auto_button")
                if isinstance(legacy_auto_add, list) and len(legacy_auto_add) >= 2:
                    try:
                        default_config["potion_auto_add_button"] = [int(legacy_auto_add[0]), int(legacy_auto_add[1])]
                        needs_save = True
                    except Exception:
                        pass

            # Update self.config IN-PLACE for ConfigVars to keep their ref
            if not hasattr(self, "config"): self.config = {}
            self.config.clear()
            self.config.update(default_config)
            
            if needs_save: core_save_config(self.config)
            return self.config
            
        except Exception as e:
            try:
                self.error_logging(e, "Error at loading config")
            except Exception:
                pass
            return {"biome_counts": {}, "session_time": "0:00:00"}

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
            self.config.clear()
            self.config.update(config)

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
            if hasattr(self, "reset_on_rare_var"): self.reset_on_rare_var.set(config.get("reset_on_rare", False))
            if hasattr(self, "teleport_back_to_limbo_var"): self.teleport_back_to_limbo_var.set(config.get("teleport_back_to_limbo", False))
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
            if hasattr(self, "rare_biome_screenshot_var"): self.rare_biome_screenshot_var.set(config.get("rare_biome_screenshot", False))
            if hasattr(self, "auto_roblox_fullscreen_var"): self.auto_roblox_fullscreen_var.set(config.get("auto_roblox_fullscreen", False))
            if hasattr(self, "auto_update_enabled_var"): self.auto_update_enabled_var.set(config.get("auto_update_enabled", True))
            if hasattr(self, "enable_glitch_effect_var"): self.enable_glitch_effect_var.set(config.get("enable_glitch_effect", False))
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
            if hasattr(self, "aura_record_minimum_var"): self.aura_record_minimum_var.set(config.get("aura_record_minimum", "500000"))
            if hasattr(self, "periodical_aura_var"): self.periodical_aura_var.set(config.get("periodical_aura_screenshot", False))
            if hasattr(self, "aura_detection_screenshot"): self.aura_screenshot_var.set(config.get("aura_detection_screenshot", False))
            if hasattr(self, "periodical_aura_interval_var"): self.periodical_aura_interval_var.set(str(config.get("periodical_aura_interval", "5")))
            if hasattr(self, "periodical_inventory_var"): self.periodical_inventory_var.set(config.get("periodical_inventory_screenshot", False))
            if hasattr(self, "periodical_inventory_interval_var"): self.periodical_inventory_interval_var.set(str(config.get("periodical_inventory_interval", "5")))
            if hasattr(self, "auto_claim_quests_var"): self.auto_claim_quests_var.set(config.get("auto_claim_daily_quests", False))
            if hasattr(self, "auto_claim_interval_var"): self.auto_claim_interval_var.set(str(config.get("auto_claim_interval", "30")))
            if hasattr(self, "macro_idle_mode_var"): self.macro_idle_mode_var.set(config.get("enable_idle_mode", False))
            if hasattr(self, "enable_obby_var"): self.enable_obby_var.set(config.get("enable_obby_path", False))
            if hasattr(self, "obby_claim_interval_var"): self.obby_claim_interval_var.set(str(config.get("obby_claim_interval", "15")))
            if hasattr(self, "auto_pop_dreamspace_var"): self.auto_pop_dreamspace_var.set(config.get("auto_pop_dreamspace", False))
            if hasattr(self, "auto_pop_cyberspace_var"): self.auto_pop_cyberspace_var.set(config.get("auto_pop_cyberspace", False))
            if hasattr(self, "cyberspace_only_warp_var"): self.cyberspace_only_warp_var.set(config.get("cyberspace_only_warp", False))
            if hasattr(self, "enable_buff_glitched_var"): self.enable_buff_glitched_var.set(config.get("enable_buff_glitched", False))
            if hasattr(self, "enable_potion_crafting_var"): self.enable_potion_crafting_var.set(config.get("enable_potion_crafting", False))
            if hasattr(self, "enable_ocr_failsafe_var"): self.enable_ocr_failsafe_var.set(config.get("enable_ocr_failsafe", False))
            if hasattr(self, "fishing_mode_var"): self.fishing_mode_var.set(config.get("fishing_mode", False))
            # merchant
            self.merchant_extra_slot_var.set(config.get("merchant_extra_slot", "0"))
            self.ping_mari_var.set(config.get("ping_mari", False))
            self.mari_user_id_var.set(config.get("mari_user_id", ""))
            self.ping_jester_var.set(config.get("ping_jester", False))
            self.jester_user_id_var.set(config.get("jester_user_id", ""))
            if hasattr(self, "ping_rin_var"): self.ping_rin_var.set(config.get("ping_rin", False))
            if hasattr(self, "rin_user_id_var"): self.rin_user_id_var.set(config.get("rin_user_id", ""))
            try:
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