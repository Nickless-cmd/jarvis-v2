"""`/central/profiles` — Fase 9's forklarings-flade.

Spec'en siger «Mission Control explains ...». MC findes ikke laengere; fladerne
er `central_cli` og desk. Kriteriet ligger derfor her, hvor de begge henter
deres `/central/*`-overflader.

Laesende og ejer-gated som de oevrige central-ruter: en profil beskriver hvilke
rettigheder koersler har, og det er ikke noget et husstandsmedlem skal kunne
kortlaegge.
"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-profiles"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/profiles")
def get_profiles() -> dict:
    _require_owner()
    from core.services.central_profiles import build_profiles_surface
    return build_profiles_surface()
