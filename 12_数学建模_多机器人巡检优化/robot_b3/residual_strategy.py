"""Strict per-channel residual-coverage search combined with score routing."""
import math
import time

from .geometry import seven_points
from .residual_search import optimized_completion
from .score_routing import plan_open_route
from .score_strategy import ScoreStrategy


class ResidualStrategy(ScoreStrategy):
    def __init__(self, client, logger=None, route_budget_s=1.0, deadline_margin_s=20):
        super().__init__(client, logger, route_budget_s, deadline_margin_s)
        self.mode = 'residual'
        self.fallback = [tuple(q) for q in seven_points(1123.0)[1:]]
        self.channel_stations = {c: [] for c in range(1, 21)}
        self._completion_cache = {}

    def _measure(self, q, c):
        result = super()._measure(q, c)
        station = tuple(q)
        history = self.channel_stations.setdefault(c, [])
        if not history or all(math.dist(station, old) > 1e-7 for old in history):
            history.append(station)
        return result

    def channel_completion(self, c, extra=()):
        existing = self.channel_stations.get(c, []) + [tuple(q) for q in extra]
        key = (tuple(existing), tuple(self.position))
        if key not in self._completion_cache:
            self._completion_cache[key] = optimized_completion(
                existing, self.fallback, self.position, min(.1, self.route_budget_s))
        return self._completion_cache[key]

    def coverage_requirements(self):
        requirements = {}
        for c in sorted(self.unknown):
            completion = self.channel_completion(c)
            if completion is None:
                raise RuntimeError(f'no strict fallback cover for channel {c}')
            for q in completion:
                requirements.setdefault(tuple(q), set()).add(c)
        return requirements

    def opportunistic_unknown_scan(self):
        """Measure only channels for which this free visit removes fallback work."""
        measured = []
        q = tuple(self.position)
        for c in sorted(self.unknown):
            before = self.channel_completion(c)
            after = self.channel_completion(c, [q])
            if before is not None and after is not None and len(after) < len(before):
                self._measure(q, c)
                measured.append(c)
        self._guaranteed_here()
        return measured

    def _scan_required(self, q, channels):
        selected = set(channels).intersection(self.unknown)
        selected.update(c for c in self.found-self.cleared if self._useful_bearing(c, q))
        ordered = sorted(selected)
        if self.client.current_channel in ordered:
            ordered.remove(self.client.current_channel)
            ordered.insert(0, self.client.current_channel)
        for c in ordered:
            if not self._time_ok():
                return False
            if c not in self.cleared and c not in self.absent:
                self._measure(q, c)
        self._guaranteed_here()
        return True

    def run(self):
        entered = self.client.enter()
        self._log('enter', response=entered, strategy_mode=self.mode)
        self.started = time.monotonic()
        self.deadline = self.started+float(entered['remaining_real_duration_s'])
        self.position = (0.0, 0.0)
        discovery_complete = False
        try:
            self._scan((0.0, 0.0))
            while self._time_ok():
                requirements = self.coverage_requirements() if self.unknown else {}
                if not self.unknown or not requirements:
                    discovery_complete = True
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                pending = self.found-self.cleared
                if not pending and discovery_complete:
                    break
                tasks = {}
                if not discovery_complete:
                    for i, (q, channels) in enumerate(requirements.items()):
                        tasks[('scan', i, q)] = q
                for c in sorted(pending):
                    tasks[('target', c)] = self._task_point(c)
                if not tasks:
                    break
                available = max(0, self.deadline-time.monotonic()-self.deadline_margin_s)
                plan = plan_open_route(self.position, tasks, min(self.route_budget_s, available/20))
                self._log('plan', **plan)
                key = plan['order'][0]
                destination = tasks[plan['order'][1]] if len(plan['order']) > 1 else None
                if key[0] == 'scan':
                    q = tasks[key]
                    self._scan_required(q, requirements[q])
                else:
                    self._service(key[1], destination)
                    self.opportunistic_unknown_scan()
            response = self.client.exit()
            self._log('exit', response=response)
            certified = sum(not self.channel_completion(c) for c in self.absent)
            return {'strategy_mode': self.mode, 'found': len(self.found), 'cleared': len(self.cleared),
                    'unknown_channels': sorted(self.unknown), 'absent_channels': sorted(self.absent),
                    'discovery_complete': discovery_complete,
                    'certified_empty_channels': certified,
                    'virtual_time_s': response.get('virtual_time_s')}
        except Exception as exc:
            self._log('fatal', error=repr(exc))
            try:
                self.client.exit()
            except Exception:
                pass
            raise
