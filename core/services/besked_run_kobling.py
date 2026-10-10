"""Hvilket run skrev denne besked? — så klienten ikke skal gætte ud fra prosa.

## Hullet (målt 6/10-2026)

Bjørn: «Jeg ser 2 runs i tråden med samme svar», og til Jarvis tidligere samme
dag: «Samme svar står to gange i træk, efter svaret er færdigt».

Dubletten står IKKE i databasen — jeg sammenlignede alle svarpar i vinduet, og
ligheden var 1-12 %. Der er én kopi gemt. Dubletten er en TEGNE-dublet:

1. Ved `message_stop` indsætter desk en bro-kopi af det streamede svar med
   `clientStatus = 'server_missing_keep_stream'` og id `a-<run_id>`, og beder så
   serveren om den gemte version (`ChatView`).
2. `mergeServer` dropper broen kun hvis
   ``serverCaughtUp || serverAsstTexts.has(assistantNorm(lm))``.
3. `serverCaughtUp` betyder «sidste server-række er en assistant». Men
   tool-rækker persisteres — målt 7.974 `tool_use` + 7.974 `tool_result` mod
   4.849 `text` i 400 beskeder — så i en flerrunde-tool-tur står transcriptet
   midlertidigt ``[…assistant(svar), tool, tool]`` og flaget er FALSK. Koden
   beskriver selv præcis det tilfælde som årsagen til at «bruger så 2-3 kopier
   af samme svar lande sammen».
4. Så alt hænger på tekst-matchet. Og `assistantNorm` er kun
   ``raw.replace(/\\s+/g, ' ').trim()`` over de sammenkædede `text`-blokke —
   mens serveren OMSKRIVER og OMORDNER blokkene ved persistering
   (`_indsaet_ved_deres_vaerktoej` flytter dem hen til deres værktøj,
   `_med_udgivne_filer` og `_with_thinking_block` tilføjer, og en backend-guard
   kan sanitere en tool-echo-leak). Ændrer rækkefølgen sig, giver `join('')` en
   anden streng, og matchet fejler.

De to sidste punkter kan ikke begge gælde: man kan ikke afdublere på en
byte-sammenligning af en tekst man selv har skrevet om.

## Hvorfor et kort i hukommelsen og ikke en kolonne

Der fandtes ingen præcis nøgle: `message_id` er et frisk uuid
(`message-db58ea…`), og `chat_messages` har ingen run-kolonne. Bjørn valgte
run-id'et med i snapshottet UDEN skema-ændring, så koblingen bor her.

Det kan den, fordi begge ender er i SAMME proces: synlige runs kører i
api-processen (se `visible_run_recovery_dispatcher`: «Dispatcheren kører i
API-processen — samme proces som brugerens egne ture»), og det er også
api-processen der bygger snapshottet.

Rækkefølgen holder: `session_version()` rykker når rækken indsættes, og
`cached_by_version` bygger derfor payloadet EFTER at `noter()` har kørt.

## Hvorfor det ligger på disk og ikke i hukommelsen (7/10-2026)

Første udgave var en in-process dict, med den begrundelse at begge ender er i
api-processen. Det holdt ikke: **autonome runs persisteres i `jarvis-runtime`**,
mens snapshottet bygges i `jarvis-api`. Målt via api'ets eget historik-kald på
`auto-dream-20261007`: assistent-beskeden bar intet `run_id`, fordi den proces
der skrev koblingen ikke er den der læser den. Og mobilen følger netop autonome
runs live, så den bro-kopi var den eneste der ALDRIG kunne afdubleres præcist.

`state_store` deler filen mellem processerne, og `med_laas` serialiserer
læs-ændr-gem — dens egen docstring er skrevet om nøjagtig dette: «jarvis-api og
jarvis-runtime kører samme kode i hver sin proces og deler disse filer».

En genstart koster nu heller ikke koblingen. Klientens tekst-fallback bliver
alligevel stående: en besked skrevet FØR denne fil fandtes har ingen kobling,
og "" skal fortsat betyde «uvist».

Kortet er BUNDET. Et ubundet kort er en lækage der ikke viser sig før den gør,
og her ville den også gøre filen større for hver besked der nogensinde er skrevet.
"""
from __future__ import annotations

import logging

from core.runtime import state_store

logger = logging.getLogger(__name__)

