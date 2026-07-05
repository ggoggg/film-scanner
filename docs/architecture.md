# Software Architecture

The scanner is organized as small modules that can be tested without Raspberry Pi hardware.

## Modules

- `film_scanner.motor`: GPIO motor control for ULN2003 4-coil sequencing or step/direction drivers, manual jog, acceleration ramping, and shutdown.
- `film_scanner.camera`: Picamera2 integration, preview capture, still capture, and simulated captures.
- `film_scanner.vision`: frame boundary detection and iterative frame alignment.
- `film_scanner.storage`: sequential file naming, output directory creation, and overwrite prevention.
- `film_scanner.workflow`: scanning state machine, pause/resume/stop, frame loop, logging, and hardware coordination.
- `film_scanner.ui`: Tkinter operator interface for live preview, controls, status, and configuration.
- `film_scanner.config`: TOML-backed application settings.

## Scan Sequence

1. Initialize motor, camera, storage, and logging.
2. Advance the film by the configured frame step distance.
3. Capture a preview image.
4. Detect the film frame boundary.
5. Convert frame error into motor correction steps.
6. Repeat preview and correction until the configured tolerance is reached.
7. Capture and save the high-resolution still image.
8. Increment the frame counter and continue until stopped, complete, or failed.

## Hardware Fallbacks

The motor and camera modules try to import Raspberry Pi libraries lazily. If `RPi.GPIO` or `picamera2` is unavailable, they run in simulation mode. This allows desktop development, CI checks, and UI testing without hardware.
