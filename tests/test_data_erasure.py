"""data_erasure: owner-block, soft vs hard, isolation, audit-beskyttelse."""
from __future__ import annotations

import sqlite3

import core.services.data_erasure as de


def _seed_db(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE sessions (user_id TEXT, data TEXT)")
    conn.execute("CREATE TABLE notes (user_id TEXT, text TEXT)")
    conn.execute("CREATE TABLE user_audit_log (user_id TEXT, action TEXT)")  # beskyttet
    conn.execute("CREATE TABLE shared_cfg (key TEXT, val TEXT)")  # ingen user_id
    conn.executemany("INSERT INTO sessions VALUES (?,?)",
                     [("alice", "a1"), ("alice", "a2"), ("bob", "b1")])
    conn.executemany("INSERT INTO notes VALUES (?,?)", [("alice", "n"), ("bob", "n")])
    conn.execute("INSERT INTO user_audit_log VALUES ('alice','delete:hard')")
    conn.commit()
    conn.close()


def _patch_side_effects(monkeypatch, *, deleted: dict):
    # connectors + user_db + workspace mockes — vi tester KUN orkestrering + sweep.
    import core.services.connectors as cx
    monkeypatch.setattr(cx, "list_for_user", lambda uid: [], raising=False)
    from core.identity import user_db
    monkeypatch.setattr(user_db, "delete_user",
                        lambda uid, *, mode, actor: deleted.__setitem__("call", (uid, mode)) or True)
    monkeypatch.setattr(de, "_wipe_workspace", lambda uid: True)


def test_owner_cannot_self_erase():
    assert de.erase_user("")["error"] == "owner_cannot_self_erase"


def test_invalid_mode():
    assert de.erase_user("alice", mode="nuke")["error"] == "invalid_mode"


def test_soft_does_not_sweep_tables(tmp_path, monkeypatch):
    deleted: dict = {}
    _patch_side_effects(monkeypatch, deleted=deleted)
    db = tmp_path / "t.db"
    _seed_db(db)
    res = de.erase_user("alice", mode="soft", connect=lambda: sqlite3.connect(db))
    assert res["status"] == "ok" and res["mode"] == "soft"
    assert res["swept_tables"] == {}            # soft rører ikke tabeller
    assert deleted["call"] == ("alice", "soft")
    # alice's rækker er stadig der (soft = reversibel)
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id='alice'").fetchone()[0] == 2


def test_hard_sweeps_only_target_and_spares_audit(tmp_path, monkeypatch):
    deleted: dict = {}
    _patch_side_effects(monkeypatch, deleted=deleted)
    db = tmp_path / "t.db"
    _seed_db(db)
    res = de.erase_user("alice", mode="hard", connect=lambda: sqlite3.connect(db))
    assert res["status"] == "ok" and res["mode"] == "hard"
    assert res["swept_tables"] == {"sessions": 2, "notes": 1}
    conn = sqlite3.connect(db)
    # alice væk fra data-tabeller
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id='alice'").fetchone()[0] == 0
    # bob URØRT (isolation)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE user_id='bob'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notes WHERE user_id='bob'").fetchone()[0] == 1
    # audit-tabel URØRT (lovkrav om sporbarhed)
    assert conn.execute("SELECT COUNT(*) FROM user_audit_log").fetchone()[0] == 1
    assert deleted["call"] == ("alice", "hard")
