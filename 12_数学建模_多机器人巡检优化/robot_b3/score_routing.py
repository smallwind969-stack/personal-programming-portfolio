"""Open-route search with an incumbent and a valid MST lower bound.

The optimality flag concerns the supplied fixed waypoints, not the unknown-source
adaptive problem. Search can use the real-time allowance without spending virtual time.
"""
import math
import time


def plan_open_route(start, named_points, budget_s=1.0):
    names = list(named_points)
    n = len(names)
    if not n:
        return {'order': [], 'distance_m': 0.0, 'lower_bound_m': 0.0, 'proven_optimal': True}
    pts = [named_points[k] for k in names] + [start]
    d = [[math.dist(a, b) for b in pts] for a in pts]
    deadline = time.monotonic()+max(0.0, budget_s)

    def length(order):
        return sum(d[a][b] for a, b in zip([n]+order, order))

    def improve(order):
        # 2-opt including the open end, followed by single-point relocation.
        while True:
            changed = False
            for i in range(n-1):
                a = n if i == 0 else order[i-1]
                b = order[i]
                for j in range(i+1, n):
                    c = order[j]
                    old, new = d[a][b], d[a][c]
                    if j+1 < n:
                        end = order[j+1]
                        old += d[c][end]
                        new += d[b][end]
                    if new < old-1e-8:
                        order[i:j+1] = reversed(order[i:j+1])
                        changed = True
                        break
                if changed:
                    break
            if changed:
                continue
            old = length(order)
            for i in range(n):
                shortened = order[:i]+order[i+1:]
                for j in range(n):
                    candidate = shortened[:j]+[order[i]]+shortened[j:]
                    if length(candidate) < old-1e-8:
                        order = candidate
                        changed = True
                        break
                if changed:
                    break
            if not changed:
                return order

    best_order, best = [], math.inf
    for first in range(n):
        remaining = set(range(n))-{first}
        order = [first]
        while remaining:
            k = min(remaining, key=lambda x: (d[order[-1]][x], x))
            remaining.remove(k)
            order.append(k)
        order = improve(order)
        cost = length(order)
        if cost < best:
            best_order, best = order, cost

    mst_cache = {0: 0.0}

    def mst(mask):
        if mask in mst_cache:
            return mst_cache[mask]
        nodes = [i for i in range(n) if mask & (1 << i)]
        rest = set(nodes[1:])
        cheapest = {j: d[nodes[0]][j] for j in rest}
        value = 0.0
        while rest:
            j = min(rest, key=cheapest.get)
            value += cheapest[j]
            rest.remove(j)
            for k in rest:
                cheapest[k] = min(cheapest[k], d[j][k])
        mst_cache[mask] = value
        return value

    full = (1 << n)-1
    lower_bound = mst(full)+min(d[n][:n])
    visited, timed_out = 0, False
    dominance = {}

    def search(last, mask, cost, prefix):
        nonlocal best, best_order, visited, timed_out
        visited += 1
        if visited % 128 == 0 and time.monotonic() >= deadline:
            timed_out = True
            return
        if timed_out or cost >= best-1e-8:
            return
        if not mask:
            best, best_order = cost, prefix[:]
            return
        key = (last, mask)
        if cost >= dominance.get(key, math.inf)-1e-8:
            return
        dominance[key] = cost
        nodes = [i for i in range(n) if mask & (1 << i)]
        if cost+mst(mask)+min(d[last][j] for j in nodes) >= best-1e-8:
            return
        for j in sorted(nodes, key=lambda x: (d[last][x], x)):
            search(j, mask ^ (1 << j), cost+d[last][j], prefix+[j])
            if timed_out:
                return

    if time.monotonic() < deadline:
        search(n, full, 0.0, [])
    else:
        timed_out = True
    return {'order': [names[j] for j in best_order], 'distance_m': best,
            'lower_bound_m': lower_bound if timed_out else best,
            'proven_optimal': not timed_out, 'search_nodes': visited}
