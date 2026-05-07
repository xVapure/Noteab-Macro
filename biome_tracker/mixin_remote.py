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
                    success_msg = f"[Remote] Bot online as {bot.user} — slash commands synced. Pycord module loaded :aga:"
                    print(success_msg)
                    try:
                        self.append_log(success_msg)
                    except Exception:
                        pass
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

            @bot.slash_command(name="start", description="Start the macro (biome detection)")
            async def start_macro(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    if getattr(self, "on_remote_start", None):
                        self.on_remote_start()
                        embed = discord.Embed(title="Macro Started", description="Biome detection has been started.", color=0x00FF00)
                        await ctx.respond(embed=embed)
                    else:
                        await _safe_respond(ctx, "Start callback not configured.", ephemeral=True)
                except Exception:
                    pass

            @bot.slash_command(name="stop", description="Stop the macro")
            async def stop_macro(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    if getattr(self, "on_remote_stop", None):
                        self.on_remote_stop()
                        embed = discord.Embed(title="Macro Stopped", description="Biome detection has been stopped.", color=0xFF0000)
                        await ctx.respond(embed=embed)
                    else:
                        await _safe_respond(ctx, "Stop callback not configured.", ephemeral=True)
                except Exception:
                    pass

            @bot.slash_command(name="status", description="Show current macro status")
            async def status_macro(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    
                    is_running = getattr(self, "detection_running", False)
                    status_text = "🟢 Running" if is_running else "🔴 Stopped"
                    current_biome = getattr(self, "current_biome", "Unknown") or "None"
                    
                    session_time = "0:00:00"
                    if is_running and getattr(self, "start_time", None):
                        import datetime as dt
                        now = dt.datetime.now()
                        elapsed = int((now - self.start_time).total_seconds()) + getattr(self, "saved_session", 0)
                        session_time = str(dt.timedelta(seconds=elapsed))
                    else:
                        import datetime as dt
                        session_time = str(dt.timedelta(seconds=getattr(self, "saved_session", 0))) if hasattr(self, "saved_session") else "0:00:00"

                    fishing_mode = "✅ On" if self.config.get("fishing_mode", False) else "❌ Off"
                    
                    embed = discord.Embed(title="== Macro Status ==", color=0x00AAFF)
                    embed.add_field(name="Status", value=status_text, inline=True)
                    embed.add_field(name="Current Biome", value=current_biome, inline=True)
                    embed.add_field(name="Session Time", value=session_time, inline=True)
                    embed.add_field(name="Fishing Mode", value=fishing_mode, inline=True)

                    biome_counts = getattr(self, "biome_counts", {})
                    valid_counts = {k: v for k, v in biome_counts.items() if v > 0}
                    if valid_counts:
                        items = sorted(valid_counts.items(), key=lambda x: x[1], reverse=True)
                        lines = []
                        for i in range(0, len(items), 2):
                            left_k, left_v = items[i]
                            left_str = f"{left_k.title():<11}: {left_v:<5}"
                            if i + 1 < len(items):
                                right_k, right_v = items[i+1]
                                right_str = f" |  {right_k.title():<11}: {right_v}"
                            else:
                                right_str = ""
                            lines.append(f"{left_str}{right_str}")
                        counts_str = "```yaml\n" + "\n".join(lines) + "\n```"
                        embed.add_field(name="Biome Counts", value=counts_str, inline=False)
                    else:
                        embed.add_field(name="Biome Counts", value="```\nNone yet.\n```", inline=False)
                    
                    try:
                        from biome_tracker.base_support import current_version
                        embed.set_footer(text=f"Coteab Macro {current_version}")
                    except Exception:
                        pass
                        
                    await ctx.respond(embed=embed)
                except Exception:
                    pass

            @bot.slash_command(name="close_roblox_and_stop_macro", description="Kill Roblox process AND stop the macro")
            async def close_roblox_and_stop_macro(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    embed = discord.Embed(title="🛑 Terminating Roblox", description="Stopping the macro and forcefully killing Roblox processes...", color=0xFF0000)
                    await ctx.respond(embed=embed)
                    
                    self.remote_command_queue.put(("__close_roblox__", ""))
                    if getattr(self, "on_remote_stop", None):
                        self.on_remote_stop()
                except Exception:
                    pass

            @bot.slash_command(name="equip_aura", description="Search for and equip an aura by name")
            async def equip_aura(ctx: discord.ApplicationContext, name: str):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                        
                    is_blocked = getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked())
                    if is_blocked:
                        embed = discord.Embed(title="Action Blocked", description=f"Cannot equip **{name}** while the macro is actively running an un-interruptible mode (e.g., Fishing Mode). Please wait for the macro to finish those action.", color=0xFF0000)
                        await ctx.respond(embed=embed, ephemeral=True)
                        return
                        
                    self.remote_command_queue.put(("__equip_aura__", str(name)))
                    embed = discord.Embed(title="Equipping Aura", description=f"Attempting to search and equip **{name}**...", color=0xFFD700)
                    await ctx.respond(embed=embed)
                except Exception:
                    pass

            @bot.slash_command(name="rejoin", description="Close Roblox to force rejoin (requires Auto Reconnect enabled)")
            async def rejoin(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    if not self.config.get("auto_reconnect"):
                        await _safe_respond(ctx, "Auto Reconnect is disabled. Enable it in settings to use /rejoin.", ephemeral=True)
                        return
                    self.remote_command_queue.put(("__rejoin__", ""))
                    embed = discord.Embed(title="Rejoining", description="Closing Roblox and forcing a server rejoin...", color=0x00FF00)
                    await ctx.respond(embed=embed)
                except Exception:
                    pass

            @bot.slash_command(name="help", description="Helping u out with remote access features")
            async def help_cmd(ctx: discord.ApplicationContext, page: int = 1):
                try:
                    cmds = getattr(self, "_help_command_list", [])
                    per = 6
                    total = (len(cmds) + per - 1) // per if cmds else 1
                    p = max(1, min(page, total))
                    start = (p - 1) * per
                    end = start + per
                    page_items = cmds[start:end]
                    
                    embed = discord.Embed(title="Remote Access Commands", color=0x5865F2)
                    for cmd in page_items:
                        name = cmd[0] if len(cmd) > 0 else ""
                        usage = cmd[1] if len(cmd) > 1 else ""
                        desc = cmd[2] if len(cmd) > 2 else ""
                        embed.add_field(name=f"/{name} {usage}", value=desc, inline=False)
                        
                    embed.set_footer(text=f"Page {p}/{total}")
                    await ctx.respond(embed=embed)
                except Exception:
                    pass

            @bot.slash_command(name="use", description="Use an item remotely")
            async def use(ctx: discord.ApplicationContext, item: str, amount: int = 1):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                        
                    is_blocked = getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked())
                    if is_blocked:
                        embed = discord.Embed(title="Action Blocked", description=f"Cannot use items while the macro is actively running an un-interruptible mode (e.g., Fishing Mode). Please wait for the macro to finish those action.", color=0xFF0000)
                        await ctx.respond(embed=embed, ephemeral=True)
                        return
                        
                    self.remote_command_queue.put((str(item), int(amount)))
                    embed = discord.Embed(title="Using Item", description=f"Using **{item}** x{amount}...", color=0x00FF00)
                    await ctx.respond(embed=embed)
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
            @discord.option(
                name="target",
                type=str,
                description="Type of screenshot to take",
                choices=[
                    discord.OptionChoice(name="Fullscreen", value="full"),
                    discord.OptionChoice(name="Inventory", value="inventory"),
                    discord.OptionChoice(name="Aura Storage", value="aura"),
                ],
                required=False
            )
            async def screenshot(ctx: discord.ApplicationContext, target: str = None):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    t = (target or "").strip().lower()
                    if not t or t not in ("full", "inventory", "aura"):
                        t = "full"
                        
                    if t != "full":
                        is_blocked = getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked())
                        if is_blocked:
                            embed = discord.Embed(title="Action Blocked", description=f"Cannot take an **{t}** screenshot while the macro is actively running an un-interruptible mode (e.g., Fishing Mode). Please wait for the macro to finish those action, or request a **Fullscreen** screenshot instead.", color=0xFF0000)
                            await ctx.respond(embed=embed, ephemeral=True)
                            return
                            
                    self.remote_command_queue.put(("__screenshot__", t))
                    labels = {"full": "full screen", "inventory": "inventory", "aura": "aura"}
                    embed = discord.Embed(title="Screenshot Requested", description=f"Taking a **{labels.get(t, t)}** screenshot and sending it to your webhooks...", color=0x00AAFF)
                    await ctx.respond(embed=embed)
                except Exception:
                    try:
                        await _safe_respond(ctx, "Something went wrong.", ephemeral=True)
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

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked()):
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

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked()):
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

                if item_name == "__close_roblox__":
                    try:
                        if self.check_roblox_procs():
                            self.terminate_roblox_processes()
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

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked()):
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

                    requested = str(amount or "").lower()
                    if requested not in ("full", "inventory", "aura"):
                        requested = "full"

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or (getattr(self, "_egg_collecting", False) and requested != "full") or ((hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked()) and requested != "full"):
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

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
                if item_name == "__equip_aura__":
                    aura_name = str(amount)
                    if not self.detection_running or self.reconnecting_state:
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked()):
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    def _equip_aura_action():
                        try:
                            self._remote_running = True
                            try:
                                self.remote_status_label.config(text=f"Bot: equipping {aura_name}")
                            except Exception:
                                pass
                            try:
                                self.remote_equip_aura(aura_name)
                            except Exception:
                                pass
                        finally:
                            self._remote_running = False
                            try:
                                self.remote_status_label.config(text="Bot: running")
                            except Exception:
                                pass

                    try:
                        self._action_scheduler.enqueue_action(_equip_aura_action, name=f"remote:equip_aura:{aura_name}", priority=2)
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

                if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked()):
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
        items_tab = self.config.get("items_tab", [1272, 329])
        
        self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
        time.sleep(0.22 + inventory_click_delay)
        
        self.Global_MouseClick(items_tab[0], items_tab[1])
        time.sleep(0.23)
        self.Global_MouseClick(items_tab[0], items_tab[1])
        time.sleep(0.23)
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

    def remote_equip_aura(self, aura_name):
        if not self.detection_running or self.reconnecting_state:return
        inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
        step_delay = 0.67 + inventory_click_delay
        for _ in range(4):
            if not self.detection_running or self.reconnecting_state:return
            self.activate_roblox_window()
            time.sleep(0.35)
        time.sleep(0.57)
        aura_menu = self.config.get("aura_menu", [37, 387])
        if aura_menu and aura_menu[0] > 0: self.Global_MouseClick(aura_menu[0], aura_menu[1])
        time.sleep(step_delay)
        aura_search_bar = self.config.get("aura_search_bar", [834, 364])
        if aura_search_bar and aura_search_bar[0] > 0: self.Global_MouseClick(aura_search_bar[0], aura_search_bar[1])
        time.sleep(step_delay)
        try:
            autoit.send(str(aura_name))
        except Exception:
            try:
                keyboard.write(str(aura_name).lower())
            except Exception:
                pass
        time.sleep(step_delay)
        try:
            keyboard.send("enter")
        except Exception:
            pass
        time.sleep(step_delay)

        first_aura_slot = self.config.get("first_aura_slot_pos", [819, 420])
        if first_aura_slot and first_aura_slot[0] > 0:
            try:
                import pyautogui
                pyautogui.moveTo(first_aura_slot[0], first_aura_slot[1])
                time.sleep(step_delay)
                # Scroll up to ensure we see the first result
                try:
                    autoit.mouse_wheel("up", max(1, int(round(5000 / 120.0))))
                except Exception:
                    pass
                time.sleep(step_delay)
            except Exception:
                pass
            self.Global_MouseClick(first_aura_slot[0], first_aura_slot[1])
        time.sleep(step_delay)
        equip_btn = self.config.get("equip_aura_button", [0, 0])
        if equip_btn and equip_btn[0] > 0:
            self.Global_MouseClick(equip_btn[0], equip_btn[1])
        time.sleep(step_delay)
        inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
        if inventory_close_button and inventory_close_button[0] > 0:
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
