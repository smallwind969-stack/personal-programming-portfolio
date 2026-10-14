from app.decision.contracts import DecisionFailure, DecisionRequirement


def test_requirement_preserves_missing_measurements_without_inventing_thresholds() -> None:
    requirement = DecisionRequirement.model_validate(
        {
            "productType": "功能性果冻",
            "attributes": [
                {
                    "metric": "antioxidant_capacity",
                    "direction": "maximize",
                }
            ],
            "missingConstraints": ["antioxidant_capacity.measurementMethod"],
        }
    )

    assert requirement.attributes[0].threshold is None
    assert requirement.attributes[0].measurementMethod is None
    assert requirement.missingConstraints == [
        "antioxidant_capacity.measurementMethod"
    ]


def test_decision_failure_uses_stable_machine_readable_code() -> None:
    failure = DecisionFailure(
        code="KNOWLEDGE_INSUFFICIENT",
        message="没有满足当前指标的已核验知识条目。",
    )

    assert failure.code == "KNOWLEDGE_INSUFFICIENT"
    assert failure.retryable is False
