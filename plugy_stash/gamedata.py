"""Bundled Diablo II item metadata."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class StatInfo:
    id: int
    encode: int
    bits: int
    add: int
    param_bits: int
    next: int


@dataclass(frozen=True)
class ItemType:
    code: str
    name: str
    width: int
    height: int
    kind: str
    stackable: bool
    min_damage: int = 0
    max_damage: int = 0
    two_hand: bool = False
    two_min: int = 0
    two_max: int = 0
    min_ac: int = 0
    max_ac: int = 0
    block: int = 0
    req_str: int = 0
    req_dex: int = 0
    req_level: int = 0


class GameData:
    def __init__(self) -> None:
        raw_stats = json.loads((DATA_DIR / "stats.json").read_text(encoding="utf-8"))
        self.stats: dict[int, StatInfo] = {
            s["id"]: StatInfo(**s) for s in raw_stats
        }
        raw_items = json.loads((DATA_DIR / "items.json").read_text(encoding="utf-8"))
        self.items: dict[str, ItemType] = {
            code: ItemType(
                code=code,
                name=info["name"],
                width=info["w"],
                height=info["h"],
                kind=info["kind"],
                stackable=info["stackable"],
                min_damage=info.get("min_damage", 0),
                max_damage=info.get("max_damage", 0),
                two_hand=info.get("two_hand", False),
                two_min=info.get("two_min", 0),
                two_max=info.get("two_max", 0),
                min_ac=info.get("min_ac", 0),
                max_ac=info.get("max_ac", 0),
                block=info.get("block", 0),
                req_str=info.get("req_str", 0),
                req_dex=info.get("req_dex", 0),
                req_level=info.get("req_level", 0),
            )
            for code, info in raw_items.items()
        }
        names = json.loads((DATA_DIR / "names.json").read_text(encoding="utf-8"))
        self.unique_names: dict[str, str] = names["unique"]
        self.set_item_names: dict[str, str] = names["set"]

        self.zh_items: dict[str, str] = json.loads(
            (DATA_DIR / "zh_items.json").read_text(encoding="utf-8")
        )
        raw_desc = json.loads((DATA_DIR / "stat_desc.json").read_text(encoding="utf-8"))
        self.stat_desc: dict[int, dict] = {entry["id"]: entry for entry in raw_desc}
        self.affixes: dict = json.loads((DATA_DIR / "affixes.json").read_text(encoding="utf-8"))
        self.skills: dict = json.loads((DATA_DIR / "skills.json").read_text(encoding="utf-8"))

    def item(self, code: str) -> ItemType:
        found = self.items.get(code)
        if found is not None:
            return found
        return ItemType(code=code, name=code or "?", width=1, height=1, kind="misc", stackable=False)

    def is_armor(self, code: str) -> bool:
        item = self.items.get(code)
        return item is not None and item.kind == "armor"

    def is_weapon(self, code: str) -> bool:
        item = self.items.get(code)
        return item is not None and item.kind == "weapon"

    def is_stackable(self, code: str) -> bool:
        item = self.items.get(code)
        return item is not None and item.stackable


@lru_cache(maxsize=1)
def game_data() -> GameData:
    return GameData()
