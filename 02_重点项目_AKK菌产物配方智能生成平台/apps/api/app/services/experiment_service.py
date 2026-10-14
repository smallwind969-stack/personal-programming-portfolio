from __future__ import annotations

from datetime import datetime, timezone
from random import Random
from threading import RLock
from uuid import uuid4

from app.domain.experiment_workspace import EXPERIMENT_WORKSPACES
from app.repositories.mock_repository import MockRepository
from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import (
    ExperimentArchiveItem,
    ExperimentArchiveResponse,
    ExperimentCreateRequest,
    ExperimentRecord,
    ExperimentWorkspaceOverview,
    ProductionContext,
    ProductionParameterDefinition,
)


class ExperimentService:
    def __init__(self, repository: SqliteRepository | None = None) -> None:
        self.repository = repository or SqliteRepository()
        self.mock_repository = MockRepository()
        self._version_lock = RLock()
        self._current_versions: dict[str, tuple[str, str]] = {}
        self._version_history: dict[str, list[dict[str, object]]] = {}

    def create_synthetic_records_for_result(self, result: dict) -> list[ExperimentRecord]:
        result_id = result["resultId"]
        candidate = result["candidates"][0]
        seed = sum(ord(char) for char in result_id)
        random = Random(seed)
        high_risk_count = len([risk for risk in candidate["riskItems"] if risk["riskLevel"] == "high"])
        risk_pressure = max(0, min(12, high_risk_count * 2.2))

        templates = [
            ("关键标志物保留率", "%", ">= 70%", 74 + random.random() * 16 - risk_pressure, "越高越好"),
            ("体系稳定性", "score", ">= 75", 72 + random.random() * 18 - risk_pressure, "越高越好"),
            ("浊度变化", "%", "<= 10%", 5 + random.random() * 8 + risk_pressure / 2, "越低越好"),
            ("感官接受度", "score", ">= 80", 76 + random.random() * 16 - risk_pressure / 2, "越高越好"),
            ("复水或分散表现", "score", ">= 75", 74 + random.random() * 18 - risk_pressure / 3, "越高越好"),
            ("单位样品成本指数", "index", "<= 75", 58 + random.random() * 22 + risk_pressure / 2, "越低越好"),
        ]

        records = []
        now = datetime.now(timezone.utc).isoformat()
        for index, (test_name, unit, target_range, value, direction) in enumerate(templates, start=1):
            value = round(value, 1)
            status = self._status(test_name, value)
            risk_level = "low" if status == "pass" else "medium" if status == "watch" else "high"
            records.append(
                {
                    "experimentId": f"exp-{result_id}-{index}",
                    "resultId": result_id,
                    "sampleCode": f"{candidate['candidateName']}-S{index:02d}",
                    "testName": test_name,
                    "metricValue": value,
                    "unit": unit,
                    "targetRange": target_range,
                    "status": status,
                    "riskLevel": risk_level,
                    "conclusion": self._conclusion(test_name, status, direction),
                    "createdAt": now,
                }
            )

        self.repository.save_experiment_records(result_id, records)
        return [ExperimentRecord.model_validate(record) for record in records]

    def list_records(self, result_id: str | None = None) -> list[ExperimentRecord]:
        if result_id is None and not self.repository.list_experiment_records(None):
            for result in self.mock_repository.get_formula_results()[:1]:
                self.create_synthetic_records_for_result(result)
        return [
            ExperimentRecord.model_validate(self._to_schema_keys(record))
            for record in self.repository.list_experiment_records(result_id)
        ]

    def list_workspace_archive(self) -> ExperimentArchiveResponse:
        persisted = self.repository.list_experiment_workspaces()
        raw_items = [*persisted, *EXPERIMENT_WORKSPACES]
        normalized_items = [
            {
                **item,
                "industry": (item.get("productionContext") or {}).get("industry", "未配置"),
                "processType": (item.get("productionContext") or {}).get("processType", "未配置"),
            }
            for item in raw_items
        ]
        items = [
            ExperimentArchiveItem.model_validate(item)
            for item in normalized_items
        ]
        confidence_values = [item.confidenceScore for item in items if item.confidenceScore is not None]
        return ExperimentArchiveResponse(
            totalCount=len(items),
            runningCount=sum(item.status == "running" for item in items),
            completedCount=sum(item.status == "completed" for item in items),
            averageConfidenceScore=(
                sum(confidence_values) / len(confidence_values) if confidence_values else 0
            ),
            experiments=items,
        )

    def get_workspace_overview(self, experiment_id: str) -> ExperimentWorkspaceOverview | None:
        workspace = self.repository.get_experiment_workspace(experiment_id) or next(
            (item for item in EXPERIMENT_WORKSPACES if item["experimentId"] == experiment_id),
            None,
        )
        if not workspace:
            return None
        if "productionContext" not in workspace and workspace.get("sourceType") == "sample":
            workspace = {
                **workspace,
                "productionContext": {
                    "industry": "生物制造与功能食品",
                    "processType": "菌藻培养与发酵",
                    "lineName": "隔离演示产线",
                    "materialSystem": "菌藻培养体系",
                    "criticalParameters": ["温度", "pH", "溶氧", "搅拌速度", "培养时长"],
                    "parameterDefinitions": [
                        ProductionParameterDefinition(key="temperatureC", label="温度", unit="℃", min=20, max=55, defaultValue=37),
                        ProductionParameterDefinition(key="ph", label="pH", unit="pH", min=4.5, max=8.5, defaultValue=6.8),
                        ProductionParameterDefinition(key="custom_1", label="溶氧", unit="%", min=0, max=100, defaultValue=20),
                        ProductionParameterDefinition(key="stirringRpm", label="搅拌速度", unit="rpm", min=0, max=400, defaultValue=150),
                        ProductionParameterDefinition(key="cultureHours", label="培养时长", unit="小时", min=12, max=96, defaultValue=48),
                    ],
                },
            }
        overview = ExperimentWorkspaceOverview.model_validate(workspace)
        with self._version_lock:
            current = self._current_versions.get(experiment_id)
            if current:
                overview.modelVersion, overview.resultVersion = current
        return overview

    def create_workspace(
        self, request: ExperimentCreateRequest, adapter_reference: dict | None,
        *, source_type: str | None = None, sample_template_version: str | None = None,
    ) -> ExperimentWorkspaceOverview:
        now = datetime.now(timezone.utc).isoformat()
        experiment_id = f"exp-{uuid4().hex[:12]}"
        adapter = adapter_reference
        production_context = ProductionContext.model_validate(request.productionContext)
        if not production_context.parameterDefinitions and production_context.criticalParameters:
            production_context = production_context.model_copy(update={
                "parameterDefinitions": self._parameter_definitions(production_context.criticalParameters),
            })
        workspace = {
            "experimentId": experiment_id,
            "name": request.name,
            "objective": request.objective,
            "batchCode": request.batchCode,
            "targetProduct": request.targetProduct,
            "targetMetrics": request.targetMetrics,
            "adapterPack": adapter,
            "sourceType": source_type or request.sourceType,
            "sampleTemplateVersion": sample_template_version,
            "productionContext": production_context.model_dump(mode="json"),
            "currentStage": "dataAnalysis",
            "status": "needsReview",
            "statusLabel": "待补充实验数据",
            "resultSummary": "待上传原始设备数据",
            "confidenceScore": None,
            "updatedAt": now,
            "modelVersion": "untrained",
            "resultVersion": None,
            "modelType": "待数据分析流程选择",
            "reliabilityMetrics": [
                {"label": "数据完整度", "value": "--", "detail": "尚未上传实验数据"},
                {"label": "设备适配", "value": "已锁定" if adapter else "待配置", "detail": adapter["packVersion"] if adapter else "可稍后配置"},
                {"label": "待人工确认", "value": "1", "detail": "上传数据后确认字段和单位"},
            ],
            "stages": [
                {"stage": "dataAnalysis", "label": "数据分析", "status": "needsReview", "canEnter": True, "canRun": False, "detail": "等待上传原始数据"},
                {"stage": "simulation", "label": "仿真模拟", "status": "waiting", "canEnter": False, "canRun": False, "detail": "完成可信数学建模后开放"},
                {"stage": "optimization", "label": "工艺优化", "status": "waiting", "canEnter": False, "canRun": False, "detail": "完成仿真验证后开放"},
            ],
            "resultMetrics": [],
            "riskItems": ["当前没有可用于建模的实验数据"],
            "validationItems": ["上传设备原始数据并人工确认字段与单位映射"],
        }
        overview = ExperimentWorkspaceOverview.model_validate(workspace)
        self.repository.save_experiment_workspace(overview.model_dump(mode="json"))
        return overview

    @staticmethod
    def _parameter_definitions(names: list[str]) -> list[ProductionParameterDefinition]:
        known = {
            "温度": ("temperatureC", "℃", 20, 55, 37),
            "温度（℃）": ("temperatureC", "℃", 20, 55, 37),
            "pH": ("ph", "pH", 4.5, 8.5, 6.8),
            "搅拌速度": ("stirringRpm", "rpm", 0, 400, 150),
            "培养时长": ("cultureHours", "小时", 12, 96, 48),
            "压力": ("pressureMpa", "MPa", 0, 450, 50),
        }
        definitions: list[ProductionParameterDefinition] = []
        for index, name in enumerate(names):
            key, unit, minimum, maximum, default = known.get(name, (f"custom_{index + 1}", "", None, None, None))
            definitions.append(ProductionParameterDefinition(
                key=key, label=name, unit=unit, min=minimum, max=maximum,
                defaultValue=default, source="实验配置",
            ))
        return definitions

    def mark_data_uploaded(self, experiment_id: str, field_count: int) -> None:
        payload = self.repository.get_experiment_workspace(experiment_id)
        if payload is None:
            return
        payload["status"] = "needsReview"
        payload["statusLabel"] = "字段与单位待确认"
        payload["resultSummary"] = f"已识别 {field_count} 个原始字段，等待人工确认"
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        payload["reliabilityMetrics"][0] = {
            "label": "数据接入", "value": f"{field_count} 字段", "detail": "原始文件已解析并生成转换证据",
        }
        payload["stages"][0].update({
            "status": "needsReview", "canRun": False, "detail": "字段与单位转换证据等待人工确认",
        })
        self.repository.update_experiment_workspace(payload)

    def is_persisted_workspace(self, experiment_id: str) -> bool:
        return self.repository.get_experiment_workspace(experiment_id) is not None

    def delete_workspace(self, experiment_id: str) -> None:
        self.repository.delete_experiment_workspace(experiment_id)
        with self._version_lock:
            self._current_versions.pop(experiment_id, None)
            self._version_history.pop(experiment_id, None)

    def assert_formal_evidence_allowed(self, experiment_id: str, action: str) -> None:
        overview = self.get_workspace_overview(experiment_id)
        if overview is None:
            raise LookupError(experiment_id)
        if overview.sourceType == "sample":
            labels = {
                "modelPromotion": "正式模型晋升",
                "measurementFeedback": "真实测量反馈",
                "deviceControl": "设备控制",
            }
            label = labels.get(action, action)
            raise ValueError(f"示例实验不能用于{label}；请创建企业实验并上传真实数据。")

    def activate_sample_demo_model(self, admission) -> None:
        """Open an isolated demo lane without registering a formal model."""
        payload = self.repository.get_experiment_workspace(admission.experimentId)
        if payload is None:
            raise LookupError(admission.experimentId)
        if payload.get("sourceType") != "sample":
            raise ValueError("demo model admission is sample-only")
        payload["modelVersion"] = admission.demoModelVersion
        payload["modelType"] = f"隔离演示 · {admission.modelType}"
        payload["confidenceScore"] = admission.reliabilityScore
        payload["currentStage"] = "simulation"
        payload["status"] = "running"
        payload["statusLabel"] = "演示模型已准入，等待仿真"
        payload["resultSummary"] = "已锁定训练血缘，可体验隔离仿真；不可用于正式模型、真实测量或设备控制"
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        payload["riskItems"] = list(admission.restrictions)
        payload["validationItems"] = [f"演示准入 {admission.admissionId}", f"训练轮次 {admission.trialId}", "仿真输出仍需真实实验验证"]
        for stage in payload["stages"]:
            if stage["stage"] == "dataAnalysis":
                stage.update({"status": "completed", "canEnter": True, "canRun": True, "detail": "示例建模血缘已锁定"})
            elif stage["stage"] == "simulation":
                stage.update({"status": "waiting", "canEnter": True, "canRun": True, "detail": "隔离演示模型已人工准入，可创建仿真运行"})
        self.repository.update_experiment_workspace(payload)

    def mark_intake_confirmed(self, experiment_id: str, mapping_count: int) -> None:
        payload = self.repository.get_experiment_workspace(experiment_id)
        if payload is None:
            return
        payload["status"] = "running"
        payload["statusLabel"] = "数据分析中"
        payload["resultSummary"] = f"{mapping_count} 个字段已确认，进入清洗对齐与建模"
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        payload["reliabilityMetrics"][2] = {
            "label": "字段人工确认", "value": f"{mapping_count}/{mapping_count}", "detail": "字段与单位映射已签署确认",
        }
        payload["stages"][0].update({
            "status": "running", "canRun": True, "detail": "接入门禁已通过，数据分析流程可运行",
        })
        self.repository.update_experiment_workspace(payload)

    def promote_versions(
        self,
        experiment_id: str,
        *,
        expected_model_version: str,
        expected_result_version: str,
        new_model_version: str,
        new_result_version: str,
        source_run_id: str,
    ) -> None:
        """Atomically compare-and-promote the current model/result pointers."""
        with self._version_lock:
            overview = self.get_workspace_overview(experiment_id)
            if overview is None:
                raise LookupError(experiment_id)
            if (overview.modelVersion, overview.resultVersion) != (expected_model_version, expected_result_version):
                raise RuntimeError("Parent model or result version changed")
            self._current_versions[experiment_id] = (new_model_version, new_result_version)
            self._version_history.setdefault(experiment_id, []).append({
                "modelVersion": new_model_version,
                "resultVersion": new_result_version,
                "parentModelVersion": expected_model_version,
                "parentResultVersion": expected_result_version,
                "sourceRunId": source_run_id,
            })

    def apply_model_evaluation(self, report, model_type: str) -> None:
        """Persist a confirmed model-evaluation result into workspace navigation gates."""
        payload = self.repository.get_experiment_workspace(report.experimentId)
        if payload is None:
            return
        payload["modelVersion"] = report.modelVersion
        payload["resultVersion"] = report.reportId
        payload["modelType"] = model_type
        payload["confidenceScore"] = report.reliabilityScore
        payload["currentStage"] = "simulation"
        payload["status"] = "running"
        payload["statusLabel"] = "模型评估已通过，等待仿真"
        payload["resultSummary"] = (
            f"{model_type} 已通过可靠性评估；"
            f"综合评分 {report.reliabilityScore * 100:.1f}%"
        )
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        payload["reliabilityMetrics"] = [
            {
                "label": "模型可靠性",
                "value": f"{report.reliabilityScore * 100:.1f}%",
                "detail": f"报告 {report.reportId}",
            },
            {
                "label": "留出集 R²",
                "value": f"{report.performanceMetrics.get('r2', 0):.3f}",
                "detail": "按时间顺序划分的独立留出集",
            },
            {
                "label": "人工确认",
                "value": "已签署",
                "detail": report.reviewedBy or "研发负责人",
            },
        ]
        payload["riskItems"] = list(report.admissionReasons)
        payload["validationItems"] = [
            "模型产物哈希已验证",
            "残差、漂移、覆盖率和预测区间已评估",
            "仿真结果仍需实际实验验证",
        ]
        for stage in payload["stages"]:
            if stage["stage"] == "dataAnalysis":
                stage.update({
                    "status": "completed",
                    "canEnter": True,
                    "canRun": True,
                    "detail": "数据、特征、模型和可靠性评估均已完成",
                })
            elif stage["stage"] == "simulation":
                stage.update({
                    "status": "waiting",
                    "canEnter": True,
                    "canRun": True,
                    "detail": "可靠性报告已人工确认，可以创建仿真运行",
                })
        self.repository.update_experiment_workspace(payload)

    def apply_simulation_result(self, run) -> None:
        """Persist a completed digital experiment and unlock constrained optimization."""
        if run.status != "completed" or run.officialResult is None:
            raise ValueError("only a completed simulation with an official result can be applied")
        payload = self.repository.get_experiment_workspace(run.experimentId)
        if payload is None:
            return
        demo_mode = payload.get("sourceType") == "sample"
        payload["resultVersion"] = run.officialResult.snapshotId
        payload["currentStage"] = "optimization"
        payload["status"] = "running"
        payload["statusLabel"] = "演示仿真已完成，等待工艺优化" if demo_mode else "数字实验已完成，等待工艺优化"
        payload["resultSummary"] = (
            f"数字实验 {run.runId} 已完成；"
            f"模型驱动目标 {len(run.officialResult.modelTargets)} 项"
        )
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        for stage in payload["stages"]:
            if stage["stage"] == "simulation":
                stage.update({
                    "status": "completed", "canEnter": True, "canRun": True,
                    "detail": f"{'隔离演示仿真' if demo_mode else '正式数字实验'} {run.runId} 已完成",
                })
            elif stage["stage"] == "optimization":
                stage.update({
                    "status": "waiting", "canEnter": True, "canRun": True,
                    "detail": (
                        "演示仿真结果已锁定，可以体验规则代理工艺优化"
                        if demo_mode else
                        "正式仿真结果已验收，可以运行模型约束工艺搜索"
                    ),
                })
        self.repository.update_experiment_workspace(payload)
        with self._version_lock:
            self._current_versions[run.experimentId] = (
                run.modelVersion, run.officialResult.snapshotId,
            )

    def mark_simulation_started(self, run) -> None:
        payload = self.repository.get_experiment_workspace(run.experimentId)
        if payload is None:
            return
        payload["status"] = "running"
        payload["statusLabel"] = "仿真运行中"
        payload["currentStage"] = "simulation"
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        for stage in payload["stages"]:
            if stage["stage"] == "simulation":
                stage.update({"status": "running", "canEnter": True, "canRun": True, "detail": f"仿真运行 {run.runId} 正在执行"})
        self.repository.update_experiment_workspace(payload)

    def mark_optimization_started(self, run) -> None:
        payload = self.repository.get_experiment_workspace(run.experimentId)
        if payload is None:
            return
        demo_mode = payload.get("sourceType") == "sample"
        payload["status"] = "running"
        payload["statusLabel"] = "演示工艺优化中" if demo_mode else "工艺优化中"
        payload["currentStage"] = "optimization"
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        for stage in payload["stages"]:
            if stage["stage"] == "optimization":
                stage.update({
                    "status": "running", "canEnter": True, "canRun": True,
                    "detail": f"{'规则代理演示' if demo_mode else '模型约束'}优化运行 {run.runId} 正在编辑",
                })
        self.repository.update_experiment_workspace(payload)

    def apply_optimization_review(self, run) -> None:
        payload = self.repository.get_experiment_workspace(run.experimentId)
        if payload is None:
            return
        demo_mode = payload.get("sourceType") == "sample"
        approved = run.status == "completed"
        payload["status"] = "completed" if approved else "stopped"
        payload["statusLabel"] = (
            "演示工艺优化已完成" if demo_mode and approved else
            "工艺优化已完成，等待真实实验验证" if approved else
            "工艺优化已驳回"
        )
        payload["resultSummary"] = (
            f"隔离演示优化 {run.runId} 已完成人工验收；演示参数与结果未写入正式实验资产"
            if demo_mode and approved else
            f"工艺优化 {run.runId} 已完成人工验收" if approved else
            f"工艺优化 {run.runId} 已被人工驳回"
        )
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        for stage in payload["stages"]:
            if stage["stage"] == "optimization":
                stage.update({
                    "status": "completed" if approved else "stopped",
                    "canEnter": True,
                    "canRun": True,
                    "detail": (
                        f"隔离演示优化 {run.runId} 已完成；可重新开始演示"
                        if demo_mode and approved else
                        f"工艺优化 {run.runId} 已完成，等待真实实验验证"
                        if approved else
                        f"工艺优化 {run.runId} 已驳回，可重新创建方案"
                    ),
                })
        self.repository.update_experiment_workspace(payload)

    def promote_optimization_result(
        self, experiment_id: str, *, expected_model_version: str,
        expected_result_version: str, new_result_version: str,
        parameter_version: str, parameters: dict, source_run_id: str,
    ) -> None:
        """Approve a predicted process version without falsely claiming model retraining."""
        with self._version_lock:
            overview = self.get_workspace_overview(experiment_id)
            if overview is None:
                raise LookupError(experiment_id)
            if (overview.modelVersion, overview.resultVersion) != (
                expected_model_version, expected_result_version,
            ):
                raise RuntimeError("Parent model or result version changed")
            payload = self.repository.get_experiment_workspace(experiment_id)
            if payload is None:
                raise LookupError(experiment_id)
            payload["resultVersion"] = new_result_version
            payload["officialProcessParameterVersion"] = parameter_version
            payload["officialProcessParameters"] = parameters
            payload["statusLabel"] = "工艺参数版本已批准，等待真实实验验证"
            payload["resultSummary"] = (
                f"工艺参数 {parameter_version} 已人工批准；"
                "当前仍为模型预测结果，尚未产生新的真实训练标签"
            )
            payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
            self.repository.update_experiment_workspace(payload)
            self._current_versions[experiment_id] = (
                expected_model_version, new_result_version,
            )
            self._version_history.setdefault(experiment_id, []).append({
                "modelVersion": expected_model_version,
                "resultVersion": new_result_version,
                "parameterVersion": parameter_version,
                "parentModelVersion": expected_model_version,
                "parentResultVersion": expected_result_version,
                "sourceRunId": source_run_id,
                "modelRetrained": False,
            })

    def get_official_process_parameters(self, experiment_id: str) -> dict | None:
        payload = self.repository.get_experiment_workspace(experiment_id)
        return payload.get("officialProcessParameters") if payload else None

    def apply_confirmed_experimental_feedback(self, batch) -> None:
        """Expose a reviewed real-data asset without claiming that retraining already occurred."""
        if batch.status != "confirmed" or batch.qualityGate is None or not batch.qualityGate.eligible:
            raise ValueError("only confirmed retraining-eligible feedback can update the workspace")
        payload = self.repository.get_experiment_workspace(batch.experimentId)
        if payload is None:
            return
        payload["status"] = "needsReview"
        payload["statusLabel"] = "真实实验反馈已确认，可创建模型重训活动"
        payload["resultSummary"] = (
            f"批次 {batch.batchCode} 已通过反馈质量闸门；"
            f"数据资产 {batch.qualityGate.feedbackDatasetVersion} 等待人工创建重训活动"
        )
        payload["updatedAt"] = datetime.now(timezone.utc).isoformat()
        payload["validationItems"] = [
            "真实反馈数据已建立模型、参数、仿真和批次血缘",
            "重训前必须与历史训练快照合并并重新执行时间外推评估",
            "新候选模型仍需人工晋升和可靠性确认",
        ]
        payload["reliabilityMetrics"] = [
            {
                "label": "反馈批次", "value": batch.batchCode,
                "detail": batch.validationBatchId,
            },
            {
                "label": "目标重复数",
                "value": str(batch.qualityGate.targetReplicateCount),
                "detail": batch.qualityGate.targetMetric,
            },
            {
                "label": "重训资格", "value": "已通过",
                "detail": batch.qualityGate.feedbackDatasetVersion,
            },
        ]
        self.repository.update_experiment_workspace(payload)

    def reset_version_registry(self) -> None:
        with self._version_lock:
            self._current_versions.clear()
            self._version_history.clear()

    def _to_schema_keys(self, record: dict) -> dict:
        return {
            "experimentId": record["experiment_id"],
            "resultId": record["result_id"],
            "sampleCode": record["sample_code"],
            "testName": record["test_name"],
            "metricValue": record["metric_value"],
            "unit": record["unit"],
            "targetRange": record["target_range"],
            "status": record["status"],
            "riskLevel": record["risk_level"],
            "conclusion": record["conclusion"],
            "createdAt": record["created_at"],
        }

    def _status(self, test_name: str, value: float) -> str:
        if test_name in {"浊度变化", "单位样品成本指数"}:
            threshold = 10 if test_name == "浊度变化" else 75
            watch_threshold = 15 if test_name == "浊度变化" else 85
            if value <= threshold:
                return "pass"
            return "watch" if value <= watch_threshold else "fail"
        if value >= 80:
            return "pass"
        if value >= 70:
            return "watch"
        return "fail"

    def _conclusion(self, test_name: str, status: str, direction: str) -> str:
        if status == "pass":
            return f"{test_name}达到当前内部打样目标，可进入下一轮样品评审。"
        if status == "watch":
            return f"{test_name}接近目标，下一轮小试需要做梯度优化；指标方向为{direction}。"
        return f"{test_name}未达到目标，建议调整配方比例或工艺条件后重新打样。"


experiment_service = ExperimentService()
