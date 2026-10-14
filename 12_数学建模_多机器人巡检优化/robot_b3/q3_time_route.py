"""Time-aware open routing for mixed physical scan and target tasks."""

import math

from .score_routing import plan_open_route


def _channels(task):
    return tuple(dict.fromkeys(int(c) for c in task.get('channels', ())))


def _channel_options(current, required):
    required = _channels({'channels': required})
    if not required:
        return ((current, 0),)
    n = len(required)
    if n == 1:
        channel = required[0]
        return ((channel, 0 if channel == current else 1),)
    if current not in required:
        return tuple((exit_channel, n) for exit_channel in required)
    return tuple(
        (exit_channel, n if exit_channel == current else n - 1)
        for exit_channel in required
    )


def _score_order(start, current_channel, names, tasks):
    position = tuple(start)
    distance = 0.0
    measurements = sum(len(_channels(tasks[name])) for name in names)
    service = sum(float(tasks[name].get('service_s', 0.0)) for name in names)
    states = {current_channel: (0, ())}
    for name in names:
        task = tasks[name]
        point = tuple(task['position'])
        distance += math.dist(position, point)
        next_states = {}
        for entry_channel, (switches, schedule) in states.items():
            for exit_channel, added in _channel_options(entry_channel, _channels(task)):
                value = switches + added
                if exit_channel not in next_states or value < next_states[exit_channel][0]:
                    next_states[exit_channel] = (value, schedule + (exit_channel,))
        states = next_states
        position = point
    exit_channel, (switches, schedule) = min(
        states.items(), key=lambda item: (item[1][0], item[0]))
    total = distance / 5.0 + 5.0 * measurements + switches + service
    return {
        'order': list(names), 'distance_m': distance,
        'measurements': measurements, 'switches': switches,
        'service_s': service, 'total_time_s': total,
        'exit_channel': exit_channel, 'station_exit_channels': schedule,
    }


def evaluate_time_order(start, current_channel, order, tasks):
    """Evaluate a supplied physical order with optimal station channel exits."""
    return _score_order(tuple(start), int(current_channel), list(order), tasks)


def _exact(start, current_channel, tasks):
    names = list(tasks)
    n = len(names)
    states = {}
    for j, name in enumerate(names):
        task = tasks[name]
        base = (math.dist(start, task['position']) / 5.0
                + 5.0 * len(_channels(task))
                + float(task.get('service_s', 0.0)))
        for exit_channel, switches in _channel_options(current_channel, _channels(task)):
            states[(1 << j, j, exit_channel)] = (
                base + switches, (j,), switches)
    for mask in range(1, 1 << n):
        snapshot = [(key, value) for key, value in states.items()
                    if key[0] == mask]
        for (old_mask, last, channel), (cost, order, switch_count) in snapshot:
            for j, name in enumerate(names):
                if old_mask & (1 << j):
                    continue
                task = tasks[name]
                travel = math.dist(tasks[names[last]]['position'], task['position']) / 5.0
                base = travel + 5.0 * len(_channels(task)) + float(task.get('service_s', 0.0))
                for exit_channel, added in _channel_options(channel, _channels(task)):
                    key = (old_mask | (1 << j), j, exit_channel)
                    candidate = (cost + base + added, order + (j,), switch_count + added)
                    if key not in states or candidate[0] < states[key][0] - 1e-12:
                        states[key] = candidate
    full = (1 << n) - 1
    _, (cost, indices, switches) = min(
        ((key, value) for key, value in states.items() if key[0] == full),
        key=lambda item: (item[1][0], item[1][1]))
    result = _score_order(start, current_channel, [names[i] for i in indices], tasks)
    result['total_time_s'] = cost
    result['switches'] = switches
    result['proven_optimal'] = True
    return result


def _heuristic(start, current_channel, tasks, budget_s):
    names = list(tasks)
    candidates = []
    distance_incumbent = plan_open_route(
        start, {name: tuple(task['position']) for name, task in tasks.items()},
        budget_s=max(0.001, float(budget_s)))
    candidates.append(distance_incumbent['order'])
    for first in names:
        remaining = set(names)
        remaining.remove(first)
        order = [first]
        current = tuple(tasks[first]['position'])
        while remaining:
            nxt = min(remaining, key=lambda name: (
                math.dist(current, tasks[name]['position']), repr(name)))
            remaining.remove(nxt)
            order.append(nxt)
            current = tuple(tasks[nxt]['position'])
        candidates.append(order)
    best = min((_score_order(start, current_channel, order, tasks)
                for order in candidates), key=lambda item: item['total_time_s'])
    improved = True
    while improved:
        improved = False
        base_order = best['order']
        for i in range(len(base_order) - 1):
            for j in range(i + 1, len(base_order)):
                trial_order = base_order[:i] + list(reversed(base_order[i:j + 1])) + base_order[j + 1:]
                trial = _score_order(start, current_channel, trial_order, tasks)
                if trial['total_time_s'] < best['total_time_s'] - 1e-10:
                    best = trial
                    improved = True
                    break
            if improved:
                break
        if improved:
            continue
        base_order = best['order']
        for i in range(len(base_order)):
            shortened = base_order[:i] + base_order[i + 1:]
            for j in range(len(base_order)):
                trial_order = shortened[:j] + [base_order[i]] + shortened[j:]
                trial = _score_order(start, current_channel, trial_order, tasks)
                if trial['total_time_s'] < best['total_time_s'] - 1e-10:
                    best = trial
                    improved = True
                    break
            if improved:
                break
    best['proven_optimal'] = False
    best['route_incumbent_used'] = True
    return best


def plan_time_aware_open_route(start, current_channel, tasks, exact_limit=10,
                               budget_s=1.0):
    """Minimize travel, measurement, switch, and supplied service time."""
    if not tasks:
        return {
            'order': [], 'distance_m': 0.0, 'measurements': 0,
            'switches': 0, 'service_s': 0.0, 'total_time_s': 0.0,
            'exit_channel': current_channel, 'station_exit_channels': (),
            'proven_optimal': True,
        }
    if len(tasks) <= exact_limit:
        return _exact(tuple(start), int(current_channel), tasks)
    return _heuristic(tuple(start), int(current_channel), tasks, budget_s)
