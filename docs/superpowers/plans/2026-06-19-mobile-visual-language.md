# Mobile Visuelt Design-Sprog (V2 §3) — Implementeringsplan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Løft jarvis-mobile til §3-design-sproget (grøn-på-dyb-mørk, åndedræt, glas, svg-gradienter) 1:1 med den godkendte mockup — uden at tabe nogen funktionalitet.

**Architecture:** Udvid `tokens.ts` til sandheds-kilde; re-style EKSISTERENDE komponenter på plads (aldrig genskriv); animationer = RN `Animated` (useNativeDriver); gradienter = `react-native-svg` (installeret). Desktop urørt.

**Tech Stack:** React Native (bare Expo SDK 56), `react-native-svg` 15.15.4, RN `Animated`, jest.

**Spec:** `docs/superpowers/specs/2026-06-19-visual-language-design.md`

**KRITISKE noter (læs FØR start):**
- Alt i `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile`. Git-commits via `git -C <worktree>` (gren `codex/jarvis-mobile-companion-v1`; `.worktrees` er gitignored i hovedrepo). Worktree-rod = `/media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1`.
- Test: `npx jest <fil>` fra `apps/mobile`. Typecheck: `npx tsc --noEmit`. **De 71 eksisterende tests SKAL forblive grønne** = funktions-bevarings-garanti.
- **BÆRENDE REGEL:** re-style på plads. Læs hver komponents NUVÆRENDE indhold før du ændrer. Bevar alle props, handlers, funktioner. Tabt funktionalitet = plan-fejl.
- `react-native-svg` autolinkes ind ved næste native build → APK skal bygges (Task 8). Indtil da kan jest-tests køre (svg mockes).
- Device: Galaxy S24 (RFCX211W6CR), `adb install -r`. Bump app.json versionCode + build.gradle + package.json før build.

---

## Fase 1: Token-fundament

### Task 1: Udvid tokens.ts med design-sproget

**Files:**
- Modify: `src/theme/tokens.ts`
- Test: `src/theme/tokens.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// src/theme/tokens.test.ts
import { tokens } from './tokens'

describe('design-sprog tokens', () => {
  it('har depth-lag', () => {
    expect(tokens.color.depth0).toBe('#0D0D12')
    expect(tokens.color.depth1).toBe('#10151d')
    expect(tokens.color.depth2).toBe('#131922')
  })
  it('har glas + accent-varianter', () => {
    expect(tokens.color.glassFill).toMatch(/rgba\(255, ?255, ?255, ?0\.07\)/)
    expect(tokens.color.accentDim).toContain('110, 231, 168')
  })
  it('har timing', () => {
    expect(tokens.motion.breath).toBe(3000)
    expect(tokens.motion.durBase).toBe(250)
    expect(tokens.motion.heartbeat).toBe(1400)
  })
})
```

- [ ] **Step 2: Run — FAIL**

Run: `npx jest src/theme/tokens.test.ts`
Expected: FAIL (`tokens.color.depth0` undefined)

- [ ] **Step 3: Implementér — udvid `tokens.ts`**

Behold ALLE eksisterende felter. Tilføj i `color`:
```typescript
    depth0: '#0D0D12',
    depth1: '#10151d',
    depth2: '#131922',
    depth3: '#1a212d',
    accentDim: 'rgba(110, 231, 168, 0.55)',
    accentGhost: 'rgba(110, 231, 168, 0.12)',
    glassFill: 'rgba(255, 255, 255, 0.07)',
    glassLine: 'rgba(255, 255, 255, 0.10)',
```
Tilføj ny top-level nøgle efter `spacing`:
```typescript
  motion: {
    durFast: 160,
    durBase: 250,
    breath: 3000,
    heartbeat: 1400
  }
```

- [ ] **Step 4: Run — PASS**

Run: `npx jest src/theme/tokens.test.ts` → PASS. Derefter `npx jest` (alle 71 + ny) → alle grønne.

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/theme/tokens.ts apps/mobile/src/theme/tokens.test.ts
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile-visual): udvid tokens med depth/accent/glas/motion"
```

---

## Fase 2: Kerne-følelsen (ring + stream) — svg-gradienter

### Task 2: Liveness-ring med ægte radial-glød (svg)

**Files:**
- Modify: `src/components/LivenessRing.tsx`
- Test: `src/components/LivenessRing.test.tsx`

> NUVÆRENDE `LivenessRing` (læs filen): `<View>`-halo + ring, breathing-loop på `status==='working'`, props `{status, size}`. Bevar props + breathing. Tilføj en svg-`RadialGradient`-glød BAG ring'en (matcher mockup). Behold View-ring som kerne.

- [ ] **Step 1: Failing test**

```typescript
// src/components/LivenessRing.test.tsx
import { render } from '@testing-library/react-native'
import { LivenessRing } from './LivenessRing'

