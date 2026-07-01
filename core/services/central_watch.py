"""core/services/central_watch.py

Det AKTIVE lag (Bjørn 1. jul: "centralen skal kunne flagge, notificere, logge, debug,
fuld trace live begge veje ... og faktisk lære, ikke bare observere").

Fase 0-2 fodrede Centralen med rå observe-data. Denne vagt gør data HANDLINGSBAR: den
læser de fodrede streams, kører hvert signal gennem støjfangeren, og for ægte signaler:
  * FLAGGER   → observe(kind=flag) i trace (synligt begge veje: owner-HUD + Jarvis)
  * LÆRER     → record_central_incident → som central_learning LÆSER (degrading/root_causes/
                propose_adjustments) → adaptiv læring fodres med det der kommer ind
  * NOTIFICERER → route_proactive_notification til owner ved high/critical (begge veje)
  * LOGGER    → per-nerve tidsserie (debugbar trend)

GRÆNSER (aktiv ÆNDRING kommer til sidst — Bjørn):
  * Vagten LÆRER + FLAGGER + NOTIFICERER, men MUTERER ALDRIG adfærd (ingen threshold-adjust,
    ingen heling, ingen self-modifikation). Forslag er reviewbare (poll_proposals), ikke handlinger.
  * §24.5: Centralens EGEN meta (decide-latency-drift) flagges+notificeres men skaber INGEN
    lærings-incident (selv-refererende incident → learning-feedback-loop). Kun observe+notify.
  * Alt gated af støjfangeren (central_noise_filter) → ingen flag/læring på blips.
"""
from __future__ import annotations

from typing import Any

from core.services import central_noise_filter, central_timeseries
from core.services.central_core import central

# Tærskler (bevidst konservative — støjfangeren kræver desuden persistens oveni).
_LATENCY_DRIFT_MS = 250.0     # decide-latency-drift der tæller som ægte regression
_INNER_SILENCE_MIN = 3        # inner-daemon-fejl/tomme i træk før det er en bekymring
_CACHE_COLD_PCT = 10.0        # prefix-cache hit-rate under dette (vedvarende) = brækket cache


def _owner_uid() -> str:
    try:
        from core.identity.owner_resolver import get_owner_discord_id
        return (get_owner_discord_id() or "").strip()
    except Exception:
        return ""


def _notify_owner(title: str, message: str, importance: str) -> bool:
    uid = _owner_uid()
    if not uid:
        return False
    try:
        from core.services.notification_router import route_proactive_notification
        res = route_proactive_notification(
            uid, "central_flag",
            {"title": title, "message": message}, importance=importance)
        return bool(res.get("delivered"))
    except Exception:
        return False


def _raise_flag(cluster: str, nerve: str, *, severity: str, message: str,
                importance: str = "medium", make_incident: bool = True) -> dict:
    """Ét flag → trace + (læring via incident) + (notifikation) + tidsserie. Self-safe."""
    out: dict[str, Any] = {"cluster": cluster, "nerve": nerve, "severity": severity,
                           "message": message, "notified": False, "incident": False}
    # 1. FLAG i trace (begge veje: owner-HUD + Jarvis' feed)
    try:
        central().observe({"cluster": cluster, "nerve": nerve, "kind": "flag",
                           "severity": severity, "message": message[:400]})
    except Exception:
        pass
    # 2. LÆR: incident → central_learning læser central_incidents (fodrer adaptiv læring).
    #    IKKE for Centralens egen meta (§24.5: selv-refererende → feedback-loop).
    if make_incident:
        try:
            from core.runtime.db_central_incidents import record_central_incident
            record_central_incident(cluster=cluster, nerve=nerve, kind="flag",
                                    severity=severity, message=message[:400])
            out["incident"] = True
        except Exception:
            pass
    # 3. NOTIFICÉR owner ved høj alvor (begge veje)
    if importance in ("high", "critical"):
        out["notified"] = _notify_owner(f"Central-flag: {cluster}/{nerve}", message, importance)
    # 4. LOG: tidsserie (debugbar)
    try:
        central_timeseries.record(cluster, f"{nerve}__flag", value=1.0,
                                  meta={"severity": severity})
    except Exception:
        pass
    return out


def _latest(cluster: str, nerve: str):
    rec = central_timeseries.recent(cluster, nerve, limit=1)
    return rec[-1] if rec else None


