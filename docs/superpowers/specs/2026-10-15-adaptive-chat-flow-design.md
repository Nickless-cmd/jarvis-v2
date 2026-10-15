# Adaptive Chat Flow Design

**Date:** 2026-10-15  
**Status:** Approved architecture, implementation specification  
**Primary application:** `apps/jarvis-desk`  
**Product principle:** Code Mode is for watching Jarvis work. Chat Mode is for talking with Jarvis.

## 1. Purpose

Jarvis Desk Chat Mode must present live agentic work as a smooth, calm conversation rather than a growing execution transcript. The same underlying run, tools, approvals, media, files, widgets, citations, errors, and observability remain intact. Only Chat Mode's presentation changes.

The feature introduces three Chat Mode preferences:

- `living`: show up to three rolling, meaningful synthesis lines.
- `calm`: show only the latest meaningful status.
- `adaptive`: choose `living` or `calm` deterministically for each run.

`living` is the default. All user-facing copy is Danish. Code comments and documentation are English.

## 2. Non-negotiable boundaries

- Code Mode keeps its current `RaekkeTranskript`, grouping, expanded rows, execution detail, preference default, and streaming behavior.
- The existing `jarvis-desk:raekkevisning` preference becomes Code Mode-only. Its key and existing values are preserved.
- Chat Mode never selects `RaekkeTranskript` because of the legacy row preference.
- Chat Mode has only `Levende`, `Rolig`, and `Adaptiv` presentation choices.
- Changing either mode's preference cannot affect the other mode.
- The SSE transport, execution semantics, `streamReducer`, stream ownership, reconnection behavior, and mobile app are not redesigned.
- Chat Flow does not enable or request additional thought summaries, syntheses, model classifications, or LLM calls.
- Existing `useChatScroll` remains the only scroll controller.
- No new npm dependency is required.

## 3. Presentation boundary

`MessageRow` receives an explicit surface or presentation input. `CodeView` passes the Code presentation and retains the existing decision between `RaekkeTranskript` and `BlocksRenderer`. `ChatView` passes the Chat presentation and delegates live assistant activity to a focused Chat Flow component.

Historical assistant messages also use the Chat presentation in Chat Mode. They render their persisted final content normally and expose persisted work details through the same compact expandable summary when such details exist. Code Mode continues to render those messages exactly as it does before this feature.

This explicit input is the isolation boundary. No component infers the surface from route state, global storage, or content shape.

## 4. Activity derivation

A pure derivation function consumes only existing run data:

- `blocks`
- `workingStep`
- `rundeEtiketter`
- `tankeResumeer`
- `finalAnswerStarted`
- completion, interruption, error, and required-interaction state already available to the message

It emits a small presentation model containing:

- deduplicated meaningful synthesis lines in arrival order;
- the latest truthful fallback status;
- work-detail blocks retained for expansion;
- whether the run has observable work worth summarizing;
- the terminal state: completed, interrupted, or failed.

The derivation never invents an action, converts every tool call into prose, or generates artificial reasoning. Exact repeated lines are removed after whitespace normalization. Agentic round boundaries do not reset the list. The retained visible list is bounded to the latest three items, while the underlying blocks remain available to the expandable work details and Mission Control.

Approvals, questions requiring user input, errors that require action, attachments, generated files, generated images, widgets, and citations remain rendered as first-class content. They are never hidden solely inside the compact activity summary.

## 5. Living and Calm presentations

### Living

The activity viewport starts with no placeholder rows. It grows from one to at most three real synthesis lines. On a fourth line, the oldest exits, the remaining lines move upward, and the newest enters from below.

Once populated, the viewport uses bounded row geometry so replacement does not create large scroll-height changes. The newest line has normal emphasis; older lines are slightly muted. Motion uses approximately 160–220 ms, 5–8 px of vertical displacement, opacity, and non-bouncy easing. There is no continuous decorative motion when data is unchanged.

### Calm

Calm displays only the newest meaningful synthesis or status. A new value replaces the old one with the same restrained motion language. If no meaningful progress exists, it displays the truthful fallback `Jarvis tænker ...`. Raw technical tool logs and agentic round counters are not placed in the main conversation.

### Reduced motion and assistive technology

`prefers-reduced-motion` disables decorative transforms and uses immediate stable replacement. Activity updates use one bounded, politely announced status rather than an aria-live entry per delta. No update moves keyboard focus. All disclosure and choice controls are keyboard reachable and have visible focus.

## 6. Work-to-answer state machine

`finalAnswerStarted` is the authoritative transition signal when it is present.

Before that signal, text deltas do not by themselves switch the message into final-answer mode. Intermediate text remains part of the underlying observable work and is not duplicated as final prose.

When `finalAnswerStarted` becomes true:

1. Freeze the activity list for the run.
2. Replace the live activity viewport with a compact work summary only if observable work exists.
3. Stream the actual final answer immediately below the summary.
4. Keep all underlying work expandable.

The summary uses truthful terminal copy. A successful completed run may use `Arbejdsforløb`; a failed or interrupted run cannot show a success checkmark or success wording.

### Missing-signal fallback

