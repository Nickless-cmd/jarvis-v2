"""Følelseslaget skal overleve en genstart — og ikke afgøre uafgjort tilfældigt.

Målt 25/9-2026. Modulet var ikke ubygget: leksikonet, scoringen og koblingen
til humør-oscillatoren var der, og `resonate` HAR en kalder —
`chat_sessions.append_chat_message` på hver brugerbesked. Det var **uden bord**:
`_history` var en `deque` i modulet, som døde ved genstart og var usynlig for
den proces der bygger fladen. Samme fejlklasse som `_PENDING_APPROVALS`.
"""
from __future__ import annotations

import core.services.text_resonance as R


def _lager(monkeypatch, tmp_path):
    monkeypatch.setattr(R, "_storage_path", lambda: tmp_path / "text_resonance.json")
    monkeypatch.setattr("core.services.mood_oscillator.apply_bump",
                        lambda *a, **k: None)


def test_resonansen_overlever_en_genstart(monkeypatch, tmp_path):
    """KERNEN. En `deque` i modulet døde med processen."""
    _lager(monkeypatch, tmp_path)
    R.reset_text_resonance()
    R.resonate("tak, det var virkelig smukt arbejde", source="test")

    import importlib
    R2 = importlib.reload(R)
    monkeypatch.setattr(R2, "_storage_path", lambda: tmp_path / "text_resonance.json")
    assert R2.build_text_resonance_surface()["total_signals"] == 1


def test_varm_og_kold_tekst_maerkes_forskelligt(monkeypatch, tmp_path):
    """Leksikonet var rigtigt hele tiden — det skal ikke gå tabt i flytningen."""
    _lager(monkeypatch, tmp_path)
    R.reset_text_resonance()
    varm = R.resonate("tak, det var dejligt og smukt")
    kold = R.resonate("det er forkert igen, jeg er frustreret og træt")
    assert varm["emotional_tone"] == "warm" and varm["warmth_level"] > 0
    assert kold["emotional_tone"] == "cold" and kold["cold_level"] > 0


def test_uafgjort_er_NEUTRAL_ikke_et_vilkaarligt_valg(monkeypatch, tmp_path):
    """Før stod der `max(set(tones), key=tones.count)`. Med lige mange warm og
    cold afgøres det af mængdens iterationsrækkefølge, som afhænger af
    hash-seedet — altså forskelligt fra proces til proces. Målt: én varm og én
    kold gav «Læser warm» med warmth=0.4 og cold=0.4."""
    _lager(monkeypatch, tmp_path)
    R.reset_text_resonance()
    R.resonate("tak, det var dejligt og smukt")
    R.resonate("det er forkert igen, jeg er frustreret og træt")
    assert R.build_text_resonance_surface()["dominant_tone"] == "neutral"


def test_en_klar_overvaegt_vinder(monkeypatch, tmp_path):
    _lager(monkeypatch, tmp_path)
    R.reset_text_resonance()
    for _ in range(3):
        R.resonate("tak, det var dejligt og smukt")
    R.resonate("det er forkert igen, jeg er frustreret og træt")
    assert R.build_text_resonance_surface()["dominant_tone"] == "warm"


def test_historikken_er_afgraenset(monkeypatch, tmp_path):
    """200, som `deque(maxlen=200)` var før."""
    _lager(monkeypatch, tmp_path)
    R.reset_text_resonance()
    for i in range(R._HISTORY_MAX + 15):
        R.resonate(f"besked nummer {i} med noget tekst i")
    assert R.build_text_resonance_surface()["total_signals"] == R._HISTORY_MAX


def test_nyeste_foerst(monkeypatch, tmp_path):
    """`deque.appendleft` gav nyeste først; rækkefølgen skal holde."""
    _lager(monkeypatch, tmp_path)
    R.reset_text_resonance()
    R.resonate("den første besked her", source="a")
    R.resonate("den anden besked her", source="b")
    assert R.recent_resonances(limit=2)[0]["source"] == "b"


def test_tom_tekst_gemmes_ikke(monkeypatch, tmp_path):
    _lager(monkeypatch, tmp_path)
    R.reset_text_resonance()
    assert R.resonate("")["emotional_tone"] == "neutral"
    assert R.build_text_resonance_surface()["total_signals"] == 0


def test_et_lager_der_ikke_kan_skrives_vaelter_ikke_chatten(monkeypatch, tmp_path):
    """Kaldet ligger i `append_chat_message`. En resonans må aldrig kunne
    forhindre at en besked bliver gemt."""
    _lager(monkeypatch, tmp_path)
    monkeypatch.setattr(R, "_save",
                        lambda h: (_ for _ in ()).throw(RuntimeError("disken er fuld")))
    try:
        R.resonate("tak for hjælpen")
    except Exception as exc:  # pragma: no cover
        raise AssertionError(f"resonansen kastede op i chatten: {exc}") from exc
