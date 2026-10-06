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

**Degraderingen er bevidst.** Efter en genstart er kortet tomt, og en bro-kopi
klienten stadig holder får intet run-id. Så falder den tilbage på tekst-matchet
— altså på dagens opførsel, ikke på noget værre. Derfor må klientens gamle
fallback IKKE fjernes.

Kortet er BUNDET. Et ubundet kort i en proces med `OLLAMA_KEEP_ALIVE=-1`-levetid
er en lækage der ikke viser sig før den gør.
"""
from __future__ import annotations

import threading
from collections import OrderedDict

#: Hvor mange koblinger der huskes. Klienten spørger kun om beskeder den lige
#: har set streame, så vinduet skal dække en håndfuld ture — ikke en historik.
#: 512 er rigeligt og koster nogle få kilobytes.
MAKS = 512

_laas = threading.Lock()
_kort: OrderedDict[str, str] = OrderedDict()


def noter(message_id: str, run_id: str) -> None:
    """Husk at ``run_id`` skrev ``message_id``. Self-safe: kaster aldrig.

    Kaldes fra persist-stien, som ikke må vælte på at en afdublerings-hjælp
    fejler — svaret er vigtigere end dubletten.
    """
    mid = str(message_id or "").strip()
    rid = str(run_id or "").strip()
    if not mid or not rid:
        return
    with _laas:
        if mid in _kort:
            _kort.move_to_end(mid)
        _kort[mid] = rid
        while len(_kort) > MAKS:
            _kort.popitem(last=False)


def run_for(message_id: str) -> str:
    """Run'et der skrev beskeden, eller "" hvis vi ikke ved det.

    "" betyder «uvist», ALDRIG «et andet run». Klienten skal derfor falde
    tilbage på sit tekst-match ved "" — ikke konkludere at broen er fremmed.
    """
    mid = str(message_id or "").strip()
    if not mid:
        return ""
    with _laas:
        return _kort.get(mid, "")


def antal() -> int:
    """Hvor mange koblinger der huskes nu. Til test og diagnostik."""
    with _laas:
        return len(_kort)


def ryd() -> None:
    """Tøm kortet. Kun til test — ingen produktionsvej rydder det."""
    with _laas:
        _kort.clear()
