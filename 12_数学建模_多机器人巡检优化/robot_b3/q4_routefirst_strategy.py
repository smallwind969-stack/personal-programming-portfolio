"""Q4 strict route-first certificate with proven boundary substitution."""

import math

from .full_view import (
    build_route_first_full_view_layout,
    can_replace_certificate_station,
    replace_certificate_station,
)
from .q4_belief_strategy import Q4BeliefStrategy


class Q4RouteFirstStrategy(Q4BeliefStrategy):
    """Use a short polar certificate and recycle safe target visits."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_routefirst'
        self.certificate_replacements = 0

    def _build_fallback_layout(self):
        layout = build_route_first_full_view_layout(start=(0.0, 0.0))
        self._active_certificate_layout = layout
        return layout

    def _after_target_service(self, coverage, layout):
        if not self.unknown or not coverage or not self._time_ok():
            return None
        active_layout = getattr(self, '_active_certificate_layout', layout)
        safe = [
            key for key, station in coverage.items()
            if can_replace_certificate_station(
                active_layout, station, self.position)
        ]
        if not safe:
            return None

        key = min(safe, key=lambda item: math.dist(coverage[item], self.position))
        old_station = coverage[key]
        unknown_before = tuple(sorted(self.unknown))
        if not self._scan(self.position):
            return None
        coverage.pop(key, None)
        self._active_certificate_layout = replace_certificate_station(
            active_layout, old_station, self.position)
        self.certificate_replacements += 1
        self._log(
            'certificate_replacement',
            old_station=old_station,
            replacement=self.position,
            channels=unknown_before,
            remaining_certificates=len(coverage),
        )
        return key
