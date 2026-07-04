from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
import time
from typing import Optional

from .config import MotorConfig

LOG = logging.getLogger(__name__)


class Direction(Enum):
    FORWARD = 1
    REVERSE = -1


@dataclass
class MotorStatus:
    enabled: bool
    position_steps: int
    moving: bool = False
    simulated: bool = False


class StepperMotor:
    def __init__(self, config: MotorConfig, simulate: bool = False) -> None:
        self.config = config
        self.position_steps = 0
        self.enabled = False
        self.moving = False
        self.simulated = simulate
        self._gpio = None

        if not simulate:
            try:
                import RPi.GPIO as GPIO  # type: ignore

                self._gpio = GPIO
            except Exception as exc:  # pragma: no cover - hardware dependent
                LOG.warning("GPIO unavailable, using simulated motor: %s", exc)
                self.simulated = True

    def initialize(self) -> None:
        if self._gpio is not None:
            gpio = self._gpio
            gpio.setmode(gpio.BCM)
            pins = [self.config.step_pin, self.config.direction_pin]
            if self.config.enable_pin is not None:
                pins.append(self.config.enable_pin)
            pins.extend(self.config.microstep_pins)
            for pin in pins:
                gpio.setup(pin, gpio.OUT)
            if self.config.enable_pin is not None:
                gpio.output(self.config.enable_pin, gpio.LOW)
        self.enabled = True
        LOG.info("Motor initialized")

    def shutdown(self) -> None:
        self.moving = False
        self.enabled = False
        if self._gpio is not None:
            if self.config.enable_pin is not None:
                self._gpio.output(self.config.enable_pin, self._gpio.HIGH)
            self._gpio.cleanup()
        LOG.info("Motor shut down at position %s", self.position_steps)

    def status(self) -> MotorStatus:
        return MotorStatus(
            enabled=self.enabled,
            position_steps=self.position_steps,
            moving=self.moving,
            simulated=self.simulated,
        )

    def jog(self, direction: Direction, steps: Optional[int] = None) -> None:
        self.move_steps(direction.value * (steps or self.config.fine_step))

    def advance_frame(self) -> None:
        self.move_steps(self.config.steps_per_frame)

    def reverse_frame(self) -> None:
        self.move_steps(-self.config.steps_per_frame)

    def move_steps(self, signed_steps: int) -> None:
        if signed_steps == 0:
            return
        if not self.enabled:
            self.initialize()

        direction = Direction.FORWARD if signed_steps > 0 else Direction.REVERSE
        steps = abs(signed_steps)
        LOG.info("Motor move %s steps %s", direction.name.lower(), steps)
        self.moving = True
        try:
            if self._gpio is not None:
                self._gpio.output(
                    self.config.direction_pin,
                    self._gpio.HIGH if direction is Direction.FORWARD else self._gpio.LOW,
                )
            self._pulse_steps(steps)
            self.position_steps += direction.value * steps
            time.sleep(self.config.settle_ms / 1000)
        finally:
            self.moving = False

    def _pulse_steps(self, steps: int) -> None:
        min_interval = 1.0 / max(self.config.speed_steps_per_second, 1.0)
        accel = max(self.config.acceleration_steps_per_second2, 1.0)
        for index in range(steps):
            ramp_limit = min(steps // 2, max(int(self.config.speed_steps_per_second / accel), 1))
            if ramp_limit and index < ramp_limit:
                interval = min_interval * (ramp_limit / max(index + 1, 1))
            elif ramp_limit and index >= steps - ramp_limit:
                interval = min_interval * (ramp_limit / max(steps - index, 1))
            else:
                interval = min_interval

            if self._gpio is not None:
                self._gpio.output(self.config.step_pin, self._gpio.HIGH)
                time.sleep(interval / 2)
                self._gpio.output(self.config.step_pin, self._gpio.LOW)
                time.sleep(interval / 2)
            else:
                time.sleep(min(interval, 0.002))
