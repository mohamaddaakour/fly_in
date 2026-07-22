"""Multi-route capacity-aware drone simulation."""

from typing import cast

from fly_in.models import Drone, MapData, ZoneType


ConnectionKey = tuple[str, str]
Occupancy = dict[str, int]


class SimulationError(Exception):
    """Raised when a simulation cannot run safely."""


class Simulation:
    """Assign drones to routes and simulate all movements safely."""

    def __init__(
        self,
        map_data: MapData,
        paths: list[str] | list[list[str]],
    ) -> None:
        """Validate routes, assign drones, and initialize shared state."""
        self.map_data = map_data
        self.connection_capacities = self.build_connection_capacities()
        self.paths = self.normalize_paths(paths)
        for path in self.paths:
            self.validate_path(path)
        if map_data.drone_count <= 0:
            raise SimulationError("drone count must be positive")

        # Retained as a read-only compatibility view of the first route.
        self.path = self.paths[0]
        assignments = self.assign_paths(map_data.drone_count)
        self.drones = [
            Drone(identifier=identifier, assigned_path=assigned_path.copy())
            for identifier, assigned_path in enumerate(assignments, start=1)
        ]

    def normalize_paths(
        self, paths: list[str] | list[list[str]]
    ) -> list[list[str]]:
        """Copy either one route or a collection of routes and deduplicate."""
        if not paths:
            raise SimulationError("at least one path is required")
        first = paths[0]
        if isinstance(first, str):
            normalized = [cast(list[str], paths).copy()]
        else:
            normalized = [
                path.copy() for path in cast(list[list[str]], paths)
            ]
        if any(not path for path in normalized):
            raise SimulationError("paths cannot be empty")

        unique: list[list[str]] = []
        seen: set[tuple[str, ...]] = set()
        for path in normalized:
            key = tuple(path)
            if key not in seen:
                unique.append(path)
                seen.add(key)
        return unique

    @staticmethod
    def connection_key(zone_a: str, zone_b: str) -> ConnectionKey:
        """Return one direction-independent key for a connection."""
        return (
            (zone_a, zone_b) if zone_a < zone_b else (zone_b, zone_a)
        )

    def build_connection_capacities(self) -> dict[ConnectionKey, int]:
        """Cache each bidirectional connection's per-turn capacity."""
        capacities: dict[ConnectionKey, int] = {}
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

    def validate_path(self, path: list[str]) -> None:
        """Ensure one route is complete, accessible, and connected."""
        if len(path) < 2:
            raise SimulationError("path must contain at least start and end")
        if path[0] != self.map_data.start_name:
            raise SimulationError(
                f"path must start at '{self.map_data.start_name}'"
            )
        if path[-1] != self.map_data.end_name:
            raise SimulationError(
                f"path must end at '{self.map_data.end_name}'"
            )

        for name in path:
            zone = self.map_data.zones.get(name)
            if zone is None:
                raise SimulationError(f"unknown zone '{name}' in path")
            if zone.zone_type == ZoneType.BLOCKED:
                raise SimulationError(f"blocked zone '{name}' in path")
            if zone.max_drones <= 0:
                raise SimulationError(
                    f"zone '{name}' has invalid capacity"
                )
        for source, destination in zip(path, path[1:]):
            key = self.connection_key(source, destination)
            if key not in self.connection_capacities:
                raise SimulationError(
                    f"no connection between '{source}' and '{destination}'"
                )

    def path_cost(self, path: list[str]) -> int:
        """Return actual travel turns for one unloaded route."""
        return sum(
            2
            if self.map_data.zones[name].zone_type == ZoneType.RESTRICTED
            else 1
            for name in path[1:]
        )

    def path_priority_count(self, path: list[str]) -> int:
        """Count preferred zones on a route for deterministic ties."""
        return sum(
            self.map_data.zones[name].zone_type == ZoneType.PRIORITY
            for name in path[1:]
        )

    def expected_completion(self, path: list[str], load: int) -> int:
        """Estimate when the next assigned drone would finish this route."""
        congestion = 0
        for source, destination in zip(path, path[1:]):
            capacity = self.connection_capacities[
                self.connection_key(source, destination)
            ]
            interval = (
                2
                if self.map_data.zones[destination].zone_type
                == ZoneType.RESTRICTED
                else 1
            )
            congestion = max(congestion, interval * (load // capacity))
        for name in path[1:-1]:
            capacity = self.map_data.zones[name].max_drones
            congestion = max(congestion, load // capacity)
        return self.path_cost(path) + congestion

    def assign_paths(self, drone_count: int) -> list[list[str]]:
        """Assign each drone to its lowest expected completion time."""
        loads = [0] * len(self.paths)
        assignments: list[list[str]] = []
        for _ in range(drone_count):
            index = min(
                range(len(self.paths)),
                key=lambda path_index: (
                    self.expected_completion(
                        self.paths[path_index], loads[path_index]
                    ),
                    self.path_cost(self.paths[path_index]),
                    -self.path_priority_count(self.paths[path_index]),
                    len(self.paths[path_index]),
                    tuple(self.paths[path_index]),
                ),
            )
            assignments.append(self.paths[index])
            loads[index] += 1
        return assignments

    def drone_path(self, drone: Drone) -> list[str]:
        """Return a drone's validated assigned route."""
        if not drone.assigned_path:
            raise SimulationError(
                f"drone D{drone.identifier} has no assigned path"
            )
        return drone.assigned_path

    def validate_drone_state(self, drone: Drone) -> None:
        """Reject impossible delivery, path-index, or transit state."""
        path = self.drone_path(drone)
        last_index = len(path) - 1
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
            destination = path[drone.path_index + 1]
            if (
                self.map_data.zones[destination].zone_type
                != ZoneType.RESTRICTED
            ):
                drone_name = f"D{drone.identifier}"
                raise SimulationError(
                    f"invalid transit destination for drone {drone_name}"
                )

    def build_occupancy(self) -> Occupancy:
        """Count drones physically inside shared intermediate zones."""
        occupancy: Occupancy = {}
        for drone in self.drones:
            self.validate_drone_state(drone)
            if drone.delivered or drone.transit_turns_remaining > 0:
                continue
            path = self.drone_path(drone)
            zone_name = path[drone.path_index]
            if zone_name in (
                self.map_data.start_name,
                self.map_data.end_name,
            ):
                continue
            occupancy[zone_name] = occupancy.get(zone_name, 0) + 1
        return occupancy

    def build_reservations(self) -> Occupancy:
        """Count destination slots promised to in-transit drones."""
        reservations: Occupancy = {}
        for drone in self.drones:
            self.validate_drone_state(drone)
            if drone.transit_turns_remaining == 0:
                continue
            path = self.drone_path(drone)
            destination = path[drone.path_index + 1]
            if destination == self.map_data.end_name:
                continue
            reservations[destination] = reservations.get(destination, 0) + 1
        return reservations

    def build_connection_usage(self) -> dict[ConnectionKey, int]:
        """Count links occupied by drones completing transit this turn."""
        usage: dict[ConnectionKey, int] = {}
        for drone in self.drones:
            if drone.transit_turns_remaining == 0:
                continue
            path = self.drone_path(drone)
            source = path[drone.path_index]
            destination = path[drone.path_index + 1]
            key = self.connection_key(source, destination)
            usage[key] = usage.get(key, 0) + 1
        return usage

    def can_depart(
        self,
        source: str,
        destination: str,
        occupancy: Occupancy,
        reservations: Occupancy,
        connection_usage: dict[ConnectionKey, int],
    ) -> bool:
        """Check global link and promised destination capacity."""
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

    def free_source(
        self, drone: Drone, path: list[str], occupancy: Occupancy
    ) -> None:
        """Release a drone's intermediate source-zone capacity."""
        source = path[drone.path_index]
        if source in (self.map_data.start_name, self.map_data.end_name):
            return
        source_count = occupancy.get(source, 0)
        if source_count <= 0:
            raise SimulationError(f"invalid occupancy for zone '{source}'")
        occupancy[source] = source_count - 1

    def apply_normal_move(
        self,
        drone: Drone,
        path: list[str],
        destination: str,
        occupancy: Occupancy,
    ) -> None:
        """Apply a one-turn movement into a non-restricted zone."""
        self.free_source(drone, path, occupancy)
        if destination != self.map_data.end_name:
            occupancy[destination] = occupancy.get(destination, 0) + 1
        drone.path_index += 1
        if destination == self.map_data.end_name:
            drone.delivered = True

    def begin_restricted_transit(
        self,
        drone: Drone,
        path: list[str],
        destination: str,
        occupancy: Occupancy,
        reservations: Occupancy,
    ) -> None:
        """Put a drone on a link and reserve its destination slot."""
        self.free_source(drone, path, occupancy)
        if destination != self.map_data.end_name:
            reservations[destination] = reservations.get(destination, 0) + 1
        drone.transit_turns_remaining = 1

    def complete_restricted_transit(
        self,
        drone: Drone,
        occupancy: Occupancy,
        reservations: Occupancy,
    ) -> str:
        """Force an in-transit drone into its reserved destination."""
        self.validate_drone_state(drone)
        path = self.drone_path(drone)
        destination = path[drone.path_index + 1]
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

    def remaining_cost(self, drone: Drone) -> int:
        """Return remaining weighted turns for movement ordering."""
        path = self.drone_path(drone)
        return sum(
            2
            if self.map_data.zones[name].zone_type == ZoneType.RESTRICTED
            else 1
            for name in path[drone.path_index + 1:]
        )

    def run_turn(self) -> list[tuple[int, str]]:
        """Run one simultaneous turn across all assigned routes."""
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
            key=lambda drone: (self.remaining_cost(drone), drone.identifier),
        )
        for drone in active_drones:
            self.validate_drone_state(drone)
            path = self.drone_path(drone)
            source = path[drone.path_index]
            destination = path[drone.path_index + 1]
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
                    drone, path, destination, occupancy, reservations
                )
                movement = f"D{drone.identifier}-{source}-{destination}"
            else:
                self.apply_normal_move(
                    drone, path, destination, occupancy
                )
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
