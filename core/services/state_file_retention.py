"""Rotation af operationelle state-filer i ``~/.jarvis-v2/state``.

Målt 2026-08-30 — fire filer havde aldrig fået ryddet:

    plan_proposals.json            400 poster, ALLE over 7 dage, ældste 125 dage
    pending_approvals.json         164 poster, 161 over 7 dage, ældste 125 dage
    in_flight_runs.json            110 poster, 108 over 7 dage, ældste 118 dage
    agentic_run_checkpoints.json    79 poster,  78 over 7 dage, ældste  47 dage

Til sammenligning roterer ``nudge_broend.json`` pænt (488 poster, ingen over
6 dage) — mønsteret findes altså i huset, det var bare ikke anvendt her.

De prompt-sektioner der læser filerne er session-scopede, så gamle poster fra
andre sessioner når aldrig Jarvis' prompt. De hober sig bare op. Det er derfor
rotation og ikke en hastesag: filerne er små, men de vokser uden loft, og en
zombie-post er stadig en post nogen en dag kommer til at tro på.

Vinduerne er bevidst rundhåndede — formålet er at fjerne det der er dødt uden
tvivl, ikke at trimme tæt på kanten. En kørende tur må ALDRIG kunne rammes.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta

# Felter der kan bære postens alder, i prioriteret rækkefølge. Filerne bruger
# forskellige navne (``created_at``, ``interrupted_at``, ``started_at`` …), så
# vi prøver dem i rækkefølge og bruger den første der kan parses.
_TS_FIELDS: tuple[str, ...] = (
    "resolved_at", "interrupted_at", "created_at", "started_at",
    "updated_at", "requested_at", "ts", "timestamp",
)

# fil → hvor længe en post må ligge før den er død.
# in_flight_runs er kortest: en tur der har været "i gang" i tre døgn er en
# zombie, ikke et arbejde. Resten er rundhåndede.
POLICIES: dict[str, int] = {
    "in_flight_runs.json": 3,
    "agentic_run_checkpoints.json": 7,
    "pending_approvals.json": 14,
    "plan_proposals.json": 30,
}


def _state_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".jarvis-v2", "state")


def parse_ts(value: object) -> datetime | None:
    """Tolk et tidsstempel. Ukendt form → None (posten regnes som ung)."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def record_age_days(record: object, now: datetime) -> float | None:
    """Postens alder i dage, eller None hvis den ikke bærer et brugbart stempel."""
    if not isinstance(record, dict):
        return None
    for field in _TS_FIELDS:
        if field in record:
            ts = parse_ts(record.get(field))
            if ts is not None:
                return (now - ts).total_seconds() / 86400.0
    return None


def select_expired(
    records: dict[str, object], *, max_age_days: int, now: datetime
) -> list[str]:
    """Nøgler på poster der er ældre end vinduet. Ren funktion.

    Poster UDEN brugbart tidsstempel beholdes altid — vi sletter aldrig noget
    vi ikke kan datere. Hellere en efterladt post end en slettet aktiv tur.
    """
    out: list[str] = []
    for key, rec in (records or {}).items():
        age = record_age_days(rec, now)
        if age is not None and age > max_age_days:
            out.append(str(key))
    return out


def prune_state_file(
    path: str, *, max_age_days: int, now: datetime | None = None
) -> int:
    """Fjern udløbne poster fra én fil. Returnér antal fjernede.

    Self-safe: enhver fejl (manglende fil, ugyldig JSON, uventet form) → 0.
    Skriver atomisk via tmp + replace, så en afbrudt kørsel aldrig efterlader
    en halv fil.
    """
    _now = now or datetime.now(UTC)
    try:
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not data:
            return 0
        expired = select_expired(data, max_age_days=max_age_days, now=_now)
        if not expired:
            return 0
        for key in expired:
            data.pop(key, None)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        os.replace(tmp, path)
        return len(expired)
    except Exception:
        return 0


def prune_all_state_files(*, now: datetime | None = None) -> dict[str, int]:
    """Kør rotationen på alle filer i ``POLICIES``. Returnér {fil: antal fjernet}."""
    directory = _state_dir()
    result: dict[str, int] = {}
    for name, days in POLICIES.items():
        removed = prune_state_file(
            os.path.join(directory, name), max_age_days=days, now=now
        )
        if removed:
            result[name] = removed
    return result
