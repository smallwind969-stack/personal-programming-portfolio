import unittest


class Q3FinalStrategyTests(unittest.TestCase):
    def test_mode_is_isolated(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q3_final_strategy import Q3FinalStrategy

        strategy = Q3FinalStrategy(OfflineSimulator({}), route_budget_s=.01)
        self.assertEqual(strategy.mode, 'q3_final')

    def test_final_strategy_uses_polygon_clipped_optical_cover(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q3_final_strategy import Q3FinalStrategy

        strategy = Q3FinalStrategy(OfflineSimulator({}), route_budget_s=.01)
        polygon = [(-100.0, -80.0), (-90.0, -90.0),
                   (100.0, 80.0), (90.0, 90.0)]
        plan = strategy._build_optical_clear_chain(
            polygon, start=(0.0, 0.0), destination=None)
        self.assertGreater(len(plan.points), 0)
        self.assertEqual(plan.method, 'polygon_cell_certificate')

    def test_guaranteed_clear_threshold_is_twenty_metres(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q3_final_strategy import Q3FinalStrategy

        strategy = Q3FinalStrategy(OfflineSimulator({}), route_budget_s=.01)
        self.assertEqual(strategy.guaranteed_clear_radius_m, 20.0)


if __name__ == '__main__':
    unittest.main()
