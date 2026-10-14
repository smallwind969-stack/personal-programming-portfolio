"""Probability state for the omnidirectional sources in Problem B, Question 3.

The belief ranks actions only.  Certified channel absence and guaranteed clear
remain properties of the deterministic residual region and bearing polygon.
"""
from dataclasses import dataclass
import math

from .geometry import point_polygon_distance


@dataclass(frozen=True)
class OmniParticle:
    x: float
    y: float
    radius: float
    weight: float

    def distance(self, q):
        return math.dist((self.x, self.y), q)

    def receives(self, q):
        return self.distance(q) <= self.radius + 1e-9


class Q3ChannelBelief:
    """Discrete posterior over absence, source position and reception radius."""

    def __init__(self, particles, absent_weight=0.0):
        self.particles = list(particles)
        self.absent_weight = float(absent_weight)
        self._normalize()

    @classmethod
    def prior(cls, spatial_step=450.0, existence_probability=0.65):
        coordinates = []
        extent = int(math.ceil(1800.0 / spatial_step))
        for i in range(-extent, extent + 1):
            for j in range(-extent, extent + 1):
                q = (i * spatial_step, j * spatial_step)
                if math.hypot(*q) <= 1800.0 + 1e-9:
                    coordinates.append(q)
        radii = (1000.0, 1250.0, 1500.0)
        weight = existence_probability / (len(coordinates) * len(radii))
        particles = [
            OmniParticle(x, y, radius, weight)
            for x, y in coordinates
            for radius in radii
        ]
        return cls(particles, 1.0 - existence_probability)

    def clone(self):
        return Q3ChannelBelief(self.particles, self.absent_weight)

    def _normalize(self):
        total = self.absent_weight + sum(p.weight for p in self.particles)
        if total <= 0.0:
            self.particles = []
            self.absent_weight = 1.0
            return
        self.absent_weight /= total
        self.particles = [
            OmniParticle(p.x, p.y, p.radius, p.weight / total)
            for p in self.particles
        ]

    def entropy(self):
        weights = [p.weight for p in self.particles]
        if self.absent_weight > 0.0:
            weights.append(self.absent_weight)
        return -sum(w * math.log2(w) for w in weights if w > 0.0)

    def outcome_probabilities(self, q):
        near = sum(p.weight for p in self.particles
                   if p.receives(q) and p.distance(q) <= 5.0 + 1e-9)
        direction = sum(p.weight for p in self.particles
                        if p.receives(q) and p.distance(q) > 5.0 + 1e-9)
        no_signal = max(0.0, 1.0 - near - direction)
        return {'near': near, 'direction': direction, 'no_signal': no_signal}

    def hit_probability(self, q):
        probabilities = self.outcome_probabilities(q)
        return probabilities['near'] + probabilities['direction']

    def observe_no_signal(self, q):
        self.particles = [p for p in self.particles if not p.receives(q)]
        self._normalize()

    def observe_direction(self, q):
        retained = [p for p in self.particles
                    if p.receives(q) and p.distance(q) > 5.0 + 1e-9]
        if retained:
            self.particles = retained
        self.absent_weight = 0.0
        self._normalize()

    def observe_near(self, q):
        retained = [p for p in self.particles
                    if p.receives(q) and p.distance(q) <= 5.0 + 1e-9]
        if retained:
            self.particles = retained
        self.absent_weight = 0.0
        self._normalize()

    def observe_clear_miss(self, q, clear_radius=20.0):
        retained = [p for p in self.particles
                    if p.distance(q) > clear_radius + 1e-9]
        if retained:
            self.particles = retained
            self._normalize()

    def condition_polygon(self, polygon):
        retained = [p for p in self.particles
                    if point_polygon_distance((p.x, p.y), polygon) <= 1e-8]
        if retained:
            self.particles = retained
            self._normalize()

    def after_outcome(self, q, outcome):
        child = self.clone()
        if outcome == 'near':
            child.observe_near(q)
        elif outcome == 'direction':
            child.observe_direction(q)
        elif outcome == 'no_signal':
            child.observe_no_signal(q)
        else:
            raise ValueError(f'unknown measurement outcome: {outcome}')
        return child
