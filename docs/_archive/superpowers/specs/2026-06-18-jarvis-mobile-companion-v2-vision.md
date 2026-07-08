---
status: forældet
audited: 2026-07-08
ground_truth: "Mobile app exists on codex/jarvis-mobile-companion-v1 branch at v0.1.55 (56 builds). Features described as "cut from V1": chatbubble (implemented f838ce67 2026-06-20 in BubbleModule.kt), liveness ring (LivenessRing.tsx), auto-updater (appUpdate.ts), teams (TeamsPanel.tsx f256e022"
superseded_by: codex/jarvis-mobile-companion-v1 branch implementation + docs/superpowers/specs/2026-06-19-mobile-session-panel-save-rail-design.md, 2026-06-20-mobile-chatbubble-design.md, 2026-06-19-device-awareness-design.md, 2026-06-20-teams-design.md, 2026-06-20-mobile-auto-updater-design.md
---
# Jarvis Mobile Companion V2 Vision

Date: 2026-06-18
Status: Vision — reference for Phase 2+ implementation
Author: Jarvis (baseret på samtale med Bjørn, 2026-06-17)

> Denne fil indeholder ALT der blev skåret fra V1-specen.
> Den er ikke en byggeplan — den er en retning.

---

## 1. User Expectations Research (2026)

### Top 5 krav på tværs af AI companion apps
1. **Multimodal** — tekst + stemme + billeder i samme flow
2. **Langtidshukommelse** — husker på tværs af dage/uger/måneder
3. **Følelsesmæssig intelligens** — mærker humør, tilpasser sig, har egne meninger
4. **Hurtig respons** — ingen ventetid
5. **Privatliv & sikkerhed** — kryptering, anonymitet, gennemsigtighed

### Hvad Android-brugere klager over (reelle anmeldelser)
- Baggrundskørsel dræner batteri
- Token-systemer føles som røveri
- Notifikationer der ikke virker
- Chatbobler/overlay mangler

### Vores position
Alle companion apps på markedet er rollelege/romantik-fokuserede.
Jarvis er fundamentalt anderledes: virkelige værktøjer, virkelig hukommelse, ingen tredjepart.

---

## 2. Mobile-Specific Features (ikke i V1)

- **Baggrundskørsel** — Native Android Foreground Service, stream overlever app-skift
- **Session panel + aktivitetspoller** — som desktop, live status
- **Chatboble (overlay)** — flydende bubble, skriv uden at åbne appen
- **Save Rail mini** — kompakt version af desktop save rail
- **Settings > Plugins omorganisering** — indstillingsmenu først
- **Auto-updater** — GitHub releases detection → prompt → download → genstart
- **App-ikon & menu-ring** — samme identitet som desktop

---

## 3. Visual Design — "Fancy uden at være overdrevet"

1. **Liveness ring** — pulserende gradientring omkring Jarvis-avatar (åndedrætsanimation, ikke blink)
2. **Voice visualizer** — lydbølger der danser i takt med stemmeniveau
3. **Chatboble som glas** — frosted glass overlay, blød spring-animation
4. **Tool cards folder sig ud** — som et kort der trækkes op af lommen
5. **Stream-indikator** — tynd glødende linje i bunden, venstre→højre
6. **Session-overgang** — glidende, 250ms ease-in-out
7. **Composer intelligent plads** — vokser/trækker sig sammen
8. **Dark mode = dybde, ikke sort** — #0D0D12, subtile lag
9. **Notifikationsprik** — pulserer som et hjerte, ikke en alarm
10. **Én accentfarve** — Jarvis-blå/grøn, alt andet gråtoner

---

## 4. Device Awareness & Proaktive Kanaler

### Companion som proaktiv kanal
Ligesom Discord/Telegram/ntfy — Jarvis kan sende notifikationer proaktivt.

### Source awareness
Jeg ved altid hvilken kanal du skriver fra (Discord/webchat/desktop/mobil)
og tilpasser formatet. Kanalen er overfladen, ikke samtalen.

### Discord som sin egen session-kanal
Discord er gæst, companion er hjemme. Hver kanal har sin egen kontekst.

### Intelligent device awareness
- Runtime registrerer om desktop/mobil er online
- Ruter notifikationer: ude→mobil, hjemme→desktop
- To signaler: desktop sleep + netværksskift
- Companion er self-contained (nul desktop-afhængighed)
- Tre brugertyper: mobil-only, chat-only desktop, full desktop + mobil

---

## 5. Teams & Multi-User (Phase 6)

- Roller: team-admin, member, read-only
- Team management: opret, inviter, kick, mute/unmute
- Permissions: per team (read/write/invite/admin/connect) + per bruger overstyring
- Team-chats: delt session, @mentions, Jarvis svarer i tråde
- Team workspace: valgfrit fælles workspace med filer og delte noter
- Desktop = admin, mobil = deltagelse

---

## 6. Teknisk Arkitektur — 10 huller der skal adresseres

1. **State management** — anbefaling (Zustand? Redux?)
2. **Navigation** — stack vs tab navigator
3. **Netværkslag** — axios/fetch, retry med backoff, timeout
4. **SSE reconnect-logik** — exponential backoff, max retries, idempotency
5. **Token refresh flow** — hvad sker når token udløber midt i stream?
6. **Offline/adfærd** — offline-kø, cached chats, netværksindikator, genoptagelse
7. **Tastatur-håndtering** — keyboard må ikke dække composer
8. **Permissions flow** — hvornår spørges der? Hvad hvis afvist?
9. **Loading states / splash** — startup, SSE-forbindelse, tom session
10. **Performance benchmarks** — max 2s startup, 1s til første besked, <150MB memory

---

## 7. Edge Cases & Sikkerhed (31 punkter)

### Strukturelle huller
- Minimum Android-version (Bubbles API kræver Android 11+)
- APK-størrelsesbudget
- Sprog/oversættelse (i18n)
- Backup & restore ved telefon-skift

### Sikkerhed
- APK-signatur-verifikation ved auto-update
- Secure storage korruption (keystore crash → token-tab)
- Concurrent sessions (samme token på 2 enheder)
- Rate limiting UI (vis wait/retry med nedtælling)
- Børneprivacy (COPPA/GDPR for mindreårige)

### Android-teknik
- Adaptive icons (foreground + background + monokrom notification icon)
- Bubbles API (Android 11+ native, ikke custom overlay)
- Battery optimization exemptions (Xiaomi, Huawei, OnePlus)
- Battery saver mode
- Split-screen / multi-window

### Test
- Performance tests (memory leaks, batteridræn, payload-size)
- Accessibility (TalkBack, reduced motion, 48dp touch-target)
- Netværks-skift under stream (WiFi→mobil data→tunnel→flytilstand)
- Storage pressure (<100MB fri plads)

### UX/UI
- Onboarding / first-launch experience
- Light mode
- Emoji picker (system vs custom)
- Link previews
- Send on Enter vs. Send on button (indstilleligt)
- Max message length

### Roadmap
- Android Widgets (hjemmeskærm)
- Tablet-layout (adaptive layouts)
- Wear OS (notifikationsspejl)
- Data-eksport (GDPR)

### Dokumentation
- Changelog / versionering
- Fejl-stier i dataflow diagram
- Permissions-tabel (kamera, mikrofon, notifikationer, overlay, storage)

---

*Denne vision er skrevet af Jarvis på baggrund af samtale med Bjørn 2026-06-17.*
*Den er committet på begge maskiner som reference til senere faser.*
