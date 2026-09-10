"""Efterproev det et barn PAASTAAR — Fase 6.

Raadet foreslog det selv: `architecture-fixer` skrev at subagent-runtime'en kan
kraeve kilde-citater, og at det er «loesbart ved seamen».

Jarvis efterproevede forslaget og tilfoejede tre ting der former designet:

  1. GENERALISERING ER IKKE AT FLYTTE ET KALD. Guarden sidder i explore'ens
     egen loekke med model-rotation ved fejl. Det virker fordi explore kan
     proeve igen. For et barn der ALLEREDE har koert, betyder «rotér modellen»
     at koere barnet om — en anden og dyrere semantik.
     → Her arves den semantik IKKE. Ingen genkoersel, intet retry.

  2. FAIL-OPEN ER LOAD-BEARING. Raadsmedlemmer laver mest prosa der ikke kan
     slaas op; et barn der citerer fil:linje kan. En uniform afvisning ville
     vaere naesten doed paa raad og haard paa explore.
     → Prosa faar `kontrolleret: 0, holder: True`. Ingen dom uden grundlag.

  3. GOER DET SYNLIGT, AFVIS IKKE — samme princip som `_trim`-retten.
     → Dommen gemmes paa runnet og siges hoejt. Rapporten kommer igennem.
"""
from __future__ import annotations

import logging

from core.services.report_claim_guard import tjek_rapport


# ── 2: ingen dom uden grundlag ───────────────────────────────────────────

def test_ren_PROSA_faar_ingen_dom():
    """Raadspositioner er vurderinger. De kan ikke slaas op, og de skal ikke
    straffes for det."""
    d = tjek_rapport("Jeg mener risikoen er overdrevet, og her er hvorfor.")
    assert d["kontrolleret"] == 0 and d["holder"] is True and d["fejl"] == []


def test_tom_rapport_faar_ingen_dom():
    for t in ("", "   ", None):
        assert tjek_rapport(t) == {"kontrolleret": 0, "holder": True, "fejl": []}


# ── det farlige: en paastand der KAN efterproeves og er falsk ────────────

def test_en_AEGTE_sti_holder():
    d = tjek_rapport("Se core/services/report_claim_guard.py:1 for kontrakten.")
    assert d["kontrolleret"] >= 1 and d["holder"] is True


def test_en_OPDIGTET_sti_falder(caplog):
    with caplog.at_level(logging.WARNING):
        d = tjek_rapport("Se core/services/findes_slet_ikke.py:42",
                         agent_id="a1", role="researcher", run_id="r1")
    assert d["holder"] is False and d["kontrolleret"] >= 1
    assert any("findes ikke" in f for f in d["fejl"])
    assert "FALSKE referencer" in caplog.text
    assert "a1" in caplog.text and "researcher" in caplog.text


def test_en_holdbar_rapport_siger_ingenting(caplog):
    """Kun det opdigtede er en haendelse."""
    with caplog.at_level(logging.WARNING):
        tjek_rapport("Alt er fint. Se core/services/report_claim_guard.py:1")
    assert "FALSKE referencer" not in caplog.text


# ── 1: den arver IKKE explore'ens genkoersel ────────────────────────────

def test_guarden_koerer_ALDRIG_barnet_om():
    """Explore roterer model og proever igen — det kan den, fordi den ikke har
    leveret endnu. Et barn der har rapporteret, ville skulle koere HELT om."""
    import inspect

    from core.services import report_claim_guard as G
    kilde = inspect.getsource(G)
    for ord_ in ("egnede_modeller", "for runde", "retry", "spawn_agent_task"):
        assert ord_ not in kilde, f"guarden arvede explore'ens {ord_}"


# ── 3: den maa aldrig vaelte rapporten den doemmer ───────────────────────

def test_den_kaster_aldrig(monkeypatch):
    import core.services.explore_claim_check as CC
    monkeypatch.setattr(CC, "tjek_paastande",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert tjek_rapport("core/x.py:1") == {"kontrolleret": 0, "holder": True,
                                           "fejl": []}


# ── koblingen: dommen gemmes paa runnet ─────────────────────────────────

def test_dommen_gemmes_paa_runnet():
    import inspect

    from core.services import agent_runtime_spawn as S
    kilde = inspect.getsource(S)
    assert "tjek_rapport(text" in kilde
    assert '"claim_check"' in kilde, "dommen naar ikke ud i nyttelasten"


def test_barne_svaret_forkortes_SYNLIGT():
    """Samme fejl som i raadet: `text[:400]` klippede hvert barne-svar midt i
    et ord uden at sige det."""
    import inspect

    from core.services import agent_runtime_spawn as S
    kilde = inspect.getsource(S)
    assert "output_summary=_trim(text, 400)" in kilde
    assert "output_summary=text[:400]" not in kilde
