"""core/services/central_router_adapt.py

DEN MODIGE DEL — Tråd 1 (model-routing), Fase 3-4: routing-PRÆFERENCE-læreren.

Fra Tråd 1's model_meta-viden (hvilke modeller er hurtigere/mere pålidelige) lærer Centralen en
PRÆFERENCE: "for denne lane, foretræk model X." Præferencen er §8-drift-gated + B4-auditeret + SHADOW
som default. Den LÆRER af RESOLVEREDE model_meta-hypoteser (grounded, §8-passerede) — ikke rå tal.

⚠️ SPEC §3 (ikke-forhandlelige):
  * ALDRIG præference-override på reasoning/deep-tier (hvor fejl er dyrest).
  * SHADOW default (`model_router_adapt_live_enabled=False`) → skriver kun shadow-diff, rører IKKE
    routing. Live-præferencen læses af routing-KONSUMENTEN (visible_runs) — som er en separat,
    bevidst hot-path-ændring bag samme flag (IKKE wiret her; se §KONSUMENT nederst).
  * Kun blandt KONFIGUREREDE providers (aldrig peg på en model der ikke findes).
  * fail-safe: enhver tvivl → ingen præference (behold default). Kaster ALDRIG.

Dette modul er HJERNEN (beslutning). Den er nyttig standalone: den gør model_meta-viden til en
eksplicit, auditeret præference Bjørn kan se i shadow FØR nogen routing ændres.
"""
from __future__ import annotations

from typing import Any

from core.services import central_hypothesis_governance as gov

_LIVE_FLAG = "model_router_adapt_live_enabled"      # Bjørns switch (default OFF)
_PREF_KEY = "model_router_preference"               # {lane: {"model":..., "strength":...}} — konsumenten læser
_SHADOW_KEY = "model_router_preference_shadow"      # foreslået præference (shadow-diff til Bjørn)
_DOMAIN = "model_router"
_MIN_SUPPORT = 3                 # ≥ så mange supporterede kontraster før en præference må dannes
_STRENGTH_BUDGET = 1.0           # §8: præference-styrke ∈ [0,1]; drift mod anker 0
_NEVER_TIERS = frozenset({"reasoning", "deep", "thinking", "think", "reason"})  # tier-TOKENS (ikke substrings)

# ── Recent-health-gate (kvote/nedbrud-værn) ─────────────────────────
# Læreren rangerer på ALL-TIME model_meta-sejre og er BLIND for AKTUEL tilgængelighed.
# 2026-07-11: den lærte kimi-k2.7-code:cloud (all-time-vinder) mens den var kvote-ramt
# (recent success-rate 0.40) → alle visible-runs (inkl. jarvis-code) routede til en død model,
# selvom deepseek-base kørte 0.84. Gaten: honorér ALDRIG en lært præference hvis modellens
# FRISKE success-rate er under gulvet (med nok samples). Fail-open: kan ikke måle → antag sund.
_HEALTH_FLOOR = 0.5              # recent success-rate under dette = degraderet (fx kvote)
_HEALTH_MIN_SAMPLES = 5         # kræv nok friske samples før vi dømmer en model usund
_HEALTH_TTL = 60.0             # hot-path: cache aggregatet i 60s (kaldes pr. visible-run)
_health_cache: dict[str, Any] = {"at": -1e9, "rates": {}}


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def is_live_enabled() -> bool:
    return bool(_kv_get(_LIVE_FLAG, False))


def _ensure_anchor() -> None:
    """§8: ankr præference-styrke = 0 (ingen routing-mutation) for model_router-domænet. Idempotent."""
    try:
        if gov.get_anchored_baseline(domain=_DOMAIN) is None:
            gov.anchor_identity_baseline({"strength": 0.0}, version="router_adapt_v1",
                                         approved_by="central_router_adapt", domain=_DOMAIN)
    except Exception:
        pass


def _is_never_tier(model_key: str) -> bool:
    """True hvis model-nøglen betegner reasoning/deep-tier. TOKEN-match (split på ikke-alfanumerisk)
    så 'deepseek' (brand) IKKE fejlagtigt fanges af 'deep' (tier). Self-safe."""
    import re
    tokens = set(re.split(r"[^a-z0-9]+", str(model_key or "").lower()))
    return bool(tokens & _NEVER_TIERS)


