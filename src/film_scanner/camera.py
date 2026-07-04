from __future__ import annotations

from datetime import datetime
from pathlib import Path
import logging
import threading

from .config import CameraConfig

LOG = logging.getLogger(__name__)


class Camera:
    def __init__(self, config: CameraConfig, simulate: bool = False) -> None:
        self.config = config
        self.simulated = simulate
        self._camera = None
        self._started = False
        self._preview_stats_logged = False
        self._lock = threading.RLock()
        if not simulate:
            try:
                from picamera2 import Picamera2  # type: ignore

                self._camera = Picamera2()
            except ModuleNotFoundError as exc:  # pragma: no cover - hardware dependent
                LOG.warning(
                    "Picamera2 is not installed. Falling back to simulated camera. "
                    "Install Raspberry Pi camera packages with apt and create the venv with "
                    "--system-site-packages so python3-picamera2 and python3-libcamera are visible. "
                    "Original error: %s",
                    exc,
                )
                self.simulated = True
            except Exception as exc:  # pragma: no cover - hardware dependent
                LOG.warning("Picamera2 initialization failed, using simulated camera: %s", exc)
                self.simulated = True

    @property
    def status(self) -> str:
        if self._camera is not None:
            return "ready (picamera2)"
        if self.simulated:
            return "simulated"
        return "not initialized"

    def initialize(self) -> None:
        with self._lock:
            if self._camera is not None and not self._started:
                preview = self._camera.create_preview_configuration(
                    main={"size": (self.config.preview_width, self.config.preview_height), "format": "RGB888"}
                )
                self._camera.configure(preview)
                self._camera.start()
                self._started = True
        LOG.info("Camera initialized")

    def shutdown(self) -> None:
        with self._lock:
            if self._camera is not None and self._started:
                self._camera.stop()
                self._started = False
        LOG.info("Camera shut down")

    def capture_preview(self):
        with self._lock:
            if self._camera is not None:
                preview = self._camera.capture_array()
            else:
                preview = self._synthetic_image(self.config.preview_width, self.config.preview_height)

        if not self._preview_stats_logged and hasattr(preview, "shape"):
            LOG.info(
                "Preview frame captured: shape=%s dtype=%s min=%s max=%s mean=%.1f",
                getattr(preview, "shape", None),
                getattr(preview, "dtype", None),
                preview.min(),
                preview.max(),
                float(preview.mean()),
            )
            self._preview_stats_logged = True
        return preview

    def capture_still(self, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if self._camera is not None:
                still_config = self._camera.create_still_configuration(
                    main={"size": (self.config.resolution_width, self.config.resolution_height)}
                )
                self._camera.switch_mode_and_capture_file(still_config, str(destination))
            else:
                self._write_synthetic_file(destination)
        LOG.info("Captured image %s", destination)
        return destination

    def _synthetic_image(self, width: int, height: int):
        try:
            import numpy as np  # type: ignore

            image = np.zeros((height, width, 3), dtype=np.uint8)
            image[:, :] = (20, 20, 20)
            margin_x = width // 8
            margin_y = height // 7
            image[margin_y : height - margin_y, margin_x : width - margin_x] = (190, 175, 145)
            image[margin_y + 20 : height - margin_y - 20, margin_x + 40 : width - margin_x - 40] = (
                80,
                110,
                135,
            )
            return image
        except Exception:
            return {
                "width": width,
                "height": height,
                "captured_at": datetime.now().isoformat(timespec="seconds"),
            }

    def _write_synthetic_file(self, destination: Path) -> None:
        try:
            from PIL import Image, ImageDraw  # type: ignore

            image = Image.new(
                "RGB",
                (self.config.resolution_width, self.config.resolution_height),
                color=(30, 30, 30),
            )
            draw = ImageDraw.Draw(image)
            inset_x = self.config.resolution_width // 8
            inset_y = self.config.resolution_height // 7
            draw.rectangle(
                [
                    inset_x,
                    inset_y,
                    self.config.resolution_width - inset_x,
                    self.config.resolution_height - inset_y,
                ],
                fill=(185, 170, 140),
            )
            draw.rectangle(
                [
                    inset_x + 160,
                    inset_y + 80,
                    self.config.resolution_width - inset_x - 160,
                    self.config.resolution_height - inset_y - 80,
                ],
                fill=(75, 105, 135),
            )
            image.save(destination)
        except Exception:
            destination.write_text(
                "Simulated camera capture. Install Pillow for synthetic image output.\n",
                encoding="utf-8",
            )
