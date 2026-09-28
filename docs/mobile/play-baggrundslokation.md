# Play Console — baggrundsplacering (#6)

> Skrevet 28/9-2026, da mobil-appen blev undersøgt mod Google Plays krav.
> Dette er **pakken** til erklæringen: hvad Google kræver, hvad der skal svares,
> hvordan videoen skal skydes — og hvad appen mangler i koden for at kunne søge.
>
> **Status: der er ikke søgt — og 28/9-2026 blev Vej B valgt i stedet:
> Play-bygget laves uden baggrundsplacering. Se «Valget blev taget» nederst.**

## Den ærlige vurdering først

Google vurderer baggrundsplacering efter *hvilken nytte* den giver, og de skriver
selv skalaen:

- **Betydelig nytte:** fysisk sikkerhed, oplevet sikkerhed, sundhed og motion.
- **Minimal nytte:** annoncer, analyse, **personalisering**, underholdning og
  **bekvemmelighed**.

Jarvis Mobile har baggrundsplacering for at Jarvis kan tage hensyn til hvor du er
— fx i morgenbriefingen. Det er **bekvemmelighed og personalisering**, altså
Googles egen liste over *minimal* nytte. Og de skriver videre:

> «If you can deliver the same experience without accessing location in the
> background, then do that instead.»

Det kan appen. Den pinger allerede lokation i forgrunden. Baggrundsdelen tilføjer
«Jarvis ved hvor du er, selv når appen er lukket» — for en enkeltbruger-app er
det en bekvemmelighed, ikke en kernefunktion.

**Sandsynligheden for afslag er høj.** Det er ikke en teknisk vurdering jeg kan
bevise, men det følger direkte af Googles egne kriterier. Skal der søges alligevel,
skal den stærkeste formulering bruges — den står nedenfor.

## Hvad Google kræver (fire ting)

1. **Permissions declaration form** — i Play Console under *App content →
   Sensitive app permissions → Location permissions*.
2. **Video demonstration** — ≤ 30 sekunder, YouTube- eller Drive-link.
3. **Prominent in-app disclosure** — en dialog i appen, *før* systemdialogen.
4. **Privatlivspolitik** — både i appen og på butikssiden, med lokation nævnt.

Alle fire skal være på plads. Punkt 3 findes ikke i koden i dag.

---

## 1. Erklæringsformularen

Formularen beder om **én** lokationsbaseret feature — ikke flere. Flere features
giver afslag. Den stærkeste formulering for denne app:

**Hvad er appens hovedformål?**
> En personlig ledsager, der kan svare og række ud af sig selv — også når appen
> ikke er åben.

**Hvilken feature kræver baggrundsplacering?**
> Jarvis kan tage hensyn til hvor brugeren er, når han selv tager kontakt. Uden
> baggrundsplacering ville han kun kende placeringen mens appen var åben, og
> kunne derfor ikke tage hensyn til den i en morgenbriefing eller en anden
> selvstændig henvendelse.

**Hvorfor kan den ikke laves i forgrunden?**
> Brugeren har ikke appen åben, når Jarvis tager kontakt. Et forgrundsfix ville
> være forældet i det øjeblik det blev brugt.

Det sidste svar er det svageste led — og det er præcis der Google vil trykke.

## 2. Videoen (≤ 30 sekunder)

Skal vise featuren **aktiveret fra baggrunden**, disclosure-dialogen, og
runtime-prompten. Konkret skydeliste mod den app der findes nu:

| # | Skærm | Handling | Hvorfor |
|---|---|---|---|
| 1 | Indstillinger | Rul til **Lokation** | Viser hvor featuren findes |
| 2 | Indstillinger → Lokation | Tryk chippen **«I baggrund»** | Aktiverer den erklærede feature |
| 3 | *(ny)* **Disclosure-dialog** | Læses op / vises | **Kræves af Google — findes ikke endnu** |
| 4 | Systemets tilladelses-dialog | Tryk **«Tillad altid»** | Runtime-prompten |
| 5 | Hjemmeskærm | Appen lukkes | Beviser at den kører uden at være åben |
| 6 | Notifikation | «Jarvis lokation»-notifikationen ses | Foreground-servicen der holder den i live |
| 7 | Morgenbriefing / Jarvis' besked | Viser at placeringen blev brugt | Featurens *effekt* — den har ingen UI selv |

