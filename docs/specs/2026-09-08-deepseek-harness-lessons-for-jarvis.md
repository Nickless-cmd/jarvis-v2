# DeepSeek Harness Lessons for Jarvis-v2

Date: 2026-09-08

Status: reviewed architecture spec v3; implementation requires the phased migration below

Scope: DeepSeek Harness `dsh@0.1.5-alpha.1` at `/home/bs/Skrivebord/deepseek-harness`, compared against current Jarvis-v2 runtime in this repository.

## Executive read

DeepSeek Harness is not interesting because it has more personality, memory, or Mission Control than Jarvis. It does not. Jarvis is richer there. DeepSeek is interesting because its harness layer is cleaner: plugin composition, typed capability seams, append-only session truth, explicit agent-step lifecycle, durable stream settlement, tool contracts with canonical/model/UI separation, and first-class subagent/workflow seams.

The right move is not to make Jarvis become DeepSeek Harness. The right move is to keep Jarvis as an identity-first, runtime-governed entity and adopt the harness skeleton where Jarvis is currently organic and fragile.

The highest-value Jarvis changes are:

1. Make model-visible truth append-only and replayable through an exclusively owned session handle: if the model saw it, it must be in the session log.
2. Introduce versioned, pure projection folds with one consistent sequence cut; Mission Control consumes projections but never becomes another truth store.
3. Split live streaming from durable settlement: failed attempts are auditable, while text already delivered on cancellation is anchored so UI and model history cannot diverge.
4. Separate approval from execution confinement. A confined profile must fail closed when enforcement is unavailable, and the runtime must report whether enforcement is full, partial, or absent.
5. Turn `explore` and `task` from final-text tools into providers behind a real `SubagentRuntime` with frozen, non-escalating child authority.
6. Replace scattered tool handling with `ToolDefinitionV2` and a secure generic `ArtifactStore`: canonical output, model rendering, semantic UI metadata, execution provider, effect class, runtime-resolved approval policy, and retrievable bounded output.
7. Move approvals, jobs, retry, compaction, telemetry, connection recovery, and workflow orchestration behind independent seams rather than inline visible-run logic.
8. Make package-owned runtime invariants, scoped registration ownership, cross-session provenance, and keyless real-composition tests part of the harness contract.

## Evidence base

Local DeepSeek checkout:

- Repository: `https://github.com/deepseek-ai/deepseek-harness.git`
- Local path: `/home/bs/Skrivebord/deepseek-harness`
- Local and remote `HEAD`: `5dda764ed3aa172535a7967b06ff95d9cbfe536a`
- Package version: `0.1.5-alpha.1`
- Upstream docs site checked: `https://deepseek-harness.github.io/deepseek-harness/` returned HTTP 200 on 2026-09-08.

Primary DeepSeek files reviewed:

- `/home/bs/Skrivebord/deepseek-harness/AGENTS.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/architecture.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/cordis-primer.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/agent-lifecycle.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/llm-streaming.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/subagent.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/workflow.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/core/session/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/core/agent-loop/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/core/system-prompt/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/core/tools/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/interaction/user-approval/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/jobs/jobs/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/llm/llm-retry/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/compaction/compaction-basic/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/api/gateway/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/subagent/subagent/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/subagent/tool-subagent/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/subagent/tool-subagent-control/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/workflow/workflow/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/workflow/tool-workflow/README.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/persistence.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/session-projection.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/invariants.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/scope.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/sandbox.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/spill.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/session-reference.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/session-telemetry.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/goal.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/subsystems/agent-team.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/defensive-patterns.md`
- `/home/bs/Skrivebord/deepseek-harness/docs/api-gateway.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/client/connection/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/hooks/hook-protocol/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/test-support/llm-mock-server/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/test-support/llm-replay/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/test-support/loader-smoke/README.md`
- `/home/bs/Skrivebord/deepseek-harness/packages/test-support/session-snapshot/README.md`

Verification pass (2026-09-08, opus): every path cited below was confirmed to exist — 39 DeepSeek paths and 27 Jarvis paths, none missing. The DeepSeek checkout's `HEAD`, package version, and remote match the values stated above exactly. Gaps A, C, G, H, I, and J were each checked against the code rather than accepted from the prose; §11 and §12 were checked against `presets/ptc/agent.cordis.yml` and `presets/minimal/agent.cordis.yml`. `session_events` and `chat_sessions.storage_mode` were confirmed ABSENT from the live database, so Phase 1 introduces them rather than duplicating something existing. One claim was corrected (the size of `visible_runs.py`) and one sharpened (Gap J, below). The architectural judgements themselves are not grep-verifiable and were read, not proved.

Jarvis files reviewed:

- `core/eventbus/bus.py`
- `core/eventbus/events.py`
- `core/services/chat_sessions.py`
- `core/services/visible_runs.py`
- `core/services/visible_runs_sse_v2.py`
- `core/services/visible_runs_outcomes.py`
- `core/services/visible_runs_approvals.py`
- `core/services/visible_followup.py`
- `core/services/simple_tool_executor.py`
- `core/services/local_tool_broker.py`
- `core/services/run_event_log.py`
- `core/services/subagent_ecology.py`
- `core/services/agent_dispatch.py`
- `core/services/agent_runtime_spawn.py`
- `core/runtime/db_agent_runtime.py`
- `core/runtime/db_schema.py`
- `core/tools/jc_tool_catalog.py`
- `core/tools/tool_text_render.py`
- `core/services/tool_result_store.py`
- `core/services/bash_sandbox.py`
- `core/services/permission_axes.py`
- `core/services/central_projection_cache.py`
- `core/tools/tool_scoping.py`
- `core/tools/simple_tools_definitions.py`
- `core/tools/simple_tools_native.py`
- `apps/api/jarvis_api/routes/agent_loop.py`
- `docs/streaming-production-grade-spec.md`

## What DeepSeek Harness does well

### 1. Everything is a plugin, but not as a slogan

DeepSeek uses Cordis plugins as the unit of composition. Plugins register services, typed events, prompt sections, tools, hooks, and reversible effects into a shared context. The useful rule is not "plugins everywhere"; it is "registrations are effects and must have disposers."

Jarvis has many modules and many services, but the ownership boundaries are often implicit. A subsystem can publish an event family, add prompt text, affect visible runs, or register a tool without one shared lifecycle vocabulary.

Jarvis lesson: define a small `RuntimePlugin`/`ServiceProvider` convention for new seams. It does not need to port Cordis. It needs:

- explicit dependencies
- startup registration
- shutdown disposer
- typed service contract
- typed events or declared event family
- Mission Control projection owner

### 2. Session log is the model-visible truth

DeepSeek's `dsh-session` holds an append-only session log in memory; it becomes durable when a persistence backend is composed. The model history is derived from session events. Surface events like `system/message`, `user/message`, `assistant/message`, and `tool/result` form what the model can see. Non-surface events like retry, workflow records, descriptors, or telemetry remain logged but not model-visible.

The strong invariant is: model-visible means logged.

Jarvis already has `chat_sessions`, `content_json`, `tool_result_store`, and eventbus. But visible truth is split across chat messages, SSE frames, run outcome persistence, local tool broker results, and eventbus observations. `visible_runs.py` repairs many edge cases because there is no single durable turn ledger.

Jarvis lesson: add a `TurnLog` or `RuntimeSessionLog` layer before trying to simplify visible runs. Do not delete `chat_messages`; project from the new log into the old table until the UI catches up.

### 3. Agent loop lifecycle is explicit

DeepSeek names the lifecycle:

- `turn/start`
- prompt/tool assembly
- `agent/pre-step`
- `step/start`
- `agent/request`
- `request/header/context`
- `llm/stream`
- live `agent/assistant-stream`
- durable `assistant/message` or `assistant/attempt`
- tool call/result records
- `step/end`
- maybe next step
- `turn/end`

Jarvis has the same behavior, but much of it is embedded in `visible_runs.py` and its helper modules. This makes individual fixes possible, but it keeps producing surgical repairs: survival messages, retry fences, approval state persistence, terminal-frame guarantees, provider-specific followup rescue, and outcome sanitization.

Jarvis lesson: extract an explicit `VisibleTurnDriver` with named step objects and durable attempt records. The first version can wrap existing behavior rather than rewrite it.

### 4. Streaming settlement is a first-class invariant

DeepSeek's stream model separates:

- transient live chunks for UI
- compact timed stream record embedded in the durable assistant settlement
- `assistant/message` for a successful provider settlement, including successful calls whose content derives to no visible model message
- `assistant/attempt` for failed, retried, cancelled, or stream-error attempts that settle without a surface message

This maps directly to Jarvis' existing streaming-production spec. Jarvis already knows the symptoms: transient provider drops, empty followup completions, missing terminal frames, retry/failover complexity, and no durable distinction between failed partial stream and accepted assistant content.

Jarvis lesson: implement durable attempts. A retry should not need to surgically truncate in-memory parts to avoid leaking failed text. A failed retryable attempt is recorded as non-surface and replaced/reset in the UI; a cancellation after delivered text instead anchors the exact delivered prefix as an interrupted surface message. The final accepted completion remains the only successful surface assistant message for that request series.

### 5. Tools have three consumer projections, not one output

DeepSeek tools distinguish:

- canonical JSON result
- model-facing rendering
- host/client presentation derived from canonical call/result data and persisted semantic metadata

Jarvis has moved in this direction. `tool_text_render.py`, `tool_result_store.py`, `content_json`, and `jc_tool_catalog.py` are all signs of the same architecture trying to appear. But tool definitions are still scattered between OpenAI-style definitions, Anthropic-style `input_schema`, execution handlers, local/client routing, approval gates, renderers, and post-hoc sanitizers.

Jarvis lesson: introduce `ToolDefinitionV2` as a compatibility wrapper around existing tools. Execution placement, model presentation, and UI visibility are separate axes:

```python
class ToolDefinitionV2(Protocol):
    name: str
    definition_version: str
    description: str
    args_schema: dict
    output_schema: dict | None
    execution_provider: str
    effect_class: Literal["read_only", "idempotent_write", "non_idempotent_write"]
    approval_requirement: Literal["none", "ask", "forbidden"]
    surface_tags: frozenset[str]
    default_timeout_s: float

    async def execute(self, args: dict, ctx: ToolExecutionContext) -> ToolCanonicalResult: ...
    def render_for_model(self, result: ToolCanonicalResult) -> str: ...
    def presentation_meta(self, args: dict, result: ToolCanonicalResult | None) -> dict: ...
```

Approval policy is resolved by runtime governance from the tool definition, profile, actor, and surface. A model-visible caller cannot weaken it. Tool-call presentation mode (`native`, `ptc`, or `both`) is selected once per effective agent/request profile, not per tool definition. `presentation_meta` contains versioned semantic hints only; the client remains responsible for rendering cards from canonical arguments, results, failure state, and those hints.

The first implementation should adapt current `simple_tools` and jarvis-code local tools. It should not require every tool to be rewritten immediately.

### 6. Approval is a seam, not a branch in the hot loop

DeepSeek's user approval package is intentionally small: approval mode is `ask` or `never`, tool policy can decide allow/deny/ask, answerers are listeners, missing answerers fail closed, and approval ask/decide events are logged.

Jarvis approval is functionally richer, but approval flow is partly inline in `visible_runs.py`, with pending state, UI card emission, eventbus publication, wait logic, and tool result persistence all near the visible run hot path.

Jarvis lesson: create `ApprovalRuntime`:

- `request(invocation, resolved_policy, authority) -> ApprovalDecision`
- durable `approval/requested`
- durable `approval/decided`
- fail-closed when no answerer exists
- UI/Mission Control answerers outside the tool executor
- no direct dependency from visible turn driver to a particular UI card

### 7. Subagents are a runtime relation, not just a tool result

DeepSeek's subagent seam has providers: in-process spawn, fork, ACP, Codex, Claude Code, DSH SDK. The model-facing tool is only a consumer over that seam.

Important details:

- one-shot children return final text
- continuable children have durable child sessions
- continuable children can be messaged later
- `send_message` returns acceptance, not a reply
- `interrupt_agent` stops current work but keeps inbox/descendants
- `list_agents` is a projection over durable child sessions
- provider capability flags fail loud when unsupported
- child identity is durable descriptor data, not a live object

