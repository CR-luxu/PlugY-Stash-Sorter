import unittest
from pathlib import Path
from plugy_stash import parse_stash
from plugy_stash.props import formatter

class PropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stash=parse_stash(Path(__file__).parent/'fixtures'/'plugy14.sss')
        cls.f=formatter()
        cls.items={i.code:i for p in cls.stash.pages for i in p.items}
    def test_base_names(self):
        self.assertEqual(self.f.item_name(self.items['ibk']), '鉴定书')
        self.assertEqual(self.f.item_name(self.items['hp1']), '微效治疗药水')
        self.assertEqual(self.f.item_name(self.items['qui']), '超强 棉布甲')
    def test_magic_name_and_props(self):
        it=self.items['lbl']
        self.assertIn('Sturdy',self.f.item_name(it))
        self.assertIn('of Health',self.f.item_name(it))
        lines=self.f.property_lines(it.magic_props)
        self.assertIn('+19% 防御强化',lines)
        self.assertEqual(it.magic_props[0].stat_id,16)
        self.assertEqual(it.magic_props[0].values,[19])
    def test_skill_line(self):
        it=self.items['sst']
        lines=self.f.property_lines(it.magic_props)
        self.assertIn('+1 火焰弹',lines)
    def test_sections(self):
        secs=self.f.sections(self.items['lbl'])
        titles=[s.title for s in secs]
        self.assertIn('基础属性',titles)
        self.assertIn('魔法属性',titles)

if __name__=='__main__': unittest.main()