describe('LivenessRing', () => {
  it('rendrer i alle tre tilstande uden crash', () => {
    for (const status of ['idle', 'working', 'error'] as const) {
      const { toJSON } = render(<LivenessRing status={status} />)
      expect(toJSON()).toBeTruthy()
    }
  })
})
```

- [ ] **Step 2: Run — FAIL** (`npx jest src/components/LivenessRing.test.tsx` — fejler hvis svg ikke mockes; tilføj svg-mock i `jest.setup.js` først, se Step 3).

- [ ] **Step 3: Mock react-native-svg i jest + tilføj glød**

I `jest.setup.js`, tilføj:
```javascript
jest.mock('react-native-svg', () => {
  const React = require('react')
  const mk = (n) => (p) => React.createElement(n, p, p.children)
  return { __esModule: true, default: mk('Svg'), Svg: mk('Svg'), Circle: mk('Circle'),
    Defs: mk('Defs'), RadialGradient: mk('RadialGradient'), LinearGradient: mk('LinearGradient'),
    Stop: mk('Stop'), Rect: mk('Rect') }
})
```
I `LivenessRing.tsx`: importér `Svg, Defs, RadialGradient, Stop, Circle` fra `react-native-svg`. Erstat den nuværende statiske `<View style={styles.halo}>` med en `<Animated.View>` (behold scale/opacity-interpolationerne) der wrapper en `<Svg width={size*2} height={size*2}>` med `<Defs><RadialGradient id="g"><Stop offset="0.6" stopColor={ringColor} stopOpacity="0"/><Stop offset="0.88" stopColor={ringColor} stopOpacity="0.55"/><Stop offset="1" stopColor={ringColor} stopOpacity="0"/></RadialGradient></Defs><Circle cx={size} cy={size} r={size} fill="url(#g)"/></Svg>`. Behold View-ring + breathing-loop uændret. `ringColor` = accent/error som nu.

- [ ] **Step 4: Run — PASS** (`npx jest src/components/LivenessRing.test.tsx` + `npx tsc --noEmit`).

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/LivenessRing.tsx apps/mobile/src/components/LivenessRing.test.tsx apps/mobile/jest.setup.js
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile-visual): liveness-ring med svg radial-gloed (1:1 mockup)"
```

### Task 3: Stream-indikator (svg linear-gradient)

**Files:**
- Create: `src/components/StreamIndicator.tsx`
- Test: `src/components/StreamIndicator.test.tsx`
- Modify: `src/screens/ChatScreen.tsx` (montér over Composer, drevet af eksisterende `serverBusy || stream.state.status==='working'`)

- [ ] **Step 1: Failing test**

```typescript
// src/components/StreamIndicator.test.tsx
import { render } from '@testing-library/react-native'
import { StreamIndicator } from './StreamIndicator'

describe('StreamIndicator', () => {
  it('rendrer når active', () => {
    expect(render(<StreamIndicator active />).toJSON()).toBeTruthy()
  })
  it('rendrer ingenting når inaktiv', () => {
    expect(render(<StreamIndicator active={false} />).toJSON()).toBeNull()
  })
})
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implementér `StreamIndicator.tsx`**

```typescript
import { useEffect, useRef } from 'react'
import { Animated, View } from 'react-native'
import Svg, { Defs, LinearGradient, Stop, Rect } from 'react-native-svg'
import { tokens } from '../theme/tokens'

export function StreamIndicator({ active, width = 320 }: { active: boolean; width?: number }) {
  const x = useRef(new Animated.Value(0)).current
  useEffect(() => {
    if (!active) { x.stopAnimation(); return }
    const loop = Animated.loop(
      Animated.timing(x, { toValue: 1, duration: 1200, useNativeDriver: true })
    )
    loop.start()
    return () => loop.stop()
  }, [active, x])
  if (!active) return null
  const translateX = x.interpolate({ inputRange: [0, 1], outputRange: [-width, width] })
  return (
    <View style={{ height: 2, width: '100%', overflow: 'hidden' }}>
      <Animated.View style={{ width, transform: [{ translateX }] }}>
        <Svg width={width} height={2}>
          <Defs>
            <LinearGradient id="s" x1="0" y1="0" x2="1" y2="0">
              <Stop offset="0" stopColor={tokens.color.accent} stopOpacity="0" />
              <Stop offset="0.5" stopColor={tokens.color.accent} stopOpacity="1" />
              <Stop offset="1" stopColor={tokens.color.accent} stopOpacity="0" />
            </LinearGradient>
          </Defs>
          <Rect width={width} height={2} fill="url(#s)" />
        </Svg>
      </Animated.View>
    </View>
  )
}
```

- [ ] **Step 4: Montér i ChatScreen** — læs ChatScreen, find hvor Composer rendres, indsæt `<StreamIndicator active={stream.state.status === 'working' || serverBusy} />` LIGE over Composeren. Rør intet andet.

- [ ] **Step 5: Run — PASS** (`npx jest src/components/StreamIndicator.test.tsx` + `npx jest` alle grønne + `npx tsc --noEmit`).

- [ ] **Step 6: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/StreamIndicator.tsx apps/mobile/src/components/StreamIndicator.test.tsx apps/mobile/src/screens/ChatScreen.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile-visual): stream-indikator (svg gloedende linje over composer)"
```