Jarvis currently has `explore`, `task`, `spawn_agent_task`, `dispatch_code_mode_task`, Claude-dispatch, agent-pool routing, and subagent ecology surfaces. That is a lot of capability, but the dominant model path is still: call a tool, get final text. The agent tree is not the core abstraction.

Jarvis lesson: make `explore` a provider behind `SubagentRuntime`, not the architecture.

Target shape:

```text
Jarvis visible turn
  -> SubagentRuntime.start(provider="explore", mode="one_shot", task=...)
  -> SubagentRuntime.start(provider="jarvis_code", mode="continuable", task=...)
  -> SubagentRuntime.send_message(child_id, message)
  -> SubagentRuntime.interrupt(child_id)
  -> Mission Control projects parent/child tree
```

`explore` can remain the workhorse. It should become `ExploreSubagentProvider`.

### 8. Workflows are explicit large orchestration

DeepSeek's workflow tool lets the model write a JavaScript orchestration script with `agent()`, `parallel()`, `pipeline()`, `phase()`, and `log()`. The parent waits for final JSON. Workflow has durable observational records but child transcripts stay out of parent context.

This is useful, but it should not become the default for normal delegation. DeepSeek's own guidance says plain subagent calls are better for one or two delegations.

Jarvis lesson: define `WorkflowRuntime` later, after `SubagentRuntime`. It should be for big multi-agent audits, migration planning, broad research, and adversarial review. Do not use workflow to paper over missing continuable subagents.

### 9. Jobs are a generic background primitive

DeepSeek has `dsh-jobs`: stable ids, owner session scoping, read/list/wait/kill, bounded output, completion notices. Jarvis has several background-ish systems: operator background shells, process supervisor, dispatch records, scheduled tasks, and autonomous runs.

Jarvis lesson: introduce one `JobRuntime` seam and adapt current background mechanisms into it. That gives Mission Control a single place to show long-running work, stale jobs, output handles, and cancellation.

### 10. Profiles and bundles make modes explicit

DeepSeek composes profiles from ordered plugin layers: base bundle, profile patch, home patch, command-line overlay. Jarvis has runtime settings, feature flags, user tiers, surface modes, local tool routing, and model lane policy. The behavior is powerful but broad.

Jarvis lesson: define named runtime profiles:

- `visible-owner`
- `visible-member`
- `jarvis-code`
- `autonomous`
- `maintenance`
- `research`
- `safe-offline`

Each profile should declare model route, visible tools, approval policy, memory surfaces, private layers, stream policy, retry policy, and Mission Control visibility.

### 11. PTC mode: one program against a generated SDK, not N tool calls

DeepSeek's `ptc` preset is the standard coding agent with one deliberate exception: the general-purpose `workflow` tool is absent, and the remaining tool registry is presented through a generated SDK, with `run_code` as the model-authored composition surface. A sequence that would be five round trips becomes one model-authored program. The tool-presentation layer turns the registry into typed bindings for that session; the registry itself stays on the host plane, so PTC is a presentation choice over one registry, not a new runtime.

Jarvis lesson: Jarvis has `dispatch_code_mode_task`, role plans, Claude-dispatch, and agent-pool routing, but the dominant model path is still call-a-tool-get-final-text — the agent tree is not the core abstraction. A bounded PTC-style presentation (one program against generated bindings for a scoped task) is a direct answer to the `max_tool_calls`/round-trip-latency pressure we already feel. It belongs after `WorkflowRuntime` and should land as an extension seam (see §21), not as a default surface.

### 12. Minimal mode: a two-tool agent for honest measurement

DeepSeek's `minimal` preset is deliberately naked: a fixed complete persona prompt, no runtime-context snapshots, no context compaction, and exactly two tools — persistent bash and `str_replace_editor`. This is the mode DeepSeek itself uses as the benchmark surface, because production numbers depend as much on the harness as on the model; minimal mode is how they separate model ability from scaffolding.

Jarvis lesson: we have never measured what the underlying model (for example deepseek-v4-flash) can do without the Jarvis prompt stack. A minimal-mode baseline — fixed prompt, two tools, no Centralen context injection — would give an honest ceiling: how much of observed behavior is the model, how much is the harness. That measurement belongs in Phase 0 characterization, before the refactor can claim credit for behavior changes.

## Jarvis strengths to preserve

Jarvis has things DeepSeek Harness does not appear to target as first-class product identity:

- protected identity and memory layers
- Mission Control as operator truth/control plane
- cross-channel continuity
- inner-life/private experimental layers
- eventbus as nervous system
- hardware/system awareness ambitions
- owner/member/user scoping
- long-lived autonomous daemons
- Danish/person-specific relational context

The harness refactor should serve those. It should not flatten Jarvis into a generic agent runner.

## Current Jarvis gaps against the DeepSeek harness model

### Gap A: event family allowlist is fragile

`core/eventbus/events.py` has a large `ALLOWED_EVENT_FAMILIES` allowlist with repeated comments documenting previously dropped event families. This is useful operational memory, but the pattern is brittle: a new event can fail because the family was not manually added.

Desired state: event declarations live next to the service that emits them and are checked at boot/test time. The global registry can still exist, but generated or collected declarations should feed it.

### Gap B: visible run lifecycle is too concentrated

`core/services/visible_runs.py` still owns too much: run state, streaming, tool-loop, approvals, retries, followups, presentation invariants, persistence coordination, survival outcomes, local tool execution, and provider quirks. Some pieces have been extracted, but the hot path remains the integration sink.

Desired state: visible run delegates to:

- `TurnLog`
- `StreamSettlement`
- `ToolRuntime`
- `ApprovalRuntime`
- `RetryRuntime`
- `SubagentRuntime`
- `OutcomeProjector`

### Gap C: local tool broker is good but one-off

`core/services/local_tool_broker.py` is a clean standalone broker: register, wait, and resolve are correlated by `call_id`, while disconnect cleanup cancels pending calls by session. It demonstrates the seam style Jarvis should use more often. But it is process-local, specific to Path B, and cannot distinguish "not started" from "started but result lost."

Desired state: keep the broker, but wrap it as a provider under `ToolRuntime` or `RemoteExecutionRuntime`.

### Gap D: `explore` is too model-shaped

`explore` is exposed as a convenient read-only research tool. The user correctly noted that most other agents are currently called via that tool. That is useful in practice, but architecturally it hides child work behind one result string.

Desired state: `explore` becomes a subagent provider with:

- `start_one_shot`
- `start_continuable`
- `status`
- `send_message`
- `interrupt`
- `events`
- `list_children`

### Gap E: workflow exists as concepts, not a stable runtime seam

Jarvis has `dispatch_code_mode_task`, role plans, Claude-dispatch, council-style notes, and mission pipelines. These are useful, but they are not one bounded workflow contract with start/result/cancel/dispose and durable records.

Desired state: workflows become an optional consumer over `SubagentRuntime`, not a separate parallel universe.

### Gap F: database serialization is not session ownership

SQLite WAL and per-process locks prevent some low-level write collisions, but Jarvis has no single contract that says which process owns continuation of one live Session. API requests, detached runs, heartbeat work, recovery, and cold readers need one `SessionHandle` boundary with an exclusive cross-process write lease. A read observer may balance an interrupted log in memory; only the write owner may append durable repair events.

### Gap G: projections are ad hoc views and caches

Jarvis has projection tables and `central_projection_cache.py`, but no domain registry for pure event folds, schema/version invalidation, a shared `as_of_seq`, or deterministic replay from a common cut. TTL and content-version caches reduce polling cost; they do not establish projection semantics.

### Gap H: approval policy can overstate execution confinement

`permission_axes.py` correctly separates capability from approval timing. The present bash sandbox does not complete that design: it is disabled by default, excludes the normal persistent-shell path, and deliberately falls back to unconfined execution when `bwrap` is unavailable. A selected restricted profile therefore does not yet prove restricted execution. The runtime must expose enforcement quality and fail closed whenever a call promises confinement.

### Gap I: static tool filtering does not own scoped lifetime

`tool_scoping.py` provides useful role/mode allowlists through `ContextVar`, but visibility, registration ownership, and teardown are separate concerns. A child or plugin needs an opaque runtime scope whose tool, prompt, service, listener, and projection contributions disappear together after quiescent disposal.

### Gap J: out-of-line output is tool-specific and under-specified

`tool_result_store.py` proves the value of out-of-line results, but it is not a general artifact capability. It stores arguments and output directly, relies on ambient file permissions, clips the value advertised as full output, and does not make authority, completeness, retention, provenance, and retrieval separate contracts.

Verified 2026-09-08: `save_tool_result()` clips at `_MAX_STORED_CHARS = 2_000_000` via `clip_head_tail` and writes the result under the `result` key. The clipping is **not** silent — `clip_head_tail` splices a visible note into the text (`… [N tegn udeladt i midten — hoved+hale bevaret] …`), so a reader can see it. But completeness is carried **in the payload prose, not as structured metadata**: a programmatic consumer must parse Danish text to learn whether it holds the whole output, and nothing records the original length. That is precisely the contract this gap asks for — completeness as a separate, machine-readable fact — and it is cheap to close ahead of the phase.

(An earlier revision of this note claimed the clipping was undetectable. That was wrong: the marker in the text was checked only after the sentence was written. The narrower criticism above is the accurate one.) Jobs, web fetches, subagents, workflows, and cross-session references need the same secure storage seam.

### Gap K: cross-session context lacks one provenance envelope

Jarvis has strong cross-session memory and continuity, but no universal immutable snapshot form that records the source Session format, source sequence cut, content digest, compaction/truncation facts, and untrusted-context classification. A source Session id alone cannot reproduce exactly what entered another model request.

### Gap L: operational signals can be mistaken for durable truth

Jarvis uses the eventbus, Central observations, runtime tables, and SSE frames for different purposes, but the class of each stream is not uniformly declared. The harness needs a hard distinction between canonical records, projections, best-effort telemetry, and ephemeral delivery frames, including outbound redaction and deduplication semantics.

### Gap M: recovery and conformance are tested subsystem by subsystem

Jarvis has many focused regression tests, but the new harness needs keyless whole-composition evidence: scripted provider wire faults, deterministic replay, session-format corpus fixtures, prompt/tool-schema snapshots, workspace-effect checks, reconnect generations, and disposal/quiescence checks through the production loader path.

## Proposed Jarvis architecture

### 1. `RuntimeSessionLog`

Purpose: append-only event log for what the model can see and what the runtime needs to replay a turn.

Access contract:

```python
class SessionHandle(Protocol):
    session_id: str
    header: SessionHeader
    access: Literal["read", "write"]

    async def read(self, offset: int = 0, limit: int | None = None) -> EventSlice: ...
    async def append(self, events: Sequence[SessionEvent]) -> None: ...
    async def flush(self) -> None: ...
    async def close(self) -> None: ...
```

- Every ledger read and write flows through a handle. Id-addressed convenience APIs must acquire and close a handle internally rather than bypass ownership.
- At most one write handle owns a Session across all Jarvis processes. SQLite transaction serialization is not a substitute for this semantic lease.
- A write lease records owner process/runtime identity, fencing token, acquisition time, heartbeat, and expiry. Every append verifies the current fencing token inside its transaction.
- A second live writer fails with `SESSION_ALREADY_OWNED`; loss or expiry during use fails with `SESSION_OWNERSHIP_LOST`.
- Read handles never mutate durable state. They may derive balanced recovery state in memory for inspection.
- `append()` promises accepted ordering and visibility. `flush()` is the durability/materialization barrier; with the initial SQLite provider, a committed append already satisfies it, but callers retain the explicit boundary for future providers.
- `close()` is asynchronous, idempotent, uncancellable, drains accepted work, and releases ownership only after quiescence.
- Recovery acquires write ownership before appending synthetic interruption closers. It preserves every semantically complete event and removes only a physically incomplete storage tail.

Immutable Session header:

```text
SessionHeader
  format_version
  session_id
  created_at
  cwd
  parent_session_id
  inherited_event_count
  origin
  delegation_depth
  effective_profile_schema
  effective_profile_hash
```

Format contract:

