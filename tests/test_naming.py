import unittest
from pathlib import Path

from plugy_stash import parse_stash
from plugy_stash.naming import name_pages
from plugy_stash.sorter import apply_plan, plan_sort

FIXTURE = Path(__file__).parent / "fixtures" / "plugy14.sss"


class NamingTests(unittest.TestCase):
    def test_type_mode_names_categories(self):
        stash = parse_stash(FIXTURE)
        apply_plan(stash, plan_sort(stash, "type"))
        names = name_pages(stash, "type")
        self.assertEqual(names, ["首饰", "武器", "防具", "药剂", "其他"])

    def test_compact_page_gets_mixed_name(self):
        stash = parse_stash(FIXTURE)
        apply_plan(stash, plan_sort(stash, "compact"))
        name_pages(stash, "compact")
        self.assertIn("/", stash.pages[0].name)

    def test_custom_page_name_is_preserved(self):
        stash = parse_stash(FIXTURE)
        apply_plan(stash, plan_sort(stash, "type"))
        stash.pages[0].name_bytes = "我的仓库".encode("gbk")
        name_pages(stash, "type")
        self.assertEqual(stash.pages[0].name, "我的仓库")

    def test_stale_auto_name_is_cleared_on_empty_page(self):
        stash = parse_stash(FIXTURE)
        for page in stash.pages:
            page.items = []
        stash.pages[3].name_bytes = "符文".encode("gbk")
        name_pages(stash, "type")
        self.assertEqual(stash.pages[3].name_bytes, b"")

    def test_reserved_pages_stay_unnamed(self):
        stash = parse_stash(FIXTURE)
        apply_plan(stash, plan_sort(stash, "type_compact", reserve_pages=3))
        name_pages(stash, "type_compact")
        for page in stash.pages[:3]:
            self.assertEqual(page.name_bytes, b"")
        self.assertTrue(stash.pages[3].name_bytes)


if __name__ == "__main__":
    unittest.main()
