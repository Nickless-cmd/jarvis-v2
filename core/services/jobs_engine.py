"""Jobs Engine — proper async job queue with provider selection and cost tracking.

Ported pattern from jarvis-ai (2026-03). V2 has initiative_queue (Jarvis-
initiated proposals) but not a general-purpose job engine. This fills the
gap: a typed queue of deferrable work that:
- Carries allowed_providers + prefer_free_first preferences
- Tracks tokens/USD per run (when handler supplies cost data)
- Integrates with scheduled_job_windows (window_key, scheduled_job_id)
- Has status lifecycle: pending → running → completed | error | cancelled

Handlers are registered per job_type. `run_next_job()` picks the oldest
pending job and invokes its handler. This module does NOT execute LLM
calls itself — it's infrastructure; handlers decide what work happens.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

logger = logging.getLogger(__name__)

_STORAGE_REL = "workspaces/default/runtime/jobs_queue.json"
_HANDLERS: dict[str, Callable[[dict[str, Any]], "JobResult | dict[str, Any]"]] = {}


@dataclass
class JobResult:
    job_id: str
    job_type: str
    status: str
    selected_provider: str | None = None
    requests_used: int = 0
    tokens_used: int = 0
    usd_used: float = 0.0
    window_key: str | None = None
    scheduled_job_id: str | None = None
    error: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


def _storage_path() -> Path:
    base = os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2")
    return Path(base) / _STORAGE_REL


def _load() -> list[dict[str, Any]]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception as exc:
        logger.warning("jobs_engine: load failed: %s", exc)
    return []


def _save(items: list[dict[str, Any]]) -> None:
    path = _storage_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as exc:
        logger.warning("jobs_engine: save failed: %s", exc)


def register_handler(
    job_type: str,
    handler: Callable[[dict[str, Any]], "JobResult | dict[str, Any]"],
) -> None:
    """Register a handler function for a given job_type."""
    _HANDLERS[str(job_type)] = handler


def enqueue_job(
    *,
    job_type: str,
    payload: dict[str, Any] | None = None,
    allowed_providers: list[str] | None = None,
    prefer_free_first: bool = False,
    max_requests: int = 10,
    max_tokens: int | None = None,
    max_usd: float | None = None,
    window_key: str | None = None,
    scheduled_job_id: str | None = None,
    priority: int = 5,  # 1 = urgent, 10 = low
) -> str:
    """Create a new pending job. Returns job_id."""
    items = _load()
    job_id = f"job-{uuid4().hex[:12]}"
    items.append({
        "job_id": job_id,
        "job_type": str(job_type),
        "status": "pending",
        "payload": dict(payload or {}),
        "allowed_providers": list(allowed_providers or []),
        "prefer_free_first": bool(prefer_free_first),
        "max_requests": int(max_requests),
        "max_tokens": int(max_tokens) if max_tokens is not None else None,
        "max_usd": float(max_usd) if max_usd is not None else None,
        "window_key": window_key,
        "scheduled_job_id": scheduled_job_id,
        "priority": int(priority),
        "enqueued_at": datetime.now(UTC).isoformat(),
        "started_at": None,
        "finished_at": None,
        "result": None,
    })
    _save(items)
    return job_id


def select_provider(
    allowed: list[str] | None, *, prefer_free_first: bool = False
) -> str | None:
    """Pick the first usable provider from the list.

    This stub selects simply — subsystems can replace with richer provider
    ranking by wrapping this module. The free-first flag reorders the list.
    """
    if not allowed:
        # Default priority order when no explicit list provided
        default_order = (
            ["ollama-free", "openrouter-free", "anthropic", "openai"]
            if prefer_free_first
            else ["anthropic", "openai", "ollama-free", "openrouter-free"]
        )
        return default_order[0]
    ordered = list(allowed)
    if prefer_free_first:
        free = [p for p in ordered if "free" in p.lower()]
        paid = [p for p in ordered if "free" not in p.lower()]
        ordered = free + paid
    return ordered[0] if ordered else None


def _pop_next_pending(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    pending = [i for i in items if i.get("status") == "pending"]
    if not pending:
        return None
    pending.sort(key=lambda i: (int(i.get("priority", 5)), i.get("enqueued_at") or ""))
    return pending[0]


def run_next_job() -> JobResult | None:
    """Run the highest-priority pending job via its registered handler."""
    items = _load()
    job = _pop_next_pending(items)
    if job is None:
        return None
    job_type = str(job.get("job_type"))
    handler = _HANDLERS.get(job_type)
    if handler is None:
        job["status"] = "error"
        job["finished_at"] = datetime.now(UTC).isoformat()
        job["result"] = {"error": f"no-handler-registered:{job_type}"}
        _save(items)
        return JobResult(
            job_id=str(job.get("job_id")),
            job_type=job_type,
            status="error",
            error=f"no-handler-registered:{job_type}",
        )

    provider = select_provider(
        job.get("allowed_providers") or None,
        prefer_free_first=bool(job.get("prefer_free_first")),
    )
    job["status"] = "running"
    job["started_at"] = datetime.now(UTC).isoformat()
    if not isinstance(job.get("result"), dict):
        job["result"] = {}
    job["result"]["selected_provider"] = provider
    _save(items)

    try:
        handler_result = handler({
            **job,
            "selected_provider": provider,
        })
    except Exception as exc:
        logger.warning("jobs_engine: handler raised for %s: %s", job_type, exc)
        job["status"] = "error"
        job["finished_at"] = datetime.now(UTC).isoformat()
        job["result"] = {"error": str(exc), "selected_provider": provider}
        _save(items)
        return JobResult(
            job_id=str(job.get("job_id")),
            job_type=job_type,
            status="error",
            selected_provider=provider,
            error=str(exc),
        )

    # Normalize handler result
    if isinstance(handler_result, JobResult):
        result_dict = asdict(handler_result)
        status = handler_result.status
    else:
        result_dict = dict(handler_result or {})
        status = str(result_dict.get("status") or "completed")

    job["status"] = status
    job["finished_at"] = datetime.now(UTC).isoformat()
    job["result"] = {
        "selected_provider": result_dict.get("selected_provider") or provider,
        "requests_used": int(result_dict.get("requests_used", 0) or 0),
        "tokens_used": int(result_dict.get("tokens_used", 0) or 0),
        "usd_used": float(result_dict.get("usd_used", 0) or 0),
        "error": result_dict.get("error"),
        "details": result_dict.get("details") or {},
    }
    _save(items)
    return JobResult(
        job_id=str(job.get("job_id")),
        job_type=job_type,
        status=status,
        selected_provider=job["result"]["selected_provider"],
        requests_used=job["result"]["requests_used"],
        tokens_used=job["result"]["tokens_used"],
        usd_used=job["result"]["usd_used"],
        window_key=job.get("window_key"),
        scheduled_job_id=job.get("scheduled_job_id"),
        error=job["result"]["error"],
        details=job["result"]["details"],
    )


def cancel_job(job_id: str) -> bool:
    items = _load()
    for item in items:
        if item.get("job_id") == job_id and item.get("status") in ("pending", "running"):
            item["status"] = "cancelled"
            item["finished_at"] = datetime.now(UTC).isoformat()
            _save(items)
            return True
    return False


def list_jobs(*, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    items = _load()
    if status:
        items = [i for i in items if i.get("status") == status]
    return items[-limit:]


def build_jobs_engine_surface() -> dict[str, Any]:
    items = _load()
    by_status: dict[str, int] = {}
    cost_totals = {"tokens": 0, "usd": 0.0}
    for i in items:
        s = str(i.get("status") or "unknown")
        by_status[s] = by_status.get(s, 0) + 1
        result = i.get("result") or {}
        cost_totals["tokens"] += int(result.get("tokens_used") or 0)
        cost_totals["usd"] += float(result.get("usd_used") or 0)
    return {
        "active": len(items) > 0,
        "total_jobs": len(items),
        "by_status": by_status,
        "registered_handlers": list(_HANDLERS.keys()),
        "cost_totals": {
            "tokens": cost_totals["tokens"],
            "usd": round(cost_totals["usd"], 4),
        },
        "recent_jobs": items[-5:],
        "summary": (
            f"{by_status.get('pending', 0)} pending, {by_status.get('running', 0)} running, "
            f"{by_status.get('completed', 0)} completed, "
            f"{len(_HANDLERS)} handlers"
        ),
    }
