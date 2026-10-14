"""Literature-aligned final strategy for Problem 3.

The class is intentionally isolated from the earlier competition modes so the
new decision model can evolve without changing a known baseline.
"""

from .q3_dynamic_strategy import Q3DynamicStrategy
from .polygon_disk_cover import certified_polygon_disk_cover


class Q3FinalStrategy(Q3DynamicStrategy):
    guaranteed_clear_radius_m = 20.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q3_final'

    def _build_optical_clear_chain(self, polygon, start, destination=None):
        """Use a certificate clipped to the feasible polygon, not its box."""
        return certified_polygon_disk_cover(
            polygon, start, destination=destination,
            clear_radius=self.guaranteed_clear_radius_m,
        )
