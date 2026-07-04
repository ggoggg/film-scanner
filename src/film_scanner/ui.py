from __future__ import annotations

from pathlib import Path
import argparse
import logging
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .config import AppConfig, load_config
from .logging_setup import configure_logging
from .motor import Direction
from .workflow import ScannerController, ScanState

LOG = logging.getLogger(__name__)


class FilmScannerApp(tk.Tk):
    def __init__(self, config: AppConfig, simulate: bool = False) -> None:
        super().__init__()
        self.title("8 mm Film Scanner")
        self.minsize(1120, 720)
        self.config_data = config
        self.controller = ScannerController(config, simulate=simulate)
        self.preview_image = None
        self.vars: dict[str, tk.StringVar] = {}

        self._build_layout()
        self._apply_config_to_fields()
        self.after(100, self._initialize_controller)
        self.after(self.config_data.ui.refresh_ms, self._refresh)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        preview_frame = ttk.Frame(self, padding=12)
        preview_frame.grid(row=0, column=0, sticky="nsew")
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_frame, anchor="center", text="Live preview")
        self.preview_label.grid(row=0, column=0, sticky="nsew")

        side = ttk.Frame(self, padding=(0, 12, 12, 12))
        side.grid(row=0, column=1, sticky="nsew")
        side.columnconfigure(0, weight=1)

        self._build_controls(side)
        self._build_status(side)
        self._build_config(side)

    def _build_controls(self, parent: ttk.Frame) -> None:
        controls = ttk.LabelFrame(parent, text="Controls", padding=10)
        controls.grid(row=0, column=0, sticky="ew")
        for col in range(4):
            controls.columnconfigure(col, weight=1)

        ttk.Button(controls, text="Start", command=self._start).grid(row=0, column=0, sticky="ew", padx=3, pady=3)
        ttk.Button(controls, text="Pause", command=self.controller.pause).grid(row=0, column=1, sticky="ew", padx=3, pady=3)
        ttk.Button(controls, text="Resume", command=self.controller.resume).grid(row=0, column=2, sticky="ew", padx=3, pady=3)
        ttk.Button(controls, text="Stop", command=self.controller.stop).grid(row=0, column=3, sticky="ew", padx=3, pady=3)

        ttk.Button(controls, text="Forward", command=lambda: self.controller.manual_jog(Direction.FORWARD, fine=False)).grid(
            row=1, column=0, sticky="ew", padx=3, pady=3
        )
        ttk.Button(controls, text="Reverse", command=lambda: self.controller.manual_jog(Direction.REVERSE, fine=False)).grid(
            row=1, column=1, sticky="ew", padx=3, pady=3
        )
        ttk.Button(controls, text="Fine +", command=lambda: self.controller.manual_jog(Direction.FORWARD, fine=True)).grid(
            row=1, column=2, sticky="ew", padx=3, pady=3
        )
        ttk.Button(controls, text="Fine -", command=lambda: self.controller.manual_jog(Direction.REVERSE, fine=True)).grid(
            row=1, column=3, sticky="ew", padx=3, pady=3
        )

    def _build_status(self, parent: ttk.Frame) -> None:
        status = ttk.LabelFrame(parent, text="Status", padding=10)
        status.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        status.columnconfigure(1, weight=1)

        self.status_labels: dict[str, ttk.Label] = {}
        for row, key in enumerate(
            ("state", "frame_number", "motor_status", "camera_status", "alignment_status", "current_file", "message")
        ):
            ttk.Label(status, text=key.replace("_", " ").title()).grid(row=row, column=0, sticky="w", pady=2)
            label = ttk.Label(status, text="-", anchor="w", wraplength=380)
            label.grid(row=row, column=1, sticky="ew", pady=2)
            self.status_labels[key] = label

    def _build_config(self, parent: ttk.Frame) -> None:
        notebook = ttk.Notebook(parent)
        notebook.grid(row=2, column=0, sticky="nsew", pady=(12, 0))
        parent.rowconfigure(2, weight=1)

        motor = ttk.Frame(notebook, padding=10)
        camera = ttk.Frame(notebook, padding=10)
        scan = ttk.Frame(notebook, padding=10)
        notebook.add(motor, text="Motor")
        notebook.add(camera, text="Camera")
        notebook.add(scan, text="Scan")

        self._field(motor, "motor.speed_steps_per_second", "Speed", 0)
        self._field(motor, "motor.acceleration_steps_per_second2", "Acceleration", 1)
        self._field(motor, "motor.steps_per_frame", "Steps / frame", 2)
        self._field(motor, "motor.fine_step", "Fine step", 3)
        self._field(motor, "alignment.tolerance_pixels", "Tolerance px", 4)

        self._field(camera, "camera.resolution_width", "Width", 0)
        self._field(camera, "camera.resolution_height", "Height", 1)
        self._field(camera, "camera.exposure_us", "Exposure us", 2)
        self._field(camera, "camera.iso", "ISO", 3)
        self._field(camera, "camera.format", "Format", 4)

        self._field(scan, "scan.output_directory", "Output", 0, browse=True)
        self._field(scan, "scan.naming_pattern", "Naming", 1)
        self._field(scan, "scan.max_frames", "Max frames", 2)
        ttk.Button(scan, text="Apply Configuration", command=self._apply_fields_to_config).grid(
            row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0)
        )

    def _field(self, parent: ttk.Frame, key: str, label: str, row: int, browse: bool = False) -> None:
        parent.columnconfigure(1, weight=1)
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar()
        self.vars[key] = var
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
        if browse:
            ttk.Button(parent, text="Browse", command=lambda: self._choose_directory(var)).grid(
                row=row, column=2, padx=(8, 0), pady=4
            )

    def _initialize_controller(self) -> None:
        try:
            self.controller.initialize()
        except Exception as exc:
            messagebox.showerror("Initialization failed", str(exc))

    def _start(self) -> None:
        self._apply_fields_to_config()
        max_frames = self.config_data.scan.max_frames or None
        self.controller.start(max_frames=max_frames)

    def _choose_directory(self, var: tk.StringVar) -> None:
        selected = filedialog.askdirectory(initialdir=var.get() or str(Path.cwd()))
        if selected:
            var.set(selected)

    def _apply_config_to_fields(self) -> None:
        for key, var in self.vars.items():
            section_name, attr = key.split(".", 1)
            var.set(str(getattr(getattr(self.config_data, section_name), attr)))

    def _apply_fields_to_config(self) -> None:
        converters = {
            int: int,
            float: float,
            bool: lambda value: value.lower() in {"1", "true", "yes", "on"},
            str: str,
        }
        for key, var in self.vars.items():
            section_name, attr = key.split(".", 1)
            section = getattr(self.config_data, section_name)
            current = getattr(section, attr)
            converter = converters.get(type(current), str)
            try:
                setattr(section, attr, converter(var.get()))
            except ValueError:
                messagebox.showwarning("Invalid value", f"Could not apply {key}: {var.get()}")

    def _refresh(self) -> None:
        status = self.controller.snapshot()
        values = {
            "state": status.state.value,
            "frame_number": str(status.frame_number),
            "motor_status": status.motor_status,
            "camera_status": status.camera_status,
            "alignment_status": status.alignment_status,
            "current_file": status.current_file,
            "message": status.message,
        }
        for key, value in values.items():
            self.status_labels[key].configure(text=value or "-")

        if status.state not in {ScanState.ERROR, ScanState.STOPPING}:
            self._refresh_preview()
        self.after(self.config_data.ui.refresh_ms, self._refresh)

    def _refresh_preview(self) -> None:
        preview = self.controller.capture_preview()
        try:
            from PIL import Image, ImageTk  # type: ignore

            if hasattr(preview, "shape"):
                image = Image.fromarray(preview)
            else:
                image = Image.new("RGB", (640, 480), (35, 35, 35))
            width = max(self.preview_label.winfo_width(), 320)
            height = max(self.preview_label.winfo_height(), 240)
            image.thumbnail((width, height))
            self.preview_image = ImageTk.PhotoImage(image)
            self.preview_label.configure(image=self.preview_image, text="")
        except Exception as exc:
            LOG.warning("Live preview display failed: %s", exc)
            self.preview_label.configure(text="Live preview unavailable. Install Pillow for image display.")

    def _on_close(self) -> None:
        self.controller.shutdown()
        self.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch the 8 mm film scanner operator UI")
    parser.add_argument("--config", default=None, help="Path to TOML configuration file")
    parser.add_argument("--simulate", action="store_true", help="Run without GPIO/camera hardware")
    args = parser.parse_args()
    configure_logging()
    try:
        app = FilmScannerApp(load_config(args.config), simulate=args.simulate)
    except tk.TclError as exc:
        message = (
            "Could not open the Tkinter UI because no graphical display is available. "
            "Run film-scanner-ui from the Raspberry Pi desktop terminal, connect with VNC, "
            "or SSH with X forwarding enabled."
        )
        LOG.error("%s Original error: %s", message, exc)
        print(message, file=sys.stderr)
        raise SystemExit(1) from exc
    app.mainloop()


if __name__ == "__main__":
    main()
