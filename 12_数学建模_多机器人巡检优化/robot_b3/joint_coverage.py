"""Joint strict disk-cover and open-route optimizer for Problem B, Question 3.

The seven-point hexagonal construction is used only as a certified incumbent.
Every accepted deformation is checked against the continuous circular arena,
so route shortening never comes from silently leaving an uncovered raster cell.
"""
import math

from .coverage import farthest_uncovered
from .coverage_optimizer import complete_coverage
from .geometry import seven_points
from .routing import optimal_open_route


ARENA_RADIUS = 1800.0
COVER_RADIUS = 1000.0
SYMMETRIC_RING_RADIUS = 1123.0


def _inside_arena(q):
    return math.hypot(q[0], q[1]) <= ARENA_RADIUS + 1e-8


def _key(points):
    return tuple((round(q[0], 5), round(q[1], 5)) for q in points)


def _route_value(start, free, targets):
    tasks = {('scan', i): q for i, q in enumerate(free)}
    tasks.update({('target', name): q for name, q in targets.items()})
    order, distance = optimal_open_route(start, tasks)
    return distance, order


def _evaluate(start, existing, free, targets, threshold):
    if len({_key([q]) for q in free}) != len(free):
        return None
    if any(not _inside_arena(q) for q in free):
        return None
    witness, cover_radius = farthest_uncovered(existing + free, ARENA_RADIUS)
    if cover_radius > threshold + 1e-7:
        return None
    distance, order = _route_value(start, free, targets)
    return {
        'centers': [tuple(q) for q in free],
        'route_order': order,
        'distance_m': distance,
        'coverage_radius_m': cover_radius,
        'coverage_witness': witness,
    }


def _fallback(existing, free_count, budget_s, threshold):
    if not existing and free_count == 7:
        return seven_points(SYMMETRIC_RING_RADIUS)
    return complete_coverage(existing, free_count,
                             budget_s=min(.20, max(.04, budget_s*.15)),
                             threshold=threshold)


def _move_candidates(points, order, start, step):
    """Generate deterministic local deformations guided by the open route."""
    scan_order = [item[1] for item in order if item[0] == 'scan']
    predecessor = {}
    previous = start
    for index in scan_order:
        predecessor[index] = previous
        previous = points[index]
    successor = {scan_order[i]: points[scan_order[i+1]]
                 for i in range(len(scan_order)-1)}
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1),
                  (.7071067812, .7071067812), (.7071067812, -.7071067812),
                  (-.7071067812, .7071067812), (-.7071067812, -.7071067812)]
    for i, q in enumerate(points):
        local = list(directions)
        anchors = [predecessor.get(i), successor.get(i)]
        anchors = [a for a in anchors if a is not None]
        if anchors:
            ax = sum(a[0] for a in anchors)/len(anchors)
            ay = sum(a[1] for a in anchors)/len(anchors)
            dx, dy = ax-q[0], ay-q[1]
            norm = math.hypot(dx, dy)
            if norm > 1e-9:
                local.insert(0, (dx/norm, dy/norm))
        radial = math.hypot(*q)
        if radial > 1e-9:
            local.extend([(-q[0]/radial, -q[1]/radial),
                          (-q[1]/radial, q[0]/radial),
                          (q[1]/radial, -q[0]/radial)])
        for ux, uy in local:
            trial = list(points)
            trial[i] = (q[0]+step*ux, q[1]+step*uy)
            yield trial

    # Coherent translations/rotations let the search escape a boundary-active
    # symmetric layout without requiring one infeasible intermediate point.
    for ux, uy in directions[:4]:
        yield [(q[0]+step*.35*ux, q[1]+step*.35*uy) for q in points]
    angle = min(.08, step/ARENA_RADIUS)
    for sign in (-1, 1):
        c, s = math.cos(sign*angle), math.sin(sign*angle)
        yield [(c*q[0]-s*q[1], s*q[0]+c*q[1]) for q in points]


def _select_beam(pool, width=4):
    """Keep route quality plus one slack-rich state for feasible exploration."""
    by_route = sorted(pool, key=lambda item: (item['distance_m'],
                                               item['coverage_radius_m']))
    chosen = by_route[:max(1, width-1)]
    slack = min(pool, key=lambda item: (item['coverage_radius_m'],
                                        item['distance_m']))
    if _key(slack['centers']) not in {_key(item['centers']) for item in chosen}:
        chosen.append(slack)
    return chosen[:width]


def optimize_joint_cover(start, existing, free_count, targets=None, initial_free=None,
                         budget_s=1.0, threshold=COVER_RADIUS):
    """Minimize remaining open-route length subject to exact disk coverage.

    ``existing`` stations have already been scanned and therefore contribute to
    the coverage certificate without being route tasks.  ``initial_free`` is the
    current remaining plan and makes online replanning lossless: if no deformation
    improves it, the previous certified plan is returned unchanged.
    """
    start = tuple(start)
    existing = [tuple(q) for q in existing]
    targets = dict(targets or {})
    seeds = []
    if initial_free is not None and len(initial_free) == free_count:
        seeds.append([tuple(q) for q in initial_free])
    fallback = _fallback(existing, free_count, budget_s, threshold)
    if fallback is not None and len(fallback) == free_count:
        seeds.append([tuple(q) for q in fallback])
    if not existing and free_count == 7:
        # This layout has useful feasibility slack for route-directed deformation.
        seeds.append(seven_points(1200.0))

    beam = []
    seen = set()
    evaluations = 0
    incumbent_distance = math.inf
    max_evaluations = max(80, min(1200, int(420*max(.1, budget_s))))
    for seed in seeds:
        k = _key(seed)
        if k in seen:
            continue
        seen.add(k)
        value = _evaluate(start, existing, seed, targets, threshold)
        evaluations += 1
        if value is not None:
            beam.append(value)
            if initial_free is not None and _key(seed) == _key(initial_free):
                incumbent_distance = value['distance_m']
    if not beam:
        return None
    beam = _select_beam(beam)

    for step in (180.0, 90.0, 45.0, 20.0, 8.0, 3.0, 1.0):
        if evaluations >= max_evaluations:
            break
        pool = list(beam)
        for state in beam:
            for trial in _move_candidates(state['centers'], state['route_order'], start, step):
                if evaluations >= max_evaluations:
                    break
                k = _key(trial)
                if k in seen:
                    continue
                seen.add(k)
                value = _evaluate(start, existing, trial, targets, threshold)
                evaluations += 1
                if value is not None:
                    pool.append(value)
        beam = _select_beam(pool)

    best = dict(min(beam, key=lambda item: (item['distance_m'],
                                            item['coverage_radius_m'])))
    best['evaluations'] = evaluations
    best['certified'] = True
    best['incumbent_distance_m'] = (None if not math.isfinite(incumbent_distance)
                                    else incumbent_distance)
    best['improvement_m'] = (0.0 if not math.isfinite(incumbent_distance)
                             else incumbent_distance-best['distance_m'])
    best['used_symmetric_fallback'] = (
        _key(best['centers']) == _key(seven_points(SYMMETRIC_RING_RADIUS))
        if not existing and free_count == 7 else False)
    return best
