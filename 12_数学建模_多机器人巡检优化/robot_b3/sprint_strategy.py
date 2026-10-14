"""Risk-budgeted score strategy for speed/completion-rate frontier experiments."""
import time

from .coverage_risk import miss_risk
from .geometry import seven_points
from .score_routing import plan_open_route
from .score_strategy import ScoreStrategy


class SprintStrategy(ScoreStrategy):
    def __init__(self, client, logger=None, route_budget_s=1.0, deadline_margin_s=20,
                 risk_budget=.10):
        super().__init__(client, logger, route_budget_s, deadline_margin_s)
        if not 0 <= risk_budget <= 1:
            raise ValueError('risk_budget must be between 0 and 1')
        self.mode = 'sprint'
        self.risk_budget = float(risk_budget)
        self.estimated_miss_risk = 1.0

    def run(self):
        entered = self.client.enter()
        self._log('enter', response=entered, strategy_mode=self.mode,
                  risk_budget=self.risk_budget)
        self.started = time.monotonic()
        self.deadline = self.started+float(entered['remaining_real_duration_s'])
        self.position = (0.0, 0.0)
        coverage = {('scan', i): q for i, q in enumerate(seven_points(1123.0))}
        discovery_complete = False
        try:
            self._scan((0.0, 0.0))
            coverage.pop(('scan', 0))
            while self._time_ok():
                self.estimated_miss_risk = miss_risk(
                    self.scan_stations, len(self.unknown), len(self.found))
                if (not self.unknown or not coverage or
                        self.estimated_miss_risk <= self.risk_budget):
                    discovery_complete = True
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                pending = self.found-self.cleared
                if not pending and discovery_complete:
                    break
                tasks = {}
                if not discovery_complete:
                    tasks.update(coverage)
                for c in sorted(pending):
                    tasks[('target', c)] = self._task_point(c)
                if not tasks:
                    break
                available = max(0, self.deadline-time.monotonic()-self.deadline_margin_s)
                plan = plan_open_route(self.position, tasks,
                                       min(self.route_budget_s, available/20))
                self._log('plan', **plan)
                key = plan['order'][0]
                destination = tasks[plan['order'][1]] if len(plan['order']) > 1 else None
                if key[0] == 'scan':
                    self._scan(tasks[key])
                    coverage.pop(key, None)
                else:
                    self._service(key[1], destination)
                    self._maybe_replace_scan(coverage)
            response = self.client.exit()
            self._log('exit', response=response,
                      estimated_miss_risk=self.estimated_miss_risk)
            return {'strategy_mode': self.mode, 'found': len(self.found),
                    'cleared': len(self.cleared), 'unknown_channels': sorted(self.unknown),
                    'absent_channels': sorted(self.absent),
                    'discovery_complete': discovery_complete,
                    'coverage_stations': self.coverage_stations,
                    'risk_budget': self.risk_budget,
                    'estimated_miss_risk': self.estimated_miss_risk,
                    'virtual_time_s': response.get('virtual_time_s')}
        except Exception as exc:
            self._log('fatal', error=repr(exc))
            try:
                self.client.exit()
            except Exception:
                pass
            raise
