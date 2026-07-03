import builtins

from film_scanner.camera import Camera
from film_scanner.config import CameraConfig


def test_camera_reports_missing_picamera2_install_hint(monkeypatch, caplog) -> None:
    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "picamera2":
            raise ModuleNotFoundError("No module named 'picamera2'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with caplog.at_level("WARNING"):
        camera = Camera(CameraConfig())

    assert camera.simulated is True
    assert "python3 -m pip install -e '.[pi,vision]'" in caplog.text
