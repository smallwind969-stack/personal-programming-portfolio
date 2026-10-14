"""Paired, entirely offline Q3 benchmark using the published action costs."""
import argparse
import csv
import json
import statistics
import time
from pathlib import Path

from .offline import OfflineSimulator, make_scene
from .score_strategy import ScoreStrategy
from .strategy import RobotStrategy
from .channel_strategy import ChannelCoverageStrategy
from .race_strategy import RaceStrategy
from .residual_strategy import ResidualStrategy
from .sprint_strategy import SprintStrategy
from .fusion_strategy import FusionStrategy
from .joint_strategy import JointStrategy
from .q3_dynamic_strategy import Q3DynamicStrategy
from .q3_final_strategy import Q3FinalStrategy
from .q3_oracle_fusion_strategy import Q3OracleFusionStrategy
from .q3_joint_residual_strategy import Q3JointResidualStrategy
from .q4_strategy import Q4Strategy
from .q4_belief_strategy import Q4BeliefStrategy
from .q4_routefirst_strategy import Q4RouteFirstStrategy
from .q4_unified_strategy import Q4UnifiedStrategy
from .q4_oracle import omniscient_clear_oracle, decompose_oracle_regret


class NoOpticalProbeStrategy(ScoreStrategy):
    """Ablation: retain the planner but disable unguaranteed optical attempts."""
    def _service(self, c, destination):
        self._probed.add(c)
        return super()._service(c, destination)


