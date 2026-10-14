"""Strict fusion planner: robust reception + minimax localization + route detour."""
import math

from .active_localization import guaranteed_reception
from .geometry import clear_visit_point
from .score_strategy import ScoreStrategy


class FusionStrategy(ScoreStrategy):
    """ScoreStrategy with a continuous, route-aware active-localization layer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mode = 'fusion'

    def _positive_stations(self, c):
        return [station for station, _ in self.observations.get(c, ())]

    def likely_reception(self, c, q, margin=None):
        # Opportunistic shared-station measurements retain the calibrated
        # empirical gate; the strict certificate is mandatory for deliberately
        # chosen refinement stations below.
        return super().likely_reception(c, q, margin)

    def _candidate_cost(self, c, q, destination):
        predicted = self._prediction(c, q)
        if not math.isfinite(predicted):
            return math.inf
        center, _ = self._circle(c)
        if destination is None:
            route_distance = math.dist(self.position, q) + math.dist(q, center)
        else:
            # After measuring, both the updated target and the next route task
            # still have to be visited.  Compare the two possible local orders.
            route_distance = math.dist(self.position, q) + min(
                math.dist(q, center)+math.dist(center, destination),
                math.dist(q, destination)+math.dist(destination, center))
        # A successful second bearing costs 5 s.  The residual term estimates
        # another bearing plus the travel needed to shrink the MEC to 19.5 m.
        residual = 0.0 if predicted <= 19.5 else 6.0 + .7*(predicted-19.5)/5
        switch = 0.0 if self.client.current_channel == c else 1.0
        return route_distance/5 + 5 + switch + residual

    def _coarse_candidates(self, c, destination):
        center, radius = self._circle(c)
        # The proven baseline candidate is always retained; the enlarged C_rx
        # search may improve it but can never disappear merely because the
        # exploratory grid changed.
        result = [center, super().refinement_point(c)]
        if destination is not None:
            result.extend((self.position[0]+t*(destination[0]-self.position[0]),
                           self.position[1]+t*(destination[1]-self.position[1]))
                          for t in (0.15, .3, .45, .6, .75, .9))
        result.extend((self.position[0]+t*(center[0]-self.position[0]),
                       self.position[1]+t*(center[1]-self.position[1]))
                      for t in (.25, .5, .75, 1.0))
        angles = [k*math.pi/6 for k in range(12)]
        distances = sorted({40.0, 80.0, 160.0, 280.0, 420.0,
                            max(40.0, min(700.0, radius))})
        result.extend((center[0]+r*math.cos(a), center[1]+r*math.sin(a))
                      for r in distances for a in angles)
        if self.observations.get(c):
            station, bearing = self.observations[c][-1]
            a = math.radians(bearing)
            ux, uy = math.cos(a), math.sin(a)
            nx, ny = -uy, ux
            for along in (250, 500, 750, 1000, 1250):
                for cross in (-1000, -750, -500, -250, 250, 500, 750, 1000):
                    result.append((station[0]+along*ux+cross*nx,
                                   station[1]+along*uy+cross*ny))
        return result

    def refinement_point(self, c, destination=None):
        stations = self._positive_stations(c)
        baseline = super().refinement_point(c)
        baseline_cost = self._candidate_cost(c, baseline, destination)
        seen = set()

        def legal(q):
            key = (round(q[0], 7), round(q[1], 7))
            if key in seen or (tuple(q), c) in self._measured:
                return False
            seen.add(key)
            return guaranteed_reception(self.poly[c], q, stations)

        ranked = []
        for q in self._coarse_candidates(c, destination):
            if legal(q):
                ranked.append((self._candidate_cost(c, q, destination), q))
        ranked.sort(key=lambda item: item[0])

        # Two local meshes approximate the continuous minimizer without imposing
        # an arena constraint: /measure positions are allowed outside the arena.
        for step in (100.0, 30.0):
            seeds = [q for _, q in ranked[:5]]
            for seed in seeds:
                for dx in (-step, 0.0, step):
                    for dy in (-step, 0.0, step):
                        q = (seed[0]+dx, seed[1]+dy)
                        if legal(q):
                            ranked.append((self._candidate_cost(c, q, destination), q))
            ranked.sort(key=lambda item: item[0])
        if ranked:
            # Scenario prediction is approximate.  Demand a material 100 s
            # modeled advantage before departing from the empirically strong
            # baseline; this prevents small geometric gains buying long travel.
            best_cost, best = ranked[0]
            use_dynamic = best_cost <= baseline_cost-100
            selected = best if use_dynamic else baseline
            self._log(
                'refinement_decision',
                channel=c,
                destination=destination,
                baseline_position=baseline,
                best_position=best,
                selected_position=selected,
                total_candidates=len(seen),
                feasible_candidates=len(ranked),
                baseline_cost_s=baseline_cost,
                best_cost_s=best_cost,
                gate_s=100.0,
                used_dynamic_candidate=use_dynamic,
                current_radius_m=self._circle(c)[1],
                predicted_radius_m=self._prediction(c, selected),
            )
            return selected

        # A small displacement from the latest positive station remains inside
        # its certified neighbourhood and avoids repeating the same bearing call.
        station, bearing = self.observations[c][-1]
        a = math.radians(bearing) + math.pi/2
        for distance in (10.0, 5.0, 1.0):
            q = (station[0]+distance*math.cos(a), station[1]+distance*math.sin(a))
            if guaranteed_reception(self.poly[c], q, stations):
                self._log(
                    'refinement_decision',
                    channel=c,
                    destination=destination,
                    baseline_position=baseline,
                    best_position=q,
                    selected_position=q,
                    total_candidates=len(seen),
                    feasible_candidates=0,
                    baseline_cost_s=baseline_cost,
                    best_cost_s=self._candidate_cost(c, q, destination),
                    gate_s=100.0,
                    used_dynamic_candidate=True,
                    used_certified_fallback=True,
                    current_radius_m=self._circle(c)[1],
                    predicted_radius_m=self._prediction(c, q),
                )
                return q
        raise RuntimeError(f'no certified refinement point on channel {c}')

    def _service(self, c, destination):
        center, radius = self._circle(c)
        if radius <= 19.5:
            q = clear_visit_point(self.poly[c], self.position, destination)
            if not self._clear(q, c):
                raise RuntimeError(f'guaranteed optical clear failed on channel {c}')
        elif radius <= 40 and len(self.observations[c]) >= 2 and c not in self._probed:
            self._probed.add(c)
            if not self._clear(center, c) and self._time_ok():
                self._measure(self.position, c)
        else:
            self._measure(self.refinement_point(c, destination), c)
        self._guaranteed_here()
        for other in sorted(self.found-self.cleared):
            if other != c and self._time_ok() and self._useful_bearing(other, self.position):
                self._measure(self.position, other)
        self._guaranteed_here()
