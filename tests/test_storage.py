from pathlib import Path

import pytest

from film_scanner.config import CameraConfig, ScanConfig
from film_scanner.storage import ImageStore


def test_path_for_frame_uses_pattern_and_format(tmp_path: Path) -> None:
    store = ImageStore(
        ScanConfig(output_directory=str(tmp_path), naming_pattern="scan_{frame:04d}"),
        CameraConfig(format="tiff"),
    )

    assert store.path_for_frame(7) == tmp_path / "scan_0007.tiff"


def test_path_for_frame_prevents_overwrite(tmp_path: Path) -> None:
    existing = tmp_path / "frame_000001.png"
    existing.write_text("existing", encoding="utf-8")
    store = ImageStore(ScanConfig(output_directory=str(tmp_path)), CameraConfig())

    with pytest.raises(FileExistsError):
        store.path_for_frame(1)
