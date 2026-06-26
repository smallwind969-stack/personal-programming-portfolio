import unittest

from agent.guideline_rules import (
    SAFETY_NOTE,
    audit_agent_text,
    guideline_hint_for_finding,
    normalize_nodule_type,
)


class GuidelineRulesTests(unittest.TestCase):
    def test_solid_6_to_8_mm_gets_ct_followup_hint(self):
        hint = guideline_hint_for_finding(
            {"diameter_mm": "7", "imaging_features": {"solid_type": "实性"}},
            {"age": "60", "smoking_history": "有"},
        )

        self.assertEqual(hint["framework"], "Fleischner 2017")
        self.assertEqual(hint["patient_risk"], "high")
        self.assertIn("6-12个月CT复查", hint["recommendation"])

    def test_part_solid_large_nodule_gets_short_interval_hint(self):
        hint = guideline_hint_for_finding(
            {"diameter_mm": "8.5", "imaging_features": {"solid_type": "部分实性", "spiculation": "可疑"}},
            {"age": "45", "smoking_history": "无"},
        )

        self.assertEqual(hint["nodule_type"], "part_solid")
        self.assertIn("3-6个月CT", hint["recommendation"])
        self.assertIn("毛刺", hint["suspicious_features"])

    def test_missing_size_and_type_blocks_precise_guideline(self):
        hint = guideline_hint_for_finding({}, {})

        self.assertIn("暂不能精确生成", hint["recommendation"])
        self.assertIn("结节最大径", hint["missing_inputs"])
        self.assertIn("结节类型：实性、磨玻璃或部分实性", hint["missing_inputs"])

    def test_screening_context_switches_framework_label(self):
        hint = guideline_hint_for_finding(
            {"diameter_mm": "5", "imaging_features": {"solid_type": "实性"}},
            {"scenario": "肺癌筛查"},
        )

        self.assertEqual(hint["primary_framework"], "Lung-RADS/NCCN")

    def test_audit_requires_safety_note_and_blocks_dangerous_phrases(self):
        ok = audit_agent_text("谨慎建议。" + SAFETY_NOTE)
        bad = audit_agent_text("该结节确诊为癌。")

        self.assertTrue(ok["passed"])
        self.assertFalse(bad["passed"])
        self.assertIn("确诊为癌", bad["violations"])

    def test_normalize_nodule_type(self):
        self.assertEqual(normalize_nodule_type("磨玻璃"), "ground_glass")
        self.assertEqual(normalize_nodule_type("part-solid"), "part_solid")
        self.assertEqual(normalize_nodule_type("实性"), "solid")


if __name__ == "__main__":
    unittest.main()
