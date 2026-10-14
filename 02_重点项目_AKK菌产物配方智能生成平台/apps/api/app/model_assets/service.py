from __future__ import annotations

from app.model_assets.contracts import (
    ModelAssetDetail,
    ModelAssetEvaluation,
    ModelAssetSummary,
    ModelSimulationUsage,
)


class ModelAssetCenterService:
    def __init__(
        self, *, registry, archive_provider, evaluation_source,
        binding_store, simulation_source, artifact_store, knowledge_usage_source=None,
    ) -> None:
        self.registry = registry
        self.archiveProvider = archive_provider
        self.evaluationSource = evaluation_source
        self.bindingStore = binding_store
        self.simulationSource = simulation_source
        self.artifactStore = artifact_store
        self.knowledgeUsageSource = knowledge_usage_source

    def list_assets(self) -> list[ModelAssetSummary]:
        assets: list[ModelAssetSummary] = []
        for experiment in self.archiveProvider().experiments:
            records = self.registry.list(experiment.experimentId)
            latest = self.registry.latest(experiment.experimentId)
            reports = self.evaluationSource.list_reports(experiment.experimentId)
            runs = self.simulationSource.list_runs(experiment.experimentId)
            for record in records:
                report = self._evaluation(record.modelVersion, reports)
                binding = self.bindingStore.latest(experiment.experimentId, record.modelVersion)
                usages = [run for run in runs if run.modelVersion == record.modelVersion]
                assets.append(ModelAssetSummary(
                    experimentId=record.experimentId,
                    experimentName=experiment.name,
                    modelVersion=record.modelVersion,
                    targetField=record.targetField,
                    modelType=record.modelType,
                    approvedAt=record.approvedAt,
                    approvedBy=record.approvedBy,
                    status=record.status,
                    latest=bool(latest and latest.modelVersion == record.modelVersion),
                    datasetSnapshotId=record.datasetSnapshotId,
                    featureCount=len(record.featureNames),
                    metrics=record.metrics,
                    artifactVerified=self._artifact_verified(record.artifactFingerprint),
                    evaluationStatus=report.status if report else None,
                    reliabilityScore=report.reliabilityScore if report else None,
                    bindingVersion=binding.bindingVersion if binding else None,
                    simulationUsageCount=len(usages),
                ))
        assets.sort(key=lambda item: (item.approvedAt, item.modelVersion), reverse=True)
        return assets

    def get_detail(self, experiment_id: str, model_version: str) -> ModelAssetDetail:
        record = self.registry.get(experiment_id, model_version)
        if record is None:
            raise LookupError("model asset was not found")
        archive_item = next(
            (item for item in self.archiveProvider().experiments if item.experimentId == experiment_id),
            None,
        )
        reports = self.evaluationSource.list_reports(experiment_id)
        report = self._evaluation(model_version, reports)
        latest = self.registry.latest(experiment_id)
        binding = self.bindingStore.latest(experiment_id, model_version)
        usages = [
            ModelSimulationUsage(
                runId=run.runId, version=run.version, status=run.status,
                bindingVersions=run.bindingVersions,
                reliabilityScore=run.reliabilityScore,
                officialSnapshotId=run.officialResult.snapshotId if run.officialResult else None,
                updatedAt=run.updatedAt,
            )
            for run in self.simulationSource.list_runs(experiment_id)
            if run.modelVersion == model_version
        ]
        usages.sort(key=lambda item: (item.updatedAt, item.version), reverse=True)
        knowledge_usages = []
        if self.knowledgeUsageSource is not None:
            knowledge_usages = [
                usage for usage in self.knowledgeUsageSource.list(experiment_id=experiment_id)
                if usage.targetVersion in {model_version, record.datasetSnapshotId}
            ]
        return ModelAssetDetail(
            experimentName=archive_item.name if archive_item else experiment_id,
            latest=bool(latest and latest.modelVersion == model_version),
            artifactVerified=self._artifact_verified(record.artifactFingerprint),
            record=record,
            evaluationReport=report,
            binding=binding,
            simulationUsages=usages,
            knowledgeUsages=knowledge_usages,
        )

    @staticmethod
    def _evaluation(model_version: str, reports) -> ModelAssetEvaluation | None:
        report = next((item for item in reversed(reports) if item.modelVersion == model_version), None)
        if report is None:
            return None
        return ModelAssetEvaluation(
            reportId=report.reportId, status=report.status,
            reliabilityScore=report.reliabilityScore,
            reliabilityGrade=report.reliabilityGrade,
            recommendedAdmission=report.recommendedAdmission,
            admissionAllowed=report.admissionAllowed,
            artifactVerified=report.artifactVerified,
        )

    def _artifact_verified(self, fingerprint: str) -> bool:
        try:
            return bool(self.artifactStore.verify(fingerprint))
        except (OSError, ValueError):
            return False
