"""Hvilke budget-valgte sektioner der hører i præfikset, og hvilke i halen.

Udskilt fra `prompt_contract.py` 30/9-2026 (Boy Scout: filen var 4.925 linjer),
fordi den samme flytning nu er lavet tre gange og begrundelsen hver gang stod
som prosa i en 4.900-linjers fil. Her er den **data**.

## Loven placeringen hviler på

DeepSeeks præfiks er strengt ordnet `[system][tools][beskeder]`, og cachen
matcher fra begyndelsen: **en ændring koster alt fra ændringspunktet og frem —
intet før.** Målt direkte mod deres API 30/9-2026: første tegn i systemblokken
ændret → 0 % hit; sidste tegn ændret → 60 %; én ny værktøjsdefinition bagerst
i tools → 8.704 tokens tabt. Positionen er hele prisen; størrelsen er næsten
ligegyldig.

Derfor: en sektion i systemblokken der ændrer sig, koster **hele
værktøjsarrayet og hele samtalen** hver gang den gør det. Målt i produktion:
to præfiks-varianter der adskilte sig med **to tegn** 98 % inde i
systemblokken efterlod kun 33 % af præfikset i behold.

## Afvejningen — og hvorfor listen ikke bare skal være tom

Halen caches aldrig. At flytte en sektion derned bytter *«nogle gange gratis,
nogle gange katastrofalt»* for *«altid en lille fast pris»*. Det er en gevinst
for en sektion der skifter ofte, og et **tab** for en der ikke gør: `USER.md`
ændrede sig én gang på to døgn, så en flytning ville koste ~4.600 tegn hver
eneste tur for at undgå ét brud. Den bliver derfor i præfikset med vilje.

Kriteriet for halen er altså ikke «kan variere», men **«varierer i praksis,
tur for tur»**.
"""
from __future__ import annotations

from collections.abc import Mapping, MutableSequence

#: Sektioner der bliver i det cachede præfiks.
#:
#: Fem af de syv sættes i praksis til ``None`` andre steder i
#: `prompt_contract.py` og rutes til halen ad anden vej — `continuity` (2514),
#: `inner_visible_bridge` (2550, altid), `cognitive_state` (2572, 2601),
#: `self_state` (2604) og `cognitive_frame` (2612). De står stadig her, fordi
#: listen beskriver **hvor de havner hvis de er sat**, ikke hvad der tilfældigvis
#: er sat i dag.
#:
#: Og det er selve risikoen: holder en af de `if`-grene op med at fyre, glider
#: sektionen tilbage i præfikset i stilhed. Det er præcis den fejlform der
#: kostede tre flytninger 30/9-2026. `test_praefiks_uden_levende_tal.py` er
#: vagten mod det.
PRAEFIKS_SEKTIONER: tuple[str, ...] = (
    "capability_truth",
    "output_discipline",
    "cognitive_frame",
    "cognitive_state",
    "self_state",
    "inner_visible_bridge",
    "continuity",
)

#: Sektioner der lægges EFTER cache-grænsen, med den målte grund til hver.
#: Rækkefølgen er den de flyttes i, ikke en prioritet.
HALE_SEKTIONER: dict[str, str] = {
    # Indholdet er et TIDS-SNAPSHOT: bygningen er cappet, og rammes deadline'en
    # beholdes kun de under-sektioner der NAAEDE at blive færdige. Hvilke der
    # nåede det afhænger af et kapløb, så sektionen er ikke-deterministisk ved
    # design. Målt: to varianter, 30.204 og 30.206 tegn — to tegns forskel,
    # 98 % inde i blokken, hit 89,5 % -> 79,2 %.
    "support_signals": "bounded runtime support signals",
    # Bygges MED brugerbeskeden som parameter og har betingede linjer, så den
    # er helt med eller helt ude alt efter turen. Målt 30/9 kl. 15:45: tre runs
    # i SAMME session gav to systemblokke — 29.782 og 30.257 tegn — og
    # journalens egen sektionsliste navngav forskellen i ét opslag:
    # `RUNTIME_SELF-REPORT_GROUNDING (Jarvis-specific) = +473 tegn`, til stede
    # i den ene assembly og fraværende i den anden. Afvigelsen lå i chunk 29,
    # og kun 32,5 % af præfikset overlevede.
    "self_report": "grounded runtime self-report support",
}


def placer_sektioner(
    *,
    selected: Mapping[str, str | None],
    labels: Mapping[str, str],
    parts: MutableSequence[str],
    dyn_tail: MutableSequence[str],
    derived_inputs: MutableSequence[str],
) -> None:
    """Læg hver budget-valgt sektion i præfikset eller i halen.

    ``selected`` er resultatet EFTER attention-budgettet — ikke det rå indhold.
    Det er væsentligt: budgettet klipper sektionerne til deres loft, og
    `support_signals` kostede 27,4 s af en 31-sekunders kold opbygning før den
    blev cappet. Gav man halen det uklippede indhold, forsvandt loftet i
    stilhed, uden at noget fejlede.
    """
    for navn in PRAEFIKS_SEKTIONER:
        indhold = selected.get(navn)
        if indhold:
            parts.append(indhold)
            derived_inputs.append(labels.get(navn, navn))
    for navn in HALE_SEKTIONER:
        indhold = selected.get(navn)
        if indhold:
            dyn_tail.append(indhold)
            derived_inputs.append(labels.get(navn, navn) + " (tail)")
