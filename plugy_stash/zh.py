"""Chinese display helpers for the stash organizer."""
from __future__ import annotations

from .stash import Item

QUALITY_ZH = {
    0: "",
    1: "粗劣",
    2: "普通",
    3: "超强",
    4: "魔法",
    5: "套装",
    6: "稀有",
    7: "暗金",
    8: "合成",
    9: "洗练",
}

RUNE_NAMES = [
    "",
    "艾尔",
    "艾德",
    "特尔",
    "那夫",
    "爱斯",
    "伊司",
    "塔尔",
    "拉尔",
    "欧特",
    "书尔",
    "安姆",
    "索尔",
    "夏",
    "多尔",
    "海尔",
    "伊欧",
    "卢姆",
    "科",
    "法尔",
    "蓝姆",
    "普尔",
    "乌姆",
    "马尔",
    "伊斯特",
    "古尔",
    "维克斯",
    "欧姆",
    "罗",
    "瑟",
    "贝",
    "乔",
    "查姆",
    "萨德",
]

RUNE_EN = [
    "",
    "El",
    "Eld",
    "Tir",
    "Nef",
    "Eth",
    "Ith",
    "Tal",
    "Ral",
    "Ort",
    "Thul",
    "Amn",
    "Sol",
    "Shael",
    "Dol",
    "Hel",
    "Io",
    "Lum",
    "Ko",
    "Fal",
    "Lem",
    "Pul",
    "Um",
    "Mal",
    "Ist",
    "Gul",
    "Vex",
    "Ohm",
    "Lo",
    "Sur",
    "Ber",
    "Jah",
    "Cham",
    "Zod",
]

# code -> (gem name, grade). grade 0 chipped ... 4 perfect.
GEMS = {
    "gcv": ("紫水晶", 0), "gfv": ("紫水晶", 1), "gsv": ("紫水晶", 2), "gzv": ("紫水晶", 3), "gpv": ("紫水晶", 4),
    "gcw": ("钻石", 0), "gfw": ("钻石", 1), "gsw": ("钻石", 2), "glw": ("钻石", 3), "gpw": ("钻石", 4),
    "gcg": ("绿宝石", 0), "gfg": ("绿宝石", 1), "gsg": ("绿宝石", 2), "glg": ("绿宝石", 3), "gpg": ("绿宝石", 4),
    "gcr": ("红宝石", 0), "gfr": ("红宝石", 1), "gsr": ("红宝石", 2), "glr": ("红宝石", 3), "gpr": ("红宝石", 4),
    "gcb": ("蓝宝石", 0), "gfb": ("蓝宝石", 1), "gsb": ("蓝宝石", 2), "glb": ("蓝宝石", 3), "gpb": ("蓝宝石", 4),
    "skc": ("骷髅", 0), "skf": ("骷髅", 1), "sku": ("骷髅", 2), "skl": ("骷髅", 3), "skz": ("骷髅", 4),
    "gcy": ("黄玉", 0), "gfy": ("黄玉", 1), "gsy": ("黄玉", 2), "gly": ("黄玉", 3), "gpy": ("黄玉", 4),
}

GEM_GRADES = ["碎裂", "瑕疵", "普通", "无瑕", "完美"]

CHARMS = {
    "cm1": "小护身符",
    "cm2": "中护身符",
    "cm3": "大护身符",
    "tch": "地狱火炬",
}

JEWELRY = {
    "rin": "戒指",
    "amu": "项链",
    "jew": "珠宝",
}

POTIONS = {
    "hp1": "微效治疗药水", "hp2": "轻型治疗药水", "hp3": "治疗药水", "hp4": "强力治疗药水", "hp5": "超强治疗药水",
    "hpo": "治疗药水", "hpf": "全面治疗药水",
    "mp1": "微效法力药水", "mp2": "轻型法力药水", "mp3": "法力药水", "mp4": "强力法力药水", "mp5": "超强法力药水",
    "mpo": "法力药水", "mpf": "全面法力药水",
    "rvs": "体力恢复药水", "rvl": "全面恢复药水",
    "vps": "耐力药水", "yps": "解毒药水", "wms": "解冻药水", "elx": "灵药",
    "bpl": "大紫药水", "bps": "小紫药水",
}

POTION_SHORT = {
    "hp1": "微治", "hp2": "轻治", "hp3": "治疗", "hp4": "强治", "hp5": "超治",
    "hpo": "治疗", "hpf": "全治",
    "mp1": "微法", "mp2": "轻法", "mp3": "法力", "mp4": "强法", "mp5": "超法",
    "mpo": "法力", "mpf": "全法",
    "rvs": "小紫", "rvl": "大紫", "bpl": "大紫", "bps": "小紫",
    "vps": "耐力", "yps": "解毒", "wms": "解冻", "elx": "灵药",
}

