"""Domain models for Fly-in maps."""

from dataclasses import dataclass
from enum import Enum


# an enum for different zone types
class ZoneType(str, Enum):
    """Supported zone behavior types."""

    NORMAL = "normal"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"
    PRIORITY = "priority"


@dataclass(frozen=True)
class Zone:
    """A zone in the drone network.

    Attributes:
        name: Unique zone name.
        x: X coordinate.
        y: Y coordinate.
        zone_type: Movement behavior for this zone.
        color: Optional display color.
        max_drones: Maximum drones allowed in the zone.
        is_start: Whether this zone is the start hub.
        is_end: Whether this zone is the end hub.
    """

    name: str
    x: int
    y: int
    zone_type: ZoneType
    color: str
    max_drones: int
    is_start: bool
    is_end: bool


# this is the link between two zones
@dataclass(frozen=True)
class Connection:
    """A bidirectional connection between two zones.

    Attributes:
        zone_a: First zone name.
        zone_b: Second zone name.
        max_link_capacity: Maximum drones traversing this link per turn.
    """

    zone_a: str
    zone_b: str
    max_link_capacity: int

    def name(self) -> str:
        """Return the display name used for this connection."""
        return f"{self.zone_a}-{self.zone_b}"


# these are the map data
@dataclass(frozen=True)
class MapData:
    """Parsed Fly-in map data.

    Attributes:
        drone_count: Number of drones to route.
        start_name: Start zone name.
        end_name: End zone name.
        zones: Zones keyed by name.
        connections: All bidirectional connections.
    """

    drone_count: int
    start_name: str
    end_name: str

    # here we have an object of zones names as keys
    # an the zones instances as values
    zones: dict[str, Zone]

    # list of connections instances
    connections: list[Connection]
