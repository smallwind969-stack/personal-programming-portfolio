"""Per-channel certified Q3 search with virtual-time-aware shared routing."""

import time

from .q3_time_route import evaluate_time_order, plan_time_aware_open_route
from .residual_strategy import ResidualStrategy
from .score_routing import plan_open_route


def _completion_tasks(points, channel):
    return {
        i: {'position': tuple(q), 'channels': (int(channel),)}
        for i, q in enumerate(points)
    }


def optional_scan_is_better(start, current_channel, channel, before, after):
    """Compare certified completion time after paying for a scan at `start`."""
    old = plan_time_aware_open_route(
        start, current_channel, _completion_tasks(before, channel))
    new = plan_time_aware_open_route(
        start, channel, _completion_tasks(after, channel))
    immediate = 5.0 + (0.0 if current_channel == channel else 1.0)
    return immediate + new['total_time_s'] < old['total_time_s'] - 1e-9


def select_robust_plan(baseline, candidate, uncertainty_margin_s):
    """Change route only when predicted gain exceeds tail-model uncertainty."""
    if ('distance_m' in baseline and 'distance_m' in candidate
            and abs(candidate['distance_m'] - baseline['distance_m']) > 1e-7):
        return baseline
    if candidate['total_time_s'] < baseline['total_time_s'] - uncertainty_margin_s:
        return candidate
    return baseline


def replace_channel_requirements(requirements, channel, completion):
    """Replace one channel's future certificate without touching the others."""
    updated = {}
    for q, channels in requirements.items():
        retained = set(channels) - {channel}
        if retained:
            updated[tuple(q)] = retained
    for q in completion:
        updated.setdefault(tuple(q), set()).add(channel)
    return updated


class Q3OracleFusionStrategy(ResidualStrategy):
    """Fuse strict residual certificates with time-aware physical routing."""

    def __init__(self, client, logger=None, route_budget_s=1.0,
                 deadline_margin_s=20):
        super().__init__(client, logger, route_budget_s, deadline_margin_s)
        self.mode = 'q3_oracle_fusion'

    def _target_channels(self, channel):
        _, radius = self._circle(channel)
        return () if radius <= 19.5 else (channel,)

    def _time_tasks(self, requirements, pending):
        tasks = {}
        for i, (q, channels) in enumerate(requirements.items()):
            tasks[('scan', i, tuple(q))] = {
                'position': tuple(q),
                'channels': tuple(sorted(channels)),
                'service_s': 0.0,
            }
        for channel in sorted(pending):
            channels = self._target_channels(channel)
            tasks[('target', channel)] = {
                'position': tuple(self._task_point(channel)),
                'channels': channels,
                'service_s': 5.0 if not channels else 0.0,
            }
        return tasks

    def _time_plan(self, requirements, pending, current_channel=None,
                   budget_s=None):
        tasks = self._time_tasks(requirements, pending)
        current_channel = (self.client.current_channel if current_channel is None
                           else current_channel)
        budget_s = self.route_budget_s if budget_s is None else budget_s
        candidate = plan_time_aware_open_route(
            self.position, current_channel, tasks, budget_s=budget_s)
        distance_plan = plan_open_route(
            self.position,
            {name: task['position'] for name, task in tasks.items()},
            budget_s)
        baseline = evaluate_time_order(
            self.position, current_channel,
            distance_plan['order'], tasks)
        baseline['proven_optimal'] = distance_plan['proven_optimal']
        baseline['route_incumbent_used'] = True
        margin = max(8.0, 0.01 * baseline['total_time_s'])
        result = select_robust_plan(baseline, candidate, margin)
        result['used_time_route'] = result is candidate
        result['model_uncertainty_margin_s'] = margin
        result['tasks'] = tasks
        return result

    def opportunistic_unknown_scan(self):
        """Take certificate-reducing scans; use the global model as an audit."""
        measured = []
        q = tuple(self.position)
        for channel in sorted(tuple(self.unknown)):
            channel_before = self.channel_completion(channel)
            completion = self.channel_completion(channel, [q])
            if (channel_before is None or completion is None
                    or len(completion) >= len(channel_before)):
                continue
            before_requirements = self.coverage_requirements()
            pending = self.found - self.cleared
            short_budget = min(.003, self.route_budget_s)
            before = self._time_plan(
                before_requirements, pending, budget_s=short_budget)
            after_requirements = replace_channel_requirements(
                before_requirements, channel, completion)
            after = self._time_plan(
                after_requirements, pending, current_channel=channel,
                budget_s=short_budget)
            immediate = 5.0 + (
                0.0 if self.client.current_channel == channel else 1.0)
            self._log(
                'q3_opportunity_audit', channel=channel,
                certificate_stations_removed=(
                    len(channel_before) - len(completion)),
                predicted_total_gain_s=(
                    before['total_time_s'] - immediate - after['total_time_s']),
            )
            self._measure(q, channel)
            measured.append(channel)
        self._guaranteed_here()
        return measured

    def run(self):
        entered = self.client.enter()
        self._log('enter', response=entered, strategy_mode=self.mode)
        self.started = time.monotonic()
        self.deadline = self.started + float(entered['remaining_real_duration_s'])
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
                pending = self.found - self.cleared
                if not pending and discovery_complete:
                    break
                if not requirements and not pending:
                    break
                plan = self._time_plan(requirements, pending)
                self._log(
                    'q3_oracle_fusion_plan', order=plan['order'],
                    distance_m=plan['distance_m'],
                    expected_time_s=plan['total_time_s'],
                    planned_measurements=plan['measurements'],
                    planned_switches=plan['switches'],
                    proven_optimal=plan['proven_optimal'],
                )
                key = plan['order'][0]
                task = plan['tasks'][key]
                next_position = (plan['tasks'][plan['order'][1]]['position']
                                 if len(plan['order']) > 1 else None)
                if key[0] == 'scan':
                    q = tuple(task['position'])
                    if not self._scan_required(q, set(task['channels'])):
                        break
                else:
                    self._service(key[1], next_position)
                    self.opportunistic_unknown_scan()
            response = self.client.exit()
            self._log('exit', response=response)
            certified = sum(not self.channel_completion(c) for c in self.absent)
            return {
                'strategy_mode': self.mode,
                'found': len(self.found), 'cleared': len(self.cleared),
                'unknown_channels': sorted(self.unknown),
                'absent_channels': sorted(self.absent),
                'discovery_complete': discovery_complete,
                'certified_empty_channels': certified,
                'virtual_time_s': response.get('virtual_time_s'),
            }
        except Exception as exc:
            self._log('fatal', error=repr(exc))
            try:
                self.client.exit()
            except Exception:
                pass
            raise
