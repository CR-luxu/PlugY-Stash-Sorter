import tempfile
import unittest
from pathlib import Path

from plugy_stash.backups import prune_backups


class BackupTests(unittest.TestCase):
    def test_keeps_newest_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save = folder / "stash.sss"
            save.write_bytes(b"save")
            for i in range(7):
                (folder / f"stash.sss.20260101-00000{i}.bak").write_bytes(b"old")
            prune_backups(save)
            left = sorted(p.name for p in folder.glob("stash.sss.*.bak"))
            self.assertEqual(len(left), 5)
            self.assertNotIn("stash.sss.20260101-000000.bak", left)
            self.assertNotIn("stash.sss.20260101-000001.bak", left)
            self.assertIn("stash.sss.20260101-000006.bak", left)


if __name__ == "__main__":
    unittest.main()
