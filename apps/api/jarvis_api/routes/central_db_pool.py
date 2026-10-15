"""Central 'db-pool' route — gør DB-forbindelses-poolen læsbar i drift.

Sporet fra 15/10-2026: de ~92 åbne forbindelser til jarvis.db kunne ikke henføres
til en tråd. ``/proc/PID/task/TID/fd`` er ÉN delt fd-tabel (alle tråde viser samme
fds), og ``lsof -K`` kan ikke læse tråd-niveau på denne host. Instrumenteringen i
``core.runtime.db_core`` tæller derfor ved FØDSEL og DØD og melder poster hvis
ejer-tråd er død som ``orphaned`` — den eneste klasse der kan vokse monotont over
dage og ende i fd-udmattelse.

Tællerne er PROCES-LOKALE, så ét tal er ikke nok. Denne route læser begge processer:

  * **api** (visible-lane, ``JARVIS_ENABLE_RUNTIME_SERVICES=0``) — direkte, da vi ER
    api-processen.
  * **runtime** (daemons, ``=1``) — via ``proxy_or_local`` over 8011, samme beviste
    kanal som self/mind-fladerne bruger.

Routen findes kun i api-processen (den registreres i ``app.py``); kaldes den alligevel
i runtime-processen, udelades modparten frem for at udgive ét tal for to.

Owner-gated + read-only + self-safe: en manglende modpart → ``{}`` for den nøgle,
aldrig en fejl.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/central", tags=["central-db-pool"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


def _own_pool() -> dict:
    """Denne proces' pool-attribution. Self-safe → {}."""
    try:
        from core.runtime.db_core import pool_connection_stats
        return pool_connection_stats()
    except Exception:  # self-safe: en måling må aldrig kunne vælte routen
        return {}


def _runtime_pool() -> dict:
    """Runtime-processens pool over 8011. Self-safe → {}."""
    try:
        from core.services.central_runtime_proxy import proxy_or_local
        return proxy_or_local("db_pool", _own_pool)
    except Exception:  # self-safe: en måling må aldrig kunne vælte routen
        return {}


@router.get("/db-pool")
def get_db_pool() -> dict:
    """DB-forbindelses-poolen i begge processer (owner-only, read-only, self-safe).

    ``orphaned`` er det afgørende tal: poster hvis ejer-tråd ikke længere findes.
    Er den tom i begge processer, ejer hver forbindelse en levende tråd — og så er
    de ~90 forbindelser poolens leje, ikke en læk.
    """
    _require_owner()
    from core.services.central_xproc import process_role
    egen_rolle = process_role()
    ud: dict = {
        egen_rolle: _own_pool(),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    # Modparten: api kan nå runtime over 8011. Kører routen i runtime-processen, er
    # `proxy_or_local` lokal og ville gentage vores eget tal — så den springes over.
    if egen_rolle == "api":
        ud["runtime"] = _runtime_pool()
    return ud
