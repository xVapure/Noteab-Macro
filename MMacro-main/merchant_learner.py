"""Merchant Learner: watches Roblox's cache (rbx-storage.db) and, when you say a merchant just arrived (F8 or its
button), counts the animations Roblox used in the minute and a half before as seen with that merchant: their addresses
(the lookup rows, for detection) and their downloaded files' keys (for blocking). Any number of visits: what turned
up in most of them is kept. Saves them where MMacro reads them.
With "Read chat" on it also reads Roblox's chat, and a "<merchant> has arrived" line does what F8 does, so it can be
left on all night. Boss ("... is patrolling the graveyard" in chat) keeps every kind of asset, not just animations.
Reads the cache and the screen only: nothing in Roblox is changed, blocked or sent anywhere."""
import ctypes
import glob
import json
import math
import os
import queue
import re
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import messagebox

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')      # numpy's maths library sets memory aside for every core as
                                                        # it loads, and a PC short of it cannot open the learner

MERCHANTS = ('Mari', 'Jester', 'Rin')
BOSS = 'Boss'
NAMES = MERCHANTS + (BOSS,)
LEARN_S = 90
ANIMATION = '24'
KINDS = {'1': 'image', '3': 'sound', '4': 'mesh', '24': 'animation', '39': 'model', '63': 'texture pack'}
MODEL = b'<roblox!'                     # an animation's file is a binary Roblox model
_ADDRESS = re.compile(rb'/(?:v\d+/)?sc\d+/([0-9a-f]{32})')
_KIND = re.compile(rb'roblox-assettypeid: (\d+)')
LOCAL = os.getenv('LOCALAPPDATA') or os.path.expanduser('~')
DB = os.path.join(LOCAL, 'Roblox', 'rbx-storage.db')
BLOBS = os.path.join(LOCAL, 'Roblox', 'rbx-storage')
OUT_DIR = os.path.join(LOCAL, 'MMacro')
OUT = os.path.join(OUT_DIR, 'merchant_hashes.json')
LOG = os.path.join(OUT_DIR, 'merchant_learner.txt')
SETTINGS = os.path.join(OUT_DIR, 'merchant_learner_settings.json')
CHAT_S = 3                      # how often chat is read
WAIT_S = 20                     # after the chat line, for the merchant's animations to load
COOLDOWN_S = 600                # the line stays in chat a while: one visit is read once
GONE_S = 60                     # and only once it has been out of chat this long can it be read again
SAME_VISIT_S = 300              # F8 and chat on one visit count it once
WARM_S = 120                    # right after opening, everything Roblox loads looks new
BOSS_BEFORE_S = 15              # the boss loads around its line: a short window keeps other players' auras out
_ARRIVED = re.compile(r'(?<![a-z])(mari|jester|rin)\W*(?:has\W*)?ar+iv')   # OCR sometimes drops the spaces
_BOSS = re.compile(r'patrol+ing')          # "Sinister S. is patrolling the graveyard.."

BG, PANEL, TEXT, DIM, GOOD, ACCENT = '#16161d', '#1f1f29', '#e8e8f0', '#8a8aa0', '#5fd38d', '#8b7cf7'


def touched(since_ms, path=DB):
    """[(address, atime ms, asset type)] of the asset rows Roblox used after since_ms."""
    if not os.path.exists(path):
        return []
    con = sqlite3.connect(path, timeout=2)
    try:
        con.execute('PRAGMA query_only = 1')
        out = []
        for content, atime in con.execute('SELECT content, atime FROM files WHERE category = 11 AND atime > ?',
                                          (int(since_ms),)):
            kind = _KIND.search(content or b'')
            m = kind and _ADDRESS.search(content)
            if m:
                out.append((m.group(1).decode(), atime, kind.group(1).decode()))
        return out
    finally:
        con.close()


def touched_files(since_ms, path=DB):
    """[(key hex, atime ms)] of the downloaded-file rows Roblox used after since_ms."""
    if not os.path.exists(path):
        return []
    con = sqlite3.connect(path, timeout=2)
    try:
        con.execute('PRAGMA query_only = 1')
        return [(k.hex(), a) for k, a in con.execute('SELECT id, atime FROM files WHERE category = 10 AND atime > ?',
                                                     (int(since_ms),))]
    finally:
        con.close()


