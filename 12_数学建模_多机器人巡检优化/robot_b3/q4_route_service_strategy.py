"""Route-aware target service retaining the certified 21-station fallback."""
import math

from .q4_certified21_strategy import Q4Certified21Strategy
from .geometry import clear_visit_point


class Q4RouteServiceStrategy(Q4Certified21Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_route_service'
        self._service_destination = None

    def _scheduled_key(self, order, tasks, coverage):
        # Evaluate a target as an insertion into the next discovery leg.
        # Coverage tasks remain present; no probabilistic deletion is allowed.
        if coverage:
            anchor = next(iter(coverage))
            end = coverage[anchor]
            # A route optimizer's target-first decision is retained. Its actual
            # service coordinate is refined against the next certificate.
            selected = order[0]
            self._service_destination = end if selected[0] == 'target' else None
            return selected if selected[0] == 'target' else anchor
        self._service_destination = None
        return order[0]

    def _target_point(self, c, destination=None):
        _, radius = self._circle(c)
        if radius <= 19.5:
            return clear_visit_point(self.poly[c], self.position, destination)
        probes = self._probe_queue(c)
        if probes:
            return min(probes, key=lambda q: math.dist(self.position, q) +
                       (math.dist(q, destination) if destination is not None else 0.0))
        return super()._target_point(c, destination)

    def _service_one(self, c, destination, remaining_sweeps):
        destination = self._service_destination or destination
        _, radius = self._circle(c)
        if radius <= 19.5:
            return super()._service_one(c, destination, remaining_sweeps)
        probes = self._probe_queue(c)
        if not probes:
            return super()._service_one(c, destination, remaining_sweeps)
        q = self._target_point(c, destination)
        probes.remove(q)
        self._probe_attempts[c] = self._probe_attempts.get(c, 0) + 1
        self._measure(q, c)
        self._guaranteed_here()
