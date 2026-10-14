from __future__ import annotations

from typing import Protocol

from app.feature_binding_advisor.contracts import BindingAdvisorContext, BindingLlmCandidate


class BindingProviderFailure(RuntimeError):
    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class BindingSuggestionProvider(Protocol):
    provider: str
    model: str
    enabled: bool
    def suggest(self, context: BindingAdvisorContext) -> list[BindingLlmCandidate]: ...


class NullBindingSuggestionProvider:
    provider = "disabled"
    model = "none"
    enabled = False

    def suggest(self, context: BindingAdvisorContext) -> list[BindingLlmCandidate]:
        return []
