"""Rene result-formende helpers for workspace-capabilities.

Udskilt fra workspace_capabilities.py (Boy Scout-reglen) som de deltagelses-frie
byggeklodser, der normaliserer et capability-resultat (status-familie, ok/error,
detail), afgør approval-krav og laver korte previews/fingerprints.

Ingen side-effekter, ingen I/O. Både hoved-modulet, execute- og verdict-
undermodulerne importerer herfra, så der ikke opstår dobbelt-sandhed.

Alle funktioner re-eksporteres fra core.tools.workspace_capabilities for
bagudkompatibilitet.
"""
from __future__ import annotations

from hashlib import sha1


def _finalize_capability_result(result: dict[str, object]) -> dict[str, object]:
    normalized = dict(result)
    status = str(normalized.get("status") or "unknown")
    execution_mode = str(normalized.get("execution_mode") or "unsupported")
    detail = str(normalized.get("detail") or "").strip()
    status_family = _capability_status_family(status)

    if not detail:
        detail = _default_capability_detail(status=status, execution_mode=execution_mode)

    normalized["status_family"] = status_family
    normalized["ok"] = status == "executed"
    normalized["error"] = status_family in {"blocked", "unavailable", "missing", "error"}
    normalized["detail"] = detail
    normalized["message"] = detail
    return normalized


def _capability_status_family(status: str) -> str:
    if status == "executed":
        return "success"
    if status == "approval-required":
        return "approval"
    if status in {"not-found", "blocked-missing-capability"}:
        return "missing"
    if status in {"unavailable", "not-runnable"}:
        return "unavailable"
    if status.startswith("blocked"):
        return "blocked"
    if status.endswith("error") or "error" in status:
        return "error"
    return "other"


def _default_capability_detail(*, status: str, execution_mode: str) -> str:
    if status == "executed":
        return f"Capability executed: {execution_mode}."
    if status == "approval-required":
        return f"Capability requires approval before execution: {execution_mode}."
    if status == "unavailable":
        return f"Capability is unavailable: {execution_mode}."
    if status == "not-runnable":
        return f"Capability is not runnable in this pass: {execution_mode}."
    if status == "not-found":
        return "Capability was not found in runtime truth."
    if status.startswith("blocked"):
        return f"Capability execution was blocked: {status}."
    return f"Capability finished with status {status}: {execution_mode}."


def _requires_capability_approval(summary: dict[str, object]) -> bool:
    return bool(summary.get("approval_required"))


def _approval_result(
    summary: dict[str, object], *, approved: bool, granted: bool
) -> dict[str, object]:
    policy = str(summary.get("approval_policy") or "not-applicable")
    required = bool(summary.get("approval_required"))
    return {
        "policy": policy,
        "required": required,
        "approved": approved,
        "granted": granted,
    }


def _preview_text(text: str, limit: int = 120) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _result_preview(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    text = str(result.get("text", "")).strip()
    if text:
        return _preview_text(text)
    matches = result.get("matches")
    if isinstance(matches, list) and matches:
        excerpt = str((matches[0] or {}).get("excerpt", "")).strip()
        if excerpt:
            return _preview_text(excerpt)
    return None


def _content_fingerprint(text: str) -> str:
    return sha1((text or "").encode("utf-8")).hexdigest()[:16]
