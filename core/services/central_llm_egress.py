"""Samlet LLM-egress-observation — "har vi styr på ALLE udgående kald?" (Bjørn 4. jul).

Problemet (målt): 25+ filer laver udgående LLM-kald, men `record_cost` dækker kun 3.
Visible+cheap → record_cost. Daemon → daemon_llm_call (kun timeseries). Flere filer har
DIREKTE urlopen der går udenom alt → ukontrolleret egress, usynligt i regnskabet.

Dette modul er ÉT sted alle kald kan rapportere til, så Centralen har et komplet billede:
hvert kald → nerve `cost/llm_egress` + tidsserie `cost:llm_egress` med lane, provider,
model, formål (purpose), tokens, cost, og — for Bølge 3 — `cheap_eligible` (kunne dette
kald have taget en billigere/gratis model?). Rolle-bevidst: identitet/ræsonnement = nej;
faktuelt/opsummering/formattering/klassifikation/ekstraktion = ja.

SHADOW: dette OBSERVERER kun (måler leveren). Ingen omdirigering. En senere on-switch
kan bruge cheap_eligible til faktisk at rute. Egress-fri (kun skalarer). Self-safe.
"""
from __future__ import annotations

# Formål der trygt kan tage en billig/gratis model (ikke identitets-bærende).
_CHEAP_ELIGIBLE_PURPOSES = frozenset({
    "factual", "summary", "summarize", "format", "formatting", "classify",
    "classification", "extract", "extraction", "embed", "embedding", "score",
    "scoring", "dedup", "tag", "label", "relevance", "rewrite", "translate",
})
# Lanes der ALTID skal på den stærke/stabile model (Jarvis' synlige stemme + identitet).
_IDENTITY_LANES = frozenset({"visible", "primary"})


def classify_cheap_eligible(*, lane: str, purpose: str, autonomous: bool) -> bool:
    """Rolle-bevidst: kunne dette kald have taget en billigere model uden kvalitetstab?
    Konservativ — ved tvivl: False (behold den stærke model). Self-safe."""
    try:
        p = str(purpose or "").strip().lower()
        ln = str(lane or "").strip().lower()
        # Eksplicit billig-egnet formål → ja (uanset lane).
        if p in _CHEAP_ELIGIBLE_PURPOSES:
            return True
        # Autonome/interne kald (ingen bruger der venter på Jarvis' stemme) → egnet.
        if autonomous and ln not in _IDENTITY_LANES:
            return True
        # Identitets-lanes med bruger til stede → behold den stærke model.
        return False
    except Exception:
        return False


def observe(
    *,
    lane: str,
    provider: str,
    model: str,
    purpose: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    autonomous: bool = False,
    source: str = "",
) -> None:
    """Rapportér ét udgående LLM-kald til Centralens samlede egress-billede. Kald fra
    HVERT egress-punkt (chokepoints + direkte-urlopen-sites). Self-safe; kaster aldrig.

    source = hvilket modul/kaldested (så vi kan se dækning + finde blinde pletter)."""
    try:
        _eligible = classify_cheap_eligible(lane=lane, purpose=purpose, autonomous=autonomous)
        try:
            from core.services.central_timeseries import record as _ts
            _ts("cost", "llm_egress", value=(1.0 if _eligible else 0.0), meta={
                "lane": str(lane or "")[:24], "provider": str(provider or "")[:24],
                "model": str(model or "")[:40], "purpose": str(purpose or "")[:32],
                "source": str(source or "")[:40], "cheap_eligible": bool(_eligible),
                "tokens": int(input_tokens) + int(output_tokens),
            })
        except Exception:
            pass
        try:
            from core.services.central_core import central as _central
            _central().observe({
                "cluster": "cost", "nerve": "llm_egress",
                "lane": str(lane or ""), "provider": str(provider or ""),
                "model": str(model or ""), "purpose": str(purpose or ""),
                "source": str(source or ""), "autonomous": bool(autonomous),
                "cheap_eligible": bool(_eligible),
                "input_tokens": int(input_tokens), "output_tokens": int(output_tokens),
                "cost_usd": float(cost_usd),
            })
        except Exception:
            pass
    except Exception:
        pass


def build_llm_egress_surface() -> dict[str, object]:
    """Mission Control — read-only meta-projektion."""
    return {
        "module": "central_llm_egress",
        "purpose": "unified outgoing-LLM-call observability + Bölge-3 cheap-eligibility",
        "cheap_eligible_purposes": sorted(_CHEAP_ELIGIBLE_PURPOSES),
    }
