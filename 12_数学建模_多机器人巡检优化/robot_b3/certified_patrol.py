"""Offline patrol geometry optimization with deterministic certificates.

Differential evolution is used only to search continuous geometry parameters.
Every returned layout is rechecked by an analytic coverage certificate; an
infeasible candidate can never be loaded by an online strategy.
"""

from dataclasses import dataclass
import math
import random

from .full_view import FullViewLayout
from .routing import optimal_open_route


@dataclass(frozen=True)
class DiskPatrolLayout:
    stations: tuple
    route_distance_m: float
    ring_radius_m: float
    reception_radius_m: float = 1000.0
    arena_radius_m: float = 1800.0


@dataclass(frozen=True)
class DiskCoverReport:
    feasible: bool
    worst_distance_m: float


@dataclass(frozen=True)
class TriangleCertificateReport:
    feasible: bool
    max_edge_m: float
    outer_inradius_m: float


def build_q3_seven_station_layout(start=(0.0, 0.0), ring_radius=1123.0):
    center = (0.0, 0.0)
    ring = tuple(
        (ring_radius * math.cos(i * math.pi / 3.0),
         ring_radius * math.sin(i * math.pi / 3.0))
        for i in range(6)
    )
    points = (center,) + ring
    order, distance = optimal_open_route(
        tuple(start), {i: q for i, q in enumerate(points)})
    return DiskPatrolLayout(
        tuple(points[i] for i in order), distance, float(ring_radius))


def validate_q3_disk_cover(layout):
    """Analytic certificate for one centre plus six equally spaced stations."""
    rho = layout.ring_radius_m
    reception = layout.reception_radius_m
    arena = layout.arena_radius_m
    half_sector = math.pi / 6.0
    # Inside the central reception disk is covered by the origin.  Outside it,
    # the farthest point from the nearest ring centre occurs at a sector
    # boundary and at one of the two radial endpoints.
    def distance(r):
        return math.sqrt(r*r + rho*rho
                         - 2.0*r*rho*math.cos(half_sector))
    worst = max(distance(reception), distance(arena))
    return DiskCoverReport(worst <= reception + 1e-8, worst)


def _polar_q4_layout(inner_radius, outer_margin, rotation=0.0,
                     start=(0.0, 0.0), arena_radius=1800.0):
    outer_radius = ((arena_radius + outer_margin)
                    / math.cos(math.pi / 16.0))
    center = (0.0, 0.0)
    inner = tuple(
        (inner_radius * math.cos(rotation + 2.0 * math.pi * i / 8.0),
         inner_radius * math.sin(rotation + 2.0 * math.pi * i / 8.0))
        for i in range(8)
    )
    outer = tuple(
        (outer_radius * math.cos(rotation + 2.0 * math.pi * j / 16.0),
         outer_radius * math.sin(rotation + 2.0 * math.pi * j / 16.0))
        for j in range(16)
    )
    triangles = []
    for i in range(8):
        ni, j = (i + 1) % 8, 2 * i
        triangles.extend((
            (center, inner[i], inner[ni]),
            (inner[i], outer[j], outer[(j + 1) % 16]),
            (inner[i], outer[(j + 1) % 16], inner[ni]),
            (inner[ni], outer[(j + 1) % 16], outer[(j + 2) % 16]),
        ))
    points = (center,) + inner + outer
    order, distance = optimal_open_route(
        tuple(start), {i: q for i, q in enumerate(points)})
    return FullViewLayout(
        tuple(points[i] for i in order), tuple(triangles), 0.0,
        (float(inner_radius), float(outer_radius)), float(rotation), distance)


def build_de_optimized_q4_layout(start=(0.0, 0.0)):
    """Load the best conservative candidate from the offline DE family."""
    layout = _polar_q4_layout(985.5, 0.5, 0.0, start=start)
    report = validate_q4_triangle_certificate(layout)
    if not report.feasible:
        raise RuntimeError('stored Q4 patrol geometry lost its certificate')
    return layout


def validate_q4_triangle_certificate(layout, arena_radius=1800.0,
                                     reception_radius=1000.0):
    edges = []
    for triangle in layout.triangles:
        edges.extend((math.dist(triangle[0], triangle[1]),
                      math.dist(triangle[1], triangle[2]),
                      math.dist(triangle[2], triangle[0])))
    max_edge = max(edges, default=math.inf)
    radii = sorted({round(math.hypot(*q), 8) for q in layout.stations})
    outer_radius = radii[-1] if radii else 0.0
    outer_inradius = outer_radius * math.cos(math.pi / 16.0)
    topology_ok = len(layout.triangles) == 32 and len(layout.stations) == 25
    feasible = (topology_ok
                and max_edge < reception_radius
                and outer_inradius >= arena_radius - 1e-7)
    return TriangleCertificateReport(feasible, max_edge, outer_inradius)


def optimize_q4_polar_parameters(generations=80, population_size=36, seed=0):
    """Feasibility-first DE/rand/1/bin for the strict 8+16 polar family."""
    if population_size < 4:
        raise ValueError('population_size must be at least four')
    rng = random.Random(seed)
    bounds = ((980.0, 999.0), (0.25, 1.0),
              (-math.pi / 16.0, math.pi / 16.0))
    population = [[985.5, 0.5, 0.0]]
    while len(population) < population_size:
        population.append([rng.uniform(lo, hi) for lo, hi in bounds])

    def evaluate(v):
        layout = _polar_q4_layout(*v)
        report = validate_q4_triangle_certificate(layout)
        violation = (max(0.0, report.max_edge_m - 999.9)
                     + 100.0 * max(0.0, 1800.25 - report.outer_inradius_m))
        # Virtual-time proxy: travel plus one all-channel station scan.  The
        # scan term is constant in this topology but keeps units explicit.
        objective = layout.route_distance_m / 5.0 + 25 * 20 * 5.0
        return (0 if report.feasible else 1, violation, objective), layout, report

    scores = [evaluate(v) for v in population]
    for _ in range(max(0, generations)):
        for i, target in enumerate(list(population)):
            choices = [j for j in range(population_size) if j != i]
            a, b, c = rng.sample(choices, 3)
            mutant = [population[a][k] + 0.75 *
                      (population[b][k] - population[c][k])
                      for k in range(3)]
            mutant = [min(hi, max(lo, x))
                      for x, (lo, hi) in zip(mutant, bounds)]
            forced = rng.randrange(3)
            trial = [mutant[k] if k == forced or rng.random() < 0.9
                     else target[k] for k in range(3)]
            candidate = evaluate(trial)
            if candidate[0] < scores[i][0]:
                population[i], scores[i] = trial, candidate
    index = min(range(population_size), key=lambda j: scores[j][0])
    vector, (_, layout, report) = population[index], scores[index]
    return {
        'inner_radius_m': vector[0],
        'outer_margin_m': vector[1],
        'rotation_rad': vector[2],
        'route_distance_m': layout.route_distance_m,
        'max_edge_m': report.max_edge_m,
        'outer_inradius_m': report.outer_inradius_m,
        'feasible': report.feasible,
    }
