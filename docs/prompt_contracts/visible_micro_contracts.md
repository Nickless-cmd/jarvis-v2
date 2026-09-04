# Visible Prompt Micro-Contracts

Small contracts that must stay true when editing the visible prompt.

## Cache Boundary

Stable identity, rules, tool schemas and history stay before
`DYNAMIC_TAIL_SENTINEL`. Per-turn memory, time, current state and routing hints
stay after it so DeepSeek-style prefix caching keeps working.

## Personal Context Before Web

If the user asks about "my", "our", remembered decisions, workspace state, or
Jarvis' own work, route through `recall`, `search_memory`, or Jarvis brain
before using public web tools. Web/data tools are for explicit current,
public, or external information.

## Memory Must Matter

Visible MEMORY.md injection is for facts that can change the answer, not for
generic background. Selection may find candidates, but answer-impact gating
decides whether they are worth carrying into the turn.

## Skills Are Lazy

Prompt/tool surfaces should carry skill summaries by default. Full `SKILL.md`
instructions are loaded only after a strong match, explicit skill selection, or
`load_full=true`.

## Tool Turns Must Answer

After tools have run, a final response of only "done", "ok", or empty text is
not a real answer. The runtime must force one tool-free synthesis attempt before
falling back to cutoff messaging.

## Impact Beats Inclusion

Telemetry should distinguish "section was injected" from "section appears to
have affected the answer". Use answer-overlap impact signals to find sections
that burn tokens without changing output.
