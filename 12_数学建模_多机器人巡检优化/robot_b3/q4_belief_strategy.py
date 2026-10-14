"""Independent Q4 planner driven by expected remaining virtual time."""
import math
import time

from .full_view import build_competition_full_view_layout, receiver_side_probe_pairs
from .fusion_strategy import FusionStrategy
from .geometry import clear_visit_point, point_polygon_distance
from .q4_belief import ChannelBelief, opportunity_value_seconds
from .q4_rollout import OpportunityRolloutPlanner
from .score_routing import plan_open_route


class Q4BeliefStrategy(FusionStrategy):
    """Safe full-view fallback with belief-ranked zero-detour measurements."""

    max_probe_actions = 3

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_belief'
        self.beliefs = {c: ChannelBelief.prior() for c in range(1, 21)}
        self.rollout = OpportunityRolloutPlanner(depth=2, beam_width=6)
        self._rollout_window = False
        self.absent = set()
        self._probe_queues = {}
        self._probe_attempts = {}
        self._optical_cover = {}
        self.opportunity_measures = 0
        self.cancelled_sweeps = 0
        self.last_discovery_virtual_time_s = None

    def _measure(self, q, c):
        before = len(self.found)
        result = super()._measure(q, c)
        if result == 'direction':
            self.beliefs[c].condition_polygon(self.poly[c])
            self.beliefs[c].observe_direction(tuple(q))
        elif result == 'near':
            self.beliefs[c].observe_signal(tuple(q))
        elif result == 'no_signal':
            self.beliefs[c].observe_no_signal(tuple(q))
        if len(self.found) > before:
            self.last_discovery_virtual_time_s = self.client.virtual_time_s
        return result

    def _clear(self, q, c):
        success = super()._clear(q, c)
        if not success and c in self.found:
            self.beliefs[c].observe_clear_miss(tuple(q))
        return success

    def _opportunity_channels(self, remaining_sweeps):
        ranked = []
        current = self.client.current_channel
        for c in self.unknown:
            probability = self.beliefs[c].hit_probability(self.position)
            value = opportunity_value_seconds(
                probability, remaining_sweeps, current != c)
            if value > 0:
                ranked.append((value, probability, c))
        ranked.sort(reverse=True)
        return ranked

    def _next_rollout_decision(self, remaining_sweeps):
        if not self._rollout_window or not self.unknown or remaining_sweeps <= 0:
            return None
        return self.rollout.choose(
            self.position, self.client.current_channel,
            remaining_sweeps, self.beliefs, self.unknown)

    def _opportunity_scan(self, remaining_sweeps):
        """Buy only measurements with positive expected future sweep savings."""
        scanned = 0
        while self.unknown and self._time_ok():
            ranked = self._opportunity_channels(remaining_sweeps)
            if not ranked:
                break
            value, probability, c = ranked[0]
            self._log('belief_action', action='opportunity_measure', channel=c,
                      hit_probability=probability, expected_net_s=value,
                      remaining_sweeps=remaining_sweeps)
            self._measure(self.position, c)
            self.opportunity_measures += 1
            scanned += 1
            if len(self.found) == 16:
                break
        return scanned

    def _scheduled_key(self, order, tasks, coverage):
        """Trade a local route insertion against earlier expected discoveries."""
        baseline = order[0]
        if baseline[0] != 'certificate' or not self.unknown:
            return baseline
        base_point = tasks[baseline]
        sweeps = len(coverage)

        def discovery_value(q):
            return sum(self.beliefs[c].hit_probability(q)*6.0*sweeps
                       for c in self.unknown)

        best = (discovery_value(base_point), baseline)
        considered = 0
        for key in order:
            if key[0] != 'certificate':
                continue
            considered += 1
            if considered > 8:
                break
            q = tasks[key]
            insertion = (math.dist(self.position, q)+math.dist(q, base_point)
                         -math.dist(self.position, base_point))/5.0
            score = discovery_value(q)-insertion
            if score > best[0]+1e-9:
                best = (score, key)
        if best[1] != baseline:
            self._log('belief_action', action='advance_certificate',
                      selected=best[1], baseline=baseline,
                      expected_net_s=best[0]-discovery_value(base_point))
        return best[1]

    @staticmethod
    def _interval_centers(lo, hi, spacing):
        width = max(0.0, hi-lo)
        count = max(1, int(math.ceil(width/spacing)))
        cell = width/count if width else 0.0
        return [(lo+hi)/2] if not width else [lo+(i+.5)*cell for i in range(count)]

    def _new_optical_cover(self, c, radius=19.5):
        station, bearing = self.observations[c][-1]
        a = math.radians(bearing)
        u = (math.cos(a), math.sin(a))
        n = (-u[1], u[0])

        def project(p):
            d = (p[0]-station[0], p[1]-station[1])
            return d[0]*u[0]+d[1]*u[1], d[0]*n[0]+d[1]*n[1]

        coordinates = [project(p) for p in self.poly[c]]
        spacing = radius*math.sqrt(2)
        along = self._interval_centers(min(x for x, _ in coordinates),
                                       max(x for x, _ in coordinates), spacing)
        across = self._interval_centers(min(y for _, y in coordinates),
                                        max(y for _, y in coordinates), spacing)
        points = []
        for row, y in enumerate(across):
            xs = along if row % 2 == 0 else list(reversed(along))
            points.extend((station[0]+x*u[0]+y*n[0],
                           station[1]+x*u[1]+y*n[1]) for x in xs)
        points = [q for q in points
                  if point_polygon_distance(q, self.poly[c]) <= radius + 1e-8]
        if points and math.dist(self.position, points[-1]) < math.dist(self.position, points[0]):
            points.reverse()
        return points

    def _optical_queue(self, c):
        signature = (len(self.observations[c]),
                     tuple((round(x, 5), round(y, 5)) for x, y in self.poly[c]))
        cached = self._optical_cover.get(c)
        if cached is None or cached[0] != signature:
            cached = (signature, self._new_optical_cover(c))
            self._optical_cover[c] = cached
        return cached[1]

    def _probe_queue(self, c):
        if self._probe_attempts.get(c, 0) >= self.max_probe_actions:
            return []
        signature = len(self.observations[c])
        cached = self._probe_queues.get(c)
        if cached is None or cached[0] != signature:
            center, _ = self._circle(c)
            positive = self.observations[c][0][0]
            points = [q for pair in receiver_side_probe_pairs(center, positive)
                      for q in pair]
            cached = (signature, points)
            self._probe_queues[c] = cached
        return cached[1]

    def _target_point(self, c, destination=None):
        _, radius = self._circle(c)
        if radius <= 19.5:
            return clear_visit_point(self.poly[c], self.position, destination)
        probes = self._probe_queue(c)
        if probes:
            return min(probes, key=lambda q: math.dist(self.position, q))
        optical = self._optical_queue(c)
        return optical[0] if optical else self._circle(c)[0]

    def _service_one(self, c, destination, remaining_sweeps):
        _, radius = self._circle(c)
        if radius <= 19.5:
            q = clear_visit_point(self.poly[c], self.position, destination)
            if not self._clear(q, c):
                raise RuntimeError(f'guaranteed Q4 belief clear failed on channel {c}')
        else:
            probes = self._probe_queue(c)
            if probes:
                q = min(probes, key=lambda p: math.dist(self.position, p))
                probes.remove(q)
                self._probe_attempts[c] = self._probe_attempts.get(c, 0)+1
                self._measure(q, c)
            else:
                optical = self._optical_queue(c)
                if not optical:
                    raise RuntimeError(f'empty optical cover for channel {c}')
                q = optical.pop(0)
                if self._clear(q, c):
                    self._optical_cover.pop(c, None)
        self._guaranteed_here()

    def _build_fallback_layout(self):
        """Layout hook retained for independently verifiable Q4 variants."""
        return build_competition_full_view_layout(start=(0.0, 0.0))

    def _after_target_service(self, coverage, layout):
        """Optional post-service hook; the baseline keeps every certificate."""
        return None

    def _initial_certificate_tasks(self, layout):
        return {('certificate', i): q for i, q in enumerate(layout.stations)}

    def _refresh_certificate_tasks(self, coverage, layout):
        """Hook for variants whose residual certificate changes by channel."""
        return coverage

    def _execute_certificate_task(self, key, point, coverage):
        return self._scan(point)

    def _refine_action_plan(self, order, tasks, coverage):
        return order, tasks

    def run(self):
        layout = self._build_fallback_layout()
        entered = self.client.enter()
        self._log('enter', response=entered, strategy_mode=self.mode,
                  fallback_stations=len(layout.stations),
                  fallback_route_m=layout.route_distance_m)
        self.started = time.monotonic()
        self.deadline = self.started+float(entered['remaining_real_duration_s'])
        self.position = (0.0, 0.0)
        coverage = self._initial_certificate_tasks(layout)
        discovery_complete = False
        try:
            while self._time_ok():
                coverage = self._refresh_certificate_tasks(coverage, layout)
                if len(self.found) == 16:
                    self.cancelled_sweeps += len(coverage)
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                    coverage.clear()
                    discovery_complete = True
                elif not coverage:
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                    discovery_complete = True

                if not discovery_complete and self.unknown and coverage:
                    decision = self._next_rollout_decision(len(coverage))
                    if decision is not None:
                        self._log(
                            'rollout_action', action='measure',
                            channel=decision.channel,
                            position=self.position,
                            expected_delta_s=decision.expected_delta_s,
                            hit_probability=decision.hit_probability,
                            branches_evaluated=decision.branches_evaluated,
                            depth=decision.depth)
                        result = self._measure(self.position, decision.channel)
                        self.opportunity_measures += 1
                        self._log('rollout_observation', channel=decision.channel,
                                  result=result)
                        continue
                    self._rollout_window = False

                pending = self.found-self.cleared
                if discovery_complete and not pending:
                    break
                tasks = dict(coverage) if not discovery_complete else {}
                target_keys = []
                for c in sorted(pending):
                    key = ('target', c)
                    target_keys.append(key)
                    tasks[key] = self._target_point(c)
                if not tasks:
                    break
                available = max(0.0, self.deadline-time.monotonic()-self.deadline_margin_s)
                cap = .10 if len(tasks) > 12 else .40
                plan = plan_open_route(
                    self.position, tasks,
                    min(self.route_budget_s, cap, available/20))
                order = plan['order']
                order, tasks = self._refine_action_plan(order, tasks, coverage)
                key = self._scheduled_key(order, tasks, coverage)
                index = order.index(key)
                destination = tasks[order[index+1]] if index+1 < len(order) else None
                self._log('belief_plan', **plan)
                if key[0] == 'certificate':
                    if self._execute_certificate_task(
                            key, tasks[key], coverage):
                        coverage.pop(key, None)
                    self._rollout_window = False
                else:
                    self._service_one(key[1], destination, len(coverage))
                    self._after_target_service(coverage, layout)
                    self._rollout_window = True

            response = self.client.exit()
            self._log('exit', response=response)
            return {
                'strategy_mode': self.mode,
                'found': len(self.found),
                'cleared': len(self.cleared),
                'unknown_channels': sorted(self.unknown),
                'absent_channels': sorted(self.absent),
                'discovery_complete': discovery_complete,
                'opportunity_measures': self.opportunity_measures,
                'cancelled_sweeps': self.cancelled_sweeps,
                'certificate_replacements': getattr(
                    self, 'certificate_replacements', 0),
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
