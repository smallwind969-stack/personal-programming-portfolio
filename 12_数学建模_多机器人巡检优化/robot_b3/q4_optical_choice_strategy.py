"""Compare a complete optical chain with the next bearing's immediate cost."""
import math

from .q4_certified21_strategy import Q4Certified21Strategy
from .geometry import point_polygon_distance


def optical_chain_preferred(position, optical, probes, current_channel, channel, polygon=None):
    if not optical:
        return False
    if not probes:
        return True
    length = math.dist(position, optical[0])
    length += sum(math.dist(a, b) for a, b in zip(optical, optical[1:]))
    optical_upper = length/5 + 3*(len(optical)-1) + 5
    # Completing this source after probing requires reaching within 20 m of P.
    # This distance lower bound remains valid even with intervening tasks.
    def lower(q):
        cost = math.dist(position, q)/5
        if polygon:
            cost += max(0., point_polygon_distance(q, polygon)-20)/5 + 5
        return cost
    probe_lower = min(lower(q) for q in probes)
    probe_lower += 5 + int(current_channel != channel)
    return optical_upper <= probe_lower


class Q4OpticalChoiceStrategy(Q4Certified21Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_optical_choice'
        self.early_optical_actions = 0

    def _prefer_optical(self, c):
        previous = self._optical_cover.get(c)
        preferred = optical_chain_preferred(self.position, self._optical_queue(c),
                                            self._probe_queue(c),
                                            self.client.current_channel, c,
                                            polygon=self.poly[c])
        # Evaluating a rejected action must not freeze a newly generated optical
        # route whose best starting end can change before it is actually used.
        if not preferred:
            if previous is None:
                self._optical_cover.pop(c, None)
            else:
                self._optical_cover[c] = previous
        return preferred

    def _target_point(self, c, destination=None):
        if self._circle(c)[1] > 19.5 and self._prefer_optical(c):
            return self._optical_queue(c)[0]
        return super()._target_point(c, destination)

    def _service_one(self, c, destination, remaining_sweeps):
        if self._circle(c)[1] <= 19.5 or not self._prefer_optical(c):
            return super()._service_one(c, destination, remaining_sweeps)
        if self._probe_queue(c):
            self.early_optical_actions += 1
        points = self._optical_queue(c)
        q = points.pop(0)
        if self._clear(q, c):
            self._optical_cover.pop(c, None)
        self._guaranteed_here()
