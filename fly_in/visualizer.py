"""ANSI terminal visualization for Fly-in simulations."""

from fly_in.models import MapData, SimulationSnapshot, Zone


class TerminalVisualizer:
    """Render colored network metadata, movements, and turn states."""

    RESET = "\033[0m"
    NAMED_COLORS: dict[str, str] = {
        "black": "30",
        "red": "31",
        "green": "32",
        "yellow": "33",
        "blue": "34",
        "purple": "35",
        "magenta": "35",
        "cyan": "36",
        "white": "37",
        "gray": "90",
        "grey": "90",
        "orange": "38;5;208",
    }

    def __init__(self, map_data: MapData) -> None:
        """Store map metadata used to color and describe the simulation."""
        self.map_data = map_data

    def ansi_code(self, color: str) -> str | None:
        """Return an ANSI foreground code for any non-``none`` color."""
        normalized = color.lower()
        if normalized == "none":
            return None
        named = self.NAMED_COLORS.get(normalized)
        if named is not None:
            return named

        accumulator = 2166136261
        for character in normalized:
            accumulator ^= ord(character)
            accumulator = (accumulator * 16777619) & 0xFFFFFFFF
        red = 64 + (accumulator & 0xBF)
        green = 64 + ((accumulator >> 8) & 0xBF)
        blue = 64 + ((accumulator >> 16) & 0xBF)
        return f"38;2;{red};{green};{blue}"

    def colorize(self, text: str, color: str) -> str:
        """Wrap text in a zone's ANSI color, when one is configured."""
        code = self.ansi_code(color)
        if code is None:
            return text
        return f"\033[{code}m{text}{self.RESET}"

    def format_zone(self, zone: Zone) -> str:
        """Format one colored zone entry for the network legend."""
        if zone.is_start or zone.is_end:
            capacity = "unlimited"
        else:
            capacity = str(zone.max_drones)
        name = self.colorize(zone.name, zone.color)
        return (
            f"  {name}: type={zone.zone_type.value} "
            f"capacity={capacity} position=({zone.x},{zone.y})"
        )

    def movement_destination(self, movement: str) -> str:
        """Extract a destination zone from a movement token."""
        payload = movement.split("-", 1)[1]
        if payload in self.map_data.zones:
            return payload
        return payload.rsplit("-", 1)[-1]

    def format_movement(self, movement: str) -> str:
        """Color a movement using its destination zone metadata."""
        destination = self.movement_destination(movement)
        zone = self.map_data.zones.get(destination)
        if zone is None:
            return movement
        return self.colorize(movement, zone.color)

    @staticmethod
    def format_identifiers(identifiers: tuple[int, ...]) -> str:
        """Format drone identifiers compactly for a state line."""
        names = ",".join(f"D{identifier}" for identifier in identifiers)
        return f"[{names}]"

    def format_snapshot(self, snapshot: SimulationSnapshot) -> list[str]:
        """Render zone occupancy, transit state, and delivery progress."""
        zone_parts: list[str] = []
        for name in sorted(snapshot.zone_drones):
            zone = self.map_data.zones[name]
            label = self.colorize(name, zone.color)
            drones = self.format_identifiers(snapshot.zone_drones[name])
            zone_parts.append(f"{label}={drones}")
        if not zone_parts:
            zone_parts.append("none")

        lines = ["  Zones: " + " ".join(zone_parts)]
        if snapshot.connection_drones:
            connection_parts = [
                f"{name}={self.format_identifiers(identifiers)}"
                for name, identifiers in sorted(
                    snapshot.connection_drones.items()
                )
            ]
            lines.append("  In flight: " + " ".join(connection_parts))
        else:
            lines.append("  In flight: none")
        lines.append(
            "  Delivered: "
            f"{snapshot.delivered_count}/{self.map_data.drone_count}"
        )
        return lines

    def render(
        self,
        turns: list[str],
        snapshots: list[SimulationSnapshot],
    ) -> list[str]:
        """Return the complete visual terminal output as separate lines."""
        if len(turns) != len(snapshots):
            raise ValueError("each visual turn requires one state snapshot")
        lines = ["Fly-in Visual Simulation", "Zones:"]
        lines.extend(
            self.format_zone(zone) for zone in self.map_data.zones.values()
        )
        lines.append("Connections:")
        lines.extend(
            "  "
            f"{connection.name()} capacity={connection.max_link_capacity}"
            for connection in self.map_data.connections
        )
        for turn_number, (turn, snapshot) in enumerate(
            zip(turns, snapshots), start=1
        ):
            movements = " ".join(
                self.format_movement(movement)
                for movement in turn.split()
            )
            lines.append(f"Turn {turn_number}:")
            lines.append(f"  Moves: {movements}")
            lines.extend(self.format_snapshot(snapshot))
        return lines
