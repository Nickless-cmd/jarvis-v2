"""Tests for chronicle_engine prompt-boundary — særligt Spec H anti-drift-wiring (shadow)."""
from __future__ import annotations

from core.services import chronicle_engine
from core.services import identity_drift_guard as idg_mod


def _stub_entries(monkeypatch, narrative: str) -> None:
    monkeypatch.setattr(
        chronicle_engine, "list_cognitive_chronicle_entries",
        lambda limit=5: [{"period": "juni", "narrative": narrative, "created_at": None}],
    )


def test_chronicle_context_passes_through_drift_guard(monkeypatch) -> None:
    """Chronicle-kontekst rutes gennem identity_drift_guard med source='chronicle'."""
    calls: list[str] = []

    def _spy(text, *, source):  # noqa: ANN001, ANN202
        calls.append(source)
        return text, []

    monkeypatch.setattr(idg_mod, "identity_drift_guard", _spy)
    _stub_entries(monkeypatch, "jeg voksede denne måned")
    out = chronicle_engine.get_chronicle_context_for_prompt(n=1)
    assert calls == ["chronicle"]
    assert "jeg voksede denne måned" in out


def test_chronicle_shadow_non_destructive(monkeypatch) -> None:
    """Ægte guard i shadow (default): en normal refleksion passerer uændret."""
    _stub_entries(monkeypatch, "en helt normal refleksion")
    out = chronicle_engine.get_chronicle_context_for_prompt(n=1)
    assert "en helt normal refleksion" in out


def test_chronicle_guard_error_is_safe(monkeypatch) -> None:
    """En guard-fejl må aldrig vælte chronicle-konteksten (self-safe)."""
    def _boom(text, *, source):  # noqa: ANN001, ANN202
        raise RuntimeError("guard nede")

    monkeypatch.setattr(idg_mod, "identity_drift_guard", _boom)
    _stub_entries(monkeypatch, "min historie")
    out = chronicle_engine.get_chronicle_context_for_prompt(n=1)
    assert "min historie" in out


def test_chronicle_empty_returns_empty(monkeypatch) -> None:
    monkeypatch.setattr(chronicle_engine, "list_cognitive_chronicle_entries", lambda limit=5: [])
    assert chronicle_engine.get_chronicle_context_for_prompt(n=1) == ""
