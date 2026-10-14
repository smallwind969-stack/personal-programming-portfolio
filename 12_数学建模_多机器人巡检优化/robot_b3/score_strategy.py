"""Q3 score-oriented search/localize/clear planner; only consumes protocol feedback."""
import math
import time

from .geometry import (arena_polygon, bearing_clip, clear_visit_point,
                       enclosing_circle, reception_clip, seven_points,
                       bearing_least_squares)
from .score_routing import plan_open_route
from .strategy import RobotStrategy
from .coverage_optimizer import complete_coverage
from .routing import optimal_open_route


class ScoreStrategy(RobotStrategy):
    reception_margin=60.0
    def __init__(self, client, logger=None, route_budget_s=1.0, deadline_margin_s=20):
        super().__init__(client, logger, deadline_margin_s, mode='safe')
        self.mode = 'score'
        self.route_budget_s = route_budget_s
        self.position = (0.0, 0.0)
        self._circles = {}
        self._measured = set()
        self._probed = set()
        self.coverage_stations = 0
        self.scan_stations = []
        self.absent = set()

    def _circle(self, c):
        if c not in self._circles:
            self._circles[c] = enclosing_circle(self.poly[c])
        return self._circles[c]

    def _measure(self, q, c):
        # Only /measure changes the receiver channel. Every accepted movement counts,
        # including an optical search that reports no target.
        response = self.client.measure(q, c)
        self.position = tuple(q)
        self._measured.add((tuple(q), c))
        self._log('measure', position=q, channel=c, response=response)
        result = response['measure_result']
        if result in ('direction', 'near'):
            self.found.add(c)
            self.unknown.discard(c)
            self.poly.setdefault(c, arena_polygon())
            self.observations.setdefault(c, [])
        if result == 'direction':
            theta = float(response['svd_deg'])
            self.observations[c].append((tuple(q), theta))
            polygon = bearing_clip(self.poly[c], q, theta, 1.00000001)
            self.poly[c] = reception_clip(polygon, q)
            self._circles.pop(c, None)
            if not self.poly[c]:
                raise RuntimeError(f'empty feasible region on channel {c}')
        elif result == 'near':
            self._clear(q, c)
        if len(self.found) == 16:
            self.absent.update(self.unknown)
            self.unknown.clear()
        return result

    def _clear(self, q, c):
        response = self.client.clear(q, c)
        self.position = tuple(q)
        self._log('clear', position=q, channel=c, response=response)
        if response['clear_result'] == 'success':
            self.cleared.add(c)
            return True
        return False

    def _guaranteed_here(self):
        for c in sorted(self.found-self.cleared):
            if not self._time_ok():
                break
            if self.poly[c] and max(math.dist(self.position, p) for p in self.poly[c]) <= 19.9:
                if not self._clear(self.position, c):
                    raise RuntimeError(f'guaranteed optical clear failed on channel {c}')

    def _prediction(self, c, q):
        poly = self.poly[c]
        center, _ = self._circle(c)
        probes = [center]+poly[::max(1, len(poly)//4)]
        radii = []
        for p in probes:
            if math.dist(p, q) <= 5:
                radii.append(0.0)
                continue
            a = math.degrees(math.atan2(p[1]-q[1], p[0]-q[0]))
            for error in (-1.0, 0.0, 1.0):
                region = bearing_clip(poly, q, a+error, 1.00000001)
                if region:
                    radii.append(enclosing_circle(region)[1])
        return max(radii, default=math.inf)

    def refinement_point(self, c):
        center, radius = self._circle(c)
        angles = [i*math.pi/4 for i in range(8)]
        if self.observations[c]:
            a = math.radians(self.observations[c][-1][1])+math.pi/2
            angles.extend([a, a+math.pi])
        distances = sorted({30.0, 60.0, 120.0, 240.0, max(40.0, min(420.0, radius))})
        choices = [center, self.position]
        choices.extend((center[0]+r*math.cos(a), center[1]+r*math.sin(a))
                       for r in distances for a in angles)
        best = None
        for q in choices:
            if (tuple(q), c) in self._measured:
                continue
            if max(math.dist(q, p) for p in self.poly[c]) > 999:
                continue
            predicted = self._prediction(c, q)
            # Movement and operation costs in seconds; residual localization is
            # a scenario-based estimate, not a guaranteed global optimum.
            tail = 0 if predicted <= 19.5 else 6+2*(predicted-19.5)/5
            cost = (math.dist(self.position, q)+math.dist(q, center))/5+5+tail
            if best is None or cost < best[0]:
                best = (cost, q)
        if best is not None:
            return best[1]
        # Reception constraints imply diameter <=1500 after a first bearing;
        # this fallback is normally unnecessary and never repeats a station.
        return (center[0]+10, center[1]+10)

    def _useful_bearing(self, c, q):
        if (tuple(q), c) in self._measured:
            return False
        center, radius = self._circle(c)
        if radius <= 19.5 or not self.likely_reception(c,q,self.reception_margin):
            return False
        predicted = self._prediction(c, q)
        return predicted <= 19.5 or predicted < radius*0.65

    def likely_reception(self,c,q,margin=None):
        margin=self.reception_margin if margin is None else margin
        center,_=self._circle(c)
        positive=self.observations.get(c,())
        learned=max([1000.0]+[math.dist(center,station) for station,_ in positive])
        return math.dist(center,q)<=min(1500.0,learned+margin)

    def defer_to_shared_station(self,c,stations):
        return len(self.observations.get(c,()))<2 and any(self._useful_bearing(c,q) for q in stations)

    def _task_point(self,c):return self._circle(c)[0]

    def _scan(self, q):
        # Merge both channel lists: current channel first, each channel once.
        unknown = set(self.unknown)
        known = {c for c in self.found-self.cleared if self._useful_bearing(c, q)}
        channels = sorted(unknown | known)
        if self.client.current_channel in channels:
            channels.remove(self.client.current_channel)
            channels.insert(0, self.client.current_channel)
        required=set(self.unknown)
        for c in channels:
            if not self._time_ok():
                return False
            if c in self.cleared or c in self.absent:
                continue
            self._measure(q, c)
        measured_here={c for position,c in self._measured if position==tuple(q)}
        if required.issubset(measured_here|self.absent):
            if not self.scan_stations or math.dist(self.scan_stations[-1],q)>1e-7:
                self.scan_stations.append(tuple(q))
                self.coverage_stations=len(self.scan_stations)
        self._guaranteed_here()
        return True

    def _maybe_replace_scan(self,coverage):
        """Use a target visit as a scan station only if it removes fixed stations.

        Thus adaptive coverage never increases the number of full channel sweeps and
        retains an exact 1000 m coverage certificate.
        """
        if not self.unknown or not coverage or not self._time_ok():return
        if any(math.dist(self.position,q)<1e-6 for q in self.scan_stations):return
        # One current scan must replace at least one future full sweep. Free
        # centers are reoptimized jointly instead of being tied to old vertices.
        planned=complete_coverage(self.scan_stations+[self.position],len(coverage)-1,
                                  budget_s=min(.25,self.route_budget_s))
        if planned is None:return
        # Removing a sweep is useful only when the remaining mandatory travel is
        # shorter too.  The current point is already reached, so scan/switch costs
        # cancel against the removed future sweep and distance decides the gain.
        pending={('target',c):self._task_point(c) for c in sorted(self.found-self.cleared)}
        old_tasks=dict(coverage);old_tasks.update(pending)
        old_distance=optimal_open_route(self.position,old_tasks)[1]
        new_tasks={('candidate',i):q for i,q in enumerate(planned)}
        new_tasks.update(pending)
        new_distance=optimal_open_route(self.position,new_tasks)[1]
        # A margin absorbs later shifts of target estimates and route coupling.
        if new_distance >= old_distance-150.0:return
        self._scan(self.position)
        coverage.clear()
        for i,q in enumerate(planned):coverage[('scan','opt',len(self.scan_stations),i)]=q

    def _service(self, c, destination):
        center, radius = self._circle(c)
        if radius <= 19.5:
            q = clear_visit_point(self.poly[c], self.position, destination)
            if not self._clear(q, c):
                raise RuntimeError(f'guaranteed optical clear failed on channel {c}')
        elif radius <= 40 and len(self.observations[c]) >= 2 and c not in self._probed:
            self._probed.add(c)
            if not self._clear(center,c) and self._time_ok():self._measure(self.position,c)
        else:
            self._measure(self.refinement_point(c), c)
        self._guaranteed_here()
        # Nearby pending sources can share this station if another bearing is useful.
        for other in sorted(self.found-self.cleared):
            if other != c and self._time_ok() and self._useful_bearing(other, self.position):
                self._measure(self.position, other)
        self._guaranteed_here()

    def _select_task(self, plan, tasks, coverage):
        order=plan['order']
        return order[0], tasks[order[1]] if len(order)>1 else None

    def run(self):
        entered = self.client.enter()
        self._log('enter', response=entered, strategy_mode=self.mode)
        self.started = time.monotonic()
        self.deadline = self.started+float(entered['remaining_real_duration_s'])
        self.position = (0.0, 0.0)
        # Fixed stations provide the conservative fallback certificate. Target
        # visits may replace them only after an exact union-coverage check.
        # Minimal symmetric ring radius is about 1122.955 m; 1123 keeps a
        # small numerical margin while shortening the mandatory tour.
        coverage={('scan',i):q for i,q in enumerate(seven_points(1123.0))}
        discovery_complete = False
        try:
            self._scan((0.0, 0.0))
            coverage.pop(('scan',0))
            while self._time_ok():
                if not self.unknown or not coverage:
                    discovery_complete = True
                    self.absent.update(self.unknown)
                    self.unknown.clear()
                pending = self.found-self.cleared
                if not pending and discovery_complete:
                    break
                tasks = {}
                if not discovery_complete:
                    tasks.update(coverage)
                for c in sorted(pending):
                    tasks[('target',c)]=self._task_point(c)
                if not tasks:
                    break
                available = max(0, self.deadline-time.monotonic()-self.deadline_margin_s)
                plan = plan_open_route(self.position, tasks, min(self.route_budget_s, available/20))
                self._log('plan', **plan)
                order = plan['order']
                key, destination = self._select_task(plan, tasks, coverage)
                if key[0] == 'scan':
                    self._scan(tasks[key])
                    coverage.pop(key,None)
                else:
                    self._service(key[1], destination)
                    self._maybe_replace_scan(coverage)
            response = self.client.exit()
            self._log('exit', response=response)
            return {'strategy_mode': self.mode, 'found': len(self.found), 'cleared': len(self.cleared),
                    'unknown_channels': sorted(self.unknown), 'absent_channels': sorted(self.absent),
                    'discovery_complete': discovery_complete, 'coverage_stations': self.coverage_stations,
                    'virtual_time_s': response.get('virtual_time_s')}
        except Exception as exc:
            self._log('fatal', error=repr(exc))
            try:
                self.client.exit()
            except Exception:
                pass
            raise
