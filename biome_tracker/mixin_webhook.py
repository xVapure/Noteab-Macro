from .base_support import *

class WebhookMixin:
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
                "footer": {"text": f"Coteab Macro {current_ver}", "icon_url": icon_url},
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
                        self.append_log(f"Failed to send screenshot to {webhook_url}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            self.error_logging(e, "Error in send_screen_screenshot_webhook")


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

    def _extract_webhook_channel_id(self, payload):
        try:
            if not isinstance(payload, dict):
                return ""
            channel_id = payload.get("channel_id")
            if channel_id is None:
                channel_obj = payload.get("channel")
                if isinstance(channel_obj, dict):
                    channel_id = channel_obj.get("id")
            channel_id_str = str(channel_id).strip() if channel_id is not None else ""
            if channel_id_str.isdigit():
                return channel_id_str
            return ""
        except Exception:
            return ""

    def refresh_active_webhook_channels(self, force=False):
        try:
            urls = self.get_webhook_list()
            normalized_urls = [u.strip() for u in urls if isinstance(u, str) and u.strip()]

            cached_urls = getattr(self, "_active_webhook_channel_lookup_urls", [])
            cached_mentions = getattr(self, "_active_webhook_channel_mentions", [])
            last_resolve = getattr(self, "_webhook_channel_resolve_time", 0)
            cooldown = getattr(self, "_webhook_channel_resolve_cooldown", 60)
            now = time.time()

            if (
                not force
                and isinstance(cached_urls, list)
                and isinstance(cached_mentions, list)
                and normalized_urls == cached_urls
            ):
                return list(cached_mentions)

            if not force and (now - last_resolve) < cooldown:
                return list(cached_mentions)

            mentions = []
            got_429 = False
            for webhook_url in normalized_urls:
                try:
                    response = requests.get(webhook_url, timeout=8)
                    if response.status_code == 429:
                        got_429 = True
                        retry_after = 120
                        try:
                            data = response.json()
                            retry_after = max(int(float(data.get("retry_after", 120))), 30)
                        except Exception:
                            pass
                        self._webhook_channel_resolve_cooldown = retry_after
                        print(f"[Webhook] Rate limited (429), backing off for {retry_after}s")
                        break
                    response.raise_for_status()
                    payload = response.json()
                    channel_id = self._extract_webhook_channel_id(payload)
                    if channel_id:
                        mentions.append(f"<#{channel_id}>")
                    else:
                        print(f"Failed to resolve channel_id from webhook payload: {webhook_url}")
                except requests.exceptions.HTTPError as e:
                    if "429" in str(e):
                        got_429 = True
                        self._webhook_channel_resolve_cooldown = 120
                        print(f"[Webhook] Rate limited (429), backing off for 120s")
                        break
                    print(f"Failed to resolve webhook channel for {webhook_url}: {e}")
                except Exception as e:
                    print(f"Failed to resolve webhook channel for {webhook_url}: {e}")

            self._webhook_channel_resolve_time = now
            if not got_429:
                self._webhook_channel_resolve_cooldown = 60
                self._active_webhook_channel_lookup_urls = normalized_urls
                self._active_webhook_channel_mentions = mentions
            return list(getattr(self, "_active_webhook_channel_mentions", []))
        except Exception:
            return []

    def _build_active_webhook_channels_field_value(self):
        mentions = self.refresh_active_webhook_channels()
        if not mentions:
            return "- (No webhook channels resolved)"
        return "\n".join(f"- {mention}" for mention in mentions)

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
                "footer": {"text": f"Coteab Macro {current_ver}", "icon_url": icon_url},
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
                        self.append_log(f"Failed to send quest screenshot to {webhook_url}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            self.error_logging(e, "Error in send_quest_screenshot_webhook")

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
                "footer": {"text": f"Coteab Macro {current_ver}", "icon_url": icon_url},
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
                        self.append_log(f"Failed to send inventory screenshot to {webhook_url}: {e}")
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
                "footer": {"text": f"Coteab Macro {current_ver}", "icon_url": icon_url},
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
                        self.append_log(f"Failed to send aura screenshot to {webhook_url}: {e}")
                    except Exception:
                        pass
        except Exception as e:
            self.error_logging(e, "Error in send_aura_screenshot_webhook")

    def send_webhook(self, biome, message_type, event_type, screenshot_path=None):
        urls = self.get_webhook_list()
        if not urls:
            self.append_log("Webhook URL is missing/not included in the config.json")
            return
        if message_type == "None": return
        biome_info = self.biome_data[biome]
        biome_color = int(biome_info["color"], 16)
        current_utc_time = datetime.now(timezone.utc)
        current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
        current_utc_time = str(current_utc_time)
        unix_ts = int(time.time())
        timestamp_title = f"<t:{unix_ts}:F> (<t:{unix_ts}:R>)"
        icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
        content = ""
        if event_type == "start" and biome in rare_biomes:
            content = "@everyone"
        private_server_link = self.config.get("private_server_link").replace("\n", "")
        if private_server_link == "":
            description = f"> ## Biome Started - {biome} \nNo link provided (ManasAarohi ate the link blame him)" if event_type == "start" else f"> ## Biome Ended - {biome}"
        else:
            description = f"> ## Biome Started - {biome} \n> ### **[Join Server]({private_server_link})**" if event_type == "start" else f"> ## Biome Ended - {biome}"
        embed = {
            "title": timestamp_title,
            "description": description,
            "color": biome_color,
            "footer": {
                "text": f"""Coteab Macro {current_ver}""",
                "icon_url": icon_url
            },
            "timestamp": current_utc_time
        }
        if event_type == "start":
            embed["thumbnail"] = {"url": biome_info["thumbnail_url"]}
        for webhook_url in urls:
            try:
                embed_copy = dict(embed)
                if screenshot_path and os.path.exists(screenshot_path):
                    embed_copy["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}
                    with open(screenshot_path, "rb") as image_file:
                        files = {"file": (os.path.basename(screenshot_path), image_file, "image/png")}
                        data = {"payload_json": json.dumps({"content": content, "embeds": [embed_copy]})}
                        response = requests.post(webhook_url, data=data, files=files, timeout=10)
                else:
                    payload = {"content": content, "embeds": [embed_copy]}
                    response = requests.post(webhook_url, json=payload)
                response.raise_for_status()
                self.append_log(f"Sent {message_type} for {biome} - {event_type} to webhook")
            except requests.exceptions.RequestException as e:
                self.append_log(f"Failed to send webhook: {e}")

    def send_merchant_webhook(self, merchant_name, screenshot_path=None, source='ocr'):
        urls = self.get_webhook_list()
        if not urls:
            self.append_log("Webhook URL is missing/not included in the config.json")
            return
        merchant_thumbnails = {
            "Mari": "https://i.postimg.cc/RZh2pw0j/mari.png ",
            "Jester": "https://i.postimg.cc/7PBVsdTq/jester.png",
            "Rin": "https://i.postimg.cc/j5n9B6Km/rin.png"
        }
        
        # merchant_counts is incremented in Merchant_Handler (mixin_actions.py)
        # so we only trigger the UI refresh here if needed
        if hasattr(self, "on_stats_update") and callable(self.on_stats_update):
            try:
                self.on_stats_update()
            except Exception:
                pass
        
        if merchant_name == "Mari":
            ping_id = self.mari_user_id_var.get() if hasattr(self, 'mari_user_id_var') else self.config.get("mari_user_id", "")
            ping_enabled = self.ping_mari_var.get() if hasattr(self, 'ping_mari_var') else self.config.get("ping_mari", False)
        elif merchant_name == "Jester":
            ping_id = self.jester_user_id_var.get() if hasattr(self, 'jester_user_id_var') else self.config.get("jester_user_id", "")
            ping_enabled = self.ping_jester_var.get() if hasattr(self, 'ping_jester_var') else self.config.get("ping_jester", False)
        elif merchant_name == "Rin":
            ping_id = self.rin_user_id_var.get() if hasattr(self, 'rin_user_id_var') else self.config.get("rin_user_id", "")
            ping_enabled = self.ping_rin_var.get() if hasattr(self, 'ping_rin_var') else self.config.get("ping_rin", False)
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
            "color": 11753 if merchant_name == "Mari" else (16752955 if merchant_name == "Rin" else 8595632),
            "thumbnail": {"url": merchant_thumbnails.get(merchant_name, "")},
            "timestamp": current_utc_time,
            "fields": [
                {"name": "Detection Source", "value": source.upper()}
            ],
            "footer": {
                "text": f"""Coteab Macro {current_ver}""",
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
                            self.append_log(
                                f"Webhook sent successfully for {merchant_name}: {response.status_code}")
                        except requests.exceptions.RequestException as e:
                            self.append_log(f"Failed to send merchant webhook: {e}")
            else:
                payload = {"content": content, "embeds": [embed]}
                for webhook_url in urls:
                    try:
                        response = requests.post(webhook_url, json=payload)
                        response.raise_for_status()
                        self.append_log(f"Webhook sent successfully for {merchant_name}: {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        self.append_log(f"Failed to send merchant webhook: {e}")
        except requests.exceptions.RequestException as e:
            self.append_log(f"Failed to send merchant webhook: {e}")

    def send_aura_webhook(self, aura_name, rarity, biome_message, screenshot_path=None):
        urls = self.get_webhook_list()
        if not urls:
            self.append_log("Webhook URL is missing/not included in the config.json")
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
                "text": f"""Coteab Macro {current_ver}""",
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
                            self.append_log(f"Aura webhook with screenshot sent for {aura_name}")
                        except requests.exceptions.RequestException as e:
                            self.append_log(f"Failed to send aura webhook with screenshot: {e}")
            else:
                payload = {"content": content, "embeds": [embed]}
                for webhook_url in urls:
                    try:
                        response = requests.post(webhook_url, json=payload, timeout=10)
                        response.raise_for_status()
                        self.append_log(f"Aura webhook sent for {aura_name}")
                    except requests.exceptions.RequestException as e:
                        self.append_log(f"Failed to send aura webhook: {e}")
        except Exception as e:
            self.error_logging(e, "Error in send_aura_webhook")

    def send_webhook_status(self, status, color=None):
        try:
            urls = self.get_webhook_list()
            if not urls:
                self.append_log("Webhook URL is missing/not included in the config.json")
                return
            default_color = 3066993 if "started" in status.lower() else 15158332
            embed_color = color if color is not None else default_color
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            if "started" in status.lower():
                n = len(urls)
                status = f"{status} ({n} webhook{'s' if n != 1 else ''} active)"
            fields = []
            if "started" in status.lower():
                fields.append({
                    "name": "Active webhook channels:",
                    "value": self._build_active_webhook_channels_field_value(),
                    "inline": False
                })
            fields.append({
                "name": "Join our Discord:",
                "value": "https://discord.gg/fw6q274Nrt",
                "inline": False
            })
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)
            embeds = [{
                "title": "== 🌟 Macro Status 🌟 ==",
                "description": f"> ## {status}",
                "color": embed_color,
                "timestamp": current_utc_time,
                "footer": {
                    "text": f"Coteab Macro {current_ver}",
                    "icon_url": icon_url
                },
                "fields": fields
            }]
            for webhook_url in urls:
                try:
                    response = requests.post(webhook_url, json={"embeds": embeds}, timeout=8)
                    response.raise_for_status()
                except requests.exceptions.RequestException as e:
                    self.append_log(f"Failed to send webhook status: {e}")
        except Exception as e:
            self.error_logging(e, "Error in webhook_status")

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
                    "text": f"Coteab Macro {current_ver}",
                    "icon_url": icon_url
                },
                "fields": [
                    {
                        "name": "Session Times:",
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

    def send_egg_ocr_webhook(self, egg_name, aura_rarity, discord_user_id="", screenshot_path=None):
        try:
            urls = self.get_webhook_list()
            if not urls: return
            icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
            current_utc_time = datetime.now(timezone.utc)
            current_utc_time.replace(microsecond=0).isoformat(timespec='seconds') + 'Z'
            current_utc_time = str(current_utc_time)

            content = f"<@{discord_user_id}>" if discord_user_id else ""

            embed = {
                "title": "🥚 Special Easter Egg Found 🥚",
                "description": f"> ## {egg_name}\n> Possible respective egg aura rarity: **{aura_rarity}**",
                "color": 0xffd700,
                "timestamp": current_utc_time,
                "thumbnail": {"url": "https://i.postimg.cc/FzRsHF7y/eggdoggo.png"},
                "footer": {
                    "text": f"Coteab Macro {current_ver}",
                    "icon_url": icon_url
                }
            }

            if screenshot_path and os.path.isfile(screenshot_path):
                embed["image"] = {"url": f"attachment://{os.path.basename(screenshot_path)}"}

            for webhook_url in urls:
                try:
                    embed_copy = dict(embed)
                    if screenshot_path and os.path.isfile(screenshot_path):
                        with open(screenshot_path, "rb") as img_file:
                            files = {"file": (os.path.basename(screenshot_path), img_file, "image/png")}
                            data = {"payload_json": json.dumps({"content": content, "embeds": [embed_copy]})}
                            response = requests.post(webhook_url, data=data, files=files, timeout=15)
                    else:
                        payload = {"content": content, "embeds": [embed_copy]}
                        response = requests.post(webhook_url, json=payload, timeout=10)
                    response.raise_for_status()
                    self.append_log(f"Egg OCR webhook sent for {egg_name}")
                except requests.exceptions.RequestException as e:
                    self.append_log(f"Failed to send egg OCR webhook: {e}")
        except Exception as e:
            self.error_logging(e, "Error in send_egg_ocr_webhook")
