"""Auto clip rare auras: a rolling buffer of the Roblox window, saved as a video when a rare one rolls."""
import collections
import ctypes
import json
import os
import re
import sys
import threading
import time
import urllib.request

import cv2
import numpy as np

import game

FPS = 20
BEFORE_S = 90            # the log only shows the aura after its cutscene
AFTER_S = 30
HEIGHTS = {'768p': 768, '1080p': 1080, '1440p': 1440, '4K': 2160}     # two minutes of frames sit in memory
HEIGHT = 768
QUALITY = 75
SHOT_S = 5               # embed picture is from this long before the log line
CLIP_DIR = os.path.join(game.APP_DIR, 'clips')

_table = None


def norm(name):
    return re.sub(r'[^a-z0-9]', '', (name or '').lower())


def biome_key(name):
    return norm(re.sub(r'^\W*the\s+', '', (name or '').strip(), flags=re.I))


_names = None
AURAS_URL = 'https://raw.githubusercontent.com/ManasAarohi1/MMacro/main/auras.json'
LIVE = os.path.join(game.APP_DIR, 'auras.json')     # the last list fetched from GitHub


def _read(body):
    """{name: [1 in N, {biome: 1 in M}]}, bad entries dropped."""
    try:
        d = json.loads(body)
    except ValueError:
        return {}
    if not isinstance(d, dict):
        return {}
    return {k: v for k, v in d.items() if isinstance(v, list) and len(v) == 2 and isinstance(v[0], int)
            and isinstance(v[1], dict)}


def _load():
    """The list built into the exe, with the fetched one on top (it can add and change, never remove)."""
    here = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    auras = {}
    for path in (os.path.join(here, 'auras.json'), LIVE):
        try:
            with open(path, encoding='utf-8') as f:
                auras.update(_read(f.read()))
        except OSError:
            pass
    return auras


