from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.contracts import AuthIdentity
from app.auth.dependencies import auth_service, current_identity
from app.auth.service import AuthError
from app.decision.contracts import DecisionRequirement
from app.decision.errors import DecisionError
from app.decision.knowledge_repository import JsonKnowledgeRepository
from app.decision.model_gateway import ActivatedModelGateway
from app.decision.pipeline import DecisionPipeline
from app.decision.requirement_parser import (
    HttpRequirementProvider,
    RequirementParser,
)
from app.decision.trace_store import DecisionTrace, SqliteDecisionTraceStore
from app.model_registry.runtime import promoted_model_inference_service
from app.paths import project_path
from app.services.llm_service import local_llm_service


router = APIRouter(prefix="/decision", tags=["decision"])


class ParseRequest(BaseModel):
    text: str


class RunRequest(BaseModel):
    rawRequirement: str
    requirement: dict[str, Any]
    supplementalConstraints: dict[str, Any] = Field(default_factory=dict)


class ConfirmRequest(BaseModel):
    planId: str
    note: str | None = None


_parser = RequirementParser(
    HttpRequirementProvider(
        provider=local_llm_service.provider,
        model=local_llm_service.model,
        base_url=local_llm_service.base_url,
        api_key=local_llm_service.api_key,
        enabled=local_llm_service.enabled,
        timeout=local_llm_service.timeout,
    )
)
_trace_path = project_path(
    os.getenv("DECISION_TRACE_DB_PATH", "data/runtime/decision-traces.db")
)
_trace_path.parent.mkdir(parents=True, exist_ok=True)
_pipeline = DecisionPipeline(
    JsonKnowledgeRepository(
        project_path(
            os.getenv("DECISION_KNOWLEDGE_PATH", "data/decision/knowledge-v1.json")
        )
    ),
    ActivatedModelGateway(promoted_model_inference_service),
    SqliteDecisionTraceStore(_trace_path, auth_service),
    model_experiment_id=os.getenv(
        "DECISION_MODEL_EXPERIMENT_ID", "decision-functional-jelly-v1"
    ),
)


def get_requirement_parser() -> RequirementParser:
    return _parser


def get_pipeline() -> DecisionPipeline:
    return _pipeline


def _raise_domain_error(exc: Exception) -> None:
    if isinstance(exc, DecisionError):
        statuses = {
            "REQUIREMENT_PARSER_UNAVAILABLE": 503,
            "INCOMPLETE_CONSTRAINTS": 422,
            "KNOWLEDGE_INSUFFICIENT": 422,
            "MODEL_NOT_AVAILABLE": 409,
            "MODEL_FEATURE_MISMATCH": 422,
            "MODEL_INPUT_OUT_OF_RANGE": 422,
            "NO_FEASIBLE_SOLUTION": 422,
            "TENANT_ACCESS_DENIED": 403,
        }
        raise HTTPException(
            status_code=statuses.get(exc.code, 400),
            detail={"code": exc.code, "message": exc.message, "details": exc.details},
        ) from exc
    if isinstance(exc, AuthError):
        raise HTTPException(
            status_code=403, detail={"code": exc.code, "message": exc.message}
        ) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail="DECISION_RUN_NOT_FOUND") from exc
    raise exc


@router.post("/requirements/parse", response_model=DecisionRequirement)
def parse_requirement(
    payload: ParseRequest,
    _: AuthIdentity = Depends(current_identity),
    parser: RequirementParser = Depends(get_requirement_parser),
) -> DecisionRequirement:
    try:
        return parser.parse(payload.text)
    except Exception as exc:
        _raise_domain_error(exc)


@router.post("/runs", response_model=DecisionTrace, status_code=201)
def create_run(
    payload: RunRequest,
    identity: AuthIdentity = Depends(current_identity),
    pipeline: DecisionPipeline = Depends(get_pipeline),
) -> DecisionTrace:
    try:
        return pipeline.execute(identity, payload.model_dump())
    except Exception as exc:
        _raise_domain_error(exc)


@router.get("/runs/{run_id}", response_model=DecisionTrace)
def get_run(
    run_id: str,
    identity: AuthIdentity = Depends(current_identity),
    pipeline: DecisionPipeline = Depends(get_pipeline),
) -> DecisionTrace:
    try:
        return pipeline.get(identity, run_id)
    except Exception as exc:
        _raise_domain_error(exc)


@router.post("/runs/{run_id}/confirm", response_model=DecisionTrace)
def confirm_run(
    run_id: str,
    payload: ConfirmRequest,
    identity: AuthIdentity = Depends(current_identity),
    pipeline: DecisionPipeline = Depends(get_pipeline),
) -> DecisionTrace:
    try:
        return pipeline.confirm(identity, run_id, payload.planId, payload.note)
    except Exception as exc:
        _raise_domain_error(exc)


@router.get("/cases", response_model=list[DecisionTrace])
def list_cases(
    identity: AuthIdentity = Depends(current_identity),
    pipeline: DecisionPipeline = Depends(get_pipeline),
) -> list[DecisionTrace]:
    return pipeline.cases(identity)


@router.post("/cases/{case_id}/replay", response_model=DecisionTrace)
def replay_case(
    case_id: str,
    identity: AuthIdentity = Depends(current_identity),
    pipeline: DecisionPipeline = Depends(get_pipeline),
) -> DecisionTrace:
    original = pipeline.get(identity, case_id)
    return pipeline.execute(
        identity,
        {
            "rawRequirement": original.rawRequirement,
            "requirement": original.requirement,
            "supplementalConstraints": original.supplementalConstraints,
            "replayOfRunId": original.runId,
        },
    )
