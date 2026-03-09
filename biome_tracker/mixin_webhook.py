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
        icon_url = "https://i.postimg.cc/rsXpGncL/Noteab-Biome-Tracker.png"
        content = ""
        if event_type == "start" and biome in rare_biomes:
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
