"""Joint physical-task planner for per-channel residual Q3 search."""

from .q3_oracle_fusion_strategy import select_robust_plan
from .q3_time_route import evaluate_time_order, plan_time_aware_open_route
from .score_routing import plan_open_route


def select_dominating_plan(baseline, candidate):
    """Accept a structural change only when no modeled cost is worsened."""
    if (candidate['distance_m'] <= baseline['distance_m']+1e-7 and
            candidate['total_time_s'] <= baseline['total_time_s']+1e-9):
        return candidate
    return baseline


def _point_key(q):
    return round(q[0], 7), round(q[1], 7)


def _assemble(requirements, selected):
    physical = {}

    def task_at(q):
        key = _point_key(q)
        return physical.setdefault(key, {
            'position': tuple(q), 'channels': set(), 'service_s': 0.0,
            'target_actions': [], 'terminal_proxy_s': 0.0,
        })

    for q, channels in requirements.items():
        task_at(q)['channels'].update(channels)
    for channel, variant in selected.items():
        task = task_at(variant['position'])
        action = variant.get('action', 'measure')
        task['target_actions'].append((int(channel), action))
        if action == 'clear':
            task['service_s'] += 5.0
        else:
            task['channels'].add(int(channel))
            proxy = (
                max(0.0, float(variant.get('predicted_radius', 19.5))-19.5)
                + max(0.0, float(variant.get('return_distance', 0.0))))/5.0
            task['service_s'] += proxy
            task['terminal_proxy_s'] += proxy
    tasks = {}
    for i, task in enumerate(physical.values()):
        task['channels'] = tuple(sorted(task['channels']))
        task['target_actions'] = tuple(sorted(task['target_actions']))
        tasks[('physical', i, task['position'])] = task
    return tasks


def _evaluate(start, current_channel, requirements, selected, budget_s):
    tasks = _assemble(requirements, selected)
    candidate = plan_time_aware_open_route(
        start, current_channel, tasks, budget_s=budget_s)
    distance = plan_open_route(
        start, {name: task['position'] for name, task in tasks.items()},
        budget_s)
    baseline = evaluate_time_order(
        start, current_channel, distance['order'], tasks)
    baseline['proven_optimal'] = distance['proven_optimal']
    plan = select_robust_plan(
        baseline, candidate, max(8.0, .01*baseline['total_time_s']))
    plan['tasks'] = tasks
    plan['selected_variants'] = dict(selected)
    return plan


def plan_joint_residual(start, current_channel, requirements, target_variants,
                        budget_s=1.0):
    """Coordinate-descent target choices inside one command-time route model."""
    selected = {}
    for channel, variants in target_variants.items():
        if not variants:
            continue
        selected[channel] = variants[0]
    best = _evaluate(start, current_channel, requirements, selected, budget_s)
    for _ in range(2):
        changed = False
        for channel, variants in target_variants.items():
            incumbent = selected.get(channel)
            candidates = []
            for variant in variants:
                if (variant is not incumbent and
                        variant.get('predicted_radius', 19.5) > 19.5+1e-9):
                    continue
                if (incumbent is not None and
                        variant.get('predicted_radius', 19.5)
                        > incumbent.get('predicted_radius', 19.5)+1e-9):
                    continue
                trial = dict(selected)
                trial[channel] = variant
                candidate = _evaluate(
                    start, current_channel, requirements, trial,
                    max(.001, budget_s/max(1, len(variants))))
                if candidate['distance_m'] <= best['distance_m']+1e-7:
                    candidates.append(candidate)
            if not candidates:
                continue
            candidate = min(candidates, key=lambda p: p['total_time_s'])
            if candidate['total_time_s'] < best['total_time_s']-1e-9:
                selected = candidate['selected_variants']
                best = candidate
                changed = incumbent != selected.get(channel)
        if not changed:
            break
    return best
