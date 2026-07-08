---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Mobil Session-panel live-status + Save Rail mini — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mobil-appen får (A) arbejder-prik + ulæst-badge pr. session i SidePanel og (B) tommel-venlige hop-knapper + scrubber i chat-skærmen.

**Architecture:** Klient-side, ingen backend. Ren logik (`sessionStatus`, `messageNav`, `lastSeen`) i isolerede jest-testede moduler. Arbejder-status fra eksisterende `getActiveRuns`. Ulæst persisteres i `expo-secure-store`. Hop indkapsles i en imperativ `MessageListHandle` (MessageList ejer den `inverted` FlatList + den transformerede række-liste); SaveRail kalder handle-metoder.

**Tech Stack:** React Native / Expo bare, TypeScript, jest (jest-expo), `expo-secure-store`, `react-native` `Animated`/`PanResponder`.

**Miljø:** Alt i `.worktrees/jarvis-mobile-companion-v1/apps/mobile`. Commits via
`git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1` (gren
`codex/jarvis-mobile-companion-v1`). Tests: `cd <mobile> && npx jest <fil>`.
Type-check: `npx tsc --noEmit`. De ~83 eksisterende jest-tests SKAL forblive grønne.

---

## File Structure

**Nye:**
- `src/lib/lastSeen.ts` — persistent map `sessionId→sidst-set count` (secure-store).
- `src/lib/sessionStatus.ts` — ren: `isWorking`, `computeUnread`.
- `src/lib/messageNav.ts` — ren: `nextUserRow` (retnings-bevidst nabo-bruger-række).
- `src/components/SaveRail.tsx` — flydende hop-knapper + scrubber.
- `src/lib/lastSeen.test.ts`, `src/lib/sessionStatus.test.ts`, `src/lib/messageNav.test.ts`.

**Modificerede:**
- `src/components/SidePanel.tsx` — arbejder/ulæst-indikator pr. række.
- `src/components/MessageList.tsx` — `forwardRef` + `useImperativeHandle` (hop-metoder).
- `src/screens/ChatScreen.tsx` — active-runs-poll mens panel åbent, lastSeen, SaveRail-wiring, bonus-prik.

---

## Phase 1 — Ren logik

### Task 1: sessionStatus (isWorking + computeUnread)

**Files:**
- Create: `src/lib/sessionStatus.ts`, `src/lib/sessionStatus.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// src/lib/sessionStatus.test.ts
import { isWorking, computeUnread } from './sessionStatus'
import type { ChatSession } from './types'

const S = (id: string, count: number): ChatSession =>
  ({ id, title: id, message_count: count } as ChatSession)

describe('isWorking', () => {
  it('true når session-id er i active-runs', () => {
    expect(isWorking('s1', ['s1', 's2'])).toBe(true)
    expect(isWorking('s3', ['s1', 's2'])).toBe(false)
  })
})

describe('computeUnread', () => {
  it('ulæst når server-count > gemt og ikke aktiv', () => {
    const sessions = [S('s1', 5), S('s2', 3), S('s3', 0)]
    const lastSeen = { s1: 3, s2: 3 }
    const r = computeUnread(sessions, lastSeen, 'none')
    expect(r).toEqual({ s1: true, s2: false, s3: false })
  })
  it('aktiv session er aldrig ulæst', () => {
    const r = computeUnread([S('s1', 9)], { s1: 0 }, 's1')
    expect(r.s1).toBe(false)
  })
  it('manglende lastSeen → 0-baseline', () => {
    const r = computeUnread([S('s1', 2)], {}, 'none')
    expect(r.s1).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile && npx jest src/lib/sessionStatus.test.ts`
Expected: FAIL (modul findes ikke).

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/lib/sessionStatus.ts
import type { ChatSession } from './types'

export function isWorking(sessionId: string, activeRunIds: string[]): boolean {
  return activeRunIds.includes(sessionId)
}

