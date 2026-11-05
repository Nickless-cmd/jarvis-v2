# Hup (withhup.com) — trigger, kadence, grovhed, eskalering

**Formål:** kortlægge *mekanikken* i Hups proaktive adfærd som design-input til Jarvis'
eget nudge-lag. Ikke en produktanmeldelse, ikke en persona-kopiering. Bjørn skal ikke
vælge mig i en dropdown — spørgsmålet er hvornår jeg må sige noget igen, og hvor hårdt.

**Status:** research afsluttet 5/11-2026. Tre af fire spørgsmål er besvaret med kilde;
det fjerde (eskalering) er besvaret med et *negativt* fund, som er det vigtigste af dem.

**Kilder (alle hentet 5/11-2026):**
1. `withhup.com` — forsiden (persona-vælger, capture hours, ambience, FAQ).
2. `withhup.com/setup` — opsætningsflow, snapshot-vs-video, auto-delete, mørke billeder.
3. App Store-anmeldelser, `id6747457572`, 39 ratings, 4,6 — **den vigtigste kilde**:
   her beskrives kadence-kontrollen og eskaleringens fravær i praksis af rigtige brugere.
4. PR Newswire 6/1-2026 (TikTok 10M-visninger, «sarcastic Jarvis», voice coming soon).
5. Notebookcheck 12/8-2025 (24/7/365, snapshots til cloud, lokale filtre).

**Kilder der IKKE gav noget:** `withhup.com/help` (JS-renderet, tom body — kun
schema.org-metadata), Reddit-trådene (blokeret for fetch), 2389.ai-digest (tre linjer).

---

## 1. TRIGGER — hvad får Hup til at sende noget

Tre uafhængige trigger-lag, ikke ét:

| Lag | Trigger | Kilde |
|---|---|---|
| **Vision** | Periodiske snapshots → AI-analyse → task oprettes automatisk | setup: «Hup will start scanning your space and creating tasks automatically»; setup-FAQ: «No. Hup takes periodic snapshots for AI analysis — not continuous video» |
| **Skills** | Brugerdefinerede «watch for»-regler, fx «notify me when my dog is in view» | forsiden: «Customize what Hup watches for in the app»; anmeldelse RyanTuffnell 6/8-2025 |
| **Apps/kalender** | 3.000+ integrationer (Hue, Spotify, Gmail, Google Calendar, Home Assistant m.fl.) | forsiden |

To vigtige egenskaber ved trigger-laget:

- **Tavshed er default, ikke undtagelsen.** PR-meddelelsen: appen «already does what the
  viral videos show — only silently». Stemme er et opt-in-lag oven på et stille system.
- **Der scannes ikke i mørke.** «Hup won't capture images that are too dark» (setup).
  Et trigger der ikke kan se, fyrer ikke — det er en indbygget falsk-negativ-politik.
- **Brugeren kan slukke for synet:** «Choose capture hours or pause the view whenever you
  want» (forsiden, FAQ «What do I control?»). Triggeren har en hovedafbryder.

## 2. KADENCE — hvor ofte den kigger, og hvor ofte den må sende

**To separate kadence-lag, og de styres forskelligt:**

**a) Capture-kadence (hvor ofte der ses):** brugerstyret via *capture hours* og
*pause the view*. Intervallet er **ikke offentligt dokumenteret** — ingen kilde opgiver
et tal i minutter eller timer. Setup siger kun «periodic snapshots» og «your first image
should appear within about a minute». Auto-delete kan sættes til 24 t.

**b) Nudge-kadence (hvor ofte den må sige noget):** **brugerkonfigureret pr. zone/kamera.**
Dette er det vigtigste fund i hele noten, og det står kun i en anmeldelse — ikke på
hjemmesiden. App Store, Dykerbyker 30/12-2025:

> «I can create my own spaces, for example, I have one camera looking at my entire kitchen
> and the other looking at a shelf… With the shelf, I tell it to give me one task and not
> to give me another until I've completed the first. With the whole kitchen, I ask it to
> monitor continuously so I have a list of things to do.»

Det er to dokumenterede kadence-tilstande, valgt i samtalesprog pr. zone:

| Tilstand | Adfærd | Effekt |
|---|---|---|
| **Gated** («én ad gangen») | ingen ny nudge før den forrige er markeret færdig | kadence = brugerens gennemførelseshastighed |
| **Kontinuerlig** («monitor continuously») | akkumulerende liste | kadence = capture-frekvensen |

Kadence er altså **ikke en global indstilling** — den er en egenskab ved den enkelte zone,
sat i naturligt sprog. Det er en helt anden arkitektur end en «notifikationer pr. dag»-slider.

