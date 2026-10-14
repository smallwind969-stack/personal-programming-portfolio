import itertools
import math
import unittest

from robot_b3.geometry import arena_polygon, bearing_clip


class ScoreTests(unittest.TestCase):
    def test_exact_coverage_certificate_for_seven_points(self):
        from robot_b3.coverage import farthest_uncovered
        from robot_b3.geometry import seven_points
        p, radius = farthest_uncovered(seven_points(1123))
        self.assertLessEqual(radius, 1000)
        self.assertLessEqual(math.hypot(*p), 1800+1e-7)

    def test_center_alone_does_not_certify_arena(self):
        from robot_b3.coverage import farthest_uncovered
        _, radius = farthest_uncovered([(0, 0)])
        self.assertAlmostEqual(radius, 1800)

    def test_target_visit_can_replace_a_fixed_coverage_station(self):
        from robot_b3.coverage import farthest_uncovered
        stations = [(0,0),(1140,0),(570,987),(-570,987),(-1140,0),(-570,-987)]
        before = farthest_uncovered(stations)[1]
        after = farthest_uncovered(stations+[(570,-987)])[1]
        self.assertGreater(before,1000)
        self.assertLessEqual(after,1000)

    def test_official_199_second_example_and_clear_keeps_channel(self):
        from robot_b3.offline import OfflineSimulator
        sim = OfflineSimulator({})
        sim.enter()
        sim.measure((300, 400), 1)
        sim.measure((300, 400), 2)
        sim.clear((300, 0), 3)
        self.assertEqual(sim.current_channel, 2)
        sim.measure((300, 0), 2)
        self.assertAlmostEqual(sim.exit()['virtual_time_s'], 199)

    def test_repeat_measurement_error_fixed_by_position(self):
        from robot_b3.offline import OfflineSimulator
        sim = OfflineSimulator({1: ((800, 100), 1000)}, seed=9)
        sim.enter()
        a = sim.measure((0, 0), 1)['svd_deg']
        sim.measure((300, 200), 1)
        self.assertEqual(a, sim.measure((0, 0), 1)['svd_deg'])

    def test_arena_polygon_contains_boundary_between_vertices(self):
        poly = arena_polygon(sides=36)
        p = (1800*math.cos(math.pi/36), 1800*math.sin(math.pi/36))
        for a, b in zip(poly, poly[1:] + poly[:1]):
            cross = (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
            self.assertGreaterEqual(cross, -1e-7)

    def test_clear_point_stays_within_every_vertex_and_saves_distance(self):
        from robot_b3.geometry import clear_visit_point
        poly = [(100, -3), (103, 0), (100, 3), (97, 0)]
        q = clear_visit_point(poly, (0, 0), (200, 0))
        self.assertTrue(all(math.dist(q, p) <= 19.9+1e-7 for p in poly))
        self.assertLess(q[0], 90)

    def test_bearing_least_squares_recovers_intersection(self):
        from robot_b3.geometry import bearing_least_squares
        estimate, quality=bearing_least_squares([((-500,0),0),((0,-500),90)])
        self.assertAlmostEqual(estimate[0],0,places=8)
        self.assertAlmostEqual(estimate[1],0,places=8)
        self.assertGreater(quality,0.9)

    def test_parallel_bearings_are_rejected_for_optical_probe(self):
        from robot_b3.geometry import bearing_least_squares
        estimate,quality=bearing_least_squares([((0,0),0),((0,10),0.1)])
        self.assertIsNotNone(estimate)
        self.assertLess(quality,0.01)

    def test_branch_bound_matches_exhaustive_open_path(self):
        from robot_b3.score_routing import plan_open_route
        start = (0, 0)
        pts = {'a': (1, 1), 'b': (0, 6), 'c': (7, 2), 'd': (5, -2), 'e': (3, 6)}
        answer = plan_open_route(start, pts, budget_s=1)
        best = min(math.dist(start, pts[o[0]]) + sum(math.dist(pts[a], pts[b])
                   for a, b in zip(o, o[1:])) for o in itertools.permutations(pts))
        self.assertAlmostEqual(answer['distance_m'], best)
        self.assertTrue(answer['proven_optimal'])
        self.assertEqual(set(answer['order']), set(pts))

    def test_short_local_refinement_remains_in_reception_range(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.score_strategy import ScoreStrategy
        sim = OfflineSimulator({1: ((0, 0), 1000)})
        strategy = ScoreStrategy(sim, route_budget_s=0.01)
        strategy.position = (-100, 0)
        strategy.poly[1] = [(-40, -4), (40, -4), (40, 4), (-40, 4)]
        strategy.observations[1] = [((-800, 0), 0)]
        strategy.found = {1}
        q = strategy.refinement_point(1)
        self.assertLess(math.dist(q, (0, 0)), 200)
        self.assertLessEqual(max(math.dist(q, p) for p in strategy.poly[1]), 1000)

    def test_robust_reception_accepts_candidate_beyond_old_999_rule(self):
        from robot_b3.active_localization import guaranteed_reception
        poly = [(1200, -5), (1300, -5), (1300, 5), (1200, 5)]
        q = (600, 950)
        self.assertGreater(max(math.dist(q, p) for p in poly), 999)
        self.assertTrue(guaranteed_reception(poly, q, [(0, 0)]))

    def test_robust_reception_rejects_uncovered_candidate(self):
        from robot_b3.active_localization import guaranteed_reception
        poly = [(1200, -5), (1300, -5), (1300, 5), (1200, 5)]
        self.assertFalse(guaranteed_reception(poly, (-600, 950), [(0, 0)]))

    def test_all_positive_stations_expand_guaranteed_reception_region(self):
        from robot_b3.active_localization import guaranteed_reception
        poly = [(-1078.16, 213.18), (-1018.16, 213.18),
                (-1018.16, 273.18), (-1078.16, 273.18)]
        q = (-1843.45, -649.25)
        self.assertFalse(guaranteed_reception(poly, q, [(0, 0)]))
        self.assertTrue(guaranteed_reception(
            poly, q, [(0, 0), (-100.98, -845.41)]))

    def test_fusion_refinement_is_certified_and_accepts_destination(self):
        from robot_b3.active_localization import guaranteed_reception
        from robot_b3.fusion_strategy import FusionStrategy
        from robot_b3.offline import OfflineSimulator
        strategy = FusionStrategy(OfflineSimulator({}), route_budget_s=.01)
        strategy.position = (0, 0)
        strategy.poly[1] = [(800, -20), (1400, -20), (1400, 20), (800, 20)]
        strategy.observations[1] = [((0, 0), 0)]
        strategy.found = {1}
        q = strategy.refinement_point(1, destination=(1500, 500))
        self.assertTrue(guaranteed_reception(strategy.poly[1], q, [(0, 0)]))
        self.assertNotEqual(q, (0, 0))

    def test_fusion_refinement_records_dynamic_decision_evidence(self):
        from robot_b3.fusion_strategy import FusionStrategy
        from robot_b3.offline import OfflineSimulator

        class MemoryLogger:
            def __init__(self):
                self.records = []

            def write(self, event, **data):
                self.records.append({'event': event, **data})

        logger = MemoryLogger()
        strategy = FusionStrategy(OfflineSimulator({}), logger=logger,
                                  route_budget_s=.01)
        strategy.position = (0, 0)
        strategy.poly[1] = [(800, -20), (1400, -20),
                            (1400, 20), (800, 20)]
        strategy.observations[1] = [((0, 0), 0)]
        strategy.found = {1}
        selected = strategy.refinement_point(1, destination=(1500, 500))

        decisions = [r for r in logger.records
                     if r['event'] == 'refinement_decision']
        self.assertEqual(len(decisions), 1)
        record = decisions[0]
        self.assertEqual(tuple(record['selected_position']), tuple(selected))
        self.assertEqual(record['channel'], 1)
        self.assertEqual(record['gate_s'], 100.0)
        self.assertGreater(record['total_candidates'], 0)
        self.assertGreater(record['feasible_candidates'], 0)
        self.assertIn('baseline_cost_s', record)
        self.assertIn('best_cost_s', record)
        self.assertIn('predicted_radius_m', record)

    def test_single_bearing_target_waits_for_useful_shared_station(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.score_strategy import ScoreStrategy
        sim=OfflineSimulator({})
        strategy=ScoreStrategy(sim)
        strategy.poly[1]=[(-10,-10),(1010,-10),(1010,10),(-10,10)]
        strategy.observations[1]=[((-500,0),0)]
        strategy.found={1}
        self.assertTrue(strategy.defer_to_shared_station(1,[(500,-600)]))

    def test_learned_reception_radius_skips_implausible_known_measurement(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.score_strategy import ScoreStrategy
        strategy=ScoreStrategy(OfflineSimulator({}))
        strategy.poly[1]=[(990,-10),(1010,-10),(1010,10),(990,10)]
        strategy.observations[1]=[((0,0),0)]
        strategy.found={1}
        self.assertFalse(strategy.likely_reception(1,(-1000,0),margin=100))

    def test_full_run_from_zero_including_fixed_errors(self):
        from robot_b3.offline import OfflineSimulator, make_scene
        from robot_b3.score_strategy import ScoreStrategy
        sim = OfflineSimulator(make_scene(91, count=10), seed=91)
        result = ScoreStrategy(sim, route_budget_s=0.02).run()
        self.assertEqual(result['cleared'], 10)
        self.assertTrue(result['discovery_complete'])
        self.assertTrue(sim.exited)
        self.assertAlmostEqual(result['virtual_time_s'], sim.cost_breakdown()['total_s'])

    def test_dynamic_coverage_is_certified_from_actual_scan_stations(self):
        from robot_b3.coverage import farthest_uncovered
        from robot_b3.offline import OfflineSimulator, make_scene
        from robot_b3.score_strategy import ScoreStrategy
        sim=OfflineSimulator(make_scene(119,count=10),seed=119)
        strategy=ScoreStrategy(sim,route_budget_s=0.01)
        result=strategy.run()
        self.assertLessEqual(farthest_uncovered(strategy.scan_stations)[1],1000+1e-7)
        self.assertTrue(result['discovery_complete'])
        self.assertEqual(result['coverage_stations'],len(strategy.scan_stations))

    def test_per_channel_search_replaces_future_station_without_losing_certificate(self):
        from robot_b3.channel_strategy import ChannelCoverageStrategy
        from robot_b3.offline import OfflineSimulator
        sim=OfflineSimulator({})
        strategy=ChannelCoverageStrategy(sim,route_budget_s=.01)
        strategy._fixed_scan(0)
        strategy.position=(570,-987);sim.position=strategy.position
        before=sum(len(x) for x in strategy.search_remaining.values())
        strategy._opportunistic_search(strategy.position)
        after=sum(len(x) for x in strategy.search_remaining.values())
        self.assertLess(after,before)

    def test_sixteen_sources_certify_completion_without_full_coverage(self):
        from robot_b3.offline import OfflineSimulator
        from robot_b3.score_strategy import ScoreStrategy
        scene = {i: ((300*math.cos(i), 300*math.sin(i)), 1000) for i in range(1, 17)}
        sim = OfflineSimulator(scene, seed=4)
        result = ScoreStrategy(sim, route_budget_s=0.01).run()
        self.assertEqual(result['cleared'], 16)
        self.assertTrue(result['discovery_complete'])
        self.assertEqual(result['coverage_stations'], 1)


if __name__ == '__main__':
    unittest.main()
