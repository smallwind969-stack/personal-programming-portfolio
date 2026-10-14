"""Question 4 anytime strategy for mixed omni/directional sources."""
import math
import time

from .full_view import build_full_view_layout, receiver_side_probe_pairs
from .fusion_strategy import FusionStrategy
from .geometry import clear_visit_point
from .score_routing import plan_open_route


class Q4Strategy(FusionStrategy):
    """Strict full-view discovery with route-aware opportunistic acceleration."""

    def __init__(self, *args, novelty_distance_m=350.0,
                 insertion_distance_m=220.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4'
        self.absent = set()
        self._directional_probe_attempts = {}
        self._optical_cover = {}
        self.full_view_station_count = 0
        self.novelty_distance_m = float(novelty_distance_m)
        self.insertion_distance_m = float(insertion_distance_m)
        self.opportunity_scans = 0
        self.deferred_targets = 0
        self.cancelled_full_view_stations = 0
        self.last_discovery_virtual_time_s = None
        self._found14_opportunity_scans = 0

    def _measure(self, q, c):
        before = len(self.found)
        result = super()._measure(q, c)
        if len(self.found) > before:
            self.last_discovery_virtual_time_s = self.client.virtual_time_s
        return result

    def _ordered_pair(self, pair, destination):
        def cost(q):
            value = math.dist(self.position, q)
            if destination is not None:
                value += math.dist(q, destination)
            return value
        return sorted(pair, key=cost)

    def _probe_once(self, c, destination):
        """Visit one receiver-side pair and stop the pair at first positive."""
        if not self.observations.get(c):
            return False
        center, _ = self._circle(c)
        positive_station = self.observations[c][0][0]
        groups = receiver_side_probe_pairs(center, positive_station)
        attempt = self._directional_probe_attempts.get(c, 0)
        if attempt >= len(groups):
            return False
        self._directional_probe_attempts[c] = attempt+1
        before = len(self.observations[c])
        for q in self._ordered_pair(groups[attempt], destination):
            if not self._time_ok() or (tuple(q), c) in self._measured:
                continue
            result = self._measure(q, c)
            if result in ('direction', 'near'):
                break
        return len(self.observations.get(c, ())) > before or c in self.cleared

    def _novel_unknown_channels(self, q):
        q = tuple(q)
        result = []
        threshold = self.novelty_distance_m*(1.25 if len(self.found) == 14 else 1.0)
        for c in sorted(self.unknown):
            prior = [position for position, channel in self._measured if channel == c]
            if not prior or min(math.dist(q, p) for p in prior) >= threshold:
                result.append(c)
        return result

    def _opportunity_scan(self, coverage):
        """Seek source 15/16 at an already-paid-for dynamic stop.

        Misses never remove certificate stations or clip the safe polygon.
        """
        if len(self.found) < 14 or not self.unknown or not self._time_ok():
            return False
        if len(self.found) == 14 and self._found14_opportunity_scans >= 1:
            return False
        channels = self._novel_unknown_channels(self.position)
        if not channels:
            return False
        if self.client.current_channel in channels:
            channels.remove(self.client.current_channel)
            channels.insert(0, self.client.current_channel)
        self.opportunity_scans += 1
        if len(self.found) == 14:
            self._found14_opportunity_scans += 1
        for c in channels:
            if c not in self.unknown or not self._time_ok():
                continue
            self._measure(self.position, c)
            if len(self.found) == 16:
                self.cancelled_full_view_stations += len(coverage)
                coverage.clear()
                return True
        return False

    @staticmethod
    def _interval_centers(lo, hi, spacing):
        width = max(0.0, hi-lo)
        count = max(1, int(math.ceil(width/spacing)))
        if width <= 1e-12:
            return [(lo+hi)/2]
        cell = width/count
        return [lo+(i+.5)*cell for i in range(count)]

    def _build_optical_cover(self, c, radius=19.5):
        """Conservatively cover the safe bearing polygon by optical cells."""
        station, bearing = self.observations[c][-1]
        a = math.radians(bearing)
        ux, uy = math.cos(a), math.sin(a)
        nx, ny = -uy, ux

        def project(p):
            dx, dy = p[0]-station[0], p[1]-station[1]
            return dx*ux+dy*uy, dx*nx+dy*ny

        coordinates = [project(p) for p in self.poly[c]]
        spacing = radius*math.sqrt(2)
        along = self._interval_centers(min(x for x, _ in coordinates),
                                       max(x for x, _ in coordinates), spacing)
        across = self._interval_centers(min(y for _, y in coordinates),
                                        max(y for _, y in coordinates), spacing)
        rows = []
        for row, y in enumerate(across):
            xs = along if row % 2 == 0 else list(reversed(along))
            rows.extend((station[0]+x*ux+y*nx, station[1]+x*uy+y*ny)
                        for x in xs)
        if rows and math.dist(self.position, rows[-1]) < math.dist(self.position, rows[0]):
            rows.reverse()
        return rows

    def _optical_queue(self, c):
        signature = (len(self.observations[c]),
                     tuple((round(p[0], 6), round(p[1], 6)) for p in self.poly[c]))
        cached = self._optical_cover.get(c)
        if cached is None or cached[0] != signature:
            cached = (signature, self._build_optical_cover(c))
            self._optical_cover[c] = cached
        return cached[1]

    def _run_optical_chain(self, c, coverage):
        """Finish a started optical cover atomically instead of leaving it."""
        self._opportunity_scan(coverage)
        queue = self._optical_queue(c)
        while queue and c not in self.cleared and self._time_ok():
            q = queue.pop(0)
            if self._clear(q, c):
                self._optical_cover.pop(c, None)
                return True
        if c not in self.cleared and not queue:
            raise RuntimeError(f'certified optical cover missed channel {c}')
        return c in self.cleared

    @staticmethod
    def _insertion_distance(start, point, destination):
        if destination is None:
            return math.dist(start, point)
        return (math.dist(start, point)+math.dist(point, destination)
                -math.dist(start, destination))

    def _scheduled_key(self, order, tasks):
        """Keep the joint route, except for an expensive detour at 15 found."""
        key = order[0]
        if len(self.found) != 15 or key[0] != 'target':
            return key
        coverage_key = next((candidate for candidate in order
                             if candidate[0] == 'full_view'), None)
        if coverage_key is None:
            return key
        delta = self._insertion_distance(
            self.position, tasks[key], tasks[coverage_key])
        limit = self.insertion_distance_m*.55
        if delta <= limit:
            return key
        self.deferred_targets += 1
        self._log('defer_target', channel=key[1],
                  insertion_distance_m=delta, limit_m=limit,
                  found=len(self.found))
        return coverage_key

    def _service_q4(self, c, destination, coverage):
        _, radius = self._circle(c)
        if radius <= 19.5:
            q = clear_visit_point(self.poly[c], self.position, destination)
            if not self._clear(q, c):
                raise RuntimeError(f'guaranteed Q4 clear failed on channel {c}')
            self._opportunity_scan(coverage)
            return
        if self._directional_probe_attempts.get(c, 0) < 2:
            self._probe_once(c, destination)
        else:
            self._run_optical_chain(c, coverage)
        self._guaranteed_here()
        self._opportunity_scan(coverage)

    def run(self):
        layout = build_full_view_layout(start=(0.0, 0.0), side=990.0)
        stations = layout.stations
        entered = self.client.enter()
        self._log('enter', response=entered, strategy_mode=self.mode,
                  full_view_stations=len(stations), lattice_side_m=layout.side,
                  lattice_phase=layout.phase,
                  shortest_certificate_route_m=layout.route_distance_m,
                  novelty_distance_m=self.novelty_distance_m,
                  insertion_distance_m=self.insertion_distance_m)
        self.started = time.monotonic()
        self.deadline = self.started+float(entered['remaining_real_duration_s'])
        self.position = (0.0, 0.0)
        coverage = {('full_view', i): q for i, q in enumerate(stations)}
        self.full_view_station_count = len(coverage)
        discovery_complete = False
        try:
            while self._time_ok():
                if len(self.found) == 16:
                    self.cancelled_full_view_stations += len(coverage)
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                    coverage.clear()
                    discovery_complete = True
                elif not coverage:
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                    discovery_complete = True

                pending = self.found-self.cleared
                if discovery_complete and not pending:
                    break
                if not coverage and not pending:
                    break

                tasks = {}
                if not discovery_complete:
                    tasks.update(coverage)
                for c in sorted(pending):
                    tasks[('target', c)] = self._task_point(c)
                if not tasks:
                    break
                available = max(0.0, self.deadline-time.monotonic()
                                -self.deadline_margin_s)
                planning_cap = .08 if len(tasks) > 11 else .25
                plan = plan_open_route(
                    self.position, tasks,
                    min(self.route_budget_s, planning_cap, available/20))
                self._log('plan', phase=('target_cleanup' if discovery_complete
                                         else 'joint_discovery'), **plan)
                order = plan['order']
                key = self._scheduled_key(order, tasks)
                index = order.index(key)
                destination = (tasks[order[index+1]]
                               if index+1 < len(order) else None)
                if key[0] == 'full_view':
                    self._scan(tasks[key])
                    coverage.pop(key, None)
                else:
                    self._service_q4(key[1], destination, coverage)

            response = self.client.exit()
            self._log('exit', response=response)
            return {
                'strategy_mode': self.mode,
                'found': len(self.found),
                'cleared': len(self.cleared),
                'unknown_channels': sorted(self.unknown),
                'absent_channels': sorted(self.absent),
                'discovery_complete': discovery_complete,
                'coverage_stations': self.coverage_stations,
                'full_view_station_count': self.full_view_station_count,
                'opportunity_scans': self.opportunity_scans,
                'deferred_targets': self.deferred_targets,
                'cancelled_full_view_stations': self.cancelled_full_view_stations,
                'last_discovery_virtual_time_s': self.last_discovery_virtual_time_s,
                'virtual_time_s': response.get('virtual_time_s'),
            }
        except Exception as exc:
            self._log('fatal', error=repr(exc))
            try:
                self.client.exit()
            except Exception:
                pass
            raise
