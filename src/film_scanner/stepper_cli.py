from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

if __package__:
    from .config import load_config
    from .motor import Direction, StepperMotor
else:
    # Allow direct execution: python3 src/film_scanner/stepper_cli.py
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from film_scanner.config import load_config
    from film_scanner.motor import Direction, StepperMotor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Move the film scanner stepper motor a specific number of steps."
    )
    parser.add_argument("--steps", type=positive_int, required=True, help="Number of steps to move")
    parser.add_argument(
        "--speed",
        type=positive_float,
        required=True,
        metavar="STEPS_PER_SECOND",
        help="Maximum movement speed in steps per second",
    )
    parser.add_argument(
        "-d",
        "--direction",
        choices=("f", "r"),
        required=True,
        help="Movement direction: f=forward, r=reverse",
    )
    parser.add_argument("--config", help="Path to a TOML configuration file")
    parser.add_argument("--simulate", action="store_true", help="Run without GPIO hardware")
    return parser


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = load_config(args.config)
    config.motor.speed_steps_per_second = args.speed
    direction = Direction.FORWARD if args.direction == "f" else Direction.REVERSE
    signed_steps = direction.value * args.steps

    motor = StepperMotor(config.motor, simulate=args.simulate)
    try:
        motor.initialize()
        motor.move_steps(signed_steps)
    except KeyboardInterrupt:
        logging.getLogger(__name__).warning("Movement interrupted")
        return 130
    finally:
        motor.shutdown()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
