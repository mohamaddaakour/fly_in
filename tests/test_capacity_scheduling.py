"""Tests for Phase 5 connection- and zone-capacity scheduling."""

import unittest

from fly_in.parser import MapParser
from fly_in.simulation import Simulation


def simulate(lines: list[str], path: list[str]) -> list[str]:
    """Parse a compact map and return all generated turns."""
    return Simulation(MapParser().parse_lines(lines), path).run()


class ConnectionCapacityTests(unittest.TestCase):
    """Verify each bidirectional link enforces its per-turn limit."""

    def test_default_connection_capacity_is_one(self) -> None:
        """Serialize a direct route when link metadata is omitted."""
        turns = simulate(
            [
                "nb_drones: 3",
                "start_hub: start 0 0",
                "end_hub: end 1 0",
                "connection: start-end",
            ],
            ["start", "end"],
        )
        self.assertEqual(turns, ["D1-end", "D2-end", "D3-end"])

    def test_explicit_connection_capacity_allows_parallel_moves(self) -> None:
        """Allow no more than two drones across a capacity-two link."""
        turns = simulate(
            [
                "nb_drones: 5",
                "start_hub: start 0 0",
                "end_hub: end 1 0",
                "connection: start-end [max_link_capacity=2]",
            ],
            ["start", "end"],
        )
        self.assertEqual(
            turns,
            ["D1-end D2-end", "D3-end D4-end", "D5-end"],
        )

    def test_connection_usage_resets_each_turn(self) -> None:
        """Treat capacity as a per-turn limit rather than a lifetime limit."""
        turns = simulate(
            [
                "nb_drones: 3",
                "start_hub: start 0 0",
                "end_hub: end 2 0",
                "hub: staging 1 0 [max_drones=3]",
                "connection: start-staging [max_link_capacity=2]",
                "connection: staging-end",
            ],
            ["start", "staging", "end"],
        )
        self.assertEqual(
            turns,
            [
                "D1-staging D2-staging",
                "D1-end D3-staging",
                "D2-end",
                "D3-end",
            ],
        )

    def test_link_and_zone_capacity_are_both_required(self) -> None:
        """Use the lower effective limit when capacities differ."""
        turns = simulate(
            [
                "nb_drones: 4",
                "start_hub: start 0 0",
                "end_hub: end 2 0",
                "hub: staging 1 0 [max_drones=2]",
                "connection: start-staging [max_link_capacity=4]",
                "connection: staging-end [max_link_capacity=2]",
            ],
            ["start", "staging", "end"],
        )
        self.assertEqual(
            turns,
            [
                "D1-staging D2-staging",
                "D1-end D2-end D3-staging D4-staging",
                "D3-end D4-end",
            ],
        )


if __name__ == "__main__":
    unittest.main()
