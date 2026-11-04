"""Dagbøger glemmes ikke automatisk — og et arkiveret kan hentes tilbage.

Målt 4/11-2026: 58 af 147 backfillede dagbøger blev arkiveret af den eksisterende
glemsel inden for minutter (observation: halveringstid 14 dage, tærskel 0,05 ≈ 29 dage;
jarvis_brain_daemon: 90 dage), og resten var på vej. Tagget `daily-journal` er undtaget.
"""
from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from core.services import brain_archive, daily_journal_entry as je, jarvis_brain

_NU = datetime(2026, 11, 4, 20, 0, tzinfo=UTC)
_GAMMEL = datetime(2026, 6, 9, 20, 0, tzinfo=UTC)


@pytest.fixture
def hjerne(tmp_path, monkeypatch):
    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    return jarvis_brain.brain_dir()


def _gammel_dagbog(hjerne, dag="2026-06-09"):
    p = hjerne / "observation" / f"{dag}-daily.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"# Daily journal — {dag}\n\n_Synthesized {dag}T20:00:00+00:00 — 5 chat-msgs, 0 carries._\n\nDagen gik.\n",
        encoding="utf-8",
    )
    assert je.ensure_frontmatter(p) == "added"
    jarvis_brain.rebuild_index_from_files()
    return p


def _gammel_observation():
    return jarvis_brain.write_entry(
        kind="observation", title="Gammel observation", content="noget",
        visibility="personal", domain="self", now=_GAMMEL,
    )


def _status(entry_id_or_path_like):
    conn = jarvis_brain.connect_index()
    try:
        return conn.execute(
            "SELECT status FROM brain_index WHERE id = ? OR path LIKE ?",
            (entry_id_or_path_like, f"%{entry_id_or_path_like}"),
        ).fetchone()[0]
    finally:
        conn.close()


@pytest.mark.parametrize("entry, forventet", [
    ({"tags": ["daily-journal"]}, True),
    ({"tags": ["x", "daily-journal"]}, True),
    ({"tags": ["andet"]}, False),
    ({"tags": []}, False),
    ({}, False),
])
def test_er_undtaget_laeser_tags_fra_dict(entry, forventet):
    assert brain_archive.er_undtaget(entry) is forventet


def test_er_undtaget_laeser_tags_fra_en_brainentry(hjerne):
    _gammel_dagbog(hjerne)
    conn = jarvis_brain.connect_index()
    try:
        eid = conn.execute("SELECT id FROM brain_index WHERE path LIKE '%-daily.md'").fetchone()[0]
    finally:
        conn.close()
    assert brain_archive.er_undtaget(jarvis_brain.read_entry(eid)) is True
    assert brain_archive.er_undtaget(jarvis_brain.read_entry(_gammel_observation())) is False


def test_auto_arkivering_efter_90_dage_springer_dagbogen_over(hjerne):
    from core.services import jarvis_brain_daemon as bd

    _gammel_dagbog(hjerne)
    obs = _gammel_observation()
    assert bd.auto_archive_low_salience() == 1
    assert _status(obs) == "archived"
    assert _status("2026-06-09-daily.md") == "active"


def test_selektiv_konsolidering_arkiverer_ikke_en_undtaget_post(hjerne, monkeypatch):
    from core.services import selective_consolidation_daemon as sc

    arkiveret = []
    monkeypatch.setattr(jarvis_brain, "archive_entry", lambda eid, **kw: arkiveret.append(eid))
    sal = {"j": 0.05, "a": 0.5, "b": 0.6, "c": 0.9}   # j er klart lavest: uden undtagelsen er den bund-kandidaten
    monkeypatch.setattr(jarvis_brain, "read_entry",
                        lambda eid: {"id": eid, "tags": ["daily-journal"] if eid == "j" else [],
                                     "salience_base": sal[eid]})
    conn = jarvis_brain.connect_index()
    try:
        for eid in ("j", "a", "b", "c"):
            conn.execute(
                "INSERT INTO brain_index (id, path, kind, visibility, domain, title, created_at, updated_at,"
                " salience_base, salience_bumps, recall_count, importance, tags, related, status, file_hash,"
                " file_mtime_ns, file_size, indexed_at) VALUES (?,?,?,?,?,?,?,?,?,0,0,0.4,'[]','[]','active','h',0,0,?)",
                (eid, f"observation/{eid}.md", "observation", "personal", "self", eid,
                 "2026-11-04T10:00:00+00:00", "2026-11-04T10:00:00+00:00", 0.1, "2026-11-04T10:00:00+00:00"),
            )
        conn.commit()
    finally:
        conn.close()
    res = sc._consolidate_brain("2026-11-04T00:00:00+00:00")
    assert "j" not in arkiveret
    assert res["scored"] == 3 and res["archived"] == len(arkiveret) >= 1   # den rangerede de andre; ikke vacuøst