def _recent_success_rate(model_key: str) -> tuple[float, int]:
    """(recent success-rate, samples) for en model i det friske model_meta-vindue. Cachet i
    _HEALTH_TTL sek (kaldes på hot-path pr. visible-run). Fail-open → (1.0, 0). Self-safe."""
    import time as _t
    now = _t.monotonic()
    if now - float(_health_cache["at"]) > _HEALTH_TTL or not _health_cache["rates"]:
        try:
            from core.services.central_model_meta import aggregate_model_outcomes
            _health_cache["rates"] = {
                k: (float(d.get("success_rate") or 0.0), int(d.get("samples") or 0))
                for k, d in aggregate_model_outcomes().items()
            }
            _health_cache["at"] = now
        except Exception:
            return (1.0, 0)
    return _health_cache["rates"].get(str(model_key), (1.0, 0))


def _is_currently_healthy(model_key: str) -> bool:
    """False KUN når vi har ≥_HEALTH_MIN_SAMPLES friske samples OG recent success-rate < gulvet
    (degraderet/kvote-ramt). Manglende/utilstrækkelige data → sund (fail-open, ingen falsk
    blokering). Self-safe."""
    try:
        rate, n = _recent_success_rate(model_key)
        if n >= _HEALTH_MIN_SAMPLES and rate < _HEALTH_FLOOR:
            return False
    except Exception:
        pass
    return True


def _configured_models() -> set[str]:
    """Modeller der FAKTISK er konfigureret (aldrig peg på noget der ikke findes). Self-safe."""
    out: set[str] = set()
    try:
        from core.services.central_model_meta import aggregate_model_outcomes
        # de modeller Centralen rent faktisk har set køre = de reelt tilgængelige
        for k, d in aggregate_model_outcomes().items():
            if int(d.get("samples") or 0) > 0:
                out.add(k)
    except Exception:
        pass
    return out


def compute_preference() -> dict[str, Any]:
    """Læs RESOLVEREDE, supporterede model_meta-hypoteser → tæl 'sejre' pr. model → foreslå den mest
    dominerende KONFIGUREREDE ikke-deep-tier model som visible-præference. Self-safe."""
    wins: dict[str, int] = {}
    try:
        from core.runtime.db import connect
        with connect() as c:
            rows = c.execute(
                "SELECT provenance_json FROM central_hypotheses WHERE source='model_meta' "
                "AND status='resolved' AND outcome='supported'").fetchall()
        import json
        for r in rows:
            fam = str(json.loads(r["provenance_json"] or "{}").get("family") or "")
            # family = "<metric>:<winner>><loser>"
            _, _, rest = fam.partition(":")
            winner, _, _loser = rest.partition(">")
            if winner:
                wins[winner] = wins.get(winner, 0) + 1
    except Exception:
        return {"enough": False, "preferred": None, "support": 0}
    configured = _configured_models()
    # kun konfigurerede, ikke-deep-tier, AKTUELT SUNDE vindere (spring kvote-ramte over)
    ranked = sorted(((m, n) for m, n in wins.items()
                     if m in configured and not _is_never_tier(m) and _is_currently_healthy(m)),
                    key=lambda kv: kv[1], reverse=True)
    if not ranked or ranked[0][1] < _MIN_SUPPORT:
        return {"enough": False, "preferred": ranked[0][0] if ranked else None,
                "support": ranked[0][1] if ranked else 0}
    top_model, support = ranked[0]
    total = sum(wins.values()) or 1
    strength = round(min(1.0, support / total), 3)
    return {"enough": True, "preferred": top_model, "support": support, "strength": strength}


