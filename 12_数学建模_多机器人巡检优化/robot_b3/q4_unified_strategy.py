"""Q4 route-first strategy with expected-time adaptive localization."""

import math

from .full_view import receiver_side_probe_pairs
from .geometry import clear_visit_point
from .q4_localization_planner import (
    ProbeOption,
    choose_localization_probe,
    order_optical_clear_points,
)
from .q4_certificate import PerChannelDiscoveryCertificate
from .q4_routefirst_strategy import Q4RouteFirstStrategy


class Q4UnifiedStrategy(Q4RouteFirstStrategy):
    """Compare every extra bearing directly against optical completion time."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_unified'
        self._planned_localization = {}
        self._channel_certificate = None
        self._certificate_channels_by_key = {}

    @staticmethod
    def _certificate_key(point):
        return ('certificate', round(point[0], 8), round(point[1], 8))

    def _measure(self, q, c):
        result = super()._measure(q, c)
        if result == 'no_signal' and self._channel_certificate is not None:
            self._channel_certificate.record_no_signal(c, q)
        return result

    def _initial_certificate_tasks(self, layout):
        self._channel_certificate = PerChannelDiscoveryCertificate(layout)
        return self._refresh_certificate_tasks({}, layout)

    def _refresh_certificate_tasks(self, coverage, layout):
        certificate = self._channel_certificate
        if certificate is None:
            return super()._refresh_certificate_tasks(coverage, layout)

        newly_absent = {
            c for c in self.unknown if certificate.complete(c)
        }
        if newly_absent:
            self.absent.update(newly_absent)
            self.unknown.difference_update(newly_absent)
            self._log('channel_certified_absent',
                      channels=sorted(newly_absent))

        requirements = certificate.requirements(self.unknown)
        refreshed = {}
        channel_map = {}
        for point, channels in requirements.items():
            key = self._certificate_key(point)
            refreshed[key] = point
            channel_map[key] = set(channels)
        self._certificate_channels_by_key = channel_map
        return refreshed

    def _execute_certificate_task(self, key, point, coverage):
        channels = set(self._certificate_channels_by_key.get(key, ()))
        channels.intersection_update(self.unknown)
        ordered = sorted(channels)
        if self.client.current_channel in ordered:
            ordered.remove(self.client.current_channel)
            ordered.insert(0, self.client.current_channel)
        for channel in ordered:
            if not self._time_ok():
                return False
            self._measure(point, channel)
        self._guaranteed_here()
        return True

    def _after_target_service(self, coverage, layout):
        """Turn a free target visit into channel-specific certificate work."""
        certificate = self._channel_certificate
        if certificate is None or not self.unknown or not self._time_ok():
            return None
        point = tuple(self.position)
        substitutions = []
        for channel in sorted(tuple(self.unknown)):
            remaining = certificate.remaining(channel)
            exact = next((q for q in remaining
                          if math.dist(q, point) <= 1e-7), None)
            station = exact
            if station is None:
                station = certificate.best_replacement(
                    channel, point, start=point)
            if station is None:
                continue
            result = self._measure(point, channel)
            if result == 'no_signal' and exact is None:
                certificate.apply_replacement(channel, station, point)
                substitutions.append((channel, station))
        if substitutions:
            self.certificate_replacements += len(substitutions)
            self._log(
                'per_channel_certificate_replacement',
                position=point,
                replacements=[
                    {'channel': channel, 'old_station': station}
                    for channel, station in substitutions
                ],
            )
        self._guaranteed_here()
        return tuple(substitutions)

    def _candidate_probe_points(self, c, destination=None):
        center, _ = self._circle(c)
        positive = self.observations[c][0][0]
        dx, dy = positive[0] - center[0], positive[1] - center[1]
        distance = math.hypot(dx, dy)
        if distance <= 1e-9:
            angle = math.radians(self.observations[c][0][1])
            dx, dy, distance = math.cos(angle), math.sin(angle), 500.0
        ex, ey = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
        nx, ny = -ey, ex
        raw = [q for pair in receiver_side_probe_pairs(center, positive)
               for q in pair]
        scale = max(250.0, min(1100.0, distance))
        for alpha in (.30, .45, .60, .75, .90):
            base = (center[0] + alpha * dx, center[1] + alpha * dy)
            for beta in (.12, .24, .36, .48):
                offset = beta * scale
                raw.extend((
                    (base[0] + offset * nx, base[1] + offset * ny),
                    (base[0] - offset * nx, base[1] - offset * ny),
                ))
        if destination is not None:
            raw.extend((
                self.position[0] + t * (destination[0] - self.position[0]),
                self.position[1] + t * (destination[1] - self.position[1]),
            ) for t in (.25, .5, .75))

        unique = []
        seen = set()
        for q in raw:
            q = (float(q[0]), float(q[1]))
            key = round(q[0], 7), round(q[1], 7)
            if key in seen or (q, c) in self._measured:
                continue
            seen.add(key)
            unique.append(q)
        return tuple(unique)

    def _raw_optical_cover(self, c, radius=19.5):
        return super()._new_optical_cover(c, radius=radius)

    def _new_optical_cover(self, c, radius=19.5, belief=None, start=None):
        points = self._raw_optical_cover(c, radius=radius)
        belief = self.beliefs[c] if belief is None else belief
        start = self.position if start is None else tuple(start)
        return list(order_optical_clear_points(
            start, points, getattr(belief, 'particles', ()),
            clear_radius=20.0,
        ))

    def _optical_tail_estimate(self, c, start=None, belief=None,
                               optimize_order=True):
        belief = self.beliefs[c] if belief is None else belief
        start = self.position if start is None else tuple(start)
        if optimize_order:
            points = list(self._new_optical_cover(
                c, belief=belief, start=start))
        else:
            # During candidate screening the same strict geometric cover is
            # scored under many hypothetical miss posteriors.  Reordering the
            # entire cover for every branch dominated real execution time;
            # scoring both directions of the native sweep retains the full
            # cover and leaves the final, observed posterior to be optimized.
            points = list(self._raw_optical_cover(c))
        if not points:
            return math.inf
        particles = list(getattr(belief, 'particles', ()))

        def estimate(order):
            prefix = []
            distance = 0.0
            previous = start
            for q in order:
                distance += math.dist(previous, q)
                prefix.append(distance)
                previous = q
            if not particles:
                return prefix[-1] / 2.0 / 5.0 + 1.5 * (len(order) - 1) + 5.0
            total_weight = sum(p.weight for p in particles)
            if total_weight <= 0:
                return math.inf
            expected = 0.0
            for particle in particles:
                index = next(
                    (i for i, q in enumerate(order)
                     if math.dist((particle.x, particle.y), q) <= 20.0 + 1e-8),
                    len(order) - 1,
                )
                cost = prefix[index] / 5.0 + 3.0 * index + 5.0
                expected += particle.weight * cost
            return expected / total_weight

        return min(estimate(points), estimate(list(reversed(points))))

    def _probe_decision(self, c, destination=None):
        _, current_radius = self._circle(c)
        direct_tail = self._optical_tail_estimate(c)
        options = []
        for q in self._candidate_probe_points(c, destination):
            probability = self.beliefs[c].hit_probability(q)
            if probability <= 1e-9:
                continue
            predicted = self._prediction(c, q)
            if not math.isfinite(predicted):
                continue
            if predicted <= 19.5:
                center, _ = self._circle(c)
                hit_tail = math.dist(q, center) / 5.0 + 5.0
            else:
                shrink = min(1.0, (predicted / max(19.5, current_radius)) ** 2)
                hit_tail = max(5.0, direct_tail * shrink)
            miss_belief = self.beliefs[c].after_no_signal(q)
            miss_tail = self._optical_tail_estimate(
                c, start=q, belief=miss_belief, optimize_order=False)
            options.append(ProbeOption(q, probability, hit_tail, miss_tail))
        decision = choose_localization_probe(
            self.position, destination, self.client.current_channel, c,
            direct_tail, options,
        )
        self._log(
            'localization_value', channel=c,
            current_radius_m=current_radius,
            direct_optical_tail_s=direct_tail,
            candidate_count=len(options),
            selected_position=None if decision is None else decision.position,
            selected_expected_s=None if decision is None else decision.expected_total_s,
            selected_gain_s=None if decision is None else decision.expected_gain_s,
        )
        return decision

    def _target_point(self, c, destination=None):
        _, radius = self._circle(c)
        if radius <= 19.5:
            return clear_visit_point(self.poly[c], self.position, destination)
        decision = self._probe_decision(c, destination)
        if decision is not None:
            return decision.position
        optical = self._optical_queue(c)
        return optical[0] if optical else self._circle(c)[0]

    def _service_one(self, c, destination, remaining_sweeps):
        _, radius = self._circle(c)
        if radius <= 19.5:
            q = clear_visit_point(self.poly[c], self.position, destination)
            if not self._clear(q, c):
                raise RuntimeError(f'guaranteed unified clear failed on channel {c}')
        else:
            decision = self._probe_decision(c, destination)
            if decision is not None:
                self._measure(decision.position, c)
            else:
                optical = self._optical_queue(c)
                if not optical:
                    raise RuntimeError(f'empty unified optical cover on channel {c}')
                q = optical.pop(0)
                if self._clear(q, c):
                    self._optical_cover.pop(c, None)
                elif self._time_ok():
                    follow_up = self._probe_decision(c, destination)
                    if follow_up is None:
                        result = None
                    else:
                        result = self._measure(follow_up.position, c)
                    if result in ('direction', 'near') and c not in self.cleared:
                        center, new_radius = self._circle(c)
                        if new_radius <= 19.5 and self._clear(center, c):
                            self._optical_cover.pop(c, None)
        self._guaranteed_here()