def body(key, path=DB):
    """The file Roblox keeps under this key (inline or in rbx-storage), without its RBXH header; None if gone."""
    con = sqlite3.connect(path, timeout=2)
    try:
        con.execute('PRAGMA query_only = 1')
        row = con.execute('SELECT content FROM files WHERE id = ?', (bytes.fromhex(key),)).fetchone()
    finally:
        con.close()
    data = row[0] if row and row[0] else None
    if data is None:
        try:
            with open(os.path.join(os.path.dirname(path), 'rbx-storage', key[:2], key), 'rb') as f:
                data = f.read()
        except OSError:
            return None
    if data[:4] != b'RBXH' or len(data) < 37:
        return data
    url_len = int.from_bytes(data[8:12], 'little')
    off = 13 + url_len
    headers_len = int.from_bytes(data[off + 4:off + 8], 'little')
    body_len = int.from_bytes(data[off + 12:off + 16], 'little')
    start = off + 24 + headers_len
    return data[start:start + body_len]


def is_model(key, path=DB):
    b = body(key, path)
    return bool(b) and b.startswith(MODEL)


def kept(counts, visits):
    """What turned up in at least 60% of the visits (every one, for 1 or 2), so one late F8 spoils nothing."""
    need = max(1, math.ceil(visits * 0.6))
    return {k for k, n in counts.items() if n >= need}


def load(path=OUT):
    """(counts, visits, file counts): per merchant, how many visits each address / file key turned up in."""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}

    def table(key):
        t = data.get(key) if isinstance(data.get(key), dict) else {}
        return {n: {k: int(v) for k, v in (t.get(n) or {}).items()} for n in NAMES}
    visits = data.get('visits') if isinstance(data.get('visits'), dict) else {}
    counts, file_counts = table('counts'), table('file_counts')
    # a visit that caught nothing (older builds counted those) only raises the bar for the real ones
    return counts, {n: int(visits.get(n) or 0) if counts[n] or file_counts[n] else 0 for n in NAMES}, file_counts


def save(counts, visits, file_counts, path=OUT):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {n: sorted(kept(counts[n], visits[n])) for n in NAMES}
    data['files'] = {n: sorted(kept(file_counts[n], visits[n])) for n in NAMES}
    data['visits'] = visits
    data['counts'] = counts
    data['file_counts'] = file_counts
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)


def arrival(lines):
    """The merchant (or Boss) a chat line says arrived, else None."""
    for text in list(lines) + [' '.join(lines)]:
        text = text.lower().replace('1', 'i').replace('|', 'i')
        m = _ARRIVED.search(text)
        if m:
            return m.group(1).capitalize()
        if _BOSS.search(text):
            return BOSS
    return None


_ocr = None
OCR_THREADS = min(4, os.cpu_count() or 4)


def load_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        try:
            _ocr = RapidOCR(intra_op_num_threads=OCR_THREADS)
        except Exception:
            _ocr = RapidOCR()
    return _ocr


def ocr_lines(img):
    """The text lines OCR finds in a BGR picture."""
    import numpy as np
    result, _ = load_ocr()(np.ascontiguousarray(img), use_cls=False)
    return [r[1] for r in result] if result else []


MARK = 'merchant_learner.mark'      # in every copy the one-file exe unpacks


def clear_old_unpacks(temp=None, current=None, fresh_s=120):
    """Delete the copies of itself the one-file exe unpacked into %TEMP% and never got to remove (killed, crashed,
    Windows shut down under it). A running copy's Python DLL cannot be deleted, so that copy is left whole, and so is
    one changed in the last fresh_s seconds (still unpacking). Returns how many went."""
    current = current or getattr(sys, '_MEIPASS', None)
    temp = temp or tempfile.gettempdir()
    gone = 0
    for d in glob.glob(os.path.join(temp, '_MEI*')):
        if current and os.path.normcase(os.path.abspath(d)) == os.path.normcase(os.path.abspath(current)):
            continue
        if not d.endswith('-old'):                          # -old: one of ours, cut short while being deleted
            if not os.path.isfile(os.path.join(d, MARK)):
                continue                                    # another program's
            core = sorted(glob.glob(os.path.join(d, 'python3*.dll')), key=len, reverse=True)[:1]
            try:
                if not core or time.time() - os.path.getmtime(d) < fresh_s:
                    continue
                os.remove(core[0])                          # refused while that copy is running
                os.rename(d, d + '-old')
            except OSError:
                continue
            d += '-old'
        shutil.rmtree(d, ignore_errors=True)
        gone += not os.path.exists(d)
    return gone


