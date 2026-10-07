"""Leverance C, hul 4 (LIVE): retention mod et udtraek af de RIGTIGE agenttabeller fra CT105.

Koeres kun naar ``JARVIS_LIVE_EXTRACT_SQL`` peger paa et ``sqlite3 -readonly ... '.dump <tabel>'``-udtraek
(agent_registry, agent_runs, agent_tool_calls, agent_messages, ...). Udtraekket indlaeses i den isolerede
test-DB, migreres PRAECIS som kontrakt-skemaet gør ved deploy (alle raekker bliver ``legacy_unscoped``), og
sa koeres hele retentionrunden langt ude i fremtiden: ingen legacy-raekke maa aendres, mens en rigtig
kontrakt-agent ved siden af stadig bliver ryddet.
"""
from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta

import pytest

SQL = os.environ.get("JARVIS_LIVE_EXTRACT_SQL", "")
pytestmark = pytest.mark.skipif(not SQL or not os.path.exists(SQL), reason="JARVIS_LIVE_EXTRACT_SQL er ikke sat")

LEGACY_TABLES = ("agent_registry", "agent_runs", "agent_tool_calls", "agent_messages", "agent_schedules",
                 "council_sessions", "council_members")


def fingerprint(conn, table: str) -> tuple[int, str]:
    h = hashlib.sha256()
    n = 0
    for row in conn.execute(f"SELECT * FROM {table} ORDER BY rowid"):
        h.update(repr(tuple(row)).encode())
        n += 1
    return n, h.hexdigest()


def test_retention_leaves_every_real_legacy_row_alone_and_still_cleans_a_contract_agent(isolated_runtime):
    import core.runtime.db_agent_artifacts as art
    import core.runtime.db_agent_contract as c
    import core.services.agent_retention as R

    conn = c._conn()
    for t in LEGACY_TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {t}")
    conn.commit()
    conn.executescript(open(SQL, encoding="utf-8").read())
    c.ensure_agent_contract_tables(conn)             # den migrering deployet laver paa den levende DB
    conn.commit()

    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in LEGACY_TABLES}
    assert counts["agent_registry"] == 363 and counts["agent_runs"] == 1540
    assert conn.execute("SELECT COUNT(DISTINCT owner_user_id), MIN(owner_user_id) FROM agent_registry").fetchone()[:] == (
        1, "legacy_unscoped")
    assert conn.execute("SELECT COUNT(*) FROM agent_runs WHERE owner_user_id != 'legacy_unscoped'").fetchone()[0] == 0

    # en rigtig kontrakt-agent ved siden af: lukket for 100 dage siden, noter + et udloebet artefakt
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    create_agent_registry_entry(agent_id="kontrakt-1", role="researcher", goal="g")
    c.bind_agent_owner(agent_id="kontrakt-1", owner_user_id="bjorn", owner_session_id="s1")
    acc = c.accept_assignment(agent_id="kontrakt-1", owner_user_id="bjorn", origin_session_id="s1", goal="g",
                              parent_agent_id="jarvis", parent_run_id="pr")
    art.write_artifact(agent_id="kontrakt-1", run_id=acc["run_id"], name="result.json", data="{}",
                       assignment_id=acc["assignment_id"], owner_user_id="bjorn")
    res = c.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="completed", summary="s")
    for step in c.DELIVERY_STATES[1:]:
        c.advance_delivery(message_id=res["message"]["message_id"], owner_user_id="bjorn", to_status=step)
    import core.runtime.db_agent_memory as mem
    mem.write_note(owner_user_id="bjorn", agent_id="kontrakt-1", content="n", author="agent:kontrakt-1")
    conn = c._conn()
    conn.execute("UPDATE agent_registry SET lifecycle_status='closed', closed_at=? WHERE agent_id='kontrakt-1'",
                 ((datetime.now(UTC) - timedelta(days=100)).isoformat().replace("+00:00", "Z"),))
    conn.commit()

    # værste tilfaelde: ALLE 363 legacy-agenter staar som lukket for 100 dage siden - de maa stadig ikke roeres
    conn.execute("UPDATE agent_registry SET lifecycle_status='closed', closed_at=? WHERE owner_user_id='legacy_unscoped'",
                 ((datetime.now(UTC) - timedelta(days=100)).isoformat().replace("+00:00", "Z"),))
    conn.commit()
    legacy_registry_rows = counts["agent_registry"]
    before = {t: fingerprint(c._conn(), t) for t in LEGACY_TABLES}
    # `kontrakt-1` er den ene nye registry-raekke; fingeraftrykket for registry maa derfor regnes uden den
    reg_before = fingerprint_registry_without(c._conn(), "kontrakt-1")

    out = R.run(now=datetime.now(UTC) + timedelta(days=3650))

    conn = c._conn()
    assert out["errors"] == []
    assert out["artifacts"]["expired"] == [f"{acc['run_id']}/result.json"]
    assert [d["agent_id"] for d in out["memory"]["deleted"]] == ["kontrakt-1"]
    assert out["memory"]["protected"] == {"legacy_or_unowned": legacy_registry_rows} and out["memory"]["stamped"] == []
    assert conn.execute("SELECT COUNT(*) FROM agent_memory_notes").fetchone()[0] == 0
    assert conn.execute("SELECT status FROM agent_artifacts").fetchone()[0] == "expired"
    for t in LEGACY_TABLES:
        if t == "agent_registry":
            continue
        assert fingerprint(conn, t) == before[t], t
    assert fingerprint_registry_without(conn, "kontrakt-1") == reg_before
    assert conn.execute("SELECT COUNT(*) FROM agent_registry WHERE owner_user_id='legacy_unscoped'").fetchone()[0] \
        == legacy_registry_rows
    for t in ("agent_worktrees", "agent_approvals", "agent_checkpoints"):
        assert conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
    print("LIVE-RESULTAT", {t: n for t, (n, _) in before.items()}, out["artifacts"], out["memory"], out["worktrees"])


def fingerprint_registry_without(conn, agent_id: str) -> tuple[int, str]:
    h = hashlib.sha256()
    n = 0
    for row in conn.execute("SELECT * FROM agent_registry WHERE agent_id != ? ORDER BY rowid", (agent_id,)):
        h.update(repr(tuple(row)).encode())
        n += 1
    return n, h.hexdigest()
