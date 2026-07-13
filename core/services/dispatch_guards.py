"""core/services/dispatch_guards.py

Fire sikkerheds-backstops for den autonome, event-drevne dispatch-loop. De sikrer
at loopet aldrig re-dispatcher det samme signal efter et crash, aldrig hænger
uendeligt på en dispatch der aldrig rapporterer tilbage, aldrig hamrer en syg lane
i en fejl-storm, og ALDRIG brænder mere end et hårdt budget-loft pr. lane pr. døgn.

Alle fire er:
  * DURABLE — tilstand overlever restart (via runtime_state_kv i jarvis.db;
    idempotens-CAS'en bruger en dedikeret lille tabel for reel atomicitet).
  * SELF-SAFE — kaster aldrig; ved DB-fejl fejler de *sikkert* (idempotens
    fail-consumed, breaker fail-open-læse men fejl-tæl er durabel, budget
    fail-CLOSED så "idle=zero burn" holder selv hvis alt andet fejler).
  * RUNTIME-STATE-TUNABLE — alle tærskler læses live fra runtime-state.
  * DETERMINISTISK TESTBAR — tid gives ind som `now`/`now_ts`-param (default
    time.time()), så tests kan spole uret uden at mocke.

Guard 1 — Idempotens:      try_consume(key) -> bool           (CAS, TTL 3600s)
Guard 2 — Dead-man-timeout: synthesize_timeout_envelope / register_deadline / overdue
Guard 3 — Circuit-breaker:  record_outcome(lane, ok) / is_tripped(lane)
Guard 4 — Budget-loft:      budget_allows(lane, cost) / record_spend(lane, cost)

Genbruger dispatch_envelope.build_envelope + dispatch_status.DispatchStatus.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from core.services.dispatch_envelope import build_envelope
from core.services.dispatch_status import DispatchStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Runtime-state tuning-nøgler + defaults
# ---------------------------------------------------------------------------
_IDEM_TTL_KEY = "dispatch_idem_ttl_s"
_DEFAULT_IDEM_TTL = 3600.0

_BREAKER_THRESHOLD_KEY = "dispatch_breaker_threshold"
_DEFAULT_BREAKER_THRESHOLD = 5

_BREAKER_WINDOW_KEY = "dispatch_breaker_window_s"
_DEFAULT_BREAKER_WINDOW = 900.0

_BREAKER_COOLDOWN_KEY = "dispatch_breaker_cooldown_s"
_DEFAULT_BREAKER_COOLDOWN = 900.0

_BUDGET_MAX_COUNT_KEY = "dispatch_budget_max_count"
_DEFAULT_BUDGET_MAX_COUNT = 200

_BUDGET_MAX_COST_KEY = "dispatch_budget_max_cost_usd"
_DEFAULT_BUDGET_MAX_COST = 5.0

_BUDGET_WINDOW_S = 86400.0  # rullende 24h — hård (ikke tunable: budget-loftets kontrakt)

# Durable runtime-state key-prefixes
_DEADLINE_KEY = "dispatch_deadlines"          # {dispatch_id: deadline_ts}
_BREAKER_KEY_PREFIX = "dispatch_breaker:"     # per-lane {count, last_fail_ts, tripped_at}
_BUDGET_KEY_PREFIX = "dispatch_budget:"       # per-lane [[ts, cost], ...]

# Dedikeret idempotens-tabel (CAS via INSERT OR IGNORE)
_IDEM_TABLE = "dispatch_idempotency"


# ---------------------------------------------------------------------------
# runtime-state helpers (self-safe)
# ---------------------------------------------------------------------------
def _rs_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value

        v = get_runtime_state_value(key, default)
        return default if v is None else v
    except Exception:
        return default


def _rs_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value

        set_runtime_state_value(key, value)
    except Exception:
        logger.debug("dispatch_guards: rs_set failed for %s", key, exc_info=True)


def _as_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _as_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ===========================================================================
# Guard 1 — Idempotens (durabel CAS via dedikeret tabel)
# ===========================================================================
def _idem_ttl_s() -> float:
    return max(1.0, _as_float(_rs_get(_IDEM_TTL_KEY, _DEFAULT_IDEM_TTL), _DEFAULT_IDEM_TTL))


def try_consume(key: str, *, now: float | None = None, ttl_s: float | None = None) -> bool:
    """Markér `key` forbrugt ATOMISK. True første gang, False hvis allerede forbrugt
    inden for TTL (default 3600s). Forhindrer re-dispatch af samme (signal, baseline-epoke)
    efter crash-før-record.

    Atomicitet: `INSERT OR IGNORE` i en dedikeret tabel — SQLite serialiserer writes, så
    kun ÉN kald vinder indsættelsen (rowcount==1). En udløbet række (nu-ts > forbrugt+TTL)
    ryddes og genindsættes i samme transaktion. Self-safe: ved DB-fejl fejler vi CONSUMED
    (returnér False) så en tvivlsom sag aldrig dobbelt-dispatcher.
    """
    k = str(key or "").strip()
    if not k:
        return False
    now = time.time() if now is None else now
    ttl = _idem_ttl_s() if ttl_s is None else max(1.0, float(ttl_s))
    try:
        from core.runtime.db_core import connect

        with connect() as conn:
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {_IDEM_TABLE} "
                "(key TEXT PRIMARY KEY, consumed_at REAL)"
            )
            # Ryd udløbet række for netop denne key, så den kan genforbruges efter TTL.
            conn.execute(
                f"DELETE FROM {_IDEM_TABLE} WHERE key=? AND consumed_at < ?",
                (k, now - ttl),
            )
            cur = conn.execute(
                f"INSERT OR IGNORE INTO {_IDEM_TABLE} (key, consumed_at) VALUES (?, ?)",
                (k, now),
            )
            return cur.rowcount == 1
    except Exception:
        logger.debug("dispatch_guards: try_consume DB error → fail-consumed", exc_info=True)
        return False


# ===========================================================================
# Guard 2 — Dead-man-timeout
# ===========================================================================
def synthesize_timeout_envelope(agent_id: str, deadline_ms: int) -> dict:
    """Byg en LARMENDE TIMEOUT-envelope for en dispatch der aldrig meldte tilbage.
    Fast 7-nøgle-envelope (via build_envelope), status=TIMEOUT, duration_ms=deadline_ms."""
    aid = str(agent_id or "").strip() or "unknown"
    return build_envelope(
        status=DispatchStatus.TIMEOUT,
        duration_ms=int(deadline_ms),
        result=f"no completion by deadline (agent={aid})",
    )


def register_deadline(dispatch_id: str, deadline_ts: float) -> None:
    """Registrér hvornår en dispatch SENEST skal have rapporteret. Durabel."""
    did = str(dispatch_id or "").strip()
    if not did:
        return
    store = _rs_get(_DEADLINE_KEY, {}) or {}
    if not isinstance(store, dict):
        store = {}
    store[did] = float(deadline_ts)
    _rs_set(_DEADLINE_KEY, store)


def overdue(now_ts: float | None = None) -> list[str]:
    """Returnér dispatch_ids hvis deadline er passeret ved now_ts (frisk = ikke med)."""
    now_ts = time.time() if now_ts is None else now_ts
    store = _rs_get(_DEADLINE_KEY, {}) or {}
    if not isinstance(store, dict):
        return []
    out: list[str] = []
    for did, dl in store.items():
        try:
            if float(dl) <= now_ts:
                out.append(str(did))
        except (TypeError, ValueError):
            continue
    return out


def clear_deadline(dispatch_id: str) -> None:
    """Fjern en deadline (kaldes når dispatch rapporterer tilbage). Durabel, self-safe."""
    did = str(dispatch_id or "").strip()
    if not did:
        return
    store = _rs_get(_DEADLINE_KEY, {}) or {}
    if isinstance(store, dict) and did in store:
        store.pop(did, None)
        _rs_set(_DEADLINE_KEY, store)


# ===========================================================================
# Guard 3 — Circuit-breaker (per-lane, durabel)
# ===========================================================================
def _breaker_threshold() -> int:
    return max(1, _as_int(_rs_get(_BREAKER_THRESHOLD_KEY, _DEFAULT_BREAKER_THRESHOLD),
                          _DEFAULT_BREAKER_THRESHOLD))


def _breaker_window_s() -> float:
    return max(1.0, _as_float(_rs_get(_BREAKER_WINDOW_KEY, _DEFAULT_BREAKER_WINDOW),
                              _DEFAULT_BREAKER_WINDOW))


def _breaker_cooldown_s() -> float:
    return max(1.0, _as_float(_rs_get(_BREAKER_COOLDOWN_KEY, _DEFAULT_BREAKER_COOLDOWN),
                              _DEFAULT_BREAKER_COOLDOWN))


def _breaker_state(lane: str) -> dict:
    st = _rs_get(_BREAKER_KEY_PREFIX + lane, {}) or {}
    if not isinstance(st, dict):
        st = {}
    return st


def record_outcome(lane: str, ok: bool, *, now: float | None = None) -> None:
    """Registrér udfaldet af en dispatch på `lane`. En succes nulstiller den
    fortløbende fejl-tæller (og lukker en åben breaker); N fortløbende fejl inden
    for vinduet TRIPPER breakeren. Durabel."""
    ln = str(lane or "").strip()
    if not ln:
        return
    now = time.time() if now is None else now
    st = _breaker_state(ln)
    if ok:
        # Succes → fuld nulstilling.
        _rs_set(_BREAKER_KEY_PREFIX + ln, {"count": 0, "last_fail_ts": 0.0, "tripped_at": 0.0})
        return
    last_fail = _as_float(st.get("last_fail_ts", 0.0), 0.0)
    count = _as_int(st.get("count", 0), 0)
    # Faldt fejl-stimen ud af vinduet? Så starter en ny stime.
    if last_fail and (now - last_fail) > _breaker_window_s():
        count = 0
    count += 1
    tripped_at = _as_float(st.get("tripped_at", 0.0), 0.0)
    if count >= _breaker_threshold():
        tripped_at = now
    _rs_set(_BREAKER_KEY_PREFIX + ln,
            {"count": count, "last_fail_ts": now, "tripped_at": tripped_at})


def is_tripped(lane: str, *, now: float | None = None) -> bool:
    """True hvis breakeren for `lane` er åben (blokér dispatch). Auto-resetter efter
    cooldown: første kald efter cooldown lukker breakeren og returnerer False.
    Self-safe → fail-OPEN (læse-fejl blokerer ikke; fejl-tælling er durabel andetsteds)."""
    ln = str(lane or "").strip()
    if not ln:
        return False
    now = time.time() if now is None else now
    st = _breaker_state(ln)
    tripped_at = _as_float(st.get("tripped_at", 0.0), 0.0)
    if tripped_at <= 0.0:
        return False
    if (now - tripped_at) >= _breaker_cooldown_s():
        # Cooldown udløbet → luk breakeren durabelt.
        _rs_set(_BREAKER_KEY_PREFIX + ln, {"count": 0, "last_fail_ts": 0.0, "tripped_at": 0.0})
        return False
    return True


# ===========================================================================
# Guard 4 — Budget-loft (HÅRD backstop, fail-CLOSED)
# ===========================================================================
def _budget_max_count() -> int:
    return max(0, _as_int(_rs_get(_BUDGET_MAX_COUNT_KEY, _DEFAULT_BUDGET_MAX_COUNT),
                          _DEFAULT_BUDGET_MAX_COUNT))


def _budget_max_cost() -> float:
    return max(0.0, _as_float(_rs_get(_BUDGET_MAX_COST_KEY, _DEFAULT_BUDGET_MAX_COST),
                              _DEFAULT_BUDGET_MAX_COST))


def _budget_events(lane: str, now: float) -> list[list]:
    """Hent lane-forbrug som liste af [ts, cost] beskåret til det rullende 24h-vindue."""
    raw = _rs_get(_BUDGET_KEY_PREFIX + lane, []) or []
    if not isinstance(raw, list):
        return []
    cutoff = now - _BUDGET_WINDOW_S
    out: list[list] = []
    for ev in raw:
        try:
            ts = float(ev[0])
            cost = float(ev[1])
        except (TypeError, ValueError, IndexError):
            continue
        if ts >= cutoff:
            out.append([ts, cost])
    return out


def budget_allows(lane: str, cost_usd: float, *, now: float | None = None) -> bool:
    """HÅRD backstop FØR LLM'en fyrer: False hvis dette dispatch ville bryde ENTEN
    max antal (default 200) ELLER max cost_usd (default 5.0) pr. lane i rullende 24h.
    Self-safe → fail-CLOSED (fejl = nægt), så 'idle=zero burn' holder selv ved bug."""
    ln = str(lane or "").strip()
    if not ln:
        return False
    now = time.time() if now is None else now
    try:
        cost = max(0.0, float(cost_usd))
    except (TypeError, ValueError):
        return False
    try:
        events = _budget_events(ln, now)
        count = len(events)
        spent = sum(float(c) for _, c in events)
        if count + 1 > _budget_max_count():
            return False
        if spent + cost > _budget_max_cost():
            return False
        return True
    except Exception:
        logger.debug("dispatch_guards: budget_allows error → fail-closed", exc_info=True)
        return False


def record_spend(lane: str, cost_usd: float, *, now: float | None = None) -> None:
    """Registrér ét dispatch + dets cost på `lane`. Beskærer samtidig vinduet til 24h.
    Durabel, self-safe."""
    ln = str(lane or "").strip()
    if not ln:
        return
    now = time.time() if now is None else now
    try:
        cost = max(0.0, float(cost_usd))
    except (TypeError, ValueError):
        cost = 0.0
    events = _budget_events(ln, now)
    events.append([now, cost])
    _rs_set(_BUDGET_KEY_PREFIX + ln, events)
