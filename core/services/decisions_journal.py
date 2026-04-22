"""Decisions Journal — moralsk beslutnings-log (extension of decision_log).

Bygger oven på eksisterende v2 `decision_log.py` + `cognitive_decisions`
tabel. Tilføjer det forgænger-modulet havde som v2 mangler:

- **Fingerprint-dedup** på (title, decision) — forhindrer duplikerede
  journal-entries med forskellige IDs
- **Token-based search** `find_relevant_decisions(query)` — find tidligere
  beslutninger relateret til en situation
- **`capture_decision_signal()`** — auto-journalisering fra runtime events
  med strong_signal-gate og integration med regret_engine

Porteret fra jarvis-ai/agent/cognition/decisions.py (2026-04-22).

LLM-path: ingen. Ren beslutnings-journal.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.runtime.db import (
    insert_cognitive_decision,
    list_cognitive_decisions,
)

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"[a-z0-9_\-/]{3,}", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN_PATTERN.finditer(str(text or ""))}


def _fingerprint(title: str, decision: str) -> str:
    return f"{str(title or '').strip().lower()}::{str(decision or '').strip().lower()}"


def create_decision_record(
    *,
    title: str,
    context: str,
    options: list[str],
    decision: str,
    why: str,
    regrets: list[str] | None = None,
    refs: list[str] | None = None,
) -> dict[str, Any]:
    """Journalize a decision. Required: title, decision, why.

    Dedups against existing decisions by (title, decision) fingerprint.
    Returns {"outcome": "completed" | "skipped" | "duplicate", ...}.
    """
    safe_title = str(title or "").strip()
    safe_decision = str(decision or "").strip()
    safe_why = str(why or "").strip()
    if not safe_title or not safe_decision or not safe_why:
        return {"outcome": "skipped", "reason": "missing_required_fields"}

    # Dedup by fingerprint
    fp = _fingerprint(safe_title, safe_decision)
    for existing in list_cognitive_decisions(limit=300):
        existing_fp = _fingerprint(
            str(existing.get("title") or ""),
            str(existing.get("decision") or ""),
        )
        if existing_fp == fp:
            return {
                "outcome": "duplicate",
                "reason": "existing_fingerprint",
                "record": existing,
            }

    from uuid import uuid4
    decision_id = f"dec-{uuid4().hex[:10]}"
    result = insert_cognitive_decision(
        decision_id=decision_id,
        title=safe_title,
        context=str(context or "").strip(),
        options=json.dumps(
            [s.strip() for s in (options or []) if str(s).strip()], ensure_ascii=False
        ),
        decision=safe_decision,
        why=safe_why,
        regrets=json.dumps(
            [s.strip() for s in (regrets or []) if str(s).strip()], ensure_ascii=False
        ),
        refs=json.dumps(
            [s.strip() for s in (refs or []) if str(s).strip()], ensure_ascii=False
        ),
    )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("cognitive_decision.journaled", {
            "decision_id": decision_id,
            "title": safe_title,
        })
    except Exception:
        pass
    return {"outcome": "completed", "record": result}


def capture_decision_signal(
    *,
    event_type: str,
    payload: dict[str, Any],
    refs: list[str] | None = None,
    strong_signal: bool = False,
    user_confirmed: bool = False,
) -> dict[str, Any]:
    """Capture an automatic decision-signal from runtime events.

    Requires strong_signal=True OR user_confirmed=True to persist.
    If outcome indicates failure, also opens a regret on the decision.
    """
    safe_event = str(event_type or "").strip()
    if not safe_event:
        return {"outcome": "skipped", "reason": "event_type_missing"}
    if not strong_signal and not user_confirmed:
        return {"outcome": "skipped", "reason": "confirmation_required"}

    title = f"Decision from {safe_event.replace('_', ' ').replace('.', ' ')}"
    context = str(payload.get("workspace_id") or payload.get("session_id") or "runtime")
    decision = str(
        payload.get("question")
        or payload.get("phrase")
        or payload.get("metric")
        or payload.get("tool")
        or safe_event
    )
    why = str(
        payload.get("reason")
        or payload.get("outcome")
        or payload.get("summary")
        or "Strong operational signal"
    )
    options: list[str] = []
    for key in ("question", "phrase", "metric", "signal_type", "tool"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            options.append(v.strip())

    result = create_decision_record(
        title=title, context=context, options=options[:4],
        decision=decision, why=why, regrets=[], refs=refs or [],
    )
    record = result.get("record") if isinstance(result, dict) else None

    # If we created a fresh decision and outcome suggests failure → open regret
    if (
        isinstance(record, dict)
        and result.get("outcome") == "completed"
    ):
        outcome = str(payload.get("outcome") or payload.get("status") or "").strip().lower()
        if outcome in {"failed", "error", "rejected", "degraded", "incident"}:
            try:
                from core.services.regret_engine import open_or_update_regret
                open_or_update_regret(
                    decision_id=str(record.get("decision_id") or ""),
                    context={"event_type": safe_event, "payload": payload},
                    expected_outcome="completed",
                    actual_outcome=outcome,
                    lesson=str(payload.get("reason") or "")[:200]
                           or "Outcome did not match completion.",
                    confidence_before=0.75,
                    confidence_after=0.35,
                )
            except Exception:
                pass
    return result


def find_relevant_decisions(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Token-overlap search: find decisions matching the query."""
    q_tokens = _tokens(query)
    if not q_tokens:
        return []
    rows = list_cognitive_decisions(limit=500)
    scored: list[tuple[int, dict[str, Any]]] = []
    for r in rows:
        hay = " ".join([
            str(r.get("title") or ""),
            str(r.get("context") or ""),
            str(r.get("decision") or ""),
            str(r.get("why") or ""),
        ])
        overlap = len(q_tokens & _tokens(hay))
        if overlap > 0:
            scored.append((overlap, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:max(1, int(limit))]]


def build_decisions_journal_surface() -> dict[str, Any]:
    """MC surface for decisions journal (extension view vs decision_log's basic view)."""
    recent = list_cognitive_decisions(limit=10)
    active = bool(recent)
    summary = f"{len(recent)} journaliserede beslutninger"
    if recent:
        top = str(recent[0].get("title") or "")[:60]
        summary += f" — seneste: {top}"
    return {
        "active": active,
        "summary": summary,
        "recent": recent,
        "total_visible": len(recent),
    }
