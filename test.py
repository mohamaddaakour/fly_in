def _parse_zone(self, line_number: int, line: str, prefix: str) -> Zone:
        body: str = line.removeprefix(f"{prefix}:").strip()
        data_part, metadata = self._split_metadata(line_number, body)
        self._validate_metadata_keys(line_number, metadata, self._ZONE_KEYS)
        tokens: list[str] = data_part.split()
        if len(tokens) != 3:
            self._fail(line_number, f"{prefix} requires: <name> <x> <y>")

        name: str = tokens[0]
        self._validate_zone_name(line_number, name)
        x: int = self._parse_int(line_number, tokens[1], "x coordinate")
        y: int = self._parse_int(line_number, tokens[2], "y coordinate")
        zone_type: ZoneType = self._parse_zone_type(line_number, metadata)
        color: str = metadata.get("color", "none")
        max_drones: int = self._parse_positive_int(
            line_number,
            metadata.get("max_drones", "1"),
            "max_drones",
        )