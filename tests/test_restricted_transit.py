"""Tests for Phase 6 restricted-zone multi-turn movement."""

import unittest

from fly_in.models import ZoneType
from fly_in.parser import MapParser
from fly_in.simulation import Simulation, SimulationError


def restricted_simulation(
    drone_count: int,
    zone_capacity: int = 1,
    link_capacity: int = 1,
) -> Simulation:
    """Build a direct route into one restricted intermediate zone."""
    data = MapParser().parse_lines(
        [
            f"nb_drones: {drone_count}",
            "start_hub: start 0 0",
            "end_hub: end 2 0",
            (
                "hub: secure 1 0 "
                f"[zone=restricted max_drones={zone_capacity}]"
            ),
            (
                "connection: start-secure "
                f"[max_link_capacity={link_capacity}]"
            ),
            (
                "connection: secure-end "
                f"[max_link_capacity={link_capacity}]"
            ),
        ]
    )
    return Simulation(data, ["start", "secure", "end"])


class RestrictedTransitOutputTests(unittest.TestCase):
    """Verify two-turn state and official connection output."""

    def test_subject_phase6_example(self) -> None:
        """Print the connection turn followed by forced arrival."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 3 0",
                "hub: a 1 0",
                "hub: restrictedZone 2 0 [zone=restricted]",
                "connection: start-a",
                "connection: a-restrictedZone",
                "connection: restrictedZone-end",
            ]
        )
        turns = Simulation(
            data, ["start", "a", "restrictedZone", "end"]
        ).run()
        self.assertEqual(
            turns,
            [
                "D1-a",
                "D1-a-restrictedZone",
                "D1-restrictedZone",
                "D1-end",
            ],
        )

    def test_link_remains_occupied_until_arrival_turn_finishes(self) -> None:
        """Prevent a new departure while the prior drone arrives."""
        turns = restricted_simulation(2).run()
        self.assertEqual(
            turns,
            [
                "D1-start-secure",
                "D1-secure",
                "D1-end D2-start-secure",
                "D2-secure",
                "D2-end",
            ],
        )

    def test_parallel_transit_respects_link_and_zone_capacity(self) -> None:
        """Move batches only when both restricted capacities allow them."""
        turns = restricted_simulation(
            4, zone_capacity=2, link_capacity=2
        ).run()
        self.assertEqual(
            turns,
            [
                "D1-start-secure D2-start-secure",
                "D1-secure D2-secure",
                "D1-end D2-end D3-start-secure D4-start-secure",
                "D3-secure D4-secure",
                "D3-end D4-end",
            ],
        )

    def test_destination_reservation_blocks_excess_departures(self) -> None:
        """Reserve a restricted slot before a drone enters its link."""
        simulation = restricted_simulation(
            2, zone_capacity=1, link_capacity=2
        )
        first_turn = simulation.run_turn()
        self.assertEqual(first_turn, [(1, "D1-start-secure")])
        self.assertEqual(simulation.drones[0].transit_turns_remaining, 1)
        self.assertEqual(simulation.drones[1].transit_turns_remaining, 0)

    def test_restricted_end_uses_unlimited_destination_capacity(self) -> None:
        """Reserve no finite slot when the restricted destination is end."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 2",
                "start_hub: start 0 0",
                "end_hub: end 1 0 [zone=restricted]",
                "connection: start-end [max_link_capacity=2]",
            ]
        )
        turns = Simulation(data, ["start", "end"]).run()
        self.assertEqual(
            turns,
            ["D1-start-end D2-start-end", "D1-end D2-end"],
        )


class RestrictedTransitStateTests(unittest.TestCase):
    """Verify transit invariants and occupancy accounting."""

    def test_in_transit_drone_no_longer_occupies_source(self) -> None:
        """Free source capacity as soon as restricted transit begins."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 2",
                "start_hub: start 0 0",
                "end_hub: end 3 0",
                "hub: staging 1 0",
                "hub: secure 2 0 [zone=restricted]",
                "connection: start-staging",
                "connection: staging-secure",
                "connection: secure-end",
            ]
        )
        simulation = Simulation(
            data, ["start", "staging", "secure", "end"]
        )
        simulation.run_turn()
        second_turn = simulation.run_turn()
        self.assertEqual(
            second_turn,
            [(1, "D1-staging-secure"), (2, "D2-staging")],
        )

    def test_rejects_invalid_transit_state(self) -> None:
        """Fail clearly if transit state targets a normal zone."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 2 0",
                "hub: normal 1 0",
                "connection: start-normal",
                "connection: normal-end",
            ]
        )
        simulation = Simulation(data, ["start", "normal", "end"])
        simulation.drones[0].transit_turns_remaining = 1
        with self.assertRaisesRegex(
            SimulationError, "invalid transit destination"
        ):
            simulation.run_turn()

    def test_restricted_zone_type_is_preserved(self) -> None:
        """Confirm the test fixture exercises a restricted destination."""
        simulation = restricted_simulation(1)
        self.assertEqual(
            simulation.map_data.zones["secure"].zone_type,
            ZoneType.RESTRICTED,
        )


if __name__ == "__main__":
    unittest.main()
