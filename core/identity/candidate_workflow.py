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
    "user-preference:language:danish",
    "user-preference:reply-style:concise",
    "user-preference:summaries:concise-technical",
    "user-preference:reply-style:plain-grounded-concise",
    "user-preference:review-style:challenge-before-settling",
    "user-workstyle:direction:stable-threading",
    "user-preference:reminders:assumption-caution",
}
_AUTO_APPLY_SAFE_MEMORY_MD_PREFIX = "workspace-memory:stable-context:"
_AUTO_APPLY_SAFE_REMEMBERED_FACT_CANONICAL_KEYS = {
    "workspace-memory:remembered-fact:project-anchor",
    "workspace-memory:remembered-fact:repo-context",
    "workspace-memory:remembered-fact:workspace-context",
}
_APPROVED_RUNTIME_CONTRACT_TARGET_FILES = {
    "USER.md",
    "MEMORY.md",
    "SOUL.md",
    "IDENTITY.md",
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
        return _apply_chronicle_runtime_contract_candidate(
            candidate,
            status_reason_override=status_reason_override,
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


def apply_approved_runtime_contract_candidates(
    *,
    target_files: set[str] | None = None,
    limit: int = 12,
) -> dict[str, object]:
    allowed_targets = target_files or _APPROVED_RUNTIME_CONTRACT_TARGET_FILES
    considered = 0
    applied = 0
    skipped = 0
    items: list[dict[str, object]] = []

    approved_candidates = list_runtime_contract_candidates(
        status="approved",
        limit=max(limit * 3, 24),
    )
    for candidate in approved_candidates:
        if applied >= max(limit, 1):
            break
        if str(candidate.get("target_file") or "") not in allowed_targets:
            continue
        considered += 1
        try:
            result = apply_runtime_contract_candidate(str(candidate["candidate_id"]))
        except Exception:
            skipped += 1
            continue
        applied_candidate = dict(result.get("candidate") or {})
        items.append(applied_candidate)
        if str(applied_candidate.get("status") or "") == "applied":
            applied += 1
        else:
            skipped += 1

    return {
        "considered": considered,
        "applied": applied,
        "skipped": skipped,
        "items": items,
        "summary": (
            f"Applied {applied} approved runtime contract candidates."
            if applied
            else "No approved runtime contract candidates were ready to apply."
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
    confidence = str(candidate.get("confidence") or "")
    if confidence not in {"high", "medium"}:
        return False
    canonical_key = str(candidate.get("canonical_key") or "")
    source_mode = str(candidate.get("source_mode") or "")
    source_kind = str(candidate.get("source_kind") or "")
    evidence_class = str(candidate.get("evidence_class") or "")
    if canonical_key not in _AUTO_APPLY_SAFE_USER_MD_CANONICAL_KEYS:
        if not (
            source_mode == "end_of_run_memory_consolidation"
            and source_kind in {"user-explicit", "runtime-inference"}
            and evidence_class in {
                "explicit_user_statement",
                "explicit_assistant_confirmation",
                "runtime-inference",
            }
        ):
            return False
    readiness = candidate_apply_readiness(candidate)
    if str(readiness.get("apply_readiness") or "") not in {"high", "medium"}:
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
    confidence = str(candidate.get("confidence") or "")
    if confidence not in {"high", "medium"}:
        return False
    canonical_key = str(candidate.get("canonical_key") or "")
    source_mode = str(candidate.get("source_mode") or "")
    source_kind = str(candidate.get("source_kind") or "")
    evidence_class = str(candidate.get("evidence_class") or "")
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
    elif (
        canonical_key.startswith("workspace-memory:remembered-fact:llm-")
        and source_mode == "end_of_run_memory_consolidation"
        and source_kind == "user-explicit"
        and evidence_class == "explicit_user_statement"
    ):
        if str(readiness.get("apply_readiness") or "") != "medium":
            return False
        if str(readiness.get("apply_reason") or "") != "factual-memory":
            return False
    elif (
        # Broaden: medium-confidence facts from end-of-run consolidation
        # that aren't explicit-user-statement but are runtime-derived or
        # assistant-confirmed — these are commonly dropped today
        canonical_key.startswith("workspace-memory:remembered-fact:llm-")
        and source_mode == "end_of_run_memory_consolidation"
        and confidence == "medium"
        and evidence_class in {"runtime-inference", "explicit_assistant_confirmation"}
    ):
        pass  # eligible — fall through to duplicate check
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
    if target_file == "runtime/CHRONICLE.md":
        return _chronicle_write_material(candidate)
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


def _chronicle_write_material(candidate: dict[str, object]) -> dict[str, str]:
    summary = _single_line(candidate.get("summary") or "")
    reason = _single_line(candidate.get("reason") or "")
    confidence = _single_line(candidate.get("confidence") or "low")
    proposal_type, focus = _chronicle_entry_shape(candidate)
    entry_date = _now_iso()[:10]
    header = f"### {entry_date} | {proposal_type} | {focus}"
    content_block = "\n".join(
        [
            header,
            f"- Summary: {summary or 'Bounded chronicle carry-forward candidate.'}",
            f"- Reason: {reason or 'Approved bounded chronicle draft.'}",
            f"- Confidence: {confidence}",
        ]
    )
    return {
        "section_heading": "## Chronicle Entries",
        "content_line": header,
        "content_block": content_block,
    }


def _default_approval_status_reason(
    candidate: dict[str, object],
    *,
    superseded: int,
) -> str:
    target_file = str(candidate.get("target_file") or "")
    if target_file == "runtime/CHRONICLE.md":
        if superseded:
            return (
                "Approved for chronicle apply through the chronicle-specific gate. "
                f"Superseded {superseded} older candidates."
            )
        return "Approved for chronicle apply through the chronicle-specific gate."
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
    if target_file == "runtime/CHRONICLE.md":
        if write_status == "written":
            return "Applied as bounded chronicle entry through chronicle-specific approved gate."
        return "Equivalent chronicle content already present in runtime chronicle file."
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
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _append_workspace_contract_block(
    *,
    target_file: str,
    section_heading: str,
    content_block: str,
) -> dict[str, str]:
    workspace_dir = ensure_default_workspace()
    path = Path(workspace_dir) / target_file
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    normalized_block = str(content_block or "").strip()
    if not normalized_block:
        raise ValueError("Candidate has no writeable content block")

    if normalized_block in existing:
        return {
            "write_status": "already-present",
            "path": str(path),
            "content_line": normalized_block.splitlines()[0].strip(),
        }

    lines = existing.splitlines()
    heading = str(section_heading or "").strip()
    block = normalized_block
    if not lines:
        next_text = f"{heading}\n\n{block}\n"
    elif heading not in existing:
        base = existing.rstrip()
        next_text = f"{base}\n\n{heading}\n\n{block}\n"
    else:
        next_text = _insert_block_under_heading(existing, heading, block)

    path.write_text(next_text, encoding="utf-8")
    return {
        "write_status": "written",
        "path": str(path),
        "content_line": block.splitlines()[0].strip(),
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


def _insert_block_under_heading(text: str, heading: str, content_block: str) -> str:
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
            out.append(content_block)
            inserted = True
            index = next_index - 1
        index += 1
    if not inserted:
        body = text.rstrip()
        return f"{body}\n\n{heading}\n\n{content_block}\n"
    return "\n".join(out).rstrip() + "\n"


def _apply_chronicle_runtime_contract_candidate(
    candidate: dict[str, object],
    *,
    status_reason_override: str | None = None,
) -> dict[str, object]:
    if str(candidate.get("candidate_type") or "") != "chronicle_draft":
        raise ValueError("Unsupported chronicle candidate type")

    equivalent_applied = _latest_equivalent_applied_candidate(candidate)
    if equivalent_applied is not None:
        updated = update_runtime_contract_candidate_status(
            str(candidate["candidate_id"]),
            status="superseded",
            updated_at=_now_iso(),
            status_reason=(
                f"Equivalent canonical key already applied by {equivalent_applied['candidate_id']}."
            ),
        )
        if updated is None:
            raise RuntimeError("failed to supersede duplicate chronicle candidate")
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

    material = _chronicle_write_material(candidate)
    write_result = _append_workspace_contract_block(
        target_file="runtime/CHRONICLE.md",
        section_heading=material["section_heading"],
        content_block=str(material["content_block"]),
    )
    now = _now_iso()
    write = record_runtime_contract_file_write(
        write_id=f"write-{uuid4().hex}",
        candidate_id=str(candidate["candidate_id"]),
        target_file="runtime/CHRONICLE.md",
        canonical_key=str(candidate["canonical_key"]),
        write_status=write_result["write_status"],
        actor="runtime:chronicle-apply-gate",
        summary=str(candidate["summary"]),
        content_line=material["content_line"],
        created_at=now,
    )
    updated = update_runtime_contract_candidate_status(
        str(candidate["candidate_id"]),
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
        raise RuntimeError("failed to mark chronicle candidate applied")
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


def _chronicle_entry_shape(candidate: dict[str, object]) -> tuple[str, str]:
    canonical_key = str(candidate.get("canonical_key") or "")
    parts = [part for part in canonical_key.split(":") if part]
    proposal_type = parts[1] if len(parts) >= 2 else "chronicle-draft"
    focus = parts[2] if len(parts) >= 3 else "chronicle-thread"
    return proposal_type, focus


def _single_line(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