# --- restore ---------------------------------------------------------------

def test_restore_flytter_filen_tilbage_og_beholder_id_og_embedding(hjerne):
    p = _gammel_dagbog(hjerne)
    conn = jarvis_brain.connect_index()
    try:
        eid = conn.execute("SELECT id FROM brain_index WHERE path LIKE '%-daily.md'").fetchone()[0]
        conn.execute("UPDATE brain_index SET embedding = ?, embedding_dim = 3 WHERE id = ?", (b"abc", eid))
        conn.commit()
    finally:
        conn.close()
    jarvis_brain.archive_entry(eid, reason="test")
    assert not p.exists() and (hjerne / "_archive" / "observation" / p.name).exists()

    assert brain_archive.restore_entry(eid, now=_NU) == "restored"

    assert p.exists() and not (hjerne / "_archive" / "observation" / p.name).exists()
    fm, _ = jarvis_brain.parse_frontmatter(p)
    assert fm["id"] == eid and fm["status"] == "active"
    conn = jarvis_brain.connect_index()
    try:
        status, path, emb = conn.execute(
            "SELECT status, path, embedding FROM brain_index WHERE id = ?", (eid,)).fetchone()
    finally:
        conn.close()
    assert (status, emb) == ("active", b"abc") and path.endswith("observation/2026-06-09-daily.md")
    conn = jarvis_brain.connect_index()
    try:
        mtime, size = conn.execute("SELECT file_mtime_ns, file_size FROM brain_index WHERE id = ?", (eid,)).fetchone()
    finally:
        conn.close()
    assert (mtime, size) == (p.stat().st_mtime_ns, p.stat().st_size)   # indekset ser filen som uændret
    assert jarvis_brain.rebuild_index_from_files() == 0       # filen og indekset er ens


def test_restore_af_en_aktiv_post_aendrer_intet(hjerne):
    _gammel_dagbog(hjerne)
    conn = jarvis_brain.connect_index()
    try:
        eid = conn.execute("SELECT id FROM brain_index").fetchone()[0]
    finally:
        conn.close()
    assert brain_archive.restore_entry(eid) == "not-archived"
    assert brain_archive.restore_entry("brn_FINDES_IKKE") == "unknown"


def test_restore_exempt_henter_kun_undtagne_og_er_idempotent(hjerne):
    _gammel_dagbog(hjerne, "2026-06-09")
    _gammel_dagbog(hjerne, "2026-06-10")
    obs = _gammel_observation()
    conn = jarvis_brain.connect_index()
    try:
        ids = [r[0] for r in conn.execute("SELECT id FROM brain_index WHERE path LIKE '%-daily.md'")]
    finally:
        conn.close()
    for i in ids + [obs]:
        jarvis_brain.archive_entry(i, reason="test")

    assert brain_archive.restore_exempt_archived() == {"restored": 2, "failed": 0}
    assert _status(obs) == "archived"                      # den almindelige blev IKKE hentet
    assert all(_status(i) == "active" for i in ids)
    assert brain_archive.restore_exempt_archived() == {"restored": 0, "failed": 0}


def test_journal_exists_for_ser_ogsaa_en_arkiveret_dagbog(hjerne, monkeypatch):
    from core.services import daily_journal

    monkeypatch.setattr(daily_journal, "OBSERVATION_DIR", hjerne / "observation")
    p = _gammel_dagbog(hjerne)
    assert daily_journal.journal_exists_for(date(2026, 6, 9)) is True
    conn = jarvis_brain.connect_index()
    try:
        eid = conn.execute("SELECT id FROM brain_index").fetchone()[0]
    finally:
        conn.close()
    jarvis_brain.archive_entry(eid, reason="test")
    assert not p.exists()
    assert daily_journal.journal_exists_for(date(2026, 6, 9)) is True      # arkiveret ≠ mangler
    assert daily_journal.journal_exists_for(date(2026, 6, 10)) is False
