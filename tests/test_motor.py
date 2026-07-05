from film_scanner.config import MotorConfig
from film_scanner.motor import Direction, StepperMotor


class FakeGPIO:
    BCM = "BCM"
    OUT = "OUT"
    HIGH = 1
    LOW = 0

    def __init__(self) -> None:
        self.mode = None
        self.setup_pins = []
        self.outputs = []
        self.cleaned = False

    def setmode(self, mode) -> None:
        self.mode = mode

    def setup(self, pin, mode) -> None:
        self.setup_pins.append((pin, mode))

    def output(self, pin, value) -> None:
        self.outputs.append((pin, value))

    def cleanup(self) -> None:
        self.cleaned = True


def test_uln2003_initializes_coil_pins_and_releases_on_shutdown() -> None:
    gpio = FakeGPIO()
    motor = StepperMotor(MotorConfig(driver="uln2003", coil_pins=[17, 27, 22, 23]), simulate=True)
    motor._gpio = gpio
    motor.simulated = False

    motor.initialize()
    motor.shutdown()

    assert gpio.setup_pins == [(17, "OUT"), (27, "OUT"), (22, "OUT"), (23, "OUT")]
    assert gpio.outputs[:4] == [(17, 0), (27, 0), (22, 0), (23, 0)]
    assert gpio.outputs[-4:] == [(17, 0), (27, 0), (22, 0), (23, 0)]
    assert gpio.cleaned is True


def test_uln2003_move_uses_half_step_sequence() -> None:
    gpio = FakeGPIO()
    motor = StepperMotor(MotorConfig(driver="uln2003", coil_pins=[17, 27, 22, 23], speed_steps_per_second=1000), simulate=True)
    motor._gpio = gpio
    motor.simulated = False
    motor.initialize()
    gpio.outputs.clear()

    motor.jog(Direction.FORWARD, steps=2)

    assert gpio.outputs[:8] == [
        (17, 1),
        (27, 1),
        (22, 0),
        (23, 0),
        (17, 0),
        (27, 1),
        (22, 0),
        (23, 0),
    ]
    assert motor.position_steps == 2


def test_step_dir_driver_keeps_existing_pin_setup() -> None:
    gpio = FakeGPIO()
    config = MotorConfig(driver="step_dir", step_pin=5, direction_pin=6, enable_pin=13, microstep_pins=[19, 26])
    motor = StepperMotor(config, simulate=True)
    motor._gpio = gpio
    motor.simulated = False

    motor.initialize()

    assert gpio.setup_pins == [(5, "OUT"), (6, "OUT"), (13, "OUT"), (19, "OUT"), (26, "OUT")]
    assert gpio.outputs == [(13, 0)]
