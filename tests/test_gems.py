import copy, unittest
from pathlib import Path

from plugy_stash import parse_stash, parse_stash_bytes
from plugy_stash.bitstream import write_bits_at
from plugy_stash.gamedata import game_data
from plugy_stash.gems import apply_gem_plan, plan_gem_upgrade


FIXTURE = Path(__file__).parent / "fixtures" / "plugy14.sss"


def make_gem(template, code, x, y):
    item = copy.deepcopy(template)
    for index, char in enumerate(code.ljust(4)):
        write_bits_at(item.block, 76 + index * 8, 8, ord(char))
    item.code = code
    item_type = game_data().item(code)
    item.type_name = item_type.name
    item.kind = item_type.kind
    item.width = item_type.width
    item.height = item_type.height
    item.simple = True
    item.x = x
    item.y = y
    return item


class GemTests(unittest.TestCase):
    def make_stash(self, codes):
        stash = parse_stash(FIXTURE)
        template = next(i for p in stash.pages for i in p.items if i.code == "hp1")
        for page in stash.pages:
            page.items = []
        page = stash.pages[0]
        page.items = [make_gem(template, code, index % 10, index // 10) for index, code in enumerate(codes)]
        return stash

    def test_three_flawless_make_one_perfect(self):
        stash = self.make_stash(["glr", "glr", "glr"])
        plan = plan_gem_upgrade(stash)
        self.assertTrue(plan.has_changes)
        self.assertEqual(len(plan.upgrades), 1)
        self.assertEqual(len(plan.removals), 2)
        self.assertEqual(plan.perfect_gained, 1)
        apply_gem_plan(stash, plan)
        data = stash.to_bytes()
        reparsed = parse_stash_bytes(data)
        self.assertEqual([i.code for i in reparsed.pages[0].items], ["gpr"])
        self.assertEqual(reparsed.to_bytes(), data)

    def test_nine_chipped_chain_to_one_normal(self):
        stash = self.make_stash(["gcv"] * 9)
        plan = plan_gem_upgrade(stash)
        self.assertEqual(len(plan.upgrades), 4)  # 3 flawed + 1 normal
        self.assertEqual(plan.perfect_gained, 0)
        apply_gem_plan(stash, plan)
        codes = [i.code for i in parse_stash_bytes(stash.to_bytes()).pages[0].items]
        self.assertEqual(codes, ["gsv"])

    def test_mixed_types_do_not_combine(self):
        stash = self.make_stash(["gcv", "gcv", "gfv"])
        plan = plan_gem_upgrade(stash)
        self.assertFalse(plan.has_changes)

    def test_same_type_different_grades_do_not_combine(self):
        stash = self.make_stash(["gcv", "gcv", "gfv"])
        self.assertFalse(plan_gem_upgrade(stash).has_changes)


if __name__ == "__main__":
    unittest.main()
