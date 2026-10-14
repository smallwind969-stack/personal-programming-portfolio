"""Analytic full-view coverage geometry for mixed directional sources."""
from dataclasses import dataclass
import math

from .routing import optimal_open_route


@dataclass(frozen=True)
class FullViewLayout:
    stations: tuple
    triangles: tuple
    side: float
    phase: tuple
    angle_rad: float
    route_distance_m: float


def order_anytime_stations(stations, start=(0.0, 0.0), side=990.0,
                           anchor_count=8):
    """Keep the strict station set but give its early prefix broad diversity."""
    remaining = list(stations)
    if not remaining:
        return ()
    current = tuple(start)
    selected = []
    first = min(remaining, key=lambda q: math.dist(current, q))
    selected.append(first)
    remaining.remove(first)
    current = first

    while remaining and len(selected) < min(anchor_count, len(stations)):
        selected_angles = [math.atan2(q[1], q[0]) for q in selected
                           if math.hypot(*q) > 1e-9]

        def circular_gap(q):
            if not selected_angles or math.hypot(*q) <= 1e-9:
                return math.pi
            angle = math.atan2(q[1], q[0])
            return min(abs((angle-a+math.pi) % (2*math.pi)-math.pi)
                       for a in selected_angles)

        def value(q):
            spatial = min(math.dist(q, p) for p in selected)/side
            angular = circular_gap(q)/math.pi
            radial = min(2.5, math.hypot(*q)/side)
            travel = math.dist(current, q)/side
            return (1.25*min(1.8, spatial)+0.85*angular
                    +0.15*radial-0.60*travel)

        chosen = max(remaining,
                     key=lambda q: (value(q), -math.dist(current, q)))
        selected.append(chosen)
        remaining.remove(chosen)
        current = chosen

    if remaining:
        named = {i: q for i, q in enumerate(remaining)}
        order, _ = optimal_open_route(current, named)
        selected.extend(named[i] for i in order)
    return tuple(selected)


