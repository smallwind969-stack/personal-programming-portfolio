"""Certified zero-detour optical stops along each planned movement segment."""
import math

from .q4_certified21_strategy import Q4Certified21Strategy


def segment_clear_point(start, end, polygon, radius=19.8):
    """First feasible point on [start,end] in every vertex's radius disk.

    The polygon must contain the true source. Vertex containment then covers
    its convex hull. Empty or non-finite geometry is rejected, never cleared.
    """
    if not polygon or radius <= 0:
        return None
    if not all(math.isfinite(v) for p in (start, end, *polygon) for v in p):
        return None
    dx, dy = end[0]-start[0], end[1]-start[1]
    length2 = dx*dx+dy*dy
    if length2 <= 1e-20:
        return tuple(start) if all(math.dist(start, v) <= radius for v in polygon) else None
    lo, hi = 0., 1.
    for x, y in polygon:
        vx, vy = x-start[0], y-start[1]
        projection = (vx*dx+vy*dy)/length2
        normal2 = (vx*dy-vy*dx)**2/length2
        remainder = radius*radius-normal2
        if remainder < 0:
            return None
        half = math.sqrt(remainder/length2)
        lo, hi = max(lo, projection-half), min(hi, projection+half)
        if lo > hi:
            return None
    t = min(hi, lo+1e-10)
    point = (start[0]+t*dx, start[1]+t*dy)
    return point if all(math.dist(point, p) <= radius+1e-7 for p in polygon) else None


class Q4EnrouteStrategy(Q4Certified21Strategy):
    """Keep the 21-station search policy; service other known sources en route."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_enroute'
        self.enroute_clears = 0
        self._in_enroute_chain = False

    def _clear_along_segment(self, endpoint, excluded_channel):
        if self._in_enroute_chain:
            return
        self._in_enroute_chain = True
        try:
            while self._time_ok():
                options = []
                for c in sorted(self.found-self.cleared-{excluded_channel}):
                    q = segment_clear_point(self.position, endpoint, self.poly.get(c, ()))
                    if q is not None:
                        options.append((math.dist(self.position, q), c, q))
                if not options:
                    break
                _, c, q = min(options)
                if not super()._clear(q, c):
                    raise RuntimeError(f'certified en-route clear failed on channel {c}')
                self.enroute_clears += 1
                self._log('enroute_clear', channel=c, position=q,
                          route_endpoint=endpoint, added_distance_m=0.0)
                # Update and recompute all remaining intervals after each clear.
                # Clearing never changes the receiver channel or search duties.
        finally:
            self._in_enroute_chain = False

    def _measure(self, q, c):
        self._clear_along_segment(q, c)
        return super()._measure(q, c)

    def _clear(self, q, c):
        self._clear_along_segment(q, c)
        return super()._clear(q, c)

    def run(self):
        result = super().run()
        result['enroute_clears'] = self.enroute_clears
        return result
