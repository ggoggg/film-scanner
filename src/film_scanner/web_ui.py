from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import argparse
import io
import json
import logging
import threading

from .config import AppConfig, load_config
from .logging_setup import configure_logging
from .motor import Direction
from .workflow import ScannerController, ScanState

LOG = logging.getLogger(__name__)


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Film Scanner</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #101214;
      --panel: #1b1f23;
      --line: #30363d;
      --text: #f0f3f6;
      --muted: #9da7b1;
      --accent: #69b7ff;
      --danger: #ff6b6b;
    }
    * { box-sizing: border-box; }
    html {
      height: 100%;
      overflow: hidden;
    }
    body {
      margin: 0;
      height: 100%;
      overflow: hidden;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      height: 100vh;
      overflow: hidden;
    }
    .preview {
      display: grid;
      place-items: center;
      min-height: 0;
      height: 100vh;
      overflow: hidden;
      background: #050607;
      padding: 16px;
    }
    .preview-stage {
      position: relative;
      display: grid;
      place-items: center;
      width: min(100%, 1280px);
      max-height: calc(100vh - 32px);
    }
    .preview img,
    .preview canvas {
      grid-area: 1 / 1;
      display: block;
      max-width: 100%;
      max-height: calc(100vh - 32px);
      object-fit: contain;
    }
    .preview img {
      background: #000;
      border: 1px solid var(--line);
    }
    .preview canvas {
      pointer-events: none;
    }
    aside {
      border-left: 1px solid var(--line);
      background: var(--panel);
      min-height: 0;
      height: 100vh;
      padding: 16px;
      overflow-y: auto;
      overscroll-behavior: contain;
    }
    h1 {
      margin: 0 0 16px;
      font-size: 20px;
      font-weight: 650;
    }
    section {
      border-top: 1px solid var(--line);
      padding: 14px 0;
    }
    section:first-of-type { border-top: 0; padding-top: 0; }
    .grid {
      display: grid;
      grid-template-columns: 120px minmax(0, 1fr);
      gap: 8px 12px;
    }
    .key { color: var(--muted); }
    .value {
      overflow-wrap: anywhere;
      min-width: 0;
    }
    .controls {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 15px;
      font-weight: 650;
    }
    button, input, select {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #252b31;
      color: var(--text);
      font: inherit;
    }
    button {
      cursor: pointer;
      font-weight: 600;
    }
    button:hover { border-color: var(--accent); }
    button.danger:hover { border-color: var(--danger); }
    input {
      width: 100%;
      padding: 0 10px;
    }
    select {
      width: 100%;
      padding: 0 10px;
    }
    label {
      display: grid;
      gap: 6px;
      color: var(--muted);
      margin-bottom: 10px;
    }
    .checkbox {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .checkbox input {
      width: auto;
      min-height: 0;
    }
    .compact-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0 8px;
    }
    .message {
      min-height: 22px;
      color: var(--accent);
      overflow-wrap: anywhere;
    }
    @media (max-width: 900px) {
      html, body { overflow: auto; }
      main {
        grid-template-columns: 1fr;
        height: auto;
        min-height: 100vh;
        overflow: visible;
      }
      .preview {
        height: 55vh;
        min-height: 320px;
      }
      aside {
        height: auto;
        max-height: none;
        border-left: 0;
        border-top: 1px solid var(--line);
        overflow: visible;
      }
    }
  </style>
