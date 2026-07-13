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


def _egress_safe(payload: dict) -> dict:
    """§24.4 privatlags-membran. observe() skriver FULD payload til den lokale
    (owner-only) trace-sink — men det der forlader Centralen via ``_emit`` må ALDRIG
    bære indhold: private desire/tanke-tekst kan ligge i payload-STRENGE. Behold derfor
    KUN skalar tal/bool i emit-payloaden; drop strenge, lister og nested dicts.

    I dag er ``central.observed`` et uregistreret event-family (``central`` er ikke i
    ALLOWED_EVENT_FAMILIES → afvist i Event.create), så ``_emit`` er reelt en no-op og
    intet lækker. Denne redaktion gør membranen fail-closed OGSÅ hvis 'central' nogensinde
    registreres eller en bred subscriber wires — så indhold aldrig kan slippe ud ad bagdøren."""
    if not isinstance(payload, dict):
        return {}
    return {k: v for k, v in payload.items() if isinstance(v, (int, float, bool))}


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
    def observe(self, event: Any, *, emit: bool = True) -> None:
        """Best-effort telemetri. Kaster ALDRIG (§10.3).

        emit=False: registrér KUN til den owner-lokale trace-sink, spring egress-
        _emit over. Bruges af interne liveness-prober (fx central_self_probe i
        self_diagnose) der ellers ville egress'e til bussen på en egress-fri sti
        (§24.4) — record_private → trace-sink → xproc.maybe_publish → self_diagnose."""
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
            # Rådets #4: affektiv farve pr. nerve (tryk/varme/uro/ro). EGEN try/except —
            # affekt-beregningen må ALDRIG kunne påvirke resten af observe (hot-path).
            # Vi lægger affekten i den owner-lokale trace-payload FØR record, så den følger
            # med i tidsserien-meta. affect (streng) er trace-only; affect_intensity (float)
            # er en harmløs skalar der også må passere egress-membranen som metadata.
            try:
                from core.services.central_affect import classify_affect
                aff = classify_affect(
                    rec.cluster, rec.nerve,
                    str(event.get("kind") or "observe"),
                    event.get("value"),
                    flagged=bool(event.get("flagged")),
                )
                rec.payload["affect"] = aff["affect"]
                rec.payload["affect_intensity"] = aff["intensity"]
            except Exception:
                pass
            self._sink.record(rec)
            # Egress-membran (§24.4): trace-sinken fik FULD payload (owner-only, lokal).
            # _emit må kun bære skalar-metadata — aldrig indhold. Se _egress_safe.
            if emit:
                self._emit("central.observed", {
                    "run_id": rec.run_id, "session_id": rec.session_id,
                    "cluster": rec.cluster, "nerve": rec.nerve,
                    "payload": _egress_safe(rec.payload),
                })
        except Exception:
            pass

    # ── interne verdict-hjælpere ────────────────────────────────────────
    def _fail_verdict(self, nerve: str, klass: GateClass, reason: str) -> Verdict:
        # §8 "demokrati"-invariant (EKSPLICIT): et COGNITIVE-cluster der fejler returnerer SKIP
        # — ALDRIG RED. Det kan derfor aldrig blokere andre clusters via en fejl. KUN SECURITY-
        # clusters fail-closer til RED. Dette er reglen, ikke bare en konsekvens.
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
        v.cluster = cluster  # §4 arbitrage: bær cluster-tilhør med verdiktet
        # Rig attribuering (2026-07-13): thread run/session fra ctx ind i verdiktet, så
        # gate-fyringen er præcist attribuerbar. Self-safe — må aldrig påvirke beslutningen.
        try:
            if isinstance(ctx, dict):
                if not v.run_id:
                    v.run_id = str(ctx.get("run_id") or "")
                if not v.session_id:
                    v.session_id = str(ctx.get("session_id") or "")
        except Exception:
            pass
        try:
            cdict = ctx if isinstance(ctx, dict) else {}
            self._sink.record(central_trace.TraceRecord(
                run_id=str(cdict.get("run_id") or ""), session_id=str(cdict.get("session_id") or ""),
                cluster=cluster, nerve=nerve, kind="decide",
                decision=v.decision.value, reason=v.reason, latency_ms=v.latency_ms))
        except Exception:
            pass
        # Persistent verdict-ledger (billig in-memory increment; batchet flush på cadence).
        # Ground-truth til flip-beslutning (shadow→enforce) der OVERLEVER genstart, i modsætning
        # til den per-proces in-memory tidsserie. Selv-sikker — må aldrig påvirke governance.
        try:
            from core.services import gate_verdict_ledger
            gate_verdict_ledger.record(nerve, cluster, v.decision.value, v.reason)
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

    # ── §1 self-helbred: hvem overvåger Centralen? Den prober sig selv ──
    def self_diagnose(self) -> dict[str, Any]:
        """Meta-helbreds-check: virker Centralen SELV? Probe decide+observe, rapportér åbne
        breakers + sink-aktivitet. Self-safe — kaster aldrig. degraded=True hvis decide eller
        observe ikke fungerer (= Centralen er ved at fejle og skal eskaleres)."""
        out: dict[str, Any] = {"decide_ok": False, "observe_ok": False,
                               "open_breakers": [], "trace_records": 0}
        try:
            v = self.decide("central_self_probe", {"run_id": "health"},
                            lambda c: None, cluster="system", klass=GateClass.COGNITIVE)
            out["decide_ok"] = v.decision is Decision.GREEN
        except Exception:
            pass
        try:
            # emit=False: liveness-probe må ALDRIG egress'e (§24.4) — den kan nås fra en
            # egress-fri sti (record_private → trace-sink → xproc.maybe_publish → self_diagnose).
            self.observe({"cluster": "system", "nerve": "central_self_probe", "kind": "health"}, emit=False)
            out["observe_ok"] = True
        except Exception:
            pass
        try:
            out["open_breakers"] = self._breaker.open_nerves()
        except Exception:
            pass
        try:
            out["trace_records"] = len(self._sink.recent())
        except Exception:
            pass
        out["degraded"] = not (out["decide_ok"] and out["observe_ok"])
        return out

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
