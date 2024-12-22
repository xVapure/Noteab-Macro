import discord, asyncio, json, requests, time, os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from ahk import AHK
ahk = AHK()

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN_DO_NOT_SHARE')
USER_ID = os.getenv('DISCORD_USER_ID')

class BiomePresence(discord.Client):
    def __init__(self, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = int(user_id)
        self.config = self.load_config()
        self.biome_data = {
            "WINDY": {"color": 0x9ae5ff, "duration": 120, "thumbnail_url": "https://i.postimg.cc/6qPH4wy6/image.png"},
            "RAINY": {"color": 0x027cbd, "duration": 120, "thumbnail_url": "https://static.wikia.nocookie.net/sol-rng/images/e/ec/Rainy.png"},
            "SNOWY": {"color": 0xDceff9, "duration": 120, "thumbnail_url": "https://static.wikia.nocookie.net/sol-rng/images/d/d7/Snowy_img.png"},
            "SAND STORM": {"color": 0x8F7057, "duration": 600, "thumbnail_url": "https://i.postimg.cc/3JyL25Kz/image.png"},
            "HELL": {"color": 0xff4719, "duration": 660, "thumbnail_url": "https://i.postimg.cc/hGC5xNyY/image.png"},
            "STARFALL": {"color": 0x011ab7, "duration": 600, "thumbnail_url": "https://i.postimg.cc/1t0dY4J8/image.png"},
            "CORRUPTION": {"color": 0x6d32a8, "duration": 660, "thumbnail_url": "https://i.postimg.cc/ncZQ84Dh/image.png"},
            "NULL": {"color": 0x838383, "duration": 90, "thumbnail_url": "https://static.wikia.nocookie.net/sol-rng/images/f/fc/NULLLL.png"},
            "GLITCHED": {"color": 0xbfff00, "duration": 164, "thumbnail_url": "https://i.postimg.cc/bwJT4PxN/image.png"}
        }
        
        self.last_sent = {biome: datetime.min for biome in self.biome_data}


    def load_config(self):
       config_paths = [
           "config.json",
           "source_code/config.json",
           os.path.join(os.path.dirname(__file__), "config.json"),
           os.path.join(os.path.dirname(__file__), "source_code/config.json")
       ]
       
       for path in config_paths:
            if os.path.exists(path):
                with open(path, "r") as file:
                    return json.load(file)
       raise FileNotFoundError("config.json not found in any of the expected locations.")

    async def setup_hook(self):
        self.loop.create_task(self.check_user_activity())

    async def on_ready(self):
        print(f'Logged in as {self.user}')
    
    
    async def check_user_activity(self):
        await self.wait_until_ready()
        
        while not self.is_closed():
            user = self.get_user(self.user_id)
            if user:
                guilds = self.guilds
                for guild in guilds:
                    member = guild.get_member(self.user_id)
                    if member and member.activities:
                        for activity in member.activities:
                            if activity.name == "Roblox" and activity.details and "Sol's RNG [Eon1-1]" in activity.details:
                                biome = activity.large_image_text
                                if biome in self.biome_data:
                                    biome_info = self.biome_data[biome]
                                    now = datetime.now()
                                    cooldown = timedelta(seconds=biome_info['duration'])
                                    
                                    # Check if the biome has changed
                                    if now - self.last_sent[biome] >= cooldown or self.last_sent[biome] == datetime.min:
                                        print(f"[Background Check] {member.name} is in {activity.details}")
                                        print(f"Biome: {biome}, Color: {biome_info['color']}, Duration: {biome_info['duration']}")
                                        
                                        message_type = self.config["biome_notifier"].get(biome, "None")
                                        self.send_webhook(biome, message_type)
                                        self.last_sent[biome] = now
                                        
                                        if biome == "GLITCHED" and self.config.get("auto_pop_hp2", False):
                                            self.auto_pop_hp2()
                                    else:
                                        for other_biome in self.biome_data:
                                            if other_biome != biome:
                                                self.last_sent[other_biome] = datetime.min
            else:
                print("[Background Check] User not found, is your userid input correct cro..?")

            await asyncio.sleep(3)
            
    def send_webhook(self, biome, message_type):
        webhook_url = self.config.get("webhook_url")
        if not webhook_url:
            print("Webhook URL is missing/not included in the config.json")
            return

        if message_type == "None": return

        biome_info = self.biome_data[biome]
        biome_color = biome_info["color"]
        thumbnail_url = biome_info["thumbnail_url"]
        timestamp = time.strftime("[%H:%M:%S]") 
        
        content = ""
        if message_type == "Ping":
            user_id = self.config.get("webhook_user_id")
            if user_id:
                content = f"<@{user_id}>"

        private_server_link = self.config.get("private_server_link", "No link provided")

        payload = {
            "content": content,
            "embeds": [
                {
                    "title": f"{timestamp} Biome Started - {biome}",
                    "color": biome_color,
                    "thumbnail": {
                        "url": thumbnail_url
                    },
                    "footer": {
                        "text": "Noteab's Biome Detection [Discord Presence Method]"
                    },
                    "fields": [
                        {
                            "name": "Private Server Link",
                            "value": private_server_link,
                            "inline": False
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(webhook_url, json=payload)
            response.raise_for_status()
            print(f"Sent {message_type} for {biome}")
            
        except requests.exceptions.RequestException as e:
            print(f"Failed to send webhook: {e}")

    def auto_pop_hp2(self):
        
        for _ in range(3):
            ahk.win_activate("Roblox")
            time.sleep(0.3)

        hp2_amount = int(self.config.get("hp2_amount", 1))
        inventory_menu = self.config.get("inventory_menu", [0, 0])
        items_tab = self.config.get("items_tab", [0, 0])
        search_bar = self.config.get("search_bar", [0, 0])
        first_item_slot = self.config.get("first_item_slot", [0, 0])
        amount_box = self.config.get("amount_box", [0, 0])
        use_button = self.config.get("use_button", [0, 0])
        
        def MouseClick(x, y, click=1):
            ahk.mouse_move(x, y)
            time.sleep(0.185)
            ahk.click(x, y, click_count=click, coord_mode="Screen")
            
        MouseClick(inventory_menu[0], inventory_menu[1])

        time.sleep(0.3)
        
        MouseClick(items_tab[0], items_tab[1])
        time.sleep(0.3)
        
        MouseClick(search_bar[0], search_bar[1], click=2)
        time.sleep(0.32)
        
        ahk.send_input("Speed Potion")
        time.sleep(0.18)
        
        MouseClick(first_item_slot[0], first_item_slot[1])
        time.sleep(0.32)
        
        MouseClick(amount_box[0], amount_box[1])
        time.sleep(0.147)
        
        ahk.send_input("^a")
        time.sleep(0.2)
        ahk.send_input("{BACKSPACE}")
        time.sleep(0.15)
        
        ahk.send_input(str(hp2_amount))
        time.sleep(0.15)
        

        MouseClick(use_button[0], use_button[1])
        time.sleep(0.2)
        
        MouseClick(search_bar[0], search_bar[1])
        time.sleep(0.2)
        
        MouseClick(inventory_menu[0], inventory_menu[1])
        time.sleep(0.2)

def start_bot(user_id):
    intents = discord.Intents.default()
    intents.presences = True
    intents.members = True
    client = BiomePresence(user_id, intents=intents)
    try:
        asyncio.run(client.start(TOKEN))
    except Exception as e:
        print(f"An error occurred: {e}")


start_bot(USER_ID)



