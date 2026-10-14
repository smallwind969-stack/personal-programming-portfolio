from types import SimpleNamespace

import pytest

import app.experimental_feedback.agent as feedback_module
from app.experimental_feedback.agent import (
    ExperimentalFeedbackAgent,
    ExperimentalFeedbackConflictError,
)
from app.experimental_feedback.contracts import (
    ExperimentalFeedbackReview,
    ExperimentalMeasurementInput,
    ExperimentalValidationBatchCreate,
    ExperimentalValidationSubmission,
)
from app.schemas.optimization import OptimizationParameters
from app.services.experiment_data_store import SqliteExperimentDataStore


def _approved_run():
    parameters = OptimizationParameters(
        temperatureC=38.0,
        ph=6.9,
        cultureHours=48,
        stirringRpm=200,
    )
    return SimpleNamespace(
        runId="optimization-approved-v1",
        status="completed",
        officialParameterVersion="process-parameters-v1",
        newResultVersion="predicted-result-v1",
        baseModelVersion="model-v1",
        baseSimulationRunId="simulation-v1",
        submittedParameters=parameters,
        submittedModelEvidence=[SimpleNamespace(targetField="OD600")],
    )


@pytest.fixture()
def feedback_agent(tmp_path, monkeypatch):
    store = SqliteExperimentDataStore(tmp_path / "feedback.db", tmp_path / "objects")
    run = _approved_run()
    monkeypatch.setattr(
        feedback_module.optimization_orchestrator,
        "get_run",
        lambda experiment_id, run_id: run,
    )
    applied = []
    monkeypatch.setattr(
        feedback_module.experiment_service,
        "apply_confirmed_experimental_feedback",
        applied.append,
    )
    return ExperimentalFeedbackAgent(store), store, applied


def _create(agent: ExperimentalFeedbackAgent):
    return agent.create(
        "exp-v1",
        ExperimentalValidationBatchCreate(
            optimizationRunId="optimization-approved-v1",
            parameterVersion="process-parameters-v1",
            predictedResultVersion="predicted-result-v1",
            batchCode="LAB-2026-001",
            scale="lab",
            operator="研发员",
            plannedAt="2026-07-22T09:00:00+08:00",
        ),
    )


def _submission(*, contaminated: bool = False):
    return ExperimentalValidationSubmission(
        actualParameters=OptimizationParameters(
            temperatureC=38.1,
            ph=6.91,
            cultureHours=48,
            stirringRpm=202,
        ),
        measurements=[
            ExperimentalMeasurementInput(
                metricName="OD600",
                value=value,
                unit="AU",
                replicate=index,
                measuredAt=f"2026-07-22T1{index}:00:00+08:00",
                method="分光光度计 600 nm",
                isModelTarget=True,
            )
            for index, value in enumerate([2.91, 2.95, 2.93], start=1)
        ],
        contaminationObserved=contaminated,
        equipmentAbnormalities=[],
        notes="真实小试复测",
    )


def test_confirmed_feedback_creates_persistent_retraining_eligible_asset(feedback_agent):
    agent, store, applied = feedback_agent
    draft = _create(agent)

    submitted = agent.submit("exp-v1", draft.validationBatchId, _submission())
    assert submitted.status == "needsReview"
    assert submitted.qualityGate.eligible is False
    assert submitted.qualityGate.checks["humanConfirmed"] is False
    assert all(
        passed
        for key, passed in submitted.qualityGate.checks.items()
        if key != "humanConfirmed"
    )

    confirmed = agent.review(
        "exp-v1",
        draft.validationBatchId,
        ExperimentalFeedbackReview(
            decision="approved",
            operator="研发负责人",
            reason="测量方法、重复样和批次状态均已复核",
        ),
    )

    assert confirmed.status == "confirmed"
    assert confirmed.qualityGate.eligible is True
    assert confirmed.qualityGate.feedbackDatasetVersion.startswith("feedback-dataset-")
    assert confirmed.parentModelVersion == "model-v1"
    assert len(applied) == 1
    datasets = store.list("experimental_feedback_dataset", "exp-v1")
    assert datasets[0]["rows"][0]["OD600"] == pytest.approx(2.93)
    restored = ExperimentalFeedbackAgent(store).get("exp-v1", draft.validationBatchId)
    assert restored.status == "confirmed"


def test_contaminated_batch_cannot_pass_human_review(feedback_agent):
    agent, _store, _applied = feedback_agent
    draft = _create(agent)
    submitted = agent.submit(
        "exp-v1",
        draft.validationBatchId,
        _submission(contaminated=True),
    )
    assert submitted.qualityGate.checks["noContamination"] is False

    with pytest.raises(ExperimentalFeedbackConflictError):
        agent.review(
            "exp-v1",
            draft.validationBatchId,
            ExperimentalFeedbackReview(
                decision="approved",
                operator="研发负责人",
                reason="尝试批准受污染批次",
            ),
        )


def test_batch_lineage_must_match_approved_optimization(feedback_agent):
    agent, _store, _applied = feedback_agent
    with pytest.raises(ExperimentalFeedbackConflictError):
        agent.create(
            "exp-v1",
            ExperimentalValidationBatchCreate(
                optimizationRunId="optimization-approved-v1",
                parameterVersion="process-parameters-wrong",
                predictedResultVersion="predicted-result-v1",
                batchCode="LAB-2026-002",
                scale="lab",
                operator="研发员",
                plannedAt="2026-07-22T09:00:00+08:00",
            ),
        )


def test_parameter_values_exactly_on_tolerance_boundary_are_accepted(feedback_agent):
    agent, _store, _applied = feedback_agent
    draft = _create(agent)
    submission = _submission()
    submission.actualParameters = OptimizationParameters(
        temperatureC=37.8,
        ph=6.85,
        cultureHours=47,
        stirringRpm=195,
    )

    submitted = agent.submit("exp-v1", draft.validationBatchId, submission)

    assert submitted.qualityGate.checks["actualParametersWithinTolerance"] is True