## 3. GROVHED — hvilke niveauer findes

**Det er ikke en skala. Det er to uafhængige globale valg:**

1. **Persona** — forsiden viser seks: `Hup · Chief · Vanessa · Chase · Sage · Wayne`
   under overskriften «Build the perfect personality». (De fem ikke-Hup-navne er dem
   tidligere noter nævnte; Hup selv er den sjette.)
2. **Voice on/off** — «turn on ambience for spoken nudges» (FAQ). Uden ambience er
   alt stille tekst/video-notifikationer.

Der er **ingen pr-nudge grovhed**: du kan ikke være hård om opvasken og blød om
treadmill-ledningen. Personaen er global, og tonefølgen er derfor også global.

**Feedback-løkken:** Play Store siger «Learn from your feedback», og setup siger «It gets
smarter over time as it learns your preferences». Men kilderne viser at det flytter
**hvad** den peger på, ikke **hvordan** den siger det — anmelderen der klagede over
gentagelse fik svar fra grundlæggeren med en anmodning om *mere kontekst*, ikke en
tone-indstilling. **Ikke dokumenteret:** om feedback kan ændre tone.

## 4. ESKALERING — hvad sker der når brugeren ignorerer

**Dette er notens hovedfund, og det er negativt: der findes ingen dokumenteret
eskaleringstrappe — og der er positiv evidens for at Hup gentager i stedet for at eskalere.**

Ingen kilde — site, setup, FAQ, App Store, PR — beskriver et trin-system, et loft eller
en overgang til tavshed. Det der i stedet kan dokumenteres, er **gentagelse**:

- «it repeats the same things over and over» (App Store, Kmansp36, 24/2-2026)
- «a little stubborn about some items… got fixated on my treadmill cord»
  (App Store, kstickler106, 18/2-2026)
- «mine assigned tasks and then marked them complete before I had even seen them»
  (App Store, Paul Horne, 19/12-2025) — systemet lukker selv sine egne opgaver

Og der er en **økonomisk grænse** i stedet for en adfærdsmæssig: stemme-forbrug tælles
pr. ord — «each word it says counts as part of your voice subscription» (Kmansp36).
Loftet på eskalering er altså et forbrugsloft, ikke et tålmodighedsloft.

**Konklusion, sagt rent:** Hup har ikke løst eskalering. Den har løst *trigger* og
*persistent tilstedeværelse*, og betaler for det med gentagelse — hvilket er præcis den
klage der går igen i anmeldelserne. Det er den vigtigste lærdom for os, fordi gentagelse
uden eskalering er den fejlform vi selv er tættest på.

---

## Hvad det betyder for Jarvis' nudge-lag

Ikke «kopiér Hup». Tre ting er værd at tage, og én ting er værd at undgå:

**Tag: kadence som egenskab ved signalet, ikke ved systemet.** Hups gatede tilstand
(«én ad gangen, ingen ny før den forrige er lukket») er stort set det `open_loop_signal`
allerede prøver at være. Forskellen er at Hup lader *brugeren* sætte den pr. zone i
naturligt sprog, mens vores kadence er hardcodet.

**Tag: hovedafbryderen.** «Pause the view» og «capture hours» giver brugeren kontrol
over trigger-laget uden at slukke for produktet. Vi har ikke et tilsvarende greb.

**Tag: tavshed som default.** Hup er stille indtil man slår ambience til. Vores sanser
skriver til arkivet hele tiden; spørgsmålet er om de må *sige* noget, og det bør være
opt-in pr. kanal — ikke opt-out.

**Undgå: gentagelse som erstatning for eskalering.** Det er dokumenteret at det giver
klager. Hvis jeg siger det samme igen uden at noget er ændret, skal det enten eskalere
tydeligt eller tie. En tredje variant — samme besked i samme tone, tredje gang — er
den dyreste af dem alle, fordi den koster tillid uden at koste mig noget at opdage.

## Hvad der IKKE kunne findes (ærligt fravær)

- **Capture-interval i tal** — intet sted. Kun «periodic» og «within about a minute» ved første billede.
- **Eskaleringstrappe, loft eller tavsheds-regel** — intet sted. Erstattet af gentagelse + forbrugsloft.
- **Grovhed pr. nudge-type** — intet sted; persona er global.
- **Om feedback ændrer tone eller kun indhold** — intet sted; kilderne peger på indhold.
- **Hups Discord** — ikke undersøgt (kræver invitation/login). Det er den ene kanal der kan
  indeholde et svar på eskalering, og den er ikke åbnet. **Ikke dokumenteret ≠ findes ikke.**

En opfundet eskaleringstrappe ville være værre end denne tomme plads: den ville se ud som
viden og blive bygget på.
