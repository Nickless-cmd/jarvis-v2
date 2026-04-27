"""Agent Skill Library — per-role learned patterns + workflows.

Inspired by Letta's Skill Library (Letta Code). Each agent role gets a
markdown file at ~/.jarvis-v2/agent_memory/{role}/skills.md that:

- Is READ when an agent of that role is spawned (joined into goal context)
- Is APPENDED when the agent completes (observed patterns added)
- Survives across sessions (cross-session memory per role)

Schema for skills.md (markdown sections):

  # Skills for role: researcher

  ## Workflows
  - When asked to find code patterns, search both core/services and core/tools first.
  - For Python imports, use grep with type=py for speed.

  ## Pitfalls
  - Don't trust caching for live state — eventbus is more accurate.

  ## Successful patterns
  - 2026-04-27: unified_recall + composite_invoke gave 3x faster answer.

Audit trail: every mutation goes through agent_skill_mutation_log
(same pattern as identity_mutation_log). Rollback per mutation_id.

Decay: skills don't auto-decay. Manual archive via tool when patterns
become stale.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_SKILLS_ROOT = Path.home() / ".jarvis-v2" / "agent_memory"
_MUTATION_LOG_KEY = "agent_skill_mutations"


def _skills_path(role: str) -> Path:
    role = (role or "").strip().replace("/", "_")
    return _SKILLS_ROOT / role / "skills.md"


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def get_skills(role: str) -> dict[str, Any]:
    """Read the skills.md for a role. Returns {role, content, exists, path}."""
    path = _skills_path(role)
    if not path.exists():
        return {
            "role": role, "exists": False, "path": str(path),
            "content": "",
            "note": f"No skills file yet for role '{role}'",
        }
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"role": role, "exists": False, "error": str(exc), "path": str(path)}
    return {"role": role, "exists": True, "path": str(path), "content": content,
            "chars": len(content)}


def append_skill_observation(
    *,
    role: str,
    section: str,
    observation: str,
    proposer: str = "agent",
) -> dict[str, Any]:
    """Append an observation to a section of the role's skills.md.

    Sections: 'Workflows', 'Pitfalls', 'Successful patterns'. Custom
    sections allowed but a heading is created if absent.

    Logged in agent_skill_mutation_log with full before/after snapshot.
    """
    role = (role or "").strip()
    section = (section or "").strip()
    observation = (observation or "").strip()
    if not role or not section or not observation:
        return {"status": "error", "error": "role, section, observation required"}

    path = _skills_path(role)
    path.parent.mkdir(parents=True, exist_ok=True)

    before = path.read_text(encoding="utf-8") if path.exists() else f"# Skills for role: {role}\n"
    timestamp = datetime.now(UTC).date().isoformat()

    # Ensure section header exists
    section_header = f"## {section}"
    if section_header in before:
        # Insert observation immediately after the section header line
        lines = before.splitlines()
        out_lines: list[str] = []
        inserted = False
        for line in lines:
            out_lines.append(line)
            if not inserted and line.strip() == section_header:
                out_lines.append(f"- {timestamp}: {observation}")
                inserted = True
        after = "\n".join(out_lines)
        if not after.endswith("\n"):
            after += "\n"
    else:
        # Append new section with first observation
        sep = "\n\n" if before and not before.endswith("\n\n") else ""
        after = before + sep + f"{section_header}\n- {timestamp}: {observation}\n"

    try:
        path.write_text(after, encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    mutation_id = _record_skill_mutation(
        role=role, path=path, before=before, after=after,
        reason=f"append to {section}: {observation[:80]}",
        proposer=proposer,
    )
    return {
        "status": "ok",
        "role": role,
        "mutation_id": mutation_id,
        "section": section,
        "chars_before": len(before),
        "chars_after": len(after),
    }


def _record_skill_mutation(
    *, role: str, path: Path, before: str, after: str,
    reason: str, proposer: str,
) -> str:
    mutation_id = f"smut-{uuid4().hex[:12]}"
    record = {
        "mutation_id": mutation_id,
        "recorded_at": datetime.now(UTC).isoformat(),
        "role": role,
        "target_path": str(path),
        "before_content": before,
        "after_content": after,
        "before_hash": _hash(before),
        "after_hash": _hash(after),
        "reason": reason[:400],
        "proposer": proposer,
        "rolled_back": False,
        "rolled_back_at": None,
    }
    try:
        log = load_json(_MUTATION_LOG_KEY, [])
        if not isinstance(log, list):
            log = []
        log.append(record)
        save_json(_MUTATION_LOG_KEY, log)
    except Exception as exc:
        logger.warning("agent_skill_library: log persist failed: %s", exc)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "agent_skill.appended",
            {"mutation_id": mutation_id, "role": role,
             "delta_chars": len(after) - len(before)},
        )
    except Exception:
        pass
    return mutation_id


def rollback_skill_mutation(mutation_id: str) -> dict[str, Any]:
    """Restore a skills.md to its before-state from a logged mutation."""
    try:
        log = load_json(_MUTATION_LOG_KEY, [])
        if not isinstance(log, list):
            log = []
    except Exception as exc:
        return {"status": "error", "error": f"log read failed: {exc}"}
    record = next((r for r in log if r.get("mutation_id") == mutation_id), None)
    if record is None:
        return {"status": "error", "error": "mutation not found"}
    if record.get("rolled_back"):
        return {"status": "error", "error": "already rolled back"}

    target = Path(str(record.get("target_path", "")))
    before = str(record.get("before_content", ""))
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(before, encoding="utf-8")
    except OSError as exc:
        return {"status": "error", "error": f"write failed: {exc}"}

    record["rolled_back"] = True
    record["rolled_back_at"] = datetime.now(UTC).isoformat()
    save_json(_MUTATION_LOG_KEY, log)

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "agent_skill.rolled_back",
            {"mutation_id": mutation_id, "role": record.get("role")},
        )
    except Exception:
        pass
    return {"status": "ok", "mutation_id": mutation_id, "role": record.get("role")}


def list_skill_mutations(*, role: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    try:
        log = load_json(_MUTATION_LOG_KEY, [])
        if not isinstance(log, list):
            log = []
    except Exception:
        log = []
    if role:
        log = [r for r in log if r.get("role") == role]
    summaries = [
        {
            "mutation_id": r.get("mutation_id"),
            "recorded_at": r.get("recorded_at"),
            "role": r.get("role"),
            "reason": r.get("reason"),
            "proposer": r.get("proposer"),
            "delta_chars": (len(r.get("after_content", "") or "") -
                            len(r.get("before_content", "") or "")),
            "rolled_back": r.get("rolled_back"),
        }
        for r in log[-limit:]
    ]
    return list(reversed(summaries))


def list_known_roles() -> list[str]:
    """Return all roles that have a skills.md file."""
    if not _SKILLS_ROOT.exists():
        return []
    return sorted([
        d.name for d in _SKILLS_ROOT.iterdir()
        if d.is_dir() and (d / "skills.md").exists()
    ])


# ── Tools ──────────────────────────────────────────────────────────


def _exec_get_agent_skills(args: dict[str, Any]) -> dict[str, Any]:
    return get_skills(str(args.get("role") or ""))


def _exec_append_skill(args: dict[str, Any]) -> dict[str, Any]:
    return append_skill_observation(
        role=str(args.get("role") or ""),
        section=str(args.get("section") or ""),
        observation=str(args.get("observation") or ""),
        proposer=str(args.get("proposer") or "agent"),
    )


def _exec_rollback_skill_mutation(args: dict[str, Any]) -> dict[str, Any]:
    return rollback_skill_mutation(str(args.get("mutation_id") or ""))


def _exec_list_skill_mutations(args: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "mutations": list_skill_mutations(
            role=args.get("role"),
            limit=int(args.get("limit") or 50),
        ),
    }


def _exec_list_known_roles(args: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "roles": list_known_roles()}


AGENT_SKILL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_agent_skills",
            "description": "Read the skills.md for a role (cross-session learned patterns).",
            "parameters": {
                "type": "object",
                "properties": {"role": {"type": "string"}},
                "required": ["role"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_skill_observation",
            "description": (
                "Append a learned observation to a role's skills.md. Sections: "
                "'Workflows', 'Pitfalls', 'Successful patterns', or custom. "
                "Logged in agent_skill_mutation_log with full before/after."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "section": {"type": "string"},
                    "observation": {"type": "string"},
                    "proposer": {"type": "string"},
                },
                "required": ["role", "section", "observation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rollback_skill_mutation",
            "description": "Restore a skills.md to its before-state from a logged mutation.",
            "parameters": {
                "type": "object",
                "properties": {"mutation_id": {"type": "string"}},
                "required": ["mutation_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_skill_mutations",
            "description": "List recent skills.md mutations (audit trail). Optionally filter by role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_skill_roles",
            "description": "List all roles that have a skills.md file.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
