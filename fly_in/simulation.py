"""Capacity-aware turn-by-turn simulation using one shared path."""

from fly_in.models import Drone, MapData, ZoneType


class SimulationError(Exception):
    """Raised when a simulation cannot run safely."""


class Simulation:
    """Move all drones from start to end through one shared path."""

    def __init__(self, map_data: MapData, path: list[str]) -> None:
        """Validate simulation input and initialize every drone.

        Args:
            map_data: Parsed network and drone count.
            path: Shared route from the start hub to the end hub.

        Raises:
            SimulationError: If the map or path cannot be simulated.
        """
        self.map_data = map_data
        self.path = path.copy()
        self.connection_capacities = self.build_connection_capacities()
        self.validate_path()
        if map_data.drone_count <= 0:
            raise SimulationError("drone count must be positive")
        self.drones = [
            Drone(identifier=identifier)
            for identifier in range(1, map_data.drone_count + 1)
        ]

    @staticmethod
    def connection_key(zone_a: str, zone_b: str) -> tuple[str, str]:
        """Return one direction-independent key for a connection."""
        return (
            (zone_a, zone_b) if zone_a < zone_b else (zone_b, zone_a)
        )

    def build_connection_capacities(self) -> dict[tuple[str, str], int]:
        """Cache each bidirectional connection's per-turn capacity."""
        capacities: dict[tuple[str, str], int] = {}
        for connection in self.map_data.connections:
            if connection.max_link_capacity <= 0:
                raise SimulationError(
                    f"connection '{connection.name()}' has invalid capacity"
                )
            key = self.connection_key(
                connection.zone_a, connection.zone_b
            )
            if key in capacities:
                raise SimulationError(
                    f"duplicate connection '{connection.name()}'"
                )
            capacities[key] = connection.max_link_capacity
        return capacities

    def validate_path(self) -> None:
        """Ensure the shared path is complete, accessible, and connected."""
        if len(self.path) < 2:
            raise SimulationError("path must contain at least start and end")
        if self.path[0] != self.map_data.start_name:
            raise SimulationError(
                f"path must start at '{self.map_data.start_name}'"
            )
        if self.path[-1] != self.map_data.end_name:
            raise SimulationError(
                f"path must end at '{self.map_data.end_name}'"
            )

        for name in self.path:
            zone = self.map_data.zones.get(name)
            if zone is None:
                raise SimulationError(f"unknown zone '{name}' in path")
            if zone.zone_type == ZoneType.BLOCKED:
                raise SimulationError(f"blocked zone '{name}' in path")
            if zone.max_drones <= 0:
                raise SimulationError(
                    f"zone '{name}' has invalid capacity"
                )

        # Check this zone and the zone after it are in the connections list
        for source, destination in zip(self.path, self.path[1:]):
            key = self.connection_key(source, destination)
            if key not in self.connection_capacities:
                raise SimulationError(
                    f"no connection between '{source}' and '{destination}'"
                )

    # Builds a dictionary that tells us how many
    # drones are currently inside each intermediate zone.
    def build_occupancy(self) -> dict[str, int]:
        """Count drones in capacity-limited intermediate zones."""
        occupancy: dict[str, int] = {}
        last_index = len(self.path) - 1

        for drone in self.drones:
            if drone.delivered:
                continue

            if drone.path_index < 0 or drone.path_index > last_index:
                raise SimulationError(
                    f"invalid path index for drone D{drone.identifier}"
                )

            # Ignore start and end.
            if drone.path_index in (0, last_index):
                continue

            zone_name = self.path[drone.path_index]
            occupancy[zone_name] = occupancy.get(zone_name, 0) + 1
        return occupancy

    def can_move(
        self,
        source: str,
        destination: str,
        occupancy: dict[str, int],
        connection_usage: dict[tuple[str, str], int],
    ) -> bool:
        """Check destination and connection capacity for one movement."""
        key = self.connection_key(source, destination)
        link_capacity = self.connection_capacities[key]
        if connection_usage.get(key, 0) >= link_capacity:
            return False
        if destination == self.map_data.end_name:
            return True
        zone = self.map_data.zones[destination]
        return occupancy.get(destination, 0) < zone.max_drones

    def apply_move(
        self,
        drone: Drone,
        destination: str,
        occupancy: dict[str, int],
    ) -> None:
        """Move one drone and update occupancy immediately."""
        source = self.path[drone.path_index]
        if source not in (
            self.map_data.start_name,
            self.map_data.end_name,
        ):
            source_count = occupancy.get(source, 0)
            if source_count <= 0:
                raise SimulationError(
                    f"invalid occupancy for zone '{source}'"
                )
            occupancy[source] = source_count - 1

        if destination != self.map_data.end_name:
            occupancy[destination] = occupancy.get(destination, 0) + 1

        drone.path_index += 1
        if destination == self.map_data.end_name:
            drone.delivered = True

    def run_turn(self) -> list[tuple[int, str]]:
        """Run one turn and return successful movements by drone ID."""
        occupancy = self.build_occupancy()
        connection_usage: dict[tuple[str, str], int] = {}

        # Sort by index descending for not delivered
        active_drones = sorted(
            (drone for drone in self.drones if not drone.delivered),
            key=lambda drone: (-drone.path_index, drone.identifier),
        )

        movements: list[tuple[int, str]] = []
        last_index = len(self.path) - 1

        for drone in active_drones:
            if drone.path_index < 0 or drone.path_index >= last_index:
                raise SimulationError(
                    f"invalid path index for drone D{drone.identifier}"
                )
            source = self.path[drone.path_index]
            destination = self.path[drone.path_index + 1]
            if not self.can_move(
                source, destination, occupancy, connection_usage
            ):
                continue
            self.apply_move(drone, destination, occupancy)
            key = self.connection_key(source, destination)
            connection_usage[key] = connection_usage.get(key, 0) + 1
            movements.append(
                (drone.identifier, f"D{drone.identifier}-{destination}")
            )

        movements.sort(key=lambda movement: movement[0])
        return movements

    def run(self) -> list[str]:
        """Run turns until all drones are delivered or movement deadlocks."""
        turns: list[str] = []

        while not all(drone.delivered for drone in self.drones):
            movements = self.run_turn()
            if not movements:
                raise SimulationError("simulation is deadlocked")
            turns.append(" ".join(text for _, text in movements))
        return turns
