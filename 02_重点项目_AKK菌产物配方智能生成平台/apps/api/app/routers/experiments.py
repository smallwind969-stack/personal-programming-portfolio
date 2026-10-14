from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.schemas.experiments import (
    ExperimentAlignmentPreviewResponse,
    ExperimentArchiveResponse,
    ExperimentCreateRequest,
    ExperimentBatchFileUploadRequest,
    ExperimentBatchFileUploadResponse,
    ExperimentCleaningPreviewResponse,
    CleaningAlignmentConfig,
    CleaningAlignmentReviewRequest,
    CleaningAlignmentRun,
    FeatureEngineeringConfig,
    FeatureEngineeringConfirmRequest,
    FeatureEngineeringRun,
    DataCollectionLocalizationRun,
    ExperimentConfirmFieldMappingsRequest,
    ExperimentConfirmedFieldMappingSet,
    ExperimentDatasetSnapshot,
    ExperimentFieldDictionary,
    ExperimentFieldDictionaryUpsertRequest,
    ExperimentFeaturePreviewResponse,
    ExperimentModelingPlanPreview,
    ExperimentResearchBriefSummary,
    ExperimentSimulationInputSummary,
    ExperimentTrainingResultSummary,
    ExperimentTrainingTaskPreview,
    ExperimentWorkspaceOverview,
    ExperimentAgentRun,
    AgentGuidancePreview,
    AgentGuidancePreviewRequest,
    AgentGuidanceApplyRequest,
    AgentRunRestartRequest,
    AgentRunAdvanceRequest,
    HumanReviewDecisionRequest,
    ExperimentFileAuditSummary,
    ExperimentFileAuditTimeline,
    ExperimentFileAsset,
    ExperimentAssetIntegrityResult,
    ExperimentFileDeleteRequest,
    ExperimentFileDeleteResult,
    ExperimentFieldMappingSuggestionResponse,
    ExperimentRecord,
    ExperimentTextFileUploadRequest,
    SchemaRecognitionRun,
    SchemaRecognitionRunCreateRequest,
    ResultInterpretationRun,
    ResultInterpretationRunCreateRequest,
)
from app.services.experiment_file_service import experiment_file_service
from app.services.experiment_service import experiment_service
from app.services.feature_binding_advisor_agent import device_adapter_pack_service
from app.services.data_collection_localization_agent import data_collection_localization_agent
from app.services.cleaning_alignment_agent import cleaning_alignment_agent
from app.services.feature_engineering_agent import feature_engineering_agent
from app.model_evaluation.agent import model_evaluation_agent
from app.model_evaluation.contracts import (
    ModelEvaluationReport,
    ModelEvaluationReviewRequest,
)
from app.services.agent_orchestrator import (
    AgentRunConflictError,
    AgentRunNotFoundError,
    agent_orchestrator,
)
from app.services.schema_recognition_agent import schema_recognition_agent
from app.services.result_interpretation_agent import result_interpretation_agent
from app.product_innovation.contracts import (
    ProductInnovationRun,
    ProductInnovationRunCreateRequest,
    ProductRequirementConfirmRequest,
    ProductRequirementVersion,
)
from app.services.product_innovation_agent import product_innovation_agent
from app.services.product_requirement_registry import (
    ProductRequirementConflictError,
    ProductRequirementNotFoundError,
    product_requirement_registry,
)
from app.schemas.agent_tasks import AgentTaskCenter
from app.services.agent_task_center_service import AgentTaskCenterNotFoundError, agent_task_center_service
from app.schemas.agent_commands import AgentCommandEnqueueRequest, AgentCommandTask, UnifiedAgentCommandEnqueueRequest
from app.agent_queue.sqlite_queue import AgentCommandConflictError
from app.services.agent_command_service import agent_command_service
from app.research.contracts import ResearchCampaign, ResearchCampaignCreate, ResearchIterationRequest, ResearchPromotionRequest, ResearchTrialEnqueueRequest
from app.research.service import ResearchCampaignConflictError, ResearchCampaignNotFoundError, research_campaign_service
from app.schemas.simulation import (
    ExperimentSimulationRun,
    SimulationPredictRequest,
    SimulationTrialSnapshot,
    SimulationFailureRequest,
)
from app.services.simulation_run_orchestrator import (
    SimulationRunConflictError,
    SimulationRunNotFoundError,
    simulation_run_orchestrator,
)
from app.schemas.optimization import (
    ExperimentOptimizationRun,
    OptimizationReviewRequest,
    OptimizationSelectionRequest,
)
from app.services.optimization_orchestrator import (
    OptimizationConflictError,
    OptimizationNotFoundError,
    optimization_orchestrator,
)
from app.experimental_feedback.contracts import (
    ExperimentalFeedbackReview,
    ExperimentalValidationBatch,
    ExperimentalValidationBatchCreate,
    ExperimentalValidationSubmission,
)
from app.experimental_feedback.agent import (
    ExperimentalFeedbackConflictError,
    ExperimentalFeedbackNotFoundError,
    experimental_feedback_agent,
)
from app.feedback_retraining.contracts import (
    FeedbackRetrainingCreate,
    FeedbackRetrainingReview,
    FeedbackRetrainingRun,
)
from app.feedback_retraining.agent import (
    FeedbackRetrainingConflictError,
    FeedbackRetrainingNotFoundError,
    feedback_retraining_agent,
)
from app.feedback_retraining.dataset import (
    FeedbackRetrainingDatasetConflictError,
    FeedbackRetrainingDatasetNotFoundError,
)
from app.supplementary_design.contracts import (
    SupplementaryDesignCreate,
    SupplementaryDesignReview,
    SupplementaryDesignSelection,
    SupplementaryExperimentDesignRun,
)
from app.supplementary_design.agent import (
    SupplementaryExperimentDesignConflictError,
    SupplementaryExperimentDesignNotFoundError,
    supplementary_experiment_design_agent,
)
from app.supplementary_execution.contracts import (
    SupplementaryExecutionAssetAttach,
    SupplementaryExecutionBatch,
    SupplementaryExecutionBatchCreate,
    SupplementaryExecutionReview,
    SupplementaryExecutionStart,
    SupplementaryExecutionStepUpdate,
)
from app.supplementary_execution.agent import (
    SupplementaryExperimentExecutionConflictError,
    SupplementaryExperimentExecutionNotFoundError,
    supplementary_experiment_execution_agent,
)
from app.supplementary_measurement.contracts import (
    SupplementaryMeasurementBatch,
    SupplementaryMeasurementBatchCreate,
    SupplementaryMeasurementReview,
    SupplementaryMeasurementSubmission,
)
from app.supplementary_measurement.agent import (
    SupplementaryMeasurementHandoffConflictError,
    SupplementaryMeasurementHandoffNotFoundError,
    supplementary_measurement_handoff_agent,
)
from app.lifecycle.contracts import (
    ExperimentLifecycleOverview,
    ExperimentLifecycleSummary,
)
from app.lifecycle.service import (
    ExperimentLifecycleNotFoundError,
    experiment_lifecycle_projection_service,
)
from app.human_actions.contracts import HumanActionCenter
from app.human_actions.service import human_action_center_service
from app.sample_experiments.contracts import SampleExperimentCreate, SampleExperimentResult
from app.sample_experiments.service import sample_experiment_service
from app.analysis_progress.contracts import DataAnalysisProgress
from app.analysis_progress.service import (
    AnalysisProgressNotFoundError,
    data_analysis_progress_service,
)
from app.demo_models.contracts import DemoModelAdmission, DemoModelAdmissionCreate
from app.demo_models.service import demo_model_admission_service
from app.research_reports.contracts import ResearchReport, ResearchReportCreateRequest, ResearchReportReviewRequest
from app.research_reports.runtime import research_report_service
from app.enterprise_knowledge.contracts import EnterpriseKnowledgeEntry
from app.enterprise_knowledge.runtime import enterprise_knowledge_service
from app.enterprise_knowledge.runtime import enterprise_knowledge_usage_service
from app.enterprise_knowledge.usage import EnterpriseKnowledgeUsage, EnterpriseKnowledgeUsageRequest

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/enterprise-knowledge", response_model=list[EnterpriseKnowledgeEntry])
def list_enterprise_knowledge(
    experiment_id: str | None = Query(default=None, alias="experimentId"),
) -> list[EnterpriseKnowledgeEntry]:
    return enterprise_knowledge_service.list(experiment_id=experiment_id)


