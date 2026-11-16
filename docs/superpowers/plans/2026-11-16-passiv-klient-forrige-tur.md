# Problem 3 — to klienter på samme session: den passive klient viser forrige tur

**Målt 16/11-2026 af Jarvis. Rettelsen er IKKE bygget endnu — dette er diagnosen.**

## Symptomet (Bjørn, ordret)

> «Hvis jeg har feks. Code mode åben både i browseren og i desk. Og trykker send
> i den ene så startes streamen pænt men i den anden klient starter streamen op i
> forrige tur indtil turen er forbi.»

## Den målte kæde

Målingen ligger i `apps/jarvis-desk/src/lib/streamReducer.passivKlient.test.ts`
(3 tests, alle grønne — de DOKUMENTERER den nuværende adfærd, de retter intet).

Test 1: en klient med `svarLaast=true` og blokken `'Forrige turs svar.'` modtager
`message_start` for et nyt run. Resultat: **blokken står tilbage, `svarLaast` er
stadig sand, `activeRunId` er skiftet til det nye run.**

Test 2: den nye turs tekst strømmer ind. Resultat:
`['Forrige turs svar.Ny turs svar.']` — **én blok, de to ture smeltet sammen.**
Det er præcis det Bjørn ser som «streamen starter op i forrige tur».

Test 3 (kontrol): en klient der selv sender, får `client_turn_start` og rydder
korrekt. Forskellen mellem de to klienter er **én frame**.

## Roden — tre led, alle i `streamReducer.ts`

**1. `svarLaast` ryddes KUN af `client_turn_start` (linje 484-497).**
Den frame sendes kun af den klient der selv trykkede send. Den passive klient
modtager den aldrig — så dens lås fra den forrige tur står ved magt.

**2. `_bevar` arver derfor de gamle blokke (linje 324):**
```ts
const _selvstaendig = !!_indkommende && state.selvstaendigRunId === _indkommende
const _bevar = _sameRun || (state.svarLaast && !_selvstaendig)
```
`svarLaast` er sand → `_bevar` er sand → `blocks: _bevar ? state.blocks : []`
beholder den forrige turs blokke.

**3. `_selvstaendig` kan ikke redde den, og det er den vigtigste måling.**
`selvstaendigRunId` sættes kun af `run`-framen med `origin` (linje 671-676) — og
den frame kommer **efter** `message_start`. Kommentaren i koden siger det selv:
*«`message_start` kommer nemlig før denne frame (sse_v2's fallback-gren emitter
den først), så `activeRunId` er allerede skiftet når origin ankommer.»*

Så ved `message_start` er `_selvstaendig` **altid falsk** for et run klienten
ikke har set før. Vagten kan per konstruktion ikke se forskel på:
- en RUNDE i min egen tur (skal bevares), og
- en FREMMED tur fra en anden klient (skal ryddes).

Det er ikke en glemt betingelse. Det er en manglende **information** på det
tidspunkt hvor beslutningen træffes.

## Hvad der IKKE er roden (målt, så det ikke forfølges igen)

- **`followRun` er ikke skylden.** Både `ChatView.tsx:377` og `CodeView.tsx:654`
  kalder `followRun` **uden** run-id, så de rammer `/chat/sessions/{id}/live`,
  som attach'er til sessionens AKTIVE run fra offset 0. Korrekt.
  Kun `StreamContext.reattach` (linje 313) sender `runIdRef.current` med — og
  den sti rammer kun efter et netværksbrud, ikke ved en frisk tur.
- **Backend er ikke skylden.** `server_authoritative_runs` er `True` (målt i
  `runtime.json` OG gennem `load_settings()`), og `/chat/sessions/{id}/live`
  returnerer det aktive run korrekt.
- **`bgActive`-pollingen er ikke skylden.** Den finder runnet; problemet er
  reducerens håndtering af de frames den allerede modtager.

## Rettelsens form (ikke bygget)

Beslutningen skal træffes på et tidspunkt hvor informationen FINDES. Tre veje,
i stigende indgreb:

**A. Løft `origin` ind i `message_start`.** Serveren kender svaret når den
emitterer framen. Er `origin` tom for brugerens egen tur, kan reduceren rydde
låsen når `origin` er sat — uden at gætte.

MÅLT 16/11: vejen er farbar, men kræver tre små tilføjelser:
1. `MessageStart` (`apps/api/jarvis_api/sse_v2_events.py:34-58`) har felterne
   `run_id`, `model`, `provider`, `lane`, `session_id` — **ikke `origin`**.
   Tilføj `origin: str = ""` og læg den i `message`-payloaden.
2. `_state` (`core/services/visible_runs_sse_v2.py:348+`) har ikke `origin`.
   Tilføj nøglen og sæt den fra run-kilden.
3. `_emit_message_start_if_needed` (`visible_runs_sse_v2.py:410-421`) skal sende
   den med: `origin=str(_state["origin"] or "")`.

`origin` findes allerede i `core/services/autonomous_stream_run.py:281,292`, så
værdien skal ikke opfindes — den skal bare bæres videre til den frame der
emitteres først.

**B. Behandl et nyt run-id som turgrænse når klienten ikke selv streamer.**
Klienten ved om den har et aktivt `send()` i gang (`workingSessionId` /
`controlRef`). Er den passiv og ser et nyt run-id, er det per definition en
fremmed tur. Kræver at reducereren får den viden — i dag har den den ikke.

**C. Send `client_turn_start` til ALLE klienter på sessionen.** Så får den
passive klient samme autoritative grænse som den aktive. Mest korrekt
semantisk, størst blast-radius (alle klienter skal tåle den).

**Anbefaling: A.** Den flytter beslutningen til det sted hvor sandheden allerede
findes, og den kræver ingen ny tilstand i klienten. B er næstbedst og kan gøres
helt klient-side.

## Verifikation når den er bygget

De tre tests i `streamReducer.passivKlient.test.ts` skal VENDE:
- test 1: `forrigeSvarStaarTilbage: false`, `svarLaast: false`
- test 2: `tekst: ['Ny turs svar.']`, ikke sammensmeltet
- test 3: uændret grøn (den aktive klient må ikke regrediere)

Og mutationsverifikation: fjern rettelsen, bekræft at test 1 og 2 fejler igen.

## BYGGET 16/11-2026 — sådan blev det løst

Vej A er bygget: den eksisterende `origin` fra den autonome run-kilde bæres nu
gennem SSE-v2's `message_start`. Reduceren bruger feltet som autoritativ
turgrænse, så en passiv klient rydder forrige turs blokke og `svarLaast`, før
den fremmede turs tekst åbnes. Tom/manglende `origin` bevarer brugerens egne
runder som før. De vendte klientmålinger, backend-kontrakttests og begge
renderer/web-builds er grønne; mutation uden origin-grenen fælder test 1 og 2.
