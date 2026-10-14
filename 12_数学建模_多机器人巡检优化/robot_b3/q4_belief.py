"""Probability and virtual-time primitives for the Q4 belief planner.

The probability layer ranks safe actions.  It never certifies that a channel is
absent; the strategy's deterministic full-view fallback retains that job.
"""
from dataclasses import dataclass
import math

from .geometry import point_polygon_distance


@dataclass(frozen=True)
class SourceParticle:
    x: float
    y: float
    radius: float
    direction: float | None
    weight: float

    def is_received(self, q):
        dx, dy = q[0]-self.x, q[1]-self.y
        if dx*dx+dy*dy > self.radius*self.radius+1e-9:
            return False
        if self.direction is None:
            return True
        return math.cos(self.direction)*dx+math.sin(self.direction)*dy >= -1e-9


class ChannelBelief:
    """Discrete posterior over absence, position, range and radiation type."""

    def __init__(self, particles, absent_weight):
        self.particles = list(particles)
        self.absent_weight = float(absent_weight)
        self._normalize()

    @classmethod
    def prior(cls, spatial_step=300.0, orientation_count=12,
              existence_probability=0.65):
        coordinates = []
        count = int(math.ceil(1800.0/spatial_step))
        for i in range(-count, count+1):
            for j in range(-count, count+1):
                q = (i*spatial_step, j*spatial_step)
                if math.hypot(*q) <= 1800.0+1e-9:
                    coordinates.append(q)
        hypotheses = []
        radii = (1000.0, 1250.0, 1500.0)
        # Equal prior mass for omni and directional source types.  The angular
        # grid integrates the unknown boresight without random sampling noise.
        for x, y in coordinates:
            for radius in radii:
                hypotheses.append((x, y, radius, None))
                for k in range(orientation_count):
                    hypotheses.append((x, y, radius,
                                       2*math.pi*k/orientation_count))
        directional_scale = 1.0/orientation_count
        raw = []
        for x, y, radius, direction in hypotheses:
            type_weight = 0.5 if direction is None else 0.5*directional_scale
            raw.append((x, y, radius, direction,
                        existence_probability*type_weight/(len(coordinates)*len(radii))))
        return cls((SourceParticle(*p) for p in raw), 1-existence_probability)

    def _normalize(self):
        total = self.absent_weight+sum(p.weight for p in self.particles)
        if total <= 0:
            self.absent_weight = 1.0
            self.particles = []
            return
        self.absent_weight /= total
        self.particles = [SourceParticle(p.x, p.y, p.radius, p.direction,
                                         p.weight/total)
                          for p in self.particles]

    def hit_probability(self, q):
        return sum(p.weight for p in self.particles if p.is_received(q))

    def observe_signal(self, q):
        """Condition on source existence and successful reception at ``q``."""
        retained = [p for p in self.particles if p.is_received(q)]
        if not retained:
            # A coarse particle grid can miss a very small feasible set.  Keep
            # the location hypotheses rather than incorrectly reviving absence.
            retained = list(self.particles)
        self.particles = retained
        self.absent_weight = 0.0
        self._normalize()

    def observe_direction(self, q):
        """Condition on reception outside the five-metre ``near`` disk."""
        retained = [
            p for p in self.particles
            if p.is_received(q) and math.dist((p.x, p.y), q) > 5.0 + 1e-9
        ]
        if not retained:
            # Preserve a coarse-grid representation of known existence while
            # still enforcing the deterministic fact implied by ``direction``.
            retained = [p for p in self.particles
                        if math.dist((p.x, p.y), q) > 5.0 + 1e-9]
        self.particles = retained
        self.absent_weight = 0.0
        self._normalize()

    def condition_polygon(self, polygon):
        """Condition particle locations on the deterministic bearing region."""
        retained = [p for p in self.particles
                    if point_polygon_distance((p.x, p.y), polygon) <= 1e-8]
        if retained:
            self.particles = retained
            self._normalize()
            return
        if not polygon or not self.particles:
            return

        # A narrow bearing intersection can fall entirely between the spatial
        # prior grid points.  Keeping the old cloud would contradict the safe
        # polygon, so rebuild deterministic support inside it while preserving
        # the current range/type/orientation marginal.
        vertices = list(polygon)
        stride = max(1, int(math.ceil(len(vertices) / 12.0)))
        sampled = vertices[::stride]
        centroid = (
            sum(p[0] for p in vertices) / len(vertices),
            sum(p[1] for p in vertices) / len(vertices),
        )
        support = [centroid]
        support.extend(sampled)
        support.extend((
            (sampled[i][0] + sampled[(i + 1) % len(sampled)][0]) / 2.0,
            (sampled[i][1] + sampled[(i + 1) % len(sampled)][1]) / 2.0,
        ) for i in range(len(sampled)))
        unique_support = []
        seen = set()
        for q in support:
            key = round(q[0], 9), round(q[1], 9)
            if key not in seen and point_polygon_distance(q, polygon) <= 1e-8:
                seen.add(key)
                unique_support.append(q)

        parameter_mass = {}
        for particle in self.particles:
            key = particle.radius, particle.direction
            parameter_mass[key] = parameter_mass.get(key, 0.0) + particle.weight
        count = len(unique_support)
        self.particles = [
            SourceParticle(q[0], q[1], radius, direction, mass / count)
            for q in unique_support
            for (radius, direction), mass in parameter_mass.items()
        ]
        self._normalize()

    def observe_clear_miss(self, q, radius=20.0):
        """Condition a known source on an unsuccessful optical clear."""
        retained = [p for p in self.particles
                    if math.dist((p.x, p.y), q) > radius + 1e-9]
        if retained:
            self.particles = retained
            self._normalize()

    def observe_no_signal(self, q):
        self.particles = [p for p in self.particles if not p.is_received(q)]
        self._normalize()

    def after_no_signal(self, q):
        child = ChannelBelief(self.particles, self.absent_weight)
        child.observe_no_signal(q)
        return child


def opportunity_value_seconds(hit_probability, remaining_sweeps,
                              switch_required, future_sweep_cost=6.0):
    """Expected seconds saved by an extra zero-detour measurement now."""
    immediate = 5.0+(1.0 if switch_required else 0.0)
    saved = max(0, remaining_sweeps)*future_sweep_cost
    return float(hit_probability)*saved-immediate
