import subprocess
import sys
from pathlib import Path

from film_scanner.stepper_cli import main


def test_stepper_utility_moves_forward_in_simulation() -> None:
    result = main(
        ["--steps", "3", "--speed", "1000", "-d", "f", "--simulate"]
    )

    assert result == 0


def test_stepper_utility_moves_reverse_in_simulation() -> None:
    result = main(
        ["--steps", "2", "--speed", "1000", "-d", "r", "--simulate"]
    )

    assert result == 0


def test_stepper_utility_can_run_as_a_direct_script() -> None:
    script = Path(__file__).parents[1] / "src" / "film_scanner" / "stepper_cli.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--steps",
            "1",
            "--speed",
            "1000",
            "-d",
            "f",
            "--simulate",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
