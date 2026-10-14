"""Expected-completion-time choice between another bearing and optical clear."""

from dataclasses import dataclass
import itertools
import math


@dataclass(frozen=True)
class ProbeOption:
    position: tuple
    hit_probability: float
    hit_tail_s: float
    miss_tail_s: float


@dataclass(frozen=True)
class LocalizationDecision:
    position: tuple
    expected_total_s: float
    direct_optical_tail_s: float
    hit_probability: float
    expected_gain_s: float


def _route_insertion_s(position, candidate, destination):
    if destination is None:
        return math.dist(position, candidate) / 5.0
    extra = (math.dist(position, candidate)
             + math.dist(candidate, destination)
             - math.dist(position, destination))
    return max(0.0, extra) / 5.0


def choose_localization_probe(position, destination, current_channel,
                              target_channel, direct_optical_tail_s, options):
    """Return the probe beating direct optical search, or ``None``."""
    best = None
    for option in options:
        probability = min(1.0, max(0.0, float(option.hit_probability)))
        immediate = _route_insertion_s(position, option.position, destination)
        immediate += 5.0 + (0.0 if current_channel == target_channel else 1.0)
        expected = (immediate
                    + probability * float(option.hit_tail_s)
                    + (1.0 - probability) * float(option.miss_tail_s))
        decision = LocalizationDecision(
            tuple(option.position), expected, float(direct_optical_tail_s),
            probability, float(direct_optical_tail_s) - expected,
        )
        if best is None or decision.expected_total_s < best.expected_total_s:
            best = decision
    if best is None or best.expected_total_s >= direct_optical_tail_s - 1e-9:
        return None
    return best


def _expected_optical_time(start, order, particles, clear_radius):
    if not order:
        return math.inf
    prefix = []
    distance = 0.0
    previous = tuple(start)
    for q in order:
        distance += math.dist(previous, q)
        prefix.append(distance)
        previous = q
    total_weight = sum(max(0.0, float(p.weight)) for p in particles)
    if total_weight <= 0.0:
        return prefix[-1] / 5.0 + 3.0 * max(0, len(order) - 1) + 5.0
    expected = 0.0
    for particle in particles:
        weight = max(0.0, float(particle.weight))
        if weight <= 0.0:
            continue
        index = next((i for i, q in enumerate(order)
                      if math.dist((particle.x, particle.y), q)
                      <= clear_radius + 1e-9), None)
        if index is None:
            cost = prefix[-1] / 5.0 + 3.0 * len(order)
        else:
            cost = prefix[index] / 5.0 + 3.0 * index + 5.0
        expected += weight * cost
    return expected / total_weight


def order_optical_clear_points(start, points, particles, clear_radius=20.0,
                               exact_limit=8, local_search_prefix=16,
                               local_search_passes=2):
    """Order a strict optical cover by expected time to the first hit.

    Every supplied point remains in the route, so reordering cannot weaken the
    deterministic cover.  Small covers are solved exactly; larger covers use a
    probability-per-second construction followed by bounded pair-swap
    improvement.  Only the probability-dominant prefix is refined: the suffix
    remains a complete strict cover, while online planning work is independent
    of the square of a potentially large cover size.
    """
    unique = []
    seen = set()
    for point in points:
        point = tuple(point)
        key = round(point[0], 9), round(point[1], 9)
        if key not in seen:
            seen.add(key)
            unique.append(point)
    if len(unique) <= 1:
        return tuple(unique)
    particles = tuple(particles)
    if len(unique) <= exact_limit:
        return min(
            itertools.permutations(unique),
            key=lambda order: _expected_optical_time(
                start, order, particles, clear_radius),
        )

    remaining = list(unique)
    unresolved = list(particles)
    current = tuple(start)
    order = []
    while remaining:
        def priority(q):
            captured = sum(
                max(0.0, float(p.weight)) for p in unresolved
                if math.dist((p.x, p.y), q) <= clear_radius + 1e-9
            )
            action_s = math.dist(current, q) / 5.0 + 3.0
            return captured / max(1e-9, action_s), -action_s

        chosen = max(remaining, key=priority)
        remaining.remove(chosen)
        order.append(chosen)
        unresolved = [
            p for p in unresolved
            if math.dist((p.x, p.y), chosen) > clear_radius + 1e-9
        ]
        current = chosen

    best_cost = _expected_optical_time(start, order, particles, clear_radius)
    prefix_size = min(len(order), max(2, int(local_search_prefix)))
    for _ in range(max(0, int(local_search_passes))):
        pass_order = None
        pass_cost = best_cost
        for i in range(prefix_size - 1):
            for j in range(i + 1, prefix_size):
                candidate = list(order)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                cost = _expected_optical_time(
                    start, candidate, particles, clear_radius)
                if cost < pass_cost - 1e-9:
                    pass_order, pass_cost = candidate, cost
        if pass_order is None:
            break
        order, best_cost = pass_order, pass_cost
    return tuple(order)
