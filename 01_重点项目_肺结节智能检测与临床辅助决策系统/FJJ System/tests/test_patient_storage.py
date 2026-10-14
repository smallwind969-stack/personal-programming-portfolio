import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from patient_storage import delete_patients, list_patients, move_patients


class PatientStorageTests(unittest.TestCase):
    def make_case(self, root, patient_id):
        for rel in ("uploads", "static/processed", "case_context"):
            path = Path(root) / rel / patient_id
            path.mkdir(parents=True, exist_ok=True)
            (path / "marker.txt").write_text(patient_id, encoding="utf-8")

    def test_delete_patient_removes_raw_processed_and_review_context(self):
        with TemporaryDirectory() as tmp:
            self.make_case(tmp, "case-a")

            result = delete_patients(tmp, ["case-a"])

            self.assertEqual(result["deleted"], ["case-a"])
            self.assertFalse((Path(tmp) / "uploads" / "case-a").exists())
            self.assertFalse((Path(tmp) / "static/processed" / "case-a").exists())
            self.assertFalse((Path(tmp) / "case_context" / "case-a").exists())

    def test_move_patients_preserves_all_case_directories_under_new_name(self):
        with TemporaryDirectory() as tmp:
            self.make_case(tmp, "case-a")

            result = move_patients(tmp, ["case-a"], "reviewed")

            self.assertEqual(result["moved"], [{"from": "case-a", "to": "reviewed"}])
            self.assertTrue((Path(tmp) / "uploads" / "reviewed" / "marker.txt").exists())
            self.assertTrue((Path(tmp) / "static/processed" / "reviewed" / "marker.txt").exists())
            self.assertTrue((Path(tmp) / "case_context" / "reviewed" / "marker.txt").exists())

    def test_list_patients_includes_upload_only_failed_cases(self):
        with TemporaryDirectory() as tmp:
            upload_only = Path(tmp) / "uploads" / "failed-case"
            upload_only.mkdir(parents=True)

            self.assertEqual(list_patients(tmp), ["failed-case"])


if __name__ == "__main__":
    unittest.main()