class FixedCoverageStrategy(ScoreStrategy):
    """Ablation: keep the original seven fixed coverage stations."""
    def _maybe_replace_scan(self, coverage):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', type=int, default=50)
    parser.add_argument('--start', type=int, default=1000)
    parser.add_argument('--route-budget', type=float, default=0.1)
    parser.add_argument('--risk-budget', type=float, default=.10)
    parser.add_argument('--oracle-time-limit', type=float, default=2.0,
                        help='每个真值场景的离线Oracle MILP时限（秒）')
    parser.add_argument('--output', default='robot_b3/results/paired-score')
    parser.add_argument('--modes', nargs='+', choices=['safe', 'adaptive', 'score', 'fusion', 'joint', 'q3_dynamic', 'q3_final', 'q3_oracle_fusion', 'q3_joint_residual', 'q4', 'q4_belief', 'q4_routefirst', 'q4_unified', 'residual', 'sprint', 'score-fixed', 'score-no-probe', 'channel', 'race'],
                        default=['safe', 'adaptive', 'score'])
    args = parser.parse_args(argv)
    rows = []
    for offset in range(args.seeds):
        seed = args.start+offset
        layout = ('uniform', 'clustered', 'boundary')[offset % 3]
        reception = 1000 if offset % 4 == 0 else None
        error_mode = 'extreme' if offset % 5 == 0 else 'uniform'
        scene = make_scene(seed, layout=layout, reception=reception)
        q4_scene = make_scene(seed, layout=layout, reception=reception,
                              directional_fraction=.5)
        scene_oracles = {}
        for mode in args.modes:
            selected_scene = q4_scene if mode in ('q4', 'q4_belief', 'q4_routefirst', 'q4_unified') else scene
            oracle_key = 'q4' if selected_scene is q4_scene else 'q3'
            if oracle_key not in scene_oracles:
                scene_oracles[oracle_key] = omniscient_clear_oracle(
                    selected_scene, time_limit_s=args.oracle_time_limit)
            oracle = scene_oracles[oracle_key]
            sim = OfflineSimulator(selected_scene, seed=seed, error_mode=error_mode)
            if mode == 'q3_joint_residual':
                strategy=Q3JointResidualStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'q3_oracle_fusion':
                strategy=Q3OracleFusionStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'q3_final':
                strategy=Q3FinalStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'q3_dynamic':
                strategy=Q3DynamicStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'q4_unified':
                strategy=Q4UnifiedStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'q4_routefirst':
                strategy=Q4RouteFirstStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'q4_belief':
                strategy=Q4BeliefStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'q4':
                strategy=Q4Strategy(sim,route_budget_s=args.route_budget)
            elif mode == 'sprint':
                strategy=SprintStrategy(sim,route_budget_s=args.route_budget,
                                        risk_budget=args.risk_budget)
            elif mode == 'residual':
                strategy=ResidualStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'race':
                strategy=RaceStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'channel':
                strategy=ChannelCoverageStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'joint':
                strategy=JointStrategy(sim,route_budget_s=args.route_budget)
            elif mode == 'fusion':
                strategy=FusionStrategy(sim,route_budget_s=args.route_budget)
            elif mode in ('score', 'score-fixed', 'score-no-probe'):
                cls = {'score': ScoreStrategy, 'score-fixed': FixedCoverageStrategy,
                       'score-no-probe': NoOpticalProbeStrategy}[mode]
                strategy = cls(sim, route_budget_s=args.route_budget)
            else:
                strategy = RobotStrategy(sim, mode=mode)
            started = time.perf_counter()
            error = ''
            try:
                strategy.run()
            except Exception as exc:
                error = repr(exc)
            costs = sim.cost_breakdown()
            regret = decompose_oracle_regret(costs, oracle)
            row = {'seed': seed, 'layout': layout, 'reception': reception or 'mixed',
                   'error_mode': error_mode, 'mode': mode, 'sources': len(scene),
                   'cleared': len(sim.cleared), **costs, **regret,
                   'real_s': time.perf_counter()-started, 'error': error}
            rows.append(row)
        if (offset+1) % 10 == 0:
            print(f'completed {offset+1}/{args.seeds} paired scenes', flush=True)
    summary = {'scenes': args.seeds, 'start_seed': args.start,
               'route_budget_s': args.route_budget, 'modes': {}}
    for mode in args.modes:
        data = [r for r in rows if r['mode'] == mode]
        summary['modes'][mode] = {
            'full_clear_runs': sum(r['cleared'] == r['sources'] and not r['error'] for r in data),
            'total_sources': sum(r['sources'] for r in data),
            'total_cleared': sum(r['cleared'] for r in data),
            'mean_total_s': statistics.mean(r['total_s'] for r in data),
            'mean_oracle_lower_bound_s': statistics.mean(
                r['oracle_lower_bound_s'] for r in data),
            'mean_oracle_regret_s': statistics.mean(
                r['total_regret_s'] for r in data),
            'mean_excess_move_s': statistics.mean(
                r['excess_move_s'] for r in data),
            'mean_measurement_regret_s': statistics.mean(
                r['measurement_regret_s'] for r in data),
            'mean_per_source_s': statistics.mean(r['total_s']/r['sources'] for r in data),
            'mean_move_s': statistics.mean(r['move_s'] for r in data),
            'mean_measures': statistics.mean(r['measures'] for r in data),
            'mean_search_measures': statistics.mean(
                r['search_measures'] for r in data),
            'mean_localization_measures': statistics.mean(
                r['localization_measures'] for r in data),
            'mean_no_signal_measures': statistics.mean(
                r['no_signal_measures'] for r in data),
            'mean_switches': statistics.mean(r['switches'] for r in data),
            'failed_clears': sum(r['failed_clears'] for r in data),
            'max_real_s': max(r['real_s'] for r in data),
            'errors': [r for r in data if r['error']],
        }
    pairs = []
    for seed in range(args.start, args.start+args.seeds):
        pair = {r['mode']: r for r in rows if r['seed'] == seed}
        if 'adaptive' in pair and 'score' in pair:
            pairs.append(pair['score']['total_s']-pair['adaptive']['total_s'])
    if pairs:
        summary['score_minus_adaptive'] = {
            'wins': sum(x < -1e-6 for x in pairs), 'ties': sum(abs(x) <= 1e-6 for x in pairs),
            'losses': sum(x > 1e-6 for x in pairs),
            'mean_delta_s': statistics.mean(pairs), 'worst_delta_s': max(pairs)}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.with_suffix('.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    output.with_suffix('.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
