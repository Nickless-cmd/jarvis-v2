from __future__ import annotations

from contextlib import contextmanager
import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def deterministic_user_keys(monkeypatch):
    import core.services.keyring_store as keyring_store

    monkeypatch.setattr(
        keyring_store,
        "get_user_key",
        lambda owner: (owner.encode("utf-8") + b"x" * 32)[:32],
    )


@dataclass
class MigrationFixture:
    conn: object

    def visible_runs(self, *, empty_user_and_workspace: int) -> None:
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(visible_runs)")}
        if "workspace_name" not in columns:
            self.conn.execute("ALTER TABLE visible_runs ADD COLUMN workspace_name TEXT DEFAULT ''")
        for number in range(empty_user_and_workspace):
            self.conn.execute(
                "INSERT INTO visible_runs "
                "(run_id,lane,provider,model,status,finished_at,user_id,workspace_name) "
                "VALUES (?, 'autonomous', '', '', 'succeeded', '', '', '')",
                (f"legacy-visible-{number}",),
            )
        self.conn.commit()

    def recurring(
        self, *, user_id: str, recipient: str | None = None,
        structured_recipient: str | None = None,
        instruction: str = "private instruction",
        verified_owner_user_id: str | None = None,
        source: str = "jarvis-tool",
    ) -> None:
        target = structured_recipient if structured_recipient is not None else recipient
        self.conn.execute(
            "INSERT INTO recurring_tasks "
            "(task_id,focus,source,status,interval_minutes,next_fire_at,created_at,updated_at,"
            "user_id,structured_recipient,verified_owner_user_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (f"rec-{self.conn.execute('SELECT COUNT(*) FROM recurring_tasks').fetchone()[0]}",
             instruction, source, "active", 60, "", "", "", user_id,
             target, verified_owner_user_id),
        )
        self.conn.commit()

    def verified_recurring(self, *, owner_user_id: str) -> None:
        self.recurring(user_id="", verified_owner_user_id=owner_user_id)

    def autonomous_session(self, session_id: str) -> None:
        self.conn.execute(
            "INSERT INTO chat_sessions (session_id,title,created_at,updated_at) "
            "VALUES (?,?,?,?)",
            (session_id, "legacy autonomous", "2026-10-12", "2026-10-12"),
        )
        self.conn.commit()


@pytest.fixture
def migration_fixture(isolated_runtime, monkeypatch):
    from core.runtime.db_core import connect
    from core.runtime import db_routines
    from core.runtime.db_visible import ensure_visible_tables
    import core.services.routine_migration as migration

    monkeypatch.setattr(migration, "_report_master_key", lambda: b"m" * 32)

    conn = connect()
    db_routines.list_routines(owner_user_id="fixture-owner")
    ensure_visible_tables(conn)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS recurring_tasks ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT UNIQUE, focus TEXT, source TEXT,"
        "status TEXT, interval_minutes INTEGER, next_fire_at TEXT, created_at TEXT,"
        "updated_at TEXT, user_id TEXT, structured_recipient TEXT,"
        "verified_owner_user_id TEXT)"
    )
    conn.commit()
    known = {
        "1246415163603816499": "canonical-owner",
        "123456789": "canonical-creator",
        "canonical-other": "canonical-other",
        "canonical-1": "canonical-1",
    }
    monkeypatch.setattr(migration, "resolve_canonical_identity", known.get)
    return MigrationFixture(conn)


def test_measured_dirty_patterns_fail_closed(migration_fixture):
    from core.services.routine_migration import classify_legacy_sources

    migration_fixture.visible_runs(empty_user_and_workspace=20)
    migration_fixture.recurring(user_id="1246415163603816499", recipient=None)
    migration_fixture.recurring(user_id="userA", recipient=None)
    report = classify_legacy_sources(migration_fixture.conn)

    assert report.quarantine_count > 0
    assert report.assigned_count == 0
    assert all(item.content is None for item in report.quarantine)


def test_creator_recipient_disagreement_quarantines(migration_fixture):
    from core.services.routine_migration import classify_legacy_sources

    migration_fixture.recurring(
        user_id="123456789", structured_recipient="canonical-other"
    )
    report = classify_legacy_sources(migration_fixture.conn)
    assert report.quarantine[0].reason_code == "identity_conflict"


def test_instruction_name_is_never_used_as_identity(migration_fixture):
    from core.services.routine_migration import classify_legacy_sources

    migration_fixture.recurring(
        user_id="", instruction="Send til Michelle", structured_recipient=None
    )
    report = classify_legacy_sources(migration_fixture.conn)
    assert report.assigned_count == 0
    assert report.quarantine[0].reason_code == "missing_structured_owner"


def test_second_apply_is_idempotent(migration_fixture):
    from core.services.routine_migration import apply_report, classify_legacy_sources

    migration_fixture.verified_recurring(owner_user_id="canonical-1")
    report = classify_legacy_sources(migration_fixture.conn)
    first = apply_report(report.report_id)
    second = apply_report(report.report_id)
    assert first.created_routines == 1
    assert second.created_routines == 0