def refresh(timeout=10):
    """Fetches the aura list from GitHub so new auras count without a new build. Returns how many are known."""
    global _names, _table
    req = urllib.request.Request(AURAS_URL, headers={'User-Agent': 'MMacro'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    if not _read(body.decode('utf-8')):
        raise ValueError('not an aura list')
    os.makedirs(game.APP_DIR, exist_ok=True)
    with open(LIVE + '.tmp', 'wb') as f:
        f.write(body)
    os.replace(LIVE + '.tmp', LIVE)
    _names = _load()
    _table = None
    return len(_names)


def names():
    global _names
    if _names is None:
        _names = _load()
    return list(_names)


def table():
    """norm(aura) -> (1 in N, {biome: 1 in M})."""
    global _table
    if _table is None:
        names()
        _table = {norm(name): (n, biomes) for name, (n, biomes) in _names.items()}
    return _table


def rarity(aura, biome='', line=''):
    """1 in N for this aura in this biome, or None."""
    m = re.search(r'1 in ([\d,]+)', line or '')
    if m:
        return int(m.group(1).replace(',', ''))
    e = table().get(norm(aura))
    if e is None:
        return None
    n, biomes = e
    b = biome_key(biome)
    if b in biomes:
        return biomes[b]
    if b == 'glitched' and biomes:          # Glitched counts as every biome
        return min(biomes.values())
    return n


MODS = {'ctrl': 0xA2, 'control': 0xA2, 'shift': 0xA0, 'alt': 0xA4, 'win': 0x5B, 'windows': 0x5B}
NAMED = {'space': 0x20, 'enter': 0x0D, 'tab': 0x09, 'esc': 0x1B, 'home': 0x24, 'end': 0x23, 'insert': 0x2D,
         'ins': 0x2D, 'delete': 0x2E, 'del': 0x2E, 'pageup': 0x21, 'pagedown': 0x22, 'printscreen': 0x2C,
         'prtsc': 0x2C, 'pause': 0x13, 'scrolllock': 0x91, 'up': 0x26, 'down': 0x28, 'left': 0x25, 'right': 0x27}
EXTENDED = {0x5B, 0x2D, 0x2E, 0x24, 0x23, 0x21, 0x22, 0x26, 0x28, 0x25, 0x27, 0x2C}


def parse_keys(text):
    """'Win+Alt+G' -> ([modifier vks], key vk). ValueError if it's not a valid combo."""
    parts = [p.strip().lower() for p in re.split(r'\s*\+\s*', (text or '').strip()) if p.strip()]
    if not parts:
        raise ValueError('no key set')
    *mods, key = parts
    if any(m not in MODS for m in mods):
        raise ValueError('%s: only Ctrl, Shift, Alt and Win go before the key' % text)
    if key in MODS:
        raise ValueError('%s: needs a key after the modifiers' % text)
    if re.fullmatch(r'f([1-9]|1[0-9]|2[0-4])', key):
        vk = 0x6F + int(key[1:])
    elif re.fullmatch(r'(num|numpad)[0-9]', key):
        vk = 0x60 + int(key[-1])
    elif key in NAMED:
        vk = NAMED[key]
    elif re.fullmatch(r'[a-z0-9]', key):
        vk = ord(key.upper())
    elif re.fullmatch(r'key[0-9a-f]{2}', key):
        vk = int(key[3:], 16)                    # unnamed key, as key_name() writes it
    else:
        raise ValueError('%s: %r is not a key this knows' % (text, key))
    if vk in (0x70, 0x71):
        raise ValueError('%s: F1 and F2 start and stop MMacro' % text)
    return [MODS[m] for m in dict.fromkeys(mods)], vk


MOD_VKS = {0xA0: 'Shift', 0xA1: 'Shift', 0xA2: 'Ctrl', 0xA3: 'Ctrl', 0xA4: 'Alt', 0xA5: 'Alt', 0x5B: 'Win',
           0x5C: 'Win'}
SKIP_VKS = set(range(0x01, 0x07)) | {0x10, 0x11, 0x12}       # mouse buttons, plus generic Shift/Ctrl/Alt


def key_name(vk):
    if 0x70 <= vk <= 0x87:
        return 'F%d' % (vk - 0x6F)
    if 0x60 <= vk <= 0x69:
        return 'Num%d' % (vk - 0x60)
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    named = {v: k for k, v in NAMED.items() if k not in ('ins', 'del', 'prtsc')}
    return named[vk].title() if vk in named else 'Key%02X' % vk


def combo_text(held):
    """Held keys as 'Ctrl+Shift+S': modifiers, then the last key pressed."""
    mods = [n for n in ('Win', 'Ctrl', 'Shift', 'Alt') if any(MOD_VKS.get(v) == n for v in held)]
    keys = [v for v in held if v not in MOD_VKS]
    return '+'.join(mods + [key_name(keys[-1])]) if keys else None


def capture_keys(timeout=15.0, down=None):
    """Wait for the player's clip key (or combo) and return it as text. None on timeout or Esc."""
    down = down or (lambda vk: bool(game.u32.GetAsyncKeyState(vk) & 0x8000))
    end, held = time.monotonic() + timeout, []
    while time.monotonic() < end:
        now = [vk for vk in range(0x01, 0xFF) if vk not in SKIP_VKS and down(vk)]
        if 0x1B in now:
            return None
        for vk in now:
            if vk not in held:
                held.append(vk)
        if held and not now and combo_text(held):
            return combo_text(held)
        if held and not now:
            held = []                           # only modifiers, wait for a real key
        time.sleep(0.02)
    return None


def press_keys(text):
    """Press and release the combo. Always lets go of everything, a stuck Win key keeps Start open."""
    mods, vk = parse_keys(text)
    held = []

    def send(code, up):
        flags = (0x0002 if up else 0) | (0x0001 if code in EXTENDED else 0)
        inp = game.IN(type=1, ki=game.KI(wVk=code, wScan=game.u32.MapVirtualKeyW(code, 0), dwFlags=flags,
                                         time=0, dwExtraInfo=0))
        game.u32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))

    with game.INPUT_LOCK:                   # keep the macro's own input out of the middle
        try:
            for code in mods + [vk]:
                send(code, False)
                held.append(code)
                time.sleep(0.03)
            time.sleep(0.08)
        finally:
            for code in reversed(held):
                if code in game.WIN_VKS:
                    game.mask_win()             # so letting go of Win doesn't open Start
                send(code, True)
                time.sleep(0.02)


