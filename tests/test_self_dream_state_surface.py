"""Tests for selv/drøm-fladen (7/11-2026). Måler KOBLINGEN, ikke producenterne."""

from __future__ import annotations

import asyncio

from core.services import self_dream_state_surface as agg

EXPECTED_COUNT = 34  # 21 selv + 13 drom, maalt 7/11-2026
EXCLUDED = {"dreaming_session", "dream_action_executor", "self_model_predictive"}


def test_grupper_og_antal():
    assert agg.group_names() == ["selv", "drom"]
    navne = agg.producer_names()
    assert len(navne) == EXPECTED_COUNT
    assert len(set(navne)) == len(navne)
    assert not any(m.endswith(tuple(EXCLUDED)) for g in agg._GROUPS.values() for (_n, m, _f) in g)


def _fake_import(calls):
    class Mod:
        def __getattr__(self, fn):
            def produce(*a, **k):
                calls.append(fn)
                return {"active": True, "fn": fn}
            return produce
    return lambda path: Mod()


def test_hver_producent_i_listen_kaldes(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(agg.importlib, "import_module", _fake_import(calls))
    r = agg.build_self_dream_state_surface()
    forventet = [f for g in agg._GROUPS.values() for (_n, _m, f) in g]
    assert sorted(calls) == sorted(forventet)
    assert r["taxse"] == []
    assert r["svarer"] == agg.producer_names()
    assert r["active"] == agg.producer_names()
    assert r["groups"]["selv"]["count"] == 21
    assert r["groups"]["drom"]["count"] == 13
    assert r["mode"] == "self-dream-state-v1"


def test_kastende_producent_isoleres(monkeypatch):
    calls: list[str] = []
    ok = _fake_import(calls)
    ødelagt = agg._GROUPS["selv"][0]

    def imp(path):
        if path == ødelagt[1]:
            raise RuntimeError("bevidst fejl")
        return ok(path)

    monkeypatch.setattr(agg.importlib, "import_module", imp)
    r = agg.build_self_dream_state_surface()
    assert r["taxse"] == [ødelagt[0]]
    assert r["groups"]["selv"]["surfaces"][ødelagt[0]]["active"] is False
    assert "bevidst fejl" in r["groups"]["selv"]["surfaces"][ødelagt[0]]["reason"]
    assert len(r["svarer"]) == EXPECTED_COUNT - 1
    assert len(calls) == EXPECTED_COUNT - 1


def test_tom_og_ikke_dict_er_tavse(monkeypatch):
    class Mod:
        n = 0
        def __getattr__(self, fn):
            return lambda: {} if fn.endswith("a_surface") else "ikke dict"
    monkeypatch.setattr(agg.importlib, "import_module", lambda p: Mod())
    r = agg.build_self_dream_state_surface()
    assert sorted(r["taxse"]) == sorted(agg.producer_names())
    assert r["svarer"] == []


def test_ægte_aggregering_kaster_ikke_og_alle_svarer():
    r = agg.build_self_dream_state_surface()
    assert r["taxse"] == [], f"producenter svigtede: {r['taxse']}"
    assert len(r["svarer"]) == EXPECTED_COUNT


def test_ruten_eksponerer_fladen(monkeypatch):
    import apps.api.jarvis_api.routes.central as central

    assert "/central/self-state" in {r.path for r in central.router.routes}
    monkeypatch.setattr(central, "_require_owner", lambda: None)
    r = asyncio.run(central.central_self_state())
    assert r["mode"] == "self-dream-state-v1"
    assert len(r["svarer"]) == EXPECTED_COUNT
