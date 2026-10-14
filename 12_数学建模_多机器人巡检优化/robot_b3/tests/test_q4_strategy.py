import math
import unittest

from robot_b3.full_view import (build_full_view_layout, certifying_triangle,
                                receiver_side_probe_pairs)


class FullViewGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.layout = build_full_view_layout(side=990.0)

    def test_every_retained_triangle_has_short_edges_and_retained_vertices(self):
        stations = {(round(x, 7), round(y, 7)) for x, y in self.layout.stations}
        self.assertTrue(self.layout.triangles)
        for triangle in self.layout.triangles:
            for a, b in ((0, 1), (1, 2), (2, 0)):
                self.assertLessEqual(math.dist(triangle[a], triangle[b]), 990.0+1e-7)
            for vertex in triangle:
                self.assertIn((round(vertex[0], 7), round(vertex[1], 7)), stations)

    def test_representative_arena_points_have_analytic_triangle_certificate(self):
        for radial in range(0, 1801, 90):
            for degree in range(0, 360, 5):
                a = math.radians(degree)
                p = (radial*math.cos(a), radial*math.sin(a))
                triangle = certifying_triangle(self.layout, p)
                self.assertIsNotNone(triangle, p)
                self.assertTrue(all(math.dist(p, q) <= 990.0+1e-6
                                    for q in triangle))

    def test_receiver_side_probe_pair_is_inside_previous_range_and_straddles(self):
        pairs = receiver_side_probe_pairs((0.0, 0.0), (1000.0, 0.0))
        self.assertEqual(len(pairs), 2)
        for pair in pairs:
            self.assertEqual(len(pair), 2)
            self.assertTrue(all(math.dist((0, 0), q) < 1000 for q in pair))
            self.assertAlmostEqual(pair[0][0], pair[1][0])
            self.assertAlmostEqual(pair[0][1], -pair[1][1])


class DirectionalOfflineTests(unittest.TestCase):
    def test_directional_source_is_heard_in_front_and_not_behind(self):
        from robot_b3.offline import OfflineSimulator
        # Orientation 0 degrees radiates eastward from the source.
        sim = OfflineSimulator({1: ((0, 0), 1000, 0.0)}, error_mode='zero')
        sim.enter()
        self.assertEqual(sim.measure((500, 0), 1)['measure_result'], 'direction')
        self.assertEqual(sim.measure((-500, 0), 1)['measure_result'], 'no_signal')

    def test_directional_boundary_is_inclusive(self):
        from robot_b3.offline import OfflineSimulator
        sim = OfflineSimulator({1: ((0, 0), 1000, 0.0)}, error_mode='zero')
        sim.enter()
        self.assertEqual(sim.measure((0, 500), 1)['measure_result'], 'direction')

    def test_legacy_omnidirectional_tuple_remains_supported(self):
        from robot_b3.offline import OfflineSimulator
        sim = OfflineSimulator({1: ((0, 0), 1000)}, error_mode='zero')
        sim.enter()
        self.assertEqual(sim.measure((-500, 0), 1)['measure_result'], 'direction')


class Q4StrategyTests(unittest.TestCase):
    def test_low_source_state_keeps_joint_route_target_insertion(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_strategy import Q4Strategy
        strategy = Q4Strategy(OfflineSimulator({}))
        strategy.found.update(range(1, 11))
        order = [('target', 1), ('full_view', 0)]
        tasks = {('target', 1): (900.0, 0.0),
                 ('full_view', 0): (1000.0, 0.0)}
        self.assertEqual(strategy._scheduled_key(order, tasks), ('target', 1))

    def test_fifteen_source_state_defers_only_large_target_detour(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_strategy import Q4Strategy
        strategy = Q4Strategy(OfflineSimulator({}), insertion_distance_m=220)
        strategy.found.update(range(1, 16))
        strategy.position = (0.0, 0.0)
        order = [('target', 1), ('full_view', 0)]
        tasks = {('target', 1): (0.0, 1000.0),
                 ('full_view', 0): (1000.0, 0.0)}
        self.assertEqual(strategy._scheduled_key(order, tasks), ('full_view', 0))

    def test_no_signal_does_not_clip_a_found_directional_source(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_strategy import Q4Strategy
        sim = OfflineSimulator({1: ((0, 0), 1000, 0.0)}, error_mode='zero')
        strategy = Q4Strategy(sim, route_budget_s=.01)
        strategy.position = (500, 0)
        strategy._measure((500, 0), 1)
        before = list(strategy.poly[1])
        self.assertEqual(strategy._measure((-500, 0), 1), 'no_signal')
        self.assertEqual(strategy.poly[1], before)
        self.assertIn(1, strategy.found)

    def test_sixteen_found_channels_cancel_remaining_discovery(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_strategy import Q4Strategy
        scene = {c: ((0, 0), 1000) for c in range(1, 17)}
        strategy = Q4Strategy(OfflineSimulator(scene, error_mode='zero'))
        for c in range(1, 17):
            strategy._measure((500, 0), c)
        self.assertFalse(strategy.unknown)
        self.assertEqual(strategy.absent, {17, 18, 19, 20})

    def test_probe_pair_is_cancelled_after_first_positive_measurement(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_strategy import Q4Strategy
        sim = OfflineSimulator({1: ((0, 0), 1000, 0.0)}, error_mode='zero')
        strategy = Q4Strategy(sim)
        strategy.position = (800, 0)
        strategy._measure((800, 0), 1)
        before = len(sim.actions)
        strategy._probe_once(1, None)
        self.assertEqual(len(sim.actions), before+1)
        self.assertGreaterEqual(len(strategy.observations[1]), 2)

    def test_mixed_scene_at_a_certified_station_is_fully_cleared(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_strategy import Q4Strategy
        q = build_full_view_layout(side=990.0).stations[0]
        scene = {c: (q, 1000, 30.0) if c % 2 else (q, 1000)
                 for c in range(1, 11)}
        sim = OfflineSimulator(scene, error_mode='zero', max_actions=1500)
        result = Q4Strategy(sim, route_budget_s=.01).run()
        self.assertEqual(result['cleared'], 10)
        self.assertTrue(result['discovery_complete'])
        self.assertTrue(sim.exited)


if __name__ == '__main__':
    unittest.main()