QUEST_KEYS = {
    "key": "钥匙",
    "pk1": "恐惧之钥",
    "pk2": "憎恨之钥",
    "pk3": "毁灭之钥",
    "dhn": "暗黑破坏神之角",
    "bey": "巴尔之眼",
    "mbr": "墨菲斯托之脑",
    "tes": "痛苦之精华",
    "ceh": "憎恨之精华",
    "bet": "恐惧之精华",
    "fed": "毁灭之精华",
    "toa": "赦免徽章",
    "std": "英雄旗帜",
}

# A small set of frequently seen base names.  Everything else falls back to the
# English base name from the game data, which is still unambiguous.
BASE_ZH = {
    "cap": "帽子", "skp": "骷髅帽", "hlm": "头盔", "fhl": "全盔", "ghm": "巨盔", "crn": "王冠",
    "msk": "面具", "xap": "战帽", "xkp": "浅头盔", "xlm": "头盔", "xhl": "轻盔", "xhm": "翼盔",
    "xrn": "巨冠", "xsk": "死亡面具", "uap": "军帽", "ukp": "九头蛇头骨", "uhm": "尖顶盔",
    "urn": "王冠", "usk": "恶魔头骨", "ci0": "头环", "ci1": "宝冠", "ci2": "头饰", "ci3": "权冠",
    "lea": "皮甲", "hla": "硬皮甲", "stu": "镶嵌甲", "rng": "锁环甲", "scl": "鳞甲", "chn": "锁子甲",
    "brs": "胸甲", "spl": "板甲", "plt": "铠甲", "fld": "战场甲", "gth": "哥特甲", "ful": "全身板甲",
    "aar": "古代装甲", "xla": "恶魔皮甲", "xea": "蛇皮甲", "xui": "幽魂甲", "xhn": "网甲",
    "xcl": "鳞甲", "xng": "链甲", "xrs": "胸甲", "xpl": "红玉甲", "xth": "浮雕板甲", "xlt": "圣殿衣",
    "xul": "混沌甲", "xar": "华丽战甲", "uui": "灰幕寿衣", "uea": "蟒皮甲", "ula": "圣甲虫甲",
    "ung": "钻石甲", "ucl": "华丽铠甲", "urs": "巨型铠甲", "upl": "炎魔皮", "uth": "漆甲",
    "ult": "地狱锻甲", "uar": "神圣盔甲", "uul": "阴影板甲", "utp": "执政官铠甲",
    "lbl": "腰带", "vbl": "轻腰带", "mbl": "腰带", "tbl": "重腰带", "hbl": "系带", "zlb": "恶魔皮腰带",
    "zvb": "鲨皮腰带", "zmb": "网带", "ztb": "战斗腰带", "zhb": "战争腰带", "ulc": "蜘蛛网腰带",
    "uvc": "吸血鬼獠牙腰带", "umc": "秘银腰带", "utc": "巨魔腰带", "uhc": "巨神腰带",
    "lgl": "手套", "vgl": "重手套", "mgl": "护腕", "tgl": "轻护手", "hgl": "护手", "xlg": "恶魔皮手套",
    "xvg": "鲨皮手套", "xmg": "重护腕", "xtg": "战斗护手", "xhg": "战争护手", "ulg": "荆棘手套",
    "uvg": "吸血鬼獠牙手套", "umg": "护臂", "utg": "十字军护手", "uhg": "食人魔护手",
    "lbt": "皮靴", "vbt": "重靴", "mbt": "锁链靴", "tbt": "轻板靴", "hbt": "板靴", "xlb": "恶魔皮靴",
    "xvb": "鲨皮靴", "xmb": "网靴", "xtb": "战斗靴", "xhb": "战争靴", "ulb": "蟒皮靴",
    "uvb": "圣甲虫靴", "umb": "骸骨靴", "utb": "镜靴", "uhb": "迈密登护胫",
    "buc": "圆盾", "sml": "小盾", "lrg": "大盾", "kit": "鸢盾", "tow": "塔盾", "gts": "哥特盾",
    "spk": "尖刺盾", "bsh": "骨盾", "xuc": "防御者", "xml": "圆盾", "xrg": "鳞盾", "xit": "龙盾",
    "xow": "墙盾", "xpk": "倒刺盾", "xsh": "魔盾", "uml": "月神盾", "urg": "亥伯龙盾",
    "uit": "君主盾", "uow": "圣盾", "ush": "洞穴盾", "upk": "刀锋盾", "uts": "守卫盾",
    "pa1": "轻盾", "pa2": "圆盾", "pa3": "纹章盾", "pa4": "艾文盾", "pa5": "皇冠盾", "pa6": "阿卡兰塔盾",
    "pa7": "阿卡兰圆盾", "pa8": "保护盾", "pa9": "镀金盾", "paa": "皇家盾", "pab": "神圣轻盾",
    "pac": "神圣圆盾", "pad": "库拉斯特盾", "pae": "萨卡兰姆盾", "paf": "漩涡盾",
    "hax": "手斧", "axe": "斧", "2ax": "双斧", "mpi": "军镐", "wax": "战斧", "lax": "大斧",
    "bax": "阔斧", "btx": "战斧", "gax": "巨斧", "gix": "巨神斧", "9ha": "斧", "9ax": "斧",
    "92a": "双斧", "9mp": "军镐", "9wa": "战斧", "9la": "大斧", "9ba": "阔斧", "9bt": "战斧",
    "9ga": "巨斧", "9gi": "巨神斧", "7ha": "斧", "7ax": "斧", "72a": "双斧", "7mp": "军镐",
    "7wa": "战斧", "7la": "大斧", "7ba": "阔斧", "7bt": "战斧", "7ga": "巨斧", "7gi": "巨神斧",
    "clb": "棍棒", "spc": "狼牙棒", "mac": "钉头锤", "mst": "晨星", "fla": "连枷", "whm": "战锤",
    "mau": "巨槌", "gma": "巨战锤", "9cl": "棍棒", "9sp": "倒刺棍棒", "9ma": "钉头锤",
    "9mt": "锯齿星", "9fl": "连枷", "9wh": "战锤", "9m9": "巨槌", "9gm": "巨战锤",
    "7cl": "棍棒", "7sp": "倒刺棍棒", "7ma": "钉头锤", "7mt": "恶魔之星", "7fl": "连枷",
    "7wh": "传说之锤", "7m7": "食人魔槌", "7gm": "雷锤",
    "ssd": "短剑", "scm": "弯刀", "sbr": "军刀", "flc": "弯刀", "crs": "水晶剑", "bsd": "阔剑",
    "lsd": "长剑", "wsd": "战争剑", "2hs": "双手剑", "clm": "双手巨剑", "gis": "巨剑", "bsw": "重剑",
    "flb": "焰形剑", "gsd": "巨剑", "9ss": "短剑", "9sm": "弯刀", "9sb": "军刀", "9fc": "弯刀",
    "9cr": "水晶剑", "9bs": "阔剑", "9ls": "长剑", "9wd": "战争剑", "92h": "双手剑",
    "9cm": "双手巨剑", "9gs": "巨剑", "9b9": "重剑", "9fb": "焰形剑", "9gd": "巨剑",
    "7ss": "短剑", "7sm": "弯刀", "7sb": "军刀", "7fc": "弯刀", "7cr": "幻化之刃",
    "7bs": "征服之剑", "7ls": "神秘之剑", "7wd": "神话之剑", "72h": "传说之剑",
    "7cm": "高地之剑", "7gs": "炎魔之刃", "7b7": "冠军之剑", "7fb": "巨神之剑", "7gd": "巨神之刃",
    "lwb": "长战弓", "swb": "短弓", "hbw": "猎弓", "lbw": "长弓", "cbw": "复合弓", "sbb": "短战斗弓",
    "lbb": "长战斗弓", "8lb": "雪松弓", "8cb": "双弓", "8hb": "剃刀弓", "8sb": "边缘弓",
    "8lw": "哥特弓", "8sw": "符文弓", "8l8": "长攻城弓", "6lb": "暗影弓", "6cb": "伟大弓",
    "6hb": "刀锋弓", "6s7": "钻石弓", "6l7": "十字军弓", "6lw": "九头蛇弓", "6sw": "庇护弓",
    "6lx": "弹丸弓", "6mx": "蛇魔弩", "6hx": "巨神弩", "6rx": "恶魔弩",
    "jav": "标枪", "pil": "长矛", "ssp": "短矛", "tsp": "三叉戟", "glv": "阔头枪", "spr": "矛",
    "tri": "三叉戟", "brn": "布兰德矛", "spt": "斑点矛", "pik": "长枪", "bar": "长戟", "vou": "斧戟",
    "scy": "镰刀", "pax": "战戟", "hal": "戟", "wsc": "战镰", "9ja": "标枪", "9pi": "长矛",
    "9s9": "短矛", "9ts": "三叉戟", "9gl": "阔头枪", "9sr": "矛", "9tr": "三叉戟", "9br": "布兰德矛",
    "9st": "斑点矛", "9p9": "长枪", "9b7": "长戟", "9vo": "斧戟", "9wc": "镰刀", "9pa": "战戟",
    "9h9": "戟", "9s8": "战镰", "7ja": "标枪", "7pi": "长矛", "7s7": "短矛", "7ts": "三叉戟",
    "7gl": "阔头枪", "7sr": "矛", "7tr": "三叉戟", "7br": "布兰德矛", "7st": "斑点矛",
    "7p7": "长枪", "7h7": "长戟", "7vo": "斧戟", "7wc": "镰刀", "7pa": "战戟", "7br": "戟",
    "7s8": "战镰", "7o7": "食人魔斧",
    "cm1": "小护身符", "cm2": "中护身符", "cm3": "大护身符", "rin": "戒指", "amu": "项链",
    "ibk": "鉴定书", "tbk": "回城书", "isc": "鉴定卷轴", "tsc": "回城卷轴", "key": "钥匙",
}

