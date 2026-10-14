from robot_b3.offline import OfflineSimulator
from robot_b3.q3_oracle_fusion_strategy import (
    Q3OracleFusionStrategy,
    optional_scan_is_better,
    replace_channel_requirements,
    select_robust_plan,
)


def test_mode_is_isolated():
    strategy = Q3OracleFusionStrategy(OfflineSimulator({}), route_budget_s=.01)
    assert strategy.mode == 'q3_oracle_fusion'


def test_physical_scan_task_merges_channels():
    strategy = Q3OracleFusionStrategy(OfflineSimulator({}), route_budget_s=.01)
    requirements = {(10.0, 20.0): {2, 7, 11}}
    tasks = strategy._time_tasks(requirements, set())
    task = next(iter(tasks.values()))
    assert task['position'] == (10.0, 20.0)
    assert task['channels'] == (2, 7, 11)


def test_optional_scan_uses_total_time_not_station_count_only():
    assert optional_scan_is_better(
        start=(0.0, 0.0), current_channel=1, channel=2,
        before=((1000.0, 0.0),), after=((10.0, 0.0),),
    )


def test_optional_scan_rejects_extra_measure_when_route_does_not_improve():
    assert not optional_scan_is_better(
        start=(0.0, 0.0), current_channel=1, channel=2,
        before=((10.0, 0.0),), after=((10.0, 0.0),),
    )


def test_route_change_requires_gain_larger_than_model_uncertainty():
    baseline = {'total_time_s': 100.0, 'order': ['baseline']}
    marginal = {'total_time_s': 96.0, 'order': ['marginal']}
    decisive = {'total_time_s': 90.0, 'order': ['decisive']}
    assert select_robust_plan(baseline, marginal, 5.0) is baseline
    assert select_robust_plan(baseline, decisive, 5.0) is decisive


def test_route_change_must_not_buy_switch_savings_with_more_travel():
    baseline = {
        'total_time_s': 100.0, 'distance_m': 400.0,
        'order': ['baseline'],
    }
    longer = {
        'total_time_s': 80.0, 'distance_m': 401.0,
        'order': ['longer'],
    }
    assert select_robust_plan(baseline, longer, 5.0) is baseline


def test_adaptive_route_change_must_preserve_geometric_incumbent():
    baseline = {
        'total_time_s': 100.0, 'distance_m': 400.0,
        'order': ['baseline'],
    }
    different = {
        'total_time_s': 80.0, 'distance_m': 399.0,
        'order': ['different'],
    }
    assert select_robust_plan(baseline, different, 5.0) is baseline


def test_replacing_one_channel_keeps_other_channel_requirements():
    requirements = {(0.0, 0.0): {1, 2}, (10.0, 0.0): {2}}
    replaced = replace_channel_requirements(
        requirements, channel=2, completion=((20.0, 0.0),))
    assert replaced == {(0.0, 0.0): {1}, (20.0, 0.0): {2}}
