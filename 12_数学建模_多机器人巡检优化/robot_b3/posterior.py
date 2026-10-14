"""Scenario cloud for bounded bearing errors and unknown common reception radius."""
import itertools
import math


def _angle_delta(a,b):return (a-b+180)%360-180


def compatible_reception(point,positive_stations,negative_stations):
    positives=[math.dist(point,s) for s in positive_stations]
    negatives=[math.dist(point,s) for s in negative_stations]
    if any(d>1500+1e-7 for d in positives) or any(d<=1000+1e-7 for d in negatives):return False
    lower=max([1000.0]+positives)
    upper=min([1500.0]+negatives)
    return lower<upper+1e-7


def _intersection(s1,a1,s2,a2):
    u=(math.cos(math.radians(a1)),math.sin(math.radians(a1)))
    v=(math.cos(math.radians(a2)),math.sin(math.radians(a2)))
    det=u[0]*v[1]-u[1]*v[0]
    if abs(det)<1e-7:return None
    dx,dy=s2[0]-s1[0],s2[1]-s1[1]
    t=(dx*v[1]-dy*v[0])/det
    w=(dx*u[1]-dy*u[0])/det
    if t<0 or w<0:return None
    return s1[0]+t*u[0],s1[1]+t*u[1]


def posterior_cloud(observations,negative_stations,failed_clear_centers,steps=15):
    """Sample the exact bounded-error feasible set via pairwise ray intersections."""
    observations=list(observations);positive=[s for s,_ in observations]
    errors=[-1+2*i/(steps-1) for i in range(steps)]
    cloud=[];seen=set()
    for (s1,a1),(s2,a2) in itertools.combinations(observations[-5:],2):
        for e1 in errors:
            for e2 in errors:
                q=_intersection(s1,a1-e1,s2,a2-e2)
                if q is None or math.hypot(*q)>1800+1e-7:continue
                if any(abs(_angle_delta(math.degrees(math.atan2(q[1]-s[1],q[0]-s[0])),a))>1.0001
                       for s,a in observations):continue
                if not compatible_reception(q,positive,negative_stations):continue
                if any(math.dist(q,f)<=20 for f in failed_clear_centers):continue
                key=(round(q[0],3),round(q[1],3))
                if key not in seen:seen.add(key);cloud.append(q)
    return cloud


def best_clear_disk(cloud,radius=20.0):
    if not cloud:return None,0.0
    best=max(cloud,key=lambda q:sum(math.dist(q,p)<=radius for p in cloud))
    probability=sum(math.dist(best,p)<=radius for p in cloud)/len(cloud)
    return best,probability
