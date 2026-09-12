# Mobile Composer, Persistence, and Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build icon-only per-conversation composer controls and split mobile voice into inline dictation and hands-free orb conversation while preserving every user setting across restart.

**Architecture:** `ChatIndstillingerV2` is the single per-session composer preference record and projects directly to the stream request. `Composer` owns only draft presentation; `useComposerDictation` owns one-shot recording/transcription, while `useVoiceConversation` owns continuous hands-free conversation.

**Tech Stack:** React Native 0.85, React 19, Expo 56, expo-audio, Expo SecureStore, Jest, Testing Library, TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-12-mobile-adaptive-research-implementation-spec.md`

## Global Constraints

- Composer control order after attach is permissions, model, research; all three are icon-only.
- User-entered text is never prefixed with research instructions.
- Dictation transcribes into an editable draft and never auto-sends.
- Wave opens hands-free orb conversation; microphone opens inline dictation.
- Per-chat preferences are local mobile state in V1 and versioned in SecureStore.
- Do not run the full repository test suite; run affected mobile Jest files and TypeScript.
- Do not touch unrelated `docs/specs/2026-09-08-deepseek-harness-lessons-for-jarvis.md` changes.

---

### Task 1: Versioned Per-Conversation Settings

**Files:**
- Modify: `apps/mobile/src/lib/chatSettings.ts`
- Modify: `apps/mobile/src/lib/chatSettings.test.ts`

**Interfaces:**
- Produces: `ChatIndstillingerV2`, `ResearchMode`, `parseChatIndstillinger(raw, legacyModel?)`, `tilStreamFelter(cfg)`.
- Consumes: existing `StoredModelChoice` shape from `sessionStore.ts`, moved or re-exported without a duplicate definition.

- [ ] **Step 1: Write failing migration and projection tests**

```ts
expect(await laesIndstillinger('s1')).toMatchObject({ version: 2, researchMode: 'off', thinkingMode: 'think' })
expect(tilStreamFelter(cfg)).toEqual(expect.objectContaining({
  model: 'deepseek-v4-flash', providerChoice: 'deepseek', researchMode: true
}))
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run: `npm test -- --runInBand src/lib/chatSettings.test.ts`
Expected: FAIL because V2 fields and atomic model choice do not exist.

- [ ] **Step 3: Implement V2 parsing, safe defaults, and V1 migration**

```ts
export interface ChatIndstillingerV2 {
  version: 2
  model: StoredModelChoice | null
  thinkingMode: 'fast' | 'think'
  researchMode: 'off' | 'on'
  vaerktoejer: 'samtale' | 'fuldt'
  stemme: boolean
  spoergFoerst: boolean
}
```

Unknown or corrupt values fall back field-by-field; unknown legacy model providers become `null` rather than guessed.

- [ ] **Step 4: Run settings tests and confirm GREEN**

Run: `npm test -- --runInBand src/lib/chatSettings.test.ts`
Expected: PASS.

### Task 2: Stream and Offline Turn Controls

**Files:**
- Modify: `apps/mobile/src/lib/streamClient.ts`
- Modify: `apps/mobile/src/lib/streamClient.test.ts`
- Modify: `apps/mobile/src/state/StreamContext.tsx`
- Modify: `apps/mobile/src/state/StreamContext.test.tsx`
- Modify: `apps/mobile/src/lib/offlineOutbox.ts`
- Modify: `apps/mobile/src/lib/offlineOutbox.test.ts`

**Interfaces:**
- Consumes: `tilStreamFelter` output.
- Produces: `researchMode?: boolean` in client options and `research_mode` on wire; versioned chat outbox controls.

- [ ] **Step 1: Write failing wire and outbox tests**

