from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import argparse
import io
import json
import logging

from .config import AppConfig, load_config
from .logging_setup import configure_logging
from .motor import Direction
from .workflow import ScannerController

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
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 15px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      min-height: 100vh;
    }
    .preview {
      display: grid;
      place-items: center;
      min-height: 100vh;
      background: #050607;
      padding: 16px;
    }
    .preview img {
      display: block;
      width: min(100%, 1280px);
      max-height: calc(100vh - 32px);
      object-fit: contain;
      background: #000;
      border: 1px solid var(--line);
    }
    aside {
      border-left: 1px solid var(--line);
      background: var(--panel);
      padding: 16px;
      overflow: auto;
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
    .message {
      min-height: 22px;
      color: var(--accent);
      overflow-wrap: anywhere;
    }
    @media (max-width: 900px) {
      main { grid-template-columns: 1fr; }
      .preview { min-height: 55vh; }
      aside { border-left: 0; border-top: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <main>
    <div class="preview">
      <img id="preview" alt="Live preview">
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
          document.getElementById("pixelsPerMotorStep").value = data.config.alignment.pixels_per_motor_step;
          document.getElementById("coarseSearchSteps").value = data.config.alignment.coarse_search_steps;
        }
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
          settle_ms: Number(document.getElementById("settleMs").value || 0)
        },
        alignment: {
          pixels_per_motor_step: Number(document.getElementById("pixelsPerMotorStep").value || 0.001),
          coarse_search_steps: Number(document.getElementById("coarseSearchSteps").value || 1)
        }
      };
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

    previewEl.addEventListener("load", () => setTimeout(refreshPreview, 250));
    previewEl.addEventListener("error", () => setTimeout(refreshPreview, 1000));
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
                self.server.controller.start(max_frames=max_frames)
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
                path = self.server.controller.capture_single()
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
                self.server.controller.manual_jog(direction, fine=bool(body.get("fine", True)))
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
        if "pixels_per_motor_step" in alignment:
            config.alignment.pixels_per_motor_step = max(float(alignment["pixels_per_motor_step"]), 0.001)
        if "coarse_search_steps" in alignment:
            config.alignment.coarse_search_steps = max(int(alignment["coarse_search_steps"]), 1)

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
        try:
            jpeg = _preview_jpeg(self.server.controller)
        except Exception as exc:
            LOG.exception("Preview request failed")
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
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
            },
            "alignment": {
                "pixels_per_motor_step": controller.config.alignment.pixels_per_motor_step,
                "coarse_search_steps": controller.config.alignment.coarse_search_steps,
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
        host = "localhost" if args.host in {"", "0.0.0.0"} else args.host
        LOG.info("Film scanner web UI running at http://%s:%s", host, args.port)
        print(f"Film scanner web UI running at http://{host}:{args.port}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.controller.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
