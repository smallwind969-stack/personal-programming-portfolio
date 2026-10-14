"""Small, auditable value functions for the rolling Q3 decision layer."""
from dataclasses import dataclass
import math

from .geometry import enclosing_circle
from .routing import optimal_open_route


@dataclass(frozen=True)
class PlanEstimate:
    name: str
    total_time_s: float
    station_count: int = 0


@dataclass(frozen=True)
class ActionEstimate:
    kind: str
    position: tuple
    channel: int | None
    immediate_time_s: float
    outcomes: tuple
    information_gain_bits: float = 0.0
    mec_gain_m: float = 0.0

    @property
    def expected_time_s(self):
        return self.immediate_time_s + sum(
            probability * tail for probability, tail in self.outcomes
        )


@dataclass(frozen=True)
class OpticalClearChain:
    """Finite 20 m optical cover, with MEC centre attempted first."""

    points: tuple
    expected_time_s: float
    upper_time_s: float


def choose_plan(plans):
    """Choose by virtual time; station count is a deterministic tie-breaker."""
    return min(plans, key=lambda p: (p.total_time_s, p.station_count, p.name))


def choose_action(actions):
    """Minimize expected remaining time, then prefer larger information gain."""
    return min(actions, key=lambda a: (
        a.expected_time_s,
        -a.information_gain_bits,
        -a.mec_gain_m,
        a.kind,
    ))


def measure_immediate_time(current_position, q, current_channel, channel):
    return (math.dist(current_position, q) / 5.0
            + 5.0
            + (0.0 if current_channel == channel else 1.0))


def expected_information_gain(belief, q):
    prior_entropy = belief.entropy()
    probabilities = belief.outcome_probabilities(q)
    posterior_entropy = 0.0
    for outcome, probability in probabilities.items():
        if probability <= 0.0:
            continue
        posterior_entropy += probability * belief.after_outcome(q, outcome).entropy()
    return max(0.0, prior_entropy - posterior_entropy)


def optical_clear_chain(polygon, start, destination=None, clear_radius=20.0):
    """Cover the localization polygon by finitely many clear disks.

    The bounding box is partitioned into cells whose diagonal is at most
    ``2*clear_radius``.  A clear command at every cell centre therefore covers
    the whole box and hence the polygon.  The MEC centre is attempted first for
    expected speed; the residual cells are visited by an open route.
    """
    if not polygon:
        raise ValueError('cannot cover an empty localization region')
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    spacing = clear_radius * math.sqrt(2.0) * (1.0 - 1e-10)
    nx = max(1, int(math.ceil((xmax - xmin) / spacing)))
    ny = max(1, int(math.ceil((ymax - ymin) / spacing)))
    width = (xmax - xmin) / nx
    height = (ymax - ymin) / ny
    cells = [
        (xmin + (i + 0.5) * width, ymin + (j + 0.5) * height)
        for i in range(nx) for j in range(ny)
    ]
    center, _ = enclosing_circle(polygon)
    residual = {
        i: q for i, q in enumerate(cells)
        if math.dist(center, q) > 1e-8
    }
    order, residual_distance = optimal_open_route(center, residual)
    points = [tuple(center)] + [residual[i] for i in order]
    # In the worst case every command but the last is a 3 s miss; the last is
    # a 5 s success.  Destination travel is included when comparing route tails.
    travel = math.dist(start, center) + residual_distance
    if destination is not None:
        travel += math.dist(points[-1], destination)
    upper = travel / 5.0 + 3.0 * (len(points) - 1) + 5.0
    # Until a calibrated spatial posterior is available, use the certified
    # upper time as a conservative expectation rather than inventing a prior.
    return OpticalClearChain(tuple(points), upper, upper)
