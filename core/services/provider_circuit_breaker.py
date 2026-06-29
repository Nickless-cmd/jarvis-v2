"""Provider circuit breaker — skip primaries that have been failing recently.

When a provider/model has failed N+ times in the last window, we stop
trying it for a cooldown period. This prevents the per-role fallback
chain from wasting 5+ seconds per call on a known-dead endpoint
(observed live with ollamafreeapi.com being down for hours).

Stateless on disk — kept in memory only. Acceptable because:
- Restarts are rare (maybe daily)
- A restart's fresh trial is actually useful (the provider may have come back)
- Persisting failure counts across restarts could permanently brick a
  recovered provider until manual intervention

API:
- record_failure(provider, model) — note a failure
- record_success(provider, model) — clear failure history
- should_skip(provider, model) — True if breaker is open
- breaker_state() — observability (for prompt awareness, debug tools)
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

# Tunables
_FAILURE_THRESHOLD = 3            # N failures within window -> open the breaker
_FAILURE_WINDOW_SECONDS = 300.0   # 5 minutes of failure history kept
_OPEN_DURATION_SECONDS = 600.0    # 10 minutes skip when breaker opens

_LOCK = threading.Lock()
# (provider, model) -> deque[timestamp]
_FAILURES: dict[tuple[str, str], deque[float]] = {}
# (provider, model) -> timestamp when breaker was opened
_OPENED_AT: dict[tuple[str, str], float] = {}


def _key(provider: str, model: str) -> tuple[str, str]:
    return (str(provider or "").strip(), str(model or "").strip())


def _prune_old_failures(failures: deque[float], now: float) -> None:
    cutoff = now - _FAILURE_WINDOW_SECONDS
    while failures and failures[0] < cutoff:
        failures.popleft()


def record_failure(provider: str, model: str) -> dict[str, Any]:
    """Record a primary-call failure. Returns updated state for this key."""
    k = _key(provider, model)
    if not k[0] or not k[1]:
        return {"opened": False, "failure_count": 0}
    now = time.time()
    with _LOCK:
        failures = _FAILURES.setdefault(k, deque(maxlen=20))
        failures.append(now)
        _prune_old_failures(failures, now)
        if len(failures) >= _FAILURE_THRESHOLD and k not in _OPENED_AT:
            _OPENED_AT[k] = now
            opened = True
        else:
            opened = bool(k in _OPENED_AT)
    return {"opened": opened, "failure_count": len(failures)}


def record_success(provider: str, model: str) -> None:
    """Clear failure tracking on success — provider seems healthy again."""
    k = _key(provider, model)
    if not k[0] or not k[1]:
        return
    with _LOCK:
        _FAILURES.pop(k, None)
        _OPENED_AT.pop(k, None)


def should_skip(provider: str, model: str) -> bool:
    """True when breaker is open for this (provider, model)."""
    k = _key(provider, model)
    if not k[0] or not k[1]:
        return False
    now = time.time()
    with _LOCK:
        opened_at = _OPENED_AT.get(k)
        if opened_at is None:
            return False
        if now - opened_at >= _OPEN_DURATION_SECONDS:
            # Cooldown expired — half-open: allow next call to retry.
            _OPENED_AT.pop(k, None)
            _FAILURES.pop(k, None)
            return False
        return True


def breaker_state() -> dict[str, Any]:
    """Observability snapshot — returns open breakers + recent failure counts."""
    now = time.time()
    open_breakers: list[dict[str, Any]] = []
    recent_failures: list[dict[str, Any]] = []
    with _LOCK:
        for (prov, mod), opened_at in _OPENED_AT.items():
            seconds_open = max(0, int(now - opened_at))
            seconds_until_retry = max(0, int(_OPEN_DURATION_SECONDS - (now - opened_at)))
            open_breakers.append({
                "provider": prov,
                "model": mod,
                "opened_seconds_ago": seconds_open,
                "retry_in_seconds": seconds_until_retry,
            })
        for (prov, mod), failures in _FAILURES.items():
            count = len(failures)
            if count > 0:
                recent_failures.append({
                    "provider": prov,
                    "model": mod,
                    "failure_count": count,
                    "window_seconds": int(_FAILURE_WINDOW_SECONDS),
                })
    return {
        "open_breakers": open_breakers,
        "recent_failures": recent_failures,
        "threshold": _FAILURE_THRESHOLD,
        "window_seconds": int(_FAILURE_WINDOW_SECONDS),
        "open_duration_seconds": int(_OPEN_DURATION_SECONDS),
    }


def reset_all() -> None:
    """Test/admin helper — clear all state."""
    with _LOCK:
        _FAILURES.clear()
        _OPENED_AT.clear()
    _PP.reset_all()


# ═════════════════════════════════════════════════════════════════════════════
# DELT PER-PROVIDER circuit-breaker (spec §4 S6, §11.2)
# ═════════════════════════════════════════════════════════════════════════════
#
# Den ovenstående breaker er keyed på (provider, MODEL) og bruges af den
# per-rolle fallback-kæde i baggrunds-lanen. Spec §11.2 kræver en DELT
# per-PROVIDER breaker (keyed kun på provider_id) til:
#   - den synlige lane's rund-retry (visible_runs.py 4.1): en DØD provider skal
#     kort-sluttes + faile over i stedet for retry-storm gennem tur-budgettet,
#   - LØFTET af de eksisterende ofa/arko-breakers (cheap_provider_runtime.py)
#     så de tre parallelle impl. bliver til ÉN delt store (konsoliderings-reglen).
#
# Adskilt fra (provider, model)-store'en ovenfor med VILJE: forskellig nøgle,
# forskellig consecutive-i-træk-semantik (ikke deque-vindue-count), forskellig
# half-open-probe-kontrakt. De deler modul men ikke state — eksisterende callere
# er byte-uændrede.

_PP_DEFAULT_THRESHOLD = 4        # consecutive failures before OPEN (spec: "fx 4")
_PP_DEFAULT_COOLDOWN_S = 60.0    # stay OPEN, then half-open probe (spec: "fx 60s")
# Vindue: fejl ældre end dette nulstiller den consecutive-tæller (en enlig fejl
# for længe siden tæller ikke mod en frisk byge).
_PP_DEFAULT_WINDOW_S = 120.0


class _PPState:
    """Per-provider breaker-state (consecutive-i-træk-state-maskine)."""

    __slots__ = (
        "threshold", "cooldown_s", "window_s", "consecutive",
        "last_failure_at", "open_until", "is_open_flag", "half_open",
    )

    def __init__(self, threshold: int, cooldown_s: float, window_s: float) -> None:
        self.threshold = int(threshold)
        self.cooldown_s = float(cooldown_s)
        self.window_s = float(window_s)
        self.consecutive = 0
        self.last_failure_at = 0.0
        self.open_until = 0.0
        self.is_open_flag = False     # True mens OPEN (kort-slut aktiv)
        self.half_open = False        # True når én probe er sluppet igennem


class _PerProviderBreaker:
    """Proces-lokal per-provider-keyed breaker. Trådsikker, self-safe.

    STATE-MASKINE pr. provider_id:
        CLOSED    — normal; tæl consecutive failures.
        OPEN      — N+ fejl i træk; kort-slut indtil cooldown udløber.
        HALF_OPEN — cooldown udløbet; lad ÉN probe igennem.
                      probe success → CLOSED · probe failure → OPEN (ny cooldown).
    """

    def __init__(
        self,
        *,
        threshold: int = _PP_DEFAULT_THRESHOLD,
        cooldown_s: float = _PP_DEFAULT_COOLDOWN_S,
        window_s: float = _PP_DEFAULT_WINDOW_S,
    ) -> None:
        self._dthreshold = int(threshold)
        self._dcooldown = float(cooldown_s)
        self._dwindow = float(window_s)
        self._states: dict[str, _PPState] = {}
        self._overrides: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(provider_id: str) -> str:
        return (provider_id or "").strip().lower() or "unknown"

    def configure(
        self,
        provider_id: str,
        *,
        threshold: int | None = None,
        cooldown_s: float | None = None,
        window_s: float | None = None,
    ) -> None:
        """Per-provider-tærskler (ofa/arko bevarer deres historiske tal)."""
        pid = self._key(provider_id)
        ov: dict[str, float] = {}
        if threshold is not None:
            ov["threshold"] = int(threshold)
        if cooldown_s is not None:
            ov["cooldown_s"] = float(cooldown_s)
        if window_s is not None:
            ov["window_s"] = float(window_s)
        with self._lock:
            self._overrides[pid] = ov
            st = self._states.get(pid)
            if st is not None:
                if "threshold" in ov:
                    st.threshold = int(ov["threshold"])
                if "cooldown_s" in ov:
                    st.cooldown_s = float(ov["cooldown_s"])
                if "window_s" in ov:
                    st.window_s = float(ov["window_s"])

    def _state(self, pid: str) -> _PPState:
        st = self._states.get(pid)
        if st is None:
            ov = self._overrides.get(pid, {})
            st = _PPState(
                threshold=int(ov.get("threshold", self._dthreshold)),
                cooldown_s=float(ov.get("cooldown_s", self._dcooldown)),
                window_s=float(ov.get("window_s", self._dwindow)),
            )
            self._states[pid] = st
        return st

    def record_failure(self, provider_id: str, *, now: float | None = None) -> bool:
        """Fejl → opdatér state. True hvis breakeren NETOP åbnede (frisk kant)."""
        try:
            t = time.monotonic() if now is None else float(now)
            pid = self._key(provider_id)
            with self._lock:
                st = self._state(pid)
                if st.last_failure_at and (t - st.last_failure_at) > st.window_s:
                    st.consecutive = 0
                st.last_failure_at = t
                if st.half_open:
                    # Half-open probe FEJLEDE → genåbn (ny cooldown), ingen ny kant.
                    st.half_open = False
                    st.open_until = t + st.cooldown_s
                    st.is_open_flag = True
                    st.consecutive = max(st.consecutive, st.threshold)
                    return False
                st.consecutive += 1
                if st.consecutive >= st.threshold and not st.is_open_flag:
                    st.open_until = t + st.cooldown_s
                    st.is_open_flag = True
                    return True
                return False
        except Exception:
            return False

    def record_success(self, provider_id: str) -> bool:
        """Success → luk (reset). True hvis den netop lukkede (frisk kant)."""
        try:
            pid = self._key(provider_id)
            with self._lock:
                st = self._state(pid)
                was_open = st.is_open_flag or st.half_open
                st.consecutive = 0
                st.open_until = 0.0
                st.is_open_flag = False
                st.half_open = False
                return bool(was_open)
        except Exception:
            return False

    def is_open(self, provider_id: str, *, now: float | None = None) -> bool:
        """OPEN nu (→ kort-slut)? Cooldown udløbet → half-open (slip én probe →
        returnér False). Fail-OPEN: enhver intern fejl → False (bloker aldrig en
        sund provider pga. en breaker-bug)."""
        try:
            t = time.monotonic() if now is None else float(now)
            pid = self._key(provider_id)
            with self._lock:
                st = self._state(pid)
                if not st.is_open_flag:
                    return False
                if t >= st.open_until:
                    st.half_open = True   # slip én probe igennem
                    return False
                return True
        except Exception:
            return False

    def snapshot(self, provider_id: str) -> dict[str, Any]:
        try:
            pid = self._key(provider_id)
            with self._lock:
                st = self._state(pid)
                return {
                    "provider_id": pid,
                    "consecutive": st.consecutive,
                    "is_open": st.is_open_flag,
                    "half_open": st.half_open,
                    "open_until": st.open_until,
                    "threshold": st.threshold,
                    "cooldown_s": st.cooldown_s,
                }
        except Exception:
            return {"provider_id": self._key(provider_id)}

    def reset_all(self) -> None:
        with self._lock:
            self._states.clear()


# Proces-singleton for den delte per-provider breaker.
_PP = _PerProviderBreaker()


def _observe_pp(nerve: str, provider_id: str, **data: Any) -> None:
    """Observér en per-provider breaker-kant til Centralen (cluster="stream")."""
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "stream",
            "nerve": nerve,
            "provider_id": (provider_id or "").strip().lower(),
            **data,
        })
    except Exception:
        pass


def pp_configure(provider_id: str, **kw: Any) -> None:
    """Sæt per-provider-tærskler på den delte breaker (ofa/arko-løft)."""
    _PP.configure(provider_id, **kw)


def pp_record_failure(provider_id: str) -> bool:
    """Registrér en provider-fejl på den DELTE per-provider breaker + observér
    hvis den netop åbnede. Returnerer True på en frisk open-kant."""
    opened = _PP.record_failure(provider_id)
    if opened:
        snap = _PP.snapshot(provider_id)
        _observe_pp(
            "provider_circuit_open", provider_id,
            consecutive=int(snap.get("consecutive") or 0),
            cooldown_s=float(snap.get("cooldown_s") or 0.0),
            threshold=int(snap.get("threshold") or 0),
        )
    return opened


def pp_record_success(provider_id: str) -> bool:
    """Registrér success på den delte per-provider breaker + observér close-kant."""
    closed = _PP.record_success(provider_id)
    if closed:
        _observe_pp("provider_circuit_close", provider_id)
    return closed


def pp_is_open(provider_id: str) -> bool:
    """Er ``provider_id``'s delte breaker OPEN lige nu? (Fail-open.)"""
    return _PP.is_open(provider_id)


def pp_snapshot(provider_id: str) -> dict[str, Any]:
    """Debug/observe-snapshot af den delte per-provider breaker."""
    return _PP.snapshot(provider_id)


def pp_reset_all() -> None:
    """Test/admin: nulstil HELE den delte per-provider breaker."""
    _PP.reset_all()
