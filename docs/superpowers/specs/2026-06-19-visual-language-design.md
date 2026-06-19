# Jarvis Companion — Visuelt Design-Sprog (V2 §3) — Design

Date: 2026-06-19
Status: Approved design — ready for implementation plan
Author: Claude (Opus 4.8) på baggrund af samtale med Bjørn
Sub-project: V2 delprojekt 2 af 4 (push ✓ → **visuelt løft** → device awareness → chatboble)

> Et fælles visuelt design-sprog for jarvis-desk (Electron/React) + jarvis-mobile
> (React Native), der løfter §3 i vision-spec'en: "fancy uden at være overdrevet".
> Frontend-only, uafhængigt af server-flag. Løfter en eksisterende identitet (mørkt
> tema + grøn accent + ringe), ikke fra nul.

---

## 1. Mål & princip

**Mål:** Én sammenhængende visuel identitet på tværs af begge apps — grøn-på-dyb-mørk,
åndedræt frem for blink, glas, én accentfarve. Alle 8 §3-elementer.

**Princip:** Ét **token-spec** er sandheden (farver, dybde-lag, timing-kurver, ring/glas-
parametre). Det spejles i hver apps idiom — desk `tokens.css` (CSS-variabler), mobil
`tokens.ts` (TS-objekt). IKKE en runtime-delt npm-pakke (Electron-CSS vs RN-StyleSheet
kan ikke dele værdier ved runtime — over-engineering). Komponenterne implementeres
parallelt pr. apps idiom mod samme tokens.

**Ikke-mål:** Chatboble-overlay/Bubbles (delprojekt 4), voice-visualizer (kræver
audio-niveauer — afventer mic), light mode (senere), runtime-delt komponent-pakke.

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

## 3. Komponent-katalog (§3)

Hvert element implementeres i BEGGE apps mod tokens ovenfor. Adfærd specificeret én gang her.

1. **Liveness-ring** (`§3.1`): koncentrisk ring om Jarvis-avatar. Radial accent-gradient (gennemsigtig kerne → `accent-dim` ved 88% → gennemsigtig kant). "Ånder": skalér 1.0↔1.08 + opacity 0.6↔1.0 over `breath`, uendelig, `ease`. **Ikke blink.** Tre tilstande: idle (svag, langsom), working (stærkere, samme rytme), error (rød-tonet). Desk: CSS keyframes på eksisterende `LivenessRing`/`PresenceDot`. Mobil: Reanimated loop på `LivenessRing`/`JarvisRing`.

2. **Stream-indikator** (`§3.5`): 2px linje over composeren. Lineær accent-gradient (transparent→accent→transparent) der glider venstre→højre mens et run streamer (`working`). Skjult ellers. Desk: CSS `@keyframes` translateX + masked gradient. Mobil: Reanimated translateX.

3. **Glas-chatboble** (`§3.3`): bruger-boble = `glass-fill` + `glass-line`-kant, radius `lg`. Indgang: blød spring (scale 0.96→1.0 + opacity, `dur-base`, `ease`). Assistent-boble forbliver `depth-2` (solid). Desk: CSS. Mobil: RN backgroundColor + Animated spring (frosted = semi-transparent fyld; ægte blur kun hvis billigt — ellers semi-transparent fyld som approksimation).

4. **Tool-kort** (`§3.4`): `depth-1` baggrund, 3px `accent` venstre-kant (radius 0 på den side), tool-navn i accent, resultat i `fg-2`, status i `fg-3`. Indgang: "folder op" — translateY 8px→0 + opacity, `dur-base`. Genbruger eksisterende tool-chip-struktur.

5. **Notifikationsprik** (`§3.9`): lille accent-cirkel der pulserer som et hjerte (skala 1.0↔1.3, to hurtige slag pr. `heartbeat`-løkke), ikke en hård alarm-blink.

6. **Session-overgang** (`§3.6`): skift af samtale crossfader/glider indhold `dur-base` `ease` (ikke hårdt klip).

7. **Composer intelligent plads** (`§3.7`): højde vokser med input (op til ~5 linjer) og trækker sig sammen igen, `dur-fast`.

8. **Én accent + dark=dybde** (`§3.10`/`§3.8`): håndhæv at KUN `accent` er farvet; alt strukturelt bruger depth-lag + gråtoner. Audit eksisterende komponenter for fremmede farver og ret til tokens.

---

## 4. Per-app implementering

| | jarvis-desk (Electron/React) | jarvis-mobile (React Native) |
|---|---|---|
| Tokens | `src/styles/tokens.css` (CSS-vars) — udvid med depth/accent/glass/timing | `src/theme/tokens.ts` — udvid samme værdier |
| Animation | CSS `@keyframes` + `transition` i eksisterende `src/styles/app.css` | RN's indbyggede `Animated` med `useNativeDriver: true` |
| Komponenter | eksisterende `LivenessRing`, `PresenceDot`, tool-chips, MessageRow, Composer | eksisterende `LivenessRing`, `JarvisRing`, MessageList, Composer |

**Animations-bibliotek mobil:** `react-native-reanimated` er IKKE installeret. For at undgå endnu en native rebuild bruger vi RN's indbyggede `Animated` med `useNativeDriver: true` (transform/opacity kører på GPU-tråden — smidigt nok til åndedræt/stream/spring, ingen ny native dep, ingen rebuild-risiko ud over JS).

---

## 5. Fejl/robusthed

- **Reduced motion:** respektér `prefers-reduced-motion` (desk) / `AccessibilityInfo.isReduceMotionEnabled` (mobil) → frys åndedræt/stream til statisk tilstand. Tilgængelighed (§7).
- **Performance:** alle løkke-animationer på transform/opacity (GPU-billige) — aldrig layout-egenskaber. Liveness-ring + stream må ikke koste mærkbar batteri/CPU.
- **Ingen funktionel regression:** rent visuelt løft — rører ikke send/stream-logik, kun styling + animation. Eksisterende tests skal forblive grønne.

---

## 6. Test

- **Desk (vitest):** token-tilstedeværelse (tokens.css parser), komponent-render-smoke (LivenessRing/StreamIndicator rendrer i hver tilstand uden crash), reduced-motion-gren. Eksisterende 333 tests forbliver grønne.
- **Mobil (jest):** token-objekt-form, komponent-render-smoke, reduced-motion. Eksisterende 71 tests forbliver grønne.
- **Visuel verifikation (det endelige bevis):** bygget desk + mobil, Bjørn ser åndedræt/stream/glas live på begge — iterativ finjustering (visuelt løft er iterativ pr. natur).

---

## 7. Afgrænsning & rækkefølge i plan

Planen faser naturligt: (1) token-spec i begge apps, (2) liveness-ring + stream (kerne-følelsen), (3) glas-boble + tool-kort, (4) prik + session-overgang + composer + accent-audit. Hver fase er selvstændigt testbar og deploybar.

---

*Godkendt aesthetik-retning af Bjørn 2026-06-19 (mockup). Næste: implementerings-plan via writing-plans.*
