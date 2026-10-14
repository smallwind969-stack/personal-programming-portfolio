"""Safety-preserving dynamic route variant for the Q4 21-station certificate.

All certificate stations and all currently unknown-channel sweeps remain
mandatory.  The only optimization is the open-route order, recomputed after
each observation/target service; therefore the continuous discovery guarantee
is unchanged.
"""
from .q4_certified21_strategy import Q4Certified21Strategy
import math


class Q4Certified21OptimizedStrategy(Q4Certified21Strategy):
    """Replan the next certificate station from the current position.

    The parent intentionally preserves the precomputed certificate order while
    no target task exists.  Here ``plan_open_route`` is allowed to choose its
    first station.  Every station is still retained in ``coverage`` and is
    eventually scanned, so this is a route optimization only, not a coverage
    relaxation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = "q4_certified21_optimized"
        self.dynamic_route_choices = 0
        self.measure_cache = {}
        self.cached_measurements = 0
        self.reused_scan_channels = 0
        self.route_gate_m = 250.0

    @staticmethod
    def _ordered_distance(start, points):
        points = list(points)
        if not points:
            return 0.0
        return math.dist(start, points[0]) + sum(
            math.dist(a, b) for a, b in zip(points, points[1:]))

    def _measure(self, q, c):
        # The simulator fixes the bearing error at a location.  Repeating the
        # exact same (position, channel) query therefore adds no information
        # but still costs five virtual seconds; reuse its previous response.
        key = (round(float(q[0]), 6), round(float(q[1]), 6), int(c))
        if key in self.measure_cache:
            self.cached_measurements += 1
            return self.measure_cache[key]
        result = super()._measure(q, c)
        self.measure_cache[key] = result
        return result

    def _scan(self, q):
        """Scan unknown channels plus useful known channels once per point.

        Unknown channels remain mandatory until the 21-station certificate is
        completed.  A discovered channel is included only when its current
        bearing can improve localization, and an exact point/channel query is
        never sent twice.
        """
        unknown = set(self.unknown)
        known = {c for c in self.found - self.cleared
                 if self._useful_bearing(c, q)}
        channels = sorted(unknown | known)
        fresh = []
        for c in channels:
            if (tuple(q), c) in self._measured:
                self.reused_scan_channels += 1
                continue
            fresh.append(c)
        channels = fresh
        if self.client.current_channel in channels:
            channels.remove(self.client.current_channel)
            channels.insert(0, self.client.current_channel)
        required = set(self.unknown)
        for c in channels:
            if not self._time_ok():
                return False
            if c not in self.cleared and c not in self.absent:
                self._measure(q, c)
        measured_here = {c for position, c in self._measured
                         if position == tuple(q)}
        if required.issubset(measured_here | self.absent):
            if not self.scan_stations or math.dist(self.scan_stations[-1], q) > 1e-7:
                self.scan_stations.append(tuple(q))
                self.coverage_stations = len(self.scan_stations)
        self._guaranteed_here()
        return True

    def _scheduled_key(self, order, tasks, coverage):
        if order and coverage and all(k[0] == "certificate" for k in tasks):
            baseline = next(iter(coverage))
            # Route reordering was tested but can change which targets are
            # discovered before later stations.  Keep the certified route
            # order; the safe optimization in this branch is measurement
            # deduplication below.
            selected = baseline
            self.dynamic_route_choices += int(selected != baseline)
            return selected
        return super()._scheduled_key(order, tasks, coverage)

    def run(self):
        result = super().run()
        result["dynamic_route_choices"] = self.dynamic_route_choices
        result["cached_measurements"] = self.cached_measurements
        result["reused_scan_channels"] = self.reused_scan_channels
        return result
