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
from core.services.identity_composer import identity_prompt_prefix

logger = logging.getLogger(__name__)


_REVIEW_INTERVAL_HOURS = 24

# GATE-FLAG (2026-07-15): den 24t-anti-gentagelses-gate nedenfor var reelt DØD pga. en
# nøgle-mismatch (læste 'reviews', men get_decision_with_reviews skriver 'recent_reviews'),
# så HVER aktiv beslutning blev genanmeldt på HVER tick → decision_review var den absolut
# største cheap-lane-brænder (~halvdelen af al daemon-LLM-trafik, ~halvdelen til deepseek/
# inner_enrichment-lanen). Gaten er nu rettet + flag-styret så den kan rulles tilbage.
#   'on'/True (DEFAULT) → spring beslutninger anmeldt inden for 24t over (den TILSIGTEDE adfærd).
#   'off'/False         → gammel adfærd (anmeld altid) — kun til fejlsøgning.
_DEDUP_GATE_FLAG = "decision_review_dedup_gate"


def _dedup_gate_enabled() -> bool:
    """Er 24t-skip-gaten aktiv? Default TRUE (den reducerede, tilsigtede adfærd)."""
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool(_DEDUP_GATE_FLAG, True)
    except Exception:
        return True


def _last_review_time(decision: dict[str, Any]) -> datetime | None:
    """Nyeste review-tidspunkt for en beslutning.

    RETTELSE (2026-07-15): læs 'recent_reviews' (det get_decision_with_reviews faktisk
    udfylder) med 'reviews' som fallback. list_reviews returnerer NYESTE-først (created_at
    DESC), så vi tager det MAKSIMALE gyldige tidsstempel i stedet for et fast indeks —
    robust uanset rækkefølge. FØR: læste 'reviews' (altid tom) + tog [-1] (ældste ved DESC)
    → gaten trippede aldrig → gentagne genanmeldelser."""
    reviews = decision.get("recent_reviews")
    if not isinstance(reviews, list) or not reviews:
        reviews = decision.get("reviews") or []
    if not isinstance(reviews, list) or not reviews:
        return None
    latest: datetime | None = None
    for entry in reviews:
        if not isinstance(entry, dict):
            continue
        ts = str(entry.get("created_at") or entry.get("at") or "")
        if not ts:
            continue
        try:
            parsed = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if latest is None or parsed > latest:
            latest = parsed
    return latest


def _build_review_prompt(decision: dict[str, Any]) -> str:
    directive = str(decision.get("directive") or "").strip()
    reason = str(decision.get("reason") or "").strip()
    return (
        f"{identity_prompt_prefix()}. Du forpligtede dig på en adfærdsbeslutning og skal nu "
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


def review_pending_decisions(*, max_reviews: int | None = None) -> dict[str, Any]:
    """Run the review loop. Returns counts.

    ``max_reviews`` caps the number of ACTUAL LLM reviews performed in this
    invocation (skips don't count). Bounds burst load on the quality lane even
    if the 24h gate has an edge case. None → no cap (walk all active decisions).
    """
    try:
        from core.services.behavioral_decisions import (
            list_active_decisions, get_decision_with_reviews, review_decision,
        )
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
    try:
        # Decision-review koblet direkte til adherence — quality lane (deepseek-v4-flash).
        from core.services.daemon_llm import quality_daemon_llm_call as daemon_llm_call
    except Exception as exc:
        return {"status": "error", "error": f"daemon_llm import failed: {exc}"}

    try:
        active = list_active_decisions(limit=20) or []
    except Exception as exc:
        return {"status": "error", "error": str(exc)}

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=_REVIEW_INTERVAL_HOURS)
    gate_on = _dedup_gate_enabled()
    reviewed = skipped = failed = 0
    for d in active:
        if max_reviews is not None and reviewed >= max_reviews:
            # Per-tick cap reached — remaining overdue decisions wait for the
            # next tick. Counted as skipped so observability stays honest.
            skipped += 1
            continue
        decision_id = str(d.get("decision_id") or "")
        if not decision_id:
            skipped += 1
            continue
        # Get full decision incl. reviews
        try:
            full = get_decision_with_reviews(decision_id) or d
        except Exception:
            full = d
        # 24h anti-repeat gate (flag-guarded; default on = intended behavior).
        if gate_on:
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
    try:  # egress-fri central-binding (kun tal, ingen review-tekst)
        from core.services.central_core import central
        central().observe({"cluster": "review", "nerve": "decision_review",
                           "kind": "review_run", "considered": len(active),
                           "reviewed": reviewed, "failed": failed})
    except Exception:
        pass
    return {
        "status": "ok",
        "considered": len(active),
        "reviewed": reviewed,
        "skipped_recent": skipped,
        "failed": failed,
    }


