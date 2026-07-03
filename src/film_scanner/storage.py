from __future__ import annotations

from pathlib import Path

from .config import CameraConfig, ScanConfig


class ImageStore:
    def __init__(self, scan_config: ScanConfig, camera_config: CameraConfig) -> None:
        self.scan_config = scan_config
        self.camera_config = camera_config
        self.root = Path(scan_config.output_directory)

    def prepare(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        return self.root

    def path_for_frame(self, frame_number: int) -> Path:
        suffix = self.camera_config.format.lower().lstrip(".")
        base_name = self.scan_config.naming_pattern.format(frame=frame_number)
        candidate = self.root / f"{base_name}.{suffix}"
        if not self.scan_config.prevent_overwrite:
            return candidate
        if candidate.exists():
            raise FileExistsError(f"Refusing to overwrite existing scan image: {candidate}")
        return candidate
