import importlib.util
import unittest


class OpticalChoiceTests(unittest.TestCase):
    def chooser(self):
        self.assertIsNotNone(importlib.util.find_spec('robot_b3.q4_optical_choice_strategy'))
        from robot_b3.q4_optical_choice_strategy import optical_chain_preferred
        return optical_chain_preferred

    def test_near_complete_chain_beats_long_probe(self):
        self.assertTrue(self.chooser()((0, 0), [(10, 0), (20, 0)], [(400, 0)], 1, 1))

    def test_long_chain_does_not_displace_short_probe(self):
        self.assertFalse(self.chooser()((0, 0), [(500, 0), (900, 0)], [(20, 0)], 1, 1))

    def test_empty_optical_cover_is_not_a_solution(self):
        self.assertFalse(self.chooser()((0, 0), [], [(20, 0)], 1, 1))

    def test_no_probes_uses_nonempty_optical_cover(self):
        self.assertTrue(self.chooser()((0, 0), [(500, 0)], [], 1, 1))

    def test_probe_must_return_to_possible_source_region(self):
        polygon = [(-10, -10), (10, -10), (10, 10), (-10, 10)]
        self.assertTrue(self.chooser()((500, 0), [(5, 0)], [(400, 0)], 1, 1,
                                       polygon=polygon))
