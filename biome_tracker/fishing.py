import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

import autoit
import cv2
import numpy as np
import pyautogui
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

WALK_TO_FISH_EVENTS: list[dict[str, Any]] = [{"type":"key_down","x":0,"y":0,"button":"","key":"w","delta":0,"t":0.7391250133514404},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":0.741126298904419},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":0.9960780143737793},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.026473045349121},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.0575404167175293},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.1038482189178467},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.1342198848724365},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.165168046951294},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.1959125995635986},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.226245641708374},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.2579402923583984},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.2890980243682861},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.3357858657836914},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.3669459819793701},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.3978071212768555},{"type":"key_down","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.4294638633728027},{"type":"key_up","x":0,"y":0,"button":"","key":"a","delta":0,"t":1.4381849765777588},{"type":"key_up","x":0,"y":0,"button":"","key":"w","delta":0,"t":8.1}]
WALK_TO_SELL_FISH_EVENTS: list[dict[str, Any]] = [{"t": 0.7601381999998011, "type": "key_down", "key": "a"}, {"t": 0.7842182999997931, "type": "key_down", "key": "w"}, {"t": 1.0363115999998627, "type": "key_down", "key": "w"}, {"t": 1.067316000000119, "type": "key_down", "key": "w"}, {"t": 1.1015920999998343, "type": "key_down", "key": "w"}, {"t": 1.1328125, "type": "key_down", "key": "w"}, {"t": 1.1639445000000705, "type": "key_down", "key": "w"}, {"t": 1.1954338999998981, "type": "key_down", "key": "w"}, {"t": 1.2264741999997568, "type": "key_down", "key": "w"}, {"t": 1.2577430999999706, "type": "key_down", "key": "w"}, {"t": 1.2888695999999982, "type": "key_down", "key": "w"}, {"t": 1.3201469000000543, "type": "key_down", "key": "w"}, {"t": 1.3512931000000208, "type": "key_down", "key": "w"}, {"t": 1.3824859000001197, "type": "key_down", "key": "w"}, {"t": 1.4136951999998928, "type": "key_down", "key": "w"}, {"t": 1.4449092999998356, "type": "key_down", "key": "w"}, {"t": 1.4761288999998214, "type": "key_down", "key": "w"}, {"t": 1.507334599999922, "type": "key_down", "key": "w"}, {"t": 1.5385197999999036, "type": "key_down", "key": "w"}, {"t": 1.5698959999999715, "type": "key_down", "key": "w"}, {"t": 1.6059064000000944, "type": "key_down", "key": "w"}, {"t": 1.6352836000000934, "type": "key_down", "key": "w"}, {"t": 1.6665265999999974, "type": "key_down", "key": "w"}, {"t": 1.70045059999984, "type": "key_down", "key": "w"}, {"t": 1.7289937000000464, "type": "key_down", "key": "w"}, {"t": 1.7602068000001054, "type": "key_down", "key": "w"}, {"t": 1.791372599999704, "type": "key_down", "key": "w"}, {"t": 1.822637499999928, "type": "key_down", "key": "w"}, {"t": 1.853939199999786, "type": "key_down", "key": "w"}, {"t": 1.8850296999999046, "type": "key_down", "key": "w"}, {"t": 1.9168245999999272, "type": "key_down", "key": "w"}, {"t": 1.9474374000001262, "type": "key_down", "key": "w"}, {"t": 1.9787836000000425, "type": "key_down", "key": "w"}, {"t": 2.01031759999978, "type": "key_down", "key": "w"}, {"t": 2.0412163999999393, "type": "key_down", "key": "w"}, {"t": 2.0724832999999308, "type": "key_down", "key": "w"}, {"t": 2.107405799999924, "type": "key_down", "key": "w"}, {"t": 2.137988999999834, "type": "key_down", "key": "w"}, {"t": 2.169086899999911, "type": "key_down", "key": "w"}, {"t": 2.2003381999998055, "type": "key_down", "key": "w"}, {"t": 2.2315911999999116, "type": "key_down", "key": "w"}, {"t": 2.2630903999997827, "type": "key_down", "key": "w"}, {"t": 2.294365799999923, "type": "key_down", "key": "w"}, {"t": 2.3252253000000564, "type": "key_down", "key": "w"}, {"t": 2.3566092999999455, "type": "key_down", "key": "w"}, {"t": 2.3876694999999017, "type": "key_down", "key": "w"}, {"t": 2.4188819999999396, "type": "key_down", "key": "w"}, {"t": 2.4500864999999976, "type": "key_down", "key": "w"}, {"t": 2.4813521999999466, "type": "key_down", "key": "w"}, {"t": 2.512524299999768, "type": "key_down", "key": "w"}, {"t": 2.5439108999999007, "type": "key_down", "key": "w"}, {"t": 2.5749095000001034, "type": "key_down", "key": "w"}, {"t": 2.6062675999996827, "type": "key_down", "key": "w"}, {"t": 2.6405697000000146, "type": "key_down", "key": "w"}, {"t": 2.6716897999999674, "type": "key_down", "key": "w"}, {"t": 2.704398399999718, "type": "key_down", "key": "w"}, {"t": 2.7340863999997964, "type": "key_down", "key": "w"}, {"t": 2.765443899999809, "type": "key_down", "key": "w"}, {"t": 2.7964366000001064, "type": "key_down", "key": "w"}, {"t": 2.82771270000012, "type": "key_down", "key": "w"}, {"t": 2.8589028000001235, "type": "key_down", "key": "w"}, {"t": 2.8902656000000206, "type": "key_down", "key": "w"}, {"t": 2.9216093, "type": "key_down", "key": "w"}, {"t": 2.952592199999799, "type": "key_down", "key": "w"}, {"t": 2.9838534999998956, "type": "key_down", "key": "w"}, {"t": 3.015107100000023, "type": "key_down", "key": "w"}, {"t": 3.0463039000001118, "type": "key_down", "key": "w"}, {"t": 3.0774164999997993, "type": "key_down", "key": "w"}, {"t": 3.1087432999997873, "type": "key_down", "key": "w"}, {"t": 3.1430233999999473, "type": "key_down", "key": "w"}, {"t": 3.1740783000000192, "type": "key_down", "key": "w"}, {"t": 3.2055442999999286, "type": "key_down", "key": "w"}, {"t": 3.2368020999997498, "type": "key_down", "key": "w"}, {"t": 3.267803400000048, "type": "key_down", "key": "w"}, {"t": 3.299095899999884, "type": "key_down", "key": "w"}, {"t": 3.330477299999984, "type": "key_down", "key": "w"}, {"t": 3.3614536000000044, "type": "key_down", "key": "w"}, {"t": 3.3927749999998014, "type": "key_down", "key": "w"}, {"t": 3.423887999999806, "type": "key_down", "key": "w"}, {"t": 3.4550469000000703, "type": "key_down", "key": "w"}, {"t": 3.4864081000000624, "type": "key_down", "key": "w"}, {"t": 3.517494700000043, "type": "key_down", "key": "w"}, {"t": 3.5487770999998247, "type": "key_down", "key": "w"}, {"t": 3.580250199999682, "type": "key_down", "key": "w"}, {"t": 3.611217199999828, "type": "key_down", "key": "w"}, {"t": 3.645394899999701, "type": "key_down", "key": "w"}, {"t": 3.6765904999997474, "type": "key_down", "key": "w"}, {"t": 3.7077934999997524, "type": "key_down", "key": "w"}, {"t": 3.739939999999933, "type": "key_down", "key": "w"}, {"t": 3.7703520000000026, "type": "key_down", "key": "w"}, {"t": 3.80170279999993, "type": "key_down", "key": "w"}, {"t": 3.8330520999998043, "type": "key_down", "key": "w"}, {"t": 3.8641362999997, "type": "key_down", "key": "w"}, {"t": 3.8953937000001133, "type": "key_down", "key": "w"}, {"t": 3.926548399999774, "type": "key_down", "key": "w"}, {"t": 3.957738199999767, "type": "key_down", "key": "w"}, {"t": 3.989611999999852, "type": "key_down", "key": "w"}, {"t": 4.020176300000003, "type": "key_down", "key": "w"}, {"t": 4.053299499999866, "type": "key_down", "key": "w"}, {"t": 4.082598799999687, "type": "key_down", "key": "w"}, {"t": 4.113801200000125, "type": "key_down", "key": "w"}, {"t": 4.148030199999994, "type": "key_down", "key": "w"}, {"t": 4.179310399999849, "type": "key_down", "key": "w"}, {"t": 4.210490399999799, "type": "key_down", "key": "w"}, {"t": 4.242093699999714, "type": "key_down", "key": "w"}, {"t": 4.272867000000133, "type": "key_down", "key": "w"}, {"t": 4.304446000000098, "type": "key_down", "key": "w"}, {"t": 4.3357600999997885, "type": "key_down", "key": "w"}, {"t": 4.366595599999982, "type": "key_down", "key": "w"}, {"t": 4.397742799999833, "type": "key_down", "key": "w"}, {"t": 4.428999799999929, "type": "key_down", "key": "w"}, {"t": 4.460248599999886, "type": "key_down", "key": "w"}, {"t": 4.491414300000088, "type": "key_down", "key": "w"}, {"t": 4.5226598999997805, "type": "key_down", "key": "w"}, {"t": 4.5538330999997925, "type": "key_down", "key": "w"}, {"t": 4.585090600000058, "type": "key_down", "key": "w"}, {"t": 4.616376999999829, "type": "key_down", "key": "w"}, {"t": 4.65067369999997, "type": "key_down", "key": "w"}, {"t": 4.682012499999928, "type": "key_down", "key": "w"}, {"t": 4.713172400000076, "type": "key_down", "key": "w"}, {"t": 4.744273299999804, "type": "key_down", "key": "w"}, {"t": 4.7754839999997785, "type": "key_down", "key": "w"}, {"t": 4.806706800000029, "type": "key_down", "key": "w"}, {"t": 4.837829799999781, "type": "key_down", "key": "w"}, {"t": 4.869063399999959, "type": "key_down", "key": "w"}, {"t": 4.900259099999857, "type": "key_down", "key": "w"}, {"t": 4.931795200000124, "type": "key_down", "key": "w"}, {"t": 4.962668599999688, "type": "key_down", "key": "w"}, {"t": 4.99392429999989, "type": "key_down", "key": "w"}, {"t": 5.025165999999899, "type": "key_down", "key": "w"}, {"t": 5.056664799999908, "type": "key_down", "key": "w"}, {"t": 5.087528499999735, "type": "key_down", "key": "w"}, {"t": 5.118816700000025, "type": "key_down", "key": "w"}, {"t": 5.15316810000013, "type": "key_down", "key": "w"}, {"t": 5.184209199999714, "type": "key_down", "key": "w"}, {"t": 5.215567499999906, "type": "key_down", "key": "w"}, {"t": 5.246742699999686, "type": "key_down", "key": "w"}, {"t": 5.277905999999803, "type": "key_down", "key": "w"}, {"t": 5.309245800000099, "type": "key_down", "key": "w"}, {"t": 5.340620299999955, "type": "key_down", "key": "w"}, {"t": 5.371710500000063, "type": "key_down", "key": "w"}, {"t": 5.40336649999972, "type": "key_down", "key": "w"}, {"t": 5.434131499999694, "type": "key_down", "key": "w"}, {"t": 5.465360299999702, "type": "key_down", "key": "w"}, {"t": 5.496689099999912, "type": "key_down", "key": "w"}, {"t": 5.528037099999892, "type": "key_down", "key": "w"}, {"t": 5.5591724000000795, "type": "key_down", "key": "w"}, {"t": 5.590299099999811, "type": "key_down", "key": "w"}, {"t": 5.621596699999827, "type": "key_down", "key": "w"}, {"t": 5.65560269999969, "type": "key_down", "key": "w"}, {"t": 5.688982899999701, "type": "key_down", "key": "w"}, {"t": 5.720224199999848, "type": "key_down", "key": "w"}, {"t": 5.75156909999987, "type": "key_down", "key": "w"}, {"t": 5.782735299999786, "type": "key_down", "key": "w"}, {"t": 5.813756099999864, "type": "key_down", "key": "w"}, {"t": 5.845134400000006, "type": "key_down", "key": "w"}, {"t": 5.876195699999698, "type": "key_down", "key": "w"}, {"t": 5.907465400000092, "type": "key_down", "key": "w"}, {"t": 5.938790799999879, "type": "key_down", "key": "w"}, {"t": 5.970230899999933, "type": "key_down", "key": "w"}, {"t": 6.001437299999907, "type": "key_down", "key": "w"}, {"t": 6.032312399999682, "type": "key_down", "key": "w"}, {"t": 6.063477799999873, "type": "key_down", "key": "w"}, {"t": 6.094779799999742, "type": "key_down", "key": "w"}, {"t": 6.126174600000013, "type": "key_down", "key": "w"}, {"t": 6.160622200000034, "type": "key_down", "key": "w"}, {"t": 6.191741300000103, "type": "key_down", "key": "w"}, {"t": 6.223750999999993, "type": "key_down", "key": "w"}, {"t": 6.255407699999978, "type": "key_down", "key": "w"}, {"t": 6.286046100000021, "type": "key_down", "key": "w"}, {"t": 6.317665999999917, "type": "key_down", "key": "w"}, {"t": 6.3486502000000655, "type": "key_down", "key": "w"}, {"t": 6.380033099999764, "type": "key_down", "key": "w"}, {"t": 6.410948799999915, "type": "key_down", "key": "w"}, {"t": 6.442448299999796, "type": "key_down", "key": "w"}, {"t": 6.473456799999894, "type": "key_down", "key": "w"}, {"t": 6.50458959999969, "type": "key_down", "key": "w"}, {"t": 6.536054700000022, "type": "key_down", "key": "w"}, {"t": 6.567110899999989, "type": "key_down", "key": "w"}, {"t": 6.598285000000033, "type": "key_down", "key": "w"}, {"t": 6.629695699999957, "type": "key_down", "key": "w"}, {"t": 6.6638990999999805, "type": "key_down", "key": "w"}, {"t": 6.69496479999998, "type": "key_down", "key": "w"}, {"t": 6.72614939999994, "type": "key_down", "key": "w"}, {"t": 6.757962700000007, "type": "key_down", "key": "w"}, {"t": 6.788844400000016, "type": "key_down", "key": "w"}, {"t": 6.819865200000095, "type": "key_down", "key": "w"}, {"t": 6.851210699999683, "type": "key_down", "key": "w"}, {"t": 6.8824681000000965, "type": "key_down", "key": "w"}, {"t": 6.913549999999759, "type": "key_down", "key": "w"}, {"t": 6.944680199999766, "type": "key_down", "key": "w"}, {"t": 6.975967200000014, "type": "key_down", "key": "w"}, {"t": 7.007300199999918, "type": "key_down", "key": "w"}, {"t": 7.0383655000000545, "type": "key_down", "key": "w"}, {"t": 7.0696797999999035, "type": "key_down", "key": "w"}, {"t": 7.101012799999808, "type": "key_down", "key": "w"}, {"t": 7.132117799999833, "type": "key_down", "key": "w"}, {"t": 7.165466299999935, "type": "key_down", "key": "w"}, {"t": 7.197389399999793, "type": "key_down", "key": "w"}, {"t": 7.227744299999813, "type": "key_down", "key": "w"}, {"t": 7.259676299999683, "type": "key_down", "key": "w"}, {"t": 7.290551099999902, "type": "key_down", "key": "w"}, {"t": 7.321388999999726, "type": "key_down", "key": "w"}, {"t": 7.3526991999997335, "type": "key_down", "key": "w"}, {"t": 7.384084100000109, "type": "key_down", "key": "w"}, {"t": 7.415072599999803, "type": "key_down", "key": "w"}, {"t": 7.446425799999815, "type": "key_down", "key": "w"}, {"t": 7.477626999999757, "type": "key_down", "key": "w"}, {"t": 7.508912299999793, "type": "key_down", "key": "w"}, {"t": 7.540008999999827, "type": "key_down", "key": "w"}, {"t": 7.571237600000131, "type": "key_down", "key": "w"}, {"t": 7.602606899999955, "type": "key_down", "key": "w"}, {"t": 7.633543500000087, "type": "key_down", "key": "w"}, {"t": 7.667811100000108, "type": "key_down", "key": "w"}, {"t": 7.698984999999993, "type": "key_down", "key": "w"}, {"t": 7.7304346000000805, "type": "key_down", "key": "w"}, {"t": 7.761631099999704, "type": "key_down", "key": "w"}, {"t": 7.792727699999887, "type": "key_down", "key": "w"}, {"t": 7.824137399999927, "type": "key_down", "key": "w"}, {"t": 7.845096199999716, "type": "key_up", "key": "w"}, {"t": 7.857303899999806, "type": "key_up", "key": "a"}, {"t": 8.352777999999944, "type": "key_down", "key": "d"}, {"t": 8.450464499999725, "type": "key_up", "key": "d"}, {"t": 8.719433700000081, "type": "key_down", "key": "d"}, {"t": 8.798820199999682, "type": "key_up", "key": "d"}, {"t": 9.552168700000038, "type": "key_down", "key": "w"}, {"t": 9.806993799999873, "type": "key_down", "key": "w"}, {"t": 9.838208000000122, "type": "key_down", "key": "w"}, {"t": 9.869421899999907, "type": "key_down", "key": "w"}, {"t": 9.900722599999881, "type": "key_down", "key": "w"}, {"t": 9.93172770000001, "type": "key_down", "key": "w"}, {"t": 9.96314829999983, "type": "key_down", "key": "w"}, {"t": 9.99436489999971, "type": "key_down", "key": "w"}, {"t": 10.025713799999721, "type": "key_down", "key": "w"}, {"t": 10.056765299999824, "type": "key_down", "key": "w"}, {"t": 10.087977199999841, "type": "key_down", "key": "w"}, {"t": 10.119319200000064, "type": "key_down", "key": "w"}, {"t": 10.150472400000126, "type": "key_down", "key": "w"}, {"t": 10.184617999999773, "type": "key_down", "key": "w"}, {"t": 10.21605180000006, "type": "key_down", "key": "w"}, {"t": 10.247151199999735, "type": "key_down", "key": "w"}, {"t": 10.278192799999943, "type": "key_down", "key": "w"}, {"t": 10.30959299999995, "type": "key_down", "key": "w"}, {"t": 10.340689899999688, "type": "key_down", "key": "w"}, {"t": 10.372011699999803, "type": "key_down", "key": "w"}, {"t": 10.403205600000092, "type": "key_down", "key": "w"}, {"t": 10.434655099999873, "type": "key_down", "key": "w"}, {"t": 10.465737699999863, "type": "key_down", "key": "w"}, {"t": 10.496874800000114, "type": "key_down", "key": "w"}, {"t": 10.528336099999706, "type": "key_down", "key": "w"}, {"t": 10.559294399999999, "type": "key_down", "key": "w"}, {"t": 10.590596600000026, "type": "key_down", "key": "w"}, {"t": 10.621681600000102, "type": "key_down", "key": "w"}, {"t": 10.652907400000004, "type": "key_down", "key": "w"}, {"t": 10.687220700000125, "type": "key_down", "key": "w"}, {"t": 10.718358600000101, "type": "key_down", "key": "w"}, {"t": 10.749910499999714, "type": "key_down", "key": "w"}, {"t": 10.780870499999764, "type": "key_down", "key": "w"}, {"t": 10.812178700000004, "type": "key_down", "key": "w"}, {"t": 10.843360800000028, "type": "key_down", "key": "w"}, {"t": 10.874492500000088, "type": "key_down", "key": "w"}, {"t": 10.905873400000019, "type": "key_down", "key": "w"}, {"t": 10.937565499999891, "type": "key_down", "key": "w"}, {"t": 10.968221399999948, "type": "key_down", "key": "w"}, {"t": 10.999837899999875, "type": "key_down", "key": "w"}, {"t": 11.030821599999854, "type": "key_down", "key": "w"}, {"t": 11.0618000999998, "type": "key_down", "key": "w"}, {"t": 11.088288200000079, "type": "key_down", "key": "a"}, {"t": 11.343969099999867, "type": "key_down", "key": "a"}, {"t": 11.374950500000068, "type": "key_down", "key": "a"}, {"t": 11.406231999999818, "type": "key_down", "key": "a"}, {"t": 11.437460999999985, "type": "key_down", "key": "a"}, {"t": 11.469144599999709, "type": "key_down", "key": "a"}, {"t": 11.499821599999905, "type": "key_down", "key": "a"}, {"t": 11.531231399999797, "type": "key_down", "key": "a"}, {"t": 11.562549799999942, "type": "key_down", "key": "a"}, {"t": 11.593787799999973, "type": "key_down", "key": "a"}, {"t": 11.624899899999946, "type": "key_down", "key": "a"}, {"t": 11.65603239999973, "type": "key_down", "key": "a"}, {"t": 11.690179899999748, "type": "key_down", "key": "a"}, {"t": 11.72157419999985, "type": "key_down", "key": "a"}, {"t": 11.752816799999891, "type": "key_down", "key": "a"}, {"t": 11.784149199999774, "type": "key_down", "key": "a"}, {"t": 11.815290199999708, "type": "key_down", "key": "a"}, {"t": 11.846466899999996, "type": "key_down", "key": "a"}, {"t": 11.877547199999754, "type": "key_down", "key": "a"}, {"t": 11.90869369999973, "type": "key_down", "key": "a"}, {"t": 11.940049100000124, "type": "key_down", "key": "a"}, {"t": 11.971389499999987, "type": "key_down", "key": "a"}, {"t": 12.002466599999934, "type": "key_down", "key": "a"}, {"t": 12.033662699999695, "type": "key_down", "key": "a"}, {"t": 12.065154299999904, "type": "key_down", "key": "a"}, {"t": 12.0961898999999, "type": "key_down", "key": "a"}, {"t": 12.127397199999905, "type": "key_down", "key": "a"}, {"t": 12.159106999999949, "type": "key_down", "key": "a"}, {"t": 12.193157400000018, "type": "key_down", "key": "a"}, {"t": 12.224049299999933, "type": "key_down", "key": "a"}, {"t": 12.255344100000002, "type": "key_down", "key": "a"}, {"t": 12.287053199999718, "type": "key_down", "key": "a"}, {"t": 12.299645399999918, "type": "key_up", "key": "a"}, {"t": 12.33172949999971, "type": "key_up", "key": "w"}, {"t": 12.927134399999886, "type": "key_down", "key": "s"}, {"t": 12.994516199999907, "type": "key_up", "key": "s"}, {"t": 13.562143600000127, "type": "key_down", "key": "space"}, {"t": 13.5695639999999, "type": "key_down", "key": "w"}, {"t": 13.750848700000006, "type": "key_up", "key": "space"}, {"t": 13.809353900000133, "type": "key_up", "key": "w"}, {"t": 14.772282800000085, "type": "key_down", "key": "w"}, {"t": 15.023818499999834, "type": "key_down", "key": "w"}, {"t": 15.055056599999716, "type": "key_down", "key": "w"}, {"t": 15.086135499999727, "type": "key_down", "key": "w"}, {"t": 15.117347299999892, "type": "key_down", "key": "w"}, {"t": 15.148617299999842, "type": "key_down", "key": "w"}, {"t": 15.180012899999838, "type": "key_down", "key": "w"}, {"t": 15.214088700000048, "type": "key_down", "key": "w"}, {"t": 15.245695399999931, "type": "key_down", "key": "w"}, {"t": 15.277174599999853, "type": "key_down", "key": "w"}, {"t": 15.307837699999709, "type": "key_down", "key": "w"}, {"t": 15.317881699999816, "type": "key_up", "key": "w"}, {"t": 15.59090819999983, "type": "key_down", "key": "s"}, {"t": 15.705647499999941, "type": "key_up", "key": "s"}, {"t": 16.15389920000007, "type": "key_down", "key": "w"}, {"t": 16.194196099999772, "type": "key_down", "key": "space"}, {"t": 16.34505360000003, "type": "key_up", "key": "space"}, {"t": 16.447836899999857, "type": "key_up", "key": "w"}, {"t": 17.417622500000107, "type": "key_down", "key": "w"}, {"t": 17.669570999999905, "type": "key_down", "key": "w"}, {"t": 17.700547200000074, "type": "key_down", "key": "w"}, {"t": 17.735217699999794, "type": "key_down", "key": "w"}, {"t": 17.766255399999864, "type": "key_down", "key": "w"}, {"t": 17.79722670000001, "type": "key_down", "key": "w"}, {"t": 17.82865609999999, "type": "key_down", "key": "w"}, {"t": 17.85993529999996, "type": "key_down", "key": "w"}, {"t": 17.891399300000103, "type": "key_down", "key": "w"}, {"t": 17.9222821999997, "type": "key_down", "key": "w"}, {"t": 17.95363150000003, "type": "key_down", "key": "w"}, {"t": 17.98468869999988, "type": "key_down", "key": "w"}, {"t": 18.015950099999827, "type": "key_down", "key": "w"}, {"t": 18.047380099999828, "type": "key_down", "key": "w"}, {"t": 18.078656799999862, "type": "key_down", "key": "w"}, {"t": 18.109630399999787, "type": "key_down", "key": "w"}, {"t": 18.14083750000009, "type": "key_down", "key": "w"}, {"t": 18.172086900000068, "type": "key_down", "key": "w"}, {"t": 18.203244599999834, "type": "key_down", "key": "w"}, {"t": 18.237686999999823, "type": "key_down", "key": "w"}, {"t": 18.26868579999973, "type": "key_down", "key": "w"}, {"t": 18.274837599999955, "type": "key_up", "key": "w"}, {"t": 18.598049199999878, "type": "key_down", "key": "s"}, {"t": 18.718410999999833, "type": "key_up", "key": "s"}, {"t": 19.132903400000032, "type": "key_down", "key": "w"}, {"t": 19.14345719999983, "type": "key_down", "key": "space"}, {"t": 19.30002119999972, "type": "key_up", "key": "space"}, {"t": 20.67171789999975, "type": "key_down", "key": "e"}, {"t": 20.82892609999999, "type": "key_up", "key": "e"}, {"t": 20.932409799999732, "type": "key_down", "key": "e"}, {"t": 21.046393699999953, "type": "key_up", "key": "e"}, {"t": 21.111757099999977, "type": "key_down", "key": "e"}, {"t": 21.259047999999893, "type": "key_up", "key": "e"}, {"t": 21.329204799999843, "type": "key_up", "key": "w"}]

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
        "fishing_use_br_sc_every_x_fish": bool(raw.get("fishing_use_br_sc_every_x_fish", False)),
        "fishing_br_sc_every_x_fish": _coerce_int(raw.get("fishing_br_sc_every_x_fish"), 30, 1, 100000),
        "fishing_actions_delay_ms": _coerce_int(raw.get("fishing_actions_delay_ms"), 100, 0, 5000),
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


def _run_recorded_events(
    *,
    events: list[dict[str, Any]],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
) -> bool:
    pressed_keys: set[str] = set()
    last_t = 0.0
    try:
        for ev in events:
            if not should_continue() or not can_run():
                return False

            t = float(ev.get("t", last_t))
            dt = t - last_t
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


def _run_pre_fishing_sequence(
    *,
    cfg: dict[str, Any],
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
    activate_roblox_cb: Callable[[], None] | None = None,
) -> bool:
    if not should_continue() or not can_run():
        return False

    fishing_actions_delay = _get_fishing_actions_delay_seconds(cfg)
    if not _run_respawn_sequence(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        action_delay_seconds=fishing_actions_delay,
        activate_roblox_cb=activate_roblox_cb,
    ):
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
    if not sleep_interruptible(0.5 + action_delay_seconds):
        return False

    _autoit_key_tap("r")
    if not sleep_interruptible(0.5 + action_delay_seconds):
        return False

    _autoit_key_tap("enter")
    if not sleep_interruptible(2.0 + action_delay_seconds):
        return False

    return True


def _run_walk_to_fish_path(
    *,
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
) -> bool:
    if not WALK_TO_FISH_EVENTS:
        return False
    return _run_recorded_events(
        events=WALK_TO_FISH_EVENTS,
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
    )


def _run_walk_to_sell_fish_path(
    *,
    sleep_interruptible: Callable[[float, float], bool],
    should_continue: Callable[[], bool],
    can_run: Callable[[], bool],
) -> bool:
    if not WALK_TO_SELL_FISH_EVENTS:
        return True
    return _run_recorded_events(
        events=WALK_TO_SELL_FISH_EVENTS,
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
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
        autoit.send(aura_name)
    except Exception:
        pass
    if not sleep_interruptible(step_delay):
        return False

    _autoit_key_tap("enter")
    if not sleep_interruptible(step_delay):
        return False

    if first_slot_x > 0:
        autoit.mouse_click("left", first_slot_x, first_slot_y, 1, speed=3)
    if not sleep_interruptible(step_delay):
        return False

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
) -> bool:
    if fish_sell_count <= 0:
        return True
    fishing_actions_delay = _get_fishing_actions_delay_seconds(cfg)
    if not _run_respawn_sequence(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
        action_delay_seconds=fishing_actions_delay,
        activate_roblox_cb=activate_roblox_cb,
    ):
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

    if not _run_walk_to_sell_fish_path(
        sleep_interruptible=sleep_interruptible,
        should_continue=should_continue,
        can_run=can_run,
    ):
        return False

    dialogue_x, dialogue_y = cfg["fishing_flarg_dialogue_box"]
    if dialogue_x > 0:
        autoit.mouse_click("left", dialogue_x, dialogue_y, 1, speed=3)
        if not sleep_interruptible(0.3 + fishing_actions_delay):
            return False

        drag_x = int(dialogue_x)
        drag_start_y = max(0, int(dialogue_y) - 500)
        drag_end_y = int(dialogue_y) + 75
        autoit.mouse_move(drag_x, drag_start_y, 0)
        if not sleep_interruptible(0.2 + fishing_actions_delay):
            return False

        autoit.mouse_down("right")
        if not sleep_interruptible(0.1 + fishing_actions_delay):
            return False
        autoit.mouse_move(drag_x, drag_end_y, 0)
        if not sleep_interruptible(0.1 + fishing_actions_delay):
            return False
        autoit.mouse_up("right")

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
    if not sleep_interruptible(0.6 + fishing_actions_delay):
        return False

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
    activate_roblox_cb: Callable[[], None] | None = None,
    runtime_state: dict[str, Any] | None = None,
) -> None:
    stop_event = stop_event or threading.Event()
    config_provider = config_provider or _load_config_file

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

    def _get_due_actions() -> tuple[bool, int, bool, bool]:
        sell_after = max(1, int(cfg.get("fishing_sell_after_x_fish", 30)))
        should_sell = bool(cfg.get("fishing_enable_selling", False)) and (fish_caught_count >= sell_after)
        sell_count = max(1, int(cfg.get("fishing_sell_how_many_fish", 1)))

        use_merchant_every_x = bool(cfg.get("fishing_use_merchant_every_x_fish", False))
        merchant_after = max(1, int(cfg.get("fishing_merchant_every_x_fish", 30)))
        should_use_merchant = use_merchant_every_x and (fish_caught_since_merchant >= merchant_after)

        use_br_sc_every_x = bool(cfg.get("fishing_use_br_sc_every_x_fish", False))
        br_sc_after = max(1, int(cfg.get("fishing_br_sc_every_x_fish", 30)))
        should_use_br_sc = use_br_sc_every_x and (fish_caught_since_br_sc >= br_sc_after)

        return should_sell, sell_count, should_use_merchant, should_use_br_sc

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
    fish_caught_since_br_sc = _state_counter("fish_caught_since_br_sc")
    _set_state_flag("merchant_requires_reset", False)

    def _persist_runtime_counters() -> None:
        if runtime_state_dict is None:
            return
        runtime_state_dict["fish_caught_count"] = max(0, int(fish_caught_count))
        runtime_state_dict["fish_caught_since_merchant"] = max(0, int(fish_caught_since_merchant))
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
                was_runnable = False
                last_start_fishing_click_at = None
                time.sleep(0.05)
                continue

            if not was_runnable:
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
                    ):
                        continue
                    fish_caught_count = 0
                    _persist_runtime_counters()
                    last_start_fishing_click_at = None
                    was_runnable = False
                    continue

                should_sell, sell_count, should_use_merchant, should_use_br_sc = _get_due_actions()

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
                    ):
                        continue
                    fish_caught_count = 0
                    _persist_runtime_counters()

                    # Re-evaluate counters after selling because merchant/BRSC counters are independent.
                    _, _, should_use_merchant, should_use_br_sc = _get_due_actions()

                    if should_use_merchant:
                        print(f"{log_prefix} merchant flow triggered after pending selling.")
                        merchant_ran, _ = _run_merchant_sequence_with_state()
                        fish_caught_since_merchant = 0
                        _persist_runtime_counters()
                        if not merchant_ran:
                            print(f"{log_prefix} merchant flow skipped/failed during fishing.")

                    if should_use_br_sc:
                        print(f"{log_prefix} BR/SC flow triggered after pending selling.")
                        _run_br_sc_sequence()
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
                    fish_caught_since_merchant = 0
                    _persist_runtime_counters()
                    if not merchant_ran:
                        print(f"{log_prefix} merchant flow skipped/failed during fishing.")

                    if should_use_br_sc:
                        print(f"{log_prefix} BR/SC flow triggered after pending merchant.")
                        _run_br_sc_sequence()
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
                    _run_br_sc_sequence()
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
                ):
                    continue
                if not _run_equip_aura_before_movement(
                    cfg=cfg,
                    sleep_interruptible=_sleep_interruptible,
                    should_continue=_should_continue,
                    can_run=_can_run,
                ):
                    continue
                if not _run_walk_to_fish_path(
                    sleep_interruptible=_sleep_interruptible,
                    should_continue=_should_continue,
                    can_run=_can_run,
                ):
                    continue
                click_x, click_y = cfg["fishing_click_position"]
                autoit.mouse_click("left", click_x, click_y, speed=3)
                last_start_fishing_click_at = time.monotonic()
                if not _sleep_interruptible(0.25):
                    continue
                was_runnable = True

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
            autoit.mouse_click("left", close_x, close_y, speed=3)
            if not _sleep_interruptible(3.0):
                continue

            fish_caught_count += 1
            fish_caught_since_merchant += 1
            fish_caught_since_br_sc += 1
            _persist_runtime_counters()

            if not _should_continue() or not _can_run():
                continue

            use_merchant_every_x = bool(cfg.get("fishing_use_merchant_every_x_fish", False))
            merchant_after = max(1, int(cfg.get("fishing_merchant_every_x_fish", 30)))
            should_use_merchant = use_merchant_every_x and (fish_caught_since_merchant >= merchant_after)

            use_br_sc_every_x = bool(cfg.get("fishing_use_br_sc_every_x_fish", False))
            br_sc_after = max(1, int(cfg.get("fishing_br_sc_every_x_fish", 30)))
            should_use_br_sc = use_br_sc_every_x and (fish_caught_since_br_sc >= br_sc_after)

            if bool(cfg.get("fishing_enable_selling", False)):
                sell_after = int(cfg.get("fishing_sell_after_x_fish", 30))
                sell_count = int(cfg.get("fishing_sell_how_many_fish", 1))
                if fish_caught_count >= max(1, sell_after):
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
                    ):
                        continue
                    fish_caught_count = 0
                    _persist_runtime_counters()

                    if should_use_merchant:
                        print(f"{log_prefix} merchant flow triggered after selling.")
                        merchant_ran, _ = _run_merchant_sequence_with_state()
                        fish_caught_since_merchant = 0
                        _persist_runtime_counters()
                        if not merchant_ran:
                            print(f"{log_prefix} merchant flow skipped/failed during fishing.")

                    if should_use_br_sc:
                        print(f"{log_prefix} BR/SC flow triggered after selling.")
                        _run_br_sc_sequence()
                        fish_caught_since_br_sc = 0
                        _persist_runtime_counters()

                    was_runnable = False
                    last_start_fishing_click_at = None
                    continue

            if should_use_merchant:
                print(f"{log_prefix} merchant flow triggered after {fish_caught_since_merchant} catches.")
                merchant_ran, merchant_requires_reset = _run_merchant_sequence_with_state()
                fish_caught_since_merchant = 0
                _persist_runtime_counters()
                if not merchant_ran:
                    print(f"{log_prefix} merchant flow skipped/failed during fishing.")

                if should_use_br_sc:
                    print(f"{log_prefix} BR/SC flow triggered after merchant.")
                    _run_br_sc_sequence()
                    fish_caught_since_br_sc = 0
                    should_use_br_sc = False
                    _persist_runtime_counters()

                if merchant_requires_reset:
                    if not _sleep_interruptible(0.4 + _get_fishing_actions_delay_seconds(cfg)):
                        continue
                    was_runnable = False
                    last_start_fishing_click_at = None
                    continue

            if should_use_br_sc:
                print(f"{log_prefix} BR/SC flow triggered after {fish_caught_since_br_sc} catches.")
                _run_br_sc_sequence()
                fish_caught_since_br_sc = 0
                _persist_runtime_counters()

            start_x, start_y = cfg["fishing_click_position"]
            autoit.mouse_click("left", start_x, start_y, speed=3)
            last_start_fishing_click_at = time.monotonic()
            _sleep_interruptible(0.3)
    finally:
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