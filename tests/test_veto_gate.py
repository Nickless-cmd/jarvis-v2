"""Fail-open-synlighed for core/services/veto_gate.py (dø-skjult-fix)."""
from __future__ import annotations
import importlib
from pathlib import Path


def test_imports():
    assert importlib.import_module("core.services.veto_gate") is not None


def test_fail_open_is_visible():
    src = Path("core/services/veto_gate.py").read_text(encoding="utf-8")
    assert "record_central_incident" in src, "check_veto fail-open skal flagge til Centralen"


# ── record_event-vagten (fix 13/9-2026) ──────────────────────────────────────
# Baggrund: `reasoning_detectors.veto_on_reasoning` genanvendte gaten på Jarvis' EGEN
# reasoning og sendte den ind som `user_message`. Det skrev 77 rækker i veto_events
# med veto_result='blocked' og tool_name='' — hvor intet værktøj blev blokeret.
# Vagtens kontrakt: en genanvendelse uden brugermelding må ikke skrive i ledger'en,
# men den ÆGTE præ-eksekverings-vej skal skrive præcis som før.

_FIRM_SECTION = (
    "PUSHBACK\n"
    "- feeling=protectiveness intensity=0.81 action=firm_pushback\n"
    "- evidence: risk marker: 'push'\n"
)
_SOFT_SECTION = (
    "PUSHBACK\n"
    "- feeling=hesitation intensity=0.46 action=soft_pushback\n"
    "- evidence: risk marker: 'restart'\n"
)


def _hermetic(monkeypatch, section: str):
    """Isolér gaten fra token-signal, pushback-beregning og adaptiv DB-læsning."""
    from core.services import veto_gate as vg
    written: list[dict] = []
    monkeypatch.setattr(vg, "_check_token_signal_gate", lambda msg, tool: False)
    monkeypatch.setattr(vg, "_adaptive_threshold", lambda tool, feeling, intensity: 0.5)
    monkeypatch.setattr(vg, "log_veto_event", lambda **kw: (written.append(kw) or "veto-test"))
    monkeypatch.setattr("core.services.pushback.affective_pushback_section",
                        lambda msg: section)
    return vg, written


def test_record_event_false_skriver_ingen_blocked_raekke(monkeypatch):
    """Kernen i fixet: genanvendelsen må ikke skrive en 'blocked'-række."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, reason = vg.check_veto("", "jeg pusher nu", record_event=False)
    assert allowed is False and "VETO" in reason  # dømmekraften kører uændret
    assert written == [], "genanvendelse uden brugermelding må ikke skrive i veto_events"


def test_record_event_false_skriver_ingen_allowed_raekke(monkeypatch):
    vg, written = _hermetic(monkeypatch, _SOFT_SECTION)
    allowed, _ = vg.check_veto("", "jeg genstarter nu", record_event=False)
    assert allowed is True
    assert written == []


def test_record_event_true_skriver_som_foer(monkeypatch):
    """Den ÆGTE vej skal være uændret — vagten må ikke slukke ledger'en."""
    vg, written = _hermetic(monkeypatch, _FIRM_SECTION)
    allowed, _ = vg.check_veto("write_file", "jeg pusher nu", record_event=True)
    assert allowed is False
    assert len(written) == 1 and written[0]["veto_result"] == "blocked"
    assert written[0]["tool_name"] == "write_file"
