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

import logging

logger = logging.getLogger(__name__)

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

# ── Hvorfor det er en MODEL der vaelger, ikke en ordliste ────────────────
#
# Jeg skrev en noegleords-tabel 25/9-2026 og maalte den mod de 42 raekker der
# faktisk havde naaet producenten:
#
#   * loest match: 10 traf, hoejst ét var rigtigt. `creativity` kom fra «digt»
#     inde i «faerdig». Fire `identity` kom fra «dig selv» i «[SELF-WAKEUP
#     FIRED] Du bad dig selv:». `memory` kom fra filnavnet MEMORY.md.
#   * med ordgraenser og de svage spor fjernet: 0 traf.
#
# Der findes ingen ordliste der virker. Doemmet — «handler den her tur om
# Jarvis' staaende udvikling inden for hukommelse?» — kraever at man forstaar
# saetningen, ikke at man finder et ord i den. Og et FORKERT domaene er vaerre
# end ingen: saa haenger droemmen paa det forkerte staaende omraade, og det er
# en fejl ingen kan se.
#
# Kaldet ligger i en baggrundstraad (`_update_cognitive_systems_async`,
# «fire-and-forget»), saa det koster ikke latenstid paa Bjoerns svar. Billig
# bane: det er en lille klassifikation, ikke en vurdering af hans samvittighed.


_PROMPT = """Du klassificerer en arbejdstur i Jarvis' runtime.

Spoergsmaalet er IKKE hvad turen handlede om fagligt, men om den roerte et
staaende omraade af Jarvis' egen udvikling. Det gjorde den som regel ikke —
«none» er det normale og rigtige svar.

De otte omraader:
{domaener}

Svar KUN med JSON:
{{"domaene": "<et af navnene ovenfor, eller none>"}}

Vaelg et navn kun hvis turen tydeligt handler om netop det omraade af Jarvis
selv. En byg-ordre, en fejlsoegning, en runtime-inspektion eller en
selv-vaekning er «none». Er du i tvivl, er svaret «none».

Turen:
{tekst}"""


def domaene_for_tur(tekst: str, *, timeout_sekunder: float | None = None) -> str | None:
    """Hvilket staaende domaene roerer turen — eller None.

    Kaster aldrig. Kan modellen ikke naas, eller svarer den noget der ikke er
    et af de otte navne, er svaret None: saa skrives der ingen hypotese, og
    det er bedre end en paa et gaettet omraade.
    """
    rens = str(tekst or "").strip()
    if len(rens) < 8:
        return None
    try:
        from core.services.daemon_llm import daemon_llm_call, tegn_for_tokens
        from core.services.llm_json import udtraek_json

        liste = "\n".join(f"- {n}: {b}" for n, b in DOMAENER.items())
        svar = daemon_llm_call(
            _PROMPT.format(domaener=liste, tekst=rens[:600]),
            max_len=tegn_for_tokens(60),
            fallback="",
            daemon_name="dream_domain",
        )
        ud = udtraek_json(svar) or {}
        navn = str(ud.get("domaene") or "").strip().lower()
        return navn if er_gyldigt_domaene(navn) else None
    except Exception:  # en droemme-hypotese maa aldrig kunne vaelte en tur
        logger.debug("domaene_for_tur fejlede", exc_info=True)
        return None


def er_gyldigt_domaene(navn: str) -> bool:
    return str(navn or "") in DOMAENER
