"""Build the small JSON data files bundled with the stash tool.

Sources:
  * D2 1.14d item stat / item type data (via squeek502/d2itemreader's bundled defaults)
  * D2R base text files (via pinkufairy/D2R-Excel); base item codes and grid sizes are
    unchanged from the 1.13/1.14 data used by PlugY.

This script is for development only.  The generated files live in data/ and are
what the application actually loads.

To regenerate the data, place these files in the repository root:
  d2_armor.txt, d2_weapons.txt, d2_misc.txt, d2_uniqueitems.txt,
  d2_setitems.txt, d2gamedata_default.txt
They are not shipped with the application.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)


def read_tsv(name: str) -> list[dict[str, str]]:
    with open(ROOT / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def intval(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# ItemStatCost: bit layout of every stat that can appear on a saved item.
# ---------------------------------------------------------------------------
def build_stats() -> list[dict]:
    text = (ROOT / "d2gamedata_default.txt").read_text(encoding="utf-8")
    body = re.search(r"d2gamedata_default_itemstats\[\] = \{(.*?)\};", text, re.S)
    if not body:
        raise SystemExit("itemstat array not found")
    rows = re.findall(
        r"\{(\d+), (\d+), (\d+), (-?\d+), (\d+), (\d+), (\d+)\}", body.group(1)
    )
    stats = []
    for row in rows:
        sid, encode, save_bits, save_add, param_bits, next_id, char_bits = map(int, row)
        stats.append(
            {
                "id": sid,
                "encode": encode,
                "bits": save_bits,
                "add": save_add,
                "param_bits": param_bits,
                "next": next_id,
            }
        )
    if len(stats) != 359:
        raise SystemExit(f"unexpected stat count {len(stats)}")
    return stats


# ---------------------------------------------------------------------------
# Base item types
# ---------------------------------------------------------------------------
def build_items() -> dict:
    items: dict[str, dict] = {}
    for filename, kind in (
        ("d2_armor.txt", "armor"),
        ("d2_weapons.txt", "weapon"),
        ("d2_misc.txt", "misc"),
    ):
        for row in read_tsv(filename):
            code = (row.get("code") or "").strip()
            if not code:
                continue
            # Later tables do not normally overwrite earlier ones, but keep the
            # first entry if a code is repeated (gld etc. only live in misc).
            if code in items:
                continue
            width = intval(row.get("invwidth", ""), 1)
            height = intval(row.get("invheight", ""), 1)
            if width <= 0:
                width = 1
            if height <= 0:
                height = 1
            stackable = intval(row.get("stackable", ""), 0) != 0
            entry = {
                "name": (row.get("name") or code).strip(),
                "w": width,
                "h": height,
                "kind": kind,
                "stackable": stackable,
                "req_str": intval(row.get("reqstr", "")),
                "req_dex": intval(row.get("reqdex", "")),
                "req_level": intval(row.get("levelreq", "")),
            }
            if kind == "weapon":
                entry.update(
                    {
                        "min_damage": intval(row.get("mindam", "")),
                        "max_damage": intval(row.get("maxdam", "")),
                        "two_hand": intval(row.get("2handed", "")) != 0,
                        "two_min": intval(row.get("2handmindam", "")),
                        "two_max": intval(row.get("2handmaxdam", "")),
                    }
                )
            elif kind == "armor":
                entry.update(
                    {
                        "min_ac": intval(row.get("minac", "")),
                        "max_ac": intval(row.get("maxac", "")),
                        "block": intval(row.get("block", "")),
                    }
                )
            items[code] = entry
    # A few saved-only / quest entries that do not need a grid footprint.
    items.setdefault("ear", {"name": "Ear", "w": 1, "h": 1, "kind": "misc", "stackable": False})
    return items


# ---------------------------------------------------------------------------
# Unique / set display names.  The *ID columns are the IDs stored in the item.
# ---------------------------------------------------------------------------
def build_names() -> tuple[dict, dict]:
    uniques = {}
    for row in read_tsv("d2_uniqueitems.txt"):
        try:
            uid = int(row["*ID"])
        except (KeyError, ValueError):
            continue
        uniques[str(uid)] = row.get("index", "").strip()
    set_items = {}
    for row in read_tsv("d2_setitems.txt"):
        try:
            sid = int(row["*ID"])
        except (KeyError, ValueError):
            continue
        set_items[str(sid)] = row.get("index", "").strip()
    return uniques, set_items


def main() -> None:
    stats = build_stats()
    items = build_items()
    uniques, set_items = build_names()

    (OUT / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (OUT / "items.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8"
    )
    (OUT / "names.json").write_text(
        json.dumps(
            {"unique": uniques, "set": set_items}, ensure_ascii=False, separators=(",", ":")
        ),
        encoding="utf-8",
    )
    print(f"stats={len(stats)} items={len(items)} uniques={len(uniques)} setitems={len(set_items)}")


if __name__ == "__main__":
    main()
