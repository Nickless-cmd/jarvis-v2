"""Cross-session arc — surface recent named conversations as a temporal arc.

Phase 3 follow-on (2026-05-08): give Jarvis felt continuity across
session boundaries. Where the per-session transcript covers the
current conversation, this section shows the WIDER arc — the last
several user-facing chat sessions, ordered by recency, so Jarvis can
sense "we've been working on this for days" instead of starting cold
each session.

Selection:
  - Reads ``chat_sessions`` rows over the last N days.
  - Filters out automated/probe sessions (titles starting with test
    prefixes, generic "New chat", autonomous-loop-only sessions like
    "Autonomous", inbound Discord DM placeholders without a meaningful
    title).
  - Caps to top-N by recency.

Procedural — no LLM call. TTL cache 10 min.

Awareness priority: 18 — below pattern_counterfactuals (20). This is
ambient continuity; failures, narrative-now, and pattern reflections
all outrank it for budget.
"""
from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta, timezone

from core.runtime.db import connect

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 7
_MAX_TO_SHOW = 6

# Titles to suppress from the arc — they're not user-facing arcs.
_NOISE_TITLE_EXACT: frozenset[str] = frozenset({
    "New chat", "Ny chat", "Autonomous",
})

# Title prefixes used by automated probes / dev sessions.
_NOISE_TITLE_PREFIXES: tuple[str, ...] = (
    "test ", "test-", "probe", "phase",
    "perf-", "prune-", "warm-", "enrich-", "verify",
    "v2", "v3", "smoke",  # generic placeholder
    "Discord DM —",  # raw DM placeholder, no topical title
)

# Substring-match noise — catches mid-string probe markers (e.g.
# "final-perf", "prewarm-test"). These are short ad-hoc dev titles
# that pollute the arc; filter them out by any of these markers.
_NOISE_TITLE_SUBSTRINGS: tuple[str, ...] = (
    "perf", "prune", "prewarm", "verify", "smoke",
    "phase2-", "phase3-",
)

_CACHE_TTL_SECONDS = 600.0  # 10 min — sessions don't change often
# Cachen holder nu RAAdata, ikke faerdig tekst. Afgraensningen afhaenger af
# BRUGEREN (`cross_session_gate.gaeldende_niveau()`), og en cachet faerdig tekst
# ville servere den ene brugers niveau til den naeste — en lille cache-aendring
# der ville have vaeret et aegte laek.
_cached_rows: list[dict] | None = None
_cached_i_alt: int = 0
_cached_at: float = 0.0


def _is_noise_title(title: str) -> bool:
    t = (title or "").strip()
    if not t or len(t) < 5:  # very short titles are usually probe placeholders
        return True
    if t in _NOISE_TITLE_EXACT:
        return True
    lower = t.lower()
    if any(lower.startswith(p.lower()) for p in _NOISE_TITLE_PREFIXES):
        return True
    return any(s in lower for s in _NOISE_TITLE_SUBSTRINGS)


def _humanize_dt(iso: str, now: datetime) -> str:
    """Return short Danish relative time for the arc render."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return iso[:16]
    delta = now - dt
    secs = max(int(delta.total_seconds()), 0)
    if secs < 60:
        return "lige nu"
    if secs < 3600:
        return f"{secs // 60} min siden"
    if secs < 86400:
        return f"{secs // 3600}t siden"
    days = secs // 86400
    if days == 1:
        return "i går"
    return f"{days} dage siden"


def _fetch_recent_arc() -> tuple[list[dict], int]:
    """(de viste raekker, HVOR MANGE der fandtes i vinduet).

    Det andet tal er nyt og er hele pointen. Foer stod der «Din samtale-bue de
    sidste 7 dage» over seks linjer, og maalt 13/9-2026 laa der 45 sessioner i
    vinduet. Niogtredive forsvandt uden at det stod nogen steder, og teksten
    laeses som BUEN — ikke som seks af femogfyrre.

    Over-hentningen (`_MAX_TO_SHOW * 5`) kender heller ikke tallet: den saa 30.
    Derfor et separat COUNT, som er billigt paa en indekseret kolonne.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=LOOKBACK_DAYS)).isoformat()
    with connect() as c:
        i_alt = int(c.execute(
            "SELECT COUNT(*) FROM chat_sessions WHERE updated_at >= ?",
            (cutoff,),
        ).fetchone()[0] or 0)
        rows = c.execute(
            "SELECT session_id, title, created_at, updated_at "
            "FROM chat_sessions "
            "WHERE updated_at >= ? "
            "ORDER BY updated_at DESC "
            "LIMIT ?",
            (cutoff, _MAX_TO_SHOW * 5),  # over-fetch so noise filter
                                          # has room to keep _MAX_TO_SHOW
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        title = str(r["title"] or "")
        if _is_noise_title(title):
            continue
        out.append({
            "session_id": str(r["session_id"]),
            "title": title,
            "updated_at": str(r["updated_at"]),
        })
        if len(out) >= _MAX_TO_SHOW:
            break
    return out, i_alt


def cross_session_arc_section() -> str:
    """Render last N user-facing sessions as a chronological arc."""
    global _cached_rows, _cached_i_alt, _cached_at
    now = time.monotonic()
    if _cached_rows is None or (now - _cached_at) >= _CACHE_TTL_SECONDS:
        try:
            _cached_rows, _cached_i_alt = _fetch_recent_arc()
        except Exception as exc:
            logger.debug("cross_session_arc: fetch failed: %s", exc)
            _cached_rows, _cached_i_alt = [], 0
        _cached_at = now
    rows, i_alt = list(_cached_rows), _cached_i_alt

    if not rows:
        return ""

    # Fase 10, kriterium 1. Gaten er i SKYGGE som standard: den regner ud hvad
    # den ville fjerne og skriver det, men fjerner intet endnu.
    try:
        from core.services.cross_session_gate import afgraens
        g = afgraens(rows, kilde="chat_sessions/arc",
                     maks_antal=_MAX_TO_SHOW, maks_tegn=1200,
                     fundet_i_alt=i_alt)
        rows = list(g.poster)
        # Gaten foerer regnskabet, saa overskriften og herkomsten ikke kan
        # komme til at sige hvert sit tal.
        udeladt = g.udeladt_antal
        herkomst = g.herkomst()
    except Exception:
        logger.debug("cross_session_arc: gate fejlede — sender ugateret",
                     exc_info=True)
        udeladt = max(0, i_alt - len(rows))
        herkomst = "[utroværdig kilde (andre sessioner) | herkomst utilgængelig]"

    now_dt = datetime.now(UTC)
    hoved = "📜 Din samtale-bue de sidste 7 dage (nyeste først)"
    if udeladt:
        # Tallet staar i OVERSKRIFTEN, ikke i en fodnote. En liste der ser
        # komplet ud, laeses som komplet.
        hoved += f" — viser {len(rows)} af {i_alt}, {udeladt} udeladt"
    lines = [herkomst, hoved + ":"]
    for r in rows:
        when = _humanize_dt(r["updated_at"], now_dt)
        title = r["title"][:60]
        lines.append(f"  · {when:>14} — \"{title}\"")

    return "\n".join(lines)


def invalidate_cache() -> None:
    global _cached_rows, _cached_i_alt, _cached_at
    _cached_rows = None
    _cached_i_alt = 0
    _cached_at = 0.0
