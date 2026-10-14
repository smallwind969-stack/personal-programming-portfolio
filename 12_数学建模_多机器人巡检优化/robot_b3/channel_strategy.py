"""Per-channel certified coverage combined with rolling target service."""
import itertools
import math
import time

from .coverage import farthest_uncovered
from .geometry import bearing_least_squares, seven_points
from .score_routing import plan_open_route
from .score_strategy import ScoreStrategy


class ChannelCoverageStrategy(ScoreStrategy):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.mode='channel'
        self.fixed_points=seven_points(1123.0)
        self.search_remaining={c:set(range(7)) for c in range(1,21)}
        self.search_scanned={c:[] for c in range(1,21)}

    def _record_search(self,c,q,result,removed):
        if c not in self.search_remaining:return
        if result in ('direction','near') or c not in self.unknown:
            self.search_remaining.pop(c,None);self.search_scanned.pop(c,None);return
        self.search_scanned[c].append(tuple(q))
        self.search_remaining[c].difference_update(removed)
        if not self.search_remaining[c]:
            self.absent.add(c);self.unknown.discard(c)

    def _scan_channels(self,q,channels,removed_by_channel):
        channels=list(dict.fromkeys(channels))
        if self.client.current_channel in channels:
            channels.remove(self.client.current_channel);channels.insert(0,self.client.current_channel)
        touched_unknown=False
        for c in channels:
            if not self._time_ok() or c in self.cleared:continue
            was_unknown=c in self.unknown
            result=self._measure(q,c)
            if was_unknown:
                touched_unknown=True
                self._record_search(c,q,result,removed_by_channel.get(c,set()))
        if touched_unknown:
            q=tuple(q)
            if q not in self.scan_stations:self.scan_stations.append(q)
            self.coverage_stations=len(self.scan_stations)
        self._guaranteed_here()

    def _fixed_scan(self,index):
        q=self.fixed_points[index]
        unknown=[c for c in self.unknown if index in self.search_remaining.get(c,set())]
        known=[c for c in self.found-self.cleared if self._useful_bearing(c,q)]
        removed={c:{index} for c in unknown}
        self._scan_channels(q,unknown+known,removed)

    def _replacement(self,c,q):
        remaining=self.search_remaining[c]
        keys=list(remaining)
        for count in range(len(keys),0,-1):
            best=None
            for removed in itertools.combinations(keys,count):
                future=[self.fixed_points[i] for i in remaining if i not in removed]
                stations=self.search_scanned[c]+[tuple(q)]+future
                _,radius=farthest_uncovered(stations)
                if radius<=1000+1e-7:
                    saving=sum(math.dist(q,self.fixed_points[i]) for i in removed)
                    if best is None or saving>best[0]:best=(saving,set(removed))
            if best is not None:return best[1]
        return set()

    def _opportunistic_search(self,q):
        removed={}
        for c in sorted(self.unknown):
            choice=self._replacement(c,q)
            if choice:removed[c]=choice
        if removed:self._scan_channels(q,removed,removed)

    def run(self):
        entered=self.client.enter();self._log('enter',response=entered,strategy_mode=self.mode)
        self.started=time.monotonic();self.deadline=self.started+float(entered['remaining_real_duration_s'])
        self.position=(0.0,0.0);discovery_complete=False
        try:
            self._fixed_scan(0)
            while self._time_ok():
                if not self.unknown:
                    discovery_complete=True
                pending=self.found-self.cleared
                if discovery_complete and not pending:break
                needed={i for c in self.unknown for i in self.search_remaining[c]}
                tasks={('scan',i):self.fixed_points[i] for i in needed}
                for c in sorted(pending):
                    tasks[('target',c)]=self._circle(c)[0]
                if not tasks:break
                available=max(0,self.deadline-time.monotonic()-self.deadline_margin_s)
                plan=plan_open_route(self.position,tasks,min(self.route_budget_s,available/20))
                self._log('plan',**plan)
                key=plan['order'][0]
                destination=tasks[plan['order'][1]] if len(plan['order'])>1 else None
                if key[0]=='scan':self._fixed_scan(key[1])
                else:
                    self._service(key[1],destination)
                    self._opportunistic_search(self.position)
            response=self.client.exit();self._log('exit',response=response)
            return {'strategy_mode':self.mode,'found':len(self.found),'cleared':len(self.cleared),
                    'unknown_channels':sorted(self.unknown),'absent_channels':sorted(self.absent),
                    'discovery_complete':discovery_complete,'coverage_stations':self.coverage_stations,
                    'virtual_time_s':response.get('virtual_time_s')}
        except Exception as exc:
            self._log('fatal',error=repr(exc))
            try:self.client.exit()
            except Exception:pass
            raise
