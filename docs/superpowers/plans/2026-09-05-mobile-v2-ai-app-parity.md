# Mobile V2 AI App Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis Mobile V2 first-class mobile surfaces for the eight app gaps: Work review, new task, steer/cancel, memory control, artifacts, live multimodal entry, research mode, and per-turn model/tool controls.

**Architecture:** Keep runtime state server-owned. The app adds typed clients and UI over existing endpoints first, with honest unavailable states where server capabilities do not exist yet. The Work room becomes the control plane; Chat remains the fast conversation plane.

**Tech Stack:** React Native 0.85, Expo 56, TypeScript 6, Jest, existing Jarvis `/chat`, `/mc`, `/api`, `/central` endpoints.

**Spec:** `docs/superpowers/specs/2026-09-02-jarvis-mobile-companion-v2-remote-design.md`

## Global Constraints

- Work only in the mobile worktree branch, not `main`.
- Use existing mobile patterns: modal screens, typed `lib/*Api.ts` clients, Jest tests beside changed files.
- No production behavior without a failing test first.
- Keep server-authoritative state; do not create local-only task truth.
- Capability gaps must be visible as unavailable/limited, not silently hidden.
- Preserve DeepSeek/provider cache behavior by leaving existing provider/model request fields compatible.

---

### Task 1: Work Review Tab

**Files:**
- Modify: `apps/mobile/src/screens/WorkScreen.tsx`
- Create: `apps/mobile/src/lib/workReviewApi.ts`
- Create: `apps/mobile/src/components/WorkReviewCard.tsx`
- Test: `apps/mobile/src/lib/workReviewApi.test.ts`
- Test: `apps/mobile/src/components/WorkReviewCard.test.tsx`
- Test: `apps/mobile/src/screens/WorkScreen.test.tsx`

**Interfaces:**
- Consumes: `ApiConfig`, `/mc/runs/{run_id}`, `/api/dispatches`, `/api/dispatches/{task_id}/diff`
- Produces: `fetchWorkReviews(config): Promise<WorkReview[]>`

- [ ] Add failing tests for normalising dispatch diffs and run detail summaries.
- [ ] Implement `workReviewApi.ts`.
- [ ] Add `Review` tab and compact cards.
- [ ] Run targeted tests and commit.

### Task 2: New Task Flow

**Files:**
- Modify: `apps/mobile/src/screens/WorkScreen.tsx`
- Create: `apps/mobile/src/components/NewWorkTaskSheet.tsx`
- Test: `apps/mobile/src/components/NewWorkTaskSheet.test.tsx`
- Test: `apps/mobile/src/screens/WorkScreen.test.tsx`

**Interfaces:**
- Consumes: existing `stream.send(config, sessionId, text, { mode: 'code' | 'cowork', model, providerChoice })`
- Produces: a mobile Work entry that starts a server-owned run through a normal session.

- [ ] Add failing tests for prompt construction and submit disabling.
- [ ] Implement sheet fields: mode, project/root text, branch text, instruction.
- [ ] Start a session and send with `mode: 'code'` by default.
- [ ] Run targeted tests and commit.

### Task 3: Steer And Cancel Work Runs

**Files:**
- Modify: `apps/mobile/src/lib/apiClient.ts`
- Modify: `apps/mobile/src/components/WorkTaskCard.tsx`
- Modify: `apps/mobile/src/screens/WorkScreen.tsx`
- Test: `apps/mobile/src/lib/apiClient.test.ts`
- Test: `apps/mobile/src/components/WorkTaskCard.test.tsx`

**Interfaces:**
- Consumes: `POST /chat/runs/{run_id}/steer`, `POST /chat/runs/{run_id}/cancel`
- Produces: `steerRun(config, runId, content)` and `cancelRunById(config, runId)`

- [ ] Add failing tests for endpoint paths and disabled states.
- [ ] Implement client helpers.
- [ ] Add run card actions for active runs.
- [ ] Run targeted tests and commit.

