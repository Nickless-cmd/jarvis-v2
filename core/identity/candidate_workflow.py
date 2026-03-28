from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.identity.runtime_candidates import candidate_apply_readiness
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import (
    get_runtime_contract_candidate,
    list_runtime_contract_candidates,
    record_runtime_contract_file_write,
    supersede_runtime_contract_candidates,
    update_runtime_contract_candidate_status,
)

ALLOWED_CANDIDATE_STATUSES = {"proposed", "approved", "rejected", "applied", "superseded"}
_AUTO_APPLY_SAFE_USER_MD_CANONICAL_KEYS = {
    "user-preference:reply-style:plain-grounded-concise",
    "user-preference:review-style:challenge-before-settling",
}
_AUTO_APPLY_SAFE_MEMORY_MD_PREFIX = "workspace-memory:stable-context:"
_AUTO_APPLY_SAFE_REMEMBERED_FACT_CANONICAL_KEYS = {
    "workspace-memory:remembered-fact:project-anchor",
    "workspace-memory:remembered-fact:repo-context",
}


def approve_runtime_contract_candidate(
    candidate_id: str,
    *,
    status_reason_override: str | None = None,
) -> dict[str, object]:
    candidate = _require_candidate(candidate_id)
    _require_status(candidate, allowed={"proposed"})
    now = _now_iso()
    superseded = supersede_runtime_contract_candidates(
        candidate_type=str(candidate["candidate_type"]),
        target_file=str(candidate["target_file"]),
        canonical_key=str(candidate["canonical_key"]),
        exclude_candidate_id=str(candidate["candidate_id"]),
        updated_at=now,
        status_reason=f"Superseded by approval of {candidate['candidate_id']}.",
    )
    updated = update_runtime_contract_candidate_status(
        candidate_id,
        status="approved",
        updated_at=now,
        status_reason=(
            status_reason_override
            if status_reason_override is not None
            else _default_approval_status_reason(
                candidate,
                superseded=superseded,
            )
        ),
    )
    if updated is None:
        raise RuntimeError("failed to update candidate")
    event_bus.publish(
        "runtime.contract_candidate_approved",
        {
            "candidate_id": updated["candidate_id"],
            "candidate_type": updated["candidate_type"],
            "target_file": updated["target_file"],
            "status": updated["status"],
            "summary": updated["summary"],
        },
    )
    return updated


def reject_runtime_contract_candidate(candidate_id: str) -> dict[str, object]:
    candidate = _require_candidate(candidate_id)
    _require_status(candidate, allowed={"proposed", "approved"})
    updated = update_runtime_contract_candidate_status(
        candidate_id,
        status="rejected",
        updated_at=_now_iso(),
        status_reason="Rejected before apply.",
    )
    if updated is None:
        raise RuntimeError("failed to update candidate")
    event_bus.publish(
        "runtime.contract_candidate_rejected",
        {
            "candidate_id": updated["candidate_id"],
            "candidate_type": updated["candidate_type"],
            "target_file": updated["target_file"],
            "status": updated["status"],
            "summary": updated["summary"],
        },
    )
    return updated


