from __future__ import annotations

from itertools import product
from typing import Literal, Protocol

import numpy as np
from pydantic import BaseModel, Field, model_validator

from .contracts import DecisionPrediction
from .errors import DecisionError


class SearchVariable(BaseModel):
    name: str
    minimum: float
    maximum: float
    points: int = Field(ge=2, le=25)
    unit: str | None = None

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.minimum > self.maximum:
            raise ValueError("search variable minimum exceeds maximum")
        return self


class DecisionSearchContext(BaseModel):
    experimentId: str
    variables: list[SearchVariable] = Field(min_length=1)
    outputTarget: str = "target_product_output"
    qualityTarget: str | None = "quality_score"
    resourceTarget: str | None = "resource_consumption"
    riskTarget: str | None = "risk_score"
    resourceParameter: str | None = None
    minimumOutput: float
    minimumQuality: float
    balancedWeights: dict[str, float] = Field(
        default_factory=lambda: {
            "output": 0.4,
            "quality": 0.25,
            "resource": 0.2,
            "risk": 0.15,
        }
    )


class SearchCandidate(BaseModel):
    candidateId: str
    parameters: dict[str, float]
    predictions: dict[str, DecisionPrediction]
    constraintsPassed: bool
    rejectionReasons: list[str] = Field(default_factory=list)


class DecisionPlan(BaseModel):
    planId: str
    objective: Literal["maximize_output", "balanced", "minimize_resource"]
    parameters: dict[str, float]
    predictions: dict[str, DecisionPrediction]
    objectiveScore: float
    scoreBreakdown: dict[str, float]
    constraintsPassed: bool = True


class DecisionSearchResult(BaseModel):
    plans: list[DecisionPlan]
    evaluatedCandidates: list[SearchCandidate]
    rejectedCandidateIds: list[str]
    scoringVersion: str = "deterministic-grid-v1"


class PredictionGateway(Protocol):
    def predict_many(
        self, experiment_id: str, inputs_by_target: dict[str, dict[str, float]]
    ) -> dict[str, DecisionPrediction]:
        ...


