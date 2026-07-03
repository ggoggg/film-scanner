from pathlib import Path

from film_scanner.config import load_config


def test_load_config_overrides_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "scanner.toml"
    config_path.write_text(
        """
[motor]
steps_per_frame = 123

[scan]
output_directory = "custom"
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.motor.steps_per_frame == 123
    assert config.scan.output_directory == "custom"
    assert config.camera.format == "png"
