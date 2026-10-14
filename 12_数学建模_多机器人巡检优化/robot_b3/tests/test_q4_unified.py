import unittest
from unittest.mock import patch
from types import SimpleNamespace


class UnifiedQ4StrategyTests(unittest.TestCase):
    def _discovered_strategy(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_unified_strategy import Q4UnifiedStrategy

        sim = OfflineSimulator({1: ((600.0, 100.0), 1200.0)}, error_mode='zero')
        strategy = Q4UnifiedStrategy(sim, route_budget_s=.01)
        strategy._measure((0.0, 0.0), 1)
        return strategy

    def test_strategy_is_independent_and_has_multiscale_candidates(self):
        strategy = self._discovered_strategy()
        candidates = strategy._candidate_probe_points(1)

        self.assertEqual(strategy.mode, 'q4_unified')
        self.assertGreater(len(candidates), 4)
        self.assertEqual(len(candidates), len(set(candidates)))

    def test_measured_candidate_is_not_generated_again(self):
        strategy = self._discovered_strategy()
        candidate = strategy._candidate_probe_points(1)[0]
        strategy._measured.add((candidate, 1))
        self.assertNotIn(candidate, strategy._candidate_probe_points(1))

    def test_no_profitable_probe_routes_directly_to_optical_cover(self):
        strategy = self._discovered_strategy()
        optical = strategy._optical_queue(1)
        with patch.object(strategy, '_probe_decision', return_value=None):
            self.assertEqual(strategy._target_point(1), optical[0])

    def test_optical_tail_uses_particle_weighted_first_clear_hit(self):
        from types import SimpleNamespace

        strategy = self._discovered_strategy()
        strategy.position = (0.0, 0.0)
        strategy.beliefs[1].particles = [
            SimpleNamespace(x=0.0, y=0.0, weight=.8),
            SimpleNamespace(x=100.0, y=0.0, weight=.2),
        ]
        with patch.object(
            strategy, '_new_optical_cover',
            return_value=[(0.0, 0.0), (100.0, 0.0)],
        ):
            estimate = strategy._optical_tail_estimate(1)

        self.assertAlmostEqual(estimate, .8 * 5.0 + .2 * 28.0)

    def test_probe_miss_tail_conditions_on_the_no_signal_posterior(self):
        strategy = self._discovered_strategy()
        candidate = (100.0, 0.0)
        child = object()

        class Belief:
            def hit_probability(self, q):
                return .5

            def after_no_signal(self, q):
                self.last_miss = tuple(q)
                return child

        belief = Belief()
        strategy.beliefs[1] = belief
        calls = []

        def optical_tail(channel, start=None, belief=None,
                         optimize_order=True):
            calls.append((channel, start, belief, optimize_order))
            if start is None:
                return 100.0
            return 20.0 if belief is child else 200.0

        with patch.object(strategy, '_candidate_probe_points',
                          return_value=(candidate,)), \
             patch.object(strategy, '_prediction', return_value=100.0), \
             patch.object(strategy, '_circle', return_value=((0.0, 0.0), 100.0)), \
             patch.object(strategy, '_optical_tail_estimate', side_effect=optical_tail):
            decision = strategy._probe_decision(1)

        self.assertIsNotNone(decision)
        self.assertEqual(belief.last_miss, candidate)
        self.assertIn((1, candidate, child, False), calls)

    def test_failed_optical_clear_replans_measurement_without_fixed_threshold(self):
        strategy = self._discovered_strategy()
        failed = (40.0, 0.0)
        follow_up = (40.0, 20.0)
        decision = SimpleNamespace(position=follow_up)
        measured = []

        with patch.object(strategy, '_circle',
                          return_value=((0.0, 0.0), 100.0)), \
             patch.object(strategy, '_probe_decision',
                          side_effect=(None, decision)) as choose, \
             patch.object(strategy, '_optical_queue', return_value=[failed]), \
             patch.object(strategy, '_clear', return_value=False), \
             patch.object(strategy, '_measure',
                          side_effect=lambda q, c: measured.append((q, c))), \
             patch.object(strategy, '_guaranteed_here'):
            strategy._service_one(1, destination=None, remaining_sweeps=10)

        self.assertEqual(choose.call_count, 2)
        self.assertEqual(measured, [(follow_up, 1)])

    def test_optical_cover_is_reordered_by_expected_clear_time(self):
        from robot_b3.q4_routefirst_strategy import Q4RouteFirstStrategy

        strategy = self._discovered_strategy()
        raw = [(1.0, 0.0), (2.0, 0.0)]
        reordered = tuple(reversed(raw))
        with patch.object(Q4RouteFirstStrategy, '_new_optical_cover',
                          return_value=raw), \
             patch('robot_b3.q4_unified_strategy.order_optical_clear_points',
                   return_value=reordered) as optimize:
            result = strategy._new_optical_cover(1)

        self.assertEqual(result, list(reordered))
        optimize.assert_called_once()


if __name__ == '__main__':
    unittest.main()