def apply_runtime_contract_candidate(
    candidate_id: str,
    *,
    status_reason_override: str | None = None,
) -> dict[str, object]:
    candidate = _require_candidate(candidate_id)
    _require_status(candidate, allowed={"approved"})
    if str(candidate.get("target_file") or "") == "runtime/CHRONICLE.md":
        raise ValueError(
            "Chronicle drafts remain draft-only in this phase and cannot be applied."
        )

    equivalent_applied = _latest_equivalent_applied_candidate(candidate)
    if equivalent_applied is not None:
        updated = update_runtime_contract_candidate_status(
            candidate_id,
            status="superseded",
            updated_at=_now_iso(),
            status_reason=(
                f"Equivalent canonical key already applied by {equivalent_applied['candidate_id']}."
            ),
        )
        if updated is None:
            raise RuntimeError("failed to supersede duplicate candidate")
        event_bus.publish(
            "runtime.contract_candidate_superseded",
            {
                "candidate_id": updated["candidate_id"],
                "candidate_type": updated["candidate_type"],
                "target_file": updated["target_file"],
                "status": updated["status"],
                "summary": updated["summary"],
            },
        )
        return {
            "candidate": updated,
            "write": None,
        }

    material = _candidate_write_material(candidate)
    write_result = _append_workspace_contract_line(
        target_file=str(candidate["target_file"]),
        section_heading=material["section_heading"],
        content_line=material["content_line"],
    )
    now = _now_iso()
    write = record_runtime_contract_file_write(
        write_id=f"write-{uuid4().hex}",
        candidate_id=str(candidate["candidate_id"]),
        target_file=str(candidate["target_file"]),
        canonical_key=str(candidate["canonical_key"]),
        write_status=write_result["write_status"],
        actor="runtime:contract-workflow",
        summary=str(candidate["summary"]),
        content_line=material["content_line"],
        created_at=now,
    )
    updated = update_runtime_contract_candidate_status(
        candidate_id,
        status="applied",
        updated_at=now,
        status_reason=(
            status_reason_override
            if status_reason_override is not None
            else _default_apply_status_reason(
                candidate,
                write_status=str(write_result["write_status"] or ""),
            )
        ),
    )
    if updated is None:
        raise RuntimeError("failed to mark candidate applied")
    event_bus.publish(
        "runtime.contract_candidate_applied",
        {
            "candidate_id": updated["candidate_id"],
            "candidate_type": updated["candidate_type"],
            "target_file": updated["target_file"],
            "status": updated["status"],
            "summary": updated["summary"],
            "write_status": write["write_status"],
        },
    )
    event_bus.publish(
        "runtime.contract_file_updated",
        {
            "write_id": write["write_id"],
            "candidate_id": write["candidate_id"],
            "target_file": write["target_file"],
            "write_status": write["write_status"],
            "summary": write["summary"],
        },
    )
    return {
        "candidate": updated,
        "write": write,
    }


def auto_apply_safe_user_md_candidates() -> dict[str, object]:
    considered = 0
    auto_applied = 0
    skipped = 0
    items: list[dict[str, object]] = []

    for candidate in list_runtime_contract_candidates(
        candidate_type="preference_update",
        target_file="USER.md",
        status="proposed",
        limit=12,
    ):
        considered += 1
        if not _candidate_eligible_for_auto_apply(candidate):
            skipped += 1
            continue
        approved = approve_runtime_contract_candidate(
            str(candidate["candidate_id"]),
            status_reason_override="Approved by bounded auto-apply policy for safe USER.md candidate.",
        )
        applied = apply_runtime_contract_candidate(
            str(approved["candidate_id"]),
            status_reason_override="Applied by bounded auto-apply policy for safe USER.md candidate.",
        )
        auto_applied += 1
        items.append(applied["candidate"])

    return {
        "considered": considered,
        "auto_applied": auto_applied,
        "skipped": skipped,
        "items": items,
        "summary": (
            f"Auto-applied {auto_applied} safe USER.md candidates."
            if auto_applied
            else "No safe USER.md candidates were eligible for auto-apply."
        ),
    }


def auto_apply_safe_memory_md_candidates() -> dict[str, object]:
    considered = 0
    auto_applied = 0
    skipped = 0
    items: list[dict[str, object]] = []

    for candidate in list_runtime_contract_candidates(
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        limit=12,
    ):
        considered += 1
        if not _memory_candidate_eligible_for_auto_apply(candidate):
            skipped += 1
            continue
        approved = approve_runtime_contract_candidate(
            str(candidate["candidate_id"]),
            status_reason_override="Approved by bounded auto-apply policy for safe MEMORY.md candidate.",
        )
        applied = apply_runtime_contract_candidate(
            str(approved["candidate_id"]),
            status_reason_override="Applied by bounded auto-apply policy for safe MEMORY.md candidate.",
        )
        auto_applied += 1
        items.append(applied["candidate"])

    return {
        "considered": considered,
        "auto_applied": auto_applied,
        "skipped": skipped,
        "items": items,
        "summary": (
            f"Auto-applied {auto_applied} safe MEMORY.md candidates."
            if auto_applied
            else "No safe MEMORY.md candidates were eligible for auto-apply."
        ),
    }


