"""Tænke-sprog-killswitchen — modulet (30/9-2026).

Fastholder de ting der let glider:
  1. Standard = dansk, og direktivet er TOMT. Killswitchen må ikke ændre
     prompten før Bjørn tænder den — ellers er der ingen baseline at måle mod.
  2. Direktivet er HÅRDT formuleret. Den milde variant blev målt virkningsløs
     30/9 (modellen tænkte engelsk trods «tænk på dansk»), så testen kræver
     ordene der gør den til et krav og ikke et ønske.
  3. Ukendte værdier afvises i stedet for at sætte flaget i en tilstand
     prompten ikke forstår.
"""
from __future__ import annotations

import core.services.think_language as tl


def fake_kv(monkeypatch, start: dict | None = None) -> dict:
    """Erstat runtime-state med et in-memory-dict (ingen DB i testen)."""
    store: dict = dict(start or {})

    def _get(key, default=None):
        return store.get(key, default)

    def _set(key, value, **_kw):
        store[key] = value

    monkeypatch.setattr(tl, "get_runtime_state_value", _get)
    monkeypatch.setattr(tl, "set_runtime_state_value", _set)
    return store


def test_default_er_dansk_og_direktivet_er_tomt(monkeypatch):
    fake_kv(monkeypatch)
    assert tl.current() == "da"
    assert tl.is_english() is False
    assert tl.directive() == "", "killswitchen maa ikke aendre prompten naar den er slukket"


def test_engelsk_taender_direktivet(monkeypatch):
    fake_kv(monkeypatch)
    assert tl.set_language("en") == "en"
    assert tl.is_english() is True
    d = tl.directive()
    assert d, "direktivet skal findes naar engelsk er aktivt"
    assert "English" in d


def test_direktivet_er_haardt_ikke_milt(monkeypatch):
    """Den milde formulering blev maalt virkningsloes — kravene skal staa der."""
    fake_kv(monkeypatch, {"think_language": "en"})
    d = tl.directive().lower()
    assert "exclusively" in d, "skal vaere et krav, ikke et oenske"
    assert "do not" in d, "skal eksplicit afvise at taenke dansk"
    assert "danish" in d, "skal naevne dansk som det der IKKE skal taenkes i"
    # Faelden fra 30/9: modellen noterede bare at svaret skulle vaere dansk.
    assert "merely note" in d, "skal lukke 'We need answer in Danish'-faelden"


def test_ukendt_vaerdi_afvises(monkeypatch):
    fake_kv(monkeypatch)
    assert tl.set_language("fr") == "da", "ukendt sprog maa ikke saettes"
    assert tl.current() == "da"
    assert tl.set_language("") == "da"


def test_ukendt_lagret_vaerdi_falder_til_dansk(monkeypatch):
    """En forvildet vaerdi i DB'en maa ikke give en prompt vi ikke forstaar."""
    fake_kv(monkeypatch, {"think_language": "klingon"})
    assert tl.current() == "da"
    assert tl.directive() == ""


def test_db_fejl_giver_dansk_uden_at_kaste(monkeypatch):
    """Laesningen ligger i prompt-assembly — den maa aldrig tage en tur med sig."""
    def _boom(key, default=None):
        raise RuntimeError("DB nede")

    monkeypatch.setattr(tl, "get_runtime_state_value", _boom)
    assert tl.current() == "da"
    assert tl.directive() == ""
