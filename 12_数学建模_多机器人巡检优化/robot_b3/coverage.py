"""Exact candidate enumeration for covering a circular arena by equal disks."""
import itertools
import math


def _circumcenter(a,b,c):
    ax,ay=a;bx,by=b;cx,cy=c
    d=2*(ax*(by-cy)+bx*(cy-ay)+cx*(ay-by))
    if abs(d)<1e-9:return None
    ux=((ax*ax+ay*ay)*(by-cy)+(bx*bx+by*by)*(cy-ay)+(cx*cx+cy*cy)*(ay-by))/d
    uy=((ax*ax+ay*ay)*(cx-bx)+(bx*bx+by*by)*(ax-cx)+(cx*cx+cy*cy)*(bx-ax))/d
    return ux,uy


def farthest_uncovered(stations,arena_radius=1800.0):
    """Return a farthest arena point and its distance to the nearest station.

    Maxima occur at an arena-boundary Voronoi breakpoint/extremum or an
    interior Voronoi vertex, all of which are enumerated below.
    """
    stations=list(stations)
    if not stations:return (arena_radius,0.0),math.inf
    candidates=[(0.0,0.0)]
    for x,y in stations:
        a=math.atan2(y,x)+math.pi
        candidates.append((arena_radius*math.cos(a),arena_radius*math.sin(a)))
    for a,b in itertools.combinations(stations,2):
        vx,vy=b[0]-a[0],b[1]-a[1]
        norm=math.hypot(vx,vy)
        if norm<1e-9:continue
        rhs=(b[0]*b[0]+b[1]*b[1]-a[0]*a[0]-a[1]*a[1])/(2*arena_radius*norm)
        if abs(rhs)<=1+1e-12:
            phi=math.atan2(vy,vx);delta=math.acos(max(-1,min(1,rhs)))
            for angle in (phi+delta,phi-delta):
                candidates.append((arena_radius*math.cos(angle),arena_radius*math.sin(angle)))
    for a,b,c in itertools.combinations(stations,3):
        q=_circumcenter(a,b,c)
        if q is not None and math.hypot(*q)<=arena_radius+1e-7:
            candidates.append(q)
    return max(candidates,key=lambda q:min(math.dist(q,s) for s in stations)),max(
        min(math.dist(q,s) for s in stations) for q in candidates)
