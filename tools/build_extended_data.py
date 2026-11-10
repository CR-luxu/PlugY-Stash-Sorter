"""Generate item-name / affix / stat-description data used by the detail view.

Development inputs (not shipped):
  d2_itemstatcost.txt, string_full.txt, tr_affixes.json, items.json,
  d2_magicprefix.txt, d2_magicsuffix.txt, d2_rareprefix.txt,
  d2_raresuffix.txt, d2_runes.txt, d2_skills.txt

The output files live in data/.
"""
from __future__ import annotations

import csv
import ctypes
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)


def simplify(text: str) -> str:
    """Traditional -> Simplified Chinese using the Windows locale API."""
    if not text:
        return ""
    try:
        k32 = ctypes.windll.kernel32
    except AttributeError:
        return text
    flag = 0x02000000  # LCMAP_SIMPLIFIED_CHINESE
    size = k32.LCMapStringEx("zh-CN", flag, text, len(text), None, 0, None, None, 0)
    if size <= 0:
        return text
    buf = ctypes.create_unicode_buffer(size + 1)
    k32.LCMapStringEx("zh-CN", flag, text, len(text), buf, size + 1, None, None, 0)
    # A few Taiwan-only variants are not folded by LCMapStringEx.
    extra = str.maketrans(
        {
            "後": "后",
            "於": "于",
            "與": "与",
            "為": "为",
            "這": "这",
            "來": "来",
            "時": "时",
            "間": "间",
            "發": "发",
            "現": "现",
            "點": "点",
            "數": "数",
            "質": "质",
            "傷": "伤",
            "強": "强",
            "擊": "击",
            "竊": "窃",
            "電": "电",
            "體": "体",
            "禦": "御",
            "復": "复",
            "獲": "获",
            "經": "经",
            "驗": "验",
            "幣": "币",
            "尋": "寻",
            "機": "机",
            "無": "无",
            "凍": "冻",
            "結": "结",
            "敵": "敌",
            "轉": "转",
            "麼": "么",
            "樣": "样",
            "對": "对",
            "還": "还",
            "沒": "没",
            "說": "说",
            "覺": "觉",
            "應": "应",
            "該": "该",
            "會": "会",
            "實": "实",
            "際": "际",
            "隻": "只",
            "幾": "几",
            "頭": "头",
            "長": "长",
            "門": "门",
            "風": "风",
            "雲": "云",
            "龍": "龙",
            "鳳": "凤",
            "龜": "龟",
            "齒": "齿",
        }
    )
    return buf.value.translate(extra)