CATEGORY_ORDER = ["符文", "宝石", "珠宝", "护身符", "首饰", "武器", "防具", "药剂", "任务/钥匙", "其他"]
QUALITY_ORDER = ["符文之语", "暗金", "套装", "稀有", "魔法", "超强", "普通", "其他"]

CATEGORY_COLORS = {
    "符文": "#c47a35",
    "宝石": "#8257b5",
    "珠宝": "#b04f83",
    "护身符": "#2f8f8a",
    "首饰": "#b0913c",
    "武器": "#9a4b45",
    "防具": "#466c9e",
    "药剂": "#4e8a4e",
    "任务/钥匙": "#6f6f6f",
    "其他": "#555555",
}


def is_rune(code: str) -> bool:
    return len(code) == 3 and code[0] == "r" and code[1:].isdigit() and 1 <= int(code[1:]) <= 33


def category(item: Item) -> str:
    code = item.code
    if is_rune(code):
        return "符文"
    if code in GEMS:
        return "宝石"
    if code == "jew":
        return "珠宝"
    if code in CHARMS:
        return "护身符"
    if code in JEWELRY:
        return "首饰"
    if item.kind == "weapon":
        return "武器"
    if item.kind == "armor":
        return "防具"
    if code in POTIONS or code.startswith(("hp", "mp")):
        return "药剂"
    if code in QUEST_KEYS:
        return "任务/钥匙"
    return "其他"


