"""Exact fallback completion for one unknown channel's measured stations."""
import itertools

from .coverage import farthest_uncovered
from .coverage_optimizer import complete_coverage
from .routing import optimal_open_route


def minimum_completion(existing, candidates, start, threshold=1000.0):
    """Return the smallest candidate subset that certifies 1000 m coverage.

    Ties are resolved by shortest open route from ``start`` and then by the
    original candidate order, making online decisions reproducible.
    """
    existing = [tuple(q) for q in existing]
    candidates = list(dict.fromkeys(tuple(q) for q in candidates if tuple(q) not in existing))
    for size in range(len(candidates) + 1):
        feasible = []
        for indices in itertools.combinations(range(len(candidates)), size):
            chosen = [candidates[i] for i in indices]
            if farthest_uncovered(existing + chosen)[1] <= threshold + 1e-7:
                named = {i: q for i, q in zip(indices, chosen)}
                distance = optimal_open_route(start, named)[1]
                feasible.append((distance, indices, chosen))
        if feasible:
            return min(feasible, key=lambda item: (item[0], item[1]))[2]
    return None


def optimized_completion(existing, fallback, start, budget_s=.1, threshold=1000.0):
    """Allow free completion centers, falling back to the certified fixed subset."""
    fixed = minimum_completion(existing, fallback, start, threshold)
    if fixed is None:
        return None
    for size in range(len(fixed)):
        planned = complete_coverage(existing, size, budget_s=budget_s, threshold=threshold)
        if planned is not None:
            return planned
    return fixed
