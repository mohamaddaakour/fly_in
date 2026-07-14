"""Parser for Fly-in map files."""

from pathlib import Path
from typing import NoReturn

from fly_in.models import *


# create a new exception type
class ParseError(Exception):
    """Raised when a Fly-in map file contains invalid syntax."""


class MapParser:
    """Parse and validate Fly-in map files."""

    # constants
    ZONE_KEYS: set[str] = set({"zone", "color", "max_drones"})
    CONNECTION_KEYS: set[str] = set(["max_link_capacity"])


    # we parse the content of map file
    def parse_file(self, path: Path) -> MapData:
        """Parse a map file from disk.

        Args:
            path: Path to the map file.

        Returns:
            Parsed map data.

        Raises:
            ParseError: If the file cannot be read or contains invalid syntax.
        """

        lines: list[str] = []

        try:
            # read_text is a Path class method to read text content
            # of this file and splitlines is a method to put every line as
            # an element
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            raise ParseError(f"Could not read map file: {e}")
        
        return self.parse_lines(lines)
    

    def parse_lines(self, lines: list[str]) -> MapData:
        """Parse map data from raw lines.

        Args:
            lines: Raw map file lines.

        Returns:
            Parsed map data.

        Raises:
            ParseError: If any line is invalid.
        """

        drone_count: int = 0
        start_name: str = ""
        end_name: str = ""
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []

        # this is used to detect duplicate connections
        connection_keys: list[tuple[str, str]] = set()

        first_data_line_seen: bool = False