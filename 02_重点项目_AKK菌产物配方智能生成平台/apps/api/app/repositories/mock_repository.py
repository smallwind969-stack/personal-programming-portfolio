import json
from functools import lru_cache
from pathlib import Path
from typing import Any


class MockRepository:
    def __init__(self) -> None:
        self.mock_dir = Path(__file__).resolve().parents[4] / "data" / "mock"

    def _read_json(self, file_name: str) -> list[dict[str, Any]]:
        with (self.mock_dir / file_name).open("r", encoding="utf-8") as file:
            return json.load(file)

    @lru_cache(maxsize=1)
    def get_products(self) -> list[dict[str, Any]]:
        return self._read_json("akk_products.json")

    @lru_cache(maxsize=1)
    def get_formula_results(self) -> list[dict[str, Any]]:
        return self._read_json("formula_results.json")

    @lru_cache(maxsize=1)
    def get_prediction_examples(self) -> list[dict[str, Any]]:
        return self._read_json("prediction_examples.json")

    @lru_cache(maxsize=1)
    def get_knowledge_items(self) -> list[dict[str, Any]]:
        literature_path = self.mock_dir / "literature_knowledge_items.json"
        items = []
        if literature_path.exists():
            items.extend(self._read_json("literature_knowledge_items.json"))
        items.extend(self._read_json("knowledge_items.json"))
        return items

    @lru_cache(maxsize=1)
    def get_knowledge_chunks(self) -> list[dict[str, Any]]:
        chunks_path = self.mock_dir / "literature_knowledge_chunks.json"
        if not chunks_path.exists():
            return []
        return self._read_json("literature_knowledge_chunks.json")
