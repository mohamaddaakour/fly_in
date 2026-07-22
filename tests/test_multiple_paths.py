"""Tests for Phase 7 multiple routes and drone distribution."""

import unittest

from fly_in.models import MapData
from fly_in.parser import MapParser
from fly_in.pathfinder import Pathfinder
from fly_in.simulation import Simulation


def fork_data(drone_count: int = 4) -> MapData:
    """Build a two-route graph for path and scheduling tests."""
    return MapParser().parse_lines(
        [
            f"nb_drones: {drone_count}",
            "start_hub: start 0 0",
            "end_hub: end 3 0",
            "hub: north 1 1",
            "hub: south 1 -1",
            "connection: start-north",
            "connection: north-end",
            "connection: start-south",
            "connection: south-end",
        ]
    )


class MultiplePathfinderTests(unittest.TestCase):
    """Verify deterministic loopless alternative-route discovery."""

    def test_finds_all_available_fork_routes(self) -> None:
        """Return both equal-cost routes and no duplicates."""
        paths = Pathfinder(fork_data()).find_paths(10)
        self.assertEqual(
            paths,
            [
                ["start", "north", "end"],
                ["start", "south", "end"],
            ],
        )

    def test_paths_are_loopless(self) -> None:
        """Never return a route containing the same zone twice."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 5",
                "start_hub: start 0 0",
                "end_hub: end 3 0",
                "hub: a 1 0",
                "hub: b 2 0",
                "connection: start-a",
                "connection: start-b",
                "connection: a-b",
                "connection: a-end",
                "connection: b-end",
            ]
        )
        paths = Pathfinder(data).find_paths(5)
        self.assertGreaterEqual(len(paths), 2)
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(len(path), len(set(path)))

    def test_weight_and_priority_order_alternatives(self) -> None:
        """Order by cost first and priority preference second."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 3",
                "start_hub: start 0 0",
                "end_hub: end 4 0",
                "hub: normal 1 0",
                "hub: preferred 1 1 [zone=priority]",
                "hub: restricted 2 0 [zone=restricted]",
                "connection: start-normal",
                "connection: normal-end",
                "connection: start-preferred",
                "connection: preferred-end",
                "connection: start-restricted",
                "connection: restricted-end",
            ]
        )
        paths = Pathfinder(data).find_paths(3)
        self.assertEqual(paths[0], ["start", "preferred", "end"])
        self.assertEqual(paths[1], ["start", "normal", "end"])
        self.assertEqual(paths[2], ["start", "restricted", "end"])

    def test_cached_results_are_defensive_copies(self) -> None:
        """Prevent callers from mutating cached path results."""
        finder = Pathfinder(fork_data())
        first = finder.find_paths(2)
        first[0].clear()
        self.assertEqual(
            finder.find_paths(2)[0], ["start", "north", "end"]
        )


class MultiRouteSimulationTests(unittest.TestCase):
    """Verify route assignment and shared-capacity scheduling."""

    def test_equal_routes_receive_balanced_assignments(self) -> None:
        """Distribute drones by expected completion instead of one route."""
        data = fork_data()
        paths = Pathfinder(data).find_paths()
        simulation = Simulation(data, paths)
        assignments = [drone.assigned_path for drone in simulation.drones]
        self.assertEqual(assignments, [paths[0], paths[1], paths[0], paths[1]])
        self.assertEqual(
            simulation.run(),
            [
                "D1-north D2-south",
                "D1-end D2-end D3-north D4-south",
                "D3-end D4-end",
            ],
        )

    def test_shorter_route_gets_more_drones_when_faster(self) -> None:
        """Use estimated completion time rather than round-robin assignment."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 3",
                "start_hub: start 0 0",
                "end_hub: end 4 0",
                "hub: short 1 0",
                "hub: long1 1 1",
                "hub: long2 2 1",
                "connection: start-short",
                "connection: short-end",
                "connection: start-long1",
                "connection: long1-long2",
                "connection: long2-end",
            ]
        )
        paths = Pathfinder(data).find_paths()
        simulation = Simulation(data, paths)
        self.assertEqual(
            [drone.assigned_path for drone in simulation.drones],
            [paths[0], paths[0], paths[1]],
        )

    def test_overlapping_routes_share_zone_capacity(self) -> None:
        """Enforce occupancy globally where assigned routes merge."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 2",
                "start_hub: start 0 0",
                "end_hub: end 4 0",
                "hub: north 1 1",
                "hub: south 1 -1",
                "hub: merge 3 0",
                "connection: start-north",
                "connection: start-south",
                "connection: north-merge",
                "connection: south-merge",
                "connection: merge-end",
            ]
        )
        paths = Pathfinder(data).find_paths(2)
        turns = Simulation(data, paths).run()
        self.assertEqual(
            turns,
            [
                "D1-north D2-south",
                "D1-merge",
                "D1-end D2-merge",
                "D2-end",
            ],
        )

    def test_normal_and_restricted_routes_run_together(self) -> None:
        """Preserve Phase 6 transit state across different assignments."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 3",
                "start_hub: start 0 0",
                "end_hub: end 3 0",
                "hub: normal 1 0",
                "hub: secure 1 1 [zone=restricted]",
                "connection: start-normal",
                "connection: normal-end",
                "connection: start-secure",
                "connection: secure-end",
            ]
        )
        paths = Pathfinder(data).find_paths()
        simulation = Simulation(data, paths)
        self.assertEqual(
            [drone.assigned_path for drone in simulation.drones],
            [paths[0], paths[0], paths[1]],
        )
        self.assertEqual(
            simulation.run(),
            [
                "D1-normal D3-start-secure",
                "D1-end D2-normal D3-secure",
                "D2-end D3-end",
            ],
        )


if __name__ == "__main__":
    unittest.main()
