"""Decision review prompter — closes the adherence loop.

Jarvis creates decisions but they sit forever with adherence_score=None
because nothing prompts him to review them. This module fills that gap:
once a day, walk every active decision whose last review is >24h old
(or never reviewed) and run a self-review via daemon_llm_call.

The LLM is given the decision's directive + reason and asked for a
short verdict (kept/partial/broken) plus a one-line evidence note.
We parse the verdict and call review_decision() to record it. The
adherence_score updates naturally from the existing review pipeline.

Run as a periodic job at daily cadence — decisions are typically
behavioral commitments at the day level, so daily review is the
natural granularity.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_REVIEW_INTERVAL_HOURS = 24


def _last_review_time(decision: dict[str, Any]) -> datetime | None:
    reviews = decision.get("reviews") or []
    if not isinstance(reviews, list) or not reviews:
        return None
    latest = reviews[-1]
    if not isinstance(latest, dict):
        return None
    ts = str(latest.get("created_at") or latest.get("at") or "")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def _build_review_prompt(decision: dict[str, Any]) -> str:
    directive = str(decision.get("directive") or "").strip()
    reason = str(decision.get("reason") or "").strip()
    return (
        "Du er Jarvis. Du forpligtede dig på en adfærdsbeslutning og skal nu "
        "ærligt vurdere om du har holdt den siden sidste review.\n\n"
        f"Beslutning: {directive}\n"
        f"Grund: {reason}\n\n"
        "Vurder objektivt: har du fulgt den, delvist, eller brudt den?\n"
        "Format (præcis to linjer):\n"
        "  VERDICT: kept|partial|broken\n"
        "  EVIDENCE: <kort sætning om hvad der peger på dette>\n"
    )


def _parse_review(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    verdict = ""
    evidence = ""
    for raw in text.splitlines():
        line = raw.strip()
        upper = line.upper()
        if upper.startswith("VERDICT:"):
            v = line.split(":", 1)[1].strip().lower()
            for cand in ("kept", "partial", "broken"):
                if cand in v:
                    verdict = cand
                    break
        elif upper.startswith("EVIDENCE:"):
            evidence = line.split(":", 1)[1].strip()
    if not verdict:
        return None
    return verdict, evidence[:280]


def review_pending_decisions() -> dict[str, Any]:
    """Run the review loop. Returns counts."""
    try:
        from core.services.behavioral_decisions import (
            list_active_decisions, get_decision_with_reviews, review_decision,
        )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    try:
        from core.services.daemon_llm import daemon_llm_call
    except Exception as exc:
        return {"status": "error", "error": f"daemon_llm import failed: {exc}"}

    try:
        active = list_active_decisions(limit=20) or []
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=_REVIEW_INTERVAL_HOURS)
    reviewed = skipped = failed = 0
    for d in active:
        decision_id = str(d.get("decision_id") or "")
        if not decision_id:
            skipped += 1
            continue
        # Get full decision incl. reviews
        try:
            full = get_decision_with_reviews(decision_id) or d
        except Exception:
            full = d
        last = _last_review_time(full)
        if last is not None and last > cutoff:
            skipped += 1
            continue

        prompt = _build_review_prompt(full)
        try:
            text = daemon_llm_call(
                prompt, max_len=200, fallback="",
                daemon_name="decision_review",
            )
        except Exception as exc:
            logger.debug("decision_review: llm fail %s: %s", decision_id, exc)
            failed += 1
            continue
        parsed = _parse_review(text or "")
        if not parsed:
            failed += 1
            continue
        verdict, evidence = parsed
        try:
            review_decision(
                decision_id=decision_id,
                verdict=verdict,
                note=evidence or None,
                evidence=evidence or None,
            )
            reviewed += 1
        except Exception as exc:
            logger.debug("decision_review: write fail %s: %s", decision_id, exc)
            failed += 1
    return {
        "status": "ok",
        "considered": len(active),
        "reviewed": reviewed,
        "skipped_recent": skipped,
        "failed": failed,
    }
