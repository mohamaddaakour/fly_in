*This project has been created as part of the 42 curriculum by mdaakour.*

# Fly-in

## Description

Fly-in is a Python drone-routing simulator. The final program will parse a graph of
zones, route multiple drones from a start hub to an end hub, and output each
simulation turn while respecting zone and connection capacity rules.

Current phase: Phase 3. The program strictly parses and validates map files,
builds an object-oriented graph, and finds one minimum-cost valid path. Blocked
zones are excluded, entering a restricted zone costs two turns, and priority
zones are preferred when multiple paths have the same weighted cost.

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

The program currently prints the parsed zones and connections followed by the
selected path and its weighted cost. Drone simulation begins in Phase 4 and is
intentionally not part of this version.

## Algorithm

The parser processes the input once and rejects malformed declarations with a
line number and cause. Connections are stored as bidirectional adjacency lists.

Pathfinding uses a custom Dijkstra implementation. Its comparison label contains
the total movement cost, the number of priority zones, and the hop count—in that
order. This produces a minimum-cost path while preferring priority zones on
equal-cost routes. Building the graph is `O(V + E)` in time and memory. The path
search is `O((V + E) log V)` time and `O(V + E)` memory, where `V` is the number
of zones and `E` is the number of connections.

## Resources

- [Python documentation](https://docs.python.org/3/)
- [heapq documentation](https://docs.python.org/3/library/heapq.html)
- [dataclasses documentation](https://docs.python.org/3/library/dataclasses.html)

AI was used to help split the subject into implementation phases and to
bootstrap the initial project structure. Each implementation step is reviewed
and tested manually as the project evolves.
