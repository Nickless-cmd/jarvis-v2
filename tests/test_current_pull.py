"""Tests for current_pull prompt-boundary — særligt Spec H anti-drift-wiring (shadow)."""
from __future__ import annotations

from core.services import current_pull
from core.services import identity_drift_guard as idg_mod


def _stub_state(monkeypatch, pull: str) -> None:
    monkeypatch.setattr(current_pull, "_enabled", lambda: True)
    monkeypatch.setattr(current_pull, "_expire_if_stale", lambda: None)
    monkeypatch.setattr(current_pull, "_load_state", lambda: {"pull": pull})


def test_pull_passes_through_drift_guard(monkeypatch) -> None:
    """Prompt-fragmentet rutes gennem identity_drift_guard med source='pull'."""
    calls: list[str] = []

    def _spy(text, *, source):  # noqa: ANN001, ANN202
        calls.append(source)
        return text, []

    monkeypatch.setattr(idg_mod, "identity_drift_guard", _spy)
    _stub_state(monkeypatch, "jeg søger klarhed")
    out = current_pull.get_current_pull_for_prompt()
    assert calls == ["pull"]
    assert "jeg søger klarhed" in out


def test_pull_shadow_non_destructive(monkeypatch) -> None:
    """Ægte guard i shadow (default): en normal pull passerer uændret."""
    _stub_state(monkeypatch, "en helt normal indre bevægelse")
    out = current_pull.get_current_pull_for_prompt()
    assert out == "[indre træk]: en helt normal indre bevægelse"


def test_pull_guard_error_is_safe(monkeypatch) -> None:
    """En guard-fejl må aldrig vælte prompt-fragmentet (self-safe)."""
    def _boom(text, *, source):  # noqa: ANN001, ANN202
        raise RuntimeError("guard nede")

    monkeypatch.setattr(idg_mod, "identity_drift_guard", _boom)
    _stub_state(monkeypatch, "tekst")
    out = current_pull.get_current_pull_for_prompt()
    assert out == "[indre træk]: tekst"


def test_pull_empty_returns_empty(monkeypatch) -> None:
    _stub_state(monkeypatch, "")
    assert current_pull.get_current_pull_for_prompt() == ""
