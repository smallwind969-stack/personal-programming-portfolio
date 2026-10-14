import argparse
import socket
import sys
from datetime import datetime
from pathlib import Path

from .client import HttpTransport, SimulatorClient
from .strategy import JsonlLogger, RobotStrategy
from .score_strategy import ScoreStrategy
from .q3_action_rollout_strategy import Q3ActionRolloutStrategy
from .score_v2_strategy import ScoreV2Strategy
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
from .q4_belief_v2_strategy import Q4BeliefV2Strategy
from .q4_routefirst_strategy import Q4RouteFirstStrategy
from .q4_certified21_strategy import Q4Certified21Strategy
from .q4_enroute_strategy import Q4EnrouteStrategy
from .q4_probe_joint_strategy import Q4ProbeJointStrategy
from .q4_discovery_race_strategy import Q4DiscoveryRaceStrategy
from .q4_certified21_optimized_strategy import Q4Certified21OptimizedStrategy
from .q4_unified_strategy import Q4UnifiedStrategy
from .q4_final_strategy import Q4FinalStrategy


def port_open(host,port,timeout=0.8):
    try:
        with socket.create_connection((host,port),timeout):return True
    except OSError:return False


def main(argv=None):
    p=argparse.ArgumentParser(description='B题问题3/4机器狗程序')
    p.add_argument('--robot-id',help='当前模拟器登录的参赛队号')
    p.add_argument('--base-url',default='http://127.0.0.1:2026')
    p.add_argument('--mode',choices=('q4_certified21_optimized','q4_discovery_race','q3_action_rollout','q4_probe_joint','q4_enroute','q4_certified21','score_v2','q4_final','q3_joint_residual','q3_oracle_fusion','q3_final','q4_unified','q4_routefirst','q4_belief_v2','q4_belief','q4','q3_dynamic','joint','fusion','score','residual','sprint','adaptive','safe'),default='joint',help='q4_certified21_optimized为保持连续证书的动态路线试验；q4_discovery_race为竞速试验；q4_certified21为21站连续覆盖基线')
    p.add_argument('--route-budget',type=float,default=1.0,help='每次路径搜索的软时间预算（实秒），默认1；不计入虚拟耗时')
    p.add_argument('--risk-budget',type=float,default=.10,help='仅sprint使用：估计漏失风险上限，0为严格保证')
    p.add_argument('--q4-novelty-distance',type=float,default=350.0,help='问题4动态停靠点机会扫描的空间新颖阈值（米）')
    p.add_argument('--q4-insertion-distance',type=float,default=220.0,help='问题4发现阶段允许目标任务插队的最大增量路程（米）')
    p.add_argument('--execute',action='store_true',help='实际调用/enter并执行；省略时只检查配置')
    args=p.parse_args(argv)
    if args.route_budget <= 0:
        p.error('--route-budget must be positive')
    if not 0 <= args.risk_budget <= 1:
        p.error('--risk-budget must be between 0 and 1')
    if args.q4_novelty_distance <= 0:
        p.error('--q4-novelty-distance must be positive')
    if args.q4_insertion_distance < 0:
        p.error('--q4-insertion-distance must be nonnegative')
    if not args.execute:
        print(f'配置检查通过：mode={args.mode}, route_budget={args.route_budget:g}s。'
              '未探测接口、未调用/enter；加入 --execute 才会开始。')
        return 0
    host='127.0.0.1'; port=int(args.base_url.rsplit(':',1)[-1])
    if not port_open(host,port):
        print(f'接口未开放：{host}:{port}。请启动模拟器并选择对应问题的演练测试，等待接口就绪。')
        return 2
    if not args.robot_id:
        print('拒绝执行：必须提供 --robot-id 参赛队号。')
        return 2
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    log=JsonlLogger(Path(__file__).resolve().parent/'logs'/f'run-{stamp}.jsonl')
    client=SimulatorClient(args.robot_id,HttpTransport(args.base_url))
    if args.mode == 'q4_certified21_optimized':
        strategy = Q4Certified21OptimizedStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_discovery_race':
        strategy = Q4DiscoveryRaceStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q3_action_rollout':
        strategy = Q3ActionRolloutStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_probe_joint':
        strategy = Q4ProbeJointStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_enroute':
        strategy = Q4EnrouteStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_certified21':
        strategy = Q4Certified21Strategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_final':
        strategy = Q4FinalStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q3_joint_residual':
        strategy = Q3JointResidualStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q3_oracle_fusion':
        strategy = Q3OracleFusionStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q3_final':
        strategy = Q3FinalStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_unified':
        strategy = Q4UnifiedStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_routefirst':
        strategy = Q4RouteFirstStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_belief_v2':
        strategy = Q4BeliefV2Strategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4_belief':
        strategy = Q4BeliefStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'q4':
        strategy = Q4Strategy(
            client, log, route_budget_s=args.route_budget,
            novelty_distance_m=args.q4_novelty_distance,
            insertion_distance_m=args.q4_insertion_distance)
    elif args.mode == 'q3_dynamic':
        strategy = Q3DynamicStrategy(
            client, log, route_budget_s=args.route_budget)
    elif args.mode == 'joint':
        strategy = JointStrategy(client, log, route_budget_s=args.route_budget)
    elif args.mode == 'fusion':
        strategy = FusionStrategy(client, log, route_budget_s=args.route_budget)
    elif args.mode == 'score':
        strategy = ScoreStrategy(client, log, route_budget_s=args.route_budget)
    elif args.mode == 'score_v2':
        strategy = ScoreV2Strategy(client, log, route_budget_s=args.route_budget)
    elif args.mode == 'residual':
        strategy = ResidualStrategy(client, log, route_budget_s=args.route_budget)
    elif args.mode == 'sprint':
        strategy = SprintStrategy(client, log, route_budget_s=args.route_budget,
                                  risk_budget=args.risk_budget)
    else:
        strategy = RobotStrategy(client, log, mode=args.mode)
    summary=strategy.run()
    print(summary)
    return 0


if __name__=='__main__':sys.exit(main())
