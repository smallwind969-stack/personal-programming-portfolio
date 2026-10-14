from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.experiments import ExperimentFileAsset, ExperimentWorkspaceOverview


class SampleExperimentCreate(BaseModel):
    templateKey: Literal["algae-culture"] = "algae-culture"
    name: str | None = Field(default=None, min_length=2, max_length=120)


class SampleExperimentResult(BaseModel):
    overview: ExperimentWorkspaceOverview
    asset: ExperimentFileAsset
    intakeRunId: str
    templateKey: str
    templateVersion: str
    templateContentHash: str
    disclaimer: str