```ts
expect(JSON.parse(String(EventSource.mock.calls[0][1].body))).toMatchObject({ research_mode: true })
expect(item).toMatchObject({ controls: { thinkingMode: 'fast', researchMode: true } })
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `npm test -- --runInBand src/lib/streamClient.test.ts src/state/StreamContext.test.tsx src/lib/offlineOutbox.test.ts`
Expected: FAIL on missing research field and controls.

- [ ] **Step 3: Add additive request plumbing and outbox migration**

```ts
research_mode: request.researchMode ?? false
```

Old outbox records remain valid and default to normal chat controls.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `npm test -- --runInBand src/lib/streamClient.test.ts src/state/StreamContext.test.tsx src/lib/offlineOutbox.test.ts`
Expected: PASS.

### Task 3: Icon-Only Composer Control Order

**Files:**
- Modify: `apps/mobile/src/components/Composer.tsx`
- Modify: `apps/mobile/src/components/Composer.test.tsx`

**Interfaces:**
- Produces: test IDs `composer-permission`, `composer-model`, `composer-research`, `composer-dictate`, `composer-button`.
- Consumes: existing callbacks plus separate `onDictate` and `onConversation`.

- [ ] **Step 1: Write failing order, label, and primary-button tests**

```ts
expect(controlIds).toEqual(['composer-permission', 'composer-model', 'composer-research'])
expect(screen.queryByText('Research')).toBeNull()
fireEvent.press(screen.getByLabelText('Start samtale'))
expect(onConversation).toHaveBeenCalledTimes(1)
```

- [ ] **Step 2: Run Composer tests and confirm RED**

Run: `npm test -- --runInBand src/components/Composer.test.tsx`
Expected: FAIL because controls contain labels/order mismatch and wave calls `onMic`.

- [ ] **Step 3: Implement fixed-size icon controls and stop/send/wave priority**

Use Lucide `ShieldCheck`, `Cpu`, `SearchCheck`, `Mic`, `AudioLines`, `ArrowUp`, and `Square`. Keep all icon buttons dimensionally stable and accessible.

- [ ] **Step 4: Run Composer tests and confirm GREEN**

Run: `npm test -- --runInBand src/components/Composer.test.tsx`
Expected: PASS.

### Task 4: Inline Dictation State Machine

**Files:**
- Create: `apps/mobile/src/lib/useComposerDictation.ts`
- Create: `apps/mobile/src/lib/useComposerDictation.test.ts`
- Create: `apps/mobile/src/components/DictationBar.tsx`
- Create: `apps/mobile/src/components/DictationBar.test.tsx`
- Modify: `apps/mobile/src/components/Composer.tsx`

**Interfaces:**
- Produces: `{state, level, elapsedMs, text, error, start, stop, cancel, clearResult}` where state is `idle|recording|transcribing|error`.
- Consumes: existing `transcribeAudio(config, uri)` and Expo recorder APIs.

- [ ] **Step 1: Write failing hook lifecycle tests**

```ts
await result.current.start()
expect(result.current.state).toBe('recording')
await result.current.stop()
expect(result.current.text).toBe('dikteret tekst')
expect(send).not.toHaveBeenCalled()
```

- [ ] **Step 2: Run hook/component tests and confirm RED**

Run: `npm test -- --runInBand src/lib/useComposerDictation.test.ts src/components/DictationBar.test.tsx`
Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement one-shot recording, metering, cleanup, and inline bar**

The hook requests permission, starts one recorder, samples metering into `Animated.Value`, stops to STT, deletes/abandons temporary audio on cancel, and never calls chat send.

- [ ] **Step 4: Run dictation tests and confirm GREEN**

Run: `npm test -- --runInBand src/lib/useComposerDictation.test.ts src/components/DictationBar.test.tsx`
Expected: PASS.

### Task 5: Draft Insertion and Voice Ownership

**Files:**
- Modify: `apps/mobile/src/components/Composer.tsx`
- Modify: `apps/mobile/src/components/Composer.test.tsx`
- Modify: `apps/mobile/src/screens/ChatScreen.tsx`
- Modify: `apps/mobile/src/lib/useVoiceConversation.ts`
- Modify: `apps/mobile/src/components/VoiceOverlay.tsx`
- Modify: corresponding existing tests.

**Interfaces:**
- Consumes: dictation result signal `{text, sequence}`.
- Produces: hands-free-only `useVoiceConversation`; dictation inserts at selection or appends safely.

- [ ] **Step 1: Write failing integration tests**

```ts
expect(input.props.value).toBe('eksisterende dikteret tekst')
expect(onSend).not.toHaveBeenCalled()
expect(screen.queryByText('Push-to-talk')).toBeNull()
```

- [ ] **Step 2: Run affected tests and confirm RED**

Run: `npm test -- --runInBand src/components/Composer.test.tsx src/components/VoiceOverlay.test.tsx src/lib/useVoiceConversation.test.ts`
Expected: FAIL on auto ownership/mode picker and missing insertion.

- [ ] **Step 3: Wire separate callbacks and remove orb push mode**

`ChatScreen` calls dictation start for mic and `voice.enter()` for wave. App background, session switch, unmount, and orb entry call dictation cancel. Dictation result updates Composer through a sequence signal and never invokes `ensureSessionAndSend`.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `npm test -- --runInBand src/components/Composer.test.tsx src/components/VoiceOverlay.test.tsx src/lib/useVoiceConversation.test.ts`
Expected: PASS.

### Task 6: Apply Per-Chat Settings in ChatScreen

**Files:**
- Modify: `apps/mobile/src/screens/ChatScreen.tsx`
- Modify: `apps/mobile/src/components/ModelPicker.tsx`
- Modify: `apps/mobile/src/components/ModelPicker.test.tsx`
- Modify: `apps/mobile/src/components/ChatSettingsSheet.tsx`
- Modify: `apps/mobile/src/components/ChatSettingsSheet.test.tsx`
- Delete: `apps/mobile/src/lib/chatPrompt.ts`
- Delete: `apps/mobile/src/lib/chatPrompt.test.ts`

**Interfaces:**
- Consumes: V2 chat settings and stream projection.
- Produces: one active conversation config; no transient model/thinking/research truth.

- [ ] **Step 1: Write failing picker and persistence integration tests**

```ts
expect(onChange).toHaveBeenCalledWith({ model: selectedChoice })
expect(outgoingUserText).toBe('Find kilder')
```

- [ ] **Step 2: Run affected tests and confirm RED**

Run: `npm test -- --runInBand src/components/ModelPicker.test.tsx src/components/ChatSettingsSheet.test.tsx src/lib/chatSettings.test.ts`
Expected: FAIL until whole model choice and controls are V2-backed.

- [ ] **Step 3: Replace local state with chat config and remove prompt prefix**

Load config on session selection, update optimistically then persist, and project all controls for online/offline sends. Remove duplicate `thinkingMode` property. Wire `stemme` to response TTS or remove the control only if the functional behavior cannot be made truthful.

- [ ] **Step 4: Run affected tests and confirm GREEN**

Run: `npm test -- --runInBand src/components/ModelPicker.test.tsx src/components/ChatSettingsSheet.test.tsx src/lib/chatSettings.test.ts src/components/Composer.test.tsx`
Expected: PASS.

### Task 7: Preference Reload Audit

**Files:**
- Create: `apps/mobile/src/lib/preferenceReload.test.ts`
- Modify only a preference module whose reload behavior fails this test.

**Interfaces:**
- Consumes: theme, camera, battery, location, bubble, auth, session, connector, and notification stores.
- Produces: documented automated reload coverage; no generic mega-store.

- [ ] **Step 1: Add table-driven cold-load tests**

```ts
it.each(cases)('$name restores the stored selection', async ({save, load, value}) => {
  await save(value)
  await expect(load()).resolves.toEqual(value)
})
```

- [ ] **Step 2: Run and inspect failures**

Run: `npm test -- --runInBand src/lib/preferenceReload.test.ts`
Expected: RED only for an actual unpersisted presented setting; do not force transient UI state into storage.

- [ ] **Step 3: Fix only demonstrated persistence gaps**

Keep each setting with its existing owner. Server preferences remain server-backed; local preferences remain SecureStore-backed.

- [ ] **Step 4: Run reload tests and confirm GREEN**

Run: `npm test -- --runInBand src/lib/preferenceReload.test.ts`
Expected: PASS.

### Task 8: Mobile Verification

**Files:**
- No production changes unless verification exposes a defect.

**Interfaces:**
- Consumes: Tasks 1-7.
- Produces: verified mobile deliverable.

- [ ] **Step 1: Run all affected tests**

Run: `npm test -- --runInBand src/lib/chatSettings.test.ts src/lib/streamClient.test.ts src/state/StreamContext.test.tsx src/lib/offlineOutbox.test.ts src/components/Composer.test.tsx src/lib/useComposerDictation.test.ts src/components/DictationBar.test.tsx src/components/VoiceOverlay.test.tsx src/components/ModelPicker.test.tsx src/components/ChatSettingsSheet.test.tsx src/lib/preferenceReload.test.ts`
Expected: PASS.

- [ ] **Step 2: Run TypeScript**

Run: `npm run typecheck`
Expected: exit 0.

- [ ] **Step 3: Review UI at phone dimensions**

Verify 360x800 and 412x915: no text controls, no overlap, recorder line remains inside composer, and buttons do not shift between states.

