from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class ResearchEvaluationOutcome:
    metrics: dict[str, float]
    durationSeconds: float
    errorMessage: str | None = None
    artifactFingerprint: str | None = None
    artifactUri: str | None = None
    datasetFingerprint: str | None = None
    featureNames: list[str] | None = None
    targetField: str | None = None
    modelType: str | None = None
    featureRanges: dict[str, dict[str, float]] | None = None
    modelCard: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResearchEvaluationContext:
    experimentId: str
    campaignId: str
    datasetSnapshotId: str
    trialSequence: int


class ResearchEvaluationRunner(Protocol):
    mode: Literal["mock_evaluation", "real_runner"]
    runnerKey: str
    def evaluate(self, baseline: dict[str, float], parameter_patch: dict[str, Any], fixed_budget_seconds: int, context: ResearchEvaluationContext) -> ResearchEvaluationOutcome: ...


class DeterministicMockResearchRunner:
    mode: Literal["mock_evaluation"] = "mock_evaluation"
    runnerKey = "fixed-rd-evaluator-v1"

    def evaluate(self, baseline: dict[str, float], parameter_patch: dict[str, Any], fixed_budget_seconds: int, context: ResearchEvaluationContext) -> ResearchEvaluationOutcome:
        if parameter_patch.get("maxDepth", 0) > 64:
            return ResearchEvaluationOutcome({"mae": 0.0, "rmse": 0.0, "r2": 0.0}, 0.1, "candidate exceeded bounded complexity")
        if "learningRate" in parameter_patch and float(parameter_patch["learningRate"]) <= 0.03: gain = 0.012
        elif "maxDepth" in parameter_patch and int(parameter_patch["maxDepth"]) > 12: gain = -0.02
        else:
            import hashlib, json
            digest = int(hashlib.sha256(json.dumps(parameter_patch, sort_keys=True).encode()).hexdigest()[:8], 16)
            gain = ((digest % 17) - 7) / 1000
        metrics = {"r2": round(max(-1, min(1, baseline["r2"] + gain)), 6),
                   "mae": round(max(0, baseline["mae"] - gain / 2), 6),
                   "rmse": round(max(0, baseline["rmse"] - gain / 2.5), 6)}
        return ResearchEvaluationOutcome(metrics, float(fixed_budget_seconds))
