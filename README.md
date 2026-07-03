# Frame-by-Frame 8 mm Film Digitization System

This repository contains an initial Python implementation for an automated Super 8 / Regular 8 frame scanner driven by a Raspberry Pi 4, GPIO stepper motor control, a Pi camera module, and computer-vision based frame alignment.

## What is included

- GPIO stepper driver with simulation fallback
- Camera abstraction with Picamera2 support and simulation fallback
- Frame detection and iterative alignment modules
- Automated scan workflow with pause, resume, stop, and manual jog controls
- Tkinter operator interface
- Sequential PNG/TIFF image storage with overwrite protection
- TOML configuration and rotating logs
- Architecture, installation, configuration, and operating documentation

## Quick start on a development machine

```bash
PYTHONPATH=src python3 -m film_scanner.cli --simulate --frames 5
PYTHONPATH=src python3 -m film_scanner.ui --simulate
```

## Quick start on Raspberry Pi

Install the project in editable mode with the Raspberry Pi extras:

```bash
python3 -m pip install -e ".[pi,vision]"
film-scanner-ui --config config/default.toml
```

The application automatically falls back to simulation mode if GPIO or camera libraries are unavailable. Use `--simulate` explicitly when testing without hardware.

## Documentation

- [Software architecture](docs/architecture.md)
- [Installation guide](docs/installation.md)
- [Configuration guide](docs/configuration.md)
- [Operating instructions](docs/operating.md)
