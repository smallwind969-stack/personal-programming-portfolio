import unittest
from unittest.mock import patch

from agent.followup_agent import build_followup_recommendation


class FollowupAgentReportTests(unittest.TestCase):
    def test_unreviewed_candidates_do_not_receive_low_risk_label(self):
        case_context = {
            "clinical_context": {},
            "model_findings": [{"nodule_id": "model-1", "doctor_confirmed": False}],
            "final_nodules": [],
        }

        with patch("agent.followup_agent.generate_with_llm_api") as llm:
            result = build_followup_recommendation("case-pending", case_context=case_context)

        self.assertEqual(result["risk_level"], "not_assessed")
        self.assertEqual(result["risk_label"], "待复核")
        self.assertIn("待复核", result["case_summary"])
        llm.assert_not_called()

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

        with patch(
            "agent.followup_agent.generate_with_llm_api",
            return_value=("API 生成的医生复核建议", {"available": True, "model": "test-model"}),
        ):
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

        self.assertEqual(result["llm_summary"], "API 生成的医生复核建议")

    def test_llm_prompt_uses_doctor_readable_digest(self):
        captured = {}
        case_context = {
            "clinical_context": {},
            "final_nodules": [
                {
                    "nodule_id": "doctor_box_internal_id_should_not_leak",
                    "source": "doctor",
                    "doctor_confirmed": True,
                    "slice_idx": 22,
                    "diameter_mm": "-0.1",
                    "status": "confirmed",
                    "imaging_features": {},
                }
            ],
        }

        def fake_llm(prompt):
            captured["prompt"] = prompt
            return "复核建议", {"available": True, "model": "test-model"}

        with patch("agent.followup_agent.generate_with_llm_api", side_effect=fake_llm):
            result = build_followup_recommendation("case-002", case_context=case_context)

        self.assertNotIn("doctor_box_internal_id_should_not_leak", captured["prompt"])
        self.assertTrue(any("最大径数值无效" in item for item in result["risk_sections"]["medium"][0]["basis"]))
        self.assertIsNone(result["risk_sections"]["medium"][0]["diameter_mm"])
        self.assertIn("不要输出内部 nodule_id", captured["prompt"])


if __name__ == "__main__":
    unittest.main()
