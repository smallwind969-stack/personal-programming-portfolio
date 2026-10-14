"""Geometry for guaranteed active localization under an unknown reception radius.

After a positive observation at station S, a hypothetical source X implies
R(X) >= max(1000, |X-S|).  With several positive stations the lower bound is
the maximum over all of them.  A new station Q is therefore guaranteed to
receive iff no feasible X is both farther than 1000 m from Q and closer to
every previous positive station than to Q.
"""
import math


def _clip_ge(poly, value, tolerance=1e-9):
    """Clip a convex polygon to value(point) >= 0."""
    if not poly:
        return []
    out = []
    a = poly[-1]
    va = value(a)
    for b in poly:
        vb = value(b)
        ina, inb = va >= -tolerance, vb >= -tolerance
        if ina != inb:
            t = va / (va - vb)
            out.append((a[0] + t*(b[0]-a[0]), a[1] + t*(b[1]-a[1])))
        if inb:
            out.append(b)
        a, va = b, vb
    return out


def reception_residual_polygon(poly, q, positive_stations):
    """Return feasible sources for which Q is no closer than every old station."""
    residual = list(poly)
    qx, qy = q
    q2 = qx*qx + qy*qy
    for sx, sy in positive_stations:
        # |X-S|^2 <= |X-Q|^2
        rhs = q2 - sx*sx - sy*sy
        residual = _clip_ge(
            residual,
            lambda x, sx=sx, sy=sy, rhs=rhs:
                rhs - 2*x[0]*(qx-sx) - 2*x[1]*(qy-sy),
        )
        if not residual:
            break
    return residual


def guaranteed_reception(poly, q, positive_stations, base_radius=1000.0,
                         tolerance=1e-7):
    """Conservative exact certificate that a bearing will be returned at Q.

    The only deliberate conservatism is treating equidistance boundaries as
    belonging to the possible-violation polygon.  Reusing a known positive
    station is recognized exactly.
    """
    if not poly or not positive_stations:
        return False
    if any(math.dist(q, s) <= tolerance for s in positive_stations):
        return True
    residual = reception_residual_polygon(poly, q, positive_stations)
    return not residual or max(math.dist(q, x) for x in residual) <= base_radius+tolerance

