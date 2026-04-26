
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any
import os as _os
import tempfile as _tempfile
import threading as _threading

_config_lock = _threading.Lock()

def get_base_path() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

BASE_PATH = get_base_path()
EXE_CONFIG = BASE_PATH / "config.json"
DEV_CONFIG_DIR = BASE_PATH / "config_folder"
DEV_CONFIG = DEV_CONFIG_DIR / "config.json"

DEFAULT_AUTO_POP_BUFFS = [
    "Fortune Potion I",
    "Fortune Potion II",
    "Fortune Potion III",
    "Godlike Potion",
    "Haste Potion I",
    "Haste Potion II",
    "Haste Potion III",
    "Heavenly Potion",
    "Lucky Potion",
    "Oblivion Potion",
    "Potion of bound",
    "Speed Potion",
    "Stella's Candle",
    "Strange Potion I",
    "Strange Potion II",
    "Transcendent Potion",
    "Warp Potion",
    "Xyz Potion",
]

DEFAULT_AUTO_POP_BIOMES = [
    "WINDY",
    "RAINY",
    "SNOWY",
    "SAND STORM",
    "HELL",
    "STARFALL",
    "CORRUPTION",
    "NULL",
    "GLITCHED",
    "DREAMSPACE",
    "CYBERSPACE",
    "AURORA",
    "HEAVEN",
]

RARE_BIOMES = {"GLITCHED", "DREAMSPACE", "CYBERSPACE"}


def _coerce_auto_pop_amount(value: Any) -> int:
    try:
        return max(1, int(value))
    except Exception:
        return 1


def _normalize_auto_pop_buff_map(raw: Any) -> dict[str, list[Any]]:
    normalized: dict[str, list[Any]] = {
        buff_name: [False, 1] for buff_name in DEFAULT_AUTO_POP_BUFFS
    }
    if not isinstance(raw, dict):
        return normalized

    for buff_name, buff_value in raw.items():
        if not isinstance(buff_name, str) or not buff_name.strip():
            continue

        enabled = False
        amount = 1
        if isinstance(buff_value, (list, tuple)):
            if len(buff_value) >= 1:
                enabled = bool(buff_value[0])
            if len(buff_value) >= 2:
                amount = _coerce_auto_pop_amount(buff_value[1])
        elif isinstance(buff_value, dict):
            enabled = bool(buff_value.get("enabled", False))
            amount = _coerce_auto_pop_amount(buff_value.get("amount", 1))
        else:
            enabled = bool(buff_value)

        normalized[buff_name] = [enabled, amount]

    return normalized