def quality_category(item: Item) -> str:
    if item.is_runeword:
        return "符文之语"
    if item.quality == 7:
        return "暗金"
    if item.quality == 5:
        return "套装"
    if item.quality in (6, 8, 9):
        return "稀有"
    if item.quality == 4:
        return "魔法"
    if item.quality == 3:
        return "超强"
    if item.quality in (1, 2):
        return "普通"
    return "其他"


def rune_number(code: str) -> int:
    return int(code[1:]) if is_rune(code) else 0


def base_name(item: Item) -> str:
    code = item.code
    if is_rune(code):
        n = rune_number(code)
        return f"{RUNE_NAMES[n]} {n:02d}"
    if code in GEMS:
        gem, grade = GEMS[code]
        return f"{GEM_GRADES[grade]}{gem}"
    if code in CHARMS:
        if item.unique_name:
            return item.unique_name
        return CHARMS[code]
    if code in JEWELRY:
        return JEWELRY[code]
    if code in POTIONS:
        return POTIONS[code]
    if code in QUEST_KEYS:
        return QUEST_KEYS[code]
    if code in BASE_ZH and BASE_ZH[code]:
        return BASE_ZH[code]
    return item.type_name or code


def display_name(item: Item) -> str:
    name = item.unique_name or item.set_item_name or base_name(item)
    if item.unique_name or item.set_item_name:
        # Keep the base type visible, e.g. "军帽 · Harlequin Crest".
        base = base_name(item)
        if base and base.lower() not in name.lower():
            name = f"{base}\n{name}"
    prefix = []
    if item.is_runeword:
        prefix.append("符文之语")
    elif item.quality in (1, 3, 4, 5, 6, 7, 8, 9) and item.code not in GEMS:
        q = QUALITY_ZH.get(item.quality)
        if q and not (item.unique_name or item.set_item_name):
            prefix.append(q)
    if item.ethereal:
        prefix.append("无形")
    if prefix:
        return " ".join(prefix) + "\n" + name
    return name


def subtitle(item: Item) -> str:
    bits = []
    if item.code:
        bits.append(item.code)
    if item.ilvl:
        bits.append(f"ilvl {item.ilvl}")
    q = QUALITY_ZH.get(item.quality)
    if q:
        bits.append(q)
    if item.total_sockets:
        bits.append(f"孔 {item.num_sockets}/{item.total_sockets}")
    elif item.num_sockets:
        bits.append(f"镶嵌 {item.num_sockets}")
    if item.defense:
        bits.append(f"防御 {item.defense}")
    if item.max_durability:
        bits.append(f"耐久 {item.max_durability}")
    if item.quantity:
        bits.append(f"数量 {item.quantity}")
    if item.ethereal:
        bits.append("无形")
    if item.width != 1 or item.height != 1:
        bits.append(f"{item.width}x{item.height}")
    return " · ".join(bits)
