import inspect
import unittest

from engine import DiagnosisEngine


class EngineConfigurationTests(unittest.TestCase):
    def test_run_inference_exposes_experiment_parameters_without_changing_defaults(self):
        sig = inspect.signature(DiagnosisEngine.run_inference)

        self.assertEqual(sig.parameters["prob_threshold"].default, 0.15)
        self.assertEqual(sig.parameters["resnet_threshold"].default, 0.4)
        self.assertEqual(sig.parameters["patch_size"].default, 64)
        self.assertEqual(sig.parameters["stride"].default, 32)
        self.assertEqual(sig.parameters["return_all_candidates"].default, False)


if __name__ == "__main__":
    unittest.main()
