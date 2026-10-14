from __future__ import annotations

from app.sample_experiments.contracts import SampleExperimentCreate, SampleExperimentResult
from app.sample_experiments.templates import (
    FILE_NAME, TEMPLATE_KEY, TEMPLATE_VERSION, build_algae_culture_csv,
    template_content_hash,
)
from app.schemas.experiments import ExperimentCreateRequest, ExperimentTextFileUploadRequest
from app.services.data_collection_localization_agent import (
    DataCollectionLocalizationAgent, data_collection_localization_agent,
)
from app.services.experiment_file_service import ExperimentFileService, experiment_file_service
from app.services.experiment_service import ExperimentService, experiment_service


class SampleExperimentService:
    def __init__(
        self,
        workspace_service: ExperimentService,
        file_service: ExperimentFileService,
        intake_agent: DataCollectionLocalizationAgent,
    ) -> None:
        self.workspaceService = workspace_service
        self.fileService = file_service
        self.intakeAgent = intake_agent

    def create(self, request: SampleExperimentCreate) -> SampleExperimentResult:
        if request.templateKey != TEMPLATE_KEY:
            raise ValueError("unsupported sample experiment template")
        content = build_algae_culture_csv()
        overview = self.workspaceService.create_workspace(
            ExperimentCreateRequest(
                name=request.name or "菌藻培养工艺建模示例",
                objective="学习多设备时序数据整理、数学建模、仿真模拟与工艺优化闭环",
                batchCode="SAMPLE-V1",
                targetProduct="通用菌藻培养产物",
                targetMetrics=["OD600", "溶氧", "培养稳定性"],
                adapterPack=None,
                sourceType="blank",
                productionContext={
                    "industry": "生物制造与功能食品",
                    "processType": "菌藻培养与发酵",
                    "lineName": "隔离演示产线",
                    "materialSystem": "菌藻培养体系",
                    "criticalParameters": ["温度", "pH", "溶氧", "搅拌速度", "培养时长"],
                    "parameterDefinitions": [
                        {"key": "temperatureC", "label": "温度", "unit": "℃", "min": 20, "max": 55, "defaultValue": 37, "source": "示例模板"},
                        {"key": "ph", "label": "pH", "unit": "pH", "min": 4.5, "max": 8.5, "defaultValue": 6.8, "source": "示例模板"},
                        {"key": "custom_1", "label": "溶氧", "unit": "%", "min": 0, "max": 100, "defaultValue": 20, "source": "示例模板"},
                        {"key": "stirringRpm", "label": "搅拌速度", "unit": "rpm", "min": 0, "max": 400, "defaultValue": 150, "source": "示例模板"},
                        {"key": "cultureHours", "label": "培养时长", "unit": "小时", "min": 12, "max": 96, "defaultValue": 48, "source": "示例模板"},
                    ],
                },
            ),
            None,
            source_type="sample",
            sample_template_version=TEMPLATE_VERSION,
        )
        asset = None
        run = None
        try:
            asset = self.fileService.save_text_file(
                overview.experimentId,
                ExperimentTextFileUploadRequest(fileName=FILE_NAME, content=content),
            )
            run = self.intakeAgent.create_run(overview.experimentId, asset.assetId)
            self.workspaceService.mark_data_uploaded(overview.experimentId, run.transformationCount)
        except Exception:
            if run is not None:
                self.intakeAgent.discard_run(overview.experimentId, run.runId)
            if asset is not None:
                try:
                    self.fileService.delete_file_asset(
                        overview.experimentId, asset.assetId,
                        "sample-experiment-factory", "rollback failed sample creation",
                    )
                except LookupError:
                    pass
            self.workspaceService.delete_workspace(overview.experimentId)
            raise
        refreshed = self.workspaceService.get_workspace_overview(overview.experimentId)
        if refreshed is None:
            raise RuntimeError("sample workspace disappeared after creation")
        return SampleExperimentResult(
            overview=refreshed,
            asset=asset.model_copy(update={
                "intakeRunId": run.runId,
                "adapterApplied": run.adapterPack is not None,
                "pendingReviewCount": run.pendingReviewCount,
            }),
            intakeRunId=run.runId,
            templateKey=TEMPLATE_KEY,
            templateVersion=TEMPLATE_VERSION,
            templateContentHash=template_content_hash(content),
            disclaimer="示例数据只用于学习研发闭环，不得作为真实测量、正式模型晋升或设备控制依据。",
        )


sample_experiment_service = SampleExperimentService(
    experiment_service, experiment_file_service, data_collection_localization_agent,
)
