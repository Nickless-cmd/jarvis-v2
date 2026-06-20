# Mobil chatboble (Android Bubbles API) — Design

**Dato:** 2026-06-20
**Status:** Godkendt design, klar til implementeringsplan
**Vision-reference:** `2026-06-18-jarvis-mobile-companion-v2-vision.md` §2 (Chatboble/overlay), §3 (glas-look)

Delprojekt D af de resterende mobil-features (rækkefølge: A+B ✓ → C auto-updater ✓ →
**D chatboble**). Ren klient-side (native Android + JS); ingen backend-ændringer. En
ægte Android system-boble (Bubbles API, Android 11+) lader Bjørn tale med Jarvis i en
flydende boble oven på andre apps — uden at åbne den fulde app.

## Bærende valg (afklaret med Bjørn)

1. **Fuld Bubbles API** — ægte system-boble (Conversation/Bubbles API), ikke in-app
   bobler og ikke gammeldags `SYSTEM_ALERT_WINDOW`-overlay.
2. **Både proaktiv og vedvarende:** (a) når Jarvis sender noget (eksisterende FCM-push)
   bliver det en samtale-notifikation man kan trække ud som boble; (b) en manuelt
   aktiverbar vedvarende chat-head.
3. **Boble-indhold = genbrug af app'ens chat:** boblen renderer en kompakt udgave af den
   eksisterende RN-chat (MessageList + composer + streaming) mod samme backend-session.
4. **Native-integration: Tilgang A** — `BubbleActivity extends ReactActivity` med en
   anden registreret JS-komponent (`JarvisBubble`), der deler bridge med hovedappen.
   `android/` er checket ind og bygges direkte med gradlew (ingen `expo prebuild`), så
   native filer tilføjes direkte uden config-plugin.

## Arkitektur (tre lag)

```
JS-lag (genbrug):  BubbleChat.tsx (kompakt 1-session-chat) + registerBubble
                   + bubbleModule.ts (TS-wrapper) + bubbleTrigger.ts (ren logik)
        ▲ initialProps {sessionId}      │ NativeModules
Native-lag (ny):   BubbleActivity.kt (ReactActivity, comp="JarvisBubble")
                   + BubbleModule.kt (@ReactMethod) + BubblePackage.kt
                   + AndroidManifest (resizeable/allowEmbedded/documentLaunchMode)
        ▲ samme backend-session
Backend (uændret): /chat + stream/v2 + FCM-push (server-autoritative runs →
                   boble & app deler session, synkroniserer af sig selv)
```

**Kerneidé:** Boblen er bare en anden Android-Activity der renderer en kompakt udgave af
samme RN-chat mod samme backend-session. Fordi runs er server-autoritative, holder boble
og hovedapp sig automatisk i sync uden ekstra sync-kode.

## Native Android-lag (Kotlin, pakke `dk.srvlab.jarvis.mobile`)

**`BubbleActivity.kt`** (extends `ReactActivity`):
- `getMainComponentName() = "JarvisBubble"`.
- Læser `sessionId` + `title` fra intent-extras → giver videre som `initialProps` (override
  `createReactActivityDelegate` → `getLaunchOptions`).
- Manifest-flags: `resizeableActivity="true"`, `allowEmbedded="true"`,
  `documentLaunchMode="always"`, `exported="true"`, `taskAffinity=""` (boblen er sin egen
  opgave, ikke flettet ind i hovedappen).

**`BubbleModule.kt`** (`@ReactMethod`-API mod JS):
| Metode | Gør |
|---|---|
| `isSupported(promise)` | Android ≥ 11 **og** `NotificationManager.areBubblesAllowed()` |
| `floatCurrentChat(sessionId, title)` | Person + long-lived shortcut + `MessagingStyle`-notifikation m. `BubbleMetadata(autoExpand=true, suppressNotification=true)` → boblen popper straks (manuel trigger) |
| `showConversationBubble(sessionId, title, body)` | Samme, men `autoExpand=false` → samtale-notifikation man kan trække ud (proaktiv, kaldes fra FCM) |
| `setPersistent(enabled)` | Vedvarende boble: ongoing low-priority notifikation m. bubble-metadata; `enabled=false` annullerer den |

**Fælles VVS** (privat helper `buildBubbleNotification`):
- `Person.Builder().setName("Jarvis").setIcon(ic_notification).setKey(uid).setImportant(true)`.
- `ShortcutInfoCompat` pr. session: id `bubble-<sessionId>`, `setLongLived(true)`,
  `setPerson`, `setCategories(SHORTCUT_CATEGORY_CONVERSATION)`, intent → `BubbleActivity`
  m. extras. `ShortcutManagerCompat.pushDynamicShortcut`.
- Notifikationskanal `jarvis-bubbles` m. `setAllowBubbles(true)` (API 30).
- `PendingIntent` → `BubbleActivity` (korrekt mutable-flag for API 31+).
- Den vedvarende boble bruger den aktive session, eller `bubble-default` hvis ingen.

**`BubblePackage.kt`** registrerer `BubbleModule`; tilføjes i `MainApplication.kt`'s
package-liste.

## JS-lag (genbrug)

