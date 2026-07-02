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
    # kun konfigurerede, ikke-deep-tier vindere
    ranked = sorted(((m, n) for m, n in wins.items()
                     if m in configured and not _is_never_tier(m)),
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
            return p
    except Exception:
        pass
    return None


def resolve_visible_model(*, provider_override: str = "", model_override: str = "",
                          default_provider: str, default_model: str) -> tuple[str, str]:
    """KONSUMENTEN (Tråd 1 live-wire): afgør (provider, model) for et visible-run. Centraliserer den
    tidligere inline-dublerede selektion + anvender den LÆRTE routing-præference — men KUN når:
      * en eksplicit override IKKE er sat (rolle-clampet member-override vinder ALTID — sikkerhed), OG
      * flaget er ON + præferencen er grounded/konfigureret/ikke-deep-tier (get_live_preference-værn).
    Default/shadow → uændret adfærd (base). Kaster ALDRIG — fail-safe til base."""
    base_provider = (str(provider_override or "").strip() or default_provider)
    base_model = (str(model_override or "").strip() or default_model)
    try:
        # eksplicit override (fx member→ollama-clamp) er ukrænkelig — præference må ikke røre den
        if str(provider_override or "").strip() or str(model_override or "").strip():
            return base_provider, base_model
        pref = get_live_preference("visible")     # None i shadow/uden flag
        if pref and pref.get("model") and "/" in str(pref["model"]):
            p, m = str(pref["model"]).split("/", 1)
            if p and m:
                return p, m
    except Exception:
        pass
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
    return {"active": True, "live_enabled": is_live_enabled(),
            "proposed": _kv_get(_SHADOW_KEY, {}) or {},
            "live_preference": _kv_get(_PREF_KEY, {}) or {},
            "never_tiers": list(_NEVER_TIERS)}