def run_watch_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Evaluér de fodrede streams; flag ægte (støjfangede) signaler. Self-safe."""
    flags: list[dict] = []

    # ── A. Bro-observe-fejl (§24.3: må aldrig sluges stille) ──
    try:
        s = _latest("system", "bridge_observe_failures")
        breached = bool(s) and float(s.value or 0) > 0
        if central_noise_filter.is_real_signal("bridge_failures", breached):
            n = int(s.value)
            flags.append(_raise_flag(
                "system", "eventbus_bridge", severity="error",
                message=f"Bro-observe fejlede for {n} events (streams når ikke Centralen)",
                importance="high"))
    except Exception:
        pass

    # ── B. Centralens EGEN decide-latency-drift (§24.5: notify+observe, INGEN incident) ──
    try:
        s = _latest("system", "central_meta")
        drift = float((s.meta or {}).get("drift_ms") or 0) if s else 0.0
        breached = abs(drift) > _LATENCY_DRIFT_MS
        if central_noise_filter.is_real_signal("central_latency_drift", breached):
            flags.append(_raise_flag(
                "system", "central_meta", severity="error",
                message=f"Centralens decide-latency drifter {drift:+.0f}ms fra baseline",
                importance="high", make_incident=False))  # §24.5: ingen selv-incident
    except Exception:
        pass

    # ── C. Åbne circuit-breakers ──
    try:
        s = _latest("system", "central_meta")
        opb = int((s.meta or {}).get("open_breakers") or 0) if s else 0
        breached = opb > 0
        if central_noise_filter.is_real_signal("open_breakers", breached):
            flags.append(_raise_flag(
                "system", "breaker", severity="severe",
                message=f"{opb} circuit-breaker(e) åbne — nerve(r) isoleret",
                importance="critical"))
    except Exception:
        pass

    # ── D. Inner-life-daemons der fejler/tier (Jarvis' metakognition stagnerer) ──
    try:
        for (cl, nv) in central_timeseries.nerves():
            if cl != "inner":
                continue
            recent = central_timeseries.recent(cl, nv, limit=_INNER_SILENCE_MIN)
            if len(recent) < _INNER_SILENCE_MIN:
                continue
            all_down = all((r.value or 0) == 0.0 for r in recent)
            if central_noise_filter.is_real_signal(f"inner:{nv}", all_down):
                # inner-life fodrer læring (legitimt signal) men notificeres ikke som push
                # (medium) — undgår at spamme owner på indre udsving.
                flags.append(_raise_flag(
                    "inner", nv, severity="error",
                    message=f"Inner-life-daemon '{nv}' har fejlet/tiet {_INNER_SILENCE_MIN} tick i træk",
                    importance="medium"))
    except Exception:
        pass

    # ── E. Cache kold (spec §3.2): prefix-cache hit-rate kollapset = ~10x omkostning ──
    # VIGTIGT (cross-proces): cache produceres i api-processen (record_visible_cache), men
    # vagten kører i runtime-processen. In-process-tidsserien ser den derfor IKKE. Vi læser
    # i stedet cache.telemetry fra EVENTBUSSEN (DB-backet = cross-proces sandhed).
    try:
        pcts = _recent_cache_pcts(limit=6)
        if pcts:
            # Flag kun hvis SELV de varmeste kald er kolde (max<tærskel = caching reelt død;
            # første-kald-miss er normalt og skal ikke flagge en sund cache).
            breached = max(pcts) < _CACHE_COLD_PCT
            if central_noise_filter.is_real_signal("cache_cold", breached):
                flags.append(_raise_flag(
                    "cost", "prefix_cache", severity="error",
                    message=f"Cache kold: bedste hit-rate {max(pcts):.0f}% over {len(pcts)} kald "
                            f"(prefix-cache brækket → ~10x omkostning)",
                    importance="medium"))  # incident+læring, ingen push (undgå cache-spam)
    except Exception:
        pass

    # ── F. Recall svigter (§23.3 #4): memory returnerer VEDVARENDE intet = recall brudt ──
    # Cross-proces (recall kører også i api-processen) → læs fra eventbus.
    try:
        counts = _recent_recall_counts(limit=6)
        if len(counts) >= 3:
            breached = all(c == 0 for c in counts[:3])  # seneste 3 recalls alle tomme
            if central_noise_filter.is_real_signal("recall_empty", breached):
                flags.append(_raise_flag(
                    "memory", "recall", severity="error",
                    message="Recall returnerer intet over de seneste kald (memory-recall brudt?)",
                    importance="medium"))
    except Exception:
        pass

    return {"status": "ok", "flags": flags, "flag_count": len(flags)}


def _recent_recall_counts(*, limit: int = 6) -> list[int]:
    """Læs seneste recall-result-counts fra eventbussen (cross-proces). Self-safe."""
    out: list[int] = []
    try:
        from core.eventbus.bus import event_bus
        for r in event_bus.recent_by_family("memory", limit=limit):
            if r.get("kind") != "memory.recall":
                continue
            rc = (r.get("payload") or {}).get("result_count")
            if rc is not None:
                out.append(int(rc))
    except Exception:
        pass
    return out


def _recent_cache_pcts(*, limit: int = 6) -> list[float]:
    """Læs seneste cache-hit-rater fra eventbussen (cross-proces). Self-safe."""
    out: list[float] = []
    try:
        from core.eventbus.bus import event_bus
        for r in event_bus.recent_by_family("cache", limit=limit):
            pct = (r.get("payload") or {}).get("pct")
            if pct is not None:
                out.append(float(pct))
    except Exception:
        pass
    return out


def register_watch_producer() -> None:
    """Registrér vagten som cadence-producer (~hvert 2 min). Læser tidsserie + flagger."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_watch",
        cooldown_minutes=2,
        visible_grace_minutes=0,
        run_fn=run_watch_tick,
        priority=4,
    ))
