"""Efter en hentning må værktøjsarrayet ikke ændre sig — og det skal kunne slås fra.

Målt 30/9-2026: én ny definition i arrayet koster 8.704 tokens mod DeepSeeks
API, og +419 tegn kostede 62.672 miss i produktion (hit 97 % → 28,3 %), fordi
arrayet ligger før hele samtalen i præfikset. Skemaerne står allerede i
hentningens resultat — altså i beskederne, hvor de koster ~0.

Risikoen er reel: bruger modellen ikke `call_loaded_tool`, kan et hentet
værktøj ikke kaldes. Derfor er killswitchen live, og derfor måler disse tests
den.
"""
from __future__ import annotations

import types

from core.services import hentede_vaerktoejer as hv

_ALLE = [{"function": {"name": n}} for n in ("a", "b", "c")]


def _flag(monkeypatch, frossen: bool):
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: types.SimpleNamespace(visible_tools_frozen=frossen))


def test_navnene_laeses_KUN_fra_load_more_tools():
    r = [
        {"tool_name": "read_file", "result": {"added": ["x"]}},
        {"tool_name": "load_more_tools", "result": {"added": ["a", "b"]}},
        {"tool_name": "load_more_tools", "result": {"added": ["a"]}},
    ]
    assert hv.hentede_navne(r) == ["a", "b"], hv.hentede_navne(r)
    assert hv.hentede_navne(None) == []


def test_FROSSET_lader_arrayet_staa_helt_stille(monkeypatch):
    _flag(monkeypatch, True)
    defs = [{"function": {"name": "a"}}]
    assert hv.flet_ind(defs, ["b", "c"], _ALLE) == defs
    assert hv.udvid_laasen("s1", ["b"]) is False


def test_IKKE_frosset_er_den_gamle_adfaerd(monkeypatch):
    """Kontrollen. Uden den kunne testen ovenfor bestaa paa en `flet_ind` der
    ALDRIG fletter — og saa maaler killswitchen ingenting."""
    _flag(monkeypatch, False)
    ud = hv.flet_ind([{"function": {"name": "a"}}], ["b", "c"], _ALLE)
    assert [(d.get("function") or d)["name"] for d in ud] == ["a", "b", "c"]


def test_et_vaerktoej_der_allerede_er_der_tilfoejes_ikke_igen(monkeypatch):
    _flag(monkeypatch, False)
    ud = hv.flet_ind([{"function": {"name": "a"}}], ["a"], _ALLE)
    assert len(ud) == 1


def test_et_ULAESELIGT_flag_aendrer_ingenting(monkeypatch):
    """Fail-safe: en killswitch der ikke kan laeses maa ikke aendre adfaerd af
    sig selv. Den falder tilbage til den GAMLE adfaerd, ikke den nye."""
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    assert hv.frosset() is False
    ud = hv.flet_ind([{"function": {"name": "a"}}], ["b"], _ALLE)
    assert len(ud) == 2, "et ulaeseligt flag froes arrayet — forkert retning"


def test_laasen_udvides_ikke_uden_navne_eller_session(monkeypatch):
    _flag(monkeypatch, False)
    assert hv.udvid_laasen("s1", []) is False
    assert hv.udvid_laasen("", ["a"]) is False
