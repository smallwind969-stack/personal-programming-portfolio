"""Local Q3 evaluation fixture. Ground truth is never supplied to the strategy."""
import hashlib
import math
import random


def make_scene(seed, count=None, layout='uniform', reception=None,
               directional_fraction=0.0):
    rng = random.Random(seed)
    count = rng.randint(10, 16) if count is None else count
    scene = {}
    anchors = [(900*math.cos(a), 900*math.sin(a)) for a in (0, 2.1, 4.2)]
    for i, channel in enumerate(rng.sample(range(1, 21), count)):
        a = rng.uniform(0, 2*math.pi)
        r = 1800*math.sqrt(rng.random())
        if layout == 'boundary':
            r = rng.uniform(1750, 1800)
        p = (r*math.cos(a), r*math.sin(a))
        if layout == 'clustered':
            x, y = anchors[i % 3]
            p = (x+rng.uniform(-120, 120), y+rng.uniform(-120, 120))
        source_radius = reception if reception is not None else rng.uniform(1000, 1500)
        if directional_fraction > 0 and rng.random() < directional_fraction:
            scene[channel] = (p, source_radius, rng.uniform(0, 360))
        else:
            scene[channel] = (p, source_radius)
    return scene


class OfflineSimulator:
    def __init__(self, sources, seed=0, error_mode='uniform', max_actions=3000):
        self._sources = dict(sources)
        self.seed = seed
        self.error_mode = error_mode
        self.max_actions = max_actions
        self.position = (0.0, 0.0)
        self.current_channel = 1
        self.virtual_time_s = 0.0
        self.cleared = set()
        self.exited = False
        self.moves_m = 0.0
        self.measures = self.switches = self.successes = self.failures = 0
        self.search_measures = self.localization_measures = 0
        self.no_signal_measures = self.direction_measures = self.near_measures = 0
        self._discovered_channels = set()
        self.actions = []

    def _response(self, **result):
        return {'accepted': True, 'virtual_time_s': self.virtual_time_s, **result}

    def enter(self):
        return self._response(remaining_real_duration_s=1200, max_virtual_duration_s=360000)

    def _move(self, p):
        if len(self.actions) >= self.max_actions:
            raise RuntimeError('offline action limit reached')
        d = math.dist(self.position, p)
        self.moves_m += d
        self.virtual_time_s += d/5.0
        self.position = tuple(p)

    def _finish_measure(self, c, result, **extra):
        if c in self._discovered_channels:
            self.localization_measures += 1
        else:
            self.search_measures += 1
        if result == 'no_signal':
            self.no_signal_measures += 1
        elif result == 'direction':
            self.direction_measures += 1
            self._discovered_channels.add(c)
        elif result == 'near':
            self.near_measures += 1
            self._discovered_channels.add(c)
        return self._response(measure_result=result, **extra)

    def measure(self, p, c):
        self._move(p)
        if c != self.current_channel:
            self.switches += 1
            self.virtual_time_s += 1
        self.current_channel = c
        self.measures += 1
        self.virtual_time_s += 5
        self.actions.append(('measure', tuple(p), c))
        source = self._sources.get(c)
        if source is None or c in self.cleared:
            return self._finish_measure(c, 'no_signal')
        location, reception = source[0], source[1]
        orientation = source[2] if len(source) >= 3 else None
        distance = math.dist(p, location)
        if distance > reception:
            return self._finish_measure(c, 'no_signal')
        if orientation is not None and distance > 1e-12:
            a = math.radians(float(orientation))
            vx, vy = p[0]-location[0], p[1]-location[1]
            if math.cos(a)*vx+math.sin(a)*vy < -1e-9:
                return self._finish_measure(c, 'no_signal')
        if distance <= 5:
            return self._finish_measure(c, 'near')
        key = f'{self.seed}:{float(p[0]):.7f}:{float(p[1]):.7f}:{c}'.encode()
        z = int.from_bytes(hashlib.sha256(key).digest()[:8], 'big')/(2**64-1)
        error = 2*z-1
        if self.error_mode == 'extreme':
            error = 1.0 if z >= 0.5 else -1.0
        if self.error_mode == 'zero':
            error = 0.0
        g = location
        bearing = math.degrees(math.atan2(g[1]-p[1], g[0]-p[0]))
        return self._finish_measure(c, 'direction', svd_deg=(bearing+error) % 360)

    def clear(self, p, c):
        self._move(p)
        source = self._sources.get(c)
        ok = source is not None and c not in self.cleared and math.dist(p, source[0]) <= 20
        self.actions.append(('clear', tuple(p), c))
        if ok:
            self.successes += 1
            self.cleared.add(c)
        else:
            self.failures += 1
        self.virtual_time_s += 5 if ok else 3
        return self._response(clear_result='success' if ok else 'no_target_in_range')

    def exit(self):
        self.exited = True
        return self._response(exit_reason='user_exit')

    def cost_breakdown(self):
        return {'move_distance_m': self.moves_m, 'move_s': self.moves_m/5,
                'measures': self.measures, 'measure_s': 5*self.measures,
                'search_measures': self.search_measures,
                'localization_measures': self.localization_measures,
                'no_signal_measures': self.no_signal_measures,
                'direction_measures': self.direction_measures,
                'near_measures': self.near_measures,
                'switches': self.switches, 'switch_s': self.switches,
                'clear_s': 5*self.successes+3*self.failures, 'failed_clears': self.failures,
                'total_s': self.moves_m/5+5*self.measures+self.switches+5*self.successes+3*self.failures}