Trin 3 er blokerende: dialogen findes ikke, og uden den er videoen ugyldig.

## 3. Prominent in-app disclosure — **mangler i koden**

Det her er den egentlige opgave, ikke papirarbejdet.

**Hvad Google kræver:**

- Skal vises **i den normale brug af appen** — *ikke* inde i en menu eller
  indstillinger. (Google: «must be displayed in the normal usage of the app and
  not require the user to navigate into a menu or settings.»)
- Skal vise den **før** systemdialogen.
- Skal nævne ordet **lokation/location**.
- Skal bruge en af vendingerne: *«i baggrunden»*, *«når appen er lukket»*,
  *«altid i brug»*, *«når appen ikke er i brug»*.
- Skal nævne **hvilke features** der bruger baggrundsplacering.
- Må **ikke** kun ligge i privatlivspolitikken.
- Må **ikke** blandes sammen med andre erklæringer.

**Hvad der findes i dag:**

- `SensorPrivacyScreen.tsx` viser et **read-only dashboard** med rækker og
  risikoniveauer. Den er ikke en disclosure-dialog, og den ligger bag
  Indstillinger — hvilket er præcis det Google forbyder.
- `syncBackgroundLocation()` i `backgroundLocation.ts` kalder
  `Location.requestBackgroundPermissionsAsync()` **direkte**, uden nogen
  erklæring forinden.
- `grep` efter `disclosure`, `even when the app is closed` og tilsvarende i hele
  `apps/mobile/src` giver **nul træf**.

**Foreslået tekst** (dansk, med den engelske sætning med, så revieweren kan læse
den uden at oversætte):

> **Jarvis bruger din lokation i baggrunden**
>
> Jarvis indsamler lokationsdata for at kunne tage hensyn til hvor du er, **også
> når appen er lukket eller ikke er i brug**. Placeringen sendes kun til din egen
> Jarvis-server og deles ikke med andre.
>
> *Jarvis collects location data to enable location-aware responses even when
> the app is closed or not in use.*
>
> [ Fortsæt ]  [ Luk ]

Knappen behøver ikke være et samtykke — det giver systemdialogen umiddelbart
efter. Men den skal kunne lukkes.

**Hvor den skal bo:** i `syncBackgroundLocation()`-stien, *før*
`requestBackgroundPermissionsAsync()`, og den skal kunne vises fra den normale
brug — ikke kun fra Indstillinger. Det er en rigtig kodeændring, ikke en streng.

## 4. Privatlivspolitikken

Kræves både i appen og på butikssiden, med lokation specifikt nævnt, og på en
aktiv URL (ingen PDF). Politikken ligger på:

```
https://api.srvlab.dk/privatlivspolitik.html
```

Lokation er nævnt i politikken i dag (§3 og §7). **Men der var et hul:** se
nedenfor.

---

## Fundet undervejs: Nominatim var ikke erklæret

`reverseLabel()` i `apps/mobile/src/lib/location.ts` sender **præcise
koordinater** til OpenStreetMap's Nominatim-tjeneste for at lave et læsbart
label («Toftegårdsvej, Svendborg»):

```ts
const NOMINATIM = 'https://nominatim.openstreetmap.org'
const url = `${NOMINATIM}/reverse?format=json&lat=${lat}&lon=${lon}…`
```

Det er en **rigtig tredjepart**, og den var ikke nævnt i politikken — hverken i
tredjeparts-tabellen eller i data safety-svarene. Google kræver at politikken
udtømmende beskriver «the types of parties with whom it's shared».

**Rettet 28/9-2026:** Nominatim er nu en række i tredjeparts-tabellen i både
`apps/ui/public/privatlivspolitik.html` og `docs/mobile/privatlivspolitik.md`.

Det ændrer ikke på at *placeringen* ikke deles i Play's forstand — Nominatim får
koordinaterne for at kunne svare med et stednavn, og de gemmer dem ikke som
brugerdata. Men de skal nævnes.

---

## Anbefaling: to veje

### Vej A — søg alligevel

