"""Deterministic online completion of a 1000 m disk cover for the 1800 m arena."""
import itertools
import math
import random

from .coverage import farthest_uncovered


def _score(existing,free):return farthest_uncovered(existing+free)[1]


def _ring_start(existing,k):
    best=None
    for phase_index in range(36):
        phase=phase_index*math.pi/108
        ring=[(1123*math.cos(phase+i*math.pi/3),1123*math.sin(phase+i*math.pi/3)) for i in range(6)]
        if k<6:
            # Retain the subset that best complements already accepted stations.
            for chosen in itertools.combinations(ring,k):
                value=_score(existing,list(chosen))
                if best is None or value<best[0]:best=(value,list(chosen))
        else:
            value=_score(existing,ring)
            if best is None or value<best[0]:best=(value,ring)
    return best


def complete_coverage(existing,k,budget_s=.2,threshold=1000.0):
    """Find k further centers and certify the resulting coverage, else return None."""
    existing=[tuple(q) for q in existing]
    if k<0:return None
    if k==0:return [] if _score(existing,[])<=threshold+1e-7 else None
    start=_ring_start(existing,k)
    if start is None:return None
    best_value,best=start[0],[tuple(q) for q in start[1]]
    # Time budget maps to a fixed iteration count, keeping runs reproducible.
    iterations=max(100,min(5000,int(2500*max(.04,budget_s))))
    rng=random.Random(202613002010+97*k+31*len(existing))
    for scale in (240,100,40,15,5,1.5):
        for _ in range(max(1,iterations//6)):
            j=rng.randrange(k);angle=rng.random()*2*math.pi;radius=scale*math.sqrt(rng.random())
            trial=best[:]
            q=(best[j][0]+radius*math.cos(angle),best[j][1]+radius*math.sin(angle))
            if math.hypot(*q)>1800:continue
            trial[j]=q;value=_score(existing,trial)
            if value<best_value-1e-9:best_value,best=value,trial
    return best if best_value<=threshold+1e-7 else None
