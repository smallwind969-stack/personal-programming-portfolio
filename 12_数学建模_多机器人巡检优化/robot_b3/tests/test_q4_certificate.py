import unittest


class PerChannelDiscoveryCertificateTests(unittest.TestCase):
    def setUp(self):
        from robot_b3.full_view import build_route_first_full_view_layout
        from robot_b3.q4_certificate import PerChannelDiscoveryCertificate

        self.layout = build_route_first_full_view_layout()
        self.certificate = PerChannelDiscoveryCertificate(
            self.layout, channels=(1, 2))

    def test_requirements_group_shared_physical_stations(self):
        requirements = self.certificate.requirements((1, 2))

        self.assertEqual(len(requirements), len(self.layout.stations))
        self.assertTrue(all(channels == {1, 2}
                            for channels in requirements.values()))

    def test_one_channel_observation_does_not_discharge_another(self):
        station = self.layout.stations[0]
        self.certificate.record_no_signal(1, station)
        requirements = self.certificate.requirements((1, 2))

        self.assertNotIn(1, requirements[station])
        self.assertIn(2, requirements[station])

    def test_replacement_requires_an_observed_no_signal(self):
        channel = 1
        station = self.layout.stations[-1]
        candidate = station

        with self.assertRaises(ValueError):
            self.certificate.apply_replacement(channel, station, candidate)

        self.certificate.record_no_signal(channel, candidate)
        self.certificate.apply_replacement(channel, station, candidate)
        self.assertNotIn(candidate, self.certificate.remaining(channel))


if __name__ == '__main__':
    unittest.main()
