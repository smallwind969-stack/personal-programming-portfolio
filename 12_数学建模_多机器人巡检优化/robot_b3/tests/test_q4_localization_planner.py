import unittest


class LocalizationActionPlannerTests(unittest.TestCase):
    def test_information_gain_can_beat_nearest_probe(self):
        from robot_b3.q4_localization_planner import (
            ProbeOption,
            choose_localization_probe,
        )

        near = ProbeOption((0.0, 0.0), .01, 10.0, 100.0)
        informative = ProbeOption((100.0, 0.0), .90, 10.0, 100.0)
        decision = choose_localization_probe(
            position=(0.0, 0.0), destination=None,
            current_channel=1, target_channel=2,
            direct_optical_tail_s=100.0,
            options=(near, informative),
        )

        self.assertIsNotNone(decision)
        self.assertEqual(decision.position, informative.position)
        self.assertLess(decision.expected_total_s, 100.0)

    def test_direct_optical_is_selected_when_no_probe_has_positive_value(self):
        from robot_b3.q4_localization_planner import (
            ProbeOption,
            choose_localization_probe,
        )

        option = ProbeOption((500.0, 0.0), .01, 90.0, 100.0)
        decision = choose_localization_probe(
            position=(0.0, 0.0), destination=None,
            current_channel=1, target_channel=2,
            direct_optical_tail_s=100.0,
            options=(option,),
        )
        self.assertIsNone(decision)

    def test_destination_uses_route_insertion_not_only_current_distance(self):
        from robot_b3.q4_localization_planner import (
            ProbeOption,
            choose_localization_probe,
        )

        off_route = ProbeOption((0.0, 100.0), .8, 10.0, 100.0)
        on_route = ProbeOption((50.0, 0.0), .8, 10.0, 100.0)
        decision = choose_localization_probe(
            position=(0.0, 0.0), destination=(100.0, 0.0),
            current_channel=1, target_channel=1,
            direct_optical_tail_s=100.0,
            options=(off_route, on_route),
        )
        self.assertEqual(decision.position, on_route.position)

    def test_optical_order_minimizes_particle_weighted_time_to_first_hit(self):
        from types import SimpleNamespace
        from robot_b3.q4_localization_planner import order_optical_clear_points

        near = (1.0, 0.0)
        likely = (30.0, 0.0)
        particles = [
            SimpleNamespace(x=near[0], y=near[1], weight=.1),
            SimpleNamespace(x=likely[0], y=likely[1], weight=.9),
        ]

        order = order_optical_clear_points(
            (0.0, 0.0), (near, likely), particles, clear_radius=5.0)

        self.assertEqual(order, (likely, near))
        self.assertEqual(set(order), {near, likely})

    def test_large_optical_cover_uses_bounded_local_search(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import robot_b3.q4_localization_planner as planner

        points = tuple((float(i * 25), float((i % 5) * 25))
                       for i in range(60))
        particles = tuple(
            SimpleNamespace(x=q[0], y=q[1], weight=1.0 / len(points))
            for q in points
        )

        with patch.object(
                planner, '_expected_optical_time',
                wraps=planner._expected_optical_time) as evaluator:
            order = planner.order_optical_clear_points(
                (0.0, 0.0), points, particles, clear_radius=20.0)

        self.assertEqual(len(order), len(points))
        self.assertEqual(set(order), set(points))
        self.assertLessEqual(evaluator.call_count, 300)


if __name__ == '__main__':
    unittest.main()
