"""Tests for ghost_networks.py"""

import pytest
from core.services.ghost_networks import (
    archive_dead_nodes,
    describe_ghost_network,
    format_ghost_for_prompt,
    reset_ghost_networks,
    build_ghost_networks_surface,
)


def setup_function():
    reset_ghost_networks()


def test_archive_dead_nodes():
    archive_dead_nodes(["node1", "node2"])
    surface = build_ghost_networks_surface()
    assert surface["ghost_count"] == 2
    assert surface["active"] is True


def test_describe_ghost_network():
    archive_dead_nodes(["old_node"])
    desc = describe_ghost_network()
    assert "old_node" in desc


def test_format_ghost_for_prompt():
    archive_dead_nodes(["ghost_node"])
    result = format_ghost_for_prompt()
    assert "SPØGELSE:" in result


def test_build_ghost_networks_surface():
    archive_dead_nodes(["node_a", "node_b"])
    surface = build_ghost_networks_surface()
    assert surface["active"] is True
    assert surface["ghost_count"] == 2


def test_reset_ghost_networks():
    archive_dead_nodes(["node1"])
    reset_ghost_networks()
    surface = build_ghost_networks_surface()
    assert surface["ghost_count"] == 0
    assert surface["active"] is False


def test_empty_ghost_networks():
    surface = build_ghost_networks_surface()
    assert surface["active"] is False
    assert surface["ghost_count"] == 0


# ── Spøgelser er mønstre der DØDE, og de falmer (25/9-2026) ──────────────
#
# Indtil i dag stod der:
#
#     _ghosts: list[dict] = []
#     "decay_rate": 0.0,
#
# En modul-global liste der døde ved genstart, og et henfald der blev sat til
# 0.0 og ALDRIG opdateret. `describe_ghost_network` filtrerede på
# `decay_rate < 0.8` og tog `active[0]` — det ældste spøgelse, for evigt.
# Et spor der per definition aldrig kunne falme.
#
# `archive_dead_nodes` havde INGEN kalder. Kilden er nu signal-tabellernes
# døde rækker: 29.393 står `superseded`/`stale`, men kun de unge cirkler.
from datetime import UTC, datetime, timedelta  # noqa: E402

import core.services.ghost_networks as G  # noqa: E402


def _lager(monkeypatch, tmp_path):
    monkeypatch.setattr(G, "_storage_path", lambda: tmp_path / "ghost_networks.json")


def test_spoegelserne_overlever_en_genstart(monkeypatch, tmp_path):
    """KERNEN. En modul-global liste døde med processen."""
    _lager(monkeypatch, tmp_path)
    G.reset_ghost_networks()
    G.archive_dead_nodes(["et gammelt fokus paa dansk"], "et fokus")

    import importlib
    G2 = importlib.reload(G)
    monkeypatch.setattr(G2, "_storage_path", lambda: tmp_path / "ghost_networks.json")
    assert G2.build_ghost_networks_surface()["ghost_count"] == 1


def test_henfaldet_er_ALDEREN_ikke_nul(monkeypatch, tmp_path):
    """Det var 0.0 og blev aldrig opdateret."""
    _lager(monkeypatch, tmp_path)
    G.reset_ghost_networks()
    gammel = (datetime.now(UTC) - timedelta(days=15)).isoformat()
    G.archive_dead_nodes(["et moenster fra for laenge siden"], "et fokus", gammel)
    assert abs(G._med_henfald()[0]["decay_rate"] - 0.5) < 0.02


def test_et_falmet_spoegelse_naevnes_ikke_men_slettes_heller_ikke(monkeypatch, tmp_path):
    _lager(monkeypatch, tmp_path)
    G.reset_ghost_networks()
    doedt = (datetime.now(UTC) - timedelta(days=29)).isoformat()
    G.archive_dead_nodes(["noget der er helt falmet nu"], "et fokus", doedt)
    u = G.build_ghost_networks_surface()
    assert u["ghost_count"] == 1 and u["circling_count"] == 0
    assert G.describe_ghost_network() == ""


def test_det_MINDST_falmede_naevnes_ikke_det_aeldste(monkeypatch, tmp_path):
    """Før stod der `active[0]` — det første i listen, altså det ældste."""
    _lager(monkeypatch, tmp_path)
    G.reset_ghost_networks()
    G.archive_dead_nodes(["det gamle moenster her"], "et fokus",
                         (datetime.now(UTC) - timedelta(days=20)).isoformat())
    G.archive_dead_nodes(["det nye moenster her"], "en indre note",
                         (datetime.now(UTC) - timedelta(days=1)).isoformat())
    assert "det nye moenster her" in G.describe_ghost_network()


def test_samme_moenster_arkiveres_ikke_to_gange(monkeypatch, tmp_path):
    _lager(monkeypatch, tmp_path)
    G.reset_ghost_networks()
    assert G.archive_dead_nodes(["et moenster der gentages"], "et fokus") == 1
    assert G.archive_dead_nodes(["et moenster der gentages"], "et fokus") == 0


def test_en_kort_ytring_er_ikke_et_moenster(monkeypatch, tmp_path):
    """Maalt i produktionen: blandt de 54 der cirklede stod «Private inner
    note: Hmm», «: Ja tak», «: Gør det». En ytring der tilfældigvis blev til
    et signal er ikke et spor af et mønster."""
    assert G._kernen("Private inner note: Hmm") == "Hmm"
    assert len(G._kernen("Private inner note: Hmm")) < G._MINDSTE_MOENSTER
    assert len(G._kernen("Diary synthesis: hvorn gaar antropic og chatgpt")) >= G._MINDSTE_MOENSTER


def test_tikket_henter_kun_de_DOEDE_og_kun_de_unge(monkeypatch, tmp_path):
    _lager(monkeypatch, tmp_path)
    G.reset_ghost_networks()
    sql = []

    class _C:
        def execute(self, s, a=()):
            sql.append(s)
            return self

        def fetchall(self):
            return [("Diary synthesis: et rigtigt moenster her", "k1",
                     datetime.now(UTC).isoformat())]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("core.runtime.db.connect", lambda *a, **k: _C())
    # attrappen giver SAMME titel fra alle fire tabeller — dedup goer det til ét
    assert G.tick(30.0)["nye"] == 1
    for s in sql:
        assert "superseded" in s and "stale" in s
        assert "-30 days" in s


def test_en_base_der_ikke_kan_naas_vaelter_ikke_tikket(monkeypatch, tmp_path):
    _lager(monkeypatch, tmp_path)
    monkeypatch.setattr("core.runtime.db.connect",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    assert G.tick(30.0) == {"nye": 0}


def test_der_er_INTET_random():
    import ast
    import inspect
    traen = ast.parse(inspect.getsource(G))
    assert not any(isinstance(n, ast.Import) and any(a.name == "random" for a in n.names)
                   for n in ast.walk(traen))
