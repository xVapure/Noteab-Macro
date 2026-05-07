import os
import time
import json
import threading
import autoit
import keyboard
import mouse

class RecorderMixin:
    # ── Camera alignment ─────────────────────────────────────────────
    def align_camera(self):
        def _align():
            print("[Camera] Aligning camera...")
            collections_btn = self.config.get("collections_button", [0, 0])
            exit_collections_btn = self.config.get("exit_collections_button", [0, 0])

            if collections_btn[0] > 0:
                autoit.mouse_click("left", collections_btn[0], collections_btn[1])
                time.sleep(0.3)

            if exit_collections_btn[0] > 0:
                autoit.mouse_click("left", exit_collections_btn[0], exit_collections_btn[1])
                time.sleep(0.3)

            start_x = exit_collections_btn[0] if exit_collections_btn[0] > 0 else 500
            start_y = exit_collections_btn[1] if exit_collections_btn[1] > 0 else 500
            autoit.mouse_move(start_x, start_y)
            autoit.mouse_down("right")
            time.sleep(0.1)
            autoit.mouse_move(start_x, start_y + 75)
            time.sleep(0.1)
            autoit.mouse_up("right")
            time.sleep(0.2)
            print("[Camera] Alignment finished.")

        threading.Thread(target=_align, daemon=True).start()

    # ── Recording ────────────────────────────────────────────────────
    def start_recording_path(self):
        if getattr(self, "_is_recording", False):
            return
        print("[Recorder] Recording started...")
        self._is_recording = True
        self._recorded_events = []
        self._record_start_time = time.time()
        mouse.hook(self._on_mouse_event)
        keyboard.hook(self._on_keyboard_event)

    def _on_mouse_event(self, event):
        if not getattr(self, "_is_recording", False):
            return
        t = time.time() - self._record_start_time
        path_evt = {"type": "", "x": 0, "y": 0, "button": "", "key": "", "delta": 0, "t": t}
        valid = False
        if isinstance(event, mouse.MoveEvent):
            path_evt["type"] = "mouse_move"
            path_evt["x"] = event.x
            path_evt["y"] = event.y
            valid = True
        elif isinstance(event, mouse.ButtonEvent):
            path_evt["type"] = "mouse_down" if event.event_type == "down" else "mouse_up"
            path_evt["button"] = str(event.button).lower()
            valid = True
        elif isinstance(event, mouse.WheelEvent):
            path_evt["type"] = "mouse_wheel"
            path_evt["delta"] = int(event.delta)
            valid = True
        if valid:
            self._recorded_events.append(path_evt)

    def _on_keyboard_event(self, event):
        if not getattr(self, "_is_recording", False):
            return
        t = time.time() - self._record_start_time
        key_name = str(event.name).lower()
        if key_name in ("f1", "f2", "f3", "f4"):
            return
        self._recorded_events.append({
            "type": "key_down" if event.event_type == "down" else "key_up",
            "x": 0, "y": 0, "button": "", "key": key_name, "delta": 0, "t": t,
        })

    def stop_recording_path(self, filename, save_dir="recorded_files"):
        if not getattr(self, "_is_recording", False):
            return "Not recording."

        self._is_recording = False
        try:
            mouse.unhook(self._on_mouse_event)
        except Exception:
            pass
        try:
            keyboard.unhook(self._on_keyboard_event)
        except Exception:
            pass

        # Trim trailing left-click noise
        if self._recorded_events:
            cutoff_t = self._recorded_events[-1]["t"] - 0.5
            while self._recorded_events and self._recorded_events[-1]["t"] > cutoff_t:
                last = self._recorded_events[-1]
                if last["type"] in ("mouse_down", "mouse_up", "mouse_move") and last.get("button", "left") == "left":
                    self._recorded_events.pop()
                else:
                    break

        print(f"[Recorder] Stopped recording, saving to {save_dir}/{filename}.json...")
        os.makedirs(save_dir, exist_ok=True)
        filepath = os.path.join(save_dir, f"{filename}.json")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({"events": self._recorded_events}, f, indent=4)
            return "OK"
        except Exception as e:
            return str(e)

    # ── Replay ───────────────────────────────────────────────────────
    def replay_path_recording(self, filename, save_dir="recorded_files"):
        filepath = os.path.join(save_dir, f"{filename}.json")
        if not os.path.exists(filepath):
            return f"Error: File not found: {filepath}"

        print(f"[Recorder] Loading macro from {filepath}")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            events = data.get("events", [])
        except Exception as e:
            return f"Error: Failed to load file: {e}"

        self._cancel_replay = False

        def _on_esc():
            print("[Recorder] Replay cancelled by user (ESC).")
            self._cancel_replay = True

        try:
            keyboard.add_hotkey("esc", _on_esc)
        except Exception as e:
            print(f"Failed to bind ESC: {e}")

        start_time = time.time()
        pressed_keys = set()

        for event in events:
            if self._cancel_replay:
                break
            target_time = start_time + event.get("t", 0.0)
            now = time.time()
            if target_time > now:
                if target_time - now > 0.02:
                    time.sleep((target_time - now) - 0.015)
                while time.time() < target_time:
                    if self._cancel_replay:
                        break

            if self._cancel_replay:
                break

            typ = event.get("type", "")
            if typ == "mouse_move":
                autoit.mouse_move(int(event.get("x", 0)), int(event.get("y", 0)), speed=0)
            elif typ in ("mouse_down", "mouse_up"):
                getattr(autoit, typ)(event.get("button", "left"))
            elif typ == "mouse_wheel":
                autoit.mouse_wheel("up" if event.get("delta", 0) > 0 else "down", abs(event.get("delta", 0)))
            elif typ in ("key_down", "key_up"):
                k = event.get("key", "")
                if k and k not in ("f1", "f2", "f3", "f4", "esc"):
                    try:
                        if typ == "key_down":
                            keyboard.press(k)
                            pressed_keys.add(k)
                        else:
                            keyboard.release(k)
                            pressed_keys.discard(k)
                    except Exception:
                        pass

        # Release any stuck keys
        if pressed_keys:
            print(f"[Recorder] Releasing {len(pressed_keys)} stuck keys...")
            for k in list(pressed_keys):
                try:
                    keyboard.release(k)
                except Exception:
                    pass

        try:
            keyboard.remove_hotkey(_on_esc)
        except Exception:
            pass

        print("[Recorder] Macro finished.")
        return "Cancelled" if self._cancel_replay else "Finished"
