from types import SimpleNamespace

from app.human_actions.service import HumanActionCenterService


class ReportSource:
    def __init__(self, report): self.report = report
    def latest_report(self, experiment_id): return self.report


class ListSource:
    def __init__(self, items=None): self.items = items or []
    def list(self, experiment_id): return list(self.items)


def _service(*, report=None, designs=None, executions=None, measurements=None, retraining=None):
    return HumanActionCenterService(
        archive_provider=lambda: SimpleNamespace(experiments=[SimpleNamespace(experimentId="exp-1", name="补实验闭环演示")]),
        evaluation_source=ReportSource(report), design_source=ListSource(designs),
        execution_source=ListSource(executions), measurement_source=ListSource(measurements),
        retraining_source=ListSource(retraining),
    )


def _report(**changes):
    values = dict(
        reportId="report-v2", modelVersion="model-v2", status="needsReview",
        recommendedAdmission=False, admissionAllowed=False,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def _design(**changes):
    values = dict(
        runId="design-v2", reportId="report-v2", modelVersion="model-v2",
        status="approved", planVersion="plan-v2",
        selectedCandidateIds=["candidate-1", "candidate-2", "candidate-3"],
        candidates=[
            SimpleNamespace(candidateId=f"candidate-{index}", displayName=f"方案 {index}")
            for index in [1, 2, 3]
        ],
        reviewReason=None,
    )
    values.update(changes)
    return SimpleNamespace(**values)


def test_action_center_projects_missing_executions_and_draft_measurement_only():
    execution = SimpleNamespace(
        batchId="execution-1", planVersion="plan-v2", candidateId="candidate-1",
        status="completed", batchCode="SUP-01",
    )
    measurement = SimpleNamespace(
        measurementBatchId="measurement-1", executionBatchId="execution-1",
        status="draft", qualityGate=None,
    )
    historical = SimpleNamespace(
        runId="retrain-old", status="needsReview", feedbackDatasetVersions=["feedback-old"],
    )
    center = _service(
        report=_report(), designs=[_design()], executions=[execution],
        measurements=[measurement], retraining=[historical],
    ).get()

    assert center.totalCount == 3
    assert [item.actionType for item in center.items].count("createExecution") == 2
    assert [item.actionType for item in center.items].count("enterMeasurements") == 1
    assert all("retrain-old" not in item.sourceRef for item in center.items)
    assert len({item.actionId for item in center.items}) == 3
    assert center.experimentActionCounts == {"exp-1": 3}


def test_design_waiting_review_replaces_execution_actions():
    center = _service(
        report=_report(), designs=[_design(status="needsReview", planVersion=None, selectedCandidateIds=[])],
    ).get()

    assert [item.actionType for item in center.items] == ["reviewDesign"]
    assert center.items[0].priority == "medium"


def test_reliable_model_waiting_signature_creates_high_priority_review():
    center = _service(
        report=_report(recommendedAdmission=True, admissionAllowed=False),
    ).get()

    assert [item.actionType for item in center.items] == ["reviewReliability"]
    assert center.items[0].priority == "high"


def test_measurement_review_and_lineage_matched_retraining_review_are_high_priority():
    execution = SimpleNamespace(batchId="execution-1", planVersion="plan-v2", candidateId="candidate-1", status="completed", batchCode="SUP-01")
    execution_2 = SimpleNamespace(batchId="execution-2", planVersion="plan-v2", candidateId="candidate-2", status="completed", batchCode="SUP-02")
    measurement = SimpleNamespace(measurementBatchId="measurement-1", executionBatchId="execution-1", status="needsReview", qualityGate=SimpleNamespace(feedbackDatasetVersion=None, eligible=False))
    confirmed = SimpleNamespace(measurementBatchId="measurement-2", executionBatchId="execution-2", status="confirmed", qualityGate=SimpleNamespace(feedbackDatasetVersion="feedback-current", eligible=True))
    retraining = SimpleNamespace(runId="retrain-current", status="needsReview", feedbackDatasetVersions=["feedback-current", "feedback-2", "feedback-3"])
    center = _service(
        report=_report(),
        designs=[_design(selectedCandidateIds=["candidate-1", "candidate-2"], candidates=[SimpleNamespace(candidateId="candidate-1", displayName="方案 1"), SimpleNamespace(candidateId="candidate-2", displayName="方案 2")])],
        executions=[execution, execution_2], measurements=[measurement, confirmed], retraining=[retraining],
    ).get()

    assert {item.actionType for item in center.items} == {"reviewMeasurements", "reviewRetraining"}
    assert all(item.priority == "high" for item in center.items)
    assert center.highPriorityCount == 2


def test_missing_current_design_creates_generation_action_not_historical_actions():
    old_design = _design(runId="design-old", reportId="report-old", modelVersion="model-v1")
    center = _service(report=_report(), designs=[old_design]).get()

    assert [item.actionType for item in center.items] == ["generateDesign"]
    assert center.items[0].sourceRef == "model-evaluation://report-v2"


def test_action_center_filters_by_priority_stage_and_experiment_without_mutating_sources():
    service = _service(
        report=_report(recommendedAdmission=True, admissionAllowed=False),
    )

    matching = service.get(priority="high", stage_key="modelEvaluation", experiment_id="exp-1")
    wrong_stage = service.get(priority="high", stage_key="measurementFeedback")
    wrong_experiment = service.get(experiment_id="exp-other")

    assert matching.totalCount == 1
    assert matching.items[0].actionType == "reviewReliability"
    assert wrong_stage.totalCount == 0
    assert wrong_experiment.totalCount == 0
    assert matching.experimentActionCounts == {"exp-1": 1}
