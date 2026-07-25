"""Weighted single- and multiple-route pathfinding."""

from heapq import heappop, heappush

from fly_in.models import MapData, ZoneType


PathScore = tuple[int, int, int]
DirectedEdge = tuple[str, str]


class PathNotFoundError(Exception):
    """Raised when no valid route connects the start and end zones."""


class Pathfinder:
    """Find and cache cheapest loopless routes without graph libraries."""

    def __init__(self, map_data: MapData) -> None:
        """Build and cache a deterministic bidirectional adjacency list."""
        self.map_data = map_data

        # Zone names as keys and list of negihbors
        # Initialzie the list
        self.adjacency: dict[str, list[str]] = {
            name: [] for name in map_data.zones
        }

        # Fill the lists of neighbors lists for each zone
        for connection in map_data.connections:
            self.adjacency[connection.zone_a].append(connection.zone_b)
            self.adjacency[connection.zone_b].append(connection.zone_a)

        # Sort all neighbors lists
        for neighbors in self.adjacency.values():
            neighbors.sort()

        # This stores previously calculated path results.
        self._path_cache: dict[int, tuple[tuple[str, ...], ...]] = {}

    def find_shortest_path(self) -> list[str]:
        """Return the best weighted route from start to end."""
        return self.find_paths(1)[0]

    def find_paths(self, max_paths: int | None = None) -> list[list[str]]:
        """Return up to ``max_paths`` cheapest loopless routes using Yen.

        Results are ordered by movement cost, priority preference, hop count,
        and finally zone names. Results are cached by requested path count.
        """
        limit = self.map_data.drone_count if max_paths is None else max_paths

        if limit <= 0:
            raise ValueError("max_paths must be positive")

        # Try to retrieve a previously calculated result for this limit.
        cached = self._path_cache.get(limit)

        if cached is not None:
            return [list(path) for path in cached]

        self.validate_endpoints()

        first_path = self.shortest_route(
            self.map_data.start_name,
            self.map_data.end_name,
            set(),
            set(),
        )

        if first_path is None:
            raise PathNotFoundError(
                f"no valid path from {self.map_data.start_name} "
                f"to {self.map_data.end_name}"
            )

        selected: list[list[str]] = [first_path]
        selected_keys = {tuple(first_path)}
        candidates: list[tuple[PathScore, tuple[str, ...], list[str]]] = []
        candidate_keys: set[tuple[str, ...]] = set()

        while len(selected) < limit:
            # Use the latest selected path.
            previous_path = selected[-1]

            for index in range(len(previous_path) - 1):
                root = previous_path[:index + 1]
                banned_edges: set[DirectedEdge] = set()

                for path in selected:
                    if path[:index + 1] == root and len(path) > index + 1:
                        banned_edges.add((path[index], path[index + 1]))

                spur = self.shortest_route(
                    root[-1],
                    self.map_data.end_name,
                    set(root[:-1]),
                    banned_edges,
                )

                if spur is None:
                    continue

                candidate = root[:-1] + spur
                candidate_key = tuple(candidate)

                if (
                    candidate_key in selected_keys
                    or candidate_key in candidate_keys
                ):
                    continue

                heappush(
                    candidates,
                    (self.path_score(candidate), candidate_key, candidate),
                )

                candidate_keys.add(candidate_key)

            if not candidates:
                break
            
            _, candidate_key, next_path = heappop(candidates)
            candidate_keys.remove(candidate_key)
            selected.append(next_path)
            selected_keys.add(candidate_key)

        frozen = tuple(tuple(path) for path in selected)
        self._path_cache[limit] = frozen
        return [list(path) for path in frozen]

    # Check the start zone and the end zone are not blocked
    def validate_endpoints(self) -> None:
        """Reject blocked start or end zones before searching."""
        start = self.map_data.start_name
        end = self.map_data.end_name
        if self.map_data.zones[start].zone_type == ZoneType.BLOCKED:
            raise PathNotFoundError("the start zone is blocked")
        if self.map_data.zones[end].zone_type == ZoneType.BLOCKED:
            raise PathNotFoundError("the end zone is blocked")

    # We're not writing a normal Dijkstra.
    # We're writing the version used inside Yen's Algorithm,
    # which repeatedly asks Dijkstra:
    # "Find another shortest path, but don't use these nodes or these edges."
    # for that reason we pass banned_nodes and banned_edges
    def shortest_route(
        self,
        start: str,
        end: str,
        banned_nodes: set[str],
        banned_edges: set[DirectedEdge],
    ) -> list[str] | None:
        """Run constrained Dijkstra for one Yen spur route."""
        if start in banned_nodes or end in banned_nodes:
            return None

        # (cost, negative_priorities, hops)
        labels: dict[str, PathScore] = {start: (0, 0, 0)}

        # Saves each zone where it comes from.
        previous: dict[str, str] = {}

        # priority queue
        # (cost, priorities, hops, current_zone)
        queue: list[tuple[int, int, int, str]] = [(0, 0, 0, start)]

        while queue:
            cost, negative_priorities, hops, current = heappop(queue)
            label = (cost, negative_priorities, hops)

            # One zone can be discovered more than one time
            # so in this case the lower cost will be first so we continue
            if label != labels[current]:
                continue

            # We get to the end so we finish the algorithm
            if current == end:
                return self.build_path(previous, end)

            # We get to all neighbors of this zone
            for neighbor in self.adjacency[current]:
                if neighbor in banned_nodes:
                    continue

                if (current, neighbor) in banned_edges:
                    continue

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

        return None

    # Return the cost of the zone
    # Restricted zone cost: 2
    # Normal zone cost: 1
    def movement_cost(self, destination: str) -> int:
        """Return the turn cost of entering a destination zone."""
        zone_type = self.map_data.zones[destination].zone_type
        return 2 if zone_type == ZoneType.RESTRICTED else 1

    def path_score(self, path: list[str]) -> PathScore:
        """Return cost, priority preference, and hop count for a path."""
        priority_count = sum(
            self.map_data.zones[name].zone_type == ZoneType.PRIORITY
            for name in path[1:]
        )
        return self.path_cost(path), -priority_count, len(path) - 1

    def path_cost(self, path: list[str]) -> int:
        """Calculate the weighted movement cost of a path."""
        return sum(self.movement_cost(name) for name in path[1:])

    # Build the exact path from start to end
    # When we apply dijkstra algorithm we are saving the previous nodes
    # for each zone so using it we will get the correct path
    def build_path(
        self, previous: dict[str, str], end: str
    ) -> list[str]:
        """Reconstruct a path from predecessor links."""
        path = [end]
        while path[-1] in previous:
            path.append(previous[path[-1]])
        path.reverse()
        return path
