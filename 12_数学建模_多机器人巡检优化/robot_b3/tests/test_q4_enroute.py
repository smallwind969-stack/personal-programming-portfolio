import importlib.util
import math
import unittest
from robot_b3.offline import OfflineSimulator


class EnrouteTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('robot_b3.q4_enroute_strategy'))
        from robot_b3 import q4_enroute_strategy
        return q4_enroute_strategy

    def test_segment_hits_all_vertex_disks(self):
        poly = [(50, -10), (50, 10)]
        point = self.module().segment_clear_point((0, 0), (100, 0), poly)
        self.assertIsNotNone(point)
        self.assertEqual(point[1], 0)
        self.assertTrue(all(math.dist(point, p) <= 19.9 for p in poly))

    def test_large_region_and_off_route_target_are_rejected(self):
        f = self.module().segment_clear_point
        self.assertIsNone(f((0, 0), (100, 0), [(50, -30), (50, 30)]))
        self.assertIsNone(f((0, 0), (100, 0), [(50, 100)]))
        self.assertIsNone(f((0, 0), (100, 0), []))

    def test_zero_length_leg(self):
        f = self.module().segment_clear_point
        self.assertEqual(f((0, 0), (0, 0), [(1, 1)]), (0, 0))
        self.assertIsNone(f((0, 0), (0, 0), [(50, 0)]))

    def strategy(self):
        sim = OfflineSimulator({1: ((50, 0), 1000), 2: ((150, 0), 1000)})
        s = self.module().Q4EnrouteStrategy(sim)
        s._time_ok = lambda: True
        s.found = {1, 2}
        s.unknown.difference_update(s.found)
        s.poly = {1: [(50, -2), (50, 2)], 2: [(150, -2), (150, 2)]}
        return s, sim

    def test_two_targets_clear_in_route_order_without_extra_distance(self):
        s, sim = self.strategy()
        s._measure((200, 0), 3)
        self.assertEqual(sim.cleared, {1, 2})
        self.assertEqual([a[0] for a in sim.actions], ['clear', 'clear', 'measure'])
        self.assertAlmostEqual(sim.moves_m, 200)
        self.assertEqual(sim.switches, 1)
        self.assertEqual(sim.current_channel, 3)
        self.assertAlmostEqual(sim.virtual_time_s, 56)

    def test_scheduled_clear_is_not_issued_twice(self):
        s, sim = self.strategy()
        self.assertTrue(s._clear((150, 0), 2))
        self.assertEqual([a[2] for a in sim.actions], [1, 2])
        self.assertEqual(sim.failures, 0)
        self.assertEqual(sim.current_channel, 1)
        self.assertAlmostEqual(sim.moves_m, 150)

    def test_deadline_disables_optional_chain(self):
        s, sim = self.strategy()
        s._time_ok = lambda: False
        s._measure((200, 0), 3)
        self.assertEqual(sim.cleared, set())
