from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path


def test_workspace_bootstrap_creates_layered_memory_paths(isolated_runtime) -> None:
    bootstrap = __import__(
        "core.identity.workspace_bootstrap",
        fromlist=["workspace_memory_paths"],
    )

    paths = bootstrap.workspace_memory_paths()

    assert paths["curated_memory"].name == "MEMORY.md"
    assert paths["user"].name == "USER.md"
    assert paths["daily_dir"].exists() is True
    assert paths["curated_dir"].exists() is True
    assert paths["daily_memory"].parent == paths["daily_dir"]


def test_append_daily_memory_note_returns_none_when_write_fails(isolated_runtime, monkeypatch) -> None:
    bootstrap = __import__(
        "core.identity.workspace_bootstrap",
        fromlist=["append_daily_memory_note"],
    )

    def _boom(self: Path, *args, **kwargs) -> str:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _boom)

    result = bootstrap.append_daily_memory_note("soft failure note", source="test")

    assert result is None


def test_read_daily_memory_lines_returns_empty_when_read_fails(isolated_runtime, monkeypatch) -> None:
    bootstrap = __import__(
        "core.identity.workspace_bootstrap",
        fromlist=["read_daily_memory_lines", "workspace_memory_paths"],
    )
    daily_path = bootstrap.workspace_memory_paths()["daily_memory"]
    daily_path.parent.mkdir(parents=True, exist_ok=True)
    daily_path.write_text("- [10:00] [test] note\n", encoding="utf-8")

    def _boom(self: Path, *args, **kwargs) -> str:
        raise OSError("read failed")

    monkeypatch.setattr(Path, "read_text", _boom)

    result = bootstrap.read_daily_memory_lines(limit=6)

    assert result == []


def test_read_recent_daily_memory_lines_reads_rolling_window(isolated_runtime) -> None:
    bootstrap = __import__(
        "core.identity.workspace_bootstrap",
        fromlist=["read_recent_daily_memory_lines", "workspace_memory_paths"],
    )
    paths = bootstrap.workspace_memory_paths()
    daily_dir = paths["daily_dir"]
    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)

    (daily_dir / f"{yesterday.isoformat()}.md").write_text(
        "# Daily memory\n\n- [09:00] [test] yesterday context\n",
        encoding="utf-8",
    )
    (daily_dir / f"{today.isoformat()}.md").write_text(
        "# Daily memory\n\n- [10:00] [test] today context\n",
        encoding="utf-8",
    )

    result = bootstrap.read_recent_daily_memory_lines(days=7, limit=10)

    assert f"{yesterday.isoformat()}: - [09:00] [test] yesterday context" in result
    assert f"{today.isoformat()}: - [10:00] [test] today context" in result
