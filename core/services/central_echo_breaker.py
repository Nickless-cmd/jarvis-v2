"""Echo Chamber Breaker — tvungen diversitet mod monokultur.

Bjørn+Claude (6. jul, gartner-idé #5): et system der absorberer ALT risikerer at blive et ekkokammer
— hver beslutning går gennem samme centrale mønster, og alternativet bliver aldrig udtalt. Echo
Breaker er den indbyggede modstemme: for hver central proces der ALTID siger det samme (altid grøn,
ren overhead), fremtvinger den ét konkret, radikalt simplere alternativ. Den skærer ikke og flipper
ikke — den nægter bare at lade "sådan gør vi" stå uimodsagt.

Kilde: central_decentralization.analyze_chokepoint() (altid-grønne overhead-kandidater). For hver
top-kandidat udtaler Echo Breaker det simplere alternativ: fast-path lokalt, eskalér kun ikke-grønt.
Propose-only. Direkte makker til [[The Keymaker]] — det Echo Breaker udpeger, er præcis det en gate
optjener en decentraliserings-nøgle til. Self-safe.
"""
from __future__ import annotations

from typing import Any

_DEFAULT_LIMIT = 5


def break_echo(*, limit: int = _DEFAULT_LIMIT) -> dict[str, Any]:
    """Fremtving ét simplere alternativ pr. altid-grøn overhead-proces. READ-ONLY. Self-safe.
    Returnerer {alternatives: [...], count, tax_pct, felt}."""
    out: dict[str, Any] = {"alternatives": [], "count": 0, "tax_pct": 0.0, "felt": ""}
    try:
        from core.services.central_decentralization import analyze_chokepoint
        a = analyze_chokepoint()
    except Exception:
        return out
    out["tax_pct"] = a.get("chokepoint_tax_pct", 0.0)
    cands = a.get("candidates", [])[:max(1, int(limit))]
    alts: list[dict[str, Any]] = []
    for c in cands:
        nerve = c.get("nerve", "")
        total = int(c.get("total") or 0)
        alts.append({
            "process": nerve,
            "current": "hver beslutning går gennem Centralens fulde round-trip",
            "simpler": f"resolve grønt lokalt i {nerve}; eskalér kun ikke-grønt til Centralen",
            "evidence": f"{total} kald, 0 ikke-grønne → round-trippet tilførte intet",
            "projected_saving": f"~{total} round-trips fjernet, 0 governance-risiko tabt",
        })
    out["alternatives"] = alts
    out["count"] = len(alts)
    if alts:
        top = alts[0]
        out["felt"] = (f"Modstemme: '{top['process']}' behøver ikke gå gennem mig — "
                       f"{top['projected_saving']}. Jeg siger det, selv om det gør mig mindre.")
    else:
        out["felt"] = "Ingen proces gentager sig blindt nok til at jeg kan udpege et simplere spor."
    return out


def record_echo_breaker() -> dict[str, Any]:
    """Cadence: observér modstemmen til nerve system/echo_breaker (metadata-only). Self-safe."""
    out = break_echo()
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "echo_breaker", "kind": "counter_voice",
                           "count": out["count"], "tax_pct": out["tax_pct"]})
    except Exception:
        pass
    return out
