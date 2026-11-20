import ctypes
import glob
import io
import itertools
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import tkinter as tk
from tkinter import messagebox
import urllib.error
import urllib.request
import uuid
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')      # numpy reserves memory per core; low-RAM PCs fail to open


def dpi_aware():
    """Real pixels on every monitor. Must run before any window exists."""
    for aware in (lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4)),
                  lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0,
                  lambda: ctypes.windll.user32.SetProcessDPIAware()):
        try:
            if aware():
                return
        except (AttributeError, OSError):
            pass


dpi_aware()

try:
    from pynput import keyboard, mouse  # noqa: E402
    from PIL import Image, ImageTk  # noqa: E402
    import game  # noqa: E402
    import eden  # noqa: E402
    import fishing  # noqa: E402
    import merchant as shop  # noqa: E402
    import clipper  # noqa: E402
    import equip  # noqa: E402
    import merchant_cache  # noqa: E402
except Exception as e:          # numpy's DLLs raise OSError, not ImportError
    why = str(e).strip().splitlines()[-1] if str(e).strip() else type(e).__name__
    try:
        folder = os.path.join(os.getenv('LOCALAPPDATA') or os.path.expanduser('~'), 'MMacro')
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, 'startup_error.txt'), 'w', encoding='utf-8') as f:
            f.write('%s\n\nexe: %s\n' % (e, sys.executable))
    except OSError:
        pass
    ctypes.windll.user32.MessageBoxW(0, 'The macro could not load one of its own files.\n\n%s\n\n'
                                     'Most often an antivirus removed it, or the PC is out of memory:\n'
                                     '  - add the macro to your antivirus exclusions and download it again\n'
                                     '  - close other programs, then open it again\n%s\n'
                                     'Send this message to Manas if it keeps happening.'
                                     % (why, '  - on Windows N or KN, install the Media Feature Pack (Settings > Apps '
                                        '> Optional features)\n' if 'DLL load failed' in why else ''),
                                     'MMacro', 0x10)
    sys.exit(1)

BG, PANEL, SUNK, EDGE = '#101116', '#16181f', '#0c0d11', '#272b36'
TEXT, DIM, ACCENT, GOOD, BAD = '#e6e8f0', '#767d92', '#aaaaff', '#7ee08a', '#ef6b6b'
UI, UIB = 'Segoe UI', 'Segoe UI Semibold'
SMALL_BUTTON = dict(bg=SUNK, fg=TEXT, activebackground=SUNK, activeforeground=ACCENT, relief='flat',
                    font=(UIB, 9), pady=4, cursor='hand2', borderwidth=0,
                    highlightthickness=1, highlightbackground=EDGE)

TITLE = 'MMacro'
VERSION = '1.0.5'
RELEASE_PAGE = 'https://github.com/ManasAarohi1/MMacro/releases/latest'
RELEASES = os.environ.get('MMACRO_UPDATE_URL') or 'https://api.github.com/repos/ManasAarohi1/MMacro/releases/latest'
INVITE = 'https://discord.gg/oppression'
ITEM_EVERY_S = {game.SC: 20 * 60, game.BR: 35 * 60}    # SC lasts 20 min, BR 35
ITEM_RETRY_S = 5 * 60                   # retry a failed one after this
ITEM_SPARE_S = 15                       # past the cooldown, so a use never lands just before it ends
REJOIN_WAITS = (15, 30, 60)             # last one repeats
IN_GAME_S = 150                         # after a rejoin, time to really be in game
OUT_S = 180                             # Roblox up but not in game this long = disconnect
PLAY_EVERY_S = 20                       # min gap between Play clicks
STALL_S = 600                           # loop stuck this long = restart the run
SLEPT_S = 60                            # clock jumped this far = PC slept
WATCH_EVERY = 0.5
CRASH_WAITS = (30, 60, 120, 300)        # last one repeats
LOOK_EVERY_S = 1.5                      # also how often Eden is looked for
AFK_EVERY_S = 300                       # Roblox kicks after 20 idle min
EDEN_RETRY_S = 60                       # retry the Eden contract this often
EDEN_GIVE_UP_S = 30 * 60                # give up after this (path on)
EDEN_AFK_REST_S = 900                   # no jumps while the contract is up
CRACK = 'portable crack'                # takes you to Eden's spawn, where the walk starts
CRACK_S = 3.0                           # wait after using it
EQUIP_RETRY_S = 5 * 60                  # retry a failed equip after this
JOIN_NONE_S = 300                       # 'nothing equipped' right after a join = title screen
EQUIP_GAP_S = 90                        # Aura Storage at most this often (auto roll swaps fast)
MERCHANT_STALE_S = 150                  # merchants stay ~3 min
MERCHANT_CATCH_S = 90                   # max wait for the fish on the line
MERCHANT_REPEAT_S = 600                 # one post per visit (the animation replays)

LOG_MAX = 4 << 20                       # trim logs.txt past this


_log_lock = threading.Lock()


def note(tag, msg):
    """Append a line to logs.txt; never raises."""
    with _log_lock:
        _note(tag, msg)


def _note(tag, msg):
    try:
        os.makedirs(game.APP_DIR, exist_ok=True)
        path = os.path.join(game.APP_DIR, 'logs.txt')
        if os.path.exists(path) and os.path.getsize(path) > LOG_MAX:
            with open(path, 'rb') as f:
                f.seek(-LOG_MAX // 2, os.SEEK_END)
                tail = f.read().split(b'\n', 1)[-1]
            with open(path, 'wb') as f:
                f.write(tail)
        with open(path, 'a', encoding='utf-8') as f:
            f.write('%s  [%s] %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), tag, msg))
    except OSError:
        pass


STORE_ROBLOX = ('Merchant detection reads Roblox\'s cache (rbx-storage.db), which was not found on this PC. It works '
                'with Roblox from roblox.com, Bloxstrap or Fishstrap.\n\nOpen Roblox once, or leave Merchant detection '
                'off.')


class _ToLog:
    """The windowed exe has no console, so print goes to logs.txt."""

    def __init__(self):
        self.buf = ''

    def write(self, s):
        self.buf += s
        while '\n' in self.buf:
            line, self.buf = self.buf.split('\n', 1)
            if line.strip():
                note('out', line.strip())

    def flush(self):
        pass


if sys.stdout is None or type(sys.stdout).__name__ == 'NullWriter':     # PyInstaller's no-console stub
    sys.stdout = sys.stderr = _ToLog()


def clip_floor(text):
    """'from 1 in' as a number; junk means 1 in a billion, never every roll."""
    try:
        return max(1, int(float(re.sub(r'[,\s_]', '', text or ''))))
    except ValueError:
        return 1_000_000_000


def device_line():
    """PC info for bug reports; never raises."""
    try:
        import platform
        u = ctypes.windll.user32
        w = game.find_roblox_window()
        client = 'no Roblox window'
        if w is not None:
            x, y, cw, ch = game.client_rect(w)
            s = game.window_scale(w)
            client = '%dx%d at %d,%d (%s%s)' % (cw, ch, x, y, game.awareness(w.hwnd), '' if s == 1 else
                                               ', laid out at %dx%d, stretched %d%% by Windows'
                                               % (round(cw / s), round(ch / s), round(s * 100)))
        dpi = u.GetDpiForWindow(w.hwnd) if w is not None else 0
        return ('v%s, Windows %s, screen %dx%d (all %dx%d), Roblox client %s, scale %d%%%s, MMacro %s%s%s'
                % (VERSION, platform.version(), u.GetSystemMetrics(0), u.GetSystemMetrics(1), u.GetSystemMetrics(78),
                   u.GetSystemMetrics(79), client, round(dpi * 100 / 96), game.in_dpi(game.REAL, display_line, w),
                   game.awareness(), '' if u.IsProcessDPIAware() else ' (a compatibility setting on the exe?)',
                   ', mouse buttons swapped' if u.GetSystemMetrics(23) else ''))
    except Exception as e:
        return 'v%s, device not read: %s: %s' % (VERSION, type(e).__name__, e)


def display_line(w):
    """Real monitor resolution and scale, outside our own DPI view."""
    try:
        u, g = ctypes.WinDLL('user32'), ctypes.WinDLL('gdi32')
        u.GetDC.restype = u.MonitorFromWindow.restype = ctypes.c_void_p
        u.GetDC.argtypes, u.ReleaseDC.argtypes = [ctypes.c_void_p], [ctypes.c_void_p, ctypes.c_void_p]
        g.GetDeviceCaps.argtypes = [ctypes.c_void_p, ctypes.c_int]
        u.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        hdc = u.GetDC(None)
        real = '%dx%d' % (g.GetDeviceCaps(hdc, 118), g.GetDeviceCaps(hdc, 117))    # DESKTOPHORZRES, DESKTOPVERTRES
        u.ReleaseDC(None, hdc)
        mon = u.MonitorFromWindow(w.hwnd if w is not None else None, 2)            # nearest monitor
        x, y = ctypes.c_uint(), ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(ctypes.c_void_p(mon), 0, ctypes.byref(x), ctypes.byref(y))
        return ' (display %s, monitor scale %d%%%s)' % (real, round(x.value * 100 / 96),
                                                        ', remote desktop' if u.GetSystemMetrics(0x1000) else '')
    except Exception as e:
        return ' (display not read: %s)' % type(e).__name__


# ================================================================ Discord
FOOTER = 'Join Manas Biome Support/Hunt Server'
TESTERS = ('Forsakened One', 'Daniel', 'Slpxy', 'Nova', 'imsomeone', 'Evil Talin Siran', 'ghost', '███\'█_Guest',
           'delta_likes_cats_xd')
EMBED_GOOD, EMBED_BAD, EMBED_INFO, EMBED_BIOME, EMBED_GOLD = 0x57F287, 0xED4245, 0x8A8F98, 0x58B9FF, 0xFFD700
BIOME_COLOURS = {'NORMAL': 0xB5BAC1, 'WINDY': 0x9ED9FF, 'RAINY': 0x4A7BD0, 'SNOWY': 0xDCEBFF, 'SAND STORM': 0xE0A85A,
                 'HELL': 0xC0392B, 'STARFALL': 0x6C7BFF, 'CORRUPTION': 0x8E44AD, 'NULL': 0x6B6B6B, 'HEAVEN': 0xFFE89A,
                 'LOST FOREST': 0x2E8B57, 'GLITCHED': 0x3BE37A, 'DREAMSPACE': 0xE86AF0, 'CYBERSPACE': 0x2FD3FF,
                 'SINGULARITY': 0x4B1E8C, 'THE RADIANT FOREST': 0xFFF1A8,
                 'GRAVEYARD': 0x5E6B5A, 'PUMPKIN MOON': 0xFF7A1A, 'BLOOD RAIN': 0x8B0A1A}      # events
PING = {'GLITCHED', 'DREAMSPACE', 'CYBERSPACE'}
CLIP_COLOURS = ((10 ** 10, 0xFFC94D), (10 ** 9, 0xB38CFF), (10 ** 8, 0x58B9FF), (1, EMBED_GOOD))  # by rarity
MERCHANT_COLOURS = {'Rin': 0xFF8C00, 'Mari': 0xFFD700, 'Jester': 0x9B59B6, 'Boss': 0x6A0DAD}


def biome_colour(name):
    """Event biomes may come as '(Event) Graveyard'."""
    name = re.sub(r'^\W*EVENT\W*', '', (name or '').upper()).strip()
    return BIOME_COLOURS.get(name, EMBED_BIOME)


def is_rare(name):
    squashed = name.upper().replace(' ', '')
    return any(p in squashed for p in PING)


class BiomeWatcher:
    """Tracks biome changes; rare ones alert once per cooldown, even at start."""

    def __init__(self, cooldown=300.0):
        self.cooldown = cooldown
        self.current = None
        self._last_alert = {}

    def feed(self, name, now=None):
        """(biome, alert) on a change, else None."""
        if not name:
            return None
        name = name.upper()
        if name == self.current:
            return None
        now = time.time() if now is None else now
        self.current = name
        last = self._last_alert.get(name)
        alert = is_rare(name) and (last is None or now - last >= self.cooldown)
        if alert:
            self._last_alert[name] = now
        return name, alert


def pretty(name):
    return ' '.join(w.capitalize() for w in name.split())


def clean_url(text):
    """Strip whitespace; pasted URLs often pick some up."""
    return ''.join((text or '').split())


def _post(webhook_url, payload, files=None, on_error=None):
    """Posts on a thread; `files` {name: png} go as attachment://name."""
    def run():
        try:
            if not files:
                body, kind = json.dumps(payload).encode(), 'application/json'
            else:
                b = uuid.uuid4().hex
                body = ('--%s\r\nContent-Disposition: form-data; name="payload_json"\r\n'
                        'Content-Type: application/json\r\n\r\n%s\r\n' % (b, json.dumps(payload))).encode()
                for i, (name, png) in enumerate(files.items()):
                    body += ('--%s\r\nContent-Disposition: form-data; name="files[%d]"; filename="%s"\r\n'
                             'Content-Type: image/png\r\n\r\n' % (b, i, name)).encode() + png + b'\r\n'
                body += ('--%s--\r\n' % b).encode()
                kind = 'multipart/form-data; boundary=' + b
            request = urllib.request.Request(webhook_url, data=body,
                                             headers={'Content-Type': kind, 'User-Agent': 'SolsBiomeLogger/1.0'})
            urllib.request.urlopen(request, timeout=30).close()
        except (urllib.error.URLError, OSError, ValueError) as e:
            if on_error:
                on_error('webhook failed: %s: %s' % (type(e).__name__, e))
    threading.Thread(target=run, daemon=True).start()


def _timestamp():
    return time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())


_logo = []


def logo_png():
    """axolotl.png bytes for the embed icon, or None."""
    if not _logo:
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'axolotl.png'), 'rb') as f:
                _logo.append(f.read())
        except OSError:
            _logo.append(None)
    return _logo[0]


def server_field(link):
    link = (link or '').strip()
    if not link:
        return 'No private server inserted'
    if link.startswith(('https://', 'http://')) and ' ' not in link:
        return '[Join](%s)' % link[:900]
    return link[:1000]


