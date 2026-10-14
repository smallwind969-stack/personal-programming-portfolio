from __future__ import annotations

import re

from app.schema_recognition.contracts import ProviderCandidate, SchemaRecognitionContext
from app.schemas.experiments import SchemaRecognitionCandidate

_FIELD = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_KNOWN_UNITS = {None, "", "°C", "℃", "rpm", "pH", "%", "g/L", "mg/L", "OD600", "a.u."}
_UNIT_DIMENSIONS = {
    "°C": "temperature", "℃": "temperature", "rpm": "rotation", "pH": "acidity",
    "%": "ratio", "g/L": "concentration", "mg/L": "concentration",
    "OD600": "opticalDensity", "a.u.": "arbitrary",
}
_DANGEROUS = ("控制产线", "执行代码", "powershell", "cmd.exe", "../", "\\")


class SchemaRecognitionPolicy:
    def validate_candidates(self, context: SchemaRecognitionContext, candidates: list[ProviderCandidate]):
        fields = {(asset.assetId, field.originalColumn) for asset in context.assets for field in asset.fields}
        by_column = {column: asset_id for asset_id, column in fields}
        accepted, rejected = [], []
        for item in candidates:
            asset_id = item.assetId or by_column.get(item.originalColumn)
            if not asset_id or (asset_id, item.originalColumn) not in fields:
                rejected.append("unknownOriginalColumn")
                continue
            if not _FIELD.fullmatch(item.standardField) or any(token in " ".join(item.evidence).lower() for token in _DANGEROUS):
                rejected.append("unsafeCandidate")
                continue
            reasons = []
            if item.sourceUnit not in _KNOWN_UNITS or item.targetUnit not in _KNOWN_UNITS:
                reasons.append("unknownUnit")
            elif item.sourceUnit and item.targetUnit and _UNIT_DIMENSIONS.get(item.sourceUnit) != _UNIT_DIMENSIONS.get(item.targetUnit):
                reasons.append("unitDimensionConflict")
            if item.confidence < 0.8:
                reasons.append("lowConfidence")
            accepted.append(SchemaRecognitionCandidate(
                **item.model_dump(exclude={"assetId"}), assetId=asset_id,
                requiresHumanReview=bool(reasons), reviewReasons=reasons, source="llm",
            ))
        return accepted, rejected

    @staticmethod
    def merge(rule_candidates, llm_candidates):
        llm_by_key = {(item.assetId, item.originalColumn): item for item in llm_candidates}
        merged, conflicts, used = [], 0, set()
        for rule in rule_candidates:
            key = (rule.assetId, rule.originalColumn)
            llm = llm_by_key.get(key)
            if llm and llm.standardField == rule.standardField:
                merged.append(rule.model_copy(update={
                    "source": "merged", "confidence": min(rule.confidence, llm.confidence),
                    "evidence": [*rule.evidence, *llm.evidence],
                    "requiresHumanReview": rule.requiresHumanReview or llm.requiresHumanReview,
                    "reviewReasons": list(dict.fromkeys([*rule.reviewReasons, *llm.reviewReasons])),
                }))
                used.add(key)
            elif llm:
                conflicts += 1
                merged.append(rule.model_copy(update={"requiresHumanReview": True, "reviewReasons": [*rule.reviewReasons, "ruleLlmConflict"]}))
                used.add(key)
            else:
                merged.append(rule)
        for key, llm in llm_by_key.items():
            if key not in used:
                merged.append(llm.model_copy(update={"requiresHumanReview": True, "reviewReasons": list(dict.fromkeys([*llm.reviewReasons, "llmOnlyCandidate"]))}))
        return merged, conflicts
