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

    def snapshot(self):
        from film_scanner.workflow import ScanStatus

        return ScanStatus()


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
            },
        }
    )

    assert controller.config.motor.steps_per_frame == 321
    assert controller.config.motor.fine_step == 7
    assert controller.config.motor.speed_steps_per_second == 123.5
    assert controller.config.motor.settle_ms == 42
    assert controller.config.motor.invert_direction is True
    assert controller.config.alignment.pixels_per_motor_step == 0.25
    assert controller.config.alignment.coarse_search_steps == 16

    status = _status_payload(controller)
    assert status["config"]["motor"]["steps_per_frame"] == 321
    assert status["config"]["motor"]["invert_direction"] is True
    assert status["config"]["alignment"]["coarse_search_steps"] == 16
