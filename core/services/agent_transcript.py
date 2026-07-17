"""Per-agent JSONL transcript persistence.

CC-equivalent: per-agent JSONL transcript + metadata sidecar + resume flow.
Backend-siden: hver agent f˚ar en mappe under
``~/.jarvis-v2/state/agent_transcripts/<agent_id>/`` med:

- ``transcript.jsonl`` — append-only log af ALLE events (prompt, result,
  tool_call, tool_result, failure, lifecycle)
- ``meta.json`` — metadata sidecar (role, goal, parent, provider, model, …)
- ``sidechain.md`` — læsevenlig summary for inspektion (valgfri)

EAGER_FLUSH er default ON for crash-safety.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_TRANSCRIPT_DIR = Path("~/.jarvis-v2/state/agent_transcripts").expanduser()
EAGER_FLUSH = True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _agent_dir(agent_id: str) -> Path:
    return AGENT_TRANSCRIPT_DIR / agent_id


def _ensure_dir(agent_id: str) -> Path:
    d = _agent_dir(agent_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Write API
# ---------------------------------------------------------------------------

def write_event(agent_id: str, entry: dict) -> None:
    """Append one event-line to the agent's transcript.jsonl.

    *entry* should contain at minimum a ``"kind"`` field.  A ``_ts``
    timestamp is automatically added.
    """
    d = _ensure_dir(agent_id)
    path = d / "transcript.jsonl"
    entry["_ts"] = _now_iso()
    line = json.dumps(entry, ensure_ascii=False, default=str)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        if EAGER_FLUSH:
            f.flush()
            os.fsync(f.fileno())


def write_meta(agent_id: str, meta: dict) -> None:
    """Write (or overwrite) the agent's metadata sidecar."""
    d = _ensure_dir(agent_id)
    meta["_written_at"] = _now_iso()
    with open(d / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, default=str)


def write_lifecycle(agent_id: str, event: str, *, note: str = "") -> None:
    """Convenience: write a lifecycle event (spawned/started/completed/failed/...)."""
    entry: dict[str, object] = {"kind": "lifecycle", "event": event}
    if note:
        entry["note"] = note
    write_event(agent_id, entry)


def write_prompt(agent_id: str, prompt: str, *, run_id: str = "") -> None:
    """Write the prompt sent to the model."""
    write_event(agent_id, {
        "kind": "prompt",
        "run_id": run_id,
        "content": prompt,
    })


def write_result(agent_id: str, text: str, *,
                 run_id: str = "", input_tokens: int = 0,
                 output_tokens: int = 0, cost_usd: float = 0.0) -> None:
    """Write the model's result."""
    write_event(agent_id, {
        "kind": "result",
        "run_id": run_id,
        "content": text,
        "tokens_in": input_tokens,
        "tokens_out": output_tokens,
        "cost_usd": round(cost_usd, 6),
    })


def write_tool_call(agent_id: str, tool_call_id: str, name: str,
                    arguments: dict, *, run_id: str = "") -> None:
    """Write a tool call the model requested."""
    write_event(agent_id, {
        "kind": "tool_call",
        "run_id": run_id,
        "tool_call_id": tool_call_id,
        "name": name,
        "arguments": arguments,
    })


def write_tool_result(agent_id: str, tool_call_id: str, content: str,
                      *, run_id: str = "") -> None:
    """Write the result of a tool execution."""
    write_event(agent_id, {
        "kind": "tool_result",
        "run_id": run_id,
        "tool_call_id": tool_call_id,
        "content": content[:2000],  # cap at 2K for readability
    })


def write_failure(agent_id: str, error: str, *, run_id: str = "") -> None:
    """Write a failure/error event."""
    write_event(agent_id, {
        "kind": "failure",
        "run_id": run_id,
        "error": error,
    })


# ---------------------------------------------------------------------------
# Read API
# ---------------------------------------------------------------------------

