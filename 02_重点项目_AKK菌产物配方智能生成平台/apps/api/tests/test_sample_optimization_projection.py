from types import SimpleNamespace

from app.repositories.sqlite_repository import SqliteRepository
from app.schemas.experiments import ExperimentCreateRequest
from app.services.experiment_service import ExperimentService


def test_completed_sample_optimization_updates_archive_and_stage_projection(tmp_path) -> None:
    service = ExperimentService(SqliteRepository(tmp_path / "workspace.db"))
    overview = service.create_workspace(
        ExperimentCreateRequest(
            name="隔离演示实验", objective="验证演示状态同步", targetProduct="示例产物",
            targetMetrics=["od600"], sourceType="blank",
        ),
        None,
    )
    payload = service.repository.get_experiment_workspace(overview.experimentId)
    payload["sourceType"] = "sample"
    payload["currentStage"] = "optimization"
    payload["status"] = "running"
    for stage in payload["stages"]:
        if stage["stage"] == "optimization":
            stage.update({"status": "running", "canEnter": True, "canRun": True})
    service.repository.update_experiment_workspace(payload)

    run = SimpleNamespace(
        experimentId=overview.experimentId, runId="optimization-demo-1", status="completed",
        officialParameterVersion="demo-process-parameters-v1",
        newResultVersion="demo-predicted-result-v1",
    )
    service.apply_optimization_review(run)

    updated = service.get_workspace_overview(overview.experimentId)
    assert updated.status == "completed"
    assert updated.statusLabel == "演示工艺优化已完成"
    assert updated.resultVersion is None
    optimization = next(stage for stage in updated.stages if stage.stage == "optimization")
    assert optimization.status == "completed"
    assert "隔离演示" in optimization.detail
