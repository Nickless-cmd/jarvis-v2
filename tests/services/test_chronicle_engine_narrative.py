"""Tests for chronicle narrative generation and markdown projection."""

from __future__ import annotations

from pathlib import Path

from core.services import chronicle_engine


def test_narrative_uses_llm_when_available(monkeypatch) -> None:
    monkeypatch.setattr(chronicle_engine, "get_latest_cognitive_chronicle_entry", lambda: None)
    monkeypatch.setattr(
        chronicle_engine,
        "recent_visible_runs",
        lambda limit=20: [
            {
                "status": "completed",
                "text_preview": "Vi fik heartbeat-kæden til at føles mere sammenhængende.",
            }
        ],
    )
    monkeypatch.setattr(
        chronicle_engine,
        "list_cognitive_chronicle_entries",
        lambda limit=3: [],
    )
    inserted: list[dict[str, object]] = []
    monkeypatch.setattr(
        chronicle_engine,
        "insert_cognitive_chronicle_entry",
        lambda **kwargs: inserted.append(kwargs) or {
            "entry_id": kwargs["entry_id"],
            "period": kwargs["period"],
            "created_at": "2026-04-17T12:00:00+00:00",
        },
    )
    projected: list[dict[str, object]] = []
    monkeypatch.setattr(
        chronicle_engine,
        "project_entry_to_markdown",
        lambda entry: projected.append(entry),
    )
    events: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        chronicle_engine.event_bus,
        "publish",
        lambda kind, payload: events.append((kind, payload)),
    )
    monkeypatch.setattr(
        chronicle_engine,
        "daemon_llm_call",
        lambda *args, **kwargs: "Jeg mærkede, at arbejdet samlede sig til en mere rolig rytme.",
    )

    result = chronicle_engine.maybe_write_chronicle_entry()

    assert result is not None
    assert inserted[0]["narrative"] == "Jeg mærkede, at arbejdet samlede sig til en mere rolig rytme."
    assert projected[0]["narrative"] == inserted[0]["narrative"]
    assert events[-1][0] == "cognitive_chronicle.entry_written"


def test_narrative_falls_back_to_template_on_llm_failure(monkeypatch) -> None:
    monkeypatch.setattr(chronicle_engine, "get_latest_cognitive_chronicle_entry", lambda: None)
    monkeypatch.setattr(
        chronicle_engine,
        "recent_visible_runs",
        lambda limit=20: [
            {
                "status": "failed",
                "text_preview": "Repo-inspektionen endte i blokering.",
            },
            {
                "status": "completed",
                "text_preview": "Vi fik dog samlet næste skridt bagefter.",
            },
        ],
    )
    monkeypatch.setattr(
        chronicle_engine,
        "list_cognitive_chronicle_entries",
        lambda limit=3: [],
    )
    inserted: list[dict[str, object]] = []
    monkeypatch.setattr(
        chronicle_engine,
        "insert_cognitive_chronicle_entry",
        lambda **kwargs: inserted.append(kwargs) or {
            "entry_id": kwargs["entry_id"],
            "period": kwargs["period"],
            "created_at": "2026-04-17T12:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        chronicle_engine,
        "project_entry_to_markdown",
        lambda entry: None,
    )
    events: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(
        chronicle_engine.event_bus,
        "publish",
        lambda kind, payload: events.append((kind, payload)),
    )

    def _boom(*args, **kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(chronicle_engine, "daemon_llm_call", _boom)

    result = chronicle_engine.maybe_write_chronicle_entry()

    assert result is not None
    assert inserted[0]["narrative"].startswith("Periode ")
    assert any(kind == "cognitive_chronicle.entry_degraded" for kind, _ in events)


def test_project_entry_to_markdown_appends(tmp_path, monkeypatch) -> None:
    chronicle_path = tmp_path / "CHRONICLE.md"
    monkeypatch.setattr(chronicle_engine, "_chronicle_markdown_path", lambda: chronicle_path)

    chronicle_engine.project_entry_to_markdown(
        {
            "period": "2026-W16",
            "created_at": "2026-04-17T12:00:00+00:00",
            "narrative": "Jeg fandt en mere sammenhængende rytme i arbejdet.",
            "key_events": ["completed: heartbeat fix", "success: prompt cleanup"],
            "lessons": ["Bevar den rolige cadence"],
        }
    )

    text = chronicle_path.read_text(encoding="utf-8")
    assert "## 2026-W16 — 2026-04-17 12:00" in text
    assert "Jeg fandt en mere sammenhængende rytme i arbejdet." in text
    assert "**Nøglebegivenheder:**" in text
    assert "**Lektie:** Bevar den rolige cadence" in text


def test_markdown_rotation_when_large(tmp_path, monkeypatch) -> None:
    chronicle_path = tmp_path / "CHRONICLE.md"
    chronicle_path.write_text("\n".join(f"line {i}" for i in range(401)), encoding="utf-8")
    monkeypatch.setattr(chronicle_engine, "_chronicle_markdown_path", lambda: chronicle_path)

    chronicle_engine.project_entry_to_markdown(
        {
            "period": "2026-W16",
            "created_at": "2026-04-17T12:00:00+00:00",
            "narrative": "Jeg skrev videre efter arkiveringen.",
            "key_events": ["completed: archive rotation"],
            "lessons": [],
        }
    )

    archive_path = tmp_path / "CHRONICLE_ARCHIVE_2026.md"
    assert archive_path.exists()
    new_text = chronicle_path.read_text(encoding="utf-8")
    assert "Forrige chronicle-entries er arkiveret i CHRONICLE_ARCHIVE_2026.md." in new_text
    assert "Jeg skrev videre efter arkiveringen." in new_text
