from __future__ import annotations

from datetime import datetime, timezone
import uuid

from app.auth.contracts import AuthIdentity

from .contracts import DecisionRequirement
from .errors import DecisionError
from .knowledge_repository import JsonKnowledgeRepository
from .model_gateway import ActivatedModelGateway
from .search import DecisionSearchContext, DecisionSearcher, SearchVariable
from .trace_store import DecisionTrace, SqliteDecisionTraceStore


class DecisionPipeline:
    TARGETS = ["target_product_output"]

    def __init__(
        self,
        knowledge: JsonKnowledgeRepository,
        models: ActivatedModelGateway,
        traces: SqliteDecisionTraceStore,
        *,
        model_experiment_id: str,
        grid_points: int = 4,
    ) -> None:
        self.knowledge = knowledge
        self.models = models
        self.traces = traces
        self.model_experiment_id = model_experiment_id
        self.grid_points = grid_points

    def execute(self, identity: AuthIdentity, payload: dict) -> DecisionTrace:
        if identity.tenantId is None:
            raise DecisionError("TENANT_ACCESS_DENIED", "当前账号未绑定企业。")
        requirement = DecisionRequirement.model_validate(payload["requirement"])
        supplemental = payload.get("supplementalConstraints", {})
        unresolved = [
            key for key in requirement.missingConstraints if key not in supplemental
        ]
        if unresolved:
            raise DecisionError(
                "INCOMPLETE_CONSTRAINTS",
                "仍有阻止计算的必要约束未补充。",
                details={"missingConstraints": unresolved},
            )
        if "minimumOutput" not in supplemental or "minimumQuality" not in supplemental:
            raise DecisionError(
                "INCOMPLETE_CONSTRAINTS",
                "缺少最低产出或最低质量约束。",
                details={
                    "missingConstraints": [
                        key
                        for key in ("minimumOutput", "minimumQuality")
                        if key not in supplemental
                    ]
                },
            )
        metrics = list(
            {
                *(attribute.metric for attribute in requirement.attributes),
                *self.TARGETS,
            }
        )
        evidence = self.knowledge.search(requirement.productType, metrics)
        if not evidence:
            raise DecisionError(
                "KNOWLEDGE_INSUFFICIENT", "没有满足当前产品与指标的启用知识条目。"
            )
        model_ranges = self.models.common_feature_ranges(
            self.model_experiment_id, self.TARGETS
        )
        variables = []
        for name, bounds in model_ranges.items():
            knowledge_bounds = [
                item.processRanges[name]
                for item in evidence
                if name in item.processRanges
            ]
            minimum = max(
                [bounds["min"], *[item[0] for item in knowledge_bounds]]
            )
            maximum = min(
                [bounds["max"], *[item[1] for item in knowledge_bounds]]
            )
            user_range = supplemental.get("parameterRanges", {}).get(name)
            if user_range:
                minimum = max(minimum, float(user_range["min"]))
                maximum = min(maximum, float(user_range["max"]))
            if minimum > maximum:
                raise DecisionError(
                    "NO_FEASIBLE_SOLUTION", f"工艺变量 {name} 没有共同可行范围。"
                )
            variables.append(
                SearchVariable(
                    name=name,
                    minimum=minimum,
                    maximum=maximum,
                    points=self.grid_points,
                )
            )
        search_result = DecisionSearcher(self.models).search(
            DecisionSearchContext(
                experimentId=self.model_experiment_id,
                variables=variables,
                qualityTarget=None,
                resourceTarget=None,
                riskTarget=None,
                resourceParameter="time_hours",
                minimumOutput=float(supplemental["minimumOutput"]),
                minimumQuality=float(supplemental["minimumQuality"]),
                balancedWeights=supplemental.get(
                    "balancedWeights",
                    {
                        "output": 0.4,
                        "quality": 0.25,
                        "resource": 0.2,
                        "risk": 0.15,
                    },
                ),
            )
        )
        model_versions = {}
        data_versions = set()
        for prediction in search_result.plans[0].predictions.values():
            model_versions[prediction.targetField] = prediction.lineage.modelVersion
            data_versions.add(prediction.lineage.datasetSnapshotId)
        trace = DecisionTrace(
            runId=f"run-{uuid.uuid4()}",
            tenantId=identity.tenantId,
            userId=identity.userId,
            rawRequirement=payload["rawRequirement"],
            requirement=requirement.model_dump(mode="json"),
            supplementalConstraints=supplemental,
            knowledgeVersion=self.knowledge.version,
            knowledgeIds=[item.evidenceId for item in evidence],
            dataVersions=sorted(data_versions),
            modelVersions=model_versions,
            search=search_result.model_dump(mode="json"),
            plans=[
                plan.model_dump(mode="json") for plan in search_result.plans
            ],
            risks=sorted(
                {
                    condition
                    for item in evidence
                    for condition in item.disabledConditions
                }
            ),
            applicability=[
                f"{variable.name}: {variable.minimum}–{variable.maximum}"
                for variable in variables
            ],
            generatedAt=datetime.now(timezone.utc).isoformat(),
            replayOfRunId=payload.get("replayOfRunId"),
        )
        return self.traces.create(identity, trace)

    def get(self, identity: AuthIdentity, run_id: str) -> DecisionTrace:
        return self.traces.get(run_id, identity)

    def confirm(
        self,
        identity: AuthIdentity,
        run_id: str,
        plan_id: str,
        note: str | None,
    ) -> DecisionTrace:
        return self.traces.confirm(run_id, identity, plan_id, note)

    def cases(self, identity: AuthIdentity) -> list[DecisionTrace]:
        return self.traces.list_for_identity(identity)
