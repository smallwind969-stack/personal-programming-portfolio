"""Compare short receiver-side bearings against original Q4 probe candidates."""
import math
from .q4_certified21_strategy import Q4Certified21Strategy


class Q4CompactServiceStrategy(Q4Certified21Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_compact_service'

    def _probe_queue(self, c):
        original = super()._probe_queue(c)
        if not original:
            return original
        signature = len(self.observations[c])
        cache = getattr(self, '_compact_cache', {})
        self._compact_cache = cache
        if c not in cache or cache[c][0] != signature:
            center, _ = self._circle(c)
            station = self.observations[c][0][0]
            dx, dy = station[0]-center[0], station[1]-center[1]
            candidates = list(original)
            for along, across in ((.20, .15), (.35, .20)):
                for sign in (-1, 1):
                    candidates.append((center[0]+along*dx-sign*across*dy,
                                       center[1]+along*dy+sign*across*dx))
            measured = {q for q, channel in self._measured if channel == c}
            candidates = [q for q in candidates if q not in measured]
            # Finite predicted geometry ranks probes. Actual observations alone
            # update safe polygons; all original optical-cover points remain.
            ranked = sorted(candidates, key=lambda q: self._candidate_cost(c, q, None))
            cache[c] = (signature, ranked)
        return cache[c][1]

    def _target_point(self, c, destination=None):
        _, radius = self._circle(c)
        if radius <= 19.5:
            return super()._target_point(c, destination)
        probes = self._probe_queue(c)
        return probes[0] if probes else super()._target_point(c, destination)

    def _service_one(self, c, destination, remaining_sweeps):
        _, radius = self._circle(c)
        probes = self._probe_queue(c) if radius > 19.5 else []
        if not probes:
            return super()._service_one(c, destination, remaining_sweeps)
        q = probes.pop(0)
        self._probe_attempts[c] = self._probe_attempts.get(c, 0)+1
        self._measure(q, c)
        self._guaranteed_here()
