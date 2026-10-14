import math
import unittest


class RouteFirstGeometryTests(unittest.TestCase):
    def test_polar_certificate_is_strict_and_short(self):
        from robot_b3.full_view import (
            build_route_first_full_view_layout,
            certifying_triangle,
        )

        layout = build_route_first_full_view_layout()
        self.assertEqual(len(layout.stations), 25)
        self.assertEqual(len(layout.triangles), 32)
        self.assertLess(layout.route_distance_m, 18000.0)

        longest = max(
            math.dist(triangle[i], triangle[(i + 1) % 3])
            for triangle in layout.triangles
            for i in range(3)
        )
        self.assertLess(longest, 1000.0)

        for radius in range(0, 1801, 60):
            for degree in range(0, 360, 3):
                angle = math.radians(degree)
                point = (radius * math.cos(angle), radius * math.sin(angle))
                triangle = certifying_triangle(layout, point)
                self.assertIsNotNone(triangle, point)
                self.assertTrue(
                    all(math.dist(point, q) < 1000.0 for q in triangle),
                    (point, triangle),
                )

    def test_boundary_station_can_move_slightly_outward_but_not_inward(self):
        from robot_b3.full_view import (
            build_route_first_full_view_layout,
            can_replace_certificate_station,
        )

        layout = build_route_first_full_view_layout()
        old = max(layout.stations, key=lambda q: q[0])
        outward = (old[0] + 2.0, old[1])
        inward = (old[0] - 2.0, old[1])

        self.assertTrue(can_replace_certificate_station(layout, old, old))
        self.assertTrue(can_replace_certificate_station(layout, old, outward))
        self.assertFalse(can_replace_certificate_station(layout, old, inward))

    def test_interior_station_is_not_replaceable(self):
        from robot_b3.full_view import (
            build_route_first_full_view_layout,
            can_replace_certificate_station,
        )

        layout = build_route_first_full_view_layout()
        center = min(layout.stations, key=lambda q: math.hypot(*q))
        self.assertFalse(
            can_replace_certificate_station(layout, center, (1.0, 0.0))
        )

    def test_replacement_produces_the_next_certificate_state(self):
        from robot_b3.full_view import (
            build_route_first_full_view_layout,
            replace_certificate_station,
        )

        layout = build_route_first_full_view_layout()
        old = max(layout.stations, key=lambda q: q[0])
        candidate = (old[0] + 2.0, old[1])
        updated = replace_certificate_station(layout, old, candidate)

        self.assertTrue(any(candidate in triangle for triangle in updated.triangles))
        self.assertFalse(any(old in triangle for triangle in updated.triangles))
        self.assertTrue(any(old in triangle for triangle in layout.triangles))


class RouteFirstStrategyTests(unittest.TestCase):
    def test_strategy_selects_route_first_layout(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_routefirst_strategy import Q4RouteFirstStrategy

        strategy = Q4RouteFirstStrategy(OfflineSimulator({}), route_budget_s=.01)
        layout = strategy._build_fallback_layout()

        self.assertEqual(strategy.mode, "q4_routefirst")
        self.assertLess(layout.route_distance_m, 18000.0)

    def test_safe_target_stop_replaces_one_future_boundary_station(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_routefirst_strategy import Q4RouteFirstStrategy

        sim = OfflineSimulator({})
        strategy = Q4RouteFirstStrategy(sim, route_budget_s=.01)
        layout = strategy._build_fallback_layout()
        old = max(layout.stations, key=lambda q: q[0])
        strategy.position = (old[0] + 2.0, old[1])
        strategy.unknown = {1, 2}
        coverage = {("certificate", 7): old}

        strategy._after_target_service(coverage, layout)

        self.assertEqual(coverage, {})
        self.assertEqual(sim.measures, 2)
        self.assertEqual(strategy.certificate_replacements, 1)
        self.assertTrue(
            any(strategy.position in triangle
                for triangle in strategy._active_certificate_layout.triangles)
        )


if __name__ == "__main__":
    unittest.main()
