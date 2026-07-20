"""Tests for parsing and Phase 3 weighted pathfinding."""

import unittest

from fly_in.models import ZoneType
from fly_in.parser import MapParser, ParseError
from fly_in.pathfinder import Pathfinder, PathNotFoundError


class ParserTests(unittest.TestCase):
    """Verify strict parsing constraints from the subject."""

    def test_valid_map_and_defaults(self) -> None:
        """Parse defaults and bidirectional graph data."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 2",
                "start_hub: start 0 0",
                "end_hub: end 2 0",
                "hub: middle 1 0",
                "connection: start-middle",
                "connection: middle-end [max_link_capacity=2]",
            ]
        )
        self.assertEqual(data.drone_count, 2)
        self.assertEqual(data.zones["middle"].zone_type, ZoneType.NORMAL)
        self.assertEqual(data.zones["middle"].max_drones, 1)
        self.assertEqual(data.connections[1].max_link_capacity, 2)

    def test_connection_must_use_previously_defined_zones(self) -> None:
        """Reject a connection whose endpoint has not been declared."""
        with self.assertRaisesRegex(ParseError, "Line 3: unknown zone"):
            MapParser().parse_lines(
                [
                    "nb_drones: 1",
                    "start_hub: start 0 0",
                    "connection: start-end",
                    "end_hub: end 1 0",
                ]
            )

    def test_rejects_duplicate_reversed_connection(self) -> None:
        """Treat a-b and b-a as the same connection."""
        with self.assertRaisesRegex(ParseError, "duplicate connection"):
            MapParser().parse_lines(
                [
                    "nb_drones: 1",
                    "start_hub: start 0 0",
                    "end_hub: end 1 0",
                    "connection: start-end",
                    "connection: end-start",
                ]
            )

    def test_rejects_invalid_capacity_and_zone_type(self) -> None:
        """Reject non-positive capacity and unsupported zone types."""
        invalid_maps = [
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 1 0 [max_drones=0]",
                "connection: start-end",
            ],
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 1 0 [zone=unknown]",
                "connection: start-end",
            ],
        ]
        for lines in invalid_maps:
            with self.subTest(lines=lines), self.assertRaises(ParseError):
                MapParser().parse_lines(lines)

    def test_missing_declaration_has_line_and_cause(self) -> None:
        """Report structural errors with a source line and clear cause."""
        with self.assertRaisesRegex(
            ParseError, "Line 3: missing end_hub definition"
        ):
            MapParser().parse_lines(
                ["nb_drones: 1", "start_hub: start 0 0"]
            )


class PathfinderTests(unittest.TestCase):
    """Verify Phase 3 weighted route selection."""

    def test_restricted_cost_and_blocked_zone(self) -> None:
        """Avoid blocked zones and count restricted entry as two turns."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 3 0",
                "hub: blocked 1 0 [zone=blocked]",
                "hub: restricted 2 0 [zone=restricted]",
                "connection: start-blocked",
                "connection: blocked-end",
                "connection: start-restricted",
                "connection: restricted-end",
            ]
        )
        finder = Pathfinder(data)
        path = finder.find_shortest_path()
        self.assertEqual(path, ["start", "restricted", "end"])
        self.assertEqual(finder.path_cost(path), 3)

    def test_priority_zone_wins_equal_cost_tie(self) -> None:
        """Prefer a priority route when weighted costs are equal."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 2 0",
                "hub: alpha 1 0",
                "hub: zulu 1 1 [zone=priority]",
                "connection: start-alpha",
                "connection: alpha-end",
                "connection: start-zulu",
                "connection: zulu-end",
            ]
        )
        self.assertEqual(
            Pathfinder(data).find_shortest_path(),
            ["start", "zulu", "end"],
        )

    def test_reports_no_path(self) -> None:
        """Raise a clear error when blocked zones disconnect the graph."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 2 0",
                "hub: wall 1 0 [zone=blocked]",
                "connection: start-wall",
                "connection: wall-end",
            ]
        )
        with self.assertRaises(PathNotFoundError):
            Pathfinder(data).find_shortest_path()


if __name__ == "__main__":
    unittest.main()
