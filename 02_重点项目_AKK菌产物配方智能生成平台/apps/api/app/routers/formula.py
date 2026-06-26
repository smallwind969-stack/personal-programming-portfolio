from fastapi import APIRouter, HTTPException

from app.schemas.formula import FormulaGenerationRequest, FormulaResult
from app.services.formula_service import formula_service

router = APIRouter(tags=["formula"])


@router.post("/formula/generate", response_model=FormulaResult)
def generate_formula(request: FormulaGenerationRequest) -> FormulaResult:
    return formula_service.generate_formula(request)


@router.get("/formula-results", response_model=list[FormulaResult])
def list_formula_results() -> list[FormulaResult]:
    return formula_service.list_results()


@router.get("/formula-results/{result_id}", response_model=FormulaResult)
def get_formula_result(result_id: str) -> FormulaResult:
    result = formula_service.get_result(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Formula result not found")
    return result
