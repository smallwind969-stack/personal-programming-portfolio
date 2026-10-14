"""Literature-aligned final strategy for Problem 4."""

from .q4_unified_strategy import Q4UnifiedStrategy
from .certified_patrol import build_de_optimized_q4_layout
from .polygon_disk_cover import certified_polygon_disk_cover


class Q4FinalStrategy(Q4UnifiedStrategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_final'

    def _build_fallback_layout(self):
        layout = build_de_optimized_q4_layout(start=(0.0, 0.0))
        self._active_certificate_layout = layout
        return layout

    def _raw_optical_cover(self, c, radius=19.5):
        plan = certified_polygon_disk_cover(
            self.poly[c], self.position, clear_radius=20.0)
        return list(plan.points)
