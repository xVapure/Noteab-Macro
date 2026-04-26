import json
import threading
import time
from pathlib import Path
from typing import Any, Callable
import keyboard
import autoit
import cv2
import numpy as np
import pyautogui
import win32clipboard

try:
    import mss
except Exception:
    mss = None

pyautogui.FAILSAFE = False

DEFAULT_FISHING_CONFIG = {
    "fishing_bar_region": [757, 762, 405, 21],          # this is the big ahh fishing bar
    "fishing_detect_pixel": [1176, 836],                # this is the thingy at the corner when a fish gets detected (fishing diamond)
    "fishing_click_position": [862, 843],               # fishing click boom
    "fishing_midbar_sample_pos": [955, 767],            # this is the midbar colour
    "fishing_close_button_pos": [1113, 342],            # fishing close button
    "fishing_flarg_dialogue_box": [1046, 782],          # Captain Flarg dialogue box
    "fishing_shop_open_button": [616, 938],             # open fishing shop
    "fishing_shop_sell_tab": [1285, 312],               # fishing shop sell tab
    "fishing_shop_close_button": [1458, 269],           # close fishing shop
    "fishing_shop_first_fish": [827, 404],              # first fish slot in shop
    "fishing_shop_sell_all_button": [662, 799],         # sell all button in shop
    "fishing_confirm_sell_all_button": [800, 619],      # confirm sell-all button
    "collections_button": [33, 443],                    # collections menu button
    "exit_collections_button": [385, 164],              # close collections menu button
    "aura_menu": [1200, 500],                           # aura menu button
    "aura_search_bar": [834, 364],                      # aura search bar
    "first_aura_slot_pos": [0, 0],                      # first aura slot
    "equip_aura_button": [0, 0],                        # equip aura button
    "inventory_close_button": [1418, 298],              # close inventory button
}

AUTOIT_KEY_MAP = {
    "space": "SPACE",
    "enter": "ENTER",
    "tab": "TAB",
    "esc": "ESC",
    "escape": "ESC",
    "shift": "SHIFT",
    "ctrl": "CTRL",
    "control": "CTRL",
    "alt": "ALT",
    "left": "LEFT",
    "right": "RIGHT",
    "up": "UP",
    "down": "DOWN",
}

def _safe_type_text(text: str, cfg: dict[str, Any] | None = None) -> None:
    text = str(text)
    if cfg and cfg.get("azerty_mode", False):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            autoit.send("^v")
            return
        except Exception:
            pass
    autoit.send(text)

