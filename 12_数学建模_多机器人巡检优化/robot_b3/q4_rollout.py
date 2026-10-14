"""Finite-horizon outcome-tree optimizer for zero-detour Q4 measurements."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RolloutDecision:
    channel: int
    expected_delta_s: float
    hit_probability: float
    branches_evaluated: int
    depth: int


class OpportunityRolloutPlanner:
    """Minimize expected change in remaining completion time.

    Continuing the mandatory route has value zero.  A negative tree value means
    that measuring now is expected to beat continuing immediately.
    """

    def __init__(self, depth=2, beam_width=6, future_sweep_cost=6.0,
                 risk_weight=0.3):
        if depth < 1 or beam_width < 1:
            raise ValueError('depth and beam_width must be positive')
        self.depth = int(depth)
        self.beam_width = int(beam_width)
        self.future_sweep_cost = float(future_sweep_cost)
        self.risk_weight = float(risk_weight)

    def _search(self, position, current_channel, remaining_sweeps,
                beliefs, unknown, depth):
        if depth <= 0 or not unknown or remaining_sweeps <= 0:
            return 0.0, None, 0
        saved = remaining_sweeps*self.future_sweep_cost
        ranked = []
        for c in unknown:
            probability = min(1.0, max(0.0, beliefs[c].hit_probability(position)))
            immediate = 5.0+(0.0 if current_channel == c else 1.0)
            ranked.append((immediate-probability*saved, c, probability, immediate))
        ranked.sort()
        best_value, best_channel = 0.0, None
        branches = 0
        for _, c, probability, immediate in ranked[:self.beam_width]:
            hit_unknown = set(unknown)
            hit_unknown.remove(c)
            hit_value, _, hit_branches = self._search(
                position, c, remaining_sweeps, beliefs, hit_unknown, depth-1)
            miss_beliefs = dict(beliefs)
            miss_beliefs[c] = beliefs[c].after_no_signal(position)
            miss_value, _, miss_branches = self._search(
                position, c, remaining_sweeps, miss_beliefs, set(unknown), depth-1)
            hit_branch = -saved+hit_value
            miss_branch = miss_value
            mean = (immediate+probability*hit_branch
                    +(1.0-probability)*miss_branch)
            # A finite-horizon mean-plus-tail objective.  For the binary
            # observation tree the worse branch is the exact one-step CVaR
            # surrogate; only positive completion-time regret is penalized.
            tail = immediate+max(hit_branch, miss_branch)
            expected = mean+self.risk_weight*max(0.0, tail)
            branches += 2+hit_branches+miss_branches
            if expected < best_value-1e-9:
                best_value, best_channel = expected, c
        return best_value, best_channel, branches

    def choose(self, position, current_channel, remaining_sweeps,
               beliefs, unknown):
        value, channel, branches = self._search(
            tuple(position), current_channel, int(remaining_sweeps),
            beliefs, set(unknown), self.depth)
        if channel is None:
            return None
        probability = beliefs[channel].hit_probability(position)
        return RolloutDecision(channel, value, probability, branches, self.depth)
