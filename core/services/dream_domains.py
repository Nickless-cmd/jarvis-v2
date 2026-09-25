"""Det faelles emne-ordforraad for droemme-kaeden.

Kaeden hypotese -> adoptions-kandidat -> indflydelses-forslag -> selvskrevet
prompt-forslag foejer paa EMNE: hvert hop slaar op paa sidste segment af
`canonical_key` og leder efter et maal eller et fokus i samme emne.

Det virkede. Maalt 25/9-2026 i produktionen: `danish-concise-calibration`
fandtes 15.–25. maj som hypotese, som fokus OG som 123 maal-raekker — og det er
praecis derfor den sidste adoptions-kandidat er fra 15. maj.

Saa holdt tre ting op med at vaere enige inden for en maaned:

  * 25/5  `runtime_goal_signals` holdt op med at blive skrevet. Nyeste maal er
          derfra.
  * ~maj  fokusserne gik over til `focus:bearing:<fri tekst>`.
  * 9/6   `cadence_producers` begyndte at skrive `dream:topic:<slug af Bjoerns
          besked>`. 42 hypoteser siden, og ingen af dem kan moede noget.

Det sidste er ikke en anden FORM, det er en anden BETYDNING. For den producent
betyder «emne» hvad Bjoern lige sagde; for droemme-kaeden betyder det hvilket
staaende omraade af Jarvis' udvikling det angaar. Samme ord, to begreber.
Kodebasen ved det allerede: `quarantine_legacy_world_topics` rydder netop
samtale-emner ud af verdensmodellen, tolv linjer over det kald der laver dem.

Ordforraadet her er ikke nyt. Det stod i `dream_hypothesis_forced._DOMAINS` og
er i brug — fire raekker fra 24/9 baerer `capability`, `creativity`, `memory`
og `identity`. Det har bare kun haft én bruger.
"""
from __future__ import annotations

#: De otte kognitive domaener. Raekkefoelgen er ligegyldig; navnene er ikke.
#: Aendres et navn, holder det op med at moede de maal og fokusser der allerede
#: baerer det.
DOMAENER: dict[str, str] = {
    "identity": "Jarvis udviklede sin selvforståelse i dette interval",
    "curiosity": "En uudtalt nysgerrighed er ved at krystallisere sig",
    "memory": "Et mønster i erfaringshukommelsen fortjener opmærksomhed",
    "capability": "En ny kompetence er ved at tage form",
    "relational": "Relationsdynamikken med brugeren har skiftet",
    "boundary": "Jarvis' grænser testes og defineres på ny",
    "creativity": "Et kreativt potentiale er uudnyttet",
    "resilience": "Gentagne udfordringer har afsat et spor",
}

# ── Hvorfor der IKKE staar en klassifikation her ─────────────────────────
#
# Jeg skrev en 25/9-2026: en lille noegleords-tabel der skulle udlede domaenet
# af turens tekst. Maalt mod de 42 raekker der faktisk naaede producenten:
#
#   * loest match: 10 traf, hoejst ét var rigtigt. `creativity` kom fra
#     «digt» inde i «faerdig». Fire `identity` kom fra «dig selv» i
#     «[SELF-WAKEUP FIRED] Du bad dig selv:». `memory` kom fra filnavnet
#     MEMORY.md.
#   * med ordgraenser og de svage spor fjernet: 0 traf.
#
# Der findes ingen noegleords-tabel der virker, og det er ikke tabellens skyld.
# Teksten der naar producenten handler ikke om staaende domaener — den handler
# om byg-ordrer, runtime-inspektioner, selv-vaekninger og natrutiner. Et
# forkert domaene er vaerre end ingen: saa haenger droemmen paa det forkerte
# staaende omraade, og det er en fejl ingen kan se.
#
# Ordforraadet nedenfor er stadig rigtigt og deles nu af producenterne. HVEM
# der vaelger et domaene ud fra en tur er et aabent spoergsmaal.


def er_gyldigt_domaene(navn: str) -> bool:
    return str(navn or "") in DOMAENER
