*This project has been created as part of the 42 curriculum by mdaakour.*

# Fly-in

## Description

Fly-in is a Python drone-routing simulator. The final program will parse a graph of
zones, route multiple drones from a start hub to an end hub, and output each
simulation turn while respecting zone and connection capacity rules.

Current phase: Phase 5. The program strictly parses and validates map files,
finds one minimum-cost valid path, and moves every drone through that shared
path one turn at a time. Blocked zones are excluded, entering a restricted zone
has pathfinding cost two, and priority zones win equal-cost path ties.

## Instructions

Install development dependencies:

```bash
make install
```

Run the program with the example map:

```bash
make run
```

Run with a custom map:

```bash
python main.py path/to/map
```

Run the automated tests and mandatory quality checks:

```bash
make test
make lint
```

Successful runs print only the official movement lines. Each entry uses
`D<ID>-<zone>`, waiting drones are omitted, and each line represents one turn.

Example:

```text
D1-a
D1-b D2-a
D1-end D2-b D3-a
D2-end D3-b
D3-end
```

## Algorithm

The parser processes the input once and rejects malformed declarations with a
line number and cause. Connections are stored as bidirectional adjacency lists.

Pathfinding uses a custom Dijkstra implementation. Its comparison label contains
the total movement cost, the number of priority zones, and the hop count—in that
order. This produces a minimum-cost path while preferring priority zones on
equal-cost routes. Building the graph is `O(V + E)` in time and memory. The path
search is `O((V + E) log V)` time and `O(V + E)` memory, where `V` is the number
of zones and `E` is the number of connections.

## Capacity-Aware Simulation

Every drone receives an identifier beginning at `D1` and stores its current
index in the shared path. Drones closest to the end are evaluated first, which
lets a drone leaving a zone free that capacity for a following drone during the
same turn. Start and end capacity is unlimited; every intermediate zone obeys
its `max_drones` value. A drone that cannot enter the next zone waits silently,
and delivered drones no longer participate. A turn with no movement while
drones remain raises a clear deadlock error.

Every connection also enforces `max_link_capacity` per turn. Connection keys are
direction-independent because links are bidirectional, and usage is rebuilt at
the beginning of each turn. A move is approved only when both its destination
zone and its connection have capacity. This prevents link overuse while still
letting a drone moving out free zone space for another drone in the same turn.

For Phase 5, each edge still takes one simulation turn. The two-turn transit
behavior of restricted zones belongs to Phase 6.

With `D` drones, path length `P`, and `T` turns, initialization is `O(D)`.
Occupancy, connection usage, and movement processing are `O(D)` per turn, while
ordering active drones is `O(D log D)`. Total simulation time is
`O(T * D log D)`. Cached connection capacities use `O(E)` memory, so live state
uses `O(D + P + E)` memory, excluding retained output lines.

## Resources

- [Python documentation](https://docs.python.org/3/)
- [heapq documentation](https://docs.python.org/3/library/heapq.html)
- [dataclasses documentation](https://docs.python.org/3/library/dataclasses.html)

AI was used to help split the subject into implementation phases and to
bootstrap the initial project structure. Each implementation step is reviewed
and tested manually as the project evolves.
