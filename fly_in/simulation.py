"""Capacity-aware simulation with restricted-zone transit."""

from fly_in.models import Drone, MapData, ZoneType


class SimulationError(Exception):
    """Raised when a simulation cannot run safely."""


class Simulation:
    """Move all drones through one shared, capacity-safe path."""

    def __init__(self, map_data: MapData, path: list[str]) -> None:
        """Validate input and initialize every drone at the start hub."""
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

        for source, destination in zip(self.path, self.path[1:]):
            key = self.connection_key(source, destination)
            if key not in self.connection_capacities:
                raise SimulationError(
                    f"no connection between '{source}' and '{destination}'"
                )

    def validate_drone_state(self, drone: Drone) -> None:
        """Reject impossible delivery, path-index, or transit state."""
        last_index = len(self.path) - 1
        if drone.path_index < 0 or drone.path_index > last_index:
            raise SimulationError(
                f"invalid path index for drone D{drone.identifier}"
            )
        if drone.transit_turns_remaining not in (0, 1):
            raise SimulationError(
                f"invalid transit state for drone D{drone.identifier}"
            )
        if drone.delivered:
            if (
                drone.path_index != last_index
                or drone.transit_turns_remaining != 0
            ):
                raise SimulationError(
                    f"invalid delivered state for drone D{drone.identifier}"
                )
            return
        if drone.path_index == last_index:
            raise SimulationError(
                f"invalid delivery state for drone D{drone.identifier}"
            )
        if drone.transit_turns_remaining == 1:
            destination = self.path[drone.path_index + 1]
            if (
                self.map_data.zones[destination].zone_type
                != ZoneType.RESTRICTED
            ):
                drone_name = f"D{drone.identifier}"
                raise SimulationError(
                    f"invalid transit destination for drone {drone_name}"
                )

    def build_occupancy(self) -> dict[str, int]:
        """Count drones physically inside intermediate zones."""
        occupancy: dict[str, int] = {}
        for drone in self.drones:
            self.validate_drone_state(drone)
            if drone.delivered or drone.transit_turns_remaining > 0:
                continue
            zone_name = self.path[drone.path_index]
            if zone_name in (
                self.map_data.start_name,
                self.map_data.end_name,
            ):
                continue
            occupancy[zone_name] = occupancy.get(zone_name, 0) + 1
        return occupancy

    def build_reservations(self) -> dict[str, int]:
        """Count destination slots promised to in-transit drones."""
        reservations: dict[str, int] = {}
        for drone in self.drones:
            self.validate_drone_state(drone)
            if drone.transit_turns_remaining == 0:
                continue
            destination = self.path[drone.path_index + 1]
            if destination == self.map_data.end_name:
                continue
            reservations[destination] = reservations.get(destination, 0) + 1

        return reservations

    def build_connection_usage(self) -> dict[tuple[str, str], int]:
        """Count links occupied by drones completing transit this turn."""
        usage: dict[tuple[str, str], int] = {}
        for drone in self.drones:
            if drone.transit_turns_remaining == 0:
                continue
            source = self.path[drone.path_index]
            destination = self.path[drone.path_index + 1]
            key = self.connection_key(source, destination)
            usage[key] = usage.get(key, 0) + 1
        return usage

    def can_depart(
        self,
        source: str,
        destination: str,
        occupancy: dict[str, int],
        reservations: dict[str, int],
        connection_usage: dict[tuple[str, str], int],
    ) -> bool:
        """Check link capacity and all promised destination capacity."""
        key = self.connection_key(source, destination)
        if (
            connection_usage.get(key, 0)
            >= self.connection_capacities[key]
        ):
            return False
        if destination == self.map_data.end_name:
            return True
        used_capacity = occupancy.get(destination, 0) + reservations.get(
            destination, 0
        )
        return used_capacity < self.map_data.zones[destination].max_drones

    def free_source(self, drone: Drone, occupancy: dict[str, int]) -> None:
        """Release a drone's intermediate source-zone capacity."""
        source = self.path[drone.path_index]
        if source in (self.map_data.start_name, self.map_data.end_name):
            return
        source_count = occupancy.get(source, 0)
        if source_count <= 0:
            raise SimulationError(f"invalid occupancy for zone '{source}'")
        occupancy[source] = source_count - 1

    def apply_normal_move(
        self, drone: Drone, destination: str, occupancy: dict[str, int]
    ) -> None:
        """Apply a one-turn movement into a non-restricted zone."""
        self.free_source(drone, occupancy)
        if destination != self.map_data.end_name:
            occupancy[destination] = occupancy.get(destination, 0) + 1
        drone.path_index += 1
        if destination == self.map_data.end_name:
            drone.delivered = True

    def begin_restricted_transit(
        self,
        drone: Drone,
        destination: str,
        occupancy: dict[str, int],
        reservations: dict[str, int],
    ) -> None:
        """Put a drone on a link and reserve its required destination slot."""
        self.free_source(drone, occupancy)
        if destination != self.map_data.end_name:
            reservations[destination] = reservations.get(destination, 0) + 1
        drone.transit_turns_remaining = 1

    def complete_restricted_transit(
        self,
        drone: Drone,
        occupancy: dict[str, int],
        reservations: dict[str, int],
    ) -> str:
        """Force an in-transit drone to arrive at its reserved destination."""
        self.validate_drone_state(drone)
        destination = self.path[drone.path_index + 1]
        if destination != self.map_data.end_name:
            reserved = reservations.get(destination, 0)
            if reserved <= 0:
                raise SimulationError(
                    f"missing reservation for drone D{drone.identifier}"
                )
            reservations[destination] = reserved - 1
            occupancy[destination] = occupancy.get(destination, 0) + 1
            if (
                occupancy[destination]
                > self.map_data.zones[destination].max_drones
            ):
                raise SimulationError(
                    f"reserved capacity exceeded in zone '{destination}'"
                )
        drone.path_index += 1
        drone.transit_turns_remaining = 0
        if destination == self.map_data.end_name:
            drone.delivered = True
        return destination

    def run_turn(self) -> list[tuple[int, str]]:
        """Run one simultaneous turn and return successful movements."""
        occupancy = self.build_occupancy()
        reservations = self.build_reservations()
        connection_usage = self.build_connection_usage()
        movements: list[tuple[int, str]] = []
        moved_ids: set[int] = set()

        arriving = sorted(
            (
                drone
                for drone in self.drones
                if drone.transit_turns_remaining > 0
            ),
            key=lambda drone: drone.identifier,
        )
        for drone in arriving:
            destination = self.complete_restricted_transit(
                drone, occupancy, reservations
            )
            movements.append(
                (drone.identifier, f"D{drone.identifier}-{destination}")
            )
            moved_ids.add(drone.identifier)

        active_drones = sorted(
            (
                drone
                for drone in self.drones
                if not drone.delivered
                and drone.identifier not in moved_ids
                and drone.transit_turns_remaining == 0
            ),
            key=lambda drone: (-drone.path_index, drone.identifier),
        )
        for drone in active_drones:
            self.validate_drone_state(drone)
            source = self.path[drone.path_index]
            destination = self.path[drone.path_index + 1]
            if not self.can_depart(
                source,
                destination,
                occupancy,
                reservations,
                connection_usage,
            ):
                continue

            key = self.connection_key(source, destination)
            connection_usage[key] = connection_usage.get(key, 0) + 1
            if (
                self.map_data.zones[destination].zone_type
                == ZoneType.RESTRICTED
            ):
                self.begin_restricted_transit(
                    drone, destination, occupancy, reservations
                )
                connection_name = f"{source}-{destination}"
                movement = f"D{drone.identifier}-{connection_name}"
            else:
                self.apply_normal_move(drone, destination, occupancy)
                movement = f"D{drone.identifier}-{destination}"
            movements.append((drone.identifier, movement))

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