def normalize_auto_pop_biomes(
    config_data: dict[str, Any],
    biome_names: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    names: list[str] = []
    seen: set[str] = set()

    if biome_names:
        for biome_name in biome_names:
            if isinstance(biome_name, str) and biome_name and biome_name != "NORMAL" and biome_name not in seen:
                seen.add(biome_name)
                names.append(biome_name)

    biome_counts = config_data.get("biome_counts", {})
    if isinstance(biome_counts, dict):
        for biome_name in biome_counts.keys():
            if isinstance(biome_name, str) and biome_name and biome_name != "NORMAL" and biome_name not in seen:
                seen.add(biome_name)
                names.append(biome_name)

    biome_notifier = config_data.get("biome_notifier", {})
    if isinstance(biome_notifier, dict):
        for biome_name in biome_notifier.keys():
            if isinstance(biome_name, str) and biome_name and biome_name != "NORMAL" and biome_name not in seen:
                seen.add(biome_name)
                names.append(biome_name)

    for biome_name in DEFAULT_AUTO_POP_BIOMES:
        if biome_name not in seen:
            seen.add(biome_name)
            names.append(biome_name)

    raw_auto_pop_biomes = config_data.get("auto_pop_biomes", {})
    if isinstance(raw_auto_pop_biomes, dict) and raw_auto_pop_biomes:
        normalized: dict[str, dict[str, Any]] = {}
        for biome_name in names:
            entry = raw_auto_pop_biomes.get(biome_name, {})
            if not isinstance(entry, dict):
                entry = {}
            normalized[biome_name] = {
                "enabled": bool(entry.get("enabled", False)),
                "buffs": _normalize_auto_pop_buff_map(entry.get("buffs", {})),
            }
        for biome_name, entry in raw_auto_pop_biomes.items():
            if (
                isinstance(biome_name, str)
                and biome_name
                and biome_name != "NORMAL"
                and biome_name not in normalized
            ):
                if not isinstance(entry, dict):
                    entry = {}
                normalized[biome_name] = {
                    "enabled": bool(entry.get("enabled", False)),
                    "buffs": _normalize_auto_pop_buff_map(entry.get("buffs", {})),
                }
        return normalized

    rare_template = _normalize_auto_pop_buff_map(config_data.get("auto_buff_glitched", {}))
    non_rare_template = _normalize_auto_pop_buff_map(config_data.get("auto_buff_individual_biome", {}))
    non_rare_enabled = bool(config_data.get("auto_pop_individual_biomes", False))
    non_rare_list = config_data.get("individual_biome_pop_list", {})
    if not isinstance(non_rare_list, dict):
        non_rare_list = {}

    normalized: dict[str, dict[str, Any]] = {}
    for biome_name in names:
        if biome_name in RARE_BIOMES:
            enabled = bool(config_data.get(f"auto_pop_{biome_name.lower()}", False))
            buffs = copy.deepcopy(rare_template)
            if biome_name == "CYBERSPACE" and bool(config_data.get("cyberspace_only_warp", False)):
                for buff_name in list(buffs.keys()):
                    if buff_name not in {"Warp Potion", "Transcendent Potion"}:
                        buffs[buff_name][0] = False
        else:
            enabled = non_rare_enabled and bool(non_rare_list.get(biome_name, False))
            buffs = copy.deepcopy(non_rare_template)

        normalized[biome_name] = {
            "enabled": enabled,
            "buffs": buffs,
        }

    return normalized

def get_config_file() -> Path:
    return EXE_CONFIG


def ensure_workspace_files() -> None:
    (BASE_PATH / "resources").mkdir(exist_ok=True)
    (BASE_PATH / "resources" / "paths").mkdir(parents=True, exist_ok=True)
    (BASE_PATH / "paths").mkdir(exist_ok=True)
    (BASE_PATH / "logs").mkdir(exist_ok=True)
    (BASE_PATH / "images").mkdir(exist_ok=True)
    
    if not getattr(sys, 'frozen', False):
        DEV_CONFIG_DIR.mkdir(exist_ok=True)

    config_file = get_config_file()
    if not config_file.exists():
        default = {}
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(json.dumps(default, indent=4) + "\n", encoding="utf-8")


def sync_config() -> None:
    pass


def load_config() -> dict[str, Any]:
    ensure_workspace_files()
    with _config_lock:
        try:
            config_file = get_config_file()
            raw = config_file.read_text(encoding="utf-8").strip()
            if not raw:
                return {}
            data = json.loads(raw)
            if isinstance(data, dict):
                data["auto_pop_biomes"] = normalize_auto_pop_biomes(data)
                return data
            return {}
        except Exception:
            return {}

def save_config(config_data: dict[str, Any]) -> None:
    with _config_lock:
        try:
            config_file = get_config_file()
            current_config = {}
            if config_file.exists():
                try:
                    raw = config_file.read_text(encoding="utf-8").strip()
                    if raw:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict):
                            current_config = parsed
                except Exception:
                    pass

            current_config.update(config_data)
            current_config["auto_pop_biomes"] = normalize_auto_pop_biomes(current_config)
            tmp_fd, tmp_path = _tempfile.mkstemp(
                dir=str(config_file.parent), suffix=".tmp", prefix="config_"
            )
            try:
                with _os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(current_config, f, indent=4)
                    f.write("\n")
                    f.flush()
                    _os.fsync(f.fileno())
                _os.replace(tmp_path, str(config_file))
            except Exception:
                try:
                    _os.unlink(tmp_path)
                except Exception:
                    pass
                raise
        except Exception as e:
            print(f"Failed to save config: {e}")