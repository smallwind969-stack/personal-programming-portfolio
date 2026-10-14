import unittest
from pathlib import Path


class AppModelPathTests(unittest.TestCase):
    def test_app_uses_project_relative_model_paths(self):
        source = Path("app2.py").read_text(encoding="utf-8")

        self.assertNotIn(r"C:\Users\LSY\Desktop\程序设计大赛", source)
        self.assertIn("os.path.join(base_dir, 'models'", source)


if __name__ == "__main__":
    unittest.main()
