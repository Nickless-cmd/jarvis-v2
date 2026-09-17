# Visible Task Terminal Recovery Design

## Goal

A visible Jarvis task must never silently disappear because one provider call,
agentic loop, process, or SSE segment ended. Recoverable endings checkpoint,
notify the user, and continue. `completed` is reserved for positive evidence
that the task is actually finished.

## Lifecycle Model

The runtime distinguishes three lifetimes:

1. A provider attempt may end because of stop, length, error, or timeout.
2. A run segment may end because of budget, process lifecycle, guard, or failure.
3. A user task ends only as `completed`, `waiting_for_user`, `cancelled`, or
   `failed_terminal`.

`message_stop` closes only the current SSE segment. It is not proof that the
task completed.

## Central Terminal Decision

A focused `visible_terminal_policy` module owns terminal classification. It
accepts the observed run exit, provider finish reason, forced-finalize state,
pending tool intent, checkpoint availability, and explicit user cancellation.
It returns one of:

- `completed`: clean model stop and no evidence of unfinished work.
- `waiting_for_user`: approval, question, or pause-and-ask state.
- `recovering`: budget, truncation, retry exhaustion, provider failure,
  unsupported follow-up, shutdown, guard stop, or unfinished tool intent.
- `cancelled`: explicit user cancellation only.
- `failed_terminal`: recovery cannot proceed after bounded attempts.

No adapter, loop `break`, detached runner, or SSE translator may independently
upgrade an outcome to `completed`.

## Recovery Flow

For a recoverable ending the runtime:

1. Saves the latest agentic checkpoint and working conclusion.
2. Emits a structured `run_recovery` event with reason, action, and chain count.
3. Produces a bounded checkpoint synthesis without tools when useful.
4. Closes the current stream segment with a non-success stop reason.
5. Starts a continuation segment in the same session from the checkpoint.

If the synthesis contains tool-call syntax or unfinished action intent, that is
evidence that the task is not complete. The intent is retained for continuation
and the segment cannot be classified as `completed`.

Continuation chains remain bounded. Exhausting the chain emits a visible
`failed_terminal` notification containing the reason and preserved checkpoint;
it never silently reports success.

## DeepSeek Tool Intent

DeepSeek DSML parsing supports both known wrappers:

- `<｜｜DSML｜｜tool_calls>...`
- `<｜｜DSML｜｜ calls>...<｜｜DSML｜｜ invoke ...>`

Raw DSML never reaches visible chat. When tools are unavailable, detected DSML
is treated as pending tool intent rather than ordinary final prose.

## Stream Contract

Every stream still receives a terminal `message_stop`, including failures, so
clients cannot remain stuck in `working`. Before it, the server emits a
structured status event and a `message_delta.stop_reason` matching the task
state. Synthetic terminal frames must carry a reason and must not imply
`end_turn` or `completed`.

Desk renders `run_recovery` and terminal failure events as timeline notices in
chatview. Recovery notices state why the segment ended and that Jarvis is
continuing. They are not inserted into Jarvis' assistant prose.

## Process Failure

Graceful shutdown writes a durable checkpoint and never starts new work in the
dying process. The checkpoint is surfaced for resume after startup. An
unhandled detached-run crash emits a structured failure/recovery event before
its terminal frame. A host power loss can lose the in-flight token tail, but
the last durable checkpoint remains resumable.

## Safety

Explicit user cancellation remains final. Security and approval gates may move
the task to `waiting_for_user`; they do not auto-approve or continue risky work.
Recovery never fabricates a user message or consent.

## Verification

Focused tests cover terminal classification, both DSML dialects, forced-final
unfinished intent, budget and guard recovery, detached-run crashes, truthful SSE
stop reasons, bounded continuation, and clean completion without continuation.
