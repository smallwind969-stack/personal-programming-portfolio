from types import SimpleNamespace

import pytest

from app.services.experiment_data_store import SqliteExperimentDataStore
from app.supplementary_design.agent import (
    SupplementaryExperimentDesignAgent,
    SupplementaryExperimentDesignConflictError,
)
from app.supplementary_design.contracts import (
    SupplementaryDesignCreate,
    SupplementaryDesignReview,
    SupplementaryDesignSelection,
)


class EvaluationSource:
    def __init__(self):
        self.report = SimpleNamespace(
            reportId="model-eval-v2",
            experimentId="exp-1",
            modelVersion="model-v2",
            inputFingerprint="sha256:report-input",
            status="needsReview",
            recommendedAdmission=False,
            reliabilityScore=0.63,
            admissionReasons=["分布覆盖不足", "综合可靠性低于准入线"],
            predictionInterval=SimpleNamespace(margin=0.18),
            residualDiagnostics=SimpleNamespace(
                meanResidual=0.08, residualStd=0.22,
                meanAbsoluteResidual=0.16, maxAbsoluteResidual=0.41,
                lag1Autocorrelation=0.2, predictionResidualCorrelation=0.1,
            ),
            driftDiagnostics=[
                SimpleNamespace(feature="temperature_c", standardizedMeanShift=2.8, holdoutRangeCoverage=0.55, severity="high", trainMean=37.0, holdoutMean=37.8),
                SimpleNamespace(feature="ph", standardizedMeanShift=1.1, holdoutRangeCoverage=0.82, severity="low", trainMean=6.8, holdoutMean=6.9),
                SimpleNamespace(feature="agitation_rpm", standardizedMeanShift=1.8, holdoutRangeCoverage=0.75, severity="medium", trainMean=190.0, holdoutMean=205.0),
            ],
            featureEffects=[
                SimpleNamespace(feature="temperature_c", effect=0.8, normalizedImportance=0.5, method="permutation"),
                SimpleNamespace(feature="ph", effect=0.3, normalizedImportance=0.2, method="permutation"),
                SimpleNamespace(feature="agitation_rpm", effect=0.6, normalizedImportance=0.3, method="permutation"),
            ],
        )

    def list_reports(self, experiment_id):
        return [self.report]

    def latest_report(self, experiment_id):
        return self.report


class Registry:
    def __init__(self):
        self.record = SimpleNamespace(
            modelVersion="model-v2", experimentId="exp-1",
            campaignId="campaign-v2", trialId="trial-v2",
            artifactFingerprint="sha256:model-v2", datasetFingerprint="sha256:data-v2",
            featureNames=["temperature_c", "ph", "agitation_rpm"], targetField="od600",
            featureRanges={
                "temperature_c": SimpleNamespace(min=36.0, max=38.0),
                "ph": SimpleNamespace(min=6.6, max=7.0),
                "agitation_rpm": SimpleNamespace(min=180.0, max=220.0),
            },
        )

    def latest(self, experiment_id):
        return self.record

    def get(self, experiment_id, model_version):
        return self.record if model_version == self.record.modelVersion else None


class ResearchSource:
    def get(self, experiment_id, campaign_id):
        card = {
            "trainFeatureStats": {
                "temperature_c": {"mean": 37.0, "std": 0.55},
                "ph": {"mean": 6.8, "std": 0.12},
                "agitation_rpm": {"mean": 190.0, "std": 12.0},
            },
            "holdoutFeatureStats": {
                "temperature_c": {"mean": 37.8, "std": 0.12},
                "ph": {"mean": 6.9, "std": 0.05},
                "agitation_rpm": {"mean": 205.0, "std": 5.0},
            },
        }
        return SimpleNamespace(
            trials=[SimpleNamespace(trialId="trial-v2", modelCard=card)]
        )