@router.get("/{experiment_id}/knowledge-usage", response_model=list[EnterpriseKnowledgeUsage])
def list_knowledge_usage(experiment_id: str) -> list[EnterpriseKnowledgeUsage]:
    return enterprise_knowledge_usage_service.list(experiment_id=experiment_id)


@router.post("/{experiment_id}/knowledge-usage", response_model=EnterpriseKnowledgeUsage)
def register_knowledge_usage(experiment_id: str, payload: EnterpriseKnowledgeUsageRequest) -> EnterpriseKnowledgeUsage:
    try:
        return enterprise_knowledge_usage_service.register(
            experiment_id, knowledge_ids=payload.knowledgeIds, purpose=payload.purpose,
            target_version=payload.targetVersion, operator=payload.operator, note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{experiment_id}/research-reports", response_model=ResearchReport)
def create_research_report(experiment_id: str, payload: ResearchReportCreateRequest) -> ResearchReport:
    try:
        return research_report_service.create(experiment_id, payload.commandId)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{experiment_id}/research-reports", response_model=list[ResearchReport])
def list_research_reports(experiment_id: str) -> list[ResearchReport]:
    return research_report_service.list(experiment_id)


@router.post("/{experiment_id}/research-reports/{report_id}/review", response_model=ResearchReport)
def review_research_report(
    experiment_id: str, report_id: str, payload: ResearchReportReviewRequest,
) -> ResearchReport:
    try:
        return research_report_service.review(
            experiment_id, report_id, operator=payload.operator, reason=payload.reason,
            approved_statement_ids=payload.approvedStatementIds,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{experiment_id}/research-reports/{report_id}/knowledge-deposit",
    response_model=list[EnterpriseKnowledgeEntry],
)
def deposit_research_report_knowledge(
    experiment_id: str, report_id: str,
) -> list[EnterpriseKnowledgeEntry]:
    try:
        return enterprise_knowledge_service.deposit(experiment_id, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{experiment_id}/research-reports/{report_id}/markdown", response_class=PlainTextResponse)
def download_research_report_markdown(experiment_id: str, report_id: str) -> PlainTextResponse:
    try:
        report = research_report_service.get(experiment_id, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PlainTextResponse(
        research_report_service.render_markdown(report),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.md"'},
    )


@router.get("/{experiment_id}/research-reports/{report_id}/json", response_class=JSONResponse)
def download_research_report_json(experiment_id: str, report_id: str) -> JSONResponse:
    """Export the versioned report envelope for downstream enterprise archiving."""
    try:
        report = research_report_service.get(experiment_id, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONResponse(
        content=report.model_dump(mode="json"),
        headers={"Content-Disposition": f'attachment; filename="{report_id}.json"'},
    )


@router.get("/{experiment_id}/research-reports/{report_id}", response_model=ResearchReport)
def get_research_report(experiment_id: str, report_id: str) -> ResearchReport:
    try:
        return research_report_service.get(experiment_id, report_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _research_action(action):
    try: return action()
    except ResearchCampaignNotFoundError as exc: raise HTTPException(status_code=404, detail="Research campaign or trial not found") from exc
    except ResearchCampaignConflictError as exc: raise HTTPException(status_code=409, detail=str(exc)) from exc


def _assert_formal_evidence(experiment_id: str, action: str) -> None:
    if experiment_service.get_workspace_overview(experiment_id) is None:
        return
    try:
        experiment_service.assert_formal_evidence_allowed(experiment_id, action)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Experiment not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{experiment_id}/research-campaigns", response_model=ResearchCampaign)
def create_research_campaign(experiment_id: str, payload: ResearchCampaignCreate) -> ResearchCampaign:
    if experiment_service.is_persisted_workspace(experiment_id):
        try:
            feature_engineering_agent.assert_training_ready(experiment_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _research_action(lambda: research_campaign_service.create(experiment_id, payload))


@router.get("/{experiment_id}/research-campaigns", response_model=list[ResearchCampaign])
def list_research_campaigns(experiment_id: str) -> list[ResearchCampaign]:
    return research_campaign_service.list(experiment_id)


@router.get("/{experiment_id}/research-campaigns/{campaign_id}", response_model=ResearchCampaign)
def get_research_campaign(experiment_id: str, campaign_id: str) -> ResearchCampaign:
    return _research_action(lambda: research_campaign_service.get(experiment_id, campaign_id))


@router.post("/{experiment_id}/research-campaigns/{campaign_id}/trials", response_model=AgentCommandTask)
def enqueue_research_trial(experiment_id: str, campaign_id: str, payload: ResearchTrialEnqueueRequest) -> AgentCommandTask:
    _research_action(lambda: research_campaign_service.get(experiment_id, campaign_id))
    return agent_command_service.enqueue_research_trial(experiment_id, campaign_id, payload.commandId, payload.hypothesis, payload.parameterPatch, payload.priority)


@router.post("/{experiment_id}/research-campaigns/{campaign_id}/iterate", response_model=AgentCommandTask)
def enqueue_research_iteration(experiment_id: str, campaign_id: str, payload: ResearchIterationRequest) -> AgentCommandTask:
    proposal = _research_action(lambda: research_campaign_service.propose_next(experiment_id, campaign_id, payload.commandId))
    return agent_command_service.enqueue_research_trial(experiment_id, campaign_id, proposal.commandId, proposal.hypothesis, proposal.parameterPatch, payload.priority)


@router.post("/{experiment_id}/research-campaigns/{campaign_id}/promotion", response_model=ResearchCampaign)
def promote_research_trial(experiment_id: str, campaign_id: str, payload: ResearchPromotionRequest) -> ResearchCampaign:
    _assert_formal_evidence(experiment_id, "modelPromotion")
    return _research_action(lambda: research_campaign_service.promote(experiment_id, campaign_id, payload))


@router.get("/{experiment_id}/demo-model-admission", response_model=DemoModelAdmission | None)
def get_demo_model_admission(experiment_id: str) -> DemoModelAdmission | None:
    if experiment_service.get_workspace_overview(experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return demo_model_admission_service.latest(experiment_id)


@router.post("/{experiment_id}/demo-model-admission", response_model=DemoModelAdmission)
def create_demo_model_admission(
    experiment_id: str, payload: DemoModelAdmissionCreate,
) -> DemoModelAdmission:
    try:
        return demo_model_admission_service.create(experiment_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Experiment, campaign, or trial not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{experiment_id}/agent-task-center", response_model=AgentTaskCenter)
def get_agent_task_center(experiment_id: str) -> AgentTaskCenter:
    try:
        return agent_task_center_service.get(experiment_id)
    except AgentTaskCenterNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Experiment not found") from exc


@router.get("", response_model=list[ExperimentRecord])
def list_experiments(result_id: str | None = None) -> list[ExperimentRecord]:
    return experiment_service.list_records(result_id)


@router.get("/archive", response_model=ExperimentArchiveResponse)
def get_experiment_archive() -> ExperimentArchiveResponse:
    return experiment_service.list_workspace_archive()


@router.post("/workspaces", response_model=ExperimentWorkspaceOverview)
def create_experiment_workspace(payload: ExperimentCreateRequest) -> ExperimentWorkspaceOverview:
    reference = None
    if payload.adapterPack is not None:
        selector = payload.adapterPack
        try:
            pack = device_adapter_pack_service.get_verified(
                selector.enterpriseKey, selector.deviceType, selector.packVersion,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if pack is None:
            raise HTTPException(status_code=404, detail="Device adapter pack was not found")
        reference = {
            "enterpriseKey": pack.enterpriseKey, "deviceType": pack.deviceType,
            "packVersion": pack.packVersion, "packId": pack.packId,
            "contentHash": pack.contentHash,
        }
    return experiment_service.create_workspace(payload, reference)


@router.post("/sample-workspaces", response_model=SampleExperimentResult)
def create_sample_experiment_workspace(payload: SampleExperimentCreate) -> SampleExperimentResult:
    try:
        return sample_experiment_service.create(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{experiment_id}/overview", response_model=ExperimentWorkspaceOverview)
def get_experiment_workspace_overview(experiment_id: str) -> ExperimentWorkspaceOverview:
    overview = experiment_service.get_workspace_overview(experiment_id)
    if overview is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return overview


@router.post("/{experiment_id}/files", response_model=ExperimentFileAsset)
def upload_experiment_file(
    experiment_id: str,
    payload: ExperimentTextFileUploadRequest,
) -> ExperimentFileAsset:
    try:
        asset = experiment_file_service.save_text_file(experiment_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if asset.parseStatus != "parsed":
        return asset
    try:
        run = data_collection_localization_agent.create_run(experiment_id, asset.assetId)
    except (LookupError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    experiment_service.mark_data_uploaded(experiment_id, run.transformationCount)
    return asset.model_copy(update={
        "intakeRunId": run.runId,
        "adapterApplied": run.adapterPack is not None,
        "pendingReviewCount": run.pendingReviewCount,
    })


@router.get("/{experiment_id}/files", response_model=list[ExperimentFileAsset])
def list_experiment_file_assets(experiment_id: str) -> list[ExperimentFileAsset]:
    return experiment_file_service.list_file_assets(experiment_id)


@router.get(
    "/{experiment_id}/files/{asset_id}/integrity",
    response_model=ExperimentAssetIntegrityResult,
)
def verify_experiment_file_asset(
    experiment_id: str, asset_id: str,
) -> ExperimentAssetIntegrityResult:
    asset = experiment_file_service.get_file_asset(experiment_id, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Experiment file asset not found")
    try:
        verified = experiment_file_service.verify_asset_integrity(asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ExperimentAssetIntegrityResult(
        assetId=asset.assetId, experimentId=experiment_id,
        contentHash=asset.contentHash, verified=verified,
        storageScheme="content-addressed-sha256",
    )


@router.delete(
    "/{experiment_id}/files/{asset_id}",
    response_model=ExperimentFileDeleteResult,
)
def delete_experiment_file_asset(
    experiment_id: str, asset_id: str, payload: ExperimentFileDeleteRequest,
) -> ExperimentFileDeleteResult:
    try:
        return experiment_file_service.delete_file_asset(
            experiment_id, asset_id, payload.operator, payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{experiment_id}/files/batch", response_model=ExperimentBatchFileUploadResponse)
def upload_experiment_files_batch(
    experiment_id: str,
    payload: ExperimentBatchFileUploadRequest,
) -> ExperimentBatchFileUploadResponse:
    try:
        result = experiment_file_service.save_text_files_batch(experiment_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    assets = []
    transformation_total = 0
    for asset in result.assets:
        if asset.parseStatus != "parsed":
            assets.append(asset)
            continue
        try:
            run = data_collection_localization_agent.create_run(experiment_id, asset.assetId)
        except (LookupError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        assets.append(asset.model_copy(update={
            "intakeRunId": run.runId,
            "adapterApplied": run.adapterPack is not None,
            "pendingReviewCount": run.pendingReviewCount,
        }))
        transformation_total += run.transformationCount
    if transformation_total:
        experiment_service.mark_data_uploaded(experiment_id, transformation_total)
    return result.model_copy(update={"assets": assets})


@router.get(
    "/{experiment_id}/data-intake-runs",
    response_model=list[DataCollectionLocalizationRun],
)
def list_data_intake_runs(experiment_id: str) -> list[DataCollectionLocalizationRun]:
    return data_collection_localization_agent.list_runs(experiment_id)


@router.get(
    "/{experiment_id}/data-intake-runs/latest",
    response_model=DataCollectionLocalizationRun,
)
def get_latest_data_intake_run(experiment_id: str) -> DataCollectionLocalizationRun:
    run = data_collection_localization_agent.latest_run(experiment_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Data intake run not found")
    return run


@router.get("/{experiment_id}/file-audits", response_model=ExperimentFileAuditTimeline)
def list_experiment_file_audits(experiment_id: str) -> ExperimentFileAuditTimeline:
    return experiment_file_service.list_audit_events(experiment_id)


@router.get("/{experiment_id}/file-audit-summary", response_model=ExperimentFileAuditSummary)
def get_experiment_file_audit_summary(experiment_id: str) -> ExperimentFileAuditSummary:
    return experiment_file_service.summarize_audit_events(experiment_id)


@router.get(
    "/{experiment_id}/field-mapping-suggestions",
    response_model=ExperimentFieldMappingSuggestionResponse,
)
def get_experiment_field_mapping_suggestions(
    experiment_id: str,
) -> ExperimentFieldMappingSuggestionResponse:
    return experiment_file_service.suggest_field_mappings(experiment_id)


@router.post("/{experiment_id}/schema-recognition-runs", response_model=SchemaRecognitionRun)
def create_schema_recognition_run(experiment_id: str, payload: SchemaRecognitionRunCreateRequest) -> SchemaRecognitionRun:
    return schema_recognition_agent.create_run(experiment_id, payload.commandId)


@router.get("/{experiment_id}/schema-recognition-runs/{run_id}", response_model=SchemaRecognitionRun)
def get_schema_recognition_run(experiment_id: str, run_id: str) -> SchemaRecognitionRun:
    run = schema_recognition_agent.get_run(experiment_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Schema recognition run not found")
    return run


@router.post("/{experiment_id}/result-interpretation-runs", response_model=ResultInterpretationRun)
def create_result_interpretation_run(experiment_id: str, payload: ResultInterpretationRunCreateRequest) -> ResultInterpretationRun:
    return result_interpretation_agent.create_run(experiment_id, payload.commandId)


@router.get("/{experiment_id}/result-interpretation-runs/{run_id}", response_model=ResultInterpretationRun)
def get_result_interpretation_run(experiment_id: str, run_id: str) -> ResultInterpretationRun:
    run = result_interpretation_agent.get_run(experiment_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Result interpretation run not found")
    return run


@router.post("/{experiment_id}/product-innovation-runs", response_model=ProductInnovationRun)
def create_product_innovation_run(experiment_id: str, payload: ProductInnovationRunCreateRequest) -> ProductInnovationRun:
    return product_innovation_agent.create_run(experiment_id, payload.commandId, payload.input)


@router.get("/{experiment_id}/product-innovation-runs/latest", response_model=ProductInnovationRun)
def get_latest_product_innovation_run(experiment_id: str) -> ProductInnovationRun:
    run = product_innovation_agent.latest_run(experiment_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Product innovation run not found")
    return run


@router.get("/{experiment_id}/product-innovation-runs/{run_id}", response_model=ProductInnovationRun)
def get_product_innovation_run(experiment_id: str, run_id: str) -> ProductInnovationRun:
    run = product_innovation_agent.get_run(experiment_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Product innovation run not found")
    return run


def _product_requirement_action(action):
    try:
        return action()
    except ProductRequirementNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Product innovation run not found") from exc
    except ProductRequirementConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{experiment_id}/product-innovation-runs/{run_id}/confirm", response_model=ProductRequirementVersion)
def confirm_product_requirement(
    experiment_id: str,
    run_id: str,
    payload: ProductRequirementConfirmRequest,
) -> ProductRequirementVersion:
    return _product_requirement_action(lambda: product_requirement_registry.confirm(experiment_id, run_id, payload))


@router.get("/{experiment_id}/product-requirement-versions", response_model=list[ProductRequirementVersion])
def list_product_requirement_versions(experiment_id: str) -> list[ProductRequirementVersion]:
    return product_requirement_registry.list_versions(experiment_id)


@router.get("/{experiment_id}/product-requirement-versions/latest", response_model=ProductRequirementVersion)
def get_latest_product_requirement_version(experiment_id: str) -> ProductRequirementVersion:
    version = product_requirement_registry.latest(experiment_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Confirmed product requirement version not found")
    return version


@router.post(
    "/{experiment_id}/field-mappings/confirm",
    response_model=ExperimentConfirmedFieldMappingSet,
)
def confirm_experiment_field_mappings(
    experiment_id: str,
    payload: ExperimentConfirmFieldMappingsRequest,
) -> ExperimentConfirmedFieldMappingSet:
    if data_collection_localization_agent.latest_run(experiment_id) is None:
        return experiment_file_service.confirm_field_mappings(experiment_id, payload)
    try:
        data_collection_localization_agent.confirm(experiment_id, payload)
        experiment_service.mark_intake_confirmed(experiment_id, len(payload.mappings))
        return experiment_file_service.get_confirmed_field_mappings(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{experiment_id}/field-mappings", response_model=ExperimentConfirmedFieldMappingSet)
def get_experiment_confirmed_field_mappings(
    experiment_id: str,
) -> ExperimentConfirmedFieldMappingSet:
    return experiment_file_service.get_confirmed_field_mappings(experiment_id)


@router.post("/{experiment_id}/field-dictionary", response_model=ExperimentFieldDictionary)
def upsert_experiment_field_dictionary(
    experiment_id: str,
    payload: ExperimentFieldDictionaryUpsertRequest,
) -> ExperimentFieldDictionary:
    return experiment_file_service.upsert_field_dictionary(experiment_id, payload)


@router.get("/{experiment_id}/field-dictionary", response_model=ExperimentFieldDictionary)
def get_experiment_field_dictionary(experiment_id: str) -> ExperimentFieldDictionary:
    return experiment_file_service.get_field_dictionary(experiment_id)


@router.get("/{experiment_id}/cleaning-preview", response_model=ExperimentCleaningPreviewResponse)
def get_experiment_cleaning_preview(experiment_id: str) -> ExperimentCleaningPreviewResponse:
    return experiment_file_service.preview_cleaning(experiment_id)


@router.get("/{experiment_id}/alignment-preview", response_model=ExperimentAlignmentPreviewResponse)
def get_experiment_alignment_preview(experiment_id: str) -> ExperimentAlignmentPreviewResponse:
    return experiment_file_service.preview_alignment(experiment_id)


@router.get("/{experiment_id}/feature-preview", response_model=ExperimentFeaturePreviewResponse)
def get_experiment_feature_preview(experiment_id: str) -> ExperimentFeaturePreviewResponse:
    return experiment_file_service.preview_features(experiment_id)


@router.post(
    "/{experiment_id}/cleaning-alignment-runs",
    response_model=CleaningAlignmentRun,
)
def create_cleaning_alignment_run(
    experiment_id: str, payload: CleaningAlignmentConfig,
) -> CleaningAlignmentRun:
    try:
        return cleaning_alignment_agent.create_run(experiment_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{experiment_id}/cleaning-alignment-runs",
    response_model=list[CleaningAlignmentRun],
)
def list_cleaning_alignment_runs(experiment_id: str) -> list[CleaningAlignmentRun]:
    return cleaning_alignment_agent.list_runs(experiment_id)


@router.get(
    "/{experiment_id}/cleaning-alignment-runs/latest",
    response_model=CleaningAlignmentRun,
)
def get_latest_cleaning_alignment_run(experiment_id: str) -> CleaningAlignmentRun:
    run = cleaning_alignment_agent.latest_run(experiment_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Cleaning alignment run not found")
    return run


@router.post(
    "/{experiment_id}/cleaning-alignment-runs/{run_id}/review",
    response_model=CleaningAlignmentRun,
)
def review_cleaning_alignment_run(
    experiment_id: str, run_id: str, payload: CleaningAlignmentReviewRequest,
) -> CleaningAlignmentRun:
    try:
        return cleaning_alignment_agent.confirm_review(
            experiment_id, run_id, payload.operator, payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{experiment_id}/feature-engineering-runs",
    response_model=FeatureEngineeringRun,
)
def create_feature_engineering_run(
    experiment_id: str, payload: FeatureEngineeringConfig,
) -> FeatureEngineeringRun:
    try:
        return feature_engineering_agent.create_run(experiment_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{experiment_id}/feature-engineering-runs",
    response_model=list[FeatureEngineeringRun],
)
def list_feature_engineering_runs(
    experiment_id: str,
) -> list[FeatureEngineeringRun]:
    return feature_engineering_agent.list_runs(experiment_id)


@router.get(
    "/{experiment_id}/feature-engineering-runs/latest",
    response_model=FeatureEngineeringRun,
)
def get_latest_feature_engineering_run(
    experiment_id: str,
) -> FeatureEngineeringRun:
    run = feature_engineering_agent.latest_run(experiment_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Feature engineering run not found")
    return run


@router.post(
    "/{experiment_id}/feature-engineering-runs/{feature_set_id}/confirm",
    response_model=FeatureEngineeringRun,
)
def confirm_feature_engineering_run(
    experiment_id: str,
    feature_set_id: str,
    payload: FeatureEngineeringConfirmRequest,
) -> FeatureEngineeringRun:
    try:
        return feature_engineering_agent.confirm(
            experiment_id, feature_set_id, payload.operator,
            payload.reason, payload.selectedFeatureNames,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{experiment_id}/model-evaluation-reports",
    response_model=ModelEvaluationReport,
)
def create_model_evaluation_report(
    experiment_id: str,
) -> ModelEvaluationReport:
    try:
        return model_evaluation_agent.create_report(experiment_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{experiment_id}/model-evaluation-reports",
    response_model=list[ModelEvaluationReport],
)
def list_model_evaluation_reports(
    experiment_id: str,
) -> list[ModelEvaluationReport]:
    return model_evaluation_agent.list_reports(experiment_id)


@router.get(
    "/{experiment_id}/model-evaluation-reports/latest",
    response_model=ModelEvaluationReport,
)
def get_latest_model_evaluation_report(
    experiment_id: str,
) -> ModelEvaluationReport:
    report = model_evaluation_agent.latest_report(experiment_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Model evaluation report not found")
    return report


@router.post(
    "/{experiment_id}/model-evaluation-reports/{report_id}/review",
    response_model=ModelEvaluationReport,
)
def review_model_evaluation_report(
    experiment_id: str,
    report_id: str,
    payload: ModelEvaluationReviewRequest,
) -> ModelEvaluationReport:
    try:
        return model_evaluation_agent.review(
            experiment_id, report_id, payload.decision,
            payload.operator, payload.reason,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{experiment_id}/dataset-snapshots", response_model=ExperimentDatasetSnapshot)
def create_experiment_dataset_snapshot(experiment_id: str) -> ExperimentDatasetSnapshot:
    try:
        data_collection_localization_agent.assert_snapshot_ready(experiment_id)
        if experiment_service.is_persisted_workspace(experiment_id):
            run = cleaning_alignment_agent.assert_snapshot_ready(experiment_id)
            return experiment_file_service.create_dataset_snapshot(
                experiment_id,
                aligned_rows_override=run.alignedRows,
                cleaning_run_id=run.runId,
                cleaning_output_hash=run.outputHash,
            )
        return experiment_file_service.create_dataset_snapshot(experiment_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{experiment_id}/dataset-snapshots/latest", response_model=ExperimentDatasetSnapshot)
def get_latest_experiment_dataset_snapshot(experiment_id: str) -> ExperimentDatasetSnapshot:
    return experiment_file_service.get_latest_dataset_snapshot(experiment_id)


@router.get("/{experiment_id}/modeling-plan-preview", response_model=ExperimentModelingPlanPreview)
def get_experiment_modeling_plan_preview(experiment_id: str) -> ExperimentModelingPlanPreview:
    return experiment_file_service.preview_modeling_plan(experiment_id)


@router.post("/{experiment_id}/training-tasks", response_model=ExperimentTrainingTaskPreview)
def create_experiment_training_task(experiment_id: str) -> ExperimentTrainingTaskPreview:
    return experiment_file_service.create_training_task(experiment_id)


@router.get("/{experiment_id}/training-tasks/latest", response_model=ExperimentTrainingTaskPreview)
def get_latest_experiment_training_task(experiment_id: str) -> ExperimentTrainingTaskPreview:
    return experiment_file_service.get_latest_training_task(experiment_id)


@router.get("/{experiment_id}/training-results/latest", response_model=ExperimentTrainingResultSummary)
def get_latest_experiment_training_result(experiment_id: str) -> ExperimentTrainingResultSummary:
    return experiment_file_service.get_latest_training_result(experiment_id)


@router.get("/{experiment_id}/research-brief/latest", response_model=ExperimentResearchBriefSummary)
def get_latest_experiment_research_brief(experiment_id: str) -> ExperimentResearchBriefSummary:
    return experiment_file_service.get_latest_research_brief(experiment_id)


@router.get("/{experiment_id}/simulation-inputs/latest", response_model=ExperimentSimulationInputSummary)
def get_latest_experiment_simulation_input(experiment_id: str) -> ExperimentSimulationInputSummary:
    return experiment_file_service.get_latest_simulation_input(experiment_id)


@router.get("/{experiment_id}/agent-runs/latest", response_model=ExperimentAgentRun)
def get_latest_agent_run(experiment_id: str) -> ExperimentAgentRun:
    _ensure_workspace_experiment(experiment_id)
    return agent_orchestrator.latest_run(experiment_id)


@router.post("/{experiment_id}/agent-runs", response_model=ExperimentAgentRun)
def create_agent_run(experiment_id: str) -> ExperimentAgentRun:
    _ensure_workspace_experiment(experiment_id)
    return agent_orchestrator.create_run(experiment_id)


@router.post("/{experiment_id}/agent-runs/{run_id}/commands", response_model=AgentCommandTask)
def enqueue_agent_run_command(experiment_id: str, run_id: str, payload: AgentCommandEnqueueRequest) -> AgentCommandTask:
    _ensure_workspace_experiment(experiment_id)
    try:
        return agent_command_service.enqueue(experiment_id, run_id, payload)
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent run not found") from exc
    except AgentCommandConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{experiment_id}/agent-commands", response_model=AgentCommandTask)
def enqueue_domain_agent_command(experiment_id: str, payload: UnifiedAgentCommandEnqueueRequest) -> AgentCommandTask:
    _ensure_workspace_experiment(experiment_id)
    try:
        return agent_command_service.enqueue_domain(experiment_id, payload)
    except AgentCommandConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{experiment_id}/agent-runs/{run_id}/advance", response_model=ExperimentAgentRun)
def advance_agent_run(experiment_id: str, run_id: str, payload: AgentRunAdvanceRequest) -> ExperimentAgentRun:
    _ensure_workspace_experiment(experiment_id)
    return _agent_run_action(lambda: agent_orchestrator.advance(experiment_id, run_id, payload.expectedRevision, payload.commandId))


@router.post("/{experiment_id}/agent-runs/{run_id}/stop", response_model=ExperimentAgentRun)
def stop_agent_run(experiment_id: str, run_id: str) -> ExperimentAgentRun:
    _ensure_workspace_experiment(experiment_id)
    return _agent_run_action(lambda: agent_orchestrator.stop(experiment_id, run_id))


@router.post("/{experiment_id}/agent-runs/{run_id}/restart", response_model=ExperimentAgentRun)
def restart_agent_run(
    experiment_id: str,
    run_id: str,
    payload: AgentRunRestartRequest,
) -> ExperimentAgentRun:
    _ensure_workspace_experiment(experiment_id)
    return _agent_run_action(
        lambda: agent_orchestrator.restart(experiment_id, run_id, payload.guidanceId)
    )


@router.post(
    "/{experiment_id}/agent-runs/{run_id}/guidance/preview",
    response_model=AgentGuidancePreview,
)
def preview_agent_guidance(
    experiment_id: str,
    run_id: str,
    payload: AgentGuidancePreviewRequest,
) -> AgentGuidancePreview:
    _ensure_workspace_experiment(experiment_id)
    return _agent_run_action(
        lambda: agent_orchestrator.preview_guidance(experiment_id, run_id, payload.prompt)
    )


@router.post(
    "/{experiment_id}/agent-runs/{run_id}/guidance/apply",
    response_model=ExperimentAgentRun,
)
def apply_agent_guidance(
    experiment_id: str,
    run_id: str,
    payload: AgentGuidanceApplyRequest,
) -> ExperimentAgentRun:
    _ensure_workspace_experiment(experiment_id)
    return _agent_run_action(
        lambda: agent_orchestrator.apply_guidance(
            experiment_id,
            run_id,
            payload.guidanceId,
            payload.confirmed,
        )
    )


@router.post("/{experiment_id}/agent-runs/{run_id}/review", response_model=ExperimentAgentRun)
def review_agent_run(
    experiment_id: str,
    run_id: str,
    payload: HumanReviewDecisionRequest,
) -> ExperimentAgentRun:
    _ensure_workspace_experiment(experiment_id)
    return _agent_run_action(
        lambda: agent_orchestrator.review(
            experiment_id,
            run_id,
            payload.decision,
            payload.reason,
            payload.operator,
            payload.impactScope,
        )
    )


def _ensure_workspace_experiment(experiment_id: str) -> None:
    if experiment_service.get_workspace_overview(experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found")


def _agent_run_action(action):
    try:
        return action()
    except AgentRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Agent run or guidance not found") from exc
    except AgentRunConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{experiment_id}/simulation-runs/latest", response_model=ExperimentSimulationRun)
def get_latest_simulation_run(experiment_id: str) -> ExperimentSimulationRun:
    return _simulation_run_action(lambda: simulation_run_orchestrator.latest(experiment_id))


@router.post("/{experiment_id}/simulation-runs", response_model=ExperimentSimulationRun)
def create_simulation_run(experiment_id: str) -> ExperimentSimulationRun:
    return _simulation_run_action(lambda: simulation_run_orchestrator.create(experiment_id))


@router.post("/{experiment_id}/simulation-runs/{run_id}/advance", response_model=ExperimentSimulationRun)
def advance_simulation_run(experiment_id: str, run_id: str) -> ExperimentSimulationRun:
    return _simulation_run_action(lambda: simulation_run_orchestrator.advance(experiment_id, run_id))


@router.post("/{experiment_id}/simulation-runs/{run_id}/stop", response_model=ExperimentSimulationRun)
def stop_simulation_run(experiment_id: str, run_id: str) -> ExperimentSimulationRun:
    return _simulation_run_action(lambda: simulation_run_orchestrator.stop(experiment_id, run_id))


@router.post("/{experiment_id}/simulation-runs/{run_id}/restart", response_model=ExperimentSimulationRun)
def restart_simulation_run(experiment_id: str, run_id: str) -> ExperimentSimulationRun:
    return _simulation_run_action(lambda: simulation_run_orchestrator.restart(experiment_id, run_id))


@router.post("/{experiment_id}/simulation-runs/{run_id}/trial", response_model=SimulationTrialSnapshot)
def create_simulation_trial(
    experiment_id: str,
    run_id: str,
    payload: SimulationPredictRequest,
) -> SimulationTrialSnapshot:
    return _simulation_run_action(
        lambda: simulation_run_orchestrator.trial(experiment_id, run_id, payload)
    )


@router.post("/{experiment_id}/simulation-runs/{run_id}/fail", response_model=ExperimentSimulationRun)
def fail_simulation_run(
    experiment_id: str,
    run_id: str,
    payload: SimulationFailureRequest,
) -> ExperimentSimulationRun:
    return _simulation_run_action(
        lambda: simulation_run_orchestrator.fail(
            experiment_id,
            run_id,
            payload.reason,
            payload.affectedVersions,
        )
    )


@router.post("/{experiment_id}/simulation-runs/{run_id}/retry", response_model=ExperimentSimulationRun)
def retry_simulation_run(experiment_id: str, run_id: str) -> ExperimentSimulationRun:
    return _simulation_run_action(lambda: simulation_run_orchestrator.retry(experiment_id, run_id))


def _simulation_run_action(action):
    try:
        return action()
    except SimulationRunNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Experiment or simulation run not found") from exc
    except SimulationRunConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{experiment_id}/optimization-runs/latest", response_model=ExperimentOptimizationRun)
def get_latest_optimization_run(experiment_id: str) -> ExperimentOptimizationRun:
    return _optimization_action(lambda: optimization_orchestrator.latest(experiment_id))


@router.get("/{experiment_id}/optimization-runs", response_model=list[ExperimentOptimizationRun])
def list_optimization_runs(experiment_id: str) -> list[ExperimentOptimizationRun]:
    return optimization_orchestrator.list_runs(experiment_id)


@router.post("/{experiment_id}/optimization-runs", response_model=ExperimentOptimizationRun)
def create_optimization_run(experiment_id: str) -> ExperimentOptimizationRun:
    return _optimization_action(lambda: optimization_orchestrator.create(experiment_id))


@router.patch("/{experiment_id}/optimization-runs/{run_id}/selection", response_model=ExperimentOptimizationRun)
def select_optimization_candidate(
    experiment_id: str,
    run_id: str,
    payload: OptimizationSelectionRequest,
) -> ExperimentOptimizationRun:
    return _optimization_action(
        lambda: optimization_orchestrator.select(
            experiment_id, run_id, payload.planId, payload.parameters
        )
    )


@router.post("/{experiment_id}/optimization-runs/{run_id}/submit", response_model=ExperimentOptimizationRun)
def submit_optimization_run(experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
    return _optimization_action(lambda: optimization_orchestrator.submit(experiment_id, run_id))


@router.post("/{experiment_id}/optimization-runs/{run_id}/advance", response_model=ExperimentOptimizationRun)
def advance_optimization_run(experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
    return _optimization_action(lambda: optimization_orchestrator.advance(experiment_id, run_id))


@router.post("/{experiment_id}/optimization-runs/{run_id}/restart-demo", response_model=ExperimentOptimizationRun)
def restart_demo_optimization_run(experiment_id: str, run_id: str) -> ExperimentOptimizationRun:
    return _optimization_action(lambda: optimization_orchestrator.restart_demo(experiment_id, run_id))


@router.post("/{experiment_id}/optimization-runs/{run_id}/review", response_model=ExperimentOptimizationRun)
def review_optimization_run(
    experiment_id: str,
    run_id: str,
    payload: OptimizationReviewRequest,
) -> ExperimentOptimizationRun:
    return _optimization_action(
        lambda: optimization_orchestrator.review(
            experiment_id,
            run_id,
            payload.decision,
            payload.reason,
            payload.operator,
            payload.impactScope,
        )
    )


def _optimization_action(action):
    try:
        return action()
    except OptimizationNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Experiment or optimization run not found") from exc
    except OptimizationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{experiment_id}/validation-batches", response_model=list[ExperimentalValidationBatch])
def list_validation_batches(experiment_id: str) -> list[ExperimentalValidationBatch]:
    return experimental_feedback_agent.list(experiment_id)


@router.post("/{experiment_id}/validation-batches", response_model=ExperimentalValidationBatch)
def create_validation_batch(
    experiment_id: str,
    payload: ExperimentalValidationBatchCreate,
) -> ExperimentalValidationBatch:
    _assert_formal_evidence(experiment_id, "measurementFeedback")
    return _experimental_feedback_action(
        lambda: experimental_feedback_agent.create(experiment_id, payload)
    )


@router.get(
    "/{experiment_id}/validation-batches/{validation_batch_id}",
    response_model=ExperimentalValidationBatch,
)
def get_validation_batch(
    experiment_id: str,
    validation_batch_id: str,
) -> ExperimentalValidationBatch:
    return _experimental_feedback_action(
        lambda: experimental_feedback_agent.get(experiment_id, validation_batch_id)
    )


@router.post(
    "/{experiment_id}/validation-batches/{validation_batch_id}/submit",
    response_model=ExperimentalValidationBatch,
)
def submit_validation_batch(
    experiment_id: str,
    validation_batch_id: str,
    payload: ExperimentalValidationSubmission,
) -> ExperimentalValidationBatch:
    return _experimental_feedback_action(
        lambda: experimental_feedback_agent.submit(
            experiment_id, validation_batch_id, payload
        )
    )


@router.post(
    "/{experiment_id}/validation-batches/{validation_batch_id}/review",
    response_model=ExperimentalValidationBatch,
)
def review_validation_batch(
    experiment_id: str,
    validation_batch_id: str,
    payload: ExperimentalFeedbackReview,
) -> ExperimentalValidationBatch:
    return _experimental_feedback_action(
        lambda: experimental_feedback_agent.review(
            experiment_id, validation_batch_id, payload
        )
    )


def _experimental_feedback_action(action):
    try:
        return action()
    except ExperimentalFeedbackNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Experiment validation batch was not found",
        ) from exc
    except ExperimentalFeedbackConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{experiment_id}/feedback-retraining-runs",
    response_model=list[FeedbackRetrainingRun],
)
def list_feedback_retraining_runs(
    experiment_id: str,
) -> list[FeedbackRetrainingRun]:
    return _feedback_retraining_action(
        lambda agent: agent.list(experiment_id)
    )


@router.post(
    "/{experiment_id}/feedback-retraining-runs",
    response_model=FeedbackRetrainingRun,
)
def create_feedback_retraining_run(
    experiment_id: str,
    payload: FeedbackRetrainingCreate,
) -> FeedbackRetrainingRun:
    return _feedback_retraining_action(
        lambda agent: agent.create(experiment_id, payload)
    )


@router.get(
    "/{experiment_id}/feedback-retraining-runs/{run_id}",
    response_model=FeedbackRetrainingRun,
)
def get_feedback_retraining_run(
    experiment_id: str, run_id: str,
) -> FeedbackRetrainingRun:
    return _feedback_retraining_action(
        lambda agent: agent.get(experiment_id, run_id)
    )


@router.post(
    "/{experiment_id}/feedback-retraining-runs/{run_id}/advance",
    response_model=FeedbackRetrainingRun,
)
def advance_feedback_retraining_run(
    experiment_id: str, run_id: str,
) -> FeedbackRetrainingRun:
    return _feedback_retraining_action(
        lambda agent: agent.advance(experiment_id, run_id)
    )


@router.post(
    "/{experiment_id}/feedback-retraining-runs/{run_id}/review",
    response_model=FeedbackRetrainingRun,
)
def review_feedback_retraining_run(
    experiment_id: str, run_id: str,
    payload: FeedbackRetrainingReview,
) -> FeedbackRetrainingRun:
    return _feedback_retraining_action(
        lambda agent: agent.review(experiment_id, run_id, payload)
    )


def _feedback_retraining_action(action):
    if feedback_retraining_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Persistent experiment data store is required for feedback retraining",
        )
    try:
        return action(feedback_retraining_agent)
    except (
        FeedbackRetrainingNotFoundError,
        FeedbackRetrainingDatasetNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=404,
            detail="Feedback retraining resource was not found",
        ) from exc
    except (
        FeedbackRetrainingConflictError,
        FeedbackRetrainingDatasetConflictError,
        ValueError,
    ) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{experiment_id}/supplementary-design-runs",
    response_model=list[SupplementaryExperimentDesignRun],
)
def list_supplementary_design_runs(
    experiment_id: str,
) -> list[SupplementaryExperimentDesignRun]:
    return _supplementary_design_action(
        lambda agent: agent.list(experiment_id)
    )


@router.post(
    "/{experiment_id}/supplementary-design-runs",
    response_model=SupplementaryExperimentDesignRun,
)
def create_supplementary_design_run(
    experiment_id: str,
    payload: SupplementaryDesignCreate,
) -> SupplementaryExperimentDesignRun:
    return _supplementary_design_action(
        lambda agent: agent.create(experiment_id, payload)
    )


@router.get(
    "/{experiment_id}/supplementary-design-runs/{run_id}",
    response_model=SupplementaryExperimentDesignRun,
)
def get_supplementary_design_run(
    experiment_id: str, run_id: str,
) -> SupplementaryExperimentDesignRun:
    return _supplementary_design_action(
        lambda agent: agent.get(experiment_id, run_id)
    )


@router.patch(
    "/{experiment_id}/supplementary-design-runs/{run_id}/selection",
    response_model=SupplementaryExperimentDesignRun,
)
def select_supplementary_design_candidates(
    experiment_id: str, run_id: str,
    payload: SupplementaryDesignSelection,
) -> SupplementaryExperimentDesignRun:
    return _supplementary_design_action(
        lambda agent: agent.select(experiment_id, run_id, payload)
    )


@router.post(
    "/{experiment_id}/supplementary-design-runs/{run_id}/review",
    response_model=SupplementaryExperimentDesignRun,
)
def review_supplementary_design_run(
    experiment_id: str, run_id: str,
    payload: SupplementaryDesignReview,
) -> SupplementaryExperimentDesignRun:
    return _supplementary_design_action(
        lambda agent: agent.review(experiment_id, run_id, payload)
    )


def _supplementary_design_action(action):
    if supplementary_experiment_design_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Persistent experiment data store is required for supplementary design",
        )
    try:
        return action(supplementary_experiment_design_agent)
    except SupplementaryExperimentDesignNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Supplementary experiment design resource was not found",
        ) from exc
    except (SupplementaryExperimentDesignConflictError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{experiment_id}/supplementary-execution-batches",
    response_model=list[SupplementaryExecutionBatch],
)
def list_supplementary_execution_batches(
    experiment_id: str,
) -> list[SupplementaryExecutionBatch]:
    return _supplementary_execution_action(lambda agent: agent.list(experiment_id))


@router.post(
    "/{experiment_id}/supplementary-execution-batches",
    response_model=SupplementaryExecutionBatch,
)
def create_supplementary_execution_batch(
    experiment_id: str, payload: SupplementaryExecutionBatchCreate,
) -> SupplementaryExecutionBatch:
    return _supplementary_execution_action(
        lambda agent: agent.create(experiment_id, payload)
    )


@router.get(
    "/{experiment_id}/supplementary-execution-batches/{batch_id}",
    response_model=SupplementaryExecutionBatch,
)
def get_supplementary_execution_batch(
    experiment_id: str, batch_id: str,
) -> SupplementaryExecutionBatch:
    return _supplementary_execution_action(
        lambda agent: agent.get(experiment_id, batch_id)
    )


@router.post(
    "/{experiment_id}/supplementary-execution-batches/{batch_id}/start",
    response_model=SupplementaryExecutionBatch,
)
def start_supplementary_execution_batch(
    experiment_id: str, batch_id: str, payload: SupplementaryExecutionStart,
) -> SupplementaryExecutionBatch:
    return _supplementary_execution_action(
        lambda agent: agent.start(experiment_id, batch_id, payload)
    )


@router.post(
    "/{experiment_id}/supplementary-execution-batches/{batch_id}/steps/{step_key}",
    response_model=SupplementaryExecutionBatch,
)
def update_supplementary_execution_step(
    experiment_id: str, batch_id: str, step_key: str,
    payload: SupplementaryExecutionStepUpdate,
) -> SupplementaryExecutionBatch:
    return _supplementary_execution_action(
        lambda agent: agent.update_step(experiment_id, batch_id, step_key, payload)
    )


@router.post(
    "/{experiment_id}/supplementary-execution-batches/{batch_id}/assets",
    response_model=SupplementaryExecutionBatch,
)
def attach_supplementary_execution_assets(
    experiment_id: str, batch_id: str, payload: SupplementaryExecutionAssetAttach,
) -> SupplementaryExecutionBatch:
    return _supplementary_execution_action(
        lambda agent: agent.attach_assets(experiment_id, batch_id, payload)
    )


@router.post(
    "/{experiment_id}/supplementary-execution-batches/{batch_id}/review",
    response_model=SupplementaryExecutionBatch,
)
def review_supplementary_execution_batch(
    experiment_id: str, batch_id: str, payload: SupplementaryExecutionReview,
) -> SupplementaryExecutionBatch:
    return _supplementary_execution_action(
        lambda agent: agent.review(experiment_id, batch_id, payload)
    )


def _supplementary_execution_action(action):
    if supplementary_experiment_execution_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Persistent experiment data store is required for supplementary execution",
        )
    try:
        return action(supplementary_experiment_execution_agent)
    except SupplementaryExperimentExecutionNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Supplementary experiment execution resource was not found",
        ) from exc
    except (SupplementaryExperimentExecutionConflictError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{experiment_id}/supplementary-measurement-batches",
    response_model=list[SupplementaryMeasurementBatch],
)
def list_supplementary_measurement_batches(
    experiment_id: str,
) -> list[SupplementaryMeasurementBatch]:
    return _supplementary_measurement_action(lambda agent: agent.list(experiment_id))


@router.post(
    "/{experiment_id}/supplementary-measurement-batches",
    response_model=SupplementaryMeasurementBatch,
)
def create_supplementary_measurement_batch(
    experiment_id: str, payload: SupplementaryMeasurementBatchCreate,
) -> SupplementaryMeasurementBatch:
    _assert_formal_evidence(experiment_id, "measurementFeedback")
    return _supplementary_measurement_action(
        lambda agent: agent.create(experiment_id, payload)
    )


@router.get(
    "/{experiment_id}/supplementary-measurement-batches/{batch_id}",
    response_model=SupplementaryMeasurementBatch,
)
def get_supplementary_measurement_batch(
    experiment_id: str, batch_id: str,
) -> SupplementaryMeasurementBatch:
    return _supplementary_measurement_action(
        lambda agent: agent.get(experiment_id, batch_id)
    )


@router.post(
    "/{experiment_id}/supplementary-measurement-batches/{batch_id}/submit",
    response_model=SupplementaryMeasurementBatch,
)
def submit_supplementary_measurement_batch(
    experiment_id: str, batch_id: str,
    payload: SupplementaryMeasurementSubmission,
) -> SupplementaryMeasurementBatch:
    return _supplementary_measurement_action(
        lambda agent: agent.submit(experiment_id, batch_id, payload)
    )


@router.post(
    "/{experiment_id}/supplementary-measurement-batches/{batch_id}/review",
    response_model=SupplementaryMeasurementBatch,
)
def review_supplementary_measurement_batch(
    experiment_id: str, batch_id: str,
    payload: SupplementaryMeasurementReview,
) -> SupplementaryMeasurementBatch:
    return _supplementary_measurement_action(
        lambda agent: agent.review(experiment_id, batch_id, payload)
    )


def _supplementary_measurement_action(action):
    if supplementary_measurement_handoff_agent is None:
        raise HTTPException(
            status_code=503,
            detail="Persistent experiment data store is required for supplementary measurement handoff",
        )
    try:
        return action(supplementary_measurement_handoff_agent)
    except SupplementaryMeasurementHandoffNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail="Supplementary measurement handoff resource was not found",
        ) from exc
    except (SupplementaryMeasurementHandoffConflictError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/lifecycle-summaries",
    response_model=list[ExperimentLifecycleSummary],
)
def list_experiment_lifecycle_summaries() -> list[ExperimentLifecycleSummary]:
    return experiment_lifecycle_projection_service.list_summaries()


@router.get(
    "/{experiment_id}/lifecycle",
    response_model=ExperimentLifecycleOverview,
)
def get_experiment_lifecycle(
    experiment_id: str,
) -> ExperimentLifecycleOverview:
    try:
        return experiment_lifecycle_projection_service.get(experiment_id)
    except ExperimentLifecycleNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Experiment lifecycle was not found",
        ) from exc


@router.get(
    "/{experiment_id}/analysis-progress",
    response_model=DataAnalysisProgress,
)
def get_data_analysis_progress(experiment_id: str) -> DataAnalysisProgress:
    try:
        return data_analysis_progress_service.get(experiment_id)
    except AnalysisProgressNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Data analysis progress was not found",
        ) from exc


@router.get("/human-actions", response_model=HumanActionCenter)
def get_human_action_center(
    priority: Literal["high", "medium", "normal"] | None = Query(default=None),
    stage_key: Literal[
        "dataAnalysis", "modelEvaluation", "supplementaryDesign",
        "supplementaryExecution", "measurementFeedback", "feedbackRetraining",
    ] | None = Query(default=None, alias="stageKey"),
    experiment_id: str | None = Query(default=None, alias="experimentId"),
) -> HumanActionCenter:
    if priority is None and stage_key is None and experiment_id is None:
        return human_action_center_service.get()
    return human_action_center_service.get(
        priority=priority, stage_key=stage_key, experiment_id=experiment_id,
    )