#: Navnet i `state_store`. Står i `docs/persistens/register.json`.
NOEGLE = "besked_run_kobling"

#: Hvor mange koblinger der huskes. Klienten spørger kun om beskeder den lige
#: har set streame, så vinduet skal dække en håndfuld ture — ikke en historik.
#: 512 er rigeligt og koster nogle få kilobytes.
MAKS = 512


def _laes() -> dict[str, str]:
    raa = state_store.load_json(NOEGLE, {})
    if not isinstance(raa, dict):
        return {}
    return {str(k): str(v) for k, v in raa.items() if isinstance(v, (str, int))}


def noter(message_id: str, run_id: str) -> None:
    """Husk at ``run_id`` skrev ``message_id``. Self-safe: kaster aldrig.

    Kaldes fra persist-stien, som ikke må vælte på at en afdublerings-hjælp
    fejler — svaret er vigtigere end dubletten.
    """
    mid = str(message_id or "").strip()
    rid = str(run_id or "").strip()
    if not mid or not rid:
        return
    try:
        # Laas om HELE laes-aendr-gem: hver gemning skriver filen HEL, saa uden
        # den forsvinder den anden proces' kobling sporloest.
        with state_store.med_laas(NOEGLE):
            kort = _laes()
            kort.pop(mid, None)      # indsaettelses-orden = aeldst foerst
            kort[mid] = rid
            while len(kort) > MAKS:
                kort.pop(next(iter(kort)))
            state_store.save_json(NOEGLE, kort)
    except Exception:
        # IKKE tavs: fejler den her, falder klienten tilbage paa tekst-matchet
        # uden at nogen kan se hvorfor afdubleringen pludselig blev upraecis.
        logger.warning("kunne ikke notere besked-run-kobling for %s", mid[:28],
                       exc_info=True)


def run_for(message_id: str) -> str:
    """Run'et der skrev beskeden, eller "" hvis vi ikke ved det.

    "" betyder «uvist», ALDRIG «et andet run». Klienten skal derfor falde
    tilbage på sit tekst-match ved "" — ikke konkludere at broen er fremmed.
    """
    mid = str(message_id or "").strip()
    if not mid:
        return ""
    try:
        return _laes().get(mid, "")
    except Exception:
        logger.warning("kunne ikke laese besked-run-koblinger", exc_info=True)
        return ""


def skrev_run(run_id: str) -> bool:
    """Har DETTE run persisteret mindst én besked?

    Den omvendte vej af `run_for`: koblingen binder besked→run, og her spørger
    vi run→besked. Bruges af recovery-dispatcheren til at afgøre om et run der
    blev stemplet `interrupted` allerede NÅEDE at svare — den falske-
    interrupted-klasse (målt 3/10 og 10/10-2026).

    Hvorfor netop denne kilde: et bredere filter (enhver assistant-besked i
    sessionen efter døden) ville også tælle hver proaktiv besked, morgenbrief
    og heartbeat-ping — og droppe genoptagelser Bjørn faktisk ventede på. Det
    var præcis grænsen der standsede denne søster 3/10. Koblingen er bundet til
    runnet, så svaret bliver «skrev DETTE run?», ikke «blev der talt i rummet?».

    Bounded som kortet selv: er koblingen skredet ud (512 poster, ældst først),
    svarer den False — og kalderen genoptager, som den gjorde før. Fail-open mod
    genoptagelse er med vilje: et run må hellere genoptages forgæves end dø tavst.
    """
    rid = str(run_id or "").strip()
    if not rid:
        return False
    try:
        return any(v == rid for v in _laes().values())
    except Exception:
        logger.warning("kunne ikke afgoere om %s skrev en besked", rid[:28],
                       exc_info=True)
        return False


def antal() -> int:
    """Hvor mange koblinger der huskes nu. Til test og diagnostik."""
    try:
        return len(_laes())
    except Exception:  # kun til test og diagnostik — et tal her maa aldrig
        return 0       # vaelte en kalder, og `run_for` logger allerede fejlen


def ryd() -> None:
    """Tøm kortet. Kun til test — ingen produktionsvej rydder det."""
    try:
        with state_store.med_laas(NOEGLE):
            state_store.save_json(NOEGLE, {})
    except Exception:
        logger.warning("kunne ikke rydde besked-run-koblinger", exc_info=True)
