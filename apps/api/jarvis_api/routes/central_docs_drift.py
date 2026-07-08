"""Central 'docs-drift' route — docs-drift watchdog surface (owner-view, read-only, self-safe).

SP5: surfaces docs/drift_report.json (hard/soft counts, report freshness, top items) so the
Central and `jc docs-drift` show whether docs have drifted from git+runtime truth."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-docs-drift"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


@router.get("/docs-drift")
async def get_docs_drift() -> dict:
    """Docs-drift surface: hard/soft counts, report freshness, top drift items. Owner-only."""
    _require_owner()
    try:
        from core.services.docs_drift_watchdog import build_docs_drift_surface
        surf = build_docs_drift_surface()
        if not isinstance(surf, dict):
            surf = {"status": "unavailable"}
    except Exception:
        surf = {"status": "unavailable"}
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf
