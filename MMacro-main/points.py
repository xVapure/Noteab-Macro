"""Button boxes from gui_points.json, scaled to the Roblox window."""
import json
import os
import sys
import time

import game

_SIZES = None


def _sizes():
    global _SIZES
    if _SIZES is None:
        here = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(here, 'gui_points.json'), encoding='utf-8') as f:
            _SIZES = {tuple(int(v) for v in k.split('x')): boxes for k, boxes in json.load(f)['sizes'].items()}
    return _SIZES


NAMES = {(2560, 1440): '1440p fullscreen', (2560, 1369): '1440p windowed', (1920, 1080): '1080p fullscreen',
         (1920, 1009): '1080p windowed', (1366, 768): '768p fullscreen', (1366, 697): '768p windowed'}


WINDOWS = ('auraStorage', 'inventory')     # buttons inside the centred Inventory / Aura Storage window


def sizes():
    return list(_sizes())


def _nearest(cw, ch):
    """Closest stored size: same shape first, then nearest height."""
    return min(_sizes(), key=lambda s: (round(abs(s[0] / s[1] - cw / ch), 2), abs(s[1] - ch)))


def _lerp(xs, ys, x):
    i = 1 if x <= xs[1] else len(xs) - 1
    return ys[i - 1] + (ys[i] - ys[i - 1]) * (x - xs[i - 1]) / (xs[i] - xs[i - 1])


def _bar_box(name, ow, oh):
    """The fishing bar at an unstored size. It's placed by width, so plain stretching misses the icon."""
    full = sorted(s for s in _sizes() if abs(s[0] / s[1] - 16 / 9) < 0.01)
    rows = [(w, h) + tuple(_sizes()[(w, h)][name]) for w, h in full]
    ws = [r[0] for r in rows]
    bw = _lerp(ws, [r[4] for r in rows], ow)
    bh = _lerp(ws, [r[5] for r in rows], ow)
    cx = ow / 2 + _lerp(ws, [l + a / 2 - w / 2 for w, h, l, t, a, b in rows], ow)
    cy = oh * _lerp(ws, [(t + b / 2) / h for w, h, l, t, a, b in rows], ow)
    return cx - bw / 2, cy - bh / 2, bw, bh


def box(name):
    """(left, top, right, bottom) on screen, or None with no Roblox window."""
    w = game.roblox_window()                    # costs ~8 ms and fishing calls this a lot
    if w is None:
        return None
    x0, y0, cw, ch = game.client_rect(w)
    if cw <= 0 or ch <= 0:                      # minimised
        return None
    s = game.window_scale(w)
    own = (round(cw / s), round(ch / s))        # the size Roblox lays out at, before DPI stretch
    size = own if own in _sizes() else _nearest(*own)
    l, t, bw, bh = _sizes()[size][name]
    if name.startswith(WINDOWS) and own not in _sizes():
        # that window is half the client wide, keeps its shape and stays centred, so width alone sets the scale
        s = cw / size[0]
        y = lambda v: y0 + ch / 2 + (v - size[1] / 2) * s
        return round(x0 + l * s), round(y(t)), round(x0 + (l + bw) * s), round(y(t + bh))
    if name.startswith('fishingMinigame') and 'Result' not in name and own not in _sizes():
        l, t, bw, bh = _bar_box(name, *own)
        size = own
    sx, sy = cw / size[0], ch / size[1]
    return (round(x0 + l * sx), round(y0 + t * sy), round(x0 + (l + bw) * sx), round(y0 + (t + bh) * sy))


def centre(name):
    """Middle of a button. A Calibrator point wins over the stored box."""
    stored = game.load_points()
    for key in [k for k, v in game.BUILT_IN.items() if v == name]:
        if key in stored:
            return game.to_screen(stored[key])
    b = box(name)
    return None if b is None else ((b[0] + b[2]) // 2, (b[1] + b[3]) // 2)


def click(name, settle=0.3):
    """Click a button's middle. False if there's no window or Roblox won't come forward."""
    c = centre(name)
    if c is None or not game.click(*c, park=False):
        return False
    game.paced(settle)
    return True


def grab(name):
    b = box(name)
    return None if b is None else game.grab(b)


def choice(colour):
    """Where the 'green' or 'red' dialogue choice is, or None."""
    b = box('dialogueChoicesFrame')
    if b is None:
        return None
    rgb = game.grab(b).astype(int)
    r, g, bl = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    main, a, c = (g, r, bl) if colour == 'green' else (r, g, bl)
    mask = (main >= 120) & (main > a + 40) & (main > c + 40)
    if mask.sum() < 30:
        return None
    # biggest patch only, so an aura glowing at the feet doesn't drag the point off the button
    patches = game._group(mask, (b[0], b[1]), 6, 12, 30)
    return (int(patches[0][0]), int(patches[0][1])) if patches else None


def dialogue_up():
    """Both green and red showing (an aura only ever fakes one colour)."""
    return choice('green') is not None and choice('red') is not None


def leave_dialogue(tries=3, gap=0.3, skip=False):
    """Press Leave until the dialogue's gone. True if there was one.

    A shop on top can eat the click. `skip` clicks "Click to skip" first; only use it with no shop open.
    """
    pressed = False
    for n in range(tries):
        at = choice('red')
        if at is None:
            if pressed:
                print('dialogue: gone after %d go(es)' % n)
            break
        if skip:
            click('dialogueSkipDialogue', 0.2)
            at = choice('red')
            if at is None:
                print('dialogue: gone after "Click to skip"')
                return True
        print('dialogue: Leave seen at %d,%d - pressing it (go %d)' % (at[0], at[1], n + 1))
        game.click(*at, park=False)
        pressed = True
        time.sleep(gap)
    else:
        if pressed and choice('red') is not None:
            print('dialogue: Leave still up after %d goes' % tries)
    return pressed
