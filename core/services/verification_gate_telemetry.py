"""R2 verification gate telemetry — track whether warnings get heeded.

The verification gate (R2) is observational only — it surfaces
"⚠ N mutations, M verifies" and lets the model decide. We've never
known whether the model actually ACTS on these warnings.

This module records two streams of evidence:

1. **Surfaces** — every time verification_gate_section returns non-None,
   we log a snapshot (warning kind, mutation_count, failed_verify_count,
   timestamp).

2. **Reactions** — for each surfaced warning, we observe the next
   60 seconds for verify_* tool calls. If a verify follows, the warning
   was "heeded". If not, it was "ignored". Recorded with provenance.

Aggregate:
- `surfaced_total`, `heeded_total`, `ignored_total`
- `heed_rate` (last 24h, last 7d)
- per-warning-kind breakdown

Promotion path: when `heed_rate < 0.4` over a meaningful window AND
unverified mutations are still flowing, we have data to flip R2 → R2.5
(conditional blocking). That decision is left to the user; this module
just provides the numbers.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_TELEMETRY_KEY = "r2_verification_gate_telemetry"
_REACTION_WINDOW_SECONDS = 60
#: Fast målevindue. Horisonten skal være en *tid*, ikke et *antal*: et antal
#: flytter målevinduet når aktiviteten gør (målt 20/9-2026: 500 poster dækkede
#: 9,7 døgn ved ~52/døgn — ved 500/døgn ville «7d» være 1 døgn, og tallet ville
#: se lige så rigtigt ud). 30 dage er husets etablerede horisont (jf.
#: `visual_memory`: «4/day × 30 days»).
_RETENTION_DAYS = 30
#: Sikkerhedsnet mod vækst, IKKE den effektive horisont. Ved ~52 poster/døgn
#: binder loftet først ved ~667/døgn — aldersvinduet rammer længe før.
_MAX_RECORDS = 20000


def _load() -> dict[str, Any]:
    try:
        data = load_json(_TELEMETRY_KEY, {}) or {}
        if not isinstance(data, dict):
            return {}
        data.setdefault("surfaces", [])
        data.setdefault("reactions", [])
        return data
    except Exception:
        return {"surfaces": [], "reactions": []}


def _save(data: dict[str, Any]) -> None:
    try:
        # Beskaering der TAELLER, paa et fast tidsvindue.
        #
        # Foer stod her `list(...)[-_MAX_RECORDS:]` — maalt 20/9-2026 stod begge
        # ringe praecis paa 500/500, altsaa havde de kastet vaek, og der fandtes
        # ikke ét tal for hvor meget (samme symptom som `decision_signal_telemetry`
        # fik fixet 13/9; denne tvilling blev aldrig migreret).
        #
        # Fase 10, kriterium 2: «tolerate loss honestly». Tab er i orden for
        # telemetri — det er netop forskellen paa telemetri og sandhed. Usynligt
        # tab er ikke.
        try:
            from core.services.telemetry_gate import beskaer_efter_alder
            data["surfaces"] = beskaer_efter_alder(
                data.get("surfaces", []), _RETENTION_DAYS,
                navn="verification_gate_telemetry.surfaces", maks=_MAX_RECORDS)
            data["reactions"] = beskaer_efter_alder(
                data.get("reactions", []), _RETENTION_DAYS,
                navn="verification_gate_telemetry.reactions", maks=_MAX_RECORDS)
        except Exception:
            # Regnskabet maa aldrig koste os selve beskaeringen — en ring uden
            # loft ville vokse til den spiste state-filen.
            data["surfaces"] = list(data.get("surfaces", []))[-_MAX_RECORDS:]
            data["reactions"] = list(data.get("reactions", []))[-_MAX_RECORDS:]
        save_json(_TELEMETRY_KEY, data)
    except Exception as exc:
        logger.debug("r2_telemetry: persist failed: %s", exc)


_lock = threading.Lock()


def record_surface(
    *,
    failed_verify_count: int,
    unverified_count: int,
    mutation_count: int,
    verify_count: int,
) -> None:
    """Called by verification_gate_section when it returns a non-None section."""
    if failed_verify_count <= 0 and unverified_count <= 0:
        return
    now = datetime.now(UTC)
    record = {
        "at": now.isoformat(),
        "kind": "failed_verify" if failed_verify_count > 0 else "unverified",
        "failed_verify_count": failed_verify_count,
        "unverified_count": unverified_count,
        "mutation_count": mutation_count,
        "verify_count": verify_count,
        "resolved": False,  # set True once a verify_* arrives within window
    }
    with _lock:
        data = _load()
        # Suppress duplicate if we just recorded the same warning <60s ago
        existing = data.get("surfaces", [])
        if existing:
            last = existing[-1]
            try:
                last_ts = datetime.fromisoformat(str(last.get("at", "")))
                if (now - last_ts).total_seconds() < 30:
                    return
            except ValueError:
                pass
        existing.append(record)
        data["surfaces"] = existing
        _save(data)


def record_verify_event(
    *, tool: str, status: str, at: datetime | None = None, verify_kind: str = "strict"
) -> None:
    """Called by the telemetry listener for tool.completed events. If a recent
    surface is unresolved and within the reaction window, mark it heeded.

    verify_kind: "strict" for explicit verify_* tools, "light" for read-back
    tools (read_file, db_query, process_list, ...). Recorded separately so we
    can tell whether Jarvis explicitly verified or just glanced back.
    """
    now = at or datetime.now(UTC)
    if status != "ok":
        return
    verdict_label = "heeded" if verify_kind == "strict" else "light_heeded"
    with _lock:
        data = _load()
        surfaces = data.get("surfaces", [])
        cutoff = now - timedelta(seconds=_REACTION_WINDOW_SECONDS)
        changed = False
        for s in reversed(surfaces):
            if s.get("resolved"):
                continue
            try:
                s_at = datetime.fromisoformat(str(s.get("at", "")))
            except ValueError:
                continue
            if s_at < cutoff:
                break
            s["resolved"] = True
            s["heeded_by"] = tool
            s["heeded_at"] = now.isoformat()
            s["heeded_kind"] = verify_kind
            changed = True
            data.setdefault("reactions", []).append({
                "at": now.isoformat(),
                "verdict": verdict_label,
                "tool": tool,
                "verify_kind": verify_kind,
                "surface_at": s.get("at"),
                "kind": s.get("kind"),
            })
            break
        if changed:
            _save(data)


def sweep_expired_surfaces() -> int:
    """Mark surfaces as 'ignored' once they're past the reaction window with
    no matching verify_*. Run periodically."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=_REACTION_WINDOW_SECONDS)
    ignored = 0
    with _lock:
        data = _load()
        surfaces = data.get("surfaces", [])
        for s in surfaces:
            if s.get("resolved"):
                continue
            try:
                s_at = datetime.fromisoformat(str(s.get("at", "")))
            except ValueError:
                continue
            if s_at < cutoff:
                s["resolved"] = True
                s["ignored_at"] = now.isoformat()
                ignored += 1
                data.setdefault("reactions", []).append({
                    "at": now.isoformat(),
                    "verdict": "ignored",
                    "surface_at": s.get("at"),
                    "kind": s.get("kind"),
                })
        if ignored:
            _save(data)
    return ignored


