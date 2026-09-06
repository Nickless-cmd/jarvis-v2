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
from core.services.decision_evidence import (
    evidence_permits_verdict,
    gather_evidence,
)
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


def _build_review_prompt(decision: dict[str, Any], evidence: dict[str, Any] | None = None) -> str:
    directive = str(decision.get("directive") or "").strip()
    reason = str(decision.get("reason") or "").strip()
    regnskab = str((evidence or {}).get("summary") or "").strip()
    timer = (evidence or {}).get("window_hours")
    return (
        f"{identity_prompt_prefix()}. Du forpligtede dig på en adfærdsbeslutning og skal nu "
        "vurdere om du har holdt den siden sidste review.\n\n"
        f"Beslutning: {directive}\n"
        f"Grund: {reason}\n\n"
        f"REGNSKAB for de seneste {timer} timer — dette er hentet fra eventbus og "
        "git-log, ikke fra din hukommelse:\n"
        f"  {regnskab}\n\n"
        "Hold din vurdering op mod regnskabet, ikke mod hvad du mener at have gjort. "
        "Siger regnskabet at intet skete, kan du ikke have holdt en beslutning der "
        "kræver handling.\n"
        "Vurder: fulgte du den, delvist, eller brød du den?\n"
        "Format (præcis to linjer):\n"
        "  VERDICT: kept|partial|broken\n"
        "  REASONING: <kort sætning om hvorfor>\n"
    )


def _parse_review(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    verdict = ""
    reasoning = ""
    for raw in text.splitlines():
        line = raw.strip()
        upper = line.upper()
        if upper.startswith("VERDICT:"):
            v = line.split(":", 1)[1].strip().lower()
            for cand in ("kept", "partial", "broken"):
                if cand in v:
                    verdict = cand
                    break
        elif upper.startswith("REASONING:") or upper.startswith("EVIDENCE:"):
            # EVIDENCE beholdes som fallback: aeldre modelsvar bruger stadig det ord.
            # Uanset hvad, ender teksten i `note` — aldrig i `evidence`.
            reasoning = line.split(":", 1)[1].strip()
    if not verdict:
        return None
    return verdict, reasoning[:280]


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
    reviewed = skipped = failed = downgraded = 0
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

        # C3: hent regnskabet for vinduet SIDEN sidste review — eller det seneste
        # døgn hvis den aldrig er anmeldt. Det er dette, og ikke modellens
        # hukommelse, dommen skal holdes op mod.
        vindue_start = _last_review_time(full) or (now - timedelta(hours=_REVIEW_INTERVAL_HOURS))
        try:
            evidence = gather_evidence(since=vindue_start, until=now)
        except Exception as exc:
            logger.debug("decision_review: evidens fejlede %s: %s", decision_id, exc)
            evidence = {"has_evidence": False, "summary": "regnskab utilgængeligt",
                        "window_hours": _REVIEW_INTERVAL_HOURS}

        prompt = _build_review_prompt(full, evidence)
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
        paastand, reasoning = parsed
        # Porten: en positiv dom uden ydre spor bliver til "unknown", som det
        # rullende gennemsnit i append_review ignorerer. "broken" slipper altid
        # igennem — fraværet af handling ER ofte bruddet.
        verdict = evidence_permits_verdict(paastand, evidence)
        if verdict != paastand:
            downgraded += 1
            logger.info(
                "decision_review: %s nedgraderet %s→%s (intet ydre spor i %sh)",
                decision_id, paastand, verdict, evidence.get("window_hours"),
            )
        try:
            review_decision(
                decision_id=decision_id,
                verdict=verdict,
                note=reasoning or None,
                evidence=str(evidence.get("summary") or "") or None,
            )
            reviewed += 1
        except Exception as exc:
            logger.debug("decision_review: write fail %s: %s", decision_id, exc)
            failed += 1
    try:  # egress-fri central-binding (kun tal, ingen review-tekst)
        from core.services.central_core import central
        central().observe({"cluster": "review", "nerve": "decision_review",
                           "kind": "review_run", "considered": len(active),
                           "reviewed": reviewed, "failed": failed,
                           "downgraded": downgraded})
    except Exception:
        pass
    return {
        "status": "ok",
        "considered": len(active),
        "reviewed": reviewed,
        "skipped_recent": skipped,
        "failed": failed,
        "downgraded_no_evidence": downgraded,
    }


