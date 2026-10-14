import importlib.util
import unittest
from robot_b3.q4_belief import SourceParticle
from robot_b3.offline import OfflineSimulator


class ProbeJointTests(unittest.TestCase):
    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('robot_b3.q4_probe_joint_strategy'))
        from robot_b3 import q4_probe_joint_strategy
        return q4_probe_joint_strategy

    def test_switch_is_charged_exactly_once(self):
        f = self.module().expected_probe_cost
        poly = [(99,-1),(101,-1),(101,1),(99,1)]
        particles = [SourceParticle(100,0,1000,None,1)]
        a = f((0,0),(50,20),poly,particles,(200,0),False)
        b = f((0,0),(50,20),poly,particles,(200,0),True)
        self.assertAlmostEqual(b-a, 1)

    def test_onward_endpoint_changes_cost(self):
        f = self.module().expected_probe_cost
        poly = [(99,-1),(101,-1),(101,1),(99,1)]
        particles = [SourceParticle(100,0,1000,None,1)]
        a = f((0,0),(50,20),poly,particles,(100,0),False)
        b = f((0,0),(50,20),poly,particles,(1100,0),False)
        self.assertGreater(b, a+190)

    def test_evaluation_does_not_modify_polygon_or_particles(self):
        f = self.module().expected_probe_cost
        poly = [(0,-10),(500,-10),(500,10),(0,10)]
        particles = [SourceParticle(250,0,1000,0.,1)]
        snapshot = list(poly), list(particles)
        f((0,0),(100,100),poly,particles,None,False)
        self.assertEqual((poly, particles), snapshot)

    def test_service_executes_exact_scored_probe(self):
        cls = self.module().Q4ProbeJointStrategy
        sim = OfflineSimulator({1: ((1000,0),1500)})
        s = cls(sim)
        s._time_ok = lambda: True
        s.found = {1}
        s.unknown.discard(1)
        s.poly = {1: [(990,-30),(1010,-30),(1010,30),(990,30)]}
        s.observations = {1: [((0,0),0.)]}
        probes = list(s._probe_queue(1))
        tasks = {('target',1): probes[0], ('certificate',0): (1500,0)}
        order, tasks = s._refine_action_plan(list(tasks), tasks, {})
        selected = tasks[('target',1)]
        self.assertIn(selected, probes)
        s._service_one(1, (1500,0), 1)
        self.assertEqual(sim.actions[0], ('measure', selected, 1))
        self.assertEqual(s._probe_attempts[1], 1)

    def test_near_branch_counts_measure_clear_and_onward_travel(self):
        f = self.module().expected_probe_cost
        poly = [(99,-1),(101,-1),(101,1),(99,1)]
        p = SourceParticle(100,0,1000,None,1)
        self.assertAlmostEqual(f((0,0),(100,0),poly,[p],(200,0),False),50)

    def test_empty_belief_cannot_produce_artificial_zero_cost(self):
        import math
        f = self.module().expected_probe_cost
        self.assertEqual(f((0,0),(100,0),[(100,0)],[],None,False),math.inf)

    def test_empty_scene_preserves_21_station_search(self):
        sim = OfflineSimulator({})
        s = self.module().Q4ProbeJointStrategy(sim,route_budget_s=.01)
        result = s.run()
        self.assertTrue(result['discovery_complete'])
        self.assertEqual(len(result['absent_channels']),20)
        self.assertEqual(sim.measures,420)
        self.assertAlmostEqual(sim.moves_m,17808.42897191402)
