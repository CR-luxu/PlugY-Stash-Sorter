"""Auto-arrangement engine for PlugY stash pages."""
from __future__ import annotations

from dataclasses import dataclass, field

from .stash import Item, StashError, StashFile, StashPage
from .zh import (
    CATEGORY_ORDER,
    GEMS,
    QUALITY_ORDER,
    category,
    is_rune,
    quality_category,
    rune_number,
)

GRID = 10


@dataclass
class Placement:
    item: Item
    page: int
    x: int
    y: int


@dataclass
class SortPlan:
    mode: str
    placements: list[Placement]
    new_pages: list[list[Placement]]
    page_meta: list[StashPage]
    group_counts: dict[str, int] = field(default_factory=dict)
    used_pages: int = 0
    added_pages: int = 0
    reserved_pages: int = 0
    grid: int = GRID

    @property
    def item_count(self) -> int:
        return len(self.placements)


class _PageGrid:
    def __init__(self, grid: int) -> None:
        self.grid = grid
        self.cells: list[list[bool]] = [[False] * grid for _ in range(grid)]

    def can_place(self, x: int, y: int, w: int, h: int) -> bool:
        if x < 0 or y < 0 or x + w > self.grid or y + h > self.grid:
            return False
        for yy in range(y, y + h):
            row = self.cells[yy]
            for xx in range(x, x + w):
                if row[xx]:
                    return False
        return True

    def occupy(self, x: int, y: int, w: int, h: int) -> None:
        for yy in range(y, y + h):
            row = self.cells[yy]
            for xx in range(x, x + w):
                row[xx] = True

    def first_fit(self, w: int, h: int) -> tuple[int, int] | None:
        # Keep the top-left corner free for the first category.  Scanning rows
        # from top to bottom and columns from left to right also makes the
        # result easy to read.
        for y in range(0, self.grid - h + 1):
            for x in range(0, self.grid - w + 1):
                if self.can_place(x, y, w, h):
                    return x, y
        return None

    @property
    def free_cells(self) -> int:
        return sum(1 for row in self.cells for cell in row if not cell)


def _group_key(item: Item, mode: str) -> str:
    if mode == "quality":
        return quality_category(item)
    return category(item)


def _rune_key(item: Item) -> tuple:
    n = rune_number(item.code)
    return (-n, item.quality, item.item_id)


def _gem_key(item: Item) -> tuple:
    gem, grade = GEMS.get(item.code, ("", 0))
    gem_order = ["紫水晶", "钻石", "绿宝石", "红宝石", "蓝宝石", "骷髅", "黄玉"]
    try:
        g = gem_order.index(gem)
    except ValueError:
        g = 99
    return (g, -grade, -item.area)


def _within_key(item: Item, group: str) -> tuple:
    if group == "符文":
        return _rune_key(item)
    if group == "宝石":
        return _gem_key(item)
    if group == "护身符":
        return (-item.area, item.quality, item.code, item.unique_id)
    if group == "首饰":
        return (0 if item.code == "rin" else 1, item.quality, item.code)
    if group == "武器":
        return (-item.area, item.quality, item.type_name, item.code)
    if group == "防具":
        return (-item.area, item.quality, item.type_name, item.code)
    if group == "药剂":
        return (item.code,)
    return (-item.area, item.quality, item.type_name, item.code)


def _ordered_items(items: list[Item], mode: str) -> list[Item]:
    indexed = list(enumerate(items))
    if mode == "compact":
        return [item for _, item in indexed]

    group_order = QUALITY_ORDER if mode == "quality" else CATEGORY_ORDER

    def key(pair: tuple[int, Item]) -> tuple:
        order, item = pair
        group = _group_key(item, mode)
        try:
            gidx = group_order.index(group)
        except ValueError:
            gidx = len(group_order)
        return (gidx,) + _within_key(item, category(item)) + (order,)

    indexed.sort(key=key)
    return [item for _, item in indexed]