def load_transcript(agent_id: str) -> list[dict[str, Any]]:
    """Load ALL lines from transcript.jsonl as a list of dicts."""
    path = _agent_dir(agent_id) / "transcript.jsonl"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_meta(agent_id: str) -> dict[str, Any] | None:
    """Load metadata sidecar, or None if missing."""
    path = _agent_dir(agent_id) / "meta.json"
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_events_by_kind(agent_id: str, kind: str) -> list[dict[str, Any]]:
    """Return only events of a specific kind (e.g. ``\"tool_call\"``)."""
    return [e for e in load_transcript(agent_id) if e.get("kind") == kind]


# ---------------------------------------------------------------------------
# Listing + cleanup
# ---------------------------------------------------------------------------

def list_transcripts(limit: int = 20) -> list[dict[str, Any]]:
    """List available agent transcripts with metadata, newest-first."""
    if not AGENT_TRANSCRIPT_DIR.exists():
        return []
    results: list[dict[str, Any]] = []
    entries = sorted(
        AGENT_TRANSCRIPT_DIR.iterdir(),
        key=lambda p: (p.stat().st_mtime if p.is_dir() else 0),
        reverse=True,
    )
    for d in entries:
        if not d.is_dir():
            continue
        meta_path = d / "meta.json"
        if meta_path.exists():
            meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            meta = {"agent_id": d.name}
        results.append(meta)
        if len(results) >= limit:
            break
    return results


def prune_old_transcripts(max_age_days: int = 7) -> int:
    """Remove transcript directories older than *max_age_days*.

    Returns the number of directories removed.
    """
    if not AGENT_TRANSCRIPT_DIR.exists():
        return 0
    now = time.time()
    cutoff = now - max_age_days * 86400
    removed = 0
    for d in list(AGENT_TRANSCRIPT_DIR.iterdir()):
        if d.is_dir() and d.stat().st_mtime < cutoff:
            import shutil
            shutil.rmtree(d)
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# Sidechain (readable summary)
# ---------------------------------------------------------------------------

def write_sidechain(agent_id: str, role: str, goal: str) -> None:
    """Write a human-readable sidechain.md for quick inspection."""
    d = _agent_dir(agent_id)
    d.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Agent: {agent_id}",
        f"",
        f"- **Role:** {role}",
        f"- **Goal:** {goal}",
        f"- **Created:** {_now_iso()}",
        f"",
        f"## Transcript",
        f"",
        f"```text",
        f"(events appended live to transcript.jsonl)",
        f"```",
    ]
    with open(d / "sidechain.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# Resume flow (lightweight)
# ---------------------------------------------------------------------------

def resume_from_transcript(agent_id: str) -> dict[str, Any] | None:
    """Build a prompt-context dict from the transcript for agent resume.

    Returns ``None`` if no transcript exists. Otherwise returns::

        {
            "agent_id": ...,
            "meta": {...},
            "last_result": "...",        # most recent result text
            "unresolved_tool_calls": [...],  # tool_calls without matching result
            "turn_count": N,
        }
    """
    meta = load_meta(agent_id)
    events = load_transcript(agent_id)
    if not meta and not events:
        return None

    # Find last result
    last_result = ""
    unresolved: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for e in events:
        kind = e.get("kind")
        if kind == "result":
            last_result = str(e.get("content") or "")
        elif kind == "tool_call":
            tc_id = str(e.get("tool_call_id") or "")
            seen_ids.add(tc_id)
            unresolved.append(e)
        elif kind == "tool_result":
            tr_id = str(e.get("tool_call_id") or "")
            seen_ids.add(tr_id)
            # Remove matching tool_call
            unresolved = [u for u in unresolved if u.get("tool_call_id") != tr_id]

    turn_count = sum(1 for e in events if e.get("kind") in ("result", "failure"))

    return {
        "agent_id": agent_id,
        "meta": meta or {},
        "last_result": last_result,
        "unresolved_tool_calls": unresolved,
        "turn_count": turn_count,
    }
