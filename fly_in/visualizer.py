"""Simple Tkinter animation for the drone simulation."""

import sys
import time

from fly_in.models import MapData, SimulationSnapshot


class TerminalVisualizer:
    """Turn simulation snapshots into simple terminal frames."""

    # ANSI code to reset terminal.
    RESET = "\033[0m"

    # ANSI code for colors.
    COLORS = {
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
        self.map_data = map_data

    def ansi_code(self, color: str) -> str | None:
        """Get a terminal color, including a stable color for custom names."""
        color = color.lower()
        if color == "none":
            return None
        if color in self.COLORS:
            return self.COLORS[color]

        # To get the exact ansi code in RGB
        value = 2166136261
        for character in color:
            value = ((value ^ ord(character)) * 16777619) & 0xFFFFFFFF
        red = 64 + (value & 0xBF)
        green = 64 + ((value >> 8) & 0xBF)
        blue = 64 + ((value >> 16) & 0xBF)
        return f"38;2;{red};{green};{blue}"

    def colorize(self, text: str, color: str) -> str:
        code = self.ansi_code(color)
        return text if code is None else f"\033[{code}m{text}{self.RESET}"

    @staticmethod
    def drone_list(identifiers: tuple[int, ...]) -> str:
        """Format drone ID numbers as a compact "[D1,D2]" style string."""
        return "[" + ",".join(f"D{number}" for number in identifiers) + "]"

    def destination(self, movement: str) -> str:
        """Get the destination from D1-zone or D1-source-zone."""
        payload = movement.split("-", 1)[1]
        if payload in self.map_data.zones:
            return payload
        return payload.split("-", 1)[-1]

    def colored_movement(self, movement: str) -> str:
        zone = self.map_data.zones.get(self.destination(movement))
        if zone is None:
            return movement
        return self.colorize(movement, zone.color)

    def frame(
        self, turn_number: int, movement: str, snapshot: SimulationSnapshot
    ) -> list[str]:
        """Build one compact frame showing every current drone position."""
        zone_parts = []
        for name, identifiers in snapshot.zone_drones.items():
            zone = self.map_data.zones[name]
            zone_parts.append(
                f"{self.colorize(name, zone.color)}="
                f"{self.drone_list(identifiers)}"
            )

        flight_parts = [
            f"{name}={self.drone_list(identifiers)}"
            for name, identifiers in snapshot.connection_drones.items()
        ]
        moves = " ".join(
            self.colored_movement(item) for item in movement.split()
        )
        return [
            "Fly-in Visual Simulation",
            f"Turn {turn_number}:",
            f"  Moves: {moves}",
            "  Zones: " + ("  |  ".join(zone_parts) or "none"),
            "  In flight: " + ("  |  ".join(flight_parts) or "none"),
            "  Delivered: "
            f"{snapshot.delivered_count}/{self.map_data.drone_count}",
        ]

    def render(
        self, turns: list[str], snapshots: list[SimulationSnapshot]
    ) -> list[str]:
        """Build all frames, mainly for redirected output and tests."""
        if len(turns) != len(snapshots):
            raise ValueError("each visual turn requires one state snapshot")
        lines: list[str] = []
        for number, (turn, snapshot) in enumerate(zip(turns, snapshots), 1):
            lines.extend(self.frame(number, turn, snapshot))
        return lines

    def animate(
        self,
        turns: list[str],
        snapshots: list[SimulationSnapshot],
        delay: float = 0.5,
    ) -> None:
        """Open a small animation window or print when output is redirected."""
        if len(turns) != len(snapshots):
            raise ValueError("each visual turn requires one state snapshot")

        if sys.stdout.isatty():
            try:
                self.animate_window(turns, delay)
                return
            except (ImportError, RuntimeError):
                pass

        for number, (turn, snapshot) in enumerate(zip(turns, snapshots), 1):
            print("\n".join(self.frame(number, turn, snapshot)))

    def animate_window(self, turns: list[str], delay: float) -> None:
        """Draw the map and smoothly move drones with Tkinter."""
        import tkinter as tk

        try:
            root = tk.Tk()
        except tk.TclError as error:
            raise RuntimeError("Tkinter window is unavailable") from error
        root.title("Fly-in Drone Animation")
        closed = False

        def close_window() -> None:
            """Stop animation callbacks before destroying the window."""
            nonlocal closed
            closed = True
            try:
                root.destroy()
            except tk.TclError:
                pass

        root.protocol("WM_DELETE_WINDOW", close_window)
        canvas = tk.Canvas(root, width=800, height=600, bg="white")
        canvas.pack()

        # Convert map coordinates to positions that fit inside the window.
        xs = [zone.x for zone in self.map_data.zones.values()]
        ys = [zone.y for zone in self.map_data.zones.values()]

        def scale(value: int, values: list[int], size: int) -> float:
            low, high = min(values), max(values)
            return 100 + (value - low) * (size - 200) / max(high - low, 1)

        points = {
            name: (scale(zone.x, xs, 800), scale(zone.y, ys, 600))
            for name, zone in self.map_data.zones.items()
        }
        positions = {
            number: points[self.map_data.start_name]
            for number in range(1, self.map_data.drone_count + 1)
        }

        def draw(turn_number: int) -> bool:
            # Redrawing the small scene is simpler than moving many canvas IDs.
            if closed:
                return False
            canvas.delete("all")
            for connection in self.map_data.connections:
                canvas.create_line(
                    *points[connection.zone_a],
                    *points[connection.zone_b],
                    width=2,
                    fill="#888888",
                )
            for name, zone in self.map_data.zones.items():
                x, y = points[name]
                color = zone.color if zone.color != "none" else "lightgray"
                try:
                    canvas.create_oval(
                        x - 25, y - 25, x + 25, y + 25,
                        fill=color, outline="black",
                    )
                except tk.TclError:
                    canvas.create_oval(
                        x - 25, y - 25, x + 25, y + 25,
                        fill="lightgray", outline="black",
                    )
                canvas.create_text(x, y - 38, text=name)
            for number, (x, y) in positions.items():
                offset = ((number - 1) % 5) * 8 - 16
                canvas.create_oval(
                    x - 9 + offset, y - 9, x + 9 + offset, y + 9,
                    fill="#222222",
                )
                canvas.create_text(
                    x + offset, y, text=str(number), fill="white"
                )
            canvas.create_text(
                400, 25, text=f"Turn {turn_number}", font=("Arial", 16)
            )
            try:
                root.update()
            except tk.TclError:
                close_window()
                return False
            return not closed

        if not draw(0):
            return
        time.sleep(delay)
        for turn_number, turn in enumerate(turns, 1):
            if closed:
                return
            # A normal move targets a zone. Restricted transit targets the
            # middle of its connection until the following arrival turn.
            targets: dict[int, tuple[float, float]] = {}
            for movement in turn.split():
                drone_text, payload = movement.split("-", 1)
                number = int(drone_text[1:])
                if payload in points:
                    targets[number] = points[payload]
                else:
                    source, destination = payload.rsplit("-", 1)
                    start = points[source]
                    end = points[destination]
                    targets[number] = (
                        (start[0] + end[0]) / 2,
                        (start[1] + end[1]) / 2,
                    )

            starts = {number: positions[number] for number in targets}
            # Twenty small position changes make each turn look continuous.
            for step in range(1, 21):
                if closed:
                    return
                for number, target in targets.items():
                    start = starts[number]
                    positions[number] = (
                        start[0] + (target[0] - start[0]) * step / 20,
                        start[1] + (target[1] - start[1]) * step / 20,
                    )
                if not draw(turn_number):
                    return
                time.sleep(delay / 20)

        if closed:
            return
        canvas.create_text(
            400, 570, text="All drones delivered!", font=("Arial", 16)
        )
        try:
            root.mainloop()
        except tk.TclError:
            close_window()
