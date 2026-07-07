from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import time

from .camera import Camera
from .config import AppConfig
from .motor import Direction, StepperMotor
from .storage import ImageStore
from .vision import FrameAligner, FrameDetector

LOG = logging.getLogger(__name__)


class ScanState(Enum):
    IDLE = "idle"
    INITIALIZING = "initializing"
    SCANNING = "scanning"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ScanStatus:
    state: ScanState = ScanState.IDLE
    frame_number: int = 0
    current_file: str = ""
    motor_status: str = "idle"
    camera_status: str = "idle"
    alignment_status: str = "idle"
    message: str = "Ready"
    started_at: float | None = None
    completed_at: float | None = None
    errors: list[str] = field(default_factory=list)


class ScannerController:
    def __init__(self, config: AppConfig, simulate: bool = False) -> None:
        self.config = config
        self.motor = StepperMotor(config.motor, simulate=simulate)
        self.camera = Camera(config.camera, simulate=simulate)
        self.detector = FrameDetector(config.alignment)
        self.aligner = FrameAligner(config.alignment, self.detector)
        self.store = ImageStore(config.scan, config.camera)
        self.status = ScanStatus()
        self._lock = threading.RLock()
        self._pause = threading.Event()
        self._stop = threading.Event()
        self._worker: threading.Thread | None = None
        self._initialized = False
        self._pause.set()

    def initialize(self) -> None:
        if self._initialized:
            with self._lock:
                self.status.state = ScanState.IDLE
                self.status.motor_status = "ready"
                self.status.camera_status = self.camera.status
                self.status.message = "Ready"
            return

        with self._lock:
            self.status.state = ScanState.INITIALIZING
            self.status.message = "Initializing hardware"
        self.store.prepare()
        self.motor.initialize()
        self.camera.initialize()
        self._initialized = True
        with self._lock:
            self.status.state = ScanState.IDLE
            self.status.motor_status = "ready"
            self.status.camera_status = self.camera.status
            self.status.message = "Ready"

    def shutdown(self) -> None:
        self.stop()
        if self._worker is not None:
            self._worker.join(timeout=5)
        self.camera.shutdown()
        self.motor.shutdown()

    def snapshot(self) -> ScanStatus:
        with self._lock:
            return ScanStatus(
                state=self.status.state,
                frame_number=self.status.frame_number,
                current_file=self.status.current_file,
                motor_status=self.status.motor_status,
                camera_status=self.status.camera_status,
                alignment_status=self.status.alignment_status,
                message=self.status.message,
                started_at=self.status.started_at,
                completed_at=self.status.completed_at,
                errors=list(self.status.errors),
            )

    def apply_runtime_config(self) -> None:
        self.motor.config = self.config.motor
        self.detector.config = self.config.alignment
        self.aligner.config = self.config.alignment
        self.store.scan_config = self.config.scan
        self.store.camera_config = self.config.camera
        with self._lock:
            self.status.message = "Configuration applied"
        LOG.info(
            "Runtime configuration applied: steps_per_frame=%s fine_step=%s speed=%.2f settle_ms=%s invert=%s",
            self.config.motor.steps_per_frame,
            self.config.motor.fine_step,
            self.config.motor.speed_steps_per_second,
            self.config.motor.settle_ms,
            self.config.motor.invert_direction,
        )

    def start(self, max_frames: int | None = None) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._pause.set()
        self._worker = threading.Thread(
            target=self._run_scan,
            args=(max_frames,),
            name="film-scan-worker",
            daemon=True,
        )
        self._worker.start()

    def pause(self) -> None:
        self._pause.clear()
        with self._lock:
            self.status.state = ScanState.PAUSED
            self.status.message = "Paused"
        LOG.info("Scan paused")

    def resume(self) -> None:
        self._pause.set()
        with self._lock:
            self.status.state = ScanState.SCANNING
            self.status.message = "Scanning"
        LOG.info("Scan resumed")

    def stop(self) -> None:
        self._stop.set()
        self._pause.set()
        with self._lock:
            if self.status.state in {ScanState.SCANNING, ScanState.PAUSED}:
                self.status.state = ScanState.STOPPING
                self.status.message = "Stopping"
        LOG.info("Scan stop requested")

    def manual_jog(self, direction: Direction, fine: bool = True) -> None:
        steps = self.config.motor.fine_step if fine else self.config.motor.steps_per_frame
        self.motor.jog(direction, steps=steps)
        with self._lock:
            self.status.motor_status = f"position {self.motor.position_steps} steps"
            self.status.message = "Manual move complete"
        LOG.info("Operator jogged motor %s by %s steps", direction.name.lower(), steps)

    def capture_preview(self):
        return self.camera.capture_preview()

    def capture_single(self) -> str:
        if not self._initialized:
            self.initialize()

        next_frame = self.status.frame_number + 1
        destination = self.store.path_for_frame(next_frame)
        with self._lock:
            self.status.camera_status = "capturing"
            self.status.message = "Capturing frame"
        self.camera.capture_still(destination)
        with self._lock:
            self.status.frame_number = next_frame
            self.status.current_file = str(destination)
            self.status.camera_status = self.camera.status
            self.status.message = f"Captured frame {next_frame}"
        LOG.info("Single frame %s saved to %s", next_frame, destination)
        return str(destination)

    def _run_scan(self, max_frames: int | None) -> None:
        try:
            if not self._initialized:
                self.initialize()

            frame_limit = max_frames or self.config.scan.max_frames
            with self._lock:
                self.status.state = ScanState.SCANNING
                self.status.started_at = time.time()
                self.status.completed_at = None
                self.status.message = "Scanning"

            LOG.info("Scan started")
            while not self._stop.is_set():
                if frame_limit and self.status.frame_number >= frame_limit:
                    break
                self._pause.wait()
                if self._stop.is_set():
                    break

                with self._lock:
                    self.status.motor_status = "advancing"
                    self.status.alignment_status = "pending"
                self.motor.advance_frame()

                with self._lock:
                    self.status.motor_status = f"position {self.motor.position_steps} steps"
                    self.status.alignment_status = "aligning"
                detection = self.aligner.align(self.camera, self.motor)

                next_frame = self.status.frame_number + 1
                destination = self.store.path_for_frame(next_frame)
                with self._lock:
                    self.status.camera_status = "capturing"
                    self.status.alignment_status = (
                        f"aligned error={detection.error_pixels:.1f}px confidence={detection.confidence:.2f}"
                    )
                self.camera.capture_still(destination)

                with self._lock:
                    self.status.frame_number = next_frame
                    self.status.current_file = str(destination)
                    self.status.camera_status = self.camera.status
                    self.status.message = f"Captured frame {next_frame}"
                LOG.info("Frame %s saved to %s", next_frame, destination)
        except Exception as exc:
            LOG.exception("Scan failed")
            with self._lock:
                self.status.state = ScanState.ERROR
                self.status.errors.append(str(exc))
                self.status.message = str(exc)
        else:
            with self._lock:
                self.status.state = ScanState.COMPLETE
                self.status.completed_at = time.time()
                self.status.message = "Scan complete"
            LOG.info("Scan complete after %s frames", self.status.frame_number)
