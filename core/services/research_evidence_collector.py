"""Capture structured web-tool evidence for the active research run."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from core.services.research_contract import normalize_source

_ACTIVE: ContextVar[tuple[str, str] | None] = ContextVar("research_evidence", default=None)


@contextmanager
def collecting_for(run_id: str, *, task_id: str = ""):
    token = _ACTIVE.set((run_id, task_id))
    try:
        yield
    finally:
        _ACTIVE.reset(token)


def _structured_sources(tool_name: str, result: dict) -> list[dict]:
    if result.get("status") != "ok":
        return []
    if tool_name == "web_search":
        return [item for item in result.get("results", []) if isinstance(item, dict)]
    if tool_name in {"web_fetch", "web_scrape"} and result.get("url"):
        return [{
            "url": result["url"],
            "title": result.get("title", ""),
            "publisher": result.get("publisher", ""),
            "published_at": result.get("published_at", ""),
            "snippet": str(result.get("text") or "")[:600],
        }]
    return []


def observe_web_result(tool_name: str, result: object) -> int:
    active = _ACTIVE.get()
    if active is None or not isinstance(result, dict):
        return 0
    run_id, task_id = active
    seen: set[str] = set()
    captured = 0
    for raw in _structured_sources(tool_name, result):
        source = normalize_source(raw)
        if not source.canonical_url or source.canonical_url in seen:
            continue
        seen.add(source.canonical_url)
        try:
            from core.services.research_store import add_source
            add_source(run_id, source, task_id=task_id)
            captured += 1
        except Exception:
            # Evidence observation must never break an ordinary web-tool call.
            continue
    return captured
