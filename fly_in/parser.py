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

        drone_count: int | None = None
        start_name: str | None = None
        end_name: str | None = None
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []

        # this is used to detect duplicate connections
        connection_keys: set[tuple[str, str]] = set()

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

                drone_count = self.parse_drone_count(line_number, line)
            
            elif line.startswith("start_hub:"):
                if start_name is not None:
                    self.fail(line_number, "start_hub is already defined")

                zone: Zone = self.parse_zone(line_number, line, "start_hub")

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

            elif line.startswith("connection:"):
                connection: Connection = self.parse_connection(
                    line_number,
                    line,
                    zones,
                    connection_keys,
                )
                connections.append(connection)
            else:
                self.fail(line_number, "unknown line prefix")

        if drone_count is None:
            raise ParseError("Missing nb_drones definition")
        if start_name is None:
            raise ParseError("Missing start_hub definition")
        if end_name is None:
            raise ParseError("Missing end_hub definition")
        if not connections:
            raise ParseError("Missing connection definitions")

        return MapData(
            drone_count=drone_count,
            start_name=start_name,
            end_name=end_name,
            zones=zones,
            connections=connections,
        )


    # parsing the connection if it is valid
    def parse_connection(
        self,
        line_number: int,
        line: str,
        zones: dict[str, Zone],
        connection_keys: set[tuple[str, str]],
    ) -> Connection:
        body: str = line.removeprefix("connection:").strip()

        data_part, metadata = self.split_metadata(line_number, body)

        self.validate_metadata_keys(line_number, metadata, self.CONNECTION_KEYS)

        names: list[str] = data_part.split("-")

        if len(names) != 2 or not names[0] or not names[1]:
            self.fail(line_number, "connection requires: <zone1>-<zone2>")

        zone_a: str = names[0]
        zone_b: str = names[1]

        self.validate_zone_name(line_number, zone_a)
        self.validate_zone_name(line_number, zone_b)

        if zone_a == zone_b:
            self.fail(line_number, "connection cannot link a zone to itself")

        if zone_a not in zones:
            self.fail(line_number, f"unknown zone in connection: {zone_a}")

        if zone_b not in zones:
            self.fail(line_number, f"unknown zone in connection: {zone_b}")

        key: tuple[str, str] = (
            (zone_a, zone_b) if zone_a < zone_b else (zone_b, zone_a)
        )

        if key in connection_keys:
            self.fail(line_number, "duplicate connection")
        connection_keys.add(key)

        capacity: int = self.parse_positive_int(
            line_number,
            metadata.get("max_link_capacity", "1"),
            "max_link_capacity",
        )

        return Connection(zone_a=zone_a, zone_b=zone_b, max_link_capacity=capacity)


    def parse_zone_type(
        self,
        line_number: int,
        metadata: dict[str, str],
    ) -> ZoneType:
        raw_zone_type: str = metadata.get("zone", ZoneType.NORMAL.value)
        try:
            return ZoneType(raw_zone_type)
        except ValueError:
            self.fail(line_number, f"invalid zone type: {raw_zone_type}")

    
    # to parse zone format
    def parse_zone(self, line_number: int, line: str, prefix: str) -> Zone:
        body: str = line.removeprefix(f"{prefix}:").strip()

        data_part, metadata = self.split_metadata(line_number, body)

        self.validate_metadata_keys(line_number, metadata, self.ZONE_KEYS)

        # tokens is the data part after spliting
        tokens: list[str] = data_part.split()

        if len(tokens) != 3:
            self.fail(line_number, f"{prefix} requires: <name> <x> <y>")

        name: str = tokens[0]

        self.validate_zone_name(line_number, name)

        x: int = self.parse_int(line_number, tokens[1], "x coordinate")
        y: int = self.parse_int(line_number, tokens[2], "y coordinate")

        zone_type: ZoneType = self.parse_zone_type(line_number, metadata)

        color: str = metadata.get("color", "none")

        max_drones: int = self.parse_positive_int(line_number, metadata.get("max_drones", "1"), "max_drones")

        return Zone(
            name=name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            is_start=prefix == "start_hub",
            is_end=prefix == "end_hub",
        )


    # validate the metadata keys
    def validate_metadata_keys(
        self,
        line_number: int,
        metadata: dict[str, str],
        allowed_keys: set[str],
    ) -> None:
        for key in metadata:
            if key not in allowed_keys:
                self.fail(line_number, f"metadata key is not allowed here: {key}")


    # split the data and metadata (that is inside [])
    def split_metadata(self, line_number: int, body: str) -> tuple[str, dict[str, str]]:
        if "[" not in body and "]" not in body:
            return (body.strip(), {})
        
        if body.count("[") != 1 or body.count("]") != 1:
            self.fail(line_number, "metadata block must use one [metadata] block")

        start: int = body.index("[")
        end: int = body.index("]")

        if end < start:
            self.fail(line_number, "metadata closing bracket is misplaced")

        if body[end + 1:].strip():
            self.fail(line_number, "unexpected content after metadata block")

        data_part: str = body[:start].strip()

        metadata_text: str = body[start + 1:end].strip()

        return (data_part, self.parse_metadata(line_number, metadata_text))


    # add zone to the zones dictionary
    def add_zone(
        self,
        line_number: int,
        zones: dict[str, Zone],
        zone: Zone,
    ) -> None:
        if zone.name in zones:
            self.fail(line_number, f"duplicate zone name: {zone.name}")
        zones[zone.name] = zone


    # validate the zone name
    def validate_zone_name(self, line_number: int, name: str) -> None:
        if not name:
            self.fail(line_number, "zone name cannot be empty")
        if "-" in name:
            self.fail(line_number, "zone names cannot contain dashes")
        if any(character.isspace() for character in name):
            self.fail(line_number, "zone names cannot contain spaces")
    

    # parse the metadata inside [] to a dictionary by key and value
    def parse_metadata(self, line_number: int, text: str) -> dict[str, str]:
        metadata: dict[str, str] = {}

        if not text:
            self.fail(line_number, "metadata block cannot be empty")

        for item in text.split():
            if item.count("=") != 1:
                self.fail(line_number, f"invalid metadata item: {item}")

            key, value = item.split("=")

            if not key or not value:
                self.fail(line_number, f"invalid metadata item: {item}")

            if key in metadata:
                self.fail(line_number, f"duplicate metadata key: {key}")

            if key not in self.ZONE_KEYS and key not in self.CONNECTION_KEYS:
                self.fail(line_number, f"unknown metadata key: {key}")

            metadata[key] = value

        return metadata


    # function to parse drone count
    def parse_drone_count(self, line_number: int, line: str) -> int:
        value: str = line.removeprefix("nb_drones:").strip()

        if not value:
            self.fail(line_number, "nb drones requires positive integer")

        return self.parse_positive_int(line_number, value, "nb_drones")
    

    # function to parse a string to integer
    def parse_int(self, line_number: int, value: str, label: str) -> int:
        try:
            return int(value)
        except ValueError:
            self.fail(line_number, f"{label} must be an integer")
    

    # function to parse the integer and check if it is greater than 0
    def parse_positive_int(self, line_number: int, value: str, label: str) -> int:
        number: int = self.parse_int(line_number, value, label)

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
