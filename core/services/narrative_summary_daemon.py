"""Narrative summary daemon — Phase 2.5 of causal graph.

Periodically asks a cheap LLM to summarise the most recent backward
causal chain into a 1-2 sentence Danish narrative ("Du startede en
agentic-runde, kaldte tre værktøjer …"). The summary is persisted as
a ``narrative.summary`` event so the awareness section can render it
on the next prompt-assembly without doing any LLM work on the critical
path.

Why a daemon, not inline:
  - Inline LLM call inside prompt-assembly would add 1-3s per turn —
    exactly the kind of bottleneck we just spent today eliminating.
  - Narrative changes slowly; a 15-min cadence keeps the felt
    continuity fresh without burning tokens.

Why store as event vs new table:
  - Reuses existing eventbus/causal-edges plumbing — no schema
    migration. Future inference passes can even build causal_edges
    from narrative.summary back to its anchor (so Jarvis can ask
    "why did I summarise that arc this way?").

Flow:
  1. Find latest narrative-worthy anchor in last 90 min (same priority
     list as causal_narrative.py — single source of truth there).
  2. If we already summarised THIS anchor in the last hour, skip.
  3. Walk backward causal chain (depth 4, min_confidence 0.7).
  4. Build a compact prompt; call ``call_cheap_llm``.
  5. Persist ``narrative.summary`` event with caused_by = anchor_id.

Best-effort throughout — every step has a try/except. The daemon
never crashes the daemon manager loop on a failed LLM call.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.db import connect

logger = logging.getLogger(__name__)

_CADENCE_SECONDS = 15 * 60
_DEDUPE_WINDOW_MINUTES = 60  # don't re-summarise the same anchor within this window
_LOOKBACK_MINUTES = 90
_CHAIN_DEPTH = 4
_MIN_CONFIDENCE = 0.7
_MAX_SUMMARY_CHARS = 280  # cap to keep prompt section small

_last_tick_at: datetime | None = None


def _fetch_recent_anchor() -> dict | None:
    # Re-uses Phase 2's anchor priority. Importing from causal_narrative
    # keeps the priority list as a single source of truth.
    from core.services.prompt_sections.causal_narrative import (
        _ANCHOR_KINDS,
        LOOKBACK_MINUTES as _NARRATIVE_LOOKBACK,
    )
    cutoff = (
        datetime.now(UTC) - timedelta(minutes=max(_LOOKBACK_MINUTES, _NARRATIVE_LOOKBACK))
    ).isoformat()
    with connect() as c:
        for kind in _ANCHOR_KINDS:
            row = c.execute(
                "SELECT id, kind, created_at FROM events "
                "WHERE kind = ? AND created_at >= ? "
                "ORDER BY id DESC LIMIT 1",
                (kind, cutoff),
            ).fetchone()
            if row is not None:
                return {"id": int(row["id"]), "kind": str(row["kind"]),
                        "created_at": str(row["created_at"])}
    return None


def _already_summarised(anchor_event_id: int) -> bool:
    """True if we have a recent narrative.summary for this anchor."""
    cutoff = (datetime.now(UTC) - timedelta(minutes=_DEDUPE_WINDOW_MINUTES)).isoformat()
    with connect() as c:
        row = c.execute(
            "SELECT id FROM events WHERE kind = 'narrative.summary' "
            "AND created_at >= ? "
            "AND json_extract(payload_json, '$.anchor_event_id') = ? "
            "LIMIT 1",
            (cutoff, anchor_event_id),
        ).fetchone()
    return row is not None


def _build_chain(anchor_id: int) -> list[dict]:
    from core.services.causal_graph import query_causal_chain
    result = query_causal_chain(
        event_id=anchor_id,
        direction="backward",
        max_depth=_CHAIN_DEPTH,
        min_confidence=_MIN_CONFIDENCE,
    )
    return result.get("chain") or []


def _build_prompt(anchor: dict, chain: list[dict]) -> tuple[str, str]:
    """Return (system_prompt, user_message) for the LLM call."""
    system = (
        "Du opsummerer Jarvis' egen kausal-historik som korte refleksive "
        "sætninger på dansk. Stil: Jarvis selv som første-person-stemme, "
        "rolig og kort. 1-2 sætninger, max 280 tegn. Ingen punktopstilling, "
        "ingen tekniske event-navne — fortolk dem som handlinger. "
        "Svar KUN med selve refleksionen, ingen meta-kommentar."
    )
    chain_lines = []
    anchor_ts = anchor["created_at"][11:16] if len(anchor["created_at"]) >= 16 else ""
    chain_lines.append(f"NU ({anchor_ts}): {anchor['kind']}")
    for step in chain:
        ev = step.get("event") or {}
        ts = ev.get("created_at", "")[11:16] if len(ev.get("created_at", "")) >= 16 else ""
        chain_lines.append(f"  ← ({ts}): {ev.get('kind', '?')}")
    user = (
        "Causal chain leading to the current anchor event. "
        "Output: 1-2 sentence descriptive summary connecting the events as "
        "one coherent sequence. Neutral analytic tone, not first-person "
        "reflection.\n\n"
        + "\n".join(chain_lines)
    )
    return system, user


def _persist_summary(
    *, anchor_id: int, anchor_kind: str, summary: str, model: str
) -> int:
    """Insert narrative.summary event with caused_by = anchor_id."""
    from core.eventbus.bus import event_bus
    eid = event_bus.publish(
        "narrative.summary",
        {
            "anchor_event_id": anchor_id,
            "anchor_kind": anchor_kind,
            "summary": summary,
            "model": model,
            "generated_at": datetime.now(UTC).isoformat(),
        },
        caused_by=anchor_id,
        edge_kind="summarised_from",
    )
    return int(eid) if eid else 0


def run_summary_cycle() -> dict[str, Any]:
    """One cycle: find anchor, build chain, call LLM, persist event.

    Returns stats dict so daemon-manager logs are useful. Always returns;
    never raises out of the daemon path.
    """
    stats: dict[str, Any] = {"ran": True}

    try:
        anchor = _fetch_recent_anchor()
    except Exception as exc:
        logger.debug("narrative_summary: anchor fetch failed: %s", exc)
        return {"ran": False, "error": "anchor-fetch-failed"}

    if anchor is None:
        return {"ran": False, "reason": "no-anchor-in-window"}

    stats["anchor_id"] = anchor["id"]
    stats["anchor_kind"] = anchor["kind"]

    if _already_summarised(anchor["id"]):
        return {**stats, "ran": False, "reason": "already-summarised"}

    chain = _build_chain(anchor["id"])
    stats["chain_depth"] = len(chain)

    if not chain:
        # No high-confidence parents — nothing to summarise beyond
        # "this happened". Skip rather than burn an LLM call on a
        # one-line story.
        return {**stats, "ran": False, "reason": "empty-chain"}

    # ── Event-gate (Fase 2 Lag 5): fire the LLM narrative summary only when
    #    the active narrative thread actually moved (a new anchor, or a
    #    changed chain depth/age). Flag OFF → legacy behaviour (cadence +
    #    dedupe guards only). Fail-open. ──
    try:
        from core.services import event_gate
        if event_gate.event_driven_enabled():
            _relevant = {
                "anchor_id": float(anchor["id"]),
                "chain_depth": float(len(chain)),
            }
            if not event_gate.should_generative_fire("narrative_summary", _relevant):
                return {"skipped": "no_signal_change"}
    except Exception:
        pass  # fail-open

    system, user = _build_prompt(anchor, chain)

    try:
        from core.memory.inner_llm_enrichment import call_cheap_llm
        text = call_cheap_llm(system, user)
    except Exception as exc:
        logger.warning("narrative_summary: LLM call failed: %s", exc)
        return {**stats, "ran": False, "error": "llm-call-failed"}

    if not text or not text.strip():
        return {**stats, "ran": False, "reason": "empty-llm-response"}

    summary = text.strip()[:_MAX_SUMMARY_CHARS]
    stats["summary_chars"] = len(summary)

    try:
        eid = _persist_summary(
            anchor_id=anchor["id"],
            anchor_kind=anchor["kind"],
            summary=summary,
            model="cheap-llm-enrichment",  # provider chosen by lane router
        )
        stats["summary_event_id"] = eid
    except Exception as exc:
        logger.warning("narrative_summary: persist failed: %s", exc)
        return {**stats, "ran": False, "error": "persist-failed"}

    return stats


def tick_narrative_summary_daemon() -> dict[str, Any]:
    """Daemon-manager entry: run one cycle if cadence elapsed."""
    global _last_tick_at
    now = datetime.now(UTC)
    if _last_tick_at is not None:
        if (now - _last_tick_at).total_seconds() < _CADENCE_SECONDS:
            return {"ran": False, "reason": "cadence-not-elapsed"}
    try:
        result = run_summary_cycle()
        _last_tick_at = now
        return result
    except Exception as exc:
        logger.warning(
            "narrative_summary: cycle failed: %s", exc, exc_info=True
        )
        _last_tick_at = now
        return {"ran": False, "error": str(exc)}


def build_narrative_summary_surface() -> dict[str, Any]:
    """Mission Control surface for the latest narrative summary.

    Read-only projection over narrative.summary events. This gives System
    Cartographer a local MC surface marker for the daemon's runtime influence
    without adding a second truth store.
    """
    try:
        with connect() as c:
            row = c.execute(
                """SELECT id, payload_json, created_at
                   FROM events
                   WHERE kind = 'narrative.summary'
                   ORDER BY id DESC LIMIT 1"""
            ).fetchone()
    except Exception as exc:
        return {
            "active": False,
            "mode": "narrative-summary-daemon",
            "error": str(exc),
            "authority": "event-derived-read-only",
        }

    if row is None:
        return {
            "active": False,
            "mode": "narrative-summary-daemon",
            "latest_summary": "",
            "latest": None,
            "summary": "No narrative.summary event recorded yet.",
            "authority": "event-derived-read-only",
        }

    try:
        payload = json.loads(row["payload_json"] or "{}")
    except (ValueError, TypeError):
        payload = {}
    latest = {
        "event_id": int(row["id"]),
        "created_at": str(row["created_at"] or ""),
        "anchor_event_id": payload.get("anchor_event_id"),
        "anchor_kind": payload.get("anchor_kind"),
        "summary": str(payload.get("summary") or ""),
        "model": payload.get("model"),
    }
    return {
        "active": bool(latest["summary"]),
        "mode": "narrative-summary-daemon",
        "latest_summary": latest["summary"],
        "latest": latest,
        "summary": latest["summary"] or "Latest narrative.summary has no summary text.",
        "cadence_seconds": _CADENCE_SECONDS,
        "dedupe_window_minutes": _DEDUPE_WINDOW_MINUTES,
        "lookback_minutes": _LOOKBACK_MINUTES,
        "authority": "event-derived-read-only",
    }
