"""Cache-bevidst microcompact af gamle tool-resultater i det synlige transcript.

Bjoern 18/9-2026: «kør den cache-bevidste vej kun når cachen faktisk er
brudt, og brug de målte tal frem for et estimat». Den maalte virkelighed
vendte opgaven om, saa den staar her.

## Hvad der var galt med 60-minutters-gaettet

Maalt paa CT105 19/9 (86 betalte ture efter caching-rettelsen 11/9, foerste
kald i hver tur, andel af prompten fra cachen):

    pause < 5 min .. 3 t   median 84-88 %   — cachen er VARM
    pause 3 .. 12 t        median 26 %      — cachen er kold

Den gamle regel stubbede efter 60 minutter, altsaa midt i en varm cache. Og
den var ikke klaebende: ved naeste tur var pausen vaek, stubbene forsvandt, og
de fulde resultater kom tilbage. Maalt paa hans aktive session: ved 61 min
stubbedes 78 af 83 tool-raekker, foerste forskel 58 % inde i transcriptet,
~18.000 tokens nye for cachen — og samme brud igen ved turen efter. To brud
pr. pause, ogsaa naar cachen var kold, fordi tilbageskiftet brød den friske.

«Seneste kald havde mange miss» er heller ikke signalet: et miss betyder at
praefikset netop ER blevet cachet paa ny. At stubbe lige efter bryder den
friske cache.

## Reglen nu

- En KLAEBENDE graense pr. session: tool-raekker med id ≤ graensen stubbes ved
  HVER bygning. Praefikset er det samme tur efter tur.
- Graensen rykker kun frem naar cachen maalt er kold (pause ≥ 3 t). Da er
  aendringen gratis — kaldet ville misse alligevel — og alle ture efter
  rammer cachen med de korte stubbe.
- Ny komprimerings-markoer = ny epoke: graensen nulstilles, fordi praefikset
  aendrer sig dér under alle omstaendigheder.
- Kun en rigtig prompt-bygning maa flytte graensen (`persist=True`); desks
  kontekst-ring maaler bare.

Gaettet (en tidsgraense) er stadig et gaet — DeepSeek siger ikke hvornaar en
cache udloeber — men graensen er nu kalibreret paa maalte ture i stedet for
valgt. Kontrol-scriptet til at maale igen: se docstringen i
tests/test_microcompact.py.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_ENABLED_KEY = "time_gap_microcompact_enabled"
# Maalt 19/9: varm til og med 1-3 t (median 86 %), kold fra 3 t (median 26 %).
DEFAULT_GAP_MINUTES = 180
DEFAULT_KEEP_RECENT_TOOLS = 5
_STUB_PREFIX = "[old_tool_result:"


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _enabled() -> bool:
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool(_ENABLED_KEY, default=True)
    except Exception:
        return True


def _parse_dt(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _latest_assistant_at(messages: list[dict[str, Any]]) -> datetime | None:
    for message in reversed(messages):
        if str(message.get("role") or "") == "assistant":
            parsed = _parse_dt(message.get("created_at"))
            if parsed is not None:
                return parsed
    return None


def _is_stubbed(content: Any) -> bool:
    return str(content or "").startswith(_STUB_PREFIX)


def _stub_tool_result(message: dict[str, Any]) -> dict[str, Any]:
    content = str(message.get("content") or "")
    stub = dict(message)
    stub["content"] = f"{_STUB_PREFIX}{message.get('id', '?')} - {len(content)} chars]"
    return stub


def _id(message: dict[str, Any]) -> int | None:
    try:
        return int(message.get("id"))
    except (TypeError, ValueError):
        return None


# ── Den klaebende graense ──────────────────────────────────────────────────

def _sikr_tabel(conn: Any) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS microcompact_cutoff (
            session_id TEXT PRIMARY KEY,
            cutoff_id INTEGER NOT NULL DEFAULT 0,
            epoke TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )"""
    )