@pytest.fixture()
def setup_agent(tmp_path):
    store = SqliteExperimentDataStore(tmp_path / "design.db", tmp_path / "objects")
    evaluation = EvaluationSource()
    registry = Registry()
    inference = SimpleNamespace(predict=lambda experiment_id, values, model_version, allow_extrapolation: SimpleNamespace(prediction=sum(values.values()) / 100))
    agent = SupplementaryExperimentDesignAgent(
        store=store,
        evaluation_agent=evaluation,
        registry=registry,
        research_service=ResearchSource(),
        binding_service=SimpleNamespace(store=SimpleNamespace(latest=lambda *_: None)),
        inference_service=inference,
        official_parameters_provider=lambda _: {
            "temperatureC": 37.0, "ph": 6.8,
            "cultureHours": 48, "stirringRpm": 190,
        },
    )
    return agent, store, evaluation, registry


def _request():
    return SupplementaryDesignCreate(
        commandId="supplement-command-v1",
        reportId="model-eval-v2",
    )


def test_agent_generates_three_distinct_in_range_evidence_driven_candidates(setup_agent):
    agent, _store, _evaluation, registry = setup_agent

    run = agent.create("exp-1", _request())

    assert run.status == "needsReview"
    assert run.modelVersion == "model-v2"
    assert run.reportId == "model-eval-v2"
    assert {item.strategyKey for item in run.candidates} == {
        "coverageRecovery", "boundaryValidation", "residualCorrection",
    }
    assert len({tuple(item.modelFeatureValues.values()) for item in run.candidates}) == 3
    for candidate in run.candidates:
        for feature, value in candidate.modelFeatureValues.items():
            allowed = registry.record.featureRanges[feature]
            assert allowed.min <= value <= allowed.max
        assert candidate.addressesGaps
        assert candidate.evidence
        assert 0 <= candidate.informationGainScore <= 1
        assert candidate.extrapolated is False
        assert candidate.processParameters.cultureHours == 48


def test_create_is_idempotent_and_persists_run(setup_agent):
    agent, store, evaluation, registry = setup_agent
    first = agent.create("exp-1", _request())
    second = agent.create("exp-1", _request())
    recovered = SupplementaryExperimentDesignAgent(
        store, evaluation, registry, ResearchSource(),
        SimpleNamespace(store=SimpleNamespace(latest=lambda *_: None)),
        SimpleNamespace(predict=lambda *args, **kwargs: SimpleNamespace(prediction=1.0)),
        lambda _: {"temperatureC": 37, "ph": 6.8, "cultureHours": 48, "stirringRpm": 190},
    )

    assert first.runId == second.runId
    assert recovered.get("exp-1", first.runId).requestFingerprint == first.requestFingerprint


def test_selection_and_human_approval_create_immutable_plan_version(setup_agent):
    agent, _store, _evaluation, _registry = setup_agent
    run = agent.create("exp-1", _request())
    selected = agent.select(
        "exp-1", run.runId,
        SupplementaryDesignSelection(candidateIds=[run.candidates[0].candidateId, run.candidates[2].candidateId]),
    )
    assert len(selected.selectedCandidateIds) == 2

    approved = agent.review(
        "exp-1", run.runId,
        SupplementaryDesignReview(
            decision="approved", operator="研发负责人",
            reason="覆盖缺口与残差复测方案均有必要",
        ),
    )

    assert approved.status == "approved"
    assert approved.planVersion.startswith("supplement-plan-")
    assert approved.selectedCandidateIds == selected.selectedCandidateIds
    assert approved.disclaimer.endswith("不直接控制设备。")


def test_approval_is_blocked_when_model_or_report_changed(setup_agent):
    agent, _store, evaluation, registry = setup_agent
    run = agent.create("exp-1", _request())
    agent.select("exp-1", run.runId, SupplementaryDesignSelection(candidateIds=[run.candidates[0].candidateId]))
    registry.record = SimpleNamespace(modelVersion="model-v3", experimentId="exp-1")

    with pytest.raises(SupplementaryExperimentDesignConflictError, match="changed"):
        agent.review(
            "exp-1", run.runId,
            SupplementaryDesignReview(
                decision="approved", operator="研发负责人",
                reason="尝试批准过期设计",
            ),
        )


def test_reliable_model_does_not_generate_unnecessary_supplement(setup_agent):
    agent, _store, evaluation, _registry = setup_agent
    evaluation.report.recommendedAdmission = True

    with pytest.raises(SupplementaryExperimentDesignConflictError, match="already recommends admission"):
        agent.create("exp-1", _request())
