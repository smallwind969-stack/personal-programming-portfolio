import unittest


class ChannelBeliefTests(unittest.TestCase):
    def test_failed_clear_removes_particles_inside_optical_disk(self):
        from robot_b3.q4_belief import ChannelBelief, SourceParticle

        belief = ChannelBelief([
            SourceParticle(0.0, 0.0, 1000.0, None, .5),
            SourceParticle(100.0, 0.0, 1000.0, None, .5),
        ], absent_weight=0.0)
        belief.observe_clear_miss((0.0, 0.0), radius=20.0)

        self.assertEqual(len(belief.particles), 1)
        self.assertEqual((belief.particles[0].x, belief.particles[0].y),
                         (100.0, 0.0))

    def test_bearing_polygon_conditions_particle_positions(self):
        from robot_b3.q4_belief import ChannelBelief

        belief = ChannelBelief.prior(spatial_step=450.0, orientation_count=8)
        polygon = [(400.0, -50.0), (500.0, -50.0),
                   (500.0, 50.0), (400.0, 50.0)]
        belief.condition_polygon(polygon)

        self.assertTrue(belief.particles)
        self.assertTrue(all(
            400.0 - 1e-8 <= p.x <= 500.0 + 1e-8
            and -50.0 - 1e-8 <= p.y <= 50.0 + 1e-8
            for p in belief.particles
        ))

    def test_polygon_conditioning_rebuilds_support_when_grid_misses_region(self):
        from robot_b3.q4_belief import ChannelBelief

        belief = ChannelBelief.prior(spatial_step=600.0, orientation_count=4)
        polygon = [(100.0, 100.0), (120.0, 100.0),
                   (120.0, 120.0), (100.0, 120.0)]
        belief.condition_polygon(polygon)

        self.assertTrue(belief.particles)
        self.assertTrue(all(
            100.0 - 1e-8 <= p.x <= 120.0 + 1e-8
            and 100.0 - 1e-8 <= p.y <= 120.0 + 1e-8
            for p in belief.particles
        ))

    def test_direction_excludes_particles_in_the_near_disk(self):
        from robot_b3.q4_belief import ChannelBelief, SourceParticle

        belief = ChannelBelief([
            SourceParticle(2.0, 0.0, 1000.0, None, .5),
            SourceParticle(20.0, 0.0, 1000.0, None, .5),
        ], absent_weight=0.0)
        belief.observe_direction((0.0, 0.0))

        self.assertEqual(len(belief.particles), 1)
        self.assertEqual((belief.particles[0].x, belief.particles[0].y),
                         (20.0, 0.0))

    def test_positive_signal_conditions_on_existence_and_reception(self):
        from robot_b3.q4_belief import ChannelBelief

        belief = ChannelBelief.prior(spatial_step=450.0, orientation_count=8)
        belief.observe_signal((0.0, 0.0))

        self.assertEqual(belief.absent_weight, 0.0)
        self.assertAlmostEqual(belief.hit_probability((0.0, 0.0)), 1.0)

    def test_hypothetical_no_signal_branch_does_not_mutate_parent(self):
        from robot_b3.q4_belief import ChannelBelief

        belief = ChannelBelief.prior(spatial_step=450.0, orientation_count=8)
        before = belief.hit_probability((0.0, 0.0))
        child = belief.after_no_signal((0.0, 0.0))

        self.assertAlmostEqual(belief.hit_probability((0.0, 0.0)), before)
        self.assertAlmostEqual(child.hit_probability((0.0, 0.0)), 0.0)

    def test_no_signal_makes_repeating_same_measurement_worthless(self):
        from robot_b3.q4_belief import ChannelBelief

        belief = ChannelBelief.prior(spatial_step=450.0, orientation_count=8)
        before = belief.hit_probability((0.0, 0.0))
        belief.observe_no_signal((0.0, 0.0))

        self.assertGreater(before, 0.0)
        self.assertAlmostEqual(belief.hit_probability((0.0, 0.0)), 0.0)

    def test_distant_observation_retains_possible_sources(self):
        from robot_b3.q4_belief import ChannelBelief

        belief = ChannelBelief.prior(spatial_step=450.0, orientation_count=8)
        belief.observe_no_signal((0.0, 0.0))

        self.assertGreater(belief.hit_probability((1500.0, 0.0)), 0.0)


