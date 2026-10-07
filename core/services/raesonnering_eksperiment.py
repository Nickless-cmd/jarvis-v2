"""A/B: raesonnerer han paa mellem-runderne, eller ikke?

## Hvorfor

Maalt 5/10-2026 over 7 dage: output er den stoerste post paa regningen (15,7
mio. tokens, $9,42 af $31,68), og **32,9 % af det er raesonnering**. Latensen
er naesten linjaer i output — 2,69 s ved 0-400 output-tokens, 14,10 s ved
1600+ — saa raesonneringen er ogsaa en tredjedel af ventetiden.
`thinking` slaas i dag KUN fra paa den afsluttende prosa-runde; hver
mellemliggende agentisk runde koerer med fuld raesonnering.

Men det er umaalt om det koster kvalitet, og det er paa mellem-runderne han
vaelger hvilket vaerktoej han skal bruge. `visible_followup_adapters` noterer
selv tvivlen: «Om det er dét der koster de 22 %, ved vi ikke — derfor noteres
det.» Derfor et A/B og ikke et flip.

## Knappen er BINAER

Probet direkte mod API'en 5/10, tre gentagelser pr. indstilling paa samme
spoergsmaal:

```
reasoning_effort=high    raeson [296, 290, 358]   ud median 792
reasoning_effort=medium  raeson [309, 299, 317]   ud median 777
reasoning_effort=low     raeson [381, 317, 296]   ud median 818
thinking: disabled       raeson [  0,   0,   0]   ud median 577
```

`reasoning_effort` ignoreres i TAVSHED af deepseek-v4-flash: spredningen
inden for `high` alene (290-358) daekker hele spaendet mellem
indstillingerne. Havde vi bygget armen paa «medium», ville A/B'en have vist
«ingen forskel» — ikke fordi raesonnering er gratis, men fordi knappen aldrig
blev drejet. Den eneste indstilling der virker er `thinking: disabled`, og
det er derfor armen er binaer.

## Armen er stabil paa tvaers af PROCESSER

`hash()` paa en streng er saltet pr. proces (PYTHONHASHSEED), og prompten
bygges i BAADE `jarvis-api` og `jarvis-runtime` — samme run ville kunne
havne i hver sin arm i de to processer og blande forsoeget. Derfor sha256.
Se memory `both_units_run_the_same_app`.

Armen er en REN funktion af run_id, saa analysen kan regne den ud bagefter.
Ingen ny kolonne, intet at glemme at skrive.
"""
from __future__ import annotations

import hashlib

ARM_FULD = "fuld"
ARM_DAEMPET = "daempet"

#: Fald tilbage hvis indstillingen ikke kan laeses: INGEN eksponering.
#: En maaling der tager en andel fordi en config-laesning fejlede, er en
#: aendring ingen har besluttet.
_PROCENT_FALLBACK = 0


def _procent() -> int:
    from core.runtime.settings import load_settings
    try:
        raa = getattr(load_settings(), "raesonnering_daempet_procent", _PROCENT_FALLBACK)
    except Exception:  # config utilgaengelig: fald mod nul eksponering, aldrig mod en andel
        return _PROCENT_FALLBACK
    try:
        return max(0, min(100, int(raa)))
    except (TypeError, ValueError):  # en vaerdi der ikke er et tal er ikke en andel: nul eksponering
        return _PROCENT_FALLBACK


def arm_for_run(run_id: str, *, procent: int | None = None) -> str:
    """"daempet" eller "fuld" — stabilt for et givet run_id, i enhver proces.

    Et tomt run_id giver ALTID "fuld": uden en stabil noegle kan runnet skifte
    arm mellem runder, og en tur med halvdelen af runderne i hver arm maaler
    ingenting.
    """
    pct = _procent() if procent is None else max(0, min(100, int(procent)))
    if pct <= 0 or not (run_id or "").strip():
        return ARM_FULD
    if pct >= 100:
        return ARM_DAEMPET
    fordeling = hashlib.sha256(run_id.strip().encode("utf-8")).digest()
    return ARM_DAEMPET if (fordeling[0] | (fordeling[1] << 8)) % 100 < pct else ARM_FULD


#: Kun standard-tilstanden daempes. Vaelger Bjoern «deep» i composeren, er det
#: et valg han har truffet, og forsoeget maa ikke overskrive det; vaelger han
#: «fast», er raesonneringen allerede slaaet fra og der er intet at daempe.
_DAEMPBAR_TILSTAND = "think"


def daemp_krop(
    krop: dict | None,
    run_id: str,
    *,
    thinking_mode: str = _DAEMPBAR_TILSTAND,
    procent: int | None = None,
) -> tuple[dict | None, bool]:
    """Returnerer (krop, blev_daempet) for en FOELGE-runde.

    Roerer kun kroppen i den daempede arm, og lader den vaere helt i fred
    ellers — saa arm "fuld" er bit-for-bit dagens adfaerd, ikke en ny vej der
    tilfaeldigvis ligner den.
    """
    if (thinking_mode or _DAEMPBAR_TILSTAND).strip().lower() != _DAEMPBAR_TILSTAND:
        return krop, False
    if arm_for_run(run_id, procent=procent) != ARM_DAEMPET:
        return krop, False
    ny = dict(krop or {})
    ny.pop("reasoning_effort", None)  # ignoreres alligevel, men efterlad ikke et modsat signal
    ny["thinking"] = {"type": "disabled"}
    return ny, True
