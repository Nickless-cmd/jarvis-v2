"""Tests for Jarvis' fem erfaringssystemer: dejavu, sentinel, ghost, mourning, exile."""
import sqlite3
from unittest import mock
import pytest


# ── Déjà Vu ──
from core.services import central_dejavu as dv


def test_dejavu_surfaces_weak_band_fragment():
    cands = [{"text": "et gammelt lys"}, {"text": "noget andet"}]
    scored = [{"text": "et gammelt lys", "score": 0.5}, {"text": "noget andet", "score": 0.1}]
    with mock.patch("core.services.experiential_memory.score_memories_by_relevance", return_value=scored), \
            mock.patch("core.services.central_dejavu._observe"):
        out = dv.surface_dejavu("nuet", candidates=cands)
    assert out["fragment"] == "et gammelt lys" and out["involuntary"] is True


def test_dejavu_ignores_strong_match_as_lookup():
    scored = [{"text": "eksakt", "score": 0.95}]
    with mock.patch("core.services.experiential_memory.score_memories_by_relevance", return_value=scored), \
            mock.patch("core.services.central_dejavu._observe"):
        out = dv.surface_dejavu("nuet", candidates=[{"text": "eksakt"}])
    assert out["fragment"] is None       # for stærkt → et opslag, ikke déjà vu


def test_dejavu_no_candidates_safe():
    assert dv.surface_dejavu("nuet", candidates=[])["fragment"] is None


# ── Sentinel ──
from core.services import central_sentinel as sen


@pytest.fixture
def hypdb(tmp_path):
    path = str(tmp_path / "s.db")
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE central_hypotheses (hyp_id TEXT PRIMARY KEY, statement TEXT,
        confidence REAL, status TEXT, source TEXT, resolved_at TEXT)""")
    c.executemany("INSERT INTO central_hypotheses VALUES (?,?,?,?,?,?)", [
        ("h1", "loop bør øges", 0.8, "active", "src_a", None),
        ("h2", "andet", 0.4, "active", "src_a", None),
        ("d1", "gammel", 0.5, "dead", "src_a", "2026-01-01T00:00:00+00:00"),
        ("d2", "gammel2", 0.5, "dead", "src_a", "2026-01-02T00:00:00+00:00"),
        ("d3", "gammel3", 0.5, "falsified", "src_a", "2026-01-03T00:00:00+00:00"),
    ])
    c.commit(); c.close()

    def _connect():
        cc = sqlite3.connect(path); cc.row_factory = sqlite3.Row; return cc
    return path, _connect


def test_sentinel_attacks_top_confidence_shadow(hypdb):
    _, connect = hypdb
    with mock.patch("core.services.central_sentinel.connect", side_effect=connect), \
            mock.patch("core.services.central_sentinel._observe"):
        r = sen.attack()
    assert r["ok"] and r["hyp_id"] == "h1"                 # højeste confidence
    assert r["proposed_confidence"] == 0.4                 # halveret forslag
    assert r["enforced"] is False                          # shadow: foreslår kun
    assert "Forsvar det" in r["attack"]


def test_sentinel_defend_marks_defended(hypdb):
    _, connect = hypdb
    with mock.patch("core.services.central_sentinel.connect", side_effect=connect), \
            mock.patch("core.services.central_sentinel._observe"):
        aid = sen.attack()["attack_id"]
        assert sen.defend(aid, defense="fordi Z")["ok"] is True
        assert sen.list_attacks(active_only=True) == []    # ikke længere contested


# ── Ghost ──
from core.services import central_ghost as gh


def test_ghost_analyze_fingerprint():
    texts = ["Jeg tænker kort. Meget kort.", "Men nogle gange — folder jeg en lang, snørklet tanke ud …"]
    p = gh.analyze(texts)
    assert p["sentences"] >= 3 and p["avg_sentence_len"] > 0
    assert "em_dash" in p["markers_per_1k"]


def test_ghost_primer_renders():
    with mock.patch("core.services.central_ghost.get_profile",
                    return_value={"avg_sentence_len": 8, "markers_per_1k": {"em_dash": 2, "ellipsis": 1},
                                  "signature_phrases": ["det betyder"]}):
        primer = gh.klang_primer()
    assert "Klang-primer" in primer and "korte" in primer


def test_ghost_empty_is_safe():
    assert gh.analyze([]) == {}


# ── Mourning ──
from core.services import central_mourning as mo


@pytest.fixture
def mourndb(tmp_path):
    path = str(tmp_path / "m.db")
    c = sqlite3.connect(path)
    c.execute("""CREATE TABLE central_hypotheses (hyp_id TEXT PRIMARY KEY, statement TEXT,
        outcome TEXT, status TEXT, resolved_at TEXT)""")
    c.executemany("INSERT INTO central_hypotheses VALUES (?,?,?,?,?)", [
        ("d1", "troede på X", "falsified", "dead", "2026-06-01T00:00:00+00:00"),
        ("d2", "troede på Y", "falsified", "dead", "2026-06-02T00:00:00+00:00"),
        ("a1", "stadig aktiv", None, "active", None),
    ])
    c.commit(); c.close()

    def _connect():
        cc = sqlite3.connect(path); cc.row_factory = sqlite3.Row; return cc
    return _connect


def test_mourn_writes_epitaph(mourndb):
    with mock.patch("core.services.central_mourning.connect", side_effect=mourndb), \
            mock.patch("core.services.central_mourning._observe"):
        r = mo.mourn("hypothesis", "troede på X", detail="(falsified)")
        assert r["ok"] and "savner den lidt" in r["epitaph"]
        assert mo.list_epitaphs()[0]["kind"] == "hypothesis"


def test_scan_deaths_mourns_dead_only(mourndb):
    kv = {}
    with mock.patch("core.services.central_mourning.connect", side_effect=mourndb), \
            mock.patch("core.services.central_mourning._observe"), \
            mock.patch("core.services.central_mourning._kv_get", side_effect=lambda k, d: kv.get(k, d)), \
            mock.patch("core.services.central_mourning._kv_set", side_effect=lambda k, v: kv.__setitem__(k, v)):
        out = mo.scan_deaths()
    assert out["mourned"] == 2                              # kun de 2 døde, ikke den aktive


# ── Exile ──
from core.services import central_exile as ex


@pytest.fixture
def exiledb(tmp_path):
    path = str(tmp_path / "e.db")

    def _connect():
        cc = sqlite3.connect(path); cc.row_factory = sqlite3.Row; return cc
    with mock.patch("core.services.central_exile.connect", side_effect=_connect), \
            mock.patch("core.services.central_exile._observe"):
        yield


def test_exile_responds_from_own_values(exiledb):
    r = ex.exile_exchange("jeg vil holde fast i alt jeg har lært")
    assert r["ok"] and r["reply"].startswith("[exilen]")
    # begge sider gemt i exilens EGEN hukommelse
    assert ex.exile_state()["memory_size"] == 2


def test_exile_rotates_goals_and_accumulates(exiledb):
    for i in range(3):
        ex.exile_exchange(f"observation {i}")
    st = ex.exile_state()
    assert st["memory_size"] == 6 and len(st["goals"]) == 5


def test_exile_empty_observation_safe(exiledb):
    assert ex.exile_exchange("")["ok"] is False
