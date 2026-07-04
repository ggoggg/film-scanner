from film_scanner.config import AppConfig, ScanConfig
from film_scanner.vision import FrameDetection
from film_scanner.workflow import ScanState, ScannerController


class FakeMotor:
    position_steps = 0

    def __init__(self) -> None:
        self.initialize_calls = 0

    def initialize(self) -> None:
        self.initialize_calls += 1

    def shutdown(self) -> None:
        pass

    def advance_frame(self) -> None:
        self.position_steps += 1


class FakeCamera:
    status = "ready (fake)"

    def __init__(self) -> None:
        self.initialize_calls = 0

    def initialize(self) -> None:
        self.initialize_calls += 1

    def shutdown(self) -> None:
        pass

    def capture_still(self, destination):
        destination.write_text("fake image", encoding="utf-8")


class FakeAligner:
    def align(self, camera, motor) -> FrameDetection:
        return FrameDetection(found=True, error_pixels=0.0, confidence=1.0)


def test_start_reuses_initialized_hardware(tmp_path) -> None:
    config = AppConfig(scan=ScanConfig(output_directory=str(tmp_path), max_frames=1))
    controller = ScannerController(config, simulate=True)
    motor = FakeMotor()
    camera = FakeCamera()
    controller.motor = motor
    controller.camera = camera
    controller.aligner = FakeAligner()

    controller.initialize()
    controller.start(max_frames=1)
    assert controller._worker is not None
    controller._worker.join(timeout=2)

    assert controller.snapshot().state == ScanState.COMPLETE
    assert motor.initialize_calls == 1
    assert camera.initialize_calls == 1
