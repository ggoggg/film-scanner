# Installation Guide

## Raspberry Pi Setup

1. Install Raspberry Pi OS with camera support enabled.
2. Connect the stepper driver pins defined in `config/default.toml`.
3. Create a virtual environment.
4. Install the package:

```bash
python3 -m pip install -e ".[pi,vision]"
```

5. Launch the UI:

```bash
film-scanner-ui --config config/default.toml
```

## Development Machine

Run in simulation mode from the repository:

```bash
PYTHONPATH=src python3 -m film_scanner.cli --simulate --frames 5
PYTHONPATH=src python3 -m film_scanner.ui --simulate
```

Optional packages:

- `Pillow` enables simulated PNG/TIFF image generation and UI preview display.
- `opencv-python` and `numpy` enable real frame detection.
- `pytest` runs the test suite.
