import time
import unittest
from robot_b3.offline import OfflineSimulator
from robot_b3.q3_action_rollout_strategy import Q3ActionRolloutStrategy


class ActionRolloutTests(unittest.TestCase):
    def strategy(self):
        s=Q3ActionRolloutStrategy(OfflineSimulator({}),route_budget_s=.01)
        s.started=time.monotonic();s.deadline=s.started+1200
        return s

    def test_world_respects_known_negative_reception(self):
        s=self.strategy()
        for c in range(1,21): s.negative_stations[c]=[(0,0)]
        world=s._sample_world(9)
        self.assertIsNotNone(world)
        self.assertTrue(10<=len(world)<=16)
        import math
        self.assertTrue(all(math.hypot(*p)>r for p,r in world.values()))

    def test_shadow_reuses_historical_bearing(self):
        s=self.strategy()
        s.observations={1:[((0,0),.5)]}
        _,sim=s._shadow({1:((100,0),1000)},123)
        self.assertEqual(sim.measure((0,0),1)['svd_deg'],.5)
        self.assertEqual(s.client.measures,0)

    def test_shadow_has_independent_mutable_state(self):
        s=self.strategy();s.found={1};s.poly={1:[(100,0)]}
        child,_=s._shadow({1:((100,0),1000)},1)
        child.poly[1].append((100,1));child.cleared.add(1)
        self.assertEqual(s.poly[1],[(100,0)])
        self.assertEqual(s.cleared,set())

    def test_deadline_falls_back_to_route_incumbent(self):
        s=self.strategy();s.deadline=time.monotonic()+20
        tasks={('scan',1):(0,0),('target',1):(100,0)}
        result=s._select_task({'order':list(tasks)},tasks,{('scan',1):(0,0)})
        self.assertEqual(result,(('scan',1),(100,0)))
