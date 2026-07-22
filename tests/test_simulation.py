"""Tests for the Phase 4 one-path simulation engine."""

from dataclasses import replace
import unittest

from fly_in.parser import MapParser
from fly_in.simulation import Simulation, SimulationError


def build_simulation(
    drone_count: int,
    intermediate_zones: list[str],
    connections: list[str],
    path: list[str],
) -> Simulation:
    """Create a simulation from compact map declarations."""
    lines = [
        f"nb_drones: {drone_count}",
        "start_hub: start 0 0",
        "end_hub: end 9 0",
        *intermediate_zones,
        *connections,
    ]
    return Simulation(MapParser().parse_lines(lines), path)


class SimulationOutputTests(unittest.TestCase):
    """Verify required pipeline movement and official output."""

    def test_one_drone_linear_path(self) -> None:
        """Move one drone exactly one edge per turn."""
        simulation = build_simulation(
            1,
            ["hub: a 1 0"],
            ["connection: start-a", "connection: a-end"],
            ["start", "a", "end"],
        )
        self.assertEqual(simulation.run(), ["D1-a", "D1-end"])

    def test_capacity_one_pipeline(self) -> None:
        """Free and reserve intermediate capacity in the same turn."""
        simulation = build_simulation(
            3,
            ["hub: a 1 0", "hub: b 2 0"],
            [
                "connection: start-a",
                "connection: a-b",
                "connection: b-end",
            ],
            ["start", "a", "b", "end"],
        )
        self.assertEqual(
            simulation.run(),
            [
                "D1-a",
                "D1-b D2-a",
                "D1-end D2-b D3-a",
                "D2-end D3-b",
                "D3-end",
            ],
        )

    def test_direct_path_has_unlimited_end_capacity(self) -> None:
        """Deliver every drone together on a direct start-to-end path."""
        simulation = build_simulation(
            5,
            [],
            ["connection: start-end [max_link_capacity=5]"],
            ["start", "end"],
        )
        self.assertEqual(
            simulation.run(),
            ["D1-end D2-end D3-end D4-end D5-end"],
        )

    def test_intermediate_capacity_two(self) -> None:
        """Allow two drones into a zone whose capacity is two."""
        simulation = build_simulation(
            4,
            ["hub: waiting 1 0 [max_drones=2]"],
            [
                "connection: start-waiting [max_link_capacity=2]",
                "connection: waiting-end [max_link_capacity=2]",
            ],
            ["start", "waiting", "end"],
        )
        self.assertEqual(
            simulation.run(),
            [
                "D1-waiting D2-waiting",
                "D1-end D2-end D3-waiting D4-waiting",
                "D3-end D4-end",
            ],
        )

    def test_path_is_copied(self) -> None:
        """Prevent callers from changing a path after initialization."""
        path = ["start", "end"]
        simulation = build_simulation(
            1, [], ["connection: start-end"], path
        )
        path.clear()
        self.assertEqual(simulation.run(), ["D1-end"])

    def test_deadlock_is_reported(self) -> None:
        """Stop instead of looping if no active drone can move."""
        simulation = build_simulation(
            1,
            ["hub: a 1 0"],
            ["connection: start-a", "connection: a-end"],
            ["start", "a", "end"],
        )
        zone = simulation.map_data.zones["a"]
        simulation.map_data.zones["a"] = replace(zone, max_drones=0)
        with self.assertRaisesRegex(SimulationError, "deadlocked"):
            simulation.run()


class SimulationValidationTests(unittest.TestCase):
    """Verify invalid paths fail before movement begins."""

    def setUp(self) -> None:
        """Create a connected graph containing a blocked zone."""
        self.map_data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 3 0",
                "hub: a 1 0",
                "hub: blocked 2 0 [zone=blocked]",
                "connection: start-a",
                "connection: a-blocked",
                "connection: blocked-end",
            ]
        )

    def test_rejects_empty_and_single_zone_paths(self) -> None:
        """Require at least a start-to-end transition."""
        for path in ([], ["start"]):
            with self.subTest(path=path), self.assertRaises(SimulationError):
                Simulation(self.map_data, path)

    def test_rejects_wrong_start_and_end(self) -> None:
        """Require the declared start and end as path endpoints."""
        paths = [["a", "blocked", "end"], ["start", "a"]]
        for path in paths:
            with self.subTest(path=path), self.assertRaises(SimulationError):
                Simulation(self.map_data, path)

    def test_rejects_unknown_and_blocked_zones(self) -> None:
        """Prevent inaccessible or nonexistent zones in a route."""
        paths = [
            ["start", "unknown", "end"],
            ["start", "a", "blocked", "end"],
        ]
        for path in paths:
            with self.subTest(path=path), self.assertRaises(SimulationError):
                Simulation(self.map_data, path)

    def test_rejects_missing_connection(self) -> None:
        """Require every consecutive pair to be a graph edge."""
        with self.assertRaisesRegex(SimulationError, "no connection"):
            Simulation(self.map_data, ["start", "end"])

    def test_rejects_corrupt_path_index(self) -> None:
        """Fail clearly if runtime drone state becomes invalid."""
        simulation = build_simulation(
            1,
            ["hub: a 1 0"],
            ["connection: start-a", "connection: a-end"],
            ["start", "a", "end"],
        )
        simulation.drones[0].path_index = 99
        with self.assertRaisesRegex(SimulationError, "invalid path index"):
            simulation.run_turn()


if __name__ == "__main__":
    unittest.main()
