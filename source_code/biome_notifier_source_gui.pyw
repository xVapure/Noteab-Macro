import tkinter as tk
import json, re, os
from tkinter import ttk
from tkinter import messagebox

def load_config():
    possible_paths = [
        "config.json",
        "source_code/config.json",
        os.path.join(os.path.dirname(__file__), "config.json"),
        os.path.join(os.path.dirname(__file__), "source_code/config.json")
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as file:
                    return json.load(file)
            except json.JSONDecodeError:
                print(f"Error decoding JSON from {path}. Using default configuration.")
                break

    print("config.json not found in any of the expected locations. Using default configuration.")
    return {
        "webhook_url": "",
        "webhook_user_id": "",
        "private_server_link": "",
        "biome_notifier": {biome: "None" for biome in biomes},
        "auto_pop_hp2": False,
        "hp2_amount": 1,
        "inventory_menu": [41, 538],
        "items_tab": [1272, 329],
        "search_bar": [855, 358],
        "first_item_slot": [839, 434],
        "amount_box": [594, 570],
        "use_button": [710, 573]
    }

def save_config():
   private_server_link = private_server_link_entry.get()
   if not validate_private_server_link(private_server_link):
       messagebox.showwarning(
           "Invalid PS Link!",
           "The private server link you provided is a share link, this is not safe to use due to fake link will get your account terminated. "
           "To get the code link, paste the share link into your browser and run it. This should convert the link to a privateServerLinkCode link. "
           "Copy and paste the converted link into the Private Server setting to fix this issue.\n\n"
           "The link should look like: https://www.roblox.com/games/15532962292/Sols-RNG-Eon1-1?privateServerLinkCode=..."
       )
       return
   
   try:
       with open("config.json", "r") as file:
           existing_config = json.load(file)
   except FileNotFoundError:
       existing_config = {}
       
   config = {
       "webhook_url": webhook_url_entry.get(),
       "webhook_user_id": webhook_user_id_entry.get(),
       "private_server_link": private_server_link,
       "biome_notifier": {
           "WINDY": windy_var.get(),
           "RAINY": rainy_var.get(),
           "SNOWY": snowy_var.get(),
           "SAND STORM": storm_var.get(),
           "HELL": hell_var.get(),
           "STARFALL": starfall_var.get(),
           "CORRUPTION": corruption_var.get(),
           "GRAVEYARD": graveyard_var.get(),
           "PUMPKIN MOON": pumpkin_moon_var.get(),
           "NULL": null_var.get(),
           "GLITCHED": glitched_var.get()
       },
       "auto_pop_hp2": auto_pop_hp2_var.get(),
       "hp2_amount": hp2_amount_var.get(),
       "inventory_menu": existing_config.get("inventory_menu", [0, 0]),
       "items_tab": existing_config.get("items_tab", [0, 0]),
       "search_bar": existing_config.get("search_bar", [0, 0]),
       "first_item_slot": existing_config.get("first_item_slot", [0, 0]),
       "amount_box": existing_config.get("amount_box", [0, 0]),
       "use_button": existing_config.get("use_button", [0, 0])
   }
   
   with open("config.json", "w") as file:
       json.dump(config, file, indent=4)

def validate_private_server_link(link):
    pattern = r"https://www\.roblox\.com/games/\d+/Sols-RNG-Eon1-1\?privateServerLinkCode=\w+"
    return re.match(pattern, link)

config = load_config()

class SnippingWidget:
    def __init__(self, root, config_key=None, callback=None):
        self.root = root
        self.config_key = config_key
        self.callback = callback
        self.snipping_window = None
        self.begin_x = None
        self.begin_y = None
        self.end_x = None
        self.end_y = None

    def start(self):
        self.snipping_window = tk.Toplevel(self.root)
        self.snipping_window.attributes('-fullscreen', True)
        self.snipping_window.attributes('-alpha', 0.3)
        self.snipping_window.configure(bg="lightblue")
        
        self.snipping_window.bind("<Button-1>", self.on_mouse_press)
        self.snipping_window.bind("<B1-Motion>", self.on_mouse_drag)
        self.snipping_window.bind("<ButtonRelease-1>", self.on_mouse_release)

        self.canvas = tk.Canvas(self.snipping_window, bg="lightblue", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    def on_mouse_press(self, event):
        self.begin_x = event.x
        self.begin_y = event.y
        self.canvas.delete("selection_rect")

    def on_mouse_drag(self, event):
        self.end_x, self.end_y = event.x, event.y
        self.canvas.delete("selection_rect")
        self.canvas.create_rectangle(self.begin_x, self.begin_y, self.end_x, self.end_y,
                                      outline="black", width=2, tag="selection_rect")

    def on_mouse_release(self, event):
        self.end_x = event.x
        self.end_y = event.y

        x1, y1 = min(self.begin_x, self.end_x), min(self.begin_y, self.end_y)
        x2, y2 = max(self.begin_x, self.end_x), max(self.begin_y, self.end_y)

        self.capture_region(x1, y1, x2, y2)
        self.snipping_window.destroy()

    def capture_region(self, x1, y1, x2, y2):
        if self.config_key:
            region = [x1, y1, x2 - x1, y2 - y1]
            print(f"Region for '{self.config_key}' set to {region}")
            
            if self.callback:
                self.callback(region)
               
# Biome notifier GUI
root = tk.Tk()
root.title("Biome Settings")
root.geometry("532x520")

tk.Label(root, text="Webhook URL:").grid(row=0, column=0, sticky="e")
webhook_url_entry = tk.Entry(root, width=50)
webhook_url_entry.grid(row=0, column=1, columnspan=2, pady=5)
webhook_url_entry.insert(0, config.get("webhook_url", ""))

# ID
tk.Label(root, text="Webhook User ID:").grid(row=1, column=0, sticky="e")
webhook_user_id_entry = tk.Entry(root, width=50)
webhook_user_id_entry.grid(row=1, column=1, columnspan=2, pady=5)
webhook_user_id_entry.insert(0, config.get("webhook_user_id", ""))

# Private Server Link
tk.Label(root, text="Private Server Link:").grid(row=2, column=0, sticky="e")
private_server_link_entry = tk.Entry(root, width=50)
private_server_link_entry.grid(row=2, column=1, columnspan=2, pady=5)
private_server_link_entry.insert(0, config.get("private_server_link", ""))

biomes = ["WINDY", "RAINY", "SNOWY", "SAND STORM", "HELL", "STARFALL", "CORRUPTION", "NULL", "GLITCHED", "GRAVEYARD", "PUMPKIN MOON"]
options = ["None", "Message", "Ping"]
variables = {}

for i, biome in enumerate(biomes, start=3):
    tk.Label(root, text=f"{biome}:").grid(row=i, column=0, sticky="e")
    var = tk.StringVar(value=config["biome_notifier"].get(biome, "None"))
    variables[biome] = var
    dropdown = ttk.Combobox(root, textvariable=var, values=options, state="readonly")
    dropdown.grid(row=i, column=1, pady=5)

windy_var = variables["WINDY"]
rainy_var = variables["RAINY"]
snowy_var = variables["SNOWY"]
storm_var = variables["SAND STORM"]
hell_var = variables["HELL"]
starfall_var = variables["STARFALL"]
corruption_var = variables["CORRUPTION"]
null_var = variables["NULL"]
glitched_var = variables["GLITCHED"]

# EVENT BIOMES
graveyard_var = variables["GRAVEYARD"]
pumpkin_moon_var = variables["PUMPKIN MOON"]


## AUTO POP HEAVENLY POTION 2 SETTINGS
hp2_frame = tk.Frame(root)
hp2_frame.grid(row=len(biomes) + 3, column=0, columnspan=3, pady=10, sticky="w")
# checkbox
auto_pop_hp2_var = tk.BooleanVar(value=config.get("auto_pop_hp2", False))
auto_pop_hp2_check = tk.Checkbutton(hp2_frame, text="Auto Pop (in glitched biome)", variable=auto_pop_hp2_var).grid(row=0, column=0, padx=5)
# HP2 Amount entry
hp2_amount_label = tk.Label(hp2_frame, text="HP2 Amount:").grid(row=0, column=1, padx=5)
hp2_amount_var = tk.StringVar(value=config.get("hp2_amount", ""))
hp2_amount_entry = tk.Entry(hp2_frame, textvariable=hp2_amount_var, width=10)
hp2_amount_entry.grid(row=0, column=2, padx=5)

def open_assign_inventory_window():
    assign_window = tk.Toplevel(root)
    assign_window.title("Inventory Coordinates")
    assign_window.geometry("400x300")

    positions = [
        ("Inventory Menu", "inventory_menu"),
        ("Items Tab", "items_tab"),
        ("Search Bar", "search_bar"),
        ("First Item Slot", "first_item_slot"),
        ("Amount Box", "amount_box"),
        ("Use Button", "use_button")
    ]

    coord_vars = {}

    for i, (label_text, config_key) in enumerate(positions):
        label = ttk.Label(assign_window, text=f"{label_text} (X, Y):")
        label.grid(row=i, column=0, padx=5, pady=5, sticky="w")

        x_var = tk.IntVar(value=config.get(config_key, [0, 0])[0])
        y_var = tk.IntVar(value=config.get(config_key, [0, 0])[1])
        coord_vars[config_key] = (x_var, y_var)

        x_entry = ttk.Entry(assign_window, textvariable=x_var, width=6)
        x_entry.grid(row=i, column=1, padx=5, pady=5)

        y_entry = ttk.Entry(assign_window, textvariable=y_var, width=6)
        y_entry.grid(row=i, column=2, padx=5, pady=5)

        select_button = ttk.Button(
            assign_window, text="Assign Click",
            command=lambda key=config_key: start_capture_thread(key, coord_vars)
        )
        select_button.grid(row=i, column=3, padx=5, pady=5)

    save_button = ttk.Button(assign_window, text="Save", command=lambda: save_inventory_coordinates(assign_window, coord_vars))
    save_button.grid(row=len(positions), column=0, columnspan=4, pady=10)

def start_capture_thread(config_key, coord_vars):
    snipping_tool = SnippingWidget(root, config_key=config_key, callback=lambda region: update_coordinates(config_key, region, coord_vars))
    snipping_tool.start()
    

def update_coordinates(config_key, region, coord_vars):
    x, y, _, _ = region
    x_var, y_var = coord_vars[config_key]
    x_var.set(x)
    y_var.set(y)
    

def save_inventory_coordinates(window, coord_vars):
    try:
        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        for key, (x_var, y_var) in coord_vars.items():
            config[key] = [x_var.get(), y_var.get()]

        with open("config.json", "w") as config_file:
            json.dump(config, config_file, indent=4)
    except Exception as e:
        print(f"Failed to save inventory coordinates to config.json: {e}")
    finally:
        window.destroy()

assign_inventory_button = tk.Button(hp2_frame, text="Assign Inventory", command=open_assign_inventory_window)
assign_inventory_button.grid(row=0, column=3, padx=5)    
   

save_button = tk.Button(root, text="Save", command=save_config)
save_button.grid(row=len(biomes) + 4, column=1, pady=10)
root.mainloop()