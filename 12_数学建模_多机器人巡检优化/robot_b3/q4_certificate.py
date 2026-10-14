"""Per-channel deterministic discovery certificates for Q4.

For an unresolved channel, every triangle of the active mesh has diameter
strictly below the guaranteed 1000 m reception distance.  If a source lies in
one triangle, at least one of its vertices lies in every emitting half-plane
through the source.  Consequently, ``no_signal`` at every active vertex is a
deterministic absence certificate even when reception radius, source type and
direction are unknown.
"""

import math

from .full_view import (
    can_replace_certificate_station,
    replace_certificate_station,
)
from .routing import optimal_open_route


def _key(point):
    return round(float(point[0]), 8), round(float(point[1]), 8)


class PerChannelDiscoveryCertificate:
    """Maintain a different proven mesh and scan history for every channel."""

    def __init__(self, layout, channels=range(1, 21)):
        self.layouts = {int(c): layout for c in channels}
        self.scanned = {int(c): set() for c in channels}
        self.replacements = {int(c): 0 for c in channels}

    def record_no_signal(self, channel, point):
        if channel in self.scanned:
            self.scanned[channel].add(_key(point))

    def remaining(self, channel):
        layout = self.layouts[channel]
        observed = self.scanned[channel]
        return tuple(q for q in layout.stations if _key(q) not in observed)

    def complete(self, channel):
        return not self.remaining(channel)

    def requirements(self, channels):
        """Group equal physical stations while retaining channel obligations."""
        grouped = {}
        points = {}
        for channel in channels:
            for point in self.remaining(channel):
                point_key = _key(point)
                points.setdefault(point_key, tuple(point))
                grouped.setdefault(point_key, set()).add(channel)
        return {points[k]: grouped[k] for k in grouped}

    def replacement_options(self, channel, candidate):
        """Return unobserved vertices that ``candidate`` may safely replace."""
        layout = self.layouts[channel]
        return tuple(
            station for station in self.remaining(channel)
            if can_replace_certificate_station(layout, station, candidate)
        )

    def best_replacement(self, channel, candidate, start=None):
        """Choose the safe substitution with the shortest residual open tour."""
        candidate = tuple(candidate)
        start = candidate if start is None else tuple(start)
        layout = self.layouts[channel]
        best = None
        for station in self.replacement_options(channel, candidate):
            changed = replace_certificate_station(layout, station, candidate)
            remaining = [q for q in changed.stations
                         if _key(q) not in self.scanned[channel]
                         and _key(q) != _key(candidate)]
            named = {i: q for i, q in enumerate(remaining)}
            distance = 0.0 if not named else optimal_open_route(start, named)[1]
            score = (distance, math.dist(station, candidate), _key(station))
            if best is None or score < best[0]:
                best = (score, station, changed)
        return None if best is None else best[1]

    def apply_replacement(self, channel, station, candidate):
        """Apply a substitution only after ``candidate`` returned no signal."""
        candidate = tuple(candidate)
        if _key(candidate) not in self.scanned[channel]:
            raise ValueError('replacement point has no no_signal observation')
        layout = self.layouts[channel]
        if not can_replace_certificate_station(layout, station, candidate):
            raise ValueError('replacement does not preserve the certificate')
        self.layouts[channel] = replace_certificate_station(
            layout, station, candidate)
        self.replacements[channel] += 1

