"""Weighted pathfinding for Fly-in maps."""

# heapq implements a priority queue (min-heap)
from heapq import heappop, heappush

from fly_in.models import MapData, ZoneType


# we create a new custom exception
class PathNotFoundError(Exception):
    """Raised when the end zone cannot be reached from the start zone."""


class Pathfinder:
    """Find a cheapest valid route without using external graph libraries."""

    def __init__(self, map_data: MapData):
        """Build an adjacency list once for repeated path searches."""
        self.map_data = map_data

        # this is a dictionary that contain each zone as keys
        # and their adjacent zones for each one
        # per example: { "start": ["A"] }
        # first each zone the value of it will be an empty list
        self.adjacency: dict[str, list[str]] = {
            name: [] for name in map_data.zones
        }

        # we fill the connection list for each key in adjacency
        for connection in map_data.connections:
            self.adjacency[connection.zone_a].append(connection.zone_b)
            self.adjacency[connection.zone_b].append(connection.zone_a)

    
    def find_shortest_path(self) -> list[str]:
        """Return a minimum-cost path using Dijkstra's algorithm."""

        start = self.map_data.start_name
        end = self.map_data.end_name

        # distances keeps the cheapest known cost to reach each zone
        distances: dict[str, int] = { start: 0 }

        # previous remembers how we reached every zone
        previous: dict[str, str] = {}

        # each item in the queue is a zone with this tuple:
        # (cost, priority_rank, zone_name)
        queue: list[tuple[int, int, str]] = [(0, 0, start)]

        while queue:
            # Remove the cheapest zone currently in the queue
            cost, _, current = heappop(queue)

            # if the cost before for a specific zone is different
            # from the cost now this means we discovered a better
            # path so we will ignore now
            if cost != distances[current]:
                continue

            # If we've reached the destination,
            # reconstruct and return the path
            if current == end:
                return self.build_path(previous, end)
            
            # Visit every neighboring zone
            for neighbor in self.adjacency[current]:
                zone = self.map_data.zones[neighbor]

                # skip blockedzones
                if zone.zone_type == ZoneType.BLOCKED:
                    continue

                # Calculate the total cost of reaching this neighbor
                new_cost = cost + self.movement_cost(neighbor)

                # If the neighbor has never been visited,
                # use a very large number as its initial cost
                if new_cost < distances.get(neighbor, 2 ** 63 - 1):
                    distances[neighbor] = new_cost
                    previous[neighbor] = current

                    priority_rank = (
                        0 if zone.zone_type == ZoneType.PRIORITY else 1
                    )

                    heappush(
                        queue,
                        (new_cost, priority_rank, neighbor)
                    )

        # No path exists.
        raise PathNotFoundError(
            f"no valid path from {self.map_data.start_name} "
            f"to {self.map_data.end_name}"
        )


    # return the destination cost by giving it the destination
    # zone
    def movement_cost(self, destination: str) -> int:
        """Return the cost of entering a destination zone."""

        # Get the destination's zone type.
        zone_type = self.map_data.zones[destination].zone_type

        # Restricted zones cost 2 moves.
        # Every other zone costs 1 move.
        return 2 if zone_type == ZoneType.RESTRICTED else 1


    def path_cost(self, path: list[str]) -> int:
        """Calculate the total cost of an already existing path."""

        # Skip path[0] because the starting zone costs nothing
        # to stand on.
        return sum(
            self.movement_cost(name)
            for name in path[1:]
        )


    # function to build the path
    def build_path(
        self,
        previous: dict[str, str],
        end: str
    ) -> list[str]:
        """Reconstruct the final path."""

        # start from the destination
        path = [end]

        # walk backward
        while path[-1] in previous:
            path.append(previous[path[-1]])

        # we reverse it to get the correct path
        path.reverse()

        return path
