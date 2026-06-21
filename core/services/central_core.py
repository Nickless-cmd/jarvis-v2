"""Den Intelligente Central — facade (§3.1). Komponerer gate_kernel (decide-motor)
med trace-sink, boundary-capture og live-switches. To ansigter: observe (asynkront
telemetri) + decide (synkron beslutning pr. nerve). Alt selv-sikkert."""
from __future__ import annotations

from typing import Any, Callable

from core.services import central_capture, central_switches, central_trace
from core.services.gate_kernel import (Decision, GateClass, GateKernel, Verdict,
                                       _Gate, _normalize, kernel)


def _default_emit(kind: str, payload: dict) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(kind, payload)
    except Exception:
        pass


def _coerce_verdict(nerve: str, raw: Any, klass: GateClass) -> Verdict:
    """Normalisér en nerve-returværdi til Verdict (genbruger kernens parser)."""
    v = _normalize(_Gate(nerve, "", lambda c: raw, klass, 1000, ""), raw)
    v.klass = klass
    return v


class Central:
    def __init__(self, *, k: GateKernel | None = None,
                 sink: central_trace.TraceSink | None = None,
                 breaker: central_switches.CircuitBreaker | None = None,
                 emit: Callable[[str, dict], None] | None = None) -> None:
        self._k = k or kernel()
        self._sink = sink or central_trace.sink()
        self._breaker = breaker or central_switches.CircuitBreaker()
        self._emit = emit or _default_emit

    # ── observe (asynkront-agtigt telemetri-ansigt) ─────────────────────
    def observe(self, event: Any) -> None:
        """Best-effort telemetri. Kaster ALDRIG (§10.3)."""
        try:
            if not isinstance(event, dict):
                return
            reserved = ("run_id", "session_id", "cluster", "nerve")
            rec = central_trace.TraceRecord(
                run_id=str(event.get("run_id") or ""),
                session_id=str(event.get("session_id") or ""),
                cluster=str(event.get("cluster") or ""),
                nerve=str(event.get("nerve") or ""),
                kind="observe",
                payload={k: v for k, v in event.items() if k not in reserved},
            )
            self._sink.record(rec)
            self._emit("central.observed", {
                "run_id": rec.run_id, "session_id": rec.session_id,
                "cluster": rec.cluster, "nerve": rec.nerve, "payload": rec.payload,
            })
        except Exception:
            pass

    # ── interne verdict-hjælpere ────────────────────────────────────────
    def _fail_verdict(self, nerve: str, klass: GateClass, reason: str) -> Verdict:
        if klass is GateClass.SECURITY:
            return Verdict(nerve, Decision.RED, reason, action="block", klass=klass)
        return Verdict(nerve, Decision.SKIP, reason, action="none", klass=klass)

    def _isolated_verdict(self, nerve: str, klass: GateClass) -> Verdict:
        if klass is GateClass.SECURITY:
            return Verdict(nerve, Decision.RED, "isoleret-deny", action="block", klass=klass)
        return Verdict(nerve, Decision.SKIP, "isoleret", action="none", klass=klass)

    def _record_error(self, err: "central_capture.ErrorRecord") -> None:
        try:
            self._sink.record(central_trace.TraceRecord(
                run_id=str((err.signal or {}).get("run_id") or ""),
                session_id=str((err.signal or {}).get("session_id") or ""),
                cluster=err.cluster, nerve=err.nerve, kind="error",
                reason=err.message, latency_ms=err.latency_ms,
                payload={"kind": err.kind, "klass": err.klass.value, "stack": err.stack},
            ))
            self._emit("central.error", {
                "nerve": err.nerve, "cluster": err.cluster, "kind": err.kind,
                "message": err.message, "klass": err.klass.value,
            })
        except Exception:
            pass

    # ── decide (synkront beslutnings-ansigt) ────────────────────────────
    def decide(self, nerve: str, ctx: Any, fn: Callable[[dict], Any], *,
               cluster: str = "", klass: GateClass = GateClass.COGNITIVE) -> Verdict:
        """Kør én nerve med live-switch + boundary-capture + circuit-breaker + trace.
        Kognitiv fejl → SKIP (fail-open); sikkerhed → RED (fail-closed §9)."""
        # live-switch (§11.1) — sikkerheds-nerve kan ikke slukkes, kun deny'es
        if not central_switches.is_enabled("nerve", nerve):
            if klass is GateClass.SECURITY:
                return self._isolated_verdict(nerve, klass)
            return Verdict(nerve, Decision.SKIP, "disabled", klass=klass)
        # circuit-breaker allerede åben (§11.2) → isolér uden at kalde nerven
        if self._breaker.is_open(nerve):
            return self._isolated_verdict(nerve, klass)

        result, err = central_capture.safe_call(fn, ctx, nerve=nerve, cluster=cluster, klass=klass)
        if err is not None:
            opened = self._breaker.record(nerve, ok=False)
            self._record_error(err)
            return self._isolated_verdict(nerve, klass) if opened \
                else self._fail_verdict(nerve, klass, err.message)
        self._breaker.record(nerve, ok=True)
        v = _coerce_verdict(nerve, result, klass)
        try:
            cdict = ctx if isinstance(ctx, dict) else {}
            self._sink.record(central_trace.TraceRecord(
                run_id=str(cdict.get("run_id") or ""), session_id=str(cdict.get("session_id") or ""),
                cluster=cluster, nerve=nerve, kind="decide",
                decision=v.decision.value, reason=v.reason, latency_ms=v.latency_ms))
        except Exception:
            pass
        return v

    # ── registry-passthrough til kernen ─────────────────────────────────
    def register(self, name: str, phase: str, fn: Callable[[dict], Any], *,
                 klass: GateClass = GateClass.COGNITIVE, timeout_ms: int = 1500,
                 flag_key: str = "") -> None:
        self._k.register(name, phase, fn, klass=klass, timeout_ms=timeout_ms, flag_key=flag_key)


# Singleton — én Central pr. proces.
_CENTRAL: Central | None = None


def central() -> Central:
    global _CENTRAL
    if _CENTRAL is None:
        _CENTRAL = Central()
    return _CENTRAL
