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


# ── Pladsholderen maa ikke citeres som et svar (27/11-2026) ────────────────
# `recent_visible_runs` giver daemonerne `PLADSHOLDER_KRYPTERET` i stedet for
# chiffertekst, naar raekken tilhoerer et medlem. Kontrakten er at forbrugeren
# springer den over (`er_laesbar`) — ikke at den citerer den. Maalt 27/11:
# pladsholderen blev tokeniseret til emne-ord som «krypteret» og «bevises» og
# foert ind i chroniclen som om det var noget brugeren havde talt om.

def test_collect_topics_springer_pladsholderen_over() -> None:
    from core.services.visible_preview_crypto import PLADSHOLDER_KRYPTERET

    runs = [{"text_preview": PLADSHOLDER_KRYPTERET}]
    assert chronicle_engine._collect_topics(runs) == []


def test_collect_topics_laeser_klartekst_som_foer() -> None:
    runs = [{"text_preview": "vi byggede en ny scheduler til heartbeat"}]
    topics = chronicle_engine._collect_topics(runs)
    assert "scheduler" in topics


def test_extract_key_events_springer_pladsholderen_over() -> None:
    from core.services.visible_preview_crypto import PLADSHOLDER_KRYPTERET

    runs = [{"status": "completed", "text_preview": PLADSHOLDER_KRYPTERET}]
    assert chronicle_engine._extract_key_events(runs) == []


def test_extract_key_events_bevarer_klartekst() -> None:
    runs = [{"status": "completed", "text_preview": "fixet landede paa main"}]
    events = chronicle_engine._extract_key_events(runs)
    assert events == ["completed: fixet landede paa main"]