### Task 4: Memory Control Screen

**Files:**
- Modify: `apps/mobile/src/screens/SettingsScreen.tsx`
- Create: `apps/mobile/src/screens/MemoryScreen.tsx`
- Create: `apps/mobile/src/lib/memoryApi.ts`
- Test: `apps/mobile/src/lib/memoryApi.test.ts`
- Test: `apps/mobile/src/screens/MemoryScreen.test.tsx`

**Interfaces:**
- Consumes: `/central/mind?section=memory`, `/chat/sessions` fallback, data controls export/delete.
- Produces: read-only memory review with clear links to export/delete until edit endpoints exist.

- [ ] Add failing tests for memory item normalisation.
- [ ] Implement read-only memory client with fallback empty state.
- [ ] Add settings entry and screen.
- [ ] Run targeted tests and commit.

### Task 5: Artifacts Surface

**Files:**
- Modify: `apps/mobile/src/components/SidePanel.tsx`
- Create: `apps/mobile/src/screens/ArtifactsScreen.tsx`
- Create: `apps/mobile/src/lib/artifactsApi.ts`
- Test: `apps/mobile/src/lib/artifactsApi.test.ts`
- Test: `apps/mobile/src/screens/ArtifactsScreen.test.tsx`

**Interfaces:**
- Consumes: attachments, dispatch diffs, and message code/file blocks as artifact candidates.
- Produces: a mobile artifact library surface with unavailable-state if no server artifact index exists.

- [ ] Add failing tests for artifact candidate normalisation.
- [ ] Implement artifact client with graceful empty/error.
- [ ] Add side panel entry and modal screen.
- [ ] Run targeted tests and commit.

### Task 6: Live Multimodal Entry

**Files:**
- Modify: `apps/mobile/src/screens/CameraCapture.tsx`
- Modify: `apps/mobile/src/components/VoiceOverlay.tsx`
- Test: `apps/mobile/src/screens/CameraCapture.test.tsx`
- Test: `apps/mobile/src/components/VoiceOverlay.test.tsx`

**Interfaces:**
- Consumes: existing photo capture/upload and voice hook.
- Produces: explicit “live context not yet supported” affordance plus fast photo-to-voice workflow.

- [ ] Add failing tests for live-context unavailable copy/action.
- [ ] Add visible control in voice overlay to attach camera context.
- [ ] Keep photo upload path unchanged.
- [ ] Run targeted tests and commit.

### Task 7: Research Mode

**Files:**
- Modify: `apps/mobile/src/components/Composer.tsx`
- Modify: `apps/mobile/src/screens/ChatScreen.tsx`
- Test: `apps/mobile/src/components/Composer.test.tsx`
- Test: `apps/mobile/src/screens/ChatScreen.test.tsx`

**Interfaces:**
- Consumes: existing `mode`/message fields and backend tools.
- Produces: per-turn research hint in prompt text without changing provider cache shape.

- [ ] Add failing tests for research toggle label and prompt prefix.
- [ ] Add compact composer control.
- [ ] Prefix one turn with a clear research instruction when enabled.
- [ ] Run targeted tests and commit.

### Task 8: Per-Turn Controls

**Files:**
- Modify: `apps/mobile/src/components/ModelPicker.tsx`
- Modify: `apps/mobile/src/components/Composer.tsx`
- Modify: `apps/mobile/src/lib/streamClient.ts`
- Test: `apps/mobile/src/components/ModelPicker.test.tsx`
- Test: `apps/mobile/src/components/Composer.test.tsx`
- Test: `apps/mobile/src/lib/streamClient.test.ts`

**Interfaces:**
- Consumes: existing `thinkingMode`, `approvalMode`, `model`, `providerChoice`
- Produces: visible fast/think and ask/trust controls while preserving existing request field names.

- [ ] Add failing tests for request body compatibility.
- [ ] Expose controls in composer/model sheet.
- [ ] Ensure default request remains identical to current behavior.
- [ ] Run targeted tests and commit.
