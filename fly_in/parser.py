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

        # to check if we readed the firs line
        first_data_line_seen: bool = False

        for line_number, line in enumerate(lines, start=1):
            line: str = self.strip_comment(line).strip()

            # if it is just a comment in the line skip it
            if not line:
                continue

            if not first_data_line_seen:
                if not line.startswith("nb_drones:"):
                    self.fail(line_number, "first line must define nb_drones")
                
                first_data_line_seen = True

            if line.startswith("nb_drones:"):
                if drone_count is not None:
                    self.fail(line_number, "nb_drones is already defined")

                drone_count = self.parse_drone_count
            
            elif line.startswith("start_hub:"):
                if start_name is not None:
                    self.fail(line_number, "start_hub is already defined")

                zone: Zone = self._parse_zone(line_number, line, "start_hub")

                self.add_zone(line_number, zones, zone)
                start_name = zone.name

            elif line.startswith("end_hub:"):
                if end_name is not None:
                    self.fail(line_number, "end_hub is already defined")
                zone = self.parse_zone(line_number, line, "end_hub")
                self.add_zone(line_number, zones, zone)
                end_name = zone.name

            elif line.startswith("hub:"):
                zone = self.parse_zone(line_number, line, "hub")
                self.add_zone(line_number, zones, zone)

    
    def parse_zone(self, line_number: int, line: str, prefix: str) -> Zone:
        body: str = line.removeprefix(f"{prefix}:").strip()

        

    

    # function to parse drone count
    def parse_drone_count(self, line_number: int, line: str) -> int:
        value: str = line.removeprefix("nb_drones:").strip()

        if not value:
            self.fail(line_number, "nb drones requires positive integer")

        return self.parse_pos
    

    # function to parse a string to integer
    def parse_int(self, line_number: int, value: str, label: str) -> int:
        try:
            return int(value)
        except ValueError:
            self.fail(line_number, f"{label} must be an integer")
    

    # function to parse the integer and check if it is greater than 0
    def parse_positive_int(self, line_number: int, value: int, label: str) -> int:
        number: int = self.parse_int(value)

        if number <= 0:
            self.fail(line_number, f"{label} must be a positive number")

        return number

    
    # we may have a comment after the line of code
    # example: a = 3 # this comment
    # to take the line of code only we use this method
    def strip_comment(self, line: str) -> str:
        return line.split("#", 1)[0]
    

    # function to raise an error
    def fail(self, line_number: int, message: str) -> NoReturn:
        raise ParseError(f"Line {line_number}: {message}")