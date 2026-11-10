"""Read and write PlugY shared/personal stash files.

Format references:
  * https://squeek502.github.io/d2itemreader/formats/plugy.html
  * https://github.com/ChaosMarc/PlugY
  * https://github.com/squeek502/d2itemreader

The important property of this module is that items are moved as opaque byte
blocks.  The only bits that are modified by the organizer are the X/Y grid
coordinates in each top-level item header, so all stats, sockets, personalization
and mod data survive untouched.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

from .bitstream import BitReader, write_bits_at
from .gamedata import GameData, game_data

SSS_MAGIC = b"SSS\x00"
CSTM_MAGIC = b"CSTM"
ITEM_TAG = b"JM"
STASH_TAG = b"ST"

QUALITY_NAMES = {
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


class StashError(ValueError):
    """Raised for an unrecognised or corrupt stash file."""

    def __init__(self, message: str, offset: int | None = None) -> None:
        self.offset = offset
        super().__init__(f"{message} (偏移 0x{offset:X})" if offset is not None else message)


@dataclass
class StatValue:
    """One saved item property: stat id plus decoded parameter/value fields."""

    stat_id: int
    values: list[int]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"StatValue({self.stat_id}, {self.values})"


@dataclass
class Item:
    start: int
    end: int
    block: bytearray
    code: str
    simple: bool
    identified: bool
    socketed: bool
    ethereal: bool
    personalized: bool
    is_runeword: bool
    location_id: int
    equipped_id: int
    x: int
    y: int
    panel_id: int
    num_sockets: int
    total_sockets: int
    quality: int
    ilvl: int
    item_id: int
    defense: int
    max_durability: int
    quantity: int
    set_id: int
    unique_id: int
    magic_prefix_id: int = 0
    magic_suffix_id: int = 0
    rare_name1: int = 0
    rare_name2: int = 0
    runeword_id: int = 0
    set_bonus_bits: int = 0
    personalized_name: str = ""
    magic_props: list[StatValue] = field(default_factory=list)
    set_props: list[tuple[int, list[StatValue]]] = field(default_factory=list)
    runeword_props: list[StatValue] = field(default_factory=list)
    children: list["Item"] = field(default_factory=list)
    width: int = 1
    height: int = 1
    type_name: str = ""
    kind: str = "misc"
    unique_name: str = ""
    set_item_name: str = ""
    unknown_type: bool = False
    warning: str = ""

    @property
    def is_child(self) -> bool:
        return self.location_id == 6

    @property
    def area(self) -> int:
        return self.width * self.height

    def set_position(self, x: int, y: int) -> None:
        # Basic item header: 16 bits "JM", then X at bit 65, Y at bit 69.
        write_bits_at(self.block, 65, 4, x)
        write_bits_at(self.block, 69, 4, y)
        self.x = x
        self.y = y


@dataclass
class StashPage:
    index: int
    flags: int
    has_flags: bool
    name_bytes: bytes
    items: list[Item] = field(default_factory=list)

    @property
    def name(self) -> str:
        if not self.name_bytes:
            return ""
        for encoding in ("utf-8", "gbk", "cp1252"):
            try:
                return self.name_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        return self.name_bytes.decode("latin-1", errors="replace")

    def fill_cells(self) -> int:
        return sum(item.area for item in self.items)

    def grid(self, size: int = 10) -> list[list[Item | None]]:
        cells: list[list[Item | None]] = [[None for _ in range(size)] for _ in range(size)]
        for item in self.items:
            for yy in range(item.y, min(size, item.y + item.height)):
                for xx in range(item.x, min(size, item.x + item.width)):
                    cells[yy][xx] = item
        return cells


@dataclass
class StashFile:
    path: Path | None
    raw: bytes
    file_type: str  # "shared" or "personal"
    version: str
    shared_gold: int
    pages: list[StashPage]
    page_count_offset: int
    prefix: bytes
    tail: bytes
    gamedata: GameData
    warnings: list[str] = field(default_factory=list)

    @property
    def is_shared(self) -> bool:
        return self.file_type == "shared"

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def to_bytes(self, pages: list[StashPage] | None = None) -> bytes:
        pages = pages if pages is not None else self.pages
        prefix = bytearray(self.prefix)
        struct.pack_into("<I", prefix, self.page_count_offset, len(pages))
        out = bytearray(prefix)
        for page in pages:
            out += STASH_TAG
            if page.has_flags:
                out += struct.pack("<I", page.flags)
            out += page.name_bytes + b"\x00"
            out += ITEM_TAG + struct.pack("<H", len(page.items))
            for item in page.items:
                out += item.block
        out += self.tail
        return bytes(out)


def _find_nul(data: bytes, start: int, limit: int = 64) -> int:
    end = data.find(b"\x00", start, min(len(data), start + limit))
    if end < 0:
        raise StashError("页面名称缺少结尾的 0 字节", start)
    return end


def parse_stash_bytes(raw: bytes, path: Path | None = None) -> StashFile:
    gd = game_data()
    warnings: list[str] = []
    if raw[:4] == SSS_MAGIC:
        file_type = "shared"
        version = raw[4:6].decode("ascii", errors="replace")
        if version not in ("01", "02"):
            raise StashError(f"不支持的 PlugY 共享仓库版本: {version!r}", 4)
        if version == "02":
            if len(raw) < 14:
                raise StashError("文件过短", 0)
            shared_gold = struct.unpack_from("<I", raw, 6)[0]
            page_count_offset = 10
        else:
            shared_gold = 0
            page_count_offset = 6
    elif raw[:4] == CSTM_MAGIC:
        file_type = "personal"
        version = raw[4:6].decode("ascii", errors="replace")
        if version != "01":
            raise StashError(f"不支持的 PlugY 个人仓库版本: {version!r}", 4)
        if len(raw) < 14:
            raise StashError("文件过短", 0)
        shared_gold = 0
        page_count_offset = 10
    else:
        raise StashError("不是 PlugY 仓库文件（应以 SSS\\0 或 CSTM 开头）", 0)

    if len(raw) < page_count_offset + 4:
        raise StashError("文件头不完整", 0)
    nb_pages = struct.unpack_from("<I", raw, page_count_offset)[0]
    if nb_pages <= 0 or nb_pages > 4096:
        raise StashError(f"页面数量异常: {nb_pages}", page_count_offset)

    pages_start = page_count_offset + 4
    prefix = raw[:pages_start]
    pos = pages_start
    pages: list[StashPage] = []

    for index in range(nb_pages):
        if raw[pos : pos + 2] != STASH_TAG:
            raise StashError(f"第 {index + 1} 页缺少 ST 标记", pos)
        pos += 2
        p = pos
        name_end = _find_nul(raw, p)
        has_flags = raw[name_end + 1 : name_end + 3] != ITEM_TAG
        flags = 0
        if has_flags:
            if name_end + 1 + 4 > len(raw):
                raise StashError("页面 flags 不完整", p)
            flags = struct.unpack_from("<I", raw, p)[0]
            p += 4
            name_end = _find_nul(raw, p)
        name_bytes = raw[p:name_end]
        p = name_end + 1
        if raw[p : p + 2] != ITEM_TAG:
            raise StashError(f"第 {index + 1} 页缺少物品列表 JM 标记", p)
        if p + 4 > len(raw):
            raise StashError("物品列表头不完整", p)
        item_count = struct.unpack_from("<H", raw, p + 2)[0]
        p += 4
        items: list[Item] = []
        for item_index in range(item_count):
            item = parse_item(raw, p, gd, warnings)
            items.append(item)
            p = item.end
        pages.append(
            StashPage(
                index=index,
                flags=flags,
                has_flags=has_flags,
                name_bytes=name_bytes,
                items=items,
            )
        )
        pos = p

    tail = raw[pos:]
    if tail:
        warnings.append(f"文件末尾保留了 {len(tail)} 字节自定义数据")

    stash = StashFile(
        path=path,
        raw=raw,
        file_type=file_type,
        version=version,
        shared_gold=shared_gold,
        pages=pages,
        page_count_offset=page_count_offset,
        prefix=prefix,
        tail=tail,
        gamedata=gd,
        warnings=warnings,
    )
    validate_stash(stash)
    return stash


def parse_stash(path: str | Path) -> StashFile:
    p = Path(path)
    raw = p.read_bytes()
    return parse_stash_bytes(raw, p)


def validate_stash(stash: StashFile, grid_size: int = 10) -> None:
    for page in stash.pages:
        occupied: dict[tuple[int, int], Item] = {}
        for item in page.items:
            if item.width < 1 or item.height < 1:
                raise StashError(f"第 {page.index + 1} 页物品尺寸无效", item.start)
            if item.x + item.width > grid_size or item.y + item.height > grid_size:
                stash.warnings.append(
                    f"第 {page.index + 1} 页「{item.code}」位置超出 {grid_size}x{grid_size} 网格"
                )
                continue
            for yy in range(item.y, item.y + item.height):
                for xx in range(item.x, item.x + item.width):
                    other = occupied.get((xx, yy))
                    if other is not None:
                        stash.warnings.append(
                            f"第 {page.index + 1} 页「{item.code}」与「{other.code}」位置重叠"
                        )
                    else:
                        occupied[(xx, yy)] = item


def parse_item(data: bytes, start: int, gd: GameData, warnings: list[str]) -> Item:
    br = BitReader(data, start * 8)
    item_start_bits = br.bitpos
    if br.read(16) != 0x4D4A:  # "JM" little endian
        raise StashError("物品缺少 JM 标记", start)

    br.skip(4)
    identified = bool(br.read(1))
    br.skip(6)
    socketed = bool(br.read(1))
    br.skip(1)
    is_new = bool(br.read(1))
    br.skip(2)
    is_ear = bool(br.read(1))
    starter = bool(br.read(1))
    br.skip(3)
    simple = bool(br.read(1))
    ethereal = bool(br.read(1))
    br.skip(1)
    personalized = bool(br.read(1))
    br.skip(1)
    is_runeword = bool(br.read(1))
    br.skip(5)
    version = br.read(8)
    br.skip(2)
    location_id = br.read(3)
    equipped_id = br.read(4)
    x = br.read(4)
    y = br.read(4)
    panel_id = br.read(3)

    code = ""
    num_sockets = 0
    if not is_ear:
        chars = []
        for _ in range(4):
            c = br.read(8)
            chars.append(chr(c) if c not in (0, 0x20) else "")
        code = "".join(chars).strip("\x00 ")
        num_sockets = br.read(3)
    else:
        code = "ear"
        ear_class = br.read(3)
        ear_level = br.read(7)
        for _ in range(16):
            if br.read(7) == 0:
                break
        br.align()

    quality = 0
    ilvl = 0
    item_id = 0
    defense = 0
    max_durability = 0
    quantity = 0
    total_sockets = 0
    set_id = 0
    unique_id = 0
    magic_prefix_id = 0
    magic_suffix_id = 0
    rare_name1 = 0
    rare_name2 = 0
    runeword_id = 0
    set_bonus_bits = 0
    personalized_name = ""
    magic_props: list[StatValue] = []
    set_props: list[tuple[int, list[StatValue]]] = []
    runeword_props: list[StatValue] = []

    if not simple:
        item_id = br.read(32)
        ilvl = br.read(7)
        quality = br.read(4)
        multiple_pictures = br.read(1)
        if multiple_pictures:
            br.skip(3)
        class_specific = br.read(1)
        if class_specific:
            br.skip(11)

        if quality == 1:
            br.skip(3)
        elif quality == 2:
            pass
        elif quality == 3:
            br.skip(3)
        elif quality == 4:
            magic_prefix_id = br.read(11)
            magic_suffix_id = br.read(11)
        elif quality == 5:
            set_id = br.read(12)
        elif quality == 7:
            unique_id = br.read(12)
        elif quality in (6, 8, 9):
            rare_name1 = br.read(8)
            rare_name2 = br.read(8)
            for _ in range(6):
                if br.read(1):
                    br.skip(11)

        if is_runeword:
            runeword_id = br.read(12)
            br.skip(4)

        if personalized:
            chars = []
            for _ in range(16):
                c = br.read(7)
                if c == 0:
                    break
                chars.append(chr(c))
            personalized_name = "".join(chars)

        if code in ("ibk", "tbk"):
            br.skip(5)

        br.skip(1)  # timestamp / realm-data flag

        if gd.is_armor(code):
            defense = br.read(11) - 10
        if gd.is_armor(code) or gd.is_weapon(code):
            max_durability = br.read(8)
            if max_durability > 0:
                br.skip(8)
                br.skip(1)
        if gd.is_stackable(code):
            quantity = br.read(9)
        if socketed:
            total_sockets = br.read(4)

        if quality == 5:
            set_bonus_bits = br.read(5)

        magic_props = parse_magic_list(br, gd)
        if set_bonus_bits:
            for bit in range(5):
                if set_bonus_bits & (1 << bit):
                    set_props.append((bit, parse_magic_list(br, gd)))
        if is_runeword:
            runeword_props = parse_magic_list(br, gd)

    end = (br.bitpos + 7) // 8
    block = bytearray(data[start:end])
    item_type = gd.item(code)
    unique_name = gd.unique_names.get(str(unique_id), "") if quality == 7 else ""
    set_item_name = gd.set_item_names.get(str(set_id), "") if quality == 5 else ""

    children: list[Item] = []
    if not simple and num_sockets:
        child_pos = end
        for _ in range(num_sockets):
            child = parse_item(data, child_pos, gd, warnings)
            if child.location_id != 6:
                warnings.append(f"「{code}」的镶嵌物位置标记异常")
            children.append(child)
            child_pos = child.end
        end = child_pos
        block = bytearray(data[start:end])

    if not item_type.name:
        warnings.append(f"未知物品代码「{code}」，按 1x1 处理")
    if item_type.code == "ear":
        width = height = 1
    else:
        width, height = item_type.width, item_type.height

    return Item(
        start=start,
        end=end,
        block=block,
        code=code,
        simple=simple,
        identified=identified,
        socketed=socketed,
        ethereal=ethereal,
        personalized=personalized,
        is_runeword=is_runeword,
        location_id=location_id,
        equipped_id=equipped_id,
        x=x,
        y=y,
        panel_id=panel_id,
        num_sockets=num_sockets,
        total_sockets=total_sockets,
        quality=quality,
        ilvl=ilvl,
        item_id=item_id,
        defense=defense,
        max_durability=max_durability,
        quantity=quantity,
        set_id=set_id,
        unique_id=unique_id,
        magic_prefix_id=magic_prefix_id,
        magic_suffix_id=magic_suffix_id,
        rare_name1=rare_name1,
        rare_name2=rare_name2,
        runeword_id=runeword_id,
        set_bonus_bits=set_bonus_bits,
        personalized_name=personalized_name,
        magic_props=magic_props,
        set_props=set_props,
        runeword_props=runeword_props,
        children=children,
        width=width,
        height=height,
        type_name=item_type.name,
        kind=item_type.kind,
        unique_name=unique_name,
        set_item_name=set_item_name,
        unknown_type=code not in gd.items,
        warning="" if item_type.name else f"未知代码 {code}",
    )


def parse_magic_list(br: BitReader, gd: GameData) -> list[StatValue]:
    result: list[StatValue] = []
    while True:
        stat_id = br.read(9)
        if stat_id == 0x1FF:
            return result
        stat = gd.stats.get(stat_id)
        if stat is None:
            raise StashError(
                f"物品属性 ID {stat_id} 不在原版 1.14d 数据中；这可能是模组存档", br.bytepos
            )
        if stat.bits <= 0 or stat.bits >= 64 or stat.encode == 4:
            raise StashError(
                f"物品属性 ID {stat_id} 的位宽无效；这可能是模组存档或数据损坏", br.bytepos
            )
        values: list[int] = []
        if stat.encode == 2:
            values.append(br.read(6) - stat.add)
            values.append(br.read(10) - stat.add)
            values.append(br.read(stat.bits) - stat.add)
        elif stat.encode == 3:
            values.append(br.read(6) - stat.add)
            values.append(br.read(10) - stat.add)
            values.append(br.read(8) - stat.add)
            values.append(br.read(8) - stat.add)
        elif stat.param_bits > 0:
            values.append(br.read(stat.param_bits) - stat.add)
            values.append(br.read(stat.bits) - stat.add)
        else:
            values.append(br.read(stat.bits) - stat.add)
        chained = stat.next
        guard = 0
        while chained:
            guard += 1
            if guard > 16:
                raise StashError("物品属性链异常", br.bytepos)
            nxt = gd.stats.get(chained)
            if nxt is None or nxt.bits <= 0:
                raise StashError("物品属性链损坏", br.bytepos)
            values.append(br.read(nxt.bits) - nxt.add)
            chained = nxt.next
        result.append(StatValue(stat_id=stat_id, values=values))
