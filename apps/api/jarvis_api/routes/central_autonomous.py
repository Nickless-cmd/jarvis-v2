"""Central 'autonomous' route — Jarvis' autonome historie synlig for OWNER.

FØR funnelede alle autonome runs (drøm/råd/arbejde/outreach/recurring/heartbeat/…)
ind i én udødelig, usynlig "Autonomous"-session. NU roterer de pr. oprindelse+dag, og
denne route projicerer strømmen så Bjørn (og Central-CLI) ser den: pr. oprindelse med
antal sessioner, beskeder, seneste aktivitet og kontekst-fejl-antal.

§24.4-sikker: kun tællere + sessions-titler, ALDRIG råt beskedindhold. DB-backed →
virker direkte i api-processen (læser chat_sessions/chat_messages). Owner-gated,
read-only, self-safe.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-autonomous"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/autonomous")
async def get_autonomous_history() -> dict:
    """Jarvis' autonome historie grupperet pr. oprindelse (owner-only, read-only, self-safe)."""
    _require_owner()
    try:
        from core.services.autonomous_sessions import build_autonomous_history_surface
        surf = build_autonomous_history_surface()
        if not isinstance(surf, dict):
            surf = {}
    except Exception:
        surf = {}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
