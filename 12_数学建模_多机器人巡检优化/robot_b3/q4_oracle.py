"""Offline Q4 exact-route and evaluation primitives.

This module may use SciPy because it is never imported by the live robot entry.
Runtime strategies consume only precomputed layouts.
"""

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ExactRouteResult:
    order: tuple
    distance_m: float
    lower_bound_m: float
    relative_gap: float
    proven_optimal: bool
    status: str


@dataclass(frozen=True)
class OracleClearResult:
    route: ExactRouteResult
    move_distance_m: float
    move_s: float
    clear_s: float
    total_lower_bound_s: float


def exact_open_route_milp(start, named_points, time_limit_s=60.0):
    """Solve a start-fixed, end-free Euclidean Hamiltonian path by MILP."""
    if time_limit_s <= 0:
        raise ValueError('time_limit_s must be positive')
    names = tuple(named_points)
    if not names:
        return ExactRouteResult((), 0.0, 0.0, 0.0, True, 'empty')

    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp
    from scipy.sparse import lil_matrix

    points = tuple(tuple(named_points[name]) for name in names)
    n = len(points)
    source, sink = n, n + 1
    arcs = []
    costs = []
    for j in range(n):
        arcs.append((source, j))
        costs.append(math.dist(start, points[j]))
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            arcs.append((i, j))
            costs.append(math.dist(points[i], points[j]))
    for i in range(n):
        arcs.append((i, sink))
        costs.append(0.0)

    arc_index = {arc: k for k, arc in enumerate(arcs)}
    arc_count = len(arcs)
    variable_count = arc_count + n
    objective = np.zeros(variable_count)
    objective[:arc_count] = costs

    equality_rows = 2 + 2 * n
    equalities = lil_matrix((equality_rows, variable_count), dtype=float)
    rhs = np.ones(equality_rows)
    row = 0
    for j in range(n):
        equalities[row, arc_index[(source, j)]] = 1.0
    row += 1
    for i in range(n):
        equalities[row, arc_index[(i, sink)]] = 1.0
    row += 1
    for j in range(n):
        equalities[row, arc_index[(source, j)]] = 1.0
        for i in range(n):
            if i != j:
                equalities[row, arc_index[(i, j)]] = 1.0
        row += 1
    for i in range(n):
        equalities[row, arc_index[(i, sink)]] = 1.0
        for j in range(n):
            if i != j:
                equalities[row, arc_index[(i, j)]] = 1.0
        row += 1

    mtz_rows = n * (n - 1)
    mtz = lil_matrix((mtz_rows, variable_count), dtype=float)
    mtz_upper = np.full(mtz_rows, n - 1.0)
    row = 0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            mtz[row, arc_count + i] = 1.0
            mtz[row, arc_count + j] = -1.0
            mtz[row, arc_index[(i, j)]] = float(n)
            row += 1

    lower = np.zeros(variable_count)
    upper = np.ones(variable_count)
    lower[arc_count:] = 1.0
    upper[arc_count:] = float(n)
    integrality = np.zeros(variable_count, dtype=int)
    integrality[:arc_count] = 1
    constraints = [
        LinearConstraint(equalities.tocsr(), rhs, rhs),
        LinearConstraint(mtz.tocsr(), np.full(mtz_rows, -np.inf), mtz_upper),
    ]
    result = milp(
        objective,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=constraints,
        options={
            'time_limit': float(time_limit_s),
            'mip_rel_gap': 0.0,
            'presolve': True,
        },
    )
    if result.x is None:
        raise RuntimeError(f'open-route MILP found no incumbent: {result.message}')

    selected = {arcs[k] for k, value in enumerate(result.x[:arc_count])
                if value > 0.5}
    current = next(j for i, j in selected if i == source)
    order_indices = []
    while current != sink:
        order_indices.append(current)
        outgoing = [j for i, j in selected if i == current]
        if len(outgoing) != 1:
            raise RuntimeError('MILP incumbent does not encode one open path')
        current = outgoing[0]
    if len(order_indices) != n:
        raise RuntimeError('MILP incumbent omits route vertices')

    distance = float(result.fun)
    dual = getattr(result, 'mip_dual_bound', distance)
    lower_bound = float(dual) if dual is not None and math.isfinite(dual) else 0.0
    gap = getattr(result, 'mip_gap', math.inf)
    gap = float(gap) if gap is not None else math.inf
    proven = bool(result.success and gap <= 1e-9)
    return ExactRouteResult(
        tuple(names[i] for i in order_indices), distance, lower_bound,
        max(0.0, gap), proven, str(result.message),
    )


def omniscient_clear_oracle(sources, start=(0.0, 0.0), time_limit_s=60.0):
    """Lower bound that knows every source and clears once at its exact site."""
    points = {channel: tuple(spec[0]) for channel, spec in sources.items()}
    route = exact_open_route_milp(start, points, time_limit_s=time_limit_s)
    clear_s = 5.0 * len(points)
    move_s = route.distance_m / 5.0
    return OracleClearResult(
        route, route.distance_m, move_s, clear_s, move_s + clear_s,
    )


def decompose_oracle_regret(actual, oracle):
    """Decompose completion time above the omniscient clear lower bound."""
    components = {
        'excess_move_s': float(actual['move_s']) - oracle.move_s,
        'measurement_regret_s': float(actual['measure_s']),
        'switch_regret_s': float(actual['switch_s']),
        'clear_regret_s': float(actual['clear_s']) - oracle.clear_s,
    }
    components['total_regret_s'] = sum(components.values())
    components['oracle_lower_bound_s'] = oracle.total_lower_bound_s
    components['oracle_route_gap'] = oracle.route.relative_gap
    return components