def read_chat(box):
    """The text lines in a screen rectangle (left, top, width, height)."""
    import mss
    import numpy as np
    with mss.mss() as shot:
        return ocr_lines(np.asarray(shot.grab({'left': box[0], 'top': box[1], 'width': box[2], 'height': box[3]}))[..., :3])


def load_settings(path=SETTINGS):
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return bool(data.get('chat', True)), data.get('area') or None
    except (OSError, ValueError, AttributeError):
        return True, None


def save_settings(chat, area, path=SETTINGS):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'chat': chat, 'area': area}, f)
    except OSError:
        pass


def log(line):
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write('%s  %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), line))
    except OSError:
        pass


class Learner:
    def __init__(self, root, path=DB, out=OUT):
        self.root, self.path, self.out = root, path, out
        self.since = int(time.time() * 1000)
        self.opened = time.time()
        self.chat_ready = False             # lines already in chat at the first read are old
        self.first = {}                     # address: first atime seen since this opened
        self.first_files = {}               # downloaded file key: first atime seen since this opened
        self.last, self.last_files = {}, {}  # the same, latest atime
        self.kind = {}                      # address: asset type
        self.counts, self.visits, self.file_counts = load(out)
        self.events = queue.Queue()
        self.error = None
        self.closing = False
        self.reading, self.area = load_settings()
        self.chat_error = None
        self.ocr_loading = False
        self.heard = {}                     # merchant: when chat last said it arrived
        self.on_screen = {}                 # merchant: when its line was last read in chat
        self.counted_at = {}                # merchant: when a visit was last counted
        root.title('Merchant Learner')
        root.configure(bg=BG)
        root.attributes('-topmost', True)
        root.resizable(False, False)
        tk.Label(root, text='Merchant Learner', bg=BG, fg=TEXT, font=('Segoe UI Semibold', 12)).pack(padx=16, pady=(12, 0))
        tk.Label(root, text='Keep this open while you play. When a merchant arrives,\npress F8 (or its button below) '
                 'within %d s.' % LEARN_S, bg=BG, fg=DIM, font=('Segoe UI', 9), justify='center').pack(padx=16, pady=(2, 8))
        self.status = tk.Label(root, text='', bg=PANEL, fg=TEXT, font=('Segoe UI', 9), anchor='w', justify='left')
        self.status.pack(fill='x', padx=16, ipadx=8, ipady=6)
        row = tk.Frame(root, bg=BG)
        row.pack(padx=16, pady=10)
        for name in NAMES:
            tk.Button(row, text='%s arrived' % name, command=lambda n=name: self.learn(n), bg=PANEL, fg=TEXT,
                      activebackground=PANEL, activeforeground=ACCENT, relief='flat', padx=12, pady=6,
                      font=('Segoe UI Semibold', 9)).pack(side='left', padx=4)
        chat = tk.Frame(root, bg=BG)
        chat.pack(fill='x', padx=16, pady=(0, 8))
        self.chat_on = tk.BooleanVar(value=self.reading)
        tk.Checkbutton(chat, text='Read chat for merchants + boss (learns by itself)', variable=self.chat_on,
                       command=self.toggle_chat, bg=BG, fg=TEXT, selectcolor=PANEL, activebackground=BG,
                       activeforeground=TEXT, font=('Segoe UI', 9)).pack(side='left')
        tk.Button(chat, text='Set chat area', command=self.pick_area, bg=PANEL, fg=TEXT, relief='flat', padx=8,
                  font=('Segoe UI', 8)).pack(side='right')
        self.chat_status = tk.Label(root, text='', bg=BG, fg=DIM, font=('Segoe UI', 8), anchor='w')
        self.chat_status.pack(fill='x', padx=16)
        self.table = tk.Label(root, text='', bg=BG, fg=TEXT, font=('Consolas', 9), justify='left', anchor='w')
        self.table.pack(fill='x', padx=16)
        self.seen = tk.Label(root, text='', bg=BG, fg=GOOD, font=('Segoe UI', 9), anchor='w', justify='left')
        self.seen.pack(fill='x', padx=16, pady=(6, 0))
        tk.Button(root, text='Open folder', command=lambda: os.startfile(os.path.dirname(self.out)), bg=BG, fg=DIM,
                  relief='flat', font=('Segoe UI', 8)).pack(pady=(4, 10))
        self.show()
        threading.Thread(target=self.watch, daemon=True).start()
        threading.Thread(target=self.keys, daemon=True).start()
        threading.Thread(target=self.chat, daemon=True).start()
        root.after(200, self.tick)

    def poll(self):
        rows, files = touched(self.since, self.path), touched_files(self.since, self.path)
        mine = {n: self.learned(n) for n in NAMES}
        used = {}
        for address, atime, kind in rows:
            self.first.setdefault(address, atime)
            self.last[address] = atime
            self.kind[address] = kind
            for n in NAMES:
                if address in mine[n]:
                    count, at = used.get(n, (0, 0))
                    used[n] = (count + 1, max(at, atime))
        for n, (count, atime) in used.items():
            self.events.put(('used', n, atime, count))
        for key, atime in files:
            self.first_files.setdefault(key, atime)
            self.last_files[key] = atime
        self.since = max([self.since] + [r[1] for r in rows] + [a for _, a in files])

    def learned(self, name):
        return kept(self.counts[name], self.visits[name])

    def learned_files(self, name):
        return kept(self.file_counts[name], self.visits[name])

    def watch(self):
        while not self.closing:
            try:
                self.poll()
                self.error = None
            except Exception as e:
                self.error = '%s: %s' % (type(e).__name__, e)
            time.sleep(2)

    def chat(self):
        while not self.closing:
            time.sleep(CHAT_S)
            if not self.reading:
                continue
            try:
                if _ocr is None:                    # after the window is up: it takes a while
                    self.ocr_loading = True
                    load_ocr()
                    log('OCR loaded')
                self.ocr_loading = False
                if not self.area:
                    continue
                name = arrival(read_chat(self.area))
                self.chat_error = None
                if not self.chat_ready:
                    self.chat_ready = True
                    if name:
                        self.on_screen[name] = time.time()
                        log('%s arrival already in chat when reading started: old, not counted' % name)
                    continue
            except Exception as e:
                self.ocr_loading = False
                error = '%s: %s' % (type(e).__name__, e)
                if error != self.chat_error:
                    log('chat not readable: ' + error)
                self.chat_error = error
                continue
            if not name:
                continue
            now = time.time()
            fresh = now - self.on_screen.get(name, 0) > GONE_S     # not an old line still sitting in chat
            self.on_screen[name] = now
            if fresh and now - self.heard.get(name, 0) > COOLDOWN_S:
                self.heard[name] = now
                self.events.put(('heard', name, now))

    def toggle_chat(self):
        self.reading = bool(self.chat_on.get())
        self.chat_ready = False
        save_settings(self.reading, self.area)
        self.show()

    def pick_area(self):
        """Drag a box over the chat, on any monitor."""
        u = ctypes.windll.user32
        x, y, w, h = (u.GetSystemMetrics(i) for i in (76, 77, 78, 79))
        top = tk.Toplevel(self.root)
        top.overrideredirect(True)
        top.geometry('%dx%d+%d+%d' % (w, h, x, y))
        top.attributes('-alpha', 0.35)
        top.attributes('-topmost', True)
        c = tk.Canvas(top, bg='black', highlightthickness=0, cursor='cross')
        c.pack(fill='both', expand=True)
        c.create_text(-x + 30, -y + 30, anchor='nw', fill='white', font=('Segoe UI Semibold', 14),
                      text='Drag a box over Roblox\'s chat (where "Mari has arrived" shows). Esc cancels.')
        start = {}

        def press(e):
            start.update(at=(e.x, e.y, e.x_root, e.y_root),
                         box=c.create_rectangle(e.x, e.y, e.x, e.y, outline=ACCENT, width=3))

        def drag(e):
            if start:
                c.coords(start['box'], start['at'][0], start['at'][1], e.x, e.y)

        def release(e):
            if start:
                sx, sy = start['at'][2:]
                box = [min(sx, e.x_root), min(sy, e.y_root), abs(e.x_root - sx), abs(e.y_root - sy)]
                if box[2] > 20 and box[3] > 20:
                    self.area = box
                    self.chat_ready = False
                    save_settings(self.reading, self.area)
                    log('chat area set to %s' % box)
            top.destroy()
            self.show()
        c.bind('<ButtonPress-1>', press)
        c.bind('<B1-Motion>', drag)
        c.bind('<ButtonRelease-1>', release)
        top.bind('<Escape>', lambda e: top.destroy())
        top.focus_force()

    def keys(self):
        """F8 from any window, by asking for the key's state (no keyboard hook)."""
        was = False
        while not self.closing:
            held = bool(ctypes.windll.user32.GetAsyncKeyState(0x77) & 0x8000)
            if held and not was:
                self.events.put(('f8',))
            was = held
            time.sleep(0.02)

    def tick(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == 'f8':
                    self.ask()
                elif event[0] == 'heard':
                    _, name, at = event
                    log('%s arrival read in chat' % name)
                    self.seen.configure(text='%s arrived (read in chat): learning in %d s' % (name, WAIT_S))
                    since = int(at * 1000) - (BOSS_BEFORE_S if name == BOSS else LEARN_S - WAIT_S) * 1000
                    self.root.after(WAIT_S * 1000, lambda n=name, t=since: self.learn(n, t, quiet=True))
                else:
                    _, name, atime, count = event
                    at = time.strftime('%H:%M:%S', time.localtime(atime / 1000))
                    self.seen.configure(text='%s: %d learned asset(s) used at %s' % (name, count, at))
                    log('%s: %d learned asset(s) used again (cache stamp %s)' % (name, count, at))
        except queue.Empty:
            pass
        self.show()
        if not self.closing:
            self.root.after(500, self.tick)

    def show(self):
        if not os.path.exists(self.path):
            text = 'Roblox\'s cache was not found:\n%s' % self.path
        elif self.error:
            text = 'Cache not readable: %s' % self.error
        else:
            recent = sum(1 for t in self.first.values() if t >= (time.time() - LEARN_S) * 1000)
            animations = sum(k == ANIMATION for k in self.kind.values())
            text = 'Watching Roblox\'s cache: %d assets (%d animations) used since this opened,\n%d new in the last ' \
                   '%d s' % (len(self.first), animations, recent, LEARN_S)
        self.status.configure(text=text)
        if not self.reading:
            chat = 'Chat reading off: F8 only'
        elif self.ocr_loading:
            chat = 'Loading OCR... chat reading starts once it is ready'
        elif not self.area:
            chat = 'Chat reading on, but no chat area set yet: press Set chat area'
        elif self.chat_error:
            chat = 'Chat not readable: %s' % self.chat_error[:80]
        else:
            chat = 'Reading chat every %d s' % CHAT_S
        self.chat_status.configure(text=chat)
        self.table.configure(text='\n'.join('%-7s %s' % (n, '%d animation(s), %d file(s), %d visit(s)' % (
            len(self.learned(n)), len(self.learned_files(n)), self.visits[n]) if self.visits[n] else 'not learned yet')
            for n in NAMES))

    def ask(self):
        w = tk.Toplevel(self.root, bg=PANEL)
        w.title('Merchant arrived')
        w.attributes('-topmost', True)
        tk.Label(w, text='Which merchant just arrived?', bg=PANEL, fg=TEXT, font=('Segoe UI Semibold', 10)).pack(
            padx=18, pady=(12, 8))
        row = tk.Frame(w, bg=PANEL)
        row.pack(padx=18, pady=(0, 14))
        since = int(time.time() * 1000) - LEARN_S * 1000
        for name in NAMES:
            tk.Button(row, text=name, command=lambda n=name: (w.destroy(), self.learn(n, since)), bg=BG, fg=TEXT,
                      relief='flat', padx=14, pady=4).pack(side='left', padx=4)
        w.lift()
        w.focus_force()

    def learn(self, name, since=None, quiet=False):
        since = since if since is not None else int(time.time() * 1000) - LEARN_S * 1000
        if time.time() - self.counted_at.get(name, 0) < SAME_VISIT_S:
            self.seen.configure(text='%s: this visit is already counted' % name)
            log('%s: this visit is already counted' % name)
            return
        if time.time() - self.opened < WARM_S:
            text = '%s: not counted, opened %d s ago - Roblox loading looks like new stuff. Keep this open %d s ' \
                   'before a visit.' % (name, time.time() - self.opened, WARM_S)
            self.seen.configure(text=text)
            log(text)
            return
        try:
            self.poll()
        except Exception:
            pass
        # new since this opened, or seen on an earlier visit and used again now (Learner left open between visits)
        found = ({a for a, t in self.first.items() if t >= since}
                 | {a for a in self.counts[name] if self.last.get(a, 0) >= since})
        if name != BOSS:
            found = {a for a in found if self.kind.get(a) == ANIMATION}
        if not found and quiet:
            self.seen.configure(text='%s: no new animation around its chat line' % name)
            log('%s: no new animation around its chat line, not counted (%d animation(s) and %d file(s) used again '
                'then)' % (name, sum(t >= since for t in self.last.values()),
                           sum(t >= since for t in self.last_files.values())))
            return
        if not found:
            messagebox.showwarning('Merchant Learner', 'No new animation was used in the last %d s.\n\nPress it right '
                                   'after the merchant arrives, with Roblox open (on its first visit since Roblox '
                                   'was opened).' % LEARN_S, parent=self.root)
            log('%s: nothing new in the last %d s' % (name, LEARN_S))
            return
        files = ({k for k, t in self.first_files.items() if t >= since and (name == BOSS or is_model(k, self.path))}
                 | {k for k in self.file_counts[name] if self.last_files.get(k, 0) >= since})
        for a in found:
            self.counts[name][a] = self.counts[name].get(a, 0) + 1
        for k in files:
            self.file_counts[name][k] = self.file_counts[name].get(k, 0) + 1
        self.visits[name] += 1
        self.counted_at[name] = time.time()
        save(self.counts, self.visits, self.file_counts, self.out)
        animations, keys = self.learned(name), self.learned_files(name)
        log('%s visit %d: %d address(es) kept of %d seen: %s | %d file(s) kept of %d seen: %s' % (
            name, self.visits[name], len(animations), len(found), ', '.join(sorted(animations)),
            len(keys), len(files), ', '.join(sorted(keys))))
        if name == BOSS:
            kinds = {}
            for a in found:
                k = KINDS.get(self.kind.get(a), 'type %s' % self.kind.get(a))
                kinds[k] = kinds.get(k, 0) + 1
            log('Boss visit %d kinds: %s' % (self.visits[name], ', '.join(
                '%d %s' % (n, k) for k, n in sorted(kinds.items(), key=lambda x: -x[1]))))
        if self.visits[name] < 3:
            hint = '\nCatch it %d more time(s) to confirm.' % (3 - self.visits[name])
        elif len(animations) > 3 or len(keys) > 3:
            hint = '\nStill more than 3: catch it again to narrow it down.'
        else:
            hint = '\nConfirmed (more visits make it surer).'
        if quiet:
            self.seen.configure(text='%s, visit %d (from chat): %d animation(s), %d file(s) kept' % (
                name, self.visits[name], len(animations), len(keys)))
        else:
            messagebox.showinfo('Merchant Learner', '%s, visit %d: %d animation(s), %d file(s) kept.%s\n\nSaved to %s' % (
                name, self.visits[name], len(animations), len(keys), hint, self.out), parent=self.root)
        self.show()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # screen pixels, so the chat box lands where it was drawn
    except Exception:
        pass
    root = tk.Tk()
    app = Learner(root)

    def close():
        app.closing = True
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', close)

    def cleanup():
        try:
            n = clear_old_unpacks()
            if n:
                log('deleted %d old unpacked cop%s from %%TEMP%%' % (n, 'y' if n == 1 else 'ies'))
        except Exception as e:
            log('cleanup: %s: %s' % (type(e).__name__, e))
    root.after(5000, lambda: threading.Thread(target=cleanup, daemon=True).start())
    root.mainloop()


if __name__ == '__main__':
    main()
