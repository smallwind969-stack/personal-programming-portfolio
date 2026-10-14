"""Experimental discovery-first ordering; never weakens the 21-station fallback."""
import math
from .q4_certified21_strategy import Q4Certified21Strategy
from .score_routing import plan_open_route


class Q4DiscoveryRaceStrategy(Q4Certified21Strategy):
    def __init__(self, *args, optimism=1., **kwargs):
        super().__init__(*args, **kwargs)
        self.optimism = optimism
        self.mode = 'q4_discovery_race' if optimism == 1. else 'q4_discovery_race_bold'
        self.reordered_tasks = 0

    def _scheduled_key(self, order, tasks, coverage):
        return order[0]

    def _refine_action_plan(self, order, tasks, coverage):
        if not self.unknown or not coverage or len(order) < 2:
            return order, tasks
        candidates = list(dict.fromkeys([order[0]] +
            [k for k in order if k[0] == 'certificate'][:8] +
            [k for k in order if k[0] == 'target'][:2]))
        scored = []
        for key in candidates:
            q = tasks[key]
            rest = {k: p for k, p in tasks.items() if k != key}
            tail = plan_open_route(q, rest, 0.)
            travel = (math.dist(self.position, q) + tail['distance_m']) / 5.
            # Earlier discovery can cancel this channel's future sweep actions.
            # This is an approximate saving, not a probability of task completion.
            hits = (sum(self.beliefs[c].hit_probability(q) for c in self.unknown)
                    if key[0] == 'certificate' else 0.)
            saved = self.optimism * 6. * max(0, len(coverage)-1) * hits
            scored.append((travel-saved, key != order[0], key, tail['order']))
        value, _, selected, tail_order = min(scored)
        self.reordered_tasks += int(selected != order[0])
        self._log('discovery_race', selected=selected, baseline=order[0],
                  approximate_cost_s=value, optimism=self.optimism)
        return [selected] + list(tail_order), tasks

    def run(self):
        result = super().run()
        result['reordered_tasks'] = self.reordered_tasks
        return result


class Q4DiscoveryRaceBoldStrategy(Q4DiscoveryRaceStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, optimism=2., **kwargs)