export function computeUnread(
  sessions: ChatSession[],
  lastSeen: Record<string, number>,
  activeId: string | null,
): Record<string, boolean> {
  const out: Record<string, boolean> = {}
  for (const s of sessions) {
    const count = s.message_count ?? 0
    out[s.id] = s.id !== activeId && count > (lastSeen[s.id] ?? 0)
  }
  return out
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest src/lib/sessionStatus.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/sessionStatus.ts apps/mobile/src/lib/sessionStatus.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): sessionStatus — isWorking + computeUnread (ren logik)"
```

### Task 2: messageNav (retnings-bevidst nabo-bruger-række)

**Files:**
- Create: `src/lib/messageNav.ts`, `src/lib/messageNav.test.ts`

**Designnote:** FlatList'en er `inverted` (index 0 = nyeste). `nextUserRow` er retnings-
agnostisk: den scanner fra `current` i `direction`-skridt (+1 eller -1) og returnerer
første index hvor `isUserFlags[i]` er true, ellers null. MessageList vælger retning.

- [ ] **Step 1: Write the failing test**

```typescript
// src/lib/messageNav.test.ts
import { nextUserRow } from './messageNav'

describe('nextUserRow', () => {
  // flags[i] = er række i en bruger-besked
  const flags = [false, true, false, false, true, false] // bruger ved 1 og 4
  it('finder næste bruger-række i +retning', () => {
    expect(nextUserRow(flags, 1, 1)).toBe(4)
    expect(nextUserRow(flags, 0, 1)).toBe(1)
  })
  it('finder næste bruger-række i -retning', () => {
    expect(nextUserRow(flags, 4, -1)).toBe(1)
  })
  it('null når ingen i retningen', () => {
    expect(nextUserRow(flags, 4, 1)).toBeNull()
    expect(nextUserRow(flags, 1, -1)).toBeNull()
  })
  it('håndterer current uden for grænser', () => {
    expect(nextUserRow(flags, -1, 1)).toBe(1)
    expect(nextUserRow(flags, 99, -1)).toBe(4)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest src/lib/messageNav.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/lib/messageNav.ts
/** Find første bruger-række fra `current` i `direction` (+1/-1). Null hvis ingen.
 *  Retnings-agnostisk så MessageList kan mappe "ældre/nyere" til den rigtige vej
 *  i en inverted FlatList. */
export function nextUserRow(
  isUserFlags: boolean[],
  current: number,
  direction: 1 | -1,
): number | null {
  let i = current + direction
  while (i >= 0 && i < isUserFlags.length) {
    if (isUserFlags[i]) return i
    i += direction
  }
  return null
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest src/lib/messageNav.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/messageNav.ts apps/mobile/src/lib/messageNav.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): messageNav — nextUserRow (retnings-bevidst)"
```

### Task 3: lastSeen (secure-store round-trip)

**Files:**
- Create: `src/lib/lastSeen.ts`, `src/lib/lastSeen.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// src/lib/lastSeen.test.ts
import * as SecureStore from 'expo-secure-store'
import { loadLastSeen, markSeen } from './lastSeen'

jest.mock('expo-secure-store', () => {
  let store: Record<string, string> = {}
  return {
    getItemAsync: jest.fn(async (k: string) => store[k] ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => { store[k] = v }),
    __reset: () => { store = {} },
  }
})

beforeEach(() => { (SecureStore as unknown as { __reset: () => void }).__reset() })

describe('lastSeen', () => {
  it('markSeen + loadLastSeen round-trip', async () => {
    await markSeen('s1', 4)
    await markSeen('s2', 7)
    expect(await loadLastSeen()).toEqual({ s1: 4, s2: 7 })
  })
  it('tom når intet gemt', async () => {
    expect(await loadLastSeen()).toEqual({})
  })
  it('korrupt JSON → tom', async () => {
    await SecureStore.setItemAsync('jarvis.mobile.lastSeen', '{ ugyldig')
    expect(await loadLastSeen()).toEqual({})
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx jest src/lib/lastSeen.test.ts`
Expected: FAIL.

- [ ] **Step 3: Write minimal implementation**

```typescript
// src/lib/lastSeen.ts
import * as SecureStore from 'expo-secure-store'

const KEY = 'jarvis.mobile.lastSeen'

export async function loadLastSeen(): Promise<Record<string, number>> {
  try {
    const raw = await SecureStore.getItemAsync(KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return parsed as Record<string, number>
    }
    return {}
  } catch {
    return {}
  }
}

export async function markSeen(sessionId: string, count: number): Promise<void> {
  try {
    const map = await loadLastSeen()
    map[sessionId] = count
    await SecureStore.setItemAsync(KEY, JSON.stringify(map))
  } catch {
    /* best-effort: ulæst-status er ikke kritisk */
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx jest src/lib/lastSeen.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/lib/lastSeen.ts apps/mobile/src/lib/lastSeen.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): lastSeen-store (secure-store, sidst-set pr. session)"
```

---

## Phase 2 — A: Session-panel live-status

### Task 4: SidePanel arbejder/ulæst-indikator

**Files:**
- Modify: `src/components/SidePanel.tsx` (props + række-indikator)

**Note:** Læs `src/components/SidePanel.tsx` — sessioner renderes i `filtered.map((session) => <Pressable key={session.id}>…)`. Tilføj en indikator i højre side af hver række. Brug eksisterende `HeartbeatDot` (accent, pulserer) til arbejder; en lille statisk accent-prik (8px) til ulæst.

- [ ] **Step 1: Tilføj props til SidePanel-signaturen**

I `SidePanel`-prop-objektet (efter `onOpenSettings`):
```typescript
  workingIds?: string[]
  unreadIds?: Record<string, boolean>
```
Og i destrukturering: `workingIds = [], unreadIds = {},`.

- [ ] **Step 2: Importér HeartbeatDot**

Øverst: `import { HeartbeatDot } from './HeartbeatDot'`

- [ ] **Step 3: Render indikator i session-rækken**

Inde i `filtered.map((session) => (...))`, i `<Pressable key={session.id} …>`, tilføj
til højre for titel/dato (inde i rækkens layout-container):
```tsx
{workingIds.includes(session.id) ? (
  <HeartbeatDot size={8} />
) : unreadIds[session.id] ? (
  <View style={styles.unreadDot} />
) : null}
```
Tilføj style:
```typescript
  unreadDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: tokens.color.accent },
```
(Hvis rækken ikke har en flex-row-container, wrap titel+meta og prikken i en
`<View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>`.)

- [ ] **Step 4: Type-check**

Run: `npx tsc --noEmit`
Expected: ingen fejl.

- [ ] **Step 5: Kør eksisterende SidePanel-test (skal forblive grøn)**

Run: `npx jest src/components/SidePanel.test.tsx`
Expected: PASS (props er valgfrie → bagudkompatibelt).

- [ ] **Step 6: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/SidePanel.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): SidePanel arbejder-prik + ulaest-prik pr. session"
```

### Task 5: ChatScreen — active-runs-poll, lastSeen, mark-seen, bonus-prik

**Files:**
- Modify: `src/screens/ChatScreen.tsx`

**Note:** Læs `ChatScreen.tsx`. `panelOpen`-state + `<SidePanel …>` findes (linje ~38/326).
Sessioner kommer fra `useSessions()` (`sessions`, `activeId`, `select`). `getActiveRuns`
er i `apiClient.ts`.

- [ ] **Step 1: Importér det nødvendige**

```typescript
import { getActiveRuns } from '../lib/apiClient'
import { computeUnread } from '../lib/sessionStatus'
import { loadLastSeen, markSeen } from '../lib/lastSeen'
```

- [ ] **Step 2: State + lastSeen-load**

I ChatScreen-komponenten:
```typescript
const [activeRunIds, setActiveRunIds] = useState<string[]>([])
const [lastSeen, setLastSeen] = useState<Record<string, number>>({})
useEffect(() => { void loadLastSeen().then(setLastSeen) }, [])
```

- [ ] **Step 3: Active-runs-poll MENS panelet er åbent**

```typescript
useEffect(() => {
  if (!panelOpen) return
  let cancelled = false
  const tick = () => { void getActiveRuns(config).then((ids) => { if (!cancelled) setActiveRunIds(ids) }).catch(() => {}) }
  tick()
  const id = setInterval(tick, 2500)
  return () => { cancelled = true; clearInterval(id) }
}, [panelOpen, config])
```
(`config` er ApiConfig i scope; hvis navnet afviger, brug det rigtige — find via
`grep -n "ApiConfig\|config" src/screens/ChatScreen.tsx`.)

- [ ] **Step 4: Beregn unread + mark-seen ved valg**

```typescript
const sessionsList = sessions.list  // tjek faktisk felt-navn i useSessions()
const unreadIds = computeUnread(sessionsList, lastSeen, activeId)

const handleSelect = (sessionId: string) => {
  const s = sessionsList.find((x) => x.id === sessionId)
  const count = s?.message_count ?? 0
  setLastSeen((prev) => ({ ...prev, [sessionId]: count }))
  void markSeen(sessionId, count)
  void select(config, sessionId)  // eksisterende valg-kald (tjek signatur)
}
```
Erstat SidePanel's `onSelectSession`-handler med `handleSelect`.

- [ ] **Step 5: Send props til SidePanel**

```tsx
<SidePanel … workingIds={activeRunIds} unreadIds={unreadIds} onSelectSession={handleSelect} />
```

- [ ] **Step 6: Bonus-prik på presence-ringen (panel-åbneren)**

Find hvor presence-ringen/`JarvisRing` der åbner panelet renderes. Tilføj en lille
accent-prik (8px, absolut placeret øverst-højre på ringen) når
`activeRunIds.length > 0 || Object.values(unreadIds).some(Boolean)`:
```tsx
{(activeRunIds.length > 0 || Object.values(unreadIds).some(Boolean)) && (
  <View style={styles.ringBadge} />
)}
```
Style: `ringBadge: { position: 'absolute', top: 0, right: 0, width: 8, height: 8, borderRadius: 4, backgroundColor: tokens.color.accent }`.

- [ ] **Step 7: Type-check + eksisterende ChatScreen-test**

Run: `npx tsc --noEmit && npx jest src/screens/ChatScreen.test.tsx`
Expected: ingen tsc-fejl; ChatScreen-test grøn (tilføj `getActiveRuns: jest.fn().mockResolvedValue([])` til evt. `apiClient`-mock + secure-store-mock hvis testen brokker sig).

- [ ] **Step 8: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/screens/ChatScreen.tsx apps/mobile/src/screens/ChatScreen.test.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): ChatScreen active-runs-poll + ulaest + bonus-prik (panel live-status)"
```

---

## Phase 3 — B: Save Rail mini

### Task 6: MessageList imperativ hop-handle

**Files:**
- Modify: `src/components/MessageList.tsx`

**Note:** MessageList bruger `inverted` FlatList med `data={ordered}` (Row[]). Eksponér
en imperativ handle. "Ældre" beskeder ligger ved HØJERE index (inverted); "nyere" ved
lavere. `jumpTop` = ældste = `scrollToEnd`; `jumpBottom` = nyeste = `scrollToOffset 0`.

- [ ] **Step 1: Definér handle-typen + forwardRef**

Øverst tilføj imports: `import { forwardRef, useImperativeHandle, useRef, useState } from 'react'`
og `import { nextUserRow } from '../lib/messageNav'`.

Eksportér typen:
```typescript
export interface MessageListHandle {
  jumpTop: () => void       // ældste besked
  jumpBottom: () => void    // nyeste besked
  jumpOlderUser: () => void // forrige bruger-besked (op i historik)
  jumpNewerUser: () => void // næste bruger-besked (ned mod nyeste)
  scrubTo: (fraction: number) => void // 0=nyeste, 1=ældste
}
```

- [ ] **Step 2: Wrap komponenten i forwardRef + intern FlatList-ref + visible-index**

Konvertér `export function MessageList(props)` til:
```typescript
export const MessageList = forwardRef<MessageListHandle, MessageListProps>(function MessageList(props, ref) {
  const flatRef = useRef<FlatList>(null)
  const visibleRef = useRef(0)        // ordered-index øverst i viewport
  const contentLenRef = useRef(0)
  // … eksisterende `ordered`-bygning …
  const userFlags = ordered.map((r) => r.kind === 'message' && r.message.role === 'user')
  useImperativeHandle(ref, () => ({
    jumpTop: () => flatRef.current?.scrollToEnd({ animated: true }),
    jumpBottom: () => flatRef.current?.scrollToOffset({ offset: 0, animated: true }),
    jumpOlderUser: () => {
      const i = nextUserRow(userFlags, visibleRef.current, 1)   // højere index = ældre
      if (i != null) flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0 })
    },
    jumpNewerUser: () => {
      const i = nextUserRow(userFlags, visibleRef.current, -1)  // lavere index = nyere
      if (i != null) flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0 })
    },
    scrubTo: (f: number) => flatRef.current?.scrollToOffset({ offset: f * contentLenRef.current, animated: false }),
  }), [userFlags])
  return ( /* eksisterende JSX, men på <FlatList> tilføj nedenstående props */ )
})
```
(Tilpas `Row`-typens diskriminator: hvis besked-rækker har `kind === 'message'` med
`message.role`, brug det; ellers find det faktiske felt. `MessageListProps` =
den eksisterende props-type — udtræk den hvis den er inline.)

- [ ] **Step 3: Wire FlatList-ref + onViewableItemsChanged + onContentSizeChange**

På `<FlatList>`:
```tsx
ref={flatRef}
onContentSizeChange={(_w, h) => { contentLenRef.current = h }}
onViewableItemsChanged={({ viewableItems }) => {
  if (viewableItems.length > 0 && viewableItems[0].index != null) visibleRef.current = viewableItems[0].index
}}
onScrollToIndexFailed={(info) => {
  flatRef.current?.scrollToOffset({ offset: info.averageItemLength * info.index, animated: true })
}}
```

- [ ] **Step 4: Type-check + eksisterende MessageList-brug**

Run: `npx tsc --noEmit`
Expected: ingen fejl. (Hvis ChatScreen importerer `MessageList` som named export uændret, virker det fortsat — det ER named export.)

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/MessageList.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): MessageList imperativ hop-handle (top/bund/bruger-besked/scrub)"
```

### Task 7: SaveRail-komponent

**Files:**
- Create: `src/components/SaveRail.tsx`

- [ ] **Step 1: Skriv komponenten**

```tsx
// src/components/SaveRail.tsx
import { useRef } from 'react'
import { Animated, PanResponder, Pressable, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

/** Flydende tommel-venlige hop-knapper ved højre kant + en tynd scrubber-track.
 *  Skjult når der er for få beskeder. onScrub(fraction): 0=nyeste, 1=ældste. */
export function SaveRail({
  visible,
  onJumpTop,
  onJumpBottom,
  onOlderUser,
  onNewerUser,
  onScrub,
}: {
  visible: boolean
  onJumpTop: () => void
  onJumpBottom: () => void
  onOlderUser: () => void
  onNewerUser: () => void
  onScrub: (fraction: number) => void
}) {
  const trackH = useRef(1)
  const pan = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: () => true,
      onPanResponderMove: (_e, g) => {
        const f = Math.max(0, Math.min(1, g.moveY / Math.max(1, trackH.current)))
        onScrub(f)
      },
    }),
  ).current
  if (!visible) return null
  return (
    <View style={styles.root} pointerEvents="box-none">
      <Btn label="⤓" onPress={onJumpBottom} />
      <Btn label="▼" onPress={onNewerUser} />
      <View
        style={styles.track}
        onLayout={(e) => { trackH.current = e.nativeEvent.layout.height }}
        {...pan.panHandlers}
      />
      <Btn label="▲" onPress={onOlderUser} />
      <Btn label="⤒" onPress={onJumpTop} />
    </View>
  )
}

function Btn({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} hitSlop={8} style={({ pressed }) => [styles.btn, pressed && styles.pressed]}>
      <Text style={styles.btnText}>{label}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  root: { position: 'absolute', right: tokens.spacing.sm, top: '22%', alignItems: 'center', gap: tokens.spacing.xs },
  btn: { width: 36, height: 36, borderRadius: 18, backgroundColor: tokens.color.bg2, alignItems: 'center', justifyContent: 'center', opacity: 0.85 },
  pressed: { opacity: 1 },
  btnText: { color: tokens.color.fg1, fontSize: 16 },
  track: { width: 4, height: 90, borderRadius: 2, backgroundColor: tokens.color.line, marginVertical: tokens.spacing.xs },
})
```

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: ingen fejl. (Hvis `tokens.color.bg2`/`line` ikke findes, brug eksisterende
token-navne — tjek `src/theme/tokens.ts`.)

- [ ] **Step 3: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/SaveRail.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): SaveRail — flydende hop-knapper + scrubber"
```

### Task 8: Wire SaveRail i ChatScreen

**Files:**
- Modify: `src/screens/ChatScreen.tsx`

- [ ] **Step 1: Importér + ref**

```typescript
import { MessageList, type MessageListHandle } from '../components/MessageList'
import { SaveRail } from '../components/SaveRail'
```
(MessageList importeres måske allerede — tilføj kun `type MessageListHandle`.)

I komponenten:
```typescript
const listRef = useRef<MessageListHandle>(null)
```

- [ ] **Step 2: Sæt ref på MessageList**

Find `<MessageList messages={sessions.messages} … />` og tilføj `ref={listRef}`.

- [ ] **Step 3: Render SaveRail**

Lige efter MessageList (inde i samme container, så absolut-positionen lægger sig over):
```tsx
<SaveRail
  visible={sessions.messages.length >= 2}
  onJumpTop={() => listRef.current?.jumpTop()}
  onJumpBottom={() => listRef.current?.jumpBottom()}
  onOlderUser={() => listRef.current?.jumpOlderUser()}
  onNewerUser={() => listRef.current?.jumpNewerUser()}
  onScrub={(f) => listRef.current?.scrubTo(f)}
/>
```

- [ ] **Step 4: Type-check + ChatScreen-test**

Run: `npx tsc --noEmit && npx jest src/screens/ChatScreen.test.tsx`
Expected: ingen tsc-fejl; test grøn.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/screens/ChatScreen.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile): wire SaveRail i ChatScreen (hop + scrub)"
```

---

## Phase 4 — Verifikation + build

### Task 9: Fuld suite + build + install

- [ ] **Step 1: Hele jest-suiten**

Run: `cd <mobile> && npx jest`
Expected: ALLE grønne (de ~83 eksisterende + de nye sessionStatus/messageNav/lastSeen).

- [ ] **Step 2: Type-check**

Run: `npx tsc --noEmit`
Expected: ingen fejl.

- [ ] **Step 3: Bump version**

`android/app/build.gradle`: `versionCode 26 → 27`, `versionName "0.1.25" → "0.1.26"`.
`app.json` + `package.json`: `"0.1.25" → "0.1.26"`.

- [ ] **Step 4: Build + install på S24**

```bash
cd <mobile>/android && ./gradlew assembleRelease
adb install -r app/build/outputs/apk/release/app-release.apk
adb shell dumpsys package dk.srvlab.jarvis.mobile | grep versionName
```
Expected: `versionName=0.1.26`.

- [ ] **Step 5: Commit + push gren**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/android/app/build.gradle apps/mobile/app.json apps/mobile/package.json
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "chore(mobile): bump 0.1.26 (session-panel live-status + Save Rail)"
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 push origin codex/jarvis-mobile-companion-v1
```

- [ ] **Step 6: On-device-bekræftelse med Bjørn**
  - SidePanel: åbn et run i én session, skift væk → den session viser arbejder-prik;
    en session med nye beskeder viser ulæst-prik; åbn den → prik forsvinder.
  - Presence-ring viser bonus-prik når noget er ulæst/arbejder.
  - SaveRail: hop til top/bund, forrige/næste bruger-besked, scrubber-træk.

---

## Self-Review (udført)

**Spec-dækning:** A arbejder-prik→Task 1+4+5; A ulæst→Task 1+3+5; A bonus-prik→Task 5;
B nextUserRow→Task 2; B handle→Task 6; B SaveRail→Task 7; B wiring→Task 8. Alle
spec-krav har en task.

**Placeholder-scan:** Ingen TBD/TODO. Kode i hvert trin. Tre bevidste "tjek faktisk
felt-navn"-noter (useSessions-felt, Row-diskriminator, token-navne) med grep-kommando,
fordi de afhænger af eksisterende kode der skal bekræftes mod virkeligheden, ikke gættes.

**Type-konsistens:** `MessageListHandle`-metoder (`jumpTop/jumpBottom/jumpOlderUser/
jumpNewerUser/scrubTo`) bruges identisk i Task 6 (def) + Task 8 (kald). `computeUnread`/
`isWorking`/`nextUserRow`/`loadLastSeen`/`markSeen`-signaturer matcher på tværs af
def-task og forbrugs-task. `workingIds`/`unreadIds`-props matcher Task 4 + Task 5.
