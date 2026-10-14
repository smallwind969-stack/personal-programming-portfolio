"""Finite optical-clear covers clipped to a localization polygon.

The proof is cell based.  The bounding box is partitioned into squares whose
diagonal is strictly smaller than the clear diameter.  Only cells intersecting
the feasible polygon are retained.  Every feasible point belongs to one
retained cell and is therefore within the clear radius of that cell's centre.
"""

from dataclasses import dataclass
import math

from .routing import optimal_open_route


@dataclass(frozen=True)
class PolygonDiskCover:
    points: tuple
    expected_time_s: float
    upper_time_s: float
    cell_width_m: float
    cell_height_m: float
    method: str = 'polygon_cell_certificate'


def _cross(a, b, c):
    return ((b[0] - a[0]) * (c[1] - a[1])
            - (b[1] - a[1]) * (c[0] - a[0]))


def _point_on_segment(p, a, b, eps=1e-9):
    return (abs(_cross(a, b, p)) <= eps
            and min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps
            and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps)


def _point_in_polygon(p, polygon):
    inside = False
    j = len(polygon) - 1
    for i, a in enumerate(polygon):
        b = polygon[j]
        if _point_on_segment(p, a, b):
            return True
        if ((a[1] > p[1]) != (b[1] > p[1])):
            x = (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]
            if p[0] < x:
                inside = not inside
        j = i
    return inside


def _segments_intersect(a, b, c, d, eps=1e-9):
    ab_c, ab_d = _cross(a, b, c), _cross(a, b, d)
    cd_a, cd_b = _cross(c, d, a), _cross(c, d, b)
    if ((ab_c > eps and ab_d < -eps) or (ab_c < -eps and ab_d > eps)) and \
       ((cd_a > eps and cd_b < -eps) or (cd_a < -eps and cd_b > eps)):
        return True
    return any((_point_on_segment(c, a, b, eps),
                _point_on_segment(d, a, b, eps),
                _point_on_segment(a, c, d, eps),
                _point_on_segment(b, c, d, eps)))


def _cell_intersects_polygon(bounds, polygon):
    x0, y0, x1, y1 = bounds
    corners = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    if any(_point_in_polygon(q, polygon) for q in corners):
        return True
    if any(x0 <= q[0] <= x1 and y0 <= q[1] <= y1 for q in polygon):
        return True
    cell_edges = tuple(zip(corners, corners[1:] + corners[:1]))
    polygon_edges = tuple(zip(polygon, polygon[1:] + polygon[:1]))
    return any(_segments_intersect(a, b, c, d)
               for a, b in cell_edges for c, d in polygon_edges)


def certified_polygon_disk_cover(polygon, start, destination=None,
                                 clear_radius=20.0):
    polygon = tuple((float(x), float(y)) for x, y in polygon)
    if len(polygon) < 3:
        raise ValueError('a localization polygon needs at least three vertices')
    if clear_radius <= 0:
        raise ValueError('clear_radius must be positive')

    xs, ys = [p[0] for p in polygon], [p[1] for p in polygon]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    max_side = clear_radius * math.sqrt(2.0) * (1.0 - 1e-10)
    nx = max(1, math.ceil((xmax - xmin) / max_side))
    ny = max(1, math.ceil((ymax - ymin) / max_side))
    width = (xmax - xmin) / nx if xmax > xmin else 0.0
    height = (ymax - ymin) / ny if ymax > ymin else 0.0

    cells = []
    for i in range(nx):
        x0 = xmin + i * width
        x1 = xmax if i + 1 == nx else xmin + (i + 1) * width
        for j in range(ny):
            y0 = ymin + j * height
            y1 = ymax if j + 1 == ny else ymin + (j + 1) * height
            if _cell_intersects_polygon((x0, y0, x1, y1), polygon):
                cells.append(((x0 + x1) / 2.0, (y0 + y1) / 2.0))

    named = {i: q for i, q in enumerate(cells)}
    order, route_m = optimal_open_route(tuple(start), named)
    points = tuple(named[i] for i in order)
    travel_m = route_m
    if destination is not None and points:
        travel_m += math.dist(points[-1], destination)
    upper = travel_m / 5.0 + 3.0 * max(0, len(points) - 1) + 5.0
    return PolygonDiskCover(points, upper, upper, width, height)
