"""Strict online strategy with joint coverage-station and target routing."""
import time

from .fusion_strategy import FusionStrategy
from .geometry import seven_points
from .joint_coverage import optimize_joint_cover
from .score_routing import plan_open_route


class JointStrategy(FusionStrategy):
    """Replan unvisited cover centers and located sources after every action."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'joint'

    def _joint_plan(self, coverage, pending, initial=False):
        targets = {c: self._task_point(c) for c in sorted(pending)}
        centers = list(coverage.values())
        budget = min(.35 if initial else .12,
                     max(.04, self.route_budget_s*(.35 if initial else .12)))
        result = optimize_joint_cover(
            self.position,
            self.scan_stations,
            len(centers),
            targets=targets,
            initial_free=centers,
            budget_s=budget,
        )
        if result is None:
            return None
        coverage.clear()
        generation = len(self.scan_stations)
        for i, q in enumerate(result['centers']):
            coverage[('scan', 'joint', generation, i)] = q
        self._log('coverage_plan', initial=initial,
                  remaining_stations=len(coverage),
                  coverage_radius_m=result['coverage_radius_m'],
                  coverage_witness=result['coverage_witness'],
                  incumbent_distance_m=result['incumbent_distance_m'],
                  route_distance_m=result['distance_m'],
                  improvement_m=result['improvement_m'],
                  evaluations=result['evaluations'],
                  used_symmetric_fallback=result['used_symmetric_fallback'])
        return result

    def run(self):
        entered = self.client.enter()
        self._log('enter', response=entered, strategy_mode=self.mode)
        self.started = time.monotonic()
        self.deadline = self.started+float(entered['remaining_real_duration_s'])
        self.position = (0.0, 0.0)

        # The symmetric construction is only the incumbent.  Unlike the former
        # strategy, no instruction forces (0,0) to be measured first.
        coverage = {('scan', 'seed', i): q
                    for i, q in enumerate(seven_points(1123.0))}
        discovery_complete = False
        last_signature = None
        try:
            self._joint_plan(coverage, set(), initial=True)
            while self._time_ok():
                if not self.unknown or not coverage:
                    discovery_complete = True
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                pending = self.found-self.cleared
                if not pending and discovery_complete:
                    break

                # Rebuild only when information or the robot state changed.  The
                # warm start preserves the previous exact coverage certificate.
                signature = (len(self.scan_stations), tuple(sorted(pending)),
                             round(self.position[0], 3), round(self.position[1], 3),
                             len(coverage))
                if not discovery_complete and signature != last_signature:
                    self._joint_plan(coverage, pending)
                    last_signature = signature

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
                order = plan['order']
                key = order[0]
                destination = tasks[order[1]] if len(order) > 1 else None
                if key[0] == 'scan':
                    self._scan(tasks[key])
                    coverage.pop(key, None)
                else:
                    self._service(key[1], destination)

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
                'virtual_time_s': response.get('virtual_time_s'),
            }
        except Exception as exc:
            self._log('fatal', error=repr(exc))
            try:
                self.client.exit()
            except Exception:
                pass
            raise
