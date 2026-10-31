"""Vagter for de 12 tavse fald i jarvis_brain.py (31/10-2026).

Fejlformen der blev rettet: et ``except`` returnerede en vaerdi der er
IDENTISK med den legitime tilstand. ``[]`` = baade «ingen poster» og
«indekset kunne ikke laeses». ``continue`` = baade «filen er uaendret» og
«filen kunne ikke parses». Uden et spor kan ingen af delene skelnes bagefter.

Hver vagt beviser TO ting:
  1. fejlen efterlader et spor (WARNING paa modul-loggeren), og
  2. returvaerdien er stadig den fail-soft vaerdi kalderne forventer.

Plus én stoej-vagt: normal drift maa IKKE logge. Uden den drukner de aegte
fejl i normal-adfaerd, og saa er sporet vaerdiloest.
"""
from __future__ import annotations

import logging
import sqlite3

import core.services.jarvis_brain as jb

LOGGER = "core.services.jarvis_brain"


def _advarsler(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def _schema_conn() -> sqlite3.Connection:
    """In-memory DB med modulets EGET schema — ikke en haandskrevet efterligning.

    Maalt 31/10-2026: en haandskrevet test-tabel manglede `embedding`, saa
    SELECT'en fejlede paa en kolonne der findes i produktionen. Testen maalte
    sin egen tabel, ikke koden.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(jb._INDEX_SCHEMA)
    return conn


class _KasterPaaExecute:
    """Wrapper der faar et kast ud af en bestemt SQL-form.

    sqlite3.Connection.execute er read-only, saa monkeypatch paa den virker
    ikke — vi maa pakke forbindelsen ind i stedet.
    """

    def __init__(self, conn, marker: str):
        self._conn = conn
        self._marker = marker

    def execute(self, sql, *a, **k):
        if self._marker in sql:
            raise sqlite3.OperationalError("database is locked")
        return self._conn.execute(sql, *a, **k)

    def __getattr__(self, navn):
        return getattr(self._conn, navn)


def _indsæt(conn, entry_id: str, **kolonner) -> None:
    """Indsæt en raekke med modulets faktiske kolonner."""
    felter = {
        "id": entry_id,
        "path": f"{entry_id}.md",
        "kind": "fakta",
        "visibility": "personal",
        "domain": "d",
        "title": "t",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "file_hash": "h",
        "indexed_at": "2026-01-01T00:00:00+00:00",
    }
    felter.update(kolonner)
    navne = ", ".join(felter)
    pladser = ", ".join("?" * len(felter))
    conn.execute(
        f"INSERT INTO brain_index ({navne}) VALUES ({pladser})",
        tuple(felter.values()),
    )
    conn.commit()


_DB = None


def _nulstil() -> None:
    """Hver test skal have sin EGEN base.

    Maalt 31/10-2026: uden dette arvede stoej-vagten de foregaaende testers
    korrupte raekker og blev roed paa advarsler den ikke selv havde skabt.
    """
    global _DB
    _DB = None


def _frisk():
    """Ny forbindelse til den SAMME in-memory DB.

    `search_brain_scored` lukker sin forbindelse, og `brain_vector_cache`
    aabner sin egen bagefter — en delt, allerede lukket forbindelse giver
    «Cannot operate on a closed database». En fil-baseret DB overlever det.
    """
    import sqlite3 as _s

    return _s.connect(_DB)


def _fyld(entry_id: str, **kolonner) -> None:
    """Opret DB'en (én gang pr. test) og indsaet raekken med embedding."""
    global _DB
    import tempfile
    from pathlib import Path as _P

    if _DB is None:
        _DB = str(_P(tempfile.mkdtemp()) / "brain_test.sqlite")
        c = _s_connect(_DB)
        c.executescript(jb._INDEX_SCHEMA)
        c.close()
    c = _s_connect(_DB)
    _med_embedding(c, entry_id, **kolonner)
    c.close()


def _s_connect(sti):
    import sqlite3 as _s

    return _s.connect(sti)


def _med_embedding(conn, entry_id: str, **kolonner) -> None:
    """Samme raekke, men MED en embedding-blob.

    `search_brain_scored` filtrerer paa `WHERE embedding IS NOT NULL`, saa en
    raekke uden blob naar aldrig den loekke der indeholder de to fald vi maaler.
    Maalt 31/10-2026: uden blob var testen groen uden at have roert koden.
    """
    import numpy as np

    blob = np.zeros(768, dtype=np.float32).tobytes()
    _indsæt(conn, entry_id, embedding=blob, embedding_dim=768, **kolonner)


# ── 1. _ensure_wal: WAL kunne ikke slaas til ─────────────────────────────


def test_wal_fejl_logger_men_fortsaetter(monkeypatch, caplog):
    """Et kast paa PRAGMA journal_mode efterlader et spor — og kaster ikke videre."""
    conn = _KasterPaaExecute(sqlite3.connect(":memory:"), "journal_mode")
    monkeypatch.setattr(jb, "_WAL_READY", set())

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        jb._ensure_wal(conn, "test-noegle")  # maa ikke kaste

    assert any("WAL" in m for m in _advarsler(caplog)), "WAL-fejl efterlod intet spor"
    assert "test-noegle" not in jb._WAL_READY, "fejlet WAL blev markeret som klar"


def test_wal_success_logger_ikke(caplog):
    """Normal WAL-opsaetning maa ikke stoeje."""
    conn = sqlite3.connect(":memory:")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        jb._ensure_wal(conn, "test-ok")
    assert _advarsler(caplog) == []


# ── 2. embed_pending_entries: ulaeselig fil ──────────────────────────────


def test_embed_pending_logger_naar_fil_ikke_kan_parses(monkeypatch, caplog, tmp_path):
    """En post der ikke kan parses bliver ikke embeddet — det skal kunne ses."""
    conn = _schema_conn()
    _indsæt(conn, "brn_X", path="findes/ikke.md")
    monkeypatch.setattr(jb, "connect_index", lambda: conn)
    monkeypatch.setattr(jb, "_workspace_root", lambda: tmp_path)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        antal = jb.embed_pending_entries()

    assert antal == 0, "en ulaeselig post blev alligevel talt som embeddet"
    assert any("embedding" in m for m in _advarsler(caplog)), "ulaeselig fil efterlod intet spor"


# ── 3. search_brain_scored: korrupt importance ───────────────────────────


def test_korrupt_importance_logger_men_beholder_1_0(monkeypatch, caplog):
    _nulstil()
    """En ikke-numerisk importance giver stadig 1.0 — men nu med et spor."""
    _fyld("brn_Y", importance="IKKE-ET-TAL")
    monkeypatch.setattr(jb, "connect_index", _frisk)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        jb.search_brain_scored(query_text="x", limit=5)

    assert any("importance" in m for m in _advarsler(caplog)), "korrupt importance efterlod intet spor"


# ── 4. write_entry: observe_hub kaster ───────────────────────────────────


def test_observe_hub_fejl_logger_men_skriver_alligevel(monkeypatch, caplog, tmp_path):
    """Telemetri-fejl maa ikke blokere skrivningen — men skal kunne ses."""
    conn = _schema_conn()
    monkeypatch.setattr(jb, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(jb, "connect_index", lambda: conn)
    monkeypatch.setattr(jb, "infer_temporal_edges", lambda *_a, **_k: None)

    import core.services.central_private_observe as cpo

    def _braek(*_a, **_k):
        raise RuntimeError("centralen er nede")

    monkeypatch.setattr(cpo, "observe_hub", _braek)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        new_id = jb.write_entry(
            kind="fakta", title="t", content="c", visibility="personal",
            domain="test", skip_temporal=True,
        )

    assert new_id.startswith("brn_"), "skrivningen blev blokeret af en telemetri-fejl"
    assert any("observe_hub" in m for m in _advarsler(caplog)), "telemetri-fejl efterlod intet spor"


# ── 5. write_entry: temporal-inferens kaster ─────────────────────────────


def test_temporal_inferens_fejl_logger_men_skriver_alligevel(monkeypatch, caplog, tmp_path):
    """Inferens-fejl maa ikke blokere skrivningen — men posten staar uden kanter."""
    conn = _schema_conn()
    monkeypatch.setattr(jb, "_workspace_root", lambda: tmp_path)
    monkeypatch.setattr(jb, "connect_index", lambda: conn)

    def _braek(*_a, **_k):
        raise RuntimeError("inferens eksploderede")

    monkeypatch.setattr(jb, "infer_temporal_edges", _braek)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        new_id = jb.write_entry(
            kind="fakta", title="t2", content="c", visibility="personal", domain="test",
        )

    assert new_id.startswith("brn_"), "skrivningen blev blokeret af inferens-fejl"
    assert any("temporal-inferens" in m for m in _advarsler(caplog)), "inferens-fejl efterlod intet spor"


# ── 6. _ensure_index_schema_migrations: DROP INDEX fejler ────────────────


def test_drop_indeks_fejl_logger(monkeypatch, caplog):
    """Et DROP der ikke kan tages nu skal efterlade et spor — 59 MB bliver liggende."""
    conn = _KasterPaaExecute(_schema_conn(), "DROP INDEX")

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        jb._ensure_index_schema_migrations(conn)  # maa ikke kaste

    assert any("doedt indeks" in m for m in _advarsler(caplog)), "DROP-fejl efterlod intet spor"


# ── 7. tags-kolonne med ugyldig JSON ─────────────────────────────────────


def test_korrupt_tags_logger_men_behandles_som_tom(monkeypatch, caplog):
    _nulstil()
    """Ugyldig tags-JSON giver stadig tom liste — men posten forsvinder ikke i tavshed."""
    _fyld("brn_Z", tags="{ikke json")
    monkeypatch.setattr(jb, "connect_index", _frisk)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        jb.search_brain_scored(query_text="x", tags=["hvad-som-helst"], limit=5)

    assert any("tags" in m for m in _advarsler(caplog)), "korrupt tags efterlod intet spor"


# ── 8. stoej-vagt: normal soegning logger ikke ───────────────────────────


def test_normal_soegning_logger_ikke(monkeypatch, caplog):
    _nulstil()
    """En velfungerende raekke maa ikke producere advarsler."""
    _fyld("brn_OK", tags='["a"]', importance=0.8)
    monkeypatch.setattr(jb, "connect_index", _frisk)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        jb.search_brain_scored(query_text="x", tags=["a"], limit=5)

    assert _advarsler(caplog) == [], f"normal soegning stoejede: {_advarsler(caplog)}"
