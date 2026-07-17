"""Pool-status prompt-sektion — så Jarvis ALTID kender forskellen på de to
model-pools og deres live-status.

Bjørn: "han fatter ikk forskel på agent pool og cheap lane." Denne blok gør
distinktionen eksplicit + viser live-health. VOLATIL (route rotérer, health
skifter) → SKAL ligge i prompt-HALEN (_dyn_tail, efter DYNAMIC_TAIL_SENTINEL),
ALDRIG i det cachede hoved (ellers bustes hele historik-cachen hver tur).
"""
from __future__ import annotations


def pool_status_line() -> str:
    """Kompakt to-linjers status af de to pools. Self-safe: enhver datakilde-fejl
    degraderer til '?' — sektionen kaster aldrig og blokerer aldrig en prompt."""
    # Agent pool: nuværende GRATIS route-mål (rotérer via central-route ranking).
    agent_now = "?"
    agent_note = ""
    try:
        from core.services.agent_pool_router import route_agent_task
        r = route_agent_task(kind="explorer", allow_paid=False)
        agent_now = f"{r.get('provider', '?')}/{r.get('model', '?')}"
        if r.get("is_floor"):
            agent_note = " ⚠ på floor (rangerede modeller nede)"
    except Exception:
        pass

    # Provider-health-summary (fx "8/8 providers sunde").
    health = "?"
    try:
        from core.services.provider_health_check import build_provider_health_surface
        health = str(build_provider_health_surface().get("summary") or "").strip() or "?"
    except Exception:
        pass

    # Cheap lane: antal konfigurerede providers.
    cheap_n = "?"
    try:
        from core.services.cheap_provider_runtime_selection import cheap_lane_status_surface
        cheap_n = str(int(cheap_lane_status_surface().get("provider_count") or 0))
    except Exception:
        pass

    return (
        "[MODEL-POOLS — kend forskellen]\n"
        "  • Agent pool: dét ALT agent-drevet arbejde (subagenter + autonome runs) "
        "trækker fra — GRATIS arbejdskraft + BETALTE premium-modeller til rigtige "
        f"kode-opgaver. Nu (gratis): {agent_now}{agent_note}. Providers: {health}.\n"
        "  • Cheap lane: den brede GRATIS-only pool (INGEN betalte modeller — de er "
        f"eksklusive for agent-poolen). {cheap_n} providers.\n"
        "  (Din egen chat-model er adskilt fra begge pools.)"
    )
