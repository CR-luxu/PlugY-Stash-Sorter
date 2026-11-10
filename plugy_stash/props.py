"""Item names and human-readable property lines.

The game stores properties as numbered stats.  This module maps those ids to
Chinese/English tooltip text using the bundled D2 data tables.  It is deliberately
tolerant: an unknown or unsupported stat is shown with its internal name and raw
values instead of being silently dropped.
"""
from __future__ import annotations

from dataclasses import dataclass

from .gamedata import GameData, game_data
from .stash import Item, StatValue
from .zh import POTIONS

CLASS_ZH = {
    "ama": "亚马逊",
    "sor": "法师",
    "nec": "死灵法师",
    "pal": "圣骑士",
    "bar": "野蛮人",
    "dru": "德鲁伊",
    "ass": "刺客",
}
CLASS_EN = {
    "ama": "Amazon",
    "sor": "Sorceress",
    "nec": "Necromancer",
    "pal": "Paladin",
    "bar": "Barbarian",
    "dru": "Druid",
    "ass": "Assassin",
}
CLASS_ORDER = ["ama", "sor", "nec", "pal", "bar", "dru", "ass"]

SKILL_TABS_ZH = [
    "弓与十字弓", "被动与魔法", "标枪与长矛",
    "火焰", "闪电", "冰寒",
    "召唤", "毒素与白骨", "诅咒",
    "战斗", "攻击灵气", "防御灵气",
    "战斗技能", "战斗专精", "战吼",
    "召唤", "变身", "元素",
    "陷阱", "暗影", "武学",
]
SKILL_TABS_EN = [
    "Bow and Crossbow", "Passive and Magic", "Javelin and Spear",
    "Fire", "Lightning", "Cold",
    "Summoning", "Poison and Bone", "Curses",
    "Combat", "Offensive Auras", "Defensive Auras",
    "Combat Skills", "Combat Masteries", "Warcries",
    "Summoning", "Shapeshifting", "Elemental",
    "Traps", "Shadow Disciplines", "Martial Arts",
]

ELEMENT_ZH = {
    "fire": "火焰",
    "light": "闪电",
    "cold": "冰寒",
    "poison": "毒素",
    "magic": "魔法",
    "physical": "物理",
}

MONSTER_TYPE_ZH = {
    1: "不死",
    2: "恶魔",
    3: "昆虫",
    4: "动物",
    5: "人形",
}


def _simplify_placeholder(template: str) -> str:
    return template.replace("{{value}}", "{value}")


def _fmt_num(value: int) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"{value:,}" if isinstance(value, int) and abs(value) >= 10000 else str(value)


def _apply_template(template: str, value: int, values: list[int] | None = None) -> str:
    """Fill a Chinese template and make -/+ signs read naturally."""
    text = template.replace("{{value}}", "{value}").replace("{{charges}}", "{charges}")
    # A template such as "+{value}%" must become "-10%" for a negative value.
    if value < 0:
        text = text.replace("+{value}", "{value}").replace("-{value}", "{value}")
        rendered = _fmt_num(value)
    else:
        rendered = _fmt_num(value)
    text = text.replace("{value}", rendered)
    if values:
        for index, val in enumerate(values):
            text = text.replace(f"{{v{index}}}", _fmt_num(val))
    return text


@dataclass
class PropertySection:
    title: str
    lines: list[str]


