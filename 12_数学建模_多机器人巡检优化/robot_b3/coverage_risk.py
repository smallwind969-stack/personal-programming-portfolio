"""Deterministic area-risk estimate for deliberately incomplete search covers."""
import math

from .coverage import farthest_uncovered


def uncovered_fraction(stations, radius=1000.0, angular_bins=360, radial_bins=100):
    stations = [tuple(q) for q in stations]
    if farthest_uncovered(stations)[1] <= radius + 1e-7:
        return 0.0
    missed = 0
    total = angular_bins * radial_bins
    for i in range(radial_bins):
        r = 1800.0 * math.sqrt((i + .5) / radial_bins)
        for j in range(angular_bins):
            angle = 2 * math.pi * (j + .5 * (i & 1)) / angular_bins
            q = (r * math.cos(angle), r * math.sin(angle))
            if min(math.dist(q, s) for s in stations) > radius:
                missed += 1
    return missed / total


def miss_risk(stations, unknown_channels, found_sources):
    """Conservative occupancy indicator under a uniform-location model."""
    possible = min(int(unknown_channels), max(0, 16 - int(found_sources)))
    if possible == 0:
        return 0.0
    fraction = uncovered_fraction(stations)
    return 1.0 - (1.0 - fraction) ** possible
