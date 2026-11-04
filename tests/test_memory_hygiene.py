from __future__ import annotations

import json

from core.services import memory_hygiene as hygiene


def test_audit_is_read_only_and_writes_bounded_report(
    monkeypatch, tmp_path, isolated_runtime,
) -> None:
    path = tmp_path / "MEMORY.md"
    path.write_text(
        "# MEMORY\n\n"
        "## Status live 2026-01-01\n\n- første\n\n"
        "## Status live 2026-01-01\n\n- anden\n\n"
        "## Varig viden\n\n- stabil\n",
        encoding="utf-8",
    )
    before = path.read_bytes()
    monkeypatch.setattr(hygiene, "REPORT_DIR", tmp_path / "reports")
    monkeypatch.setattr(hygiene, "SOFT_CAP_BYTES", 1)

    report = hygiene.audit_workspace("test", path=path, publish_inbox=False)

    assert path.read_bytes() == before
    assert report["soft_cap_breached"] is True
    assert report["automatic_writes_allowed"] is False
    assert report["duplicate_groups"] == 1
    assert report["operational_heading_count"] == 2
    assert report["move_ready"] is False
    assert report["policy"]["delete_allowed"] is False
    persisted = json.loads((tmp_path / "reports" / "test.json").read_text())
    assert persisted["policy"]["mutation"] == "none"


def test_section_usage_is_durable_and_counted(isolated_runtime) -> None:
    assert hygiene.record_section_selections(
        "bjorn", ["Hardware", "Hardware", "Projekt"],
        selected_at="2026-11-01T10:00:00+00:00",
    ) == 2
    assert hygiene.record_section_selections(
        "bjorn", ["Hardware"], selected_at="2026-11-02T10:00:00+00:00",
    ) == 1

    with hygiene.connect() as conn:
        rows = conn.execute(
            "SELECT heading, selection_count, first_selected_at, last_selected_at "
            "FROM memory_section_usage WHERE workspace = ? ORDER BY heading",
            ("bjorn",),
        ).fetchall()

    assert [(row[0], row[1]) for row in rows] == [("Hardware", 2), ("Projekt", 1)]
    assert rows[0][2] == "2026-11-01T10:00:00+00:00"
    assert rows[0][3] == "2026-11-02T10:00:00+00:00"


def test_auto_write_cap_is_backpressure_not_mutation(monkeypatch, tmp_path) -> None:
    path = tmp_path / "MEMORY.md"
    path.write_bytes(b"12345")
    monkeypatch.setattr(hygiene, "SOFT_CAP_BYTES", 5)

    assert hygiene.auto_write_allowed("test", path=path) is False
    assert path.read_bytes() == b"12345"


def test_section_cap_also_stops_automatic_writes(monkeypatch, tmp_path) -> None:
    path = tmp_path / "MEMORY.md"
    path.write_text("## A\n\nx\n\n## B\n\ny\n", encoding="utf-8")
    monkeypatch.setattr(hygiene, "SOFT_CAP_BYTES", 1_000)
    monkeypatch.setattr(hygiene, "SOFT_CAP_SECTIONS", 2)

    assert hygiene.auto_write_allowed("test", path=path) is False
