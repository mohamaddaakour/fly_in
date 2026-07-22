*This project has been created as part of the 42 curriculum by mdaakour.*

# Fly-in

## Description

Fly-in is a Python drone-routing simulator. The final program will parse a graph of
zones, route multiple drones from a start hub to an end hub, and output each
simulation turn while respecting zone and connection capacity rules.

Current phase: Phase 7. The program strictly parses and validates map files,
discovers multiple weighted routes, distributes drones by expected completion
time, and simulates all assigned paths together. Blocked zones are excluded,
entering a restricted zone costs two turns, and priority zones win equal-cost
path ties.

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

## Restricted-Zone Transit

Entering a restricted zone takes exactly two turns. On the first turn, the
drone leaves its source, reserves capacity in the destination, occupies the
connection, and prints `D<ID>-<source>-<destination>`. On the following turn it
must arrive and prints `D<ID>-<destination>`; it cannot wait or move again in
that turn. A restricted end hub remains unlimited.

In-transit drones do not occupy their old zone. They do occupy connection
capacity through their arrival turn, so a capacity-one restricted link cannot
accept another drone until the next turn. Destination reservations are counted
alongside physical occupancy, preventing another movement from taking a slot
already promised to an arriving drone.

## Multiple Paths and Distribution

The pathfinder uses Yen's algorithm over the custom constrained Dijkstra search
to discover the cheapest loopless alternatives. Routes are ordered by weighted
cost, number of priority zones, hop count, and zone names. Results are cached by
the requested route count and returned as defensive copies.

Each drone owns an independent copy of its assigned route. Assignment estimates
the next completion time from route latency, zone capacity, link capacity, and
the two-turn occupancy of restricted links. This allows shorter or higher-
throughput routes to receive more drones instead of using naive round-robin
distribution. Equal estimates prefer lower cost and then priority routes.

Zone occupancy, restricted reservations, and connection usage remain global.
Consequently, disjoint paths can progress in parallel while overlapping paths
still respect shared bottlenecks. More advanced rerouting around runtime
congestion remains part of Phase 8.

With `D` drones, path length `P`, and `T` turns, initialization is `O(D)`.
Occupancy, reservations, connection usage, and movement processing are `O(D)`
per turn, while ordering active drones is `O(D log D)`. Total simulation time
is `O(T * D log D)`. Cached connection capacities use `O(E)` memory, so live
state uses `O(D + R + E)` memory, excluding retained output lines, where `R`
is the total number of zone entries across discovered routes.

For `K` requested paths, Yen's algorithm performs up to `O(K * V)` constrained
Dijkstra searches, each `O((V + E) log V)`. Assignment is `O(D * K * P)` with
the current transparent completion estimator. Cached routes require `O(K * P)`
additional memory.

## Resources

- [Python documentation](https://docs.python.org/3/)
- [heapq documentation](https://docs.python.org/3/library/heapq.html)
- [dataclasses documentation](https://docs.python.org/3/library/dataclasses.html)

AI was used to help split the subject into implementation phases and to
bootstrap the initial project structure. Each implementation step is reviewed
and tested manually as the project evolves.
