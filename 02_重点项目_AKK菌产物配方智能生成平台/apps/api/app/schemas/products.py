from typing import Literal

from pydantic import BaseModel

from app.schemas.common import ProductProperty, RiskItem, RiskLevel, ValidationMetric


class AkkProduct(BaseModel):
    productId: str
    productName: str
    productCategory: str
    description: str
    keyProperties: list[ProductProperty]
    functionalAssumptions: list[str]
    recommendedApplications: list[str]
    constraints: list[str]
    riskItems: list[RiskItem]
    validationMetrics: list[ValidationMetric]
    riskLevel: RiskLevel
    evidenceLevel: str
    sourceType: Literal["mock"]