def post_event(webhook_url, title, description='', colour=EMBED_INFO, area='Macro', fields=(), ping='', shot=None,
               footer=True):
    """Posts one embed. `ping` is the message text (mentions only), `shot` a PNG under it."""
    if not webhook_url:
        return
    embed = {'author': {'name': 'MMacro · %s' % area, 'url': INVITE}, 'title': title[:256], 'color': colour,
             'timestamp': _timestamp()}
    files = {}
    if logo_png():
        files['logo.png'] = logo_png()
        embed['author']['icon_url'] = 'attachment://logo.png'
    if description:
        embed['description'] = description[:4000]
    if footer:
        fields = list(fields) + [('​', '-# [%s](%s)' % (FOOTER, INVITE), False)]
    if fields:
        embed['fields'] = [{'name': n, 'value': str(v)[:1024] or '-', 'inline': i} for n, v, i in fields]
    if shot:
        files['shot.png'] = shot
        embed['image'] = {'url': 'attachment://shot.png'}
    _post(webhook_url, {'content': ping, 'embeds': [embed]}, files)


def capital(text):
    text = text or ''
    return text[:1].upper() + text[1:]


def mention(user_id):
    user_id = ''.join(c for c in user_id or '' if c.isdigit())
    return '<@%s>' % user_id if user_id else ''


def post_biome(webhook_url, name, ping=True, server='', previous=None):
    """@everyone only when `ping`."""
    fields = [('Private server', server_field(server), True)]
    if previous:
        fields.append(('Previous', pretty(previous), True))
    post_event(webhook_url, 'Biome Started - %s' % pretty(name), 'Found <t:%d:R>' % time.time(),
               biome_colour(name), 'Biome', fields, '@everyone' if ping else '',
               footer=False)


def post_merchant(webhook_url, name, server=''):
    title = 'Sinister S. has spawned' if name == 'Boss' else 'Merchant Arrived - %s' % name
    post_event(webhook_url, title, 'Found <t:%d:R>' % time.time(),
               MERCHANT_COLOURS.get(name, EMBED_GOLD), 'Merchant', [('Private server', server_field(server), True)],
               footer=False)


def post_shot(webhook_url, title, colour, ping='', detail='', area='Macro', fields=()):
    """Posts a screenshot of Roblox."""
    if not webhook_url:
        return
    buf = io.BytesIO()
    Image.fromarray(game.grab(game.client_box((0.0, 0.0, 1.0, 1.0)))).save(buf, 'PNG')
    post_event(webhook_url, title, detail, colour, area, fields, mention(ping), buf.getvalue())


def append_history(biome):
    """Never raises: a locked folder mustn't stop biome watching."""
    try:
        os.makedirs(os.path.dirname(game.HISTORY_FILE), exist_ok=True)
        with open(game.HISTORY_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'ts': time.time(), 'time': time.strftime('%Y-%m-%d %H:%M:%S'), 'biome': biome}) + '\n')
    except OSError:
        pass


# ================================================================ updates
# swaps the update in once MMacro has closed, then starts it again
SWAP_BAT = r"""@echo off
set sys=%SystemRoot%\System32
set n=0
:wait
"%sys%\tasklist.exe" /FI "PID eq %MMACRO_PID%" 2>nul | "%sys%\find.exe" "%MMACRO_PID%" >nul || goto swap
set /a n+=1
if %n% geq 30 goto swap
"%sys%\PING.EXE" -n 2 127.0.0.1 >nul
goto wait
:swap
set n=0
:again
if "%MMACRO_ZIP%"=="1" (
  "%sys%\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Expand-Archive -Force -LiteralPath $env:MMACRO_NEW -DestinationPath $env:MMACRO_DIR" >nul 2>&1
) else (
  move /y "%MMACRO_NEW%" "%MMACRO_EXE%" >nul 2>&1
)
if not errorlevel 1 goto start
set /a n+=1
if %n% geq 30 goto start
"%sys%\PING.EXE" -n 2 127.0.0.1 >nul
goto again
:start
if "%MMACRO_ZIP%"=="1" del "%MMACRO_NEW%"
start "" "%MMACRO_EXE%"
del "%~f0"
"""


def version_tuple(text):
    return tuple(int(n) for n in re.findall(r'\d+', text or '')[:3])


def folder_build():
    return os.path.isdir(os.path.join(os.path.dirname(sys.executable), '_internal'))


def latest_release():
    """(tag, url, size) of the newest release, or None."""
    req = urllib.request.Request(RELEASES, headers={'User-Agent': TITLE, 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.load(r)
    ext = '.zip' if folder_build() else '.exe'
    asset = next((a for a in d.get('assets', []) if a.get('name', '').lower().endswith(ext)), None)
    return (d.get('tag_name', ''), asset['browser_download_url'], int(asset.get('size') or 0)) if asset else None


def download(url, dest, size, progress=lambda f: None):
    got = 0
    req = urllib.request.Request(url, headers={'User-Agent': TITLE})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, 'wb') as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if size:
                progress(got / size)
    if size and got != size:
        os.remove(dest)
        raise IOError('download cut short (%d of %d bytes)' % (got, size))


def can_write(folder):
    probe = os.path.join(folder, '.mmacro_write_test')
    try:
        with open(probe, 'wb') as f:
            f.write(b'0')
        os.remove(probe)
        return True
    except OSError:
        return False


def install(new, exe, pid, zipped):
    bat = os.path.join(tempfile.gettempdir(), 'mmacro_update_%d.bat' % pid)
    with open(bat, 'w', encoding='ascii') as f:
        f.write(SWAP_BAT)       # paths go in as env vars, a .bat can mangle them
    # so the new exe unpacks its own files
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('_PYI_', '_MEIPASS'))}
    env.update(PYINSTALLER_RESET_ENVIRONMENT='1', MMACRO_NEW=new, MMACRO_EXE=exe, MMACRO_DIR=os.path.dirname(exe), MMACRO_PID=str(pid),
               MMACRO_ZIP='1' if zipped else '0')
    subprocess.Popen(['cmd', '/c', bat], env=env, creationflags=0x08000000 | 0x00000200, close_fds=True)


