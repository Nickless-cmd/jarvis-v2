"""Forced Dream Hypothesis Generation — 10% probability per heartbeat tick.

On each invocation, rolls a 10% chance. If it fires, picks a random cognitive
domain, synthesises a lightweight hypothesis, and upserts it via the standard
dream hypothesis signal table so it flows through the existing dream pipeline.

Hypotheses created here use signal_type="forced-hypothesis" and source_kind
"heartbeat-forced" to distinguish them from organically derived ones.
"""
from __future__ import annotations

import logging
import random
from datetime import UTC, datetime
from uuid import uuid4

from core.services.dream_domains import DOMAENER

logger = logging.getLogger(__name__)

# Probability that a given heartbeat tick forces a hypothesis
_FIRE_PROBABILITY = 0.10

# Domaenerne bor i `dream_domains` — droemme-kaeden foejer paa netop de navne,
# og de skal vaere de samme her og i `cadence_producers`. Da de kun stod her,
# var dette modul den eneste producent der skrev et emne kaeden kunne bruge.
_DOMAINS = list(DOMAENER.items())


def maybe_force_dream_hypothesis() -> dict[str, object] | None:
    """Roll 10% chance and if it fires upsert a forced dream hypothesis.

    Returns the upserted signal dict on fire, None otherwise.
    """
    if random.random() > _FIRE_PROBABILITY:
        return None

    domain_key, summary = random.choice(_DOMAINS)
    canonical_key = f"dream-hypothesis:forced:{domain_key}"
    now = datetime.now(UTC).isoformat()

    try:
        from core.runtime.db import upsert_runtime_dream_hypothesis_signal
        result = upsert_runtime_dream_hypothesis_signal(
            signal_id=f"forced-hypothesis-{uuid4().hex}",
            signal_type="forced-hypothesis",
            canonical_key=canonical_key,
            status="active",
            title=f"Forced hypothesis: {domain_key}",
            summary=summary,
            rationale="Genereret automatisk via heartbeat-forced pipeline (10% sandsynlighed pr. tick).",
            source_kind="heartbeat-forced",
            confidence="low",
            evidence_summary=f"Domain: {domain_key}. Fremkommet via probabilistisk forcing.",
            support_summary="Ingen ekstern støtte endnu — hypotesen er i sin tidligste fase.",
            support_count=1,
            session_count=1,
            created_at=now,
            updated_at=now,
            status_reason="Forced via heartbeat probabilistic trigger.",
        )
        logger.info(
            "dream_hypothesis_forced: fired — domain=%s canonical_key=%s",
            domain_key, canonical_key,
        )
        return result
    except Exception:
        logger.debug("dream_hypothesis_forced: upsert failed", exc_info=True)
        return None


