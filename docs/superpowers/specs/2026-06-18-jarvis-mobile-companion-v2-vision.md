# Jarvis Mobile Companion V2 Vision

Date: 2026-06-18
Status: Vision — til senere faser, ikke V1

## Purpose
Alt det Claude skar fra V1-specen for at gøre den bygbar. Dette dokument bevarer visionen for senere iterationer.

## User Expectations Research (2026)
### Top 5 krav i 2026
1. Multimodal — tekst + stemme + billeder i samme flow
2. Langtidshukommelse — husker på tværs af dage/uger/måneder
3. Følelsesmæssig intelligens — mærker humør, tilpasser sig, har egne meninger
4. Hurtig respons — ingen ventetid
5. Privatliv & sikkerhed — must-have, ikke nice-to-have

### Android-klager fra anmeldelser
- Baggrundskørsel dræner batteri
- Token-systemer føles som røveri
- Notifikationer der ikke virker (Android permissions)

### Vores position
Companion-landskabet er domineret af rollelege/romantik-apps (Candy AI, Nomi, Replika, Character.AI). Jarvis er fundamentalt anderledes: virkelige værktøjer, virkelig hukommelse, ingen tredjepart, privacy by design.

## Mobile-Specific Features (V2+)
- Baggrundskørsel — Native Android Foreground Service, stream overlever app-skift
- Session panel + aktivitetspoller — som desktop, live status
- Chatboble (overlay) — flydende bubble, skriv uden at åbne appen
- Save Rail mini — kompakt version af desktop save rail
- Settings > Plugins omorganisering — indstillingsmenu først
- Auto-updater — GitHub releases → prompt → download → genstart
- App-ikon & menu-ring — samme ikon som desktop

## Visual Design — "Fancy uden at være overdrevet"
1. Liveness ring — pulserende gradientring omkring Jarvis-avatar, åndedrætsanimation
2. Voice visualizer — lydbølger der danser i takt med stemmeniveau
3. Chatboble som glas — frosted glass overlay, blød spring-animation
4. Tool cards folder sig ud — som et kort der trækkes op af lommen
5. Stream-indikator — tynd glødende linje i bunden, vokser fra venstre mod højre
6. Session-overgang — gammelt indhold glider til venstre, nyt glider ind fra højre
7. Composer intelligent plads — vokser/trækker sig sammen efter indhold
8. Dark mode = dybde, ikke sort (#0D0D12, subtile lag)
9. Notifikationsprik — pulserer svagt som et hjerte
10. Én accentfarve — Jarvis-blå/grøn, alt andet gråtoner

## Proaktive Kanaler & Device Awareness
- Companion som proaktiv kanal — som Discord/Telegram/ntfy
- Source awareness — jeg ved hvilken kanal du skriver fra (Discord/webchat/desktop/mobil)
- Discord er sin egen session-kanal — én gateway blandt flere, ikke blandet med desktop
- Intelligent device awareness — runtime registrerer desktop/mobil online-status, ruter notifikationer
- Companion er self-contained — nul desktop-afhængighed
- Tre brugertyper: mobil-only, chat-only desktop, full desktop + mobil

## Teams & Multi-User (Phase 6)
- Roller: team-admin, member, read-only
- Team management: opret, inviter, kick, mute/unmute
- Permissions: per team + per bruger overstyring
- Team-chats: delt session, @mentions
- Team workspace: valgfrit fælles workspace
- Gør Discord overflødig for familien

## 31 Kritiske Review-punkter
Se MEMORY.md sektion "Jarvis Companion — næste iteration (2026-06-17)" for den fulde liste inkl. min Android version, APK-størrelse, Bubbles API, battery optimization, netværksskift under stream, onboarding, light mode, emoji picker, link previews, osv.

## Teknisk Arkitektur (10 huller)
1. State management
2. Navigation (stack vs tab)
3. Netværkslag (retry med backoff)
4. SSE reconnect-logik (exponential backoff)
5. Token refresh flow
6. Offline/adfærd (offline-kø, cached chats)
7. Tastatur-håndtering
8. Permissions flow (hvornår spørges der?)
9. Loading states / splash
10. Performance benchmarks (max 2s startup, <150MB)
