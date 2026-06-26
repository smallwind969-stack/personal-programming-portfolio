from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from datetime import datetime
from typing import Iterable

from app.repositories.mock_repository import MockRepository
from app.schemas.knowledge import KnowledgeChunk, KnowledgeItem


VECTOR_DIM = 384

MATRIX_KEYWORDS = {
    "dairy": ["牛奶", "酸奶", "乳", "发酵乳", "乳基", "milk", "dairy", "yogurt"],
    "yogurt": ["酸奶", "发酵乳", "yogurt"],
    "functional_beverage": ["饮料", "即饮", "水相", "beverage", "drink"],
    "nutrition_powder": ["粉", "营养", "代餐", "奶昔", "powder", "meal"],
}

TOPIC_KEYWORDS = {
    "safety": ["安全", "毒理", "风险", "遗传毒性", "亚慢性", "safe", "toxicity"],
    "regulatory": ["法规", "合规", "备案", "上市", "fda", "ndi", "efsa", "novel food"],
    "clinical": ["临床", "人体", "功效", "减重", "血糖", "肥胖", "志愿者", "clinical", "human"],
    "postbiotic": ["后生元", "灭活", "巴氏", "pasteurized", "heat-killed", "postbiotic"],
    "fiber_polysaccharide": ["膳食纤维", "纤维", "多糖", "菊粉", "饱腹", "fiber", "polysaccharide"],
    "metabolite": ["代谢", "脂代谢", "代谢物", "短链脂肪酸", "scfa"],
    "mechanism": ["外膜蛋白", "amuc", "tlr2", "屏障", "黏液", "免疫", "炎症"],
    "food_application": ["食品", "配方", "复配", "发酵", "酸奶", "牛奶", "饮料"],
}

CONCEPT_EXPANSIONS = {
    "低糖": ["低糖", "甜味", "赤藓糖醇", "膳食纤维", "酸奶", "口感"],
    "酸奶": ["酸奶", "发酵乳", "乳基", "酸性体系", "稳定性", "感官", "析水"],
    "牛奶": ["牛奶", "乳基", "复配脱脂乳", "稳定性", "蛋白"],
    "饮料": ["饮料", "水相", "即饮", "澄清", "浊度", "酸甜"],
    "营养粉": ["营养粉", "粉体", "复水", "分散", "膳食纤维", "饱腹"],
    "儿童": ["儿童", "安全", "低风险", "感官", "合规", "敏感人群"],
    "银发": ["银发", "老年", "营养", "蛋白", "消化", "安全"],
    "安全": ["安全", "毒理", "法规", "NDI", "EFSA", "合规"],
    "肠道": ["肠道", "黏液", "屏障", "Amuc_1100", "TLR2", "后生元"],
}

EVIDENCE_WEIGHT = {"A": 22, "B": 16, "C": 9, "D": 3}
TYPE_WEIGHT = {
    "regulatory": 8,
    "toxicology_safety": 7,
    "human_clinical": 6,
    "food_application": 5,
    "mechanism_or_basic_research": 3,
    "review": 2,
    "patent": -4,
}


