*This project has been created as part of the 42 curriculum by mdaakour.*

# Fly-in

## Description

Fly-in is a Python drone-routing simulator. The final program will parse a graph of
zones, route multiple drones from a start hub to an end hub, and output each
simulation turn while respecting zone and connection capacity rules.

Current phase: the program parses and validates map files, finds a minimum-cost
valid path, and prints the parsed graph, path, and movement cost.

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

## Resources

- Python documentation: https://docs.python.org/3/

AI was used to help split the subject into implementation phases and to
bootstrap the initial project structure. Each implementation step is reviewed
and tested manually as the project evolves.
