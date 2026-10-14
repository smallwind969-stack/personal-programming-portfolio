from types import SimpleNamespace

from app.lifecycle.service import ExperimentLifecycleProjectionService


class Source:
    def __init__(self, items=None, latest=None):
        self.items = items or []
        self.latest = latest

    def list(self, experiment_id):
        return list(self.items)

    def latest_report(self, experiment_id):
        return self.latest


def _overview(experiment_id="exp-1", analysis_status="completed"):
    return SimpleNamespace(
        experimentId=experiment_id, name="补实验闭环演示",
        stages=[SimpleNamespace(stage="dataAnalysis", status=analysis_status, detail="数学建模已完成")],
        modelVersion="model-v2",
    )


def _service(*, report=None, designs=None, executions=None, measurements=None, retraining=None, overview=None):
    overview = overview or _overview()
    return ExperimentLifecycleProjectionService(
        overview_provider=lambda experiment_id: overview if experiment_id == overview.experimentId else None,
        archive_provider=lambda: SimpleNamespace(experiments=[SimpleNamespace(experimentId=overview.experimentId)]),
        evaluation_source=Source(latest=report),
        design_source=Source(designs), execution_source=Source(executions),
        measurement_source=Source(measurements), retraining_source=Source(retraining),
    )


def test_projection_tracks_partial_current_plan_without_using_historical_retraining():
    report = SimpleNamespace(
        reportId="report-v2", modelVersion="model-v2", status="needsReview",
        recommendedAdmission=False, admissionAllowed=False, reliabilityScore=0.63,
        admissionReasons=["可靠性低于准入线"],
    )
    candidates = ["candidate-1", "candidate-2", "candidate-3"]
    design = SimpleNamespace(
        runId="design-v2", reportId="report-v2", modelVersion="model-v2",
        status="approved", planVersion="plan-v2", selectedCandidateIds=candidates,
    )
    execution = SimpleNamespace(
        batchId="execution-1", planVersion="plan-v2", candidateId="candidate-1",
        status="completed", batchCode="SUP-01",
    )
    measurement = SimpleNamespace(
        measurementBatchId="measurement-1", executionBatchId="execution-1",
        status="draft", qualityGate=None,
    )
    historical_retraining = SimpleNamespace(
        runId="retrain-old", status="completed", parentModelVersion="model-v1",
        feedbackDatasetVersions=["feedback-old"], progressPercent=100,
    )
    lifecycle = _service(
        report=report, designs=[design], executions=[execution],
        measurements=[measurement], retraining=[historical_retraining],
    ).get("exp-1")

    assert [stage.stageKey for stage in lifecycle.stages] == [
        "dataAnalysis", "modelEvaluation", "supplementaryDesign",
        "supplementaryExecution", "measurementFeedback", "feedbackRetraining",
    ]
    assert lifecycle.currentStageKey == "supplementaryExecution"
    execution_stage = lifecycle.stages[3]
    assert execution_stage.status == "running"
    assert execution_stage.progressPercent == 33
    assert execution_stage.itemCounts == {"total": 3, "completed": 1, "pending": 2}
    assert "1/3" in execution_stage.summary
    measurement_stage = lifecycle.stages[4]
    assert measurement_stage.status == "waiting"
    assert "真实测量" in "".join(measurement_stage.waitingReasons)
    retraining_stage = lifecycle.stages[5]
    assert retraining_stage.status == "waiting"
    assert "retrain-old" not in retraining_stage.evidenceRefs


def test_downstream_model_report_proves_data_analysis_complete_despite_stale_workspace_flag():
    report = SimpleNamespace(
        reportId="report-v2", modelVersion="model-v2", status="needsReview",
        recommendedAdmission=False, admissionAllowed=False, reliabilityScore=0.63,
        admissionReasons=["需要补实验"],
    )
    design = SimpleNamespace(
        runId="design-v2", reportId="report-v2", modelVersion="model-v2",
        status="approved", planVersion="plan-v2", selectedCandidateIds=["candidate-1"],
    )
    execution = SimpleNamespace(
        batchId="execution-1", planVersion="plan-v2", candidateId="candidate-1",
        status="planned", batchCode="SUP-01",
    )

    lifecycle = _service(
        report=report, designs=[design], executions=[execution],
        overview=_overview(analysis_status="needsReview"),
    ).get("exp-1")

    assert lifecycle.stages[0].status == "completed"
    assert lifecycle.currentStageKey == "supplementaryExecution"


def test_confirmed_current_measurement_is_matched_to_retraining_by_feedback_version():
    report = SimpleNamespace(reportId="report-v2", modelVersion="model-v2", status="needsReview", recommendedAdmission=False, admissionAllowed=False, reliabilityScore=0.63, admissionReasons=[])
    design = SimpleNamespace(runId="design-v2", reportId="report-v2", modelVersion="model-v2", status="approved", planVersion="plan-v2", selectedCandidateIds=["candidate-1"])
    execution = SimpleNamespace(batchId="execution-1", planVersion="plan-v2", candidateId="candidate-1", status="completed", batchCode="SUP-01")
    gate = SimpleNamespace(feedbackDatasetVersion="feedback-current", eligible=True)
    measurement = SimpleNamespace(measurementBatchId="measurement-1", executionBatchId="execution-1", status="confirmed", qualityGate=gate)
    retraining = SimpleNamespace(runId="retrain-current", status="needsReview", parentModelVersion="model-v2", feedbackDatasetVersions=["feedback-current", "feedback-2", "feedback-3"], progressPercent=100)

    lifecycle = _service(report=report, designs=[design], executions=[execution], measurements=[measurement], retraining=[retraining]).get("exp-1")

    assert lifecycle.stages[3].status == "completed"
    assert lifecycle.stages[4].status == "completed"
    assert lifecycle.stages[5].status == "needsReview"
    assert "retraining://retrain-current" in lifecycle.stages[5].evidenceRefs
    assert lifecycle.currentStageKey == "feedbackRetraining"


def test_admitted_model_marks_supplementary_branch_not_required():
    report = SimpleNamespace(
        reportId="report-good", modelVersion="model-v2", status="confirmed",
        recommendedAdmission=True, admissionAllowed=True, reliabilityScore=0.88,
        admissionReasons=[],
    )
    lifecycle = _service(report=report).get("exp-1")

    assert lifecycle.stages[1].status == "completed"
    assert [stage.status for stage in lifecycle.stages[2:]] == ["notRequired"] * 4
    assert lifecycle.overallStatus == "completed"
    assert lifecycle.progressPercent == 100


def test_empty_downstream_workflow_reports_first_waiting_stage_and_reasons():
    lifecycle = _service(report=None, overview=_overview(analysis_status="running")).get("exp-1")

    assert lifecycle.currentStageKey == "dataAnalysis"
    assert lifecycle.stages[0].status == "running"
    assert lifecycle.stages[1].status == "waiting"
    assert lifecycle.stages[1].waitingReasons


def test_summary_projection_is_lightweight_and_preserves_next_action():
    report = SimpleNamespace(reportId="report-v2", modelVersion="model-v2", status="needsReview", recommendedAdmission=False, admissionAllowed=False, reliabilityScore=0.63, admissionReasons=["需要补实验"])
    summaries = _service(report=report).list_summaries()

    assert len(summaries) == 1
    assert summaries[0].experimentId == "exp-1"
    assert summaries[0].currentStageKey == "modelEvaluation"
    assert summaries[0].route.endswith("/analysis")
    assert summaries[0].nextAction