---

## Fase 3: Beskeder & kort

### Task 4: Glas-brugerboble + spring-ind

**Files:**
- Modify: `src/components/MessageBubble.tsx`
- Test: `src/components/MessageBubble.test.tsx` (opret hvis mangler)

> Læs `MessageBubble`. Find hvor bruger- vs assistent-rolle adskilles. Bevar al tekst/markdown-rendering.

- [ ] **Step 1: Failing test** — render bruger-boble + assistent-boble, assert begge rendrer uden crash (snapshot-fri smoke).

```typescript
import { render } from '@testing-library/react-native'
import { MessageBubble } from './MessageBubble'
it('rendrer bruger + assistent uden crash', () => {
  expect(render(<MessageBubble role="user" content="hej" />).toJSON()).toBeTruthy()
  expect(render(<MessageBubble role="assistant" content="hej" />).toJSON()).toBeTruthy()
})
```
(tilpas props til komponentens faktiske signatur efter læsning.)

- [ ] **Step 2: Run — FAIL/justér** til komponentens props.

- [ ] **Step 3: Re-style** — bruger-boble: `backgroundColor: tokens.color.glassFill`, `borderWidth: 1`, `borderColor: tokens.color.glassLine`, `borderRadius: tokens.radius.lg`. Assistent-boble: `backgroundColor: tokens.color.depth2`. Wrap boblen i en `Animated.View` med spring-ind ved mount: `scale 0.96→1, opacity 0→1` (`Animated.spring`, useNativeDriver). Behold alt indhold/handlers.

- [ ] **Step 4: Run — PASS** (`npx jest src/components/MessageBubble.test.tsx` + alle grønne).

- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/MessageBubble.tsx apps/mobile/src/components/MessageBubble.test.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile-visual): glas-brugerboble + spring-ind"
```

### Task 5: Tool-kort folde-op

**Files:**
- Modify: `src/components/ToolResultCard.tsx`
- Test: `src/components/ToolResultCard.test.tsx` (opret hvis mangler)

> Læs `ToolResultCard`. Bevar tool-navn/resultat/status-felter + evt. expand/collapse.

- [ ] **Step 1: Failing test** — render uden crash (tilpas props).
- [ ] **Step 2: Run — FAIL/justér.**
- [ ] **Step 3: Re-style** — `backgroundColor: tokens.color.depth1`, 3px `borderLeftColor: tokens.color.accent` (`borderLeftWidth: 3`, `borderRadius` 0 på venstre via separat — eller behold radius og brug en accent-stribe-`View`), tool-navn i `tokens.color.accent`, resultat `tokens.color.fg2`, status `tokens.color.fg3`. Mount-animation: `Animated` translateY `8→0` + opacity `0→1` over `tokens.motion.durBase`.
- [ ] **Step 4: Run — PASS** (alle grønne).
- [ ] **Step 5: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/ToolResultCard.tsx apps/mobile/src/components/ToolResultCard.test.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile-visual): tool-kort accent-kant + folde-op"
```

---

## Fase 4: Prik + overgang + composer + audit

### Task 6: Notifikationsprik (hjerteslag) + session-overgang

**Files:**
- Create: `src/components/HeartbeatDot.tsx` + test
- Modify: `src/screens/ChatScreen.tsx` (session-overgang: fade `MessageList` ved sessionId-skift)

