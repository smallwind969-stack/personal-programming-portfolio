"""Safe rolling dynamic optimizer for Problem B, Question 3.

Per-channel residual disk coverage proves discovery.  A separate omnidirectional
belief ranks measurements and never removes deterministic feasible positions.
"""
import math

from .active_localization import guaranteed_reception
from .fusion_strategy import FusionStrategy
from .geometry import clear_visit_point
from .q3_belief import Q3ChannelBelief
from .q3_dynamic_planner import (ActionEstimate, choose_action,
                                 expected_information_gain,
                                 measure_immediate_time,
                                 optical_clear_chain)
from .residual_strategy import ResidualStrategy
from .routing import optimal_open_route


def opportunity_is_better(old_route_m, new_route_m, immediate_measure_s,
                          old_future_measure_s, new_future_measure_s,
                          hit_probability, expected_hit_saving_s):
    old_total = old_route_m / 5.0 + old_future_measure_s
    new_total = (immediate_measure_s + new_route_m / 5.0
                 + new_future_measure_s
                 - hit_probability * expected_hit_saving_s)
    return new_total < old_total - 1e-9


class Q3DynamicStrategy(ResidualStrategy, FusionStrategy):
    """ResidualStrategy with belief-ranked, route-aware dynamic actions."""

    def __init__(self, client, logger=None, route_budget_s=1.0,
                 deadline_margin_s=20):
        super().__init__(client, logger, route_budget_s, deadline_margin_s)
        self.mode = 'q3_dynamic'
        self.beliefs = {
            c: Q3ChannelBelief.prior() for c in range(1, 21)
        }

    def _build_optical_clear_chain(self, polygon, start, destination=None):
        return optical_clear_chain(
            polygon, start, destination=destination, clear_radius=20.0)

    def _measure(self, q, c):
        result = super()._measure(q, c)
        belief = self.beliefs[c]
        if result == 'no_signal':
            belief.observe_no_signal(q)
        elif result == 'direction':
            belief.observe_direction(q)
            belief.condition_polygon(self.poly[c])
        elif result == 'near':
            belief.observe_near(q)
        return result

    def _clear(self, q, c):
        success = super()._clear(q, c)
        if not success and c in self.beliefs:
            self.beliefs[c].observe_clear_miss(q)
        return success

    def likely_reception(self, c, q, margin=None):
        if c not in self.observations or not self.observations[c]:
            return self.beliefs[c].hit_probability(q) > 0.0
        stations = [station for station, _ in self.observations[c]]
        return guaranteed_reception(self.poly[c], q, stations)

    def _candidate_expected_action(self, c, q, destination):
        predicted = self._prediction(c, q)
        if not math.isfinite(predicted):
            return None
        center, radius = self._circle(c)
        probabilities = self.beliefs[c].outcome_probabilities(q)
        immediate = measure_immediate_time(
            self.position, q, self.client.current_channel, c)
        if destination is None:
            route_tail_m = math.dist(q, center)
        else:
            route_tail_m = min(
                math.dist(q, center) + math.dist(center, destination),
                math.dist(q, destination) + math.dist(destination, center),
            )
        direction_tail = route_tail_m / 5.0
        if predicted > 20.0:
            direction_tail += 5.0 + max(0.0, predicted - 20.0) / 5.0
        no_signal_tail = route_tail_m / 5.0 + 5.0 + max(0.0, radius - 20.0) / 5.0
        outcomes = (
            (probabilities['near'], 5.0),
            (probabilities['direction'], direction_tail),
            (probabilities['no_signal'], no_signal_tail),
        )
        return ActionEstimate(
            'measure', tuple(q), c, immediate, outcomes,
            information_gain_bits=expected_information_gain(self.beliefs[c], q),
            mec_gain_m=max(0.0, radius - predicted),
        )

    def refinement_point(self, c, destination=None):
        stations = [station for station, _ in self.observations.get(c, ())]
        seen = set()
        legal = []
        candidates = self._coarse_candidates(c, destination)
        for q in candidates:
            q = tuple(q)
            key = round(q[0], 7), round(q[1], 7)
            if key in seen or (q, c) in self._measured:
                continue
            seen.add(key)
            if guaranteed_reception(self.poly[c], q, stations):
                action = self._candidate_expected_action(c, q, destination)
                if action is not None:
                    legal.append(action)
        for step in (100.0, 30.0):
            seeds = [a.position for a in sorted(
                legal, key=lambda a: a.expected_time_s)[:6]]
            for seed in seeds:
                for dx in (-step, 0.0, step):
                    for dy in (-step, 0.0, step):
                        q = (seed[0] + dx, seed[1] + dy)
                        key = round(q[0], 7), round(q[1], 7)
                        if key in seen or (q, c) in self._measured:
                            continue
                        seen.add(key)
                        if guaranteed_reception(self.poly[c], q, stations):
                            action = self._candidate_expected_action(c, q, destination)
                            if action is not None:
                                legal.append(action)
        if not legal:
            return FusionStrategy.refinement_point(self, c, destination)
        selected = choose_action(legal)
        self._log(
            'q3_dynamic_decision', channel=c, destination=destination,
            selected_position=selected.position,
            expected_time_s=selected.expected_time_s,
            information_gain_bits=selected.information_gain_bits,
            mec_gain_m=selected.mec_gain_m,
            total_candidates=len(seen), feasible_candidates=len(legal),
            empirical_gate_s=None,
        )
        return selected.position

    def _useful_bearing(self, c, q):
        q = tuple(q)
        if (q, c) in self._measured:
            return False
        center, radius = self._circle(c)
        if radius <= 20.0 + 1e-8 or not self.likely_reception(c, q):
            return False
        predicted = self._prediction(c, q)
        if not math.isfinite(predicted):
            return False
        immediate = measure_immediate_time(
            self.position, q, self.client.current_channel, c)
        old_tail = math.dist(q, center) / 5.0 + max(0.0, radius - 20.0) / 5.0
        new_tail = math.dist(q, center) / 5.0 + max(0.0, predicted - 20.0) / 5.0
        return immediate + new_tail < old_tail - 1e-9

    def _service(self, c, destination):
        _, radius = self._circle(c)
        if radius <= 20.0 + 1e-8:
            q = clear_visit_point(self.poly[c], self.position, destination)
            if not self._clear(q, c):
                raise RuntimeError(f'guaranteed optical clear failed on channel {c}')
        else:
            q = self.refinement_point(c, destination)
            measure_action = self._candidate_expected_action(c, q, destination)
            chain = None
            if len(self.observations.get(c, ())) >= 3:
                chain = self._build_optical_clear_chain(
                    self.poly[c], self.position, destination=destination)
            stalled = (measure_action is None or
                       (measure_action.mec_gain_m <= 1e-6 and
                        measure_action.information_gain_bits <= 1e-9))
            if chain is not None and (stalled or
                                      chain.expected_time_s <= measure_action.expected_time_s):
                self._log(
                    'q3_clear_chain_decision', channel=c,
                    radius_m=radius, clear_points=len(chain.points),
                    clear_upper_time_s=chain.upper_time_s,
                    measure_expected_time_s=(None if measure_action is None
                                             else measure_action.expected_time_s),
                    stalled_measure=stalled,
                )
                for clear_point in chain.points:
                    if not self._time_ok():
                        break
                    if self._clear(clear_point, c):
                        break
                if c not in self.cleared and self._time_ok():
                    raise RuntimeError(
                        f'finite optical cover exhausted without clearing channel {c}')
            else:
                self._measure(q, c)
        self._guaranteed_here()
        for other in sorted(self.found - self.cleared):
            if other != c and self._time_ok() and self._useful_bearing(other, self.position):
                self._measure(self.position, other)
        self._guaranteed_here()

    def _completion_route(self, completion):
        tasks = {('scan', i): q for i, q in enumerate(completion)}
        tasks.update({('target', c): self._task_point(c)
                      for c in sorted(self.found - self.cleared)})
        return optimal_open_route(self.position, tasks)[1]

    def opportunistic_unknown_scan(self):
        """Take a zero-detour scan whenever its expected total time is lower."""
        measured = []
        q = tuple(self.position)
        for c in sorted(tuple(self.unknown)):
            before = self.channel_completion(c)
            after = self.channel_completion(c, [q])
            if before is None or after is None:
                continue
            immediate = measure_immediate_time(
                self.position, q, self.client.current_channel, c)
            hit_probability = self.beliefs[c].hit_probability(q)
            if opportunity_is_better(
                self._completion_route(before),
                self._completion_route(after),
                immediate,
                6.0 * len(before),
                6.0 * len(after),
                hit_probability,
                6.0 * len(before),
            ):
                self._measure(q, c)
                measured.append(c)
        self._guaranteed_here()
        return measured
