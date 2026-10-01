"""Ugentlig digest over kandidat-review-køen — så køen ikke hober op i tavshed.

## Hvorfor (1/10-2026)

Bjørn spurgte: «5.228 er jo alt for meget — og hvorfor er der ikk nogen der ser
dem? jeg modtager intet om dem?» Målt samme dag: `runtime_contract_candidates`
stod på 5.231 `proposed`, og svaret var strukturelt. Der FINDES en flade
(`GET /mission-control/memory-pipeline`), men den er **pull, ikke push**: den
tæller kun `target_file='MEMORY.md'`, og den sender intet signal. Bjørn skal
selv åbne HUD'en og kigge — så i praksis ser han dem aldrig.

Kandidaterne venter på et MENNESKE. Gaten er graderet
(`gate_memory.memory_promotion_gate`): GREEN = auto-apply, YELLOW = «kø til
review», RED = injection-afvist. YELLOW er pr. definition en beslutning der
kræver Bjørn — og uden en push-vej bliver den aldrig truffet. Den her daemon er
push-vejen: én kort, ærlig besked i ugen med tal og alder, så køen kan ses og
tømmes.

## Design

- **Self-throttle, ugentligt.** Kadence i modulets egen tilstand (som
  `memory_pruning_daemon`), ikke en ekstern timer. Kaldes ubetinget fra
  memory-familien; den tier selv indtil ugen er gået.
- **Kun når der er noget at rapportere.** Under `_MIN_TOTAL_TO_REPORT` sendes
  intet — en digest der siger «0 venter» hver uge er baggrundslyd, ikke et vink.
- **Self-safe.** En fejlet notifikation må ikke vælte daemonen eller familien.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

#: Én gang i ugen. Køen vokser ~87 rækker/dag; sjældnere end ugentligt gør
#: beskeden til en overraskelse, hyppigere gør den til støj.
_CADENCE_HOURS = 168
#: Under dette tal er der intet at rapportere — så tier daemonen.
_MIN_TOTAL_TO_REPORT = 50

#: De typer der faktisk venter på et menneske. `chronicle_draft` er med vilje
#: IKKE her: den har ingen auto-apply-vej og pensioneres efter 7 dage (se
#: `events_retention._CANDIDATE_TYPE_MAX_AGE`) — den er bogføring, ikke review.
_REVIEW_TYPES = ("memory_promotion", "preference_update", "prompt_feedback_update")

_last_tick_at: datetime | None = None
_last_result: dict[str, object] = {}


def build_candidate_review_digest() -> dict[str, object]:
    """Tæl de review-bare kandidater pr. type og find den ældste. Read-only, self-safe."""
    out: dict[str, object] = {
        "total_proposed": 0,
        "by_type": {},
        "oldest_days": None,
        "oldest_type": "",
    }
    try:
        from core.runtime.db import connect
    except Exception as exc:  # self-safe: uden DB er der intet at rapportere
        return {**out, "error": str(exc)[:120]}
    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT candidate_type, COUNT(*) AS n, MIN(created_at) AS aeldst "
                "FROM runtime_contract_candidates "
                "WHERE status = 'proposed' AND candidate_type IN "
                "(?, ?, ?) "
                "GROUP BY candidate_type",
                _REVIEW_TYPES,
            ).fetchall()
    except Exception as exc:  # self-safe: en laesefejl maa ikke vaelte daemonen
        return {**out, "error": str(exc)[:120]}

    by_type: dict[str, int] = {}
    oldest_days: int | None = None
    oldest_type = ""
    now = datetime.now(UTC)
    for row in rows:
        ctype = str(row[0])
        count = int(row[1] or 0)
        if count <= 0:
            continue
        by_type[ctype] = count
        raw = str(row[2] or "")
        if not raw:
            continue
        try:
            age = (now - datetime.fromisoformat(raw)).days
        except ValueError:  # ugyldigt tidsstempel — spring alderen over, behold tallet
            continue
        if oldest_days is None or age > oldest_days:
            oldest_days = age
            oldest_type = ctype

    return {
        **out,
        "total_proposed": sum(by_type.values()),
        "by_type": by_type,
        "oldest_days": oldest_days,
        "oldest_type": oldest_type,
    }


def format_candidate_review_digest(digest: dict[str, object]) -> str:
    """Kort, ærlig tekst. Kun tal der faktisk står i digest'en."""
    total = int(digest.get("total_proposed") or 0)
    if total <= 0:
        return ""
    by_type = digest.get("by_type") or {}
    dele = ", ".join(f"{n} {t.replace('_', ' ')}" for t, n in sorted(
        by_type.items(), key=lambda kv: -int(kv[1])
    ))
    linje = f"🧠 Kandidat-køen venter på dig: {total} forslag ({dele})."
    oldest_days = digest.get("oldest_days")
    if isinstance(oldest_days, int) and oldest_days > 0:
        linje += f" De ældste er {oldest_days} dage gamle."
    linje += " Gennemgå dem i Mission Control → memory-pipeline."
    return linje


def tick_candidate_review_digest() -> dict[str, object]:
    """Send ugentlig digest hvis køen er stor nok. Self-throttle, self-safe."""
    global _last_tick_at, _last_result

    now = datetime.now(UTC)
    if _last_tick_at is not None and (now - _last_tick_at) < timedelta(hours=_CADENCE_HOURS):
        return {"sent": False, "reason": "cadence"}

    digest = build_candidate_review_digest()
    total = int(digest.get("total_proposed") or 0)
    _last_tick_at = now

    if total < _MIN_TOTAL_TO_REPORT:
        _last_result = {"sent": False, "reason": "below-threshold", "total": total}
        return dict(_last_result)

    text = format_candidate_review_digest(digest)
    sent = False
    try:
        from core.services.notification_bridge import send_session_notification

        r = send_session_notification(text, source="candidate-review-digest")
        sent = str(r.get("status") or "") not in {"error", ""}
    except Exception as exc:  # self-safe: en fejlet besked maa ikke vaelte daemonen
        logger.warning("candidate_review_digest: send failed: %s", exc)

    _last_result = {"sent": sent, "total": total, "text": text[:300]}
    if sent:
        try:
            from core.eventbus.bus import event_bus

            event_bus.publish(
                "candidate_review_digest.sent",
                {"total": total, "by_type": digest.get("by_type") or {},
                 "sent_at": now.isoformat()},
            )
        except Exception as exc:  # self-safe: telemetri er ikke kritisk
            logger.debug("candidate_review_digest: event publish failed: %s", exc)
    return dict(_last_result)


def build_candidate_review_digest_surface() -> dict[str, object]:
    """State til Mission Control / health-visninger."""
    return {
        "last_tick_at": _last_tick_at.isoformat() if _last_tick_at else "",
        "last_result": _last_result,
    }
