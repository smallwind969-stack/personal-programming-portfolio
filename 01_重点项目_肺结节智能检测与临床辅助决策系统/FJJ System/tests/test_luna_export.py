import unittest

import SimpleITK as sitk

from engine import DiagnosisEngine
from experiments.export_luna_predictions import finding_to_physical


class LunaCoordinateExportTests(unittest.TestCase):
    def test_resampled_1mm_index_to_physical_uses_origin_and_direction(self):
        image = sitk.Image([20, 20, 20], sitk.sitkFloat32)
        image.SetOrigin((10.0, 20.0, 30.0))
        image.SetDirection((1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0))

        point = DiagnosisEngine.resampled_1mm_index_to_physical(None, image, 2.0, 3.0, 4.0)

        self.assertEqual(tuple(point), (12.0, 23.0, 34.0))

    def test_review_finding_to_physical_uses_original_image_index(self):
        image = sitk.Image([20, 20, 20], sitk.sitkFloat32)
        image.SetOrigin((1.0, 2.0, 3.0))
        image.SetSpacing((0.5, 0.5, 2.0))

        coord = finding_to_physical(image, {"x": 4, "y": 6, "slice_idx": 2})

        self.assertEqual(tuple(round(v, 4) for v in coord), (3.0, 5.0, 7.0))


if __name__ == "__main__":
    unittest.main()
