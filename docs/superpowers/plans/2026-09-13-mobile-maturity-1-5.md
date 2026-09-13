# Mobile Maturity 1-5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the mobile app feel more complete across i18n, navigation/back behavior, settings polish, offline/reconnect UX, and voice state clarity.

**Architecture:** Keep the current React Native/Expo structure and add small, typed helpers around it instead of introducing a navigation framework. Translation coverage expands through the existing `I18nProvider`; UX polish lands in focused components with tests before behavior changes.

**Tech Stack:** Expo 56, React Native 0.85, TypeScript, Jest, `@testing-library/react-native`.

**Spec:** User-approved chat design in this thread on 2026-09-13.

## Global Constraints

- Touch only `apps/mobile` and this plan file unless a test proves a shared API contract must change.
- Do not modify unrelated dirty files in `core/services` or unrelated tests.
- Use the existing `useI18n()` API; do not add a new i18n dependency.
- Prefer a light internal route/modal helper over adding React Navigation in this pass.
- Keep changes test-first and scoped; each task must have a targeted Jest test.

---

### Task 1: Expand Visible Mobile i18n

**Files:**
- Modify: `apps/mobile/src/i18n/i18n.ts`
- Modify: `apps/mobile/src/components/TopBar.tsx`
- Modify: `apps/mobile/src/components/TopBarMenu.tsx`
- Modify: `apps/mobile/src/components/SidePanel.tsx`
- Test: `apps/mobile/src/i18n/i18n.test.ts`
- Test: `apps/mobile/src/components/SidePanel.test.tsx`
- Test: `apps/mobile/src/components/TopBar.test.tsx`

**Interfaces:**
- Consumes: `useI18n(): { t(key, vars?), locale, setLocale }`
- Produces: stable translation keys for app chrome and panel labels.

- [ ] Add failing tests proving English locale changes TopBar segment labels, SidePanel actions/search placeholders, and TopBarMenu items.
- [ ] Add translation keys in `i18n.ts` for app chrome, side panel, common actions, and empty states.
- [ ] Replace hardcoded user-facing strings in TopBar, TopBarMenu, and SidePanel with `t(...)`.
- [ ] Run targeted tests: `npm test -- --runTestsByPath src/i18n/i18n.test.ts src/components/TopBar.test.tsx src/components/SidePanel.test.tsx --runInBand`.

### Task 2: Lightweight Mobile Route Stack

**Files:**
- Create: `apps/mobile/src/lib/mobileRoutes.ts`
- Test: `apps/mobile/src/lib/mobileRoutes.test.ts`
- Modify: `apps/mobile/src/screens/ChatScreen.tsx`
- Modify: `apps/mobile/src/App.tsx`

**Interfaces:**
- Produces: `type MobileRoute`, `pushRoute(stack, route)`, `popRoute(stack)`, `replaceTopRoute(stack, route)`, `topRoute(stack)`.
- Consumes: existing modal booleans in `ChatScreen` and top-level app mode state in `App.tsx`.

- [ ] Add failing tests for push/pop/replace/top behavior and duplicate route handling.
- [ ] Implement `mobileRoutes.ts` as pure functions.
- [ ] Use the route stack to drive ChatScreen modals that currently live as separate booleans.
- [ ] Add Android `BackHandler` handling: close top modal first, then code mode, then leave default system behavior.
- [ ] Run targeted tests: `npm test -- --runTestsByPath src/lib/mobileRoutes.test.ts src/screens/ChatScreen.test.tsx src/__tests__/App.test.tsx --runInBand`.

### Task 3: Settings Health Copy Polish

**Files:**
- Modify: `apps/mobile/src/lib/settingsHealth.ts`
- Test: `apps/mobile/src/lib/settingsHealth.test.ts`
- Modify: `apps/mobile/src/screens/SettingsScreen.tsx`
- Test: `apps/mobile/src/screens/SettingsScreen.test.tsx`

**Interfaces:**
- Consumes: existing settings health input object.
- Produces: translated, user-readable health labels and guidance for API, device route, outbox, sensors, and update/device status.

- [ ] Add failing tests for English/Danish health tile labels and outbox wording.
- [ ] Add translation keys for settings health and diagnostics.
- [ ] Replace raw diagnostic text in SettingsScreen where it is visible to users.
- [ ] Run targeted tests: `npm test -- --runTestsByPath src/lib/settingsHealth.test.ts src/screens/SettingsScreen.test.tsx --runInBand`.

### Task 4: Offline/Reconnect UX

**Files:**
- Create: `apps/mobile/src/components/OfflineNotice.tsx`
- Test: `apps/mobile/src/components/OfflineNotice.test.tsx`
- Modify: `apps/mobile/src/screens/ChatScreen.tsx`
- Modify: `apps/mobile/src/screens/SettingsScreen.tsx`

**Interfaces:**
- Consumes: `useConnectivity(config)` result and `loadOutbox()`.
- Produces: small visible notice for offline/reconnecting states and queued messages.

- [ ] Add failing tests for offline, reconnecting, queued item, and all-clear states.
- [ ] Implement `OfflineNotice` using existing tokens/theme and i18n.
- [ ] Show notice in ChatScreen near the top safe area and in Settings health context.
- [ ] Run targeted tests: `npm test -- --runTestsByPath src/components/OfflineNotice.test.tsx src/screens/ChatScreen.test.tsx --runInBand`.

### Task 5: Voice State Clarity

**Files:**
- Modify: `apps/mobile/src/lib/voiceUiState.ts`
- Test: `apps/mobile/src/lib/voiceUiState.test.ts`
- Modify: `apps/mobile/src/components/VoiceOverlay.tsx`
- Test: `apps/mobile/src/components/VoiceOverlay.test.tsx`

**Interfaces:**
- Consumes: `VoiceState` and current voice problem/workingStep.
- Produces: clearer primary/action/hint copy for idle, listening, transcribing, thinking, speaking, interrupted/error states.

- [ ] Add failing tests for all voice states in both Danish and English copy.
- [ ] Translate `voiceStatusCopy` through a small dictionary or by accepting a translator callback.
- [ ] Update VoiceOverlay accessibility labels and bottom hint to reflect state and provider.
- [ ] Run targeted tests: `npm test -- --runTestsByPath src/lib/voiceUiState.test.ts src/components/VoiceOverlay.test.tsx --runInBand`.

### Task 6: Final Verification

**Files:**
- Verify all touched files.

- [ ] Run mobile typecheck: `npm run typecheck`.
- [ ] Run mobile targeted Jest suite for all changed areas.
- [ ] Report any skipped/manual-only verification, especially Android native back/push/voice behavior.
