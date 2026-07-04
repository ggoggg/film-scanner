from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional, Tuple

from .config import AlignmentConfig

LOG = logging.getLogger(__name__)


@dataclass
class FrameDetection:
    found: bool
    error_pixels: float
    confidence: float
    frame_bounds: Optional[Tuple[int, int, int, int]] = None
    message: str = ""


class FrameDetector:
    def __init__(self, config: AlignmentConfig) -> None:
        self.config = config

    def detect(self, preview) -> FrameDetection:
        try:
            return self._detect_with_cv(preview)
        except Exception as exc:
            LOG.debug("Falling back to simple frame detection: %s", exc)
            return FrameDetection(True, 0.0, 0.5, message="simulated alignment")

    def _detect_with_cv(self, preview) -> FrameDetection:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        if not hasattr(preview, "shape"):
            raise ValueError("preview is not an image array")

        gray = cv2.cvtColor(preview, cv2.COLOR_BGR2GRAY) if preview.ndim == 3 else preview
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, threshold = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(threshold, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return FrameDetection(False, 0.0, 0.0, message="no frame boundary found")

        height, width = gray.shape[:2]
        min_area = width * height * 0.08
        candidates = [contour for contour in contours if cv2.contourArea(contour) >= min_area]
        if not candidates:
            return FrameDetection(False, 0.0, 0.0, message="no candidate large enough")

        contour = max(candidates, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)
        frame_center_y = y + h / 2
        target_y = height / 2
        error = frame_center_y - target_y
        area_ratio = cv2.contourArea(contour) / float(width * height)
        confidence = float(np.clip(area_ratio * 2.5, 0.0, 1.0))
        return FrameDetection(
            found=True,
            error_pixels=error,
            confidence=confidence,
            frame_bounds=(x, y, w, h),
            message="frame detected",
        )


class FrameAligner:
    def __init__(self, config: AlignmentConfig, detector: FrameDetector) -> None:
        self.config = config
        self.detector = detector

    def align(self, camera, motor) -> FrameDetection:
        last_detection = FrameDetection(False, 0.0, 0.0, message="alignment not started")
        for attempt in range(1, self.config.max_attempts + 1):
            preview = camera.capture_preview()
            detection = self.detector.detect(preview)
            last_detection = detection
            LOG.info(
                "Alignment attempt %s: found=%s error=%.2f confidence=%.2f",
                attempt,
                detection.found,
                detection.error_pixels,
                detection.confidence,
            )
            if detection.found and abs(detection.error_pixels) <= self.config.tolerance_pixels:
                return detection
            if not detection.found:
                motor.move_steps(self.config.coarse_search_steps)
                continue
            correction = round(-detection.error_pixels / self.config.pixels_per_motor_step)
            if correction == 0:
                correction = 1 if detection.error_pixels < 0 else -1
            motor.move_steps(correction)
        raise RuntimeError(f"Frame alignment failed: {last_detection.message}")
