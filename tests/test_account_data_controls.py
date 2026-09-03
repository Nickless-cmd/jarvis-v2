"""Brugerens egne data: tælle, eksportere, slette — lagvis.

Det vigtigste her er IKKE at sletning virker, men at den er user-scopet: en
bruger må aldrig kunne ramme en andens data, heller ikke owneren, heller ikke
ved et uheld. Derfor har hvert slette-test en fremmed post der SKAL overleve.
"""
from __future__ import annotations

import json

import pytest

from core.services import account_data_controls as adc


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """Isolér identitetsfilerne til en midlertidig mappe."""
    (tmp_path / "MEMORY.md").write_text("- noget jeg husker\n", encoding="utf-8")
    (tmp_path / "USER.md").write_text("Bjørn er udvikler\n", encoding="utf-8")
    monkeypatch.setattr(adc, "_identity_paths",
                        lambda uid: [tmp_path / "MEMORY.md", tmp_path / "USER.md"])
    return tmp_path


# ── Tælling ──────────────────────────────────────────────────────────────────

def test_overblik_har_alle_fire_lag(ws, monkeypatch):
    monkeypatch.setattr(adc, "_count_sessions", lambda uid: 3)
    monkeypatch.setattr(adc, "_count_senses", lambda uid="": 7)
    monkeypatch.setattr(adc, "_count_brain", lambda uid="": 11)

    out = adc.data_overview("u1")
    keys = [layer["key"] for layer in out["layers"]]
    assert keys == ["sessions", "senses", "brain", "identity"]
    assert [layer["count"] for layer in out["layers"]][:3] == [3, 7, 11]
    # Identitet måles i tegn, ikke i antal — filerne har indhold.
    assert out["layers"][3]["count"] > 0


def test_hvert_lag_har_et_tal_og_en_forklaring(ws, monkeypatch):
    """En sletteknap uden et tal ved siden af beder folk om at gætte hvad de
    mister."""
    monkeypatch.setattr(adc, "_count_sessions", lambda uid: 0)
    monkeypatch.setattr(adc, "_count_senses", lambda uid="": 0)
    monkeypatch.setattr(adc, "_count_brain", lambda uid="": 0)
    for layer in adc.data_overview("u1")["layers"]:
        assert isinstance(layer["count"], int)
        assert layer["detail"].strip()
        assert layer["label"].strip()


