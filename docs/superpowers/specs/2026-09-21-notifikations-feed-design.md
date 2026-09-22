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

**Rettet 2026-09-22 (opgave "routeren-foeder").** Denne tabel lovede oprindeligt
elleve slags. Tre af dem har aldrig haft en afsender nogen steder i repoet, og
en fjerde (`question`) kan strukturelt ikke fødes af serveren. Til gengæld gik
seks ægte proaktive slags allerede gennem `notification_router.
route_proactive_notification()` uden at nogen af dem nåede feeden — det er de
efterprøvet rettet nu.

| Gruppe | Slags | Ejer af sandheden | Fødes af |
|---|---|---|---|
| Kræver dig | `approval` | `approval_runtime` | `notifikations_emittere.paa_godkendelse()` |
| Kræver dig | `question` | — | **Fødes ALDRIG.** `pause_and_ask` er et VÆRKTØJSRESULTAT som klienten fortolker (`apps/jarvis-desk/src/lib/pauseAsk.ts`), ikke en server-hændelse — der findes intet fødested at bygge. Navnet lever kun videre som en `importance`-nøgle i `notifikations_emittere._maaske_push()` (dødt, ingen kalder rammer den) og i `notifikationer_hydrering.AFGOERBARE`s modstykke. |
| Fejl | `run_failed` | `visible_runs` | `notifikations_emittere.paa_koersel_fejlet()` |
| Færdig | `run_done` | `visible_runs` | `notifikations_emittere.paa_koersel_faerdig()` |
| System | `release`, `incident`, `quota` | `events` | `notifikations_emittere.system()` |
| Jarvis selv (router-ejet, 2026-09-22) | `reach_out` | ingen — rækken ER sandheden | `notification_router.route_proactive_notification()`, kaldt fra `proactivity_bridge.py`, `action_router.py`, `autonomous_outreach_daemon.py` |
| Router-ejet (2026-09-22) | `central_flag` | ingen — rækken ER sandheden | `central_watch.py` (~2 min cadence, 6-timers cooldown pr. besked) |
| Router-ejet (2026-09-22) | `membrane_breach` | ingen — rækken ER sandheden | `central_membrane_watch.py` (kun ved NYT brud, dedup på brud-signatur) |
| Router-ejet (2026-09-22) | `infra_security` | ingen — rækken ER sandheden | `infra_sense.py` (~3 min cadence, men gated af tilstandsovergang/event-drain — se rapporten for opgaven) |
| Router-ejet (2026-09-22) | `keymaker_key_earned` | ingen — rækken ER sandheden | `central_keymaker.py` |
| Router-ejet (2026-09-22) | `moltbook_mention` | ingen — rækken ER sandheden | `central_moltbook.py` |
| **Fiktion — findes ikke** | `briefing`, `reminder`, `initiative` | — | **Ingen afsender nogen steder i repoet.** `grep -rn '"briefing"\|"reminder"\|"initiative"' --include=*.py core/ apps/` giver kun urelaterede træf (et `initiative_type` i et andet domæne, et kandidat-navn). De er kolonnenavne fra den gamle `notification_preferences`-tabel, skrevet ind i denne spec som om de var funktioner. Navnene lever videre KUN i `NotifikationsValg.tsx`s `NAVN` og i `notifikations_valg.py`s `_GAMLE_KOLONNER` — en tidligere migreret bruger kan have en gemt værdi under netop dem, og at fjerne navnet ville filtrere den værdi tavst væk fra visningen (efterprøvet igen 2026-09-22: konklusionen holder stadig). |

`route_proactive_notification()` lægger siden 2026-09-22 selv en feed-række
for enhver slags den leverer, medmindre kalderen selv allerede har lagt
rækken (`feed=False`, se `notifikations_emittere.py`). De seks router-ejede
slags ovenfor krævede derfor ingen ny kode i sig selv — kun at routeren blev
gjort til det fødested dens egen docstring længe har påstået den var.

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

**Rettelse (V8, 2026-09-22):** `team_invite` og `wakeup` mappede oprindeligt
begge til slags `initiative`. `INSERT OR IGNORE` rammer det unikke indeks på
(user_id, slags), så kun den FØRSTE af de to blev skrevet — efterprøvet:
`wakeup='push'` forsvandt tavst når `team_invite` også havde et valg, hvilket
brød løftet ovenfor om at de fem kolonner bæres over uden tab. `wakeup` har nu
sin egen slags (`wakeup`), adskilt fra `team_invite`s `initiative`.

Migreringen validerede heller ikke de gamle kolonneværdier mod
`GYLDIGE_KANALER` (`auto | mobile | desktop | push | ingen`) — de kan lovligt
indeholde `discord`/`telegram` (`notification_router.VALID_CHANNELS`), som
feedens egen kanal-vælger ikke kender. En sådan værdi klemmes nu ned til
`"auto"` ved migrering i stedet for at blive skrevet uændret over.

Standard: `approval`, `question` og `run_failed` pusher — samt (2026-09-22)
`reach_out`, `membrane_breach` og `infra_security`, som hver er begrundet i
`notifikations_valg.STANDARD`s kommentarer. Resten er tavse (feeden bærer dem
stadig — "tavs" betyder kun "intet push", se samme fil).

## Levering

- `GET /notifikationer` — åbne poster for kalderen, hydreret.
- `POST /notifikationer/{id}/afgoer` — `{approved: bool}`. **Kun `approval`.**

  Rettet 21/9 EFTER godkendelsen, fordi koden sagde noget andet end specen:
  `pause_and_ask` besvares ikke med ja/nej. Svaret er en tekst eller et af
  Jarvis' egne valg, og det sendes som en BESKED i samtalen
  (`emitPauseSvar` → composeren). Der findes ingen server-side afgørelse at
  kalde. Et spørgsmål kan derfor ikke klares i feeden — rækken fører dig hen
  til samtalen, og du svarer dér. Havde planen ikke tjekket kaldestedet, var
  der blevet bygget to knapper der ikke kunne svare noget.

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
