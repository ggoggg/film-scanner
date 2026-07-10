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
python3 -m pip install -e .
film-scanner --simulate --frames 5
film-scanner-ui --simulate
```

Move only the stepper motor by providing a step count, speed (steps/second), and direction:

```bash
film-stepper --steps 200 --speed 400 -d f
film-stepper --steps 50 --speed 100 -d r --simulate
```

The utility can also be run directly from a source checkout without installation
or `PYTHONPATH`:

```bash
python3 src/film_scanner/stepper_cli.py --steps 200 --speed 400 -d f
```

## Quick start on Raspberry Pi

Install Raspberry Pi camera packages, create a venv that can see them, then install the project:

```bash
sudo apt install libcap-dev python3-libcamera python3-picamera2 python3-pil python3-pil.imagetk python3-opencv python3-numpy
python3 -m venv --system-site-packages env
source env/bin/activate
python3 -m pip install -e ".[pi,vision]"
film-scanner-web --config config/default.toml --host 0.0.0.0 --port 8080
```

Open `http://<raspberry-pi-address>:8080` from a browser on the same network. The Tkinter UI is still available with `film-scanner-ui --config config/default.toml` when running from a graphical desktop session.

The application automatically falls back to simulation mode if GPIO or camera libraries are unavailable. Use `--simulate` explicitly when testing without hardware.

## Documentation

- [Software architecture](docs/architecture.md)
- [Installation guide](docs/installation.md)
- [Configuration guide](docs/configuration.md)
- [Operating instructions](docs/operating.md)