Skriv disclosure-dialogen, optag videoen, udfyld formularen. Koster en
eftermiddags kode plus en optagelse. **Forventet udfald: afslag**, begrundet i
minimal nytte. Et afslag koster ikke adgangen til at udgive — baggrundsplacering
er ikke en blocker for resten af appen, kun for den tilladelse.

### Vej B — fjern den fra Play-bygget

Behold baggrundsplacering i sideload-APK'en (den virker fint), og byg en variant
til Play uden `ACCESS_BACKGROUND_LOCATION` og uden
`FOREGROUND_SERVICE_LOCATION`. Appen mister «Jarvis ved hvor du er når den er
lukket» — og beholder alt andet, inkl. lokation mens appen er åben.

Det er den samme slags valg som auto-updateren: en funktion der er bygget til
sideload, og som Play ikke vil have. Google skriver selv at man skal vælge den
anden vej, hvis man kan levere oplevelsen uden.

**Det jeg ikke kan afgøre for dig:** om «Jarvis ved hvor jeg er, selv når appen er
lukket» er noget du faktisk bruger. Bruger du det ikke, er Vej B gratis. Bruger
du det, er Vej A forsøget værd — men den skal bygges færdig først, uanset.

---

## Valget blev taget: Vej B (28/9-2026)

Bjørn valgte Vej B. Play-bygget laves uden baggrundsplacering; sideload-APK'en
beholder den.

**Sådan er det bygget.** En ny build type `play` ved siden af `release`, med sin
egen manifest-fil `android/app/src/play/AndroidManifest.xml` der fjerner fire
ting via `tools:node="remove"`:

| Fjernet | Hvorfor |
|---|---|
| `ACCESS_BACKGROUND_LOCATION` | Hele sagen (#6) |
| `REQUEST_INSTALL_PACKAGES` | Appens egen opdatering — Play forbyder selv-opdatering |
| `SYSTEM_ALERT_WINDOW` | Samme mekanisme |
| `FOREGROUND_SERVICE_LOCATION` + `LocationTaskService` | Uden baggrundslokation kan servicen ikke starte, og en ubrugt location-service kræver sin egen begrundelse i Play |

`FOREGROUND_SERVICE` (uden `_LOCATION`) blev **beholdt** — WebRTC's
`mediaProjection` og notifees `shortService` bruger den.

**Sideload-vejen er urørt.** `assembleRelease` bygger præcis som før. Play-bygget
laves separat:

```
./gradlew :app:assemblePlay -PreactNativeArchitectures=arm64-v8a
./gradlew :app:bundlePlay -PreactNativeArchitectures=arm64-v8a
```

Varianten hedder bare `play` (ingen flavors), så opgavenavnene er `assemblePlay`
og `bundlePlay` — **ikke** `playRelease`. APK'en lander i
`app/build/outputs/apk/play/app-play.apk`.

**Verificeret 28/9-2026** ved at bygge begge varianter og sammenligne de merged
manifester:

| Tilladelse | `release` | `play` |
|---|---|---|
| `ACCESS_BACKGROUND_LOCATION` | har | **mangler** |
| `REQUEST_INSTALL_PACKAGES` | har | **mangler** |
| `SYSTEM_ALERT_WINDOW` | har | **mangler** |
| `FOREGROUND_SERVICE_LOCATION` | har | **mangler** |
| `CAMERA`, `RECORD_AUDIO` | har | har |

Play-APK'en blev bygget (57,7 MB, arm64) og er signeret med upload-nøglen
`CN=Jarvis Mobile, O=srvlab.dk`.

**Kendt skævhed i Play-bygget:** indstillings-skærmen viser stadig chippen
«I baggrund». Den kan ikke slås til — `requestBackgroundPermissionsAsync()`
returnerer ikke «granted», og `backgroundLocation.ts` falder tilbage til
forgrunds-ping. Chippen bør skjules i Play-bygget, men det kræver et
build-tids-flag der kan læses fra JS. Ikke bygget endnu.

**Dermed er #3 i Play-listen ikke længere en blocker for udgivelsen** — men
bemærk at rækkefølgen i `docs/mobile/` ikke er en prioritering. Auto-updateren
var samme slags konflikt, og den er nu også ude af Play-bygget.
