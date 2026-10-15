# Adaptive Chat Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a per-user Living, Calm, and Adaptive live presentation to Desk Chat Mode while preserving Code Mode and all underlying run observability.

**Architecture:** An authenticated backend preference service is the single source of truth for the Desk UI and Jarvis tool. Desk receives that state through a provider, derives a bounded Chat-only presentation from existing stream blocks, and renders it through an explicit `MessageRow` surface boundary; Code Mode keeps its existing renderer and pacing unchanged.

**Tech Stack:** Python 3.11, FastAPI, SQLite, pytest, React 19, TypeScript, Vitest, React Testing Library, existing CSS and SSE reducer.

**Spec:** `docs/superpowers/specs/2026-10-15-adaptive-chat-flow-design.md`

## Global Constraints

- Code Mode's `RaekkeTranskript`, `usePacedBlocks`, visuals, grouping, and existing `jarvis-desk:raekkevisning` value remain unchanged.
- Chat Mode uses only `living`, `calm`, or `adaptive`; default is `living`.
- Do not rewrite SSE, `streamReducer`, `useChatScroll`, execution semantics, or mobile.
- Do not generate additional syntheses or make additional LLM calls.
- User-facing UI copy is Danish; code comments and documentation are English.
- No new npm package, Docker, production restart, push, or deployment.
- Follow TDD: each production behavior is preceded by a focused failing test whose expected failure is observed.
- The user requested one delivered commit. Do not create interim implementation commits. At completion, stage only intended paths and amend the existing design checkpoint through `scripts/commit_with_attribution.py --amend` with the required feature message.
- `core/tools/simple_tools.py` and `core/tools/simple_tools_definitions.py` are oversized and must not be edited. Extend their already-imported `desk_view_tools` fragment instead.

## Review Focus

- A live run that receives text but never receives `final_answer_start` must reveal all text exactly once on completion, interruption, or failure; Task 5 and Task 7 add this test.
- Two windows racing for first-run onboarding must produce one live comparison and must not mark it seen before paint; Task 2 and Task 6 add this test.
- A native owner with an empty legacy id must resolve only from verified owner context, while an empty guest/member context fails closed; Task 1 and Task 3 add this test.
- Account switching while a cached request is in flight must never render or persist the previous user's preference; Task 4 adds this test.
- Required actions and non-text rich blocks must remain visible outside the collapsed summary; Task 6 and Task 7 add this test.

---

### Task 1: Authenticated preference persistence

**Files:**
- Create: `core/services/chat_flow_preferences.py`
- Modify: `core/runtime/db_schema.py`
- Test: `tests/test_chat_flow_preferences.py`

**Interfaces:**
- Produces: `resolve_chat_flow_principal() -> str`
- Produces: `get_chat_flow_state(principal_id: str) -> dict[str, object]`
- Produces: `set_chat_flow_state(principal_id: str, *, preference: str | None = None, suggestions_enabled: bool | None = None, explicit: bool = False) -> dict[str, object]`
- Produces: `claim_chat_flow_onboarding(principal_id: str, run_id: str, *, now: datetime | None = None) -> dict[str, object]`
- Produces: `ack_chat_flow_onboarding(principal_id: str, claim_id: str) -> dict[str, object]`
- Produces: `record_chat_flow_observation(principal_id: str, *, meaningful_steps: int, expanded_work: bool, manual_override: str | None) -> dict[str, object]`
- Produces: `record_chat_flow_suggestion(principal_id: str, *, kind: str, outcome: str) -> dict[str, object]`

- [ ] **Step 1: Write failing service tests**

Add tests proving the default is `living`, two principals remain isolated, invalid values fail, no raw text field exists, empty non-owner identity fails, verified owner with an empty id maps to a reserved owner principal, onboarding claims are atomic and expire, acknowledgement requires the matching claim, and observations store counters only.