class ActionValueTests(unittest.TestCase):
    def test_depth_two_rollout_expands_both_measurement_outcomes(self):
        from robot_b3.q4_rollout import OpportunityRolloutPlanner

        class Belief:
            def __init__(self, probability): self.probability = probability
            def hit_probability(self, q): return self.probability
            def after_no_signal(self, q): return Belief(0.0)

        planner = OpportunityRolloutPlanner(depth=2, beam_width=4)
        decision = planner.choose(
            position=(0.0, 0.0), current_channel=1,
            remaining_sweeps=12,
            beliefs={1: Belief(.5), 2: Belief(.3)}, unknown={1, 2})

        self.assertIsNotNone(decision)
        self.assertEqual(decision.channel, 1)
        self.assertLess(decision.expected_delta_s, 0.0)
        self.assertGreater(decision.branches_evaluated, 2)
        self.assertEqual(decision.depth, 2)

    def test_depth_two_rollout_can_choose_continue_route(self):
        from robot_b3.q4_rollout import OpportunityRolloutPlanner

        class Belief:
            def hit_probability(self, q): return .001
            def after_no_signal(self, q): return self

        decision = OpportunityRolloutPlanner(depth=2).choose(
            position=(0.0, 0.0), current_channel=1,
            remaining_sweeps=2, beliefs={1: Belief()}, unknown={1})
        self.assertIsNone(decision)

    def test_tail_risk_rejects_a_marginal_high_miss_probability_scan(self):
        from robot_b3.q4_rollout import OpportunityRolloutPlanner

        class Belief:
            def hit_probability(self, q): return .10
            def after_no_signal(self, q): return Belief()

        # Mean-only value is 5 - .1*(10*6) = -1 second, but a miss costs
        # five seconds.  The requested mean-plus-tail objective rejects it.
        decision = OpportunityRolloutPlanner(depth=2, risk_weight=.3).choose(
            position=(0.0, 0.0), current_channel=1,
            remaining_sweeps=10, beliefs={1: Belief()}, unknown={1})
        self.assertIsNone(decision)

    def test_profitable_scan_uses_expected_saved_future_sweeps(self):
        from robot_b3.q4_belief import opportunity_value_seconds

        value = opportunity_value_seconds(
            hit_probability=0.5,
            remaining_sweeps=10,
            switch_required=True,
        )
        self.assertGreater(value, 0.0)

    def test_low_probability_scan_is_rejected(self):
        from robot_b3.q4_belief import opportunity_value_seconds

        value = opportunity_value_seconds(
            hit_probability=0.01,
            remaining_sweeps=2,
            switch_required=True,
        )
        self.assertLess(value, 0.0)