def _cross(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


def _point_in_triangle(p, triangle, tolerance=1e-7):
    a, b, c = triangle
    values = (_cross(a, b, p), _cross(b, c, p), _cross(c, a, p))
    return min(values) >= -tolerance or max(values) <= tolerance


def _segment_distance_to_origin(a, b):
    dx, dy = b[0]-a[0], b[1]-a[1]
    length2 = dx*dx+dy*dy
    if length2 <= 1e-20:
        return math.hypot(*a)
    t = max(0.0, min(1.0, -(a[0]*dx+a[1]*dy)/length2))
    return math.hypot(a[0]+t*dx, a[1]+t*dy)


def _triangle_intersects_disk(triangle, radius):
    if any(math.hypot(*p) <= radius+1e-8 for p in triangle):
        return True
    if _point_in_triangle((0.0, 0.0), triangle):
        return True
    return any(_segment_distance_to_origin(triangle[i], triangle[(i+1) % 3])
               <= radius+1e-8 for i in range(3))


def _transform(q, shift, angle):
    x, y = q[0]+shift[0], q[1]+shift[1]
    c, s = math.cos(angle), math.sin(angle)
    return c*x-s*y, s*x+c*y


def _layout_for_phase(start, side, arena_radius, phase, angle):
    height = side*math.sqrt(3)/2
    shift = (phase[0]*side+phase[1]*side/2, phase[1]*height)
    bound = int(math.ceil((arena_radius+2*side)/height))+3

    def vertex(i, j):
        return _transform((side*(i+j/2), height*j), shift, angle)

    triangles = []
    station_map = {}
    for i in range(-bound, bound+1):
        for j in range(-bound, bound+1):
            a, b, c, d = vertex(i, j), vertex(i+1, j), vertex(i, j+1), vertex(i+1, j+1)
            for triangle in ((a, b, c), (d, c, b)):
                if not _triangle_intersects_disk(triangle, arena_radius):
                    continue
                triangles.append(triangle)
                for q in triangle:
                    station_map[(round(q[0], 8), round(q[1], 8))] = q
    named = {i: q for i, q in enumerate(station_map.values())}
    order, distance = optimal_open_route(start, named)
    stations = tuple(named[i] for i in order)
    return FullViewLayout(stations, tuple(triangles), side, phase, angle, distance)


def build_full_view_layout(start=(0.0, 0.0), side=990.0, arena_radius=1800.0):
    """Return the best deterministic finite patch of a triangular lattice.

    Every triangle meeting the arena contributes all three vertices.  Hence every
    arena point is in the convex hull of three stations no farther than ``side``.
    """
    if not 0 < side < 1000.0:
        raise ValueError('full-view lattice side must be strictly between 0 and 1000 m')
    phases = tuple((u, v) for u in (0.0, .25, .5, .75)
                   for v in (0.0, .25, .5, .75))
    layouts = [_layout_for_phase(tuple(start), side, arena_radius, phase, 0.0)
               for phase in phases]
    return min(layouts, key=lambda x: (len(x.stations), x.route_distance_m))


def build_competition_full_view_layout(start=(0.0, 0.0), arena_radius=1800.0):
    """Shorter strict lattice patch found by an offline phase/scale search.

    The 995 m edges retain a 5 m margin above the guaranteed 1000 m reception
    lower bound while the phase removes two unnecessary outer vertices.
    """
    return _layout_for_phase(tuple(start), 995.0, arena_radius, (7/9, 1/9), 0.0)


def build_route_first_full_view_layout(start=(0.0, 0.0), arena_radius=1800.0):
    """Return a boundary-fitted strict certificate with a short open route.

    The outer regular 16-gon has inradius ``arena_radius + 1``.  A 990 m
    inner octagon and the origin split its interior into 32 triangles.  The
    explicit construction keeps every certificate edge strictly below the
    guaranteed 1000 m reception radius.
    """
    if arena_radius <= 0:
        raise ValueError('arena_radius must be positive')
    inner_radius = 990.0
    outer_radius = (arena_radius + 1.0) / math.cos(math.pi / 16.0)
    center = (0.0, 0.0)
    inner = tuple(
        (inner_radius * math.cos(2.0 * math.pi * i / 8.0),
         inner_radius * math.sin(2.0 * math.pi * i / 8.0))
        for i in range(8)
    )
    outer = tuple(
        (outer_radius * math.cos(2.0 * math.pi * j / 16.0),
         outer_radius * math.sin(2.0 * math.pi * j / 16.0))
        for j in range(16)
    )

    triangles = []
    for i in range(8):
        ni = (i + 1) % 8
        j = 2 * i
        triangles.append((center, inner[i], inner[ni]))
        triangles.extend((
            (inner[i], outer[j], outer[(j + 1) % 16]),
            (inner[i], outer[(j + 1) % 16], inner[ni]),
            (inner[ni], outer[(j + 1) % 16], outer[(j + 2) % 16]),
        ))

    points = (center,) + inner + outer
    named = {i: q for i, q in enumerate(points)}
    order, distance = optimal_open_route(tuple(start), named)
    stations = tuple(named[i] for i in order)
    return FullViewLayout(
        stations, tuple(triangles), 0.0,
        (inner_radius, outer_radius), 0.0, distance,
    )


def _point_key(point):
    return round(point[0], 8), round(point[1], 8)


def can_replace_certificate_station(layout, station, candidate,
                                    max_edge=1000.0, tolerance=1e-7):
    """Prove that a boundary vertex may be replaced without losing coverage.

    This deliberately uses a sufficient, not necessary, test.  Every old
    incident triangle must be contained in the corresponding new triangle,
    and every new edge must remain shorter than ``max_edge``.
    """
    station_key = _point_key(station)
    incident = [triangle for triangle in layout.triangles
                if station_key in {_point_key(q) for q in triangle}]
    if not incident:
        return False

    edge_counts = {}
    for triangle in layout.triangles:
        for i in range(3):
            edge = tuple(sorted((_point_key(triangle[i]),
                                 _point_key(triangle[(i + 1) % 3]))))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    is_boundary = any(
        station_key in edge and count == 1
        for edge, count in edge_counts.items()
    )
    if not is_boundary:
        return False

    for triangle in incident:
        others = [q for q in triangle if _point_key(q) != station_key]
        if len(others) != 2:
            return False
        replacement = (tuple(candidate), others[0], others[1])
        if not _point_in_triangle(tuple(station), replacement, tolerance):
            return False
        if any(math.dist(replacement[i], replacement[(i + 1) % 3])
               >= max_edge - tolerance for i in range(3)):
            return False
    return True


def replace_certificate_station(layout, station, candidate):
    """Return the certificate state after one already-proven replacement."""
    if not can_replace_certificate_station(layout, station, candidate):
        raise ValueError('certificate station replacement is not proven safe')
    station_key = _point_key(station)
    candidate = tuple(candidate)
    stations = tuple(
        candidate if _point_key(q) == station_key else q
        for q in layout.stations
    )
    triangles = tuple(
        tuple(candidate if _point_key(q) == station_key else q for q in triangle)
        for triangle in layout.triangles
    )
    return FullViewLayout(
        stations, triangles, layout.side, layout.phase,
        layout.angle_rad, layout.route_distance_m,
    )


def certifying_triangle(layout, point):
    """Return an arena-intersecting lattice triangle containing ``point``."""
    for triangle in layout.triangles:
        if _point_in_triangle(tuple(point), triangle):
            return triangle
    return None


def receiver_side_probe_pairs(source_estimate, positive_station):
    """Two increasingly wide paired probes on the known receiver side."""
    gx, gy = source_estimate
    sx, sy = positive_station
    dx, dy = sx-gx, sy-gy
    distance = math.hypot(dx, dy)
    if distance <= 1e-9:
        return ()
    ex, ey = dx/distance, dy/distance
    nx, ny = -ey, ex
    pairs = []
    for alpha, beta in ((.70, .25), (.55, .40)):
        base = (gx+alpha*dx, gy+alpha*dy)
        offset = beta*distance
        pairs.append(((base[0]+offset*nx, base[1]+offset*ny),
                      (base[0]-offset*nx, base[1]-offset*ny)))
    return tuple(pairs)
