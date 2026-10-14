import unittest
import itertools
import math

from robot_b3.routing import optimal_open_route, select_clear_insertion


class RoutingTests(unittest.TestCase):
    def test_open_route_avoids_nearest_neighbor_trap(self):
        start=(0.0,0.0)
        points={'a':(1.0,0.0),'b':(2.0,10.0),'c':(3.0,0.0)}
        order,length=optimal_open_route(start,points)
        brute=min(math.dist(start,points[o[0]])+sum(math.dist(points[a],points[b]) for a,b in zip(o,o[1:])) for o in itertools.permutations(points))
        self.assertAlmostEqual(length,brute,places=8)
        self.assertEqual(set(order),set(points))

    def test_empty_route(self):
        self.assertEqual(optimal_open_route((0,0),{}),([],0.0))

    def test_selects_isolated_mature_point_on_route(self):
        choice = select_clear_insertion(
            (0, 0), (1000, 0), {1: (500, 0)}, {1}, 300, 80
        )
        self.assertEqual(choice, [1])

    def test_defers_dense_cluster_with_large_detour(self):
        points = {1: (500, 400), 2: (510, 410)}
        choice = select_clear_insertion(
            (0, 0), (1000, 0), points, {1, 2}, 100, 80
        )
        self.assertEqual(choice, [])

    def test_never_selects_immature_point(self):
        choice = select_clear_insertion(
            (0, 0), (1000, 0), {1: (500, 0)}, set(), 300, 80
        )
        self.assertEqual(choice, [])


if __name__=='__main__':unittest.main()
