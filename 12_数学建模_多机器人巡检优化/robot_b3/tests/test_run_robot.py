import unittest
from unittest.mock import patch

from robot_b3 import run_robot


class RunRobotTests(unittest.TestCase):
    def setUp(self):
        # A regression test must never accidentally enter a real simulator.
        guard=patch('urllib.request.urlopen',side_effect=AssertionError('network forbidden in CLI tests'))
        guard.start()
        self.addCleanup(guard.stop)

    def _run_and_capture_mode(self,extra_args):
        captured=[]
        class FakeStrategy:
            def __init__(self,client,logger,mode=None): captured.append(mode)
            def run(self): return {'cleared':0}
        with patch.object(run_robot,'port_open',return_value=True), \
             patch.object(run_robot,'RobotStrategy',FakeStrategy):
            code=run_robot.main(['--robot-id','202613002010','--execute',*extra_args])
        self.assertEqual(code,0)
        return captured[0]

    def test_explicit_adaptive_mode_is_forwarded(self):
        self.assertEqual(self._run_and_capture_mode(['--mode','adaptive']),'adaptive')

    def test_default_uses_joint_q3_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'JointStrategy', create=True) as strategy, \
             patch.object(run_robot, 'RobotStrategy'), \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            run_robot.main(['--robot-id', '202613002010', '--execute'])
            strategy.assert_called_once()

    def test_explicit_score_mode_still_uses_baseline_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'ScoreStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main(['--robot-id', '202613002010', '--mode', 'score', '--execute'])
            self.assertEqual(code, 0)
            strategy.assert_called_once()

    def test_residual_mode_uses_residual_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'ResidualStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main(['--robot-id', '202613002010', '--mode', 'residual', '--execute'])
            self.assertEqual(code, 0)
            strategy.assert_called_once()

    def test_q3_dynamic_mode_uses_dynamic_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q3DynamicStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main([
                '--robot-id', '202613002010', '--mode', 'q3_dynamic',
                '--route-budget', '2', '--execute',
            ])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], 2)

    def test_q3_final_mode_uses_final_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q3FinalStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main([
                '--robot-id', '202613002010', '--mode', 'q3_final',
                '--route-budget', '2', '--execute',
            ])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], 2)

    def test_q3_oracle_fusion_mode_uses_fused_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q3OracleFusionStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main([
                '--robot-id', '202613002010', '--mode', 'q3_oracle_fusion',
                '--route-budget', '2', '--execute',
            ])
            self.assertEqual(code, 0)
            strategy.assert_called_once()

    def test_q3_joint_residual_mode_uses_joint_residual_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q3JointResidualStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {}
            code = run_robot.main([
                '--robot-id', '202613002010', '--mode', 'q3_joint_residual',
                '--route-budget', '2', '--execute'])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], 2)

    def test_sprint_mode_forwards_explicit_risk_budget(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'SprintStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main(['--robot-id', '202613002010', '--mode', 'sprint',
                                   '--risk-budget', '.25', '--execute'])
            self.assertEqual(code, 0)
            self.assertEqual(strategy.call_args.kwargs['risk_budget'], .25)

    def test_q4_mode_uses_full_view_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q4Strategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main(['--robot-id', '202613002010', '--mode', 'q4',
                                   '--route-budget', '.5', '--execute'])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], .5)

    def test_q4_belief_mode_uses_independent_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q4BeliefStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main(['--robot-id', '202613002010', '--mode', 'q4_belief',
                                   '--route-budget', '2', '--execute'])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], 2)

    def test_q4_routefirst_mode_uses_route_first_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q4RouteFirstStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main([
                '--robot-id', '202613002010', '--mode', 'q4_routefirst',
                '--route-budget', '2', '--execute',
            ])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], 2)

    def test_q4_unified_mode_uses_unified_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q4UnifiedStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main([
                '--robot-id', '202613002010', '--mode', 'q4_unified',
                '--route-budget', '2', '--execute',
            ])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], 2)

    def test_q4_final_mode_uses_final_planner(self):
        with patch.object(run_robot, 'port_open', return_value=True), \
             patch.object(run_robot, 'Q4FinalStrategy', create=True) as strategy, \
             patch.object(run_robot, 'SimulatorClient'):
            strategy.return_value.run.return_value = {'cleared': 0}
            code = run_robot.main([
                '--robot-id', '202613002010', '--mode', 'q4_final',
                '--route-budget', '2', '--execute',
            ])
            self.assertEqual(code, 0)
            strategy.assert_called_once()
            self.assertEqual(strategy.call_args.kwargs['route_budget_s'], 2)

    def test_check_mode_does_not_construct_or_enter_strategy(self):
        with patch.object(run_robot, 'port_open', side_effect=AssertionError('offline check must not probe the port')), \
             patch.object(run_robot, 'ScoreStrategy', create=True) as strategy:
            self.assertEqual(run_robot.main([]), 0)
            strategy.assert_not_called()

    def test_safe_mode_is_forwarded(self):
        self.assertEqual(self._run_and_capture_mode(['--mode','safe']),'safe')


if __name__=='__main__': unittest.main()
