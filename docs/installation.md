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

Install the package and run in simulation mode from the repository:

```bash
python3 -m pip install -e .
film-scanner --simulate --frames 5
film-scanner-ui --simulate
```

Optional packages:

- `opencv-python` and `numpy` enable real frame detection.
- `pytest` runs the test suite.
