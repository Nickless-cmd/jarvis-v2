"""Observationen af et faerdigt vaerktoejskald.

Udskilt fra `simple_tools.py` (2.141 linjer) efter Boy Scout-reglen, foer K2
lagde et skema-tjek ind i `execute_tool`.

Den ene egenskab der betyder noget: den maa aldrig kunne aendre eller vaelte
udfaldet. Alle tre observationer sidder paa veje der kan fejle — Centralen,
en DB-taeller, en klassificerings-skygge i en traad.
"""
from __future__ import annotations

import pytest

from core.tools.tool_call_observation import observe_tool_call


def test_den_kaster_ikke_paa_et_normalt_kald(isolated_runtime):
    observe_tool_call("write_file", {"path": "/a"}, {"status": "ok"})


def test_den_kaster_ikke_paa_et_fejlet_kald(isolated_runtime):
    observe_tool_call("write_file", {"path": "/a"},
                      {"status": "error", "error": "noget gik galt"})


@pytest.mark.parametrize("resultat", [None, "en streng", 42, [], {"uden": "status"}])
def test_den_kaster_ikke_paa_et_underligt_resultat(isolated_runtime, resultat):
    """Tidlige returns i dispatchen giver ikke altid en pæn dict."""
    observe_tool_call("noget", {}, resultat)


def test_en_kollapset_central_stopper_ikke_kaldet(isolated_runtime, monkeypatch):
    import core.services.central_core as CC
    monkeypatch.setattr(CC, "central",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    observe_tool_call("write_file", {"path": "/a"}, {"status": "ok"})


def test_den_returnerer_ingenting(isolated_runtime):
    """Den observerer. Den svarer ikke — kalderen har allerede sit resultat."""
    assert observe_tool_call("write_file", {}, {"status": "ok"}) is None


def test_execute_tool_kalder_den(isolated_runtime, monkeypatch):
    """Boy Scout-udskilningen maa ikke have tabt koblingen: hvis ingen kalder
    den, er tre observationer stille forsvundet."""
    import core.tools.simple_tools as ST
    set_af = []
    monkeypatch.setattr(ST, "_execute_tool_impl", lambda n, a: {"status": "ok"})
    monkeypatch.setattr("core.tools.tool_call_observation.observe_tool_call",
                        lambda n, a, r: set_af.append((n, r)))
    ST.execute_tool("write_file", {"path": "/a", "content": "x"})
    assert set_af == [("write_file", {"status": "ok"})]
