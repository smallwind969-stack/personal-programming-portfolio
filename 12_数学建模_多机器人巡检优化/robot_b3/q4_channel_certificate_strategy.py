"""Per-channel discovery obligations; delete only after a continuous proof."""
import math

from .q4_certified21_strategy import Q4Certified21Strategy
from .q4_local_hull_certificate import verify_local_hull_coverage


class Q4ChannelCertificateStrategy(Q4Certified21Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_channel_certificate'
        self.channel_obligations = {}
        self._checked_history = {}
        self.cancelled_channel_tasks = 0

    def _measure(self, q, c):
        # The executed position, not a rounded copy of an observation, is used
        # by both the geometry update and the millimetre-integer certificate.
        return super()._measure(tuple(round(v, 3) for v in q), c)

    def _initial_certificate_tasks(self, layout):
        tasks = super()._initial_certificate_tasks(layout)
        self.channel_obligations = {c: set(tasks) for c in self.unknown}
        return tasks

    def _after_target_service(self, coverage, layout):
        # Do not combine shared-layout substitution with channel-local duties.
        return None

    def _refresh_certificate_tasks(self, coverage, layout):
        for c in sorted(self.unknown):
            duties = self.channel_obligations[c]
            duties.intersection_update(coverage)
            history = tuple(sorted({tuple(p) for p, channel in self._measured
                                    if channel == c}))
            if self._checked_history.get(c) == history:
                continue
            self._checked_history[c] = history
            # No additional observation means no new opportunity to retire a
            # skeleton obligation. Failed/inconclusive proofs leave it intact.
            candidates = sorted(duties, key=lambda k: math.dist(
                self.position, coverage[k]))[:3]
            for key in candidates:
                stations = history + tuple(coverage[k] for k in duties if k != key)
                proof = verify_local_hull_coverage(stations)
                if proof.certified:
                    duties.remove(key)
                    self.cancelled_channel_tasks += 1
                    self._log('channel_certificate_delete', channel=c,
                              station=coverage[key], accepted_boxes=proof.accepted_boxes)
        for key in list(coverage):
            if not any(key in self.channel_obligations[c] for c in self.unknown):
                coverage.pop(key)
                self.cancelled_sweeps += 1
        return coverage

    def _execute_certificate_task(self, key, point, coverage):
        channels = {c for c in self.unknown if key in self.channel_obligations[c]}
        channels.update(c for c in self.found-self.cleared
                        if self._useful_bearing(c, point))
        channels = sorted(channels, key=lambda c: (c != self.client.current_channel, c))
        for c in channels:
            if not self._time_ok():
                return False
            if c not in self.cleared and c not in self.absent:
                self._measure(point, c)
        for duties in self.channel_obligations.values():
            duties.discard(key)
        self._guaranteed_here()
        return True
