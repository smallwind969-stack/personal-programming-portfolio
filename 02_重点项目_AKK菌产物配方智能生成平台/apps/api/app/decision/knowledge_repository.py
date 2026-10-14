from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from .contracts import KnowledgeEvidence


class KnowledgeDocument(BaseModel):
    version: str
    entries: list[KnowledgeEvidence]


class JsonKnowledgeRepository:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @property
    def version(self) -> str:
        return self._load().version

    def search(
        self, product_type: str, metrics: list[str]
    ) -> list[KnowledgeEvidence]:
        requested_metrics = set(metrics)
        matches: list[KnowledgeEvidence] = []
        for item in self._load().entries:
            if item.status != "active":
                continue
            if not (item.source.url or item.source.file):
                continue
            product_match = any(
                product_type == candidate
                or candidate in product_type
                or product_type in candidate
                for candidate in item.productTypes
            )
            metric_match = not requested_metrics or bool(
                requested_metrics.intersection(item.metrics)
            )
            if product_match and metric_match:
                matches.append(item)
        return sorted(matches, key=lambda item: item.evidenceId)

    def _load(self) -> KnowledgeDocument:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return KnowledgeDocument.model_validate(payload)