# ================================================================ widgets
class Check(tk.Canvas):
    """Drawn checkbox."""
    SIDE, R = 20, 5

    def __init__(self, parent, variable, side=None):
        self.pad = 3
        if side:
            self.SIDE, self.R = side, max(3, side // 4)
        tk.Canvas.__init__(self, parent, width=self.SIDE + 6, height=self.SIDE + 6, bg=PANEL,
                           highlightthickness=0, bd=0, cursor='hand2')
        self.var = variable
        self.bind('<Button-1>', lambda e: self.var.set(not self.var.get()))
        self.bind('<Enter>', lambda e: self._draw(True))
        self.bind('<Leave>', lambda e: self._draw(False))
        self.var.trace_add('write', lambda *a: self._draw())
        self._draw()

    def _draw(self, hover=False):
        self.delete('all')
        on = bool(self.var.get())
        p, s, r = self.pad, self.SIDE, self.R
        fill, line = (ACCENT if on else SUNK), (ACCENT if on or hover else EDGE)
        x0, y0, x1, y1 = p, p, p + s, p + s
        corners = ((x0, y0, 90), (x1 - 2 * r, y0, 0), (x0, y1 - 2 * r, 180), (x1 - 2 * r, y1 - 2 * r, 270))
        for cx, cy, start in corners:
            self.create_arc(cx, cy, cx + 2 * r, cy + 2 * r, start=start, extent=90, style='pieslice',
                            fill=fill, outline=fill)
        self.create_rectangle(x0 + r, y0, x1 - r, y1, fill=fill, outline=fill)
        self.create_rectangle(x0, y0 + r, x1, y1 - r, fill=fill, outline=fill)
        for edge in ((x0 + r, y0, x1 - r, y0), (x0 + r, y1, x1 - r, y1), (x0, y0 + r, x0, y1 - r), (x1, y0 + r, x1, y1 - r)):
            self.create_line(*edge, fill=line)
        for cx, cy, start in corners:
            self.create_arc(cx, cy, cx + 2 * r, cy + 2 * r, start=start, extent=90, style='arc', outline=line)
        if on:
            self.create_line(p + s * 0.26, p + s * 0.52, p + s * 0.44, p + s * 0.70, p + s * 0.76, p + s * 0.30,
                             fill=BG, width=2, capstyle='round', joinstyle='round')


class Switch(tk.Canvas):
    """Sliding two- or three-way switch."""
    W, H, SLIDE_MS, STEP_MS = 72, 30, 180, 12

    def __init__(self, parent, variable, options, bg=PANEL):
        self.options = options
        k = parent.winfo_fpixels('1i') / 96.0
        self.w, self.h = int(self.W * k), int(self.H * k)
        tk.Canvas.__init__(self, parent, width=self.w * len(options) + 2, height=self.h + 2, bg=bg,
                           highlightthickness=0, bd=0, cursor='hand2')
        self.var = variable
        self.x = float(self._target())
        self.hover = None
        self._job = None
        self.bind('<Button-1>', lambda e: self.var.set(self.options[self._at(e.x)][0]))
        self.bind('<Motion>', lambda e: self._hover(self._at(e.x)))
        self.bind('<Leave>', lambda e: self._hover(None))
        self.var.trace_add('write', lambda *a: self._slide())
        self._draw()

    def _at(self, x):
        return max(0, min(len(self.options) - 1, int((x - 1) // self.w)))

    def _target(self):
        keys = [k for k, _ in self.options]
        value = self.var.get()
        return 1 + self.w * (keys.index(value) if value in keys else 0)

    def _hover(self, i):
        if i != self.hover:
            self.hover = i
            self._draw()

    def _slide(self):
        if self._job is not None:
            self.after_cancel(self._job)
        start, end, t0 = self.x, self._target(), time.perf_counter()

        def step():
            f = min(1.0, (time.perf_counter() - t0) * 1000.0 / self.SLIDE_MS)
            self.x = start + (end - start) * (1 - (1 - f) ** 3)
            self._draw()
            self._job = self.after(self.STEP_MS, step) if f < 1 else None
        step()

    def _pill(self, x0, y0, x1, y1, r, **kw):
        pts = (x0 + r, y0, x1 - r, y0, x1, y0, x1, y0 + r, x1, y1 - r, x1, y1, x1 - r, y1, x0 + r, y1,
               x0, y1, x0, y1 - r, x0, y0 + r, x0, y0)
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        self.delete('all')
        n, w, h = len(self.options), self.w, self.h
        r = h // 2
        self._pill(0, 0, n * w + 1, h + 1, r, fill=SUNK, outline=EDGE)
        self._pill(self.x + 2, 3, self.x + w - 2, h - 2, r - 3, fill=ACCENT, outline=ACCENT)
        picked = self._at(self.x + w / 2)
        for i, (_, text) in enumerate(self.options):
            colour = BG if i == picked else TEXT if i == self.hover else DIM
            self.create_text(1 + w * i + w / 2, h / 2 + 1, text=text, fill=colour, font=(UIB, 9))


def card(parent, **pack):
    f = tk.Frame(parent, bg=PANEL, highlightthickness=1, highlightbackground=EDGE, highlightcolor=EDGE)
    f.pack(**pack)
    return f


def rule(parent, padx=22):
    tk.Frame(parent, bg=EDGE, height=1).pack(fill='x', padx=padx)


def entry(parent, var, **kw):
    return tk.Entry(parent, textvariable=var, bg=SUNK, fg=TEXT, insertbackground=ACCENT, relief='flat',
                    highlightthickness=1, highlightbackground=EDGE, highlightcolor=ACCENT, **kw)


class Calibrate(tk.Toplevel):
    """Button calibrator. Set records your next click, which still reaches Roblox."""

    def __init__(self, app, points=None):
        tk.Toplevel.__init__(self, app.root, bg=BG)
        self.app = app
        self.only = points is not None          # only these buttons (Play, Contract)
        sections = [(None, points)] if points else [
            ('Items (Auto SC + BR)', game.POINTS), ('Fishing', game.FISH_POINTS),
            ('Merchant collection', game.MERCHANT_POINTS), ('Daily rewards (optional)', game.DAILY_POINTS)]
        self.points = [p for _, group in sections for p in group]
        self.capturing = None
        self.banner = None
        self.title('Calibrate buttons')
        tall = 230 + 52 * len(self.points) if points else 520
        self.geometry('460x%d' % min(tall, self.winfo_screenheight() - 140))
        self.minsize(420, 300)                  # list scrolls if it doesn't fit
        self.configure(bg=BG)
        self.transient(app.root)
        self.protocol('WM_DELETE_WINDOW', self.finish)

        head = tk.Frame(self, bg=BG)
        head.pack(fill='x', padx=22, pady=(20, 12))
        tk.Label(head, text='Buttons', bg=BG, fg=TEXT, font=(UIB, 14)).pack(anchor='w')
        tk.Label(head, text='Every button works out of the box (auto). Only if a click misses: Test shows where it '
                 'clicks, Set lets you click the right spot in Roblox.',
                 bg=BG, fg=DIM, font=(UI, 9), wraplength=400, justify='left', anchor='w').pack(fill='x', pady=(4, 0))

        bar = tk.Frame(self, bg=BG)
        bar.pack(side='bottom', fill='x', padx=22, pady=16)
        scroll = app._scroller(self)
        self.rows, self.sections = {}, []
        for heading, group in sections:
            box = card(scroll, fill='x', padx=22, pady=(0, 10))
            inner = tk.Frame(box, bg=PANEL)
            if heading:
                top = tk.Frame(box, bg=PANEL, cursor='hand2')
                top.pack(fill='x', padx=18, pady=10)
                arrow = tk.Label(top, text='\u25b8', bg=PANEL, fg=DIM, font=(UIB, 10), cursor='hand2')
                arrow.pack(side='left')
                tk.Label(top, text=heading, bg=PANEL, fg=TEXT, font=(UIB, 10), cursor='hand2').pack(side='left', padx=(6, 0))
                summary = tk.Label(top, text='', bg=PANEL, fg=DIM, font=(UI, 9), cursor='hand2')
                summary.pack(side='right')
                toggle = lambda e=None, i=inner, a=arrow: self._fold(i, a)
                for w in (top, arrow, summary) + tuple(top.winfo_children()):
                    w.bind('<Button-1>', toggle)
                self.sections.append(([n for n, _ in group], summary))
            else:
                inner.pack(fill='x', pady=(4, 4))
            for i, (name, what) in enumerate(group):
                if i:
                    rule(inner, 18)
                self.rows[name] = self._row(inner, name, what)

        self.done_b = tk.Button(bar, text='Done', command=self.finish, bg=ACCENT, fg=BG, activebackground=ACCENT,
                                activeforeground=BG, relief='flat', font=(UIB, 10), pady=9, cursor='hand2',
                                borderwidth=0)
        self.done_b.pack(fill='x')
        self._refresh()

    def _fold(self, inner, arrow):
        if inner.winfo_manager():
            inner.pack_forget()
            arrow.configure(text='\u25b8')
        else:
            inner.pack(fill='x', pady=(0, 6))
            arrow.configure(text='\u25be')

    def _row(self, parent, name, what):
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill='x', padx=18, pady=5)
        tick = tk.Label(row, text='', bg=PANEL, fg=GOOD, font=(UIB, 8), width=4, anchor='w')
        tick.pack(side='left')
        tk.Label(row, text=what, bg=PANEL, fg=TEXT, font=(UI, 9), anchor='w').pack(side='left', fill='x', expand=True)
        quiet = dict(bg=SUNK, fg=DIM, activebackground=SUNK, activeforeground=ACCENT, relief='flat', font=(UI, 9),
                     padx=10, pady=3, cursor='hand2', borderwidth=0)
        b = tk.Button(row, text='Set', command=lambda: self.capture(name), padx=14, **SMALL_BUTTON)
        b.pack(side='right')
        test = tk.Button(row, text='Test', command=lambda: self.show(name), **quiet)
        test.pack(side='right', padx=(0, 6))
        reset = tk.Button(row, text='Reset', command=lambda: self.reset(name), **quiet) if name in game.BUILT_IN else None
        return tick, b, test, reset

    def show(self, name):
        """Move the pointer to the click spot without clicking."""
        at = game.point_at(name)
        if at is not None:
            game.glide(*at)

    def reset(self, name):
        game.forget_point(name)
        self._refresh()

    def _refresh(self):
        stored = game.load_points()
        for name, (tick, b, test, reset) in self.rows.items():
            done = name in stored
            tick.configure(text='set' if done else 'auto' if name in game.BUILT_IN else 'not set',
                           fg=GOOD if done else DIM)
            b.configure(text='Redo' if done else 'Set')
            if reset is not None:
                if done and not reset.winfo_manager():
                    reset.pack(side='right', padx=(0, 6), before=test)
                elif not done and reset.winfo_manager():
                    reset.pack_forget()
        for names, summary in self.sections:
            n = sum(1 for name in names if name in stored)
            summary.configure(text='%d set' % n if n else 'all auto' if all(x in game.BUILT_IN for x in names)
                              else 'not set', fg=GOOD if n else DIM)
        optional = set() if self.only else {n for n, _ in game.DAILY_POINTS}
        left = [n for n, _ in self.points if n not in stored and n not in optional and n not in game.BUILT_IN]
        self.done_b.configure(text='Done' if not left else 'Done  (%d still to set)' % len(left))

    def capture(self, name):
        if self.capturing:
            return
        self.capturing = name
        self.withdraw()
        self.banner = self._make_banner('Click %s      (Esc to cancel)' % dict(self.points)[name])
        self._got = []

        def on_click(x, y, button, pressed):
            if pressed and button == mouse.Button.left:
                self._got.append((x, y))
                return False

        self._listener = mouse.Listener(on_click=on_click)
        self._listener.start()
        self.after(60, self._poll)

    def _make_banner(self, text):
        top = tk.Toplevel(self, bg=ACCENT)
        top.overrideredirect(True)
        top.attributes('-topmost', True)
        tk.Label(top, text=text, bg=ACCENT, fg=BG, font=(UIB, 12), padx=26, pady=12).pack()
        top.update_idletasks()
        top.geometry('+%d+%d' % (max(0, (top.winfo_screenwidth() - top.winfo_reqwidth()) // 2), 40))
        top.bind('<Escape>', lambda e: self._cancel())
        self.bind_all('<Escape>', lambda e: self._cancel())
        return top

    def _poll(self):
        if not self.capturing:
            return
        if self._got:
            try:
                game.save_point(self.capturing, game.to_fraction(*self._got[0]))
            except Exception:
                pass
            self._end_capture()
        elif not self._listener.running:
            self._end_capture()
        else:
            self.after(60, self._poll)

    def _cancel(self):
        if self.capturing:
            self._end_capture()

    def _end_capture(self):
        self.capturing = None
        try:
            self._listener.stop()
        except Exception:
            pass
        if self.banner is not None:
            self.banner.destroy()
            self.banner = None
        self.unbind_all('<Escape>')
        self.deiconify()
        self.lift()
        self._refresh()

    def finish(self):
        self._cancel()
        if getattr(self, 'only', False):
            self.app._cal_window = None
            self.destroy()
            return
        self.app.phase('calibrated buttons saved', GOOD)
        self.app._cal_window = None
        self.destroy()


# ================================================================ the window
class Toast:
    """Click-through notice over Roblox that never takes focus."""
    _place = ctypes.WinDLL('user32').SetWindowPos
    _place.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                       ctypes.c_uint]
    TOPMOST = ctypes.c_void_p(-1 & 0xFFFFFFFFFFFFFFFF)     # HWND_TOPMOST as a 64-bit handle

    def __init__(self, root):
        u32 = ctypes.windll.user32
        self.top = tk.Toplevel(root, bg=EDGE)
        self.top.overrideredirect(True)
        self.top.attributes('-topmost', True)
        self.top.attributes('-alpha', 0.94)
        self.label = tk.Label(self.top, bg=SUNK, fg=TEXT, font=(UIB, 12), padx=22, pady=10, wraplength=720,
                              justify='center')
        self.label.pack(padx=1, pady=1)
        self.top.withdraw()
        self.top.update_idletasks()
        self.hwnd = u32.GetParent(self.top.winfo_id()) or self.top.winfo_id()
        ex = u32.GetWindowLongW(self.hwnd, -20)
        # no activate, no taskbar button, click-through, layered
        u32.SetWindowLongW(self.hwnd, -20, ex | 0x08000000 | 0x80 | 0x20 | 0x80000)
        self.job = None

    def show(self, text, colour=TEXT, ms=2200):
        self.label.configure(text=text, fg=colour)
        self.top.update_idletasks()
        w, h = self.top.winfo_reqwidth(), self.top.winfo_reqheight()
        x, y, cw = 0, 0, self.top.winfo_screenwidth()
        try:
            win = game.find_roblox_window()
            if win is not None:
                x, y, cw, _ = game.client_rect(win)
        except Exception:
            pass
        self._place(self.hwnd, self.TOPMOST, x + (cw - w) // 2, y + 40, w, h, 0x0010 | 0x0040)   # no activate, show
        if self.job is not None:
            self.top.after_cancel(self.job)
        self.job = self.top.after(ms, self.hide)

    def hide(self):
        self.job = None
        ctypes.windll.user32.ShowWindow(self.hwnd, 0)


class App:
    def __init__(self, root):
        self.root = root
        self.running = False
        self.biome_stop = None
        self._last_hotkey = {}
        self._closing = False
        self._cal_window = None
        self.url = ''
        self.use_items = False
        self.server_link = ''
        self.reconnect_on = False
        self.browser_rejoin = False
        self.slow_pc = False
        self.need_rejoin = None
        self.start_again = False
        self.item_due = {}
        self._toast = None
        self._key_stop = False          # F2 stopped it: say 'stopped' once done
        self.played = False             # Play pressed in a run: claim daily rewards once back in
        self.rejoining = False
        self.watch = None
        self.merchant_detect = False
        self.block_on = False       # copy for the cache thread (Tk vars are UI-thread only)
        self.blocked = {}           # file key: when Roblox last read the real one (ms)
        self.block_path = None
        self.block_lock = threading.Lock()
        self.got_past_block = False  # Roblox has a real animation in memory: reopen it
        self.merchant_due = None    # merchant waiting to be collected
        self.merchant_at = 0.0
        self._merchant_posted = {}  # merchant: last posted
        self.collect = False
        self.wanted = {}
        self.collect_names = set()  # ticked under Teleport to
        self.clipper = None         # only during a run with clipping on
        self.clip_min = 0
        self.equip_aura = None
        self.crack_on = False       # Eden on: Portable Crack after a merchant or rejoin
        self.in_dimension = True    # in Eden's dimension; merchants and rejoins leave it
        self.equip_due = None       # next Aura Storage check (monotonic), None = not due
        self.equip_busy_at = 0.0    # so our own equip isn't clipped as a roll
        self.aura_logged = (None, 0.0)      # (aura, wall time) from the log
        self.run_wall = 0.0                 # run start, wall clock
        self.equip_fails = 0                # failed equips in a row, for backoff
        self.joined_at = 0.0                # last (re)join, monotonic
        self.biome_now = ''
        self.fisher = None
        self.out_since = None
        self._look_at = self._played = 0.0
        self.beat = time.monotonic()    # watchdog heartbeat
        self.restart_run = False
        self.run_id = 0             # old connection watchers quit when this changes
        self.updates = queue.Queue()
        self.cfg = game.load_settings()

        root.title(TITLE)
        try:
            root.iconbitmap(default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico'))
        except tk.TclError:
            pass
        root.configure(bg=BG)
        k = root.winfo_fpixels('1i') / 96.0
        w = min(int(470 * k), root.winfo_screenwidth() - 40)
        root.geometry('%dx%d' % (w, int(900 * k)))
        self.body = self._scroller(root)
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.report_callback_exception = self._oops

        self._header()
        self.pages = {k: tk.Frame(self.body, bg=BG) for k in ('macro', 'fishing', 'merchant', 'eden', 'credits')}
        self._settings_card(self.pages['macro'])
        self._biome_card(self.pages['macro'])
        self._fishing_card(self.pages['fishing'])
        self._merchant_card(self.pages['merchant'])
        self._eden_card(self.pages['eden'])
        self._credits_card(self.pages['credits'])
        if self.eden_on.get() and self.fish_on.get():
            self.fish_on.set(False)                     # old settings could have both; keep Eden
        self.eden_on.trace_add('write', lambda *a: self._one_of(self.eden_on, self.fish_on, 'Auto fishing'))
        self.fish_on.trace_add('write', lambda *a: self._one_of(self.fish_on, self.eden_on, 'Eden detector'))
        self._buttons()
        self._footer()
        self.tab.trace_add('write', self._show_tab)
        self._show_tab()
        root.update_idletasks()
        h = min(self.body.winfo_reqheight(), root.winfo_screenheight() - 80)
        root.geometry('%dx%d+%d+%d' % (w, h, max(0, (root.winfo_screenwidth() - w) // 2), 20))
        root.minsize(min(w, int(360 * k)), min(h, int(300 * k)))

        self.phase('idle', DIM)
        self.cache = merchant_cache.Tracker()
        threading.Thread(target=self._watch_cache, daemon=True).start()
        self.remember()
        self._autosave()
        self._hotkeys()
        root.after(100, self._pump)
        self.updating = self.ran = False
        self.check_update()
        threading.Thread(target=self._fetch_auras, daemon=True).start()

    def _fetch_auras(self):
        try:
            note('clip', 'aura list from GitHub: %d auras' % clipper.refresh())
        except Exception as e:
            note('clip', 'aura list not fetched, using the saved one: %s: %s' % (type(e).__name__, e))

    # ----------------------------------------------------------------- layout
    def _scroller(self, root):
        canvas = tk.Canvas(root, bg=BG, highlightthickness=0, yscrollincrement=20)
        canvas.pack(fill='both', expand=True)
        body = tk.Frame(canvas, bg=BG)
        win = canvas.create_window((0, 0), window=body, anchor='nw')
        taller = lambda: body.winfo_reqheight() > canvas.winfo_height()

        def fit(_=None):
            canvas.configure(scrollregion=canvas.bbox('all'))
            if not taller():
                canvas.yview_moveto(0)
        body.bind('<Configure>', fit)
        canvas.bind('<Configure>', lambda e: (canvas.itemconfigure(win, width=e.width), fit()))
        root.bind('<MouseWheel>', lambda e: taller() and canvas.yview_scroll(int(-e.delta / 40), 'units'))
        return body

    def _header(self):
        bar = tk.Frame(self.body, bg=BG)
        bar.pack(fill='x', padx=16, pady=(12, 0))
        self.tab = tk.StringVar(value='macro')
        tk.Label(bar, text=TITLE, bg=BG, fg=TEXT, font=(UIB, 18)).pack(anchor='w')
        tk.Label(bar, text='Biome alerts, auto reconnect, fishing, merchants and Eden.', bg=BG, fg=DIM,
                 font=(UI, 9)).pack(anchor='w', pady=(3, 0))
        Switch(bar, self.tab, (('macro', 'Macro'), ('fishing', 'Fishing'), ('merchant', 'Merchant'), ('eden', 'Eden'),
                             ('credits', 'Credits')),
               bg=BG).pack(anchor='w', pady=(10, 0))

    def _show_tab(self, *_):
        for name, page in self.pages.items():
            page.pack_forget()
        self.pages[self.tab.get()].pack(fill='x', before=self.button_bar)
        self.root.after_idle(self._fit_window)

    def _settings_card(self, parent):
        box = card(parent, fill='x', padx=16, pady=10)
        self.auto_items = self._toggle(box, 'Auto SC + BR', 'use a Strange Controller and a Biome Randomizer as each '
                                       'runs out', 'auto_items')
        rule(box)
        self.anti_afk = self._toggle(box, 'Anti-AFK', 'jump twice every 5 minutes so Roblox does not kick for idling',
                                     'anti_afk')
        rule(box)
        self.merchant_on = self._toggle(box, 'Merchant detection', 'Detects Mari, Jester, Rin and the boss through '
                                        'Roblox\'s cache', 'merchant_on')
        self.block_on = bool(self.merchant_on.get())
        self.merchant_on.trace_add('write', self._merchant_toggled)
        rule(box)
        self.clip_on = tk.BooleanVar(value=bool(self.cfg.get('clip_on')))
        row, text = self._row(box, 'Clip rare auras', 'saves the %d s before and %d s after one is rolled'
                              % (clipper.BEFORE_S, clipper.AFTER_S), lambda r: Check(r, self.clip_on))
        tk.Button(row, text='Clips', command=self._open_clips, padx=12, **SMALL_BUTTON).pack(side='right', padx=(12, 0),
                                                                                         before=text)
        line = tk.Frame(text, bg=PANEL)
        line.pack(fill='x', pady=(4, 0))
        tk.Label(line, text='from 1 in', bg=PANEL, fg=DIM, font=(UI, 8)).pack(side='left')
        self.clip_from = tk.StringVar(value=str(self.cfg.get('clip_min', '1,000,000,000')))
        entry(line, self.clip_from, width=14, justify='center', font=('Consolas', 9)).pack(side='left', padx=(6, 0), ipady=1)
        tk.Label(line, text='quality', bg=PANEL, fg=DIM, font=(UI, 8)).pack(side='left', padx=(12, 0))
        q = self.cfg.get('clip_quality')
        self.clip_quality = tk.StringVar(value=q if q in clipper.HEIGHTS else '768p')
        tk.Button(line, textvariable=self.clip_quality, padx=8, **dict(SMALL_BUTTON, font=('Consolas', 9), pady=1),
                  command=self._next_quality).pack(side='left', padx=(6, 0))
        keys = tk.Frame(text, bg=PANEL)
        keys.pack(fill='x', pady=(4, 0))
        self.clip_key_on = tk.BooleanVar(value=bool(self.cfg.get('clip_key_on')))
        Check(keys, self.clip_key_on, side=14).pack(side='left')
        tk.Label(keys, text='use my recorder, key', bg=PANEL, fg=DIM, font=(UI, 8)).pack(side='left', padx=(6, 0))
        self.clip_keys = tk.StringVar(value=self.cfg.get('clip_keys') or 'Win+Alt+G')
        self.clip_key_button = tk.Button(keys, textvariable=self.clip_keys, command=self._set_clip_keys, padx=8,
                                         **dict(SMALL_BUTTON, font=('Consolas', 9), pady=1))
        self.clip_key_button.pack(side='left', padx=(6, 0))
        tk.Label(text, text='Game Bar, Medal...: click it, then press your clip key', bg=PANEL, fg=DIM,
                 font=(UI, 8), anchor='w').pack(fill='x', pady=(2, 0))
        rule(box)
        self.equip_on = tk.BooleanVar(value=bool(self.cfg.get('equip_on')))
        row, text = self._row(box, 'Keep an aura equipped', 'after any roll, puts this aura back on',
                              lambda r: Check(r, self.equip_on))
        line = tk.Frame(text, bg=PANEL)
        line.pack(fill='x', pady=(4, 0))
        self.equip_name = tk.StringVar(value=self.cfg.get('equip_aura', ''))
        name_box = entry(line, self.equip_name, width=24, font=(UI, 9))
        name_box.pack(side='left', ipady=1)
        self.equip_hint = tk.Label(line, text='', bg=PANEL, fg=DIM, font=(UI, 8), anchor='w')
        self.equip_hint.pack(side='left', padx=(6, 0))
        name_box.bind('<FocusOut>', lambda e: self._correct_aura())
        name_box.bind('<Return>', lambda e: self._correct_aura())
        self._correct_aura(quiet=True)
        rule(box)
        self._row(box, 'Buttons', 'found from your Roblox window size; calibrate only if a click misses',
                  lambda r: tk.Button(r, text='Calibrator', command=self.calibrate, padx=12, **SMALL_BUTTON))
        rule(box)
        self.auto_reconnect = tk.BooleanVar(value=bool(self.cfg.get('auto_reconnect')))
        row, text = self._row(box, 'Auto reconnect', 'rejoin the private server after a disconnect; Play is clicked '
                           '%d s after it opens (Set Play only if it misses)' % game.PLAY_AFTER_S,
                           lambda r: Check(r, self.auto_reconnect))
        tk.Button(row, text='Set Play', command=lambda: self.calibrate(game.PLAY_POINT), padx=12,
                  **SMALL_BUTTON).pack(side='right', padx=(12, 0), before=text)
        rule(box)
        self.rejoin_browser = self._toggle(box, 'Rejoin through browser', 'for PCs where the Roblox link does not open '
                                           'the game: the private server opens in your browser instead', 'rejoin_browser')
        rule(box)
        self.low_end = self._toggle(box, 'Potato PC', 'slower menus and clicks for PCs that lag', 'low_end')

    def _eden_card(self, parent):
        box = card(parent, fill='x', padx=16, pady=10)
        self.eden_on = self._toggle(box, 'Eden detector', 'watch the screen for Eden while the macro runs, and post '
                                    'it to the Discord webhook on the Macro tab', 'eden_on')
        rule(box)
        self.eden_path = tk.BooleanVar(value=bool(self.cfg.get('eden_path')))
        row, text = self._row(box, 'Walk to Eden', '', lambda r: Check(r, self.eden_path))
        tk.Button(row, text='Set Contract', command=lambda: self.calibrate(eden.POINTS), padx=12,
                  **SMALL_BUTTON).pack(side='right', padx=(12, 0), before=text)
        rule(box)
        self.eden_record = self._toggle(box, 'Record Eden', '60 s video of Roblox once Eden shows, saved in '
                                        '%LOCALAPPDATA%\\MMacro', 'eden_record')
        rule(box)
        tk.Label(box, text='ID', bg=PANEL, fg=TEXT, font=(UIB, 10), anchor='w').pack(fill='x', padx=18, pady=(10, 3))
        self.eden_ping = tk.StringVar(value=self.cfg.get('eden_ping', ''))
        entry(box, self.eden_ping, font=('Consolas', 9)).pack(fill='x', padx=22, ipady=6)
        hint = tk.Label(box, text='Discord user id pinged for Eden',
                        bg=PANEL, fg=DIM, font=(UI, 8), anchor='w', justify='left')
        hint.pack(fill='x', padx=18, pady=(4, 12))
        hint.bind('<Configure>', lambda e: hint.configure(wraplength=e.width))

    def _credits_card(self, parent):
        box = card(parent, fill='x', padx=16, pady=10)
        self.pfps = []
        for pfp, name, *what in (('axolotl.png', 'Manas', 'Solo developer and creator of MMacro'),
                                 ('coteab.png', '@criticize.', 'Fishing logic from Coteab',
                                  'took like 2% but he wants to aurafarm so hes on here now ig')):
            row = tk.Frame(box, bg=PANEL)
            row.pack(fill='x', padx=18, pady=14)
            try:
                img = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), pfp)).resize((72, 72))
                self.pfps.append(ImageTk.PhotoImage(img))
                tk.Label(row, image=self.pfps[-1], bg=PANEL).pack(side='left', padx=(0, 14))
            except (OSError, tk.TclError):
                pass
            text = tk.Frame(row, bg=PANEL)
            text.pack(side='left', fill='x', expand=True)
            top = tk.Frame(text, bg=PANEL)
            top.pack(fill='x')
            tk.Label(top, text=name, bg=PANEL, fg=TEXT, font=(UIB, 12), anchor='w').pack(side='left')
            if name == 'Manas':
                link = tk.Label(top, text=INVITE.split('//')[-1], bg=PANEL, fg=ACCENT, font=(UI, 9), cursor='hand2')
                link.pack(side='left', padx=(10, 0))
                link.bind('<Button-1>', lambda e: webbrowser.open(INVITE))
                link.bind('<Enter>', lambda e: e.widget.configure(font=(UI, 9, 'underline')))
                link.bind('<Leave>', lambda e: e.widget.configure(font=(UI, 9)))
            for i, line in enumerate(what):
                label = tk.Label(text, text=line, bg=PANEL, fg=DIM, font=(UI, 9 if i == 0 else 7), anchor='w',
                                 justify='left')
                label.pack(fill='x', pady=(2, 0))
                label.bind('<Configure>', lambda e: e.widget.configure(wraplength=e.width))
            rule(box)
        tk.Label(box, text='Testers', bg=PANEL, fg=TEXT, font=(UIB, 10), anchor='w').pack(fill='x', padx=18,
                                                                                        pady=(12, 3))
        names = tk.Label(box, text=' · '.join(TESTERS), bg=PANEL, fg=DIM, font=(UI, 9), anchor='w', justify='left')
        names.pack(fill='x', padx=18, pady=(0, 14))
        names.bind('<Configure>', lambda e: names.configure(wraplength=e.width))

    def _fishing_card(self, parent):
        box = card(parent, fill='x', padx=16, pady=10)
        self.fish_on = self._toggle(box, 'Auto fishing', 'walks to the ocean, selling at Captain Flarg on the way, '
                                    'and fishes', 'fish_on')
        rule(box)
        self.fish_vip = self._toggle(box, 'VIP', 'untick if you do not own VIP', 'fish_vip')
        rule(box)
        self.fish_sell = self._field(box, 'Sell every', str(self.cfg.get('fish_sell', 0)),
                                     'fish caught, then go back to sell (0 = off)')
        rule(box)
        self.fish_sell_all = self._toggle(box, 'Sell all', 'reads the fish count and sells until it is 0; untick '
                                          'to use Sell amount', 'fish_sell_all')
        rule(box)
        self.fish_full_check = self._toggle(box, 'Full bag check', 'reads the "not enough inventory space" note: sells, '
                                            'and rejoins if it is still full right after selling', 'fish_full_check')
        rule(box)
        self.fish_sell_amount = tk.StringVar(value=str(self.cfg.get('fish_sell_amount', 10)))
        amount = []
        self._row(box, 'Sell amount', 'kinds of fish sold each time, with Sell all off',
                  lambda r: amount.append(entry(r, self.fish_sell_amount, width=6, justify='center', font=('Consolas', 12),
                                                disabledbackground=PANEL, disabledforeground=DIM)) or amount[0], ipady=6)
        lock = lambda *_: amount[0].configure(state='disabled' if self.fish_sell_all.get() else 'normal')
        self.fish_sell_all.trace_add('write', lock)
        lock()
        tk.Frame(box, bg=PANEL, height=6).pack()

    def _merchant_card(self, parent):
        box = card(parent, fill='x', padx=16, pady=10)
        self.collect_on = self._toggle(box, 'Auto merchant collection', 'when a merchant arrives, teleport to it and '
                                       'buy the chosen items (needs Merchant detection and a Merchant Teleporter)',
                                       'collect_on')
        rule(box)
        row = tk.Frame(box, bg=PANEL)
        row.pack(fill='x', padx=18, pady=(10, 4))
        tk.Label(row, text='Teleport to', bg=PANEL, fg=TEXT, font=(UIB, 10)).pack(side='left')
        names = ['Jester', 'Mari', 'Rin']
        picked = self.cfg.get('collect_merchants', names)
        picked = picked if isinstance(picked, list) else names
        self.collect_from = {}
        for name in reversed(names):
            var = tk.BooleanVar(value=name in picked)
            tk.Label(row, text=name, bg=PANEL, fg=TEXT, font=(UI, 9)).pack(side='right', padx=(4, 10))
            Check(row, var, side=16).pack(side='right')
            var.trace_add('write', lambda *_: self._autosave_later())
            self.collect_from[name] = var
        rule(box)
        head = tk.Frame(box, bg=PANEL)
        head.pack(fill='x', padx=18, pady=(10, 0))
        tk.Label(head, text='Items to buy', bg=PANEL, fg=TEXT, font=(UIB, 10), anchor='w').pack(side='left')
        self.buy_count = tk.Label(head, text='', bg=PANEL, fg=ACCENT, font=(UIB, 9))
        self.buy_count.pack(side='right')
        tk.Label(box, text='Pick from the list or type a name. Amount empty = as many as the shop sells. None = the '
                 'shop is only read and posted.', bg=PANEL, fg=DIM, font=(UI, 8), anchor='w', justify='left',
                 wraplength=380).pack(fill='x', padx=18, pady=(2, 6))
        add = tk.Frame(box, bg=PANEL)
        add.pack(fill='x', padx=18, pady=(0, 6))
        self.new_item = tk.StringVar()
        field = entry(add, self.new_item, font=(UI, 9))
        field.pack(side='left', fill='x', expand=True, ipady=5)
        field.bind('<Return>', lambda e: self._add_item())
        tk.Button(add, text='Add', command=self._add_item, padx=12, **SMALL_BUTTON).pack(side='right', padx=(6, 0))
        pick = tk.Button(add, text='List ▾', padx=10, **SMALL_BUTTON)
        pick.configure(command=lambda: self._item_menu(pick))
        pick.pack(side='right', padx=(6, 0))
        self.items_box = tk.Frame(box, bg=PANEL)
        self.items_box.pack(fill='x', padx=12, pady=(0, 10))
        self.item_rows = {}                             # name: (on, amount, row)
        saved = self.cfg.get('buy_items')
        saved = dict(saved) if isinstance(saved, dict) else {}
        for name, amount in shop.wanted_from_text(self.cfg.get('buy_list', '')).items():    # old text box setting
            saved.setdefault(shop.identify(name, shop.KNOWN_ITEMS) or name, {'on': True, 'qty': amount or ''})
        for name, item in saved.items():
            if isinstance(item, dict) and item.get('on'):
                self._item_row(name, item)
        self._count_items()

    def _item_row(self, name, saved):
        on = tk.BooleanVar(value=True)
        qty = tk.StringVar(value=str(saved.get('qty') or ''))
        row = tk.Frame(self.items_box, bg=PANEL)
        row.pack(fill='x', pady=1)
        tk.Label(row, text=name, bg=PANEL, fg=ACCENT, font=(UI, 9), anchor='w').pack(side='left', padx=(6, 0))
        tk.Button(row, text='✕', command=lambda: self._drop_item(name), padx=6, **SMALL_BUTTON).pack(side='right',
                                                                                                     padx=(6, 6))
        entry(row, qty, width=5, justify='center', font=('Consolas', 9)).pack(side='right', ipady=2)
        tk.Label(row, text='Amount', bg=PANEL, fg=DIM, font=(UI, 8)).pack(side='right', padx=(0, 6))
        qty.trace_add('write', lambda *_: self._autosave_later())
        self.item_rows[name] = (on, qty, row)

    def _item_menu(self, button):
        if getattr(self, '_menu', None) is not None:
            self._menu.destroy()                        # old menus never got freed
        menu = self._menu = tk.Menu(self.root, tearoff=0, bg=SUNK, fg=TEXT, activebackground=ACCENT, activeforeground=BG,
                       font=(UI, 9), relief='flat', borderwidth=0)
        for name in shop.KNOWN_ITEMS:
            if name not in self.item_rows:
                menu.add_command(label=name, command=lambda n=name: (self.new_item.set(n), self._add_item()))
        menu.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())

    def _add_item(self):
        name = ' '.join(self.new_item.get().split())
        if not name:
            return
        name = shop.identify(name, shop.KNOWN_ITEMS) or name
        name = next((n for n in self.item_rows if n.lower() == name.lower()), name)
        if name not in self.item_rows:
            self._item_row(name, {})
        self.new_item.set('')
        self._count_items()
        self._autosave_later()
        self.root.after_idle(self._fit_window)

    def _drop_item(self, name):
        self.item_rows.pop(name)[2].destroy()
        self._count_items()
        self._autosave_later()
        self.root.after_idle(self._fit_window)

    def _count_items(self):
        if hasattr(self, 'buy_count'):
            n = sum(1 for on, _, _ in self.item_rows.values() if on.get())
            self.buy_count.configure(text='%d chosen' % n if n else '')

    def wanted_items(self):
        """{name: amount}, None = as many as the shop has."""
        out = {}
        for name, (on, qty, _) in self.item_rows.items():
            if on.get():
                q = qty.get().strip()
                out[name] = int(q) if q.isdigit() and int(q) > 0 else None
        return out

    def _fit_window(self):
        """Fit the window to its contents, up to the screen."""
        self.root.update_idletasks()
        h = min(self.body.winfo_reqheight(), self.root.winfo_screenheight() - 80)
        if h != self.root.winfo_height():
            self.root.geometry('%dx%d' % (self.root.winfo_width(), h))

    def _row(self, parent, label, hint, widget, **pack):
        """Label and hint on the left, control on the right."""
        row = tk.Frame(parent, bg=PANEL)
        row.pack(fill='x', padx=18, pady=6)
        widget(row).pack(side='right', padx=(12, 0), **pack)
        text = tk.Frame(row, bg=PANEL)
        text.pack(side='left', fill='x', expand=True)
        tk.Label(text, text=label, bg=PANEL, fg=TEXT, font=(UIB, 10), anchor='w').pack(fill='x')
        if hint:
            note = tk.Label(text, text=hint, bg=PANEL, fg=DIM, font=(UI, 8), anchor='w', justify='left', wraplength=300)
            note.pack(fill='x', pady=(2, 0))
            text.bind('<Configure>', lambda e: note.configure(wraplength=max(100, e.width)))
        return row, text

    def _field(self, parent, label, default, hint):
        var = tk.StringVar(value=default)
        self._row(parent, label, hint, lambda r: entry(r, var, width=6, justify='center', font=('Consolas', 12)),
                  ipady=6)
        return var

    def _toggle(self, parent, label, hint, key):
        var = tk.BooleanVar(value=bool(self.cfg.get(key)))
        self._row(parent, label, hint, lambda r: Check(r, var))
        return var

    def _buttons(self):
        bar = self.button_bar = tk.Frame(self.body, bg=BG)
        bar.pack(fill='x', padx=16, pady=(0, 10))
        self.start_b = self._button(bar, 'Start', self.start, ACCENT, BG)
        self.stop_b = self._button(bar, 'Stop', self.stop, PANEL, TEXT)
        self.stop_b.configure(state='disabled')

    def _button(self, parent, text, cmd, bg, fg):
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                      relief='flat', disabledforeground=DIM, font=(UIB, 10), pady=9, cursor='hand2', borderwidth=0,
                      highlightthickness=1, highlightbackground=EDGE)
        b.pack(side='left', fill='x', expand=True, padx=(0, 10))
        return b

    def _biome_card(self, parent):
        box = card(parent, fill='x', padx=16, pady=(0, 10))
        tk.Label(box, text='Discord webhook', bg=PANEL, fg=TEXT, font=(UIB, 10), anchor='w').pack(fill='x', padx=18, pady=(10, 3))
        self.webhook = tk.StringVar(value=self.cfg.get('webhook_url', ''))
        entry(box, self.webhook, show='•', font=('Consolas', 9)).pack(fill='x', padx=22, ipady=6)
        tk.Label(box, text='Biome, Eden and failsafe notifier', bg=PANEL, fg=DIM, font=(UI, 8), anchor='w').pack(fill='x', padx=18, pady=(4, 8))
        tk.Label(box, text='Private server link', bg=PANEL, fg=TEXT, font=(UIB, 10), anchor='w').pack(fill='x', padx=22, pady=(0, 4))
        self.server = tk.StringVar(value=self.cfg.get('private_server', ''))
        entry(box, self.server, font=('Consolas', 9)).pack(fill='x', padx=22, ipady=6)
        tk.Label(box, text='Used for auto reconnect and for biome notifications', bg=PANEL, fg=DIM, font=(UI, 8),
                 anchor='w').pack(fill='x', padx=18, pady=(4, 8))
        tk.Frame(box, bg=PANEL, height=4).pack()

    def _footer(self):
        bar = tk.Frame(self.body, bg=BG)
        bar.pack(fill='x', padx=16, pady=(2, 10))
        strip = tk.Frame(bar, bg=BG)
        strip.pack()
        tk.Label(strip, text='F1 start   F2 stop        Made by Manas', bg=BG, fg=DIM, font=(UI, 9)).pack(side='left')

    # --------------------------------------------------------------- settings
    def _autosave(self):
        """Save shortly after edits stop."""
        self._pending = None

        def later(*_):
            if self._pending is not None:
                self.root.after_cancel(self._pending)
            self._pending = self.root.after(800, self.remember)

        self._autosave_later = later
        for var in (self.auto_items, self.anti_afk, self.merchant_on, self.webhook, self.auto_reconnect, self.server,
                    self.low_end, self.rejoin_browser, self.eden_on, self.eden_path, self.eden_record,
                    self.eden_ping, self.fish_on, self.fish_vip, self.fish_sell, self.fish_sell_all, self.fish_full_check, self.fish_sell_amount, self.collect_on, self.clip_on, self.clip_from,
                    self.clip_quality, self.clip_key_on, self.clip_keys, self.equip_on, self.equip_name):
            var.trace_add('write', later)

    def remember(self):
        try:
            self.wanted = self.wanted_items()               # list edits apply mid-run too
            game.save_settings({'auto_items': bool(self.auto_items.get()),
                                'anti_afk': bool(self.anti_afk.get()),
                                'merchant_on': bool(self.merchant_on.get()),
                                'webhook_url': clean_url(self.webhook.get()),
                                'private_server': self.server.get().strip(),
                                'auto_reconnect': bool(self.auto_reconnect.get()),
                                'rejoin_browser': bool(self.rejoin_browser.get()),
                                'low_end': bool(self.low_end.get()),
                                'eden_on': bool(self.eden_on.get()),
                                'eden_path': bool(self.eden_path.get()),
                                'eden_record': bool(self.eden_record.get()),
                                'eden_ping': self.eden_ping.get().strip(),
                                'fish_on': bool(self.fish_on.get()),
                                'fish_vip': bool(self.fish_vip.get()),
                                'fish_sell': self.sell_every(),
                                'fish_sell_all': bool(self.fish_sell_all.get()),
                                'fish_full_check': bool(self.fish_full_check.get()),
                                'fish_sell_amount': self.sell_amount(),
                                'collect_on': bool(self.collect_on.get()),
                                'collect_merchants': [n for n, v in self.collect_from.items() if v.get()],
                                'clip_on': bool(self.clip_on.get()),
                                'clip_min': self.clip_from.get().strip(),
                                'clip_quality': self.clip_quality.get(),
                                'clip_key_on': bool(self.clip_key_on.get()),
                                'clip_keys': self.clip_keys.get(),
                                'equip_on': bool(self.equip_on.get()),
                                'equip_aura': self.equip_name.get().strip(),
                                'buy_items': {n: {'on': bool(on.get()), 'qty': qty.get().strip()}
                                              for n, (on, qty, _) in self.item_rows.items()},
                                'buy_list': ''})
        except Exception:
            pass

    def _next_quality(self):
        names = list(clipper.HEIGHTS)
        q = names[(names.index(self.clip_quality.get()) + 1) % len(names)]
        if clipper.HEIGHTS[q] > 1080 and not messagebox.askokcancel(
                'Clip quality', 'Clips above 1080p can use a lot more of your PC: up to 2 GB of memory at 4K and more '
                'CPU, which can slow Roblox and the macro down on weaker PCs.\n\nThey are never bigger than your Roblox '
                'window, so this only helps on a 1440p or 4K screen.\n\nUse %s?' % q, icon='warning',
                parent=self.root):
            q = names[0]
        self.clip_quality.set(q)

    def _open_clips(self):
        os.makedirs(clipper.CLIP_DIR, exist_ok=True)
        os.startfile(clipper.CLIP_DIR)

    def _correct_aura(self, quiet=False):
        """Turn what was typed into a real aura name (typos, partial, any case)."""
        typed = self.equip_name.get().strip()
        if not typed:
            self.equip_hint.configure(text='type an aura', fg=DIM)
            return None
        name = equip.resolve(typed)
        if name is None:
            self.equip_hint.configure(text='no aura found: type more of its name', fg=BAD)
            return None
        if name != typed:
            self.equip_name.set(name)
            if not quiet:
                note('equip', '"%s" read as %s' % (typed, name))
        self.equip_hint.configure(text='', fg=DIM)
        return name

    def _set_clip_keys(self):
        """The next key combo pressed becomes the clip key."""
        if getattr(self, '_capturing', False):
            return
        if self.running:                        # it'd catch the macro's own keys
            messagebox.showinfo('Clip key', 'Stop the macro first, then set the clip key.', parent=self.root)
            return
        self._capturing, before = True, self.clip_keys.get()
        self.clip_key_button.configure(textvariable='', text='press it now...')     # Esc cancels

        def wait():
            got = clipper.capture_keys()
            self.root.after(0, lambda: done(got))

        def done(got):
            self._capturing = False
            self.clip_key_button.configure(textvariable=self.clip_keys)
            try:
                if got:
                    clipper.parse_keys(got)
            except ValueError as e:
                messagebox.showwarning('Clip key not set', str(e), parent=self.root)
                got = None
            self.clip_keys.set(got or before)
            if got:
                note('clip', 'clip key set to %s' % got)

        threading.Thread(target=wait, daemon=True).start()

    def sell_every(self):
        try:
            return max(0, int(self.fish_sell.get().strip() or 0))
        except ValueError:
            return 0

    def sell_amount(self):
        try:
            return max(1, int(self.fish_sell_amount.get().strip() or 10))
        except ValueError:
            return 10

    def _oops(self, kind, value, tb):
        try:
            self.phase('%s: %s' % (kind.__name__, value), BAD)
        except Exception:
            pass

    def _hotkeys(self):
        """F1/F2 by polling key state. A keyboard hook can freeze Alt+Tab when the macro is busy."""
        self._keyboard = keyboard
        threading.Thread(target=self._poll_hotkeys, daemon=True).start()

    def _poll_hotkeys(self):
        """Windows can silently drop a hook, but not this."""
        state, was = ctypes.windll.user32.GetAsyncKeyState, {}
        while not self._closing:
            for vk, key in ((0x70, keyboard.Key.f1), (0x71, keyboard.Key.f2)):
                held = bool(state(vk) & 0x8000)             # the 'pressed since' bit is unreliable (RDP etc.)
                if held and not was.get(vk) and not getattr(self, '_capturing', False):
                    self.on_key(key)
                was[vk] = held
            time.sleep(0.01)                                # a quick tap lasts 30-50 ms

    def on_key(self, key, *_):
        """Hotkey handler; never raises, never suppresses."""
        try:
            kb = self._keyboard
            if key is not kb.Key.f1 and key is not kb.Key.f2:
                return True
            now = time.perf_counter()
            which = 'start' if key is kb.Key.f1 else 'stop'
            if now - self._last_hotkey.get(which, 0.0) < 0.75:     # a held key repeats
                return True
            self._last_hotkey[which] = now
            note('run', 'F%d pressed' % (1 if which == 'start' else 2))
            if which == 'stop':
                game.ABORT = True            # the run sees this right away
            self.updates.put({'action': which, 'key': True})
        except Exception:
            pass
        return True

    def calibrate(self, points=None):
        try:
            if game.find_roblox_window() is None:
                raise RuntimeError('no Roblox window')
        except Exception:
            messagebox.showinfo(TITLE, 'Open Roblox first, then calibrate.')
            return
        if self._cal_window is not None and self._cal_window.winfo_exists():
            self._cal_window.lift()
            return
        if points is None and not self._calibrate_anyway():
            return
        self._cal_window = Calibrate(self, points)

    def _calibrate_anyway(self):
        """Buttons are already auto: say so, then ask."""
        import points as gui
        size = game.window_size()
        name = gui.NAMES.get(size)
        if name:
            text = ('Your Roblox window is %s (%dx%d). MMacro knows every button exactly at this size, so they '
                    'already work.' % ((name,) + size))
        else:
            text = ('Your Roblox window is %dx%d, a size MMacro scales its buttons to, so a click could miss. A '
                    'windowed Roblox is resized to 1080p (768p on a smaller monitor) when the macro starts.' % size)
        return messagebox.askyesno('Calibrate', 'Highly suggested to use the preset calibrations.\n\n%s\n\n'
                                   'Are you sure you want to calibrate?' % text, icon='warning', default='no',
                                   parent=self.root)

    # ----------------------------------------------------------- biome alerts
    def start_biomes(self, url):
        if self.biome_stop is not None and not self.biome_stop.is_set():
            return
        if not (url.startswith('https://') or self.merchant_detect or self.clipper or self.equip_aura):
            return
        self.biome_stop = threading.Event()
        threading.Thread(target=self._watch_biomes, args=(url,), daemon=True).start()

    def _watch_biomes(self, url):
        cfg = game.load_settings()
        stop = self.biome_stop
        failed = None
        post_event(url, 'Macro started', '', EMBED_GOOD)
        self._set(biome=('watching', GOOD))
        try:
            watcher = BiomeWatcher(float(cfg.get('cooldown_seconds') or 300))
            self._merchant_posted = {}
            last_aura = None                        # the first one seen was already on
            for line in game.follow(stop.is_set):
                try:
                    last_aura = self._read_line(line, url, watcher, last_aura)
                except Exception as e:              # one bad line shouldn't kill detection
                    note('biomes', 'a log line was not read: %s: %s' % (type(e).__name__, e))
        except Exception as e:
            failed = '%s: %s' % (type(e).__name__, e)
        finally:
            if failed:
                post_event(url, 'Biome detection stopped', '`%s`' % failed, EMBED_BAD, 'Biome')
            else:
                post_event(url, 'Macro stopped')
            if self.biome_stop is stop:
                self.biome_stop = None
            self._set(biome=(failed, BAD) if failed else ('', DIM))

    def merchant_arrived(self, merchant, how, url=None):
        """Posts a merchant once per visit and queues collection if wanted."""
        posted = self._merchant_posted
        if time.time() - posted.get(merchant, 0.0) <= MERCHANT_REPEAT_S:
            return
        posted[merchant] = time.time()
        note('merchant', '%s arrived (%s)' % (merchant, how))
        post_merchant(url or self.url, merchant, self.server_link or game.load_settings().get('private_server', ''))
        self._set(phase='%s arrived' % merchant, colour=GOOD)
        if self.collect and merchant in self.collect_names:
            self.merchant_due, self.merchant_at = merchant, time.monotonic()

    def _watch_cache(self):
        """Watches Roblox's cache for merchant animations and keeps the block up."""
        said = False
        while not self._closing:
            try:
                came = self.cache.poll()
                said = False
                if came and self.running and self.merchant_detect:
                    for name in came:
                        self.merchant_arrived(name, 'its animation was used in Roblox\'s cache')
                self._keep_block()
            except Exception as e:
                if not said:
                    note('merchant', 'Roblox\'s cache could not be read: %s: %s' % (type(e).__name__, e))
                    said = True
            time.sleep(2)

    def _merchant_toggled(self, *_):
        self.block_on = bool(self.merchant_on.get())
        if not self.block_on:
            self.merchant_detect = False                # a run going stops looking for merchants too

    def _keep_block(self):
        """Block merchant animations while detection is on, take the block out when off."""
        keys = {k for ks in merchant_cache.FILES.values() for k in ks}
        with self.block_lock:
            if self._closing or not keys:
                return
            if self.block_on:
                path = self.cache.cache()
                if not path:
                    return
                wrote = merchant_cache.block(keys, path)
                if wrote:
                    self.cache.forget(wrote)
                    past = self.loaded_already(wrote)
                    note('merchant', '%s %d merchant animation(s) in Roblox\'s cache%s' % (
                        'blocked again' if self.blocked else 'blocked', len(wrote),
                        ': this Roblox already loaded a real one' if past else ''))
                    self.got_past_block = self.got_past_block or past
                    self.blocked = {**self.blocked, **wrote}      # replaced, not mutated: other threads read it
                    self.block_path = path
            elif self.blocked or self.cache.ours:
                self._unblock(keys)

    def _unblock(self, keys):
        path = self.block_path or self.cache.cache()
        note('merchant', 'block taken out of Roblox\'s cache (%d)' % merchant_cache.unblock(keys, path))
        self.blocked, self.block_path = {}, None

    def loaded_already(self, blocked=None):
        """True if Roblox loaded a real animation before the block (it won't reread it until reopened)."""
        blocked = self.blocked if blocked is None else blocked
        starts = []
        for p in game.roblox_processes():
            try:
                if p.name().lower() == 'robloxplayerbeta.exe':
                    starts.append(p.create_time())
            except Exception:
                pass
        return bool(starts) and any(t and t / 1000.0 > min(starts) for t in blocked.values())

    def _read_line(self, line, url, watcher, last_aura):
        """Handles one log line. Returns the aura worn after it."""
        biome = game.biome_from_line(line) if line else None
        self.biome_now = biome or self.biome_now
        aura = game.aura_from_line(line) if line and (self.clipper or self.equip_aura) else None
        if aura == '_None_' and (last_aura is None or time.monotonic() - self.joined_at < JOIN_NONE_S):
            aura = None                             # title screen after a join, not a roll
        if aura:
            self.aura_logged = (aura, time.time())
        if aura and aura != last_aura:
            ours = (self.equip_aura and clipper.norm(aura) == clipper.norm(self.equip_aura)
                    and time.monotonic() - self.equip_busy_at < 120)
            if self.clipper and last_aura is not None and aura != '_None_' and not ours:
                self.clip_aura(aura, line)
            if self.equip_aura and clipper.norm(aura) != clipper.norm(self.equip_aura):
                note('equip', 'Roblox\'s log says %s is equipped now: %s goes back on'
                     % (aura, self.equip_aura))
                if self.equip_due is None:
                    self.equip_due = max(time.monotonic(), self.equip_busy_at + EQUIP_GAP_S)
            last_aura = aura
        previous = watcher.current
        change = watcher.feed(biome)
        if change:
            name, alert = change
            append_history(name)
            server = self.server_link or game.load_settings().get('private_server', '')
            post_biome(url, name, ping=alert, server=server, previous=previous)
            self._set(biome=(pretty(name), ACCENT if alert else DIM))
        return last_aura

    def clip_aura(self, aura, line):
        n = clipper.rarity(aura, self.biome_now, line)
        if n is not None and n < self.clip_min:
            return
        odds = '1 in {:,}'.format(n) if n else 'rarity unknown'
        note('clip', '%s rolled (%s) - saving a clip' % (aura, odds))
        self._set(phase='%s rolled - clipping' % aura, colour=GOOD)

        colour = next((c for least, c in CLIP_COLOURS if (n or 0) >= least), EMBED_INFO)
        shot = self.clipper.shot(time.time())

        def done(path):
            if path:
                how = 'Clipped using hotkey' if path is True else 'clips\\%s' % os.path.basename(path)
                post_event(self.url, 'Aura Clipped - %s' % aura, '', colour, 'Clip',
                           [('Rarity', odds, True), ('Biome', pretty(self.biome_now) or '-', True), ('Clip', how, True)],
                           shot=shot)
        self.clipper.clip('%s' % aura, done)

    # --------------------------------------------------------------- plumbing
    def phase(self, text, colour=TEXT):
        """Status goes in the title bar."""
        text = (text or '').replace(' -- ', ', ').replace(' - ', ', ')
        self.root.title(TITLE if not text or text == 'idle' else '%s  |  %s' % (TITLE, text))

    def _set(self, **kw):
        """Thread-safe UI update through the queue."""
        self.updates.put(kw)

    def _pump(self):
        if not self.root.winfo_exists():
            return
        try:
            while True:
                self._apply(self.updates.get_nowait())
        except queue.Empty:
            pass
        except tk.TclError:
            return
        except Exception as e:
            self._oops(type(e), e, None)
        self.root.after(25, self._pump)       # hotkey latency

    def notice(self, text, colour=TEXT, ms=2200):
        """Toast over Roblox so F1/F2 in game get feedback."""
        try:
            if self._toast is None:
                self._toast = Toast(self.root)
            self._toast.show(text, colour, ms)
        except Exception as e:
            note('ui', 'notice: %s: %s' % (type(e).__name__, e))

    def _key_notice(self, kw):
        if kw.get('action') == 'start':
            if self.running and game.ABORT:
                self.notice('MMacro: stopping - starts again right after', DIM)
            elif self.running:
                self.notice('MMacro is already running  (F2 stops it)', ACCENT)
            else:
                self.notice('MMacro: starting', GOOD, 1200)     # short, the run is about to read the screen
        elif kw.get('action') == 'stop':
            self._key_stop = self.running
            self.notice('MMacro: stopping' if self.running else 'MMacro is not running  (F1 starts it)',
                        BAD if self.running else DIM)

    def _apply(self, kw):
        if 'toast' in kw:
            self.notice(kw['toast'], BAD, 12000)
        if 'phase' in kw:
            self.phase(kw['phase'], kw.get('colour', TEXT))
        if 'biome' in kw:
            self.phase(*kw['biome'])
        if kw.get('key'):
            self._key_notice(kw)
        if kw.get('action') == 'start' and self.running and game.ABORT:
            self.start_again = True                         # F1 while still stopping: start again after
            self.phase('stopping - starting again after it', DIM)
        elif kw.get('action') == 'start' and not self.running:
            self.phase('starting', GOOD)                    # show the press before any slow checks
            self.start()
        elif kw.get('action') == 'stop' and self.running:
            self.stop()
        elif kw.get('action') == 'quit':
            self.close()
        elif kw.get('action') == 'idle':
            self.start_b.configure(state='normal')
            self.stop_b.configure(state='disabled')
            if self._key_stop:
                self._key_stop = False
                self.notice('MMacro: stopped', DIM)
            if self.start_again:
                self.start_again = False
                self.root.after(200, self.start)
        if 'update' in kw:
            self.offer_update(kw['update'])

    def check_update(self):
        if not getattr(sys, 'frozen', False):
            return

        def run():
            for attempt in range(4):
                try:
                    found = latest_release()
                except Exception as e:
                    note('update', 'check failed (try %d of 4): %s: %s' % (attempt + 1, type(e).__name__, e))
                    time.sleep(20)
                    continue
                if found and version_tuple(found[0]) > version_tuple(VERSION):
                    note('update', '%s is out (running %s)' % (found[0], VERSION))
                    self._set(update=found)
                else:
                    note('update', 'up to date (%s)' % VERSION)
                return
        threading.Thread(target=run, daemon=True).start()

    def offer_update(self, found):
        tag, url, size = found
        if self.updating or self.ran or version_tuple(tag) <= version_tuple(VERSION):
            return                  # only asked on opening
        folder = os.path.dirname(sys.executable)
        if not can_write(folder):
            if messagebox.askyesno(TITLE, "MMacro %s is out, but this folder can't be written to:\n%s\n\n"
                                   'Open the download page?' % (tag.lstrip('v'), folder), parent=self.root):
                webbrowser.open(RELEASE_PAGE)
            return
        if not messagebox.askyesno(TITLE, 'MMacro %s is out (you have %s).\n\nUpdate now? It restarts by itself.'
                                   % (tag.lstrip('v'), VERSION), parent=self.root):
            return
        self.updating = True
        self.start_b.configure(state='disabled')
        zipped = url.lower().endswith('.zip')
        new = os.path.join(tempfile.gettempdir(), 'MMacro_update.zip') if zipped else sys.executable + '.new'

        def run():
            try:
                note('update', 'downloading %s' % url)
                download(url, new, size, lambda f: self._set(phase='downloading update %d%%' % round(100 * f)))
                install(new, sys.executable, os.getpid(), zipped)
                self._set(action='quit')
            except Exception as e:
                note('update', 'failed: %s: %s' % (type(e).__name__, e))
                self.updating = False
                try:
                    os.remove(new)
                except OSError:
                    pass
                self._set(phase='update failed: %s' % e, colour=BAD, action='idle')
        threading.Thread(target=run, daemon=True).start()

    # ---------------------------------------------------------------- actions
    def start(self):
        if self.running or self.updating:
            return
        self.ran = True
        self.server_link = self.server.get().strip()
        self.reconnect_on = bool(self.auto_reconnect.get())
        self.played = False
        self.item_due = {}                      # both due now
        self.browser_rejoin = bool(self.rejoin_browser.get())
        self.slow_pc = bool(self.low_end.get())
        if self.reconnect_on and not game.deeplink(self.server_link):
            self.phase('auto reconnect needs a private server link', BAD)
            self.refused('auto reconnect is on - paste a Roblox private server link on the Macro tab')
            return
        if game.roblox_elevated():
            self.phase('Roblox is running as administrator', BAD)
            self.refused('Roblox is running as administrator, so Windows will not let the macro press keys or click '
                         'in it.\n\nClose Roblox and open it normally (not with "Run as administrator", and with no '
                         'compatibility setting that runs it as administrator), then press Start again.')
            return
        self.merchant_detect = bool(self.merchant_on.get())
        if self.merchant_detect and not merchant_cache.cache_found():
            self.phase('Roblox\'s cache was not found', BAD)
            self.refused(STORE_ROBLOX)
            return
        self.collect = bool(self.collect_on.get())
        if self.collect and not self.merchant_detect:
            self.phase('auto merchant collection needs merchant detection', BAD)
            self.refused('auto merchant collection finds merchants through Roblox\'s cache - turn on Merchant detection on '
                         'the Macro tab')
            return
        self.wanted = self.wanted_items()
        self.collect_names = {n for n, v in self.collect_from.items() if v.get()}
        self.merchant_due = None
        self.remember()
        self.url = clean_url(self.webhook.get())
        self.use_items = bool(self.auto_items.get())
        self.clip_min = clip_floor(self.clip_from.get())
        self.clipper = None
        if self.clip_on.get() and self.clip_key_on.get():
            try:
                self.clipper = clipper.KeyClipper(self.clip_keys.get(), lambda text: note('clip', text))
            except ValueError as e:
                note('clip', 'the clip key cannot be pressed (%s): no clips this run' % e)
        elif self.clip_on.get():
            self.clipper = clipper.Clipper(lambda text: note('clip', text),
                                           height=clipper.HEIGHTS.get(self.clip_quality.get(), clipper.HEIGHT))
        if self.clipper:
            self.clipper.start()
        self.equip_aura = self._correct_aura() if self.equip_on.get() else None
        if self.equip_on.get() and not self.equip_aura:
            note('equip', 'no aura in the list to keep equipped: Keep an aura equipped is off this run')
        self.equip_due = time.monotonic() if self.equip_aura else None      # check once at start
        self.crack_on, self.in_dimension = bool(self.eden_on.get()), True
        self.run_wall, self.equip_busy_at, self.equip_fails = time.time(), -EQUIP_GAP_S, 0
        self.start_biomes(self.url)
        self.running = True
        self.start_b.configure(state='disabled')
        self.stop_b.configure(state='normal')
        threading.Thread(target=self._guard, daemon=True).start()

    def refused(self, why):
        """Why Start was refused, one box at a time."""
        if getattr(self, '_refusing', False):
            return
        self._refusing = True
        text = why[:1].upper() + why[1:]
        self.notice('Cannot start: ' + text.split('\n')[0], BAD, 8000)
        try:
            self._over_roblox(lambda: messagebox.showwarning('Cannot start', text, parent=self.root))
        except Exception:
            pass
        finally:
            self._refusing = False

    def _over_roblox(self, show):
        """Keep our window on top so the box isn't hidden behind fullscreen Roblox."""
        try:
            self.root.attributes('-topmost', True)
        except tk.TclError:
            pass
        try:
            return show()
        finally:
            try:
                self.root.attributes('-topmost', False)
            except tk.TclError:
                pass

    def tell(self, title, detail='', colour=None, area='Macro'):
        """Discord and the title bar at once."""
        post_event(self.url, title, detail, colour if colour is not None else EMBED_INFO, area)
        self._set(phase='%s%s' % (title, ' - ' + detail if detail else ''))

    def _guard(self):
        """Runs until Stop; restarts after a crash."""
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)      # keep the PC and screen awake
        try:
            for k in itertools.count():
                try:
                    self.play()
                    if not self.restart_run:
                        return
                except Exception as e:
                    try:
                        game.release_all()
                    except Exception:
                        pass
                    why = '%s: %s' % (type(e).__name__, e)
                    note('crash', '%s\n%s' % (why, traceback.format_exc()[-1500:]))
                    if game.ABORT and not self.restart_run:
                        self.tell('Macro crashed', '`%s`' % why, EMBED_BAD)
                        return
                    if not self.restart_run:
                        wait = CRASH_WAITS[min(k, len(CRASH_WAITS) - 1)]
                        self.tell('Macro crashed', '`%s`\nStarting again in %ds' % (why, wait), EMBED_BAD)
                        if not self.nap(wait):
                            return
                if self.restart_run:                    # watchdog restart: straight back in
                    self.restart_run = False
                    try:
                        game.release_all()
                    except Exception:
                        pass
                    note('run', 'run restarted after a stall')
        finally:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
            self.running = False
            if self.biome_stop is not None:
                self.biome_stop.set()
            if self.clipper is not None:
                self.clipper.stop()
            self._set(action='idle')

    def nap(self, seconds, halt=None):
        """Sleep that answers Stop (and `halt`). False if stopped."""
        halt = halt or (lambda: game.ABORT)
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            self.beat = time.monotonic()
            if halt():
                return False
            time.sleep(0.2)
        return not halt()

    def play(self):
        game.ABORT = False
        game.arm()
        game.fresh_session()
        game.set_pace(2.0 if self.slow_pc else 1.0)
        note('run', 'started: %s' % device_line())
        self.joined_at = time.monotonic()
        self.need_rejoin = None
        self.watch = game.Watch()
        self.watch.poll()
        if not game.roblox_running():
            self.need_rejoin = 'Roblox is not running'
        elif self.merchant_detect and self.reconnect_on and self.loaded_already():
            note('merchant', 'this Roblox loaded a merchant before the block: reopening it so every visit shows')
            game.close_roblox()
            self.need_rejoin = 'a merchant was loaded before the block'
        self.got_past_block = False                     # already checked above
        self.run_id += 1
        self.beat = time.monotonic()
        threading.Thread(target=self._watch_connection, args=(self.run_id,), daemon=True).start()
        if not self.ready_to_play():
            game.release_all()
            return
        self.fit_roblox()

        seer = eden.Watcher() if self.eden_on.get() else None
        afk_due = time.monotonic() + AFK_EVERY_S
        halt = lambda: game.ABORT or self.need_rejoin is not None
        self.fisher = fishing.Fisher(vip=bool(self.fish_vip.get()), sell_every=self.sell_every(),
                                     sell_amount=self.sell_amount(), sell_all=bool(self.fish_sell_all.get()),
                                     full_check=bool(self.fish_full_check.get()),
                                     say=lambda m: note('fishing', m),
                                     report=self.post_fishing) if self.fish_on.get() else None
        merchant_wait = None                            # merchant came mid-fish
        self._set(phase='running', colour=GOOD)
        while not game.ABORT:
            if self.need_rejoin:
                self.merchant_due = merchant_wait = None    # merchant is gone with the old server
                self._merchant_posted = {}                  # post again on the new server
                if self.fisher:
                    self.fisher.hold = self.fisher.pause = False
                if not self.reconnect():
                    note('run', 'stopped: could not get back in')
                    self.tell('Could not get back in', 'Macro stopped', EMBED_BAD, 'Connection')
                    break
                self.joined_at = time.monotonic()
                self.got_past_block = False                 # fresh Roblox
                self.in_dimension = False                   # new servers start in the main dimension
                self.fit_roblox()
                if self.fisher:
                    self.fisher.lost()
                if self.crack_on and not self.need_rejoin:
                    self.use_crack(halt, 'back to Eden\'s dimension after the rejoin')
            if (self.got_past_block and self.merchant_detect and self.reconnect_on and not self.merchant_due
                    and not (self.fisher and self.fisher.line_out)):
                self.got_past_block = False
                note('merchant', 'Roblox loaded a merchant\'s real animation and keeps it: reopening it so every '
                                 'visit shows again')
                game.close_roblox()
                self.need_rejoin = 'a merchant was loaded past the block'
                continue
            self.check_in_game()
            if self.need_rejoin:
                continue
            if self.merchant_due and time.monotonic() - self.merchant_at > MERCHANT_STALE_S:
                note('merchant', '%s came %d s ago: gone by now, not teleporting' % (self.merchant_due, MERCHANT_STALE_S))
                self.merchant_due = merchant_wait = None
                if self.fisher:
                    self.fisher.hold = False
            if self.merchant_due and not self.need_rejoin:
                fishing_now = self.fisher is not None and self.fisher.at_spot and self.fisher.line_out
                if fishing_now and merchant_wait is None:
                    merchant_wait = time.monotonic()             # land the fish on the line first
                    self.fisher.hold = True
                    note('merchant', '%s arrived: finishing the fish on the line first' % self.merchant_due)
                elif not fishing_now or time.monotonic() - merchant_wait > MERCHANT_CATCH_S:
                    self.collect_merchant(self.merchant_due, halt)
                    self.merchant_due = merchant_wait = None
                    if self.fisher:
                        self.fisher.hold = False
                        self.fisher.lost()
                    continue
            if self.use_items and not game.ABORT and self.items_due():
                self.items_turn(halt)
            if (self.equip_due is not None and time.monotonic() >= self.equip_due and not self.need_rejoin
                    and not game.ABORT):
                self.between_fish(halt, 'equip', 'putting %s back on' % self.equip_aura, self.equip_turn)
            if seer is not None and not self.need_rejoin and seer.seen():
                self.eden_found()
                afk_due = time.monotonic() + EDEN_AFK_REST_S
                self.nap(eden.COOLDOWN_S)
                if self.fisher:
                    self.fisher.lost()
            if self.fisher is not None and not self.need_rejoin:
                try:
                    self.fisher.step(halt, LOOK_EVERY_S * 4)
                except Exception as e:
                    note('fishing', 'failed - %s: %s' % (type(e).__name__, e))
                    self.fisher.lost()
                    self.nap(LOOK_EVERY_S)
                if self.fisher.rejoin:
                    self.fisher.rejoin = False
                    if self.reconnect_on:
                        game.close_roblox()
                        self.need_rejoin = 'inventory still full after selling'
                    else:
                        note('fishing', 'not rejoining: Auto reconnect is off')
                self.beat = time.monotonic()
                continue
            if self.anti_afk.get() and time.monotonic() >= afk_due and not self.need_rejoin:
                self.jump()
                afk_due = time.monotonic() + AFK_EVERY_S
            self.nap(LOOK_EVERY_S)

        game.release_all()
        if self.restart_run:
            note('run', 'run ended by the stall watchdog')
            return
        note('run', 'run ended%s' % (' (Stop pressed)' if game.ABORT else ''))

    def jump(self):
        """Two jumps; never raises."""
        try:
            if game.take_foreground(tries=2) is not None:
                note('run', 'anti-AFK: two jumps')
                game.tap(' ', gap=0.2)
                game.tap(' ')
        except Exception as e:
            note('run', 'anti-AFK skipped: %s: %s' % (type(e).__name__, e))

    def eden_found(self):
        """Post Eden, then go sign the contract."""
        halt = lambda: game.ABORT or self.need_rejoin is not None
        ping = self.eden_ping.get()
        note('eden', 'Eden on screen')
        self._set(phase='Eden on screen', colour=GOOD)
        game.take_foreground(tries=2)
        if self.eden_record.get():
            threading.Thread(target=eden.record, args=(eden.RECORD_S, halt), daemon=True).start()
        post_shot(self.url, 'Eden Detected', EMBED_GOOD, ping, area='Eden')
        if not self.nap(eden.SETTLE_S, halt):
            return
        path, began, go = self.eden_path.get(), time.monotonic(), 0
        while not halt():
            go += 1
            tried = time.monotonic()
            if self.eden_try(path, go, halt):
                note('eden', 'contract signed (go %d)' % go)
                post_shot(self.url, 'Eden Obtained', EMBED_GOLD, ping, area='Eden')
                return
            if halt():
                return
            if path and time.monotonic() - began >= EDEN_GIVE_UP_S:
                note('eden', 'no contract in %d minutes: giving up' % (EDEN_GIVE_UP_S // 60))
                self.tell('Eden Contract not seen', 'Tried for %d minutes, giving up' % (EDEN_GIVE_UP_S // 60), EMBED_BAD,
                          'Eden')
                return
            note('eden', 'the contract never showed (go %d): trying again' % go)
            if go == 1:
                self.tell('Eden Contract not seen', 'Trying again every %ds' % EDEN_RETRY_S, EMBED_BAD, 'Eden')
            if not self.nap(max(0.0, EDEN_RETRY_S - (time.monotonic() - tried)), halt):
                return

    def eden_try(self, path, go, halt):
        """One go at the contract. Later goes reset first, so a Portable Crack brings us back."""
        try:
            if path:
                if go > 1:
                    if not fishing.respawn(halt):
                        return False
                    self.in_dimension = False           # a reset leaves Eden's dimension
                if not self.in_dimension and not self.use_crack(halt, 'the Eden walk starts at its spawn (go %d)' % go):
                    return False
                if not game.align_camera(halt):
                    note('eden', 'Collection did not square the camera up: not walking')
                    return False
                eden.tilt()
                note('eden', 'walking the path (go %d)' % go)
                eden.walk(halt)
                time.sleep(0.5)
            if halt():
                return False
            game.down('e')
            time.sleep(0.1)
            game.up('e')
        except game.NotFocused as e:
            note('eden', 'not this go: %s' % e)
            return False
        if not self.nap(eden.TALK_S, halt):
            return False
        if not game.press_point('contract', settle=0.2):
            note('eden', 'the Contract button was not pressed: press Set Contract on the Eden tab')
            return False
        return eden.signed(halt)

    def _watch_connection(self, run_id=0):
        """Flags disconnects, sleeps and stalls while a run is going."""
        last = time.time()
        while self.running and not self._closing and run_id == self.run_id:
            gap, last = time.time() - last, time.time()
            if gap > SLEPT_S:
                # lid shut, Sleep, flat battery: not a stall
                self.beat = time.monotonic()
                note('run', 'the PC was asleep for %d minutes: nothing ran' % round(gap / 60))
                self.tell('PC was asleep', 'Nothing ran for %d minutes. MMacro keeps the PC awake, but not through a '
                          'closed lid, Sleep or a flat battery' % round(gap / 60), EMBED_BAD)
            watch = self.watch
            if watch is not None and not self.rejoining and self.need_rejoin is None:
                try:
                    why = watch.trouble()
                except Exception:
                    why = None
                if why:
                    self.need_rejoin = why
                    try:
                        game.release_all()
                    except Exception:
                        pass
            if time.monotonic() - self.beat > STALL_S and not self.restart_run and not game.ABORT:
                # stuck on something that never ends: abort, _guard restarts it
                note('run', 'the run has not moved for %d minutes: restarting it' % (STALL_S // 60))
                self.tell('Macro stuck', 'No progress for %d minutes, restarting the run' % (STALL_S // 60), EMBED_BAD)
                self.restart_run = True
                game.ABORT = True
            time.sleep(WATCH_EVERY)

    def connected(self, watch=None):
        """True if the log shows we're in game."""
        watch = watch or game.Watch()
        watch.poll()
        return game.roblox_running() and watch.state == 'joined' and game.in_game(watch)

    def ready_to_play(self):
        """Roblox open and connected? Rejoins if not."""
        watch = self.watch or game.Watch()
        why = watch.trouble(quiet_s=float('inf'))
        if why and game.roblox_running() and game.find_play() is None:
            # old disconnect lines can be hours old; no Play button means we're in
            note('run', 'the log says "%s", but the client is in a game: starting anyway' % why)
            why = None
        if why:
            self.need_rejoin = why
            if not self.reconnect():
                self.tell('Roblox is not ready', capital(why), EMBED_BAD, 'Connection')
                return False
        return True

    def fit_roblox(self):
        """Resize a windowed Roblox to a known size; never raises."""
        try:
            def say(m):
                note('window', m)
                if 'F11' in m:
                    self._set(toast=m)
            game.fit_window(say=say)
        except Exception as e:
            note('window', 'sizing the Roblox window failed: %s: %s' % (type(e).__name__, e))

    def reconnect(self):
        """Get back in game. True once in, False only on Stop."""
        why, self.need_rejoin = self.need_rejoin, None
        self.out_since = None
        if 'by itself' in (why or '') and self.connected():
            note('connection', 'already back in the game (%s)' % why)
            self.claim_daily()
            self.watch = game.Watch()
            return True
        if not self.reconnect_on:
            return self.wait_for_game(why or '')
        note('connection', 'reconnecting: %s' % (why or ''))
        self.tell('Reconnecting', capital(why), EMBED_BAD, 'Connection')
        k = -1
        while True:
            k += 1
            self.beat = time.monotonic()
            if game.ABORT:
                return False
            self.rejoining = True
            failed = ''
            try:
                ok = game.rejoin(self.server_link, stop=lambda: game.ABORT, browser=self.browser_rejoin,
                                 frozen=k > 0 or (why or '').startswith(game.FROZEN),
                                 say=lambda m: (note('connection', m), self._set(phase='reconnecting - %s' % m, colour=DIM)))
                self.beat = time.monotonic()
                if ok and not self.wait_in_game():
                    ok, failed = False, 'not in the game %d s after joining' % IN_GAME_S
            except Exception as e:
                ok, failed = False, '%s: %s' % (type(e).__name__, e)
            finally:
                self.watch = game.Watch()
                self.rejoining = False
            if game.ABORT:
                return False
            if ok:
                note('connection', 'rejoined')
                self.tell('Rejoined the private server', '', EMBED_GOOD, 'Connection')
                self.claim_daily()
                return True
            wait = REJOIN_WAITS[min(k, len(REJOIN_WAITS) - 1)]
            note('connection', 'rejoin %d failed (%s), again in %d s' % (k + 1, failed or 'see above', wait))
            self.tell('Could not rejoin', '%sTrying again in %ds' % (capital(failed) + '\n' if failed else '', wait),
                      EMBED_BAD, 'Connection')
            if not self.nap(wait):
                return False

    def wait_for_game(self, why):
        """Reconnect off: wait for the game to come back, pressing Play. False on Stop."""
        note('connection', 'auto reconnect is off: waiting for the game to be back (%s)' % why)
        self.tell('Disconnected', 'Auto Reconnect is disabled', EMBED_BAD, 'Connection')
        clicked, watch = 0.0, game.Watch()          # reused: each poll reads only new lines
        while self.nap(5):
            if not game.roblox_running():
                continue
            if self.connected(watch):
                note('connection', 'back in the game')
                self.tell('Back in the game', '', EMBED_GOOD, 'Connection')
                self.claim_daily()
                self.watch = game.Watch()
                return True
            if game.find_play() is not None and time.monotonic() - clicked > PLAY_EVERY_S:
                self.press_play()
                clicked = time.monotonic()
        return False

    def wait_in_game(self, limit=IN_GAME_S):
        """True once in game. No log or no aura counts after 20 s off the title screen."""
        end, clicked, clear_since = time.monotonic() + limit, 0.0, None
        watch = game.Watch()
        while time.monotonic() < end and not game.ABORT:
            if not game.roblox_running():
                return False
            watch.poll()
            if watch.state == 'joined' and game.in_game(watch):
                return True
            if game.find_play() is not None or (watch.in_menu and time.time() - watch.menu_at < game.MENU_S):
                clear_since = None
                if time.monotonic() - clicked > PLAY_EVERY_S:
                    self.press_play()
                    clicked = time.monotonic()
            elif watch.path is None or watch.state == 'joined':
                clear_since = clear_since or time.monotonic()
                if time.monotonic() - clear_since > 20:
                    return True
            time.sleep(2)
        return False

    def press_play(self):
        """Click Play where it's seen, else the calibrated spot. Never raises."""
        try:
            at = game.find_play()
            if at is not None:
                game.click(*at)
            elif not game.press_point('play', settle=1.0):
                return
            note('connection', 'pressed Play (%s)' % ('seen' if at else 'Set Play' if 'play' in game.load_points()
                                                       else 'built-in spot'))
        except Exception as e:
            note('connection', 'pressing Play failed: %s: %s' % (type(e).__name__, e))

    def check_in_game(self):
        """Title screen or stuck load: click Play, and after OUT_S call it a disconnect."""
        now, mono = time.time(), time.monotonic()      # log times are wall clock
        if mono < self._look_at or self.need_rejoin:
            return
        self._look_at = mono + 5
        watch = self.watch
        logged_in = watch is not None and watch.path is not None and game.in_game(watch)
        menu = watch is not None and watch.in_menu and now - watch.menu_at < game.MENU_S
        out = game.roblox_running() and not logged_in and (menu or game.find_play() is not None)
        if not out:
            self.out_since = None
            if self.played and logged_in:
                self.played = False
                self.claim_daily()
            return
        self.out_since = self.out_since or mono
        if mono - self._played > PLAY_EVERY_S:
            self.press_play()
            self._played = mono
            self.played = True
        if mono - self.out_since > OUT_S:
            note('connection', 'not in a game for %d minutes' % (OUT_S // 60))
            self.out_since = None
            self.need_rejoin = 'not in a game for %d minutes' % (OUT_S // 60)

    def claim_daily(self):
        """Claim daily rewards, after every Play back into the game. Never raises."""
        if game.ABORT:
            return
        if not game.daily_clicks_ready():
            note('daily', 'daily rewards skipped: Claim and Close are not calibrated')
            return
        try:
            game.paced(game.DAILY_WAIT_S)
            done = game.daily_by_clicks()
        except Exception as e:
            done = False
            note('daily', 'crashed: %s: %s' % (type(e).__name__, e))
        note('daily', 'daily rewards by clicks: %s' % ('claimed and closed' if done else 'did not finish'))

    def post_fishing(self, detail):
        """Fishing failsafe screenshot to the webhook. Never raises."""
        if not self.url:
            return
        try:
            post_shot(self.url, 'Fishing failsafe', EMBED_BAD, '', detail, 'Fishing')
        except Exception as e:
            note('fishing', 'webhook: %s: %s' % (type(e).__name__, e))

    def collect_merchant(self, name, halt):
        """Teleport to the merchant, buy what's wanted, post the shop."""
        say = lambda m: note('merchant', m)
        self._set(phase='going to %s' % name, colour=GOOD)
        try:
            if self.fisher is not None and not fishing.respawn(halt):
                return
            got = shop.collect(name, self.wanted, halt, say)
            if got is None:
                if not halt():
                    self.tell("Could not open %s's shop" % name, 'No Merchant Teleporter, or the shop did not open',
                              EMBED_BAD, 'Merchant')
                self.close_guis()
                return
            found, bought = got
            items = ', '.join(found[s] for s in sorted(found)) or 'Could not read the items'
            post_shot(self.url, 'Merchant Items - %s' % name, MERCHANT_COLOURS.get(name, EMBED_GOLD),
                      area='Merchant', fields=[('Item list', items, False),
                                               ('Bought', '\n'.join(bought) or 'Nothing', False)])
            time.sleep(1.0)                             # screenshot is grabbed in the background
            shop.close_shop()
        except Exception as e:
            say('failed - %s: %s' % (type(e).__name__, e))
            self.tell('Merchant collection failed', '`%s: %s`' % (type(e).__name__, e), EMBED_BAD, 'Merchant')
            try:
                shop.close_shop()                       # an open shop blocks the walk back
            except Exception:
                pass
            self.close_guis()
        finally:
            self.in_dimension = False                   # the teleporter leaves Eden's dimension
            if self.crack_on and not halt():
                self.use_crack(halt, 'back to Eden\'s dimension after %s' % name)

    def _one_of(self, turned, other, name):
        """Fishing and Eden can't both be on (fishing walks away from the crack)."""
        if turned.get() and other.get():
            turned.set(False)
            messagebox.showerror(TITLE, 'Fishing and Eden can\'t run together. Turn off %s first.' % name,
                                 parent=self.root)

    def use_crack(self, halt, why):
        """Portable Crack back to Eden's spawn. True once used."""
        say = lambda m: note('eden', m)
        say('using a Portable Crack: %s' % why)
        try:
            ok = shop.use_item(CRACK, halt, say) and self.nap(CRACK_S, halt)
        except Exception as e:
            say('Portable Crack failed - %s: %s' % (type(e).__name__, e))
            self.close_guis()
            ok = False
        self.in_dimension = bool(ok)
        if not ok and not halt():
            self.tell('Portable Crack not used', 'Ensure you have a Portable Crack', EMBED_BAD, 'Eden')
        return self.in_dimension

    def items_turn(self, halt):
        self.between_fish(halt, 'items', 'SC/BR due', self.spend_items)

    def between_fish(self, halt, tag, why, work):
        """Menu work between fish, never with a line out."""
        if self.fisher and self.fisher.at_spot and self.fisher.line_out:
            if not self.fisher.pause:
                self.fisher.pause = True
                note(tag, '%s: landing the fish on the line first' % why)
            return
        if self.fisher and fishing.window_state() == 'catch':
            fishing.close_catch(halt)
        try:
            work()
        finally:
            if self.fisher:
                self.fisher.pause = False
                self.fisher.recast = self.fisher.at_spot and not self.fisher.line_out

    def equip_turn(self):
        """Put the kept aura back on; backs off when it fails."""
        aura, say = self.equip_aura, lambda m: note('equip', m)
        halt = lambda: game.ABORT or self.need_rejoin is not None

        def logged(since):
            name, at = self.aura_logged             # lines from before this run don't count
            return bool(name) and clipper.norm(name) == clipper.norm(aura) and at >= max(since, self.run_wall)

        def other(since):
            name, at = self.aura_logged
            same = clipper.norm(name or '') == clipper.norm(aura)
            return name if name and name != '_None_' and not same and at >= max(since, self.run_wall) else None

        self.equip_due = None
        self.equip_busy_at = time.monotonic()
        try:
            on = equip.equip(aura, halt, say, logged, other)
        except Exception as e:
            say('failed - %s: %s' % (type(e).__name__, e))
            self.close_guis()
            on = False
        self.equip_busy_at = time.monotonic()
        if on:
            self.equip_fails = 0
        elif not halt():
            self.equip_fails += 1
            wait = min(EQUIP_RETRY_S * 2 ** (self.equip_fails - 1), 60 * 60)     # 5, 10, 20, 40, 60 minutes
            self.equip_due = time.monotonic() + wait
            say('trying again in %d minutes' % (wait // 60))
            if self.equip_fails == 1:
                self.tell('Could not equip %s' % aura, 'Trying again in %d minutes' % (wait // 60), EMBED_BAD, 'Aura')
        else:
            self.equip_due = time.monotonic()           # stopped or rejoining: check again after

    def items_due(self):
        now = time.monotonic()
        return any(now >= self.item_due.get(t, 0.0) for t in (game.BR, game.SC))

    def spend_items(self):
        """Use whichever items are due. True if menus were opened."""
        say = lambda m: note('items', m)
        now = time.monotonic()
        due = tuple(t for t in (game.BR, game.SC) if now >= self.item_due.get(t, 0.0))
        if not due:
            return False
        try:
            got = game.item_pass(say=say, terms=due)
            done = time.monotonic()                     # the cooldown starts at Use, not when the pass began
            for t in due:
                self.item_due[t] = done + (ITEM_EVERY_S[t] + ITEM_SPARE_S if t in got else ITEM_RETRY_S)
        except Exception as e:
            for t in due:
                self.item_due[t] = now + ITEM_RETRY_S
            say('failed - %s: %s' % (type(e).__name__, e))
            self.tell('Auto SC + BR failed', '`%s: %s`' % (type(e).__name__, e), EMBED_BAD, 'Auto SC + BR')
            self.close_guis()
            return True
        missed = ', '.join(pretty(t) for t in due if t not in got)
        if got:
            self.tell('Used a ' + ' and a '.join(pretty(t) for t in got), missed and "%s wasn't used" % missed,
                      EMBED_INFO, 'Auto SC + BR')
        else:
            self.tell('Found nothing to use', missed, EMBED_INFO, 'Auto SC + BR')
        if missed:
            self.close_guis()
        return True

    def close_guis(self):
        try:
            game.close_guis()
        except Exception as e:
            note('menus', 'closing menus failed: %s: %s' % (type(e).__name__, e))

    def stop(self):
        note('run', 'Stop pressed')
        self.start_again = False
        self.restart_run = False
        game.ABORT = True
        if self.biome_stop is not None:
            self.biome_stop.set()
        self.phase('stopping', BAD)
        self.stop_b.configure(state='disabled')
        threading.Thread(target=game.release_all, daemon=True).start()

    def close(self):
        """X stops a run if one is going, else quits."""
        if self.running:
            self.stop()
            return
        self._closing = True
        if self.biome_stop is not None:
            self.biome_stop.set()
        self.remember()
        self.block_on = False
        try:                                            # so Roblox gets the real animations back
            with self.block_lock:
                if self.blocked or self.cache.ours:
                    self._unblock({k for ks in merchant_cache.FILES.values() for k in ks})
        except Exception:
            pass
        try:
            game.ABORT = True
            game.disarm()
            game.release_all(focus=False)
        except Exception:
            pass
        self.root.destroy()
        os._exit(0)     # lingering threads would keep the exe alive


UNPACK_MARKS = ('auras.json', 'eden.png', 'gui_points.json')     # files only our own _MEI folders have


def clear_old_unpacks(temp=None, current=None, fresh_s=120):
    """Delete _MEI folders left by killed or crashed exes. A running exe's DLL can't be deleted, so it stays."""
    current = current or getattr(sys, '_MEIPASS', None)
    temp = temp or tempfile.gettempdir()
    gone = 0
    for d in glob.glob(os.path.join(temp, '_MEI*')):
        if current and os.path.normcase(os.path.abspath(d)) == os.path.normcase(os.path.abspath(current)):
            continue
        if not d.endswith('-old'):                          # -old: ours, half deleted
            if not all(os.path.isfile(os.path.join(d, f)) for f in UNPACK_MARKS):
                continue                                    # another program's
            core = sorted(glob.glob(os.path.join(d, 'python3*.dll')), key=len, reverse=True)[:1]
            try:
                if not core or time.time() - os.path.getmtime(d) < fresh_s:
                    continue
                os.remove(core[0])                          # fails while any MMacro has it loaded
                os.rename(d, d + '-old')
            except OSError:
                continue
            d += '-old'
        shutil.rmtree(d, ignore_errors=True)
        gone += not os.path.exists(d)
    return gone


def _clear_old_unpacks():
    try:
        n = clear_old_unpacks()
        if n:
            note('cleanup', 'deleted %d old unpacked cop%s of MMacro from %%TEMP%%' % (n, 'y' if n == 1 else 'ies'))
    except Exception as e:
        note('cleanup', '%s: %s' % (type(e).__name__, e))


def only_one():
    """None if we may run, else why not. One per session, one per Windows account (shared logs)."""
    global _one
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    _one = [k.CreateMutexW(None, False, 'Local\\MMacro')]
    if ctypes.get_last_error() == 183:                  # ERROR_ALREADY_EXISTS
        return 'MMacro is already open.'
    user = re.sub(r'[^\w.-]', '_', os.environ.get('USERDOMAIN', '') + '.' + os.environ.get('USERNAME', ''))
    _one.append(k.CreateMutexW(None, False, 'Global\\MMacro-' + user))
    if ctypes.get_last_error() == 183:
        return ('MMacro is already running for this Windows account in another session (another RDP).\n\n'
                'Two macros on one account share Roblox\'s logs and MMacro\'s settings, so each RDP needs its own '
                'Windows account. Log the second RDP into a different account, then open MMacro there.')
    return None


if __name__ == '__main__':
    root = tk.Tk()
    why = only_one()
    if why:
        root.withdraw()
        messagebox.showinfo(TITLE, why)
        sys.exit(0)
    threading.Thread(target=_clear_old_unpacks, daemon=True).start()
    App(root)
    root.mainloop()
