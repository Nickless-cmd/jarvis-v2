"""Structured end-of-run findings and a conservative admission fallback.

The audit ledger records decisions; `side_tasks` remains the only owner of
task status. A relevant new test failure cannot be deferred through this path.
"""
from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from core.runtime.state_store import load_json, med_laas, save_json
from core.services import side_tasks

_STATE_KEY = "run_finding_decisions"
_KINDS = frozenset({"coverage_gap", "new_test_failure", "preexisting_test_failure", "other"})
_DISPOSITIONS = frozenset({"side_task", "fixed_now", "existing_side_task", "declined", "blocked"})
_ADMISSION = re.compile(
    r"(?:ikke\s+(?:er\s+)?dækket\s+af\s+(?:en\s+)?test|"
    r"not\s+covered\s+by\s+(?:a\s+)?test|no\s+test\s+covers|"
    r"startposition(?:en)?\s+er\s+utestet)", re.IGNORECASE,
)
_CODE_FILE = re.compile(r"(?<!\w)(?:[\w.-]+/)*[\w+-]+\.(?:tsx|ts|jsx|js|py)\b")


def _key(kind: str, path: str, behavior: str) -> str:
    canonical = "|".join(" ".join(v.lower().split()) for v in (kind, path, behavior))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def _ledger() -> list[dict[str, Any]]:
    raw = load_json(_STATE_KEY, [])
    return [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []


def record_finding(*, kind: str, disposition: str, path: str, behavior: str,
                   evidence: str, title: str, next_step: str = "", reason: str = "",
                   run_id: str = "", session_id: str = "", finding_key: str = "",
                   existing_side_task_id: str = "") -> dict[str, Any]:
    """Account for one concrete finding; only deferred gaps create tasks."""
    kind, disposition = str(kind or "").strip(), str(disposition or "").strip()
    path, behavior = str(path or "").strip(), str(behavior or "").strip()
    evidence, title = str(evidence or "").strip(), str(title or "").strip()
    if kind not in _KINDS or disposition not in _DISPOSITIONS:
        return {"status": "error", "error": "invalid finding kind or disposition"}
    if not path or not behavior or not evidence:
        return {"status": "error", "error": "path, behavior and evidence are required"}
    if kind == "new_test_failure" and disposition == "side_task":
        return {"status": "error", "error": "a new relevant test failure must be handled in the current work"}
    if disposition == "side_task" and (not title or not next_step.strip()):
        return {"status": "error", "error": "side tasks require a title and concrete next_step"}
    if disposition == "declined" and not reason.strip():
        return {"status": "error", "error": "declined findings require a reason"}
    if disposition == "existing_side_task":
        if not existing_side_task_id or side_tasks.get(existing_side_task_id) is None:
            return {"status": "error", "error": "existing side task was not found"}

    key = str(finding_key or "").strip() or _key(kind, path, behavior)
    task_id = existing_side_task_id if disposition == "existing_side_task" else ""
    deduplicated = False
    if disposition == "side_task":
        prompt = (
            f"{next_step.strip()}\n\nFil: {path}. Adfærd: {behavior}. "
            f"Fund: {evidence[:700]}"
        )
        result = side_tasks.flag(
            title=title, prompt=prompt, tldr=f"{behavior}: {evidence[:120]}",
            session_id=session_id or None, finding_key=key,
            source_run_id=run_id, evidence=evidence,
        )
        if result.get("status") != "ok":
            return result
        task_id = str(result.get("side_task_id") or "")
        deduplicated = bool(result.get("deduplicated"))

    record = {
        "kind": kind, "disposition": disposition, "path": path[:300],
        "behavior": behavior[:300], "evidence": evidence[:1000],
        "reason": reason[:500], "finding_key": key,
        "side_task_id": task_id, "deduplicated": deduplicated,
        "run_id": str(run_id or "")[:120], "session_id": str(session_id or "")[:120],
        "created_at": datetime.now(UTC).isoformat(),
    }
    with med_laas(_STATE_KEY):
        rows = _ledger()
        # A repeated finalizer for the same run is idempotent. Another run
        # may report the same gap; the ledger keeps the evidence while the
        # side task remains one record.
        if not any(r.get("run_id") == record["run_id"] and
                   r.get("finding_key") == key and
                   r.get("disposition") == disposition for r in rows):
            rows.append(record)
            save_json(_STATE_KEY, rows[-2000:])
    return {"status": "ok", "side_task_id": task_id,
            "finding_key": key, "deduplicated": deduplicated}


def audit_final_response(*, run_id: str, session_id: str, text: str) -> dict[str, int]:
    """Catch only explicit self-admissions with one identifiable code file.

    This is a backstop for a missed tool call, not a general NLP classifier.
    A red unrelated suite, vague uncertainty or multiple possible files never
    creates a task. Those cases need the structured tool for classification.
    """
    run_id = str(run_id or "").strip()
    if not run_id or not text or any(
        r.get("run_id") == run_id and r.get("kind") == "coverage_gap"
        for r in _ledger()
    ):
        return {"created": 0}
    match = _ADMISSION.search(text)
    files = set(_CODE_FILE.findall(text))
    if match is None or len(files) != 1:
        return {"created": 0}
    path = next(iter(files))
    excerpt = " ".join(text[max(0, match.start() - 110):match.end() + 120].split())
    behavior = "first-frame-position" if re.search(
        r"startposition|first.frame|initial.frame", excerpt, re.IGNORECASE,
    ) else "explicitly-uncovered-behavior"
    result = record_finding(
        kind="coverage_gap", disposition="side_task", path=path,
        behavior=behavior, evidence=excerpt,
        title=f"Verificér testdækning i {path.split('/')[-1]}",
        next_step="Tilføj en test, som verificerer den beskrevne adfærd uden at låse sig til en intern implementeringsdetalje.",
        run_id=run_id, session_id=session_id,
    )
    return {"created": int(result.get("status") == "ok" and
                           not result.get("deduplicated"))}
