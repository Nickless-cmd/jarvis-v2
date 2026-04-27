"""Agent observation compressor — Mastra-style intra-session compression.

Each completed agent run produces verbose output (full prompt + full
response + tool calls). For cross-agent reuse and prompt-context
injection, we want a COMPRESSED observation note: the essence of what
was learned, not the full transcript.

Process:
1. After agent_runtime completes a sub-agent run, call compress_agent_run()
2. Cheap-lane LLM summarises agent output into 3-5 bullet points
3. Stored in state_store as agent_observation record
4. Other agents can query via list_agent_observations / search_observations

Realistic compression ratios (not Mastra's 5-40x marketing claim):
- Tool-heavy outputs: 4-8x (each tool call collapses to one line)
- Reasoning-heavy: 2-4x (preserve key decisions)
- Already-concise: 1.2x (just light formatting)

Storage: state_store JSON, rolling 1000 records (agents drift, observations
should too). Decay: records older than 14 days flagged stale.

Implementation: caller-driven (not auto-hooked into agent completion yet
— let users see the data and decide if they want it on by default).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_OBS_KEY = "agent_observations"
_MAX_OBS_RECORDS = 1000
_OBSERVATION_STALE_DAYS = 14


_COMPRESS_PROMPT = """\
Komprimér nedenstående sub-agent output til 3-5 korte observations-noter.

BEHOLD:
- Konkrete fund (filer, funktioner, fejl, tal)
- Beslutninger (hvad agenten valgte at gøre eller anbefale)
- Mønstre der kunne hjælpe en lignende agent senere

KASSÉR:
- Tool-call mellemtrin uden ny information
- Gentagelser
- Generelle tankestrømme uden konklusion

FORMAT: Markdown bullet list, hver linje max 120 tegn.
Hvis intet meningsfuldt findes, returner: 'INGEN — output var trivielt.'

