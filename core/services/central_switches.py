"""Live-kontrol for Centralen (§11). On/off pr. nerve/cluster via shared_cache-flag.
SIKKERHEDS-INVARIANT (§11.3): en sikkerheds-nerve kan ALDRIG slås fra — kun isoleres
mod deny. Plus CircuitBreaker (§11.2) og et minimalt drift-flag-skelet (§7)."""
from __future__ import annotations

import threading

from core.services import shared_cache
from core.services.gate_kernel import GateClass

_FLAG_TTL = 365 * 24 * 3600.0   # effektivt permanent indtil ændret


def _key(scope: str, name: str) -> str:
    return f"flag:central.switch.{scope}.{name}"


def set_enabled(scope: str, name: str, enabled: bool, *,
                klass: GateClass = GateClass.COGNITIVE) -> dict:
    """Slå en nerve/cluster on/off live. Sikkerheds-nerve + enabled=False afvises."""
    if klass is GateClass.SECURITY and not enabled:
        return {"ok": False, "scope": scope, "name": name,
                "reason": "sikkerheds-nerve kan ikke slås fra (kun isoleres mod deny)"}
    shared_cache.set(_key(scope, name), {"enabled": bool(enabled)}, ttl_seconds=_FLAG_TTL)
    return {"ok": True, "scope": scope, "name": name, "enabled": bool(enabled)}


def is_enabled(scope: str, name: str) -> bool:
    val = shared_cache.get(_key(scope, name))
    if isinstance(val, dict) and "enabled" in val:
        return bool(val["enabled"])
    return True   # default ON


def set_cluster_enabled(cluster: str, enabled: bool) -> dict:
    """Slå et HELT cluster on/off live (Jarvis' idé). Sikkerheds-cluster + enabled=False
    afvises (kan ikke slukkes, kun isoleres mod deny). Cognitive clusters kan frit slås fra
    → alle deres nerver SKIP'er i central().decide indtil de slås til igen (ingen genstart)."""
    if not enabled:
        try:
            from core.services.central_catalog import is_security_cluster
            if is_security_cluster(cluster):
                return {"ok": False, "scope": "cluster", "name": cluster,
                        "reason": "sikkerheds-cluster kan ikke slås fra (kun isoleres mod deny)"}
        except Exception:
            pass
    shared_cache.set(_key("cluster", cluster), {"enabled": bool(enabled)}, ttl_seconds=_FLAG_TTL)
    return {"ok": True, "scope": "cluster", "name": cluster, "enabled": bool(enabled)}


def is_cluster_enabled(cluster: str) -> bool:
    """True medmindre clusteret er EKSPLICIT slået fra. Default ON."""
    return is_enabled("cluster", cluster)


class CircuitBreaker:
    """Tæl fejl pr. nerve; isolér efter `threshold` på stribe. Nulstil ved succes."""

    def __init__(self, threshold: int = 5) -> None:
        self.threshold = threshold
        self._fails: dict[str, int] = {}
        self._lock = threading.Lock()

    def record(self, nerve: str, ok: bool) -> bool:
        """Returnér True hvis kredsen NETOP blev (eller fortsat er) åben/isoleret."""
        with self._lock:
            if ok:
                self._fails[nerve] = 0
                return False
            self._fails[nerve] = self._fails.get(nerve, 0) + 1
            return self._fails[nerve] >= self.threshold

    def is_open(self, nerve: str) -> bool:
        with self._lock:
            return self._fails.get(nerve, 0) >= self.threshold

    def reset(self, nerve: str) -> None:
        with self._lock:
            self._fails[nerve] = 0


def drift_flag(name: str, value: float, *, baseline: float, tol: float) -> dict | None:
    """Flag-on-change-skelet (§7): returnér en flag-dict hvis |value-baseline| > tol,
    ellers None. Holdes bevidst simpelt; kalibrering kommer i cluster-planerne."""
    if abs(value - baseline) > tol:
        return {"metric": name, "value": value, "baseline": baseline,
                "delta": round(value - baseline, 4)}
    return None
