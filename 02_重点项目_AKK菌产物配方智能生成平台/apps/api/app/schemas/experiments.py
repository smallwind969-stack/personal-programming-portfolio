from pydantic import BaseModel


class ExperimentRecord(BaseModel):
    experimentId: str
    resultId: str
    sampleCode: str
    testName: str
    metricValue: float
    unit: str
    targetRange: str
    status: str
    riskLevel: str
    conclusion: str
    createdAt: str