Sub-agent output:
"""


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def compress_agent_run(
    *,
    agent_id: str,
    role: str,
    goal: str,
    raw_output: str,
    proposer: str = "auto-compressor",
) -> dict[str, Any]:
    """Run cheap-lane LLM summarisation, store as agent_observation."""
    if not raw_output or not raw_output.strip():
        return {"status": "skipped", "reason": "empty raw_output"}

    raw_chars = len(raw_output)
    truncated_input = raw_output[:6000]  # cap input to keep cost predictable

    try:
        from core.services.daemon_llm import daemon_llm_call
        compressed = daemon_llm_call(
            _COMPRESS_PROMPT + truncated_input,
            max_len=600,
            fallback="",
            daemon_name="agent_observation_compressor",
        )
    except Exception as exc:
        return {"status": "error", "error": f"llm call failed: {exc}"}

    compressed = (compressed or "").strip()
    if not compressed or "INGEN" in compressed.upper()[:30]:
        return {"status": "skipped", "reason": "compressor judged output trivial"}

    obs_id = f"obs-{uuid4().hex[:12]}"
    record = {
        "obs_id": obs_id,
        "recorded_at": _now_iso(),
        "agent_id": str(agent_id),
        "role": str(role)[:60],
        "goal": str(goal)[:300],
        "raw_chars": raw_chars,
        "compressed_chars": len(compressed),
        "compression_ratio": round(raw_chars / max(1, len(compressed)), 2),
        "compressed_text": compressed[:1500],
        "proposer": str(proposer)[:60],
        "stale": False,
    }

    try:
        records = load_json(_OBS_KEY, [])
        if not isinstance(records, list):
            records = []
        records.append(record)
        save_json(_OBS_KEY, records[-_MAX_OBS_RECORDS:])
    except Exception as exc:
        logger.warning("compressor: persist failed: %s", exc)
        return {"status": "error", "error": str(exc)}

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "agent_observation.recorded",
            {"obs_id": obs_id, "role": role, "compression_ratio": record["compression_ratio"]},
        )
    except Exception:
        pass

    return {"status": "ok", "observation": record}


def list_agent_observations(
    *,
    role: str | None = None,
    agent_id: str | None = None,
    days_back: int = 14,
    limit: int = 50,
) -> list[dict[str, Any]]:
    try:
        records = load_json(_OBS_KEY, [])
        if not isinstance(records, list):
            records = []
    except Exception:
        records = []
    if days_back > 0:
        cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()
        records = [r for r in records if str(r.get("recorded_at", "")) >= cutoff]
    if role:
        records = [r for r in records if r.get("role") == role]
    if agent_id:
        records = [r for r in records if r.get("agent_id") == agent_id]
    summaries = [
        {
            "obs_id": r.get("obs_id"),
            "recorded_at": r.get("recorded_at"),
            "role": r.get("role"),
            "goal": r.get("goal"),
            "compression_ratio": r.get("compression_ratio"),
            "compressed_chars": r.get("compressed_chars"),
            "preview": str(r.get("compressed_text", ""))[:200],
        }
        for r in records[-limit:]
    ]
    return list(reversed(summaries))


def get_agent_observation(obs_id: str) -> dict[str, Any] | None:
    try:
        records = load_json(_OBS_KEY, [])
        if not isinstance(records, list):
            return None
    except Exception:
        return None
    return next((r for r in records if r.get("obs_id") == obs_id), None)


def mark_stale_observations(*, days: int = _OBSERVATION_STALE_DAYS) -> dict[str, Any]:
    """Mark records older than N days as stale (for decay tracking)."""
    try:
        records = load_json(_OBS_KEY, [])
        if not isinstance(records, list):
            return {"status": "ok", "marked": 0}
    except Exception:
        return {"status": "error", "marked": 0}
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    marked = 0
    for r in records:
        if str(r.get("recorded_at", "")) < cutoff and not r.get("stale"):
            r["stale"] = True
            marked += 1
    if marked > 0:
        save_json(_OBS_KEY, records)
    return {"status": "ok", "marked": marked, "days_threshold": days}


# ── Tools ─────────────────────────────────────────────────────────


def _exec_compress_agent_run(args: dict[str, Any]) -> dict[str, Any]:
    return compress_agent_run(
        agent_id=str(args.get("agent_id") or ""),
        role=str(args.get("role") or ""),
        goal=str(args.get("goal") or ""),
        raw_output=str(args.get("raw_output") or ""),
        proposer=str(args.get("proposer") or "manual"),
    )


def _exec_list_agent_observations(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "observations": list_agent_observations(
            role=args.get("role"),
            agent_id=args.get("agent_id"),
            days_back=int(args.get("days_back") or 14),
            limit=int(args.get("limit") or 50),
        ),
    }


def _exec_get_agent_observation(args: dict[str, Any]) -> dict[str, Any]:
    record = get_agent_observation(str(args.get("obs_id") or ""))
    if record is None:
        return {"status": "error", "error": "obs_id not found"}
    return {"status": "ok", "observation": record}


AGENT_OBSERVATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "compress_agent_run",
            "description": (
                "Compress a sub-agent's raw output to 3-5 observation bullets "
                "via cheap-lane LLM. Stored as agent_observation for cross-agent "
                "reuse. Returns compression_ratio + compressed_text."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "role": {"type": "string"},
                    "goal": {"type": "string"},
                    "raw_output": {"type": "string"},
                    "proposer": {"type": "string"},
                },
                "required": ["role", "raw_output"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_agent_observations",
            "description": "List compressed agent observations (last N days). Filter by role/agent_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "agent_id": {"type": "string"},
                    "days_back": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_agent_observation",
            "description": "Retrieve full record of one observation by obs_id.",
            "parameters": {
                "type": "object",
                "properties": {"obs_id": {"type": "string"}},
                "required": ["obs_id"],
            },
        },
    },
]
