from .base_support import *

class RemoteMixin:
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
            try:
                messagebox.showwarning("Remote Access", "Please enter a bot token first.")
            except Exception:
                print("[Remote] No bot token provided.")
            return
        self.remote_worker_running = True
        self.remote_bot_thread = threading.Thread(target=self._remote_bot_thread_func, daemon=True)
        self.remote_bot_thread.start()
        print("[Remote] Bot thread started.")
        self.save_config()


    def stop_remote_bot(self):
        try:
            self.remote_worker_running = False
            if getattr(self, "remote_bot_obj", None):
                try:
                    import asyncio
                    bot_loop = getattr(self.remote_bot_obj, "loop", None)
                    if bot_loop and bot_loop.is_running():
                        asyncio.run_coroutine_threadsafe(self.remote_bot_obj.close(), bot_loop)
                    else:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.remote_bot_obj.close())
                        loop.close()
                except Exception:
                    pass
            self.remote_bot_obj = None
            try:
                self.remote_status_label.config(text="Bot: stopped")
            except Exception:
                pass
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
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            intents = discord.Intents.default()
            bot = discord.Bot(intents=intents)
            self.remote_bot_obj = bot

            @bot.event
            async def on_ready():
                try:
                    await bot.sync_commands()
                    print(f"[Remote] Bot online as {bot.user} — slash commands synced.")
                except Exception as e:
                    print(f"[Remote] Failed to sync commands: {e}")

            def _check_auth(ctx):
                user = getattr(ctx, "user", None) or getattr(ctx, "author", None)
                user_id = getattr(user, "id", None)
                if allowed_id_int and user_id != allowed_id_int:
                    return False
                return True

            async def _safe_respond(ctx, content, ephemeral=False):
                try:
                    await ctx.respond(content, ephemeral=ephemeral)
                except Exception:
                    try:
                        await ctx.send(content)
                    except Exception:
                        pass

            @bot.slash_command(name="rejoin", description="Close Roblox to force rejoin (requires Auto Reconnect enabled)")
            async def rejoin(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    if not self.config.get("auto_reconnect"):
                        await _safe_respond(ctx, "\u274c Auto Reconnect is disabled. Enable it in settings to use /rejoin.", ephemeral=True)
                        return
                    self.remote_command_queue.put(("__rejoin__", ""))
                    await _safe_respond(ctx, "\U0001f504 Closing Roblox and rejoining the server...", ephemeral=False)
                except Exception:
                    try:
                        await _safe_respond(ctx, "\u274c Something went wrong.", ephemeral=True)
                    except Exception:
                        pass

            @bot.slash_command(name="help", description="Helping u out with remote access features")
            async def help_cmd(ctx: discord.ApplicationContext, page: int = 1):
                try:
                    cmds = getattr(self, "_help_command_list", [])
                    per = 5
                    total = (len(cmds) + per - 1) // per if cmds else 1
                    p = max(1, min(page, total))
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
                    await _safe_respond(ctx, content, ephemeral=False)
                except Exception:
                    pass

            @bot.slash_command(name="use", description="Use an item remotely")
            async def use(ctx: discord.ApplicationContext, item: str, amount: int = 1):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    self.remote_command_queue.put((str(item), int(amount)))
                    await _safe_respond(ctx, f"\U0001f4e6 Using **{item}** x{amount}...", ephemeral=False)
                except Exception:
                    try:
                        await _safe_respond(ctx, "\u274c Something went wrong.", ephemeral=True)
                    except Exception:
                        pass

            @bot.slash_command(name="check_merchant", description="Use merchant teleporter and check for merchant")
            async def check_merchant(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    uid = str(time.time()).replace(".", "")
                    self._remote_check_merchant_results[uid] = None
                    await _safe_respond(ctx, "\U0001f50d Teleporting to merchant and checking...", ephemeral=False)
                    self.remote_command_queue.put(("__check_merchant__", uid))
                except Exception:
                    try:
                        await _safe_respond(ctx, "\u274c Something went wrong.", ephemeral=True)
                    except Exception:
                        pass

            @bot.slash_command(name="screenshot", description="Take current ingame screenshot and send to webhooks")
            async def screenshot(ctx: discord.ApplicationContext, target: str = None):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    t = (target or "").strip().lower()
                    if not t or t not in ("full", "inventory", "aura"):
                        t = "full"
                    self.remote_command_queue.put(("__screenshot__", t))
                    labels = {"full": "full screen", "inventory": "inventory", "aura": "aura"}
                    await _safe_respond(ctx, f"\U0001f4f8 Taking a {labels.get(t, t)} screenshot and sending to webhooks...", ephemeral=False)
                except Exception:
                    try:
                        await _safe_respond(ctx, "\u274c Something went wrong.", ephemeral=True)
                    except Exception:
                        pass

            @bot.slash_command(name="reroll_quest", description="Reroll a selected daily quest")
            @discord.option(
                "quest",
                str,
                description="Quest to reroll",
                choices=[
                    discord.OptionChoice(name="Quest 1", value="1"),
                    discord.OptionChoice(name="Quest 2", value="2"),
                    discord.OptionChoice(name="Quest 3", value="3"),
                ],
            )
            async def reroll_quest(ctx: discord.ApplicationContext, quest: str):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    quest_value = str(quest)
                    quest_name = {"1": "Quest 1", "2": "Quest 2", "3": "Quest 3"}.get(quest_value, f"Quest {quest_value}")
                    self.remote_command_queue.put(("__reroll__", quest_value))
                    await _safe_respond(ctx, f"\U0001f3b2 Rerolling {quest_name}...", ephemeral=False)
                except Exception:
                    try:
                        await _safe_respond(ctx, "\u274c Something went wrong.", ephemeral=True)
                    except Exception:
                        pass

            try:
                self.set_title_threadsafe(f"Coteab Macro {current_ver} (Remote bot starting)")
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
            except Exception as e:
                print(f"[Remote] bot.run() failed: {e}")
                try:
                    self.error_logging(e, "Remote bot.run() failed")
                except Exception:
                    pass
        except Exception as e:
            print(f"[Remote] _remote_bot_thread_func crashed: {e}")
            try:
                self.error_logging(e, "_remote_bot_thread_func crashed")
            except Exception:
                pass
        finally:
            try:
                self.remote_status_label.config(text="Bot: stopped")
            except Exception:
                pass
            self.remote_bot_obj = None
            self.remote_worker_running = False

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
                        self._action_scheduler.enqueue_action(remote_rejoin_action, name="remote:rejoin", priority=1)
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
                            self._action_scheduler.enqueue_action(_screenshot_action, name="remote:screenshot", priority=0)
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
                            self._action_scheduler.enqueue_action(_inv_action, name="remote:screenshot:inventory", priority=3)
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
                            self._action_scheduler.enqueue_action(_aura_action, name="remote:screenshot:aura", priority=2)
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
                    self._action_scheduler.enqueue_action(_remote_action, name=f"remote:{item_name}", priority=1)
                except Exception:
                    try:
                        time.sleep(0.35)
                        self.remote_command_queue.put((item_name, amount))
                    except Exception:
                        pass

            except Exception:
                time.sleep(0.2)
                continue

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
        first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
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
                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = os.path.join(screenshot_dir, f"remote_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_screen_screenshot_webhook(filename)
            except Exception as e:
                self.error_logging(e, "Error taking/sending remote screenshot")
        except Exception:
            pass