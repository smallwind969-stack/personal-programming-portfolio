import unittest
from pathlib import Path


class PatientManagementUiTests(unittest.TestCase):
    def test_app_exposes_patient_management_routes(self):
        source = Path("app2.py").read_text(encoding="utf-8")

        self.assertIn("@app.route('/patients/delete'", source)
        self.assertIn("@app.route('/patients/move'", source)

    def test_frontend_has_context_menu_and_non_stretched_ct_image(self):
        source = Path("templates/index.html").read_text(encoding="utf-8")

        self.assertIn("oncontextmenu", source)
        self.assertIn("patient-context-menu", source)
        self.assertIn("object-fit: contain", source)

    def test_frontend_uses_directory_picker_before_legacy_folder_input(self):
        source = Path("templates/index.html").read_text(encoding="utf-8")

        self.assertIn("showDirectoryPicker", source)
        self.assertIn("collectDirectoryFiles", source)
        self.assertIn("submitUploadFiles", source)

    def test_frontend_exposes_visible_patient_bulk_actions(self):
        source = Path("templates/index.html").read_text(encoding="utf-8")

        self.assertIn("patient-bulk-actions", source)
        self.assertIn("patient-select-box", source)
        self.assertIn("updatePatientBulkActions", source)

    def test_frontend_moves_patients_by_long_press(self):
        source = Path("templates/index.html").read_text(encoding="utf-8")

        self.assertIn("beginPatientLongPress", source)
        self.assertIn("finishPatientLongPress", source)
        self.assertIn("LONG_PRESS_MOVE_MS", source)
        self.assertIn("movePatientsFromLongPress", source)
        self.assertNotIn('<button onclick="moveSelectedPatients()">移动</button>', source)


if __name__ == "__main__":
    unittest.main()
