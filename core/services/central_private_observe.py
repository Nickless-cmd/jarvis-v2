"""core/services/central_private_observe.py

Fase 2 — det indre livs liveness til Centralen, MEN egress-frit (spec §23.3 #3 / §24.4).

Jarvis' inner-life-daemons (inner_voice, dreams, witness, self_critique, prompt_evolution,
meta_learning, finitude, ...) er i dag helt mørke for Centralen: den kan ikke se om de
kører, tier, eller staganerer. Dette lukker hullet med ÉT hook i cadence-runneren
(ikke 35 steder) — men under en HÅRD isolations-invariant.

⛔ PRIVATLAGS-GRÆNSEN (§24.4 — BINDENDE, dette er kernen):
CLAUDE.md: private layers "must never outrank the protected core" og skal forblive private.
``central().observe()`` kalder ``_emit("central.observed", ...)`` → det PUBLICERER til
eventbus (→ potentiel egress til Discord/eksterne abonnenter). Derfor må inner-life ALDRIG
gå gennem den. I stedet skriver vi HER direkte til ``central_trace.sink()`` (den lokale
ring-buffer + owner-only SSE/HUD) UDEN ``_emit`` → ingen udgående kanal.

Yderligere invarianter:
  * KUN AGGREGERET LIVENESS krydser grænsen: ok / status / produced-count / empty.
    ALDRIG indhold, tekst, fingerprints eller payloads fra selve daemon-outputtet.
  * Cluster = "inner". Disse records må ALDRIG fodre learning/ingest_event eller heling
    (§24.4). De er ren owner-observabilitet.
"""
from __future__ import annotations

from typing import Any

from core.services import central_timeseries, central_trace

# De inner-life / metakognitive producers hvis liveness observes egress-frit.
# Ren infrastruktur (cache-warmere, cleanup, helbreds-scans, broen selv) er IKKE her —
# den er ikke privat og dækkes af de operationelle stier. Nye inner-daemons tilføjes her.
INNER_LIFE_PRODUCERS: frozenset[str] = frozenset({
    "brain_continuity", "sleep_consolidation", "witness_daemon", "inner_voice_daemon",
    "emergent_signal_daemon", "dream_articulation", "dream_distillation_daemon",
    "prompt_evolution_runtime", "self_critique_runtime", "ontological_revision",
    "creative_journal_runtime", "finitude_runtime", "finitude_monthly_reflection",
    "curiosity_idle_window", "meta_learning_weekly_retrospective",
    "curiosity_consolidation_weekly", "counterfactual_predictions_sweep",
    "life_projects_reassessment", "relation_map_refresh",
})

# Kun disse skalar-tælle-nøgler plukkes fra et producer-resultat — aldrig vilkårligt indhold.
_COUNT_KEYS = ("produced", "count", "written", "warmed", "kept", "consolidated",
               "emitted", "articulated", "n", "created")


def _liveness_from_result(status: str, result: Any) -> tuple[bool, int | None, bool | None]:
    """Udtræk KUN aggregeret liveness (ok, produced, empty) fra et producer-resultat.

    Ingen strings/payloads fra outputtet forlader denne funktion."""
    ok = status == "ran"
    produced: int | None = None
    empty: bool | None = None
    if isinstance(result, dict):
        for k in _COUNT_KEYS:
            v = result.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                produced = int(v)
                break
        rstatus = result.get("status")
        if rstatus in ("skipped", "noop", "empty"):
            empty = True
        elif produced is not None:
            empty = (produced == 0)
    return ok, produced, empty


def observe_hub(nerve: str, *, meta: dict[str, Any] | None = None) -> None:
    """EGRESS-FRI observe af en kognitions-HUB (aggregator på hot-path). De 4 load-bearing hubs
    (cognitive_conductor/cognitive_state_assembly/signal_surface_router/visible-turn-tracking) samler
    ~50 engines til prompten hver tur; ét observe her gør hele planet synligt for Centralen UDEN at
    røre de 50 enkeltvis. Metadata-only (kun skalarer — aldrig prompt-indhold). Skriver KUN til trace-
    sink + tidsserie, ALDRIG central().observe/_emit → egress-fri. Kaster aldrig."""
    try:
        m = {k: v for k, v in (meta or {}).items() if isinstance(v, (int, float, bool, str))}
        central_trace.sink().record(central_trace.TraceRecord(
            run_id="", session_id="", cluster="cognition", nerve=str(nerve),
            kind="observe", payload=m,
        ))
        central_timeseries.record("cognition", str(nerve), value=1.0, meta=m)
    except Exception:
        pass


def observe_liveness(nerve: str, *, ok: bool, status: str = "",
                     produced: int | None = None, empty: bool | None = None) -> None:
    """Registrér én inner-life-daemons liveness EGRESS-FRIT (§24.4).

    Skriver direkte til trace-sinken (owner-only) + per-nerve tidsserien. Kalder ALDRIG
    central().observe (som ville _emit til eventbus). Kaster aldrig."""
    try:
        payload: dict[str, Any] = {"ok": bool(ok)}
        if status:
            payload["status"] = str(status)
        if produced is not None:
            payload["produced"] = int(produced)
        if empty is not None:
            payload["empty"] = bool(empty)
        # DIREKTE til sinken — ingen _emit, ingen eventbus, ingen egress.
        central_trace.sink().record(central_trace.TraceRecord(
            run_id="", session_id="", cluster="inner", nerve=str(nerve),
            kind="observe", payload=payload,
        ))
    except Exception:
        pass
    try:
        central_timeseries.record(
            "inner", str(nerve),
            value=(1.0 if ok else 0.0),
            meta={"status": status, "empty": empty, "produced": produced},
        )
    except Exception:
        pass


def observe_operational_liveness(spec_name: str, status: str, result: Any) -> None:
    """Operationel (ikke-privat) cadence-daemon liveness → NORMAL observe (cluster=system,
    egress OK). §23.3 #13: provider_health/db_health/config_drift/stream_stall/tool_usage m.fl.
    får dermed samme dækning som inner-life. Self-safe."""
    try:
        ok, produced, empty = _liveness_from_result(status, result)
        payload: dict[str, Any] = {"cluster": "system", "nerve": spec_name,
                                   "kind": "observe", "ok": bool(ok)}
        if status:
            payload["status"] = str(status)
        if produced is not None:
            payload["produced"] = int(produced)
        from core.services.central_core import central
        central().observe(payload)
    except Exception:
        pass
    try:
        central_timeseries.record("system", spec_name, value=(1.0 if status == "ran" else 0.0),
                                  meta={"status": status})
    except Exception:
        pass


def observe_cadence_liveness(spec_name: str, status: str, result: Any) -> None:
    """Cadence-hook (§23.3 #3 — ÉT sted for ALLE ~137 cadence-daemons). Router:
    inner-life → EGRESS-FRI (lokal trace, §24.4); operationelt → NORMAL observe (§23.3 #13).
    Kaster aldrig."""
    try:
        if spec_name in INNER_LIFE_PRODUCERS:
            ok, produced, empty = _liveness_from_result(status, result)
            observe_liveness(spec_name, ok=ok, status=status, produced=produced, empty=empty)
        else:
            observe_operational_liveness(spec_name, status, result)
    except Exception:
        pass
