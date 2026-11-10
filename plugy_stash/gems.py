"""Gem upgrade helper: 3 same-type, same-grade gems -> 1 next grade.

Diablo II's Horadric Cube recipe is 3 gems of one type.  Gems are simple 1x1
items whose entire identity is the four-character item code.  Upgrading one
only rewrites that code in the item header; the item's 32-bit id and all other
bytes stay intact.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .bitstream import write_bits_at
from .gamedata import game_data
from .stash import Item, StashFile, validate_stash
from .zh import GEM_GRADES, GEMS

# Ordered so the UI report is stable.
GEM_ORDER = ["紫水晶", "钻石", "绿宝石", "红宝石", "蓝宝石", "骷髅", "黄玉"]

# (gem name, grade) -> code
GEM_CODES: dict[tuple[str, int], str] = {
    (name, grade): code for code, (name, grade) in GEMS.items()
}


@dataclass
class GemUpgrade:
    item: Item
    old_code: str
    new_code: str
    companions: list[Item] = field(default_factory=list)


@dataclass
class GemPlan:
    upgrades: list[GemUpgrade] = field(default_factory=list)
    removals: list[Item] = field(default_factory=list)
    before: dict[str, list[int]] = field(default_factory=dict)
    after: dict[str, list[int]] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.upgrades)

    @property
    def consumed(self) -> int:
        return len(self.removals)

    @property
    def perfect_gained(self) -> int:
        total = 0
        for gem in GEM_ORDER:
            before = self.before.get(gem, [0] * 5)
            after = self.after.get(gem, [0] * 5)
            total += max(0, after[4] - before[4])
        return total

    def summary_lines(self) -> list[str]:
        lines: list[str] = []
        for gem in GEM_ORDER:
            before = self.before.get(gem, [0] * 5)
            after = self.after.get(gem, [0] * 5)
            gained = max(0, after[4] - before[4])
            used = sum(max(0, before[g] - after[g]) for g in range(4))
            if not used and not gained:
                continue
            leftovers = " / ".join(
                f"{GEM_GRADES[g]}{after[g]}" for g in range(4) if after[g]
            )
            line = f"{gem}：完美 +{gained}"
            if used:
                line += f"，消耗 {used} 颗低级宝石"
            if leftovers:
                line += f"；剩余 {leftovers}"
            lines.append(line)
        return lines


def _set_code(item: Item, code: str) -> None:
    """Rewrite the 4-character item code of a simple item block."""
    for index, char in enumerate(code.ljust(4)):
        write_bits_at(item.block, 76 + index * 8, 8, ord(char))
    item.code = code
    item_type = game_data().item(code)
    item.type_name = item_type.name
    item.kind = item_type.kind
    item.width = item_type.width
    item.height = item_type.height
    item.unknown_type = False
    item.warning = ""


def plan_gem_upgrade(stash: StashFile) -> GemPlan:
    """Plan a maximal 3-to-1 gem upgrade without touching the stash."""
    plan = GemPlan()
    gd = game_data()
    for gem_name in GEM_ORDER:
        pools: list[list[Item]] = [[] for _ in range(5)]
        for page in stash.pages:
            for item in page.items:
                if item.code not in GEMS:
                    continue
                if GEMS[item.code][0] != gem_name:
                    continue
                if not item.simple:
                    plan.skipped.append(f"{item.code}（不是简单物品）")
                    continue
                pools[GEMS[item.code][1]].append(item)
        plan.before[gem_name] = [len(pool) for pool in pools]

        for grade in range(4):
            items = pools[grade]
            keep = len(items) % 3
            for offset in range(keep, len(items), 3):
                group = items[offset : offset + 3]
                if len(group) != 3:
                    break
                base, *companions = group
                new_code = GEM_CODES.get((gem_name, grade + 1))
                if not new_code:
                    continue
                plan.upgrades.append(
                    GemUpgrade(
                        item=base,
                        old_code=base.code,
                        new_code=new_code,
                        companions=companions,
                    )
                )
                plan.removals.extend(companions)
                pools[grade + 1].append(base)
            pools[grade] = items[:keep]

        plan.after[gem_name] = [len(pool) for pool in pools]
        _ = gd  # keep the data object warm for the caller
    return plan


def apply_gem_plan(stash: StashFile, plan: GemPlan) -> None:
    if not plan.has_changes:
        return
    removed_ids = {id(item) for item in plan.removals}
    for upgrade in plan.upgrades:
        _set_code(upgrade.item, upgrade.new_code)
    for page in stash.pages:
        page.items = [item for item in page.items if id(item) not in removed_ids]
    validate_stash(stash)