def _require_candidate(candidate_id: str) -> dict[str, object]:
    candidate = get_runtime_contract_candidate(candidate_id)
    if candidate is None:
        raise ValueError("Runtime contract candidate not found")
    if str(candidate.get("status") or "") not in ALLOWED_CANDIDATE_STATUSES:
        raise ValueError("Runtime contract candidate has invalid status")
    return candidate


def _require_status(candidate: dict[str, object], *, allowed: set[str]) -> None:
    status = str(candidate.get("status") or "")
    if status not in allowed:
        raise ValueError(f"Candidate must be in one of: {', '.join(sorted(allowed))}")


def _latest_equivalent_applied_candidate(candidate: dict[str, object]) -> dict[str, object] | None:
    canonical_key = str(candidate.get("canonical_key") or "")
    if not canonical_key:
        return None
    matches = list_runtime_contract_candidates(
        candidate_type=str(candidate["candidate_type"]),
        target_file=str(candidate["target_file"]),
        status="applied",
        limit=20,
    )
    for item in matches:
        if str(item.get("canonical_key") or "") != canonical_key:
            continue
        if str(item.get("candidate_id") or "") == str(candidate["candidate_id"]):
            continue
        return item
    return None


def _candidate_eligible_for_auto_apply(candidate: dict[str, object]) -> bool:
    if str(candidate.get("target_file") or "") != "USER.md":
        return False
    if str(candidate.get("candidate_type") or "") != "preference_update":
        return False
    if str(candidate.get("status") or "") != "proposed":
        return False
    if str(candidate.get("confidence") or "") != "high":
        return False
    canonical_key = str(candidate.get("canonical_key") or "")
    if canonical_key not in _AUTO_APPLY_SAFE_USER_MD_CANONICAL_KEYS:
        return False
    readiness = candidate_apply_readiness(candidate)
    if str(readiness.get("apply_readiness") or "") != "high":
        return False
    dimension_key = _candidate_dimension_key(candidate)
    if not dimension_key:
        return False
    for other in list_runtime_contract_candidates(
        candidate_type="preference_update",
        target_file="USER.md",
        limit=20,
    ):
        if str(other.get("candidate_id") or "") == str(candidate.get("candidate_id") or ""):
            continue
        if str(other.get("status") or "") not in {"proposed", "approved"}:
            continue
        if _candidate_dimension_key(other) != dimension_key:
            continue
        return False
    return True


def _memory_candidate_eligible_for_auto_apply(candidate: dict[str, object]) -> bool:
    if str(candidate.get("target_file") or "") != "MEMORY.md":
        return False
    if str(candidate.get("candidate_type") or "") != "memory_promotion":
        return False
    if str(candidate.get("status") or "") != "proposed":
        return False
    if str(candidate.get("confidence") or "") != "high":
        return False
    canonical_key = str(candidate.get("canonical_key") or "")
    readiness = candidate_apply_readiness(candidate)
    if canonical_key.startswith(_AUTO_APPLY_SAFE_MEMORY_MD_PREFIX):
        if str(readiness.get("apply_readiness") or "") != "medium":
            return False
        if str(readiness.get("apply_reason") or "") != "needs-review":
            return False
    elif canonical_key in _AUTO_APPLY_SAFE_REMEMBERED_FACT_CANONICAL_KEYS:
        if str(readiness.get("apply_readiness") or "") != "medium":
            return False
        if str(readiness.get("apply_reason") or "") != "factual-memory":
            return False
    else:
        return False
    for other in list_runtime_contract_candidates(
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        limit=20,
    ):
        if str(other.get("candidate_id") or "") == str(candidate.get("candidate_id") or ""):
            continue
        if str(other.get("status") or "") not in {"proposed", "approved"}:
            continue
        if str(other.get("canonical_key") or "") != canonical_key:
            continue
        return False
    return True


def _candidate_dimension_key(candidate: dict[str, object]) -> str:
    canonical_key = str(candidate.get("canonical_key") or "")
    parts = canonical_key.split(":")
    if len(parts) < 2:
        return canonical_key
    return ":".join(parts[:2])


