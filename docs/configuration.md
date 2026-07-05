# Configuration Guide

Configuration is stored in TOML. The default file is `config/default.toml`.

## Motor

- `driver`: `uln2003` for a 4-input ULN2003 board, or `step_dir` for a step/direction driver.
- `coil_pins`: Raspberry Pi BCM GPIO pins connected to ULN2003 `IN1`, `IN2`, `IN3`, and `IN4`.
- `invert_direction`: reverse the physical motor direction while keeping UI commands and logical position unchanged.
- `step_pin`, `direction_pin`, `enable_pin`: Raspberry Pi BCM GPIO pins connected to a step/direction motor driver.
- `microstep_pins`: optional GPIO pins for step/direction driver microstepping mode selection.
- `steps_per_frame`: coarse movement between adjacent film frames.
- `fine_step`: manual and alignment jog size.
- `speed_steps_per_second`: step rate.
- `acceleration_steps_per_second2`: acceleration and deceleration ramp for step/direction drivers.
- `settle_ms`: wait time after movement before preview or capture.

Default ULN2003 wiring uses these Raspberry Pi 4 BCM pins:

| Raspberry Pi BCM | Physical pin | ULN2003 board |
| --- | --- | --- |
| GPIO17 | 11 | IN1 |
| GPIO27 | 13 | IN2 |
| GPIO22 | 15 | IN3 |
| GPIO23 | 16 | IN4 |
| GND | 6 | GND |

Power the motor from an external supply through the ULN2003 board motor power input. Tie the external supply ground to Raspberry Pi ground.

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
- `frame_guide_x`, `frame_guide_y`, `frame_guide_width`, `frame_guide_height`: preview overlay rectangle used to calibrate expected frame position.
- `perf_roi_x`, `perf_roi_y`, `perf_roi_width`, `perf_roi_height`: preview overlay region for perforation detection calibration.
- `perf_target_y`: preview overlay horizontal target line for the perforation center.

## Scan

- `output_directory`: root directory for captured images.
- `naming_pattern`: Python format string using `{frame}`.
- `prevent_overwrite`: fail instead of overwriting existing images.
- `max_frames`: zero means continue until stopped.
