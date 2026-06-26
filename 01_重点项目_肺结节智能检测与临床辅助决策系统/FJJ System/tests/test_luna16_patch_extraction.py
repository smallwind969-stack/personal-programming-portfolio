import unittest

import numpy as np

from experiments.extract_luna16_patches import crop_patch
from experiments.metaimage_utils import parse_mhd


class Luna16PatchExtractionTests(unittest.TestCase):
    def test_crop_patch_center(self):
        arr = np.arange(10 * 10 * 10, dtype=np.float32).reshape(10, 10, 10)
        patch = crop_patch(arr, (5, 5, 5), 4)
        self.assertEqual(patch.shape, (4, 4, 4))
        self.assertEqual(patch[0, 0, 0], arr[3, 3, 3])

    def test_crop_patch_pads_edges(self):
        arr = np.ones((4, 4, 4), dtype=np.float32)
        patch = crop_patch(arr, (0, 0, 0), 4)
        self.assertEqual(patch.shape, (4, 4, 4))
        self.assertEqual(float(patch.sum()), 8.0)

    def test_parse_mhd_header(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.mhd"
            path.write_text("DimSize = 1 2 3\nElementType = MET_SHORT\n", encoding="ascii")
            meta = parse_mhd(path)
        self.assertEqual(meta["DimSize"], "1 2 3")


if __name__ == "__main__":
    unittest.main()
