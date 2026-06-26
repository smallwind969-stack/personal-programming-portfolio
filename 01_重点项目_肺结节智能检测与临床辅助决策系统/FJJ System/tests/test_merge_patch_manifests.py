import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from experiments.merge_patch_manifests import merge_manifests


class MergePatchManifestsTests(unittest.TestCase):
    def test_merge_manifests_marks_source_and_keeps_ok_rows(self):
        with TemporaryDirectory() as tmp:
            left = Path(tmp) / "left.json"
            right = Path(tmp) / "right.json"
            left.write_text(json.dumps([
                {"seriesuid": "a", "class": "1", "status": "ok", "patch": "a.npy"},
                {"seriesuid": "b", "class": "0", "status": "missing_volume", "patch": "b.npy"},
            ]), encoding="utf-8")
            right.write_text(json.dumps([
                {"seriesuid": "c", "class": "0", "status": "ok", "patch": "c.npy"},
            ]), encoding="utf-8")

            rows = merge_manifests([(left, "base"), (right, "hard")])

            self.assertEqual(len(rows), 2)
            self.assertEqual([row["source_manifest"] for row in rows], ["base", "hard"])


if __name__ == "__main__":
    unittest.main()
