"""Continuous full-view coverage certificates using millimetre integers.

For a closed 180-degree emission half-plane, every orientation is discoverable
iff x belongs to the convex hull of stations within reception range of x.
Whole boxes, not sampled source positions, are certified below.
"""
from dataclasses import dataclass
from functools import lru_cache
import math

from .full_view import FullViewLayout

SCALE = 1000
ARENA_RADIUS_MM = 1800000
RECEPTION_RADIUS_MM = 999980
# Offline MILP open-path solution for exactly the rounded coordinates below.
# This is not a proof of minimum station count or optimized node coordinates.
OPEN_ROUTE = (0, 6, 7, 8, 1, 2, 3, 4, 5, 15, 14, 13, 12, 11,
              10, 9, 20, 19, 18, 17, 16)


@dataclass(frozen=True)
class CoverageVerification:
    certified: bool
    accepted_boxes: int
    outside_boxes: int
    max_depth: int
    failed_box: object = None


def certified21_stations():
    """Origin + 995 m octagon + 1864 m dodecagon, rounded to millimetres."""
    points = [(0.0, 0.0)]
    for count, radius in ((8, 995.0), (12, 1864.0)):
        points.extend((round(radius * math.cos(2 * math.pi * i / count), 3),
                       round(radius * math.sin(2 * math.pi * i / count), 3))
                      for i in range(count))
    return tuple(points)


def _cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        return tuple(points)
    lower, upper = [], []
    for chain, sequence in ((lower, points), (upper, reversed(points))):
        for point in sequence:
            while len(chain) >= 2 and _cross(chain[-2], chain[-1], point) <= 0:
                chain.pop()
            chain.append(point)
    return tuple(lower[:-1] + upper[:-1])


def _box_covered(box, points, radius2):
    x0, x1, y0, y1 = box
    nearby = [p for p in points
              if max((p[0]-x0)**2, (p[0]-x1)**2)
              + max((p[1]-y0)**2, (p[1]-y1)**2) <= radius2]
    hull = _hull(nearby)
    if len(hull) < 3:
        return False
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    return all(_cross(hull[i], hull[(i+1) % len(hull)], q) >= 0
               for i in range(len(hull)) for q in corners)


@lru_cache(maxsize=128)
def _verify(points, arena_radius_mm, reception_radius_mm, max_depth, max_boxes):
    radius2 = reception_radius_mm**2
    root = (-arena_radius_mm, arena_radius_mm,
            -arena_radius_mm, arena_radius_mm)
    stack = [(root, 0)]
    accepted = outside = deepest = visited = 0
    while stack:
        box, depth = stack.pop()
        visited += 1
        deepest = max(deepest, depth)
        x0, x1, y0, y1 = box
        dx = max(x0, 0, -x1)
        dy = max(y0, 0, -y1)
        if dx*dx + dy*dy > arena_radius_mm**2:
            outside += 1
            continue
        if visited > max_boxes:
            return CoverageVerification(False, accepted, outside, deepest, box)
        if _box_covered(box, points, radius2):
            accepted += 1
            continue
        if depth >= max_depth or x1-x0 <= 1 or y1-y0 <= 1:
            return CoverageVerification(False, accepted, outside, deepest, box)
        xm, ym = (x0+x1)//2, (y0+y1)//2
        stack.extend(((child, depth+1) for child in (
            (x0, xm, y0, ym), (xm, x1, y0, ym),
            (x0, xm, ym, y1), (xm, x1, ym, y1))))
    return CoverageVerification(True, accepted, outside, deepest)


def verify_local_hull_coverage(stations, arena_radius_mm=ARENA_RADIUS_MM,
                               reception_radius_mm=RECEPTION_RADIUS_MM,
                               max_depth=20, max_boxes=100000):
    """Fail closed if the finite proof does not succeed within its limits.

Each accepted rectangle lies in conv(A), and every station in A is within r
of all four corners. Convexity extends both statements to the whole rectangle.
Uncertified does NOT mean the station set is mathematically infeasible.
"""
    points = []
    for station in stations:
        if len(station) != 2:
            raise ValueError('stations must be two-dimensional')
        pair = []
        for coordinate in station:
            if not math.isfinite(coordinate):
                raise ValueError('station coordinates must be finite')
            integer = round(coordinate * SCALE)
            if abs(coordinate * SCALE - integer) > 1e-6:
                raise ValueError('station coordinates must be rounded to millimetres')
            pair.append(integer)
        points.append(tuple(pair))
    parameters = (arena_radius_mm, reception_radius_mm, max_depth, max_boxes)
    if any(not isinstance(value, int) for value in parameters):
        raise ValueError('certificate limits and radii must be integers')
    if arena_radius_mm <= 0 or reception_radius_mm <= 0 or max_depth < 0 or max_boxes <= 0:
        raise ValueError('invalid certificate limits or radii')
    return _verify(tuple(sorted(set(points))), *parameters)


def build_certified21_layout():
    points = certified21_stations()
    verification = verify_local_hull_coverage(points)
    if not verification.certified:
        raise RuntimeError('21-station continuous coverage certificate failed')
    stations = tuple(points[i] for i in OPEN_ROUTE)
    distance = sum(math.dist(a, b) for a, b in zip(stations, stations[1:]))
    return FullViewLayout(stations, (), 0.0, (995.0, 1864.0), 0.0, distance)
