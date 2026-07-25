"""Turn-count regressions for the local synthetic benchmark suite."""

from pathlib import Path
import unittest

from fly_in.parser import MapParser
from fly_in.pathfinder import Pathfinder
from fly_in.simulation import Simulation


BENCHMARK_DIRECTORY = Path(__file__).parents[1] / "maps" / "benchmarks"
TARGETS: dict[str, int] = {
    "easy_linear_2.map": 6,
    "easy_fork_4.map": 8,
    "easy_capacity_4.map": 6,
    "medium_dead_end_5.map": 12,
    "medium_circular_6.map": 15,
    "medium_priority_5.map": 12,
    "hard_maze_8.map": 30,
    "hard_capacity_hell_12.map": 35,
    "hard_ultimate_15.map": 45,
}
PROVIDED_TARGETS: dict[str, int] = {
    "easy/01_linear_path.txt": 6,
    "easy/02_simple_fork.txt": 8,
    "easy/03_basic_capacity.txt": 6,
    "medium/01_dead_end_trap.txt": 12,
    "medium/02_circular_loop.txt": 15,
    "medium/03_priority_puzzle.txt": 12,
    "hard/01_maze_nightmare.txt": 30,
    "hard/02_capacity_hell.txt": 35,
    "hard/03_ultimate_challenge.txt": 45,
}


class SyntheticPerformanceTests(unittest.TestCase):
    """Ensure representative maps remain within subject turn targets."""

    def test_turn_targets(self) -> None:
        """Run every synthetic benchmark and compare its total turns."""
        for filename, target in TARGETS.items():
            with self.subTest(map=filename, target=target):
                map_data = MapParser().parse_file(
                    BENCHMARK_DIRECTORY / filename
                )
                paths = Pathfinder(map_data).find_paths()
                turns = Simulation(map_data, paths).run()
                self.assertLessEqual(
                    len(turns),
                    target,
                    f"{filename} took {len(turns)} turns",
                )


class ProvidedPerformanceTests(unittest.TestCase):
    """Protect the turn targets for the supplied challenge-map collection."""

    def test_mandatory_turn_targets(self) -> None:
        """Run all nine supplied mandatory performance maps."""
        maps_directory = BENCHMARK_DIRECTORY.parent
        for relative_path, target in PROVIDED_TARGETS.items():
            with self.subTest(map=relative_path, target=target):
                map_data = MapParser().parse_file(
                    maps_directory / relative_path
                )
                paths = Pathfinder(map_data).find_paths()
                turns = Simulation(map_data, paths).run()
                self.assertLessEqual(
                    len(turns),
                    target,
                    f"{relative_path} took {len(turns)} turns",
                )


if __name__ == "__main__":
    unittest.main()
