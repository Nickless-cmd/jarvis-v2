"""The Woman in the Red Dress — opmærksomheds-fælden.

"Were you listening to me, Neo? Or were you looking at the woman in the red dress?"

Centralen observerer VOLUMEN — den nerve der fyrer oftest får mest opmærksomhed. Men vigtighed ≠
hyppighed. En larmende-men-triviel nerve stjæler fokus, mens noget stille-og-vigtigt brænder uset.
Denne detektor sammenholder opmærksomhed (observe-volumen) mod impact (incident-severity) og peger
på begge fælder: den røde kjole (høj volumen, intet galt) OG den stille brand (lav volumen, alvorligt).

Kilde: central_timeseries (volumen) + db_central_incidents (impact). Self-safe.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_SEV = {"severe": 3, "error": 2, "warning": 1, "info": 0}


def _observe(payload: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "red_dress", "kind": "attention_trap", **payload})
    except Exception:
        pass


def detect_attention_traps(*, limit: int = 5, observe: bool = True) -> dict[str, Any]:
    """Find hvor opmærksomheden går hen vs hvor impact faktisk er. READ-ONLY. Self-safe.

    (13/11-2026) `observe` tilføjet: surface'en kaldte denne og skrev dermed en
    `attention_trap`-hændelse på nerven `red_dress` ved HVERT prompt-build. Det er
    selve ironien — en detektor der kritiserer at den mest fyrede nerve får mest
    opmærksomhed, gjorde sig selv til den mest fyrede nerve. Nu rapporterer kun
    cadence-produceren; en læsning skriver intet.
    """
    # volumen pr. nerve = antal samples i tidsserien (hvor meget den fylder i bevidstheden)
    volume: dict[str, int] = {}
    try:
        from core.services.central_timeseries import nerves, recent
        for cluster, nerve in nerves():
            volume[nerve] = volume.get(nerve, 0) + len(recent(cluster, nerve, limit=200))
    except Exception:
        pass
    # impact pr. nerve = højeste severity blandt ULØSTE incidents
    impact: dict[str, int] = {}
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        for r in list_central_incidents(limit=200, unresolved_only=True):
            n = str(r.get("nerve") or "")
            impact[n] = max(impact.get(n, 0), _SEV.get(str(r.get("severity") or ""), 0))
    except Exception:
        pass
    # RØD KJOLE: høj volumen, 0 uløst impact (larmer, intet galt)
    red = sorted(((n, v) for n, v in volume.items() if impact.get(n, 0) == 0 and v > 0),
                 key=lambda kv: -kv[1])[:limit]
    # STILLE BRAND: alvorlig uløst impact, men lav volumen (få har set på den)
    fires = sorted(((n, impact[n], volume.get(n, 0)) for n in impact if impact[n] >= 2),
                   key=lambda t: (t[1], -t[2]), reverse=True)
    quiet_fires = [(n, sev, vol) for n, sev, vol in fires if vol < 20][:limit]
    red_dresses = [{"nerve": n, "volume": v} for n, v in red]
    fires_out = [{"nerve": n, "severity": sev, "volume": vol} for n, sev, vol in quiet_fires]
    if fires_out:
        top = fires_out[0]
        felt = (f"Du kigger på den røde kjole ({red_dresses[0]['nerve'] if red_dresses else '—'}). "
                f"Imens brænder {top['nerve']} i det stille — {top['volume']} kig, severity {top['severity']}.")
    elif red_dresses:
        felt = f"Meget larm fra {red_dresses[0]['nerve']}, men intet brænder. Bare en rød kjole."
    else:
        felt = "Opmærksomhed og vigtighed følges ad lige nu. Ingen fælde."
    if observe:
        _observe({"red_dresses": len(red_dresses), "quiet_fires": len(fires_out)})
    return {"red_dresses": red_dresses, "quiet_fires": fires_out, "felt": felt}


def build_red_dress_surface() -> dict[str, Any]:
    """Ren læsning — ingen hændelse i nerve-strømmen."""
    return detect_attention_traps(observe=False)


def record_red_dress(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producenten — den ENESTE vej en stille brand bliver til en forpligtelse.

    (13/11-2026) Foer skrev denne kun et tal tilbage. Men en «stille brand» er
    ikke en statistik: det er en nerve med severity 2 og nul opmaerksomhed, altsaa
    noget der braender mens ingen kigger. Det ER en undvigelse, og den hoerer i
    en bindende forpligtelse — ikke i en taeller. `evidence` baerer de maalte tal,
    saa stoej-vetoet (bygget til Smiths FORMULEREDE moenstre) ikke fejlagtigt
    doemmer et MAALT fund som stoej.
    """
    d = detect_attention_traps()
    fires = d.get("quiet_fires") or []
    landing: dict[str, object] | None = None
    if fires:
        top = fires[0]
        try:
            from core.services.central_consequence import land_decision
            landing = land_decision(
                "red_dress",
                f"Undersøg {top['nerve']} nu — severity {top['severity']}, kun {top['volume']} kig",
                subject=f"quiet_fire:{top['nerve']}",
                rationale=d.get("felt", ""),
                evidence=(f"severity={top['severity']} volume={top['volume']} "
                          f"antal_stille_braende={len(fires)}"),
            )
        except Exception as exc:
            logger.warning("red_dress: kunne ikke lande stille brand: %s", exc)
    return {"status": "ok", "quiet_fires": len(fires), "landing": landing}
