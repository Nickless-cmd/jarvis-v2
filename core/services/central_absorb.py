"""central_absorb — den fælles "fuld behandling"-absorption.

Hver MC-kategori-wiring kalder ``absorb`` så en producent-services værdi bliver
en LEVENDE central-nerve — ikke en død ``observe``. "Fuld behandling" =

  1. **Trace** — altid ``central().observe(...)`` med kind="observe". Det giver
     fuld sporing via central_timeseries/trace-sink (owner-lokal payload).
  2. **Flag/notifikation** — hvis ``flag_if(value)`` er sand: publicér
     ``event_bus.publish(f"{cluster}.flag", …)`` + en ekstra observe med
     kind="flag", så nerven kan farve Centralen og notificere.
  3. **Læring** — hvis ``learn_key`` er sat: fodr værdien ind i Centralens
     adaptive læring. ``central_learning`` er rent læse/analyse-lag (ingen
     sikker (key,value)-indtags-entrypoint), og ``central_adaptation``
     beregner bias fra track-record via ticks — heller ingen direkte
     værdi-feed. Derfor er hooken den plan-angivne fallback: publicér
     ``central.learn`` med ``{key, value}`` som eventbus-krog, som lærings-
     pipelines kan abonnere på.

SELF-SAFE ende-til-ende: hvert delskridt i sit eget try/except. ``absorb``
KASTER ALDRIG — en wiring-kald må ikke vælte den producerende route.
"""
from __future__ import annotations

from typing import Any, Callable, Optional


def _compact(value: Any, *, limit: int = 400) -> Any:
    """Kompakt, egress-venlig repræsentation af en værdi til flag-payloads.

    Beholder små dicts/lister/skalarer som de er; store/userialiserbare
    værdier reduceres til en kort strengrepræsentation. Self-safe.
    """
    try:
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value if len(value) <= limit else (value[:limit] + "…")
        if isinstance(value, dict):
            if len(value) <= 20:
                return value
            return {"_summary": f"dict({len(value)} keys)", "keys": list(value)[:20]}
        if isinstance(value, (list, tuple)):
            if len(value) <= 20:
                return list(value)
            return {"_summary": f"list({len(value)} items)"}
        s = str(value)
        return s if len(s) <= limit else (s[:limit] + "…")
    except Exception:
        try:
            return {"_summary": type(value).__name__}
        except Exception:
            return None


def absorb(
    cluster: str,
    nerve: str,
    value: Any,
    *,
    flag_if: Optional[Callable[[Any], Any]] = None,
    flag_reason: str = "",
    learn_key: Optional[str] = None,
) -> None:
    """Absorbér en producent-værdi som en levende central-nerve. Kaster ALDRIG.

    Args:
        cluster: Central-cluster (fx "cost", "agent", "self").
        nerve: Nerve-navn inden i clusteret (fx "daily").
        value: Producentens værdi (eller et kompakt resumé heraf).
        flag_if: Valgfrit prædikat. Hvis ``flag_if(value)`` er sand, rejses et
            flag (``{cluster}.flag``-event + observe kind="flag").
        flag_reason: Menneskelæselig grund vist på flaget.
        learn_key: Valgfri lærings-nøgle. Hvis sat, fodres værdien ind i
            Centralens adaptive læring via ``central.learn``-eventet.
    """
    compact = _compact(value)

    # 1) Trace — altid observe (fuld payload til owner-lokal trace-sink). ──────
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": cluster,
            "nerve": nerve,
            "kind": "observe",
            "value": value,
        })
    except Exception:
        pass

    # 2) Flag/notifikation — betinget. ────────────────────────────────────────
    flagged = False
    if flag_if is not None:
        try:
            flagged = bool(flag_if(value))
        except Exception:
            flagged = False
    if flagged:
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                f"{cluster}.flag",
                {"nerve": nerve, "reason": flag_reason, "value": compact},
            )
        except Exception:
            pass
        try:
            from core.services.central_core import central
            central().observe({
                "cluster": cluster,
                "nerve": nerve,
                "kind": "flag",
                "reason": flag_reason,
                "value": compact,
            })
        except Exception:
            pass

    # 3) Læring — betinget hook. central_learning/central_adaptation har ingen
    #    sikker (key,value)-indtags-entrypoint, så vi bruger den plan-angivne
    #    eventbus-fallback: central.learn med {key, value}. ────────────────────
    if learn_key is not None:
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "central.learn",
                {"key": learn_key, "value": compact, "cluster": cluster, "nerve": nerve},
            )
        except Exception:
            pass

    return None
