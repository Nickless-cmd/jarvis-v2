# Notifikations-feed og push — design

**Dato:** 2026-09-21
**Bestilt af:** Bjørn
**Status:** afventer godkendelse

> «vi skal have lavet et notifikations system/push system og klokken skal være
> notifikations feed med en tæller ved klokken og hvor det er muligt at trykke
> og se notifikation og push beskeder… mulighed for at trykke ind og se og
> hoverover information på beskederne og mulighed for at afvise eller godkende
> det der kommer igennem… og med den nuance owner feed det hele og andre
> bruger kun feed vedrørende dem»

## Hvad der allerede findes

Kortlagt før designet, fordi det hyppigste mønster i dette repo er kode der er
korrekt og som ingen kalder.

- `core/services/notification_router.py` — POLITIK: per-bruger-præference,
  stilletimer, kanalvalg, eskalering. Ét indgangspunkt,
  `route_proactive_notification()`.
- `core/services/push_dispatcher.py`, `desktop_notifications.py` — transport.
- `core/runtime/opmaerksomhed` + `GET /cowork/opmaerksomhed` — tilstands-hjernen.
  Giver allerede en prioriteret tilstand med en `punkter[]`-liste. Det er det
  nærmeste et feed der findes i dag.
- `core/services/approval_runtime.py` — `pending_for_owner()`, `decide()`,
  `state()`. Godkendelsers livscyklus har allerede en ejer.
- Tabellen `events` — systemhændelser ligger der.

**Det afgørende hul: der er intet notifikations-lager.**
`route_proactive_notification()` er ren transport — fyr og glem. Der findes kun
`notification_preferences` (politik) og `delayed_notifications` (kø til
stilletimer). En besked der er leveret, findes ikke bagefter. Et feed kræver
noget at læse i.

## Afgrænsning

**Med:** feeden, dens lager, klokken med tæller i desk OG mobil, godkend/afvis
i fladen, per-slags push-valg.

**Ikke med:** at app-opdateringer kræver at man går ud og ind af appen igen.
Jarvis byggede push-vejen 20/9 (`app_release.py` → `app.release.available` på
bussen → `electron/appRelease.ts` lytter over WS). At den ikke leverer er en
FEJL i en eksisterende vej, ikke et designspørgsmål. Den hører til en
fejljagt med måling, ikke til denne spec — ellers bliver en brudt ledning til
en arkitekturdiskussion.

## Slags

En *slags* er enheden for både visning og push-valg.

| Gruppe | Slags | Ejer af sandheden |
|---|---|---|
| Kræver dig | `approval`, `question` | `approval_runtime` |
| Fejl | `run_failed` | `visible_runs` |
| Færdig | `run_done` | `visible_runs` |
| Jarvis selv | `briefing`, `reminder`, `reach_out`, `initiative` | ingen — rækken ER sandheden |
| System | `release`, `incident`, `quota` | `events` |

## Lageret

Én tynd tabel. Rækken **peger** på ejeren; den kopierer ham ikke.

```sql
CREATE TABLE IF NOT EXISTS notifikationer (
    id          TEXT PRIMARY KEY,   -- uuid4
    user_id     TEXT NOT NULL,
    slags       TEXT NOT NULL,      -- approval | question | run_failed | …
    kilde       TEXT NOT NULL,      -- approval | run | event | egen
    ref         TEXT,               -- ejerens nøgle: approval_id / run_id / event.id
    session_id  TEXT,               -- hvor det hører hjemme, hvis nogen
    titel       TEXT NOT NULL,      -- fald-tilbage naar ejeren ikke kan hydreres
    tekst       TEXT NOT NULL DEFAULT '',
    oprettet    TEXT NOT NULL,
    klaret      TEXT,               -- NULL = aaben
    udfald      TEXT                -- approved | rejected | seen | superseded
);
CREATE INDEX IF NOT EXISTS ix_notif_aaben ON notifikationer(user_id, klaret, oprettet);
CREATE UNIQUE INDEX IF NOT EXISTS ux_notif_ref ON notifikationer(slags, ref) WHERE ref IS NOT NULL;
```

`ux_notif_ref` er der for at samme godkendelse ikke kan lande to gange når en
hændelse gen-udsendes. `ref IS NULL` (det Jarvis selv sender) er undtaget —
to påmindelser må godt ligne hinanden.

### Hvorfor rækken bliver liggende når den er klaret

Feeden er en **to-do-liste**: klaret betyder væk fra fladen. Men rækken slettes
ikke med det samme, for uden den ville en gen-udsendt hændelse genåbne noget du
lige har klaret. En oprydning fjerner klarede rækker efter syv dage.

## Hydrering — designets kerne

Ved læsning slås hver åben række op hos sin ejer:

- `kilde='approval'` → `approval_runtime.state(ref)`. Er den ikke længere
  ventende, sættes `klaret` med `udfald='superseded'`, og rækken falder ud.
