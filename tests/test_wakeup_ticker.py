"""Vækninger fyres af en dedikeret tråd, ikke af en 60 s-poll via jobkøen.

Målt 12/11-2026: dagens vækninger fyrede 3-59 s efter planlagt tid (median 32 s).
Pollen hænger på heartbeatens ~30 s-poll og jobkøen, så en kortere kadence i
`_SCHEDULE` alene hjælper ikke. Tråden her kigger hvert 5. sekund og kalder
dispatcheren KUN når noget er forfaldent.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import self_wakeup as sw
from core.services import wakeup_ticker as wt


def _iso(delta_s: float) -> str:
    return (datetime.now(UTC) + timedelta(seconds=delta_s)).isoformat()


def _post(wid: str, status: str, fire_in_s: float = -5.0, **ekstra) -> dict:
    return {"wakeup_id": wid, "status": status, "fire_at": _iso(fire_in_s), **ekstra}


@pytest.mark.parametrize("poster, forventet", [
    ([_post("a", "pending", -5)], {"a"}),                                  # forfaldent
    ([_post("a", "pending", +300)], set()),                                # fremtidig
    ([_post("a", "fired")], {"a"}),                                        # fyret, ikke afleveret
    ([_post("a", "fired", dispatched=True)], set()),                       # afleveret
    ([_post("a", "fired", dispatch_skipped=True)], set()),                 # sprunget -> indbakken ejer den
    ([_post("a", "consumed")], set()),
    ([_post("a", "cancelled")], set()),
    ([_post("a", "pending", -5), _post("b", "consumed"), _post("c", "fired")], {"a", "c"}),
])
def test_forfaldne_vaekninger_er_praecis_dem_dispatcheren_skal_tage(monkeypatch, poster, forventet):
    monkeypatch.setattr(sw, "_load", lambda: poster)
    assert sw.forfaldne_ider() == forventet


def test_kan_lageret_ikke_laeses_er_intet_forfaldent_og_traaden_doer_ikke(monkeypatch):
    def _fejl():
        raise RuntimeError("væk")
    monkeypatch.setattr(sw, "_load", _fejl)
    assert sw.forfaldne_ider() == set()


def test_et_tik_uden_noget_forfaldent_kalder_ikke_dispatcheren():
    kald: list[int] = []
    ventetid = wt.tik(lambda: set(), lambda: kald.append(1) or {}, forrige=(frozenset(), 0))
    assert kald == []
    assert ventetid.naeste_ventetid_s == wt.INTERVAL_S


def test_et_tik_med_noget_forfaldent_kalder_dispatcheren_en_gang():
    kald: list[int] = []
    res = wt.tik(lambda: {"a"}, lambda: kald.append(1) or {}, forrige=(frozenset(), 0))
    assert kald == [1]
    assert res.naeste_ventetid_s == wt.INTERVAL_S


def test_samme_forfaldne_post_igen_og_igen_faar_traaden_til_at_bakke_af():
    """Kan en post ikke afsluttes (marker fejler), må tråden ikke aflevere den hver 5. s."""
    forrige = (frozenset(), 0)
    ventetider = []
    for _ in range(wt.MAKS_GENTAGELSER + 2):
        res = wt.tik(lambda: {"a"}, lambda: {}, forrige=forrige)
        forrige = res.tilstand
        ventetider.append(res.naeste_ventetid_s)
    assert ventetider[0] == wt.INTERVAL_S
    assert ventetider[-1] == wt.BAKKE_AF_S > wt.INTERVAL_S


def test_en_ny_post_nulstiller_gentagelserne():
    forrige = (frozenset({"a"}), wt.MAKS_GENTAGELSER + 1)
    res = wt.tik(lambda: {"b"}, lambda: {}, forrige=forrige)
    assert res.naeste_ventetid_s == wt.INTERVAL_S
    assert res.tilstand == (frozenset({"b"}), 1)


def test_en_dispatcher_der_kaster_vaelter_ikke_traaden():
    def _boom():
        raise RuntimeError("dispatch fejlede")
    res = wt.tik(lambda: {"a"}, _boom, forrige=(frozenset(), 0))
    assert res.naeste_ventetid_s == wt.INTERVAL_S


def test_start_er_idempotent_og_traaden_kan_stoppes(monkeypatch):
    monkeypatch.setattr(wt, "INTERVAL_S", 0.05)
    monkeypatch.setattr(sw, "_load", lambda: [])
    try:
        assert wt.start_wakeup_ticker() is True
        t1 = wt._traad
        assert wt.start_wakeup_ticker() is True
        assert wt._traad is t1 and t1.is_alive()
    finally:
        wt.stop_wakeup_ticker()
    assert wt._traad is None


def test_traaden_er_koblet_ind_i_runtime_opstarten():
    """AST, ikke grep: «bygget men ikke koblet» er det hyppigste mønster her."""
    import ast
    from pathlib import Path

    app = Path(__file__).resolve().parents[1] / "apps/api/jarvis_api/app.py"
    traer = ast.parse(app.read_text(encoding="utf-8"))
    kald = [
        n for n in ast.walk(traer)
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "start_wakeup_ticker"
    ]
    assert kald, "start_wakeup_ticker kaldes ikke fra app.py — traaden koerer aldrig"

    # og kun under runtime_services_enabled (dispatcheren bor i runtime-processen)
    for node in ast.walk(traer):
        if isinstance(node, ast.If) and "runtime_services_enabled" in ast.dump(node.test):
            inde = [n for n in ast.walk(node) if isinstance(n, ast.Call)
                    and getattr(n.func, "id", "") == "start_wakeup_ticker"]
            if inde:
                return
    raise AssertionError("start_wakeup_ticker staar ikke under `if runtime_services_enabled`")