class ItemFormatter:
    def __init__(self, gd: GameData | None = None) -> None:
        self.gd = gd or game_data()

    # ------------------------------------------------------------------ names
    def base_name(self, item: Item, english: bool = False) -> str:
        code_zh = {
            "amu": "项链",
            "cm1": "小护身符",
            "cm2": "中护身符",
            "cm3": "大护身符",
            "ibk": "鉴定书",
            "tbk": "回城书",
            "isc": "鉴定卷轴",
            "tsc": "回城卷轴",
            "key": "钥匙",
            "jew": "珠宝",
            "0sc": "卷轴",
            "ass": "技能书",
            "box": "赫拉迪克方块",
            "tr1": "赫拉迪克卷轴",
            "tr2": "抗性卷轴",
            "ice": "玛拉药水",
            "hst": "赫拉迪克法杖",
            "qf1": "克林姆的连枷",
            "qf2": "克林姆的意志",
            "qey": "克林姆的眼",
            "qbr": "克林姆的脑",
            "qhr": "克林姆的心",
            "dhn": "暗黑破坏神之角",
            "bey": "巴尔之眼",
            "mbr": "墨菲斯托之脑",
            "tes": "痛苦之精华",
            "ceh": "憎恨之精华",
            "bet": "恐惧之精华",
            "fed": "毁灭之精华",
            "toa": "赦免徽章",
            "std": "英雄旗帜",
            "pk1": "恐惧之钥",
            "pk2": "憎恨之钥",
            "pk3": "毁灭之钥",
        }
        if not english and item.code in code_zh:
            return code_zh[item.code]
        if not english and item.code in POTIONS:
            return POTIONS[item.code]
        name = item.type_name or item.code
        if english:
            return name
        translated = self.gd.zh_items.get(name, "").strip() or name
        if item.code.startswith("r") and item.code[1:].isdigit() and len(item.code) == 3:
            return f"{translated} {int(item.code[1:]):02d}"
        return translated

    def prefix_name(self, item: Item) -> str:
        return self.gd.affixes["magic_prefix"].get(str(item.magic_prefix_id), "")

    def suffix_name(self, item: Item) -> str:
        return self.gd.affixes["magic_suffix"].get(str(item.magic_suffix_id), "")

    def rare_name(self, item: Item, english: bool = False) -> str:
        first = self.gd.affixes["rare_prefix"].get(str(item.rare_name1), "")
        second = self.gd.affixes["rare_suffix"].get(str(item.rare_name2), "")
        parts = []
        if first:
            parts.append(first[:1].upper() + first[1:])
        if second:
            parts.append(second[:1].upper() + second[1:])
        return " ".join(parts)

    def runeword_name(self, item: Item) -> str:
        return self.gd.affixes["runeword"].get(str(item.runeword_id), "")

    def item_name(self, item: Item, english: bool = False, quality_prefix: bool = True) -> str:
        base = item.type_name or item.code
        base_cn = self.base_name(item)
        prefix = self.prefix_name(item)
        suffix = self.suffix_name(item)
        quality = item.quality

        if quality == 7 and item.unique_name:
            name = item.unique_name if english else self.gd.zh_items.get(item.unique_name, item.unique_name)
        elif quality == 5 and item.set_item_name:
            name = item.set_item_name if english else self.gd.zh_items.get(item.set_item_name, item.set_item_name)
        elif item.is_runeword:
            rw = self.runeword_name(item)
            rw = rw or f"Runeword {item.runeword_id}"
            name = rw if english else self.gd.zh_items.get(rw, rw)
            if quality_prefix:
                name = f"{name} {base if english else base_cn}"
        elif quality in (6, 8, 9):
            rare = self.rare_name(item, english=english)
            name = rare or (base if english else base_cn)
        elif quality == 4 and (prefix or suffix):
            name = " ".join(part for part in (prefix, base if english else base_cn, suffix) if part)
        else:
            name = base if english else base_cn

        if item.personalized and item.personalized_name:
            name = f"{item.personalized_name}的{name}" if not english else f"{item.personalized_name}'s {name}"
        if item.ethereal:
            name = f"无形 {name}" if not english else f"Ethereal {name}"
        if quality_prefix and not item.is_runeword and quality == 3 and not english:
            name = f"超强 {name}"
        elif quality_prefix and not item.is_runeword and quality == 1 and not english:
            name = f"粗劣 {name}"
        return name.strip()

    def short_name(self, item: Item) -> str:
        quality = item.quality
        if quality == 7 and item.unique_name:
            return self.gd.zh_items.get(item.unique_name, item.unique_name)
        if quality == 5 and item.set_item_name:
            return self.gd.zh_items.get(item.set_item_name, item.set_item_name)
        if item.is_runeword:
            rw = self.runeword_name(item)
            return self.gd.zh_items.get(rw, rw) if rw else "符文之语"
        return self.base_name(item)

    def quality_name(self, item: Item) -> str:
        if item.is_runeword:
            return "符文之语"
        return {
            1: "粗劣",
            2: "普通",
            3: "超强",
            4: "魔法",
            5: "套装",
            6: "稀有",
            7: "暗金",
            8: "合成",
            9: "洗练",
        }.get(item.quality, "")

    # ------------------------------------------------------------- properties
    def stat_line(self, stat: StatValue) -> str:
        sid = stat.stat_id
        values = stat.values or [0]
        value = values[-1]
        desc = self.gd.stat_desc.get(sid, {})
        stat_name = desc.get("stat", f"stat_{sid}")
        if desc.get("descfunc", 0) == 0:
            return ""

        # Special stats where the stored parameter is a skill/class/table id.
        if sid in (17, 18):
            return f"+{_fmt_num(value)}% 伤害强化"
        if sid == 83:
            cls = CLASS_ORDER[values[0]] if 0 <= values[0] < len(CLASS_ORDER) else "?"
            return f"+{_fmt_num(value)} {CLASS_ZH.get(cls, cls)}技能"
        if sid in (97, 107):
            return self._skill_line(values)
        if sid == 188:
            return self._skill_tab_line(values)
        if sid == 126:
            return f"+{_fmt_num(value)} 火焰技能"
        if sid == 127:
            return f"+{_fmt_num(value)} 所有技能"
        if sid == 151:
            return self._aura_line(values)
        if sid in (195, 196, 197, 198, 199, 201):
            return self._chance_cast_line(sid, values)
        if sid == 204:
            return self._charged_line(values)
        if sid == 155:
            return f"{_fmt_num(value)}% 概率复活为怪物 #{values[0]}" if len(values) > 1 else "复活"
        if sid in (179, 180):
            mtype = MONSTER_TYPE_ZH.get(values[0], f"怪物类型 {values[0]}") if values else "怪物"
            if sid == 179:
                return f"+{_fmt_num(value)} 准确率（对{mtype}）"
            return f"+{_fmt_num(value)}% 伤害（对{mtype}）"
        if 187 <= sid <= 193:
            element = {
                187: "冰寒", 189: "火焰", 190: "闪电", 191: "毒素",
                192: "物理", 193: "魔法",
            }.get(sid, "")
            return f"-{_fmt_num(abs(value))}% 敌人{element}抗性"
        if sid in (234, 235, 236):
            element = {234: "冰寒", 235: "火焰", 236: "闪电"}[sid]
            return f"每级 +{_fmt_num(value)} {element}吸收"
        if sid in (288, 289, 290):
            element = {288: "冰寒", 289: "火焰", 290: "闪电"}[sid]
            return f"+{_fmt_num(value)} {element}吸收（随时间变化）"
        if sid == 36:
            return f"物理抗性 +{_fmt_num(value)}%"
        if sid == 38:
            return f"魔法抗性上限 +{_fmt_num(value)}%"
        if sid == 75:
            return f"耐久度上限 +{_fmt_num(value)}%"
        if sid == 80:
            return f"更佳机会取得魔法物品 {_fmt_num(value)}%"
        if sid == 85:
            return f"获得经验值 +{_fmt_num(value)}%"
        if sid == 86:
            return f"每次击杀回复生命 +{_fmt_num(value)}"
        if sid == 87:
            return f"商人价格降低 {_fmt_num(abs(value))}%"
        if sid == 108:
            return "杀死怪物恢复平静"
        if sid == 117:
            return "防止怪物自愈"
        if sid == 120:
            return f"目标防御 {_fmt_num(value)}"
        if sid == 125:
            return "可投掷"
        if sid == 137 or sid == 249 or sid == 302:
            return f"踢击伤害 +{_fmt_num(value)}"
        if sid == 152:
            return "无法破坏"
        if sid == 154:
            return f"精力消耗减缓 {_fmt_num(abs(value))}%"
        if sid == 158:
            return "射出爆炸箭或弩矢"
        if sid == 200:
            return "不消耗充能"
        if sid == 205:
            return "不消耗数量"
        if sid == 252:
            return f"每秒回复 {_fmt_num(value)} 点耐久"
        if sid == 253:
            return "回复数量"
        if sid == 254:
            return f"提高堆叠数量 {_fmt_num(value)}%"
        if sid == 329:
            return f"+{_fmt_num(value)}% 火焰系技能伤害"
        if sid == 330:
            return f"+{_fmt_num(value)}% 闪电系技能伤害"
        if sid == 331:
            return f"+{_fmt_num(value)}% 冰寒系技能伤害"
        if sid == 332:
            return f"+{_fmt_num(value)}% 毒素系技能伤害"
        if sid == 333:
            return f"-{_fmt_num(abs(value))}% 敌人火焰抗性"
        if sid == 334:
            return f"-{_fmt_num(abs(value))}% 敌人闪电抗性"
        if sid == 335:
            return f"-{_fmt_num(abs(value))}% 敌人冰寒抗性"
        if sid == 336:
            return f"-{_fmt_num(abs(value))}% 敌人毒素抗性"
        if sid == 357:
            return f"+{_fmt_num(value)}% 魔法系技能伤害"
        if sid == 358:
            return f"-{_fmt_num(abs(value))}% 敌人魔法抗性"
        if sid == 366:
            return f"-{_fmt_num(abs(value))}% 敌人物理抗性"

        template = desc.get("zh", "")
        if template:
            rendered = _apply_template(template, value, values)
            if stat_name.endswith("_perlevel"):
                rendered = "每级 " + rendered
            return rendered

        # Per-level / by-time stats whose base text is known.
        text = desc.get("text", "")
        if text:
            if stat_name.endswith("_perlevel"):
                return f"+{_fmt_num(value)} {text}（依角色等级）"
            if stat_name.endswith("_bytime"):
                return f"+{_fmt_num(value)} {text}（随时间变化）"
            return f"+{_fmt_num(value)} {text}"

        # Last resort: still show something useful rather than dropping the mod.
        vals = ", ".join(_fmt_num(v) for v in values)
        return f"{stat_name}: {vals}"

    def _skill_line(self, values: list[int]) -> str:
        skill_id = values[0]
        level = values[-1]
        skill = self.gd.skills.get(str(skill_id), {})
        name = skill.get("zh") or skill.get("name") or f"技能 #{skill_id}"
        return f"+{_fmt_num(level)} {name}"

    def _skill_tab_line(self, values: list[int]) -> str:
        tab = values[0]
        level = values[-1]
        if 0 <= tab < len(SKILL_TABS_ZH):
            return f"+{_fmt_num(level)} {SKILL_TABS_ZH[tab]}技能"
        return f"+{_fmt_num(level)} 技能页 #{tab}"

    def _aura_line(self, values: list[int]) -> str:
        skill_id = values[0]
        level = values[-1]
        skill = self.gd.skills.get(str(skill_id), {})
        name = skill.get("zh") or skill.get("name") or f"技能 #{skill_id}"
        return f"装备时赋予等级 {_fmt_num(level)} 的{name}灵气"

    def _chance_cast_line(self, sid: int, values: list[int]) -> str:
        # encode 2 stores: level (6 bits), skill id (10 bits), chance (7 bits)
        if len(values) >= 3:
            level, skill_id, chance = values[0], values[1], values[2]
        else:
            level, skill_id, chance = 0, values[0], values[-1]
        skill = self.gd.skills.get(str(skill_id), {})
        name = skill.get("zh") or skill.get("name") or f"技能 #{skill_id}"
        when = {
            195: "攻击时",
            196: "击杀时",
            197: "死亡时",
            198: "击中时",
            199: "升级时",
            201: "被击中时",
        }.get(sid, "")
        lv = f"等级 {_fmt_num(level)} 的" if level else ""
        return f"{_fmt_num(chance)}% 概率在{when}施展{lv}{name}"

    def _charged_line(self, values: list[int]) -> str:
        # encode 3 stores: level (6), skill id (10), charges (8), max charges (8)
        if len(values) >= 4:
            level, skill_id, charges, max_charges = values[0], values[1], values[2], values[3]
        elif len(values) >= 2:
            level, skill_id, charges, max_charges = 0, values[0], 0, values[-1]
        else:
            level, skill_id, charges, max_charges = 0, 0, 0, 0
        skill = self.gd.skills.get(str(skill_id), {})
        name = skill.get("zh") or skill.get("name") or f"技能 #{skill_id}"
        text = f"等级 {_fmt_num(level)} 的{name}" if level else name
        if max_charges:
            text += f"（{_fmt_num(charges)}/{_fmt_num(max_charges)} 次充能）"
        return text

    def property_lines(self, props: list[StatValue]) -> list[str]:
        """Format a property list, combining min/max damage stats."""
        by_id: dict[int, StatValue] = {}
        for prop in props:
            by_id.setdefault(prop.stat_id, prop)

        consumed: set[int] = set()
        lines: list[str] = []

        # Enhanced damage is stored as separate min/max percentages.
        if 17 in by_id and 18 in by_id:
            low = by_id[18].values[-1]
            high = by_id[17].values[-1]
            if low == high:
                lines.append(f"+{_fmt_num(high)}% 伤害强化")
            else:
                lines.append(f"+{_fmt_num(low)}-{_fmt_num(high)}% 伤害强化")
            consumed.update((17, 18))
        elif 25 in by_id:
            value = by_id[25].values[-1]
            lines.append(f"+{_fmt_num(value)}% 伤害强化")
            consumed.add(25)

        # Elemental damage is stored as min, max and (for cold/poison) length.
        elements = [
            ("fire", 48, 49, None),
            ("light", 50, 51, None),
            ("magic", 52, 53, None),
            ("cold", 54, 55, 56),
            ("poison", 57, 58, 59),
        ]
        for element, min_id, max_id, length_id in elements:
            if min_id not in by_id and max_id not in by_id:
                continue
            low = by_id[min_id].values[-1] if min_id in by_id else 0
            high = by_id[max_id].values[-1] if max_id in by_id else 0
            if low and high:
                text = f"{_fmt_num(low)}-{_fmt_num(high)} {ELEMENT_ZH[element]}伤害"
            elif high:
                text = f"+{_fmt_num(high)} {ELEMENT_ZH[element]}伤害"
            else:
                text = f"+{_fmt_num(low)} {ELEMENT_ZH[element]}伤害"
            if length_id and length_id in by_id:
                duration = by_id[length_id].values[-1] / 25
                text += f"（{duration:g} 秒）"
            lines.append(text)
            consumed.update((min_id, max_id, length_id))

        # Plain min/max damage.
        if 21 in by_id and 22 in by_id:
            low = by_id[21].values[-1]
            high = by_id[22].values[-1]
            lines.append(f"{_fmt_num(low)}-{_fmt_num(high)} 伤害")
            consumed.update((21, 22))

        for prop in props:
            if prop.stat_id in consumed:
                continue
            line = self.stat_line(prop)
            if line and line not in lines:
                lines.append(line)
        return lines

    def sections(self, item: Item) -> list[PropertySection]:
        sections: list[PropertySection] = []
        base_lines = self.base_property_lines(item)
        if base_lines:
            sections.append(PropertySection("基础属性", base_lines))
        magic = self.property_lines(item.magic_props)
        if magic:
            sections.append(PropertySection("魔法属性", magic))
        for bit, props in item.set_props:
            lines = self.property_lines(props)
            if lines:
                sections.append(PropertySection(f"套装加成（{bit + 2} 件）", lines))
        runeword = self.property_lines(item.runeword_props)
        if runeword:
            sections.append(PropertySection("符文之语属性", runeword))
        return sections

    def base_property_lines(self, item: Item) -> list[str]:
        lines: list[str] = []
        item_type = self.gd.item(item.code)
        if item_type.kind == "weapon":
            if item_type.two_hand and item_type.two_max:
                low, high = item_type.two_min, item_type.two_max
                label = "基础双手伤害"
            elif item_type.max_damage:
                low, high = item_type.min_damage, item_type.max_damage
                label = "基础伤害"
            else:
                low = high = 0
                label = ""
            if label:
                if item.ethereal:
                    low, high = int(low * 1.5), int(high * 1.5)
                lines.append(f"{label}：{low}-{high}")
        if item.defense:
            lines.append(f"防御：{item.defense}")
        elif item_type.max_ac:
            lines.append(f"基础防御：{item_type.min_ac}-{item_type.max_ac}")
        if item_type.block:
            lines.append(f"格挡：{item_type.block}%")
        if item.max_durability:
            lines.append(f"耐久度：{item.max_durability}")
        if item.total_sockets:
            lines.append(f"凹槽：{item.num_sockets} / {item.total_sockets}")
        elif item.socketed:
            lines.append("带凹槽")
        if item.quantity:
            lines.append(f"数量：{item.quantity}")
        reqs = []
        if item_type.req_str:
            reqs.append(f"力量 {item_type.req_str}")
        if item_type.req_dex:
            reqs.append(f"敏捷 {item_type.req_dex}")
        if item_type.req_level:
            reqs.append(f"等级 {item_type.req_level}")
        if reqs:
            lines.append("需求：" + " · ".join(reqs))
        return lines

    def socketed_lines(self, item: Item) -> list[str]:
        lines = []
        for child in item.children:
            name = self.item_name(child)
            child_lines = self.property_lines(child.magic_props)
            suffix = f"：{'；'.join(child_lines)}" if child_lines else ""
            lines.append(f"{name}{suffix}")
        return lines


_FORMATTER: ItemFormatter | None = None


def formatter() -> ItemFormatter:
    global _FORMATTER
    if _FORMATTER is None:
        _FORMATTER = ItemFormatter()
    return _FORMATTER


def item_name(item: Item, english: bool = False, quality_prefix: bool = True) -> str:
    return formatter().item_name(item, english=english, quality_prefix=quality_prefix)


def short_name(item: Item) -> str:
    return formatter().short_name(item)


def property_lines(props: list[StatValue]) -> list[str]:
    return formatter().property_lines(props)


def sections(item: Item) -> list[PropertySection]:
    return formatter().sections(item)