class DecisionSearcher:
    def __init__(self, gateway: PredictionGateway) -> None:
        self.gateway = gateway

    def search(self, context: DecisionSearchContext) -> DecisionSearchResult:
        candidates = self._evaluate_grid(context)
        feasible = [item for item in candidates if item.constraintsPassed]
        if not feasible:
            raise DecisionError(
                "NO_FEASIBLE_SOLUTION",
                "当前搜索范围内没有同时满足产出、质量和模型边界的方案。",
                details={
                    "evaluated": len(candidates),
                    "rejections": {
                        item.candidateId: item.rejectionReasons for item in candidates
                    },
                },
            )

        normalized = self._normalizations(feasible, context)
        output_plan = max(
            feasible,
            key=lambda item: (
                self._metric_value(item, "output", context),
                self._stable_parameter_key(item),
            ),
        )
        resource_plan = min(
            feasible,
            key=lambda item: (
                self._metric_value(item, "resource", context),
                self._stable_parameter_key(item),
            ),
        )
        balanced_scores = {
            item.candidateId: self._balanced_score(item, context, normalized)
            for item in feasible
        }
        balanced_plan = max(
            feasible,
            key=lambda item: (
                balanced_scores[item.candidateId]["total"],
                self._stable_parameter_key(item),
            ),
        )
        plans = [
            self._plan(
                output_plan,
                "maximize_output",
                self._metric_value(output_plan, "output", context),
                {"predictedOutput": self._metric_value(output_plan, "output", context)},
            ),
            self._plan(
                balanced_plan,
                "balanced",
                balanced_scores[balanced_plan.candidateId]["total"],
                balanced_scores[balanced_plan.candidateId],
            ),
            self._plan(
                resource_plan,
                "minimize_resource",
                -self._metric_value(resource_plan, "resource", context),
                {
                    "predictedResource": self._metric_value(
                        resource_plan, "resource", context
                    )
                },
            ),
        ]
        return DecisionSearchResult(
            plans=plans,
            evaluatedCandidates=candidates,
            rejectedCandidateIds=[
                item.candidateId for item in candidates if not item.constraintsPassed
            ],
        )

    def _evaluate_grid(
        self, context: DecisionSearchContext
    ) -> list[SearchCandidate]:
        axes = [
            np.linspace(variable.minimum, variable.maximum, variable.points)
            for variable in context.variables
        ]
        targets = [
            target
            for target in [
                context.outputTarget,
                context.qualityTarget,
                context.resourceTarget,
                context.riskTarget,
            ]
            if target is not None
        ]
        candidates: list[SearchCandidate] = []
        for index, values in enumerate(product(*axes), start=1):
            parameters = {
                variable.name: round(float(value), 10)
                for variable, value in zip(context.variables, values)
            }
            predictions = self.gateway.predict_many(
                context.experimentId,
                {target: parameters for target in targets},
            )
            reasons = []
            candidate = SearchCandidate(
                candidateId=f"candidate-{index:04d}",
                parameters=parameters,
                predictions=predictions,
                constraintsPassed=True,
            )
            if self._metric_value(candidate, "output", context) < context.minimumOutput:
                reasons.append("MINIMUM_OUTPUT_NOT_MET")
            if self._metric_value(candidate, "quality", context) < context.minimumQuality:
                reasons.append("MINIMUM_QUALITY_NOT_MET")
            candidates.append(
                candidate.model_copy(
                    update={
                        "constraintsPassed": not reasons,
                        "rejectionReasons": reasons,
                    }
                )
            )
        return candidates

    def _normalizations(self, feasible, context):
        fields = {
            "output": context.outputTarget,
            "quality": context.qualityTarget,
            "resource": context.resourceTarget,
            "risk": context.riskTarget,
        }
        return {
            name: (
                min(self._metric_value(item, name, context) for item in feasible),
                max(self._metric_value(item, name, context) for item in feasible),
            )
            for name in fields
        }

    @staticmethod
    def _scale(value: float, bounds: tuple[float, float]) -> float:
        lower, upper = bounds
        return 1.0 if upper == lower else (value - lower) / (upper - lower)

    def _balanced_score(self, candidate, context, normalized):
        components = {
            "output": self._scale(
                self._metric_value(candidate, "output", context),
                normalized["output"],
            ),
            "quality": self._scale(
                self._metric_value(candidate, "quality", context),
                normalized["quality"],
            ),
            "resource": 1
            - self._scale(
                self._metric_value(candidate, "resource", context),
                normalized["resource"],
            ),
            "risk": 1
            - self._scale(
                self._metric_value(candidate, "risk", context),
                normalized["risk"],
            ),
        }
        components["total"] = sum(
            components[name] * context.balancedWeights[name]
            for name in ("output", "quality", "resource", "risk")
        )
        return {name: round(value, 10) for name, value in components.items()}

    @staticmethod
    def _metric_value(candidate, name, context) -> float:
        target = {
            "output": context.outputTarget,
            "quality": context.qualityTarget,
            "resource": context.resourceTarget,
            "risk": context.riskTarget,
        }[name]
        if target is not None:
            return candidate.predictions[target].value
        if name == "quality":
            return candidate.predictions[context.outputTarget].value
        if name == "resource" and context.resourceParameter:
            return candidate.parameters[context.resourceParameter]
        if name == "risk":
            return (
                candidate.predictions[context.outputTarget].uncertainty or 0.0
            )
        raise DecisionError(
            "MODEL_NOT_AVAILABLE", f"指标 {name} 没有模型或可靠计量字段。"
        )

    @staticmethod
    def _stable_parameter_key(candidate):
        return tuple(-value for _, value in sorted(candidate.parameters.items()))

    @staticmethod
    def _plan(candidate, objective, score, breakdown):
        return DecisionPlan(
            planId=f"{objective}:{candidate.candidateId}",
            objective=objective,
            parameters=candidate.parameters,
            predictions=candidate.predictions,
            objectiveScore=round(float(score), 10),
            scoreBreakdown=breakdown,
        )
