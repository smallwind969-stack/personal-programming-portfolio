import unittest


class CertifiedPatrolTests(unittest.TestCase):
    def test_q3_seven_station_cover_is_continuously_certified(self):
        from robot_b3.certified_patrol import (
            build_q3_seven_station_layout, validate_q3_disk_cover)

        layout = build_q3_seven_station_layout()
        report = validate_q3_disk_cover(layout)
        self.assertTrue(report.feasible)
        self.assertEqual(len(layout.stations), 7)
        self.assertLessEqual(report.worst_distance_m, 1000.0)

    def test_q4_layout_covers_arena_with_sub_1000_triangles(self):
        from robot_b3.certified_patrol import (
            build_de_optimized_q4_layout, validate_q4_triangle_certificate)

        layout = build_de_optimized_q4_layout()
        report = validate_q4_triangle_certificate(layout)
        self.assertTrue(report.feasible)
        self.assertEqual(len(layout.stations), 25)
        self.assertLess(report.max_edge_m, 1000.0)
        self.assertGreaterEqual(report.outer_inradius_m, 1800.0)

    def test_offline_differential_evolution_returns_a_feasible_candidate(self):
        from robot_b3.certified_patrol import optimize_q4_polar_parameters

        result = optimize_q4_polar_parameters(
            generations=2, population_size=8, seed=3)
        self.assertTrue(result['feasible'])
        self.assertLess(result['max_edge_m'], 1000.0)


if __name__ == '__main__':
    unittest.main()