def plan_sort(
    stash: StashFile,
    mode: str = "type",
    grid: int = GRID,
    page_limit: int | None = None,
    reserve_pages: int = 0,
) -> SortPlan:
    """Lay out all top-level items and return a non-destructive plan.

    ``reserve_pages`` leaves that many pages at the front of the stash empty.
    Items from those pages are moved into the pages after the reserved block.
    """
    if mode not in ("type", "type_compact", "quality", "compact"):
        raise ValueError(f"未知整理模式: {mode}")
    reserve = max(0, int(reserve_pages))

    items: list[Item] = []
    for page in stash.pages:
        items.extend(page.items)
    unknown = sorted({item.code for item in items if item.unknown_type})
    if unknown:
        raise StashError(
            "以下物品代码不在原版数据中，无法确定占格尺寸，已停止整理："
            + "、".join(unknown[:12])
            + ("…" if len(unknown) > 12 else "")
        )
    ordered = _ordered_items(items, mode)

    page_meta: list[StashPage] = [
        StashPage(
            index=p.index,
            flags=p.flags,
            has_flags=p.has_flags,
            name_bytes=p.name_bytes,
            items=[],
        )
        for p in stash.pages
    ]
    if page_limit is not None and page_limit > 0:
        page_meta = page_meta[:page_limit]

    shared = stash.is_shared

    def new_page_meta() -> StashPage:
        return StashPage(
            index=len(page_meta),
            flags=1 if shared else 0,
            has_flags=True,
            name_bytes=b"",
            items=[],
        )

    while len(page_meta) <= reserve:
        page_meta.append(new_page_meta())

    # Reserved pages stay empty.  Placement starts on the page after them.
    new_pages: list[list[Placement]] = [[] for _ in range(reserve)]
    group_counts: dict[str, int] = {}
    current_group: str | None = None
    current_page = reserve
    grid_state = _PageGrid(grid)
    new_pages.append([])

    def start_page() -> None:
        nonlocal current_page, grid_state
        new_pages.append([])
        current_page = len(new_pages) - 1
        grid_state = _PageGrid(grid)

    for item in ordered:
        if item.width > grid or item.height > grid:
            raise StashError(
                f"物品「{item.code}」尺寸 {item.width}x{item.height} 超过每页 {grid}x{grid}"
            )
        group = _group_key(item, mode)
        group_counts[group] = group_counts.get(group, 0) + 1
        page_break = mode in ("type", "quality") and current_group is not None and group != current_group
        if page_break and new_pages[current_page]:
            start_page()
        current_group = group

        pos = grid_state.first_fit(item.width, item.height)
        if pos is None:
            start_page()
            pos = grid_state.first_fit(item.width, item.height)
            if pos is None:
                raise StashError(f"无法放置物品「{item.code}」({item.width}x{item.height})")
        x, y = pos
        grid_state.occupy(x, y, item.width, item.height)
        new_pages[current_page].append(Placement(item=item, page=current_page, x=x, y=y))

    while len(new_pages) < len(page_meta):
        new_pages.append([])
    while len(page_meta) < len(new_pages):
        shared = stash.is_shared
        page_meta.append(
            StashPage(
                index=len(page_meta),
                flags=1 if shared else 0,
                has_flags=True,
                name_bytes=b"",
                items=[],
            )
        )

    used_pages = max(1, sum(1 for page in new_pages if page))
    placements = [p for page in new_pages for p in page]
    return SortPlan(
        mode=mode,
        placements=placements,
        new_pages=new_pages,
        page_meta=page_meta,
        group_counts=group_counts,
        used_pages=used_pages,
        added_pages=max(0, len(new_pages) - len(stash.pages)),
        reserved_pages=reserve,
        grid=grid,
    )


def apply_plan(stash: StashFile, plan: SortPlan) -> None:
    for meta in plan.page_meta:
        meta.items = []
    for page_index, placements in enumerate(plan.new_pages):
        meta = plan.page_meta[page_index]
        for placement in placements:
            placement.item.set_position(placement.x, placement.y)
            meta.items.append(placement.item)
    stash.pages = plan.page_meta
    for index, page in enumerate(stash.pages):
        page.index = index