Content preservation takes precedence over presentation inference:

- While a run is active without `finalAnswerStarted`, received text remains retained in the message's underlying blocks and observable work details. A first text delta still does not assert final-answer state.
- When the stream completes normally without the signal, all retained assistant text is promoted once to visible final content. Direct answers therefore remain readable even when an older or degraded server omits the signal.
- When the stream is interrupted or fails without the signal, all received text is rendered once as preserved partial content with interrupted or failed status. It is not discarded and is not labeled as a successful final answer.
- If a historical persisted message has answer text but no transition metadata, that text renders as the normal answer. Persisted work blocks remain available separately.
- Reconciliation between the live and persisted message uses the existing message lifecycle and must not duplicate the answer.

If the server legitimately returns from final answer to tool work, the component preserves the confirmed answer text and reopens a truthful working state for subsequent work. It never reclassifies already confirmed prose as synthesis.

## 7. Chat-only text pacing

Code Mode retains `usePacedBlocks` unchanged.

Chat Mode uses a focused bounded pacing hook for the current live final-text block. It is coordinated with animation frames or an equivalent browser-scheduled mechanism, consumes real received deltas incrementally, and exposes text with low latency. It does not delay a complete response to simulate typing.

The pacing contract is:

- no unbounded backlog;
- bounded work per frame and accelerated catch-up when behind;
- immediate flush when the stream completes;
- Unicode-safe slicing;
- stable Markdown rendering through the existing renderer;
- no whole-transcript copying for every delta;
- no pacing changes to tool, media, approval, file, or widget blocks.

## 8. First-run live onboarding

On the first actual Chat Mode run for a user, the response includes an inline, side-by-side comparison:

- `B · Levende` shows the same run's rolling one-to-three-line activity.
- `C · Rolig` shows the same run's latest status.

Both previews subscribe to one derived activity model from one server run. They are live demonstrations, not static cards, and they never issue a second request or duplicate the final answer. If the run does not produce enough real synthesis to demonstrate the density difference, the preview may supplement it with copy explicitly labeled `Eksempel`; illustrative text is never represented as live Jarvis activity.

The controls are `Vælg levende`, `Vælg rolig`, and the secondary `Tilpas automatisk`. The real answer streams normally outside the comparison and remains fully interactive. Ignoring the selector keeps `living` without recording an explicit choice.

Onboarding is marked seen only after the comparison has actually mounted and painted. To prevent duplicate onboarding across Desk windows without marking an unseen UI as seen, persistence uses a short two-phase claim:

1. A client atomically claims onboarding for a run and receives a claim token. An unexpired claim prevents another window from showing it.
2. After the live comparison is rendered, that client acknowledges the claim and the server sets `onboarding_seen`.
3. An abandoned claim expires, allowing a later actual run to show onboarding.

If claim or acknowledgement persistence is temporarily unavailable, Chat Mode continues in `living` and never blocks the answer. It may offer onboarding on a later run because the server cannot truthfully record an unseen or unconfirmed presentation.

Existing users are treated as not onboarded and receive the comparison on their next actual Chat Mode run.

## 9. Per-user persistence and API

The server is the source of truth. A dedicated `chat_flow_preferences` table stores the smallest state needed for this feature:

- `principal_id` primary key;
- `preference`: `living`, `calm`, or `adaptive`;
- `onboarding_seen`;
- onboarding claim id and expiry;
- `explicit_user_choice`;
- `suggestions_enabled`;
- last suggestion kind/time and rejection count;
- compact non-content adaptation counters;
- `updated_at`.

No raw conversation text is persisted for Chat Flow adaptation.

Self-scoped endpoints read and update the current preference, claim/acknowledge onboarding, record bounded presentation observations, and record suggestion outcomes. The authenticated server context derives the target principal. Request payloads contain no mutable `user_id`.

A stable principal resolver uses the verified token-backed run/request context. A non-empty authenticated token subject is used directly. A reserved owner principal may be used only when the verified context proves the native owner role despite a legacy empty owner id. Missing or ambiguous authentication is rejected for mutation; a TOTP session elevation is not treated as ownership of another user's preference.

Desk may cache the last server state for fast rendering, but the cache key includes the authenticated identity. Logout, account switching, and invalid authentication clear or stop using the old namespace. Storage events update other Desk windows, and successful server mutations update active Chat views without restart. Failed writes retain a usable local `living` presentation, show non-disruptive failure feedback where appropriate, and do not leak another user's cached state.

## 10. Settings

Under `Arbejde → Generelt → Udseende`, two visually separate groups appear:

**Code Mode**

- `Rækkevisning`

This is the existing preference, existing key, and existing behavior.

**Chat Mode**

- `Levende` — `Viser op til tre løbende synteser, mens Jarvis arbejder.`
- `Rolig` — `Viser kun Jarvis' aktuelle arbejdsstatus.`
- `Adaptiv` — `Jarvis vælger automatisk den visning, der passer til samtalen.`

There is no legacy-row migration into Chat Mode. The only migration behavior is preserving the existing Code Mode value and assigning `living` to users without a Chat Flow preference.