def run_router_adapt_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: beregn foreslået præference → §8-gate → SHADOW-diff altid; skriv live-præference KUN
    hvis flag ON + gate ok + ikke-deep-tier + konfigureret. Rører aldrig routing selv. Self-safe."""
    _ensure_anchor()
    pref = compute_preference()
    applied = False
    gate_action = "none"
    if pref.get("enough") and pref.get("preferred"):
        strength = float(pref["strength"])
        # SHADOW-diff altid synlig
        _kv_set(_SHADOW_KEY, {"visible": {"model": pref["preferred"], "strength": strength}})
        verdict = gov.gate_self_mutation({"strength": strength},
                                         budgets={"strength": _STRENGTH_BUDGET}, domain=_DOMAIN)
        gate_action = verdict.action
        if is_live_enabled() and verdict.action != "rollback" and not _is_never_tier(pref["preferred"]):
            _audit_notation(pref["preferred"])
            live = _kv_get(_PREF_KEY, {}) or {}
            if isinstance(live, dict):
                live["visible"] = {"model": pref["preferred"], "strength": strength}
                _kv_set(_PREF_KEY, live)
                applied = True
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "router_adapt", value=float(pref.get("strength") or 0.0),
                       meta={"preferred": pref.get("preferred"), "support": pref.get("support"),
                             "enough": pref.get("enough"), "applied": applied, "gate": gate_action,
                             "live": is_live_enabled()})
    except Exception:
        pass
    return {"status": "ok", "mode": "live" if is_live_enabled() else "shadow",
            "preferred": pref.get("preferred"), "support": pref.get("support"),
            "applied": applied, "gate": gate_action}


def _audit_notation(model_key: str) -> dict[str, Any] | None:
    """Best-effort B4-audit: præferencen som notation (stemme → handling = den valgte stemme fører
    til handling). Til inspektbarhed; §8 er den hårde gate. Self-safe."""
    try:
        from core.services.central_proposal import make_proposal
        return make_proposal(domain=_DOMAIN, notation="stemme → handling",
                             rationale=f"routing-præference: {model_key}")
    except Exception:
        return None


def get_live_preference(lane: str = "visible") -> dict[str, Any] | None:
    """KONSUMENT-API (til den fremtidige routing-wire): den LIVE præference for en lane, eller None.
    Returnerer KUN når flag ON (ellers None → default routing). Self-safe.

    §KONSUMENT: visible_runs' model-valg skal — bag samme flag — konsultere denne. Det er en bevidst
    hot-path-ændring (Boy Scout på visible_runs) som IKKE er wiret endnu; denne funktion er kontrakten."""
    if not is_live_enabled():
        return None
    try:
        pref = _kv_get(_PREF_KEY, {}) or {}
        p = pref.get(str(lane)) if isinstance(pref, dict) else None
        if isinstance(p, dict) and p.get("model") and not _is_never_tier(p["model"]):
            # Recent-health-gate: en tidligere-lært præference kan være blevet kvote-ramt/degraderet
            # SIDEN den blev skrevet (læreren kører kun hver 45 min). Honorér den ALDRIG hvis den er
            # usund nu → return None → konsumenten falder tilbage til base default (fx deepseek).
            if not _is_currently_healthy(p["model"]):
                _note_health_suppressed(p["model"])
                return None
            return p
    except Exception:
        pass
    return None


def _note_health_suppressed(model_key: str) -> None:
    """Best-effort: gør det synligt når en lært præference undertrykkes pga. dårlig recent-health.
    Self-safe (må aldrig påvirke routing)."""
    try:
        from core.services.central_private_observe import record_private
        rate, n = _recent_success_rate(model_key)
        record_private("cognition", "router_health_suppressed", value=float(rate),
                       meta={"model": model_key, "samples": n, "floor": _HEALTH_FLOOR})
    except Exception:
        pass


def resolve_visible_model(*, provider_override: str = "", model_override: str = "",
                          default_provider: str, default_model: str,
                          autonomous: bool = False) -> tuple[str, str]:
    """KONSUMENTEN (Tråd 1 live-wire): afgør (provider, model) for et visible-run. Centraliserer den
    tidligere inline-dublerede selektion + anvender (a) EKSPLORATIONS-ARMEN (kun autonome runs, skaber
    kontrast) og (b) den LÆRTE routing-præference — men KUN når:
      * en eksplicit override IKKE er sat (rolle-clampet member-override vinder ALTID — sikkerhed), OG
      * flag er ON + grounded/konfigureret/ikke-deep-tier.
    Default/shadow → uændret adfærd (base). Kaster ALDRIG — fail-safe til base."""
    base_provider = (str(provider_override or "").strip() or default_provider)
    base_model = (str(model_override or "").strip() or default_model)
    try:
        # eksplicit override (fx member→ollama-clamp) er ukrænkelig — intet må røre den
        if str(provider_override or "").strip() or str(model_override or "").strip():
            return base_provider, base_model
        # OWNER/MEMBER INTERAKTIV VISIBLE (autonomous=False): ALTID dit eksplicitte valg /
        # config-default. Den LÆRTE routing-præference må ALDRIG overrule hvad brugeren valgte
        # (/model i jarvis-code, composer i desk). Lært/adaptiv routing er indelukket til den
        # autonome/dispatch-lane nedenfor. Bjørn 2026-07-19: din deepseek ≠ agent-pool ≠ cheap-lane
        # — routeren lærte 'kimi-k2.7-code' fra blandet visible-trafik og påtvang den DINE ture.
        if not autonomous:
            return base_provider, base_model
        # (a) EKSPLORATION: kun autonome runs — sample occasionelt en alternativ model (skab kontrast)
        if autonomous:
            from core.services import central_router_explore as _explore
            alt = _explore.pick_exploration_model(base_provider, base_model)
            if alt:
                return alt
        # (b) LÆRT PRÆFERENCE
        pref = get_live_preference("visible")     # None i shadow/uden flag
        if pref and pref.get("model") and "/" in str(pref["model"]):
            p, m = str(pref["model"]).split("/", 1)
            if p and m:
                return p, m
    except Exception:
        pass
    return base_provider, base_model


# ── AUTONOM/BAGGRUNDS-model — Bjørn-regel (2026-07-16) ────────────────────────────────
# Den BETALTE deepseek.com-API må KUN bruges i visible lane. Autonome/baggrunds-runs
# (wakeup, inderliv, autonome check-ins) kører på ollama (deepseek-v4-flash:cloud) —
# ALDRIG den betalte deepseek-provider. Dette lukker to lækager på én gang:
#   1) autonome runs defaultede før til settings.visible_model (= deepseek, betalt).
#   2) eksplorations-armen kunne sample en 'deepseek'/':cloud'-kandidat → deepseek.com
#      afviste ':cloud'-tag'et med HTTP 400 ("supported names are deepseek-v4-pro/flash").
_PAID_DEEPSEEK_PROVIDER = "deepseek"
_AUTONOMOUS_FALLBACK_PROVIDER = "ollama"
_AUTONOMOUS_FALLBACK_MODEL = "deepseek-v4-flash:cloud"
# Code-tuned models degenerate on the autonomous lane's reflective/journaling work:
# they spiral into read-tool loops and never synthesise text (4/4 looped autonomous
# runs in the week to 2026-07-18 were kimi-k2.7-code:cloud → gate_loop RED → dead run).
# Substring match against the resolved model, lowercased. Same spirit as the paid-
# deepseek HARD GUARD below: never let one of these be the autonomous preference.
_AUTONOMOUS_MODEL_BLOCKLIST = ("kimi-k2.7-code", "-code:")


def resolve_autonomous_model(*, autonomous_provider: str = "",
                             autonomous_model: str = "") -> tuple[str, str]:
    """(provider, model) for et AUTONOMT/baggrunds-run.

    Baggrunds-basen defaulter til ollama/deepseek-v4-flash:cloud (config-overstyrbar via
    runtime.settings.autonomous_model_*). Honorerer stadig eksplorations-armen + lært
    præference OVENPÅ basen — men HARD-GUARD: ethvert resultat der lander på den betalte
    'deepseek'-provider klemmes tilbage til baggrunds-basen. Kaster ALDRIG — fail-safe."""
    base_provider = (str(autonomous_provider or "").strip() or _AUTONOMOUS_FALLBACK_PROVIDER)
    base_model = (str(autonomous_model or "").strip() or _AUTONOMOUS_FALLBACK_MODEL)
    try:
        p, m = resolve_visible_model(
            default_provider=base_provider, default_model=base_model, autonomous=True,
        )
        # HARD GUARD: den betalte deepseek.com-API må aldrig ramme baggrunden.
        if str(p or "").strip().lower() == _PAID_DEEPSEEK_PROVIDER:
            return base_provider, base_model
        # HARD GUARD: kode-modeller looper på autonome refleksive opgaver (se
        # _AUTONOMOUS_MODEL_BLOCKLIST) → klem tilbage til den pålidelige base.
        _ml = str(m or "").strip().lower()
        if any(bad in _ml for bad in _AUTONOMOUS_MODEL_BLOCKLIST):
            return base_provider, base_model
        return (str(p or "").strip() or base_provider), (str(m or "").strip() or base_model)
    except Exception:
        return base_provider, base_model


def register_router_adapt_producer() -> None:
    """Registrér routing-præference-læreren som cadence-producer (~hvert 45 min). SHADOW medmindre flag."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_router_adapt",
        cooldown_minutes=45,
        visible_grace_minutes=0,
        run_fn=run_router_adapt_tick,
        priority=8,
    ))


def build_router_adapt_surface() -> dict[str, object]:
    """Mission Control — read-only: foreslået (shadow) + live præference + status."""
    live = _kv_get(_PREF_KEY, {}) or {}
    pref_model = ""
    if isinstance(live, dict) and isinstance(live.get("visible"), dict):
        pref_model = str(live["visible"].get("model") or "")
    health = {}
    if pref_model:
        rate, n = _recent_success_rate(pref_model)
        health = {"model": pref_model, "recent_success_rate": rate, "samples": n,
                  "floor": _HEALTH_FLOOR, "healthy_now": _is_currently_healthy(pref_model)}
    return {"active": True, "live_enabled": is_live_enabled(),
            "proposed": _kv_get(_SHADOW_KEY, {}) or {},
            "live_preference": live,
            "preference_health": health,
            "never_tiers": list(_NEVER_TIERS)}
