from robot_b3.q3_time_route import plan_time_aware_open_route


def test_channel_carry_can_outweigh_shortest_distance_order():
    tasks = {
        'near': {'position': (1.0, 0.0), 'channels': (2,)},
        'far': {'position': (0.0, 2.0), 'channels': (1,)},
    }
    result = plan_time_aware_open_route((0.0, 0.0), 1, tasks)
    assert result['order'] == ['far', 'near']
    assert result['switches'] == 1
    assert result['measurements'] == 2


def test_route_keeps_scan_and_target_tasks_and_open_end():
    tasks = {
        ('scan', 0): {'position': (10.0, 0.0), 'channels': (1, 2)},
        ('target', 7): {'position': (20.0, 0.0), 'channels': ()},
        ('scan', 1): {'position': (30.0, 0.0), 'channels': (3,)},
    }
    result = plan_time_aware_open_route((0.0, 0.0), 1, tasks)
    assert set(result['order']) == set(tasks)
    assert result['order'][-1] == ('scan', 1)
    assert result['distance_m'] == 30.0
    assert result['measurements'] == 3


def test_large_route_accepts_search_budget_for_strong_incumbent():
    tasks = {
        i: {'position': (float(i), float((i * 7) % 5)), 'channels': ((i % 3) + 1,)}
        for i in range(12)
    }
    result = plan_time_aware_open_route(
        (0.0, 0.0), 1, tasks, exact_limit=5, budget_s=.02)
    assert set(result['order']) == set(tasks)
    assert result['route_incumbent_used']
