from .base_support import *
from .config import normalize_auto_pop_biomes

class LifecycleMixin:
    def __init__(self):
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_ALL, '')

        self.logs_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'Roblox', 'logs')
        self.config = self.load_config()
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
        
        self._active_webhook_channel_lookup_urls = []
        self._active_webhook_channel_mentions = []
        try:
            if hasattr(self, "refresh_active_webhook_channels"):
                self.refresh_active_webhook_channels(force=True)
        except Exception as e:
            try:
                print(f"Failed to resolve active webhook channels on startup: {e}")
            except Exception:
                pass
            
        self.auras_data = self.load_auras_json()
        self.biome_data = self.load_biome_data()
        self.config["auto_pop_biomes"] = normalize_auto_pop_biomes(self.config, list(self.biome_data.keys()))

        self.current_biome = None
        self.last_sent = {biome: datetime.min for biome in self.biome_data}

        self.biome_counts = self.config.get("biome_counts", {})
        for biome in self.biome_data.keys():
            if biome not in self.biome_counts:
                self.biome_counts[biome] = 0

        self.merchant_counts = self.config.get("merchant_counts", {})
        for merchant in ("Mari", "Jester", "Rin"):
            if merchant not in self.merchant_counts:
                self.merchant_counts[merchant] = 0
        self.config["merchant_counts"] = self.merchant_counts

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
        self.just_reconnected = False
        self.reconnect_confirm_deadline = None

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
        self.last_crack_time = datetime.min
        self.on_auto_merchant_state = False
        self._br_sc_running = False
        self._portable_crack_running = False
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
        self.easyocr_active = True
        self._easyocr_reader = None
        self._easyocr_lock = threading.Lock()
        # Reconnect state
        self.reconnecting_state = False
        self._pending_fishing_failsafe_rejoin = False
        self.timer_paused_by_disconnect = False
        self.register_shutdown_handler()
        self._snowman_running = False
        self.initialize_paths_and_files()
        self.last_snowman_claim = datetime.min
        self._obby_running = False
        self.last_obby_claim = datetime.min
        self._egg_collecting = False
        self._fishing_busy = False
        self.last_egg_collect_time = datetime.min
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

        # --- ConfigVar (replaces Tkinter BooleanVar / StringVar) ----
        # These let detection threads call  self.xxx_var.get()  without a Tkinter root window. 
        # The modern TSX frontend uses pywebview to set these values via the API.
        
        self.mt_var               = ConfigVar(self.config, "merchant_teleporter", False)
        self.mt_duration_var      = ConfigVar(self.config, "mt_duration", "1")
        self.br_var               = ConfigVar(self.config, "biome_randomizer", False)
        self.br_duration_var      = ConfigVar(self.config, "br_duration", "30")
        self.sc_var               = ConfigVar(self.config, "strange_controller", False)
        self.sc_duration_var      = ConfigVar(self.config, "sc_duration", "15")
        self.anti_afk_var         = ConfigVar(self.config, "anti_afk", True)
        self.auto_reconnect_var   = ConfigVar(self.config, "auto_reconnect", False)
        self.macro_idle_mode_var  = ConfigVar(self.config, "enable_idle_mode", False)
        self.auto_roblox_fullscreen_var = ConfigVar(self.config, "auto_roblox_fullscreen", False)
        self.auto_chat_close_var  = ConfigVar(self.config, "auto_chat_close", False)
        self.auto_pop_glitched_var = ConfigVar(self.config, "auto_pop_glitched", False)
        self.enable_aura_detection_var = ConfigVar(self.config, "enable_aura_detection", False)
        self.enable_aura_record_var   = ConfigVar(self.config, "enable_aura_record", False)
        self.aura_record_keybind_var  = ConfigVar(self.config, "aura_record_keybind", "shift + F8")
        self.aura_record_minimum_var  = ConfigVar(self.config, "aura_record_minimum", "500000")
        self.aura_screenshot_var      = ConfigVar(self.config, "aura_detection_screenshot", False)
        self.periodical_aura_var      = ConfigVar(self.config, "periodical_aura_screenshot", False)
        self.periodical_aura_interval_var = ConfigVar(self.config, "periodical_aura_interval", "5")
        self.periodical_inventory_var     = ConfigVar(self.config, "periodical_inventory_screenshot", False)
        self.periodical_inventory_interval_var = ConfigVar(self.config, "periodical_inventory_interval", "5")
        self.auto_merchant_in_limbo_var = ConfigVar(self.config, "auto_merchant_in_limbo", False)
        self.auto_claim_quests_var     = ConfigVar(self.config, "auto_claim_daily_quests", False)
        self.auto_claim_interval_var   = ConfigVar(self.config, "auto_claim_interval", "30")
        self.enable_snowman_var         = ConfigVar(self.config, "enable_snowman_path", False)
        self.snowman_claim_interval_var = ConfigVar(self.config, "snowman_claim_interval", "15")
        self.enable_obby_var            = ConfigVar(self.config, "enable_obby_path", False)
        self.obby_claim_interval_var    = ConfigVar(self.config, "obby_claim_interval", "15")
        self.enable_potion_crafting_var = ConfigVar(self.config, "enable_potion_crafting", False)
        self.reset_on_rare_var     = ConfigVar(self.config, "reset_on_rare", False)
        self.teleport_back_to_limbo_var = ConfigVar(self.config, "teleport_back_to_limbo", False)
        self.enable_buff_glitched_var   = ConfigVar(self.config, "enable_buff_glitched", False)
        self.record_rarest_biome_var    = ConfigVar(self.config, "record_rare_biome", False)
        self.rarest_biome_keybind_var   = ConfigVar(self.config, "rare_biome_record_keybind", "shift + F8")
        self.player_logger_var          = ConfigVar(self.config, "player_logger", True)
        self.click_delay_var            = ConfigVar(self.config, "inventory_click_delay", "0")
        self.enable_ocr_failsafe_var    = ConfigVar(self.config, "enable_ocr_failsafe", False)
        self.fishing_mode_var           = ConfigVar(self.config, "fishing_mode", False)
        self.ping_minimum_var           = ConfigVar(self.config, "ping_minimum", "100000")
        self.aura_user_id_var           = ConfigVar(self.config, "aura_user_id", "")
        self.force_ping_auras_var       = ConfigVar(self.config, "force_ping_auras", "")
        self.force_record_auras_var     = ConfigVar(self.config, "force_record_auras", "")
        self.ping_mari_var              = ConfigVar(self.config, "ping_mari", False)
        self.mari_user_id_var           = ConfigVar(self.config, "mari_user_id", "")
        self.ping_jester_var            = ConfigVar(self.config, "ping_jester", False)
        self.jester_user_id_var         = ConfigVar(self.config, "jester_user_id", "")
        self.ping_rin_var               = ConfigVar(self.config, "ping_rin", False)
        self.rin_user_id_var            = ConfigVar(self.config, "rin_user_id", "")
        self.merchant_extra_slot_var    = ConfigVar(self.config, "merchant_extra_slot", "0")
        self.remote_access_var          = ConfigVar(self.config, "remote_access_enabled", False)
        self.remote_bot_token_var       = ConfigVar(self.config, "remote_bot_token", "")
        self.remote_allowed_user_id_var = ConfigVar(self.config, "remote_allowed_user_id", "")

        # Eden detection:
        self.eden_detection_var         = ConfigVar(self.config, "eden_detection", False)
        self.eden_check_interval_var    = ConfigVar(self.config, "eden_check_interval", "5")
        self.ping_eden_var              = ConfigVar(self.config, "ping_eden", False)
        self.eden_user_id_var           = ConfigVar(self.config, "eden_user_id", "")
        self._eden_checking_pending     = False
        self._eden_checking             = False
        
        if not hasattr(self, "remote_command_queue"):
            self.remote_command_queue = queue.Queue()
        if not hasattr(self, "_remote_check_merchant_results"):
            self._remote_check_merchant_results = {}
        if not hasattr(self, "_help_command_list"):
            self._help_command_list = [
                ("screenshot", "", "Take current ingame screenshot and send to webhooks."),
                ("reroll_quest", "{quest name}", "Reroll a daily quest."),
                ("check_merchant", "", "Use merchant teleporter and check for merchant."),
                ("use", "{item_name} {amount}", "Use item remotely."),
                ("rejoin", "", "Close Roblox to force rejoin (requires Auto Reconnect enabled)."),
            ]
        if not hasattr(self, "remote_worker_running"):
            self.remote_worker_running = False
        if not hasattr(self, "remote_bot_thread"):
            self.remote_bot_thread = None
        if not hasattr(self, "remote_bot_obj"):
            self.remote_bot_obj = None
        if not hasattr(self, "_remote_running"):
            self._remote_running = False

        self.auto_pop_cyberspace_var    = ConfigVar(self.config, "auto_pop_cyberspace", False)
        self.auto_pop_dreamspace_var    = ConfigVar(self.config, "auto_pop_dreamspace", False)
        self.cyberspace_only_warp_var   = ConfigVar(self.config, "cyberspace_only_warp", False)
        self.azerty_mode_var            = ConfigVar(self.config, "azerty_mode", False)

        # aura detection:
        self.last_aura_found = None
        self.last_aura_screenshot_time = datetime.min
        self.last_inventory_screenshot_time = datetime.min

    def is_fishing_mode_enabled(self):
        try:
            return bool(self.config.get("fishing_mode", False))
        except Exception:
            return False


    def set_title_threadsafe(self, title_text):
        try:
            root = getattr(self, "root", None)
            if root is None:
                print(f"[title] {title_text}")
                return
            if threading.current_thread() is threading.main_thread():
                root.title(title_text)
            else:
                root.after(0, lambda: root.title(title_text))
        except Exception:
            pass

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