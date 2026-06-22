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
        # §7 flag-on-change: aktiv drift-detektion pr. nerve (deterministisk, read-only).
        from core.services.central_drift import NerveDriftMonitor
        self._drift = NerveDriftMonitor()

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

    def _record_error(self, err: "central_capture.ErrorRecord", *, severe: bool = False) -> None:
        run_id = str((err.signal or {}).get("run_id") or "")
        session_id = str((err.signal or {}).get("session_id") or "")
        try:
            self._sink.record(central_trace.TraceRecord(
                run_id=run_id, session_id=session_id,
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
        # ── Persistent incident-log (notifikation begge veje, 2026-06-22) ──
        # Ring-bufferen tabes ved genstart + er per-proces; persistér så incidenten
        # kan fanges live på tværs af processer + overlever genstart. Claude poller
        # central_incidents; Bjørn (owner) push-notificeres ved ALVORLIGE (circuit-
        # breaker-åbning eller sikkerheds-fejl). Selv-sikker — central må aldrig vælte.
        severity = "severe" if (severe or err.klass is GateClass.SECURITY) else "error"
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(
                cluster=err.cluster, nerve=err.nerve, kind=err.kind,
                severity=severity, message=err.message,
                run_id=run_id, session_id=session_id,
            )
        except Exception:
            pass
        if severity == "severe":
            try:
                from core.services.ntfy_gateway import send_notification
                send_notification(
                    f"⚠ Central greb ALVORLIG fejl: {err.cluster}/{err.nerve} — "
                    f"{str(err.message)[:160]}",
                    title="Den Intelligente Central",
                    priority="high",
                )
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
        # cluster-level live-switch (Jarvis' idé): et HELT cluster kan slås fra. KUN cognitive —
        # sikkerheds-cluster ignorerer dette (kan ikke slukkes; set_cluster_enabled afviser også).
        if (cluster and klass is not GateClass.SECURITY
                and not central_switches.is_enabled("cluster", cluster)):
            return Verdict(nerve, Decision.SKIP, "cluster-disabled", klass=klass)
        # circuit-breaker allerede åben (§11.2) → isolér uden at kalde nerven
        if self._breaker.is_open(nerve):
            return self._isolated_verdict(nerve, klass)

        result, err = central_capture.safe_call(fn, ctx, nerve=nerve, cluster=cluster, klass=klass)
        if err is not None:
            opened = self._breaker.record(nerve, ok=False)
            self._record_error(err, severe=opened)
            self._maybe_flag_drift(nerve, cluster, is_error=True, is_red=False)
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
        self._maybe_flag_drift(nerve, cluster, is_error=False, is_red=(v.decision is Decision.RED))
        return v

    def _maybe_flag_drift(self, nerve: str, cluster: str, *, is_error: bool, is_red: bool) -> None:
        """§7 flag-on-change: opdatér drift-monitor; hvis nervens fejl-/red-rate netop drev
        ud over baseline → FLAG det (persistent incident + trace). Selv-sikker, read-only."""
        try:
            flag = self._drift.record(nerve, is_error=is_error, is_red=is_red)
            if not flag:
                return
            msg = (f"drift: {flag.get('metric')} {flag.get('baseline')}→{flag.get('value')} "
                   f"(Δ{flag.get('delta')})")
            self.observe({"cluster": cluster, "nerve": nerve, "kind": "drift", **flag})
            try:
                from core.runtime.db_central_incidents import record_central_incident
                record_central_incident(cluster=cluster, nerve=nerve, kind="drift",
                                        severity="error", message=msg)
            except Exception:
                pass
        except Exception:
            pass

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
