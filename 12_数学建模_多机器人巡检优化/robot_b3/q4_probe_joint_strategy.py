"""One-step belief rollout for probe, optical completion and onward travel."""
import math

from .geometry import bearing_clip, enclosing_circle, clear_visit_point, point_polygon_distance
from .q4_belief import SourceParticle
from .q4_certified21_strategy import Q4Certified21Strategy


def _optical_tail(start, polygon, source, destination, bearing):
    center, radius = enclosing_circle(polygon)
    if radius <= 19.5:
        q = clear_visit_point(polygon, start, destination)
        return math.dist(start, q)/5+5+(math.dist(q, destination)/5 if destination else 0)
    a = math.radians(bearing)
    u, n = (math.cos(a), math.sin(a)), (-math.sin(a), math.cos(a))
    coordinates = [(x*u[0]+y*u[1], x*n[0]+y*n[1]) for x, y in polygon]
    def centers(lo, hi):
        count = max(1, math.ceil((hi-lo)/(19.5*math.sqrt(2))))
        return [lo+(i+.5)*(hi-lo)/count for i in range(count)]
    xs = centers(min(x for x, _ in coordinates), max(x for x, _ in coordinates))
    ys = centers(min(y for _, y in coordinates), max(y for _, y in coordinates))
    chain = [(x*u[0]+y*n[0], x*u[1]+y*n[1]) for i,y in enumerate(ys)
             for x in (xs if i % 2 == 0 else list(reversed(xs)))]
    chain = [q for q in chain if point_polygon_distance(q, polygon) <= 19.5+1e-8]
    if not chain:
        return math.inf
    if math.dist(start, chain[-1]) < math.dist(start, chain[0]):
        chain.reverse()
    cost, previous = 0., start
    for q in chain:
        cost += math.dist(previous, q)/5
        if math.dist(q, source) <= 20:
            return cost+5+(math.dist(q, destination)/5 if destination else 0)
        cost += 3
        previous = q
    return math.inf


def expected_probe_cost(start, q, polygon, particles, destination, switch, last_bearing=0.):
    """Finite scenario score, not a certificate or globally optimal value."""
    groups = {}
    for p in particles:
        key = p.x, p.y, p.is_received(q)
        groups[key] = groups.get(key, 0.)+p.weight
    mass = sum(groups.values())
    if mass <= 0:
        return math.inf
    tail = 0.
    for (x, y, received), weight in groups.items():
        source = (x, y)
        if received and math.dist(source, q) <= 5:
            cost = 5+(math.dist(q, destination)/5 if destination else 0)
        elif received:
            angle = math.degrees(math.atan2(y-q[1], x-q[0]))
            values = []
            for error in (-1., 0., 1.):
                region = bearing_clip(polygon, q, angle+error, 1.00000001)
                values.append(_optical_tail(q, region, source, destination, angle+error)
                              if region else math.inf)
            cost = sum(values)/3
        else:
            # A directional miss does NOT remove a 1000 m disk from safe P.
            cost = _optical_tail(q, polygon, source, destination, last_bearing)
        tail += weight*cost/mass
    return math.dist(start, q)/5+5+int(switch)+tail


class Q4ProbeJointStrategy(Q4Certified21Strategy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'q4_probe_joint'
        self._planned_probes = {}
        self.changed_probe_choices = 0

    def _scenarios(self, c, count=24):
        particles = [p for p in self.beliefs[c].particles
                     if point_polygon_distance((p.x,p.y), self.poly[c]) <= 1e-7 and p.weight > 0]
        total = sum(p.weight for p in particles)
        if not particles or total <= 0:
            # Unknown radiation parameters: integrate both types and directions;
            # existence is known here, but this fallback is still only a prior.
            center, _ = self._circle(c)
            support = [center]+self.poly[c][::max(1,len(self.poly[c])//4)]
            particles = [SourceParticle(x,y,1000,None,1.) for x,y in support]
            particles += [SourceParticle(x,y,1000,k*math.pi/6,1/12)
                          for x,y in support for k in range(12)]
            total = sum(p.weight for p in particles)
        sampled, index, cumulative = [], 0, particles[0].weight
        for i in range(count):
            threshold = (i+.5)*total/count
            while cumulative < threshold and index+1 < len(particles):
                index += 1
                cumulative += particles[index].weight
            p = particles[index]
            sampled.append(SourceParticle(p.x,p.y,p.radius,p.direction,1/count))
        return sampled

    def _refine_action_plan(self, order, tasks, coverage):
        self._planned_probes.clear()
        # Coordinate optimization along the currently proposed task order.
        # Execute exactly the scored first probe; do not silently reselect it.
        if order and order[0][0] == 'target':
            key = order[0]
            c = key[1]
            probes = self._probe_queue(c) if self._circle(c)[1] > 19.5 else []
            if probes:
                destination = tasks[order[1]] if len(order)>1 else None
                scenarios = self._scenarios(c)
                ranked = [(expected_probe_cost(self.position, q, self.poly[c], scenarios,
                                               destination, self.client.current_channel != c,
                                               self.observations[c][-1][1]), q) for q in probes]
                value, q = min(ranked)
                if math.isfinite(value):
                    self._planned_probes[c] = q
                    self.changed_probe_choices += int(q != tasks[key])
                    tasks[key] = q
                    self._log('joint_probe_plan', channel=c, position=q,
                              onward=destination, expected_completion_s=value,
                              candidate_count=len(probes))
        return order, tasks

    def _service_one(self, c, destination, remaining_sweeps):
        q = self._planned_probes.pop(c, None)
        if q is None:
            return super()._service_one(c, destination, remaining_sweeps)
        probes = self._probe_queue(c)
        probes.remove(q)
        self._probe_attempts[c] = self._probe_attempts.get(c, 0)+1
        self._measure(q, c)
        self._guaranteed_here()

    def run(self):
        result = super().run()
        result['changed_probe_choices'] = self.changed_probe_choices
        return result
