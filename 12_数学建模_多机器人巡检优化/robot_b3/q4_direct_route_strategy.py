"""Use the full task-route solution without belief-based station advancement."""
from .q4_certified21_strategy import Q4Certified21Strategy


class Q4DirectRouteStrategy(Q4Certified21Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_direct_route'

    def _scheduled_key(self, order, tasks, coverage):
        if coverage and all(key[0] == 'certificate' for key in tasks):
            return next(iter(coverage))
        return order[0]