- [ ] **Step 1: Failing test** for `HeartbeatDot` (render uden crash).
- [ ] **Step 2: Run — FAIL.**
- [ ] **Step 3: Implementér `HeartbeatDot`** — lille accent-cirkel, `Animated.loop` med to hurtige skala-slag (1→1.3→1→1.3→1) pr. `tokens.motion.heartbeat`, useNativeDriver. Brug hvor en ulæst-indikator allerede vises (find eksisterende sted; ellers eksportér til senere brug — montér IKKE et nyt sted uden behov).
- [ ] **Step 4: Session-overgang** — i ChatScreen, wrap MessageList i `Animated.View`; ved `sessionId`-skift kør en kort `fade ud→ind` (opacity, `durBase`). Rør ikke load-logikken.
- [ ] **Step 5: Run — PASS** (alle grønne + tsc).
- [ ] **Step 6: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src/components/HeartbeatDot.tsx apps/mobile/src/components/HeartbeatDot.test.tsx apps/mobile/src/screens/ChatScreen.tsx
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile-visual): hjerteslag-prik + bloed session-overgang"
```

### Task 7: Composer-restyle (BEVAR alle funktioner) + accent-audit + reduced-motion

**Files:**
- Modify: `src/components/Composer.tsx`
- Modify: diverse komponenter (accent-audit)
- Create: `src/lib/useReducedMotion.ts` + test

- [ ] **Step 1: Læs `Composer.tsx` HELT.** Notér alle props/handlers: `onSend, onStop, onPressModel, onAttach, modelLabel, mic, …`. Disse SKAL bevares 1:1.

- [ ] **Step 2: Re-style Composeren** — flade `tokens.color.depth0`, send-knap `tokens.color.accent`, fokus-kant `tokens.color.accent` (subtil). Behold "levende papir"-højde (vokser/trækker — allerede tænkt). ÆNDR INTET i `onSend`/`onStop`/`onAttach`/`onPressModel`/mic-logik. Kun `style`-værdier + evt. en `Animated` højde-transition.

- [ ] **Step 3: reduced-motion hook**

```typescript
// src/lib/useReducedMotion.ts
import { useEffect, useState } from 'react'
import { AccessibilityInfo } from 'react-native'
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false)
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(setReduced)
    const sub = AccessibilityInfo.addEventListener('reduceMotionChanged', setReduced)
    return () => sub.remove()
  }, [])
  return reduced
}
```
Test: mock `AccessibilityInfo.isReduceMotionEnabled` → true/false, assert hook returnerer det. Anvend i LivenessRing/StreamIndicator/HeartbeatDot: hvis `reduced`, spring loops over og sæt statisk slut-tilstand.

- [ ] **Step 4: Accent-audit** — grep mobil-komponenter for hårdkodede farver der ikke er accent/depth/fg/glass; ret til tokens. UNDTAG composeren's funktionelle dele.

- [ ] **Step 5: Run — PASS** — `npx jest` (ALLE 71 + nye grønne — composer/ChatScreen-tests beviser funktioner intakte) + `npx tsc --noEmit`.

- [ ] **Step 6: Commit**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/src
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "feat(mobile-visual): composer-restyle (funktioner bevaret) + reduced-motion + accent-audit"
```

---

## Fase 5: Build + on-device verifikation

### Task 8: Byg APK + verificér på S24

- [ ] **Step 1: Bump version** — `app.json` versionCode 22→23 + version 0.1.21→0.1.22; `android/app/build.gradle` versionCode/versionName; `package.json` version.
- [ ] **Step 2: Byg** (react-native-svg autolinkes ind):
```bash
cd /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1/apps/mobile/android && ./gradlew :app:assembleRelease -PreactNativeArchitectures=arm64-v8a
```
Forventet: BUILD SUCCESSFUL. (Hvis svg-autolink fejler: verificér `react-native-svg` i `settings.gradle`/autolink — RN autolinker normalt automatisk.)
- [ ] **Step 3: Installér** — `cp .../app-release.apk ~/jarvis-mobile.apk && adb install -r ~/jarvis-mobile.apk`.
- [ ] **Step 4: On-device-verifikation (det endelige bevis)** — Bjørn åbner appen og bekræfter: (a) liveness-ring ånder med blød glød (matcher mockup), (b) stream-linje glider mens Jarvis svarer, (c) glas-brugerboble + tool-kort ser rigtige ud, (d) **composeren virker fuldt** — vedhæft, model-pille, mic, send/stop, tastatur-løft. Iterér finjustering.
- [ ] **Step 5: Commit version-bump.**

```bash
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 add apps/mobile/app.json apps/mobile/android/app/build.gradle apps/mobile/package.json
git -C /media/projects/jarvis-v2/.worktrees/jarvis-mobile-companion-v1 commit -m "chore(mobile-visual): version-bump for visuelt-loeft-build"
```

---

## Afslutning

Efter alle tasks: verificér fuld suite (`npx tsc --noEmit` + `npx jest` — alle grønne, ingen funktionel regression). Opdatér memory `project_mobile_push_notifications`-stil: ny `project_mobile_visual_language` med live-status. Desktop forblev urørt — bekræft `git -C <hovedrepo>` har ingen jarvis-desk-ændringer.