def read_tsv(name: str) -> list[dict[str, str]]:
    with open(ROOT / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def read_string_table() -> dict[str, str]:
    table: dict[str, str] = {}
    for line in (ROOT / "string_full.txt").read_text(encoding="cp1252", errors="replace").splitlines():
        if "\t" in line:
            key, value = line.split("\t", 1)
            table[key] = value.replace("}", "")
    return table


def candidate_templates(text: str, descfunc: str, stat_name: str) -> list[str]:
    text = text.rstrip("}").strip()
    if not text:
        return []
    per_level = stat_name.endswith("_perlevel") or stat_name.endswith("_bytime")
    suffix = " (Based on Character Level)" if per_level else ""
    t = text
    candidates = [
        f"+{{{{value}}}} {t}{suffix}",
        f"{{{{value}}}}% {t}{suffix}",
        f"{t} +{{{{value}}}}%{suffix}",
        f"{t} +{{{{value}}}}{suffix}",
        f"{t} {{{{value}}}}%{suffix}",
        f"{t} {{{{value}}}}{suffix}",
        f"-{{{{value}}}}% {t}{suffix}",
        f"+{{{{value}}}}% {t}{suffix}",
        f"{{{{value}}}} {t}{suffix}",
        f"{t}{suffix}",
        f"+{{{{value}}}} {t} (Based on Character Level)",
        f"+{{{{value}}}}% {t} (Based on Character Level)",
        f"{{{{value}}}}% {t} (Based on Character Level)",
        f"{t} +{{{{value}}}} (Based on Character Level)",
        f"{t} +{{{{value}}}}% (Based on Character Level)",
        f"{{{{value}}}}% {t} (Based on Character Level)",
    ]
    if descfunc == "13":
        candidates = [f"+{{{{value}}}} {t}", f"{t} +{{{{value}}}}"] + candidates
    elif descfunc == "14":
        candidates = [f"+{{{{value}}}} {t}", f"{t} +{{{{value}}}}"] + candidates
    elif descfunc == "5":
        candidates = [f"{t} +{{{{value}}}}%", f"{t} +{{{{value}}}}"] + candidates
    elif descfunc == "12":
        candidates = [f"{t} +{{{{value}}}}", f"{t} {{{{value}}}}%"] + candidates
    elif descfunc == "29":
        candidates = [f"{t} {{{{value}}}}%", f"{t} +{{{{value}}}}%"] + candidates
    elif descfunc == "16":
        candidates = [f"Level {{{{value}}}} {t} Aura When Equipped"] + candidates
    elif descfunc == "23":
        candidates = [f"{t} {{{{value}}}}%", f"+{{{{value}}}}% {t}"] + candidates
    return candidates


def build_stats(strings: dict[str, str], affixes: dict[str, str]) -> list[dict]:
    rows = read_tsv("d2_itemstatcost.txt")
    lowered = {k.lower(): (k, v) for k, v in affixes.items()}
    result = []
    for row in rows:
        sid = row.get("*ID", "")
        if not sid:
            continue
        text = strings.get(row.get("descstrpos", ""), "").rstrip("}").strip()
        text_neg = strings.get(row.get("descstrneg", ""), "").rstrip("}").strip()
        text2 = strings.get(row.get("descstr2", ""), "").rstrip("}").strip()
        zh = ""
        matched = ""
        for cand in candidate_templates(text, row.get("descfunc", ""), row.get("Stat", "")):
            hit = lowered.get(cand.lower())
            if hit:
                matched, zh = hit
                break
        if zh:
            zh = simplify(zh)
        result.append(
            {
                "id": int(sid),
                "stat": row.get("Stat", ""),
                "descfunc": int(row.get("descfunc") or 0),
                "descval": int(row.get("descval") or 0),
                "text": text,
                "text_neg": text_neg,
                "text2": text2,
                "zh": zh,
                "template": matched,
                "priority": int(row.get("descpriority") or 0),
                "percent": "%" in matched if matched else False,
            }
        )
    return result


def build_names() -> tuple[dict, dict, dict, dict]:
    items = json.loads((ROOT / "items.json").read_text(encoding="utf-8"))
    zh_items = {k: simplify(v) for k, v in items.items()}

    magic_prefix = {}
    for index, row in enumerate(read_tsv("d2_magicprefix.txt")):
        name = (row.get("Name") or "").strip()
        if name:
            magic_prefix[str(index)] = name
    magic_suffix = {}
    for index, row in enumerate(read_tsv("d2_magicsuffix.txt")):
        name = (row.get("Name") or "").strip()
        if name:
            magic_suffix[str(index)] = name
    rare_prefix = {}
    for index, row in enumerate(read_tsv("d2_rareprefix.txt")):
        name = (row.get("name") or "").strip()
        if name:
            rare_prefix[str(index)] = name
    rare_suffix = {}
    for index, row in enumerate(read_tsv("d2_raresuffix.txt")):
        name = (row.get("name") or "").strip()
        if name:
            rare_suffix[str(index)] = name

    runewords = {}
    for row in read_tsv("d2_runes.txt"):
        title = (row.get("*Rune Name") or "").strip()
        name = (row.get("Name") or "").strip()
        m = re.match(r"Runeword(\d+)$", name)
        if not title or not m:
            continue
        n = int(m.group(1))
        # The saved 12-bit id is a string-table lookup, not the row number.
        rid = 2718 if n == 22 else (n + 26 if n < 80 else n + 25)
        runewords[str(rid)] = title

    skills = {}
    for row in read_tsv("d2_skills.txt"):
        sid = (row.get("*Id") or "").strip()
        name = (row.get("skill") or "").strip()
        if sid and name:
            skills[sid] = {
                "name": name,
                "zh": zh_items.get(name, ""),
                "class": (row.get("charclass") or "").strip(),
            }

    affix_data = {
        "magic_prefix": magic_prefix,
        "magic_suffix": magic_suffix,
        "rare_prefix": rare_prefix,
        "rare_suffix": rare_suffix,
        "runeword": runewords,
    }
    return zh_items, affix_data, skills, items


def main() -> None:
    strings = read_string_table()
    affixes = json.loads((ROOT / "tr_affixes.json").read_text(encoding="utf-8"))
    stats = build_stats(strings, affixes)
    zh_items, affix_data, skills, _ = build_names()

    (OUT / "zh_items.json").write_text(
        json.dumps(zh_items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (OUT / "stat_desc.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=0), encoding="utf-8"
    )
    (OUT / "affixes.json").write_text(
        json.dumps(affix_data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (OUT / "skills.json").write_text(
        json.dumps(skills, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    missing = [s for s in stats if s["descfunc"] and not s["zh"]]
    print(
        f"stats={len(stats)} with_zh={sum(1 for s in stats if s['zh'])} "
        f"missing={len(missing)} items={len(zh_items)} skills={len(skills)}"
    )
    for s in missing[:40]:
        print(" MISS", s["id"], s["stat"], s["descfunc"], repr(s["text"]))


if __name__ == "__main__":
    main()
