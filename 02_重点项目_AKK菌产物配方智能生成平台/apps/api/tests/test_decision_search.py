import pytest

from app.decision.contracts import DecisionPrediction, ModelLineage
from app.decision.errors import DecisionError
from app.decision.search import DecisionSearchContext, DecisionSearcher, SearchVariable


class PredictiveGateway:
    def predict_many(self, experiment_id, inputs_by_target):
        results = {}
        for target, parameters in inputs_by_target.items():
            temperature = parameters["temperature_celsius"]
            ph = parameters["ph"]
            values = {
                "target_product_output": 10 - abs(temperature - 37) - abs(ph - 6.8),
                "quality_score": 9 - abs(temperature - 36) * 0.5 - abs(ph - 6.5),
                "resource_consumption": temperature + ph,
                "risk_score": abs(temperature - 36.5) + abs(ph - 6.7),
            }
            results[target] = DecisionPrediction(
                targetField=target,
                value=values[target],
                uncertainty=0.1,
                lineage=ModelLineage(
                    modelVersion=f"{target}-v1",
                    modelCategory="literature_baseline",
                    targetField=target,
                    datasetSnapshotId="observed-v1",
                    datasetFingerprint="sha256:data",
                    artifactFingerprint=f"sha256:{target}",
                    featureRanges={
                        "temperature_celsius": {"min": 35, "max": 38},
                        "ph": {"min": 6.4, "max": 7.0},
                    },
                    metrics={"mae": 0.1},
                ),
            )
        return results


def _context(minimum_output=7.0):
    return DecisionSearchContext(
        experimentId="decision-demo",
        variables=[
            SearchVariable(
                name="temperature_celsius", minimum=35, maximum=38, points=4
            ),
            SearchVariable(name="ph", minimum=6.4, maximum=7.0, points=4),
        ],
        minimumOutput=minimum_output,
        minimumQuality=7.0,
    )


def test_three_plans_use_independent_objectives_and_model_predictions():
    result = DecisionSearcher(PredictiveGateway()).search(_context())

    assert [plan.objective for plan in result.plans] == [
        "maximize_output",
        "balanced",
        "minimize_resource",
    ]
    assert all(plan.predictions for plan in result.plans)
    assert all(plan.constraintsPassed for plan in result.plans)
    assert len(result.evaluatedCandidates) == 16


def test_search_returns_no_feasible_solution():
    with pytest.raises(DecisionError, match="NO_FEASIBLE_SOLUTION"):
        DecisionSearcher(PredictiveGateway()).search(_context(minimum_output=100))


def test_search_is_reproducible():
    searcher = DecisionSearcher(PredictiveGateway())
    assert searcher.search(_context()).model_dump() == searcher.search(
        _context()
    ).model_dump()


class OutputOnlyGateway:
    def predict_many(self, experiment_id, inputs_by_target):
        parameters = next(iter(inputs_by_target.values()))
        return {
            "target_product_output": DecisionPrediction(
                targetField="target_product_output",
                value=parameters["time_hours"] / 12,
                uncertainty=0.2,
                lineage=ModelLineage(
                    modelVersion="od600-v1",
                    modelCategory="literature_baseline",
                    targetField="target_product_output",
                    datasetSnapshotId="observed-v1",
                    datasetFingerprint="sha256:data",
                    artifactFingerprint="sha256:model",
                    featureRanges={
                        "time_hours": {"min": 24, "max": 72},
                    },
                    metrics={"mae": 0.2},
                ),
            )
        }


def test_resource_plan_can_minimize_a_metered_process_input():
    result = DecisionSearcher(OutputOnlyGateway()).search(
        DecisionSearchContext(
            experimentId="decision-demo",
            variables=[
                SearchVariable(
                    name="time_hours", minimum=24, maximum=72, points=3
                )
            ],
            qualityTarget=None,
            resourceTarget=None,
            riskTarget=None,
            resourceParameter="time_hours",
            minimumOutput=2,
            minimumQuality=2,
        )
    )
    resource_plan = result.plans[2]
    assert resource_plan.objective == "minimize_resource"
    assert resource_plan.parameters["time_hours"] == 24
    assert resource_plan.scoreBreakdown["predictedResource"] == 24
