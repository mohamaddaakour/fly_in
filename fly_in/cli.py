"""Command-line interface for the Fly-in pathfinder."""

from argparse import ArgumentParser, Namespace
from pathlib import Path

from fly_in.models import MapData, Connection
from fly_in.parser import MapParser, ParseError
from fly_in.pathfinder import Pathfinder, PathNotFoundError

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
    """Parse a map and display its minimum-cost Phase 3 path."""
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
        path = pathfinder.find_shortest_path()
    except (ParseError, PathNotFoundError) as error:
        print(f"Error: {error}")
        return 1
    if args.summary:
        print_map_summary(map_data, path, pathfinder.path_cost(path))
    print("\n".join(turns))
    return 0


def print_map_summary(map_data: MapData) -> None:
    """Print all parsed Phase 2 map data."""
    print(f"Drones: {map_data.drone_count}")
    print(f"Start: {map_data.start_name}")
    print(f"End: {map_data.end_name}")
    print("Zones:")
    for zone in map_data.zones.values():
        print(format_zone(zone))
    print("Connections:")
    for connection in map_data.connections:
        print(format_connection(connection))


def format_zone(zone: Zone) -> str:
    """Format one zone for the parser summary."""
    label = "hub"
    if zone.is_start:
        label = "start_hub"
    elif zone.is_end:
        label = "end_hub"
    return (
        f"  {label}: {zone.name} ({zone.x}, {zone.y}) "
        f"zone={zone.zone_type.value} color={zone.color} "
        f"max_drones={zone.max_drones}"
    )


def format_connection(connection: Connection) -> str:
    """Format one connection for the parser summary."""
    return (
        f"  connection: {connection.name()} "
        f"max_link_capacity={connection.max_link_capacity}"
    )
