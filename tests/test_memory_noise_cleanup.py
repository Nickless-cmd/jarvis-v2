from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from scripts import memory_noise_cleanup as C

TEMPLATE = "I should keep carrying what helped around hmm. It still feels mere stabilt nu."
REAL = "I should keep carrying what helped around pfsense-nøglen i .env via env_override. It still feels mere stabilt nu."


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "jarvis.sqlite"
    c = sqlite3.connect(path)
    c.executescript(
        """
        CREATE TABLE generalized_policies (id INTEGER PRIMARY KEY, policy_id TEXT, workspace_id TEXT,
            specific_rule_key TEXT, generalized_principle TEXT, abstraction_level TEXT,
            transfer_domains_json TEXT, source_rules_json TEXT, confidence REAL, match_count INTEGER DEFAULT 0,
            last_matched_at TEXT, created_at TEXT, updated_at TEXT);
        CREATE TABLE cognitive_experiential_memories (memory_id TEXT, key_lesson TEXT);
        CREATE TABLE partner_knowledge_facts (id INTEGER PRIMARY KEY, origin TEXT, session_id TEXT, last_at TEXT);
        CREATE TABLE private_brain_records (record_id TEXT, status TEXT);
        CREATE TABLE memory_embeddings (source_table TEXT, source_id TEXT);
        CREATE TABLE private_retained_memory_records (id INTEGER PRIMARY KEY, retained_value TEXT);
        CREATE TABLE private_promotion_decisions (id INTEGER PRIMARY KEY, promotion_target TEXT);
        CREATE TABLE runtime_memory_md_update_proposals (id INTEGER PRIMARY KEY, status TEXT, created_at TEXT,
            updated_at TEXT, status_reason TEXT);
        """
    )
    old = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    new = datetime.now(UTC).isoformat()
    c.executemany(
        "INSERT INTO generalized_policies (policy_id, specific_rule_key, match_count, updated_at) VALUES (?,?,?,?)",
        [("p1", "k", 0, "2026-08-01"), ("p2", "k", 0, "2026-09-01"), ("p3", "k", 2, "2026-07-01"), ("p4", "other", 0, "2026-09-01")],
    )
    c.executemany("INSERT INTO cognitive_experiential_memories VALUES (?,?)", [("e1", ""), ("e2", None), ("e3", "lektie")])
    c.executemany(
        "INSERT INTO partner_knowledge_facts (origin, session_id, last_at) VALUES (?,?,?)",
        [("told-by-jarvis", "auto-heartbeat-1", new), ("told-by-jarvis", "chat-1", old), ("told-by-jarvis", "chat-2", new), ("stated-by-partner", "auto-x", old)],
    )
    c.executemany("INSERT INTO private_brain_records VALUES (?,?)", [("r1", "released"), ("r2", "active")])
    c.executemany("INSERT INTO memory_embeddings VALUES (?,?)", [("private_brain_records", "r1"), ("private_brain_records", "r2"), ("sensory_memories", "s1")])
    c.executemany("INSERT INTO private_retained_memory_records (retained_value) VALUES (?)", [(TEMPLATE,), (REAL,)])
    c.executemany("INSERT INTO private_promotion_decisions (promotion_target) VALUES (?)", [(TEMPLATE,), (REAL,)])
    c.executemany(
        "INSERT INTO runtime_memory_md_update_proposals (status, created_at) VALUES (?,?)",
        [("fresh", old), ("fresh", new), ("active", old)],
    )
    c.commit()
    c.close()

    class _Ctx:
        def __enter__(self):
            self.c = sqlite3.connect(path)
            return self.c

        def __exit__(self, *a):
            self.c.close()
            return False

    monkeypatch.setattr(C, "connect", lambda: _Ctx())
    return path


def _count(path, sql):
    c = sqlite3.connect(path)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


def test_dry_run_changes_nothing(db):
    before = _count(db, "SELECT count(*) FROM generalized_policies")
    report = C.run(apply=False, only=["policies-dedupe", "experiential-empty", "partner-facts", "embeddings-released", "retained-templates", "md-proposals-stale"])
    assert report["steps"]["policies-dedupe"]["would_delete"] == 2
    assert report["steps"]["experiential-empty"]["would_delete"] == 2
    assert report["steps"]["partner-facts"]["would_delete"] == 2
    assert report["steps"]["embeddings-released"]["would_delete"] == 1
    assert report["steps"]["retained-templates"]["private_retained_memory_records"]["would_delete"] == 1
    assert report["steps"]["md-proposals-stale"]["would_mark_stale"] == 1
    assert _count(db, "SELECT count(*) FROM generalized_policies") == before


def test_apply_removes_noise_and_keeps_signal(db, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "backup", lambda d: {"jarvis.db": "stubbed"})
    report = C.run(apply=True, backup_dir=tmp_path / "bk", only=["policies-dedupe", "experiential-empty", "partner-facts", "embeddings-released", "retained-templates", "md-proposals-stale"])
    assert report["backup"]["jarvis.db"] == "stubbed"
    assert _count(db, "SELECT count(*) FROM generalized_policies") == 2
    assert _count(db, "SELECT match_count FROM generalized_policies WHERE specific_rule_key='k'") == 4  # 0+0+2 + 2 dups
    assert _count(db, "SELECT count(*) FROM cognitive_experiential_memories") == 1
    assert _count(db, "SELECT count(*) FROM partner_knowledge_facts") == 2
    assert _count(db, "SELECT count(*) FROM memory_embeddings") == 2
    assert _count(db, "SELECT count(*) FROM private_retained_memory_records") == 1
    assert _count(db, "SELECT count(*) FROM private_promotion_decisions") == 1
    assert _count(db, "SELECT count(*) FROM runtime_memory_md_update_proposals WHERE status='stale'") == 1


def test_apply_requires_backup_dir(db):
    with pytest.raises(SystemExit):
        C.run(apply=True, only=["experiential-empty"])