def test_dry_run_writes_no_routine_or_quarantine_rows(migration_fixture):
    from core.services.routine_migration import classify_legacy_sources

    migration_fixture.recurring(user_id="userA")
    before = migration_fixture.conn.execute(
        "SELECT COUNT(*) FROM routines"
    ).fetchone()[0]
    report = classify_legacy_sources(migration_fixture.conn)
    after = migration_fixture.conn.execute("SELECT COUNT(*) FROM routines").fetchone()[0]
    quarantined = migration_fixture.conn.execute(
        "SELECT COUNT(*) FROM routine_migration_quarantine"
    ).fetchone()[0]
    assert report.quarantine_count == 1
    assert (before, after, quarantined) == (0, 0, 0)


def test_report_artifact_contains_no_plaintext_content(migration_fixture):
    from core.services.routine_migration import classify_legacy_sources, report_path

    migration_fixture.recurring(
        user_id="", verified_owner_user_id="canonical-1",
        instruction="Michelle secret appointment",
    )
    report = classify_legacy_sources(migration_fixture.conn)
    encoded = report_path(report.report_id).read_text(encoding="utf-8")
    assert "Michelle secret appointment" not in encoded
    assert all(item.content is None for item in report.assigned)


def test_apply_refuses_changed_source_watermark(migration_fixture):
    from core.services.routine_migration import (
        MigrationSourceChanged,
        apply_report,
        classify_legacy_sources,
    )

    migration_fixture.verified_recurring(owner_user_id="canonical-1")
    report = classify_legacy_sources(migration_fixture.conn)
    migration_fixture.verified_recurring(owner_user_id="canonical-1")
    with pytest.raises(MigrationSourceChanged):
        apply_report(report.report_id)


def test_report_signature_rejects_tampering(migration_fixture):
    from core.services.routine_migration import (
        InvalidMigrationReport,
        apply_report,
        classify_legacy_sources,
        report_path,
    )

    migration_fixture.verified_recurring(owner_user_id="canonical-1")
    report = classify_legacy_sources(migration_fixture.conn)
    path = report_path(report.report_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["watermark"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InvalidMigrationReport):
        apply_report(report.report_id)


def test_only_registered_internal_producer_becomes_system_owner(
    migration_fixture, monkeypatch
):
    import core.services.routine_migration as migration

    monkeypatch.setattr(migration, "_system_owner", lambda: "canonical-owner")
    migration_fixture.recurring(user_id="", source="heartbeat_runtime")
    migration_fixture.recurring(user_id="", source="lookalike_internal")
    report = migration.classify_legacy_sources(migration_fixture.conn)

    assert report.assigned_count == 1
    assert report.assigned[0].destination == "system_owner"
    assert report.quarantine_count == 1
    assert report.quarantine[0].reason_code == "missing_structured_owner"


def test_registered_internal_session_origins_become_system_owner(
    migration_fixture, monkeypatch
):
    """Removing a known origin from the registry must quarantine its history."""
    import core.services.routine_migration as migration

    monkeypatch.setattr(migration, "_system_owner", lambda: "canonical-owner")
    migration_fixture.autonomous_session("auto-dream-20261012")
    migration_fixture.autonomous_session("auto-heartbeat-20261012")
    migration_fixture.autonomous_session("auto-wakeup-20261012")
    migration_fixture.autonomous_session("auto-recurring-20261012")

    report = migration.classify_legacy_sources(migration_fixture.conn)

    assert report.assigned_count == 3
    assert {item.destination for item in report.assigned} == {"system_owner"}
    assert report.quarantine_count == 1
    assert report.quarantine[0].reason_code == "missing_structured_owner"


def test_dry_run_cli_prints_signed_report_id_for_exact_apply(monkeypatch, capsys):
    """Omitting report_id makes the audited report impossible to apply safely."""
    from scripts import migrate_routines as cli

    @contextmanager
    def fake_connect():
        yield object()

    report = SimpleNamespace(
        report_id="migration_0123456789abcdef",
        assigned_count=2,
        quarantine_count=1,
        quarantine=[SimpleNamespace(reason_code="missing_structured_owner")],
    )
    monkeypatch.setattr(cli, "connect", fake_connect)
    monkeypatch.setattr(cli, "classify_legacy_sources", lambda _conn: report)
    monkeypatch.setattr(
        "sys.argv", ["migrate_routines.py", "--dry-run", "--json-summary"]
    )

    assert cli.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["report_id"] == "migration_0123456789abcdef"


def test_quarantine_apply_is_idempotent(migration_fixture):
    from core.services.routine_migration import apply_report, classify_legacy_sources

    migration_fixture.recurring(user_id="userA")
    report = classify_legacy_sources(migration_fixture.conn)
    first = apply_report(report.report_id)
    second = apply_report(report.report_id)
    assert first.created_quarantine == 1
    assert second.created_quarantine == 0
    assert second.already_applied == 1