def get_telemetry_summary(*, hours: int = 24) -> dict[str, Any]:
    """Aggregate counts + heed rates over the lookback window.

    Returns both `strict_heed_rate` (verify_* only) and `effective_heed_rate`
    (strict + light readbacks). The effective rate is the better proxy for
    "did Jarvis at least glance back?", while strict_heed_rate flags how
    often he calls a real verify_* tool.
    """
    sweep_expired_surfaces()
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    data = _load()
    in_window = 0
    heeded_strict = 0
    heeded_light = 0
    ignored = 0
    by_kind: dict[str, dict[str, int]] = {}
    for s in data.get("surfaces", []):
        try:
            s_at = datetime.fromisoformat(str(s.get("at", "")))
        except ValueError:
            continue
        if s_at < cutoff:
            continue
        in_window += 1
        kind = str(s.get("kind") or "unknown")
        by_kind.setdefault(kind, {"surfaced": 0, "heeded": 0, "light": 0, "ignored": 0})
        by_kind[kind]["surfaced"] += 1
        heeded_kind = str(s.get("heeded_kind") or "")
        if s.get("heeded_by"):
            if heeded_kind == "light":
                heeded_light += 1
                by_kind[kind]["light"] += 1
            else:
                heeded_strict += 1
                by_kind[kind]["heeded"] += 1
        elif s.get("ignored_at"):
            ignored += 1
            by_kind[kind]["ignored"] += 1
    total_heeded = heeded_strict + heeded_light
    strict_rate = round(heeded_strict / in_window, 3) if in_window > 0 else None
    effective_rate = round(total_heeded / in_window, 3) if in_window > 0 else None
    return {
        "window_hours": hours,
        "surfaced_total": in_window,
        "heeded_total": total_heeded,            # back-compat (was strict-only)
        "heeded_strict": heeded_strict,
        "heeded_light": heeded_light,
        "ignored_total": ignored,
        "heed_rate": effective_rate,             # back-compat (now effective)
        "strict_heed_rate": strict_rate,
        "effective_heed_rate": effective_rate,
        "by_kind": by_kind,
    }


