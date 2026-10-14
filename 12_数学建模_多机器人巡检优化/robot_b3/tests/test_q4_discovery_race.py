import importlib.util
from robot_b3.offline import OfflineSimulator


def strategy():
    assert importlib.util.find_spec('robot_b3.q4_discovery_race_strategy') is not None
    from robot_b3.q4_discovery_race_strategy import Q4DiscoveryRaceStrategy
    return Q4DiscoveryRaceStrategy(OfflineSimulator({}), route_budget_s=.01)


def test_reordering_preserves_all_tasks_and_unknown_channels():
    s = strategy()
    tasks = {('certificate', 0): (0., 0.), ('certificate', 1): (995., 0.),
             ('target', 1): (200., 0.)}
    coverage = {k: q for k, q in tasks.items() if k[0] == 'certificate'}
    original = dict(coverage)
    unknown = set(s.unknown)
    order, returned = s._refine_action_plan(list(tasks), tasks, coverage)
    assert set(order) == set(tasks) and len(order) == len(tasks)
    assert returned == tasks and coverage == original and s.unknown == unknown
    assert s._scheduled_key(order, tasks, coverage) == order[0]


def test_no_unknown_keeps_service_order():
    s = strategy()
    s.unknown.clear()
    tasks = {('target', 2): (100., 0.), ('target', 1): (200., 0.)}
    order, _ = s._refine_action_plan(list(tasks), tasks, {})
    assert order == list(tasks)


def test_same_certified_layout():
    s = strategy()
    layout = s._build_fallback_layout()
    assert len(layout.stations) == 21
    assert layout.route_distance_m > 17000
