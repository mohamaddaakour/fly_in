"""Strict parser for Fly-in map files."""

from pathlib import Path
from typing import NoReturn

from fly_in.models import Connection, MapData, Zone, ZoneType


class ParseError(Exception):
    """Raised when a Fly-in map file contains invalid syntax."""


class MapParser:
    """Parse and validate Fly-in map files."""

    ZONE_KEYS: set[str] = {"zone", "color", "max_drones"}
    CONNECTION_KEYS: set[str] = {"max_link_capacity"}

    def parse_file(self, path: Path) -> MapData:
        """Read and parse a map file.

        Args:
            path: Map file to read.

        Returns:
            Validated map data.

        Raises:
            ParseError: If the file cannot be read or is invalid.
        """
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            raise ParseError(f"Could not read map file: {error}") from error
        return self.parse_lines(lines)

    def parse_lines(self, lines: list[str]) -> MapData:
        """Parse and validate raw map lines.

        Args:
            lines: Lines of map input.

        Returns:
            Validated map data.

        Raises:
            ParseError: If any declaration is invalid.
        """
        drone_count: int | None = None
        start_name: str | None = None
        end_name: str | None = None
        zones: dict[str, Zone] = {}
        connections: list[Connection] = []
        connection_keys: set[tuple[str, str]] = set()
        first_data_line_seen = False

        for line_number, raw_line in enumerate(lines, start=1):
            line = self.strip_comment(raw_line).strip()
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
                zone = self.parse_zone(line_number, line, "start_hub")
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
                connection = self.parse_connection(
                    line_number, line, zones, connection_keys
                )
                connections.append(connection)
            else:
                self.fail(line_number, "unknown line prefix")

        end_line = len(lines) + 1
        if drone_count is None:
            self.fail(end_line, "missing nb_drones definition")
        if start_name is None:
            self.fail(end_line, "missing start_hub definition")
        if end_name is None:
            self.fail(end_line, "missing end_hub definition")
        if not connections:
            self.fail(end_line, "missing connection definitions")

        return MapData(
            drone_count=drone_count,
            start_name=start_name,
            end_name=end_name,
            zones=zones,
            connections=connections,
        )

    def parse_connection(
        self,
        line_number: int,
        line: str,
        zones: dict[str, Zone],
        connection_keys: set[tuple[str, str]],
    ) -> Connection:
        """Parse one connection declaration."""
        body = line.removeprefix("connection:").strip()
        data_part, metadata = self.split_metadata(line_number, body)
        self.validate_metadata_keys(
            line_number, metadata, self.CONNECTION_KEYS
        )
        names = data_part.split("-")
        if len(names) != 2 or not names[0] or not names[1]:
            self.fail(line_number, "connection requires: <zone1>-<zone2>")

        zone_a, zone_b = names
        self.validate_zone_name(line_number, zone_a)
        self.validate_zone_name(line_number, zone_b)
        if zone_a == zone_b:
            self.fail(line_number, "connection cannot link a zone to itself")
        if zone_a not in zones:
            self.fail(line_number, f"unknown zone in connection: {zone_a}")
        if zone_b not in zones:
            self.fail(line_number, f"unknown zone in connection: {zone_b}")

        key = (
            (zone_a, zone_b) if zone_a < zone_b else (zone_b, zone_a)
        )
        if key in connection_keys:
            self.fail(line_number, "duplicate connection")
        connection_keys.add(key)

        capacity = self.parse_positive_int(
            line_number,
            metadata.get("max_link_capacity", "1"),
            "max_link_capacity",
        )
        return Connection(zone_a, zone_b, capacity)

    def parse_zone(self, line_number: int, line: str, prefix: str) -> Zone:
        """Parse one start, end, or regular zone declaration."""
        body = line.removeprefix(f"{prefix}:").strip()
        data_part, metadata = self.split_metadata(line_number, body)
        self.validate_metadata_keys(line_number, metadata, self.ZONE_KEYS)
        tokens = data_part.split()
        if len(tokens) != 3:
            self.fail(line_number, f"{prefix} requires: <name> <x> <y>")

        name = tokens[0]
        self.validate_zone_name(line_number, name)
        zone_type = self.parse_zone_type(line_number, metadata)
        color = metadata.get("color", "none")
        max_drones = self.parse_positive_int(
            line_number, metadata.get("max_drones", "1"), "max_drones"
        )
        return Zone(
            name=name,
            x=self.parse_int(line_number, tokens[1], "x coordinate"),
            y=self.parse_int(line_number, tokens[2], "y coordinate"),
            zone_type=zone_type,
            color=color,
            max_drones=max_drones,
            is_start=prefix == "start_hub",
            is_end=prefix == "end_hub",
        )

    def parse_zone_type(
        self, line_number: int, metadata: dict[str, str]
    ) -> ZoneType:
        """Return a validated zone type from metadata."""
        value = metadata.get("zone", ZoneType.NORMAL.value)
        try:
            return ZoneType(value)
        except ValueError:
            self.fail(line_number, f"invalid zone type: {value}")

    def split_metadata(
        self, line_number: int, body: str
    ) -> tuple[str, dict[str, str]]:
        """Separate declaration data from its optional metadata block."""
        if "[" not in body and "]" not in body:
            return body.strip(), {}
        if body.count("[") != 1 or body.count("]") != 1:
            self.fail(
                line_number,
                "metadata block must use one [metadata] block",
            )

        start = body.index("[")
        end = body.index("]")
        if end < start:
            self.fail(line_number, "metadata closing bracket is misplaced")
        if body[end + 1:].strip():
            self.fail(line_number, "unexpected content after metadata block")
        return (
            body[:start].strip(),
            self.parse_metadata(line_number, body[start + 1:end].strip()),
        )

    def parse_metadata(self, line_number: int, text: str) -> dict[str, str]:
        """Parse whitespace-separated key/value metadata."""
        if not text:
            self.fail(line_number, "metadata block cannot be empty")
        metadata: dict[str, str] = {}
        for item in text.split():
            if item.count("=") != 1:
                self.fail(line_number, f"invalid metadata item: {item}")
            key, value = item.split("=")
            if not key or not value:
                self.fail(line_number, f"invalid metadata item: {item}")
            if key in metadata:
                self.fail(line_number, f"duplicate metadata key: {key}")
            if key not in self.ZONE_KEYS | self.CONNECTION_KEYS:
                self.fail(line_number, f"unknown metadata key: {key}")
            metadata[key] = value
        return metadata

    def validate_metadata_keys(
        self,
        line_number: int,
        metadata: dict[str, str],
        allowed_keys: set[str],
    ) -> None:
        """Reject metadata that is invalid for a declaration type."""
        for key in metadata:
            if key not in allowed_keys:
                self.fail(
                    line_number, f"metadata key is not allowed here: {key}"
                )

    def add_zone(
        self, line_number: int, zones: dict[str, Zone], zone: Zone
    ) -> None:
        """Add a zone after checking name uniqueness."""
        if zone.name in zones:
            self.fail(line_number, f"duplicate zone name: {zone.name}")
        zones[zone.name] = zone

    def validate_zone_name(self, line_number: int, name: str) -> None:
        """Validate the subject's zone-name restrictions."""
        if not name:
            self.fail(line_number, "zone name cannot be empty")
        if "-" in name:
            self.fail(line_number, "zone names cannot contain dashes")
        if any(character.isspace() for character in name):
            self.fail(line_number, "zone names cannot contain spaces")

    def parse_drone_count(self, line_number: int, line: str) -> int:
        """Parse the mandatory positive drone count."""
        value = line.removeprefix("nb_drones:").strip()
        if not value:
            self.fail(line_number, "nb_drones requires a positive integer")
        return self.parse_positive_int(line_number, value, "nb_drones")

    def parse_int(self, line_number: int, value: str, label: str) -> int:
        """Parse a decimal integer or raise a line-aware error."""
        try:
            return int(value)
        except ValueError:
            self.fail(line_number, f"{label} must be an integer")

    def parse_positive_int(
        self, line_number: int, value: str, label: str
    ) -> int:
        """Parse an integer that must be greater than zero."""
        number = self.parse_int(line_number, value, label)
        if number <= 0:
            self.fail(line_number, f"{label} must be a positive integer")
        return number

    def strip_comment(self, line: str) -> str:
        """Remove a comment beginning with the first hash character."""
        return line.split("#", 1)[0]

    def fail(self, line_number: int, message: str) -> NoReturn:
        """Raise a parsing error containing its source line number."""
        raise ParseError(f"Line {line_number}: {message}")
