import math
import unittest


class RaceTests(unittest.TestCase):
    def test_posterior_cloud_localizes_crossing_bearings(self):
        from robot_b3.posterior import posterior_cloud, best_clear_disk
        observations=[((-600,0),0.4),((0,-600),89.6)]
        cloud=posterior_cloud(observations,[],[])
        center,probability=best_clear_disk(cloud)
        self.assertLess(math.dist(center,(0,0)),15)
        self.assertGreater(probability,.5)

    def test_no_signal_rejects_candidate_inside_guaranteed_1000_disk(self):
        from robot_b3.posterior import compatible_reception
        self.assertFalse(compatible_reception((0,0),[(900,0)],[(500,0)]))
        self.assertTrue(compatible_reception((0,0),[(900,0)],[(1200,0)]))

    def test_failed_clear_excludes_its_twenty_meter_disk(self):
        from robot_b3.posterior import posterior_cloud
        observations=[((-1500,0),0),((0,-1500),90)]
        cloud=posterior_cloud(observations,[],[(0,0)])
        self.assertTrue(cloud)
        self.assertTrue(all(math.dist(p,(0,0))>20 for p in cloud))

    def test_race_mode_full_clear_from_zero(self):
        from robot_b3.offline import OfflineSimulator,make_scene
        from robot_b3.race_strategy import RaceStrategy
        scene=make_scene(321,count=10)
        sim=OfflineSimulator(scene,seed=321)
        result=RaceStrategy(sim,route_budget_s=.02).run()
        self.assertEqual(result['cleared'],10)
        self.assertTrue(result['discovery_complete'])


if __name__=='__main__':unittest.main()
