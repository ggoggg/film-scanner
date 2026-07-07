from film_scanner.config import AppConfig
from film_scanner.web_ui import _status_payload


class FakeServer:
    def __init__(self, controller) -> None:
        self.controller = controller


class FakeHandler:
    from film_scanner.web_ui import FilmScannerWebHandler

    _apply_config = FilmScannerWebHandler._apply_config

    def __init__(self, controller) -> None:
        self.server = FakeServer(controller)


class FakeController:
    def __init__(self) -> None:
        self.config = AppConfig()
        self.apply_runtime_config_calls = 0

    def snapshot(self):
        from film_scanner.workflow import ScanStatus

        return ScanStatus()

    def apply_runtime_config(self) -> None:
        self.apply_runtime_config_calls += 1


def test_web_config_updates_motor_and_alignment_settings() -> None:
    controller = FakeController()
    handler = FakeHandler(controller)

    handler._apply_config(
        {
            "motor": {
                "steps_per_frame": 321,
                "fine_step": 7,
                "speed_steps_per_second": 123.5,
                "settle_ms": 42,
                "invert_direction": True,
            },
            "alignment": {
                "pixels_per_motor_step": 0.25,
                "coarse_search_steps": 16,
                "frame_guide_x": 10,
                "frame_guide_y": 20,
                "frame_guide_width": 300,
                "frame_guide_height": 400,
                "perf_roi_x": 30,
                "perf_roi_y": 40,
                "perf_roi_width": 50,
                "perf_roi_height": 60,
                "perf_target_y": 70,
                "super8_perf_x": 80,
                "super8_perf_y": 90,
                "super8_perf_width": 100,
                "super8_perf_height": 110,
            },
        }
    )

    assert controller.config.motor.steps_per_frame == 321
    assert controller.apply_runtime_config_calls == 1
    assert controller.config.motor.fine_step == 7
    assert controller.config.motor.speed_steps_per_second == 123.5
    assert controller.config.motor.settle_ms == 42
    assert controller.config.motor.invert_direction is True
    assert controller.config.alignment.pixels_per_motor_step == 0.25
    assert controller.config.alignment.coarse_search_steps == 16
    assert controller.config.alignment.frame_guide_x == 10
    assert controller.config.alignment.frame_guide_width == 300
    assert controller.config.alignment.perf_roi_x == 30
    assert controller.config.alignment.perf_target_y == 70
    assert controller.config.alignment.super8_perf_x == 80
    assert controller.config.alignment.super8_perf_height == 110

    status = _status_payload(controller)
    assert status["config"]["motor"]["steps_per_frame"] == 321
    assert status["config"]["motor"]["invert_direction"] is True
    assert status["config"]["alignment"]["coarse_search_steps"] == 16
    assert status["config"]["alignment"]["frame_guide_height"] == 400
    assert status["config"]["alignment"]["perf_roi_height"] == 60
    assert status["config"]["alignment"]["super8_perf_width"] == 100
