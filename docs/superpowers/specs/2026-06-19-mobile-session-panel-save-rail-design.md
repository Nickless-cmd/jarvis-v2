# Mobil: Session-panel live-status + Save Rail mini — Design

**Dato:** 2026-06-19
**Status:** Godkendt design, klar til implementeringsplan
**Vision-reference:** `2026-06-18-jarvis-mobile-companion-v2-vision.md` §2 (Session panel + aktivitetspoller, Save Rail mini)

Del-projekt A+B af de resterende mobil-features (rækkefølge A+B → C auto-updater → D
chatboble; E foreground service descoped pga. server-autoritative runs). KUN mobil
(`.worktrees/jarvis-mobile-companion-v1/apps/mobile`, gren codex/jarvis-mobile-companion-v1).
Ingen backend-ændringer.

## Mål

1. **Session-panel live-status:** I det eksisterende slide-in `SidePanel` viser hver
   session (a) en pulserende prik når den LIGE NU har et aktivt run ("Jarvis arbejder
   her"), og (b) en ulæst-badge når der er nye beskeder siden du sidst åbnede den.
2. **Save Rail mini:** Tommel-venlige flydende knapper i chat-skærmen til at hoppe
   (top / bund / forrige bruger-besked / næste bruger-besked) + en tynd scrubber ved
   hold-og-træk.

## Tilgang (valgt: klient-side, genbrugs-tung)

Alt klient-side. Arbejder-status fra det eksisterende `GET /chat/active-runs`
(`getActiveRuns` findes allerede i `apiClient.ts`). Ulæst spores klient-side i
`expo-secure-store` (ingen backend). Hop bygger på at `MessageList` allerede bruger
`FlatList` (kan `scrollToIndex`/`scrollToOffset`). Ren logik isoleres i testbare
moduler; UI-komponenter holdes tynde.

Fravalgt: server-sporet ulæst (kræver nyt endpoint + state — udskudt); minimal uden
ulæst/scrubber (mindre værdi end ønsket).

## A — Session-panel live-status

### Datakilder
- **Arbejder:** `getActiveRuns(config) → string[]` (session_id'er med aktivt run lige nu).
  ChatScreen poller hvert ~2,5s MENS `SidePanel` er åbent (ingen poll når lukket).
- **Ulæst:** sammenlign serverens `session.message_count` med et gemt "sidst-set"-tal
  pr. session. Sessions kommer allerede fra `SessionContext` (med `message_count`).

### Komponenter
- `lib/lastSeen.ts` (NY): persistent map `sessionId → sidst-set message_count`,
  gemt som ÉN JSON-værdi i secure-store under nøglen `jarvis.lastSeen`.
  - `loadLastSeen(): Promise<Record<string, number>>`
  - `markSeen(sessionId: string, count: number): Promise<void>` — læs map, sæt, gem.
  - Best-effort: fejl swallow'es (ulæst er ikke kritisk).
- `lib/sessionStatus.ts` (NY, REN — ingen I/O):
  - `isWorking(sessionId: string, activeRunIds: string[]): boolean`
  - `computeUnread(sessions: ChatSession[], lastSeen: Record<string, number>, activeId: string | null): Record<string, boolean>`
    — en session er ulæst hvis `message_count > (lastSeen[id] ?? 0)` OG `id !== activeId`.
- `SidePanel.tsx` (MOD): nye props `workingIds: string[]` + `unreadIds: Record<string, boolean>`.
  Pr. session-række: hvis `isWorking` → `<HeartbeatDot>` (accent, pulserer); ellers hvis
  ulæst → lille accent-prik (8px). Begge i højre side af rækken. Ingen ændring af
  eksisterende søg/datoer/ny-samtale.
- `ChatScreen.tsx` (MOD):
  - Ejer `activeRunIds` (poll mens `panelOpen`) + `lastSeen` (load ved mount).
  - Beregner `unreadIds = computeUnread(sessions, lastSeen, activeId)`.
  - Ved session-valg (eksisterende `onSelectSession`): kald `markSeen(id, message_count)`
    + opdater lokal `lastSeen`-state, så badgen forsvinder med det samme.
  - **Bonus-prik:** hvis `workingIds.length > 0` ELLER nogen ulæst → vis en lille
    accent-prik på presence-ringen (panel-åbneren), så man ved der er noget i panelet.

### Edge cases
- Ny session uden gemt sidst-set → `lastSeen[id]` undefined → `?? 0`; `message_count 0`
  → ikke ulæst. Korrekt.
- Den aktive session er aldrig ulæst (man kigger på den).
- secure-store-fejl → `loadLastSeen` returnerer `{}` → ingen ulæst (degraderer pænt).
- Panel lukket → ingen active-runs-poll (spar batteri); bonus-prik på ringen opdateres
  på næste sessions-refresh (ulæst) — arbejder-prikken kræver panel åbent (acceptabelt).

## B — Save Rail mini

### Logik
- `lib/messageNav.ts` (NY, REN):
  - `userMessageIndexes(messages: ChatMessage[]): number[]` — indekser hvor `role === 'user'`.
  - `prevUserIndex(indexes: number[], current: number): number | null` — største index < current.
  - `nextUserIndex(indexes: number[], current: number): number | null` — mindste index > current.

### Komponenter
- `MessageList.tsx` (MOD): tag en valgfri `listRef?: React.RefObject<FlatList>` og sæt
  den på `<FlatList ref={listRef}>`. (Bevarer al eksisterende rendering.) Aktivér
  `onViewableItemsChanged` videresendt via prop `onVisibleIndexChange?: (index: number) => void`.
- `components/SaveRail.tsx` (NY): flydende kolonne ved højre kant (over composeren),
  tommel-venlige runde knapper:
  - ⤒ hop til top, ⤓ hop til bund
  - ▲ forrige bruger-besked, ▼ næste bruger-besked
  - Tynd scrubber-track til højre: `onScrub(fraction: number)` ved `PanResponder`-træk.
  Props: `onJumpTop`, `onJumpBottom`, `onPrevUser`, `onNextUser`, `onScrub`, `visible`.
  Skjules når der er <2 beskeder. Reduced-motion respekteres (ingen pulse).
- `ChatScreen.tsx` (MOD): holder `listRef` + `visibleIndex` (fra `onVisibleIndexChange`),
  renderer `<SaveRail>` med handlers:
  - `onJumpTop` → `listRef.scrollToOffset({offset:0})`
  - `onJumpBottom` → `listRef.scrollToEnd()`
  - `onPrevUser/onNextUser` → find via `messageNav` ud fra `visibleIndex` →
    `scrollToIndex({index})` (med `viewPosition: 0`)
  - `onScrub(f)` → `scrollToOffset({offset: f * contentHeight})` (contentHeight fra
    `onContentSizeChange`)

### Edge cases
- `scrollToIndex` kan fejle hvis index ikke er målt → fang `onScrollToIndexFailed` og
  fald tilbage til `scrollToOffset(estimeret)`.
- Ingen/én besked → SaveRail skjult.
- Ingen bruger-besked før/efter → den knap er disabled (nedtonet).

## Testplan (jest)

- `sessionStatus.test.ts`: `isWorking` (med/uden match), `computeUnread`
  (ulæst-tærskel, aktiv-session-undtagelse, manglende lastSeen).
- `messageNav.test.ts`: `userMessageIndexes`, `prevUserIndex`/`nextUserIndex`
  (grænser: ingen før/efter, current midt imellem).
- `lastSeen.test.ts`: `markSeen` + `loadLastSeen` round-trip med mocket secure-store;
  fejl → `{}`.
- UI: tynde komponenter; eksisterende SidePanel/ChatScreen-tests skal forblive grønne
  (tilføj mocks for `getActiveRuns`/secure-store hvor nødvendigt).

## Filer

**Nye:** `src/lib/lastSeen.ts`, `src/lib/sessionStatus.ts`, `src/lib/messageNav.ts`,
`src/components/SaveRail.tsx` (+ `*.test.ts(x)`).
**Modificerede:** `src/components/SidePanel.tsx`, `src/components/MessageList.tsx`,
`src/screens/ChatScreen.tsx`. (Ingen backend.)

## Ikke i scope (YAGNI)
- Server-sporet ulæst på tværs af enheder (udskudt).
- Tynd kant-rail med markør pr. besked (valgte hop-knapper i stedet).
- Working-step-tekst / sidst-aktiv-tidspunkt i panelet (kun arbejder-prik + ulæst).
