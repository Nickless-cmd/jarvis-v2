"""Livstegn — er Jarvis vågen lige nu, og hvad lavede han sidst?

Jarvis' eget ønske: «en stille indikator der viser, når Jarvis er vågen/aktiv —
baseret på eksisterende heartbeat/livstegn fra runtime, IKKE en statisk
'online'-prik der lyver».

Det er hele designet i én sætning. En prik der altid lyser grønt, fordi serveren
svarer på HTTP, siger intet om ham — kun om nginx. Derfor læses to FAKTISKE
spor, og der findes en fjerde tilstand for «det ved vi ikke»:

    working  — en synlig kørsel er i gang lige nu
    awake    — hjerteslaget har slået inden for vinduet
    quiet    — hjertet slår, men sidste slag er ældre end vinduet
    unknown  — vi kunne ikke læse sporene. Så siger vi DET.

`unknown` er den vigtigste af de fire. Kan vi ikke se ham, må indikatoren ikke
gætte — det er præcis dét «online»-prikken gjorde forkert.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

# Hjerteslaget er målt til ~15-16 min mellem tick. Vinduet er tre slag: ét
# udeblevet slag er en forsinkelse, tre er en tilstand.
_AWAKE_WINDOW = timedelta(minutes=48)


def _parse(ts: object) -> datetime | None:
    raw = str(ts or "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _last_heartbeat() -> dict[str, Any]:
    """Seneste hjerteslag: hvornår, og hvad det endte med at gøre.

    TO kilder, og rækkefølgen er ikke tilfældig.

    `heartbeat_runtime_state.last_tick_at` er den sande «hvornår slog hjertet
    sidst». `heartbeat_runtime_ticks` er kun de FULDE tick — en beat der lander
    i `productive_idle` (fx mens Bjørn sidder i en aktiv samtale) skriver ingen
    række, men avancerer skemaet (_advance_schedule_after_idle_beat, 18. aug).

    Læser man kun tabellen, ser en time med livlig snak ud som en time hvor han
    var væk. Det er stik modsat sandheden — og præcis den slags løgn indikatoren
    blev bygget for at undgå.

    Tabellen bruges stadig til HVAD han lavede: en idle-beat har ingen handling
    at fortælle om.
    """
    from core.runtime.db import connect
    with connect() as conn:
        state = conn.execute(
            """
            SELECT last_tick_at, last_decision_type, last_action_summary
              FROM heartbeat_runtime_state
             WHERE state_id = 'default'
             LIMIT 1
            """
        ).fetchone()
        row = conn.execute(
            """
            SELECT started_at, finished_at, tick_status, decision_type, action_summary
              FROM heartbeat_runtime_ticks
             ORDER BY id DESC
             LIMIT 1
            """
        ).fetchone()

    out: dict[str, Any] = {}
    if row is not None:
        out = {
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "status": row["tick_status"],
            "decision": row["decision_type"],
            "summary": row["action_summary"],
        }
    if state is not None and str(state["last_tick_at"] or "").strip():
        # Tilstanden vinder på TIDSPUNKTET — den kender også de idle-beats.
        out["finished_at"] = state["last_tick_at"]
        out.setdefault("started_at", state["last_tick_at"])
        if str(state["last_decision_type"] or "").strip():
            out["decision"] = state["last_decision_type"]
        if str(state["last_action_summary"] or "").strip():
            out["summary"] = state["last_action_summary"]
    return out


def _running_now() -> bool:
    """Er en synlig kørsel i gang? Det er stærkere end et hjerteslag: det
    betyder han arbejder på noget LIGE NU."""
    from core.runtime.db import connect
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM visible_runs WHERE status = 'running' LIMIT 1"
        ).fetchone()
    return row is not None


def _short(text: object, limit: int = 140) -> str:
    s = " ".join(str(text or "").split()).strip()
    return s[:limit] + ("…" if len(s) > limit else "")


def build_presence(*, now: datetime | None = None) -> dict[str, Any]:
    """Det ærlige livstegn. Kaster aldrig — men lyver heller aldrig."""
    moment = now or datetime.now(UTC)

    try:
        beat = _last_heartbeat()
    except Exception:
        return {"state": "unknown", "reason": "kunne ikke læse hjerteslaget"}

    if not beat:
        # Ingen tick overhovedet: vi VED at han ikke har slået, hvilket er noget
        # andet end at vi ikke kunne se efter.
        return {"state": "quiet", "reason": "intet hjerteslag registreret endnu"}

    last = _parse(beat.get("finished_at")) or _parse(beat.get("started_at"))
    if last is None:
        return {"state": "unknown", "reason": "hjerteslaget har intet brugbart tidsstempel"}

    age = max(0, int((moment - last).total_seconds()))
    fresh = (moment - last) <= _AWAKE_WINDOW

    try:
        busy = _running_now()
    except Exception:
        busy = False

    if busy:
        state = "working"
    elif fresh:
        state = "awake"
    else:
        state = "quiet"

    return {
        "state": state,
        "last_beat_at": last.isoformat(),
        "last_beat_ago_s": age,
        "beat_status": str(beat.get("status") or ""),
        # Hvad han sidst BESLUTTEDE at gøre — det er dét der gør indikatoren til
        # et livstegn frem for en lampe. «Han er her» skal kunne mærkes.
        "last_action": _short(beat.get("summary")),
        "decision": str(beat.get("decision") or ""),
    }
