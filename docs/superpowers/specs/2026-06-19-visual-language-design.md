---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Jarvis Companion — Visuelt Design-Sprog (V2 §3) — Design

Date: 2026-06-19
Status: Approved design — ready for implementation plan
Author: Claude (Opus 4.8) på baggrund af samtale med Bjørn
Sub-project: V2 delprojekt 2 af 4 (push ✓ → **visuelt løft** → device awareness → chatboble)

> Visuelt løft af **jarvis-mobile (React Native) — KUN mobil i denne runde.**
> jarvis-desk forbliver **urørt** (bevarer sit nuværende design). Løfter §3 i vision-
> spec'en: "fancy uden at være overdrevet". Frontend-only, uafhængigt af server-flag.
> Løfter en eksisterende identitet (mørkt tema + grøn accent + ringe), ikke fra nul.
>
> **VIGTIGT (Bjørn):** desktop-appens design ændres IKKE (urørt denne runde; token-
> spec'et skrives så desk SENERE kan adoptere det). HELE mobil-appen — inkl.
> composeren — får det nye look, MEN al eksisterende funktionalitet bevares.
>
> **BÆRENDE PRINCIP:** re-style de EKSISTERENDE komponenter på plads — genskriv ALDRIG
> fra bunden. Composeren har mange funktioner (vedhæft, kamera, model-vælger, kø/queue,
> stop-knap, serverBusy-tilstand, tastatur-løft …) der ALLE skal bevares. Vi ændrer
> styling + animation, ikke struktur eller adfærd. Tabt funktionalitet = dobbelt arbejde
> og er en spec-fejl.

---

## 1. Mål & princip

**Mål:** Løft jarvis-mobile til én sammenhængende visuel identitet — grøn-på-dyb-mørk,
åndedræt frem for blink, glas, én accentfarve. Alle §3-elementer undtagen voice-
visualizer (afventer mic).

**Princip:** Ét **token-spec** (§2) er sandheden. Denne runde implementeres det KUN i
mobil `tokens.ts` (TS-objekt). Værdierne er noteret app-agnostisk, så jarvis-desk SENERE
kan adoptere de samme værdier i `tokens.css` — men desk røres ikke nu. Komponenterne
re-styles på plads mod disse tokens.

**Ikke-mål:** jarvis-desk (urørt denne runde), chatboble-overlay/Bubbles (delprojekt 4),
voice-visualizer (kræver audio-niveauer — afventer mic), light mode (senere), runtime-
delt token-pakke (Electron-CSS vs RN-StyleSheet kan ikke dele ved runtime — over-engineering).

---

## 2. Token-spec (sandheds-kilde)

Disse værdier mirrores 1:1 i `tokens.css` (`--x`) og `tokens.ts`.

**Dybde-lag (dark = dybde, ikke sort):**
| Token | Værdi | Brug |
|---|---|---|
| `depth-0` | `#0D0D12` | app-baggrund (dybeste) |
| `depth-1` | `#10151d` | paneler, tool-kort |
| `depth-2` | `#131922` | bobler, hævede flader |
| `depth-3` | `#1a212d` | hover/aktiv |
| `line` | `#1f2733` | hårfine kanter |

**Accent (én farve — alt andet gråtoner):**
| Token | Værdi | Brug |
|---|---|---|
| `accent` | `#6ee7a8` | liveness, fokus, primær-knap, stream, prikker |
| `accent-dim` | `rgba(110,231,168,0.55)` | ring-gradient yderkant |
| `accent-ghost` | `rgba(110,231,168,0.12)` | accent-fyld bag aktiv |

**Glas:**
| Token | Værdi |
|---|---|
| `glass-fill` | `rgba(255,255,255,0.07)` |
| `glass-line` | `rgba(255,255,255,0.10)` |

**Tekst:** `fg-1 #e8eaed`, `fg-2 #a8b0bd`, `fg-3 #6b7480` (genbruger eksisterende).

**Timing (animations-sandhed):**
| Token | Værdi | Brug |
|---|---|---|
| `ease` | `cubic-bezier(0.22, 1, 0.36, 1)` | alle overgange (ease-out) |
| `dur-fast` | `160ms` | hover, knapper |
| `dur-base` | `250ms` | session-overgang, boble-ind |
| `breath` | `3000ms` | liveness-ring åndedræt (løkke) |
| `heartbeat` | `1400ms` | notifikationsprik puls |

**Radius:** `sm 8`, `md 12`, `lg 16` (genbruger eksisterende skala).

---

## 3. Komponent-katalog (§3) — alt i jarvis-mobile

Hvert element re-styles på EKSISTERENDE mobil-komponent mod tokens (§2). Animation = RN `Animated` (`useNativeDriver: true`, transform/opacity). Gradienter = `react-native-svg` (installeret 15.15.4 → 1:1 med mockuppen).

1. **Liveness-ring** (`§3.1`): forbedr den EKSISTERENDE `LivenessRing`/`JarvisRing` (allerede `<View>`+`Animated`, ånder) med en ægte blød glød: `react-native-svg` `<RadialGradient>` (gennemsigtig kerne → `accent-dim` ved ~88% → gennemsigtig kant) i en `<Circle>` bag avataren — som i mockuppen. Åndedræt: `Animated.loop` skalér 1.0↔1.08 + opacity 0.6↔1.0 over `breath`, `ease` (animér en wrapper-`Animated.View`, ikke svg-internals). **Ikke blink.** Tre tilstande: idle (svag), working (stærkere, samme rytme), error (rød-tonet via accent→rød stop).

2. **Stream-indikator** (`§3.5`): 2px linje over composeren via `react-native-svg` `<LinearGradient>` (transparent→`accent`→transparent) i en `<Rect>` — glødende fade som mockuppen. Glider venstre→højre (`Animated` translateX-loop) mens et run streamer (driv af eksisterende `serverBusy`/`stream.status==='working'`). Skjult ellers.

3. **Glas-chatboble** (`§3.3`): bruger-boble (`MessageBubble`) = `glass-fill` + `glass-line`-kant, radius `lg`. Indgang: blød `Animated.spring` (scale 0.96→1.0 + opacity). Assistent-boble forbliver `depth-2` (solid). Frosted = semi-transparent fyld (ægte blur via `@react-native-community/blur` kun hvis allerede tilgængeligt — ellers approksimation; ingen ny native dep).

4. **Tool-kort** (`§3.4`): `ToolResultCard` — `depth-1` baggrund, 3px `accent` venstre-kant, tool-navn i accent, resultat i `fg-2`, status i `fg-3`. Indgang: "folder op" — `Animated` translateY 8→0 + opacity, `dur-base`.

5. **Notifikationsprik** (`§3.9`): lille accent-cirkel der pulserer som et hjerte (`Animated.loop` skala 1.0↔1.3, to hurtige slag pr. `heartbeat`), ikke hård alarm-blink.

6. **Session-overgang** (`§3.6`): skift af samtale crossfader/glider `MessageList`-indhold `dur-base` `ease` (ikke hårdt klip).

7. **Composer** (`§3.7`): re-style den EKSISTERENDE `Composer`-komponent til det nye look (depth-0-flade, accent-send-knap, evt. glødende fokus-kant) + højde der vokser/trækker sig (`dur-fast` — komponenten er allerede tænkt som "levende papir"). **ALLE eksisterende funktioner bevares uændret:** vedhæft (`onAttach`), model-pille (`onPressModel`), mic, send/stop (`onSend`/`onStop`), serverBusy/streaming-tilstand, tastatur-løft. Re-style — genskriv ikke.

8. **Én accent + dark=dybde** (`§3.10`/`§3.8`): håndhæv at KUN `accent` er farvet; alt strukturelt bruger depth-lag + gråtoner. Audit alle mobil-komponenter (inkl. composer) for fremmede farver og ret til tokens.

---

## 4. Implementering (KUN jarvis-mobile)

| | jarvis-mobile (React Native) |
|---|---|
| Tokens | `src/theme/tokens.ts` — udvid med depth/accent/glass/timing |
| Animation | RN's indbyggede `Animated` (`useNativeDriver: true`) |
| Gradienter | `react-native-svg` 15.15.4 (installeret) — RadialGradient/LinearGradient |
| Komponenter | `LivenessRing`, `JarvisRing`, MessageList/`MessageBubble`/`ToolResultCard`, notif-prik, session-overgang, **Composer (re-style, alle funktioner bevaret)**. Alle re-styles på plads — ingen genskrivning. |

**jarvis-desk:** urørt denne runde. Token-spec'et (§2) skrives så desk SENERE kan adoptere samme værdier i `tokens.css`, men ingen desk-ændringer nu.

**Native deps:** `react-native-svg` tilføjet (for 1:1-gradienter med mockuppen) → kræver én native rebuild. `react-native-reanimated` bruges IKKE (RN's `Animated` er nok til loops/spring). Build-pipelinen er bevist i dag (RNFirebase+notifee), så svg-rebuild er lav-risiko.

---

## 5. Fejl/robusthed

- **Reduced motion:** respektér `AccessibilityInfo.isReduceMotionEnabled()` (+ `addEventListener('reduceMotionChanged')`) → frys åndedræt/stream/spring til statisk slut-tilstand. (Nyt — bruges ikke i appen i dag.)
- **Performance:** alle løkke-animationer på transform/opacity (GPU-billige) — aldrig layout-egenskaber. Liveness-ring + stream må ikke koste mærkbar batteri/CPU.
- **Ingen funktionel regression:** rent visuelt løft — rører ikke send/stream-logik, kun styling + animation. Eksisterende tests skal forblive grønne.

---

## 6. Test

- **Mobil (jest):** token-objekt-form (nye depth/accent/glass/timing-felter findes), komponent-render-smoke (LivenessRing/stream/MessageBubble/ToolResultCard/Composer rendrer i hver tilstand uden crash), reduced-motion-gren. **Eksisterende 71 tests forbliver grønne = funktions-bevarings-garantien** (Composer/ChatScreen-tests fanger hvis vedhæft/model-vælger/send/stop-adfærd brækker under re-styling). Tilføj smoke-tests for nye animations-komponenter, men rør ikke de funktionelle tests.
- **Visuel verifikation (det endelige bevis):** bygget mobil-APK på Bjørns S24 — han ser åndedræt/stream/glas live + bekræfter at composer-funktionerne stadig virker — iterativ finjustering (visuelt løft er iterativ pr. natur). Desk testes ikke (urørt).

---

## 7. Afgrænsning & rækkefølge i plan

Planen faser naturligt (alt i jarvis-mobile): (1) udvid `tokens.ts` + bekræft `react-native-svg`-autolink (rebuild), (2) liveness-ring + stream-indikator med svg-gradienter (kerne-følelsen, 1:1 mockup), (3) glas-boble + tool-kort, (4) notif-prik + session-overgang + composer-restyle + accent-audit + reduced-motion. Hver fase er selvstændigt testbar; APK bygges + verificeres på enheden.

**Native rebuild kræves** (react-native-svg autolinkes ind) — én gang, pipeline bevist i dag. Bump versionCode ved build.

---

*Godkendt aesthetik-retning af Bjørn 2026-06-19 (mockup). Næste: implementerings-plan via writing-plans.*
