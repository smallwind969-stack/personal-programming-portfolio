import pytest

from app.decision.errors import DecisionError
from app.decision.requirement_parser import RequirementParser


class FakeProvider:
    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        assert "不得虚构数值" in system_prompt
        assert "低糖、抗氧化、弹性较高" in user_prompt
        return {
            "productType": "功能性果冻",
            "attributes": [
                {
                    "metric": "sugar_content",
                    "direction": "minimize",
                    "sourceText": "低糖",
                },
                {
                    "metric": "antioxidant_capacity",
                    "direction": "maximize",
                    "sourceText": "抗氧化",
                },
                {
                    "metric": "springiness",
                    "direction": "maximize",
                    "sourceText": "弹性较高",
                },
            ],
            "missingConstraints": [
                "sugar_content.maximum",
                "antioxidant_capacity.measurementMethod",
            ],
            "confidence": 0.92,
        }


class FailingProvider:
    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict:
        raise TimeoutError("provider timeout")


def test_parser_accepts_schema_valid_llm_json_without_keyword_rules():
    result = RequirementParser(FakeProvider()).parse(
        "需要一款低糖、抗氧化、弹性较高的功能性果冻"
    )

    assert result.productType == "功能性果冻"
    assert "sugar_content.maximum" in result.missingConstraints
    assert all(attribute.threshold is None for attribute in result.attributes)


def test_parser_failure_does_not_fall_back_to_hardcoded_keywords():
    with pytest.raises(DecisionError, match="REQUIREMENT_PARSER_UNAVAILABLE"):
        RequirementParser(FailingProvider()).parse("低糖果冻")
