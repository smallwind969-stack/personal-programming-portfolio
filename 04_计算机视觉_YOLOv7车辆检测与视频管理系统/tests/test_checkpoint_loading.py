import unittest

import torch

from models.experimental import attempt_load


class CheckpointLoadingTests(unittest.TestCase):
    def test_existing_vehicle_checkpoint_loads_with_current_pytorch(self):
        model = attempt_load("yolov7.pt", map_location=torch.device("cpu"))
        self.assertIsNotNone(model)

    def test_existing_driver_checkpoint_loads_with_current_pytorch(self):
        model = attempt_load("best.pt", map_location=torch.device("cpu"))
        self.assertIsNotNone(model)


if __name__ == "__main__":
    unittest.main()
