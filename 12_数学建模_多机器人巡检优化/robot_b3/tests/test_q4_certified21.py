import contextlib
import importlib.util
import io
import math
import unittest


class Certified21Tests(unittest.TestCase):
    def geometry(self):
        self.assertIsNotNone(
            importlib.util.find_spec('robot_b3.q4_local_hull_certificate'),
            '21-station integer certificate module must exist')
        from robot_b3 import q4_local_hull_certificate
        return q4_local_hull_certificate

    def strategy(self, sim):
        self.assertIsNotNone(
            importlib.util.find_spec('robot_b3.q4_certified21_strategy'),
            'independent certified21 strategy must exist')
        from robot_b3.q4_certified21_strategy import Q4Certified21Strategy
        return Q4Certified21Strategy(sim, route_budget_s=.01)

    def test_layout_has_21_unique_millimetre_stations(self):
        layout = self.geometry().build_certified21_layout()
        self.assertEqual(len(set(layout.stations)), 21)
        self.assertEqual(layout.stations[0], (0.0, 0.0))
        self.assertFalse(layout.triangles)  # not the old edge-length certificate
        for point in layout.stations:
            for coordinate in point:
                self.assertAlmostEqual(coordinate * 1000, round(coordinate * 1000))
        distance = sum(math.dist(a, b) for a, b in
                       zip(layout.stations, layout.stations[1:]))
        self.assertAlmostEqual(distance, layout.route_distance_m)
        self.assertAlmostEqual(distance, 17808.42897191402, places=5)

    def test_whole_continuum_is_certified(self):
        geometry = self.geometry()
        result = geometry.verify_local_hull_coverage(
            geometry.certified21_stations())
        self.assertTrue(result.certified)
        self.assertGreater(result.accepted_boxes, 0)
        self.assertLessEqual(result.max_depth, 20)
        self.assertIsNone(result.failed_box)

    def test_bad_layout_and_missing_boundary_station_are_rejected(self):
        geometry = self.geometry()
        self.assertFalse(geometry.verify_local_hull_coverage(((0, 0),)).certified)
        points = geometry.certified21_stations()
        self.assertFalse(geometry.verify_local_hull_coverage(points[:-1]).certified)
        self.assertFalse(geometry.verify_local_hull_coverage(points, max_depth=0).certified)

    def test_unrounded_and_nonfinite_coordinates_are_rejected(self):
        geometry = self.geometry()
        for point in ((.0001, 0), (float('nan'), 0)):
            with self.assertRaises(ValueError):
                geometry.verify_local_hull_coverage((point,))

    def test_strategy_selects_independent_layout_and_fixed_empty_route(self):
        from robot_b3.offline import OfflineSimulator
        strategy = self.strategy(OfflineSimulator({}))
        layout = strategy._build_fallback_layout()
        coverage = strategy._initial_certificate_tasks(layout)
        self.assertEqual(strategy.mode, 'q4_certified21')
        self.assertEqual(len(coverage), 21)
        order = list(reversed(coverage))
        self.assertEqual(strategy._scheduled_key(order, coverage, coverage),
                         next(iter(coverage)))

    def test_unsafe_substitution_does_not_drop_station(self):
        from robot_b3.offline import OfflineSimulator
        sim = OfflineSimulator({})
        strategy = self.strategy(sim)
        layout = strategy._build_fallback_layout()
        old = max(layout.stations, key=lambda q: q[0])
        strategy.position = (0.0, 0.0)
        strategy.unknown = {1, 2}
        coverage = {('certificate', 1): old}
        strategy._after_target_service(coverage, layout)
        self.assertEqual(len(coverage), 1)
        self.assertEqual(sim.measures, 0)

    def test_already_reached_certified_station_can_replace_future_visit(self):
        from robot_b3.offline import OfflineSimulator
        sim = OfflineSimulator({})
        strategy = self.strategy(sim)
        layout = strategy._build_fallback_layout()
        old = max(layout.stations, key=lambda q: q[0])
        strategy.position = old
        strategy.unknown = {1, 2}
        coverage = {('certificate', 1): old, ('certificate', 2): (0., 0.)}
        strategy._after_target_service(coverage, layout)
        self.assertEqual(len(coverage), 1)
        self.assertEqual(sim.measures, 2)
        self.assertEqual(strategy.certificate_replacements, 1)

    def test_empty_scene_finishes_after_21_station_scans(self):
        from robot_b3.offline import OfflineSimulator
        sim = OfflineSimulator({})
        strategy = self.strategy(sim)
        result = strategy.run()
        self.assertTrue(result['discovery_complete'])
        self.assertEqual(result['unknown_channels'], [])
        self.assertEqual(len(result['absent_channels']), 20)
        self.assertEqual(sim.measures, 21 * 20)
        self.assertAlmostEqual(sim.moves_m, 17808.42897191402, places=5)

    def test_cli_accepts_new_mode_without_interface_access(self):
        from robot_b3.run_robot import main
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                result = main(['--mode', 'q4_certified21', '--route-budget', '1'])
        except SystemExit as exc:
            self.fail(f'CLI must accept q4_certified21, exit={exc.code}')
        self.assertEqual(result, 0)
        self.assertIn('q4_certified21', output.getvalue())


if __name__ == '__main__':
    unittest.main()