WALK_TO_FISH_EVENTS: list[dict[str, Any]] = [{"type":"key_down","x":0,"y":0,"button":"","key":"w","delta":0,"t":0.7391250133514404},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":0.741126298904419},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":0.9960780143737793},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.026473045349121},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.0575404167175293},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.1038482189178467},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.1342198848724365},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.165168046951294},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.1959125995635986},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.226245641708374},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.2579402923583984},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.2890980243682861},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.3357858657836914},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.3669459819793701},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.3978071212768555},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.4294638633728027},{"type":"key_up","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.4381849765777588},{"type":"key_up","x":0,"y":0,"button":"","key":"w","delta":0,"t":8.1}]
WALK_TO_SELL_FISH_EVENTS: list[dict[str, Any]] = [{"t": 0.6193469999998342, "type": "key_down", "key": "a"}, {"t": 0.6597596999999951, "type": "key_down", "key": "w"}, {"t": 0.6727883999992628, "type": "key_up", "key": "w"}, {"t": 0.7120463999999629, "type": "key_down", "key": "w"}, {"t": 0.9642282000004343, "type": "key_down", "key": "w"}, {"t": 0.9950336999991123, "type": "key_down", "key": "w"}, {"t": 1.0267604999989999, "type": "key_down", "key": "w"}, {"t": 1.0575645999997505, "type": "key_down", "key": "w"}, {"t": 1.0888541999993322, "type": "key_down", "key": "w"}, {"t": 1.1230503999995562, "type": "key_down", "key": "w"}, {"t": 1.1543273999996018, "type": "key_down", "key": "w"}, {"t": 1.1854724000004353, "type": "key_down", "key": "w"}, {"t": 1.2166502999989461, "type": "key_down", "key": "w"}, {"t": 1.2478993000004266, "type": "key_down", "key": "w"}, {"t": 1.2791823000006843, "type": "key_down", "key": "w"}, {"t": 1.3102110999989236, "type": "key_down", "key": "w"}, {"t": 1.3416887000003044, "type": "key_down", "key": "w"}, {"t": 1.372850899999321, "type": "key_down", "key": "w"}, {"t": 1.4039627999991353, "type": "key_down", "key": "w"}, {"t": 1.4352505999995628, "type": "key_down", "key": "w"}, {"t": 1.4664444999998523, "type": "key_down", "key": "w"}, {"t": 1.4976069000003918, "type": "key_down", "key": "w"}, {"t": 1.5290093000003253, "type": "key_down", "key": "w"}, {"t": 1.559990800000378, "type": "key_down", "key": "w"}, {"t": 1.5913504999989527, "type": "key_down", "key": "w"}, {"t": 1.6258340000003955, "type": "key_down", "key": "w"}, {"t": 1.6567837999991752, "type": "key_down", "key": "w"}, {"t": 1.6878660000002128, "type": "key_down", "key": "w"}, {"t": 1.7193091999997705, "type": "key_down", "key": "w"}, {"t": 1.7503789999991568, "type": "key_down", "key": "w"}, {"t": 1.7817417999995087, "type": "key_down", "key": "w"}, {"t": 1.812794400000712, "type": "key_down", "key": "w"}, {"t": 1.844162999999753, "type": "key_down", "key": "w"}, {"t": 1.875336499999321, "type": "key_down", "key": "w"}, {"t": 1.9066161999999167, "type": "key_down", "key": "w"}, {"t": 1.937760900000285, "type": "key_down", "key": "w"}, {"t": 1.96885839999959, "type": "key_down", "key": "w"}, {"t": 2.0002492999992683, "type": "key_down", "key": "w"}, {"t": 2.031333999999333, "type": "key_down", "key": "w"}, {"t": 2.062613899999633, "type": "key_down", "key": "w"}, {"t": 2.0937567000000854, "type": "key_down", "key": "w"}, {"t": 2.12815159999991, "type": "key_down", "key": "w"}, {"t": 2.159322699999393, "type": "key_down", "key": "w"}, {"t": 2.1907281000003422, "type": "key_down", "key": "w"}, {"t": 2.2218591999990167, "type": "key_down", "key": "w"}, {"t": 2.2530986000001576, "type": "key_down", "key": "w"}, {"t": 2.284298700000363, "type": "key_down", "key": "w"}, {"t": 2.3153827999994974, "type": "key_down", "key": "w"}, {"t": 2.3466623000003892, "type": "key_down", "key": "w"}, {"t": 2.3778927999992447, "type": "key_down", "key": "w"}, {"t": 2.4088914999992994, "type": "key_down", "key": "w"}, {"t": 2.4401868999993894, "type": "key_down", "key": "w"}, {"t": 2.471325999998953, "type": "key_down", "key": "w"}, {"t": 2.5026333999994677, "type": "key_down", "key": "w"}, {"t": 2.533809900000051, "type": "key_down", "key": "w"}, {"t": 2.5650354999997944, "type": "key_down", "key": "w"}, {"t": 2.5965634000003774, "type": "key_down", "key": "w"}, {"t": 2.6305186999998114, "type": "key_down", "key": "w"}, {"t": 2.6620552000003954, "type": "key_down", "key": "w"}, {"t": 2.692920100000265, "type": "key_down", "key": "w"}, {"t": 2.72429000000011, "type": "key_down", "key": "w"}, {"t": 2.755670500000633, "type": "key_down", "key": "w"}, {"t": 2.78684819999944, "type": "key_down", "key": "w"}, {"t": 2.818274900000688, "type": "key_down", "key": "w"}, {"t": 2.849293299999772, "type": "key_down", "key": "w"}, {"t": 2.8805269000004046, "type": "key_down", "key": "w"}, {"t": 2.911636599999838, "type": "key_down", "key": "w"}, {"t": 2.942870099999709, "type": "key_down", "key": "w"}, {"t": 2.9745170999995025, "type": "key_down", "key": "w"}, {"t": 3.0053002999993623, "type": "key_down", "key": "w"}, {"t": 3.0363990000005288, "type": "key_down", "key": "w"}, {"t": 3.0679503999999724, "type": "key_down", "key": "w"}, {"t": 3.099046499999531, "type": "key_down", "key": "w"}, {"t": 3.133262499999546, "type": "key_down", "key": "w"}, {"t": 3.1645451999993384, "type": "key_down", "key": "w"}, {"t": 3.195627400000376, "type": "key_down", "key": "w"}, {"t": 3.2268208999994386, "type": "key_down", "key": "w"}, {"t": 3.2581417999990663, "type": "key_down", "key": "w"}, {"t": 3.296984099999463, "type": "key_down", "key": "w"}, {"t": 3.320476700000654, "type": "key_down", "key": "w"}, {"t": 3.3516098000000056, "type": "key_down", "key": "w"}, {"t": 3.3829000999994605, "type": "key_down", "key": "w"}, {"t": 3.414121300000261, "type": "key_down", "key": "w"}, {"t": 3.445333699999537, "type": "key_down", "key": "w"}, {"t": 3.4765504999995755, "type": "key_down", "key": "w"}, {"t": 3.5078064999997878, "type": "key_down", "key": "w"}, {"t": 3.5390580000002956, "type": "key_down", "key": "w"}, {"t": 3.5703704000006837, "type": "key_down", "key": "w"}, {"t": 3.6014764999999898, "type": "key_down", "key": "w"}, {"t": 3.635601100000713, "type": "key_down", "key": "w"}, {"t": 3.666815399999905, "type": "key_down", "key": "w"}, {"t": 3.698049799999353, "type": "key_down", "key": "w"}, {"t": 3.7293470000004163, "type": "key_down", "key": "w"}, {"t": 3.760607300000629, "type": "key_down", "key": "w"}, {"t": 3.791690199999721, "type": "key_down", "key": "w"}, {"t": 3.823153999999704, "type": "key_down", "key": "w"}, {"t": 3.854187599999932, "type": "key_down", "key": "w"}, {"t": 3.8855776000000333, "type": "key_down", "key": "w"}, {"t": 3.916821999999229, "type": "key_down", "key": "w"}, {"t": 3.947911799999929, "type": "key_down", "key": "w"}, {"t": 3.979176599999846, "type": "key_down", "key": "w"}, {"t": 4.010453999999299, "type": "key_down", "key": "w"}, {"t": 4.041500799999994, "type": "key_down", "key": "w"}, {"t": 4.072852100000091, "type": "key_down", "key": "w"}, {"t": 4.104022399998939, "type": "key_down", "key": "w"}, {"t": 4.138394399999015, "type": "key_down", "key": "w"}, {"t": 4.169658599999821, "type": "key_down", "key": "w"}, {"t": 4.202726999999868, "type": "key_down", "key": "w"}, {"t": 4.2340526999996655, "type": "key_down", "key": "w"}, {"t": 4.265096699999049, "type": "key_down", "key": "w"}, {"t": 4.296333700000105, "type": "key_down", "key": "w"}, {"t": 4.327540599999338, "type": "key_down", "key": "w"}, {"t": 4.358830900000612, "type": "key_down", "key": "w"}, {"t": 4.390067700000145, "type": "key_down", "key": "w"}, {"t": 4.42125329999908, "type": "key_down", "key": "w"}, {"t": 4.45258769999964, "type": "key_down", "key": "w"}, {"t": 4.48373729999912, "type": "key_down", "key": "w"}, {"t": 4.515447600000698, "type": "key_down", "key": "w"}, {"t": 4.546121400000629, "type": "key_down", "key": "w"}, {"t": 4.577334999999948, "type": "key_down", "key": "w"}, {"t": 4.608623699999953, "type": "key_down", "key": "w"}, {"t": 4.642644999999902, "type": "key_down", "key": "w"}, {"t": 4.6740092, "type": "key_down", "key": "w"}, {"t": 4.705390299999635, "type": "key_down", "key": "w"}, {"t": 4.736487199999829, "type": "key_down", "key": "w"}, {"t": 4.768060200000036, "type": "key_down", "key": "w"}, {"t": 4.79895949999991, "type": "key_down", "key": "w"}, {"t": 4.830198800000289, "type": "key_down", "key": "w"}, {"t": 4.861402599999565, "type": "key_down", "key": "w"}, {"t": 4.892606899999009, "type": "key_down", "key": "w"}, {"t": 4.923649700000169, "type": "key_down", "key": "w"}, {"t": 4.955197400000543, "type": "key_down", "key": "w"}, {"t": 4.98626669999976, "type": "key_down", "key": "w"}, {"t": 5.017413199999282, "type": "key_down", "key": "w"}, {"t": 5.048671700000341, "type": "key_down", "key": "w"}, {"t": 5.07975549999901, "type": "key_down", "key": "w"}, {"t": 5.111202000000048, "type": "key_down", "key": "w"}, {"t": 5.145361299999422, "type": "key_down", "key": "w"}, {"t": 5.176747699999396, "type": "key_down", "key": "w"}, {"t": 5.207782899999074, "type": "key_down", "key": "w"}, {"t": 5.239155900000696, "type": "key_down", "key": "w"}, {"t": 5.270378900000651, "type": "key_down", "key": "w"}, {"t": 5.301812199999404, "type": "key_down", "key": "w"}, {"t": 5.332697300000291, "type": "key_down", "key": "w"}, {"t": 5.36438950000047, "type": "key_down", "key": "w"}, {"t": 5.395104400000491, "type": "key_down", "key": "w"}, {"t": 5.42637300000024, "type": "key_down", "key": "w"}, {"t": 5.457555499999216, "type": "key_down", "key": "w"}, {"t": 5.488868599999478, "type": "key_down", "key": "w"}, {"t": 5.520106500000111, "type": "key_down", "key": "w"}, {"t": 5.551268799999889, "type": "key_down", "key": "w"}, {"t": 5.582484500000646, "type": "key_down", "key": "w"}, {"t": 5.613801600000443, "type": "key_down", "key": "w"}, {"t": 5.647874399999637, "type": "key_down", "key": "w"}, {"t": 5.679281799999444, "type": "key_down", "key": "w"}, {"t": 5.7104615999996895, "type": "key_down", "key": "w"}, {"t": 5.74157170000035, "type": "key_down", "key": "w"}, {"t": 5.7729507999993075, "type": "key_down", "key": "w"}, {"t": 5.804234499999438, "type": "key_down", "key": "w"}, {"t": 5.8352063999991515, "type": "key_down", "key": "w"}, {"t": 5.866506599999411, "type": "key_down", "key": "w"}, {"t": 5.897771899999498, "type": "key_down", "key": "w"}, {"t": 5.928989000000001, "type": "key_down", "key": "w"}, {"t": 5.960458800000197, "type": "key_down", "key": "w"}, {"t": 5.991408699999738, "type": "key_down", "key": "w"}, {"t": 6.022537700000612, "type": "key_down", "key": "w"}, {"t": 6.053936199999953, "type": "key_down", "key": "w"}, {"t": 6.085071499999685, "type": "key_down", "key": "w"}, {"t": 6.116341099999772, "type": "key_down", "key": "w"}, {"t": 6.15089049999915, "type": "key_down", "key": "w"}, {"t": 6.181583100000353, "type": "key_down", "key": "w"}, {"t": 6.212923299999602, "type": "key_down", "key": "w"}, {"t": 6.244282899999234, "type": "key_down", "key": "w"}, {"t": 6.275380499999301, "type": "key_down", "key": "w"}, {"t": 6.306665500000236, "type": "key_down", "key": "w"}, {"t": 6.3378520000005665, "type": "key_down", "key": "w"}, {"t": 6.369061499999589, "type": "key_down", "key": "w"}, {"t": 6.400289999999586, "type": "key_down", "key": "w"}, {"t": 6.431366400000115, "type": "key_down", "key": "w"}, {"t": 6.462889500000529, "type": "key_down", "key": "w"}, {"t": 6.49381270000049, "type": "key_down", "key": "w"}, {"t": 6.525106600000072, "type": "key_down", "key": "w"}, {"t": 6.556317900000067, "type": "key_down", "key": "w"}, {"t": 6.587588500000493, "type": "key_down", "key": "w"}, {"t": 6.618935299999066, "type": "key_down", "key": "w"}, {"t": 6.653086899999835, "type": "key_down", "key": "w"}, {"t": 6.684172299999773, "type": "key_down", "key": "w"}, {"t": 6.6913057999991, "type": "key_up", "key": "w"}, {"t": 6.707602599999518, "type": "key_up", "key": "a"}, {"t": 7.5361897999991925, "type": "key_down", "key": "d"}, {"t": 7.623953799999072, "type": "key_up", "key": "d"}, {"t": 7.80212500000016, "type": "key_down", "key": "d"}, {"t": 7.872129999999743, "type": "key_up", "key": "d"}, {"t": 8.742754900000364, "type": "key_down", "key": "w"}, {"t": 9.000408199999583, "type": "key_down", "key": "w"}, {"t": 9.025709100000313, "type": "key_down", "key": "w"}, {"t": 9.05721369999992, "type": "key_down", "key": "w"}, {"t": 9.088090499999453, "type": "key_down", "key": "w"}, {"t": 9.119410600000265, "type": "key_down", "key": "w"}, {"t": 9.150680900000225, "type": "key_down", "key": "w"}, {"t": 9.185271599999396, "type": "key_down", "key": "w"}, {"t": 9.215967899999669, "type": "key_down", "key": "w"}, {"t": 9.24732849999964, "type": "key_down", "key": "w"}, {"t": 9.278765600000042, "type": "key_down", "key": "w"}, {"t": 9.309823300000062, "type": "key_down", "key": "w"}, {"t": 9.341039200000523, "type": "key_down", "key": "w"}, {"t": 9.372143399999914, "type": "key_down", "key": "w"}, {"t": 9.40364849999969, "type": "key_down", "key": "w"}, {"t": 9.434679199999664, "type": "key_down", "key": "w"}, {"t": 9.465984700000263, "type": "key_down", "key": "w"}, {"t": 9.49708880000071, "type": "key_down", "key": "w"}, {"t": 9.528302999999141, "type": "key_down", "key": "w"}, {"t": 9.559484299999895, "type": "key_down", "key": "w"}, {"t": 9.590852799999993, "type": "key_down", "key": "w"}, {"t": 9.622187700000723, "type": "key_down", "key": "w"}, {"t": 9.653162799999336, "type": "key_down", "key": "w"}, {"t": 9.687520199999199, "type": "key_down", "key": "w"}, {"t": 9.718865099999675, "type": "key_down", "key": "w"}, {"t": 9.749952399999529, "type": "key_down", "key": "w"}, {"t": 9.781281300000046, "type": "key_down", "key": "w"}, {"t": 9.812294199999087, "type": "key_down", "key": "w"}, {"t": 9.84373659999983, "type": "key_down", "key": "w"}, {"t": 9.87474839999959, "type": "key_down", "key": "w"}, {"t": 9.906169699999737, "type": "key_down", "key": "w"}, {"t": 9.937127400000463, "type": "key_down", "key": "w"}, {"t": 9.968458100000134, "type": "key_down", "key": "w"}, {"t": 9.999548499999946, "type": "key_down", "key": "w"}, {"t": 10.030921399998988, "type": "key_down", "key": "w"}, {"t": 10.06202470000062, "type": "key_down", "key": "w"}, {"t": 10.093436900000597, "type": "key_down", "key": "w"}, {"t": 10.124556999999186, "type": "key_down", "key": "w"}, {"t": 10.155609400000685, "type": "key_down", "key": "w"}, {"t": 10.190108900000268, "type": "key_down", "key": "w"}, {"t": 10.221244200000001, "type": "key_down", "key": "w"}, {"t": 10.252412100000583, "type": "key_down", "key": "w"}, {"t": 10.283616599999732, "type": "key_down", "key": "w"}, {"t": 10.314863499999774, "type": "key_down", "key": "w"}, {"t": 10.346077300000616, "type": "key_down", "key": "w"}, {"t": 10.377274000000398, "type": "key_down", "key": "w"}, {"t": 10.408574400000361, "type": "key_down", "key": "w"}, {"t": 10.439787799999976, "type": "key_down", "key": "w"}, {"t": 10.471979399999327, "type": "key_down", "key": "w"}, {"t": 10.503160500000376, "type": "key_down", "key": "w"}, {"t": 10.506223000000318, "type": "key_down", "key": "a"}, {"t": 10.760075599999254, "type": "key_down", "key": "a"}, {"t": 10.79137350000019, "type": "key_down", "key": "a"}, {"t": 10.82228699999905, "type": "key_down", "key": "a"}, {"t": 10.853508899999724, "type": "key_down", "key": "a"}, {"t": 10.884953499999028, "type": "key_down", "key": "a"}, {"t": 10.916021099999853, "type": "key_down", "key": "a"}, {"t": 10.94753370000035, "type": "key_down", "key": "a"}, {"t": 10.978636100000585, "type": "key_down", "key": "a"}, {"t": 11.009694299998955, "type": "key_down", "key": "a"}, {"t": 11.040936800000054, "type": "key_down", "key": "a"}, {"t": 11.072365899999568, "type": "key_down", "key": "a"}, {"t": 11.103381400000217, "type": "key_down", "key": "a"}, {"t": 11.134686699999293, "type": "key_down", "key": "a"}, {"t": 11.165795700000672, "type": "key_down", "key": "a"}, {"t": 11.200234199999613, "type": "key_down", "key": "a"}, {"t": 11.231370600000446, "type": "key_down", "key": "a"}, {"t": 11.2625551000001, "type": "key_down", "key": "a"}, {"t": 11.293824399999721, "type": "key_down", "key": "a"}, {"t": 11.325045800000225, "type": "key_down", "key": "a"}, {"t": 11.356440499999735, "type": "key_down", "key": "a"}, {"t": 11.387499799999205, "type": "key_down", "key": "a"}, {"t": 11.418791699999929, "type": "key_down", "key": "a"}, {"t": 11.450135600000067, "type": "key_down", "key": "a"}, {"t": 11.48105410000062, "type": "key_down", "key": "a"}, {"t": 11.512485799999922, "type": "key_down", "key": "a"}, {"t": 11.543878700000278, "type": "key_down", "key": "a"}, {"t": 11.574648100000559, "type": "key_down", "key": "a"}, {"t": 11.58372369999961, "type": "key_up", "key": "a"}, {"t": 11.59377189999941, "type": "key_up", "key": "w"}, {"t": 12.047159499999907, "type": "key_down", "key": "s"}, {"t": 12.154938100000436, "type": "key_up", "key": "s"}, {"t": 12.629220200000418, "type": "key_down", "key": "space"}, {"t": 12.655512100000124, "type": "key_down", "key": "w"}, {"t": 12.814489700000195, "type": "key_up", "key": "space"}, {"t": 12.910129899999447, "type": "key_down", "key": "w"}, {"t": 12.941546399999424, "type": "key_down", "key": "w"}, {"t": 12.955445999999938, "type": "key_up", "key": "w"}, {"t": 13.489220299999943, "type": "key_down", "key": "w"}, {"t": 13.561029799999233, "type": "key_up", "key": "w"}, {"t": 14.412931999999273, "type": "key_down", "key": "s"}, {"t": 14.54973980000068, "type": "key_up", "key": "s"}, {"t": 14.839802999998938, "type": "key_down", "key": "w"}, {"t": 14.910316199999215, "type": "key_down", "key": "space"}, {"t": 15.074401100000614, "type": "key_up", "key": "space"}, {"t": 15.173085799999171, "type": "key_up", "key": "w"}, {"t": 16.141198299999814, "type": "key_down", "key": "w"}, {"t": 16.39598979999937, "type": "key_down", "key": "w"}, {"t": 16.427140699999654, "type": "key_down", "key": "w"}, {"t": 16.458206899998913, "type": "key_down", "key": "w"}, {"t": 16.489464399999633, "type": "key_down", "key": "w"}, {"t": 16.52102709999963, "type": "key_down", "key": "w"}, {"t": 16.552005199999257, "type": "key_down", "key": "w"}, {"t": 16.583117899999706, "type": "key_down", "key": "w"}, {"t": 16.61437239999941, "type": "key_down", "key": "w"}, {"t": 16.645790999999008, "type": "key_down", "key": "w"}, {"t": 16.676585400000477, "type": "key_down", "key": "w"}, {"t": 16.70833870000024, "type": "key_down", "key": "w"}, {"t": 16.74216460000025, "type": "key_down", "key": "w"}, {"t": 16.773395199999868, "type": "key_down", "key": "w"}, {"t": 16.80488089999926, "type": "key_down", "key": "w"}, {"t": 16.835984800000006, "type": "key_down", "key": "w"}, {"t": 16.865132999999332, "type": "key_up", "key": "w"}, {"t": 17.111777399999482, "type": "key_down", "key": "s"}, {"t": 17.258736100000533, "type": "key_up", "key": "s"}, {"t": 17.57201990000067, "type": "key_down", "key": "w"}, {"t": 17.600325699999303, "type": "key_down", "key": "space"}, {"t": 17.763527900000554, "type": "key_up", "key": "space"}, {"t": 19.05178150000029, "type": "key_down", "key": "e"}, {"t": 19.179535499999474, "type": "key_up", "key": "e"}, {"t": 19.239933900000324, "type": "key_down", "key": "e"}, {"t": 19.329591399999117, "type": "key_up", "key": "e"}, {"t": 19.339571599999545, "type": "key_up", "key": "w"}, {"t": 19.498178499999995, "type": "mouse_down", "button": "right", "x": 960, "y": 540}, {"t": 19.657035899999755, "type": "mouse_move", "x": 960, "y": 543}, {"t": 19.66508149999936, "type": "mouse_move", "x": 960, "y": 549}, {"t": 19.672360599999593, "type": "mouse_move", "x": 958, "y": 554}, {"t": 19.680141799999546, "type": "mouse_move", "x": 956, "y": 564}, {"t": 19.688101199999437, "type": "mouse_move", "x": 952, "y": 585}, {"t": 19.696390400000382, "type": "mouse_move", "x": 948, "y": 605}, {"t": 19.70351540000047, "type": "mouse_move", "x": 954, "y": 600}, {"t": 19.711599399999614, "type": "mouse_move", "x": 954, "y": 612}, {"t": 19.719616500000484, "type": "mouse_move", "x": 960, "y": 613}, {"t": 19.727283300000636, "type": "mouse_move", "x": 963, "y": 614}, {"t": 19.735356999999567, "type": "mouse_move", "x": 969, "y": 630}, {"t": 19.74369850000039, "type": "mouse_move", "x": 971, "y": 639}, {"t": 19.751249900000403, "type": "mouse_move", "x": 973, "y": 644}, {"t": 19.75937370000065, "type": "mouse_move", "x": 976, "y": 636}, {"t": 19.76750279999942, "type": "mouse_move", "x": 978, "y": 629}, {"t": 19.775386999999682, "type": "mouse_move", "x": 977, "y": 621}, {"t": 19.785911299999498, "type": "mouse_move", "x": 978, "y": 605}, {"t": 19.79182849999961, "type": "mouse_move", "x": 973, "y": 584}, {"t": 19.79901179999979, "type": "mouse_move", "x": 961, "y": 545}, {"t": 19.805711699998938, "type": "mouse_move", "x": 965, "y": 562}, {"t": 19.813381899999513, "type": "mouse_move", "x": 962, "y": 555}, {"t": 19.820118499999808, "type": "mouse_move", "x": 961, "y": 547}, {"t": 19.83409070000016, "type": "mouse_move", "x": 960, "y": 545}, {"t": 19.971601199998986, "type": "mouse_move", "x": 960, "y": 543}, {"t": 19.99255970000013, "type": "mouse_move", "x": 960, "y": 544}, {"t": 20.006362199999785, "type": "mouse_move", "x": 960, "y": 544}, {"t": 20.03479250000055, "type": "mouse_move", "x": 960, "y": 543}, {"t": 20.048661099999663, "type": "mouse_move", "x": 961, "y": 543}, {"t": 20.06219670000064, "type": "mouse_up", "button": "right", "x": 960, "y": 543}]

def _load_config_file() -> dict[str, Any]:
    config_path = Path(__file__).resolve().with_name("config.json")
    if not config_path.exists():
        return {}
    try:
        content = json.loads(config_path.read_text(encoding="utf-8"))
        return content if isinstance(content, dict) else {}
    except Exception:
        return {}


def _coerce_point(raw: Any, fallback: list[int]) -> tuple[int, int]:
    if not isinstance(raw, (list, tuple)) or len(raw) < 2:
        return fallback[0], fallback[1]
    try:
        return int(raw[0]), int(raw[1])
    except Exception:
        return fallback[0], fallback[1]


def _coerce_region(raw: Any, fallback: list[int]) -> tuple[int, int, int, int]:
    if not isinstance(raw, (list, tuple)) or len(raw) < 4:
        return fallback[0], fallback[1], fallback[2], fallback[3]
    try:
        x = int(raw[0])
        y = int(raw[1])
        w = max(1, int(raw[2]))
        h = max(1, int(raw[3]))
        return x, y, w, h
    except Exception:
        return fallback[0], fallback[1], fallback[2], fallback[3]


def _coerce_int(raw: Any, fallback: int, min_value: int, max_value: int) -> int:
    try:
        value = int(raw)
        if value < min_value:
            return min_value
        if value > max_value:
            return max_value
        return value
    except Exception:
        return fallback


def _coerce_float(raw: Any, fallback: float, min_value: float, max_value: float) -> float:
    try:
        value = float(raw)
        if value < min_value:
            return min_value
        if value > max_value:
            return max_value
        return value
    except Exception:
        return fallback


def load_fishing_config(raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = raw_config if isinstance(raw_config, dict) else _load_config_file()
    start_fishing_button = raw.get("start_fishing_button", raw.get("fishing_click_position"))
    auto_reconnect_enabled = bool(raw.get("auto_reconnect", False))
    fishing_failsafe_enabled = bool(raw.get("fishing_failsafe_rejoin", False)) and auto_reconnect_enabled
    movement_aura_name = str(raw.get("fishing_movement_aura_name", "")).strip()
    return {
        "fishing_bar_region": _coerce_region(raw.get("fishing_bar_region"), DEFAULT_FISHING_CONFIG["fishing_bar_region"]),
        "fishing_detect_pixel": _coerce_point(raw.get("fishing_detect_pixel"), DEFAULT_FISHING_CONFIG["fishing_detect_pixel"]),
        "fishing_click_position": _coerce_point(start_fishing_button, DEFAULT_FISHING_CONFIG["fishing_click_position"]),
        "fishing_midbar_sample_pos": _coerce_point(raw.get("fishing_midbar_sample_pos"), DEFAULT_FISHING_CONFIG["fishing_midbar_sample_pos"]),
        "fishing_close_button_pos": _coerce_point(raw.get("fishing_close_button_pos"), DEFAULT_FISHING_CONFIG["fishing_close_button_pos"]),
        "fishing_flarg_dialogue_box": _coerce_point(raw.get("fishing_flarg_dialogue_box"), DEFAULT_FISHING_CONFIG["fishing_flarg_dialogue_box"]),
        "fishing_shop_open_button": _coerce_point(raw.get("fishing_shop_open_button"), DEFAULT_FISHING_CONFIG["fishing_shop_open_button"]),
        "fishing_shop_sell_tab": _coerce_point(raw.get("fishing_shop_sell_tab"), DEFAULT_FISHING_CONFIG["fishing_shop_sell_tab"]),
        "fishing_shop_close_button": _coerce_point(raw.get("fishing_shop_close_button"), DEFAULT_FISHING_CONFIG["fishing_shop_close_button"]),
        "fishing_shop_first_fish": _coerce_point(raw.get("fishing_shop_first_fish"), DEFAULT_FISHING_CONFIG["fishing_shop_first_fish"]),
        "fishing_shop_sell_all_button": _coerce_point(raw.get("fishing_shop_sell_all_button"), DEFAULT_FISHING_CONFIG["fishing_shop_sell_all_button"]),
        "fishing_confirm_sell_all_button": _coerce_point(raw.get("fishing_confirm_sell_all_button"), DEFAULT_FISHING_CONFIG["fishing_confirm_sell_all_button"]),
        "collections_button": _coerce_point(raw.get("collections_button"), DEFAULT_FISHING_CONFIG["collections_button"]),
        "exit_collections_button": _coerce_point(raw.get("exit_collections_button"), DEFAULT_FISHING_CONFIG["exit_collections_button"]),
        "aura_menu": _coerce_point(raw.get("aura_menu"), DEFAULT_FISHING_CONFIG["aura_menu"]),
        "aura_search_bar": _coerce_point(raw.get("aura_search_bar"), DEFAULT_FISHING_CONFIG["aura_search_bar"]),
        "first_aura_slot_pos": _coerce_point(raw.get("first_aura_slot_pos"), DEFAULT_FISHING_CONFIG["first_aura_slot_pos"]),
        "equip_aura_button": _coerce_point(raw.get("equip_aura_button"), DEFAULT_FISHING_CONFIG["equip_aura_button"]),
        "inventory_close_button": _coerce_point(raw.get("inventory_close_button"), DEFAULT_FISHING_CONFIG["inventory_close_button"]),
        "fishing_failsafe_rejoin": fishing_failsafe_enabled,
        "fishing_enable_selling": bool(raw.get("fishing_enable_selling", False)),
        "fishing_sell_after_x_fish": _coerce_int(raw.get("fishing_sell_after_x_fish"), 30, 1, 100000),
        "fishing_sell_how_many_fish": _coerce_int(raw.get("fishing_sell_how_many_fish"), 1, 1, 100000),
        "fishing_equip_aura_before_movement": bool(raw.get("fishing_equip_aura_before_movement", False)),
        "fishing_movement_aura_name": movement_aura_name,
        "fishing_movement_aura_delay_seconds": _coerce_float(raw.get("fishing_movement_aura_delay_seconds"), 0.67, 0.1, 2.0),
        "merchant_teleporter": bool(raw.get("merchant_teleporter", False)),
        "fishing_use_merchant_every_x_fish": bool(raw.get("fishing_use_merchant_every_x_fish", False)),
        "fishing_merchant_every_x_fish": _coerce_int(raw.get("fishing_merchant_every_x_fish"), 30, 1, 100000),
        "fishing_use_merchant_ocr_every_x_fish": bool(raw.get("fishing_use_merchant_ocr_every_x_fish", False)),
        "fishing_merchant_ocr_every_x_fish_amt": _coerce_int(raw.get("fishing_merchant_ocr_every_x_fish_amt"), 30, 1, 100000),
        "fishing_use_br_sc_every_x_fish": bool(raw.get("fishing_use_br_sc_every_x_fish", False)),
        "fishing_br_sc_every_x_fish": _coerce_int(raw.get("fishing_br_sc_every_x_fish"), 30, 1, 100000),
        "fishing_actions_delay_ms": _coerce_int(raw.get("fishing_actions_delay_ms"), 100, 0, 5000),
        "fishing_playback_multiplier": _coerce_float(raw.get("fishing_playback_multiplier"), 1.0, 1.0, 2.0),
        "non_vip_movement_path": bool(raw.get("non_vip_movement_path", False)),
        "egg_ocr_detect_special": bool(raw.get("egg_ocr_detect_special", False)),
        # Performance tuning knobs (optional in config.json)
        "fishing_click_burst": _coerce_int(raw.get("fishing_click_burst"), 2, 1, 8),
        "fishing_reel_loop_sleep": _coerce_float(raw.get("fishing_reel_loop_sleep"), 0.004, 0.001, 0.03),
        "fishing_idle_poll_sleep": _coerce_float(raw.get("fishing_idle_poll_sleep"), 0.004, 0.001, 0.05),
        "fishing_pre_reel_wait": _coerce_float(raw.get("fishing_pre_reel_wait"), 0.18, 0.05, 0.5),
        "fishing_bar_color_tolerance": _coerce_int(raw.get("fishing_bar_color_tolerance"), 12, 3, 40),
        "fishing_bar_scan_height": _coerce_int(raw.get("fishing_bar_scan_height"), 3, 1, 30),
    }


def _get_fishing_actions_delay_seconds(cfg: dict[str, Any]) -> float:
    return _coerce_int(cfg.get("fishing_actions_delay_ms"), 100, 0, 5000) / 1000.0


def _get_pixel_rgb(x: int, y: int, sct: Any | None = None) -> tuple[int, int, int]:
    if sct is not None:
        try:
            shot = sct.grab({"left": int(x), "top": int(y), "width": 1, "height": 1})
            arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape((1, 1, 4))
            b, g, r = arr[0, 0, 0], arr[0, 0, 1], arr[0, 0, 2]
            return int(r), int(g), int(b)
        except Exception:
            pass
    pixel = pyautogui.screenshot(region=(x, y, 1, 1)).getpixel((0, 0))
    return int(pixel[0]), int(pixel[1]), int(pixel[2])


def _pick_scan_region(bar_region: tuple[int, int, int, int], scan_height: int) -> tuple[int, int, int, int]:
    x, y, w, h = bar_region
    sh = max(1, min(int(scan_height), max(1, int(h))))
    scan_y = y + max(0, (h - sh) // 2)
    return int(x), int(scan_y), int(w), int(sh)


def _grab_region_bgr(region: tuple[int, int, int, int], sct: Any | None = None) -> np.ndarray:
    x, y, w, h = region
    if sct is not None:
        try:
            shot = sct.grab({"left": int(x), "top": int(y), "width": int(w), "height": int(h)})
            arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape((int(h), int(w), 4))
            return arr[:, :, :3]
        except Exception:
            pass

    pil_img = pyautogui.screenshot(region=(int(x), int(y), int(w), int(h)))
    arr = np.array(pil_img)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def detect_colour(
    bar_color: tuple[int, int, int],
    bar_region: tuple[int, int, int, int],
    *,
    tolerance: int = 12,
    scan_height: int = 3,
    sct: Any | None = None,
) -> bool:
    scan_region = _pick_scan_region(bar_region, scan_height=scan_height)
    bgr = _grab_region_bgr(scan_region, sct=sct)
    lower_bound = np.array([
        max(0, bar_color[2] - tolerance),
        max(0, bar_color[1] - tolerance),
        max(0, bar_color[0] - tolerance)
    ])
    upper_bound = np.array([
        min(255, bar_color[2] + tolerance),
        min(255, bar_color[1] + tolerance),
        min(255, bar_color[0] + tolerance)
    ])
    mask = cv2.inRange(bgr, lower_bound, upper_bound)
    return bool(np.any(mask))


def is_indicator_active(pixel: tuple[int, ...], white_threshold: int = 250) -> bool:
    return len(pixel) >= 3 and pixel[0] >= white_threshold and pixel[1] >= white_threshold and pixel[2] >= white_threshold


def _to_autoit_key(key: str) -> str:
    norm = str(key or "").strip().lower()
    if not norm:
        return ""
    mapped = AUTOIT_KEY_MAP.get(norm)
    if mapped:
        return mapped
    if len(norm) == 1:
        if norm.isalpha():
            return norm.upper()
        return norm
    return norm.upper()


def _autoit_key_down(key: str) -> None:
    token = _to_autoit_key(key)
    if token:
        autoit.send(f"{{{token} down}}")


def _autoit_key_up(key: str) -> None:
    token = _to_autoit_key(key)
    if token:
        autoit.send(f"{{{token} up}}")


def _autoit_key_tap(key: str) -> None:
    token = _to_autoit_key(key)
    if not token:
        return
    if len(token) == 1 and token.isalnum():
        autoit.send(token.lower())
    else:
        autoit.send(f"{{{token}}}")


# NON-VIP MULTIPLIER
NON_VIP_WALK_SPEED_MULTIPLIER = 1.22
_MOVEMENT_KEYS = frozenset({"w", "a", "s", "d"})

def _run_recorded_events(
    *,
    events: list[dict[str, Any]],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    speed_multiplier: float = 1.0,
) -> bool:
    pressed_keys: set[str] = set()
    last_t = 0.0
    try:
        for ev in events:
            if not should_continue() or not can_run():
                return False

            t = float(ev.get("t", last_t))
            dt = t - last_t

            # normalize time between movement key events for non-VIP walk speed (i made it x1.22)
            if speed_multiplier > 1.0 and dt > 0:
                ev_key = str(ev.get("key", "")).lower().strip()
                ev_type = str(ev.get("type", ""))
                if ev_type in ("key_down", "key_up") and ev_key in _MOVEMENT_KEYS:
                    dt *= speed_multiplier

            if dt > 0 and not sleep_interruptible(dt, 0.01):
                return False

            typ = str(ev.get("type", ""))
            try:
                if typ == "mouse_move":
                    autoit.mouse_move(int(ev.get("x", 0)), int(ev.get("y", 0)), 0)
                elif typ == "mouse_down":
                    autoit.mouse_down(str(ev.get("button", "left")))
                elif typ == "mouse_up":
                    autoit.mouse_up(str(ev.get("button", "left")))
                elif typ == "mouse_wheel":
                    delta = int(ev.get("delta", 0))
                    if delta != 0:
                        autoit.mouse_wheel("up" if delta > 0 else "down", abs(delta))
                elif typ == "key_down":
                    k = str(ev.get("key", "")).lower().strip()
                    if k:
                        _autoit_key_down(k)
                        pressed_keys.add(k)
                elif typ == "key_up":
                    k = str(ev.get("key", "")).lower().strip()
                    if k:
                        _autoit_key_up(k)
                        pressed_keys.discard(k)
            except Exception:
                pass

            last_t = t
        return should_continue() and can_run()
    finally:
        for key_name in list(pressed_keys):
            try:
                _autoit_key_up(key_name)
            except Exception:
                pass

        for k in ("w", "a", "s", "d", "space"):
            try:
                _autoit_key_up(k)
            except Exception:
                pass
            time.sleep(0.02)


def _run_pre_fishing_sequence(
    *,
    cfg: dict[str, Any],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    activate_roblox_cb: Callable[[], None] | None = None,
    close_chat_fn: Callable[[], None] | None = None,
    egg_ocr_check_cb: Callable[[], None] | None = None,
) -> bool:
    if not should_continue() or not can_run():
        return False

    if egg_ocr_check_cb is not None and bool(cfg.get("egg_ocr_detect_special", False)):
        try:
            egg_ocr_check_cb()
            print("egg ocr check in fishing done")
        except Exception as e:
            print(f"[Fishing] egg_ocr_check_cb error: {e}")

    fishing_actions_delay = _get_fishing_actions_delay_seconds(cfg)
    if not _run_respawn_sequence(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        action_delay_seconds=fishing_actions_delay,
        activate_roblox_cb=activate_roblox_cb,
    ):
        return False

    # Close chat if open before clicking collection button
    if close_chat_fn is not None:
        try:
            print("[Fishing] Checking and closing chat if open...")
            close_chat_fn()
        except Exception as e:
            print(f"[Fishing] close_chat_fn error: {e}")
    if not sleep_interruptible(0.2 + fishing_actions_delay):
        return False

    collections_x, collections_y = cfg["collections_button"]
    if collections_x > 0:
        autoit.mouse_click("left", collections_x, collections_y, speed=3)
    if not sleep_interruptible(1.0 + fishing_actions_delay):
        return False

    exit_x, exit_y = cfg["exit_collections_button"]
    if exit_x > 0:
        autoit.mouse_click("left", exit_x, exit_y, speed=3)
    if not sleep_interruptible(0.2 + fishing_actions_delay):
        return False

    return sleep_interruptible(0.5 + fishing_actions_delay)


def _run_respawn_sequence(
    *,
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    action_delay_seconds: float = 0.0,
    activate_roblox_cb: Callable[[], None] | None = None,
) -> bool:
    if not should_continue() or not can_run():
        return False

    if activate_roblox_cb is not None:
        for _ in range(4):
            try:
                activate_roblox_cb()
            except Exception:
                pass
            if not sleep_interruptible(0.5 + action_delay_seconds):
                return False

    _autoit_key_tap("esc")
    if not sleep_interruptible(1.25 + action_delay_seconds):
        return False

    _autoit_key_tap("r")
    if not sleep_interruptible(0.75 + action_delay_seconds):
        return False

    _autoit_key_tap("enter")
    if not sleep_interruptible(5.5 + action_delay_seconds):
        return False

    return True


def _run_walk_to_fish_path(
    *,
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    speed_multiplier: float = 1.0,
) -> bool:
    if not WALK_TO_FISH_EVENTS:
        return False
    return _run_recorded_events(
        events=WALK_TO_FISH_EVENTS,
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        speed_multiplier=speed_multiplier,
    )


def _run_walk_to_sell_fish_path(
    *,
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    speed_multiplier: float = 1.0,
) -> bool:
    if not WALK_TO_SELL_FISH_EVENTS:
        return True
    return _run_recorded_events(
        events=WALK_TO_SELL_FISH_EVENTS,
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        speed_multiplier=speed_multiplier,
    )


def _run_equip_aura_before_movement(
    *,
    cfg: dict[str, Any],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
) -> bool:
    if not bool(cfg.get("fishing_equip_aura_before_movement", False)):
        return True

    aura_name = str(cfg.get("fishing_movement_aura_name", "")).strip()
    if not aura_name:
        return True

    if not should_continue() or not can_run():
        return False

    step_delay = float(cfg.get("fishing_movement_aura_delay_seconds", 0.67)) + _get_fishing_actions_delay_seconds(cfg)
    aura_menu_x, aura_menu_y = cfg["aura_menu"]
    aura_search_x, aura_search_y = cfg["aura_search_bar"]
    first_slot_x, first_slot_y = cfg["first_aura_slot_pos"]
    equip_x, equip_y = cfg["equip_aura_button"]
    close_x, close_y = cfg["inventory_close_button"]

    if aura_menu_x > 0:
        autoit.mouse_click("left", aura_menu_x, aura_menu_y, 1, speed=3)
    if not sleep_interruptible(step_delay):
        return False

    if aura_search_x > 0:
        autoit.mouse_click("left", aura_search_x, aura_search_y, 1, speed=3)
    if not sleep_interruptible(step_delay):
        return False

    try:
        _safe_type_text(aura_name, cfg)
    except Exception:
        pass
    if not sleep_interruptible(step_delay):
        return False

    _autoit_key_tap("enter")
    if not sleep_interruptible(step_delay):
        return False

    if first_slot_x > 0:
        autoit.mouse_move(first_slot_x, first_slot_y, speed=3)
        if not sleep_interruptible(step_delay): return False
        try:
            autoit.mouse_wheel("up", max(1, int(round(5000 / 120.0))))
        except Exception:
            pass
        if not sleep_interruptible(step_delay): return False
        autoit.mouse_click("left", first_slot_x, first_slot_y, 1, speed=3)


    if not sleep_interruptible(step_delay): return False

    if equip_x > 0:
        autoit.mouse_click("left", equip_x, equip_y, 1, speed=3)
    if not sleep_interruptible(step_delay):
        return False

    if close_x > 0:
        autoit.mouse_click("left", close_x, close_y, 1, speed=3)
        if not sleep_interruptible(step_delay):
            return False

    return True


def _run_sell_fish_sequence(
    *,
    cfg: dict[str, Any],
    fish_sell_count: int,
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    activate_roblox_cb: Callable[[], None] | None = None,
    close_chat_fn: Callable[[], None] | None = None,
    set_busy_cb: Callable[[bool], None] | None = None,
    egg_ocr_check_cb: Callable[[], None] | None = None,
) -> bool:
    if fish_sell_count <= 0:
        return True
    if set_busy_cb is not None:
        try:
            set_busy_cb(True)
        except Exception:
            pass

    if egg_ocr_check_cb is not None and bool(cfg.get("egg_ocr_detect_special", False)):
        try:
            egg_ocr_check_cb()
        except Exception as e:
            print(f"[Fishing] egg_ocr_check_cb error in sell sequence: {e}")

    fishing_actions_delay = _get_fishing_actions_delay_seconds(cfg)
    if not _run_respawn_sequence(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        action_delay_seconds=fishing_actions_delay,
        activate_roblox_cb=activate_roblox_cb,
    ):
        return False

    if close_chat_fn is not None:
        try:
            close_chat_fn()
        except Exception as e:
            print(f"[Fishing] close_chat_fn error before selling: {e}")
    if not sleep_interruptible(0.2 + fishing_actions_delay):
        return False

    collections_x, collections_y = cfg["collections_button"]
    if collections_x > 0:
        autoit.mouse_click("left", collections_x, collections_y, speed=3)
    if not sleep_interruptible(1.0 + fishing_actions_delay):
        return False

    exit_x, exit_y = cfg["exit_collections_button"]
    if exit_x > 0:
        autoit.mouse_click("left", exit_x, exit_y, speed=3)
    if not sleep_interruptible(0.2 + fishing_actions_delay):
        return False

    if not _run_equip_aura_before_movement(
        cfg=cfg,
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
    ):
        return False

    non_vip = bool(cfg.get("non_vip_movement_path", False))
    _walk_mult = NON_VIP_WALK_SPEED_MULTIPLIER if non_vip else 1.0
    _playback_mult = float(cfg.get("fishing_playback_multiplier", 1.0))
    _combined_multiplier = _walk_mult * _playback_mult
    if not _run_walk_to_sell_fish_path(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        speed_multiplier=_combined_multiplier,
    ):
        return False

    dialogue_x, dialogue_y = cfg["fishing_flarg_dialogue_box"]
    if dialogue_x > 0:
        autoit.mouse_click("left", dialogue_x, dialogue_y, 1, speed=3)
        if not sleep_interruptible(0.3 + fishing_actions_delay):
            return False

        if not sleep_interruptible(0.2 + fishing_actions_delay):
            return False
        autoit.mouse_click("left", dialogue_x, dialogue_y, 1, speed=3)
    if not sleep_interruptible(0.6 + fishing_actions_delay):
        return False

    shop_x, shop_y = cfg["fishing_shop_open_button"]
    if shop_x > 0:
        autoit.mouse_click("left", shop_x, shop_y, 1, speed=3)
    if not sleep_interruptible(1.5 + fishing_actions_delay):
        return False

    sell_tab_x, sell_tab_y = cfg["fishing_shop_sell_tab"]
    close_shop_x, close_shop_y = cfg["fishing_shop_close_button"]
    first_fish_x, first_fish_y = cfg["fishing_shop_first_fish"]
    sell_x, sell_y = cfg["fishing_shop_sell_all_button"]
    confirm_x, confirm_y = cfg["fishing_confirm_sell_all_button"]
    for _ in range(max(1, int(fish_sell_count))):
        if not should_continue() or not can_run():
            return False
        if sell_tab_x > 0:
            autoit.mouse_click("left", sell_tab_x, sell_tab_y, 1, speed=3)
        if not sleep_interruptible(0.3 + fishing_actions_delay):
            return False
        if first_fish_x > 0:
            autoit.mouse_click("left", first_fish_x, first_fish_y, 1, speed=3)
        if not sleep_interruptible(0.3 + fishing_actions_delay):
            return False
        if sell_x > 0:
            autoit.mouse_click("left", sell_x, sell_y, 1, speed=3)
        if not sleep_interruptible(0.3 + fishing_actions_delay):
            return False
        if confirm_x > 0:
            autoit.mouse_click("left", confirm_x, confirm_y, 1, speed=3)
        if not sleep_interruptible(1.5 + fishing_actions_delay):
            return False

    if close_shop_x > 0:
        autoit.mouse_click("left", close_shop_x, close_shop_y, 1, speed=3)
    if not sleep_interruptible(0.85 + fishing_actions_delay):
        return False

    if egg_ocr_check_cb is not None and bool(cfg.get("egg_ocr_detect_special", False)):
        try:
            egg_ocr_check_cb()
        except Exception as e:
            print(f"[Fishing] egg_ocr_check_cb error before final respawn: {e}")

    if not _run_respawn_sequence(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        action_delay_seconds=fishing_actions_delay,
        activate_roblox_cb=activate_roblox_cb,
    ):
        return False

    if not sleep_interruptible(0.2 + fishing_actions_delay):
        return False

    return True


def run_fishing_loop(
    *,
    stop_event: threading.Event | None = None,
    can_run_cb: Callable[[], bool] | None = None,
    config_provider: Callable[[], dict[str, Any]] | None = None,
    config_refresh_seconds: float = 2.0,
    log_prefix: str = "[Fishing]",
    print_start_stop: bool = True,
    on_failsafe_timeout: Callable[[], None] | None = None,
    run_br_sc_sequence_cb: Callable[[], bool] | None = None,
    run_merchant_sequence_cb: Callable[[], bool] | None = None,
    merchant_ocr_check_cb: Callable[[], None] | None = None,
    activate_roblox_cb: Callable[[], None] | None = None,
    close_chat_fn: Callable[[], None] | None = None,
    runtime_state: dict[str, Any] | None = None,
    set_fishing_busy_cb: Callable[[bool], None] | None = None,
    on_f2_pressed_cb: Callable[[], None] | None = None,
    egg_ocr_check_cb: Callable[[], None] | None = None,
) -> None:
    stop_event = stop_event or threading.Event()
    config_provider = config_provider or _load_config_file

    def _set_busy(busy: bool) -> None:
        if set_fishing_busy_cb is not None:
            try:
                set_fishing_busy_cb(busy)
            except Exception:
                pass

    def _notify_failsafe_timeout() -> None:
        if on_failsafe_timeout is None:
            return
        try:
            on_failsafe_timeout()
        except Exception:
            pass

    def _run_br_sc_sequence() -> bool:
        if run_br_sc_sequence_cb is None:
            return False
        try:
            return bool(run_br_sc_sequence_cb())
        except Exception:
            return False

    def _run_merchant_sequence() -> bool:
        if run_merchant_sequence_cb is None:
            return False
        try:
            return bool(run_merchant_sequence_cb())
        except Exception:
            return False

    def _should_continue() -> bool:
        return not stop_event.is_set()

    def _can_run() -> bool:
        if can_run_cb is None:
            return True
        try:
            return bool(can_run_cb())
        except Exception:
            return False

    def _sleep_interruptible(seconds: float, poll: float = 0.02) -> bool:
        end = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < end:
            if not _should_continue() or not _can_run():
                return False
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll, remaining))
        return _should_continue() and _can_run()

    def _get_due_actions() -> tuple[bool, int, bool, bool, bool]:
        sell_after = max(1, int(cfg.get("fishing_sell_after_x_fish", 30)))
        should_sell = bool(cfg.get("fishing_enable_selling", False)) and (fish_caught_count >= sell_after)
        sell_count = max(1, int(cfg.get("fishing_sell_how_many_fish", 1)))

        use_merchant_every_x = bool(cfg.get("fishing_use_merchant_every_x_fish", False))
        merchant_after = max(1, int(cfg.get("fishing_merchant_every_x_fish", 30)))
        should_use_merchant = use_merchant_every_x and (fish_caught_since_merchant >= merchant_after)

        use_merchant_ocr_every_x = bool(cfg.get("fishing_use_merchant_ocr_every_x_fish", False))
        merchant_ocr_after = max(1, int(cfg.get("fishing_merchant_ocr_every_x_fish_amt", 30)))
        should_use_merchant_ocr = use_merchant_ocr_every_x and (fish_caught_since_merchant_ocr >= merchant_ocr_after)

        use_br_sc_every_x = bool(cfg.get("fishing_use_br_sc_every_x_fish", False))
        br_sc_after = max(1, int(cfg.get("fishing_br_sc_every_x_fish", 30)))
        should_use_br_sc = use_br_sc_every_x and (fish_caught_since_br_sc >= br_sc_after)

        return should_sell, sell_count, should_use_merchant, should_use_br_sc, should_use_merchant_ocr

    cfg = load_fishing_config(config_provider())
    next_cfg_refresh_at = time.monotonic()
    was_runnable = False

    runtime_state_dict = runtime_state if isinstance(runtime_state, dict) else None

    def _state_counter(name: str) -> int:
        if runtime_state_dict is None:
            return 0
        try:
            value = int(runtime_state_dict.get(name, 0))
            return value if value >= 0 else 0
        except Exception:
            return 0

    def _state_flag(name: str) -> bool:
        if runtime_state_dict is None:
            return False
        try:
            return bool(runtime_state_dict.get(name, False))
        except Exception:
            return False

    def _set_state_flag(name: str, value: bool) -> None:
        if runtime_state_dict is None:
            return
        runtime_state_dict[name] = bool(value)

    def _consume_state_flag(name: str) -> bool:
        value = _state_flag(name)
        _set_state_flag(name, False)
        return value

    def _run_merchant_sequence_with_state() -> tuple[bool, bool]:
        ran = _run_merchant_sequence()
        return ran, _consume_state_flag("merchant_requires_reset")

    fish_caught_count = _state_counter("fish_caught_count")
    fish_caught_since_merchant = _state_counter("fish_caught_since_merchant")
    fish_caught_since_merchant_ocr = _state_counter("fish_caught_since_merchant_ocr")
    fish_caught_since_br_sc = _state_counter("fish_caught_since_br_sc")
    _set_state_flag("merchant_requires_reset", False)

    def _persist_runtime_counters() -> None:
        if runtime_state_dict is None:
            return
        runtime_state_dict["fish_caught_count"] = max(0, int(fish_caught_count))
        runtime_state_dict["fish_caught_since_merchant"] = max(0, int(fish_caught_since_merchant))
        runtime_state_dict["fish_caught_since_merchant_ocr"] = max(0, int(fish_caught_since_merchant_ocr))
        runtime_state_dict["fish_caught_since_br_sc"] = max(0, int(fish_caught_since_br_sc))

    _persist_runtime_counters()

    last_start_fishing_click_at: float | None = None
    sct = None
    if mss is not None:
        try:
            sct = mss.mss()
        except Exception:
            sct = None

    if print_start_stop:
        print(f"{log_prefix} started")
        print(f"{log_prefix} using calibration: {cfg}")
        print(
            f"{log_prefix} session fish counters: total={fish_caught_count}, "
            f"merchant={fish_caught_since_merchant}, br_sc={fish_caught_since_br_sc}"
        )

    try:
        while _should_continue():
            now = time.monotonic()
            if now >= next_cfg_refresh_at:
                try:
                    cfg = load_fishing_config(config_provider())
                except Exception:
                    cfg = load_fishing_config()
                next_cfg_refresh_at = now + max(0.2, float(config_refresh_seconds))

            if not _can_run():
                _set_busy(False)
                was_runnable = False
                last_start_fishing_click_at = None
                time.sleep(0.05)
                continue

            if not was_runnable:
                _set_busy(True)
                if close_chat_fn is not None:
                    try:
                        close_chat_fn()
                    except Exception as e:
                        print(f"{log_prefix} close_chat_fn error on resume: {e}")

                if _state_flag("force_sell_on_next_cycle"):
                    _set_state_flag("force_sell_on_next_cycle", False)
                    force_sell_count = max(1, int(cfg.get("fishing_sell_how_many_fish", 1)))
                    print(
                        f"{log_prefix} rejoin completed; forced selling flow before fishing path "
                        f"(selling {force_sell_count} fish)."
                    )
                    if not _run_sell_fish_sequence(
                        cfg=cfg,
                        fish_sell_count=force_sell_count,
                        sleep_interruptible=_sleep_interruptible,
                        should_continue=_should_continue,
                        can_run=_can_run,
                        activate_roblox_cb=activate_roblox_cb,
                        close_chat_fn=close_chat_fn,
                        set_busy_cb=_set_busy,
                        egg_ocr_check_cb=egg_ocr_check_cb,
                    ):
                        continue
                    fish_caught_count = 0
                    _persist_runtime_counters()
                    last_start_fishing_click_at = None
                    was_runnable = False
                    continue

                should_sell, sell_count, should_use_merchant, should_use_br_sc, should_use_merchant_ocr = _get_due_actions()

                if should_sell:
                    print(
                        f"{log_prefix} pending selling flow triggered before fishing path "
                        f"after {fish_caught_count} catches (selling {sell_count} fish)."
                    )
                    if not _run_sell_fish_sequence(
                        cfg=cfg,
                        fish_sell_count=sell_count,
                        sleep_interruptible=_sleep_interruptible,
                        should_continue=_should_continue,
                        can_run=_can_run,
                        activate_roblox_cb=activate_roblox_cb,
                        close_chat_fn=close_chat_fn,
                        set_busy_cb=_set_busy,
                        egg_ocr_check_cb=egg_ocr_check_cb,
                    ):
                        continue
                    fish_caught_count = 0
                    _persist_runtime_counters()

                    # Re-evaluate counters after selling because merchant/BRSC counters are independent.
                    _, _, should_use_merchant, should_use_br_sc, should_use_merchant_ocr = _get_due_actions()

                    if should_use_merchant:
                        print(f"{log_prefix} merchant flow triggered after pending selling.")
                        merchant_ran, _ = _run_merchant_sequence_with_state()
                        if merchant_ran:
                            fish_caught_since_merchant = 0
                        _persist_runtime_counters()
                        if not merchant_ran:
                            print(f"{log_prefix} merchant flow skipped/failed during fishing.")
                            
                    if should_use_merchant_ocr and merchant_ocr_check_cb is not None:
                        print(f"{log_prefix} merchant OCR triggered after pending selling.")
                        try:
                            _set_busy(True)
                            merchant_ocr_check_cb()
                        except Exception as e:
                            print(f"{log_prefix} merchant OCR check failure: {e}")
                        finally:
                            _set_busy(False)
                            fish_caught_since_merchant_ocr = 0
                            _persist_runtime_counters()

                    if should_use_br_sc:
                        print(f"{log_prefix} BR/SC flow triggered after pending selling.")
                        br_sc_ran = _run_br_sc_sequence()
                        if br_sc_ran:
                            fish_caught_since_br_sc = 0
                        _persist_runtime_counters()

                    last_start_fishing_click_at = None
                    was_runnable = False
                    continue

                if should_use_merchant:
                    print(
                        f"{log_prefix} pending merchant flow triggered before fishing path "
                        f"after {fish_caught_since_merchant} catches."
                    )
                    merchant_ran, _ = _run_merchant_sequence_with_state()
                    if merchant_ran:
                        fish_caught_since_merchant = 0
                    _persist_runtime_counters()
                    if not merchant_ran:
                        print(f"{log_prefix} merchant flow skipped/failed during fishing.")

                    if should_use_br_sc:
                        print(f"{log_prefix} BR/SC flow triggered after pending merchant.")
                        br_sc_ran = _run_br_sc_sequence()
                        if br_sc_ran:
                            fish_caught_since_br_sc = 0
                        _persist_runtime_counters()

                    last_start_fishing_click_at = None
                    was_runnable = False
                    continue
                    
                if should_use_merchant_ocr and merchant_ocr_check_cb is not None:
                    print(
                        f"{log_prefix} pending merchant OCR flow triggered before fishing path "
                        f"after {fish_caught_since_merchant_ocr} catches."
                    )
                    try:
                        _set_busy(True)
                        merchant_ocr_check_cb()
                    except Exception as e:
                        print(f"{log_prefix} merchant OCR check failure: {e}")
                    finally:
                        _set_busy(False)
                        fish_caught_since_merchant_ocr = 0
                        _persist_runtime_counters()
                        
                        
                    if should_use_br_sc:
                        print(f"{log_prefix} BR/SC flow triggered after merchant OCR.")
                        br_sc_ran = _run_br_sc_sequence()
                        if br_sc_ran:
                            fish_caught_since_br_sc = 0
                        _persist_runtime_counters()

                    last_start_fishing_click_at = None
                    was_runnable = False
                    continue

                if should_use_br_sc:
                    print(
                        f"{log_prefix} pending BR/SC flow triggered before fishing path "
                        f"after {fish_caught_since_br_sc} catches."
                    )
                    br_sc_ran = _run_br_sc_sequence()
                    if br_sc_ran:
                        fish_caught_since_br_sc = 0
                    _persist_runtime_counters()

                    last_start_fishing_click_at = None
                    was_runnable = False
                    continue

                if not _run_pre_fishing_sequence(
                    cfg=cfg,
                    sleep_interruptible=_sleep_interruptible,
                    should_continue=_should_continue,
                    can_run=_can_run,
                    activate_roblox_cb=activate_roblox_cb,
                    close_chat_fn=close_chat_fn,
                    egg_ocr_check_cb=egg_ocr_check_cb,
                ):
                    continue
                if not _run_equip_aura_before_movement(
                    cfg=cfg,
                    sleep_interruptible=_sleep_interruptible,
                    should_continue=_should_continue,
                    can_run=_can_run,
                ):
                    continue
                _non_vip = bool(cfg.get("non_vip_movement_path", False))
                _walk_multiplier = NON_VIP_WALK_SPEED_MULTIPLIER if _non_vip else 1.0
                _playback_mult = float(cfg.get("fishing_playback_multiplier", 1.0))
                _combined_multiplier = _walk_multiplier * _playback_mult
                if not _run_walk_to_fish_path(
                    sleep_interruptible=_sleep_interruptible,
                    should_continue=_should_continue,
                    can_run=_can_run,
                    speed_multiplier=_combined_multiplier,
                ):
                    continue
                
                close_x, close_y = cfg["fishing_close_button_pos"]
                for _ in range(3):
                    autoit.mouse_click("left", close_x, close_y, speed=3)
                    if not _sleep_interruptible(0.15): break
                if not _sleep_interruptible(0.3): continue

                click_x, click_y = cfg["fishing_click_position"]
                autoit.mouse_click("left", click_x, click_y, speed=3)
                last_start_fishing_click_at = time.monotonic()
                if not _sleep_interruptible(0.25): continue
                was_runnable = True
                _set_busy(False)

            if (
                was_runnable
                and bool(cfg.get("fishing_failsafe_rejoin", False))
                and last_start_fishing_click_at is not None
                and (time.monotonic() - float(last_start_fishing_click_at)) >= 60.0
            ):
                print(f"{log_prefix} failsafe triggered: no minigame detected for >=60s. Closing Roblox.")
                _notify_failsafe_timeout()
                was_runnable = False
                last_start_fishing_click_at = None
                continue

            detect_x, detect_y = cfg["fishing_detect_pixel"]
            pixel = _get_pixel_rgb(detect_x, detect_y, sct=sct)
            if not is_indicator_active(pixel):
                time.sleep(float(cfg.get("fishing_idle_poll_sleep", 0.004)))
                continue

            _set_busy(True)
            click_x, click_y = cfg["fishing_click_position"]
            autoit.mouse_click("left", click_x, click_y, speed=3)
            last_start_fishing_click_at = time.monotonic()
            if not _sleep_interruptible(float(cfg.get("fishing_pre_reel_wait", 0.18))):
                continue

            if not _should_continue() or not _can_run():
                continue

            midbar_x, midbar_y = cfg["fishing_midbar_sample_pos"]
            bar_color = _get_pixel_rgb(midbar_x, midbar_y, sct=sct)
            start_time = time.time()

            while (time.time() - start_time) < 9:
                if not _should_continue() or not _can_run():
                    break
                found = detect_colour(
                    bar_color,
                    cfg["fishing_bar_region"],
                    tolerance=int(cfg.get("fishing_bar_color_tolerance", 12)),
                    scan_height=int(cfg.get("fishing_bar_scan_height", 3)),
                    sct=sct,
                )
                if not found:
                    click_burst = int(cfg.get("fishing_click_burst", 2))
                    for i in range(max(1, click_burst)):
                        autoit.mouse_click("left", click_x, click_y, speed=3)
                        if i + 1 < click_burst and not _sleep_interruptible(0.001):
                            break
                time.sleep(float(cfg.get("fishing_reel_loop_sleep", 0.004)))

            if not _should_continue() or not _can_run():
                continue

            if not _sleep_interruptible(1.0):
                continue

            close_x, close_y = cfg["fishing_close_button_pos"]
            for _ in range(5):
                autoit.mouse_click("left", close_x, close_y, speed=3)
                if not _sleep_interruptible(0.55):
                    break

            fish_caught_count += 1
            fish_caught_since_merchant += 1
            fish_caught_since_merchant_ocr += 1
            fish_caught_since_br_sc += 1
            _persist_runtime_counters()

            _set_busy(False)
            if not _sleep_interruptible(0.42): continue
            _set_busy(True)

            if not _should_continue() or not _can_run():
                continue

            use_merchant_every_x = bool(cfg.get("fishing_use_merchant_every_x_fish", False))
            merchant_after = max(1, int(cfg.get("fishing_merchant_every_x_fish", 30)))
            should_use_merchant = use_merchant_every_x and (fish_caught_since_merchant >= merchant_after)

            use_merchant_ocr_every_x = bool(cfg.get("fishing_use_merchant_ocr_every_x_fish", False))
            merchant_ocr_after = max(1, int(cfg.get("fishing_merchant_ocr_every_x_fish_amt", 30)))
            should_use_merchant_ocr = use_merchant_ocr_every_x and (fish_caught_since_merchant_ocr >= merchant_ocr_after)

            use_br_sc_every_x = bool(cfg.get("fishing_use_br_sc_every_x_fish", False))
            br_sc_after = max(1, int(cfg.get("fishing_br_sc_every_x_fish", 30)))
            should_use_br_sc = use_br_sc_every_x and (fish_caught_since_br_sc >= br_sc_after)

            if bool(cfg.get("fishing_enable_selling", False)):
                sell_after = int(cfg.get("fishing_sell_after_x_fish", 30))
                sell_count = int(cfg.get("fishing_sell_how_many_fish", 1))
                if fish_caught_count >= max(1, sell_after):
                    _set_busy(True)
                    print(
                        f"{log_prefix} selling flow triggered after {fish_caught_count} catches "
                        f"(selling {max(1, sell_count)} fish)."
                    )
                    if not _run_sell_fish_sequence(
                        cfg=cfg,
                        fish_sell_count=max(1, sell_count),
                        sleep_interruptible=_sleep_interruptible,
                        should_continue=_should_continue,
                        can_run=_can_run,
                        activate_roblox_cb=activate_roblox_cb,
                        close_chat_fn=close_chat_fn,
                        set_busy_cb=_set_busy,
                    ):
                        continue
                    fish_caught_count = 0
                    _persist_runtime_counters()

                    if should_use_merchant:
                        print(f"{log_prefix} merchant flow triggered after selling.")
                        merchant_ran, _ = _run_merchant_sequence_with_state()
                        if merchant_ran:
                            fish_caught_since_merchant = 0
                        _persist_runtime_counters()
                        if not merchant_ran:
                            print(f"{log_prefix} merchant flow skipped/failed during fishing.")

                    if should_use_merchant_ocr and merchant_ocr_check_cb is not None:
                        print(f"{log_prefix} merchant OCR triggered after selling.")
                        try:
                            merchant_ocr_check_cb()
                        except Exception as e:
                            print(f"{log_prefix} merchant OCR check failure: {e}")
                        finally:
                            fish_caught_since_merchant_ocr = 0
                            _persist_runtime_counters()

                    if should_use_br_sc:
                        print(f"{log_prefix} BR/SC flow triggered after selling.")
                        br_sc_ran = _run_br_sc_sequence()
                        if br_sc_ran:
                            fish_caught_since_br_sc = 0
                        _persist_runtime_counters()

                    was_runnable = False
                    last_start_fishing_click_at = None
                    _set_busy(False)
                    continue

            if should_use_merchant:
                print(f"{log_prefix} merchant flow triggered after {fish_caught_since_merchant} catches.")
                merchant_ran, merchant_requires_reset = _run_merchant_sequence_with_state()
                if merchant_ran:
                    fish_caught_since_merchant = 0
                _persist_runtime_counters()
                if not merchant_ran:
                    print(f"{log_prefix} merchant flow skipped/failed during fishing.")

                if should_use_merchant_ocr and merchant_ocr_check_cb is not None:
                    print(f"{log_prefix} merchant OCR triggered after merchant flow.")
                    try:
                        merchant_ocr_check_cb()
                    except Exception as e:
                        print(f"{log_prefix} merchant OCR check failure: {e}")
                    finally:
                        fish_caught_since_merchant_ocr = 0
                        _persist_runtime_counters()

                if should_use_br_sc:
                    print(f"{log_prefix} BR/SC flow triggered after merchant.")
                    br_sc_ran = _run_br_sc_sequence()
                    if br_sc_ran:
                        fish_caught_since_br_sc = 0
                    should_use_br_sc = False
                    _persist_runtime_counters()

                if merchant_requires_reset:
                    if not _sleep_interruptible(0.4 + _get_fishing_actions_delay_seconds(cfg)):
                        continue
                    was_runnable = False
                    last_start_fishing_click_at = None
                    continue

            if should_use_merchant_ocr and merchant_ocr_check_cb is not None:
                print(f"{log_prefix} merchant OCR triggered after {fish_caught_since_merchant_ocr} catches.")
                try:
                    merchant_ocr_check_cb()
                except Exception as e:
                    print(f"{log_prefix} merchant OCR check failure: {e}")
                finally:
                    fish_caught_since_merchant_ocr = 0
                    _persist_runtime_counters()

            if should_use_br_sc:
                print(f"{log_prefix} BR/SC flow triggered after {fish_caught_since_br_sc} catches.")
                br_sc_ran = _run_br_sc_sequence()
                if br_sc_ran:
                    fish_caught_since_br_sc = 0
                _persist_runtime_counters()

            start_x, start_y = cfg["fishing_click_position"]
            autoit.mouse_click("left", start_x, start_y, speed=3)
            last_start_fishing_click_at = time.monotonic()
            _sleep_interruptible(0.3)
            _set_busy(False)
    finally:
        _set_busy(False)
        
        for k in ("w", "a", "s", "d", "space"):
            try:
                _autoit_key_up(k)
            except Exception:
                pass
            
        if sct is not None:
            try:
                sct.close()
            except Exception:
                pass
        if print_start_stop:
            print(f"{log_prefix} stopped")

def main():
    try:
        run_fishing_loop()
    except KeyboardInterrupt:
        print("[Fishing] stopped by keynboard interrupt")


if __name__ == "__main__":
    main()

print("Sven is sick") 