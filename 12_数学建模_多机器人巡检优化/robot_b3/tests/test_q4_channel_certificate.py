import unittest
from types import SimpleNamespace
from unittest.mock import patch

from robot_b3.offline import OfflineSimulator
from robot_b3.q4_channel_certificate_strategy import Q4ChannelCertificateStrategy
from robot_b3.q4_channel_insertion_strategy import Q4ChannelInsertionStrategy


class ChannelCertificateTests(unittest.TestCase):
    def fixture(self):
        strategy = Q4ChannelCertificateStrategy(OfflineSimulator({}))
        strategy.unknown = {1, 2}
        layout = SimpleNamespace(stations=((0., 0.), (100., 0.)))
        coverage = strategy._initial_certificate_tasks(layout)
        return strategy, coverage, layout

    def test_failed_proof_preserves_every_obligation(self):
        s, coverage, layout = self.fixture()
        before = dict(coverage)
        with patch('robot_b3.q4_channel_certificate_strategy.verify_local_hull_coverage',
                   return_value=SimpleNamespace(certified=False)):
            s._refresh_certificate_tasks(coverage, layout)
        self.assertEqual(coverage, before)
        self.assertEqual(s.channel_obligations[1], set(before))

    def test_one_channels_certificate_does_not_retire_other_channels_station(self):
        s, coverage, layout = self.fixture()
        s._checked_history[2] = ()
        with patch('robot_b3.q4_channel_certificate_strategy.verify_local_hull_coverage',
                   return_value=SimpleNamespace(certified=True, accepted_boxes=1)):
            s._refresh_certificate_tasks(coverage, layout)
        self.assertEqual(len(coverage), 2)
        self.assertEqual(s.channel_obligations[1], set())
        self.assertEqual(len(s.channel_obligations[2]), 2)

    def test_interrupted_scan_retains_obligations(self):
        s, coverage, _ = self.fixture()
        s._time_ok = lambda: False
        self.assertFalse(s._execute_certificate_task(('certificate', 0), (0, 0), coverage))
        self.assertIn(('certificate', 0), s.channel_obligations[1])

    def test_real_certificate_can_reuse_channel_history(self):
        s = Q4ChannelCertificateStrategy(OfflineSimulator({}))
        s.unknown = {1, 2}
        layout = s._build_fallback_layout()
        coverage = s._initial_certificate_tasks(layout)
        s._measured = {(p, 1) for p in layout.stations}
        s._refresh_certificate_tasks(coverage, layout)
        self.assertEqual(len(s.channel_obligations[1]), 18)
        self.assertEqual(len(s.channel_obligations[2]), 21)
        self.assertEqual(len(coverage), 21)

    def test_complete_empty_scene_retains_full_discovery(self):
        sim = OfflineSimulator({})
        result = Q4ChannelCertificateStrategy(sim, route_budget_s=.01).run()
        self.assertTrue(result['discovery_complete'])
        self.assertEqual(len(result['absent_channels']), 20)
        self.assertEqual(sim.measures, 420)

    def test_insertion_never_measures_on_rejected_certificate(self):
        s = Q4ChannelInsertionStrategy(OfflineSimulator({}))
        s.unknown = {1}
        s._time_ok = lambda: True
        layout = SimpleNamespace(stations=((100., 0.),))
        coverage = s._initial_certificate_tasks(layout)
        with patch('robot_b3.q4_channel_insertion_strategy.verify_local_hull_coverage',
                   return_value=SimpleNamespace(certified=False)):
            with patch.object(s, '_measure') as measure:
                s._after_target_service(coverage, layout)
                measure.assert_not_called()
        self.assertEqual(len(s.channel_obligations[1]), 1)


if __name__ == '__main__':
    unittest.main()
