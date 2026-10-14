"""Independent Q4 branch with a continuously certified 21-station skeleton."""
from dataclasses import replace
import math

from .q4_belief_strategy import Q4BeliefStrategy
from .q4_local_hull_certificate import (
    build_certified21_layout, verify_local_hull_coverage,
)
from .score_routing import plan_open_route


class Q4Certified21Strategy(Q4BeliefStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_certified21'
        self.certificate_replacements = 0

    def _build_fallback_layout(self):
        self._active_certificate_layout = build_certified21_layout()
        return self._active_certificate_layout

    def _scheduled_key(self, order, tasks, coverage):
        # Preserve the offline open route in a skeleton-only state. Once target
        # tasks exist, retain the stable joint service/discovery rolling planner.
        if coverage and all(key[0] == 'certificate' for key in tasks):
            return next(iter(coverage))
        return super()._scheduled_key(order, tasks, coverage)

    def _after_target_service(self, coverage, layout):
        if not self.unknown or not coverage or not self._time_ok():
            return None
        candidate = tuple(round(value, 3) for value in self.position)
        active = self._active_certificate_layout
        baseline = plan_open_route(self.position, coverage, .01)['distance_m']
        for key in sorted(coverage, key=lambda k: math.dist(coverage[k], candidate))[:3]:
            old = coverage[key]
            residual = {k: q for k, q in coverage.items() if k != key}
            after = math.dist(self.position, candidate)
            if residual:
                after += plan_open_route(candidate, residual, .01)['distance_m']
            if candidate != old and after >= baseline - 1e-6:
                continue
            stations = tuple(candidate if q == old else q for q in active.stations)
            proof = verify_local_hull_coverage(stations)
            if not proof.certified:
                continue
            # Every channel still unknown was measured at all previously removed
            # stations. Scan ALL currently unknown channels before committing this
            # substitute. Partial scans or a failed certificate never delete it.
            channels = tuple(sorted(self.unknown))
            if not self._scan(candidate):
                return None
            self._active_certificate_layout = replace(active, stations=stations)
            coverage.pop(key)
            self.certificate_replacements += 1
            self._log('certificate_replacement', old_station=old,
                      replacement=candidate, channels=channels,
                      remaining_certificates=len(coverage),
                      coverage_proof='integer_local_hull',
                      accepted_boxes=proof.accepted_boxes,
                      feasible_route_saving_m=baseline-after)
            return key
        return None
