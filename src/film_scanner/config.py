from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.10
    tomllib = None


@dataclass
class MotorConfig:
    driver: str = "uln2003"
    step_pin: int = 17
    direction_pin: int = 27
    enable_pin: int | None = 22
    microstep_pins: list[int] = field(default_factory=list)
    coil_pins: list[int] = field(default_factory=lambda: [17, 27, 22, 23])
    steps_per_frame: int = 240
    fine_step: int = 4
    speed_steps_per_second: float = 450.0
    acceleration_steps_per_second2: float = 900.0
    settle_ms: int = 80


@dataclass
class CameraConfig:
    resolution_width: int = 4056
    resolution_height: int = 3040
    preview_width: int = 960
    preview_height: int = 720
    exposure_us: int = 10000
    iso: int = 100
    white_balance: str = "auto"
    gain: float = 1.0
    format: str = "png"


@dataclass
class AlignmentConfig:
    tolerance_pixels: float = 3.0
    max_attempts: int = 12
    pixels_per_motor_step: float = 0.35
    coarse_search_steps: int = 32


@dataclass
class ScanConfig:
    output_directory: str = "scans"
    naming_pattern: str = "frame_{frame:06d}"
    prevent_overwrite: bool = True
    max_frames: int = 0


@dataclass
class UIConfig:
    refresh_ms: int = 250


@dataclass
class AppConfig:
    motor: MotorConfig = field(default_factory=MotorConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    ui: UIConfig = field(default_factory=UIConfig)


def _merge_dataclass(instance: object, values: dict) -> object:
    for key, value in values.items():
        if hasattr(instance, key):
            setattr(instance, key, value)
    return instance


def load_config(path: str | Path | None = None) -> AppConfig:
    config = AppConfig()
    if path is None:
        default_path = Path("config/default.toml")
        path = default_path if default_path.exists() else None
    if path is None:
        return config

    config_path = Path(path)
    if tomllib is not None:
        with config_path.open("rb") as handle:
            raw = tomllib.load(handle)
    else:
        raw = _parse_simple_toml(config_path.read_text(encoding="utf-8"))

    for section_name in ("motor", "camera", "alignment", "scan", "ui"):
        values = raw.get(section_name, {})
        section = getattr(config, section_name)
        _merge_dataclass(section, values)
    return config


def _parse_simple_toml(text: str) -> dict:
    parsed: dict[str, dict] = {}
    current_section: dict | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = parsed.setdefault(line[1:-1].strip(), {})
            continue
        if current_section is None or "=" not in line:
            continue
        key, raw_value = [part.strip() for part in line.split("=", 1)]
        current_section[key] = _parse_simple_value(raw_value)
    return parsed


def _parse_simple_value(value: str):
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_simple_value(item.strip()) for item in inner.split(",")]
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value