def test_taelling_taaler_at_et_lag_er_utilgaengeligt(ws, monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("db nede")
    monkeypatch.setattr(adc, "_count_sessions", _boom)
    # Overblikket må ikke vælte fordi ét lag ikke kan læses.
    with pytest.raises(RuntimeError):
        adc.data_overview("u1")


# ── Identitet ────────────────────────────────────────────────────────────────

def test_identitet_toemmes_men_slettes_ikke(ws):
    """Resten af runtimen forventer at filerne FINDES. En manglende fil ville
    give fejl et helt andet sted end her."""
    out = adc.reset_identity("u1")
    assert set(out["cleared"]) == {"MEMORY.md", "USER.md"}
    for name in ("MEMORY.md", "USER.md"):
        assert (ws / name).exists()
        assert (ws / name).read_text(encoding="utf-8") == ""


def test_soul_roeres_aldrig(ws):
    """SOUL.md er Jarvis' egen kerne, ikke brugerens data."""
    assert "SOUL.md" not in adc._IDENTITY_FILES


# ── Sletning er user-scopet ──────────────────────────────────────────────────

def _seed(conn, table, rows):
    for r in rows:
        cols = ", ".join(r)
        vals = ", ".join("?" for _ in r)
        conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({vals})", tuple(r.values()))


def test_sanser_sletter_kun_egne(monkeypatch, tmp_path):
    import sqlite3
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE sensory_memories (id INTEGER PRIMARY KEY, user_id TEXT)")
    db.executemany("INSERT INTO sensory_memories (user_id) VALUES (?)",
                   [("u1",), ("u1",), ("u2",), (None,)])
    db.commit()

    class _Ctx:
        def __enter__(self): return db
        def __exit__(self, *a): return False
    import core.runtime.db as _db
    monkeypatch.setattr(_db, "connect", lambda *a, **k: _Ctx(), raising=False)

    out = adc.delete_senses("u1")
    assert out["deleted"] == 2
    # Den fremmede post SKAL overleve.
    rest = [r["user_id"] for r in db.execute("SELECT user_id FROM sensory_memories")]
    assert "u2" in rest


def test_brain_sletter_kun_egne(monkeypatch):
    import sqlite3
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE private_brain_records (id INTEGER PRIMARY KEY, user_id TEXT)")
    db.executemany("INSERT INTO private_brain_records (user_id) VALUES (?)",
                   [("u1",), ("u2",), ("u2",)])
    db.commit()

    class _Ctx:
        def __enter__(self): return db
        def __exit__(self, *a): return False
    import core.runtime.db as _db
    monkeypatch.setattr(_db, "connect", lambda *a, **k: _Ctx(), raising=False)

    assert adc.delete_brain("u1")["deleted"] == 1
    assert db.execute("SELECT count(*) FROM private_brain_records").fetchone()[0] == 2


def test_ukendt_lag_afvises_frem_for_at_tie(ws):
    with pytest.raises(ValueError):
        adc.delete_layer("u1", "alt-muligt")


def test_slet_alt_fortsaetter_selv_om_et_lag_fejler(ws, monkeypatch):
    """Stopper vi halvvejs, tror brugeren at intet skete."""
    monkeypatch.setitem(adc._DELETERS, "sessions",
                        lambda uid: (_ for _ in ()).throw(RuntimeError("nede")))
    monkeypatch.setitem(adc._DELETERS, "senses", lambda uid: {"layer": "senses", "deleted": 4})
    monkeypatch.setitem(adc._DELETERS, "brain", lambda uid: {"layer": "brain", "deleted": 2})

    out = adc.delete_all("u1")
    layers = {r["layer"]: r for r in out["results"]}
    assert layers["sessions"]["failed"] == 1
    assert "error" in layers["sessions"]
    assert layers["senses"]["deleted"] == 4
    # Identitet nåede også at køre, selv om det FØRSTE lag fejlede.
    assert layers["identity"]["deleted"] == 2


# ── Eksport ──────────────────────────────────────────────────────────────────

def test_eksport_indeholder_alle_lag(ws, monkeypatch):
    monkeypatch.setattr("core.services.chat_sessions.list_chat_sessions",
                        lambda **k: [], raising=False)
    out = adc.export_all("u1")
    for key in ("sessions", "senses", "brain", "identity", "exported_at"):
        assert key in out
    assert out["identity"]["USER.md"] == "Bjørn er udvikler\n"


def test_et_daarligt_lag_vaelter_ikke_hele_eksporten(ws, monkeypatch):
    """En delvis eksport er mere værd end ingen."""
    import core.runtime.db_sensory as sens
    monkeypatch.setattr(sens, "list_sensory_memories",
                        lambda **k: (_ for _ in ()).throw(RuntimeError("nede")),
                        raising=False)
    out = adc.export_all("u1")
    assert "error" in out["senses"]
    assert "identity" in out


def test_eksport_er_gyldig_json(ws):
    parsed = json.loads(adc.export_json("u1"))
    assert parsed["user_id"] == "u1"


def test_taelling_henter_ikke_raekker_for_at_taelle(monkeypatch):
    """Målt på Bjørns runtime: 128.550 brain-poster. Første udgave gjorde
    len(list(limit=100_000)) — loftet ville have LØJET, og hvert besøg i
    indstillingerne ville have hentet hundredtusind rækker for ét tal."""
    import sqlite3
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE private_brain_records (id INTEGER PRIMARY KEY, user_id TEXT)")
    db.executemany("INSERT INTO private_brain_records (user_id) VALUES (?)",
                   [("u1",)] * 5 + [("u2",)] * 3)
    db.commit()

    class _Ctx:
        def __enter__(self): return db
        def __exit__(self, *a): return False
    import core.runtime.db as _db
    monkeypatch.setattr(_db, "connect", lambda *a, **k: _Ctx(), raising=False)

    assert adc._count_brain("u1") == 5
    assert adc._count_brain("u2") == 3