```python
def test_empty_verified_owner_gets_stable_reserved_principal():
    token = set_context(workspace_name="bjorn", user_id="", role="owner")
    try:
        assert resolve_chat_flow_principal() == "native-owner"
    finally:
        reset_context(token)

def test_onboarding_is_claimed_once_and_seen_only_after_ack():
    first = claim_chat_flow_onboarding("user-a", "run-1", now=NOW)
    second = claim_chat_flow_onboarding("user-a", "run-2", now=NOW)
    assert first["claimed"] is True
    assert second["claimed"] is False
    assert get_chat_flow_state("user-a")["onboarding_seen"] is False
    ack_chat_flow_onboarding("user-a", first["claim_id"])
    assert get_chat_flow_state("user-a")["onboarding_seen"] is True
```

- [ ] **Step 2: Run the service tests and observe the expected import/schema failures**

Run: `conda run -n ai python -m pytest tests/test_chat_flow_preferences.py -q`

- [ ] **Step 3: Add the schema and minimal service**

Add `_ensure_chat_flow_preferences_table(conn)` to `db_schema.py` and call it from `init_db()`. Store preference, explicit choice, onboarding claim/expiry, suggestion state, bounded counters, and UTC timestamps. Implement all updates as SQLite upserts or guarded updates. The principal resolver must require a token-backed role and must never use `effective_role()` because a TOTP elevation does not transfer preference ownership.

```python
VALID_PREFERENCES = frozenset({"living", "calm", "adaptive"})
NATIVE_OWNER_PRINCIPAL = "native-owner"

def resolve_chat_flow_principal() -> str:
    role = current_role()
    user_id = current_user_id().strip()
    if role not in {"owner", "partner", "member", "guest"}:
        raise ChatFlowIdentityError("verified authenticated identity required")
    if user_id:
        return f"user:{user_id}"
    if role == "owner":
        return NATIVE_OWNER_PRINCIPAL
    raise ChatFlowIdentityError("stable authenticated user id required")
```

- [ ] **Step 4: Run service tests green and run the DB schema regression tests**

Run: `conda run -n ai python -m pytest tests/test_chat_flow_preferences.py tests/test_db_governance.py -q`

### Task 2: Self-scoped Chat Flow API

**Files:**
- Create: `apps/api/jarvis_api/routes/chat_flow_preferences.py`
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_chat_flow_routes.py`

**Interfaces:**
- Consumes: Task 1 service functions.
- Produces: `GET /api/chat-flow/preferences`
- Produces: `PATCH /api/chat-flow/preferences`
- Produces: `POST /api/chat-flow/onboarding/claim`
- Produces: `POST /api/chat-flow/onboarding/ack`
- Produces: `POST /api/chat-flow/observations`
- Produces: `POST /api/chat-flow/suggestions/outcome`

- [ ] **Step 1: Write failing route security and ownership tests**

Build a small FastAPI test app with middleware-bound contexts. Verify default reads, same-user writes, invalid enum 422/400 behavior, inability to submit `user_id`, unauthenticated mutation rejection, owner-empty-id support, cross-user isolation, atomic onboarding claim, and matching acknowledgement.

```python
def test_patch_has_no_user_id_escape_hatch(client_for):
    owner = client_for("owner-a", "owner")
    response = owner.patch("/api/chat-flow/preferences", json={
        "preference": "calm", "user_id": "victim"
    })
    assert response.status_code == 422
    assert client_for("victim", "member").get("/api/chat-flow/preferences").json()["preference"] == "living"
```

- [ ] **Step 2: Run route tests and observe missing-route failures**

Run: `conda run -n ai python -m pytest tests/test_chat_flow_routes.py -q`

- [ ] **Step 3: Implement strict Pydantic request models and route registration**

Set Pydantic models to forbid extra fields. Resolve the principal inside every handler; never accept it in a request model. Map identity errors to 401/403 and validation errors to 400. Return the complete persisted state after mutations.

- [ ] **Step 4: Run route and startup tests green**

Run: `conda run -n ai python -m pytest tests/test_chat_flow_routes.py tests/test_smoke_test_startup.py -q`

### Task 3: Jarvis-controlled preference tool

**Files:**
- Modify: `core/tools/desk_view_tools.py`
- Modify: `core/tools/tool_scoping.py`
- Test: `tests/test_chat_flow_tool.py`
- Test: `tests/test_tool_scoping.py`

**Interfaces:**
- Consumes: `resolve_chat_flow_principal()` and `set_chat_flow_state()` from Task 1.
- Produces tool: `set_chat_flow_preference(preference?, suggestions_enabled?)`.

- [ ] **Step 1: Write failing tool and scope tests**

Verify the definition has no user-id property, accepts only the three preference values, persists through the shared service, returns actual state, fails with no verified identity, isolates member users, and is included in Chat Mode for all authenticated roles without becoming an unrestricted cross-user tool.

```python
def test_tool_schema_cannot_choose_a_user():
    definition = next(d for d in DESK_VIEW_TOOL_DEFINITIONS
                      if d["function"]["name"] == "set_chat_flow_preference")
    assert "user_id" not in definition["function"]["parameters"]["properties"]