class BeliefStrategyTests(unittest.TestCase):
    def test_optical_cover_prunes_cells_far_outside_feasible_polygon(self):
        import math
        from robot_b3.geometry import point_polygon_distance
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_belief_strategy import Q4BeliefStrategy

        strategy = Q4BeliefStrategy(OfflineSimulator({}), route_budget_s=.01)
        strategy.position = (0.0, 0.0)
        strategy.observations[1] = [((0.0, 0.0), 0.0)]
        strategy.poly[1] = [(0.0, 0.0), (100.0, 0.0), (0.0, 100.0)]
        centers = strategy._new_optical_cover(1, radius=19.5)

        self.assertTrue(centers)
        self.assertTrue(all(
            point_polygon_distance(q, strategy.poly[1]) <= 19.5 + 1e-7
            for q in centers
        ))
        for x in range(0, 101, 5):
            for y in range(0, 101 - x, 5):
                self.assertLessEqual(
                    min(math.dist((x, y), q) for q in centers), 19.5 + 1e-7
                )

    def test_competition_fallback_uses_shorter_twenty_five_station_patch(self):
        from robot_b3.full_view import build_competition_full_view_layout, certifying_triangle

        layout = build_competition_full_view_layout()
        self.assertEqual(len(layout.stations), 25)
        for radius in range(0, 1801, 120):
            for degree in range(0, 360, 10):
                a = __import__('math').radians(degree)
                point = (radius*__import__('math').cos(a), radius*__import__('math').sin(a))
                triangle = certifying_triangle(layout, point)
                self.assertIsNotNone(triangle)
                self.assertTrue(all(__import__('math').dist(point, q) <= 995.0+1e-6
                                    for q in triangle))

    def test_strategy_has_independent_mode_and_no_legacy_distance_gates(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_belief_strategy import Q4BeliefStrategy

        strategy = Q4BeliefStrategy(OfflineSimulator({}), route_budget_s=.01)
        self.assertEqual(strategy.mode, 'q4_belief')
        self.assertFalse(hasattr(strategy, 'novelty_distance_m'))
        self.assertFalse(hasattr(strategy, 'insertion_distance_m'))
        self.assertEqual(strategy.rollout.depth, 2)

    def test_no_signal_updates_only_the_channel_belief(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_belief_strategy import Q4BeliefStrategy

        strategy = Q4BeliefStrategy(OfflineSimulator({}), route_budget_s=.01)
        before_1 = strategy.beliefs[1].hit_probability((0.0, 0.0))
        before_2 = strategy.beliefs[2].hit_probability((0.0, 0.0))
        strategy._measure((0.0, 0.0), 1)
        self.assertLess(strategy.beliefs[1].hit_probability((0.0, 0.0)), before_1)
        self.assertEqual(strategy.beliefs[2].hit_probability((0.0, 0.0)), before_2)

    def test_known_channel_no_signal_still_updates_its_reception_belief(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_belief_strategy import Q4BeliefStrategy

        sim = OfflineSimulator({1: ((500.0, 0.0), 1000.0)}, error_mode='zero')
        strategy = Q4BeliefStrategy(sim, route_budget_s=.01)
        strategy._measure((0.0, 0.0), 1)
        probe = (-600.0, 0.0)
        before = strategy.beliefs[1].hit_probability(probe)
        strategy._measure(probe, 1)

        self.assertGreater(before, 0.0)
        self.assertAlmostEqual(strategy.beliefs[1].hit_probability(probe), 0.0)
        self.assertEqual(strategy.beliefs[1].absent_weight, 0.0)

    def test_probe_actions_have_a_hard_cap_before_optical_fallback(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_belief_strategy import Q4BeliefStrategy

        sim = OfflineSimulator({1: ((0.0, 0.0), 1000.0)}, error_mode='zero')
        strategy = Q4BeliefStrategy(sim, route_budget_s=.01)
        self.assertEqual(strategy.max_probe_actions, 3)
        strategy._measure((500.0, 0.0), 1)
        strategy._probe_attempts[1] = strategy.max_probe_actions

        self.assertEqual(strategy._probe_queue(1), [])

    def test_station_scheduler_can_buy_a_small_detour_for_earlier_discovery(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_belief_strategy import Q4BeliefStrategy

        class Belief:
            def hit_probability(self, q):
                return 0.9 if q == (110.0, 0.0) else 0.1

        strategy = Q4BeliefStrategy(OfflineSimulator({}), route_budget_s=.01)
        strategy.position = (0.0, 0.0)
        strategy.unknown = {1}
        strategy.beliefs = {1: Belief()}
        order = [('certificate', 0), ('certificate', 1)]
        tasks = {order[0]: (100.0, 0.0), order[1]: (110.0, 0.0)}
        coverage = dict(tasks)

        self.assertEqual(strategy._scheduled_key(order, tasks, coverage), order[1])

    def test_rollout_is_closed_before_any_dynamic_target_stop(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.q4_belief_strategy import Q4BeliefStrategy

        strategy = Q4BeliefStrategy(OfflineSimulator({}), route_budget_s=.01)
        self.assertIsNone(strategy._next_rollout_decision(20))


if __name__ == '__main__':
    unittest.main()
