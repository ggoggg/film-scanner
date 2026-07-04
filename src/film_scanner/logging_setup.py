from __future__ import annotations

from logging.handlers import RotatingFileHandler
from pathlib import Path
import logging
from typing import Union


def configure_logging(log_dir: Union[str, Path] = "logs") -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    file_handler = RotatingFileHandler(
        Path(log_dir) / "film-scanner.log",
        maxBytes=1_000_000,
        backupCount=5,
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)
