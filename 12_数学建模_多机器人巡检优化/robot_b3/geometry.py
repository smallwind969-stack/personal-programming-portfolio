import math
import random


def seven_points(rho=1140.0):
    return [(0.0, 0.0)] + [
        (rho * math.cos(k * math.pi / 3), rho * math.sin(k * math.pi / 3))
        for k in range(6)
    ]


def arena_polygon(radius=1800.0, sides=360):
    # Circumscribed, so no possible target on a circular boundary is discarded.
    radius = radius / math.cos(math.pi / sides)
    return [
        (radius * math.cos(2 * math.pi * i / sides), radius * math.sin(2 * math.pi * i / sides))
        for i in range(sides)
    ]


def _clip(poly, signed_value, tolerance=1e-9):
    if not poly:
        return []
    output = []
    a = poly[-1]
    va = signed_value(a)
    for b in poly:
        vb = signed_value(b)
        ina, inb = va >= -tolerance, vb >= -tolerance
        if ina != inb:
            t = va / (va - vb)
            output.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        if inb:
            output.append(b)
        a, va = b, vb
    return output


def bearing_clip(poly, station, bearing_deg, error_deg=1.0):
    low = math.radians(bearing_deg - error_deg)
    high = math.radians(bearing_deg + error_deg)
    ul = (math.cos(low), math.sin(low))
    uh = (math.cos(high), math.sin(high))
    sx, sy = station
    left = lambda p: ul[0] * (p[1] - sy) - ul[1] * (p[0] - sx)
    right = lambda p: -(uh[0] * (p[1] - sy) - uh[1] * (p[0] - sx))
    return _clip(_clip(poly, left), right)


def diameter(poly):
    return max((math.dist(a, b) for i, a in enumerate(poly) for b in poly[i + 1:]), default=0.0)


def point_polygon_distance(point, poly):
    """Euclidean distance from a point to a closed convex polygon."""
    if not poly:
        return math.inf
    signs = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        cross = ((b[0] - a[0]) * (point[1] - a[1])
                 - (b[1] - a[1]) * (point[0] - a[0]))
        if abs(cross) > 1e-9:
            signs.append(cross > 0)
    if not signs or all(sign == signs[0] for sign in signs):
        return 0.0

    best = math.inf
    for i, a in enumerate(poly):
        b = poly[(i + 1) % len(poly)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dy * dy
        if length2 <= 1e-20:
            best = min(best, math.dist(point, a))
            continue
        t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2
        t = max(0.0, min(1.0, t))
        projection = (a[0] + t * dx, a[1] + t * dy)
        best = min(best, math.dist(point, projection))
    return best


def enclosing_circle(points):
    pts = list(points)
    if not pts:
        return (0.0, 0.0), math.inf
    random.Random(2026).shuffle(pts)

    def contains(c, p):
        return c is not None and math.dist(c[0], p) <= c[1] + 1e-7

    def pair(a, b):
        center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        return center, math.dist(a, b) / 2

    def triple(a, b, c):
        ax, ay = a; bx, by = b; cx, cy = c
        den = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(den) < 1e-10:
            return None
        ux = ((ax*ax+ay*ay)*(by-cy)+(bx*bx+by*by)*(cy-ay)+(cx*cx+cy*cy)*(ay-by))/den
        uy = ((ax*ax+ay*ay)*(cx-bx)+(bx*bx+by*by)*(ax-cx)+(cx*cx+cy*cy)*(bx-ax))/den
        center = (ux, uy)
        return center, math.dist(center, a)

    circle = None
    for i, p in enumerate(pts):
        if contains(circle, p):
            continue
        circle = (p, 0.0)
        for j, q in enumerate(pts[:i]):
            if contains(circle, q):
                continue
            circle = pair(p, q)
            for r in pts[:j]:
                if contains(circle, r):
                    continue
                candidate = triple(p, q, r)
                if candidate is not None:
                    circle = candidate
    return circle


def reception_clip(poly, station, radius=1500.0, sides=48):
    """Outer approximation of a reception disk using tangent half-planes."""
    for i in range(sides):
        a = 2*math.pi*i/sides
        nx, ny = math.cos(a), math.sin(a)
        poly = _clip(poly, lambda p: radius-nx*(p[0]-station[0])-ny*(p[1]-station[1]))
    return poly


def clear_visit_point(poly, start, destination=None, radius=19.9):
    """Feasible low-detour point in intersection of radius-19.9 disks at vertices.

    Containing every vertex guarantees containing the whole convex region.
    The center is always a candidate; sampled boundary points can only improve it.
    """
    center, r = enclosing_circle(poly)
    if r > radius or not poly:
        raise ValueError('region does not yet admit a guaranteed clear point')
    feasible = lambda q: all(math.dist(q, p) <= radius+1e-8 for p in poly)
    if feasible(start):
        return start
    if destination is not None and math.dist(start, destination) > 1e-9:
        # Exact intersection of each vertex disk with the next route segment.
        dx, dy = destination[0]-start[0], destination[1]-start[1]
        aa = dx*dx+dy*dy
        lo, hi = 0.0, 1.0
        for p in poly:
            vx, vy = start[0]-p[0], start[1]-p[1]
            bb = vx*dx+vy*dy
            disc = bb*bb-aa*(vx*vx+vy*vy-radius*radius)
            if disc < 0:
                hi = -1
                break
            sd = math.sqrt(max(0, disc))
            lo, hi = max(lo, (-bb-sd)/aa), min(hi, (-bb+sd)/aa)
        if lo <= hi:
            t = min(hi, lo+1e-10)
            q = (start[0]+t*dx, start[1]+t*dy)
            if feasible(q):
                return q
    candidates = [center]
    angles = [2*math.pi*i/64 for i in range(64)]
    angles.append(math.atan2(start[1]-center[1], start[0]-center[0]))
    for a in angles:
        ux, uy = math.cos(a), math.sin(a)
        step = math.inf
        for p in poly:
            vx, vy = center[0]-p[0], center[1]-p[1]
            dot = vx*ux+vy*uy
            root = dot*dot+radius*radius-vx*vx-vy*vy
            step = min(step, -dot+math.sqrt(max(0, root)))
        q = (center[0]+max(0, step-1e-7)*ux, center[1]+max(0, step-1e-7)*uy)
        if feasible(q):
            candidates.append(q)
    return min(candidates, key=lambda q: math.dist(start, q)+
               (math.dist(q, destination) if destination is not None else 0))


def bearing_least_squares(observations):
    """Least-squares intersection of bearing centerlines and geometry quality [0,1]."""
    aa=ab=bb=ra=rb=0.0
    for (sx,sy),degrees in observations:
        a=math.radians(degrees);nx,ny=-math.sin(a),math.cos(a)
        value=nx*sx+ny*sy
        aa+=nx*nx;ab+=nx*ny;bb+=ny*ny;ra+=nx*value;rb+=ny*value
    det=aa*bb-ab*ab;trace=aa+bb
    if trace<1e-12 or det<1e-14:return None,0.0
    point=((ra*bb-rb*ab)/det,(rb*aa-ra*ab)/det)
    return point,max(0.0,min(1.0,4*det/(trace*trace)))
