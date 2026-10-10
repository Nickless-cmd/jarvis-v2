"""Kroniske fejlere: slots hvis FAKTISKE success-rate ligger under gulvet.

Straffen i `weighted_slot_health.adaptive_snapshot` er gradueret — maks ~24 point
(10 pålidelighed + 8 kvalitet + 6 latency). Det skubber en dårlig provider ned,
men udelukker den ikke: har den en god base-priority, vinder den lodtrækningen så
snart de bedre kandidater står i cooldown.

Målt 10/10-2026: `freeai::qwen7b` fejlede 98 af 101 kald i døgnet og blev alligevel
valgt ~100 gange, jævnt fordelt hvert 5.-10. minut. To grunde:

1. **Straffen mangler en tærskel.** Den er blød, ikke hård.
2. **Den bygger på det forkerte tal.** `metadata.success_count/failure_count` i
   `cheap_provider_runtime_state` sagde 18 kald for freeai (1 succes, 17 fejl),
   mens `cheap_provider_invocations` havde 103 i samme vindue. Metadata læses,
   opdateres og skrives tilbage — samtidige skrivninger overskriver hinanden.
   Historikken er den ene sandhed.

Dommeren her læser derfor `cheap_provider_invocations` over et vindue og udelukker
slottet hårdt under en tærskel. Karantænen er TIDSBEGRÆNSET, så en provider der
retter sig kommer tilbage af sig selv — samme princip som `cheap_lane_failure_policy`.

Flag-gated (`cheap_lane_success_rate_exclusion_enabled`, default OFF) → byte-identisk
adfærd indtil den tændes. Self-safe: en fejl her må aldrig vælte routing-stien.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

_FLAG = "cheap_lane_success_rate_exclusion_enabled"
_DEFAULT_DAYS = 3
_DEFAULT_MIN_CALLS = 20
_DEFAULT_FLOOR = 0.10
_DEFAULT_QUARANTINE_HOURS = 24

# Statusser der tæller som succes i historikken. `smoke-ok` er en rigtig kørsel
# (smoke_cheap_lane), ikke en probe — den skal tælle med.
_OK_STATUSES = ("completed", "smoke-ok")


def _enabled() -> bool:
    try:
        from core.runtime.db_core import get_runtime_state_bool
        return get_runtime_state_bool(_FLAG, False)
    except Exception as exc:  # flag-laesning maa ikke vaelte dommeren; OFF er sikker
        logger.debug("success-rate-dommer: kunne ikke laese flaget: %s", exc)
        return False


def find_chronic_failures(
    *,
    days: int = _DEFAULT_DAYS,
    min_calls: int = _DEFAULT_MIN_CALLS,
    floor: float = _DEFAULT_FLOOR,
) -> list[dict]:
    """Slots hvis success-rate over vinduet er UNDER `floor`, med mindst `min_calls`.

    Returnerer [{provider, model, auth_profile, success, total, rate}]. Tom liste
    ved fejl — en dommer der ikke kan læse, dømmer ingen.
    """
    from core.runtime.db_core import connect

    since = (datetime.now(UTC) - timedelta(days=int(days))).isoformat()
    pladsholdere = ",".join("?" for _ in _OK_STATUSES)
    try:
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT provider, model,
                       COALESCE(NULLIF(auth_profile, ''), 'default') AS profile,
                       SUM(CASE WHEN status IN ({pladsholdere}) THEN 1 ELSE 0 END) AS success,
                       COUNT(*) AS total
                FROM cheap_provider_invocations
                WHERE lane = 'cheap' AND created_at >= ?
                GROUP BY provider, model, profile
                HAVING COUNT(*) >= ?
                """,
                (*_OK_STATUSES, since, int(min_calls)),
            ).fetchall()
    except Exception as exc:
        logger.warning("success-rate-dommer: kunne ikke laese historikken: %s", exc)
        return []

    ud: list[dict] = []
    for r in rows:
        total = int(r["total"] or 0)
        if total <= 0:
            continue
        success = int(r["success"] or 0)
        rate = success / total
        # Streng ulighed: praecis paa gulvet er ikke UNDER gulvet.
        if rate < float(floor):
            ud.append({
                "provider": str(r["provider"] or ""),
                "model": str(r["model"] or ""),
                "auth_profile": str(r["profile"] or "default"),
                "success": success,
                "total": total,
                "rate": round(rate, 4),
            })
    return ud


def apply_quarantine(rows: list[dict], *, hours: int = _DEFAULT_QUARANTINE_HOURS) -> int:
    """Sæt en tidsbegrænset cooldown i `cheap_provider_runtime_state` for hver dømt slot.

    Det er præcis den kilde selection-stien læser gennem `quota_snapshot` — så dommen
    virker på BEGGE stier uden at nogen skal kalde os. Self-safe pr. slot: én dårlig
    række må ikke stoppe de øvrige.
    """
    if not rows:
        return 0
    from core.runtime.db import get_cheap_provider_runtime_state, upsert_cheap_provider_runtime_state

    until = (datetime.now(UTC) + timedelta(hours=int(hours))).isoformat()
    sat = 0
    for r in rows:
        provider = str(r.get("provider") or "")
        model = str(r.get("model") or "")
        if not provider:
            continue
        try:
            current = get_cheap_provider_runtime_state(provider=provider, model=model) or {}
            try:
                metadata = json.loads(str(current.get("metadata_json") or "{}"))
            except (TypeError, ValueError):
                metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            metadata["success_rate_quarantine"] = {
                "at": datetime.now(UTC).isoformat(),
                "success": int(r.get("success") or 0),
                "total": int(r.get("total") or 0),
                "rate": float(r.get("rate") or 0.0),
                "hours": int(hours),
            }
            upsert_cheap_provider_runtime_state(
                provider=provider,
                model=model,
                status="quarantined",
                auth_ready=bool(current.get("auth_ready", True)),
                quota_limited=False,
                cooldown_until=until,
                last_error_code="low-success-rate",
                last_error_message=(
                    f"success-rate {r.get('rate')} over {r.get('total')} kald "
                    f"— under gulvet, karantaene {hours} t"
                ),
                metadata_json=json.dumps(metadata),
            )
            sat += 1
        except Exception as exc:
            logger.warning("success-rate-dommer: kunne ikke karantaene %s/%s: %s",
                           provider, model, exc)
    return sat


def enforce(*, days: int = _DEFAULT_DAYS, min_calls: int = _DEFAULT_MIN_CALLS,
            floor: float = _DEFAULT_FLOOR, hours: int = _DEFAULT_QUARANTINE_HOURS) -> dict:
    """Flag-gated indgang: find kroniske fejlere og sæt dem i karantæne.

    Returnerer altid et dict — aldrig en rejsning. Kaldes fra balancerens
    run-end-punkt, hvor `reconcile_successes` allerede HELER; denne DOEMER.
    """
    if not _enabled():
        return {"enabled": False, "quarantined": 0, "rows": []}
    try:
        rows = find_chronic_failures(days=days, min_calls=min_calls, floor=floor)
        sat = apply_quarantine(rows, hours=hours)
        if sat:
            logger.warning(
                "success-rate-dommer: %d slot(s) i karantaene %st — %s",
                sat, hours,
                ", ".join(f"{r['provider']}/{r['model']} ({r['rate']:.0%} af {r['total']})"
                          for r in rows),
            )
        return {"enabled": True, "quarantined": sat, "rows": rows}
    except Exception as exc:
        logger.warning("success-rate-dommer fejlede (roerer ikke routing): %s", exc)
        return {"enabled": True, "quarantined": 0, "rows": []}
