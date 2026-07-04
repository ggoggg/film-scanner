# Installation Guide

## Raspberry Pi Setup

1. Install Raspberry Pi OS with camera support enabled.
2. Connect the stepper driver pins defined in `config/default.toml`.
3. Install system packages needed by camera, libcamera, and GPIO Python modules:

```bash
sudo apt update
sudo apt install libcap-dev python3-libcamera python3-picamera2 python3-pil.imagetk
```

4. Create a virtual environment that can see Raspberry Pi OS camera bindings:

```bash
python3 -m venv --system-site-packages env
source env/bin/activate
```

5. Install the package:

```bash
python3 -m pip install -e ".[pi,vision]"
```

If a large wheel download times out, rerun the install with download resumption enabled:

```bash
python3 -m pip install --resume-retries 5 --timeout 120 -e ".[pi,vision]"
```

6. Launch the web UI:

```bash
film-scanner-web --config config/default.toml --host 0.0.0.0 --port 8080
```

Open `http://<raspberry-pi-address>:8080` from a browser on the same network.

The Tkinter UI is also available with `film-scanner-ui --config config/default.toml`. It needs a graphical display, so run it from the Raspberry Pi desktop terminal, a VNC session, or an SSH session with X forwarding enabled.

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
