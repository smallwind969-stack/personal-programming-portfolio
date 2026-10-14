import unittest


class Q4FinalStrategyTests(unittest.TestCase):
    def test_mode_is_isolated_and_layout_is_certified(self):
        from robot_b3.certified_patrol import validate_q4_triangle_certificate
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_final_strategy import Q4FinalStrategy

        strategy = Q4FinalStrategy(OfflineSimulator({}), route_budget_s=.01)
        layout = strategy._build_fallback_layout()
        self.assertEqual(strategy.mode, 'q4_final')
        self.assertTrue(validate_q4_triangle_certificate(layout).feasible)
        self.assertEqual(len(layout.stations), 25)

    def test_final_layout_improves_previous_static_route(self):
        from robot_b3.full_view import build_route_first_full_view_layout
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_final_strategy import Q4FinalStrategy

        strategy = Q4FinalStrategy(OfflineSimulator({}), route_budget_s=.01)
        self.assertLess(
            strategy._build_fallback_layout().route_distance_m,
            build_route_first_full_view_layout().route_distance_m,
        )

    def test_final_optical_fallback_uses_polygon_certificate(self):
        from unittest.mock import patch
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_final_strategy import Q4FinalStrategy

        strategy = Q4FinalStrategy(OfflineSimulator({}), route_budget_s=.01)
        strategy.poly[1] = [(-60.0, 0.0), (0.0, -12.0),
                            (60.0, 0.0), (0.0, 12.0)]
        with patch('robot_b3.q4_final_strategy.certified_polygon_disk_cover') as cover:
            cover.return_value.points = ((0.0, 0.0),)
            self.assertEqual(strategy._raw_optical_cover(1), [(0.0, 0.0)])
            cover.assert_called_once()


if __name__ == '__main__':
    unittest.main()
