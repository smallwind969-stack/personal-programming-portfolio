"""Task selection by common-scenario completion-time rollout for Q3."""
import copy
import math
import random
import time

from .offline import OfflineSimulator
from .score_strategy import ScoreStrategy
from .score_routing import plan_open_route


def polygon_sample(polygon, rng):
    if len(polygon) < 3:
        t = rng.random()
        return tuple((1-t)*a+t*b for a,b in zip(polygon[0],polygon[-1]))
    origin = polygon[0]
    triangles, weights = [], []
    for a,b in zip(polygon[1:-1],polygon[2:]):
        area = abs((a[0]-origin[0])*(b[1]-origin[1])-(a[1]-origin[1])*(b[0]-origin[0]))
        triangles.append((a,b)); weights.append(area)
    if sum(weights) <= 1e-12:
        return polygon[0]
    a,b = rng.choices(triangles,weights=weights,k=1)[0]
    u,v = math.sqrt(rng.random()),rng.random()
    return ((1-u)*origin[0]+u*(1-v)*a[0]+u*v*b[0],
            (1-u)*origin[1]+u*(1-v)*a[1]+u*v*b[1])


class Q3ActionRolloutStrategy(ScoreStrategy):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.mode='q3_action_rollout'
        self.negative_stations={c:[] for c in range(1,21)}
        self.rollout_rounds=0
        self.changed_tasks=0
        self.rollout_evaluations=0

    def _measure(self,q,c):
        result=super()._measure(q,c)
        if result=='no_signal' and c not in self.cleared:
            self.negative_stations[c].append(tuple(q))
        return result

    def _sample_world(self,seed):
        rng=random.Random(seed)
        count=rng.randint(max(10,len(self.found)),16)
        unknown=sorted(self.unknown)
        extra=min(len(unknown),max(0,count-len(self.found)))
        selected=sorted(self.found-self.cleared)+rng.sample(unknown,extra)
        world={}
        for c in selected:
            for _ in range(1200):
                if c in self.found:
                    p=polygon_sample(self.poly[c],rng)
                else:
                    a=rng.random()*2*math.pi; r=1800*math.sqrt(rng.random())
                    p=(r*math.cos(a),r*math.sin(a))
                if math.hypot(*p)>1800:
                    continue
                distances=[math.dist(p,s) for s,_ in self.observations.get(c,())]
                lo=max([1000.]+distances)
                hi=min([1500.]+[math.dist(p,s)-1e-6 for s in self.negative_stations[c]])
                if lo>hi or any(d<=5 for d in distances):
                    continue
                valid=True
                for s,theta in self.observations.get(c,()):
                    angle=math.degrees(math.atan2(p[1]-s[1],p[0]-s[0]))
                    if abs((angle-theta+180)%360-180)>1.00000002:
                        valid=False; break
                if valid:
                    world[c]=(p,rng.uniform(lo,hi)); break
            else:
                # Sampling failure is not evidence that an unknown source is absent.
                return None
        return world

    def _shadow(self,world,seed):
        sim=OfflineSimulator(world,seed=seed,max_actions=1500)
        sim.position=self.position
        sim.current_channel=self.client.current_channel
        sim.cleared=set(self.cleared)
        sim._discovered_channels=set(self.found)
        previous_angles={(tuple(q),c):theta for c,observations in self.observations.items()
                         for q,theta in observations}
        measure=sim.measure
        def consistent_measure(q,c):
            result=measure(q,c)
            if result['measure_result']=='direction' and (tuple(q),c) in previous_angles:
                result['svd_deg']=previous_angles[(tuple(q),c)]
            return result
        sim.measure=consistent_measure
        shadow=ScoreStrategy(sim,route_budget_s=.001)
        for name in ('position','found','cleared','unknown','absent','poly','observations',
                     '_circles','_measured','_probed','scan_stations','coverage_stations'):
            setattr(shadow,name,copy.deepcopy(getattr(self,name)))
        shadow.started=time.monotonic()
        shadow.deadline=shadow.started+1200
        return shadow,sim

    def _rollout_cost(self,world,seed,key,tasks,coverage):
        s,sim=self._shadow(world,seed)
        remaining=dict(coverage)
        next_tasks={k:q for k,q in tasks.items() if k!=key}
        tail=plan_open_route(tasks[key],next_tasks,0.)['order']
        destination=next_tasks[tail[0]] if tail else None
        def execute(k,points,dest):
            if k[0]=='scan':
                s._scan(points[k]); remaining.pop(k,None)
            else:
                s._service(k[1],dest)
                s._maybe_replace_scan(remaining)
        try:
            execute(key,tasks,destination)
            for _ in range(100):
                if time.monotonic()>=self.deadline-self.deadline_margin_s:
                    return math.inf
                if not s.unknown or not remaining:
                    s.absent.update(s.unknown); s.unknown.clear()
                pending=s.found-s.cleared
                if not pending and not s.unknown:
                    return sim.virtual_time_s
                points=dict(remaining) if s.unknown else {}
                points.update({('target',c):s._task_point(c) for c in sorted(pending)})
                if not points:
                    return math.inf
                order=plan_open_route(s.position,points,0.)['order']
                dest=points[order[1]] if len(order)>1 else None
                execute(order[0],points,dest)
        except (RuntimeError,ValueError):
            return math.inf
        return math.inf

    def _select_task(self,plan,tasks,coverage):
        baseline=plan['order'][0]
        # Keep the route incumbent plus representatives of both task classes.
        candidates=[]
        for kind in ('scan','target'):
            candidates.extend([k for k in plan['order'] if k[0]==kind][:2])
        if len(candidates)<2 or self.deadline-time.monotonic()<120:
            return super()._select_task(plan,tasks,coverage)
        self.rollout_rounds+=1
        worlds=[]
        for j in range(2):
            seed=930000+17*self.rollout_rounds+j
            world=self._sample_world(seed)
            if world is not None: worlds.append((world,seed))
        if not worlds:
            return super()._select_task(plan,tasks,coverage)
        scores=[]
        for key in candidates:
            if self.deadline-time.monotonic()<60:
                return super()._select_task(plan,tasks,coverage)
            costs=[self._rollout_cost(w,seed,key,tasks,coverage) for w,seed in worlds]
            self.rollout_evaluations+=len(costs)
            if all(math.isfinite(v) for v in costs): scores.append((sum(costs)/len(costs),key))
        if not scores or baseline not in [k for _,k in scores]:
            return super()._select_task(plan,tasks,coverage)
        value,key=min(scores,key=lambda item:(item[0],item[1]!=baseline,item[1]))
        self.changed_tasks+=int(key!=baseline)
        others={k:q for k,q in tasks.items() if k!=key}
        order=plan_open_route(tasks[key],others,0.)['order']
        destination=others[order[0]] if order else None
        self._log('action_rollout',selected=key,baseline=baseline,expected_remaining_s=value,
                  worlds=len(worlds),scores=[{'task':k,'seconds':v} for v,k in scores])
        return key,destination

    def run(self):
        result=super().run()
        result.update(changed_tasks=self.changed_tasks,rollout_evaluations=self.rollout_evaluations)
        return result