def _candidate_write_material(candidate: dict[str, object]) -> dict[str, str]:
    target_file = str(candidate.get("target_file") or "")
    proposed_value = str(candidate.get("proposed_value") or "").strip()
    if target_file == "USER.md":
        return {
            "section_heading": str(candidate.get("write_section") or "## Durable Preferences"),
            "content_line": proposed_value or _user_line_from_key(candidate),
        }
    if target_file == "MEMORY.md":
        return {
            "section_heading": str(candidate.get("write_section") or "## Curated Memory"),
            "content_line": proposed_value or _memory_line_from_key(candidate),
        }
    if target_file in {"SOUL.md", "IDENTITY.md"}:
        return {
            "section_heading": str(candidate.get("write_section") or "## Proposed Canonical Self Shifts"),
            "content_line": proposed_value or _canonical_self_line_from_key(candidate),
        }
    raise ValueError("Unsupported target file")


def _user_line_from_key(candidate: dict[str, object]) -> str:
    canonical_key = str(candidate.get("canonical_key") or "")
    mapping = {
        "user-preference:language:danish": "- Language preference: replies in Danish by default.",
        "user-preference:reply-style:concise": "- Reply preference: concise answers by default.",
        "user-preference:summaries:concise-technical": "- Summary preference: concise technical summaries.",
        "user-profile:working-hours:late-evening": "- Work pattern: mostly works late in the evening.",
    }
    return mapping.get(canonical_key, f"- {str(candidate.get('summary') or '').strip()}")


def _memory_line_from_key(candidate: dict[str, object]) -> str:
    canonical_key = str(candidate.get("canonical_key") or "")
    mapping = {
        "workspace-memory:project-anchor:build-jarvis-together": "- Project anchor: Jarvis and the user are building Jarvis together.",
    }
    return mapping.get(canonical_key, f"- {str(candidate.get('summary') or '').strip()}")


def _canonical_self_line_from_key(candidate: dict[str, object]) -> str:
    return f"- {str(candidate.get('summary') or '').strip()}"


def _default_approval_status_reason(
    candidate: dict[str, object],
    *,
    superseded: int,
) -> str:
    target_file = str(candidate.get("target_file") or "")
    if target_file in {"SOUL.md", "IDENTITY.md"}:
        if superseded:
            return (
                "Approved for canonical self apply after explicit user approval. "
                f"Superseded {superseded} older candidates."
            )
        return "Approved for canonical self apply after explicit user approval."
    if superseded:
        return f"Approved for governed apply. Superseded {superseded} older candidates."
    return "Approved for governed apply."


def _default_apply_status_reason(
    candidate: dict[str, object],
    *,
    write_status: str,
) -> str:
    target_file = str(candidate.get("target_file") or "")
    if target_file in {"SOUL.md", "IDENTITY.md"}:
        if write_status == "written":
            return "Applied to canonical self file after explicit user approval."
        return "Equivalent canonical self content already present after explicit user approval."
    if write_status == "written":
        return "Applied to workspace file."
    return "Equivalent content already present in workspace file."


def _append_workspace_contract_line(
    *,
    target_file: str,
    section_heading: str,
    content_line: str,
) -> dict[str, str]:
    workspace_dir = ensure_default_workspace()
    path = Path(workspace_dir) / target_file
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    normalized_line = " ".join(str(content_line or "").split()).strip()
    if not normalized_line:
        raise ValueError("Candidate has no writeable content line")

    if normalized_line in existing:
        return {
            "write_status": "already-present",
            "path": str(path),
            "content_line": normalized_line,
        }

    lines = existing.splitlines()
    heading = str(section_heading or "").strip()
    if not lines:
        next_text = f"{heading}\n\n{normalized_line}\n"
    elif heading not in existing:
        base = existing.rstrip()
        next_text = f"{base}\n\n{heading}\n\n{normalized_line}\n"
    else:
        next_text = _insert_under_heading(existing, heading, normalized_line)

    path.write_text(next_text, encoding="utf-8")
    return {
        "write_status": "written",
        "path": str(path),
        "content_line": normalized_line,
    }


def _insert_under_heading(text: str, heading: str, content_line: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    inserted = False
    index = 0
    while index < len(lines):
        line = lines[index]
        out.append(line)
        if line.strip() == heading and not inserted:
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                out.append(lines[next_index])
                next_index += 1
            out.append(content_line)
            inserted = True
            index = next_index - 1
        index += 1
    if not inserted:
        body = text.rstrip()
        return f"{body}\n\n{heading}\n\n{content_line}\n"
    return "\n".join(out).rstrip() + "\n"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
