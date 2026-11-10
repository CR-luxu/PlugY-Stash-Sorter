import copy
import unittest
from pathlib import Path

from plugy_stash import parse_stash, parse_stash_bytes, validate_stash
from plugy_stash.sorter import apply_plan, plan_sort
from plugy_stash.stash import StashError


FIXTURE = Path(__file__).parent / "fixtures" / "plugy14.sss"


class StashParserTests(unittest.TestCase):
    def test_roundtrip_is_exact(self):
        stash = parse_stash(FIXTURE)
        self.assertEqual(stash.to_bytes(), stash.raw)
        self.assertEqual(stash.page_count, 14)
        self.assertEqual(len(stash.pages[0].items), 3)
        self.assertEqual([i.code for i in stash.pages[0].items], ["ibk", "hp1", "hp2"])
        self.assertEqual((stash.pages[0].items[0].x, stash.pages[0].items[0].y), (7, 6))

    def test_personal_stash_header(self):
        raw = FIXTURE.read_bytes()
        personal = b"CSTM" + b"01" + b"\x00" * 4 + (14).to_bytes(4, "little") + raw[10:]
        stash = parse_stash_bytes(personal)
        self.assertEqual(stash.file_type, "personal")
        self.assertFalse(stash.is_shared)
        self.assertEqual(stash.to_bytes(), personal)

    def test_coordinates_are_the_only_change(self):
        stash = parse_stash(FIXTURE)
        originals = {id(item): bytes(item.block) for page in stash.pages for item in page.items}
        plan = plan_sort(stash, "type_compact")
        apply_plan(stash, plan)
        for page in stash.pages:
            for item in page.items:
                old = bytearray(originals[id(item)])
                new = bytearray(item.block)
                for buf in (old, new):
                    buf[8:10] = b"\x00\x00"  # bits 65..79 cover x, y and panel id
                self.assertEqual(bytes(old), bytes(new), item.code)

    def test_sort_repacks_without_overlap(self):
        stash = parse_stash(FIXTURE)
        for mode in ("type", "type_compact", "quality", "compact"):
            plan = plan_sort(stash, mode)
            self.assertEqual(plan.item_count, 10)
            apply_plan(stash, plan)
            validate_stash(stash)
            data = stash.to_bytes()
            reparsed = parse_stash_bytes(data)
            self.assertEqual(sum(len(p.items) for p in reparsed.pages), 10)
            self.assertEqual(reparsed.to_bytes(), data)
            for page in reparsed.pages:
                occupied = set()
                for item in page.items:
                    for y in range(item.y, item.y + item.height):
                        for x in range(item.x, item.x + item.width):
                            self.assertNotIn((x, y), occupied)
                            occupied.add((x, y))
            stash = parse_stash(FIXTURE)

    def test_shared_gold_v2_roundtrip(self):
        raw = FIXTURE.read_bytes()
        v2 = b"SSS\x00" + b"02" + (123456).to_bytes(4, "little") + raw[6:]
        stash = parse_stash_bytes(v2)
        self.assertEqual(stash.version, "02")
        self.assertEqual(stash.shared_gold, 123456)
        self.assertEqual(stash.to_bytes(), v2)

    def test_reserve_first_pages_stays_empty(self):
        stash = parse_stash(FIXTURE)
        plan = plan_sort(stash, "type_compact", reserve_pages=3)
        self.assertEqual(plan.reserved_pages, 3)
        self.assertTrue(all(not page for page in plan.new_pages[:3]))
        self.assertTrue(all(p.page >= 3 for p in plan.placements))
        apply_plan(stash, plan)
        data = stash.to_bytes()
        reparsed = parse_stash_bytes(data)
        self.assertEqual(reparsed.page_count, 14)
        for page in reparsed.pages[:3]:
            self.assertEqual(len(page.items), 0)
        self.assertEqual(sum(len(page.items) for page in reparsed.pages), 10)
        self.assertEqual(reparsed.to_bytes(), data)

    def test_unknown_item_is_rejected_for_sorting(self):
        from plugy_stash.bitstream import write_bits_at

        raw = bytearray(FIXTURE.read_bytes())
        stash = parse_stash_bytes(bytes(raw))
        item = next(i for p in stash.pages for i in p.items if i.code == "hp1")
        # Item code starts at bit 76 of the item header.
        for index, ch in enumerate(b"zzz "):
            write_bits_at(raw, item.start * 8 + 76 + index * 8, 8, ch)
        changed = parse_stash_bytes(bytes(raw))
        unknown = next(i for p in changed.pages for i in p.items if i.code == "zzz")
        self.assertTrue(unknown.unknown_type)
        with self.assertRaises(StashError):
            plan_sort(changed, "type_compact")

    def test_sort_uses_extra_page_when_needed(self):
        stash = parse_stash(FIXTURE)
        # Duplicate the first page's items into an in-memory page to force
        # enough material for several pages.
        page = stash.pages[0]
        extra = []
        for _ in range(40):
            for item in page.items:
                extra.append(copy.deepcopy(item))
        # The planner reads page.items, so give it a big page list through a
        # normal page object.
        page.items = extra
        total_items = sum(len(p.items) for p in stash.pages)
        plan = plan_sort(stash, "type_compact")
        self.assertGreater(plan.used_pages, 1)
        apply_plan(stash, plan)
        validate_stash(stash)
        self.assertEqual(sum(len(p.items) for p in stash.pages), total_items)


if __name__ == "__main__":
    unittest.main()