def bgr(rgb, height=HEIGHT):
    """game.grab's RGB -> BGR, at most `height` tall (never scaled up). Uses the BGRA buffer under it, opencv is
    far faster on that."""
    b = rgb.base
    if isinstance(b, np.ndarray) and b.shape == rgb.shape[:2] + (4,) and rgb.ctypes.data - b.ctypes.data == 2:
        img, code = b, cv2.COLOR_BGRA2BGR
    else:
        img, code = np.ascontiguousarray(rgb), cv2.COLOR_RGB2BGR
    h, w = img.shape[:2]
    if h > height:
        img = cv2.resize(img, (round(w * height / h) // 2 * 2, height), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(img, code)


class Clipper:
    """Keeps the last BEFORE_S + AFTER_S seconds of the Roblox window."""

    def __init__(self, say=print, fps=FPS, keep_s=BEFORE_S + AFTER_S, height=HEIGHT):
        self.say, self.fps, self.keep_s, self.height = say, fps, keep_s, height
        self.frames = collections.deque(maxlen=fps * keep_s)
        self.stop_event = threading.Event()
        self.thread = None
        self.saves, self.lock = 0, threading.Lock()     # clips still waiting out AFTER_S

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _run(self):
        gap = 1.0 / self.fps
        while not self.stop_event.is_set():
            t0 = time.perf_counter()
            try:
                if game.roblox_window() is not None:
                    ok, jpg = cv2.imencode('.jpg', bgr(game.grab(game.client_box((0.0, 0.0, 1.0, 1.0))), self.height),
                                           [cv2.IMWRITE_JPEG_QUALITY, QUALITY])
                    if ok:
                        now = time.time()
                        self.frames.append((now, jpg))
                        while self.frames[0][0] < now - self.keep_s:
                            self.frames.popleft()
            except Exception:
                pass
            self.stop_event.wait(max(0.0, gap - (time.perf_counter() - t0)))
        self._drop()

    def _drop(self):
        """Free the buffer once stopped and no clip needs it, it's most of MMacro's memory."""
        with self.lock:
            if self.stop_event.is_set() and not self.saves:
                self.frames.clear()

    def shot(self, at):
        """PNG of the last frame at least SHOT_S before `at`, or None."""
        older = [jpg for t, jpg in list(self.frames) if t <= at - SHOT_S]
        if not older:
            return None
        ok, png = cv2.imencode('.png', cv2.imdecode(older[-1], cv2.IMREAD_COLOR))
        return png.tobytes() if ok else None

    def clip(self, label, done=lambda path: None):
        """Save the buffer after AFTER_S more seconds, then done(path or None)."""
        with self.lock:
            self.saves += 1
        threading.Thread(target=self._save, args=(label, done), daemon=True).start()

    def _save(self, label, done):
        time.sleep(AFTER_S)
        frames = list(self.frames)
        with self.lock:
            self.saves -= 1
        self._drop()
        path = None
        try:
            if len(frames) >= 2:
                os.makedirs(CLIP_DIR, exist_ok=True)
                name = re.sub(r'[^\w\- ]', '', label).strip().replace(' ', '_') or 'aura'
                path = os.path.join(CLIP_DIR, '%s_%s.mp4' % (time.strftime('%Y%m%d_%H%M%S'), name))
                fps = max(1.0, (len(frames) - 1) / max(0.1, frames[-1][0] - frames[0][0]))   # the real capture rate
                first = cv2.imdecode(frames[0][1], cv2.IMREAD_COLOR)
                h, w = first.shape[:2]
                out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                for _, jpg in frames:
                    img = cv2.imdecode(jpg, cv2.IMREAD_COLOR)
                    if img is not None and img.shape[:2] == (h, w):
                        out.write(img)
                out.release()
        except Exception as e:
            self.say('clip failed - %s: %s' % (type(e).__name__, e))
            path = None
        done(path)


class KeyClipper(Clipper):
    """Presses the clip key of the player's own recorder (Game Bar, Medal, ShadowPlay...) instead.
    Only keeps a few frames for the embed picture."""

    def __init__(self, keys, say=print):
        parse_keys(keys)
        Clipper.__init__(self, say, fps=2, keep_s=SHOT_S + 5)
        self.keys = keys

    def clip(self, label, done=lambda sent: None):
        threading.Thread(target=self._press, args=(done,), daemon=True).start()

    def _press(self, done):
        try:
            press_keys(self.keys)
        except Exception as e:
            self.say('clip key %s not sent - %s: %s' % (self.keys, type(e).__name__, e))
            done(None)
            return
        self.say('clip key %s pressed' % self.keys)
        done(True)
