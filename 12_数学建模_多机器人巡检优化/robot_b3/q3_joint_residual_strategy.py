"""True per-channel residual/search/localize/clear rolling Q3 strategy."""

import math
import time

from .geometry import clear_visit_point
from .q3_joint_residual_planner import (
    plan_joint_residual, select_dominating_plan)
from .q3_oracle_fusion_strategy import replace_channel_requirements
from .residual_strategy import ResidualStrategy


class Q3JointResidualStrategy(ResidualStrategy):
    def __init__(self, client, logger=None, route_budget_s=1.0,
                 deadline_margin_s=20):
        super().__init__(client, logger, route_budget_s, deadline_margin_s)
        self.mode = 'q3_joint_residual'

    def _localization_variants(self, channel, anchors=()):
        center, radius = self._circle(channel)
        if radius <= 19.5:
            return [{'position': center, 'action': 'clear',
                     'predicted_radius': 0.0}]
        candidates = [self.refinement_point(channel), center]
        step = max(40.0, min(700.0, radius))
        candidates.extend((center[0]+step*math.cos(i*math.pi/4),
                           center[1]+step*math.sin(i*math.pi/4))
                          for i in range(8))
        for anchor in anchors:
            candidates.extend((self.position[0]+t*(anchor[0]-self.position[0]),
                               self.position[1]+t*(anchor[1]-self.position[1]))
                              for t in (.25, .5, .75))
        variants = []
        seen = set()
        for q in candidates:
            key = (round(q[0], 7), round(q[1], 7))
            if key in seen or (tuple(q), channel) in self._measured:
                continue
            seen.add(key)
            if max(math.dist(q, p) for p in self.poly[channel]) > 999.0:
                continue
            variants.append({
                'position': tuple(q), 'action': 'measure',
                'predicted_radius': self._prediction(channel, q),
                'return_distance': math.dist(q, center),
            })
        return variants or [{
            'position': self.refinement_point(channel), 'action': 'measure',
            'predicted_radius': radius,
            'return_distance': math.dist(self.refinement_point(channel), center),
        }]

    def _requirements_with_target_stations(self, requirements, positions):
        result = {tuple(q): set(channels)
                  for q, channels in requirements.items()}
        for channel in sorted(self.unknown):
            base = self.channel_completion(channel)
            extras = []
            for q in positions:
                trial = self.channel_completion(channel, extras+[q])
                if trial is not None and base is not None and len(trial) < len(base):
                    extras.append(tuple(q))
                    base = trial
            if extras:
                result = replace_channel_requirements(result, channel, base)
                for q in extras:
                    result.setdefault(q, set()).add(channel)
        return result

    def _plan(self, requirements, pending):
        anchors = list(requirements)
        variants = {c: self._localization_variants(c, anchors)
                    for c in sorted(pending)}
        first = plan_joint_residual(
            self.position, self.client.current_channel,
            requirements, variants, self.route_budget_s)
        positions = [v['position'] for v in first['selected_variants'].values()]
        joined = self._requirements_with_target_stations(requirements, positions)
        joined_plan = plan_joint_residual(
            self.position, self.client.current_channel,
            joined, variants, self.route_budget_s)
        return select_dominating_plan(first, joined_plan)

    def _execute_physical_task(self, task, exit_channel):
        q = tuple(task['position'])
        channels = [c for c in task['channels']
                    if c not in self.cleared and c not in self.absent]
        if self.client.current_channel in channels:
            channels.remove(self.client.current_channel)
            channels.insert(0, self.client.current_channel)
        if exit_channel in channels and channels[-1] != exit_channel:
            channels.remove(exit_channel)
            channels.append(exit_channel)
        for channel in channels:
            if self._time_ok():
                self._measure(q, channel)
        for channel, action in task['target_actions']:
            if action != 'clear' or channel in self.cleared:
                continue
            center, radius = self._circle(channel)
            if radius > 19.5:
                continue
            clear_q = clear_visit_point(self.poly[channel], q)
            if not self._clear(clear_q, channel):
                raise RuntimeError(
                    f'guaranteed optical clear failed on channel {channel}')
        self._guaranteed_here()

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
                plan = self._plan(requirements, pending)
                if not plan['order']:
                    break
                key = plan['order'][0]
                exit_channel = plan['station_exit_channels'][0]
                self._log('q3_joint_residual_plan', **{
                    k: v for k, v in plan.items()
                    if k not in ('tasks', 'selected_variants')})
                self._execute_physical_task(plan['tasks'][key], exit_channel)
            response = self.client.exit()
            self._log('exit', response=response)
            return {
                'strategy_mode': self.mode, 'found': len(self.found),
                'cleared': len(self.cleared),
                'unknown_channels': sorted(self.unknown),
                'absent_channels': sorted(self.absent),
                'discovery_complete': discovery_complete,
                'virtual_time_s': response.get('virtual_time_s'),
            }
        except Exception as exc:
            self._log('fatal', error=repr(exc))
            try:
                self.client.exit()
            except Exception:
                pass
            raise