- `SESSION_FORMAT_UNSUPPORTED` is distinct from `SESSION_CORRUPT`; a valid future format is not damaged data.
- The reader refuses the highest published future generation even when an older readable generation exists.
- Historical migration is copy-on-migrate: source bytes and identity stay unchanged, transformed output is verified, source revision is rechecked, and a new immutable generation is atomically published.
- No online migration rewrites a historical generation in place. A failed migration leaves the source and current publication unchanged.
- Current, historical, and deliberately refused Session generations live in a committed compatibility corpus and are exercised through the real reader.

Source-of-truth rule:

- `session_events` is the authoritative write model for migrated sessions.
- `chat_messages` remains the compatibility read projection during migration.
- The eventbus transports notifications after commit; it is not the durable ledger.
- Direct `chat_messages` writes remain authoritative for legacy sessions until their explicit cutover.
- A session has exactly one `storage_mode`: `legacy_messages` or `event_ledger_v1`. Reads never merge two authorities opportunistically. The only permitted transition is a verified, transactional `legacy_messages -> event_ledger_v1` cutover; it cannot be reversed by a runtime flag.
- `chat_sessions.storage_mode TEXT NOT NULL CHECK (storage_mode IN ('legacy_messages', 'event_ledger_v1'))` owns that decision. New rows receive the mode inside the session-creation transaction; historical rows migrate to `legacy_messages` before the constraint becomes mandatory.
- `chat_sessions.surface_generation INTEGER NOT NULL DEFAULT 0` owns the current active model-surface generation for ledger sessions.
- Every session reader and writer obtains the committed mode through one shared resolver. Ad hoc caller overrides are forbidden.

Minimum durable schema:

```text
session_log_headers
  session_id          text primary key
  format_version      integer not null
  generation          integer not null
  created_at          text not null
  cwd                 text null
  parent_session_id   text null
  inherited_event_count integer not null default 0
  origin              text null
  delegation_depth    integer not null default 0
  effective_profile_hash text not null
  source_generation_digest text null

session_write_leases
  session_id          text primary key
  owner_runtime_id    text not null
  fencing_token       integer not null
  acquired_at         text not null
  heartbeat_at        text not null
  expires_at          text not null

session_events
  session_id        text not null
  seq               integer not null
  event_id          text not null unique
  schema_version    integer not null
  kind              text not null
  surface_op        text null
  replaces_from_seq integer null
  replaces_to_seq   integer null
  surface_generation integer not null default 0
  turn_id           text null
  step_id           text null
  attempt_id        text null
  invocation_id     text null
  causation_id      text null
  correlation_id    text null
  actor_id          text null
  created_at        text not null
  payload_json      text not null
  primary key (session_id, seq)
```

Append contract:

- Sequence allocation and insert happen in one database transaction.
- `event_id` makes append idempotent across retry/reconnect.
- The append API returns only after SQLite commit. `flush(session_id)` is a durability barrier for buffered backends and a no-op after committed SQLite writes.
- Events are immutable. Corrections use explicit replacement/supersession events; rows are never updated in place.
- Event payload readers support explicitly catalogued versions. Session-format migration publishes a new immutable generation; semantic corrections inside a current log use new events rather than row mutation.
- A batch needed to preserve an invariant, such as `tool_call` plus dispatch intent, commits atomically.
- Ledger event kinds use the names in this section and do not need to be valid eventbus `family.name` values. Post-commit notifications map them explicitly to declared eventbus events.
- A `prepared_request` event commits before provider dispatch and snapshots request-series id, resolved provider/model and parameters, the complete ordered canonical tool schemas or immutable hash-checked content references, effective prompt content or immutable hash-checked reference, derived-history high-water sequence, compaction generation, effective profile schema/hash, and request-body digest. Every request component needed for exact reconstruction is stored inline or by immutable reference; a hash without retrievable content is insufficient. Every assistant attempt references exactly one prepared request.

Projection contract:

- `ProjectionRuntime` below owns general domain folds. The compatibility projector is one registered projection rather than a special second projection architecture.
- A `session_projection_offsets` row stores the last projected sequence per projection and Session.
- Projection is idempotent: applying the same `(session_id, seq)` twice has no additional effect.
- Projection row changes and cursor advancement commit in one transaction.
- Drift detection compares ledger-derived message ids/hashes with `chat_messages` and reports to Mission Control.
- Projection failure never changes ledger truth and can be replayed from the last cursor.

Minimum event vocabulary:

- `turn_started`
- `step_started`
- `system_message`
- `user_message`
- `prepared_request`
- `assistant_message`
- `assistant_attempt`
- `tool_call`
- `tool_result`
- `tool_reconciled`
- `approval_requested`
- `approval_decided`
- `retry_scheduled`
- `retry_started`
- `compaction_started`
- `compaction_summary`
- `compaction_ended`
- `subagent_descriptor`
- `subagent_settled`
- `workflow_started`
- `workflow_agent_started`
- `workflow_agent_ended`
- `workflow_ended`
- `turn_ended`

Rules:

- `surface_op` is one of `append`, `replace`, or `log_only`; only the first two participate in model-history derivation.
- Every ordinary surface append is stamped with the current `chat_sessions.surface_generation` read inside its append transaction.
- `replace` names an inclusive contiguous `[replaces_from_seq, replaces_to_seq]` range from the current generation. The range must exist, remain inside one session, contain only replaceable surface members, and not cross protected head/turn boundaries defined by the event kind. Successful replacement compares-and-swaps the session generation and appends the replacement under the new generation in one transaction. A stale expected generation, concurrent append conflict, or overlapping active replacement is rejected. Replay excludes the replaced range and inserts the replacement event at that range's logical position.
- Surface events derive model history through a versioned, deterministic projector.
- Non-surface events remain replay/audit facts.
- Every event is immutable after append.
- Projection to `chat_messages` remains for compatibility, but only one side is writable for a given session mode.
- Tool results may store full bodies out-of-line, but the reference is in the log.
- Out-of-line data is content-addressed or hash-checked so a dangling or altered body fails visibly.

Migration and rollback:

1. Add tables and projector with the feature disabled.
2. Shadow-write ledger events for test sessions while `chat_messages` remains authoritative. Shadow projection writes to an isolated comparison table/view, never to production `chat_messages`, and is not used for reads.
3. Enable `event_ledger_v1` only for newly created canary sessions. Their creation transaction sets the mode before the first event. Canonical reads derive from `session_events`; `chat_messages` is output-only compatibility projection written solely by the authorized projector.
4. After zero drift over the configured observation window, allow UI/API compatibility reads from projected `chat_messages` only where necessary; model request construction continues to derive from the ledger.
5. Expand by profile/surface. Existing sessions stay legacy unless an offline backfill verifies ordered equivalence and flips their mode in the same transaction that records the cutover checkpoint.
6. Rollback stops expansion and creates subsequent sessions in legacy mode. Existing ledger sessions remain ledger-backed; rollback does not reinterpret them as legacy or discard committed events.
7. Direct application writes to `chat_messages` become forbidden for ledger sessions once the projector is enabled. Only the designated idempotent projector identity may write those projection rows, enforced in code and by tests.

### 2. `StreamSettlement`

Purpose: one place to classify provider stream outcomes.

Responsibilities:

- collect live deltas
- emit UI stream frames
- record compact attempt stream
- classify terminal reason and settlement independently from model visibility
- append exactly one assistant settlement event per attempt: `assistant_message` or `assistant_attempt`
- guarantee terminal UI frame
- keep retry input byte-equivalent to the accepted durable history
- prevent stale provider pumps from appending after an attempt has settled

Normative settlement table:

| Provider outcome | Canonical provider blocks | UI treatment | Exactly one durable settlement | Derived model surface | Default next action |
|---|---|---|---|---|---|
| Successful text | valid text/content blocks | finalize provisional frames | `assistant_message` | include committed blocks | continue/finish |
| Successful tool calls, with or without text | valid tool/text blocks | finalize visible blocks | `assistant_message` | include non-empty committed blocks | execute accepted calls |
| Successful empty response | none | no content; terminal status only | `assistant_attempt(EMPTY_RESPONSE)` | exclude | retry within policy, else fail turn |
| Private reasoning only | reasoning blocks not eligible as answer | hide/private-status only | `assistant_attempt(EMPTY_RESPONSE)` | exclude | retry within policy, else fail turn |
| Answer-bearing provider `thinking` with empty normal content | provider blocks classified as promotable answer | promote through existing compatibility rule, then finalize | `assistant_message` | include promoted answer block | continue/finish |
| `max_tokens` with valid blocks | valid partial blocks | finalize as truncated/interrupted | interrupted/truncated `assistant_message` | include committed prefix | stop or explicit continuation policy; never silent retry |
| User cancellation before any server-emitted delta | provisional blocks not entered in the resumable run buffer | clear provisional UI | `assistant_attempt(CANCELLED)` | exclude | end interrupted |
| User cancellation after server-emitted deltas | canonical blocks matching the resumable-buffer prefix | finalize exact prefix as interrupted | interrupted `assistant_message` | include exact committed prefix | end interrupted |
| Transport/provider failure before any delta | none | terminal failure status | `assistant_attempt(failure)` | exclude | retry if policy permits |
| Transport/provider failure after partial deltas | partial canonical blocks not accepted as surface | reset/replace provisional attempt | `assistant_attempt(failure)` | exclude | retry if policy permits |
| Malformed tool call before message acceptance | malformed call plus any provisional blocks | reset or show explicit failure | `assistant_attempt(MALFORMED_TOOL_CALL)` | exclude | no side effect; policy decides retry |
| Malformed tool call discovered after valid message commitment | committed valid blocks plus invalid call | retain committed blocks and emit synthetic tool error | `assistant_message` | include committed valid surface | no side effect; continue under tool policy |
| Error after a tool call was dispatched | previously committed assistant message plus invocation state | retain committed message; show tool state | assistant attempt already settled as `assistant_message` | include committed message and later tool result | reconcile invocation; never blind retry |

Treating a semantically empty success as `EMPTY_RESPONSE` is a deliberate Jarvis policy that preserves the existing no-empty-visible-completion invariant. It is stricter than DeepSeek's generic session event vocabulary, which can record a successful content-less `assistant/message`; provider adapters normalize a truly empty Jarvis completion into the failed-attempt path before session settlement.

Streaming invariants:

- An attempt has one opaque `attempt_id`; every frame carries it plus a monotonically increasing frame sequence.
- Canonical provider blocks, UI-emitted frames, server-emitted prefix, and committed model surface are separate values. Conversion between them is deterministic and recorded by attempt id.
- The authoritative cancellation boundary is the highest contiguous frame sequence appended to the server-owned resumable run buffer before SSE emission. Ordinary SSE client acknowledgement is neither required nor inferred. Cancellation settlement snapshots that exact buffer prefix into the ledger; bytes observed by a client but absent from that buffer are a transport bug, not an alternate history authority.
- UI deltas are provisional until settlement. A failed attempt after partial delivery emits a replacement/reset frame before another attempt may stream.
- Exactly one terminal frame is emitted per attempt and one terminal run frame per visible run.
- Retry reuses the same accepted user batch, rendered prompt, tool schemas, and durable history unless an explicitly logged compaction or route transition changes the request series.
- Limits apply across providers: maximum attempts, total wall-clock duration, and total generated tokens. Provider failover does not reset them.
- Fault injection covers drop-before-first-delta, drop-after-delta, stale late delta, duplicate terminal frame, empty response, cancellation races, and tool-call interruption.
- Rollout is feature-flagged per profile with an immediate kill switch and a compatibility path for clients that cannot process reset/replacement frames.

This contract is subordinate to, and must preserve, `docs/streaming-production-grade-spec.md`. Where the older document is more specific about retry safety, stale pumps, fault injection, or client compatibility, those requirements remain normative until deliberately superseded.

### 3. `ToolRuntime`

Purpose: one registry and execution pipeline for all model-facing tools.

Pipeline:

```text
resolve definition
validate args
freeze canonical args
resolve runtime-owned policy
pre_execute hooks
monotonic guards
durably prepare invocation
approval runtime when required
atomically claim allow decision and commit dispatch intent
execute through provider
post_execute hooks
validate canonical result
model rendering
UI presentation metadata
durably settle invocation and append tool_result
```

Invocation state machine:

```text
prepared -> awaiting_approval -> authorized -> dispatching -> dispatched -> settled_success
                                        |              |             -> settled_error
                                        |              +-------------> outcome_unknown
                                        +----------------------------> outcome_unknown
prepared/awaiting_approval -> denied
prepared/authorized/dispatching -> aborted_before_dispatch only with proof of non-execution
outcome_unknown -> settled_late_success | settled_late_error (exactly once by invocation id; surface result unchanged)
```

Before external dispatch, the runtime durably records:

- opaque `invocation_id`
- session, turn, step, and attempt ids
- tool definition name and version
- execution provider
- canonical argument digest and protected/redacted argument record
- effect class and idempotency policy
- resolved approval decision id when required
- dispatch state and timestamps

Rules:

- `prepared` commits before approval is requested and before any provider may begin a side effect.
- Approval decisions bind to that prepared record. `authorized` is reached only by a valid decision; the same transaction that consumes the one-shot decision advances the invocation to durable `dispatching` before the provider boundary is crossed. Tools requiring no approval use the same transaction without a decision row.
- Provider acknowledgement advances `dispatching` to `dispatched`. It is evidence of start, not the first durable dispatch record.
- Recovery of `dispatching` or `dispatched` without a result is `aborted_before_dispatch` only when the provider proves non-execution; otherwise it becomes `outcome_unknown`.
- A disconnect/timeout after possible dispatch is `outcome_unknown`, not an ordinary tool error.
- `outcome_unknown` is never automatically retried unless the same invocation has a provider-supported idempotency key and the definition declares the operation idempotent.
- Late results reconcile by `invocation_id`; they do not create a second result.
- Tool errors are structured envelopes with stable code, retryability, provider facts, and a model-safe rendering.
- Every execution receives cancellation and deadline signals. Timeout ownership is defined once in the runtime, not independently by provider and caller.
- Guard denial is monotonic. Later hooks cannot turn deny into allow.
- Hook, renderer, and persistence failures have named outcomes; a rendering failure cannot erase a canonical result.
- Every transition to `outcome_unknown`, whether live or recovered, idempotently appends exactly one structured model-visible `tool_result` keyed by `invocation_id` with code `TOOL_OUTCOME_UNKNOWN`, so replay remains balanced. It states that the action may have occurred and forbids the model/runtime from treating it as safe to repeat.
- A late authoritative provider result moves operational state to `settled_late_success` or `settled_late_error` and appends a log-only `tool_reconciled` event. It does not replace the balancing surface result or rewrite history that a later request may already have consumed. If the model/user must act on reconciliation, the runtime appends a new explicit surface notification with provenance rather than a second result for the same tool call.

Providers:

- `server_simple_tools`
- `client_local_tools`
- `operator_bridge_tools`
- `mcp_tools`
- `subagent_tools`
- `job_tools`

The current `jc_tool_catalog.execution_location()` should initially feed a compatibility provider resolver. It remains authoritative for legacy jarvis-code tools until each definition migrates; the adapter must not create a second location map.

### 4. `ApprovalRuntime`

Purpose: remove approval wait/card/pending storage from the visible run hot path.

API:

```python
decision = await approval_runtime.request(
    invocation=prepared_invocation,
    resolved_policy=runtime_policy,
    authority=approval_authority,
    deadline=deadline,
)
```

Behavior:

- fail closed if no answerer is available
- durable ask/decide records
- UI, CLI, and Mission Control are answerers
- tool execution sees only allow/deny/timeout
- policy is resolved by runtime governance and monotonic guards; model/tool arguments cannot lower it
- the request is bound to invocation id, canonical argument digest, tool definition version, provider, effect class, actor, approver authority, user/workspace, session, turn, and expiry
- decisions are one-shot and claimed by atomic compare-and-set immediately before dispatch
- changed arguments, provider, tool version, actor, or expiry require a new approval
- late, duplicate, cancelled, expired, and cross-user answers are rejected and audited
- if request/decision audit persistence fails, execution fails closed
- restart recovery can show an unresolved request but cannot execute it until a valid decision is durably present and atomically claimed

Canonical storage:

- Existing approval tables are inventoried before schema work.
- One existing table is designated canonical or migrated into a new canonical table; the others become projections/adapters and stop accepting direct writes.
- The migration includes drift detection and a rollback flag. No third independent approval truth is introduced.

### 5. `SubagentRuntime`

Purpose: make delegated agents real runtime children.

Provider interface:

```python
class SubagentProvider(Protocol):
    name: str
    capabilities: SubagentCapabilities

    async def start_one_shot(self, request: SubagentStartRequest) -> SubagentRun: ...
    async def prepare_continuable(self, request: ContinuableCreateRequest) -> ContinuableCreateSpec: ...

class SubagentRuntime(Protocol):
    async def start(self, request: SubagentStartRequest) -> SubagentStartReceipt: ...
    async def send_message(self, authority: AgentAuthority, child_id: str, message: AgentMessage) -> MessageReceipt: ...
    async def interrupt(self, authority: AgentAuthority, child_id: str) -> InterruptReceipt: ...
    async def status(self, authority: AgentAuthority, child_id: str) -> SubagentStatus: ...
    async def list_children(self, authority: AgentAuthority, parent_id: str) -> list[SubagentDescriptor]: ...
    async def events(self, authority: AgentAuthority, child_id: str, cursor: str | None) -> AgentEventPage: ...
```

Canonical truth and compatibility:

- `agent_registry` is canonical for durable child identity, provider, parent/lineage, capability snapshot, and lifecycle status.
- `agent_runs` is canonical for each execution/activation attempt and terminal outcome.
- `agent_messages` is canonical for accepted inter-agent inbox messages and delivery state.
- Session logs are canonical only for what each model/session saw. Both `subagent_descriptor` and `subagent_settled` events reference canonical agent/run/message ids and are observational for child state; they never override the three agent tables.
- Phase 0 must ratify this authority map against every existing writer. Any incompatible existing column/table is migrated before Phase 5; publishing descriptors is blocked until the map has no unresolved overlap.
- Existing `explore`, `task`, dispatch, and agent-pool APIs remain compatibility consumers over the runtime during migration.

Child state machine:

```text
creating -> accepted -> running -> idle -> running
                              -> completed
                              -> failed
                              -> interrupted -> idle
creating -> rejected
accepted/running/idle -> orphaned -> resumed | failed
```

Rules:

- `start` returns after durable child publication and initial-message acceptance, not after completion.
- One-shot providers may instead return a run handle whose `result()` settles once; they must still publish durable identity before model work begins.
- Continuable start is rejected before mutation when the provider lacks that capability.
- `send_message` returns inbox acceptance with a message id, never an implied reply.
- Only authorized direct parent/child relations can message or interrupt. Human/operator authority is explicit and audited.
- Interrupt acknowledgement means the signal was accepted; terminal/idle state is observed separately.
- Cold resume uses canonical child/session state and a lease so two processes cannot drive the same child concurrently.
- Provider removal blocks new starts but does not erase accepted child records.
- Every child inherits a bounded authority set; it never implicitly inherits all parent tools, secrets, workspace access, or approval authority.
- Runtime policy enforces maximum depth, live children, total children per turn, token/cost budget, wall time, and provider allowlist. Child failover does not reset these limits.
- Cancellation propagation is explicit per operation: parent turn cancellation does not automatically kill detached children, while owned workflow cancellation drains its children within a configured grace period.

First providers:

- `explore`: wraps current read-only explore behavior.
- `jarvis_code`: wraps current `task`/agent-loop local execution.
- `claude_code`: wraps `core/tools/claude_dispatch`.
- `internal_agent_pool`: wraps `spawn_agent_task` / `agent_pool_router`.

Provider rollout is capability-based. Initial `explore` is one-shot only. Continuable acceptance is not required until a provider with durable continuation is migrated or `explore` is deliberately upgraded with a persistent inbox/session.

Model-facing tools:

- `subagent` or `task`: start child.
- `send_message_to_agent`: send message to direct child/parent.
- `interrupt_agent`: stop current child turn.
- `list_agents`: show continuable child tree.

Mission Control projection:

```text
visible Jarvis turn
  explore: harness architecture audit [completed]
  jarvis_code: implementation patch [running]
  critic: review [ready]
```

### 6. `WorkflowRuntime`

Purpose: large orchestration only.

Rules:

- Uses `SubagentRuntime` internally.
- V1 is explicitly non-resumable orchestration: durable observations survive restart, but the JavaScript/control execution does not resume.
- Parent turn may block in v1, but the run has explicit `cancel`, a configured cleanup grace period, and a terminal orphan report.
- Success returns structured JSON.
- Child transcripts stay in child sessions.
- Durable workflow records are observational, not model-visible unless explicitly summarized.
- Workflow ownership, child caps, provider permissions, cost/token/time budgets, and workspace authority are snapshotted at start.
- Start/end records pair by workflow id. Child ownership transfers are explicit; cancellation may not silently abandon owned children.
- Process restart settles an in-flight v1 workflow as `interrupted_by_restart`, then reconciles child states without claiming the workflow resumed.

### 7. `JobRuntime`

Purpose: unify long-running background work.

API:

- `start(authority, kind, owner_scope, args) -> job_id`
- `read(authority, job_id, offset=0, max_chars=...)`
- `wait(authority, job_id, timeout_s=...)`
- `kill(authority, job_id)`
- `list(authority, owner_scope_filter=None)`

The interface is capability-based rather than pretending every adapter has identical durability:

- `durability`: `process_local`, `reattachable`, or `restart_managed`
- `cancel_mode`: `cooperative`, `signal`, `provider_request`, or `unsupported`
- `output_mode`: `buffered`, `cursor_stream`, or `external_handle`
- `reattach_supported`: boolean
- `owner_scope`: session/user/workspace/runtime

Every job records resolved owner, initiating actor, kind, capability snapshot, start request digest, retention policy, status, output cursor/handle, lease owner, and terminal reason. Caller-supplied owner scope is validated against authenticated authority; only explicit audited operator delegation can cross user/workspace ownership. Every operation rechecks authority. `kill()` returns acknowledgement, not proof of termination; callers observe terminal state separately. Restart recovery marks non-reattachable process-local jobs lost, reclaims eligible leases, and reports orphans to Mission Control.

Adapters:

- operator background shell
- process supervisor
- one-shot background subagent
- scheduled task run
- long ComfyUI workflow
- local dev server/watchers

Adapters preserve their native semantics. A scheduled task remains restart-managed; an in-process subagent remains process-local unless backed by `SubagentRuntime`; an operator process is only reattachable when its supervisor can prove process identity. The common runtime supplies discovery and policy, not false guarantees.

### 8. `ProfileComposer`

Purpose: make runtime modes inspectable and reproducible.

Each profile declares:

- model route
- tool registry scope
- sandbox filesystem policy and minimum enforcement
- network/process policy
- memory/context sections
- private layers enabled
- approval policy
- artifact retention and retrieval policy
- retry policy
- compaction policy
- streaming mode
- tool-call presentation mode (`native`, `ptc`, or `both`) for the whole request surface
- subagent permissions
- telemetry sharing/redaction policy
- cross-session reference policy
- Mission Control visibility

Profiles are versioned config projections, not a new mutable database truth. Deterministic precedence is:

```text
repository defaults
  < runtime configuration
  < named profile
  < owner/admin policy overlay
  < per-run restrictive overlay
```

Later layers may narrow security policy but cannot broaden beyond owner/admin governance. The composer emits an immutable effective profile plus schema version and content hash. Every turn, child, workflow, and job records that hash so behavior is reproducible after configuration changes.

Mission Control audit recording and protected runtime truth are non-disableable. A profile may control user-facing visibility/redaction, but it cannot stop operational facts from being recorded or available to authorized Mission Control views. Profile changes are config events; DB rows store applied snapshots/hashes, not an independently editable copy.

Named v1 profiles are `visible-owner`, `visible-member`, `jarvis-code`, `autonomous`, `maintenance`, `research`, and `safe-offline`.

### 9. `RetryRuntime`

Purpose: make retry a bounded policy decision at durable attempt boundaries.

Rules:

- Retry receives a settled structured failure, immutable request facts, prior attempts, effective profile hash, remaining budget, and cancellation signal.
- It returns `retry(route_override?, delay)` or `stop(reason)`; it never mutates durable history itself.
- `retry_scheduled` commits before waiting. `retry_started` commits before resampling.
- Delay is cancellation-aware and respects provider hints within configured bounds.
- Empty response, rate limit, timeout, transport failure, and server failure have explicit defaults. Authentication, invalid request, policy denial, tool side effects, and `outcome_unknown` are not generic retries.
- Maximum attempts, provider failovers, wall time, generated tokens, and cost are total turn budgets.
- A route change is recorded and does not silently alter prompt/tool/profile truth.

### 10. `OutcomeProjector`

Purpose: convert one terminal turn/run state into compatibility messages, Mission Control projections, and terminal UI frames without inventing new truth.

Rules:

- Reads only committed ledger/tool/approval/subagent facts.
- Produces idempotent projections keyed by terminal event id.
- Never manufactures a successful assistant message to hide a failed attempt. A user-facing survival/interruption message is an explicit surface event with its own provenance.
- Exactly one run outcome is terminal: completed, interrupted, failed, or abandoned after recovery.
- Projection failure is retryable independently of model/tool execution.

### 11. `RuntimePluginLifecycle`

Purpose: give new capability seams consistent ownership without porting Cordis.

Contract:

```python
class RuntimePlugin(Protocol):
    name: str
    version: str
    dependencies: tuple[str, ...]

    async def start(self, ctx: RuntimeContext) -> PluginHandle: ...

class PluginHandle(Protocol):
    async def dispose(self, deadline: Deadline) -> None: ...
```

Rules:

- Registration returns a disposer and is scoped to the plugin handle.
- Runtime-scoped contributions are registered through an owned `RuntimeScope`; visibility and lifetime cannot drift apart.
- Dependency cycles and missing providers fail at boot before accepting work.
- Event declarations, service contracts, health checks, and Mission Control projection ownership are registered together.
- Disposal stops admission, drains owned work to a deadline, records unresolved ownership, then unregisters effects in reverse order.
- Dispatchers contain callback exceptions so one faulty observer cannot reject core lifecycle work or starve later observers.
- Plugin lifecycle applies to new/extracted seams first; existing services migrate incrementally.

### 12. `CompactionRuntime`

Purpose: reduce context pressure through explicit ledger surface replacement without mutating historical events or hiding request changes.

Rules:

- Compaction runs only at a pre-step boundary or after a canonical context-overflow failure, never concurrently with provider streaming or tool dispatch.
- Effective profile supplies threshold, retained-tail target, tool-result pruning policy, summarizer route, maximum compaction attempts, and budget.
- The runtime first performs deterministic eligible tool-result pruning. If still needed, it selects one contiguous replaceable surface range and produces a summary through a side-effect-free model route.
- `compaction_started` commits before asynchronous summarization. On success, the summary/replacement event and `compaction_ended` commit atomically with the new generation; on failure, a terminal failure event commits without a replacement.
- Failure appends a terminal compaction failure record, leaves the active surface generation unchanged, and preserves the original request error.
- Retry after context overflow is allowed only when pruning or summary commitment advances `surface_generation`; otherwise the original overflow remains terminal.
- Protected system/identity nodes, unresolved tool-call/result pairs, current accepted user input, and the configured retained tail cannot be replaced.
- Every prepared request records the compaction generation it derived from.

### 13. `ProjectionRuntime`

Purpose: provide one versioned mechanism for deriving Mission Control, client, and host state from committed Session events.

```python
class ProjectionDefinition(Protocol[StateT, ViewT]):
    key: str
    state_version: int
    state_schema: Schema[StateT]
    view_schema: Schema[ViewT] | None

    def init(self, header: SessionHeader) -> StateT: ...
    def apply(self, state: StateT, event: SessionEvent) -> StateT: ...
    def view(self, state: StateT) -> ViewT: ...
```

Rules:

- `init`, `apply`, and `view` are synchronous and side-effect free. State is JSON-serializable and schema validated.
- The runtime subscribes once to committed Session events and drives every registered unit. Domain packages do not own parallel event subscriptions for the same projection.
- An uninterested fold returns the identical state object, permitting zero downstream publication work.
- `snapshot(session_id)` returns all requested whole values with one shared `as_of_seq`; clients never fold domain events themselves.
- Change feeds publish whole schema-validated values plus their sequence watermark, not bare deltas.
- Persisted cells are `(session_id, projection_key, state_version, seq, value)`. Version/schema mismatch or a cache watermark beyond the log causes discard and refold.
- Projection cache is an optimization only. The complete canonical log can rebuild every value, and a cache failure never changes Session truth.
- Registration is lifecycle-owned. Unloading a domain removes its key and cells from live snapshots; consumers treat a missing key as capability absence.

### 14. `ExecutionSandbox`

Purpose: enforce what an approved process invocation can physically affect.

Approval and confinement are independent:

```text
ApprovalRuntime: may this exact invocation begin?
ExecutionSandbox: what can the started process actually read, write, execute, and reach?
```

The normative policy is:

```text
SandboxPolicy
  filesystem_mode     read_only | workspace_write | danger_full_access
  workspace_root      canonical absolute path
  network_mode        none | governed | full_access
  process_mode        restricted | inherited
  required_enforcement full | partial_allowed | none
```

Rules:

- Policy is resolved per invocation from immutable Session/profile defaults plus an explicitly approved restrictive or escalated override.
- The sandbox provider returns both wrapped execution data and `enforcement = full | partial`. It never silently passes through an invocation requesting confinement.
- Missing or failed enforcement returns `SANDBOX_UNAVAILABLE` before command execution unless the resolved policy explicitly requests full access.
- Persistent shells, one-shot shell calls, subagent subprocesses, hooks, and workflow code use the same policy vocabulary. A surface may not advertise confinement it does not enforce.
- Workspace roots are canonicalized with filesystem semantics before boundary checks. Symlink/junction handling, private temp roots, environment scrubbing, and process-group cancellation are provider obligations.
- Network and process isolation are separate policy axes; filesystem confinement must not imply either.
- Mission Control shows requested policy, selected provider, enforcement completeness, and any approved escalation for each invocation.

### 15. `RuntimeInvariantRegistry`

Purpose: turn load-bearing runtime relationships into executable, owner-attributed contracts.

Rules:

- Each migrated harness package registers checks under one unique owner name and receives an exact disposer.
- Checks assert authoritative event ordering or mutable-data relationships, never mere class/method presence.
- Initial checks cover turn/step settlement, tool-call/result pairing, one-shot approval consumption, lease fencing, projection watermarks, child lineage, terminal run outcome, and scoped disposal.
- Invalid selection configuration and duplicate owner names fail at boot. Enabled checks run in lifecycle-owned child tasks and identify the owning package in every failure.
- Production can select checks by allow/block policy, but security and ledger-integrity checks are non-disableable.
- Registration completeness is mechanically verified: every migrated package either publishes checks or an explicit package-specific reason that it owns no observable invariant.

### 16. `RuntimeScope`

Purpose: make one scope identity govern both capability visibility and registration lifetime.

Rules:

- A scope key is opaque identity, not a user-controlled string. A live agent instance uses its exact runtime identity while durable authorization continues to use stable actor/session ids.
- Registries expose global entries followed by exact-scope overlays; scoped entries may shadow global names only within that scope.
- Reads never create scope layers. Empty layers are reclaimed.
- Every registration returns an idempotent exact-entry disposer. Scope disposal stops admission and awaits all owned removals/work before resolving.
- Tools, prompt sections, interception hooks, provider adapters, and projection contributions use the same scope owner.
- Existing static role/mode allowlists remain policy inputs during migration, but schema visibility, lookup, execution, and generated tool bindings must all resolve from the same effective scope.

### 17. `ArtifactStore`

Purpose: securely retain complete or explicitly truncated large outputs independently of their producer.

```text
ArtifactRef
  artifact_id
  locator
  content_sha256
  bytes
  completeness       complete | truncated
  media_type
  producer_kind
  producer_id
  owner_scope
  created_at
  expires_at
  retrieval_hint
```

Rules:

- Tools, jobs, web fetches, Session references, and subagents share this seam; producer-specific tables store only immutable references.
- Locator and suggested filename are opaque hints, never authority or trusted paths. Every retrieval rechecks authenticated actor, Session/workspace ownership, and retention state.
- Local storage uses a private `0700` root, random collision-resistant names, exclusive `0600` creation, atomic publication, and link-safe cleanup.
- Stored arguments and metadata pass a mandatory secret-redaction policy. Raw ambient environment is never attached.
- The store reports byte count and completeness truthfully. It must not call a clipped body "full output."
- Consumer policy decides inline head/tail preview and replacement. A storage failure preserves a successful bounded inline result when possible and emits an explicit retention failure; it does not convert the underlying tool execution into a false failure.
- Existing `tool_result_store` becomes the first compatibility provider and retains hash-checked references while migrating.

### 18. `SessionReferenceRuntime`

Purpose: prepare immutable, provenance-carrying cross-session context without treating recalled text as trusted instructions.

Every reference records source Session id, source format generation, `captured_through_seq`, label, content digest, compaction state, original/retained/omitted message and byte counts, truncation, and input position. The id is authoritative; labels are presentation metadata.

Rules:

- A reference is a snapshot at one source watermark, never a live alias to a changing conversation.
- Referenced content is framed as `untrusted_context` before entering the model request.
- Preparation has explicit count and byte/token budgets. Overflow either produces a bounded snapshot plus authorized `ArtifactRef`, or fails with a stable typed error.
- Self-reference, invalid reference, too many references, source-read failure, budget exhaustion, and cancellation remain distinct outcomes.
- Provenance stays tied to the source generation and is never reinterpreted as sequence coordinates in the receiving Session.

### 19. `TelemetryRuntime`

Purpose: export observability without allowing telemetry to impersonate canonical runtime truth.

Every stream and store is classified as exactly one of:

```text
canonical | projection | telemetry | ephemeral_stream
```

Rules:

- Canonical Session records may be mirrored one-to-one into a `ledger` telemetry channel. Process-only alerts use an `ops` channel with no canonical event identity.
- Telemetry is best effort and may be lost or duplicated. A handoff cursor means enqueued, not delivered; receivers deduplicate ledger mirrors by Session id, format generation, and sequence.
- `emit()` is a nonblocking enqueue. Callback/backend exceptions are contained and cannot break the agent loop or starve other subscribers.
- Redaction transforms an export copy only; it never rewrites the canonical ledger.
- Unlike DeepSeek's empty default, Jarvis ships mandatory fail-closed secret/private-layer redaction. A redaction failure withholds that export record.
- Deployment sharing status is explicit and inspectable. Profile visibility settings may reduce export but cannot erase authorized local audit truth.
- Shutdown stops admission and drains the telemetry backend to a deadline; unresolved delivery is reported, never claimed complete.

### 20. `ConnectionRuntime`

Purpose: make browser/Mission Control recovery generation-safe without replaying mutations.

Rules:

- One controller owns the active connection generation. A generation is published only after authentication, baseline acquisition, and a `ready` marker while incremental observation is already attached.
- Ended, malformed, failed, timed-out, or explicitly replaced streams invalidate the generation before retry.
- Cancellation stops delivery and awaits source settlement before replacement. Late readiness from an old generation cannot publish state.
- Reconnect uses bounded jittered backoff and may continue indefinitely while the network is available; browser offline suspends attempts and online restarts the sequence.
- Each domain stream retains its own cursor/baseline recovery. Connection retry never replays unary mutations, refreshes credentials, or infers tool/run outcomes.
- Gap detection is explicit. A reconnecting client receives a consistent projection snapshot plus subsequent changes from its watermark.

### 21. Later extension seams

These findings belong in the target architecture but do not block the core cutover:

- `RemoteContractGateway`: explicit allowlisted unary methods, exact input/output codecs, identity lookup through authoritative maps, cancellation, and stale-handle rejection. Streaming, pagination, and change feeds remain separate protocols.
- `GoalRuntime`: durable objective phase and revisioned compare-and-set mutations separated from process-local activation; each admitted continuation round carries goal id, revision, and round attribution.
- `TeamRuntime` (experimental): durable roster, queued-minus-delivered mailbox, revisioned task DAG, and advisory write-scope overlap. It must not claim cross-process consensus and cannot become protected core before standalone `SubagentRuntime` is stable.
- `HookBridge`: Claude Code/Codex hook compatibility as an adapter over native interception. Hook failures are contained, restrictive outcomes merge deterministically, and every invoked/result pair is log-only and turn-enclosed. A parsed halt or input rewrite is never advertised until the native runtime actually enforces it.
- `PTCPresentation`: the PTC-style surface from §11 — one model-authored program against a generated SDK over the existing tool registry, with `run_code` as the composition seam. Presentation only; the registry, approval, and settlement stay on the existing runtime. Defaults off; opt-in per profile.

### 22. `HarnessConformanceKit`

Purpose: prove public harness behavior through real composition without provider keys.

Required lanes:

- scriptable OpenAI-compatible HTTP/SSE fault server: reset, stall, malformed chunk, partial disconnect, empty response, rate limit, server error, tool call, and seeded mixed-failure runs
- deterministic LLM replay bound to parent and child Sessions, with an assertion that every recorded script and chunk was consumed
- committed Session-format corpus covering current generations, historical migration, exact refusals, and unchanged source bytes
- real loader/process smoke in isolated runtime homes and workspaces, with complete process-tree cleanup
- normalized snapshots of Session logs, model-visible output, system prompt, ordered tool schemas, projection values, and filesystem effects
- scope/disposal tests that prove registrations, callbacks, child work, ports, paths, and processes reach quiescence
- world verification: a tool's report is insufficient evidence of a file/process side effect; tests inspect the actual external state

Test normalizers may replace nondeterministic ids, clocks, and private paths, but must preserve event structure, ordering, omission counts, byte counts, digests, terminal reasons, and security-relevant fields.

## Phased roadmap

### Phase 0: inventory, characterization, and mandatory extraction

Before changing behavior:

