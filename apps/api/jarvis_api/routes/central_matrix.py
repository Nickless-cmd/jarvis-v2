"""Central 'matrix' routes — de fire tematiske selv-observations-komponenter (owner-view).

Bjørn+Claude (6. jul): The Construct (sandbox: hvad kunne jeg undvære?), The Oracle (forudseende
tidsserie-projektion), The Architect (ét tungt strukturelt snit-forslag), Echo Chamber Breaker
(tvungen modstemme mod monokultur). Alle read-only / propose-only, metadata-only, self-safe.
Owner-gated.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-matrix"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


def _stamp(surf: dict) -> dict:
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf


@router.get("/construct")
async def get_construct(nerve: str = "") -> dict:
    """Sandbox: hvilke nerver kunne slukkes uden tab. ?nerve=X → projicér én nerve. Owner-only."""
    _require_owner()
    try:
        from core.services.central_construct import build_construct_surface, simulate_silence
        surf = simulate_silence(nerve) if nerve else build_construct_surface()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/oracle")
async def get_oracle() -> dict:
    """Forudsigelser: hvilke tidsserie-linjer nærmer sig en tærskel + ETA. Owner-only."""
    _require_owner()
    try:
        from core.services.central_oracle import foresee
        surf = foresee()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/architect")
async def get_architect() -> dict:
    """Ét tungt strukturelt snit-forslag fra hele-system-synet. Owner-only."""
    _require_owner()
    try:
        from core.services.central_architect import assess
        surf = assess()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/echo-breaker")
async def get_echo_breaker() -> dict:
    """Modstemme: konkrete simplere alternativer til altid-grønne central-processer. Owner-only."""
    _require_owner()
    try:
        from core.services.central_echo_breaker import break_echo
        surf = break_echo()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/glitch")
async def get_glitch() -> dict:
    """Glitches i selvbilledet: altid-shadow policies + frosne nerver + anbefalet handling. Owner-only."""
    _require_owner()
    try:
        from core.services.central_glitch import detect_glitches
        surf = detect_glitches()
    except Exception:
        surf = {}
    return _stamp(surf)
