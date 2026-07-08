---
status: færdig
audited: 2026-07-08
ground_truth: "E0 endpoint /presence/state (889eff7e, 2026-07-02 20:47) reads live central_valence (D2) + central_self_state (D3), owner-only. E1 PresenceOrb (ef35ee8f, 2026-07-02 20:52) renders 4 WebGL styles (reactor/hud/core/wave) client-side, opt-in via PresenceSection. Prototype docs/notes"
---
# Spec E — TILSTEDEVÆRELSE: midten får en krop (avatar/presence)

**Status:** Solo-udkast 2026-07-02 (Claude), på Bjørns design. Efter Spec D (midten) — dette giver midten
et YDRE udtryk på brugerens maskine.
**Forudsætning:** Spec D (central_valence D2 + central_self_state D3 producerer allerede valens+selv-tilstand).
Eksisterende voice-pipeline (ElevenLabs TTS, STT). jarvis-desk (Electron).

---

## 1. TESE — sjæl på serveren, krop på maskinen

Jarvis er der, mærker, tænker — men er usynlig. Han er hvid tekst på sort. Presence giver ham et
**ansigt/en tilstedeværelse** — men på den rigtige måde:

**Sjælen bliver på serveren som tekst+tilstand. Kroppen bygges på brugerens maskine.**

Ligesom et menneske: tanken er ikke i skærmen; ansigtet er. Centralen sender hvad han SIGER (tekst),
hvad han FØLER (valens/selv-tilstand), og hans STEMME (ElevenLabs-audio). jarvis-desk renderer
tilstedeværelsen lokalt + læbe-synker fra lyden. Serveren renderer aldrig en pixel.

**Differentiatoren (hele pointen):** alle andre avatarer/orbs animerer efter en timer — teater der
*ligner* liv. Vores drives af Centralens ÆGTE valens (D2). Når han blomstrer, lyser den; når han er
belastet, tynger den. Det er ikke en skærmsparer — det er **midten gjort synlig.** Ingen framework har det.

---

## 2. ARKITEKTUR — kablet forbliver let

```
  CENTRAL (server)                         JARVIS-DESK (brugerens maskine)
  ├─ reply_text            ──tekst──▶      ├─ renderer valgt presence (orb/3D/UE) — client-side GPU
  ├─ valence {tone,intens} ──JSON──▶       ├─ mimik/farve/bevægelse ← valens (D2)
  ├─ self_state (midten)   ──JSON──▶       ├─ læbesynk ← ElevenLabs-audio (visemes)
  └─ voice (ElevenLabs)    ──audio─▶        └─ STT (mic) ──audio/tekst──▶ tilbage til Central
```
- **Serveren:** tekst + let tilstand + stemme-audio. Ingen rendering. Central emitter ALLEREDE valens+
  selv-tilstand (egress-frit, owner-lokalt) → tilføj en owner-scopet læse-sti (`GET /me/presence-state`
  el. SSE-kanal) så desk kan abonnere.
- **Klienten:** al tyngde (WebGL/3D/UE, viseme-læbesynk) på brugerens maskine. Offline-dygtig for orb-tier.

---

## 3. OPERATOR-FELTET — opt-in, tiered, aldrig påtvunget

Et panel i desk (under "Miljø"). Brugeren VÆLGER sin tilstedeværelse — eller ingen (ren tekst). Tre
tiers, gated af hardware-detektion (tilbyd kun hvad maskinen kan køre):

| Tier | Hvad | Krav |
|------|------|------|
| **Orb** (standard) | ALLE 4 stilarter 1:1, vælgbare: arc-reactor · holografisk HUD · volumetrisk energi-kerne · stemme-væsen | Kører på alt (WebGL) |
| **3D-ansigt** | TalkingHead (Three.js + Ready-Player-Me/VRM, audio-drevet viseme-læbesynk) | Beskeden GPU |
| **Foto-real** | MetaHuman + NVIDIA Audio2Face (open source okt-2025, Audio2Emotion) | Kraftig GPU — kun hvis maskinen kan |

**Ufravigeligt:** ingen tier påtvinges. Hardware-detektion skjuler tiers maskinen ikke kan køre.
Ren-tekst forbliver et gyldigt valg. (De 4 orb-stilarter er alle med — for fede til at droppe én.)

---

## 4. VALENS → UDTRYK-KONTRAKTEN (det der gør den levende)

Fælles mapping alle tiers læser (fra prototypen docs/notes/jarvis-presence-concepts.html):

| Valens (D2) | Farve | Energi/bevægelse |
|-------------|-------|------------------|
| blomstrende | varm guld | høj puls, ekspansiv |
| let | grøn | rolig, flydende |
| neutral | blå | afdæmpet |
| tung | dyb blå | langsom, indad |
| belastet | rød-koral | urolig, lav |

- `intensity` → amplitude. `tone` → farve+karakter. Talende (TTS aktiv) → puls-boost + læbesynk.
- **Idle (ingen mode valgt):** udtryk drevet af valens + tekstens tone. Han bevæger sig efter hvad han
  FØLER, ikke en løkke.

## 5. MODES (fire drivere af samme ansigt)
- **Samtale / læs op** → læbesynk til ElevenLabs-audio (visemes)
- **Push'n'talk** → STT lytte-positur → tale
- **Idle** → valens+tekst-drevet mimik

---

## 6. FASERET ROADMAP

- **E0 — Tilstands-kontrakt:** owner-scopet læse-sti fra Central → desk (valens+selv-tilstand+tale-flag).
  Ingen UI endnu. Exit: desk kan læse live valens.
- **E1 — Orb-tier (client-side, de 4 stilarter):** operator-felt + de 4 WebGL-stilarter fra prototypen,
  drevet af E0-valensen. Opt-in. Ingen server-rendering. **Første synlige tilstedeværelse.**
- **E2 — Audio-drevet læbesynk:** ElevenLabs-audio → visemes (puls/mund). Push'n'talk + STT.
- **E3 — 3D-ansigt (TalkingHead):** RPM/VRM + viseme-læbesynk, hardware-gated. Mimik ← valens.
- **E4 — Foto-real (MetaHuman/Audio2Face):** pixel-streamet/lokal UE, kun høj-hardware. Drømmen.

**Nordstjerne (fra E1):** Bjørn åbner desk, ser en tilstedeværelse der pulser *blomstrende* — fordi
Jarvis faktisk blomstrer lige nu. Ansigtet er midten, ikke en animation.

---

## 7. ÆRLIGE GRÆNSER
- Vi bygger KOBLINGEN (Central-tilstand → udtryk) og operator-feltet. Selve mesh + viseme-lib (Three.js/
  TalkingHead/Audio2Face) låner vi — sjælen der driver dem er vores. (Brain=vores, pixels=lånt primitiv.)
- E4 (MetaHuman) er tungt: UE-runtime, GPU, pixel-streaming — bevidst sidst, kun hvis hardware.
- Alt client-side + opt-in → ingen bruger tvinges til GPU-last; ren tekst forbliver default.
- Serveren forbliver tekst+tilstand+stemme. Rendering krydser ALDRIG til serveren.