class KnowledgeService:
    def __init__(self, repository: MockRepository | None = None) -> None:
        self.repository = repository or MockRepository()

    def list_items(self) -> list[KnowledgeItem]:
        return [KnowledgeItem.model_validate(item) for item in self.repository.get_knowledge_items()]

    def search_items(self, query: str | None = None, topics: list[str] | None = None) -> list[KnowledgeItem]:
        normalized_query = (query or "").lower().strip()
        requested_topics = {topic.lower() for topic in topics or [] if topic}
        desired_topics = self._detect_topics(normalized_query).union(requested_topics)
        desired_matrices = self._detect_matrices(normalized_query)
        chunk_hits = self.search_chunks(query=query, topics=topics, limit=160)

        chunk_score_by_item: dict[str, float] = defaultdict(float)
        passages_by_item: dict[str, list[str]] = defaultdict(list)
        reasons_by_item: dict[str, list[str]] = defaultdict(list)
        for chunk in chunk_hits:
            chunk_score_by_item[chunk.knowledgeId] = max(chunk_score_by_item[chunk.knowledgeId], chunk.retrievalScore or 0)
            if len(passages_by_item[chunk.knowledgeId]) < 3:
                passages_by_item[chunk.knowledgeId].append(chunk.text)
            for reason in chunk.matchReasons[:4]:
                if reason not in reasons_by_item[chunk.knowledgeId]:
                    reasons_by_item[chunk.knowledgeId].append(reason)

        scored = []
        for item in self.repository.get_knowledge_items():
            score, reasons = self._score_item_metadata(item, normalized_query, desired_topics, desired_matrices)
            score += chunk_score_by_item.get(item["knowledgeId"], 0) * 0.8
            reasons.extend(reasons_by_item.get(item["knowledgeId"], []))
            if not normalized_query and not requested_topics:
                score += 5
            if score > 0:
                enriched = dict(item)
                enriched["retrievalScore"] = round(score, 2)
                enriched["matchReasons"] = self._unique(reasons)[:10]
                enriched["keyPassages"] = passages_by_item.get(item["knowledgeId"], [])[:3]
                scored.append(enriched)

        scored.sort(key=lambda item: item.get("retrievalScore", 0), reverse=True)
        return [KnowledgeItem.model_validate(item) for item in scored[:80]]

    def search_chunks(self, query: str | None = None, topics: list[str] | None = None, limit: int = 40) -> list[KnowledgeChunk]:
        normalized_query = (query or "").lower().strip()
        requested_topics = {topic.lower() for topic in topics or [] if topic}
        desired_topics = self._detect_topics(normalized_query).union(requested_topics)
        desired_matrices = self._detect_matrices(normalized_query)
        query_embedding = self._hashed_embedding(self._expanded_query(normalized_query))
        query_terms = self._query_terms(normalized_query)

        scored = []
        for chunk in self.repository.get_knowledge_chunks():
            score, reasons = self._score_chunk(
                chunk=chunk,
                query=normalized_query,
                query_terms=query_terms,
                query_embedding=query_embedding,
                desired_topics=desired_topics,
                desired_matrices=desired_matrices,
            )
            if not normalized_query and not requested_topics:
                score += 5
            if score > 0:
                enriched = dict(chunk)
                enriched.pop("embedding", None)
                enriched["retrievalScore"] = round(score, 2)
                enriched["matchReasons"] = self._unique(reasons)[:10]
                scored.append(enriched)

        scored.sort(key=lambda item: item.get("retrievalScore", 0), reverse=True)
        return [KnowledgeChunk.model_validate(item) for item in scored[:limit]]

    def _score_chunk(
        self,
        chunk: dict,
        query: str,
        query_terms: list[str],
        query_embedding: list[float],
        desired_topics: set[str],
        desired_matrices: set[str],
    ) -> tuple[float, list[str]]:
        haystack = " ".join(
            [
                chunk.get("title", ""),
                chunk.get("text", ""),
                " ".join(chunk.get("topics", [])),
                " ".join(chunk.get("foodMatrix", [])),
            ]
        ).lower()
        item_topics = {topic.lower() for topic in chunk.get("topics", [])}
        item_matrices = {matrix.lower() for matrix in chunk.get("foodMatrix", [])}
        score = 0.0
        reasons: list[str] = []

        vector_score = self._cosine(query_embedding, chunk.get("embedding", []))
        if vector_score:
            score += vector_score * 48
            reasons.append(f"语义向量相似度 {vector_score:.2f}")

        term_hits = [term for term in query_terms if term in haystack]
        if term_hits:
            score += min(len(term_hits) * 4.5, 32)
            reasons.append(f"关键概念命中：{', '.join(term_hits[:6])}")

        topic_hits = desired_topics.intersection(item_topics)
        if topic_hits:
            score += len(topic_hits) * 13
            reasons.append(f"科学主题匹配：{', '.join(sorted(topic_hits))}")

        matrix_hits = desired_matrices.intersection(item_matrices)
        if matrix_hits:
            score += len(matrix_hits) * 18
            reasons.append(f"食品基质匹配：{', '.join(sorted(matrix_hits))}")

        evidence_level = chunk.get("evidenceLevel", "D")
        evidence_type = chunk.get("evidenceType", "")
        score += EVIDENCE_WEIGHT.get(evidence_level, 0)
        score += TYPE_WEIGHT.get(evidence_type, 0)
        reasons.append(f"证据等级 {evidence_level} / 类型 {evidence_type or 'unknown'}")

        if {"safety", "regulatory"}.intersection(desired_topics).intersection(item_topics):
            score += 18
            reasons.append("安全/法规证据强制召回")
        if "patent" in item_topics and "patent" not in desired_topics:
            score -= 8
            reasons.append("专利资料降权，仅作竞品空间参考")

        return score, reasons

    def _score_item_metadata(
        self,
        item: dict,
        query: str,
        desired_topics: set[str],
        desired_matrices: set[str],
    ) -> tuple[float, list[str]]:
        haystack = " ".join(
            [
                item.get("title", ""),
                item.get("summary", ""),
                " ".join(item.get("topics", [])),
                " ".join(item.get("usableInsights", [])),
                " ".join(item.get("riskNotes", [])),
                " ".join(item.get("foodMatrix", [])),
                " ".join(item.get("akkMaterial", [])),
            ]
        ).lower()
        item_topics = {topic.lower() for topic in item.get("topics", [])}
        item_matrices = {matrix.lower() for matrix in item.get("foodMatrix", [])}
        score = 0.0
        reasons: list[str] = []

        query_terms = self._query_terms(query)
        term_hits = [term for term in query_terms if term in haystack]
        if term_hits:
            score += min(len(term_hits) * 3.5, 22)
            reasons.append(f"证据卡概念命中：{', '.join(term_hits[:5])}")

        topic_hits = desired_topics.intersection(item_topics)
        if topic_hits:
            score += len(topic_hits) * 10
            reasons.append(f"证据卡主题匹配：{', '.join(sorted(topic_hits))}")

        matrix_hits = desired_matrices.intersection(item_matrices)
        if matrix_hits:
            score += len(matrix_hits) * 14
            reasons.append(f"证据卡食品基质匹配：{', '.join(sorted(matrix_hits))}")

        evidence_level = item.get("evidenceLevel", "D")
        evidence_type = item.get("evidenceType", "")
        score += EVIDENCE_WEIGHT.get(evidence_level, 0)
        score += TYPE_WEIGHT.get(evidence_type, 0)
        reasons.append(f"证据等级 {evidence_level} / 类型 {evidence_type or 'unknown'}")

        year = item.get("year")
        if isinstance(year, int):
            recency = max(0, 8 - max(datetime.now().year - year, 0))
            score += recency
            if recency:
                reasons.append(f"资料较新：{year}")

        if "patent" in item_topics and "patent" not in desired_topics:
            score -= 8
            reasons.append("专利资料降权，仅作竞品空间参考")

        return score, reasons

    def _expanded_query(self, query: str) -> str:
        expansions = [query]
        for key, values in CONCEPT_EXPANSIONS.items():
            if key.lower() in query:
                expansions.extend(values)
        return " ".join(expansions)

    def _query_terms(self, query: str) -> list[str]:
        expanded = self._expanded_query(query)
        terms = [term for term in re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", expanded.lower()) if term]
        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", expanded))
        terms.extend(chinese[index : index + 2] for index in range(max(len(chinese) - 1, 0)))
        return self._unique(terms)

    def _feature_tokens(self, text: str) -> Iterable[str]:
        normalized = text.lower().replace("_", " ").replace("-", " ")
        for token in re.findall(r"[a-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", normalized):
            yield token
        chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
        for index in range(max(len(chinese) - 1, 0)):
            yield chinese[index : index + 2]
        for topic, keywords in TOPIC_KEYWORDS.items():
            if any(keyword.lower() in normalized for keyword in keywords):
                yield f"topic:{topic}"

    def _hashed_embedding(self, text: str) -> list[float]:
        vector = [0.0] * VECTOR_DIM
        for token in self._feature_tokens(text):
            bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % VECTOR_DIM
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            return vector
        return [value / norm for value in vector]

    def _cosine(self, query_embedding: list[float], chunk_embedding: list[float]) -> float:
        if not query_embedding or not chunk_embedding:
            return 0.0
        length = min(len(query_embedding), len(chunk_embedding))
        return sum(query_embedding[index] * float(chunk_embedding[index]) for index in range(length))

    def _detect_matrices(self, query: str) -> set[str]:
        return {
            matrix
            for matrix, keywords in MATRIX_KEYWORDS.items()
            if any(keyword.lower() in query for keyword in keywords)
        }

    def _detect_topics(self, query: str) -> set[str]:
        return {
            topic
            for topic, keywords in TOPIC_KEYWORDS.items()
            if any(keyword.lower() in query for keyword in keywords)
        }

    def _unique(self, values: Iterable[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result


knowledge_service = KnowledgeService()
