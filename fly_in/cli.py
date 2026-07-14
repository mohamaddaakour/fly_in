"""Command-line interface for the Fly-in simulator."""

from argparse import ArgumentParser, Namespace
from pathlib import Path

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
    
    