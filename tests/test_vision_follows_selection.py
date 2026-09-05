"""Syns-værktøjerne følger modelvælgeren (Bjørn, 5/9-2026).

«flash uden syn skal stadig være default, jeg skal bare kunne vælge syn i model
vælgeren … med syn bruger tools flash model med syn.»

Så: kører der en synlig tur på en model der selv kan se, låner værktøjerne
DENS øjne. Ellers arbejder de som hidtil på den konfigurerede vision-model.
"""
from __future__ import annotations

import pytest

from core.services import vision_backend as VB


@pytest.fixture
def no_config(monkeypatch):
    monkeypatch.setattr("core.runtime.secrets.read_runtime_key", lambda *_a, **_k: None)
    monkeypatch.setattr("core.services.attachment_service._vision_model",
                        lambda: "gemma4:31b-cloud")


def _active(monkeypatch, state):
    monkeypatch.setattr(
        "core.services.visible_runs._get_active_visible_run_state", lambda: state)


@pytest.mark.parametrize("model,sees", [
    ("deepseek-v4-flash-vision-exp", True),
    ("deepseek-v4-flash", False),
    ("deepseek-v4-pro", False),
    ("gemma4:31b-cloud", False),
    ("qwen2.5vl:3b", True),
    ("llava:13b", True),
    ("", False),
])
def test_which_models_can_see_for_themselves(model, sees):
    assert VB.model_can_see(model) is sees


def test_a_seeing_model_lends_its_own_eyes(no_config, monkeypatch):
    _active(monkeypatch, {"active": True, "provider": "deepseek",
                          "model": "deepseek-v4-flash-vision-exp"})
    assert VB.resolve_vision_target() == (
        "deepseek", "deepseek-v4-flash-vision-exp", "selected-model")


def test_the_blind_default_keeps_the_old_eyes(no_config, monkeypatch):
    """Flash UDEN syn er stadig standard — vaerktoejerne arbejder som hidtil."""
    _active(monkeypatch, {"active": True, "provider": "deepseek",
                          "model": "deepseek-v4-flash"})
    assert VB.resolve_vision_target() == ("ollama", "gemma4:31b-cloud", "config")


def test_no_active_turn_falls_back_to_config(no_config, monkeypatch):
    _active(monkeypatch, {})
    assert VB.resolve_vision_target()[2] == "config"


def test_a_cancelled_turn_does_not_lend_its_eyes(no_config, monkeypatch):
    _active(monkeypatch, {"active": True, "cancelled": True, "provider": "deepseek",
                          "model": "deepseek-v4-flash-vision-exp"})
    assert VB.resolve_vision_target()[2] == "config"


def test_a_broken_run_state_never_raises(no_config, monkeypatch):
    def _boom():
        raise RuntimeError("ingen kontekst")
    monkeypatch.setattr(
        "core.services.visible_runs._get_active_visible_run_state", _boom)
    assert VB.active_visible_target() == ("", "")
    assert VB.resolve_vision_target()[2] == "config"


def test_the_surface_says_where_the_eyes_come_from(no_config, monkeypatch):
    _active(monkeypatch, {"active": True, "provider": "deepseek",
                          "model": "deepseek-v4-flash-vision-exp"})
    s = VB.build_vision_backend_surface()
    assert s["source"] == "selected-model" and s["paid"] is True
    assert "selected-model" in s["summary"]


def test_reading_an_image_uses_the_selected_model(tmp_path, monkeypatch, no_config):
    """Hele kaeden: valgt syns-model -> read_attachment_content."""
    from core.services import attachment_service as AS
    path = tmp_path / "x.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    monkeypatch.setattr(AS, "_db_get", lambda _id: {
        "mime_type": "image/png", "local_path": str(path), "filename": "x.png"})
    _active(monkeypatch, {"active": True, "provider": "deepseek",
                          "model": "deepseek-v4-flash-vision-exp"})
    seen: dict = {}
    monkeypatch.setattr(VB, "describe_via_deepseek",
                        lambda b64, *, model, prompt, run_id="": seen.update(
                            model=model, prompt=prompt) or "et skilt")
    out = AS.read_attachment_content("a1", question="hvad staar der?")
    assert seen["model"] == "deepseek-v4-flash-vision-exp"
    assert "hvad staar der?" in seen["prompt"]
    assert out["content"] == "et skilt"