- `kilde='run'` → kørslens status. Er den ikke længere fejlet/ulæst, lukkes den.
- `kilde='event'` → `events`-rækken.
- `kilde='egen'` → `titel`/`tekst` er sandheden.

**Konsekvens, og grunden til at det er valgt:** godkender du på telefonen,
helbreder desk-feeden sig selv ved næste læsning. Ingen skal huske at rydde op
to steder, og der kan ikke opstå et spøgelse man godkender to gange. En kopi af
godkendelsen i feeden ville have den fejl indbygget.

Hydrering der fejler lukker ikke rækken — den viser `titel`/`tekst` og
markeres «kunne ikke opdateres». En utilgængelig ejer må ikke se ud som en
klaret opgave.

## Omfang pr. bruger

Rækken bærer `user_id`.

- **Owner:** egne rækker + alle `system`-rækker (som får `user_id` = owner).
- **Andre:** kun rækker hvor `user_id` er dem selv.

Owner ser altså alt **om maskinen**, men ikke andre brugeres personlige
notifikationer. Det er en bevidst læsning af «owner feed det hele», bekræftet
21/9: en feed der viste andres indhold ville gå uden om den stående regel om at
deres ting er krypterede og ikke ment til ejeren.

## Push

Push går gennem `route_proactive_notification()`. Stilletimer og kanalvalg
findes allerede dér, og en politik nummer to ville komme i utakt med den første.

`notification_preferences` har én kolonne pr. type (`briefing`, `reminder`,
`reach_out`, `team_invite`, `wakeup`) og kan ikke bære «per slags» uden en ny
kolonne hver gang. Den del laves om til rækker:

```sql
CREATE TABLE IF NOT EXISTS notifikations_valg (
    user_id TEXT NOT NULL,
    slags   TEXT NOT NULL,
    kanal   TEXT NOT NULL,          -- auto | mobile | desktop | push | ingen
    PRIMARY KEY (user_id, slags)
);
```

Migrering: de fem eksisterende kolonner skrives over som rækker ved opstart, én
gang. Kolonnerne bliver stående indtil alle kaldesteder læser den nye tabel;
`notification_router` læser rækker med kolonnerne som fald-tilbage, så en
halvvejs migreret base ikke taber nogens valg.

Standard: `approval`, `question` og `run_failed` pusher. Resten er tavse.

## Levering

- `GET /notifikationer` — åbne poster for kalderen, hydreret.
- `POST /notifikationer/{id}/afgoer` — `{approved: bool}` for handlingsrækker.
  Ruten vælger vej efter slags: `approval` → `approval_runtime.decide()`,
  `question` → pause_and_ask' eget svar-kald. De to ligner hinanden i fladen,
  men er IKKE samme mekanisme, og en rute der kaldte `decide()` for begge ville
  svare det forkerte sted.

  Feed-rækken lukkes af hydreringen, ikke af ruten. Ét sted der bestemmer —
  ellers kunne ruten lukke en række hvis ejer stadig venter.
- `POST /notifikationer/{id}/set` — for dem uden handling.
- Live: `notifikation.ny` / `notifikation.klaret` på det WS-event-socket desk
  og mobil allerede bruger. Lavfrekvent poll som sikkerhedsnet, samme mønster
  som resten af appen.

## Flader

**Tælleren** er antal ÅBNE rækker — alle slags, ikke kun dem der kræver et
svar. Det følger af to-do-listen: står noget i feeden, er det ikke klaret. En
tæller der kun talte godkendelser ville lade et fejlet run stå usynligt bag et
tomt tal.

**Desk:** klokken øverst i venstre panel (sidder der allerede siden 21/9) får
den tæller. Klik åbner en popover forankret til klokken. Hver
række: ikon efter slags, titel, relativ tid. Handlingsrækker har Godkend/Afvis
inline. Hover viser den fulde tekst. Klik på rækken går hen hvor den hører til.

**Mobil:** samme rute, samme tæller. Feeden er en skærm frem for en popover.

Begge flader bygges i samme omgang, efter aftale — desk og mobil er gledet fra
hinanden før (tool-linjens tekst stod to dage bagud på mobilen), og en delt
server gør det billigt at gøre samtidig.

## Fejl skal kunne ses

Feeden er selv et sted hvor en tom kasse og en fejl kan forveksles. Kan listen
ikke hentes, siger fladen det — den viser ikke «ingen notifikationer». Samme
regel som resten af desk efter 21/9.

## Test

- Hydrering lukker en godkendelse der er afgjort et andet sted.
- Hydrering der fejler lukker IKKE rækken.
- `ux_notif_ref` afviser den samme godkendelse to gange.
- Owner ser systemrækker; en anden bruger gør ikke.
- En anden brugers personlige række når ALDRIG owners feed.
- Push-valg pr. slags respekteres, og stilletimer slår igennem.
- Migreringen bærer de fem kolonner over uden at tabe et valg.
- Desk og mobil: tælleren falder når man godkender, uden at siden genindlæses.
