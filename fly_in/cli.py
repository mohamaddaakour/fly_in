"""Command-line interface for the Fly-in simulator."""

from argparse import ArgumentParser, Namespace
from pathlib import Path

from fly_in.parser import MapParser, ParseError
from fly_in.pathfinder import Pathfinder, PathNotFoundError
from fly_in.simulation import Simulation, SimulationError


def argument_parser() -> ArgumentParser:
    """Create the command-line argument parser."""
    parser = ArgumentParser(
        prog="fly_in", description="Route drones through connected zones"
    )
    parser.add_argument(
        "map_file",
        nargs="?",
        default="maps/example.map",
        help="Path to a Fly-in map file",
    )
    return parser


def main() -> int:
    """Parse a map, find one path, and print its capacity-safe simulation."""
    parser = argument_parser()
    args: Namespace = parser.parse_args()
    map_path = Path(str(args.map_file))

    if not map_path.exists():
        print(f"Error: map file not found: {map_path}")
        return 1
    if not map_path.is_file():
        print(f"Error: map path is not a file: {map_path}")
        return 1

    try:
        map_data = MapParser().parse_file(map_path)
        pathfinder = Pathfinder(map_data)
        paths = pathfinder.find_paths()
        turns = Simulation(map_data, paths).run()
    except ParseError as error:
        print(f"Parsing error: {error}")
        return 1
    except PathNotFoundError as error:
        print(f"Pathfinding error: {error}")
        return 1
    except SimulationError as error:
        print(f"Simulation error: {error}")
        return 1

    for turn in turns:
        print(turn)
    return 0
