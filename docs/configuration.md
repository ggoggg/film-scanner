# Configuration Guide

Configuration is stored in TOML. The default file is `config/default.toml`.

## Motor

- `step_pin`, `direction_pin`, `enable_pin`: Raspberry Pi BCM GPIO pins connected to the motor driver.
- `microstep_pins`: optional GPIO pins for driver microstepping mode selection.
- `steps_per_frame`: coarse movement between adjacent film frames.
- `fine_step`: manual and alignment jog size.
- `speed_steps_per_second`: step pulse rate.
- `acceleration_steps_per_second2`: acceleration and deceleration ramp.
- `settle_ms`: wait time after movement before preview or capture.

## Camera

- `resolution_width`, `resolution_height`: still capture size.
- `preview_width`, `preview_height`: alignment preview size.
- `exposure_us`, `iso`, `white_balance`, `gain`: camera parameters reserved for hardware configuration.
- `format`: output file extension, normally `png` or `tiff`.

## Alignment

- `tolerance_pixels`: acceptable vertical frame error before capture.
- `max_attempts`: maximum preview/correction loops per frame.
- `pixels_per_motor_step`: calibration value used to convert detected error into motor steps.
- `coarse_search_steps`: movement used when no frame boundary is detected.

## Scan

- `output_directory`: root directory for captured images.
- `naming_pattern`: Python format string using `{frame}`.
- `prevent_overwrite`: fail instead of overwriting existing images.
- `max_frames`: zero means continue until stopped.