```

- [ ] **Step 2: Run tests and observe the missing tool failure**

Run: `conda run -n ai python -m pytest tests/test_chat_flow_tool.py tests/test_tool_scoping.py -q`

- [ ] **Step 3: Extend the existing Desk tool fragment**

Add the definition and handler to `desk_view_tools.py`, using the same service as the API. Permit at least one of `preference` or `suggestions_enabled`, reject unknown values, and add `set_chat_flow_preference` to `CHAT_MODE_TOOLS_BASE`. Do not edit the oversized central tool aggregators because they already spread this module's definitions and handlers.

- [ ] **Step 4: Run tool tests green**

Run: `conda run -n ai python -m pytest tests/test_chat_flow_tool.py tests/test_tool_scoping.py -q`

### Task 4: Desk preference provider and isolated settings

**Files:**
- Create: `apps/jarvis-desk/src/lib/chatFlowApi.ts`
- Create: `apps/jarvis-desk/src/contexts/ChatFlowContext.tsx`
- Create: `apps/jarvis-desk/src/hooks/useChatFlow.ts`
- Create: `apps/jarvis-desk/src/contexts/ChatFlowContext.test.tsx`
- Modify: `apps/jarvis-desk/src/App.tsx`
- Modify: `apps/jarvis-desk/src/components/settings/ThemeSection.tsx`
- Modify: `apps/jarvis-desk/src/components/settings/ThemeSection.test.tsx`
- Modify: `apps/jarvis-desk/src/lib/visningsPref.ts`
- Test: `apps/jarvis-desk/src/lib/visningsPref.test.ts`

**Interfaces:**
- Produces: `ChatFlowPreference = 'living' | 'calm' | 'adaptive'`.
- Produces: `useChatFlow()` with `{ state, activeModeForRun, setPreference, claimOnboarding, acknowledgeOnboarding, recordObservation, recordSuggestionOutcome }`.
- Preserves: `useRaekkevisning()` and `RAEKKE_KEY` as Code Mode-only behavior.

- [ ] **Step 1: Write failing provider and settings isolation tests**

Test server hydration, default Living fallback, per-user cache namespace, stale-response rejection after an account switch, cross-window storage updates, failed persistence retaining last confirmed state, active-view updates, legacy row-value preservation, and the exact two settings groups.

```tsx
it('does not apply a late response from the previous account', async () => {
  const first = deferred<ChatFlowState>()
  mockGet.mockReturnValueOnce(first.promise).mockResolvedValueOnce(calmState)
  const view = renderProvider({ userId: 'a' })
  view.rerender(provider({ userId: 'b' }))
  first.resolve(livingState)
  await waitFor(() => expect(screen.getByTestId('preference')).toHaveTextContent('calm'))
})
```

- [ ] **Step 2: Run focused tests and observe missing-provider/settings failures**

Run: `cd apps/jarvis-desk && npm test -- src/contexts/ChatFlowContext.test.tsx src/components/settings/ThemeSection.test.tsx src/lib/visningsPref.test.ts`

- [ ] **Step 3: Implement API client and provider**

Use the existing authenticated `apiFetch` mechanism from a dedicated `chatFlowApi.ts`. Mount `ChatFlowProvider` in `App` only after settings/auth are known, pass the authenticated `WhoAmI`, and key any local cache as `jarvis-desk:chat-flow:` followed by the authenticated user id or the literal `native-owner`. Guard asynchronous results with the identity key captured at request start.

- [ ] **Step 4: Split settings into the exact Code Mode and Chat Mode groups**

Keep the existing checkbox and storage key under `Code Mode` with label `Rækkevisning`. Add an accessible radio group under `Chat Mode` with `Levende`, `Rolig`, and `Adaptiv` plus the approved descriptions. `writeRaekkevisning` may only notify Code consumers; Chat Flow reads only its provider.

- [ ] **Step 5: Run focused tests green**

Run: `cd apps/jarvis-desk && npm test -- src/contexts/ChatFlowContext.test.tsx src/components/settings/ThemeSection.test.tsx src/lib/visningsPref.test.ts`

### Task 5: Pure Chat Flow model and Chat-only pacing

**Files:**
- Create: `apps/jarvis-desk/src/lib/chatFlowModel.ts`
- Create: `apps/jarvis-desk/src/lib/chatFlowModel.test.ts`
- Create: `apps/jarvis-desk/src/lib/useChatPacedBlocks.ts`
- Create: `apps/jarvis-desk/src/lib/useChatPacedBlocks.test.tsx`

**Interfaces:**
- Produces: `deriveChatFlow(input: ChatFlowInput) -> ChatFlowModel`.
- Produces: `chooseAdaptiveMode(snapshot: AdaptiveSnapshot) -> 'living' | 'calm'`.
- Produces: `useChatPacedBlocks(blocks: ContentBlock[], options: { live: boolean; finalAnswerStarted: boolean })`.

- [ ] **Step 1: Write failing activity-model tests**

Cover one through four syntheses, hard three-line cap, oldest removal, whitespace deduplication, round continuity, Calm latest-only projection, no synthesis fallback, tool logs excluded from visible status, rich/required blocks retained, authoritative final transition, no empty summary for a direct answer, and honest failed/interrupted labels.

```ts
it('keeps only the latest three unique synthesis lines', () => {
  const model = deriveChatFlow(inputWithSummaries(['Et', 'To', 'Tre', 'Fire']))
  expect(model.visibleSynthesis).toEqual(['To', 'Tre', 'Fire'])
})

