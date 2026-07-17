"""Command-line interface for the Fly-in simulator."""

from argparse import ArgumentParser, Namespace
from pathlib import Path

from fly_in.models import Connection, MapData, Zone
from fly_in.parser import MapParser, ParseError
from fly_in.pathfinder import Pathfinder, PathNotFoundError


# parse the map file path from the command line
def argument_parser() -> ArgumentParser:
    """Create the command-line argument parser.

    Returns:
        The configured argument parser.
    """

    parser: ArgumentParser = ArgumentParser(
        prog="fly_in",
        description="Route drones through connected zones"
    )

    # nars="?" means we may take a value as argument and may not
    # if we didn't take by default take what inside default
    parser.add_argument(
        "map_file",
        nargs="?",
        default="maps/example.map",
        help="Path to a fly_in map file"
    )

    return parser


def main() -> int:
    """Run the Fly-in command-line program.

    Returns:
        Process exit status code.
    """

    parser: ArgumentParser = argument_parser()
    
    # to apply the parsing
    args: Namespace = parser.parse_args()

    # we take the value of parsed argument with name map_file
    # Path will create an instance of the class Path
    map_path: Path = Path(args.map_file)

    if not map_path.exists():
        print(f"Error: map file not found: {map_path}")
        return 1
    
    if not map_path.is_file():
        print(f"Error: map path is not a file: {map_path}")
        return 1
    

    try:
        map_data: MapData = MapParser().parse_file(map_path)
        pathfinder = Pathfinder(map_data)
        path: list[str] = pathfinder.find_shortest_path()
    except (ParseError, PathNotFoundError) as error:
        print(f"Error: {error}")
        return 1

    print_map_summary(map_data)
    print(f"Path: {' -> '.join(path)}")
    print(f"Cost: {pathfinder.path_cost(path)}")
    return 0


def print_map_summary(map_data: MapData) -> None:
    """Print a human-readable summary of parsed map data.

    Args:
        map_data: Parsed map data to display.
    """
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
    label: str = "hub"
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
    return (
        f"  connection: {connection.name()} "
        f"max_link_capacity={connection.max_link_capacity}"
    )
