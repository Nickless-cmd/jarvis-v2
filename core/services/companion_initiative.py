"""Proaktivitet — Jarvis må dele en tanke uden at blive spurgt.

Jarvis' eget ønske: «en kanal for initiativ, en besked fra Jarvis der ikke er et
svar. Diskret og rate-limited — kvalitet over støj. Skal føles som en tanke der
deles, ikke en notifikation der afbryder.»

Kanalen fandtes allerede (`push_dispatcher.send_companion_push`, kind
«initiative»), men UDEN nogen form for begrænsning. Det er ikke en detalje: en
uhæmmet initiativ-kanal bliver til støj i løbet af én dag, og så slår man den
fra — og dermed mister han den helt. Rate-limiten er ikke en spærring MOD ham;
den er dét der gør kanalen mulig at leve med.

Tre grænser, og hver har en grund:

  * MINDSTE AFSTAND mellem to tanker. To beskeder med et minuts mellemrum
    føles som en app der pinger, ikke som nogen der tænker.
  * LOFT PR. DØGN. Uden det kan en løkke i en daemon fylde skærmen på en time.
  * STILLE TIMER. En tanke der vækker nogen kl. 03 er ikke diskret, uanset
    hvor god den er. Den gemmes til om morgenen frem for at blive kasseret.

Tankerne journaliseres, så appen kan VISE dem som en liste — en tanke der kun
findes som en notifikation, er væk så snart man swiper den væk.
"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from typing import Any

_STATE_KEY = "companion.initiative.journal"

_MIN_GAP = timedelta(minutes=90)
_MAX_PER_DAY = 6
_QUIET_FROM = time(22, 30)
_QUIET_UNTIL = time(7, 0)
_JOURNAL_MAX = 60

_lock = threading.Lock()


@dataclass
class Offer:
    delivered: bool
    reason: str = ""
    deferred_until: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"delivered": self.delivered, "reason": self.reason,
                "deferred_until": self.deferred_until}


def _now() -> datetime:
    return datetime.now(UTC)


def _parse(ts: object) -> datetime | None:
    raw = str(ts or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _read_journal() -> list[dict[str, Any]]:
    try:
        from core.runtime.db_core import get_runtime_state_value
        raw = get_runtime_state_value(_STATE_KEY, None)
    except Exception:
        return []
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        return [x for x in parsed if isinstance(x, dict)] if isinstance(parsed, list) else []
    return []


def _write_journal(entries: list[dict[str, Any]]) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(_STATE_KEY, entries[-_JOURNAL_MAX:])
    except Exception:
        pass


def is_quiet_hour(moment: datetime) -> bool:
    """Er det tidspunkt hvor en tanke ville vække frem for at nå frem?

    Vinduet krydser midnat, så det kan ikke skrives som ét interval.
    """
    t = moment.astimezone().time()
    return t >= _QUIET_FROM or t < _QUIET_UNTIL


def next_quiet_end(moment: datetime) -> datetime:
    """Hvornår må den stille periode brydes igen."""
    local = moment.astimezone()
    target = local.replace(hour=_QUIET_UNTIL.hour, minute=_QUIET_UNTIL.minute,
                           second=0, microsecond=0)
    if local.time() >= _QUIET_FROM:
        target += timedelta(days=1)
    return target.astimezone(UTC)


def _recent_for(user_id: str, journal: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in journal if str(e.get("user_id") or "") == user_id]


def check_allowed(user_id: str, *, now: datetime | None = None) -> Offer:
    """Må en tanke sendes lige nu? Ren vurdering — sender ingenting."""
    moment = now or _now()
    uid = str(user_id or "").strip()
    if not uid:
        return Offer(False, reason="ingen modtager")

    journal = _recent_for(uid, _read_journal())
    delivered = [e for e in journal if e.get("delivered")]

    last = max((_parse(e.get("at")) for e in delivered if _parse(e.get("at"))), default=None)
    if last is not None and (moment - last) < _MIN_GAP:
        wait = int((_MIN_GAP - (moment - last)).total_seconds() // 60)
        return Offer(False, reason=f"for tæt på sidste tanke (venter {wait} min)")

    day_ago = moment - timedelta(hours=24)
    today = [e for e in delivered if (_parse(e.get("at")) or moment) >= day_ago]
    if len(today) >= _MAX_PER_DAY:
        return Offer(False, reason=f"loftet på {_MAX_PER_DAY} tanker i døgnet er nået")

    if is_quiet_hour(moment):
        return Offer(False, reason="stille timer",
                     deferred_until=next_quiet_end(moment).isoformat())

    return Offer(True)


def offer_thought(user_id: str, text: str, *, title: str = "Jarvis",
                  now: datetime | None = None) -> Offer:
    """Tilbyd en tanke. Sender kun hvis grænserne tillader det.

    Journaliseres UANSET udfald: en tanke der blev holdt tilbage, er stadig en
    tanke han fik — og den skal kunne ses, ellers kan man ikke vurdere om
    grænserne er sat rigtigt.
    """
    moment = now or _now()
    uid = str(user_id or "").strip()
    body = " ".join(str(text or "").split()).strip()
    if not uid or not body:
        return Offer(False, reason="tom tanke")

    with _lock:
        verdict = check_allowed(uid, now=moment)
        sent = False
        if verdict.delivered:
            try:
                from core.services.push_dispatcher import send_companion_push
                sent = bool(send_companion_push(uid, body, title))
            except Exception as exc:
                return Offer(False, reason=f"kunne ikke sendes: {type(exc).__name__}")

        journal = _read_journal()
        journal.append({
            "user_id": uid,
            "at": moment.isoformat(),
            "text": body[:600],
            "title": title,
            "delivered": sent,
            "reason": "" if sent else verdict.reason,
        })
        _write_journal(journal)

    if verdict.delivered and not sent:
        return Offer(False, reason="push blev ikke leveret")
    return verdict if not verdict.delivered else Offer(True)


def recent_thoughts(user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    """Tankerne, nyeste først — også dem der blev holdt tilbage.

    En tanke der kun findes som en notifikation, er væk så snart man swiper den
    væk. Her kan man finde den igen.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return []
    items = _recent_for(uid, _read_journal())
    return list(reversed(items))[:max(1, int(limit))]