**`src/bubble/BubbleChat.tsx`** — kompakt 1-session-chat:
- Modtager `sessionId` + `title` via `initialProps`.
- Monterer `AuthProvider` (auth fra `expo-secure-store` via `loadAuthConfig`) + en
  enkelt-session-chat: genbruger `MessageList`, composeren og `streamClient` direkte —
  ingen SidePanel/Save Rail/presence.
- Henter beskeder via `apiClient` (`GET /chat/sessions/{id}`) og følger streamen via samme
  `streamClient` som hovedappen.
- Chrome: titel-bjælke (Jarvis-navn + session-titel), beskedliste, composer. Genbruger
  `tokens`-temaet.

**`src/bubble/registerBubble.tsx`**: `AppRegistry.registerComponent('JarvisBubble', () =>
BubbleChatRoot)` — kaldes fra `index.js` ved siden af `registerRootComponent(App)`.

**`src/lib/bubbleModule.ts`** — tynd TS-wrapper over `NativeModules.BubbleModule`:
`isSupported()`, `floatCurrentChat(sessionId, title)`, `showConversationBubble(sessionId,
title, body)`, `setPersistent(enabled)`. Guard: mangler modulet (iOS/gammel build) →
no-op/false.

**`src/lib/bubbleTrigger.ts`** — ren, testbar logik: `shouldFloatOnPush(data): boolean` —
true for `answer_ready`/`reminder`, false for presence/andet/malformet.

**Integration med eksisterende kode:**
- **Proaktiv:** i `index.js`-baggrundshandler + `push.ts`-forgrund, efter `display(config,
  data)`: hvis `shouldFloatOnPush(data)` → `bubbleModule.showConversationBubble(...)`.
- **Manuel "flyt denne chat":** boble-knap i `SidePanel`-headeren →
  `bubbleModule.floatCurrentChat(activeSessionId, title)`. Skjult hvis `isSupported()` false.
- **Vedvarende boble:** toggle i Settings → `bubbleModule.setPersistent(on)`.

## Dataflow

1. **Proaktiv:** Jarvis svarer → FCM-push → `display()` viser notifikation + (hvis
   `shouldFloatOnPush`) `showConversationBubble` gør den til floatbar samtale-boble. Tap
   boble → `BubbleActivity` → `BubbleChat(sessionId)` → kompakt chat på samme session.
2. **Manuel:** "flyt denne chat" → `floatCurrentChat(activeSessionId)` → boble popper
   straks (autoExpand).
3. **Vedvarende:** toggle on → ongoing bubble-notifikation → chat-head altid tilgængelig.
4. Skriv i boble → samme `/chat`+stream → vises i hovedappen (server-autoritativ session).

## Fejlhåndtering / edge cases

- **Android < 11:** `isSupported()` false → boble-knap + persistent-toggle skjules,
  FCM-float springes over. Appen uændret.
- **Bobler slået fra:** `showConversationBubble` degraderer til almindelig
  samtale-notifikation (Android håndterer selv; intet crash).
- **Ingen aktiv session ved persistent-toggle:** brug `bubble-default`-shortcut; åbner
  nyeste session ved udvidelse.
- **Auth mangler i boble-Activity:** `BubbleChat` viser "Åbn appen og log ind" i stedet for
  tom chat.
- **Dobbelt-bridge (Tilgang A):** `taskAffinity=""` + egen Activity isolerer
  boble-navigation fra hovedappen.

## Testplan

- **jest:** `bubbleTrigger.test.ts` (answer_ready→true, reminder→true, presence/andet→false,
  malformet→false); `bubbleModule.test.ts` (manglende native-modul → no-op/false). De
  eksisterende ~104 jest-tests forbliver grønne.
- **`tsc --noEmit`** rent.
- **Native + Bubbles-flow:** manuelt på S24 — ingen meningsfuld enhedstest for selve
  OS-boblen. Verificér: (1) Jarvis-besked → floatbar samtale-boble; (2) "flyt denne chat" →
  boble popper straks; (3) skriv i boble → vises i app; (4) persistent-toggle → vedvarende
  chat-head.

## Filer

**Native (ny, `android/app/src/main/java/dk/srvlab/jarvis/mobile/`):** `BubbleActivity.kt`,
`BubbleModule.kt`, `BubblePackage.kt`.
**Native (modificeret):** `MainApplication.kt` (registrér package), `AndroidManifest.xml`
(BubbleActivity-entry).
**JS (ny):** `src/bubble/BubbleChat.tsx`, `src/bubble/registerBubble.tsx`,
`src/lib/bubbleModule.ts`, `src/lib/bubbleTrigger.ts` (+ `bubbleTrigger.test.ts`,
`bubbleModule.test.ts`).
**JS (modificeret):** `index.js` (registrér 'JarvisBubble' + float-på-FCM), `src/lib/push.ts`
(forgrund-float), `src/components/SidePanel.tsx` (float-knap), Settings (persistent-toggle).

## Ikke i scope (YAGNI)

- iOS (Bubbles er Android-only).
- Per-besked rige bobler ud over chatten.
- Boble for flere samtidige samtaler ud over det Android selv grupperer.
- Note-backlog-punkter 2/3/5 (kamera/composer/direct-reply) — separate features efter D.
