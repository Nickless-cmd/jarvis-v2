"""Evidence-bounded world facts and their visible prompt representation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from core.runtime.db_world_self_truth import insert_world_fact, select_world_facts


_WORLD_FACT_STATUSES = {
    "observed",
    "reported",
    "verified",
    "contradicted",
    "stale",
    "superseded",
}
_PROMPT_STATUSES = ("verified", "observed", "reported", "contradicted")

# En samtale der SIGER at noget er sandt, er et RYGTE — ikke en iagttagelse.
# `observed` betyder «runtimen saa det ske»; `verified` betyder «det er
# efterproevet mod en kilde». Ingen af delene kan en beskedtekst levere, uanset
# hvor sikkert den er formuleret. Uden denne graense kan enhver der skriver til
# Jarvis forfremme sin egen paastand til husets sandhed ved at formulere den
# skarpt nok.
_SAMTALE_KILDER = {"conversation_report", "conversation", "chat_report"}

# Status der KRAEVER at man kan pege paa hvor det kommer fra. En «verificeret»
# kendsgerning uden kildehenvisning er en paastand med et finere ord.
_KRAEVER_KILDEHENVISNING = {"verified"}

# Status en samtale ikke kan give.
_KRAEVER_FOERSTEHAAND = {"observed", "verified"}


def record_world_fact(
    *,
    canonical_key: str,
    statement: str,
    status: str,
    confidence: str,
    source_kind: str,
    source_ref: str = "",
    observed_at: str = "",
    valid_from: str = "",
    valid_until: str = "",
    contradicts_fact_id: str = "",
    supersedes_fact_id: str = "",
    evidence_count: int = 1,
    distinct_source_count: int = 1,
) -> dict[str, object]:
    normalized_key = str(canonical_key or "").strip()
    normalized_statement = " ".join(str(statement or "").split()).strip()
    normalized_status = str(status or "").strip().lower()
    if not normalized_key:
        raise ValueError("canonical_key is required")
    if not normalized_statement:
        raise ValueError("statement is required")
    if normalized_status not in _WORLD_FACT_STATUSES:
        raise ValueError(f"unsupported world fact status: {status}")
    normalized_kind = str(source_kind or "").strip().lower()
    if (normalized_status in _KRAEVER_FOERSTEHAAND
            and normalized_kind in _SAMTALE_KILDER):
        raise ValueError(
            f"conversation-derived evidence cannot assert status "
            f"{normalized_status!r}: a report that something is true is not an "
            "observation of it. Use 'reported'."
        )
    if (normalized_status in _KRAEVER_KILDEHENVISNING
            and not str(source_ref or "").strip()):
        raise ValueError(
            f"status {normalized_status!r} requires a concrete source_ref — "
            "a verified fact you cannot point back to is a claim with a "
            "finer word."
        )
    now = datetime.now(UTC).isoformat()
    return insert_world_fact(
        fact_id=f"fact-{uuid4().hex}",
        canonical_key=normalized_key,
        statement=normalized_statement,
        status=normalized_status,
        confidence=str(confidence or "").strip().lower(),
        source_kind=str(source_kind or "").strip(),
        source_ref=str(source_ref or "").strip(),
        observed_at=str(observed_at or "").strip() or now,
        valid_from=str(valid_from or "").strip(),
        valid_until=str(valid_until or "").strip(),
        contradicts_fact_id=str(contradicts_fact_id or "").strip(),
        supersedes_fact_id=str(supersedes_fact_id or "").strip(),
        evidence_count=evidence_count,
        distinct_source_count=distinct_source_count,
        created_at=now,
        updated_at=now,
    )


def list_world_facts(
    *,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    statuses = [status] if status else None
    return select_world_facts(statuses=statuses, limit=limit)


def build_world_fact_prompt_section(
    *,
    limit: int = 8,
    facts: list[dict[str, object]] | None = None,
) -> str | None:
    relevant = facts if facts is not None else select_world_facts(
        statuses=_PROMPT_STATUSES,
        limit=limit,
    )
    status_rank = {status: rank for rank, status in enumerate(_PROMPT_STATUSES)}
    ordered = sorted(
        (
            fact
            for fact in relevant
            if str(fact.get("status") or "") in _PROMPT_STATUSES
        ),
        key=lambda fact: status_rank[str(fact.get("status") or "")],
    )[: max(int(limit), 1)]
    if not ordered:
        return None

    lines = ["Verified/observed world facts:"]
    for fact in ordered:
        status = str(fact.get("status") or "")
        statement = " ".join(str(fact.get("statement") or "").split()).strip()
        if not statement:
            continue
        details = [
            value
            for value in (
                f"confidence={str(fact.get('confidence') or '').strip()}",
                f"source={str(fact.get('source_kind') or '').strip()}",
                f"source_ref={str(fact.get('source_ref') or '').strip()}",
                f"contradicts={str(fact.get('contradicts_fact_id') or '').strip()}",
                f"supersedes={str(fact.get('supersedes_fact_id') or '').strip()}",
            )
            if not value.endswith("=")
        ]
        suffix = f" ({'; '.join(details)})" if details else ""
        lines.append(f"- [{status}] {statement}{suffix}")
    if len(lines) == 1:
        return None
    lines.append(
        "Treat reported facts as unverified reports; verified and observed evidence outrank them."
    )
    return "\n".join(lines)

