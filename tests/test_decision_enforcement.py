"""Loop-liveness-synlighed for core/services/decision_enforcement.py (dø-skjult-fix)."""
from __future__ import annotations
import importlib
from pathlib import Path


def test_imports():
    assert importlib.import_module("core.services.decision_enforcement") is not None


def test_loop_error_reaches_central():
    src = Path("core/services/decision_enforcement.py").read_text(encoding="utf-8")
    assert "observe_operational_liveness" in src, "loop-except skal nå Centralen"


# ---------------------------------------------------------------------------
# Præmissen (26/9-2026): dommeren skal se Bjørns besked, ikke kun sin egen tekst
# ---------------------------------------------------------------------------


def test_breach_prompten_har_praemissen(monkeypatch):
    """Målt 26/9-2026: `_build_breach_prompt` fik `assistant_text` og
    rækkefølgen — aldrig Bjørns besked. Alligevel dømte den fire brud af typen
    «responded without first reproducing Bjørn's quoted message». Den dømte på
    en præmis den ikke havde, og kunne ikke skelne «du citerede ham ikke» fra
    «der var intet at citere»."""
    from core.services import decision_enforcement as DE

    monkeypatch.setattr(
        DE, "_seneste_bruger_besked", lambda limit=1: ["Skær triggeren ned"],
    )
    p = DE._build_breach_prompt(
        "Her er mit svar uden citat.",
        [{"decision_id": "dec_x", "directive": "citér hans ord"}],
    )
    assert "Skær triggeren ned" in p, "præmissen mangler — dommen gætter igen"
    assert "dec_x" in p


def test_breach_prompten_taaler_ingen_besked(monkeypatch):
    """Ingen besked fundet → dommeren skal vide det, ikke gætte."""
    from core.services import decision_enforcement as DE

    monkeypatch.setattr(DE, "_seneste_bruger_besked", lambda limit=1: [])
    p = DE._build_breach_prompt("Svar.", [])
    assert "ingen fundet" in p


def test_bruger_besked_er_selvsikker_mod_doed_db(monkeypatch):
    """Samme kontrakt som resten: fejler DB'en, er svaret tomt — ikke en exception."""
    from core.services import decision_enforcement as DE

    def _sprang(*_a, **_k):
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db.connect", _sprang)
    assert DE._seneste_bruger_besked() == []
