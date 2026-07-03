from __future__ import annotations

import argparse
import time

from .config import load_config
from .logging_setup import configure_logging
from .workflow import ScannerController, ScanState


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 8 mm film scanner workflow")
    parser.add_argument("--config", default=None, help="Path to TOML configuration file")
    parser.add_argument("--simulate", action="store_true", help="Run without GPIO/camera hardware")
    parser.add_argument("--frames", type=int, default=None, help="Maximum frames to scan")
    args = parser.parse_args()

    configure_logging()
    controller = ScannerController(load_config(args.config), simulate=args.simulate)
    try:
        controller.start(max_frames=args.frames)
        while True:
            status = controller.snapshot()
            print(
                f"{status.state.value:>12} frame={status.frame_number} "
                f"motor={status.motor_status} align={status.alignment_status} {status.message}"
            )
            if status.state in {ScanState.COMPLETE, ScanState.ERROR}:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        controller.stop()
    finally:
        controller.shutdown()


if __name__ == "__main__":
    main()
