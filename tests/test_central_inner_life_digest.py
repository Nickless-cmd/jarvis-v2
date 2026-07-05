"""Tests for central_inner_life_digest — §24.4 reducér-ved-kilden.

Verificerer at digestet KUN bærer liveness+count pr. sektion (aldrig rå tekst),
at reduktionen er self-safe, og at en kastende builder isoleres. Dækker begge
grupper: inner_life (22, living-mind) og experiment (15, AGI/experiment-lag).
"""
from __future__ import annotations

import core.services.central_inner_life_digest as d


def test_digest_two_groups_and_total():
    out = d.build_inner_life_digest()
    assert isinstance(out, dict)
    assert "inner_life" in out and "experiment" in out
    assert "live_count" in out and "total" in out
    assert len(out["inner_life"]) == 22
    assert len(out["experiment"]) == 15
    assert out["total"] == 37


def test_no_text_keys_leak_in_either_group():
    out = d.build_inner_life_digest()
    for group in ("inner_life", "experiment"):
        for name, sec in out[group].items():
            # INGEN tekst-nøgler må lække — kun liveness/count
            assert set(sec.keys()) <= {"liveness", "count"}, f"{group}/{name} lækkede {sec.keys()}"
            assert isinstance(sec.get("liveness"), bool)
            assert isinstance(sec.get("count"), int)


def test_live_count_matches_liveness_across_both_groups():
    out = d.build_inner_life_digest()
    expected = sum(1 for s in out["inner_life"].values() if s.get("liveness"))
    expected += sum(1 for s in out["experiment"].values() if s.get("liveness"))
    assert out["live_count"] == expected


def test_reduce_empty():
    assert d._reduce({}) == {"liveness": False, "count": 0}
    assert d._reduce(None) == {"liveness": False, "count": 0}


def test_reduce_list_and_active():
    assert d._reduce({"items": [1, 2, 3], "active": True}) == {"liveness": True, "count": 3}


def test_first_count_int_when_no_list():
    assert d._first_count({"n": 7}) == 7
    # bool tælles ikke som int-magnitude
    assert d._first_count({"active": True, "n": 4}) == 4


def test_reduce_active_false():
    assert d._reduce({"active": False, "items": [1]}) == {"liveness": False, "count": 1}


def test_reduce_no_active_nonempty_is_live():
    # ingen 'active'-nøgle men ikke-tom → liveness True
    assert d._reduce({"n": 2}) == {"liveness": True, "count": 2}


def test_raising_inner_life_builder_is_isolated(monkeypatch):
    import core.services.somatic_daemon as som

    def boom():
        raise RuntimeError("nej")

    monkeypatch.setattr(som, "build_body_state_surface", boom, raising=False)
    out = d.build_inner_life_digest()
    assert out["inner_life"]["body"] == {"liveness": False, "count": 0}
    # resten uskadt: stadig 22+15 sektioner, alle med kun liveness/count
    assert out["total"] == 37
    for group in ("inner_life", "experiment"):
        for sec in out[group].values():
            assert set(sec.keys()) <= {"liveness", "count"}


def test_raising_experiment_builder_is_isolated(monkeypatch):
    import core.services.internal_cadence as ic

    def boom():
        raise RuntimeError("nej")

    monkeypatch.setattr(ic, "get_cadence_state", boom, raising=False)
    out = d.build_inner_life_digest()
    assert out["experiment"]["internal_cadence"] == {"liveness": False, "count": 0}
    assert out["total"] == 37
