"""Weighted pathfinding for Fly-in maps."""

from heapq import heappop, heappush

from fly_in.models import MapData, ZoneType


class PathNotFoundError(Exception):
    """Raised when no valid route connects the start and end zones."""


class Pathfinder:
    """Find a cheapest valid route without external graph libraries."""

    def __init__(self, map_data: MapData) -> None:
        """Build and cache a bidirectional adjacency list."""
        self.map_data = map_data
        self.adjacency: dict[str, list[str]] = {
            name: [] for name in map_data.zones
        }
        for connection in map_data.connections:
            self.adjacency[connection.zone_a].append(connection.zone_b)
            self.adjacency[connection.zone_b].append(connection.zone_a)
        for neighbors in self.adjacency.values():
            neighbors.sort()

    def find_shortest_path(self) -> list[str]:
        """Find a minimum-cost path, preferring priority zones on ties."""
        start = self.map_data.start_name
        end = self.map_data.end_name
        if self.map_data.zones[start].zone_type == ZoneType.BLOCKED:
            raise PathNotFoundError("the start zone is blocked")
        if self.map_data.zones[end].zone_type == ZoneType.BLOCKED:
            raise PathNotFoundError("the end zone is blocked")

        # Labels compare cost first, then prefer more priority zones, then
        # fewer hops. The second value is negative for normal tuple ordering.
        labels: dict[str, tuple[int, int, int]] = {start: (0, 0, 0)}
        previous: dict[str, str] = {}
        queue: list[tuple[int, int, int, str]] = [(0, 0, 0, start)]

        while queue:
            cost, negative_priorities, hops, current = heappop(queue)
            label = (cost, negative_priorities, hops)
            if label != labels[current]:
                continue
            if current == end:
                return self.build_path(previous, end)

            for neighbor in self.adjacency[current]:
                zone = self.map_data.zones[neighbor]
                if zone.zone_type == ZoneType.BLOCKED:
                    continue
                priority_change = (
                    -1 if zone.zone_type == ZoneType.PRIORITY else 0
                )
                new_label = (
                    cost + self.movement_cost(neighbor),
                    negative_priorities + priority_change,
                    hops + 1,
                )
                if new_label < labels.get(neighbor, (2**63, 0, 0)):
                    labels[neighbor] = new_label
                    previous[neighbor] = current
                    heappush(queue, (*new_label, neighbor))

        raise PathNotFoundError(f"no valid path from {start} to {end}")

    def movement_cost(self, destination: str) -> int:
        """Return the turn cost of entering a destination zone."""
        zone_type = self.map_data.zones[destination].zone_type
        return 2 if zone_type == ZoneType.RESTRICTED else 1

    def path_cost(self, path: list[str]) -> int:
        """Calculate the weighted movement cost of a path."""
        return sum(self.movement_cost(name) for name in path[1:])

    def build_path(
        self, previous: dict[str, str], end: str
    ) -> list[str]:
        """Reconstruct a path from predecessor links."""
        path = [end]
        while path[-1] in previous:
            path.append(previous[path[-1]])
        path.reverse()
        return path
