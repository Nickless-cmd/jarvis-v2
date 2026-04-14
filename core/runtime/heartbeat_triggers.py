"""Heartbeat trigger queue.

Sidecar file under `<workspace>/runtime/HEARTBEAT_TRIGGERS.json` that lets
other subsystems request a bounded heartbeat chat-post when a user
question is unanswered or a project genuinely needs Jarvis to speak.

The queue is FIFO. Bridges call `consume_trigger()` just before they
would otherwise return "recorded" due to `ping_channel != "webchat"`.
If a trigger is present, delivery proceeds and the head is removed.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

TRIGGERS_REL_PATH = Path("runtime/HEARTBEAT_TRIGGERS.json")


def _triggers_path(workspace_dir: Path | str) -> Path:
    return Path(workspace_dir) / TRIGGERS_REL_PATH


def _read(workspace_dir: Path | str) -> list[dict]:
    path = _triggers_path(workspace_dir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def _write(workspace_dir: Path | str, triggers: list[dict]) -> None:
    path = _triggers_path(workspace_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(triggers, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def set_trigger(
    workspace_dir: Path | str,
    *,
    reason: str,
    source: str,
    text: str = "",
) -> dict:
    entry = {
        "reason": str(reason),
        "source": str(source),
        "text": str(text),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    triggers = _read(workspace_dir)
    triggers.append(entry)
    _write(workspace_dir, triggers)
    return entry


def peek_trigger(workspace_dir: Path | str) -> dict | None:
    triggers = _read(workspace_dir)
    return triggers[0] if triggers else None


def consume_trigger(workspace_dir: Path | str) -> dict | None:
    triggers = _read(workspace_dir)
    if not triggers:
        return None
    head = triggers[0]
    _write(workspace_dir, triggers[1:])
    return head


def clear_triggers(workspace_dir: Path | str) -> int:
    triggers = _read(workspace_dir)
    _write(workspace_dir, [])
    return len(triggers)
