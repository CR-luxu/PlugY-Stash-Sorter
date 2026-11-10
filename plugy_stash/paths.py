"""Locate Diablo II / PlugY save folders and remember UI preferences."""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "PlugYStashSorter"


def config_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_NAME / "config.json"


def load_config() -> dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(data: dict) -> None:
    try:
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


def _registry_save_paths() -> list[Path]:
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []
    found: list[Path] = []
    for root, key_name in (
        (winreg.HKEY_CURRENT_USER, r"Software\Blizzard Entertainment\Diablo II"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Blizzard Entertainment\Diablo II"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Blizzard Entertainment\Diablo II"),
    ):
        try:
            with winreg.OpenKey(root, key_name) as key:
                for value_name in ("Save Path", "Install Path", "save path"):
                    try:
                        value, _ = winreg.QueryValueEx(key, value_name)
                    except OSError:
                        continue
                    if value:
                        p = Path(str(value))
                        found.append(p)
                        found.append(p / "save")
                        found.append(p / "Save")
        except OSError:
            continue
    return found


def candidate_save_dirs() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Saved Games" / "Diablo II",
        home / "Saved Games" / "Diablo II" / "save",
        home / "Documents" / "Diablo II" / "save",
        home / "Documents" / "Diablo II" / "Save",
        home / "Documents" / "My Games" / "Diablo II",
        Path(r"C:\Program Files (x86)\Diablo II\save"),
        Path(r"C:\Program Files\Diablo II\save"),
        Path(r"D:\Diablo II\save"),
        Path(r"D:\Games\Diablo II\save"),
        Path(r"D:\游戏\暗黑破坏神2\save"),
        Path(r"D:\游戏\暗黑2\save"),
    ]
    candidates.extend(_registry_save_paths())
    seen: set[str] = set()
    result: list[Path] = []
    for p in candidates:
        try:
            key = str(p.resolve()).lower()
        except OSError:
            continue
        if key in seen:
            continue
        seen.add(key)
        if p.is_dir():
            result.append(p)
    return result


def find_stash_files() -> list[Path]:
    found: list[Path] = []
    seen: set[str] = set()
    for folder in candidate_save_dirs():
        try:
            entries = list(folder.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_file() and entry.suffix.lower() in (".sss", ".d2x"):
                key = str(entry).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(entry)
    # Some installations keep the stash inside a subfolder.
    for folder in candidate_save_dirs():
        try:
            for entry in folder.glob("*/*.sss"):
                key = str(entry).lower()
                if key not in seen:
                    seen.add(key)
                    found.append(entry)
        except OSError:
            pass
    return sorted(found)
