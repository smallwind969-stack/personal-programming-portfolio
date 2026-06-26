from pydantic import BaseModel


class LlmStatus(BaseModel):
    enabled: bool
    provider: str
    model: str
    baseUrl: str
    available: bool
    mode: str