#: Horisonter for udfaldsaksen — hvor længe efter en advarsel vi stadig
#: anerkender at verifikationen kom. Den gamle akse
#: (`_REACTION_WINDOW_SECONDS` = 60) måler reaktionstid; målt 17/11-2026 faldt
#: 97,5 % af den ægte verifikation uden for det vindue, så «ignored» betød
#: «svarede ikke inden 60 s» — ikke «verificerede ikke». Den akse er derfor
#: ikke forkert, men den måler noget andet end dækning.
_OUTCOME_HORIZONS_MINUTES: tuple[int, ...] = (1, 5, 10, 30, 60, 240)


def measure_outcome_axis(
    *,
    hours: int = 24,
    horizons_minutes: tuple[int, ...] = _OUTCOME_HORIZONS_MINUTES,
) -> dict[str, Any]:
    """Mål om advarslen førte til en ÆGTE verifikation — ikke hvor hurtigt.

    Læser advarslerne fra telemetri-filen og slår op i `events` om der kom et
    strict verify-kald efter hver enkelt. Forskellen fra
    `get_telemetry_summary` er de to ting der gjorde den metric misvisende:
    den ser på et tidsrum frem for et 60-sekunders vindue, og den tæller ikke
    en simpel læsning som verifikation.

    `cross_tab` viser hvor ofte de to akser er uenige — dvs. advarsler den
    gamle metric kaldte «ignored» som alligevel blev verificeret, og omvendt.
    Det er selve pointen: er uenigheden stor, måler den gamle akse reaktion
    og ikke kontrol.

    Ren læsning — muterer hverken telemetri-filen eller `events`.
    """
    import bisect
    import json as _json

    empty = {
        "window_hours": hours,
        "surfaces": 0,
        "verified": 0,
        "rate": None,
        "per_horizon": {int(h): 0 for h in horizons_minutes},
        "cross_tab": {},
        "median_seconds_to_verify": None,
    }

    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    data = _load()
    surfaces: list[dict[str, Any]] = []
    for s in data.get("surfaces", []):
        try:
            s_at = datetime.fromisoformat(str(s.get("at", "")))
        except ValueError:  # uparseligt tidsstempel: posten kan ikke placeres i tid
            continue
        if s_at < cutoff:
            continue
        surfaces.append(
            {
                "at": s_at,
                "kind": str(s.get("kind") or "unknown"),
                "heeded_kind": str(s.get("heeded_kind") or ""),
                "heeded": bool(s.get("heeded_by")),
                "ignored": bool(s.get("ignored_at")),
            }
        )
    if not surfaces:
        return empty

    try:
        from core.runtime.db import connect
        from core.services.verification_gate import _VERIFY_TOOLS as _strict
    except Exception as exc:
        logger.debug("r2_outcome: kan ikke importere db/gate: %s", exc)
        return {**empty, "surfaces": len(surfaces), "error": "import"}

    oldest = min(s["at"] for s in surfaces)
    newest = max(s["at"] for s in surfaces) + timedelta(minutes=max(horizons_minutes))
    verifies: list[datetime] = []
    try:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json, created_at
                FROM events
                WHERE kind = 'tool.completed'
                  AND created_at >= ?
                  AND created_at <= ?
                ORDER BY created_at ASC
                """,
                (oldest.isoformat(), newest.isoformat()),
            ).fetchall()
        for payload_json, created_at in rows:
            try:
                payload = _json.loads(payload_json or "{}")
            except (ValueError, TypeError):  # ikke-JSON kan ikke bære et værktøjsnavn
                continue
            if not isinstance(payload, dict):
                continue
            if str(payload.get("status") or "") != "ok":
                continue
            if str(payload.get("tool") or "") not in _strict:
                continue
            try:
                verifies.append(datetime.fromisoformat(str(created_at)))
            except ValueError:  # uparseligt created_at: rækken kan ikke tidsordnes
                continue
    except Exception as exc:
        logger.debug("r2_outcome: events-opslag fejlede: %s", exc)
        return {**empty, "surfaces": len(surfaces), "error": "db"}

    verifies.sort()
    per_horizon = {int(h): 0 for h in horizons_minutes}
    deltas: list[float] = []
    cross = {
        "ignored_but_verified": 0,
        "ignored_and_unverified": 0,
        "heeded_strict": 0,
        "heeded_light_but_unverified": 0,
    }
    widest = max(horizons_minutes)
    for s in surfaces:
        start = bisect.bisect_right(verifies, s["at"])
        first_delta: float | None = None
        for h in sorted(horizons_minutes):
            end = s["at"] + timedelta(minutes=h)
            stop = bisect.bisect_right(verifies, end)
            if stop > start:
                per_horizon[int(h)] += 1
                if first_delta is None:
                    first_delta = (verifies[start] - s["at"]).total_seconds()
        if first_delta is not None:
            deltas.append(first_delta)

        verified_widest = bisect.bisect_right(
            verifies, s["at"] + timedelta(minutes=widest)
        ) > start
        if s["ignored"]:
            key = "ignored_but_verified" if verified_widest else "ignored_and_unverified"
            cross[key] += 1
        elif s["heeded_kind"] == "light" and not verified_widest:
            cross["heeded_light_but_unverified"] += 1
        elif s["heeded_kind"] == "strict":
            cross["heeded_strict"] += 1

    total = len(surfaces)
    verified = per_horizon[int(widest)]
    deltas.sort()
    median = None
    if deltas:
        mid = len(deltas) // 2
        median = round(
            deltas[mid] if len(deltas) % 2 else (deltas[mid - 1] + deltas[mid]) / 2, 1
        )

    return {
        "window_hours": hours,
        "surfaces": total,
        "verified": verified,
        "rate": round(verified / total, 3) if total else None,
        "per_horizon": per_horizon,
        "cross_tab": cross,
        "median_seconds_to_verify": median,
    }


def telemetry_section() -> str | None:
    """Render telemetry as a prompt-awareness section. Only shows when there's
    a meaningful pattern (>= 5 surfaces in the last 24h)."""
    s = get_telemetry_summary(hours=24)
    if s.get("surfaced_total", 0) < 5:
        return None
    strict_rate = s.get("strict_heed_rate")
    eff_rate = s.get("effective_heed_rate")
    strict_str = f"{int(strict_rate * 100)}%" if strict_rate is not None else "n/a"
    eff_str = f"{int(eff_rate * 100)}%" if eff_rate is not None else "n/a"
    flag = ""
    if eff_rate is not None and eff_rate < 0.4:
        flag = " ⚠ under 40% — readback-followup below threshold"
    return (
        f"R2-gate telemetry (24t): surfaced={s['surfaced_total']} "
        f"strict_heeded={s['heeded_strict']} light_heeded={s['heeded_light']} "
        f"ignored={s['ignored_total']} "
        f"strict={strict_str} effective={eff_str}{flag}"
    )


# ── Eventbus DB-polling listener ───────────────────────────────────────────
# Was previously an in-process event_bus.subscribe() loop — but eventbus
# subscribers are per-process Python queues. The api workers (where chat
# lives and verify_* calls actually fire) had no subscriber attached
# because governance_bootstrap is gated on JARVIS_ENABLE_RUNTIME_SERVICES,
# which is 0 on jarvis-api.service. Net effect: ~63 of 71 real verify
# events since 8 May never reached the telemetry listener.
#
# Fix (2026-05-14): poll the events DB table instead. SQLite is shared
# across processes, so a single listener (running on jarvis-runtime)
# now sees every tool.completed regardless of which process emitted it.


_subscribed = False
_POLL_INTERVAL_SECONDS = 5.0


def _poll_db_for_verify_events() -> None:
    """Poll the events table for new tool.completed verify_* events.

    Cursor is last_event_id_seen, stored in memory. On first run we
    initialize the cursor to the current MAX(id) so we don't replay
    history. Subsequent polls fetch only new rows.
    """
    import time as _time
    try:
        from core.runtime.db import connect
    except Exception:
        return

    # Initialize cursor at current max id — we don't want to replay
    # old verifies against new surfaces.
    last_id = 0
    try:
        with connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()
            last_id = int(row[0] or 0) if row else 0
    except Exception as exc:
        logger.debug("r2_telemetry: cursor init failed: %s", exc)

    while True:
        _time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            import json as _json
            with connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, payload_json, created_at
                    FROM events
                    WHERE id > ?
                      AND kind = 'tool.completed'
                    ORDER BY id ASC
                    LIMIT 500
                    """,
                    (last_id,),
                ).fetchall()
            # Pull tool-set classifications fresh each cycle so changes
            # to _LIGHT_VERIFY_TOOLS propagate without restart.
            try:
                from core.services.verification_gate import (
                    _VERIFY_TOOLS as _STRICT,
                    _LIGHT_VERIFY_TOOLS as _LIGHT,
                )
            except Exception:
                _STRICT, _LIGHT = frozenset(), frozenset()
            for row in rows:
                eid = int(row[0])
                last_id = max(last_id, eid)
                try:
                    payload = _json.loads(row[1] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                tool = str(payload.get("tool") or "")
                status = str(payload.get("status") or "")
                if status != "ok":
                    continue
                if tool in _STRICT:
                    verify_kind = "strict"
                elif tool in _LIGHT:
                    verify_kind = "light"
                else:
                    continue
                created_at_raw = str(row[2] or "")
                try:
                    event_at = datetime.fromisoformat(created_at_raw)
                except ValueError:
                    event_at = datetime.now(UTC)
                record_verify_event(
                    tool=tool, status=status, at=event_at, verify_kind=verify_kind,
                )
        except Exception as exc:
            logger.debug("r2_telemetry: poll cycle failed: %s", exc)
            continue


def subscribe() -> None:
    """Start the DB-polling telemetry listener. Idempotent per process."""
    global _subscribed
    if _subscribed:
        return
    _subscribed = True
    threading.Thread(
        target=_poll_db_for_verify_events,
        name="r2-telemetry-db-poll",
        daemon=True,
    ).start()
