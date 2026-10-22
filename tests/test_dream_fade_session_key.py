"""Fade-mekanikken skal kunne NÅS — `presented` skal være per-session.

Målt 22/10-2026 i den levende carry-fil:
    28 aktive drømme, ALLE `presented=True`, 0 bekræftet, carry 1–3,
    arkiv fastfrosset på 7.

`presented` var en permanent boolean uden nogen session at nulstille den ved.
Efter første præsentation blev drømmen aldrig præsentabel igen, så
`mark_dream_presented` — den ENESTE kalder af `_maybe_fade_old_dreams` — blev
aldrig kaldt igen. Fade var ikke død af en enhedsfejl; den blev aldrig nået.

Disse tests ser den nye kontrakt: én præsentation pr. SESSION, ikke pr. levetid.
"""
from __future__ import annotations

import pytest

from core.services import dream_carry_over as dco


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    """Isolér hukommelse + persistens, så testen ikke rører den levende fil."""
    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", True)
    monkeypatch.setattr(dco, "_persist_file", lambda: tmp_path / "DREAM_CARRY.json")
    monkeypatch.setattr(dco, "_save", lambda: None)
    yield


def _set_session(monkeypatch, key: str) -> None:
    monkeypatch.setattr(dco, "_current_session_key", lambda: key)


def test_samme_session_praesenterer_kun_en_gang(monkeypatch):
    """Inden for ÉN session må drømmen ikke gentages hver tur."""
    _set_session(monkeypatch, "sess-A")
    dco.adopt_dream(dream_id="d1", content="Unikt indhold A")

    foerste = dco.get_presentable_dream()
    assert foerste is not None
    dco.mark_dream_presented("d1")

    assert dco.get_presentable_dream() is None


def test_ny_session_praesenterer_igen_og_carry_vokser(monkeypatch):
    """Kernen i fikset: en NY session giver ét nyt carry-trin.

    Uden dette voksede `session_carry_count` aldrig forbi 1, og
    `_FADE_AFTER_SESSIONS` blev aldrig nået."""
    _set_session(monkeypatch, "sess-A")
    dco.adopt_dream(dream_id="d1", content="Unikt indhold B")
    dco.mark_dream_presented("d1")

    _set_session(monkeypatch, "sess-B")
    assert dco.get_presentable_dream() is not None, "ny session skal kunne se drømmen"
    dco.mark_dream_presented("d1")

    dream = next(d for d in dco._ACTIVE_DREAMS if d["dream_id"] == "d1")
    assert int(dream["session_carry_count"]) == 2


def test_fade_fyrer_naar_carry_naar_taersklen(monkeypatch):
    """Fade skal faktisk arkivere drømmen — det var det der aldrig skete."""
    _set_session(monkeypatch, "sess-0")
    dco.adopt_dream(dream_id="d-fade", content="Skal fade")

    for i in range(dco._FADE_AFTER_SESSIONS):
        _set_session(monkeypatch, f"sess-{i}")
        assert dco.get_presentable_dream() is not None, f"runde {i} skal kunne præsentere"
        dco.mark_dream_presented("d-fade")

    ids = {d["dream_id"] for d in dco._ACTIVE_DREAMS}
    assert "d-fade" not in ids, "drømmen skulle være fadet ud af de aktive"
    assert any(d["dream_id"] == "d-fade" for d in dco._DREAM_ARCHIVE)


def test_bekraeftet_droem_fader_aldrig(monkeypatch):
    """Bekræftede drømme uddybes — de må ikke arkiveres som ubesvarede."""
    _set_session(monkeypatch, "sess-0")
    dco.adopt_dream(dream_id="d-conf", content="Bekræftet")
    dco.confirm_dream("d-conf")

    for i in range(dco._FADE_AFTER_SESSIONS + 2):
        _set_session(monkeypatch, f"sess-{i}")
        dco.mark_dream_presented("d-conf")

    assert any(d["dream_id"] == "d-conf" for d in dco._ACTIVE_DREAMS)


def test_gammel_presented_uden_session_noegle_bliver_praesentabel(monkeypatch):
    """De 28 fastlåste drømme har `presented=True` men intet
    `presented_in_session`. De skal kunne præsenteres igen — ellers arver
    fikset den samme fastlåsning det skulle løse."""
    _set_session(monkeypatch, "sess-ny")
    dco._ACTIVE_DREAMS.append(
        {
            "dream_id": "gammel",
            "content": "Fra den gamle ordning",
            "confidence": 0.5,
            "status": "active",
            "presented": True,  # gammel permanent boolean
            "confirmed": False,
            "session_carry_count": 1,
        }
    )

    assert dco.get_presentable_dream() is not None


def test_default_session_id_bruges_ikke_som_noegle(monkeypatch):
    """`current_session_id()` returnerer `_default` uden for en tur. Den må
    ikke blive nøglen — så ville alle autonome kald dele én "session"."""
    monkeypatch.setattr(
        "core.services.operator_channel.current_session_id", lambda: "_default"
    )
    noegle = dco._current_session_key()
    assert noegle != "_default"
    assert noegle.startswith("day-")
