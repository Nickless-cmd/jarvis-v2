"""Read image shares a safe preview without exposing arbitrary temp files."""
from pathlib import Path

from core.tools.simple_tools_web import _exec_analyze_image


def test_analyze_image_stages_a_preview_for_server_side_temp_image(tmp_path, monkeypatch):
    from core.services import vision_backend

    image = tmp_path / "crop-nederst.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"test-image")
    monkeypatch.setattr(vision_backend, "resolve_vision_target", lambda: ("deepseek", "vision", "test"))
    monkeypatch.setattr(vision_backend, "describe", lambda **_kw: {"text": "Et udsnit"})

    result = _exec_analyze_image({"image_path": str(image)})

    assert result["analysis"] == "Et udsnit"
    preview = Path(result["preview_path"])
    assert preview.name.startswith("jarvisx-vision-")
    assert preview.read_bytes() == image.read_bytes()
    preview.unlink()
