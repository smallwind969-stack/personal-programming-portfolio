from robot_b3.offline import OfflineSimulator
from robot_b3.q3_joint_residual_planner import (
    plan_joint_residual, select_dominating_plan)
from robot_b3.q3_joint_residual_strategy import Q3JointResidualStrategy
from robot_b3.residual_strategy import ResidualStrategy


def test_strategy_inherits_per_channel_residual_state():
    strategy = Q3JointResidualStrategy(OfflineSimulator({}), route_budget_s=.01)
    assert isinstance(strategy, ResidualStrategy)
    assert strategy.mode == 'q3_joint_residual'


def test_joint_plan_merges_channels_at_same_physical_station():
    plan = plan_joint_residual(
        (0.0, 0.0), 1,
        {(100.0, 0.0): {2, 3}}, {}, budget_s=.01)
    task = next(iter(plan['tasks'].values()))
    assert task['channels'] == (2, 3)
    assert plan['measurements'] == 2


def test_joint_plan_selects_second_point_together_with_route():
    variants = {
        7: [
            {'position': (1000.0, 0.0), 'predicted_radius': 10.0},
            {'position': (100.0, 0.0), 'predicted_radius': 10.0},
        ]
    }
    plan = plan_joint_residual(
        (0.0, 0.0), 1, {}, variants, budget_s=.01)
    assert plan['selected_variants'][7]['position'] == (100.0, 0.0)


def test_shorter_route_cannot_buy_worse_localization_radius():
    variants = {
        7: [
            {'position': (1000.0, 0.0), 'predicted_radius': 10.0},
            {'position': (100.0, 0.0), 'predicted_radius': 11.0},
        ]
    }
    plan = plan_joint_residual(
        (0.0, 0.0), 1, {}, variants, budget_s=.01)
    assert plan['selected_variants'][7]['position'] == (1000.0, 0.0)


def test_nonterminal_radius_reduction_does_not_replace_proven_baseline():
    variants = {
        7: [
            {'position': (1000.0, 0.0), 'predicted_radius': 30.0},
            {'position': (100.0, 0.0), 'predicted_radius': 20.0},
        ]
    }
    plan = plan_joint_residual(
        (0.0, 0.0), 1, {}, variants, budget_s=.01)
    assert plan['selected_variants'][7]['position'] == (1000.0, 0.0)


def test_target_at_clear_radius_is_a_clear_not_measure_task():
    plan = plan_joint_residual(
        (0.0, 0.0), 1, {},
        {4: [{'position': (20.0, 0.0), 'action': 'clear',
              'predicted_radius': 0.0}]}, budget_s=.01)
    task = next(iter(plan['tasks'].values()))
    assert task['channels'] == ()
    assert task['service_s'] == 5.0
    assert task['target_actions'] == ((4, 'clear'),)


def test_measure_task_prices_return_to_target_region():
    plan = plan_joint_residual(
        (0.0, 0.0), 1, {},
        {4: [{'position': (20.0, 0.0), 'action': 'measure',
              'predicted_radius': 19.5, 'return_distance': 50.0}]},
        budget_s=.01)
    task = next(iter(plan['tasks'].values()))
    assert task['terminal_proxy_s'] == 10.0


def test_dynamic_certificate_replacement_cannot_lengthen_route():
    baseline = {'distance_m': 100.0, 'total_time_s': 30.0}
    detour = {'distance_m': 101.0, 'total_time_s': 29.0}
    assert select_dominating_plan(baseline, detour) is baseline
