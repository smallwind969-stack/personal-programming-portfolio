import math
import unittest


class Q3BeliefTests(unittest.TestCase):
    def test_no_signal_conditions_on_range_and_existence(self):
        from robot_b3.q3_belief import OmniParticle, Q3ChannelBelief

        belief = Q3ChannelBelief([
            OmniParticle(0.0, 0.0, 1000.0, 0.4),
            OmniParticle(1400.0, 0.0, 1000.0, 0.4),
        ], absent_weight=0.2)
        belief.observe_no_signal((0.0, 0.0))

        self.assertEqual(len(belief.particles), 1)
        self.assertAlmostEqual(belief.particles[0].x, 1400.0)
        self.assertAlmostEqual(belief.absent_weight, 1.0 / 3.0)

    def test_expected_information_gain_is_entropy_reduction(self):
        from robot_b3.q3_belief import OmniParticle, Q3ChannelBelief
        from robot_b3.q3_dynamic_planner import expected_information_gain

        belief = Q3ChannelBelief([
            OmniParticle(0.0, 0.0, 1000.0, 0.5),
            OmniParticle(1600.0, 0.0, 1000.0, 0.5),
        ], absent_weight=0.0)
        gain = expected_information_gain(belief, (0.0, 0.0))

        self.assertAlmostEqual(gain, 1.0, places=7)


class Q3DynamicPlannerTests(unittest.TestCase):
    def test_lower_total_time_wins_without_station_count_or_margin_gate(self):
        from robot_b3.q3_dynamic_planner import PlanEstimate, choose_plan

        old = PlanEstimate('fixed', 500.0, station_count=4)
        dynamic = PlanEstimate('dynamic', 499.5, station_count=4)

        self.assertEqual(choose_plan([old, dynamic]).name, 'dynamic')

    def test_measure_cost_includes_movement_detection_and_switch(self):
        from robot_b3.q3_dynamic_planner import measure_immediate_time

        self.assertAlmostEqual(
            measure_immediate_time((0.0, 0.0), (300.0, 400.0), 1, 2),
            106.0,
        )

    def test_depth_two_value_uses_feedback_probabilities(self):
        from robot_b3.q3_dynamic_planner import ActionEstimate, choose_action

        informative = ActionEstimate(
            'measure', (0.0, 0.0), 1, 6.0,
            outcomes=((0.5, 10.0), (0.5, 30.0)),
        )
        direct = ActionEstimate(
            'continue', (0.0, 0.0), None, 5.0,
            outcomes=((1.0, 22.0),),
        )

        self.assertEqual(choose_action([informative, direct]).kind, 'measure')

    def test_optical_chain_finitely_covers_a_small_localization_region(self):
        from robot_b3.q3_dynamic_planner import optical_clear_chain

        polygon = [(0.0, 0.0), (46.84, 0.0), (46.84, 20.41), (0.0, 20.41)]
        chain = optical_clear_chain(polygon, start=(-900.0, 10.0))

        self.assertLessEqual(len(chain.points), 3)
        for i in range(48):
            for j in range(22):
                point = (46.84 * i / 47.0, 20.41 * j / 21.0)
                self.assertLessEqual(
                    min(math.dist(point, q) for q in chain.points),
                    20.0 + 1e-7,
                )

    def test_log_replay_prefers_finite_clear_chain_after_third_bearing(self):
        from robot_b3.geometry import (arena_polygon, bearing_clip,
                                       reception_clip)
        from robot_b3.q3_dynamic_planner import (ActionEstimate, choose_action,
                                                  optical_clear_chain)

        polygon = arena_polygon()
        observations = [
            ((1123.00, 0.00), 49.81),
            ((876.61, 365.60), 14.93),
            ((687.11, 739.75), 350.06),
        ]
        for station, bearing in observations:
            polygon = reception_clip(
                bearing_clip(polygon, station, bearing, 1.00000001), station)
        chain = optical_clear_chain(polygon, start=observations[-1][0])
        stalled_measure = ActionEstimate(
            'measure', (668.27, 774.67), 8, 13.0,
            outcomes=((1.0, 275.0),),
            information_gain_bits=0.0,
            mec_gain_m=0.0,
        )
        clear_action = ActionEstimate(
            'clear_chain', chain.points[0], 8, chain.expected_time_s,
            outcomes=((1.0, 0.0),),
        )

        self.assertEqual(choose_action([stalled_measure, clear_action]).kind,
                         'clear_chain')
        self.assertLess(chain.upper_time_s, 230.0)


