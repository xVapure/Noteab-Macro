from .base_support import *
from .config import validate_merchant_settings
import numpy as np
from PIL import Image, ImageOps

rapidocr_lock = threading.Lock()
rapidocr_engine = None

class ActionsMixin:
    def initialize_paths_and_files(self):
        try:
            paths_folder = os.path.join(os.getcwd(), "paths")
            os.makedirs(paths_folder, exist_ok=True)

            try:
                from biome_tracker.config import get_base_path
                import shutil
                source_paths = os.path.join(str(get_base_path()), "paths")
            except Exception:
                source_paths = None

            base_url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/paths/"
            for filename in ["obby.json", "eden.json", "egg_route1.json", "egg_route2.json", "egg_route3.json"]:
                file_path = os.path.join(paths_folder, filename)
                if not os.path.exists(file_path):
                    if source_paths and os.path.exists(os.path.join(source_paths, filename)):
                        try:
                            shutil.copy2(os.path.join(source_paths, filename), file_path)
                            self.append_log(f"Copied {filename} from local workspace")
                            continue
                        except Exception:
                            pass
                    try:
                        response = requests.get(base_url + filename, timeout=5)
                        response.raise_for_status()
                        open(file_path, "w", encoding="utf-8").write(response.text)
                        self.append_log(f"Downloaded {filename}")
                    except Exception as e:
                        self.error_logging(e, f"Failed to download {filename}")
                else:
                    self.append_log(f"{filename} already exists")
        except Exception as e:
            self.error_logging(e, "Error in initialize_paths_and_files")

    def _safe_type_text(self, text):
        text = str(text)
        if not self.config.get("azerty_mode", False):
            autoit.send(text)
            return
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            autoit.send("^v")
        except Exception:
            autoit.send(text)

    def _recognize_ocr_images(self, images):
        global rapidocr_engine
        with rapidocr_lock:
            try:
                if rapidocr_engine is None:
                    from rapidocr_onnxruntime import RapidOCR
                    rapidocr_engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)
            except Exception as e:
                self.append_log(f"[RapidOCR] Initialization failed: {e}")
                return [""] * len(images)

            texts = []
            for image in images:
                try:
                    result, _ = rapidocr_engine(image.convert("RGB"))
                    raw = " ".join(str(item[1]).strip() for item in (result or []) if len(item) > 1)
                    texts.append("".join(c if ord(c) < 128 else "" for c in raw).strip())
                except Exception as e:
                    self.append_log(f"[RapidOCR] Failed: {e}")
                    texts.append("")
        return texts

    def extract_text_candidates(self, region, median_frames=False, single_pass=False, log_text=True, capture=""):
        try:
            x, y, w, h = region
            image = pyautogui.screenshot(region=(x, y, w, h)).convert("RGB")
            if single_pass:
                if capture and getattr(self, "debug_mode", False):
                    try:
                        debugdir = os.path.join(os.getenv("LOCALAPPDATA", os.getcwd()), "CoteabMacro")
                        os.makedirs(debugdir, exist_ok=True)
                        path = os.path.join(debugdir, f"{capture}_{time.time_ns()}.png")
                        image.save(path)
                    except Exception:
                        pass
                image = image.resize((image.width * 3, image.height * 3), Image.Resampling.LANCZOS)
                texts = self._recognize_ocr_images([image])
                for text in texts:
                    if text and log_text:
                        self.append_log(f"[RapidOCR] Extracted text: '{text}'")
                return texts
            median = None
            if median_frames:
                frames = [image]
                for _ in range(2):
                    time.sleep(0.05)
                    try:
                        frames.append(pyautogui.screenshot(region=(x, y, w, h)).convert("RGB"))
                    except Exception:
                        break
                if len(frames) > 1:
                    try:
                        median = Image.fromarray(np.median(np.stack([np.asarray(frame) for frame in frames]), axis=0).astype(np.uint8))
                    except Exception:
                        pass
            gray = ImageOps.autocontrast(image.convert("L"))
            pixels = np.asarray(gray)
            hist = np.bincount(pixels.ravel(), minlength=256)
            total = pixels.size
            sumall = int(np.dot(np.arange(256), hist))
            sumback = 0
            weightback = 0
            best = 0
            bestvar = -1
            for level, count in enumerate(hist):
                weightback += int(count)
                if not weightback or weightback == total:
                    continue
                weightfore = total - weightback
                sumback += level * int(count)
                meanback = sumback / weightback
                meanfore = (sumall - sumback) / weightfore
                variance = weightback * weightfore * (meanback - meanfore) ** 2
                if variance > bestvar:
                    bestvar = variance
                    best = level
            binary = gray.point(lambda value: 255 if value > best else 0)
            variants = [image]
            if median is not None:
                variants.append(median)
            variants.extend([gray, binary, ImageOps.invert(binary)])
            images = [variant.resize((variant.width * 3, variant.height * 3), Image.Resampling.LANCZOS) for variant in variants]
            texts = self._recognize_ocr_images(images)
            for text in texts:
                if text and log_text:
                    self.append_log(f"[RapidOCR] Extracted text: '{text}'")
            return texts
        except Exception as e:
            self.error_logging(e, "Error extracting OCR candidates with RapidOCR")
            return []

    def extract_text_with_rapidocr(self, region):
        try:
            x, y, w, h = region
            image = pyautogui.screenshot(region=(x, y, w, h)).convert("RGB")
            image = image.resize((image.width * 3, image.height * 3), Image.Resampling.BICUBIC)
            texts = self._recognize_ocr_images([image])
            if texts and texts[0]:
                self.append_log(f"[RapidOCR] Extracted text: '{texts[0]}'")
                return texts[0]
            self.append_log("[RapidOCR] No text detected.")
            return ""
        except Exception as e:
            self.error_logging(e, "Error extracting text with RapidOCR")
            return ""

    def _normalize_ocr_label(self, text):
        text = str(text).lower().replace("'", "").replace(chr(8226), "")
        return re.sub(r"[^a-z0-9]+", " ", text).strip()

    def _match_ocr_label(self, text, candidates, aliases=None, threshold=0.78):
        rarities = ("common", "uncommon", "rare", "epic", "legendary", "mythical", "exotic")
        tiers = {"i": "i", "1": "i", "l": "i", "ii": "ii", "11": "ii", "ll": "ii", "iii": "iii", "111": "iii", "lll": "iii", "ill": "iii"}

        def parts(value):
            words = self._normalize_ocr_label(value).split()
            if words and len(words[-1]) >= 3 and any(rarity.startswith(words[-1]) for rarity in rarities):
                words.pop()
            tier = tiers.get(words[-1], "") if words else ""
            if tier:
                words.pop()
            return " ".join(words), tier

        raw_labels = [self._normalize_ocr_label(label).split() for label in re.split(r"[|\r\n]+", str(text))]
        labels = [parts(label) for label in re.split(r"[|\r\n]+", str(text))]
        labels = [(name, tier) for name, tier in labels if name]
        if not labels:
            return ""
        scores = {}
        for candidate in candidates:
            choices = [candidate]
            choices.extend((aliases or {}).get(candidate, []))
            score = 0.0
            for choice in choices:
                exact_words = self._normalize_ocr_label(choice).split()
                if exact_words and any(
                    words[index:index + len(exact_words)] == exact_words
                    for words in raw_labels
                    for index in range(len(words) - len(exact_words) + 1)
                ):
                    score = 1.0
                name, tier = parts(choice)
                if not name:
                    continue
                for label, label_tier in labels:
                    if tier and tier != label_tier:
                        continue
                    if not tier and label_tier:
                        pass
                    elif tier != label_tier:
                        continue
                    if len(name.split()) == len(label.split()):
                        score = max(score, difflib.SequenceMatcher(None, name, label).ratio())
            scores[candidate] = score
        ranked = sorted(scores.items(), key=lambda item: (item[1], len(self._normalize_ocr_label(item[0]))), reverse=True)
        if not ranked or ranked[0][1] < threshold:
            return ""
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.02 and len(self._normalize_ocr_label(ranked[0][0])) == len(self._normalize_ocr_label(ranked[1][0])):
            return ""
        return ranked[0][0]
    def _match_merchant_item(self, texts, candidates, aliases=None, strict=False):
        def normalize(value):
            words = self._normalize_ocr_label(value).split()
            while words:
                last = words[-1]
                if re.fullmatch(r"(?:n?x|ix)\d*|\d+x", last):
                    words.pop()
                elif last.isdigit() and len(words) > 1 and words[-2] in ("x", "nx"):
                    words.pop()
                    words.pop()
                else:
                    break
            tiers = {"i": "i", "1": "i", "ii": "ii", "11": "ii", "il": "ii", "1l": "ii", "ll": "ii", "iii": "iii", "111": "iii", "lll": "iii", "ill": "iii"}
            tier = ""
            if len(words) > 1 and words[-2:] == ["1l", "l"]:
                words.pop()
                words.pop()
                tier = "ii"
            elif words and words[-1] in tiers:
                tier = tiers[words.pop()]
            return words, tier

        def score_words(wanted, actual):
            start = 0
            total = 0.0
            for word in wanted:
                found = None
                for index in range(start, len(actual)):
                    item = actual[index]
                    score = 1.0 if word == item else (
                        difflib.SequenceMatcher(None, word, item).ratio()
                        if len(word) > 2 and len(item) > 2 else 0.0
                    )
                    if score >= 0.65 and (found is None or score > found[1]):
                        found = (index, score)
                if found is None:
                    return 0.0
                start = found[0] + 1
                total += found[1]
            return total / len(actual) if actual else 0.0

        texts = texts if isinstance(texts, (list, tuple)) else [texts]
        scores = {}
        for candidate in candidates:
            choices = [candidate] + list((aliases or {}).get(candidate, []))
            best = 0.0
            for choice in choices:
                wanted, wanted_tier = normalize(choice)
                if not wanted:
                    continue
                for text in texts:
                    for label in re.split(r"[|\r\n]+", str(text)):
                        actual, actual_tier = normalize(label)
                        if not actual:
                            continue
                        if strict:
                            if wanted == actual and wanted_tier == actual_tier:
                                best = 1.0
                            continue
                        if self._normalize_ocr_label(candidate) == "void coin" and "fortune" in actual:
                            continue
                        if wanted_tier and actual_tier and wanted_tier != actual_tier:
                            continue
                        best = max(best, score_words(wanted, actual))
            scores[candidate] = best

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if not ranked or ranked[0][1] < 0.6:
            return ""
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.15:
            return ""
        return ranked[0][0]
    def _match_merchant_slots(self, texts, candidates, aliases=None, count=5, strict=False):
        values = texts if isinstance(texts, (list, tuple)) else [texts]
        raw = " ".join(str(value) for value in values if value)
        raw = re.sub(r"(?:nx|ix|x)\s*\d+", " ", raw.lower())
        if strict:
            words = self._normalize_ocr_label(raw).split()
            options = []
            seen = set()
            for candidate in candidates:
                for choice in [candidate] + list((aliases or {}).get(candidate, [])):
                    label = tuple(self._normalize_ocr_label(choice).split())
                    if label and label not in seen:
                        seen.add(label)
                        options.append((candidate, label))
            options.sort(key=lambda item: (len(item[1]), sum(map(len, item[1]))), reverse=True)
            result = []
            pos = 0
            while pos < len(words) and len(result) < count:
                match = next(((candidate, label) for candidate, label in options if tuple(words[pos:pos + len(label)]) == label), None)
                if match:
                    candidate, label = match
                    result.append(candidate)
                    pos += len(label)
                else:
                    pos += 1
                    while pos < len(words) and not any(tuple(words[pos:pos + len(label)]) == label for _, label in options):
                        pos += 1
                    result.append("")
            return (result + [""] * count)[:count]
        compact = re.sub(r"[^a-z0-9]", "", raw)
        if not compact:
            return [""] * count

        options = []
        seen = set()
        for candidate in candidates:
            choices = [candidate] + list((aliases or {}).get(candidate, []))
            for choice in choices:
                label = re.sub(r"[^a-z0-9]", "", self._normalize_ocr_label(choice))
                if label and label not in seen:
                    seen.add(label)
                    options.append((candidate, label))
        if not options:
            return [""] * count

        max_length = max(len(label) for _, label in options) + 4
        memo = {}

        def solve(slot, position):
            key = (slot, position)
            if key in memo:
                return memo[key]
            if slot >= count:
                result = (-0.03 * max(0, len(compact) - position), [])
                memo[key] = result
                return result
            if position >= len(compact):
                result = (-0.45 * (count - slot), [""] * (count - slot))
                memo[key] = result
                return result

            best = None
            for gap in range(4):
                start = position + gap
                if start >= len(compact):
                    break
                for candidate, label in options:
                    first = max(start + 1, start + len(label) - 4)
                    last = min(len(compact), start + len(label) + 4)
                    for end in range(first, last + 1):
                        part = compact[start:end]
                        ratio = difflib.SequenceMatcher(None, label, part).ratio()
                        if ratio < 0.62:
                            continue
                        rest = solve(slot + 1, end)
                        score = ratio - (abs((end - start) - len(label)) * 0.045) - (gap * 0.12) + rest[0]
                        value = (score, [candidate] + rest[1])
                        if best is None or value[0] > best[0]:
                            best = value

            for length in range(1, min(max_length, len(compact) - position) + 1):
                rest = solve(slot + 1, position + length)
                score = -0.75 - (length * 0.02) + rest[0]
                value = (score, [""] + rest[1])
                if best is None or value[0] > best[0]:
                    best = value

            if best is None:
                best = (-0.9, [""] + [""] * (count - slot - 1))
            memo[key] = best
            return best

        return (solve(0, 0)[1] + [""] * count)[:count]

    def _consensus_ocr_match(self, texts, candidates, aliases=None, threshold=0.78, min_votes=2):
        votes = {}
        for text in texts:
            match = self._match_ocr_label(text, candidates, aliases, threshold)
            if match:
                votes[match] = votes.get(match, 0) + 1
        ranked = sorted(votes.items(), key=lambda item: item[1], reverse=True)
        if not ranked or ranked[0][1] < min_votes:
            return ""
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            return ""
        return ranked[0][0]

    def load_notice_tab(self):
        url = "https://raw.githubusercontent.com/xVapure/Noteab-Macro/refs/heads/main/assets/noticetabcontents.txt"
        data = ""
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            data = r.text
        except Exception as e:
            print(f"Error loading noticetabcontents.txt from {url}: {e}")
            self.error_logging(e, f"Error loading noticetabcontents.txt from {url}")

        return data

    def is_roblox_focused(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd: return False
            try:
                _, fg_pid = win32process.GetWindowThreadProcessId(hwnd)
                if fg_pid:
                    my_session = ctypes.c_ulong()
                    ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(my_session))
                    their_session = ctypes.c_ulong()
                    ctypes.windll.kernel32.ProcessIdToSessionId(fg_pid, ctypes.byref(their_session))
                    if my_session.value != their_session.value: return False
            except Exception: pass
            title = (win32gui.GetWindowText(hwnd) or "").lower()
            if "roblox" in title: return True
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid:
                    proc = psutil.Process(pid)
                    pname = (proc.name() or "").lower()
                    if "roblox" in pname: return True
            except Exception: pass
            return False
        except Exception: return False

    def _is_fishing_blocked(self) -> bool:
        try:
            return (
                bool(self.is_fishing_mode_enabled())
                and not bool(getattr(self, "_remote_running", False))
                and not bool(getattr(self, "_fishing_br_sc_override", False))
                and not bool(getattr(self, "_fishing_action_override", False))
                and not bool(self.config.get("enable_idle_mode", False))
            ) or bool((getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)))
        except Exception:
            return False

    def _sleep_with_cancel(self, seconds: float, poll: float = 0.05, allow_fishing=False) -> bool:
        end = time.monotonic() + max(0.0, float(seconds))
        while time.monotonic() < end:
            if (not self.detection_running
                    or (self._is_fishing_blocked() and not allow_fishing)
                    or bool(getattr(self, "auto_pop_state", False))):
                return False
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(poll, remaining))
        return (self.detection_running
                and (allow_fishing or not self._is_fishing_blocked())
                and not bool(getattr(self, "auto_pop_state", False)))

    def _run_fishing_action(self, fn, name="fishing_action"):
        if not self.detection_running or self._detection_stop_event.is_set():
            return
        if not self.is_fishing_mode_enabled() or not getattr(self, "_fishing_worker_active", False):
            return fn()
        api = getattr(self, "_fishing_api", None)
        if api is not None and hasattr(api, "queue_fishing_action"):
            return api.queue_fishing_action(fn, name)
        old_override = getattr(self, "_fishing_action_override", False)
        self._fishing_action_override = True
        try:
            return fn()
        finally:
            self._fishing_action_override = old_override

    def _get_update_api_url(self):
        return (
            os.environ.get("COTEAB_UPDATE_API_URL")
            or "https://api.github.com/repos/xVapure/Noteab-Macro/releases/latest"
        )

    def _normalize_version(self, value):
        try:
            v = str(value or "").strip().lower()
            if v.startswith("v"):
                v = v[1:]
            return v
        except Exception:
            return ""

    def _is_same_version(self, a, b):
        return self._normalize_version(a) == self._normalize_version(b)

    def _fetch_latest_release(self):
        try:
            response = requests.get(self._get_update_api_url(), timeout=12)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                return payload
        except Exception as e:
            print(f"Failed to fetch latest release metadata: {e}")
        return None

    def _pick_update_exe_asset(self, release_payload):
        assets = release_payload.get("assets", []) if isinstance(release_payload, dict) else []
        if not isinstance(assets, list):
            return "", ""

        preferred = {
            "coteabmacro.exe",
            "coteab macro.exe",
            "coteab_macro.exe",
            "coteab-macro.exe",
        }
        exe_candidates = []
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", "")).strip()
            url = str(asset.get("browser_download_url", "")).strip()
            if not name or not url:
                continue
            lower_name = name.lower()
            if lower_name in preferred:
                return name, url
            if lower_name.endswith(".exe"):
                exe_candidates.append((name, url))

        if exe_candidates:
            return exe_candidates[0]
        return "", ""

    def _spawn_detached_exe(self, exe_path, extra_args=None):
        try:
            cmd = [os.path.abspath(exe_path)]
            if extra_args:
                cmd.extend([str(x) for x in extra_args])

            creationflags = 0
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(
                cmd,
                creationflags=creationflags,
                close_fds=True,
            )
            return True
        except Exception as e:
            print(f"Failed to spawn detached EXE: {e}")
            return False

    def _download_and_stage_exe_update(self, download_url, asset_name="CoteabMacro.exe"):
        if not getattr(sys, "frozen", False):
            return False

        current_dir = os.path.dirname(os.path.abspath(sys.executable))
        temp_exe = os.path.join(current_dir, "CoteabMacro1.exe")

        try:
            if os.path.exists(temp_exe):
                os.remove(temp_exe)
        except Exception:
            pass

        response = requests.get(download_url, timeout=120, stream=True)
        response.raise_for_status()

        with open(temp_exe, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

        if not os.path.exists(temp_exe) or os.path.getsize(temp_exe) <= 0:
            raise RuntimeError("Downloaded update file is empty")

        canonical_exe = os.path.join(current_dir, "CoteabMacro.exe")
        args = [
            "--coteab-finalize-update",
            "--coteab-target",
            canonical_exe,
            "--coteab-old-pid",
            str(os.getpid()),
        ]
        if not self._spawn_detached_exe(temp_exe, args):
            raise RuntimeError("Failed to launch downloaded update executable")
        return True

    def _is_pid_alive(self, pid):
        try:
            pid_i = int(pid)
            if pid_i <= 0:
                return False
            proc = psutil.Process(pid_i)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except Exception:
            return False

    def maybe_self_rename_to_canonical_exe(self, canonical_target="CoteabMacro.exe", old_pid=None):
        try:
            if not getattr(sys, "frozen", False):
                return False

            current_exe = os.path.abspath(sys.executable)
            current_dir = os.path.dirname(current_exe)
            current_name = os.path.basename(current_exe)
            if not current_name.lower().endswith(".exe"):
                return False

            canonical_raw = str(canonical_target or "CoteabMacro.exe").strip() or "CoteabMacro.exe"
            if not canonical_raw.lower().endswith(".exe"):
                canonical_raw += ".exe"

            canonical_path = canonical_raw if os.path.isabs(canonical_raw) else os.path.join(current_dir, canonical_raw)
            canonical_path = os.path.abspath(canonical_path)

            if current_exe.lower() == canonical_path.lower():
                # We are the canonical exe! Clean up any temporary updater executable
                temp_exe = os.path.join(current_dir, "CoteabMacro1.exe")
                if os.path.exists(temp_exe):
                    try:
                        os.remove(temp_exe)
                    except Exception:
                        pass
                return False

            deadline = time.monotonic() + 120.0
            while time.monotonic() < deadline:
                if old_pid and self._is_pid_alive(old_pid):
                    time.sleep(0.2)
                    continue

                try:
                    if os.path.exists(canonical_path):
                        os.remove(canonical_path)
                except Exception:
                    pass

                try:
                    import shutil
                    shutil.copy2(current_exe, canonical_path)
                    self._spawn_detached_exe(canonical_path)
                    return True
                except Exception as ex:
                    print(f"Failed to copy {current_exe} to {canonical_path}: {ex}")
                    time.sleep(0.25)

            print("Failed to replace old executable with the new one within timeout.")
            return False
        except Exception as e:
            print(f"Failed to normalize executable name: {e}")
            return False

    def _download_exe_to_folder(self, download_url, target_dir, asset_name="CoteabMacro.exe"):
        os.makedirs(target_dir, exist_ok=True)

        base_name = os.path.basename(str(asset_name or "").strip()) or "CoteabMacro.exe"
        if not base_name.lower().endswith(".exe"):
            base_name += ".exe"

        target_path = os.path.join(target_dir, base_name)
        if os.path.exists(target_path):
            stem, ext = os.path.splitext(base_name)
            target_path = os.path.join(target_dir, f"{stem}_downloaded{ext}")

        response = requests.get(download_url, timeout=120, stream=True)
        response.raise_for_status()

        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)

        if not os.path.exists(target_path) or os.path.getsize(target_path) <= 0:
            raise RuntimeError("Downloaded update file is empty")

        return target_path

    def apply_startup_auto_update(self):
        try:
            if not getattr(sys, "frozen", False):
                return False

            latest_release = self._fetch_latest_release()
            if not latest_release:
                return False

            latest_version = str(latest_release.get("tag_name", "")).strip()
            if not latest_version or self._is_same_version(latest_version, current_ver):
                return False

            asset_name, download_url = self._pick_update_exe_asset(latest_release)
            if not download_url:
                print("Update available, but no .exe asset was found in latest release.")
                return False

            print("hold up downloading the new Coteab update bro")
            if self._download_and_stage_exe_update(download_url, asset_name=asset_name):
                print(f"Update {latest_version} downloaded. Restarting into the new executable...")
                return True
            return False
        except Exception as e:
            print(f"Startup auto-update failed: {e}")
            return False

    def check_for_updates(self):
        current_version = current_ver

        try:
            latest_release = self._fetch_latest_release()
            if not latest_release:
                return

            latest_version = str(latest_release.get("tag_name", "")).strip()
            if latest_version and not self._is_same_version(latest_version, current_version):
                asset_name, download_url = self._pick_update_exe_asset(latest_release)
                if not download_url:
                    return

                if hasattr(self, "on_update_available") and callable(self.on_update_available):
                    self.on_update_available(latest_version, download_url)

        except Exception as e:
            print(f"Failed to check for updates: {e}")

    def download_and_apply_update(self, download_url, version=""):
        try:
            if not download_url:
                if hasattr(self, "on_update_status") and callable(self.on_update_status):
                    self.on_update_status("failed")
                return False

            if hasattr(self, "on_update_status") and callable(self.on_update_status):
                self.on_update_status("downloading")

            guessed_name = os.path.basename(str(download_url).split("?", 1)[0]) or "CoteabMacro.exe"
            if getattr(sys, "frozen", False):
                self._download_and_stage_exe_update(download_url, asset_name=guessed_name)

                if hasattr(self, "on_update_status") and callable(self.on_update_status):
                    self.on_update_status("done|restarting")

                # allow status callback to flush before terminating process
                time.sleep(0.25)
                os._exit(0)
            else:
                try:
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    project_root = os.path.dirname(base_dir)
                except Exception:
                    project_root = os.getcwd()

                downloaded_path = self._download_exe_to_folder(
                    download_url,
                    project_root,
                    asset_name=guessed_name,
                )

                if hasattr(self, "on_update_status") and callable(self.on_update_status):
                    self.on_update_status(f"done|{os.path.basename(downloaded_path)}")
                return True
        except Exception as e:
            print(f"Failed to download/apply update: {e}")
            if hasattr(self, "on_update_status") and callable(self.on_update_status):
                self.on_update_status("failed")
            return False


    def update_theme(self, theme_name):
        self.root.style.theme_use(theme_name)
        self.config["selected_theme"] = theme_name
        self.save_config()

    def take_inventory_screenshot_now(self, fishing_safe=False):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if not self.check_roblox_procs():
                return
            if (getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)):
                return
            
            for _ in range(4):
                self.activate_roblox_window()
                time.sleep(0.35)

            search_bar = self.config.get("search_bar", [855, 358])
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
            if inventory_menu and inventory_menu[0]:
                try:
                    autoit.mouse_click("left", inventory_menu[0], inventory_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                    except Exception:
                        pass
                time.sleep(0.35)
            if items_tab and items_tab[0]:
                try:
                    autoit.mouse_click("left", items_tab[0], items_tab[1], 1, speed=3)
                    time.sleep(1)
                    autoit.mouse_click("left", search_bar[0], search_bar[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(items_tab[0], items_tab[1])
                    except Exception:
                        pass
                time.sleep(0.35)
            try:
                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = os.path.join(screenshot_dir, f"inventory_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_inventory_screenshot_webhook(filename)
                self.last_inventory_screenshot_time = datetime.now()
            except Exception as e:
                self.error_logging(e, "Error taking/sending forced inventory screenshot")
            try:
                if inventory_close_button and inventory_close_button[0]:
                    try:
                        autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        except Exception:
                            pass
                    time.sleep(0.22)
            except Exception as e:
                self.error_logging(e, "Error while closing inventory after forced screenshot")
        except Exception as e:
            self.error_logging(e, "Error in take_inventory_screenshot_now")
            
    def perform_glitched_enable_buff(self):
        try:
            if not self.config.get("enable_buff_glitched", False):
                return
            if self.config.get("enable_idle_mode", False):
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            menu = self.config.get("glitched_menu_button", [0, 0])
            buff_enable = self.config.get("glitched_buff_enable_button", [0, 0])
            settings = self.config.get("glitched_settings_button", [0, 0])
            for _ in range(4):
                if not self.detection_running or self.reconnecting_state:
                    return
                self.activate_roblox_window()
                time.sleep(0.15)
            while True:
                if not self.detection_running or self.reconnecting_state:
                    return
                if not getattr(self, "_br_sc_running", False) and not getattr(self, "_mt_running", False) and not getattr(self, "auto_pop_state", False) and not getattr(self, "on_auto_merchant_state", False) and not (getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)) and not self.config.get("enable_potion_crafting", False):
                    break
                time.sleep(0.67)
            if menu and menu[0]:
                self.Global_MouseClick(menu[0], menu[1])
                time.sleep(0.67)
            if settings and settings[0]:
                self.Global_MouseClick(settings[0], settings[1])
                time.sleep(0.67)
            if buff_enable and buff_enable[0]:
                self.Global_MouseClick(buff_enable[0], buff_enable[1])
                time.sleep(0.67)
        except Exception as e:
            self.error_logging(e, "Error in perform_glitched_enable_buff")

    def _reset_on_rare_impl(self):
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if not self.detection_running or self.reconnecting_state:
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            for _ in range(4):
                if not self.detection_running:
                    return
                self.activate_roblox_window()
                time.sleep(0.15)
            keyboard.press_and_release('esc')
            time.sleep(0.3)
            keyboard.press_and_release('r')
            time.sleep(0.3)
            keyboard.press_and_release('enter')
        except Exception:
            pass

    def _make_player_embed(self, kind, name, pid, ts_iso, duration_text=None, join_biome=None, left_biome=None):
        color = 3066993 if kind == "join" else 15158332
        title = "Player Joined" if kind == "join" else "Player Left"
        if kind == "join" and join_biome:
            title = f"Player Joined during {join_biome} biome"
        elif kind == "leave" and left_biome:
            title = f"Player Left during {left_biome} biome"    
        desc = f"**{name}**\n`{pid}`"
        fields = []
        if duration_text:
            fields.append({"name": "Stayed", "value": duration_text, "inline": True})
        if kind == "leave" and join_biome:
            fields.append({"name": "Joined During", "value": f"{join_biome} biome", "inline": True})
        embed = {
            "title": title,
            "description": desc,
            "color": color,
            "timestamp": ts_iso,
            "footer": {"text": "Coteab • Player Logger"},
            "fields": fields
        }
        return embed

    def _send_embeds_to_all(self, embeds):
        urls = self.get_webhook_list()
        if not urls:
            return
        payload = {"embeds": embeds}
        for url in urls:
            try:
                requests.post(url, json=payload, timeout=5)
            except Exception:
                pass


    def perform_quest_claim_sequence_sync(self, fishing_safe=False):
        try:
            if not self.detection_running or self._detection_stop_event.is_set():
                return
            baseaction = lambda: self._perform_quest_claim_sequence_impl(fishing_safe=fishing_safe)
            action = baseaction
            if fishing_safe:
                action = lambda: self._run_fishing_action(baseaction, "quest_claim")
            self._action_scheduler.enqueue_action(action, name="quest_claim", priority=5)
        except Exception:
            try:
                self._perform_quest_claim_sequence_impl(fishing_safe=fishing_safe)
            except Exception:
                pass

    def _perform_quest_claim_sequence_impl(self, fishing_safe=False):
        try:
            if not self.detection_running or self._detection_stop_event.is_set():
                return
            if self.config.get("enable_idle_mode", False):
                return
            if self._is_fishing_blocked() and not fishing_safe:
                return
            if not getattr(self, "auto_claim_quests_var", None) or not self.auto_claim_quests_var.get():
                return
            if (getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)):
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            if not self.check_roblox_procs():
                return
            self.activate_roblox_window()
            quest_menu = self.config.get("quest_menu", [0, 0])
            quest1 = self.config.get("quest1_button", [0, 0])
            quest2 = self.config.get("quest2_button", [0, 0])
            quest3 = self.config.get("quest3_button", [0, 0])
            claim_btn = self.config.get("claim_quest_button", [0, 0])

            for _ in range(4):
                if not self.detection_running or (self._is_fishing_blocked() and not fishing_safe):
                    return
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.15, allow_fishing=fishing_safe):
                    return

            if quest_menu and quest_menu[0]:
                try:
                    autoit.mouse_click("left", quest_menu[0], quest_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest_menu[0], quest_menu[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                    return

            try:
                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = os.path.join(screenshot_dir, f"quest_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_quest_screenshot_webhook(filename)
            except Exception as e:
                self.error_logging(e, "Error taking/sending quest screenshot")

            if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                return

            if quest1 and quest1[0]:
                try:
                    autoit.mouse_click("left", quest1[0], quest1[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest1[0], quest1[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                    return
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                    return

            if quest2 and quest2[0]:
                try:
                    autoit.mouse_click("left", quest2[0], quest2[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest2[0], quest2[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                    return
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                    return

            if quest3 and quest3[0]:
                try:
                    autoit.mouse_click("left", quest3[0], quest3[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(quest3[0], quest3[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                    return
            if claim_btn and claim_btn[0]:
                try:
                    autoit.mouse_click("left", claim_btn[0], claim_btn[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(claim_btn[0], claim_btn[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                    return
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
            try:
                if inventory_close_button and inventory_close_button[0]:
                    try:
                        autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        except Exception:
                            pass
                    self._sleep_with_cancel(0.3, allow_fishing=fishing_safe)
            except Exception:
                pass

        except Exception as e:
            self.error_logging(e, "Error in perform_quest_claim_sequence_sync")

    def _fetch_daily_reward_time(self):
        tz = timezone(timedelta(hours=7))
        sources = [
            ("json", "https://timeapi.io/api/Time/current/zone?timeZone=Asia/Bangkok"),
            ("json", "https://worldtimeapi.org/api/timezone/Asia/Bangkok"),
            ("header", "https://www.google.com/generate_204"),
            ("header", "https://www.cloudflare.com/"),
        ]
        for kind, url in sources:
            try:
                res = requests.get(url, timeout=4)
                res.raise_for_status()
                if kind == "json":
                    data = res.json()
                    value = data.get("dateTime") or data.get("datetime")
                    current = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                    if current.tzinfo is None:
                        current = current.replace(tzinfo=tz)
                    return current.astimezone(tz)
                from email.utils import parsedate_to_datetime
                return parsedate_to_datetime(res.headers["Date"]).astimezone(tz)
            except Exception:
                continue
        return datetime.now().astimezone().astimezone(tz)

    def start_daily_reward_clock(self):
        with self._daily_reward_state_lock:
            if self._daily_reward_clock_started:
                return
            self._daily_reward_clock_started = True
            self._daily_reward_stop_event.clear()
        threading.Thread(target=self._sync_daily_reward_clock, name="DailyRewardTimeSync", daemon=True).start()
        threading.Thread(target=self._daily_reward_clock_loop, name="DailyRewardClock", daemon=True).start()

    def stop_daily_reward_clock(self):
        self._daily_reward_stop_event.set()
        self._daily_reward_pause_requested.clear()
        self._daily_reward_wake_event.set()

    def request_daily_reward_claim(self, initial=False):
        if not getattr(self, "claim_daily_rewards_var", None) or not self.claim_daily_rewards_var.get():
            return
        with self._daily_reward_state_lock:
            if initial and self._daily_reward_initial_claim_done.is_set():
                return
            self._daily_reward_claim_pending = True
            if initial:
                self._daily_reward_initial_claim_pending = True
        self._daily_reward_wake_event.set()

    def _sync_daily_reward_clock(self):
        current = self._fetch_daily_reward_time()
        target = current.replace(minute=0, second=10, microsecond=0)
        if target <= current:
            target += timedelta(hours=1)
        self._daily_reward_next_claim_at = time.monotonic() + (target - current).total_seconds()
        self._daily_reward_time_synced.set()
        self._daily_reward_wake_event.set()

    def _daily_reward_clock_loop(self):
        nextclaim = None
        while not self._daily_reward_stop_event.is_set():
            if nextclaim is None and self._daily_reward_time_synced.is_set():
                nextclaim = self._daily_reward_next_claim_at
            now = time.monotonic()
            if nextclaim is not None and now >= nextclaim:
                if self.detection_running:
                    self.request_daily_reward_claim()
                nextclaim += 3600
                if nextclaim <= now:
                    nextclaim += (int((now - nextclaim) // 3600) + 1) * 3600
                self._daily_reward_next_claim_at = nextclaim
            with self._daily_reward_state_lock:
                initial = self._daily_reward_initial_claim_pending
                ready = self._daily_reward_claim_pending and not self._daily_reward_initial_claim_inflight.is_set()
                ready = ready and (initial or (self.detection_running and not self.reconnecting_state))
                if ready:
                    self._daily_reward_claim_pending = False
                    self._daily_reward_initial_claim_pending = False
                    if initial:
                        self._daily_reward_initial_claim_inflight.set()
            if ready:
                claimstop = self._daily_reward_claim_stop_event
                done = self._run_daily_reward_claim(initial=initial, claim_stop_event=claimstop)
                if initial:
                    self._daily_reward_initial_claim_inflight.clear()
                    if done:
                        self._daily_reward_initial_claim_done.set()
                if not done and not claimstop.is_set():
                    with self._daily_reward_state_lock:
                        if self._daily_reward_claim_stop_event is claimstop:
                            self._daily_reward_claim_pending = True
                            self._daily_reward_initial_claim_pending = initial
                    self._daily_reward_wake_event.wait(1.0)
                    self._daily_reward_wake_event.clear()
                continue
            wait = 1.0 if nextclaim is None else max(0.05, min(1.0, nextclaim - time.monotonic()))
            self._daily_reward_wake_event.wait(wait)
            self._daily_reward_wake_event.clear()
    def _daily_reward_action_active(self):
        return any(getattr(self, name, False) for name in (
            "_mt_running",
            "_br_sc_running",
            "_portable_crack_running",
            "_remote_running",
            "_egg_collecting",
            "_eden_running",
            "_eden_path_pending",
            "_potion_thread_active",
            "_fishing_busy",
            "_merchant_log_event_queued",
            "_merchant_log_event_pending",
            "auto_pop_state",
            "on_auto_merchant_state",
        ))

    def _run_daily_reward_claim(self, initial=False, reconnect=False, claim_stop_event=None):
        claimstop = claim_stop_event or self._daily_reward_claim_stop_event
        if claimstop.is_set() or (not self.detection_running and not initial) or (self.reconnecting_state and not reconnect):
            return False
        if not reconnect:
            if self.is_fishing_mode_enabled() and getattr(self, "_fishing_worker_active", False):
                self._daily_reward_pause_requested.set()
                self._daily_reward_wake_event.set()
                while self.detection_running and not claimstop.is_set():
                    if self._daily_reward_fishing_paused.is_set() or not getattr(self, "_fishing_worker_active", False):
                        break
                    claimstop.wait(0.05)
            while self.detection_running and not claimstop.is_set():
                if self.reconnecting_state:
                    if self._daily_reward_claim_stop_event is claimstop:
                        self._daily_reward_pause_requested.clear()
                    return False
                if not self._daily_reward_action_active():
                    break
                claimstop.wait(0.1)
        if claimstop.is_set() or not self.check_roblox_procs():
            return False
        done = threading.Event()
        result = [False]

        def run():
            try:
                if claimstop.is_set() or (not reconnect and self._daily_reward_action_active()):
                    return
                if not reconnect and not initial and not self.detection_running:
                    return
                self.perform_daily_reward_claim_impl(
                    after_reconnect=reconnect,
                    during_startup=initial,
                    claim_stop_event=claimstop,
                )
                result[0] = True
            finally:
                done.set()

        try:
            self._action_scheduler.enqueue_action(run, name="daily_reward_claim", priority=-100 if initial or reconnect else 0)
        except Exception:
            run()
        while (self.detection_running or initial) and not claimstop.is_set() and not done.wait(0.1):
            pass
        if self._daily_reward_claim_stop_event is claimstop:
            self._daily_reward_pause_requested.clear()
            self._daily_reward_wake_event.set()
        return result[0] and done.is_set()
    def perform_daily_reward_claim_after_reconnect(self):
        if not getattr(self, "claim_daily_rewards_var", None) or not self.claim_daily_rewards_var.get():
            return True
        if not self.detection_running or not self.reconnecting_state or not self.check_roblox_procs():
            return False
        with self._daily_reward_state_lock:
            self._daily_reward_reconnect_claim_pending = True
            self._daily_reward_reconnect_claim_done.clear()
        try:
            return self._run_daily_reward_claim(reconnect=True)
        finally:
            with self._daily_reward_state_lock:
                self._daily_reward_reconnect_claim_pending = False
                self._daily_reward_claim_pending = False
                self._daily_reward_initial_claim_pending = False
            self._daily_reward_initial_claim_done.set()
            self._daily_reward_reconnect_claim_done.set()

    def perform_daily_reward_claim_sync(self):
        if not self.claim_daily_rewards_var.get():
            return
        self.request_daily_reward_claim(initial=True)
        while self.detection_running and not self._daily_reward_claim_stop_event.is_set() and not self._daily_reward_initial_claim_done.wait(0.1):
            pass

    def perform_daily_reward_claim_impl(self, after_reconnect=False, during_startup=False, claim_stop_event=None):
        claimstop = claim_stop_event or self._daily_reward_claim_stop_event
        if claimstop.is_set() or (not self.detection_running and not during_startup) or (self.reconnecting_state and not after_reconnect) or (self.config.get("enable_idle_mode", False) and not after_reconnect) or not self.claim_daily_rewards_var.get():
            return
        if not self.check_roblox_procs():
            return

        claim = self.config.get("daily_reward_claim_button", [964, 661])
        close = self.config.get("daily_reward_close_button", [1418, 395])
        try:
            claim = [int(claim[0]), int(claim[1])]
            close = [int(close[0]), int(close[1])]
        except (TypeError, ValueError, IndexError):
            return
        if min(*claim, *close) <= 0:
            return

        for _ in range(4):
            if claimstop.is_set() or (not self.detection_running and not during_startup) or (self.reconnecting_state and not after_reconnect):
                return
            self.activate_roblox_window()
            if claimstop.wait(0.15):
                return

        if claimstop.is_set() or (not self.detection_running and not during_startup):
            return
        try:
            autoit.mouse_click("left", claim[0], claim[1], 1, speed=3)
        except Exception:
            try:
                self.Global_MouseClick(claim[0], claim[1])
            except Exception:
                return

        try:
            delay = max(0.0, float(self.config.get("claim_daily_rewards_delay", 0.4)))
        except (TypeError, ValueError):
            delay = 0.4
        if claimstop.wait(delay):
            return
        if claimstop.is_set() or (not self.detection_running and not during_startup) or (self.reconnecting_state and not after_reconnect):
            return

        try:
            autoit.mouse_click("left", close[0], close[1], 1, speed=3)
        except Exception:
            try:
                self.Global_MouseClick(close[0], close[1])
            except Exception:
                pass
    def obby_path_loop(self):
        stopevent = self._detection_stop_event
        try:
            if self.config.get("enable_idle_mode", False):
                return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get():
                return
        except Exception as error:
            self.error_logging(error, "Error in obby_path_loop")

        while self.detection_running and not stopevent.is_set():
            try:
                if self.is_fishing_mode_enabled() or not getattr(self, "enable_obby_var", None) or not self.enable_obby_var.get():
                    stopevent.wait(2)
                    continue
                try:
                    interval = float(self.obby_claim_interval_var.get())
                except Exception:
                    interval = 15.0
                if (datetime.now() - self.last_obby_claim) < timedelta(minutes=interval):
                    stopevent.wait(2)
                    continue
                if ((getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)) or getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "config", {}).get("enable_potion_crafting", False)):
                    stopevent.wait(2)
                    continue
                if self.detection_running and not stopevent.is_set():
                    self._action_scheduler.enqueue_action(
                        self._perform_obby_path_sequence_impl,
                        name="obby_path",
                        priority=0,
                    )
                    self.last_obby_claim = datetime.now()
            except Exception as error:
                self.error_logging(error, "Error in obby_path_loop")
            if stopevent.wait(1):
                return
    def _perform_obby_path_sequence_impl(self):
        try:
            if self._is_fishing_blocked():
                return
            if not getattr(self, "enable_obby_var", None) or not self.enable_obby_var.get():
                return
            if not self.check_roblox_procs():
                return

            self._obby_running = True

            print("[Obby] Activating Roblox...")

            for _ in range(4):
                if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                    self._obby_running = False
                    return
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.15):
                    self._obby_running = False
                    return

            # 2. Reset Character
            print("[Obby] Resetting Character...")
            keyboard.press_and_release('esc')
            if not self._sleep_with_cancel(0.3):
                return
            keyboard.press_and_release('r')
            if not self._sleep_with_cancel(0.3):
                return
            keyboard.press_and_release('enter')
            if not self._sleep_with_cancel(6):
                return

            if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                return

            # 3. Close chat and then click Collection Buttons

            if not self._sleep_with_cancel(0.2): return
            collections_button = self.config.get("collections_button", [0, 0])
            if collections_button and collections_button[0]:
                try:
                    autoit.mouse_click("left", collections_button[0], collections_button[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(collections_button[0], collections_button[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.3):
                    return

            exit_collections_button = self.config.get("exit_collections_button", [0, 0])
            if exit_collections_button and exit_collections_button[0]:
                try:
                    autoit.mouse_click("left", exit_collections_button[0], exit_collections_button[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(exit_collections_button[0], exit_collections_button[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.3):
                    return

            if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                return

            # 4. Camera Adjustment
            start_x = exit_collections_button[0] if exit_collections_button and exit_collections_button[0] else 500
            start_y = exit_collections_button[1] if exit_collections_button and exit_collections_button[1] else 500

            autoit.mouse_move(start_x, start_y, 0)
            autoit.mouse_down("right")
            if not self._sleep_with_cancel(0.1):
                return
            autoit.mouse_move(start_x, start_y + 75, 0)
            if not self._sleep_with_cancel(0.1):
                return
            autoit.mouse_up("right")
            try:
                autoit.send("{I down}")
            except Exception:
                pass
            if not self._sleep_with_cancel(4.0):
                try: autoit.send("{I up}")
                except: pass
                return
            try:
                autoit.send("{I up}")
            except Exception:
                pass
            if not self._sleep_with_cancel(0.3):
                return

            try:
                autoit.send("{O down}")
            except Exception:
                pass
            if not self._sleep_with_cancel(0.85):
                try: autoit.send("{O up}")
                except: pass
                return
            try:
                autoit.send("{O up}")
            except Exception:
                pass
            if not self._sleep_with_cancel(0.3):
                return

            # 4.5 Equip Float Aura if enabled
            use_float_aura = self.config.get("use_float_aura", False)
            if use_float_aura:
                aura_name = self.config.get("float_aura_name", "").strip()
                if aura_name:
                    # Check if already equipped to avoid unequip loop
                    current_aura = getattr(self, "last_aura_found", None)
                    if current_aura and current_aura == aura_name:
                        print(f"[Obby] Float Aura '{aura_name}' already equipped. Skipping.")
                    else:
                        print(f"[Obby] Equipping Float Aura: {aura_name}")
                        inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
                        aura_menu = self.config.get("aura_menu", [0, 0])
                        search_bar = self.config.get(
                            "aura_search_bar",
                            self.config.get("search_bar", [834, 364]),
                        )
                        close_btn = self.config.get("inventory_close_button", [0, 0])

                        if aura_menu and aura_menu[0] > 0:
                            self.Global_MouseClick(aura_menu[0], aura_menu[1])
                            if not self._sleep_with_cancel(0.7 + inventory_click_delay):
                                return

                            if search_bar and search_bar[0] > 0:
                                self.Global_MouseClick(search_bar[0], search_bar[1])
                                if not self._sleep_with_cancel(0.5 + inventory_click_delay):
                                    return
                                try:
                                    self._safe_type_text(aura_name)
                                except Exception:
                                    try:
                                        self._safe_type_text(aura_name.lower())
                                    except Exception:
                                        pass
                                if not self._sleep_with_cancel(0.8 + inventory_click_delay):
                                    return

                                first_aura_slot = self.config.get("first_aura_slot_pos", [0, 0])
                                if first_aura_slot and first_aura_slot[0] > 0:
                                    self.Global_MouseClick(first_aura_slot[0], first_aura_slot[1])
                                    if not self._sleep_with_cancel(0.5 + inventory_click_delay):
                                        return

                                    # Click "Equip" button
                                    equip_btn = self.config.get("equip_aura_button", [0, 0])
                                    if equip_btn and equip_btn[0] > 0:
                                        self.Global_MouseClick(equip_btn[0], equip_btn[1])
                                        if not self._sleep_with_cancel(0.3 + inventory_click_delay):
                                            return

                            if close_btn and close_btn[0] > 0:
                                self.Global_MouseClick(close_btn[0], close_btn[1])
                                if not self._sleep_with_cancel(0.5 + inventory_click_delay):
                                    return

            if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state:
                return

            # 5. Run Obby recording file
            obby_file = os.path.join(os.getcwd(), "paths", "obby.json")
            if os.path.exists(obby_file):
                print("[Obby] Starting obby macro playback...")
                self._run_obby_macro(obby_file)
            else:
                print("[Obby] Macro file not found: " + obby_file)

        except Exception as e:
            self.error_logging(e, "Error in _perform_obby_path_sequence_impl")
        finally:
            self._obby_running = False

    def _run_obby_macro(self, json_file_path):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.error_logging(e, f"Failed to load obby macro from {json_file_path}")
            return

        if isinstance(data, dict) and "events" in data:
            all_events = data["events"]
        elif isinstance(data, list):
            all_events = data
        else:
            print("[Obby] obby.json has unexpected format. Skipping.")
            return

        _ALLOWED_KEYS = {"w", "a", "s", "d", "space"}
        events = [
            e for e in all_events
            if e.get("type") in ("key_down", "key_up") and e.get("key", "").lower() in _ALLOWED_KEYS
        ]
        if not events:
            print("[Obby] No movement events found in obby.json.")
            return

        events.sort(key=lambda ev: ev.get("t", 0.0))
        _KEY_MAP = {"space": "SPACE", "enter": "ENTER", "esc": "ESC", "shift": "SHIFT"}

        def _to_autoit(k):
            norm = k.strip().lower()
            mapped = _KEY_MAP.get(norm)
            if mapped:
                return mapped
            if len(norm) == 1 and norm.isalpha():
                return norm.upper()
            return norm.upper()

        def _key_down(k):
            token = _to_autoit(k)
            if token:
                autoit.send(f"{{{token} down}}")

        def _key_up(k):
            token = _to_autoit(k)
            if token:
                autoit.send(f"{{{token} up}}")

        non_vip = bool(self.config.get("non_vip_movement_path", False))
        speed_multiplier = 1.22 if non_vip else 1.0

        def _cancelled():
            return (
                not self.detection_running
                or not getattr(self, "enable_obby_var", None)
                or not self.enable_obby_var.get()
                or self._is_fishing_blocked()
                or self.reconnecting_state
                or self.auto_pop_state
            )

        pressed_keys = set()
        base_t = events[0].get("t", 0.0)
        start_wall = time.perf_counter()

        print(f"[Obby] Playback ({len(events)} events, speed_mult={speed_multiplier:.2f})...")

        try:
            for ev in events:
                if _cancelled():
                    print("[Obby] Cancelled during playback.")
                    return

                ev_t = float(ev.get("t", base_t)) - base_t
                if speed_multiplier != 1.0:
                    ev_t *= speed_multiplier
                target_wall = start_wall + ev_t

                while True:
                    now = time.perf_counter()
                    if now >= target_wall:
                        break
                    remaining = target_wall - now
                    if _cancelled():
                        print("[Obby] Cancelled during wait.")
                        return
                    if remaining > 0.002:
                        time.sleep(min(remaining * 0.5, 0.005))

                typ = str(ev.get("type", ""))
                k = str(ev.get("key", "")).lower().strip()
                try:
                    if typ == "key_down" and k:
                        _key_down(k)
                        pressed_keys.add(k)
                    elif typ == "key_up" and k:
                        _key_up(k)
                        pressed_keys.discard(k)
                except Exception:
                    pass

            print("[Obby] Macro finished successfully yatta")
        finally:
            for key_name in list(pressed_keys):
                try:
                    _key_up(key_name)
                except Exception:
                    pass
            for k in ("w", "a", "s", "d", "space"):
                try:
                    _key_up(k)
                except Exception:
                    pass
                time.sleep(0.02)

    def _run_eden_macro(self, json_file_path):
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.error_logging(e, f"Failed to load eden macro from {json_file_path}")
            return

        if isinstance(data, dict) and "events" in data:
            all_events = data["events"]
        elif isinstance(data, list):
            all_events = data
        else:
            print("[Eden] eden.json has unexpected format. Skipping.")
            return

        _ALLOWED_KEYS = {"w", "a", "s", "d", "space"}
        events = [
            e for e in all_events
            if e.get("type") in ("key_down", "key_up") and str(e.get("key", "")).lower() in _ALLOWED_KEYS
        ]
        if not events:
            print("[Eden] No movement events found in eden.json.")
            return

        events.sort(key=lambda ev: float(ev.get("t", 0.0)))
        base_t = float(events[0].get("t", 0.0))

        def _cancelled():
            return not self.detection_running

        pressed_keys = set()
        start_wall = time.time()

        print(f"[Eden] Playback ({len(events)} events)...")

        try:
            for ev in events:
                if _cancelled():
                    print("[Eden] Cancelled during playback.")
                    return

                ev_t = float(ev.get("t", base_t)) - base_t
                target_wall = start_wall + ev_t

                now = time.time()
                if target_wall > now:
                    if target_wall - now > 0.02:
                        time.sleep((target_wall - now) - 0.015)
                    while time.time() < target_wall:
                        if _cancelled():
                            print("[Eden] Cancelled during wait.")
                            return

                typ = str(ev.get("type", ""))
                k = str(ev.get("key", "")).lower().strip()
                
                if k:
                    try:
                        if typ == "key_down":
                            keyboard.press(k)
                            pressed_keys.add(k)
                        elif typ == "key_up":
                            keyboard.release(k)
                            pressed_keys.discard(k)
                    except Exception:
                        pass

            print("[Eden] Macro finished successfully!")
        finally:
            if pressed_keys:
                print(f"[Eden] Releasing {len(pressed_keys)} stuck keys...")
                for k in list(pressed_keys):
                    try:
                        keyboard.release(k)
                    except Exception:
                        pass

    # --- Easter Egg Collection ---
    def egg_collect_loop(self):
        stopevent = self._detection_stop_event
        while self.detection_running and not stopevent.is_set():
            try:
                if self.config.get("enable_idle_mode", False) or not self.config.get("collect_easter_egg", False):
                    stopevent.wait(2)
                    continue
                try:
                    interval = float(self.config.get("egg_collect_interval_min", "25"))
                except Exception:
                    interval = 25.0
                if (datetime.now() - getattr(self, "last_egg_collect_time", datetime.min)) < timedelta(minutes=interval):
                    stopevent.wait(2)
                    continue
                if (getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_auto_merchant_running", False) or getattr(self, "_fishing_busy", False) or self.reconnecting_state or getattr(self, "_obby_running", False)):
                    stopevent.wait(2)
                    continue
                current_biome = str(getattr(self, "current_biome", "") or "").upper().strip()
                if current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"):
                    stopevent.wait(2)
                    continue
                if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get():
                    stopevent.wait(2)
                    continue
                if not self._egg_collection_pending and self.detection_running and not stopevent.is_set():
                    self._egg_collection_pending = True
                    self._action_scheduler.enqueue_action(self._scheduled_egg_collect, name="egg_collect", priority=4)
                    while self._egg_collection_pending and self.detection_running and not stopevent.wait(0.1):
                        pass
            except Exception as error:
                self._egg_collection_pending = False
                self._egg_collecting = False
                self.error_logging(error, "Error in egg_collect_loop")
            if stopevent.wait(1):
                return
    def _scheduled_egg_collect(self):
        try:
            if not self.detection_running or self._detection_stop_event.is_set():
                return
            self._egg_collecting = True
            if not self._sleep_with_cancel(3.5):
                return
            if self.is_fishing_mode_enabled():
                close_btn = self.config.get("fishing_close_button_pos", [1113, 342])
                if close_btn and close_btn[0]:
                    self.activate_roblox_window()
                    if not self._sleep_with_cancel(0.3):
                        return
                    try:
                        autoit.mouse_click("left", close_btn[0], close_btn[1], 1, speed=3)
                    except Exception:
                        self.Global_MouseClick(close_btn[0], close_btn[1])
                    if not self._sleep_with_cancel(1.0):
                        return
            if self.detection_running and not self._detection_stop_event.is_set():
                self._perform_egg_collect_impl()
        except Exception as e:
            self.error_logging(e, "Error in _scheduled_egg_collect execution")
        finally:
            self._egg_collecting = False
            self._egg_collection_pending = False
            self.last_egg_collect_time = datetime.now()

    def _perform_egg_collect_impl(self):
        try:
            if not self.config.get("collect_easter_egg", False):
                return
            if not self.check_roblox_procs():
                return

            print("[EggCollect] Starting egg collection sequence...")
            self.append_log("[EggCollect] Starting egg collection sequence...")

            from .egg_collect import run_egg_collect_once, load_egg_config

            cfg = load_egg_config(self.config)

            def _should_continue():
                return (
                    self.detection_running
                    and not self.reconnecting_state
                    and not self.auto_pop_state
                )

            def _can_run():
                try:
                    return (
                        self.detection_running
                        and not self.reconnecting_state
                        and not self.auto_pop_state
                        and bool(self.config.get("collect_easter_egg", False))
                    )
                except Exception:
                    return False

            def _sleep_interruptible(seconds, poll=0.02):
                end = time.monotonic() + max(0.0, float(seconds))
                while time.monotonic() < end:
                    if not _should_continue() or not _can_run():
                        return False
                    remaining = end - time.monotonic()
                    if remaining <= 0:
                        break
                    time.sleep(min(poll, remaining))
                return _should_continue() and _can_run()

            run_egg_collect_once(
                cfg=cfg,
                sleep_interruptible=_sleep_interruptible,
                should_continue=_should_continue,
                can_run=_can_run,
                activate_roblox_cb=self.activate_roblox_window,
                egg_ocr_check_cb=self._perform_egg_ocr_check,
            )

        except Exception as e:
            self.error_logging(e, "Error in _perform_egg_collect_impl")

    # --- Easter Egg OCR Special Detection ---
    EGG_SPAWN_MESSAGES: list[tuple[str, str, str]] = [
        ("Dreamer Egg (Sky Festival)",           "wait. am i still dreaming?", "1 in 2,000,000,000"),
        ("Egg v2.0 (Y.O.L.K.E.G.G)",            "preparing protocol. do you want to be my friend?", "1 in 1,780,908,090"),
        ("The Egg of the Sky (Eggis)",           "scanning. egg cannon charging 2000%", "1 in 1,150,000,000"),
        ("Forest Egg (Eostre)",                  "let's have an egg hunt here!", "1 in 1,000,000,000"),
        ("Blooming Egg (Eggore)",                "don't forget to water the small plant", "1 in 700,000,000"),
        ("Angelic Egg (REVIVE)",                 "holy eggsus", "1 in 645,000,000"),
        ("Andromeda Egg (Eggsistance)",           "am i in spaaaace right now?", "1 in 307,777,777"),
        ("Either Royal Egg or Hatch Egg",        "a special egg has spawned", "1 in 80,000,000 / 1 in 40,000,000"),
    ]

    def eden_ocr_check_loop(self):
        stopevent = self._detection_stop_event
        last_check = time.monotonic()
        while self.detection_running and not stopevent.is_set():
            try:
                if not self.config.get("eden_detection", False):
                    stopevent.wait(2)
                    continue
                try:
                    interval = float(self.config.get("eden_check_interval", "5"))
                except Exception:
                    interval = 5.0
                if (time.monotonic() - last_check) < max(60.0, interval * 60.0):
                    stopevent.wait(2)
                    continue
                if getattr(self, "_eden_checking_pending", False) or getattr(self, "_eden_checking", False):
                    stopevent.wait(2)
                    continue
                try:
                    pending = any("br" in str(item[2]).lower() or "sc" in str(item[2]).lower() or "merchant" in str(item[2]).lower() or "portable" in str(item[2]).lower() for item in list(self._action_scheduler._pq.queue))
                except Exception:
                    pending = False
                if pending or self.reconnecting_state or self.auto_pop_state or getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False) or getattr(self, "_obby_running", False) or getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_auto_merchant_running", False) or getattr(self, "_fishing_busy", False) or self._is_fishing_blocked():
                    stopevent.wait(2)
                    continue
                current_biome = str(getattr(self, "current_biome", "") or "").upper().strip()
                if current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE") or (getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get()) or not self.check_roblox_procs():
                    stopevent.wait(2)
                    continue
                self._eden_checking_pending = True
                last_check = time.monotonic()
                self._action_scheduler.enqueue_action(self._scheduled_eden_ocr_check, name="eden_ocr", priority=4)
                while self._eden_checking_pending and self.detection_running and not stopevent.wait(0.1):
                    pass
            except Exception as error:
                self._eden_checking_pending = False
                self._eden_checking = False
                self.error_logging(error, "Error in eden_ocr_check_loop")
            if stopevent.wait(1):
                return
    def _scheduled_eden_ocr_check(self):
        try:
            if not self.detection_running or self._detection_stop_event.is_set():
                return
            self._eden_checking = True
            print("[Eden ocr] Starting eden ocr check")
            chat_box_region = self.config.get("chat_box_ocr_pos", [0, 0, 0, 0])
            if not chat_box_region or len(chat_box_region) < 4: return
            if chat_box_region[2] <= 0 or chat_box_region[3] <= 0: return

            chat_hover = self.config.get("chat_hover_pos", [272, 252])
            chat_ocr_region = self.config.get("chat_tab_ocr_pos", [341, 83, 210, 40])
            chat_close = self.config.get("chat_close_button", [174, 40])

            if not (chat_hover and chat_hover[0] and chat_close and chat_close[0]): return

            for _ in range(3):
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.15):
                    return

            sw = pyautogui.size()
            autoit.mouse_move(sw.width // 2, sw.height // 2, speed=3)
            if not self._sleep_with_cancel(0.6):
                return
            autoit.mouse_move(chat_hover[0], chat_hover[1], speed=3)
            if not self._sleep_with_cancel(0.6):
                return

            # Check if chat is already open
            chat_is_open = False
            for attempt in range(1, 3):
                tab_text = self.extract_text_with_rapidocr(tuple(chat_ocr_region)).lower()
                if fuzzy_match_any(tab_text, ["here", "general", "server message"], threshold=0.8):
                    chat_is_open = True
                    break
                if attempt < 2:
                    if not self._sleep_with_cancel(0.35):
                        return

            if not chat_is_open:
                autoit.mouse_click("left", chat_close[0], chat_close[1], 1, speed=3)
                if not self._sleep_with_cancel(0.8):
                    return

                autoit.mouse_move(chat_hover[0], chat_hover[1], speed=3)
                if not self._sleep_with_cancel(0.5):
                    return

                for attempt in range(1, 3):
                    tab_text = self.extract_text_with_rapidocr(tuple(chat_ocr_region)).lower()
                    if fuzzy_match_any(tab_text, ["general", "server message"], threshold=0.8):
                        chat_is_open = True
                        break
                    if attempt < 2:
                        if not self._sleep_with_cancel(0.35):
                            return

            if not chat_is_open:
                self.append_log("[EdenOCR] Could not confirm chat is open. Skipping OCR check.")
                return

            text = self.extract_text_with_rapidocr(tuple(chat_box_region)).lower()
            if not text: return
            
            _PLAYER_TAGS = [
                "[fan]", "[vip]", "[vip+]", "[donator]", "[contributor]",
                "[cm]", "[dev]", "[moderator]", "[admin]", "[owner]",
                "[og]", "[tester]", "[youtuber]", "[rolls]"
            ]
            _TAG_LOOKBACK = 100

            def _is_player_message(match_pos: int) -> bool:
                start = max(0, match_pos - _TAG_LOOKBACK)
                prefix = text[start:match_pos]
                return any(tag in prefix for tag in _PLAYER_TAGS)

            _EDEN_FUZZY_THRESHOLD = 0.8
            fuzzy_target = "devourer of the void, eden has appeared"

            found_eden = False
            
            exact_pos = text.find(fuzzy_target)
            if exact_pos != -1:
                if not _is_player_message(exact_pos):
                    found_eden = True
                else:
                    print("[eden ocr] meh u aint slick lil bro")
                    self.append_log("[Eden OCR] 'Eden' exact string detected but it's just some random player trolling shit")
            else:
                win_len = len(fuzzy_target)
                if win_len <= len(text):
                    for i in range(len(text) - win_len + 1):
                        window = text[i:i + win_len]
                        ratio = difflib.SequenceMatcher(None, fuzzy_target, window).ratio()
                        if ratio >= _EDEN_FUZZY_THRESHOLD:
                            if not _is_player_message(i):
                                found_eden = True
                            else:
                                print("[eden ocr] STOP TRYING THIS DOGSHIT")
                                self.append_log("[Eden OCR] 'Eden' fuzzy string detected but it's just some random player trolling shit")
                            break

            if not found_eden: return

            # Skip if eden recently found to prevent spam
            _EDEN_OCR_COOLDOWN_SEC = 2400 # 40 mins
            last_eden_time = getattr(self, "_last_eden_ocr_found_time", 0)
            now = time.monotonic()
            if (now - last_eden_time) < _EDEN_OCR_COOLDOWN_SEC: return
            self._last_eden_ocr_found_time = now

            print(f"[EdenOCR] Eden spawn detected!")
            self.append_log(f"[EdenOCR] Eden spawn detected!")

            should_ping = self.config.get("ping_eden", False)
            discord_user_id = str(self.config.get("eden_user_id", "")).strip() if should_ping else ""
            screenshot_path = None
            
            try:
                if self.is_roblox_focused():
                    x, y, w, h = int(chat_box_region[0]), int(chat_box_region[1]), int(chat_box_region[2]), int(chat_box_region[3])
                    img = pyautogui.screenshot(region=(x, y, w, h))
                    screenshot_dir = os.path.join(os.getcwd(), "images")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshot_dir, f"eden_ocr_{int(time.time())}.png")
                    img.save(screenshot_path)
            except Exception as e:
                print(f"[EdenOCR] Failed to take chat screenshot: {e}")
                screenshot_path = None

            try:
                self.send_eden_ocr_webhook(discord_user_id, screenshot_path=screenshot_path)
            except Exception as e:
                print(f"[EdenOCR] Failed to send webhook: {e}")

        except Exception as e:
            self.error_logging(e, "Error in _scheduled_eden_ocr_check")
        finally:
            try:
                chat_close = self.config.get("chat_close_button", [174, 40])
                if chat_close and chat_close[0]:
                    autoit.mouse_click("left", chat_close[0], chat_close[1], 1, speed=3)
            except Exception:
                pass
            self._eden_checking = False
            self._eden_checking_pending = False


    def start_merchant_cache_monitor(self):
        from .merchant_logs import Tracker

        thread = getattr(self, "_merchant_cache_thread", None)
        if thread and thread.is_alive():
            return
        self._merchant_cache_tracker = Tracker()
        self._merchant_cache_lock = threading.Lock()
        self._merchant_cache_running = True
        thread = threading.Thread(target=self.merchant_logs_check_loop, name="Merchant Cache", daemon=True)
        self._merchant_cache_thread = thread
        thread.start()

    def stop_merchant_cache_monitor(self):
        from .merchant_logs import FILES, unblock

        tracker = getattr(self, "_merchant_cache_tracker", None)
        cache_lock = getattr(self, "_merchant_cache_lock", None)
        if cache_lock is None:
            self._merchant_cache_running = False
            return
        try:
            with cache_lock:
                self._merchant_cache_running = False
                if tracker:
                    keys = {key for values in FILES.values() for key in values}
                    path = getattr(tracker, "block_path", None) or tracker.cache()
                    if path:
                        unblock(keys, path)
                    tracker.ours.clear()
                    tracker.block_path = None
        except Exception as e:
            self.error_logging(e, "Error removing merchant cache blocks")

    def merchant_logs_check_loop(self):
        from .merchant_logs import FILES, Tracker, block, unblock

        tracker = getattr(self, "_merchant_cache_tracker", None) or Tracker()
        self._merchant_cache_tracker = tracker
        cache_lock = getattr(self, "_merchant_cache_lock", None)
        if cache_lock is None:
            cache_lock = threading.Lock()
            self._merchant_cache_lock = cache_lock
        keys = {key for values in FILES.values() for key in values}
        seen = {}
        try:
            while self._merchant_cache_running:
                came = []
                try:
                    with cache_lock:
                        if not self._merchant_cache_running:
                            break
                        path = tracker.cache()
                        block_path = getattr(tracker, "block_path", None)
                        if path:
                            if block_path and block_path != path:
                                unblock(keys, block_path)
                                tracker.ours.clear()
                                tracker.file_read.clear()
                                tracker.block_path = None
                                tracker.since = int(time.time() * 1000)
                            wrote = block(keys, path)
                            if wrote:
                                tracker.forget(wrote)
                                tracker.block_path = path
                                self.append_log("[Merchant Logs] Blocked merchant animations for repeat detection.")
                            came = tracker.poll()
                            if not self.detection_running:
                                came = []
                            if tracker.ours:
                                tracker.block_path = path
                    for name in came:
                        now = time.time()
                        if now - seen.get(name, 0) < 1500:
                            continue
                        seen[name] = now
                        self.append_log(f"[Merchant Logs] {name} spawn detected!")
                        if self.config.get("merchant_ocr", False) and hasattr(self, "send_merchant_webhook"):
                            threading.Thread(
                                target=self.send_merchant_webhook,
                                args=(name,),
                                kwargs={"source": "logs"},
                                daemon=True,
                            ).start()
                            if hasattr(self, "last_merchant_sent"):
                                self.last_merchant_sent[(name, "logs")] = now
                        callback = getattr(self, "on_merchant_cache_event", None)
                        if callable(callback):
                            try:
                                callback(name)
                            except Exception as e:
                                self.error_logging(e, "Error dispatching merchant cache event")
                except Exception as e:
                    self.error_logging(e, "Error in merchant_logs_check_loop")
                time.sleep(2)
        finally:
            try:
                with cache_lock:
                    path = getattr(tracker, "block_path", None) or tracker.cache()
                    if path:
                        unblock(keys, path)
                    tracker.ours.clear()
                    tracker.block_path = None
            except Exception as e:
                self.error_logging(e, "Error removing merchant cache blocks")
    def egg_ocr_check_loop(self):
        last_check = time.monotonic()
        while self.detection_running:
            try:
                if not self.config.get("egg_ocr_detect_special", False):
                    time.sleep(2)
                    continue

                # 25-second interval
                if (time.monotonic() - last_check) < 25.0:
                    time.sleep(1)
                    continue

                try:
                    pending_high_priority = False
                    for item in list(self._action_scheduler._pq.queue):
                        qname = str(item[2]).lower()
                        if "br" in qname or "sc" in qname or "merchant" in qname or "portable" in qname:
                            pending_high_priority = True
                            break
                    if pending_high_priority:
                        time.sleep(2)
                        continue
                except Exception:
                    pass

                if (self.reconnecting_state or
                    self.auto_pop_state or
                    (getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)) or
                    getattr(self, "_obby_running", False) or
                    getattr(self, "_br_sc_running", False) or
                    getattr(self, "_mt_running", False) or
                    getattr(self, "on_auto_merchant_state", False) or
                    getattr(self, "_auto_merchant_running", False) or
                    getattr(self, "_fishing_busy", False) or
                    self._is_fishing_blocked()):
                    time.sleep(2)
                    continue

                # Don't check during rare biomes
                current_biome = str(getattr(self, "current_biome", "") or "").upper().strip()
                if current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE"):
                    time.sleep(2)
                    continue

                # Don't check during potion crafting
                if (getattr(self, "enable_potion_crafting_var", None)
                    and self.enable_potion_crafting_var.get()):
                    time.sleep(2)
                    continue

                if not self.check_roblox_procs():
                    time.sleep(2)
                    continue

                # Perform the OCR check
                last_check = time.monotonic()
                self._perform_egg_ocr_check()

            except Exception as e:
                self.error_logging(e, "Error in egg_ocr_check_loop")
            time.sleep(1)

    def _perform_egg_ocr_check(self):
        try:
            chat_box_region = self.config.get("chat_box_ocr_pos", [0, 0, 0, 0])
            if not chat_box_region or len(chat_box_region) < 4: return
            if chat_box_region[2] <= 0 or chat_box_region[3] <= 0: return

            chat_hover = self.config.get("chat_hover_pos", [272, 252])
            chat_ocr_region = self.config.get("chat_tab_ocr_pos", [341, 83, 210, 40])
            chat_close = self.config.get("chat_close_button", [174, 40])

            if not (chat_hover and chat_hover[0] and chat_close and chat_close[0]): return

            for _ in range(3):
                self.activate_roblox_window()
                time.sleep(0.15)

            sw = pyautogui.size()
            autoit.mouse_move(sw.width // 2, sw.height // 2, speed=3)
            time.sleep(0.6)
            autoit.mouse_move(chat_hover[0], chat_hover[1], speed=3)
            time.sleep(0.6)

            # Check if chat is already open
            chat_is_open = False
            for attempt in range(1, 3):
                tab_text = self.extract_text_with_rapidocr(tuple(chat_ocr_region)).lower()
                if fuzzy_match_any(tab_text, ["general", "server message"], threshold=0.8):
                    chat_is_open = True
                    break
                if attempt < 2:
                    time.sleep(0.35)

            if not chat_is_open:
                autoit.mouse_click("left", chat_close[0], chat_close[1], 1, speed=3)
                time.sleep(0.8)

                autoit.mouse_move(chat_hover[0], chat_hover[1], speed=3)
                time.sleep(0.5)

                for attempt in range(1, 3):
                    tab_text = self.extract_text_with_rapidocr(tuple(chat_ocr_region)).lower()
                    if fuzzy_match_any(tab_text, ["general", "server message"], threshold=0.8):
                        chat_is_open = True
                        break
                    if attempt < 2:
                        time.sleep(0.35)

            if not chat_is_open:
                self.append_log("[EggOCR] Could not confirm chat is open. Skipping OCR check.")
                return

            text = self.extract_text_with_rapidocr(tuple(chat_box_region)).lower()
            if not text: return
            _PLAYER_TAGS = [
                "[fan]", "[vip]", "[vip+]", "[donator]", "[contributor]",
                "[cm]", "[dev]", "[moderator]", "[admin]", "[owner]",
                "[og]", "[tester]", "[youtuber]", "[rolls]"
            ]
            _TAG_LOOKBACK = 100

            def _is_player_message(match_pos: int) -> bool:
                start = max(0, match_pos - _TAG_LOOKBACK)
                prefix = text[start:match_pos]
                return any(tag in prefix for tag in _PLAYER_TAGS)

            egg_spawned_pos = text.find("egg spawned")
            if egg_spawned_pos == -1: return

            all_trolled = True
            search_start = 0
            while True:
                pos = text.find("egg spawned", search_start)
                if pos == -1: break
                if not _is_player_message(pos):
                    all_trolled = False
                    break
                search_start = pos + 1
            if all_trolled:
                self.append_log("[EggOCR] 'egg spawned' detected but it's just some random player trolling shit...")
                return

            _EGG_FUZZY_THRESHOLD = 0.8
            found_egg_name = None
            found_message = None
            found_rarity = None
            found_match_pos = -1

            for egg_name, unique_substr, aura_rarity in self.EGG_SPAWN_MESSAGES:
                exact_pos = text.find(unique_substr)
                if exact_pos != -1:
                    if not _is_player_message(exact_pos):
                        found_egg_name = egg_name
                        found_message = unique_substr
                        found_rarity = aura_rarity
                        found_match_pos = exact_pos
                        break
                    continue

                win_len = len(unique_substr)
                if win_len > len(text): continue
                for i in range(len(text) - win_len + 1):
                    window = text[i:i + win_len]
                    ratio = difflib.SequenceMatcher(None, unique_substr, window).ratio()
                    if ratio >= _EGG_FUZZY_THRESHOLD:
                        if not _is_player_message(i):
                            found_egg_name = egg_name
                            found_message = unique_substr
                            found_rarity = aura_rarity
                            found_match_pos = i
                        break
                if found_egg_name: break

            if not found_egg_name:
                found_egg_name = "Unknown Egg"
                found_message = "egg spawned"
                found_rarity = "Unknown"

            # skip if the same egg was detected within 10 minutes (guard check :aga:)
            _EGG_OCR_COOLDOWN_SEC = 600
            last_egg = getattr(self, "_last_egg_ocr_found", None)
            last_egg_time = getattr(self, "_last_egg_ocr_found_time", 0)
            now = time.monotonic()
            if last_egg == found_egg_name and (now - last_egg_time) < _EGG_OCR_COOLDOWN_SEC: return
            self._last_egg_ocr_found = found_egg_name
            self._last_egg_ocr_found_time = now

            print(f"[EggOCR] Egg spawn detected: {found_egg_name} | Aura rarity: {found_rarity}")
            self.append_log(f"[EggOCR] Egg spawn detected: {found_egg_name} | Aura rarity: {found_rarity}")

            discord_user_id = str(self.config.get("egg_ocr_discord_userid", "")).strip()
            screenshot_path = None
            
            try:
                if self.is_roblox_focused():
                    x, y, w, h = int(chat_box_region[0]), int(chat_box_region[1]), int(chat_box_region[2]), int(chat_box_region[3])
                    img = pyautogui.screenshot(region=(x, y, w, h))
                    screenshot_dir = os.path.join(os.getcwd(), "images")
                    os.makedirs(screenshot_dir, exist_ok=True)
                    screenshot_path = os.path.join(screenshot_dir, f"egg_ocr_{int(time.time())}.png")
                    img.save(screenshot_path)
            except Exception as e:
                print(f"[EggOCR] Failed to take chat screenshot: {e}")
                screenshot_path = None

            try:
                self.send_egg_ocr_webhook(found_egg_name, found_rarity, discord_user_id, screenshot_path=screenshot_path)
            except Exception as e:
                print(f"[EggOCR] Failed to send webhook: {e}")

        except Exception as e:
            self.error_logging(e, "Error in _perform_egg_ocr_check")
        finally:
            try:
                chat_close = self.config.get("chat_close_button", [174, 40])
                if chat_close and chat_close[0]:
                    autoit.mouse_click("left", chat_close[0], chat_close[1], 1, speed=3)
            except Exception:
                pass

    def perform_quest_reroll(self, quest_index, fishing_safe=False):
        try:
            index = str(quest_index).strip()
            if index not in ("1", "2", "3") or not self.check_roblox_procs():
                return
            old_override = getattr(self, "_fishing_action_override", False)
            if fishing_safe:
                self._fishing_action_override = True
            try:
                for _ in range(4):
                    if not self.detection_running:
                        return
                    self.activate_roblox_window()
                    if not self._sleep_with_cancel(0.15, allow_fishing=fishing_safe):
                        return
                quest_menu = self.config.get("quest_menu", [0, 0])
                quest1 = self.config.get("quest1_button", [0, 0])
                quest2 = self.config.get("quest2_button", [0, 0])
                quest3 = self.config.get("quest3_button", [0, 0])
                reroll_btn = self.config.get("quest_reroll_button", [0, 0])
                if quest_menu and quest_menu[0]:
                    try:
                        autoit.mouse_click("left", quest_menu[0], quest_menu[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(quest_menu[0], quest_menu[1])
                        except Exception:
                            pass
                    if not self._sleep_with_cancel(0.5, allow_fishing=fishing_safe):
                        return
                qbtn = {"1": quest1, "2": quest2, "3": quest3}[index]
                if qbtn and qbtn[0]:
                    try:
                        autoit.mouse_click("left", qbtn[0], qbtn[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(qbtn[0], qbtn[1])
                        except Exception:
                            pass
                    if not self._sleep_with_cancel(0.4, allow_fishing=fishing_safe):
                        return
                if reroll_btn and reroll_btn[0]:
                    try:
                        autoit.mouse_click("left", reroll_btn[0], reroll_btn[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(reroll_btn[0], reroll_btn[1])
                        except Exception:
                            pass
                    if not self._sleep_with_cancel(0.45, allow_fishing=fishing_safe):
                        return
                close_btn = self.config.get("inventory_close_button", [1418, 298])
                if close_btn and close_btn[0]:
                    try:
                        autoit.mouse_click("left", close_btn[0], close_btn[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(close_btn[0], close_btn[1])
                        except Exception:
                            pass
                    self._sleep_with_cancel(0.3, allow_fishing=fishing_safe)
            finally:
                if fishing_safe:
                    self._fishing_action_override = old_override
        except Exception as e:
            try:
                self.error_logging(e, "Error in perform_quest_reroll")
            except Exception:
                pass

    def quest_claim_loop(self):
        lastclaim = datetime.min
        stopevent = self._detection_stop_event
        while self.detection_running and not stopevent.is_set():
            try:
                if not getattr(self, "auto_claim_quests_var", None) or not self.auto_claim_quests_var.get():
                    if stopevent.wait(2):
                        return
                    continue
                try:
                    interval = float(self.auto_claim_interval_var.get())
                except Exception:
                    interval = 30.0
                if (datetime.now() - lastclaim) < timedelta(minutes=interval):
                    if stopevent.wait(2):
                        return
                    continue
                if not self.detection_running or stopevent.is_set():
                    return
                if not self.is_fishing_mode_enabled():
                    self._action_scheduler.enqueue_action(self.perform_periodic_aura_screenshot_sync, name="periodical:aura", priority=2)
                    self._action_scheduler.enqueue_action(self.perform_periodic_inventory_screenshot_sync, name="periodical:inventory", priority=3)
                self.perform_quest_claim_sequence_sync(fishing_safe=self.is_fishing_mode_enabled())
                lastclaim = datetime.now()
            except Exception as error:
                self.error_logging(error, "Error in quest_claim_loop")
                if stopevent.wait(1):
                    return
            if stopevent.wait(1):
                return
    def perform_eden_path_sync(self):
        if not self.detection_running:
            print("[Eden Pathing] Aborted: detection not running")
            return
        self._eden_running = True

        def _eden_sleep(seconds):
            end = time.monotonic() + max(0.0, float(seconds))
            while time.monotonic() < end:
                if not self.detection_running: return False
                remaining = end - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(0.05, remaining))
            return self.detection_running

        try:
            # 1. Activate Roblox
            print("[Eden Pathing] Activating Roblox...")
            if not self.check_roblox_procs():
                print("[Eden Pathing] No Roblox process found, aborting")
                return
            for _ in range(4):
                if not self.detection_running:
                    print("[Eden Pathing] Aborted during activation: detection stopped")
                    return
                self.activate_roblox_window()
                time.sleep(0.15)

            # 2. Reset Character
            print("[Eden Pathing] Resetting Character...")
            keyboard.press_and_release('esc')
            if not _eden_sleep(1.25): return
            keyboard.press_and_release('r')
            if not _eden_sleep(1.25): return
            keyboard.press_and_release('enter')
            if not _eden_sleep(5): return

            if not self.detection_running:
                return

            # 3. Close chat and then click Collection Buttons

            if not _eden_sleep(0.2): return
            collections_button = self.config.get("collections_button", [0, 0])
            if collections_button and collections_button[0]:
                try:
                    autoit.mouse_click("left", collections_button[0], collections_button[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(collections_button[0], collections_button[1])
                    except Exception:
                        pass
                if not _eden_sleep(0.65): return

            exit_collections_button = self.config.get("exit_collections_button", [0, 0])
            if exit_collections_button and exit_collections_button[0]:
                try:
                    autoit.mouse_click("left", exit_collections_button[0], exit_collections_button[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(exit_collections_button[0], exit_collections_button[1])
                    except Exception:
                        pass
                if not _eden_sleep(0.65): return

            if not self.detection_running:
                return

            # 4. Camera Adjustment
            start_x = exit_collections_button[0] if exit_collections_button and exit_collections_button[0] else 500
            start_y = exit_collections_button[1] if exit_collections_button and exit_collections_button[1] else 500

            autoit.mouse_move(start_x, start_y, 0)
            autoit.mouse_down("right")
            if not _eden_sleep(0.45): return
            autoit.mouse_move(start_x, start_y + 75, 0)
            if not _eden_sleep(0.45): return
            autoit.mouse_up("right")
            try:
                autoit.send("{I down}")
            except Exception:
                pass
            if not _eden_sleep(4.0):
                try: autoit.send("{I up}")
                except: pass
                return
            try:
                autoit.send("{I up}")
            except Exception:
                pass
            if not _eden_sleep(0.3): return

            try:
                autoit.send("{O down}")
            except Exception:
                pass
            if not _eden_sleep(1.05):
                try: autoit.send("{O up}")
                except: pass
                return
            try:
                autoit.send("{O up}")
            except Exception:
                pass
            if not _eden_sleep(0.3): return

            if not self.detection_running:
                return

            # teleport using crack
            print("[Eden Pathing] Using portable crack...")
            self._teleport_crack_impl(ignore_eden=True)
            self.last_crack_time = datetime.now()
            if not _eden_sleep(10): return
            if not self.detection_running:
                return

            # 6. Eden path playback
            eden_file = os.path.join(os.getcwd(), "paths", "eden.json")
            if os.path.exists(eden_file):
                print("[Eden Pathing] Starting eden path playback...")
                self._run_eden_macro(eden_file)
            else:
                print("[Eden Pathing] Macro file not found: " + eden_file)
        except Exception as e:
            print(f"[Eden Pathing] ERROR: {e}")
            self.error_logging(e, "Error in perform_eden_path_sync")
        finally:
            print("[Eden Pathing] Path sequence finished.")
            self._eden_running = False
            self._eden_path_pending = False

    def perform_eden_contract_sync(self):
        if not self.detection_running or self.is_fishing_mode_enabled() or self.auto_pop_state: return
        self._eden_running = True
        try:
            print("[Eden] Performing contract...")
            contract_btn = self.config.get("eden_contract_button", [0, 0])

            for _ in range(4):
                if not self.detection_running: return
                pyautogui.press('e')
                time.sleep(0.3)
            
            for _ in range(7):
                if not self.detection_running: return
                if contract_btn and contract_btn[0] > 0 and contract_btn[1] > 0:
                    self.Global_MouseClick(contract_btn[0], contract_btn[1])
                    print("[Eden] Clicked Eden contract button.")
                time.sleep(0.5)
            
            time.sleep(0.5)
        except Exception as e:
            self.error_logging(e, "Error in perform_eden_contract_sync")
        finally:
            self._eden_running = False

    def eden_contract_loop(self):
        stopevent = self._detection_stop_event
        lastcontract = datetime.min
        lastpath = datetime.min
        while self.detection_running and not stopevent.is_set():
            try:
                if self.config.get("enable_idle_mode", False) or getattr(self, "_eden_running", False) or self.is_fishing_mode_enabled() or getattr(self, "_egg_collecting", False) or getattr(self, "_potion_thread_active", False) or getattr(self, "_obby_running", False):
                    stopevent.wait(2)
                    continue
                goeden = self.config.get("go_to_eden_spawn", False)
                contract = self.config.get("auto_eden_contract", False)
                if not goeden and not contract:
                    stopevent.wait(2)
                    continue
                if getattr(self, "_br_sc_running", False) or getattr(self, "_mt_running", False) or getattr(self, "auto_pop_state", False) or getattr(self, "on_auto_merchant_state", False) or getattr(self, "_auto_merchant_running", False) or getattr(self, "_fishing_busy", False) or self.reconnecting_state:
                    stopevent.wait(2)
                    continue
                current_biome = str(getattr(self, "current_biome", "") or "").upper().strip()
                if current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE") or (getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get()):
                    stopevent.wait(2)
                    continue
                if goeden:
                    try:
                        pathinterval = float(self.config.get("eden_path_interval", "35"))
                    except Exception:
                        pathinterval = 35.0
                    if (datetime.now() - lastpath) >= timedelta(minutes=pathinterval):
                        self.perform_eden_path_sync()
                        lastpath = datetime.now()
                        continue
                if contract:
                    try:
                        interval = float(self.config.get("eden_contract_interval", "10"))
                    except Exception:
                        interval = 10.0
                    if (datetime.now() - lastcontract) >= timedelta(minutes=interval):
                        self._action_scheduler.enqueue_action(self.perform_eden_contract_sync, name="eden_contract", priority=3)
                        lastcontract = datetime.now()
            except Exception as error:
                self.error_logging(error, "Error in eden_contract_loop")
            if stopevent.wait(1):
                return
    def _potion_thread_launcher(self, *args, **kwargs):
        potiongen = getattr(self, "_potion_gen", 0)
        self._potion_thread_active = True
        self._potion_active_gen = potiongen
        try:
            self._potion_thread_launcher_impl(*args, potiongen=potiongen, **kwargs)
        finally:
            if getattr(self, "_potion_active_gen", None) == potiongen:
                self._potion_thread_active = False
                self._potion_active_gen = None

    def _potion_thread_launcher_impl(self, file_name, potions_directory="crafting_files_do_not_open", stop_after=None, cancel_if=None, potiongen=None):
        try:
            final_name = file_name if file_name.endswith(".json") else f"{file_name}.json"
            path = os.path.join(os.getcwd(), potions_directory, final_name)
            if not os.path.exists(path):
                print(f"[Potion] File not found: {path}")
                return
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.error_logging(e, "Failed to load potion file")
            return

        events = data.get("events", [])
        if not events:
            return
        events.sort(key=lambda ev: ev.get("t", 0.0))

        potion_name = os.path.splitext(os.path.basename(final_name))[0]
        print(f"[Potion] Starting preparation sequence for {potion_name}")

        def _cancelled():
            try:
                if callable(cancel_if) and cancel_if():
                    return True
            except Exception:
                pass
            return (
                (potiongen is not None and getattr(self, "_potion_gen", 0) != potiongen)
                or not self.detection_running
                or not self.enable_potion_crafting_var.get()
                or self.is_fishing_mode_enabled()
            )


        def _waitcancel(seconds):
            deadline = time.monotonic() + max(0.0, float(seconds))
            while time.monotonic() < deadline:
                if _cancelled():
                    return False
                time.sleep(min(0.05, deadline - time.monotonic()))
            return not _cancelled()

        try:
            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            tab_pos = self.config.get("potion_items_tab", [0, 0])
            search_pos = self.config.get("potion_search_bar", [0, 0])
            first_slot_pos = self.config.get("potion_first_potion_slot_pos", [0, 0])
            auto_btn = self.config.get(
                "potion_auto_add_button",
                self.config.get("potion_auto_button", [0, 0]),
            )
            recipe_btn = self.config.get("potion_recipe_button", [0, 0])

            self.activate_roblox_window()
            if not _waitcancel(0.5): return

            # Press F 4 times (open crafting menu)
            for _ in range(4):
                if _cancelled(): return
                autoit.send("f")
                if not _waitcancel(0.45): return

            # Click items tab 5 times
            if tab_pos and tab_pos[0] > 0:
                for _ in range(5):
                    if _cancelled(): return
                    self.Global_MouseClick(tab_pos[0], tab_pos[1])
                    if not _waitcancel(0.3): return

            # Search bar: clear and type potion name
            if search_pos and search_pos[0] > 0:
                if _cancelled(): return
                self.Global_MouseClick(search_pos[0], search_pos[1])
                if not _waitcancel(0.6 + inventory_click_delay): return
                autoit.send("^{a}")
                if not _waitcancel(0.6 + inventory_click_delay): return
                autoit.send("{BACKSPACE}")
                if not _waitcancel(0.6 + inventory_click_delay): return
                if potion_name:
                    self._safe_type_text(potion_name)
                    if not _waitcancel(0.6 + inventory_click_delay): return
                autoit.send("{ENTER}")
                if not _waitcancel(1.5 + inventory_click_delay): return

            # Click first potion slot 3 times
            if first_slot_pos and first_slot_pos[0] > 0:
                for _ in range(3):
                    if _cancelled(): return
                    self.Global_MouseClick(first_slot_pos[0], first_slot_pos[1])
                    if not _waitcancel(0.3): return

            # Click Auto Add button (must happen before opening recipe)
            if auto_btn and auto_btn[0] > 0:
                if _cancelled(): return
                self.Global_MouseClick(auto_btn[0], auto_btn[1])
                if not _waitcancel(0.5): return

            # Click recipe button
            if recipe_btn and recipe_btn[0] > 0:
                if _cancelled(): return
                self.Global_MouseClick(recipe_btn[0], recipe_btn[1])
                if not _waitcancel(2.0): return

        except Exception as e:
            self.error_logging(e, "Potion prep sequence failed")
            return

        # --- Potion Switching ---
        overall_start = time.perf_counter()

        while not _cancelled():
            if stop_after is not None and time.perf_counter() - overall_start >= float(stop_after):
                print("[Potion] Switching interval reached. Stopping for next potion.")
                break

            loop_start = time.perf_counter()
            pressed_keys = set()
            print("[Potion] Starting loop iteration...")

            for ev in events:
                if _cancelled(): break
                if stop_after is not None and time.perf_counter() - overall_start >= float(stop_after):
                    break

                t = max(float(ev.get("t", 0.0)), 0.0)
                target_time = loop_start + t
                now = time.perf_counter()

                if target_time > now:
                    diff = target_time - now
                    if diff > 0.02:
                        sleep_ms = int((diff - 0.015) * 1000)
                        chunks = sleep_ms // 50
                        for _ in range(chunks):
                            if _cancelled(): break
                            if stop_after is not None and time.perf_counter() - overall_start >= float(stop_after):
                                break
                            if not _waitcancel(0.05): break
                        rem = (sleep_ms % 50) / 1000.0
                        if rem > 0:
                            if not _waitcancel(rem): return
                    while time.perf_counter() < target_time:
                        if not _waitcancel(min(0.02, target_time - time.perf_counter())):
                            break

                if _cancelled(): break
                typ = ev.get("type", "")
                try:
                    if typ == "mouse_move":
                        autoit.mouse_move(int(ev.get("x", 0)), int(ev.get("y", 0)), speed=0)
                    elif typ == "mouse_down":
                        autoit.mouse_down(ev.get("button", "left"))
                    elif typ == "mouse_up":
                        autoit.mouse_up(ev.get("button", "left"))
                    elif typ == "mouse_wheel":
                        delta = int(ev.get("delta", 0))
                        if delta != 0:
                            mouse.wheel(delta)
                    elif typ == "key_down":
                        k = ev.get("key", "")
                        if k and k not in ("f1", "f2", "f3", "f4"):
                            keyboard.press(k)
                            pressed_keys.add(k)
                    elif typ == "key_up":
                        k = ev.get("key", "")
                        if k and k not in ("f1", "f2", "f3", "f4"):
                            keyboard.release(k)
                            pressed_keys.discard(k)
                except Exception:
                    pass

            # Release stuck keys at end of each iteration
            if pressed_keys:
                print(f"[Potion] Releasing {len(pressed_keys)} stuck keys...")
                for k in list(pressed_keys):
                    try:
                        keyboard.release(k)
                    except Exception:
                        pass

            print("[Potion] Loop iteration finished.")
            if not _waitcancel(0.1): return

    def start_potion_crafting(self):
        if not hasattr(self, "_potion_craft_lock"):
            self._potion_craft_lock = threading.Lock()
        with self._potion_craft_lock:
            worker = getattr(self, "_potion_craft_thread", None)
            if worker and worker.is_alive():
                return
            workergen = getattr(self, "_potion_craft_worker_gen", 0) + 1
            self._potion_craft_worker_gen = workergen

            def _potion_craft_loop():
                try:
                    try:
                        while self.detection_running and self._potion_craft_worker_gen == workergen:
                            try:
                                if self.is_fishing_mode_enabled():
                                    time.sleep(1)
                                    continue
                                if not getattr(self, "enable_potion_crafting_var", None) or not self.enable_potion_crafting_var.get():
                                    time.sleep(1)
                                    continue

                                if (self.reconnecting_state or self.auto_pop_state or
                                    self.on_auto_merchant_state or
                                    self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE") or
                                    getattr(self, "_mt_running", False) or
                                    (getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False))):
                                    time.sleep(2)
                                    continue

                                if self.config.get("enable_idle_mode", False):
                                    time.sleep(2)
                                    continue

                                switching_enabled = self.config.get("enable_potion_switching", False)
                                if switching_enabled:
                                    current_index = 0
                                    slot_keys = [
                                        "selected_potion_file",
                                        "potion_file_1",
                                        "potion_file_2",
                                        "potion_file_3",
                                    ]
                                    while self.detection_running and self.enable_potion_crafting_var.get() and self._potion_craft_worker_gen == workergen:
                                        if not bool(self.config.get("enable_potion_switching", False)): break
                                        interval = float(self.config.get("potion_switch_interval", "60"))
                                        target_file = self.config.get(slot_keys[current_index], "").strip()

                                        if not target_file or target_file.lower() == "none":
                                            print(f"[Potion] Slot #{current_index} is empty. Skipping.")
                                            current_index = (current_index + 1) % 4
                                            time.sleep(0.5)
                                            continue

                                        print(f"[Potion] Starting Auto Craft: {target_file} (Index: {current_index})")
                                        self._potion_thread_launcher(
                                            target_file,
                                            "crafting_files_do_not_open",
                                            stop_after=interval,
                                            cancel_if=lambda: not bool(self.config.get("enable_potion_switching", False)),
                                        )
                                        current_index = (current_index + 1) % 4
                                else:
                                    file_name = self.config.get("selected_potion_file", "").strip()
                                    if not file_name or file_name.lower() == "none":
                                        time.sleep(2)
                                        continue

                                    print(f"[Potion] Starting Auto Craft: {file_name}")
                                    self._potion_thread_launcher(
                                        file_name,
                                        cancel_if=lambda: bool(self.config.get("enable_potion_switching", False)),
                                    )
                                    self.config["potion_last_file"] = file_name
                                    self.save_config()

                                time.sleep(0.5)

                            except Exception as e:
                                self.error_logging(e, "Error in potion craft loop iteration")
                                time.sleep(2)
                    except Exception as e:
                        self.error_logging(e, "Error in potion craft loop")
                finally:
                    with self._potion_craft_lock:
                        if self._potion_craft_worker_gen == workergen:
                            self._potion_craft_worker_gen += 1
                            self._potion_craft_thread = None

            self._potion_craft_thread = threading.Thread(target=_potion_craft_loop, daemon=True)
            self._potion_craft_thread.start()
    def stop_potion_crafting(self):
        with self._potion_craft_lock:
            self._potion_craft_worker_gen += 1
            self._potion_gen += 1
            worker = self._potion_craft_thread
            self._potion_craft_thread = None
        if worker and worker.is_alive() and worker is not threading.current_thread():
            worker.join()

    def glitch_effect(self):
        glitch_texts = [
            "GLITCHED", "GlItChEd", "gLiTcHeD", "GL1TCHED", "g#lt#c%",
            "g!olitc3", "g$&*ct", "G1iTcHeD", "gL1tCh3d", "gL!tCh3d",
            "G1!tCh3D", "gL1tCh3D", "gL!tCh3D", "G1!tCh3d", "gL1tCh3d"]

        glitch_colors = [
            "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF",
            "#00FFFF", "#a6c9a3", "#ff69b4", "#8a2be2", "#7fff00",
            "#d2691e", "#ff7f50", "#6495ed", "#dc143c", "#00ced1"
        ]

        def update_glitch():
            glitchy_ahh_text = random.choice(glitch_texts)
            color = random.choice(glitch_colors)
            self.stats_labels["GLITCHED"].config(text=f"{glitchy_ahh_text}: {self.biome_counts['GLITCHED']}",
                                                 foreground=color)
            self.root.after(25, update_glitch)

        update_glitch()

    def update_stats(self):
        total_biomes = sum(self.biome_counts.values())

        if hasattr(self, "stats_labels"):
            for biome, label in self.stats_labels.items():
                try:
                    label.config(text=f"{biome}: {self.biome_counts[biome]}")
                except Exception:
                    pass

        if hasattr(self, "total_biomes_label"):
            try:
                self.total_biomes_label.config(text=f"Total Biomes Found: {total_biomes}", foreground="light green")
            except Exception:
                pass

        if hasattr(self, "session_label"):
            try:
                self.session_label.config(text=f"Running Session: {self.get_total_session_time()}")
            except Exception:
                pass

        self.save_config()
        
        if hasattr(self, "on_stats_update") and callable(self.on_stats_update):
            try:
                self.on_stats_update()
            except Exception:
                pass

    def format_seconds_to_hhmmss(self, total_seconds):
        total_seconds = int(total_seconds)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"


    def start_capture_thread(self, config_key, coord_vars):
        snipping_tool = SnippingWidget(self.root, config_key=config_key,
                                       callback=lambda region: self.update_coordinates(config_key, region, coord_vars))
        snipping_tool.start()

    def update_coordinates(self, config_key, region, coord_vars):
        x, y = region[0], region[1]
        coord_vars[config_key][0].set(x)
        coord_vars[config_key][1].set(y)
        self.save_config()

    def validate_and_save_ps_link(self):
        private_server_link = self.private_server_link_entry.get()
        if not self.validate_private_server_link(private_server_link):
            messagebox.showwarning(
                "Invalid PS Link!",
                "The link you provided is not a valid Roblox link. It could be either a share link or a private server code link. "
                "Please ensure the link is correct and try again.\n\n"
                "Valid links should look like:\n"
                "- Share link: https://www.roblox.com/share?code=1234567899abcdefxyz&type=Server\n"
                "- Private server code link: https://www.roblox.com/games/15532962292/Sols-RNG?privateServerLinkCode=xxxxxxxx"
            )
            return

        self.save_config()

    def validate_private_server_link(self, link):
        try:
            from urllib.parse import parse_qs, urlparse

            raw_link = str(link or "").strip()
            if not raw_link:
                return False

            # Backward compatible support for old raw PS-code format
            if re.search(r"privateserverlinkcode=", raw_link, flags=re.IGNORECASE):
                return True

            parsed = urlparse(raw_link)
            if parsed.scheme not in ("http", "https"):
                return False

            host = (parsed.netloc or "").lower()
            if host not in ("roblox.com", "www.roblox.com"):
                return False

            path = parsed.path or ""
            query = parse_qs(parsed.query)
            query_ci = {str(k).strip().lower(): v for k, v in query.items()}

            # Private-server-code links
            if query_ci.get("privateserverlinkcode") and str(query_ci["privateserverlinkcode"][0]).strip():
                return True

            # Share links
            if path.startswith("/share"):
                has_code = bool(query_ci.get("code") and str(query_ci["code"][0]).strip())
                link_type = str(query_ci.get("type", [""])[0]).strip().lower()
                return has_code and link_type in ("", "server")

            return False
        except Exception:
            return False

    def _build_reconnect_deep_links(self, link):
        try:
            from urllib.parse import parse_qs, quote, urlparse

            raw_link = str(link or "").strip()
            if not raw_link:
                return []

            parsed = urlparse(raw_link)
            query = parse_qs(parsed.query)
            query_ci = {str(k).strip().lower(): v for k, v in query.items()}
            path = parsed.path or ""
            is_roblox_protocol = parsed.scheme.lower() == "roblox"
            path_l = path.lower()
            raw_l = raw_link.lower()

            # roblox://placeID=...&linkCode=... does not parse query normally
            raw_place_match = re.search(r"placeID=(\d+)", raw_link, flags=re.IGNORECASE)
            raw_place_id = raw_place_match.group(1) if raw_place_match else ""

            place_match = re.search(r"/games/(\d+)", path, flags=re.IGNORECASE)
            place_id = place_match.group(1) if place_match else (raw_place_id or "15532962292")

            link_code = ""
            source_type = ""
            if query_ci.get("privateserverlinkcode"):
                link_code = str(query_ci["privateserverlinkcode"][0]).strip()
                source_type = "private"
            elif query_ci.get("linkcode"):
                link_code = str(query_ci["linkcode"][0]).strip()
                source_type = "private"
            elif query_ci.get("code"):
                link_type = str(query_ci.get("type", [""])[0]).strip().lower()
                if link_type in ("", "server"):
                    link_code = str(query_ci["code"][0]).strip()
                    source_type = "share"

            # Backward-compat support for old raw format:
            # Sols-RNG?privateServerLinkCode=xxxxxxxx
            if not link_code:
                m = re.search(r"privateServerLinkCode=([^&\s]+)", raw_link, flags=re.IGNORECASE)
                if m:
                    link_code = str(m.group(1)).strip()
                    source_type = "private"
            if not link_code:
                m = re.search(r"linkCode=([^&\s]+)", raw_link, flags=re.IGNORECASE)
                if m:
                    link_code = str(m.group(1)).strip()
                    source_type = "private"
            if not link_code:
                m = re.search(r"code=([^&\s]+)", raw_link, flags=re.IGNORECASE)
                if m:
                    link_code = str(m.group(1)).strip()
                    if "navigation/share_links" in raw_l or path_l.startswith("/share"):
                        source_type = "share"

            # Keep explicit roblox:// input as the first launch candidate.
            candidates = []
            if is_roblox_protocol:
                candidates.append(raw_link)

            if not link_code:
                return candidates

            encoded_code = quote(link_code, safe="")
            share_deep_link = f"roblox://navigation/share_links?code={encoded_code}&type=Server"
            private_deep_link = f"roblox://placeID={place_id}&linkCode={encoded_code}"
            if source_type == "private":
                candidates.extend([private_deep_link, share_deep_link])
            else:
                candidates.extend([share_deep_link, private_deep_link])

            deduped = []
            for candidate in candidates:
                if candidate not in deduped:
                    deduped.append(candidate)
            return deduped
        except Exception:
            return []

    def _check_disconnect_in_logs(self):
        try:
            logfile = self.get_latest_log_file()
            if not logfile or not os.path.exists(logfile):
                return False
            if not hasattr(self, "_disconnect_log_file"):
                self._disconnect_log_file = None
                self._last_position_disconnect = 0
                self._last_disconnect_time = 0
                self._disconnect_handled = False
            if self._disconnect_handled:
                return False
            filesize = os.path.getsize(logfile)
            if logfile != self._disconnect_log_file:
                try:
                    created = os.path.getctime(logfile)
                except OSError:
                    created = 0
                started = getattr(self, "_detection_started_at", time.time())
                self._last_position_disconnect = 0 if created >= started - 1 else filesize
                self._disconnect_log_file = logfile
            elif filesize < self._last_position_disconnect:
                self._last_position_disconnect = filesize
            if time.time() - self._last_disconnect_time < 30:
                return False
            startpos = self._last_position_disconnect
            with open(logfile, "rb") as file:
                file.seek(startpos)
                data = file.read()
            newline = data.rfind(b"\n")
            if newline < 0:
                return False
            lines = [line.decode("utf-8", errors="ignore") for line in data[:newline + 1].splitlines()]
            if not lines:
                self._last_position_disconnect = startpos + newline + 1
                return False
            username = self._get_target_roblox_username() if hasattr(self, "_get_target_roblox_username") else ""
            states = getattr(self, "_log_username_state_map", {})
            state = states.get(logfile)
            if username and state != "accepted":
                try:
                    valid = self._consume_log_username_validation(logfile) if hasattr(self, "_consume_log_username_validation") else True
                except Exception:
                    valid = False
                state = getattr(self, "_log_username_state_map", {}).get(logfile)
                if state == "rejected":
                    self._last_position_disconnect = startpos + newline + 1
                    return False
                if state != "accepted" or not valid:
                    return False
            elif state == "rejected":
                self._last_position_disconnect = startpos + newline + 1
                return False
            self._last_position_disconnect = startpos + newline + 1
            markers = (
                "Client:Disconnect",
                "Sending disconnect with reason:",
                "<< AUTO REJOIN >> Rejoin Attempt :",
            )
            for line in reversed(lines):
                if any(marker in line for marker in markers):
                    self.append_log(f"[Disconnect] Detected disconnect in Roblox logs: {line.strip()}")
                    self._last_disconnect_time = time.time()
                    self._disconnect_handled = True
                    return True
        except Exception as error:
            self.error_logging(error, "Error checking disconnect in logs")
        return False
    def check_disconnect_loop(self, current_attempt=1):
        if not hasattr(self, "has_sent_disconnected_message"):
            self.has_sent_disconnected_message = False

        stop_event = self._detection_stop_event
        while self.detection_running and not stop_event.is_set():
            try:
                process_dead = not self.check_roblox_procs()
                log_disconnect = not process_dead and self._check_disconnect_in_logs()
                if not process_dead and not log_disconnect:
                    if stop_event.wait(0.5):
                        return
                    continue

                reason = "Roblox instance closed!" if process_dead else "Disconnected from server (detected in Roblox logs)"
                self._pause_timer_for_disconnect(reason)
                if stop_event.wait(4.5):
                    return

                auto_reconnect = bool(self.config.get("auto_reconnect"))
                deep_links = self._build_reconnect_deep_links(self.config.get("private_server_link")) if auto_reconnect else []
                if auto_reconnect and not deep_links:
                    if not getattr(self, "_missing_reconnect_link_notified", False):
                        self.send_webhook_status("Auto-reconnect is enabled, but no valid private server link is configured. Rejoin manually.", color=0xff0000)
                        self._missing_reconnect_link_notified = True
                    auto_reconnect = False

                old_log_file = None
                old_log_size = None
                try:
                    old_log_file = self.get_latest_log_file()
                    old_log_size = os.path.getsize(old_log_file)
                except Exception:
                    pass

                if auto_reconnect:
                    rejoined = False
                    for attempt in range(current_attempt, 5):
                        if not self.detection_running or stop_event.is_set():
                            return
                        self.terminate_roblox_processes()
                        self.send_webhook_status("Reconnecting to your server. hold on bro", color=0xffff00)
                        self.set_title_threadsafe(f"Coteab {current_ver} (Reconnecting)")
                        launch_error = None
                        for deep_link in deep_links:
                            try:
                                os.startfile(deep_link)
                                launch_error = None
                                break
                            except Exception as e:
                                launch_error = e
                        if launch_error is not None:
                            self.error_logging(launch_error, "Failed to launch reconnect link")
                            if stop_event.wait(2):
                                return
                            continue

                        deadline = time.monotonic() + 180
                        while self.detection_running and not stop_event.is_set() and time.monotonic() < deadline:
                            if self.check_roblox_procs():
                                break
                            if stop_event.wait(2):
                                return
                        if not self.detection_running or stop_event.is_set():
                            return
                        if not self.check_roblox_procs():
                            continue

                        self.send_webhook_status("Roblox opened. Loading into the games...", color=0x4aff65)
                        self.has_sent_disconnected_message = False
                        if not self.reconnect_check_start_button(old_log_file=old_log_file, old_log_size=old_log_size):
                            if not self.detection_running or stop_event.is_set():
                                return
                            self.send_webhook_status("Stuck in 'In Main Menu' for too long. I might reconnect bro back to server again", color=0xff0000)
                            try:
                                old_log_file = self.get_latest_log_file()
                                old_log_size = os.path.getsize(old_log_file)
                            except Exception:
                                pass
                            continue

                        self._resume_timer_after_reconnect()
                        if not self.reconnecting_state:
                            self.close_chat_if_open()
                            self._disconnect_handled = False
                            rejoined = True
                            break
                    if rejoined:
                        continue
                    if stop_event.is_set() or not self.detection_running:
                        return
                    self.terminate_roblox_processes()
                    self.send_webhook_status("Max retries reached but failed to rejoin the game. Macro stopped", color=0xff0000)
                    self.stop_detection()
                    return

                while self.detection_running and not stop_event.is_set() and not self.check_roblox_procs():
                    if stop_event.wait(1):
                        return
                while self.detection_running and not stop_event.is_set() and not self.reconnect_logs_state(old_log_file=old_log_file, old_log_size=old_log_size):
                    if stop_event.wait(1):
                        return
                if not self.detection_running or stop_event.is_set():
                    return
                self._resume_timer_after_reconnect()
                if not self.reconnecting_state:
                    self.close_chat_if_open()
                    self._disconnect_handled = False
            except Exception as e:
                self.error_logging(e, "Error in check_disconnect_loop function.")
                if stop_event.wait(1):
                    return
    def reconnect_check_start_button(self, old_log_file=None, old_log_size=None):
        try:
            self.set_title_threadsafe(f"Coteab {current_ver} (Reconnecting - In Main Menu)")
            reconnect_start_button = self.config.get("reconnect_start_button", [954, 876])

            for _ in range(10):
                if not self.detection_running or self._detection_stop_event.is_set():
                    return False
                self.activate_roblox_window()
                if self._detection_stop_event.wait(0.5):
                    return False

            deadline = time.monotonic() + 600
            click_interval = 4.0
            while time.monotonic() < deadline:
                if not self.detection_running or self._detection_stop_event.is_set():
                    return False
                self.activate_roblox_window()
                if self._detection_stop_event.wait(0.3):
                    return False
                self.Global_MouseClick(reconnect_start_button[0], reconnect_start_button[1])
                if self.reconnect_logs_state(old_log_file=old_log_file, old_log_size=old_log_size):
                    self.send_webhook_status("Clicked 'Start' button and you are in the game now!!", color=0x4aff65)
                    print("Game has started, exiting click loop.")
                    self.set_title_threadsafe(f"Coteab {current_ver} (Running)")
                    return True
                if self._detection_stop_event.wait(click_interval):
                    return False

            self.append_log("Timed out waiting for in-game state after 4 minutes.")
            return False
        except Exception as e:
            self.error_logging(e, "Error in reconnect_check_start_button function.")
            return False
    def reconnect_logs_state(self, old_log_file=None, old_log_size=None):
        try:
            log_file_path = self.get_latest_log_file()
            if old_log_file and log_file_path == old_log_file:
                if old_log_size is None:
                    return False
                with open(log_file_path, "rb") as f:
                    f.seek(old_log_size)
                    data = f.read()
                log_lines = [line.decode("utf-8", errors="ignore") for line in data.splitlines()]
            else:
                log_lines = self.read_full_log_file(log_file_path)
            return any(re.search(r'"state":"Equipped', line) for line in reversed(log_lines))
        except Exception as e:
            self.error_logging(e, "Error in reconnect_logs_state function.")
            return False

    def _pause_timer_for_disconnect(self, reason=None):
        try:
            if not getattr(self, "timer_paused_by_disconnect", False):
                if self.start_time:
                    now = datetime.now()
                    elapsed = int((now - self.start_time).total_seconds())
                    self.saved_session += elapsed
                    self.start_time = None
                self.timer_paused_by_disconnect = True
                self.pause_reason = reason
            self.reconnecting_state = True
            self.set_title_threadsafe(
                f"""Coteab {current_ver} (Roblox Disconnected :c )""")
            if reason and not getattr(self, 'has_sent_disconnected_message', False):
                sent = self.send_webhook_status(reason, color=0xff0000)
                self.has_sent_disconnected_message = sent is not False
            self.save_config()
        except Exception as e:
            self.error_logging(e, "_pause_timer_for_disconnect")

    def register_shutdown_handler(self):
        try:
            atexit.register(self._on_exit_handler)
        except Exception:
            pass
        try:
            import win32api, win32con
            def _handler(ctrl_type):
                if ctrl_type in (win32con.CTRL_SHUTDOWN_EVENT, win32con.CTRL_LOGOFF_EVENT):
                    try:
                        self._pause_timer_for_disconnect("System Shutdown")
                    except Exception:
                        pass
                return False

            win32api.SetConsoleCtrlHandler(_handler, True)
        except Exception:
            pass

    def _enqueue_player_embed(self, embed):
        if not hasattr(self, "player_log_queue") or self.player_log_queue is None:
            try:
                self.player_log_queue = queue.Queue()
            except Exception:
                return
        try:
            self.player_log_queue.put(embed)
        except Exception:
            pass

    def _parse_iso_ts(self, s):
        try:
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            return datetime.fromisoformat(s)
        except:
            return datetime.now(timezone.utc)

    def check_roblox_procs(self):
        try:
            try:
                current_user_norm = str(psutil.Process().username() or "").strip().lower()
            except Exception:
                current_user_norm = ""

            for proc in psutil.process_iter(["name", "username"]):
                try:
                    info = proc.info or {}
                    proc_name = str(info.get("name") or "").casefold()
                    if proc_name not in {"robloxplayerbeta.exe", "windows10universal.exe"}:
                        continue
                    proc_user_norm = str(info.get("username") or "").strip().lower()
                    if current_user_norm and proc_user_norm and proc_user_norm != current_user_norm:
                        continue
                    return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            self.error_logging(e, "Error in check_roblox_procs function.")

        return False
    def terminate_roblox_processes(self):
        try:
            current_user = psutil.Process().username()
            current_user_norm = str(current_user or "").strip().lower()
            running_processes = psutil.process_iter(['pid', 'name', 'username'])
            target_procs = ['RobloxPlayerBeta.exe', 'Windows10Universal.exe', 'RobloxPlayerLauncher.exe', 'RobloxCrashHandler.exe']

            for proc in running_processes:
                try:
                    proc_name = str(proc.info.get('name') or "")
                    if proc_name not in target_procs: continue
                    proc_user_norm = str(proc.info.get('username') or "").strip().lower()
                    if current_user_norm and proc_user_norm and proc_user_norm != current_user_norm: continue
                    print(f"Terminating process: {proc_name} (PID: {proc.info.get('pid')})")
                    try:
                        proc.kill()
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        pass
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

        except Exception as e:
            self.error_logging(e, "Error in terminate_roblox_processes function.")

    def perform_periodic_inventory_screenshot_sync(self):
        try:
            if self.config.get("enable_idle_mode", False): return
            if self._is_fishing_blocked(): return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return
            if not getattr(self, "periodical_inventory_var", None) or not self.periodical_inventory_var.get(): return
            if not self.detection_running or self.reconnecting_state: return
            try:
                interval_min = float(self.periodical_inventory_interval_var.get())
            except Exception:
                interval_min = 5.0
            if (datetime.now() - getattr(self, "last_inventory_screenshot_time", datetime.min)) < timedelta(minutes=interval_min):
                return
            if not self.check_roblox_procs(): return
            for _ in range(4):
                if not self.detection_running or self._is_fishing_blocked() or self.auto_pop_state or (getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)):
                    return
                self.activate_roblox_window()
                if not self._sleep_with_cancel(0.8):
                    return
            search_bar = self.config.get("search_bar", [855, 358])
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
            if inventory_menu and inventory_menu[0]:
                try:
                    autoit.mouse_click("left", inventory_menu[0], inventory_menu[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.35):
                    return
            if items_tab and items_tab[0]:
                try:
                    autoit.mouse_click("left", items_tab[0], items_tab[1], 1, speed=3)
                    if not self._sleep_with_cancel(1):
                        return
                    autoit.mouse_click("left", search_bar[0], search_bar[1], 1, speed=3)
                except Exception:
                    try:
                        self.Global_MouseClick(items_tab[0], items_tab[1])
                    except Exception:
                        pass
                if not self._sleep_with_cancel(0.35):
                    return
            try:
                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)
                filename = os.path.join(screenshot_dir, f"inventory_screenshot_{int(time.time())}.png")
                img = pyautogui.screenshot()
                img.save(filename)
                self.send_inventory_screenshot_webhook(filename)
                self.last_inventory_screenshot_time = datetime.now()
            except Exception as e:
                self.error_logging(e, "Error taking/sending inventory screenshot")
            try:
                if inventory_close_button and inventory_close_button[0]:
                    try:
                        autoit.mouse_click("left", inventory_close_button[0], inventory_close_button[1], 1, speed=3)
                    except Exception:
                        try:
                            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        except Exception:
                            pass
                    self._sleep_with_cancel(0.22)
            except Exception as e:
                self.error_logging(e, "Error while closing inventory after screenshot")
        except Exception as e:
            self.error_logging(e, "Error in perform_periodic_inventory_screenshot_sync")

    def Global_MouseClick(self, x, y, click=1):
        time.sleep(0.335)
        autoit.mouse_click("left", x, y, click, speed=3)

    def use_portable_crack(self):
        try:
            self._action_scheduler.enqueue_action(self._teleport_crack_impl, name="teleport_crack", priority=8)
        except Exception:
            try:
                self._teleport_crack_impl()
            except Exception:
                pass

    def _teleport_crack_impl(self, ignore_eden=False):
        self._portable_crack_running = True
        fishing_override = bool(getattr(self, "_fishing_br_sc_override", False))
        try:
            def _cancelled():
                if fishing_override:
                    return not self.detection_running or self.reconnecting_state
                return (
                    not self.detection_running
                    or self.reconnecting_state
                    or self.auto_pop_state
                    or self.on_auto_merchant_state
                    or (self.is_fishing_mode_enabled() if ignore_eden else self._is_fishing_blocked())
                    or self.config.get("enable_potion_crafting")
                    or (getattr(self, "_egg_collecting", False) or (not ignore_eden and getattr(self, "_eden_running", False)) or getattr(self, "_potion_thread_active", False))
                    or (getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get())
                )

            def _do_sleep(seconds):
                if fishing_override or ignore_eden:
                    time.sleep(max(0.0, seconds))
                    return not _cancelled()
                return self._sleep_with_cancel(seconds)

            if _cancelled(): return
            if not _do_sleep(1.3): return

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            search_bar = self.config.get("search_bar", [855, 358])
            first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
            amount_box = self.config.get("amount_box", [594, 570])
            use_button = self.config.get("use_button", [710, 573])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])

            for _ in range(3):
                if _cancelled(): return
                self.activate_roblox_window()
                if not _do_sleep(0.15): return

            self.append_log("Using Portable Crack")

            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            if not _do_sleep(0.2 + inventory_click_delay): return
            self.Global_MouseClick(items_tab[0], items_tab[1])
            if not _do_sleep(0.23): return
            self.Global_MouseClick(items_tab[0], items_tab[1])
            if not _do_sleep(0.23): return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.2 + inventory_click_delay): return
            if _cancelled(): return

            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.23): return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.23): return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.2 + inventory_click_delay): return
            if _cancelled(): return
            self._safe_type_text("crack")
            if not _do_sleep(0.4 + inventory_click_delay): return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not _do_sleep(0.4 + inventory_click_delay): return
            try:
                if not self._ocr_first_slot_matches("Portable Crack"):
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    _do_sleep(0.15 + inventory_click_delay)
                    return
            except Exception as e:
                self.append_log(f"[OCR Failsafe] Validation failed for Portable Crack: {e}; skipping item use.")
                self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                _do_sleep(0.15 + inventory_click_delay)
                return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not _do_sleep(0.4 + inventory_click_delay): return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not _do_sleep(0.3 + inventory_click_delay): return

            if _cancelled(): return
            self.Global_MouseClick(amount_box[0], amount_box[1])
            if not _do_sleep(0.16 + inventory_click_delay): return
            autoit.send("^{a}")
            if not _do_sleep(0.13 + inventory_click_delay): return
            autoit.send("{BACKSPACE}")
            if not _do_sleep(0.13 + inventory_click_delay): return
            self._safe_type_text('1')
            if not _do_sleep(0.13 + inventory_click_delay): return

            if _cancelled(): return
            self.Global_MouseClick(use_button[0], use_button[1])
            if not _do_sleep(0.22 + inventory_click_delay): return

            if _cancelled(): return
            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
            _do_sleep(0.22 + inventory_click_delay)

        except Exception as e:
            self.error_logging(e, "Error in _teleport_crack_impl function.")
        finally:
            self._portable_crack_running = False

    def use_br_sc(self, item_name):
        try:
            self._action_scheduler.enqueue_action(lambda: self._use_br_sc_impl(item_name), name=f"use_br_sc:{item_name}", priority=6)
        except Exception:
            try:
                self._use_br_sc_impl(item_name)
            except Exception:
                pass

    def _use_br_sc_impl(self, item_name):
        self._br_sc_running = True
        fishing_override = bool(getattr(self, "_fishing_br_sc_override", False))
        _inventory_opened = False
        try:
            def _cancelled():
                if fishing_override:
                    return (
                        not self.detection_running
                        or self.reconnecting_state
                        or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE")
                        or self.current_biome in self.config.get("disabled_biomes_br_sc", [])
                    )
                return (
                    not self.detection_running
                    or self.reconnecting_state
                    or self.auto_pop_state
                    or self.on_auto_merchant_state
                    or self._is_fishing_blocked()
                    or self.config.get("enable_potion_crafting")
                    or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE")
                    or self.current_biome in self.config.get("disabled_biomes_br_sc", [])
                    or getattr(self, "_mt_running", False)
                    or (getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False))
                    or (getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get())
                )

            # When called from fishing loop
            def _do_sleep(seconds):
                if fishing_override:
                    time.sleep(max(0.0, seconds))
                    return not _cancelled()
                return self._sleep_with_cancel(seconds)

            if _cancelled():
                return
            if not _do_sleep(1.3):
                return

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            inventory_menu = self.config.get("inventory_menu", [36, 535])
            items_tab = self.config.get("items_tab", [1272, 329])
            search_bar = self.config.get("search_bar", [855, 358])
            first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
            amount_box = self.config.get("amount_box", [594, 570])
            use_button = self.config.get("use_button", [710, 573])
            inventory_close_button = self.config.get("inventory_close_button", [1418, 298])

            for _ in range(5):
                if _cancelled():
                    return
                self.activate_roblox_window()
                if not _do_sleep(0.15):
                    return

            print(f"Using {item_name.capitalize()}")

            self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
            _inventory_opened = True
            if not _do_sleep(0.2 + inventory_click_delay):
                return
            self.Global_MouseClick(items_tab[0], items_tab[1])
            if not _do_sleep(0.23):
                return
            self.Global_MouseClick(items_tab[0], items_tab[1])
            if not _do_sleep(0.23):
                return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.2 + inventory_click_delay):
                return
            if _cancelled():
                return

            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.23):
                return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.23):
                return
            self.Global_MouseClick(search_bar[0], search_bar[1])
            if not _do_sleep(0.2 + inventory_click_delay):
                return
            if _cancelled():
                return
            self._safe_type_text(item_name)
            if not _do_sleep(0.4 + inventory_click_delay):
                return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not _do_sleep(0.4 + inventory_click_delay):
                return
            try:
                if not self._ocr_first_slot_matches(item_name):
                    inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    _do_sleep(0.15 + inventory_click_delay)
                    return
            except Exception as e:
                self.append_log(f"[OCR Failsafe] Validation failed for {item_name}: {e}; skipping item use.")
                inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                _do_sleep(0.15 + inventory_click_delay)
                return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not _do_sleep(0.4 + inventory_click_delay):
                return
            self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
            if not _do_sleep(0.3 + inventory_click_delay):
                return
            if _cancelled():
                return
            self.Global_MouseClick(amount_box[0], amount_box[1])
            if not _do_sleep(0.16 + inventory_click_delay):
                return
            autoit.send("^{a}")
            if not _do_sleep(0.13 + inventory_click_delay):
                return
            autoit.send("{BACKSPACE}")
            if not _do_sleep(0.13 + inventory_click_delay):
                return
            self._safe_type_text('1')
            if not _do_sleep(0.13 + inventory_click_delay):
                return

            if _cancelled():
                return
            self.Global_MouseClick(use_button[0], use_button[1])
            if not _do_sleep(0.22 + inventory_click_delay):
                return

            if _cancelled():
                return
            self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
            _do_sleep(0.22 + inventory_click_delay)
            _inventory_opened = False

        except Exception as e:
            self.error_logging(e, "Error in use_br_sc function.")
        finally:
            if _inventory_opened:
                try:
                    _inv_close = self.config.get("inventory_close_button", [1418, 298])
                    self.Global_MouseClick(_inv_close[0], _inv_close[1])
                    time.sleep(0.35)
                except Exception:
                    pass
            self._br_sc_running = False

    def Merchant_Handler(self, known_merchant_name=None):
        try:
            fishing_override = bool(getattr(self, "_fishing_br_sc_override", False))
            event_override = bool(getattr(self, "_merchant_log_event_override", False))
            def _cancelled():
                if fishing_override or event_override:
                    return (
                        not self.detection_running
                        or self.reconnecting_state
                    )
                return (
                    not self.detection_running
                    or self.reconnecting_state
                    or self.auto_pop_state
                    or (self._is_fishing_blocked() and not event_override)
                    or (self.config.get("enable_potion_crafting") and not event_override)
                    or ((getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)) and not event_override)
                    or self.current_biome in ("GLITCHED", "DREAMSPACE", "CYBERSPACE")
                )
            if _cancelled():
                return False

            merchant_settings, merchant_setting_warnings = validate_merchant_settings(self.config)
            for warning in merchant_setting_warnings:
                self.append_log(f"[Merchant Config] {warning}")

            self.on_auto_merchant_state = True
            merchant_name_ocr_pos = self.config["merchant_name_ocr_pos"]
            merchant_open_button = self.config["merchant_open_button"]
            first_item_slot_pos = self.config.get("first_item_merchant_slot_pos", [954, 696])
            item_name_ocr_pos = self.config["item_name_ocr_pos"]
            merchant_dialogue_box = self.config["merchant_dialogue_box"]
            merchant_extra_slot = merchant_settings["merchant_extra_slot"]

            merchant_name = known_merchant_name if known_merchant_name in ("Mari", "Jester", "Rin") else ""
            if merchant_name:
                self.append_log(f"[Merchant Detection] Using log-detected merchant: {merchant_name}")
            merchant_aliases = {
                "Mari": ["Mori", "Marl", "Mar1", "MarI", "Mar!", "Maori"],
                "Jester": ["Dester", "Jostor", "Jestor", "Joster", "Destor", "Doster", "Dostor"],
                "Rin": ["R1n", "R1N", "RiN"]
            }
            ocrMisdetect_Key = {
                "heavenly potion": "heavenly potion",
                "henvnely potion": "heavenly potion",
                "rune of galaxy": "rune of galaxy",
                "rune of rainstorm": "rune of rainstorm",
                "strange potion": "strange potion",
                "stella's candle": "stella's candle",
                "merchant tracker": "merchant tracker",
                "random potion sack": "random potion sack",
                "gear a": "gear a",
                "Genr A": "gear a",
                "gear b": "gear b",
                "geor a": "gear a",
                "geor b": "gear b",
                "lucky potion": "lucky potion",
                "lucky penny": "lucky penny",
                "mixed potion": "mixed potion",
                "fortune spoid i": "fortune potion i",
                "fortune spoid il": "fortune potion ii",
                "fortune godid i": "fortune potion i",
                "lucky potion l": "lucky potion l",
                "lucky potion xl": "lucky potion xl",
                "speed potion": "speed potion",
                "speed potion l": "speed potion l",
                "speed potion xl": "speed potion xl",
                "oblivion potion": "oblivion potion",
                "potion of bound": "potion of bound",
                "rune of everything": "rune of everything",
                "rune of dust": "rune of dust",
                "rune of nothing": "rune of nothing",
                "rune of corruption": "rune of corruption",
                "rune of hell": "rune of hell",
                "rune of frost": "rune of frost",
                "rune of wind": "rune of wind"
            }

            if not hasattr(self, 'last_merchant_interaction'):
                self.last_merchant_interaction = 0

            if not hasattr(self, 'last_merchant_sent'):
                self.last_merchant_sent = {}

            merchant_cooldown_time = 300
            current_time = time.time()


            for _ in range(6):
                if _cancelled():
                    return
                autoit.send("e")
                if not self._sleep_with_cancel(0.55):
                    return

            if not self._sleep_with_cancel(0.65):
                return

            # Click through merchant dialogue (no hold)
            for _ in range(8):
                if _cancelled():
                    return
                autoit.mouse_click("left", merchant_dialogue_box[0], merchant_dialogue_box[1], 2, speed=2)
                if not self._sleep_with_cancel(0.55):
                    return

            if not merchant_name:
                merchant_texts = []
                for _ in range(6):
                    if _cancelled():
                        return

                    x, y, w, h = merchant_name_ocr_pos
                    texts = self.extract_text_candidates((x, y, w, h), single_pass=True)
                    merchant_texts.extend(texts)
                    merchant_name = self._consensus_ocr_match(merchant_texts, list(merchant_aliases), merchant_aliases, threshold=0.75)
            if merchant_name:
                if event_override and not fishing_override and current_time - self.last_merchant_interaction < merchant_cooldown_time:
                    print(f"Merchant {merchant_name} already interacted recently")
                    return False
                merchant_source = "logs" if known_merchant_name == merchant_name else "ocr"
                merchant_source_key = "log_routine" if merchant_source == "logs" else merchant_source
                last_sent_time = self.last_merchant_sent.get((merchant_name, merchant_source_key), 0)
                if self.config.get("merchant_ocr", False) and current_time - last_sent_time < merchant_cooldown_time:
                    print(f"Merchant {merchant_name} already sent recently lol")
                    return False

                print(f"Opening merchant interface for {merchant_name}")
                btn_pos = merchant_open_button

                autoit.mouse_click("left", btn_pos[0], btn_pos[1], 1)
                inventory_click_delay = merchant_settings["inventory_click_delay"] / 1000.0
                if not self._sleep_with_cancel(7 + inventory_click_delay): return

                screenshot_dir = os.path.join(os.getcwd(), "images")
                os.makedirs(screenshot_dir, exist_ok=True)

                item_screenshot = pyautogui.screenshot()
                screenshot_path = os.path.join(screenshot_dir,
                                               f"merchant_{merchant_name.lower()}_{int(current_time)}.png")
                item_screenshot.save(screenshot_path)

                self.last_merchant_sent[(merchant_name, merchant_source_key)] = current_time

                if "merchant_counts" not in self.config:
                    self.config["merchant_counts"] = {"Jester": 0, "Mari": 0, "Rin": 0}
                self.config["merchant_counts"][merchant_name] = self.config["merchant_counts"].get(merchant_name, 0) + 1
                self.save_config()
                if hasattr(self, "on_stats_update") and callable(self.on_stats_update):
                    self.on_stats_update()
                self.append_log(f"[Merchant Detection] {merchant_name} count: {self.config['merchant_counts'][merchant_name]}")

                merchant_settings, merchant_setting_warnings = validate_merchant_settings(self.config)
                for warning in merchant_setting_warnings:
                    self.append_log(f"[Merchant Config] {warning}")
                auto_buy_items = merchant_settings.get(f"{merchant_name}_Items", {})
                item_aliases = {name: [name] for name in auto_buy_items}
                for alias, correct in ocrMisdetect_Key.items():
                    for name in item_aliases:
                        if self._normalize_ocr_label(name) == self._normalize_ocr_label(correct):
                            item_aliases[name].append(alias)

                merchant_slot_positions = [
                    self.config.get("first_item_merchant_slot_pos", [954, 719]),
                    self.config.get("second_item_merchant_slot_pos", [1047, 719]),
                    self.config.get("third_item_merchant_slot_pos", [1140, 719]),
                    self.config.get("fourth_item_merchant_slot_pos", [1233, 719]),
                    self.config.get("fifth_item_merchant_slot_pos", [1326, 719]),
                ]

                total_slots = 5 + merchant_extra_slot
                item_texts = self.extract_text_candidates(item_name_ocr_pos, single_pass=True, log_text=False, capture="merchant_item_ocr")
                item_text = " | ".join(text for text in item_texts if text)
                self.append_log(f"[Merchant Detection - {merchant_name}] Detected shop text: {item_text}")
                resolved_items = self._match_merchant_slots(item_texts, list(item_aliases), item_aliases, strict=merchant_name == "Mari")
                self.append_log(f"[Merchant Detection - {merchant_name}] Resolved slots: {resolved_items}")
                detected_items = []

                for slot_index in range(total_slots):
                    if _cancelled():
                        return
                    if slot_index < len(merchant_slot_positions):
                        x, y = merchant_slot_positions[slot_index]
                    else:
                        base_x, base_y = merchant_slot_positions[-1]
                        extra_index = slot_index - (len(merchant_slot_positions) - 1)
                        x, y = base_x + (extra_index * 193), base_y
                    autoit.mouse_click("left", x, y, 2)
                    if not self._sleep_with_cancel(0.15):
                        return
                    corrected_item_name = resolved_items[slot_index] if slot_index < len(resolved_items) else ""
                    if slot_index >= 5:
                        slot_texts = self.extract_text_candidates(item_name_ocr_pos, single_pass=True, log_text=False, capture="merchant_item_ocr")
                        corrected_item_name = self._match_merchant_item(slot_texts, list(item_aliases), item_aliases, strict=merchant_name == "Mari")
                    if not corrected_item_name:
                        self.append_log(f"[Merchant Detection - {merchant_name}] Item label uncertain; skipping slot {slot_index}.")
                        detected_items.append(f"Slot {slot_index}: No items detected")
                        continue

                    print(f"Detected item text: {item_text} | Corrected: {corrected_item_name}")
                    matched_name = corrected_item_name
                    item_vals = auto_buy_items.get(matched_name)
                    if item_vals is None:
                        for item_name, values in auto_buy_items.items():
                            if self._normalize_ocr_label(item_name) == self._normalize_ocr_label(corrected_item_name):
                                matched_name = item_name
                                item_vals = values
                                break
                    detected_items.append(f"Slot {slot_index}: {matched_name}")
                    if item_vals is None:
                        self.append_log(f"[Merchant Detection - {merchant_name}] Item {corrected_item_name} is not configured; skipping slot {slot_index}.")
                        continue
                    enabled = bool(item_vals[0]) if len(item_vals) > 0 else False
                    if not enabled:
                        self.append_log(f"[Merchant Detection - {merchant_name}] Item {matched_name} is disabled; skipping slot {slot_index}.")
                        continue
                    quantity = int(item_vals[1]) if len(item_vals) > 1 else 1
                    buy_all = bool(item_vals[3]) if len(item_vals) > 3 else False
                    self.append_log(f"[Merchant Detection - {merchant_name}] - Item {matched_name} found. Proceeding to buy {('MAX' if buy_all else quantity)}")

                    purchase_amount_button = self.config["purchase_amount_button"]
                    purchase_button = self.config["purchase_button"]
                    if buy_all:
                        max_btn = self.config.get("autobuy_set_to_max_button", [0, 0])
                        if max_btn and max_btn[0] > 0 and max_btn[1] > 0:
                            autoit.mouse_click("left", *max_btn)
                            if not self._sleep_with_cancel(0.3):
                                return
                        else:
                            self.append_log(f"[Merchant] Set to Max button not calibrated! Falling back to typing {quantity}")
                            autoit.mouse_click("left", *purchase_amount_button)
                            self._safe_type_text(str(quantity))
                            if not self._sleep_with_cancel(0.23):
                                return
                    else:
                        autoit.mouse_click("left", *purchase_amount_button)
                        self._safe_type_text(str(quantity))
                        if not self._sleep_with_cancel(0.23):
                            return
                    autoit.mouse_click("left", *purchase_button, 3)
                    if not self._sleep_with_cancel(3.67):
                        return

                if (screenshot_path and os.path.isfile(screenshot_path)) or self.config.get("merchant_ocr", False):
                    threading.Thread(target=self.send_merchant_webhook, args=(merchant_name, screenshot_path), kwargs={"source": merchant_source, "detected_items": detected_items}, daemon=True).start()

                merchant_close_button = self.config.get("merchant_close_button", [1086, 342])
                self.Global_MouseClick(merchant_close_button[0], merchant_close_button[1], click=3)
                self.last_merchant_interaction = current_time

                return True
            else:    
                merchant_close_button = self.config.get("merchant_close_button", [1086, 342])
                self.Global_MouseClick(merchant_close_button[0], merchant_close_button[1], click=3)
                if not self._sleep_with_cancel(0.67): return False
                return False

        except Exception as e:
            self.error_logging(e,
                               "Merchant handler failed; check merchant settings and calibration.")
            return False
        finally:
            self.on_auto_merchant_state = False

    def _ocr_first_slot_matches(self, expected):
        if not self.config.get("enable_ocr_failsafe", False):
            return True
        ocr_pos = self.config.get("first_item_slot_ocr_pos", [0, 0, 80, 80])
        try:
            x, y, w, h = int(ocr_pos[0]), int(ocr_pos[1]), int(ocr_pos[2]), int(ocr_pos[3])
            texts = self.extract_text_candidates((x, y, w, h), single_pass=True)
            text = " | ".join(value for value in texts if value).lower()
            self.append_log(f"[DEBUG] ocr item first slot failsafe: '{text}'")
        except Exception as e:
            texts = []
            self.append_log(f"[DEBUG] ocr item first slot failsafe exception: {e}")
        expected_words = self._normalize_ocr_label(expected).split()
        if not expected_words or not texts:
            return False
        try:
            threshold = float(self.config.get("ocr_failsafe_match_threshold", 0.78))
        except Exception:
            threshold = 0.78
        threshold = max(0.78, min(1.0, threshold))
        word_aliases = {
            "ooy": "day", "ond": "and", "mosters": "masters", "tolismon": "talisman",
            "sock": "sack", "oust": "dust", "stronge": "strange", "rondom": "random",
            "condle": "candle", "hoste": "haste", "dvertime": "overtime", "dblivion": "oblivion",
            "df": "of", "goloxy": "galaxy", "crock": "crack", "genr": "gear", "geor": "gear",
            "henvnely": "heavenly", "heovenly": "heavenly", "stellos": "stellas", "moster": "masters"
        }
        roman_aliases = {"i": {"1"}, "ii": {"11", "ll"}, "iii": {"111", "lll", "ill"}}
        candidates = list(dict.fromkeys((expected,)))
        config = self.config if isinstance(self.config, dict) else {}
        for key in ("Mari_Items", "Jester_Items", "Rin_Items"):
            items = config.get(key, {})
            if isinstance(items, dict):
                candidates.extend(items)
        from .config import DEFAULT_AUTO_POP_BUFFS
        candidates.extend(DEFAULT_AUTO_POP_BUFFS)
        candidates.extend(("Merchant Teleporter", "Portable Crack"))
        candidates = list(dict.fromkeys(candidates))
        votes = {}
        for text in texts:
            labels = [self._normalize_ocr_label(value).split() for value in re.split(r"[|\r\n]+", str(text))]
            ranked = []
            for candidate in candidates:
                words_expected = self._normalize_ocr_label(candidate).split()
                if len(words_expected) != len(expected_words):
                    continue
                score = 0.0
                is_exact = False
                for words in labels:
                    extra = words[len(words_expected):]
                    if len(extra) == 1 and re.fullmatch(r"(?:n?x|ix)\d*", extra[0]):
                        words = words[:len(words_expected)]
                    elif len(extra) == 2 and extra[0] in ("x", "nx") and extra[1].isdigit():
                        words = words[:len(words_expected)]
                    if len(words) != len(words_expected):
                        continue
                    exact = [
                        actual == wanted
                        or word_aliases.get(actual, actual) == wanted
                        or (index == len(words) - 1 and wanted in roman_aliases and actual in roman_aliases[wanted])
                        for index, (wanted, actual) in enumerate(zip(words_expected, words))
                    ]
                    scores = [
                        1.0 if exact[index] else (
                            difflib.SequenceMatcher(None, wanted, actual).ratio()
                            if len(wanted) > 2 and len(actual) > 2 else 0.0
                        )
                        for index, (wanted, actual) in enumerate(zip(words_expected, words))
                    ]
                    current_score = sum(scores) / len(scores)
                    if current_score > score:
                        score = current_score
                        is_exact = all(exact)
                if score:
                    ranked.append((score, candidate, is_exact))
            ranked.sort(key=lambda result: (result[0], result[2]), reverse=True)
            if not ranked or ranked[0][0] < threshold:
                continue
            if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.02 and ranked[0][2] == ranked[1][2]:
                continue
            winner = ranked[0][1]
            votes[winner] = votes.get(winner, 0) + 1
        ranked_votes = sorted(votes.items(), key=lambda item: item[1], reverse=True)
        required_votes = 1 if len(texts) == 1 else 2
        matches = bool(ranked_votes) and ranked_votes[0][0] == expected and ranked_votes[0][1] >= required_votes and (len(ranked_votes) == 1 or ranked_votes[0][1] > ranked_votes[1][1])
        result = "matched" if matches else "rejected"
        self.append_log(f"[DEBUG] OCR failsafe {result} expected {expected!r}; votes={ranked_votes}")
        return matches
    def close_chat_if_open(self, force=False):
        try:
            if self.config.get("enable_idle_mode", False): return
            if not force and not self.config.get("auto_chat_close", False): return

            chat_hover = self.config.get("chat_hover_pos", [272, 252])
            chat_ocr_region = self.config.get("chat_tab_ocr_pos", [341, 83, 210, 40])
            chat_close = self.config.get("chat_close_button", [174, 40])

            if not (chat_hover and chat_hover[0] and chat_close and chat_close[0]):
                self.append_log("[RapidOCR] You haven't calibrated chat failsafe so auto close chat will not running (WARNING)")
                return

            for _ in range(3):
                self.activate_roblox_window()
                time.sleep(0.2)

            sw = pyautogui.size()
            autoit.mouse_move(sw.width // 2, sw.height // 2, speed=3)
            time.sleep(0.85)
            autoit.mouse_move(chat_hover[0], chat_hover[1], speed=3)
            time.sleep(0.85)

            chat_detected = False
            for attempt in range(1, 4):
                tab_text = self.extract_text_with_rapidocr(tuple(chat_ocr_region)).lower()
                self.append_log(f"[RapidOCR] Close Chat OCR Check ({attempt}/3): '{tab_text}'")

                if fuzzy_match_any(tab_text, ["general", "server message", "here"], threshold=0.75):
                    chat_detected = True
                    break

                if attempt < 3:
                    time.sleep(0.45)

            if chat_detected:
                self.append_log("[RapidOCR] Chat is open! Closing it...")
                autoit.mouse_click("left", chat_close[0], chat_close[1], 1, speed=3)
                time.sleep(0.45)
            else:
                self.append_log("[RapidOCR] Chat already closed! Skipping...")

        except Exception as e:
            self.error_logging(e, "close_chat_if_open error")


    def activate_roblox_window(self):
        hwnd = None
        try:
            hwnds = self._find_roblox_hwnds()
            if hwnds:
                hwnd = hwnds[0]
                self._focus_window_hwnd(hwnd, max_attempts=10, sleep_between=0.2)
        except Exception as e:
            print(f"[activate_roblox_window] hwnd path failed: {e}")

        if hwnd is None:
            # fallback
            try:
                for title in gw.getAllTitles():
                    if "Roblox" in title:
                        win = gw.getWindowsWithTitle(title)[0]
                        win.activate()
                        try:
                            hwnd = win._hWnd
                        except Exception:
                            pass
                        break
            except Exception as e:
                print(f"[activate_roblox_window] gw fallback failed: {e}")

        if hwnd is None:
            if not self.check_roblox_procs():
                print("Roblox window not found.")
            return

        self._apply_roblox_fullscreen(hwnd)

    def _apply_roblox_fullscreen(self, hwnd):
        if not self.config.get("auto_roblox_fullscreen", True):
            return False
        try:
            if win32gui.IsIconic(hwnd):
                return False
            monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
            left, top, right, bottom = win32api.GetMonitorInfo(monitor)["Monitor"]
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            fullscreen_style = (
                style
                & ~(
                    win32con.WS_CAPTION
                    | win32con.WS_THICKFRAME
                    | win32con.WS_MINIMIZEBOX
                    | win32con.WS_MAXIMIZEBOX
                    | win32con.WS_SYSMENU
                )
            ) | win32con.WS_POPUP
            bounds = (left, top, right, bottom)
            changed = style != fullscreen_style or win32gui.GetWindowRect(hwnd) != bounds
            if style != fullscreen_style:
                win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, fullscreen_style)
            if changed:
                win32gui.SetWindowPos(
                    hwnd,
                    None,
                    left,
                    top,
                    right - left,
                    bottom - top,
                    win32con.SWP_NOZORDER
                    | win32con.SWP_NOACTIVATE
                    | win32con.SWP_FRAMECHANGED
                    | win32con.SWP_SHOWWINDOW,
                )
                self.append_log(f"[Roblox] Fullscreen at {right - left}x{bottom - top}.")
            return True
        except Exception:
            return False

    def _monitor_roblox_window(self):
        stop_event = self._detection_stop_event
        while self.detection_running and not stop_event.is_set():
            if self.config.get("auto_roblox_fullscreen", True):
                try:
                    hwnds = self._find_roblox_hwnds()
                    if hwnds:
                        self._apply_roblox_fullscreen(hwnds[0])
                except Exception:
                    pass
            if stop_event.wait(1):
                return

    def _find_roblox_hwnds(self):
        pids = set()
        try:
            current_user = psutil.Process().username()
            current_user_norm = str(current_user or "").strip().lower()
        except Exception:
            current_user = None
            current_user_norm = ""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    proc_name = str(proc.info.get('name') or "")
                    if proc_name not in ['RobloxPlayerBeta.exe', 'Windows10Universal.exe']:
                        continue

                    proc_user_norm = str(proc.info.get('username') or "").strip().lower()
                    if current_user is not None and current_user_norm and proc_user_norm and proc_user_norm != current_user_norm:
                        continue

                    pid = proc.info.get('pid')
                    if pid is not None:
                        pids.add(pid)
                except Exception:
                    pass
        except Exception:
            pass

        hwnds = []
        try:
            def enum_cb(hwnd, lparam):
                try:
                    if not win32gui.IsWindowVisible(hwnd) or not win32gui.IsWindowEnabled(hwnd):
                        return True
                    tid, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid in pids:
                        hwnds.append(hwnd)
                except Exception:
                    pass
                return True

            win32gui.EnumWindows(enum_cb, None)
        except Exception:
            pass
        return hwnds

    def _focus_window_hwnd(self, hwnd, max_attempts=20, sleep_between=0.25):
        attempt = 0
        while self.detection_running and attempt < max_attempts:
            attempt += 1
            try:
                if win32gui.IsIconic(hwnd):
                    try:
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    except Exception:
                        pass
                fg = win32gui.GetForegroundWindow()
                if fg == hwnd:
                    return True
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    try:
                        fg_hwnd = win32gui.GetForegroundWindow()
                        foreground_tid = win32process.GetWindowThreadProcessId(fg_hwnd)[0]
                        target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
                        current_tid = ctypes.windll.kernel32.GetCurrentThreadId()
                        try:
                            ctypes.windll.user32.AttachThreadInput(current_tid, foreground_tid, True)
                            ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, True)
                        except Exception:
                            pass
                        try:
                            win32gui.SetForegroundWindow(hwnd)
                        except Exception:
                            pass
                        try:
                            ctypes.windll.user32.AttachThreadInput(current_tid, foreground_tid, False)
                            ctypes.windll.user32.AttachThreadInput(current_tid, target_tid, False)
                        except Exception:
                            pass
                    except Exception:
                        pass
                time.sleep(sleep_between)
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
                try:
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        try:
                            autoit.win_activate(title)
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(sleep_between)
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
                try:
                    pyautogui.keyDown('alt')
                    pyautogui.press('tab')
                    pyautogui.keyUp('alt')
                except Exception:
                    pass
                time.sleep(sleep_between)
                if win32gui.GetForegroundWindow() == hwnd:
                    return True
            except Exception:
                pass
        return win32gui.GetForegroundWindow() == hwnd

    def perform_anti_afk_action(self):
        try:
            if not getattr(self, "anti_afk_var", None) or not self.anti_afk_var.get():
                return

            while self.detection_running and not self._detection_stop_event.is_set():
                if not getattr(self, "anti_afk_var", None) or not self.anti_afk_var.get():
                    return

                if not self.check_roblox_procs():
                    if self._detection_stop_event.wait(1.0):
                        return
                    continue

                target = None
                while self.detection_running and not self._detection_stop_event.is_set() and not target:
                    roblox_hwnds = self._find_roblox_hwnds()
                    if not roblox_hwnds:
                        for t in gw.getAllTitles():
                            if "Roblox" in (t or ""):
                                wins = gw.getWindowsWithTitle(t)
                                if wins:
                                    try:
                                        if hasattr(wins[0], '_hWnd'):
                                            roblox_hwnds.append(wins[0]._hWnd)
                                        else:
                                            h = win32gui.FindWindow(None, t)
                                            if h:
                                                roblox_hwnds.append(h)
                                    except Exception:
                                        pass
                    if roblox_hwnds:
                        target = roblox_hwnds[0]
                        break
                    if self._detection_stop_event.wait(1.0):
                        return

                if not self.detection_running:
                    return

                try:
                    hwnd_before = win32gui.GetForegroundWindow()
                except Exception:
                    hwnd_before = None
                try:
                    title_before = win32gui.GetWindowText(hwnd_before) if hwnd_before else ""
                except Exception:
                    title_before = ""

                was_roblox_focused = bool(hwnd_before and hwnd_before in roblox_hwnds)
                if not was_roblox_focused and hwnd_before:
                    try:
                        current_title = win32gui.GetWindowText(hwnd_before)
                        if "Roblox" in (current_title or ""):
                            was_roblox_focused = True
                    except Exception:
                        pass

                focused = False
                while self.detection_running and not self._detection_stop_event.is_set() and not focused:
                    focused = self._focus_window_hwnd(target, max_attempts=4, sleep_between=0.35)
                    if focused:
                        break
                    refreshed_hwnds = self._find_roblox_hwnds()
                    if refreshed_hwnds:
                        target = refreshed_hwnds[0]
                    if self._detection_stop_event.wait(0.35):
                        return

                if not self.detection_running:
                    return
                if not focused:
                    continue

                jumps_done = 0
                while self.detection_running and not self._detection_stop_event.is_set() and jumps_done < 1:
                    if win32gui.GetForegroundWindow() != target:
                        focused = False
                        while self.detection_running and not self._detection_stop_event.is_set() and not focused:
                            focused = self._focus_window_hwnd(target, max_attempts=4, sleep_between=0.35)
                            if focused:
                                break
                            refreshed_hwnds = self._find_roblox_hwnds()
                            if refreshed_hwnds:
                                target = refreshed_hwnds[0]
                            if self._detection_stop_event.wait(0.35):
                                return
                        if not self.detection_running:
                            return
                        if not focused:
                            continue

                    jump_success = False
                    try:
                        autoit.send("{SPACE}")
                        jump_success = True
                    except Exception:
                        pass

                    if not jump_success:
                        try:
                            pyautogui.keyDown("space")
                            if self._detection_stop_event.wait(0.04):
                                return
                            pyautogui.keyUp("space")
                            jump_success = True
                        except Exception:
                            pass

                    if jump_success:
                        jumps_done += 1
                        try:
                            self.append_log(f"[Anti-AFK] Jump {jumps_done}/1")
                        except Exception:
                            pass
                        if self._detection_stop_event.wait(0.28):
                            return
                    else:
                        if self._detection_stop_event.wait(0.2):
                            return

                if jumps_done == 1:
                    if was_roblox_focused:
                        return

                    if not hwnd_before:
                        return

                    # Return focus to previous window, but less aggressively
                    try:
                        if win32gui.IsWindow(hwnd_before):
                            win32gui.SetForegroundWindow(hwnd_before)
                    except Exception:
                        pass
                    return
        except Exception as e:
            try:
                self.error_logging(e, "Error in anti-afk")
            except Exception:
                pass

    def anti_afk_loop(self):
        wake = self._anti_afk_wake_event
        while self.detection_running:
            try:
                interval_min = float(self.anti_afk_interval_var.get())
            except Exception:
                interval_min = 5.0
            interval_min = max(1.0, min(20.0, interval_min))
            wake.wait(interval_min * 60.0)
            wake.clear()
            if not self.detection_running or self._detection_stop_event.is_set():
                break
            if not self.anti_afk_var.get() or self.is_fishing_mode_enabled():
                continue
            try:
                if getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False):
                    continue
                self.perform_anti_afk_action()
            except Exception as e:
                try:
                    self.error_logging(e, "Error in anti_afk_loop")
                except Exception:
                    pass
    def autoit_hold_left_click(self, posX, posY, holdTime=1):
        for _ in range(5):
            autoit.mouse_click("left", posX, posY, 2, speed=2)
            time.sleep(0.1)

    def get_scaled_coordinates(self, original_x, original_y):
        original_width = 1920
        original_height = 1080
        current_width, current_height = pyautogui.size()

        x_scale = current_width / original_width
        y_scale = current_height / original_height
        return int(original_x * x_scale), int(original_y * y_scale)

    def _get_auto_pop_biome_entry(self, biome_name):
        try:
            all_biomes = self.config.get("auto_pop_biomes", {})
            if not isinstance(all_biomes, dict):
                return {"enabled": False, "buffs": {}}
            entry = all_biomes.get(biome_name, {})
            if not isinstance(entry, dict):
                return {"enabled": False, "buffs": {}}
            buffs = entry.get("buffs", {})
            if not isinstance(buffs, dict):
                buffs = {}
            return {
                "enabled": bool(entry.get("enabled", False)),
                "buffs": buffs,
            }
        except Exception:
            return {"enabled": False, "buffs": {}}

    def _build_auto_pop_buffs_to_use(self, buff_config):
        buffs_to_use = []
        priority_order = [
            "Xyz Potion",
            "Transcendent Potion",
            "Warp Potion",
            "Rune of Everything",
            "Heavenly Potion",
            "Godlike Potion",
            "Potion of bound",
            "Oblivion Potion",
        ]

        if not isinstance(buff_config, dict):
            return buffs_to_use

        def _read_buff_state(raw_value):
            try:
                if isinstance(raw_value, (list, tuple)) and len(raw_value) >= 2:
                    return bool(raw_value[0]), max(1, int(raw_value[1]))
            except Exception:
                pass
            return False, 1

        for buff_name in priority_order:
            enabled, amount = _read_buff_state(buff_config.get(buff_name))
            if enabled:
                buffs_to_use.append((buff_name, amount))

        for buff_name, raw_value in buff_config.items():
            if buff_name in priority_order:
                continue
            enabled, amount = _read_buff_state(raw_value)
            if enabled:
                buffs_to_use.append((buff_name, amount))

        return buffs_to_use

    def auto_pop_buffs_for_current_biome(self, target_biome=None):
        if not self.detection_running or self._detection_stop_event.is_set():
            return
        if target_biome is None:
            target_biome = self.current_biome
        try:
            self._action_scheduler.enqueue_action(
                lambda: self._auto_pop_buffs_for_current_biome_impl(target_biome=target_biome),
                name="auto_pop_current_biome",
                priority=0,
            )
        except Exception:
            try:
                self._auto_pop_buffs_for_current_biome_impl(target_biome=target_biome)
            except Exception:
                pass

    def _auto_pop_buffs_for_current_biome_impl(self, target_biome=None):
        if not self.detection_running or self._detection_stop_event.is_set():
            return
        self.auto_pop_state = True

        def waitcancel(seconds):
            end = time.monotonic() + max(0.0, float(seconds))
            while time.monotonic() < end:
                if not self.detection_running or self._detection_stop_event.is_set() or self.reconnecting_state:
                    return False
                if self._detection_stop_event.wait(min(0.05, end - time.monotonic())):
                    return False
            return self.detection_running and not self._detection_stop_event.is_set() and not self.reconnecting_state
        if target_biome is None:
            target_biome = self.current_biome
        try:
            if not target_biome or target_biome == "NORMAL": return
            if self.config.get("enable_idle_mode", False): return
            if getattr(self, "enable_potion_crafting_var", None) and self.enable_potion_crafting_var.get(): return

            biome_entry = self._get_auto_pop_biome_entry(target_biome)
            if not biome_entry.get("enabled", False): return

            buffs_to_use = self._build_auto_pop_buffs_to_use(biome_entry.get("buffs", {}))
            if not buffs_to_use: return

            inventory_click_delay = int(self.config.get("inventory_click_delay", "0")) / 1000.0
            warp_enabled = any(buff in ("Warp Potion", "Transcendent Potion") for buff, _ in buffs_to_use)

            if (
                self.is_fishing_mode_enabled()
                or bool(getattr(self, "on_auto_merchant_state", False))
                or bool(getattr(self, "_mt_running", False))
                or bool(getattr(self, "_br_sc_running", False))
                or bool((getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)))
            ):
                self.append_log(f"[Auto Pop] Waiting for other actions to finish before popping buffs")
                wait_deadline = time.monotonic() + 50
                while time.monotonic() < wait_deadline:
                    if not self.detection_running or self.reconnecting_state: return
                    if self.current_biome != target_biome: return
                    still_busy = (
                        bool(getattr(self, "_fishing_busy", False))
                        or bool(getattr(self, "on_auto_merchant_state", False))
                        or bool(getattr(self, "_mt_running", False))
                        or bool(getattr(self, "_br_sc_running", False))
                        or bool((getattr(self, "_egg_collecting", False) or getattr(self, "_eden_running", False) or getattr(self, "_potion_thread_active", False)))
                    )
                    if not still_busy: break
                    if not waitcancel(0.55): return
                if not waitcancel(0.5): return

            for buff, amount in buffs_to_use:
                if not self.detection_running or self.reconnecting_state: return
                if self.current_biome != target_biome:
                    self.append_log(f"[Auto Pop] Biome changed to {self.current_biome}, stopping auto pop...")
                    self.send_webhook_status(
                        f"Biome changed to {self.current_biome}, stopping auto pop...",
                        color=0x34ebab,
                    )
                    return

                self.append_log(f"[Auto Pop] Preparing {buff} x{amount} in {target_biome}")

                additional_wait_time = 0
                if buff == "Oblivion Potion":
                    additional_wait_time = 0.85 * amount
                    if warp_enabled:
                        additional_wait_time *= 0.12

                for _ in range(5):
                    if not self.detection_running or self.reconnecting_state:
                        return
                    self.activate_roblox_window()
                    if not waitcancel(0.35): return

                if not waitcancel(0.57): return

                inventory_menu = self.config.get("inventory_menu", [36, 535])
                inventory_close_button = self.config.get("inventory_close_button", [1418, 298])
                items_tab = self.config.get("items_tab", [1272, 329])
                search_bar = self.config.get("search_bar", [855, 358])
                first_item_slot = self.config.get("first_item_inventory_slot_pos", [845, 460])
                amount_box = self.config.get("amount_box", [594, 570])
                use_button = self.config.get("use_button", [710, 573])

                self.Global_MouseClick(inventory_menu[0], inventory_menu[1])
                if not waitcancel(0.22 + inventory_click_delay): return
                self.Global_MouseClick(items_tab[0], items_tab[1])
                if not waitcancel(0.22 + inventory_click_delay): return
                self.Global_MouseClick(search_bar[0], search_bar[1], click=2)
                if not waitcancel(0.23 + inventory_click_delay): return

                if not self.detection_running or self.reconnecting_state:
                    return
                if self.current_biome != target_biome:
                    self.append_log(f"[Auto Pop] Biome changed mid-inventory, closing and stopping")
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    if not waitcancel(0.15 + inventory_click_delay): return
                    return

                self._safe_type_text(buff.lower())
                if not waitcancel(0.22 + inventory_click_delay): return
                self.Global_MouseClick(first_item_slot[0], first_item_slot[1])
                if not waitcancel(0.22 + inventory_click_delay): return

                try:
                    if not self._ocr_first_slot_matches(buff):
                        self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                        if not waitcancel(0.15 + inventory_click_delay): return
                        continue
                except Exception as e:
                    self.append_log(f"[OCR Failsafe] Validation failed for {buff}: {e}; skipping item use.")
                    self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                    if not waitcancel(0.15 + inventory_click_delay): return
                    continue

                self.Global_MouseClick(amount_box[0], amount_box[1])
                if not waitcancel(0.22 + inventory_click_delay): return

                if not self.detection_running or self.reconnecting_state:
                    return

                autoit.send("^{a}")
                if not waitcancel(0.285 + inventory_click_delay): return
                autoit.send("{BACKSPACE}")
                if not waitcancel(0.285 + inventory_click_delay): return
                self._safe_type_text(str(amount))
                if not waitcancel(0.285 + inventory_click_delay): return

                self.Global_MouseClick(use_button[0], use_button[1])
                if not waitcancel(0.3 + inventory_click_delay): return

                self.append_log(f"[Auto Pop] Used {buff} x{amount} in {target_biome}")
                self.send_webhook_status(f"Used x{amount} {buff} in {target_biome}", color=0x34ebab)

                self.Global_MouseClick(inventory_close_button[0], inventory_close_button[1])
                if not waitcancel(0.32 + inventory_click_delay): return

                if additional_wait_time > 0:
                    if not waitcancel(additional_wait_time): return

        except Exception as e:
            self.error_logging(e, "Error in auto_pop_buffs_for_current_biome function")
        finally:
            self.auto_pop_state = False

    def auto_pop_buffs(self):
        self.auto_pop_buffs_for_current_biome()

    def auto_pop_buffs_individual(self):
        self.auto_pop_buffs_for_current_biome()
