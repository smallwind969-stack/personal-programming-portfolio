from types import SimpleNamespace

import pytest

from app.analysis_progress.service import AnalysisProgressNotFoundError, DataAnalysisProgressService


class Source:
    def __init__(self, value=None):
        self.value = value

    def get_workspace_overview(self, experiment_id):
        return self.value

    def latest_run(self, experiment_id):
        return self.value

    def get_latest_dataset_snapshot(self, experiment_id):
        return self.value

    def list(self, experiment_id):
        return self.value or []

    def latest_report(self, experiment_id):
        return self.value


def service(*, workspace, intake=None, cleaning=None, snapshot=None, feature=None, campaigns=None, report=None):
    return DataAnalysisProgressService(
        workspace_source=Source(workspace), intake_source=Source(intake),
        cleaning_source=Source(cleaning), snapshot_source=Source(snapshot),
        feature_source=Source(feature), campaign_source=Source(campaigns),
        evaluation_source=Source(report),
    )


def test_blank_workspace_starts_at_data_intake_without_fabricated_evidence():
    projection = service(workspace=SimpleNamespace(
        experimentId="exp-blank", name="空白实验", sourceType="blank",
    )).get("exp-blank")

    assert len(projection.steps) == 6
    assert projection.currentStepKey == "dataIntake"
    assert projection.progressPercent == 0
    assert projection.steps[0].status == "running"
    assert projection.steps[0].evidenceRefs == []
    assert projection.steps[1].status == "waiting"
    assert "上传" in projection.steps[0].actionLabel


def test_sample_with_unconfirmed_intake_selects_mapping_review_as_only_current_step():
    intake = SimpleNamespace(
        runId="intake-sample", assetId="asset-sample", status="needsReview",
        transformationCount=6, pendingReviewCount=6,
    )
    projection = service(
        workspace=SimpleNamespace(experimentId="exp-sample", name="示例", sourceType="sample"),
        intake=intake,
        snapshot=SimpleNamespace(status="not_ready", snapshotId="", contentHash=""),
    ).get("exp-sample")

    assert projection.currentStepKey == "mappingReview"
    assert projection.steps[0].status == "completed"
    assert projection.steps[1].status == "needsReview"
    assert projection.steps[1].evidenceRefs == ["data-intake://intake-sample"]
    assert projection.steps[2].status == "waiting"
    assert sum(step.current for step in projection.steps) == 1
    assert projection.progressPercent > 0


def test_projection_uses_current_lineage_through_reliability_completion():
    projection = service(
        workspace=SimpleNamespace(experimentId="exp-complete", name="完整实验", sourceType="enterprise"),
        intake=SimpleNamespace(runId="intake-1", assetId="asset-1", status="confirmed", transformationCount=6, pendingReviewCount=0),
        cleaning=SimpleNamespace(runId="clean-1", status="confirmed", outputHash="hash-clean"),
        snapshot=SimpleNamespace(status="modeling_ready", snapshotId="snapshot-1", contentHash="hash-snapshot"),
        feature=SimpleNamespace(featureSetId="features-1", status="confirmed", contentHash="hash-features"),
        campaigns=[SimpleNamespace(campaignId="campaign-1", status="completed", promotion=SimpleNamespace(status="approved", promotedModelVersion="model-1"))],
        report=SimpleNamespace(reportId="report-1", status="confirmed", modelVersion="model-1"),
    ).get("exp-complete")

    assert projection.currentStepKey is None
    assert projection.progressPercent == 100
    assert all(step.status == "completed" for step in projection.steps)
    assert projection.steps[-1].evidenceRefs[-1] == "model-evaluation://report-1"


def test_projection_respects_completed_data_analysis_stage_for_isolated_demo():
    projection = service(
        workspace=SimpleNamespace(
            experimentId="exp-demo", name="隔离演示", sourceType="sample",
            stages=[SimpleNamespace(stage="dataAnalysis", status="completed")],
        ),
        intake=SimpleNamespace(runId="intake-demo", assetId="asset-demo", status="confirmed", transformationCount=6, pendingReviewCount=0),
        cleaning=SimpleNamespace(runId="clean-demo", status="completed"),
        snapshot=SimpleNamespace(status="modeling_ready", snapshotId="snapshot-demo"),
        feature=SimpleNamespace(featureSetId="features-demo", status="confirmed"),
    ).get("exp-demo")

    assert projection.currentStepKey is None
    assert projection.progressPercent == 100
    assert all(step.status == "completed" for step in projection.steps)


def test_projection_rejects_unknown_experiment():
    with pytest.raises(AnalysisProgressNotFoundError):
        service(workspace=None).get("missing")
