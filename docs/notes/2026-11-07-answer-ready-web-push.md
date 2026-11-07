# Feed-stien nåede aldrig web-push (7/11-2026)

**Status:** rettet og verificeret lokalt · **Slags:** fejlretning · **Fravalg:** se nedenfor

## Fejlen, målt

Efter at `_push_to_web` fik telemetri (commit `fad825468`) kunne spørgsmålet
«fik hun den?» endelig besvares. Svaret var nej.

Siden deploy 6/11 kl. 19:46: **43 `run_done`-rækker i feeden, 4 `push.web_sent`.**
Alle fire til Bjørn, alle fra rutine- og initiative-stierne. **Nul** til Mikkel
(`238975101381378048`), **nul** til Michelle (`1313522677369143429`).

Og det afgørende spor: **nul `push.web_skipped` og nul `push.web_failed`.**
Havde brugerne manglet abonnementer, ville `skipped` stået der — `_push_to_web`
skriver den linje, før den returnerer. Nul betyder at funktionen **aldrig blev
kaldt**. Alle tre brugere havde et aktivt abonnement, målt samme dag:
Michelle på `web.push.apple.com`, Bjørn og Mikkel på `fcm.googleapis.com`.

## Tre rodårsager

**1. Transportlaget kendte ikke web-push.** `_deliver_to_channel`
(`notification_router.py`) kaldte ved `mobile`/`push` kun `pd._push_to_user`
(FCM) — og ved `auto` kun `route_device_aware`, som selv ender i
`_send_fcm`/`_send_desktop`. Web-push fandtes udelukkende i
`push_dispatcher._route_or_blast`, som feed-stien aldrig rammer.

**2. `run_done` havde standardkanalen `ingen`.** `STANDARD["run_done"] = "ingen"`
(`notifikations_valg.py`), og `_maaske_push` returnerer *før* routeren ved
`kanal == "ingen"`. Så for `run_done` skete der intet push overhovedet —
hverken FCM eller web.

**3. Et autonomt run bærer en intern agent-id.** Mikkels run 7/11 kl. 05:00
(`autonomous-6c927312c86242f98ecc11cc898fc05e`) havde
`user_id=3668ffdc9daa58529b9a20a570c4af92`, som ikke findes i `users` (kun
Lotte, Rune, Bjørn, Michelle, Mikkel). Notifikationen fik hans Discord-id via
`_ejer_og_titel`, men run-rækken gør ikke. **Dette er ikke rettet** — se fravalg.

## Ændring

- `notification_router.py` — `_deliver_to_channel` kalder nu `_push_to_web` i
  **begge** grene: `auto` (før `route_device_aware`, samme rækkefølge som
  `_route_or_blast`) og `mobile`/`push` (ved siden af FCM). Returværdien er
  `fcm_ok or web_ok`, så en leverance der nåede web-abonnementet ikke meldes
  som fejlet — det var Mikkels og Michelles eneste vej.
- `notifikations_valg.py` — `STANDARD["run_done"]` fra `ingen` til `auto`.
- `notifikations_emittere.py` — `_maaske_push` springer pushet over når runnet
  allerede er set live (`run_event_log.was_consumed_or_active`), og `_foed`
  sender `ref` videre så tjekket har et run-id at slå op. Kan tilstanden ikke
  læses, sendes der — et tabt svar er værre end et ekstra push.

Suppressionen er ikke pynt: målt 6/11 var **59 % af dagens 81 `run_done`** svar
på et spørgsmål stillet under et minut før (median 17 s). Uden den ville fixet
bytte et tavst system ud med et der ringer om noget man sidder og kigger på.
Det er samme `was_consumed_or_active` som `_dispatch_run_done` bruger, så de to
stier vurderer ens.

## Bevis

- `tests/test_web_push_i_feed_stien.py` (4 nye): måler **koblingen** — at
  routerens transportlag faktisk kalder `_push_to_web` — ikke funktionen alene.
- `tests/test_notifikations_emittere.py` (3 nye/omskrevne): pushet går igennem,
  suppressionen holder, og en måle-fejl fører til push frem for tavshed.
- **Mutation, auto-grenen:** fjernes `pd._push_to_web(...)`, fejler
  `test_auto_kanalen_naar_web_push`. Gendannet.
- **Mutation, suppressionen:** ændres `if _rel.was_consumed_or_active(ref)` til
  `if False`, fejler `test_faerdigt_svar_der_allerede_er_set_pusher_IKKE`. Gendannet.
- 61 tests grønne i de fire berørte filer.

## Fravalg

- **Rodårsag 3 er ikke rettet.** At knytte et autonomt run til en menneske-ejer
  kræver en beslutning om hvilken kilde der er sandheden når `visible_runs.user_id`
  er en agent-id — og den beslutning er ikke målt endnu. Feed-stien rammer ikke
  problemet, fordi den bruger `chat_sessions.owner_user_id`. Kun den anden sti
  (`detached_run` → `on_run_done`) gør.
- **`release`/`incident`/`quota` er uændrede.** De står stadig på `ingen`. Kun
  `run_done` blev hævet, fordi det er den eneste af dem brugerne venter på.
- **Ingen leveringsgaranti.** Telemetrien viser at pushet blev *afsendt* og
  hvilken vært der tog imod. Den viser ikke at enheden viste det. Den grænse
  kan ikke lukkes fra serveren.
