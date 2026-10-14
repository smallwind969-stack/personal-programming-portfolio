import json
import math
import time
from pathlib import Path

from .geometry import arena_polygon, bearing_clip, enclosing_circle, seven_points
from .routing import optimal_open_route, select_clear_insertion


class JsonlLogger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
    def write(self, event, **data):
        record = {'real_time':time.time(),'event':event,**data}
        with self.path.open('a',encoding='utf-8') as f:
            f.write(json.dumps(record,ensure_ascii=False)+'\n')


class RobotStrategy:
    def __init__(self, client, logger=None, deadline_margin_s=20, mode='adaptive'):
        if mode not in ('adaptive','safe'):
            raise ValueError("mode must be 'adaptive' or 'safe'")
        self.client=client; self.logger=logger; self.deadline_margin_s=deadline_margin_s
        self.mode=mode
        self.poly={}; self.observations={}; self.found=set(); self.cleared=set(); self.unknown=set(range(1,21))
        self.started=None; self.deadline=None

    def _log(self,event,**data):
        if self.logger:self.logger.write(event,**data)

    def _time_ok(self):
        return self.deadline is None or time.monotonic() < self.deadline-self.deadline_margin_s

    def _measure(self,q,c):
        response=self.client.measure(q,c); self._log('measure',position=q,channel=c,response=response)
        result=response['measure_result']
        if result in ('direction','near'):
            self.found.add(c); self.unknown.discard(c)
            self.poly.setdefault(c,arena_polygon())
            self.observations.setdefault(c,[])
        if result=='direction':
            theta=float(response['svd_deg'])
            self.observations[c].append((q,theta))
            self.poly[c]=bearing_clip(self.poly[c],q,theta,1.0)
        elif result=='near':
            self._clear(q,c)
        return result

    def _clear(self,q,c):
        response=self.client.clear(q,c); self._log('clear',position=q,channel=c,response=response)
        if response['clear_result']=='success':self.cleared.add(c)
        return response['clear_result']=='success'

    def _circle(self,c):
        return enclosing_circle(self.poly[c])

    def ready_clear_order(self,channels):
        points={c:self._circle(c)[0] for c in channels}
        return optimal_open_route(self.position,points)[0]

    def _mature_points(self):
        return {
            c:self._circle(c)[0]
            for c in self.found-self.cleared
            if self._circle(c)[1]<=19.5
        }

    def _adaptive_detour_limit(self,remaining_coverage):
        return 120.0+40.0*max(0,6-remaining_coverage)

    def _clear_insertions(self,next_coverage_point,remaining_coverage):
        if self.mode!='adaptive':return
        while self._time_ok():
            try:
                points=self._mature_points()
                order=select_clear_insertion(
                    self.position,next_coverage_point,points,set(points),
                    self._adaptive_detour_limit(remaining_coverage),160.0
                )
            except Exception as exc:
                self._log('adaptive_skip',error=repr(exc)); return
            if not order:return
            progressed=False
            for c in order:
                if c in self.cleared or not self._time_ok():continue
                center,radius=self._circle(c)
                if radius<=19.5 and self._clear(center,c):
                    self.position=center; progressed=True
            if not progressed:return

    def _targeted_point(self,c):
        center,radius=self._circle(c)
        obs=self.observations[c]
        if len(obs)==1:
            s,deg=obs[0]; a=math.radians(deg); u=(math.cos(a),math.sin(a)); n=(-u[1],u[0])
            choices=[(s[0]+750*u[0]+550*n[0],s[1]+750*u[1]+550*n[1]),(s[0]+750*u[0]-550*n[0],s[1]+750*u[1]-550*n[1])]
            return min(choices,key=lambda q:math.dist(q,getattr(self,'position',(0,0))))
        # Offset perpendicular to the most recent bearing while remaining near the feasible set.
        a=math.radians(obs[-1][1]); n=(-math.sin(a),math.cos(a))
        b=max(120.0,min(500.0,math.sqrt(max(0.0,950.0**2-min(radius,949.0)**2))))
        choices=[(center[0]+b*n[0],center[1]+b*n[1]),(center[0]-b*n[0],center[1]-b*n[1])]
        return min(choices,key=lambda q:math.dist(q,getattr(self,'position',(0,0))))

    def run(self):
        enter=self.client.enter(); self._log('enter',response=enter)
        self.started=time.monotonic(); self.deadline=self.started+float(enter['remaining_real_duration_s'])
        self.position=(0.0,0.0)
        try:
            coverage_points=seven_points(1140.0)
            for index,q in enumerate(coverage_points):
                if not self._time_ok():break
                batch=sorted(self.unknown)
                if self.client.current_channel in batch:
                    batch.remove(self.client.current_channel); batch.insert(0,self.client.current_channel)
                for c in batch:
                    if not self._time_ok():break
                    self._measure(q,c); self.position=q
                # Cheap piggyback bearings at a point already visited for coverage.
                for c in sorted(self.found-self.cleared):
                    if not self._time_ok() or c in batch:continue
                    _,r=self._circle(c)
                    if r>19.5:
                        self._measure(q,c); self.position=q
                if index+1<len(coverage_points):
                    self._clear_insertions(coverage_points[index+1],len(coverage_points)-index-1)

            while self.found-self.cleared and self._time_ok():
                pending=self.found-self.cleared
                ready={ch for ch in pending if self._circle(ch)[1]<=19.5}
                if ready==pending:
                    order=self.ready_clear_order(ready)
                    for c in order:
                        if not self._time_ok() or c in self.cleared:continue
                        center,radius=self._circle(c)
                        if radius<=19.5 and self._clear(center,c):
                            self.position=center
                    continue
                c=min(pending,key=lambda ch:math.dist(self.position,self._circle(ch)[0]))
                center,radius=self._circle(c)
                if radius<=19.5:
                    self._clear(center,c); self.position=center; continue
                if len(self.observations[c])>=10:
                    if self._clear(center,c):
                        self.position=center; continue
                    raise RuntimeError(f'channel {c} did not converge to a guaranteed clear region')
                q=self._targeted_point(c); result=self._measure(q,c); self.position=q
                if result=='no_signal':
                    center,_=self._circle(c)
                    q=((q[0]+center[0])/2,(q[1]+center[1])/2)
                    self._measure(q,c); self.position=q
            exit_response=self.client.exit(); self._log('exit',response=exit_response)
            return {'strategy_mode':self.mode,'found':len(self.found),'cleared':len(self.cleared),'unknown_channels':sorted(self.unknown),'virtual_time_s':exit_response.get('virtual_time_s')}
        except Exception as exc:
            self._log('fatal',error=repr(exc))
            if self._time_ok():
                try:self.client.exit()
                except Exception:pass
            raise