- inventory every direct writer/reader of `chat_messages`, approval tables, agent runtime tables, tool routing maps, and terminal run outcomes
- classify every current eventbus, Central trace, SSE buffer, projection table, and compatibility store as canonical, projection, telemetry, or ephemeral
- inventory every shell/subprocess path and record its actual sandbox, network, environment, cancellation, and fail-open/fail-closed behavior
- document which existing tables become canonical and which become projections
- add characterization tests for successful text, tool-only output, empty response, retry after partial stream, cancellation before/after deltas, local-tool disconnect, approvals, and child dispatch
- establish the minimal-mode baseline from §12 (fixed prompt, two tools, no context injection) and record model-only success/failure on the same fixtures, so later phases can measure what the harness adds rather than assuming it
- establish `HarnessConformanceKit` fixtures for deterministic replay, scripted provider faults, production-loader smoke, and current Session/prompt/tool-schema snapshots
- because `core/services/visible_runs.py` is **7,290 lines** (measured 2026-09-08, not the 4,131 the repository's own list claimed), first extract the nearest coherent stream accumulation/settlement unit with compatibility re-exports before changing its logic. The scale matters for planning: this is the second-largest file in the repository, behind `heartbeat_runtime.py` at 7,569, and the extraction is a phase of work rather than a preparatory step
- add declared event ownership checks without changing the eventbus into the ledger
- introduce the `RuntimeInvariantRegistry` and register the existing load-bearing settlement, approval, and authority relationships as its first checks
- introduce the minimal `RuntimePluginLifecycle` contract for every newly extracted seam
- add a compatibility `EffectiveProfileSnapshot` adapter that resolves current config into a stable schema version/hash; full named-profile composition remains Phase 9

Exit criteria:

- current behavior is covered by focused tests and fault injection
- extraction is behavior-preserving
- source-of-truth inventory has no unresolved table or writer
- the agent identity/run/message authority map is ratified with no unresolved writer overlap
- feature flags and rollback metrics are named before rollout
- every later phase can record an effective profile hash and register/dispose its new seam through the minimal lifecycle contract
- the conformance kit reproduces current success, cancellation, disconnect, and provider-failure behavior without a live model key
- no surface claims sandbox enforcement more strongly than the inventory proves

### Phase 1: durable session ledger and shadow projection

Implement `SessionHandle`, cross-process write leases with fencing, immutable `SessionHeader`, guarded format generations, `chat_sessions.storage_mode`, creation/cutover transactions, `session_events`, append/flush/close APIs, per-session sequencing, `ProjectionRuntime`, projection checkpoints, and the compatibility projector. Keep legacy sessions authoritative in `chat_messages`; shadow-write only selected test sessions.

Exit criteria:

- atomic append and idempotent replay tests pass under duplicate delivery and process restart
- every reader/writer uses the shared committed storage-mode resolver, and only the projector can write compatibility rows for ledger sessions
- projector can rebuild selected `chat_messages` rows from an empty projection
- drift detection reports no mismatch for canary fixtures
- eventbus loss does not lose committed ledger events
- no production session changes read authority yet
- a second process cannot acquire or append through a competing write handle, and a stale fencing token cannot write after lease loss
- read-only interrupted-session inspection writes nothing; recovery appends balancing events only under write ownership
- current, historical-migratable, future-unsupported, and corrupt formats produce distinct verified outcomes while source generations remain byte-identical
- every registered projection can refold from an empty cache; snapshots share one `as_of_seq`, stale/version-mismatched cells are discarded, and cache failure cannot change truth

**Status 2026-09-09 (opus).** Built and tested, nothing cut over — every session is still `legacy`:

| Piece | File | Tests |
| --- | --- | --- |
| ledger, leases, fencing, sequencing, `storage_mode` | `core/runtime/db_session_ledger.py` | `tests/test_db_session_ledger.py` (25) |
| `ProjectionRuntime`, checkpoints, snapshots | `core/services/projection_runtime.py` | `tests/test_projection_runtime.py` (14) |
| compatibility projector + direct-write guard | `core/services/projection_chat_messages.py` | `tests/test_projection_chat_messages.py` (20) |
| drift detection and the cutover gate | `core/services/projection_drift.py` | `tests/test_projection_drift.py` (14) |
| `SessionHandle`, `SessionHeader`, format generations | `core/runtime/session_handle.py` | `tests/test_session_handle.py` (24) |

Three decisions worth carrying forward, because each was a bug the tests found rather than a design chosen up front:

* **`message_id` is derived from the event, not `uuid4()`.** The original write path generates a fresh id per call; a projector that copied that rule would produce a second identical row on every replay. Deriving the id is what makes a crash between the row work and the cursor cost a repetition instead of a duplicate — and it is why the cursor does not have to be atomic with the write.
* **The connections are pooled, so `with connect()` inside another `with connect()` is the *same* connection and commits the outer transaction on exit.** The write guard therefore takes the caller's open connection. Any future check placed mid-write must do the same.
* **Drift ignores `message_id` and normalises `content_json`.** `uuid4` against a derived id can never match, and text-vs-object is a difference in form, not content. Comparing them would flag every session and make the measurement worthless.

**Update, same day, after deploying.** Shadow writing is wired into
`append_chat_message` and two of the owner's real sessions run in `shadow`
(`chat-055b2f70…`, `chat-48db8cf9…`); `chat_messages` remains authoritative and
nothing has cut over. A legacy session pays 5.9 µs per message for the shadow
check — one lookup, no write.

The canary earned its keep within the hour, finding two defects that 136 tests
could not, because those tests supply their own events:

* **Compact markers were excluded in three places** — the shadow write, the
  backfill, and the drift comparison. Together that meant a session could read
  as *in agreement* and still lose its markers on cutover, because the detector
  was not looking at the thing that was missing. Production holds 102 markers
  across 14 sessions.
* **Append is not a repair.** Backfilling the one missing marker placed it at
  the *end* of the ledger (seq 579) while the table holds it at position 474,
  producing 291 disagreements from that point on. A backfill is only correct
  when the ledger is a *prefix* of the table; `backfill` now refuses otherwise
  and names the position where they diverge, and `reseed()` rewrites the whole
  session in table order — clearing its projection checkpoint, or the
  projection would believe it had already folded to 579 and skip everything.

The remaining Phase 1 work is the rest of the wiring: no writer calls
`SessionHandle` yet, and `store_compact_marker` deliberately raises for a
`ledger` session because marker writing has no handle behind it — a landmine
recorded as a test rather than hidden.

### Phase 2: stream settlement, retry, outcomes, and compaction

Implement `StreamSettlement`, `RetryRuntime`, `OutcomeProjector`, and `CompactionRuntime` over the ledger. Migrate one canary profile behind a kill switch. Preserve the existing streaming-production contract.

Exit criteria:

- every row in the settlement table has a test
- retries preserve accepted request history and obey total attempt/time/token/cost caps
- cancellation after delivered text records an interrupted surface anchor with the exact prefix
- failed partial attempts reset compatible UI state and never enter derived model history
- stale pumps cannot append after settlement
- exactly one terminal frame and one terminal run outcome are projected
- prepared requests can be reconstructed with route, prompt, ordered tool schemas, derived-history watermark, profile hash, and compaction generation
- compaction advances surface generation atomically or leaves it unchanged; overflow retries occur only after an advancing replacement

**Status 2026-09-09 (opus).** All four runtimes are built and tested as pure
contracts, and the settlement classifier is wired to the live answer path in
shadow. Nothing has replaced existing behaviour.

| Piece | File | Tests |
| --- | --- | --- |
| settlement table (13 rows) + exactly-once attempt ledger | `core/services/stream_settlement.py` | `tests/test_stream_settlement.py` (80) |
| retry policy and turn-wide budgets | `core/services/retry_runtime.py` | `tests/test_retry_runtime.py` (36) |
| reconstructable prepared request | `core/services/prepared_request.py` | `tests/test_prepared_request.py` (26) |
| one terminal run outcome | `core/services/outcome_projector.py` | `tests/test_outcome_projector.py` (28) |
| compaction that cannot loop | `core/services/compaction_runtime.py` | `tests/test_compaction_runtime.py` (28) |
| shadow comparison against the running code | `core/services/settlement_shadow.py` | `tests/test_settlement_shadow.py` (21) |
| extracted run-outcome state machine (Boy Scout) | `core/services/visible_run_outcome_state.py` | `tests/test_visible_run_outcome_state.py` (15) |

Three of these came from *this repository's* scars rather than from the DeepSeek
document, and they are the load-bearing ones:

* **`EMPTY_RESPONSE` requires that nothing was emitted.** `visible_runs.py`
  carries two warnings (lines ~2290 and ~4644) that a false empty-completion
  makes the fallback "wipe the streamed answer" — the system concluding no
  answer arrived while the user was looking at it. The rule is an assertion in
  the classifier, not only a test.
* **A failed attempt never becomes an assistant message.** An aihubmix quota
  error was once stored as an *assistant* message and surfaced inside the
  `[SELF]` anchor. A user-facing failure notice is now its own event kind with
  its own provenance, so the difference is visible in data rather than in tone.
* **`surface_generation` is the proof that compaction freed something.** Without
  it, context overflow is a loop that costs a model call per lap.

Two wiring mistakes worth recording, both found by measuring rather than by
reasoning:

* The shadow call first landed inside `if _collected_native_tool_calls:` and so
  measured only tool-calling runs. It now sits in the `finally` block — the one
  place every run passes — with the abandonment downgrade applied *before* the
  observation, so the shadow sees the final decision rather than the optimistic
  default.
* `central_switches.is_enabled()` is **fail-open**: it returns `True` for a key
  nobody has set. Correct for a gate protecting a function, wrong for a
  measurement on the visible answer path. The shadow reads the raw value and
  requires an explicit `enabled: true`.

Remaining for Phase 2: the cancellation path does not yet read the server-owned
resumable-buffer prefix (the classifier specifies it; nothing supplies it), and
no profile has been migrated — only the shadow comparison runs.

### Phase 3: tool definition adapter and durable invocation state

Build `ToolDefinitionV2` wrappers, `ExecutionSandbox`, and `ArtifactStore` compatibility providers for current simple tools and jarvis-code tools. Generate legacy OpenAI/Anthropic schemas and routing projections from the adapter while `jc_tool_catalog` remains authoritative for unmigrated tools. Phase 3 also introduces the minimal invocation-bound approval bridge: it stores the exact invocation digest and atomically consumes one decision while committing `dispatching`. Phase 4 migrates answerers, expiry, UI, and canonical storage behind `ApprovalRuntime` without weakening that safety invariant.

Exit criteria:

- execution provider, presentation mode, and UI metadata are separate
- canonical arguments/results validate against versioned schemas
- `prepared` commits before dispatch
- approval-required tools cannot enter rollout until the invocation-bound atomic approval bridge is active
- approval claim and `dispatching` commit in one transaction before crossing the provider boundary
- disconnect tests distinguish `aborted_before_dispatch` from `outcome_unknown`
- non-idempotent `outcome_unknown` is never automatically retried
- externalized results remain retrievable through hash-checked handles, with explicit completeness when storage caps apply
- every process-producing provider reports requested policy and actual enforcement; requested confinement fails before execution when unavailable
- persistent and one-shot shell paths obey the same policy contract, and no approval mode silently widens sandbox authority
- artifact files use private roots, exclusive owner-only creation, explicit completeness, content digests, authorized retrieval, redacted metadata, and link-safe cleanup

### Phase 4: approval runtime and authority migration

Choose the canonical existing approval store, migrate adapters, and move policy resolution, request/decision persistence, answerer dispatch, expiry, and the Phase 3 atomic claim bridge behind `ApprovalRuntime`.

Exit criteria:

- invocation digest/tool/provider/actor changes invalidate approval
- missing answerer, audit-write failure, expiry, cancellation, and restart fail closed
- duplicate, late, and cross-user answers cannot authorize execution
- a decision is consumed at most once by atomic claim
- Mission Control, UI, and CLI act as answerers without owning policy
- unattended child approval is pinned to rejection; wider authority requires a new parent-owned invocation and decision

### Phase 5: one-shot subagent runtime and `explore`

Map existing agent registry/run/message truth, implement child descriptors and provider capability negotiation, then wrap current `explore` as a one-shot `ExploreSubagentProvider`. Keep the existing `explore` tool as a compatibility alias returning final text.

Exit criteria:

- child identity is durable before work starts
- `explore` appears under its parent in Mission Control
- existing one-shot UX and result rendering remain compatible
- provider removal/new-start rejection and child failure are observable
- no continuable capability is advertised for `explore` unless implemented
- child authority/profile/tool scope is frozen before publication, cannot import ambient parent authority, and disposes through its owned `RuntimeScope`

### Phase 6: continuable agent providers

Move `task`, `spawn_agent_task`, `dispatch_code_mode_task`, Claude-dispatch, and agent-pool routing behind providers as each satisfies the continuation contract.

Exit criteria:

- canonical agent tables remain the only child/run/message truth
- start resolves on message acceptance, and send returns a message receipt rather than a reply
- direct-lineage authorization, leases, cold resume, interrupt acknowledgement, and orphan recovery are tested
- depth, child-count, provider, cost, token, time, tool, secret, and workspace limits are enforced across failover
- parent can continue while an accepted continuable child runs
- child tool schemas, lookup, execution, prompt sections, and generated bindings all reflect one effective scope rather than independent filters

### Phase 7: job runtime

Introduce `JobRuntime` with explicit durability, cancellation, output, reattachment, owner, lease, and retention capabilities. Migrate one adapter class at a time.

Exit criteria:

- process-local jobs become `lost` after restart rather than pretending to resume
- reattachable jobs prove process/provider identity before adoption
- kill acknowledgement and observed termination are distinct
- output cursors are bounded and replayable
- Mission Control reports stale leases and orphans
- cross-owner read/wait/kill/list and confused-deputy delegation attempts are denied and audited

### Phase 8: workflow runtime

Add non-resumable v1 `WorkflowRuntime` only after subagent and job contracts are stable. Restrict it to profiles that explicitly permit large orchestration.

Exit criteria:

- workflow and child start/end records pair by id
- workflow restart settles as `interrupted_by_restart`
- cancellation drains owned children to a configured deadline and reports survivors
- child transcripts remain in child sessions
- total child/cost/token/time/workspace authority is fixed at workflow start

### Phase 9: profiles and plugin lifecycle

Introduce versioned `ProfileComposer` and `RuntimePluginLifecycle` for `visible-owner`, `visible-member`, `jarvis-code`, `autonomous`, `maintenance`, `research`, and `safe-offline`.

Exit criteria:

- precedence and monotonic security narrowing are deterministic
- every run records effective profile schema version and hash
- Mission Control explains model, tools, approval, retry, compaction, memory, private layers, and subagent policy
- audit truth cannot be disabled by profiles
- plugin boot rejects missing/cyclic dependencies, and disposal reports unresolved ownership
- scoped registration is identity-based, exact-entry disposal is idempotent, empty layers are reclaimed, and disposal reaches quiescence
- requested and actual sandbox enforcement, telemetry sharing, and cross-session-context policy are visible in the effective profile

### Phase 10: Session references, telemetry, and connection recovery

Introduce `SessionReferenceRuntime`, `TelemetryRuntime`, and `ConnectionRuntime` after ledger/projection contracts are stable.

Exit criteria:

- cross-session context carries source format/sequence/digest/omission provenance, is immutable and marked untrusted, and obeys count plus byte/token budgets
- telemetry records are classified separately from canonical truth, use mandatory export-copy redaction, tolerate loss/duplication honestly, and cannot authorize or settle work
- reconnect publishes only a ready generation after baseline acquisition, fences late old-generation callbacks, and resumes each stream from an explicit watermark
- connection retry never replays a unary mutation, refreshes credentials, or guesses a tool/run result

### Phase 11: cutover and legacy retirement

Expand `event_ledger_v1` by canary profile after the observation window, migrate eligible historical sessions offline, and retire direct legacy writers only after drift-free verification.

Exit criteria:

- each session has exactly one read/write authority
- rollback has been exercised without deleting ledger events
- direct `chat_messages` writes fail for ledger sessions
- old approval, tool-routing, and agent adapters are read-only projections or removed
- capability audit and Mission Control show no orphaned duplicate subsystem

**Status 2026-09-11 (opus).** The observation window has enough data, and the
second criterion is exercised.

*Window.* `session_events` holds 2 509 events across three sessions,
2026-09-09 10:14 → 2026-09-11 08:55. All three are `shadow`; drift is zero:

| session | events | drift |
|---|---|---|
| `chat-055b2f70…` | 803 | `enige=True`, `bevis=verificeret` |
| `chat-48db8cf9…` | 579 | `enige=True`, `bevis=verificeret` |
| `chat-e58f16c5…` | 1 127 | `enige=True`, `bevis=verificeret` |

`projection_drift.may_cut_over()` returns `True` for all three. The canary
carried the heaviest traffic this system has seen — explore agents, five
sacrificial turns, ~72 restarts, a bridge outage and a frozen event loop — with
no disagreement. That is a better window than a quiet day would have given.

*Criterion 2 — rollback exercised without deleting ledger events.* Run on the
dormant `chat-48db8cf9…`, fingerprinting the ledger rows (not just counting
them) at each step:

```
before     shadow   579 events   sha256[:16] 788e0dedd187c4fe   may_cut_over=True
rollback   legacy   579 events   788e0dedd187c4fe               may_cut_over=False
re-enter   shadow   579 events   788e0dedd187c4fe               may_cut_over=True
```

`abandon_shadow()` only flips `chat_sessions.storage_mode`; the events are
untouched and still comparable afterwards. Re-entry through `enable_shadow()`
reported `beskeder: 579, skrevet: 0` — `backfill` is idempotent in production,
not only in its docstring, and `UNIQUE(session_id, event_id)` enforces it at
the schema level rather than in code.

**Cutover taken 2026-09-11 (opus), on Bjørn's word.** The canary
`chat-e58f16c5…` is now `ledger`, at seq 1 141 with the row fingerprint
unchanged across the flip (`7336996b71ece52f`). Drift after the cutover:
1 141/1 141, `bevis=verificeret`, and the session still reads normally.

*Criterion 1 — one read/write authority.* Satisfied for the canary: `shadow`
means two by definition, `ledger` means the event is canonical and
`chat_messages` is derived.

*Criterion 3 — direct writes fail for ledger sessions.* Verified differentially
rather than in isolation, because a guard that raises for everything proves
nothing:

```
canary (ledger)          -> DirekteSkrivningAfvist
control group (shadow)   -> passes through
```

*The write path, proven end to end.* Not on Bjørn's conversation — a throwaway
session was walked `legacy → shadow → ledger` and written through:

```
before   ledger=3  chat_messages=3  seq=3
append   message-bdd70c4257234be8
after    ledger=4  chat_messages=4  seq=4   drift 4/4, enige=True
read path returns the new message
```

So the event lands in the ledger, the projector materialises the row, and the
ordinary read path sees it. The rehearsal ran on a session nobody would miss,
because the flip is one-way and a broken write path would have surfaced on
Bjørn's next message instead of on a probe.

*Criterion 5 — no orphaned duplicate subsystem.* The capability audit over 996
services reports 364 LIVE, 618 PARTIAL, 0 STALE, 13 SUSPICIOUS, 1 ORPHAN. None
of the 14 is a **duplicate**, which is what the criterion asks about:

- the single orphan, `central_gardener.py`, has zero importers — measured —
  and is not a duplicate. **It is also not dead code**, and this document said
  so wrongly on first writing: its docstring states «"Yes, Jarvis"-gaten =
  mennesket kører execute + godkender», and `COMMIT_HISTORY.md:5587` already
  settled it on 19 August — *«nul referencer er den KORREKTE tilstand for den.
  Indekset måler referencer, og et værktøj man kalder i hånden ser identisk ud
  med forladt kode.»* An index cannot distinguish a hand-run tool from
  abandoned code, and this audit is itself hand-run.
- four of the thirteen suspicious were added the day after this spec
  (2026-09-09): `compaction_runtime`, `ledger_recovery`, `prepared_request`,
  `retry_runtime`. Built and awaiting wiring is the expected state
  mid-migration.
- three more — `model_benchmark`, `model_catalogue_sweep`, `model_probe` —
  were added 2026-09-07, the day *before* this spec, and appear in no spec
  file. Calling them "this spec's components" was wrong; they predate it.
  `permission_axes` (2026-09-06) is the one this list should have named: it
  is cited twice in this document and was left out.
- `bro_broker.py` reads as a duplicate bridge and is not one: it *uses*
  `jarvisx_bridge.bridge_registry` and waits for the Phase 4 listener.

*What the audit was measuring.* `capability_matrix.md` had not been
regenerated since **2026-07-23** (`781c8598`). The proof is a shift of exactly
+51 days on two unrelated files — `central_gardener` 16d→67d, `bro_broker`
38d→89d — and both old figures were correct *for 23 July*. So the 1 965 changed
lines are not a changed system; they are fifty days of arrears in a hand-run
report whose output looks equally authoritative at any age. The numbers this
document quoted before tonight were seven weeks old.

The audit half therefore holds. **The Mission Control half cannot be measured:**
MC was removed in `b8c98551` and is being rebuilt, so there is no surface to
sweep. The criterion as written outlives the subsystem it names.

*Criterion 4 — old adapters are read-only projections or removed.* **Not met,
and not close.** Measured write recency and write sites:

| adapter | newest row | write sites in code |
|---|---|---|
| `approval_claims` | today | 7 |
| `tool_router_decisions` | today | 1 |
| `agent_runs` / `agent_messages` / `agent_registry` | today | 2+ |
| `capability_approval_requests` | 2026-05-15 | 5 |
| `tool_intent_approval_requests` | 2026-08-17 | 4 |
| `jc_agent_audit` | 2026-08-04 | 1 |
| `approval_notification_outbox` | 2026-09-06 | 3 |

The live three are still **direct writers**, not projections: there is no
shadow mode, no drift comparison and no `storage_mode` equivalent for approval,
tool-routing or agent state. The dormant four are not removed either — every
one still has write sites that simply have not fired. A table with old rows and
live code is not a retired adapter; it is an adapter waiting to surprise
someone.

Closing this criterion means repeating the `chat_messages` cutover three more
times — build the projection, run it in shadow, verify drift, flip — and the
runtimes from Phases 3–5 exist but none of that scaffolding does.

*Incidental.* `tool_router_decisions` stamps `2026-09-11 19:38:09` — no zone,
space separator — where every other table writes ISO with `+00:00`. A reader
using `fromisoformat` gets a naive datetime and treats it as local. Same class
as the `_friskere_end` fallback: true about its own writer, false about the
world.

Two sessions remain in `shadow` on purpose as a control group.

### Phase 12: optional remote, goal, hook, and team extensions

After the core cutover, implement only extensions justified by an active Jarvis consumer: strict generated/declared remote contracts, revisioned `GoalRuntime`, native-enforced hook compatibility, and finally experimental `TeamRuntime` coordination.

Exit criteria:

- unmarked remote methods are unreachable, request/result codecs are exact, cancellation is cooperative, and unary RPC is not reused for streams
- goal mutations use revision CAS, durable lifecycle remains separate from live activation, and continuation rounds retain goal attribution
- hooks advertise only effects the native runtime enforces; failures cannot crash the loop, pairing is invariant-checked, and disposal drains detached commands
- TeamRuntime remains optional until durable mailbox de-duplication, task DAG invariants, exact-member authority, recovery, and advisory write-scope semantics are proven

## Non-goals

- Do not port Jarvis to TypeScript.
- Do not replace Mission Control with DeepSeek's UI assumptions.
- Do not remove Jarvis' identity, private layers, chronicle, or memory model.
- Do not rewrite `visible_runs.py` in one large pass.
- Do not make workflows the default for normal delegation.
- Do not expose private inner-life records as child-agent transcripts.
- Do not use the asynchronous eventbus as the durable session ledger.
- Do not promise resumable workflows or jobs where the underlying provider cannot support them.
- Do not migrate every historical session before new-session canaries prove the ledger.
- Do not port Cordis, DeepSeek's JSONL/Zstandard backend, JavaScript workflow runtime, or generated TypeScript gateway as implementation dependencies.
- Do not treat artifact locators, Session labels, tool visibility, telemetry cursors, or live runtime objects as authorization credentials.
- Do not imply that filesystem confinement also supplies network or process isolation.
- Do not ship TeamRuntime as protected core while its guarantees remain process-local or its Jarvis consumer is hypothetical.
- Do not expose a hook halt, input rewrite, continuation result, or remote stream as supported until the native runtime enforces its complete contract.

## Design risks

Risk: adding another log beside `chat_messages` creates dual truth.

Mitigation: authority is selected per session with immutable `storage_mode`; shadow mode is comparison-only, projection is idempotent, and cutover requires verified zero drift.

Risk: a remote/client tool performs a side effect but loses its result.

Mitigation: commit invocation intent before dispatch, distinguish `outcome_unknown`, reconcile late results by invocation id, and prohibit blind retries of non-idempotent effects.

Risk: an approval is replayed or applied to altered arguments.

Mitigation: bind one-shot approval to the canonical invocation digest and authority context, then consume it by atomic compare-and-set immediately before dispatch.

Risk: provisional streamed text diverges from model-visible history.

Mitigation: cancellation anchors delivered text; failed retryable attempts emit explicit UI reset/replacement and stay out of derived history.

Risk: subagent runtime can overcomplicate simple `explore`.

Mitigation: keep the one-shot compatibility alias, advertise only supported provider capabilities, and reuse the canonical agent registry rather than creating a parallel child database.

Risk: workflows give the model too much orchestration power too early.

Mitigation: workflow tool requires explicit profile permission and fixed depth, child, cost, token, time, provider, tool, and workspace budgets. V1 is explicitly non-resumable.

Risk: named profiles become a second configuration system or hide audit truth.

Mitigation: profiles are deterministic projections of versioned config, each run records the effective hash, and authorized Mission Control audit recording cannot be disabled.

Risk: event declarations become ceremony.

Mitigation: generate the global event registry from small per-service declarations and enforce with tests.

Risk: two Jarvis processes both believe they own one Session and append valid but conflicting continuations.

Mitigation: require one cross-process write lease with a transaction-checked fencing token for every append; recovery and continuation use the same handle contract.

Risk: an upgrade silently misreads a future or historical Session format.

Mitigation: distinguish unsupported format from corruption, retain immutable source generations, publish migrations copy-on-verify, and pin accepted plus rejected historical artifacts in the conformance corpus.

Risk: projection checkpoints become a second source of truth or combine values from different cuts.

Mitigation: projections are versioned pure folds over the ledger, cache rows are disposable hints, and multi-key snapshots carry one shared `as_of_seq`.

Risk: UI permission labels promise confinement that the executor does not provide.

Mitigation: approval and sandbox are separate facts, every provider reports enforcement completeness, and any requested confined mode fails closed when its mechanism is unavailable.

Risk: retained tool/session output leaks secrets or can be fetched across owners.

Mitigation: use opaque non-authoritative locators, mandatory retrieval authorization, redacted metadata, private exclusive files, content hashes, explicit retention, and link-safe cleanup.

Risk: recalled cross-session text injects stale or hostile instructions without provenance.

Mitigation: capture an immutable source watermark and digest, record omissions, apply strict budgets, and frame the inserted material as untrusted context.

Risk: telemetry loss or duplication is mistaken for runtime state.

Mitigation: classify telemetry separately, use canonical sequence identities only for de-duplication, make delivery best effort explicitly, and prohibit telemetry consumers from authorizing or settling work.

Risk: reconnect duplicates a mutation or publishes stale state from a cancelled connection.

Mitigation: use generation fencing, baseline-before-ready, settle-before-replace, explicit stream watermarks, and never replay unary calls in the connection layer.

Risk: runtime checks or hooks destabilize the hot loop.

Mitigation: checks observe owner-defined relationships, hook/observer exceptions are contained, detached work is lifecycle-owned, and security/ledger checks fail loudly without executing arbitrary repair.

## Acceptance tests for the full spec

- Ledger append allocates a unique monotonic session sequence and is idempotent by event id under duplicate submission.
- A Session admits one cross-process writer; stale fencing tokens fail, lease loss is observable, close is idempotent and quiescent, and read-only inspection cannot persist repair.
- Crash recovery preserves every complete event, discards only a torn physical tail, and appends interruption closers only after acquiring write ownership.
- Current and historical Session formats restore through the declared catalog; a future format is refused distinctly from corruption, migration leaves source bytes unchanged, and publication races cannot overwrite a changed source.
- A projector crash between row work and cursor advancement replays without duplicate messages; eventbus loss does not lose ledger truth.
- Projection units are pure, versioned, schema-validated folds; every multi-key snapshot has one `as_of_seq`, stale or incompatible caches are discarded, and an empty cache reproduces the same values.
- Legacy and ledger sessions each use exactly one read/write authority, and rollback does not reinterpret or delete committed ledger events.
- A guarded one-way storage-mode cutover makes the backfill checkpoint and new authority visible atomically to every shared reader/writer.
- Surface replacement rejects stale generations, invalid/non-contiguous ranges, protected boundaries, and overlapping active replacements; deterministic replay yields one model surface.
- A prepared request can reconstruct route/model parameters, complete ordered tool schemas, prompt, history watermark, profile hash, compaction generation, and body digest after definitions/configuration change or restart.
- Every terminal stream outcome in the normative table settles to the specified event/history/action combination.
- Cancellation after delivered text records the exact interrupted prefix in model history; cancellation before text does not create a surface message.
- Cancellation uses the highest contiguous server resumable-buffer frame sequence, never an inferred SSE client acknowledgement.
- A retryable partial failure records `assistant_attempt`, resets provisional UI content, fences stale deltas, and resamples from byte-equivalent accepted history.
- Retry schedule/start ordering, total attempt/time/token/cost caps, failover accounting, kill switch, and fault injection are verified.
- A tool invocation is durable before dispatch and includes definition version, provider, argument digest, effect class, and approval reference.
- Approval consumption and durable `dispatching` state commit in one transaction before provider I/O.
- Every live or recovered transition to `outcome_unknown` appends exactly one balancing `TOOL_OUTCOME_UNKNOWN` result; late reconciliation is log-only and cannot create a second result for that call.
- Disconnect before proven dispatch becomes `aborted_before_dispatch`; disconnect after possible dispatch becomes `outcome_unknown`.
- A non-idempotent `outcome_unknown` cannot retry automatically; a late result reconciles exactly once by invocation id.
- A clipped tool result includes a hash-checked retrieval handle and stable model rendering.
- Artifact retention reports exact bytes and completeness, uses private exclusive storage, rejects unauthorized cross-owner retrieval, redacts protected metadata, and cannot be redirected through a symlink or suggested filename.
- Requested confined execution never falls through to an unconfined command; full, partial, unavailable, and explicit full-access modes are distinguishable for one-shot and persistent shell paths.
- Approval cannot execute after argument/provider/tool-version/actor changes, missing answerer, audit failure, expiry, cancellation, duplicate answer, restart race, or cross-user answer.
- One approval decision authorizes at most one invocation through atomic claim.
- `explore` publishes a durable one-shot child before work and Mission Control shows it under the canonical parent.
- Unsupported continuation fails before child mutation and is not advertised by the provider.
- A continuable child enforces lineage authorization, leases, cold resume, message acceptance semantics, interrupt acknowledgement, and global budgets.
- A child starts with a frozen scope, cannot inherit or widen ambient parent authority, rejects unattended approval, and removes every scoped tool/prompt/adapter contribution on quiescent disposal.
- Job restart behavior matches declared durability; kill acknowledgement is distinct from observed termination; stale leases/orphans are visible.
- Every job operation revalidates authenticated authority; cross-owner and confused-deputy requests are denied and audited.
- Workflow restart settles non-resumable v1 as interrupted, cancellation drains owned children to deadline, and surviving children are reported.
- Profile composition is deterministic, security overlays only narrow authority, every run records its profile hash, and audit truth remains available to authorized Mission Control.
- Plugin boot rejects missing/cyclic dependencies; disposal stops admission and records work that outlives its deadline.
- Runtime invariant checks detect invalid turn, tool, approval, lease, projection, lineage, settlement, and disposal relationships and attribute each violation to its owner package.
- Cross-session references retain source generation, sequence watermark, digest, omissions, and untrusted framing; self-reference, count, read, budget, and cancellation failures stay distinct.
- Telemetry export is nonblocking, redacted on a copy, honest about loss/duplication, separately identifies ledger mirrors and ops signals, and cannot change canonical state.
- A connection generation is invisible until ready after baseline acquisition; cancelled generations cannot publish late, reconnect resumes streams by watermark, and unary mutations are never replayed.
- Keyless replay and real-loader smoke reproduce success plus scripted reset, stall, malformed chunk, partial disconnect, rate limit, server error, cancellation, and teardown cases with Session/prompt/tool/workspace snapshots.
- Optional remote contracts reject unmarked methods and malformed inputs/outputs; GoalRuntime uses revision CAS; HookBridge advertises only enforced outcomes; TeamRuntime remains feature-gated until its mailbox/task invariants pass recovery tests.
- Compaction success advances one surface generation atomically; failed compaction preserves the prior generation and cannot unlock an overflow retry.

## Implementation note

The dependency order is mandatory: characterize, extract, establish conformance fixtures, runtime invariants, and minimal lifecycle/profile snapshots; establish handle-owned ledger truth plus projection folds; add stream settlement/retry/outcomes/compaction; then tools, sandbox, artifacts, and approvals; then one-shot and continuable subagents; then jobs and workflows; then full named-profile/scoped lifecycle composition; then Session references, telemetry, and connection recovery; finally cut over before considering optional remote, goal, hook, or Team extensions. Each phase ships behind its own flag and meets its exit criteria before the next phase uses the seam.

This specification is implementation-ready at the architecture level, but each phase still requires a repository-specific implementation plan naming exact modules, migrations, tests, feature flags, metrics, and rollback commands. No phase authorizes a broad rewrite of `visible_runs.py` or another oversized core file.

## Bottom line

DeepSeek Harness shows what a clean generic agent harness looks like. Jarvis already has a stronger long-lived entity model. The spec target is therefore:

```text
Jarvis identity + memory + Mission Control
  on top of
append-only session truth + typed seams + durable stream settlement + first-class subagents
  + truthful confinement + versioned projections + executable invariants
```

That is the combination worth building toward.
