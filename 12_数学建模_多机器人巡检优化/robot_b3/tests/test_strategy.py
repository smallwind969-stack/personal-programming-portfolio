import math
import unittest

from robot_b3.strategy import RobotStrategy


class FakeSimulator:
    def __init__(self):
        self.sources = {c:(650*math.cos(2*math.pi*c/10),650*math.sin(2*math.pi*c/10)) for c in range(1,11)}
        self.cleared = set(); self.current_channel=1; self.virtual_time_s=0.0; self.exited=False
        self.position=(0.0,0.0)
    def enter(self): return {'accepted':True,'remaining_real_duration_s':1200,'virtual_time_s':0}
    def _move(self,p):
        self.virtual_time_s += math.dist(self.position,p)/5.0
        self.position=p
    def measure(self,p,c):
        self._move(p)
        if c!=self.current_channel:self.virtual_time_s+=1
        self.virtual_time_s += 5; self.current_channel=c
        if c not in self.sources or c in self.cleared or math.dist(p,self.sources[c])>1500:
            return {'accepted':True,'virtual_time_s':self.virtual_time_s,'measure_result':'no_signal'}
        if math.dist(p,self.sources[c])<=5:
            return {'accepted':True,'virtual_time_s':self.virtual_time_s,'measure_result':'near'}
        g=self.sources[c]; a=math.degrees(math.atan2(g[1]-p[1],g[0]-p[0]))%360
        return {'accepted':True,'virtual_time_s':self.virtual_time_s,'measure_result':'direction','svd_deg':a}
    def clear(self,p,c):
        self._move(p)
        ok=c in self.sources and c not in self.cleared and math.dist(p,self.sources[c])<=20
        self.virtual_time_s += 5 if ok else 3
        if ok:self.cleared.add(c)
        return {'accepted':True,'virtual_time_s':self.virtual_time_s,'clear_result':'success' if ok else 'no_target_in_range'}
    def exit(self): self.exited=True; return {'accepted':True,'virtual_time_s':self.virtual_time_s,'exit_reason':'user_exit'}


class MovementSimulator(FakeSimulator):
    def __init__(self):
        super().__init__()
        self.sources={1:(570.0,0.0)}; self.position=(0.0,0.0)


class StrategyTests(unittest.TestCase):
    def test_adaptive_inserts_mature_on_route_clear(self):
        sim=FakeSimulator(); strategy=RobotStrategy(sim,mode='adaptive'); strategy.position=(0,0)
        target=sim.sources[1]
        strategy.found={1}; strategy.poly={1:[target]}; strategy.observations={1:[]}
        strategy._clear_insertions((2*target[0],2*target[1]),remaining_coverage=4)
        self.assertIn(1,sim.cleared)

    def test_safe_mode_does_not_insert_clear(self):
        sim=FakeSimulator(); strategy=RobotStrategy(sim,mode='safe'); strategy.position=(0,0)
        strategy.found={1}; strategy.poly={1:[(500,0)]}; strategy.observations={1:[]}
        strategy._clear_insertions((1000,0),remaining_coverage=4)
        self.assertNotIn(1,sim.cleared)

    def test_ready_clear_order_uses_open_route_optimizer(self):
        sim=FakeSimulator(); strategy=RobotStrategy(sim); strategy.position=(0,0)
        strategy.poly={1:[(1,0)],2:[(2,10)],3:[(3,0)]}
        order=strategy.ready_clear_order({1,2,3})
        self.assertEqual(set(order),{1,2,3})
        self.assertNotEqual(order,[1,2,3])

    def test_clears_all_full_direction_sources(self):
        sim=FakeSimulator(); summary=RobotStrategy(sim).run()
        self.assertEqual(sim.cleared,set(range(1,11)))
        self.assertTrue(sim.exited)
        self.assertEqual(summary['cleared'],10)

    def test_safe_mode_also_clears_all_sources(self):
        sim=FakeSimulator(); summary=RobotStrategy(sim,mode='safe').run()
        self.assertEqual(sim.cleared,set(range(1,11)))
        self.assertEqual(summary['cleared'],10)

    def test_adaptive_reduces_virtual_time(self):
        results={}
        for mode in ('safe','adaptive'):
            sim=MovementSimulator(); strategy=RobotStrategy(sim,mode=mode)
            strategy.found={1}; strategy.unknown.discard(1)
            strategy.poly={1:[sim.sources[1]]}; strategy.observations={1:[]}
            results[mode]=strategy.run()
            self.assertEqual(sim.cleared,{1})
            self.assertEqual(results[mode]['strategy_mode'],mode)
        self.assertLess(results['adaptive']['virtual_time_s'],results['safe']['virtual_time_s'])


if __name__=='__main__': unittest.main()
