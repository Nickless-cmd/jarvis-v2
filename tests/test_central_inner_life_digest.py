"""Tests for central_inner_life_digest — §24.4 reducér-ved-kilden.

Verificerer at digestet KUN bærer liveness+count pr. sektion (aldrig rå tekst),
at reduktionen er self-safe, og at en kastende builder isoleres.
"""
from __future__ import annotations

import core.services.central_inner_life_digest as d


def test_digest_shape_only_liveness_count():
    out = d.build_inner_life_digest()
    assert isinstance(out, dict)
    assert "sections" in out and "live_count" in out and "total" in out
    assert out["total"] == 12
    assert len(out["sections"]) == 12
    for name, sec in out["sections"].items():
        # INGEN tekst-nøgler må lække — kun liveness/count
        assert set(sec.keys()) <= {"liveness", "count"}, f"{name} lækkede nøgler {sec.keys()}"
        assert isinstance(sec.get("liveness"), bool)
        assert isinstance(sec.get("count"), int)


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


def test_raising_builder_is_isolated(monkeypatch):
    import core.services.somatic_daemon as som

    def boom():
        raise RuntimeError("nej")

    monkeypatch.setattr(som, "build_body_state_surface", boom, raising=False)
    out = d.build_inner_life_digest()
    assert out["sections"]["body"] == {"liveness": False, "count": 0}
    # resten uskadt: stadig 12 sektioner, alle med kun liveness/count
    assert out["total"] == 12
    for sec in out["sections"].values():
        assert set(sec.keys()) <= {"liveness", "count"}