def _epoke(conn: Any, session_id: str) -> str:
    """Seneste komprimerings-markoer. En ny markoer aendrer praefikset alligevel."""
    row = conn.execute(
        "SELECT MAX(id) FROM chat_messages WHERE session_id = ? AND role = 'compact_marker'",
        (session_id,),
    ).fetchone()
    return str((row[0] if row else "") or "")


def laes_graense(session_id: str) -> int:
    """Den gaeldende graense for sessionen i den aktuelle epoke (0 = ingen)."""
    try:
        from core.runtime.db import connect
        with connect() as conn:
            _sikr_tabel(conn)
            row = conn.execute(
                "SELECT cutoff_id, epoke FROM microcompact_cutoff WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not row or str(row[1]) != _epoke(conn, session_id):
                return 0
            return int(row[0] or 0)
    except Exception:
        return 0


def _gem_graense(session_id: str, cutoff_id: int) -> None:
    try:
        from core.runtime.db import connect
        with connect() as conn:
            _sikr_tabel(conn)
            conn.execute(
                "INSERT INTO microcompact_cutoff (session_id, cutoff_id, epoke, updated_at)"
                " VALUES (?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET"
                " cutoff_id=excluded.cutoff_id, epoke=excluded.epoke, updated_at=excluded.updated_at",
                (session_id, int(cutoff_id), _epoke(conn, session_id), _now_utc().isoformat()),
            )
            conn.commit()
    except Exception:
        pass


def apply_cache_aware_microcompact(
    messages: list[dict[str, Any]],
    *,
    session_id: str,
    now: datetime | None = None,
    gap_minutes: int = DEFAULT_GAP_MINUTES,
    keep_recent_tools: int = DEFAULT_KEEP_RECENT_TOOLS,
    persist: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Stub gamle tool-resultater bag en klaebende, cache-bevidst graense.

    Input muteres aldrig. Ukendte tidsstempler og ids fejler aabent: historikken
    bevares. Samme beskeder + samme graense giver samme output, saa praefikset
    er stabilt fra bygning til bygning.
    """
    if not messages:
        return [], {"active": False, "folded_tool_results": 0, "reason": "empty"}
    if not _enabled():
        return list(messages), {"active": False, "folded_tool_results": 0, "reason": "disabled"}

    sid = (session_id or "").strip()
    graense = laes_graense(sid) if sid else 0
    rykket = False

    latest = _latest_assistant_at(messages)
    if latest is not None and sid:
        current = now or _now_utc()
        if current.tzinfo is None:
            current = current.replace(tzinfo=UTC)
        pause_s = (current.astimezone(UTC) - latest).total_seconds()
        if pause_s >= max(int(gap_minutes), 0) * 60:
            # Cachen er maalt kold: flyt graensen op til lige foer de nyeste
            # `keep` tool-resultater. Gratis nu, og stabil for alle ture efter.
            tool_ids = [i for i in (_id(m) for m in messages if str(m.get("role") or "") == "tool")
                        if i is not None]
            keep = max(int(keep_recent_tools), 0)
            kandidat = tool_ids[-keep - 1] if len(tool_ids) > keep else 0
            if kandidat > graense:
                graense = kandidat
                rykket = True
                if persist:
                    _gem_graense(sid, graense)

    if graense <= 0:
        return list(messages), {"active": False, "folded_tool_results": 0,
                                "reason": "no_cutoff", "cutoff_id": 0}

    folded = 0
    out: list[dict[str, Any]] = []
    for message in messages:
        mid = _id(message)
        if (str(message.get("role") or "") == "tool" and mid is not None and mid <= graense
                and not _is_stubbed(message.get("content"))):
            out.append(_stub_tool_result(message))
            folded += 1
        else:
            out.append(message)
    return out, {
        "active": True,
        "folded_tool_results": folded,
        "reason": "cold_cache_advance" if rykket else "sticky_cutoff",
        "cutoff_id": graense,
    }