class Q3DynamicStrategyTests(unittest.TestCase):
    def test_strategy_keeps_per_channel_scan_histories(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q3_dynamic_strategy import Q3DynamicStrategy

        strategy = Q3DynamicStrategy(OfflineSimulator({}), route_budget_s=0.01)
        strategy._measure((0.0, 0.0), 1)
        strategy._measure((300.0, 0.0), 2)

        self.assertEqual(strategy.channel_stations[1], [(0.0, 0.0)])
        self.assertEqual(strategy.channel_stations[2], [(300.0, 0.0)])
        self.assertNotEqual(strategy.beliefs[1].entropy(),
                            strategy.beliefs[2].entropy())

    def test_dynamic_opportunity_can_be_selected_without_reducing_station_count(self):
        from robot_b3.q3_dynamic_strategy import opportunity_is_better

        self.assertTrue(opportunity_is_better(
            old_route_m=1000.0,
            new_route_m=970.0,
            immediate_measure_s=5.0,
            old_future_measure_s=12.0,
            new_future_measure_s=6.0,
            hit_probability=0.0,
            expected_hit_saving_s=0.0,
        ))

    def test_refinement_candidates_remain_guaranteed_receivable(self):
        from robot_b3.active_localization import guaranteed_reception
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q3_dynamic_strategy import Q3DynamicStrategy

        sim = OfflineSimulator({1: ((900.0, 200.0), 1000.0)}, error_mode='zero')
        strategy = Q3DynamicStrategy(sim, route_budget_s=0.01)
        strategy._measure((0.0, 0.0), 1)
        q = strategy.refinement_point(1)

        positives = [station for station, _ in strategy.observations[1]]
        self.assertTrue(guaranteed_reception(strategy.poly[1], q, positives))
        self.assertTrue(math.isfinite(strategy._prediction(1, q)))

    def test_service_uses_clear_chain_instead_of_repeating_zero_gain_bearings(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q3_dynamic_strategy import Q3DynamicStrategy

        class ReplaySimulator(OfflineSimulator):
            replay = iter((49.81, 14.93, 350.06, 348.07))

            def measure(self, p, c):
                response = super().measure(p, c)
                if c == 8 and response['measure_result'] == 'direction':
                    try:
                        response['svd_deg'] = next(self.replay)
                    except StopIteration:
                        pass
                return response

        sim = ReplaySimulator({8: ((1604.0, 570.0), 1500.0)},
                              error_mode='zero')
        strategy = Q3DynamicStrategy(sim, route_budget_s=0.01)
        self.assertEqual(strategy._measure((0.0, 0.0), 8), 'no_signal')
        self.assertEqual(strategy._measure((561.5, -972.55), 8), 'no_signal')
        for q in ((1123.0, 0.0), (876.61, 365.60), (687.11, 739.75)):
            self.assertEqual(strategy._measure(q, 8), 'direction')
        before = sim.measures

        strategy._service(8, (561.5, 972.5465))
        if 8 not in strategy.cleared:
            strategy._service(8, (561.5, 972.5465))

        self.assertIn(8, strategy.cleared)
        self.assertLessEqual(sim.measures, before + 1)
        self.assertLessEqual(sim.failures + sim.successes, 3)


if __name__ == '__main__':
    unittest.main()
