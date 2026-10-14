import math


_HELD_KARP_LIMIT = 11


def _held_karp(start, names, pts):
    n = len(pts)
    dp = {}
    for j, p in enumerate(pts):
        dp[(1 << j, j)] = (math.dist(start, p), -1)
    for mask in range(1, 1 << n):
        for j in range(n):
            if not mask & (1 << j) or (mask, j) not in dp:
                continue
            cost, _ = dp[(mask, j)]
            for k in range(n):
                if mask & (1 << k):
                    continue
                key = (mask | (1 << k), k)
                candidate = cost + math.dist(pts[j], pts[k])
                if key not in dp or candidate < dp[key][0]:
                    dp[key] = (candidate, j)
    full = (1 << n) - 1
    end = min(range(n), key=lambda j: dp[(full, j)][0])
    length = dp[(full, end)][0]
    order = []
    mask = full
    j = end
    while j != -1:
        order.append(names[j])
        prev = dp[(mask, j)][1]
        mask ^= 1 << j
        j = prev
    order.reverse()
    return order, length


def _nn_plus_2opt(start, names, pts):
    n = len(pts)
    visited = [False] * n
    order_idx = []
    cur = start
    for _ in range(n):
        best_j = -1
        best_d = math.inf
        for j in range(n):
            if visited[j]:
                continue
            d = math.dist(cur, pts[j])
            if d < best_d:
                best_d = d
                best_j = j
        visited[best_j] = True
        order_idx.append(best_j)
        cur = pts[best_j]
    improved = True
    while improved:
        improved = False
        for i in range(n - 1):
            for j in range(i + 1, n):
                a = order_idx[i - 1] if i > 0 else None
                b = order_idx[i]
                c = order_idx[j]
                d = order_idx[j + 1] if j + 1 < n else None
                before = 0.0
                after = 0.0
                if a is not None:
                    before += math.dist(pts[a], pts[b])
                    after += math.dist(pts[a], pts[c])
                else:
                    before += math.dist(start, pts[b])
                    after += math.dist(start, pts[c])
                if d is not None:
                    before += math.dist(pts[c], pts[d])
                    after += math.dist(pts[b], pts[d])
                if after < before - 1e-12:
                    order_idx[i:j + 1] = reversed(order_idx[i:j + 1])
                    improved = True
    length = math.dist(start, pts[order_idx[0]])
    for a in range(n - 1):
        length += math.dist(pts[order_idx[a]], pts[order_idx[a + 1]])
    order = [names[i] for i in order_idx]
    return order, length


def optimal_open_route(start, named_points):
    """Shortest open path from start visiting every named point. DP for small n, NN+2-opt otherwise."""
    names = list(named_points)
    if not names:
        return [], 0.0
    pts = [named_points[n] for n in names]
    if len(pts) <= _HELD_KARP_LIMIT:
        return _held_karp(start, names, pts)
    return _nn_plus_2opt(start, names, pts)


def _route_between(start, destination, named_points):
    """Shortest route from start through all named points to destination."""
    if not named_points:
        return [], math.dist(start, destination)
    names = list(named_points)
    pts = [named_points[name] for name in names]
    n = len(pts)
    dp = {}
    for j, point in enumerate(pts):
        dp[(1 << j, j)] = (math.dist(start, point), -1)
    for mask in range(1, 1 << n):
        for j in range(n):
            if (mask, j) not in dp:
                continue
            cost, _ = dp[(mask, j)]
            for k in range(n):
                if mask & (1 << k):
                    continue
                key = (mask | (1 << k), k)
                candidate = cost + math.dist(pts[j], pts[k])
                if key not in dp or candidate < dp[key][0]:
                    dp[key] = (candidate, j)
    full = (1 << n) - 1
    end = min(range(n), key=lambda j: dp[(full, j)][0] + math.dist(pts[j], destination))
    length = dp[(full, end)][0] + math.dist(pts[end], destination)
    order = []
    mask, j = full, end
    while j != -1:
        order.append(names[j])
        previous = dp[(mask, j)][1]
        mask ^= 1 << j
        j = previous
    order.reverse()
    return order, length


def select_clear_insertion(start, destination, points, mature, detour_limit, cluster_radius):
    """Choose the lowest-detour mature singleton or compact cluster to clear now."""
    remaining = set(points).intersection(mature)
    clusters = []
    while remaining:
        seed = remaining.pop()
        component = {seed}
        frontier = [seed]
        while frontier:
            current = frontier.pop()
            neighbors = {
                other for other in remaining
                if math.dist(points[current], points[other]) <= cluster_radius
            }
            remaining.difference_update(neighbors)
            component.update(neighbors)
            frontier.extend(neighbors)
        clusters.append(component)

    direct = math.dist(start, destination)
    candidates = []
    for cluster in clusters:
        subset = {name: points[name] for name in cluster}
        order, length = _route_between(start, destination, subset)
        detour = length - direct
        limit = detour_limit if len(cluster) == 1 else detour_limit * 0.5
        if detour <= limit + 1e-9:
            candidates.append((detour, order))
    return min(candidates, default=(0.0, []), key=lambda item: item[0])[1]
