from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from threading import RLock
from typing import Callable
from uuid import uuid4

from app.feature_binding_advisor.contracts import (
    BindingAdvisorContext, BindingSuggestionCandidate, DeviceAdapterPackReference,
    DeviceAdapterPackSelector, FeatureBindingSuggestionRun,
)
from app.feature_binding_advisor.adapter_pack import DeviceAdapterPack
from app.feature_binding_advisor.providers import BindingProviderFailure, BindingSuggestionProvider
from app.feature_binding_advisor.store import SqliteFeatureBindingSuggestionStore
from app.model_registry.bindings import is_supported_simulation_parameter


ALIASES = {
    "temperature_c": ("temperatureC", "℃"), "temperature": ("temperatureC", "℃"),
    "ph": ("ph", "pH"), "agitation_rpm": ("stirringRpm", "rpm"),
    "stirring_rpm": ("stirringRpm", "rpm"), "duration_hours": ("cultureHours", "h"),
    "culture_hours": ("cultureHours", "h"), "pressure_mpa": ("pressureMpa", "MPa"),
    "anaerobic_score": ("anaerobicScore", None), "carbon_concentration": ("carbonConcentration", "g/L"),
}


class FeatureBindingAdvisorAgent:
    def __init__(self, context_provider: Callable[[str, str], BindingAdvisorContext],
                 provider: BindingSuggestionProvider,
                 store: SqliteFeatureBindingSuggestionStore | None = None,
                 adapter_pack_provider: Callable[[DeviceAdapterPackSelector], DeviceAdapterPack | None] | None = None) -> None:
        self.contextProvider = context_provider
        self.provider = provider
        self.store = store
        self.adapterPackProvider = adapter_pack_provider
        self._runs: dict[str, FeatureBindingSuggestionRun] = {}
        self._commands: dict[tuple[str, str, str], str] = {}
        self._lock = RLock()

    def create_run(
        self, experiment_id: str, model_version: str, command_id: str,
        adapter_selector: DeviceAdapterPackSelector | None = None,
    ) -> FeatureBindingSuggestionRun:
        key = (experiment_id, model_version, command_id)
        persisted = self.store.get_by_command(*key) if self.store else None
        if persisted and not self._selector_matches_reference(adapter_selector, persisted.adapterPack):
            raise ValueError("command was already used with a different adapter pack")
        with self._lock:
            existing_id = self._commands.get(key)
            in_memory = self._runs.get(existing_id) if existing_id else None
        if in_memory and not self._selector_matches_reference(adapter_selector, in_memory.adapterPack):
            raise ValueError("command was already used with a different adapter pack")
        adapter_pack = self._resolve_adapter_pack(adapter_selector)
        adapter_reference = self._adapter_reference(adapter_pack)
        request_fingerprint = self._request_fingerprint(
            experiment_id, model_version, command_id, adapter_reference,
        )
        if persisted:
            if persisted.requestFingerprint != request_fingerprint:
                raise ValueError("command was already used with a different adapter pack")
            return persisted
        with self._lock:
            if in_memory:
                if in_memory.requestFingerprint != request_fingerprint:
                    raise ValueError("command was already used with a different adapter pack")
                return in_memory.model_copy(deep=True)
        context = self.contextProvider(experiment_id, model_version)
        rules = self._rules(context)
        candidates = {item.modelFeature: item for item in rules}
        if adapter_pack:
            candidates = self._merge_adapter(context, candidates, adapter_pack)
        conflicts = rejected = 0
        mode = "rule_only"; fallback = None
        if self.provider.enabled:
            try:
                for proposed in self.provider.suggest(context):
                    if proposed.modelFeature not in candidates or not is_supported_simulation_parameter(proposed.simulationParameter):
                        rejected += 1; continue
                    current = candidates[proposed.modelFeature]
                    if current.simulationParameter and current.simulationParameter != proposed.simulationParameter:
                        conflicts += 1
                        candidates[proposed.modelFeature] = current.model_copy(update={
                            "source": "adapter" if current.source == "adapter" else "merged",
                            "requiresHumanReview": True,
                            "reviewReasons": list(dict.fromkeys([*current.reviewReasons, "providerConflict"])),
                            "evidence": [*current.evidence, *proposed.evidence],
                        })
                    elif current.simulationParameter is None:
                        candidates[proposed.modelFeature] = current.model_copy(update={
                            "simulationParameter": proposed.simulationParameter, "scale": proposed.scale, "offset": proposed.offset,
                            "confidence": min(0.89, proposed.confidence), "source": "llm", "evidence": proposed.evidence,
                            "requiresHumanReview": True, "reviewReasons": ["llmCandidate"],
                        })
                mode = "llm_assisted"
            except BindingProviderFailure as exc:
                mode = "rule_fallback"; fallback = exc.category
            except Exception as exc:
                mode = "rule_fallback"; fallback = type(exc).__name__
        ordered = [candidates[name] for name in context.featureNames]
        run = FeatureBindingSuggestionRun(
            runId=f"binding-suggestion-{uuid4().hex[:12]}", experimentId=experiment_id,
            modelVersion=model_version, commandId=command_id,
            requestFingerprint=request_fingerprint, adapterPack=adapter_reference,
            status="completed", mode=mode,
            provider=self.provider.provider, model=self.provider.model, fallbackReason=fallback,
            candidateCount=len(ordered), reviewCount=sum(item.requiresHumanReview for item in ordered),
            conflictCount=conflicts, rejectedCount=rejected,
            readyForConfirmation=all(item.simulationParameter is not None for item in ordered), candidates=ordered,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._runs[run.runId] = run; self._commands[key] = run.runId
        return self.store.save(run) if self.store else run.model_copy(deep=True)

    def _resolve_adapter_pack(
        self, selector: DeviceAdapterPackSelector | None,
    ) -> DeviceAdapterPack | None:
        if selector is None:
            return None
        if self.adapterPackProvider is None:
            raise LookupError("device adapter pack provider is unavailable")
        pack = self.adapterPackProvider(selector)
        if pack is None:
            raise LookupError("device adapter pack was not found")
        if (
            pack.enterpriseKey != selector.enterpriseKey
            or pack.deviceType != selector.deviceType
            or pack.packVersion != selector.packVersion
        ):
            raise ValueError("device adapter pack selector mismatch")
        return pack

    @staticmethod
    def _adapter_reference(pack: DeviceAdapterPack | None) -> DeviceAdapterPackReference | None:
        if pack is None:
            return None
        return DeviceAdapterPackReference(
            packId=pack.packId, enterpriseKey=pack.enterpriseKey, deviceType=pack.deviceType,
            packVersion=pack.packVersion, contentHash=pack.contentHash,
        )

    @staticmethod
    def _selector_matches_reference(
        selector: DeviceAdapterPackSelector | None,
        reference: DeviceAdapterPackReference | None,
    ) -> bool:
        if selector is None or reference is None:
            return selector is None and reference is None
        return (
            selector.enterpriseKey == reference.enterpriseKey
            and selector.deviceType == reference.deviceType
            and selector.packVersion == reference.packVersion
        )

    @staticmethod
    def _request_fingerprint(
        experiment_id: str, model_version: str, command_id: str,
        adapter_reference: DeviceAdapterPackReference | None,
    ) -> str:
        payload = {
            "experimentId": experiment_id, "modelVersion": model_version, "commandId": command_id,
            "adapterPack": adapter_reference.model_dump(mode="json") if adapter_reference else None,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "sha256:" + sha256(canonical).hexdigest()

    @staticmethod
    def _merge_adapter(
        context: BindingAdvisorContext,
        candidates: dict[str, BindingSuggestionCandidate],
        pack: DeviceAdapterPack,
    ) -> dict[str, BindingSuggestionCandidate]:
        by_standard = {entry.standardField.casefold(): entry for entry in pack.entries}
        by_alias = {entry.sourceFieldAlias.casefold(): entry for entry in pack.entries}
        merged = dict(candidates)
        for feature in context.featureNames:
            entry = by_standard.get(feature.casefold()) or by_alias.get(feature.casefold())
            if entry is None:
                continue
            rule = merged[feature]
            conflict = bool(
                rule.simulationParameter
                and rule.simulationParameter != entry.simulationParameter
            )
            reasons = ["adapterRuleConflict"] if conflict else []
            merged[feature] = BindingSuggestionCandidate(
                modelFeature=feature, standardField=entry.standardField,
                simulationParameter=entry.simulationParameter,
                sourceUnit=entry.sourceUnit, targetUnit=entry.targetUnit,
                scale=entry.scale, offset=entry.offset,
                confidence=0.92 if conflict else 0.99, source="adapter",
                evidence=[
                    f"adapter pack {pack.packId}",
                    f"content hash {pack.contentHash}",
                    *rule.evidence,
                ],
                requiresHumanReview=conflict, reviewReasons=reasons,
            )
        return merged

    def get_run(self, experiment_id: str, run_id: str) -> FeatureBindingSuggestionRun | None:
        if self.store:
            return self.store.get(experiment_id, run_id)
        run = self._runs.get(run_id)
        return run.model_copy(deep=True) if run and run.experimentId == experiment_id else None

    @staticmethod
    def _rules(context: BindingAdvisorContext) -> list[BindingSuggestionCandidate]:
        result = []
        for feature in context.featureNames:
            alias = ALIASES.get(feature.lower())
            parameter, expected_unit = alias if alias else (None, None)
            source_unit = context.confirmedStandardFields.get(feature)
            unit_conflict = bool(expected_unit and source_unit and source_unit not in {expected_unit, "°C" if expected_unit == "℃" else expected_unit})
            review_reasons = (["unitMismatch"] if unit_conflict else []) + (["noDeterministicAlias"] if not parameter else [])
            result.append(BindingSuggestionCandidate(
                modelFeature=feature, standardField=feature, simulationParameter=parameter,
                sourceUnit=source_unit, targetUnit=expected_unit, confidence=0.55 if not parameter else 0.75 if unit_conflict else 0.97,
                source="rule", evidence=["confirmed standard field", "deterministic alias table" if parameter else "no alias match"],
                requiresHumanReview=bool(review_reasons), reviewReasons=review_reasons,
            ))
        return result