it('does not treat the first text delta as a final answer', () => {
  const model = deriveChatFlow({ ...base, blocks: [{ type: 'text', text: 'foreløbig' }], finalAnswerStarted: false })
  expect(model.finalBlocks).toEqual([])
  expect(model.workBlocks).toContainEqual({ type: 'text', text: 'foreløbig' })
})
```

- [ ] **Step 2: Write failing deterministic Adaptive tests**

Verify selection uses only the run-start snapshot, defaults Living on uncertainty, repeated prior low-work observations can select Calm, repeated detail expansion selects Living, a single short exchange does not create a preference change, and subsequent current-run observations cannot mutate the selected mode.

- [ ] **Step 3: Run model tests and observe missing-module failures**

Run: `cd apps/jarvis-desk && npm test -- src/lib/chatFlowModel.test.ts`

- [ ] **Step 4: Implement the pure derivation and selector**

Normalize only meaningful existing summaries (`tool_use_summary`, `rundeEtiketter`, `tankeResumeer`, and truthful `workingStep`). Partition final text only after `finalAnswerStarted`; on terminal fallback, promote retained text exactly once. Keep rich blocks in their original order and return stable arrays where inputs have not changed.

- [ ] **Step 5: Write and run failing pacing tests**

Use mocked animation frames to prove incremental low-latency output, bounded lag under a fast source, Unicode safety, immediate completion flush, tool blocks appearing immediately, and no text reuse across runs.

Run: `cd apps/jarvis-desk && npm test -- src/lib/useChatPacedBlocks.test.tsx`

- [ ] **Step 6: Implement bounded frame pacing and run both suites green**

Keep only a cursor for the current final text block, schedule at most one frame, cap backlog, accelerate when behind, cancel on unmount/run change, and return source blocks immediately when `live` becomes false.

Run: `cd apps/jarvis-desk && npm test -- src/lib/chatFlowModel.test.ts src/lib/useChatPacedBlocks.test.tsx`

### Task 6: Living, Calm, onboarding, summary, and suggestions UI

**Files:**
- Create: `apps/jarvis-desk/src/components/rich/ChatFlowPresentation.tsx`
- Create: `apps/jarvis-desk/src/components/rich/ChatFlowPresentation.test.tsx`
- Create: `apps/jarvis-desk/src/components/rich/ChatFlowOnboarding.tsx`
- Create: `apps/jarvis-desk/src/components/rich/ChatFlowOnboarding.test.tsx`
- Create: `apps/jarvis-desk/src/components/rich/ChatFlowSuggestion.tsx`
- Create: `apps/jarvis-desk/src/components/rich/ChatFlowSuggestion.test.tsx`
- Create: `apps/jarvis-desk/src/styles/chat-flow.css`

**Interfaces:**
- Consumes: Task 4 provider and Task 5 model/pacing.
- Produces: `<ChatFlowPresentation blocks={blocks} mode={mode} streaming={streaming} status={status} finalAnswerStarted={finalAnswerStarted} workingStep={workingStep} rundeEtiketter={rundeEtiketter} tankeResumeer={tankeResumeer} />` plus the existing message identity/configuration props required by rich blocks.
- Produces: live two-phase onboarding and post-turn suggestion controls.

- [ ] **Step 1: Write failing Living and Calm component tests**

Assert the exact visible counts and replacement behavior, no placeholders, real synthesis copy, neutral Calm fallback, summary disclosure, final answer streaming beneath it, no raw tool log in main activity, required action/rich blocks outside the disclosure, truthful failure/interruption UI, and reduced-motion class/behavior.

- [ ] **Step 2: Run presentation tests and observe missing-component failures**

Run: `cd apps/jarvis-desk && npm test -- src/components/rich/ChatFlowPresentation.test.tsx`

- [ ] **Step 3: Implement presentation and CSS**

Use keyed synthesis rows in a fixed bounded viewport. CSS transitions use 180 ms, 6 px, opacity, and existing Desk tokens; `@media (prefers-reduced-motion: reduce)` removes transitions/transforms. Use a single `role="status"`/polite announcement for the latest bounded status. Render expanded work with existing rich block primitives, filtering final blocks so text is not duplicated.

- [ ] **Step 4: Write failing live onboarding tests**

Prove both previews consume one changing model, B shows up to three while C shows one, the answer remains singular and streaming, claim happens once, acknowledgement happens only after the comparison mounts, ignored choice keeps default Living without `explicit_user_choice`, insufficient activity is labeled `Eksempel`, keyboard controls work, and a failed claim never blocks the answer.

- [ ] **Step 5: Implement onboarding and run its tests green**

Use a post-paint effect (`requestAnimationFrame` followed by acknowledgement) only after the comparison DOM exists. Render the same `ChatFlowModel` into both previews and never invoke chat transport from the onboarding component.

- [ ] **Step 6: Write failing suggestion tests and implement the inline suggestion**

Prove it is absent during streaming/onboarding, respects the 14-day server decision and suppression state, persists each action, disables suggestions permanently, and does not steal focus.

Run: `cd apps/jarvis-desk && npm test -- src/components/rich/ChatFlowPresentation.test.tsx src/components/rich/ChatFlowOnboarding.test.tsx src/components/rich/ChatFlowSuggestion.test.tsx`

### Task 7: Integrate active and historical Chat messages without changing Code Mode

**Files:**
- Modify: `apps/jarvis-desk/src/components/rich/MessageRow.tsx`
- Modify: `apps/jarvis-desk/src/components/rich/MessageRow.test.tsx`
- Modify: `apps/jarvis-desk/src/views/ChatView.tsx`
- Modify: `apps/jarvis-desk/src/views/ChatView.test.tsx`
- Modify: `apps/jarvis-desk/src/views/CodeView.tsx`
- Modify: `apps/jarvis-desk/src/views/CodeView.test.tsx`
- Modify: `apps/jarvis-desk/src/App.tsx`
- Test: `apps/jarvis-desk/src/lib/useChatScroll.test.ts`

**Interfaces:**
- Extends `MessageRow` with explicit `presentation: 'chat' | 'code'` and live status inputs.
- ChatView passes `presentation="chat"` for persisted, primary live, and followed-run messages.
- CodeView passes `presentation="code"` and otherwise retains its prior props and renderer path.

- [ ] **Step 1: Write failing surface-isolation tests**

Set `RAEKKE_KEY=1` and verify Chat still renders `ChatFlowPresentation`, then verify Code still renders `RaekkeTranskript`. Change Chat preference and verify Code markup is unchanged; change row preference and verify Chat markup is unchanged. Cover active and historical messages.

- [ ] **Step 2: Run isolation tests and observe the old global behavior fail**

Run: `cd apps/jarvis-desk && npm test -- src/components/rich/MessageRow.test.tsx src/views/ChatView.test.tsx src/views/CodeView.test.tsx`

- [ ] **Step 3: Add the explicit presentation branch**

Call `usePacedBlocks` only for the Code assistant path and `useChatPacedBlocks` only for the Chat assistant path. User messages retain their existing bubble behavior. Historical Chat messages use terminal fallback semantics and no entry animation. Preserve shared artifact, edited-file, source, action, image, file, widget, citation, and error rendering.

- [ ] **Step 4: Wire run-stable Adaptive selection and lifecycle**

At a Chat run's first observed `activeRunId`, ask the provider for one active mode and cache it by run id. Pass `stream.status`, `workingStep`, labels, summaries, run id, and final signal into the live Chat row. Record bounded counters only after terminal state. Followed runs use their own stable run id. Persisted messages never re-trigger onboarding or observation writes.

- [ ] **Step 5: Add missing-signal, reconciliation, and scroll regression tests**

Verify completion promotes all text once, interrupted/error states preserve partial text with honest labels, direct persisted answers render normally, live-to-persisted reconciliation does not duplicate, synthesis replacement does not add a scroll writer, bottom-following continues, and manual upward scrolling remains respected.

- [ ] **Step 6: Run integration and existing renderer/scroll suites green**

Run: `cd apps/jarvis-desk && npm test -- src/components/rich/MessageRow.test.tsx src/components/rich/MessageRow.donecrash.test.tsx src/components/rich/MessageRow.streamcrash.test.tsx src/components/rich/RaekkeTranskript.test.tsx src/views/ChatView.test.tsx src/views/CodeView.test.tsx src/lib/useChatScroll.test.ts src/contexts/SessionContext.test.tsx`

### Task 8: Mutation proof, documentation, full verification, and single commit

**Files:**
- Modify: `DEVLOG.md`
- Modify: `STATUS.md`
- Amend: all files introduced or changed by Tasks 1–7 plus the approved spec and this plan.

**Interfaces:**
- Consumes all earlier tasks.
- Produces one attributed feature commit and no deployment.

- [ ] **Step 1: Mutation-prove the five critical contracts**

For each mutation below, make the one-line temporary change with `apply_patch`, run the named focused test and observe a failure for the intended assertion, then restore with `apply_patch` and rerun green:

1. Ignore `presentation="chat"` and consult `RAEKKE_KEY` → mode-isolation test fails.
2. Change visible synthesis slice from `-3` to `-4` → three-line-limit test fails.
3. Treat any text delta as final → authoritative-transition test fails.
4. Accept a request/model `user_id` or bypass the context principal → ownership test fails.
5. Set `onboarding_seen` during claim rather than acknowledgement → onboarding test fails.

- [ ] **Step 2: Update durable documentation**

Add English entries to `DEVLOG.md` and `STATUS.md` covering Living/Calm/Adaptive, live single-run onboarding, per-user storage and endpoints, the Jarvis tool, strict Chat/Code isolation, fallback behavior, accessibility, and the exact verification results obtained below.

- [ ] **Step 3: Run complete frontend verification**

Run from `apps/jarvis-desk`:

```bash
npm test
npm run lint
npm run build:renderer
```

Read every exit code and report any unrelated existing failure separately rather than changing it casually.

- [ ] **Step 4: Run backend and syntax verification**

Run from the repository root:

```bash
conda run -n ai python -m pytest tests/test_chat_flow_preferences.py tests/test_chat_flow_routes.py tests/test_chat_flow_tool.py tests/test_tool_scoping.py tests/test_smoke_test_startup.py -q
python -m compileall core apps/api scripts
git diff --check
```

- [ ] **Step 5: Review the diff against every acceptance criterion**

Confirm Code Mode files have only the explicit surface prop required for isolation, no mobile/SSE/reducer changes exist, no raw conversation text is stored, all required rich blocks remain reachable, no new dependency exists, and `git status --short` contains only intended files.

- [ ] **Step 6: Stage intended files and amend into the one required feature commit**

Stage exactly the paths listed in the Tasks above, after confirming each one appears in `git status --short`. Invoke the attribution wrapper with one `--path` argument for each staged path; the authoritative path list is the staged output from `git diff --cached --name-only`, and it must contain no unrelated file. Use this exact commit message:

```bash
python scripts/commit_with_attribution.py --repo . --actor codex \
  --origin interactive --approved-by bjorn --amend \
  --message 'feat(desk): add adaptive chat flow with living and calm streaming' \
  --path docs/superpowers/specs/2026-10-15-adaptive-chat-flow-design.md \
  --path docs/superpowers/plans/2026-10-15-adaptive-chat-flow.md \
  --path core/services/chat_flow_preferences.py \
  --path core/runtime/db_schema.py \
  --path apps/api/jarvis_api/routes/chat_flow_preferences.py \
  --path apps/api/jarvis_api/app.py \
  --path core/tools/desk_view_tools.py \
  --path core/tools/tool_scoping.py \
  --path tests/test_chat_flow_preferences.py \
  --path tests/test_chat_flow_routes.py \
  --path tests/test_chat_flow_tool.py \
  --path tests/test_tool_scoping.py \
  --path apps/jarvis-desk/src/lib/chatFlowApi.ts \
  --path apps/jarvis-desk/src/contexts/ChatFlowContext.tsx \
  --path apps/jarvis-desk/src/contexts/ChatFlowContext.test.tsx \
  --path apps/jarvis-desk/src/hooks/useChatFlow.ts \
  --path apps/jarvis-desk/src/lib/chatFlowModel.ts \
  --path apps/jarvis-desk/src/lib/chatFlowModel.test.ts \
  --path apps/jarvis-desk/src/lib/useChatPacedBlocks.ts \
  --path apps/jarvis-desk/src/lib/useChatPacedBlocks.test.tsx \
  --path apps/jarvis-desk/src/lib/visningsPref.ts \
  --path apps/jarvis-desk/src/lib/visningsPref.test.ts \
  --path apps/jarvis-desk/src/components/settings/ThemeSection.tsx \
  --path apps/jarvis-desk/src/components/settings/ThemeSection.test.tsx \
  --path apps/jarvis-desk/src/components/rich/ChatFlowPresentation.tsx \
  --path apps/jarvis-desk/src/components/rich/ChatFlowPresentation.test.tsx \
  --path apps/jarvis-desk/src/components/rich/ChatFlowOnboarding.tsx \
  --path apps/jarvis-desk/src/components/rich/ChatFlowOnboarding.test.tsx \
  --path apps/jarvis-desk/src/components/rich/ChatFlowSuggestion.tsx \
  --path apps/jarvis-desk/src/components/rich/ChatFlowSuggestion.test.tsx \
  --path apps/jarvis-desk/src/components/rich/MessageRow.tsx \
  --path apps/jarvis-desk/src/components/rich/MessageRow.test.tsx \
  --path apps/jarvis-desk/src/views/ChatView.tsx \
  --path apps/jarvis-desk/src/views/ChatView.test.tsx \
  --path apps/jarvis-desk/src/views/CodeView.tsx \
  --path apps/jarvis-desk/src/views/CodeView.test.tsx \
  --path apps/jarvis-desk/src/App.tsx \
  --path apps/jarvis-desk/src/styles/chat-flow.css \
  --path DEVLOG.md \
  --path STATUS.md
```

Verify the final commit and working tree with `git status --short --branch` and `git log -1 --format=fuller`. Do not push, tag, deploy, or restart services.