</head>
<body>
  <main>
    <div class="preview">
      <div class="preview-stage">
        <img id="preview" alt="Live preview">
        <canvas id="overlay"></canvas>
      </div>
    </div>
    <aside>
      <h1>Film Scanner</h1>
      <section class="grid" id="status"></section>
      <section>
        <h2>Capture</h2>
        <label>Output directory
          <input id="outputDirectory" type="text">
        </label>
        <label>Naming pattern
          <input id="namingPattern" type="text">
        </label>
        <label>Image format
          <select id="imageFormat">
            <option value="png">png</option>
            <option value="tiff">tiff</option>
            <option value="jpg">jpg</option>
            <option value="jpeg">jpeg</option>
          </select>
        </label>
        <label>Max frames
          <input id="maxFrames" type="number" min="0" step="1" value="0">
        </label>
        <div class="controls">
          <button data-action="start">Start</button>
          <button data-action="capture">Capture Frame</button>
          <button data-action="pause">Pause</button>
          <button data-action="resume">Resume</button>
          <button class="danger" data-action="stop">Stop</button>
          <button data-action="apply-config">Apply</button>
        </div>
      </section>
      <section>
        <h2>Motor</h2>
        <label>Steps per frame
          <input id="stepsPerFrame" type="number" min="1" step="1">
        </label>
        <label>Fine step
          <input id="fineStep" type="number" min="1" step="1">
        </label>
        <label>Speed steps / second
          <input id="speedSteps" type="number" min="1" step="1">
        </label>
        <label>Settle ms
          <input id="settleMs" type="number" min="0" step="1">
        </label>
        <label>Pixels / motor step
          <input id="pixelsPerMotorStep" type="number" min="0.001" step="0.001">
        </label>
        <label>Coarse search steps
          <input id="coarseSearchSteps" type="number" min="1" step="1">
        </label>
        <label class="checkbox">
          <input id="invertDirection" type="checkbox">
          Invert direction
        </label>
      </section>
      <section>
        <h2>Overlay</h2>
        <label class="checkbox">
          <input id="showOverlay" type="checkbox" checked>
          Show overlay
        </label>
        <div class="compact-grid">
          <label>Frame X
            <input id="frameGuideX" type="number" min="0" step="1">
          </label>
          <label>Frame Y
            <input id="frameGuideY" type="number" min="0" step="1">
          </label>
          <label>Frame W
            <input id="frameGuideWidth" type="number" min="1" step="1">
          </label>
          <label>Frame H
            <input id="frameGuideHeight" type="number" min="1" step="1">
          </label>
          <label>Perf X
            <input id="perfRoiX" type="number" min="0" step="1">
          </label>
          <label>Perf Y
            <input id="perfRoiY" type="number" min="0" step="1">
          </label>
          <label>Perf W
            <input id="perfRoiWidth" type="number" min="1" step="1">
          </label>
          <label>Perf H
            <input id="perfRoiHeight" type="number" min="1" step="1">
          </label>
          <label>Perf target Y
            <input id="perfTargetY" type="number" min="0" step="1">
          </label>
        </div>
      </section>
      <section>
        <div class="controls">
          <button data-jog="forward">Forward</button>
          <button data-jog="reverse">Reverse</button>
          <button data-jog="fine-forward">Fine +</button>
          <button data-jog="fine-reverse">Fine -</button>
        </div>
      </section>
      <section class="message" id="message"></section>
    </aside>
  </main>
  <script>
    const statusEl = document.getElementById("status");
    const messageEl = document.getElementById("message");
    const previewEl = document.getElementById("preview");
    const overlayEl = document.getElementById("overlay");
    let overlayConfig = null;
    const fields = [
      ["state", "State"],
      ["frame_number", "Frame"],
      ["motor_status", "Motor"],
      ["camera_status", "Camera"],
      ["alignment_status", "Alignment"],
      ["current_file", "File"],
      ["message", "Message"]
    ];

    function renderStatus(data) {
      statusEl.innerHTML = fields.map(([key, label]) => `
        <div class="key">${label}</div>
        <div class="value">${data[key] || "-"}</div>
      `).join("");
    }

    async function refreshStatus() {
      try {
        const response = await fetch("/api/status", { cache: "no-store" });
        const data = await response.json();
        renderStatus(data);
        if (!document.activeElement || !["INPUT", "SELECT"].includes(document.activeElement.tagName)) {
          document.getElementById("outputDirectory").value = data.config.scan.output_directory;
          document.getElementById("namingPattern").value = data.config.scan.naming_pattern;
          document.getElementById("imageFormat").value = data.config.camera.format;
          document.getElementById("maxFrames").value = data.config.scan.max_frames;
          document.getElementById("stepsPerFrame").value = data.config.motor.steps_per_frame;
          document.getElementById("fineStep").value = data.config.motor.fine_step;
          document.getElementById("speedSteps").value = data.config.motor.speed_steps_per_second;
          document.getElementById("settleMs").value = data.config.motor.settle_ms;
          document.getElementById("invertDirection").checked = data.config.motor.invert_direction;
          document.getElementById("pixelsPerMotorStep").value = data.config.alignment.pixels_per_motor_step;
          document.getElementById("coarseSearchSteps").value = data.config.alignment.coarse_search_steps;
          document.getElementById("frameGuideX").value = data.config.alignment.frame_guide_x;
          document.getElementById("frameGuideY").value = data.config.alignment.frame_guide_y;
          document.getElementById("frameGuideWidth").value = data.config.alignment.frame_guide_width;
          document.getElementById("frameGuideHeight").value = data.config.alignment.frame_guide_height;
          document.getElementById("perfRoiX").value = data.config.alignment.perf_roi_x;
          document.getElementById("perfRoiY").value = data.config.alignment.perf_roi_y;
          document.getElementById("perfRoiWidth").value = data.config.alignment.perf_roi_width;
          document.getElementById("perfRoiHeight").value = data.config.alignment.perf_roi_height;
          document.getElementById("perfTargetY").value = data.config.alignment.perf_target_y;
        }
        overlayConfig = data.config;
        drawOverlay();
      } catch (error) {
        messageEl.textContent = error;
      }
    }

    async function post(path, body = {}) {
      const response = await fetch(path, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body)
      });
      const data = await response.json();
      messageEl.textContent = data.message || data.error || "";
      refreshStatus();
    }

    document.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.action;
        const config = scannerConfig();
        if (action === "apply-config") {
          post("/api/config", config);
        } else if (action === "start") {
          post("/api/start", config);
        } else if (action === "capture") {
          post("/api/capture", config);
        } else {
          post(`/api/${action}`, {});
        }
      });
    });

    function scannerConfig() {
      return {
        scan: {
          output_directory: document.getElementById("outputDirectory").value,
          naming_pattern: document.getElementById("namingPattern").value,
          max_frames: Number(document.getElementById("maxFrames").value || 0)
        },
        camera: {
          format: document.getElementById("imageFormat").value
        },
        motor: {
          steps_per_frame: Number(document.getElementById("stepsPerFrame").value || 1),
          fine_step: Number(document.getElementById("fineStep").value || 1),
          speed_steps_per_second: Number(document.getElementById("speedSteps").value || 1),
          settle_ms: Number(document.getElementById("settleMs").value || 0),
          invert_direction: document.getElementById("invertDirection").checked
        },
        alignment: {
          pixels_per_motor_step: Number(document.getElementById("pixelsPerMotorStep").value || 0.001),
          coarse_search_steps: Number(document.getElementById("coarseSearchSteps").value || 1),
          frame_guide_x: Number(document.getElementById("frameGuideX").value || 0),
          frame_guide_y: Number(document.getElementById("frameGuideY").value || 0),
          frame_guide_width: Number(document.getElementById("frameGuideWidth").value || 1),
          frame_guide_height: Number(document.getElementById("frameGuideHeight").value || 1),
          perf_roi_x: Number(document.getElementById("perfRoiX").value || 0),
          perf_roi_y: Number(document.getElementById("perfRoiY").value || 0),
          perf_roi_width: Number(document.getElementById("perfRoiWidth").value || 1),
          perf_roi_height: Number(document.getElementById("perfRoiHeight").value || 1),
          perf_target_y: Number(document.getElementById("perfTargetY").value || 0)
        }
      };
    }

    function drawOverlay() {
      const ctx = overlayEl.getContext("2d");
      const rect = previewEl.getBoundingClientRect();
      overlayEl.width = Math.max(Math.round(rect.width), 1);
      overlayEl.height = Math.max(Math.round(rect.height), 1);
      overlayEl.style.width = `${rect.width}px`;
      overlayEl.style.height = `${rect.height}px`;
      ctx.clearRect(0, 0, overlayEl.width, overlayEl.height);
      if (!overlayConfig || !document.getElementById("showOverlay").checked || !previewEl.naturalWidth) {
        return;
      }

      const scaleX = overlayEl.width / previewEl.naturalWidth;
      const scaleY = overlayEl.height / previewEl.naturalHeight;
      const a = overlayConfig.alignment;
      const line = (x1, y1, x2, y2, color) => {
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      };
      const rectLine = (x, y, w, h, color) => {
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY);
      };

      line(overlayEl.width / 2, 0, overlayEl.width / 2, overlayEl.height, "rgba(105, 183, 255, 0.75)");
      line(0, overlayEl.height / 2, overlayEl.width, overlayEl.height / 2, "rgba(105, 183, 255, 0.75)");
      rectLine(a.frame_guide_x, a.frame_guide_y, a.frame_guide_width, a.frame_guide_height, "rgba(0, 255, 150, 0.9)");
      rectLine(a.perf_roi_x, a.perf_roi_y, a.perf_roi_width, a.perf_roi_height, "rgba(255, 215, 0, 0.9)");
      line(
        a.perf_roi_x * scaleX,
        a.perf_target_y * scaleY,
        (a.perf_roi_x + a.perf_roi_width) * scaleX,
        a.perf_target_y * scaleY,
        "rgba(255, 80, 80, 0.95)"
      );
    }

    document.querySelectorAll("[data-jog]").forEach((button) => {
      button.addEventListener("click", () => {
        const fine = button.dataset.jog.startsWith("fine-");
        const direction = button.dataset.jog.endsWith("reverse") ? "reverse" : "forward";
        const config = scannerConfig();
        config.direction = direction;
        config.fine = fine;
        post("/api/jog", config);
      });
    });

    function refreshPreview() {
      previewEl.src = `/preview.jpg?ts=${Date.now()}`;
    }

    previewEl.addEventListener("load", () => {
      drawOverlay();
      setTimeout(refreshPreview, 750);
    });
    previewEl.addEventListener("error", () => setTimeout(refreshPreview, 1000));
    document.getElementById("showOverlay").addEventListener("change", drawOverlay);
    window.addEventListener("resize", drawOverlay);
    refreshPreview();
    refreshStatus();
    setInterval(refreshStatus, 1000);
  </script>
