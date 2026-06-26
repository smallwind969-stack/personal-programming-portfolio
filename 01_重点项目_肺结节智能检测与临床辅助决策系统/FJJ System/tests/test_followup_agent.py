import unittest
from unittest.mock import patch

from agent.followup_agent import build_followup_recommendation


class FollowupAgentReportTests(unittest.TestCase):
    def test_builds_structured_agent_report_for_reviewed_case(self):
        case_context = {
            "clinical_context": {
                "age": "62",
                "sex": "女",
                "smoking_history": "无",
                "previous_ct": "",
                "tumor_history": "无",
                "symptoms": "咳嗽",
            },
            "final_nodules": [
                {
                    "nodule_id": "model_001",
                    "source": "model",
                    "doctor_confirmed": True,
                    "slice_idx": 88,
                    "x": 210,
                    "y": 245,
                    "diameter_mm": "8.5",
                    "prob": 0.82,
                    "malignancy_prob": 0.76,
                    "status": "malignant",
                    "doctor_assessment": "边界欠清，建议重点复核。",
                    "imaging_features": {
                        "spiculation": "可疑",
                        "solid_type": "部分实性",
                    },
                },
                {
                    "nodule_id": "doctor_box_001",
                    "source": "doctor",
                    "doctor_confirmed": True,
                    "slice_idx": 91,
                    "x": 260,
                    "y": 220,
                    "status": "confirmed",
                    "doctor_assessment": "医生新增可疑小结节。",
                },
            ],
        }

        with patch("agent.followup_agent.generate_with_local_qwen", return_value=("", {"available": False})):
            result = build_followup_recommendation("case-001", case_context=case_context)

        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["statistics"]["total_nodules"], 2)
        self.assertEqual(result["statistics"]["doctor_added_count"], 1)
        self.assertEqual(result["statistics"]["high_count"], 1)
        self.assertIn("presentation_highlight", result)
        self.assertIn("AI检测-医生复核-临床补充-Agent建议", result["presentation_highlight"])
        self.assertIn("risk_sections", result)
        self.assertEqual(result["risk_sections"]["high"][0]["nodule_id"], "model_001")
        self.assertIn("guideline_hint", result["risk_sections"]["high"][0])
        self.assertIn("Fleischner", result["risk_sections"]["high"][0]["guideline_hint"]["framework"])
        self.assertIn("既往CT对比", result["missing_information"])
        self.assertIn("safety_note", result)


if __name__ == "__main__":
    unittest.main()