## 11. Adaptive selection

Adaptive is opt-in. The active presentation is selected once when the run begins and remains stable until that run ends.

Selection may use only information already available at that time:

- the explicit `adaptive` permission;
- prior aggregate presentation observations;
- recent accepted or rejected suggestions;
- current request metadata already present before execution, such as attachment presence and coarse request size;
- prior-run complexity aggregates.

It cannot depend on future work steps, syntheses, or tool calls from the current run. Signals observed during the run update only later-run aggregates and cannot switch the active presentation.

The selector is deterministic and conservative:

- uncertainty chooses `living`;
- a single short message cannot create a lasting preference or suggestion;
- repeated direct low-work runs may choose `calm`;
- repeated multi-step or frequently expanded work may choose `living`;
- a manual per-run override wins immediately for the current run;
- selecting explicit `living` or `calm` exits Adaptive and is authoritative.

## 12. Suggestions

Suggestions are generated from bounded aggregate counters, not an LLM classifier. They appear only after a completed turn, never during first-run onboarding or active streaming.

The minimum cooldown is 14 days per suggestion direction. Rejection increments a direction-specific counter and strongly suppresses repeated proposals. The user can permanently disable suggestions. Complexity alone is insufficient; the rule requires a repeated behavioral pattern such as manual switching, detail expansion, or repeated acceptance of the alternate mode.

Suggestion UI is an inline conversational prompt, not a modal, toast, or notification-feed item. Actions persist an explicit choice, retain the current choice, enable Adaptive, or disable future suggestions.

## 13. Jarvis preference tool

The existing Desk-oriented tool module is extended with a narrowly scoped capability rather than adding registration logic to the oversized central tool files.

`set_chat_flow_preference` accepts only:

- `preference`: `living | calm | adaptive` when changing the presentation;
- `suggestions_enabled`: boolean when changing suggestion permission.

It never accepts a user id. Its handler resolves a verified authenticated principal from the run context and calls the same preference service as the self API. Missing, unverified, or ambiguous identity fails closed. The tool returns the actual persisted state and emits the normal observable tool result. It is available in Chat Mode through existing tool-scoping policy and does not change answer style, reasoning effort, or execution policy.

## 14. Error handling and observability

- Preference reads fail to `living` without blocking chat.
- Preference mutation failures do not claim success and preserve the last confirmed server state.
- Failed or interrupted runs use honest status and retain partial text.
- Required interaction surfaces remain outside collapsed work details.
- Expansion exposes original work blocks, including tool errors and results.
- Mission Control remains unchanged as the full operational view.
- Active and historical messages use the same content-preservation rules, with animation only on active messages.

## 15. Test strategy

Frontend Vitest and React Testing Library coverage must verify observable behavior, including:

- strict Chat/Code preference and rendering isolation;
- one, two, three, and four synthesis events with a hard visible maximum of three;
- deduplication and newest-line retention;
- Calm replacement and truthful fallback;
- authoritative `finalAnswerStarted` transition;
- completion, interruption, failure, and historical-message fallback without that signal;
- incremental Chat text pacing and immediate completion flush;
- live single-run side-by-side onboarding and acknowledgement only after render;
- user switching, storage synchronization, and failed persistence isolation;
- deterministic stable Adaptive selection and manual override;
- cooldown, rejection suppression, and suggestion disablement;
- reduced motion, bounded announcements, keyboard access, and existing scroll ownership;
- no duplication after live/persisted reconciliation.

Backend pytest coverage must verify:

- default and persisted preference state;
- self-scoped API authorization and inability to choose another user;
- native owner empty-id handling only with verified owner context;
- atomic onboarding claim, acknowledgement, and expiry;
- deterministic adaptation counters without raw text;
- tool/API use of the same service and failure on missing verified identity;
- Chat Mode tool availability through the existing permission architecture.

The critical tests for mode isolation, the three-line limit, final transition, preference ownership, and onboarding deduplication are mutation-proved by deliberately disabling or inverting the relevant production condition, observing the targeted test fail, restoring the implementation, and observing it pass.

Final validation runs:

```bash
cd apps/jarvis-desk
npm test
npm run lint
npm run build:renderer

cd /media/projects/jarvis-v2
conda run -n ai python -m pytest <relevant-backend-tests> -q
python -m compileall core apps/api scripts
```

## 16. Documentation and delivery

`DEVLOG.md` and `STATUS.md` document Chat Mode Living/Calm/Adaptive, first-run onboarding, per-user persistence, the Jarvis tool, Chat/Code isolation, and verification evidence.

Product work is delivered as one cohesive feature commit with message:

`feat(desk): add adaptive chat flow with living and calm streaming`

The design checkpoint may be amended into that final commit through the repository attribution wrapper so the delivered feature remains one commit. Nothing is pushed, deployed, or used to restart production services without separate authorization.

## 17. Out of scope

- Mobile presentation changes.
- SSE or reducer redesign.
- Execution-policy, reasoning-quality, or model-answer-style changes.
- New synthesis generation.
- Mission Control redesign.
- Decorative color expansion or dashboard-style Chat UI.
