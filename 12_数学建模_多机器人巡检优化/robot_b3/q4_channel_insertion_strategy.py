"""Buy an in-place channel scan only when certified obligations can retire."""
import math

from .q4_channel_certificate_strategy import Q4ChannelCertificateStrategy
from .q4_local_hull_certificate import verify_local_hull_coverage
from .score_routing import plan_open_route


class Q4ChannelInsertionStrategy(Q4ChannelCertificateStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_channel_insertion'
        self.certificate_insertion_measures = 0

    def _after_target_service(self, coverage, layout):
        if not self.unknown or not coverage or not self._time_ok():
            return None
        q = tuple(round(v, 3) for v in self.position)
        proposals = {}
        for c in sorted(self.unknown):
            history = tuple(sorted({p for p, channel in self._measured if channel == c}))
            if q in history:
                continue
            duties = set(self.channel_obligations[c]) & set(coverage)
            remaining = set(duties)
            for key in sorted(duties, key=lambda k: math.dist(q, coverage[k]))[:3]:
                points = history + (q,) + tuple(coverage[k] for k in remaining if k != key)
                if verify_local_hull_coverage(points).certified:
                    remaining.remove(key)
            if remaining != duties:
                proposals[c] = duties-remaining
        if not proposals:
            return None
        residual = {key: point for key, point in coverage.items()
                    if any(key in self.channel_obligations[c]
                           and key not in proposals.get(c, ()) for c in self.unknown)}
        before = plan_open_route(self.position, coverage, .01)['distance_m']
        after = (plan_open_route(q, residual, .01)['distance_m'] if residual else 0.)
        # Compare feasible route estimates, not a lower bound or global optimum.
        # Charge all new switches, credit only 5 s for each retired measurement.
        scan_cost = math.dist(self.position, q)/5 + 6*len(proposals)
        estimated_saving = (before-after)/5 + 5*sum(map(len, proposals.values()))
        if estimated_saving <= scan_cost:
            return None
        for c in sorted(proposals, key=lambda c: (c != self.client.current_channel, c)):
            if not self._time_ok():
                break
            self._measure(q, c)
            self.certificate_insertion_measures += 1
            self.channel_obligations[c].difference_update(proposals[c])
            self.cancelled_channel_tasks += len(proposals[c])
            self._log('channel_certificate_insertion', channel=c, position=q,
                      retired_tasks=len(proposals[c]), estimated_saving_s=estimated_saving,
                      scan_cost_s=scan_cost)
        self._guaranteed_here()
        return None
