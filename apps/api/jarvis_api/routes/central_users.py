"""Central 'users' route — hvornår var hver bruger sidst aktiv, og hvordan (owner-view).

Bjørn (6. jul): "Kan centralen se hvornår Mikkel sidst har været aktiv?" Fletter alle kilder
(chat/api/run/device) → sidst aktiv · via · aktiv nu · beskeder · token-estimat. Metadata-only
(ingen samtaleindhold). Owner-gated, read-only, self-safe.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-users"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


# Centralen poller denne 100 gange i kvarteret, og fletningen over alle kilder
# koster 111ms. Efter costs-daily blev cachet stod den for 67% af den resterende
# poll-belastning. Hvem der sidst var aktiv ændrer sig ikke på et sekund.
_USERS_TTL_S = 10.0


@router.get("/users")
def get_user_activity() -> dict:
    """Bruger-aktivitet: sidst aktiv pr. bruger flettet fra alle kilder. Owner-only."""
    _require_owner()
    from core.services.central_projection_cache import cached

    def _build() -> dict:
        try:
            from core.services.user_activity import build_user_activity_surface
            surf = build_user_activity_surface()
            if not isinstance(surf, dict):
                surf = {}
        except Exception:
            surf = {}
        # ts bygges INDE i cachen, så det er tidspunktet data blev flettet — ikke
        # tidspunktet svaret blev sendt. Ellers ville et 9s gammelt snapshot bære
        # et friskt tidsstempel og se nyere ud end det er.
        surf["ts"] = datetime.now(timezone.utc).isoformat()
        return surf

    surf, age_s = cached("central:users", _USERS_TTL_S, _build)
    return {**surf, "cache_age_ms": int(age_s * 1000)}
