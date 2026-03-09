import traceback
import pygetwindow as gw
from tkinter import messagebox, filedialog, simpledialog
import tkinter as tk
from PIL import Image, ImageTk
from datetime import datetime, timedelta, timezone
import ttkbootstrap as ttk
import logging
import shutil, glob
import atexit
import difflib
import itertools
import zipfile, subprocess, tempfile
import json, requests, time, os, threading, re, webbrowser, random, keyboard, pyautogui, autoit, psutil, \
    locale, win32gui, win32process, win32con, ctypes, queue, mouse, sys


current_ver = os.environ.get("COTEAB_MACRO_VERSION", "v2.1.0-hotfix2")
rare_biomes = ["GLITCHED", "DREAMSPACE", "CYBERSPACE"]

class ConfigVar:
    def __init__(self, config: dict, key: str, default=None):
        self._cfg = config
        self._key = key
        self._default = default

    def get(self):
        return self._cfg.get(self._key, self._default)

    def set(self, value):
        self._cfg[self._key] = value


def fuzzy_match_any(text, candidates, threshold=0.6):
    try:
        import difflib
    except Exception:
        return False

    if not text:
        return False

    t = str(text).lower().strip()
    tokens = [tok for tok in re.split(r"\s+|[^a-z0-9]", t) if tok]

    for cand in candidates:
        c = str(cand).lower().strip()
        if not c:
            continue
        if c in t:
            return True
        try:
            whole_ratio = difflib.SequenceMatcher(None, c, t).ratio()
            if whole_ratio >= threshold:
                return True
        except Exception:
            pass
        for tok in tokens:
            try:
                if difflib.SequenceMatcher(None, c, tok).ratio() >= threshold:
                    return True
            except Exception:
                pass
    return False

def fuzzy_correct_item_name(text, mapping, threshold=0.6):
    try:
        import difflib
    except Exception:
        return text

    if not text:
        return text

    t = str(text).lower().strip()
    for mis, correct in mapping.items():
        if t == mis.lower().strip():
            return correct
    tokens = [tok for tok in re.split(r"\s+|[^a-z0-9]", t) if tok]

    best_score = 0.0
    best_correct = None
    best_key = None

    for mis, correct in mapping.items():
        mis_norm = str(mis).lower().strip()
        try:
            if mis_norm in t:
                return correct
        except Exception:
            pass
        try:
            score_whole = difflib.SequenceMatcher(None, t, mis_norm).ratio()
            if score_whole > best_score:
                best_score = score_whole
                best_correct = correct
                best_key = mis
        except Exception:
            pass
        for tok in tokens:
            try:
                score_tok = difflib.SequenceMatcher(None, tok, mis_norm).ratio()
                if score_tok > best_score:
                    best_score = score_tok
                    best_correct = correct
                    best_key = mis
            except Exception:
                pass

    if best_score >= float(threshold):
        return best_correct

    return text

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
        self.snipping_window = ttk.Toplevel(self.root)
        self.snipping_window.attributes('-fullscreen', True)
        self.snipping_window.attributes('-alpha', 0.3)
        self.snipping_window.configure(bg="lightblue", cursor="cross_reverse")

        self.snipping_window.bind("<Button-1>", self.on_mouse_press)
        self.snipping_window.bind("<B1-Motion>", self.on_mouse_drag)
        self.snipping_window.bind("<ButtonRelease-1>", self.on_mouse_release)

        self.canvas = ttk.Canvas(self.snipping_window, bg="lightblue", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

    # hi im tea (ffffffffff)

    def on_mouse_press(self, event):
        self.begin_x = event.x
        self.begin_y = event.y
        self.canvas.delete("selection_rect")

    def on_mouse_drag(self, event):
        self.end_x, self.end_y = event.x, event.y
        self.canvas.delete("selection_rect")
        self.canvas.create_rectangle(self.begin_x, self.begin_y, self.end_x, self.end_y,
                                     outline="white", width=2, tag="selection_rect")

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


class CalibrationManager:
    def __init__(self):
        self._queue = queue.Queue()
        self._window = None  # pywebview window ref
        self._tracker = None
        self._save_fn = None
        self._emit_fn = None
        self._overlay_window = None
        threading.Thread(target=self._tk_loop, daemon=True).start()

    def set_refs(self, window, tracker, save_fn, emit_fn):
        self._window = window
        self._tracker = tracker
        self._save_fn = save_fn
        self._emit_fn = emit_fn

    def request_calibration(self, config_key, window_type="point"):
        print(f"[CalibrationManager] Queued snip for '{config_key}', type: {window_type}")
        self._queue.put({"action": "calibrate", "key": config_key, "type": window_type})

    def request_display(self, config_key, label=None, duration_ms=2500):
        self._queue.put({
            "action": "display",
            "key": config_key,
            "label": label or str(config_key),
            "duration_ms": int(duration_ms) if duration_ms else 2500
        })

    def request_display_many(self, items, duration_ms=2500):
        self._queue.put({
            "action": "display_many",
            "items": items if isinstance(items, list) else [],
            "duration_ms": int(duration_ms) if duration_ms else 2500
        })

    def _destroy_overlay(self):
        try:
            if self._overlay_window is not None:
                try:
                    self._overlay_window.destroy()
                except Exception:
                    pass
                self._overlay_window = None
        except Exception:
            self._overlay_window = None

    def _render_calibration_overlay(self, root, value, label, duration_ms=2500):
        try:
            if not isinstance(value, (list, tuple)) or len(value) < 2:
                return

            self._destroy_overlay()
            overlay = ttk.Toplevel(root)
            overlay.overrideredirect(True)
            overlay.attributes("-topmost", True)
            try:
                overlay.attributes("-alpha", 0.22)
            except Exception:
                pass

            screen_w = overlay.winfo_screenwidth()
            screen_h = overlay.winfo_screenheight()
            overlay.geometry(f"{screen_w}x{screen_h}+0+0")
            overlay.configure(bg="black")

            canvas = ttk.Canvas(overlay, bg="black", highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            is_region = len(value) >= 4
            if is_region:
                x, y, w, h = int(value[0]), int(value[1]), max(1, int(value[2])), max(1, int(value[3]))
                x2, y2 = x + w, y + h
                color = "#00ff87"
                canvas.create_rectangle(x, y, x2, y2, outline=color, width=3)
                text = f"{label}: ({x}, {y}, {w}, {h})"
                tx = max(10, min(screen_w - 10, x + 6))
                ty = max(24, min(screen_h - 10, y - 10))
                text_id = canvas.create_text(
                    tx,
                    ty,
                    text=text,
                    anchor="sw",
                    fill=color,
                    font=("Segoe UI", 13, "bold")
                )
                bbox = canvas.bbox(text_id)
                if bbox:
                    pad = 5
                    bg = canvas.create_rectangle(
                        bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad,
                        fill="#000000", outline=color, width=1
                    )
                    canvas.tag_lower(bg, text_id)
            else:
                x, y = int(value[0]), int(value[1])
                color = "#ffcc00"
                radius = 11
                canvas.create_oval(x - radius, y - radius, x + radius, y + radius, outline=color, width=3)
                canvas.create_line(x - 24, y, x + 24, y, fill=color, width=2)
                canvas.create_line(x, y - 24, x, y + 24, fill=color, width=2)
                text = f"{label}: ({x}, {y})"
                tx = max(10, min(screen_w - 10, x + 20))
                ty = max(24, min(screen_h - 10, y - 18))
                text_id = canvas.create_text(
                    tx,
                    ty,
                    text=text,
                    anchor="sw",
                    fill=color,
                    font=("Segoe UI", 13, "bold")
                )
                bbox = canvas.bbox(text_id)
                if bbox:
                    pad = 5
                    bg = canvas.create_rectangle(
                        bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad,
                        fill="#000000", outline=color, width=1
                    )
                    canvas.tag_lower(bg, text_id)

            def _close_overlay(_evt=None):
                self._overlay_window = None
                try:
                    overlay.destroy()
                except Exception:
                    pass

            overlay.bind("<Escape>", _close_overlay)
            overlay.bind("<Button-1>", _close_overlay)
            overlay.after(max(600, int(duration_ms)), _close_overlay)
            overlay.focus_force()
            self._overlay_window = overlay
        except Exception as e:
            try:
                print(f"[CalibrationManager] Failed to render overlay: {e}")
            except Exception:
                pass

    def _render_calibration_overlay_many(self, root, items, duration_ms=2500):
        try:
            valid_items = []
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    value = item.get("value")
                    if not isinstance(value, (list, tuple)) or len(value) < 2:
                        continue
                    label = str(item.get("label", item.get("key", "Calibration")))
                    valid_items.append({"label": label, "value": value})

            if not valid_items:
                return

            self._destroy_overlay()
            overlay = ttk.Toplevel(root)
            overlay.overrideredirect(True)
            overlay.attributes("-topmost", True)
            try:
                overlay.attributes("-alpha", 0.20)
            except Exception:
                pass

            screen_w = overlay.winfo_screenwidth()
            screen_h = overlay.winfo_screenheight()
            overlay.geometry(f"{screen_w}x{screen_h}+0+0")
            overlay.configure(bg="black")

            canvas = ttk.Canvas(overlay, bg="black", highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)

            title_id = canvas.create_text(
                20, 20,
                text="Fishing Calibrations (all values)",
                anchor="nw",
                fill="#ffffff",
                font=("Segoe UI", 15, "bold")
            )
            title_bbox = canvas.bbox(title_id)
            if title_bbox:
                canvas.create_rectangle(
                    title_bbox[0] - 6, title_bbox[1] - 4, title_bbox[2] + 6, title_bbox[3] + 4,
                    fill="#111111", outline="#dddddd", width=1
                )
                canvas.tag_raise(title_id)

            colors = ["#ffcc00", "#00ff87", "#66b3ff", "#ff77aa", "#c2ff4d", "#ff9f40", "#b794f4"]
            for idx, item in enumerate(valid_items):
                label = item["label"]
                value = item["value"]
                color = colors[idx % len(colors)]
                is_region = len(value) >= 4

                if is_region:
                    x = int(value[0])
                    y = int(value[1])
                    w = max(1, int(value[2]))
                    h = max(1, int(value[3]))
                    x2, y2 = x + w, y + h
                    canvas.create_rectangle(x, y, x2, y2, outline=color, width=3)
                    text = f"{label}: ({x}, {y}, {w}, {h})"
                    tx = max(10, min(screen_w - 10, x + 6))
                    ty = max(24, min(screen_h - 10, y - 10))
                else:
                    x = int(value[0])
                    y = int(value[1])
                    radius = 10
                    canvas.create_oval(x - radius, y - radius, x + radius, y + radius, outline=color, width=3)
                    canvas.create_line(x - 22, y, x + 22, y, fill=color, width=2)
                    canvas.create_line(x, y - 22, x, y + 22, fill=color, width=2)
                    text = f"{label}: ({x}, {y})"
                    tx = max(10, min(screen_w - 10, x + 18))
                    ty = max(24, min(screen_h - 10, y - 16))

                text_id = canvas.create_text(
                    tx,
                    ty,
                    text=text,
                    anchor="sw",
                    fill=color,
                    font=("Segoe UI", 12, "bold")
                )
                bbox = canvas.bbox(text_id)
                if bbox:
                    bg = canvas.create_rectangle(
                        bbox[0] - 4, bbox[1] - 3, bbox[2] + 4, bbox[3] + 3,
                        fill="#000000", outline=color, width=1
                    )
                    canvas.tag_lower(bg, text_id)

            def _close_overlay(_evt=None):
                self._overlay_window = None
                try:
                    overlay.destroy()
                except Exception:
                    pass

            overlay.bind("<Escape>", _close_overlay)
            overlay.bind("<Button-1>", _close_overlay)
            overlay.after(max(700, int(duration_ms)), _close_overlay)
            overlay.focus_force()
            self._overlay_window = overlay
        except Exception as e:
            try:
                print(f"[CalibrationManager] Failed to render multi overlay: {e}")
            except Exception:
                pass

    def _tk_loop(self):
        root = tk.Tk()
        root.withdraw()

        def poll():
            try:
                req = self._queue.get_nowait()
                action = req.get("action", "calibrate")
                config_key = req.get("key")

                if action == "display_many":
                    duration_ms = req.get("duration_ms", 2500)
                    items = req.get("items", [])
                    self._render_calibration_overlay_many(root, items, duration_ms=duration_ms)
                    root.after(100, poll)
                    return

                if action == "display":
                    if not config_key:
                        root.after(100, poll)
                        return
                    label = req.get("label", str(config_key))
                    duration_ms = req.get("duration_ms", 2500)
                    value = None
                    try:
                        if self._tracker and hasattr(self._tracker, "config"):
                            value = self._tracker.config.get(config_key)
                    except Exception:
                        value = None
                    self._render_calibration_overlay(root, value, label, duration_ms=duration_ms)
                    root.after(100, poll)
                    return

                if not config_key:
                    root.after(100, poll)
                    return
                window_type = req["type"]

                print(f"[CalibrationManager] Opening snipping widget for '{config_key}'")

                if self._window is not None:
                    try: self._window.hide()
                    except: pass

                def on_snip(region):
                    if window_type == "point":
                        value = [region[0], region[1]]
                    else:
                        value = [region[0], region[1], region[2], region[3]]

                    if self._tracker and hasattr(self._tracker, 'config'):
                        self._tracker.config[config_key] = value
                        if self._save_fn:
                            self._save_fn(self._tracker.config)

                    if self._window is not None:
                        try: self._window.show()
                        except: pass

                    if self._emit_fn:
                        self._emit_fn({"key": config_key, "value": value})

                snipper = SnippingWidget(root, config_key=config_key, callback=on_snip)
                snipper.start()
                if hasattr(snipper, 'snipping_window') and snipper.snipping_window:
                    snipper.snipping_window.focus_force()

            except queue.Empty:
                pass

            root.after(100, poll)

        root.after(100, poll)
        root.mainloop()

class ActionScheduler:
    def __init__(self, owner, worker_name="ActionScheduler"):
        self.owner = owner
        self._pq = queue.PriorityQueue()
        self._counter = itertools.count()
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker, name=worker_name, daemon=True)
        self._worker_thread.start()
        self._action_lock = threading.RLock()
        self._action_active = threading.Event()

    def enqueue_action(self, fn, name=None, priority=5, block=False, timeout=None):
        idx = next(self._counter)
        qname = name or f"action-{idx}"
        self._pq.put((priority, idx, qname, fn))
        if block:
            start = time.time()
            while True:
                with self._action_lock:
                    pass
                if timeout is not None and (time.time() - start) > timeout:
                    break
                time.sleep(0.08)
            return True
        return True

    def _worker(self):
        while self._running:
            try:
                try:
                    priority, idx, name, fn = self._pq.get(timeout=0.7)
                except Exception:
                    continue

                self._action_active.set()
                self._action_lock.acquire()
                try:
                    try:
                        fn()
                    except Exception:
                        try:
                            self.owner.error_logging(
                                sys.exc_info(),
                                f"Error executing scheduled action {name}"
                            )
                        except Exception:
                            pass
                finally:
                    try:
                        self._action_lock.release()
                    except Exception:
                        pass
                    self._action_active.clear()

            except Exception:
                self._action_active.clear()
                try:
                    self._action_lock.release()
                except Exception:
                    pass

    def stop(self):
        self._running = False
        try:
            while not self._pq.empty():
                self._pq.get_nowait()
        except Exception:
            pass