</body>
</html>
"""


class FilmScannerWebHandler(BaseHTTPRequestHandler):
    server: "FilmScannerWebServer"

    def log_message(self, format: str, *args) -> None:
        LOG.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_bytes(HTML.encode("utf-8"), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/status":
            self._send_json(_status_payload(self.server.controller))
            return
        if parsed.path == "/preview.jpg":
            self._send_preview()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/start":
                body = self._read_json()
                self._apply_config(body)
                max_frames = int(body.get("scan", {}).get("max_frames") or body.get("max_frames") or 0) or None
                self.server.with_preview_paused(lambda: self.server.controller.start(max_frames=max_frames))
                self._send_json({"message": "Scan started"})
                return
            if parsed.path == "/api/pause":
                self.server.controller.pause()
                self._send_json({"message": "Scan paused"})
                return
            if parsed.path == "/api/resume":
                self.server.controller.resume()
                self._send_json({"message": "Scan resumed"})
                return
            if parsed.path == "/api/stop":
                self.server.controller.stop()
                self._send_json({"message": "Scan stop requested"})
                return
            if parsed.path == "/api/capture":
                body = self._read_json()
                self._apply_config(body)
                path = self.server.with_preview_paused(self.server.controller.capture_single)
                self._send_json({"message": f"Captured {path}"})
                return
            if parsed.path == "/api/config":
                self._apply_config(self._read_json())
                self._send_json({"message": "Capture settings applied"})
                return
            if parsed.path == "/api/jog":
                body = self._read_json()
                self._apply_config(body)
                direction = Direction.REVERSE if body.get("direction") == "reverse" else Direction.FORWARD
                self.server.with_preview_paused(
                    lambda: self.server.controller.manual_jog(direction, fine=bool(body.get("fine", True)))
                )
                self._send_json({"message": "Manual move complete"})
                return
        except Exception as exc:
            LOG.exception("Web action failed")
            self._send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def _apply_config(self, body: dict) -> None:
        config = self.server.controller.config
        scan = body.get("scan", {})
        camera = body.get("camera", {})
        motor = body.get("motor", {})
        alignment = body.get("alignment", {})
        if "output_directory" in scan:
            config.scan.output_directory = str(scan["output_directory"])
        if "naming_pattern" in scan:
            config.scan.naming_pattern = str(scan["naming_pattern"])
        if "max_frames" in scan:
            config.scan.max_frames = int(scan["max_frames"] or 0)
        if "format" in camera:
            image_format = str(camera["format"]).lower()
            if image_format not in {"png", "tiff", "jpg", "jpeg"}:
                raise ValueError(f"Unsupported image format: {image_format}")
            config.camera.format = image_format
        if "steps_per_frame" in motor:
            config.motor.steps_per_frame = max(int(motor["steps_per_frame"]), 1)
        if "fine_step" in motor:
            config.motor.fine_step = max(int(motor["fine_step"]), 1)
        if "speed_steps_per_second" in motor:
            config.motor.speed_steps_per_second = max(float(motor["speed_steps_per_second"]), 1.0)
        if "settle_ms" in motor:
            config.motor.settle_ms = max(int(motor["settle_ms"]), 0)
        if "invert_direction" in motor:
            config.motor.invert_direction = bool(motor["invert_direction"])
        if "pixels_per_motor_step" in alignment:
            config.alignment.pixels_per_motor_step = max(float(alignment["pixels_per_motor_step"]), 0.001)
        if "coarse_search_steps" in alignment:
            config.alignment.coarse_search_steps = max(int(alignment["coarse_search_steps"]), 1)
        for key in (
            "frame_guide_x",
            "frame_guide_y",
            "perf_roi_x",
            "perf_roi_y",
            "perf_target_y",
        ):
            if key in alignment:
                setattr(config.alignment, key, max(int(alignment[key]), 0))
        for key in ("frame_guide_width", "frame_guide_height", "perf_roi_width", "perf_roi_height"):
            if key in alignment:
                setattr(config.alignment, key, max(int(alignment[key]), 1))

    def _read_json(self) -> dict:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {key: values[-1] for key, values in parse_qs(raw).items()}

    def _send_preview(self) -> None:
        jpeg, error = self.server.latest_preview()
        if jpeg is None:
            self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, error or "Preview is not ready")
            return
        self._send_bytes(jpeg, "image/jpeg", cache=False)

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._send_bytes(json.dumps(payload).encode("utf-8"), "application/json", status=status, cache=False)

    def _send_bytes(
        self,
        payload: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
        cache: bool = True,
    ) -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(payload)))
        if not cache:
            self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


class FilmScannerWebServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], config: AppConfig, simulate: bool = False) -> None:
        super().__init__(address, FilmScannerWebHandler)
        self.controller = ScannerController(config, simulate=simulate)
        self._preview_lock = threading.Lock()
        self._preview_condition = threading.Condition()
        self._preview_jpeg: bytes | None = None
        self._preview_error: str | None = "Preview is starting"
        self._preview_stop = threading.Event()
        self._preview_thread: threading.Thread | None = None
        self._preview_paused = False
        self._preview_active = False

    def start_preview(self) -> None:
        if self._preview_thread is not None and self._preview_thread.is_alive():
            return
        self._preview_stop.clear()
        self._preview_thread = threading.Thread(target=self._preview_loop, name="film-web-preview", daemon=True)
        self._preview_thread.start()

    def stop_preview(self) -> None:
        self._preview_stop.set()
        with self._preview_condition:
            self._preview_condition.notify_all()
        if self._preview_thread is not None:
            self._preview_thread.join(timeout=2)

    def latest_preview(self) -> tuple[bytes | None, str | None]:
        with self._preview_lock:
            return self._preview_jpeg, self._preview_error

    def with_preview_paused(self, callback):
        with self._preview_condition:
            self._preview_paused = True
            while self._preview_active and not self._preview_stop.is_set():
                self._preview_condition.wait(timeout=0.1)
        try:
            return callback()
        finally:
            with self._preview_condition:
                self._preview_paused = False
                self._preview_condition.notify_all()

    def _preview_loop(self) -> None:
        while not self._preview_stop.is_set():
            with self._preview_condition:
                while self._should_pause_preview() and not self._preview_stop.is_set():
                    self._preview_condition.wait(timeout=0.25)
                if self._preview_stop.is_set():
                    break
                self._preview_active = True
            try:
                jpeg = _preview_jpeg(self.controller)
            except Exception as exc:  # pragma: no cover - hardware dependent
                LOG.exception("Preview refresh failed")
                with self._preview_lock:
                    self._preview_error = str(exc)
            else:
                with self._preview_lock:
                    self._preview_jpeg = jpeg
                    self._preview_error = None
            finally:
                with self._preview_condition:
                    self._preview_active = False
                    self._preview_condition.notify_all()
            self._preview_stop.wait(0.5)

    def _should_pause_preview(self) -> bool:
        if self._preview_paused:
            return True
        return self.controller.snapshot().state in {ScanState.SCANNING, ScanState.STOPPING}


def _status_payload(controller: ScannerController) -> dict:
    status = controller.snapshot()
    return {
        "state": status.state.value,
        "frame_number": status.frame_number,
        "current_file": status.current_file,
        "motor_status": status.motor_status,
        "camera_status": status.camera_status,
        "alignment_status": status.alignment_status,
        "message": status.message,
        "errors": status.errors,
        "config": {
            "scan": {
                "output_directory": controller.config.scan.output_directory,
                "naming_pattern": controller.config.scan.naming_pattern,
                "max_frames": controller.config.scan.max_frames,
            },
            "camera": {
                "format": controller.config.camera.format,
            },
            "motor": {
                "driver": controller.config.motor.driver,
                "steps_per_frame": controller.config.motor.steps_per_frame,
                "fine_step": controller.config.motor.fine_step,
                "speed_steps_per_second": controller.config.motor.speed_steps_per_second,
                "settle_ms": controller.config.motor.settle_ms,
                "invert_direction": controller.config.motor.invert_direction,
            },
            "alignment": {
                "pixels_per_motor_step": controller.config.alignment.pixels_per_motor_step,
                "coarse_search_steps": controller.config.alignment.coarse_search_steps,
                "frame_guide_x": controller.config.alignment.frame_guide_x,
                "frame_guide_y": controller.config.alignment.frame_guide_y,
                "frame_guide_width": controller.config.alignment.frame_guide_width,
                "frame_guide_height": controller.config.alignment.frame_guide_height,
                "perf_roi_x": controller.config.alignment.perf_roi_x,
                "perf_roi_y": controller.config.alignment.perf_roi_y,
                "perf_roi_width": controller.config.alignment.perf_roi_width,
                "perf_roi_height": controller.config.alignment.perf_roi_height,
                "perf_target_y": controller.config.alignment.perf_target_y,
            },
        },
    }


def _preview_jpeg(controller: ScannerController) -> bytes:
    from PIL import Image  # type: ignore

    preview = controller.capture_preview()
    if hasattr(preview, "shape"):
        if len(preview.shape) == 3 and preview.shape[2] == 4:
            image = Image.fromarray(preview[:, :, 2::-1], "RGB")
        else:
            image = Image.fromarray(preview)
    else:
        image = Image.new("RGB", (640, 480), (35, 35, 35))

    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80, optimize=True)
    return buffer.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the 8 mm film scanner web UI")
    parser.add_argument("--config", default=None, help="Path to TOML configuration file")
    parser.add_argument("--simulate", action="store_true", help="Run without GPIO/camera hardware")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address")
    parser.add_argument("--port", type=int, default=8080, help="Bind port")
    args = parser.parse_args()

    configure_logging()
    server = FilmScannerWebServer((args.host, args.port), load_config(args.config), simulate=args.simulate)
    try:
        server.controller.initialize()
        server.start_preview()
        host = "localhost" if args.host in {"", "0.0.0.0"} else args.host
        LOG.info("Film scanner web UI running at http://%s:%s", host, args.port)
        print(f"Film scanner web UI running at http://{host}:{args.port}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop_preview()
        server.controller.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
