"""Tests for optional Phase 9 terminal visualization."""

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fly_in.cli import main
from fly_in.parser import MapParser
from fly_in.pathfinder import Pathfinder
from fly_in.simulation import Simulation
from fly_in.visualizer import TerminalVisualizer


class TerminalVisualizerTests(unittest.TestCase):
    """Verify colors, movements, and state rendering."""

    def test_named_and_arbitrary_colors_produce_ansi(self) -> None:
        """Support standard names and any custom single-word color."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0 [color=red]",
                "end_hub: end 1 0 [color=ultraviolet]",
                "connection: start-end",
            ]
        )
        visualizer = TerminalVisualizer(data)
        self.assertEqual(
            visualizer.colorize("start", "red"),
            "\033[31mstart\033[0m",
        )
        custom = visualizer.colorize("end", "ultraviolet")
        self.assertTrue(custom.startswith("\033[38;2;"))
        self.assertTrue(custom.endswith("end\033[0m"))
        self.assertEqual(visualizer.colorize("plain", "none"), "plain")

    def test_render_shows_turn_movements_and_zone_state(self) -> None:
        """Render state snapshots alongside each colored movement turn."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0 [color=green]",
                "end_hub: end 2 0 [color=yellow]",
                "hub: secure 1 0 [zone=restricted color=purple]",
                "connection: start-secure",
                "connection: secure-end",
            ]
        )
        paths = Pathfinder(data).find_paths()
        simulation = Simulation(data, paths, capture_snapshots=True)
        turns = simulation.run()
        output = "\n".join(
            TerminalVisualizer(data).render(turns, simulation.snapshots)
        )
        self.assertIn("Turn 1:", output)
        self.assertIn("Moves:", output)
        self.assertIn("In flight: start-secure=[D1]", output)
        self.assertIn("Delivered: 1/1", output)
        self.assertIn("\033[35mD1-start-secure\033[0m", output)

    def test_render_rejects_missing_snapshots(self) -> None:
        """Prevent misleading visual output without matching state data."""
        data = MapParser().parse_lines(
            [
                "nb_drones: 1",
                "start_hub: start 0 0",
                "end_hub: end 1 0",
                "connection: start-end",
            ]
        )
        with self.assertRaisesRegex(ValueError, "one state snapshot"):
            TerminalVisualizer(data).render(["D1-end"], [])


class VisualCliTests(unittest.TestCase):
    """Verify visual mode is optional and evaluator output stays clean."""

    def run_cli(self, visual: bool) -> tuple[int, str]:
        """Run the CLI against a temporary colored direct map."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "visual.map"
            path.write_text(
                "\n".join(
                    [
                        "nb_drones: 1",
                        "start_hub: start 0 0 [color=green]",
                        "end_hub: end 1 0 [color=yellow]",
                        "connection: start-end",
                    ]
                ),
                encoding="utf-8",
            )
            arguments = ["fly_in", str(path)]
            if visual:
                arguments.append("--visual")
            output = StringIO()
            with patch("sys.argv", arguments), redirect_stdout(output):
                status = main()
            return status, output.getvalue()

    def test_default_mode_remains_official_output(self) -> None:
        """Keep turn output free from labels and ANSI control sequences."""
        status, output = self.run_cli(visual=False)
        self.assertEqual(status, 0)
        self.assertEqual(output, "D1-end\n")
        self.assertNotIn("\033[", output)

    def test_visual_flag_enables_rich_output(self) -> None:
        """Add colors, turn numbers, movements, and delivered state."""
        status, output = self.run_cli(visual=True)
        self.assertEqual(status, 0)
        self.assertIn("Fly-in Visual Simulation", output)
        self.assertIn("Turn 1:", output)
        self.assertIn("Moves:", output)
        self.assertIn("Delivered: 1/1", output)
        self.assertIn("\033[", output)


if __name__ == "__main__":
    unittest.main()
