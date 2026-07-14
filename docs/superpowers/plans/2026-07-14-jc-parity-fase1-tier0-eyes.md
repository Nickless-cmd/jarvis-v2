# Fase 1 — [CLIENT] Tier 0 Stability Contracts (A1–A8) + Client Eyes — Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development.

**Goal:** Make jarvis-code's client-owned turn loop as stable as Claude Code by extracting it into a pure, UI-free `jc_agent_loop` module and building the eight Tier 0 stability contracts (A1–A8) as testable behaviors, so a broken/empty/truncated turn is never accepted as a valid "done" — plus client-side eyes (image input via `read_file` + composer paste).

**Architecture:** A new pure module `src/jc_agent_loop.py` owns an `AgentLoop` class with dependency-injected `step_fn` (model call) and `tool_fn` (tool executor) and an optional `emit` sink — so the whole loop is testable with a mock provider (exactly the fault-injection harness §9 asks for). Two helper modules carry pure logic: `src/jc_tool_result.py` (cap→spill→redact, A4) and `src/jc_multimodal.py` (base64/media-type + image blocks). `repl_ptk._turn_worker` becomes a thin adapter that wires real `step_fn`/`tool_fn` and renders emitted events. All eight contracts are reimplemented client-side — **jarvis-code CANNOT import `core.*`**; each task states where its logic lives.

**Tech Stack:** Python 3.10+ (runs in conda env `ai`), `httpx`, `prompt_toolkit` 3.0.52, `pytest`. Tests run: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest <path> -o addopts="" -q`. No new third-party deps.

---

## File Structure

**Created (client repo `/home/bs/jarvis-code`):**
- `src/jc_agent_loop.py` — pure UI-free turn loop; owns `StepResult`, `TurnResult`, `AgentLoop`; hosts contracts A1, A2, A3, A5, A6, A7. One responsibility: run a client-owned agentic turn to a guaranteed terminal outcome.
- `src/jc_tool_result.py` — A4: uniform cap on any tool result → spill-to-disk with a visible "truncated N" marker + secret redaction of the spill file. One responsibility: bound tool-result size before it enters the message history.
- `src/jc_multimodal.py` — client eyes: `read_file_block` (base64 + media_type for images/binaries), `build_image_block` (paste → typed content block). One responsibility: turn bytes/files into typed multimodal content blocks.
- `tests/test_jc_agent_loop.py` — TDD for A1, A2, A3, A5, A6, A7 + the §9 fault-injection acceptance harness.
- `tests/test_jc_tool_result.py` — TDD for A4.
- `tests/test_jc_multimodal.py` — TDD for read_file base64/media-type + image blocks.

**Modified (client repo):**
- `src/tools.py` — A8: wrap `route_tool_call` forwarding in try/except → typed `{status:error}`; and route `local_read_file` through `jc_multimodal.read_file_block` for the media-type branch.
- `src/api.py` — A6: surface `finish_reason` from the server `done` event in `agent_step_stream` and `agent_step` (default `None` when absent — backward compatible).
- `src/repl_ptk.py` — wire `AgentLoop` into `_turn_worker` (adapter); add composer image-paste key binding.
- `tests/test_tools.py` — additions for A8 + read_file media-type.

**NOT touched here (server, Fase 0):** `apps/api/jarvis_api/routes/agent_loop.py`. This plan is [CLIENT]-only. Server finish_reason plumbing and content-array acceptance are Fase 0 prerequisites; the client degrades gracefully without them.

---

### Task 1: [CLIENT jarvis-code] `jc_agent_loop` module + A1 terminal guarantee

Extract repl_ptk's turn loop into a pure, dependency-injected module and encode the terminal-guarantee: **never treat empty-content + no-tool_calls as done.** This is the Fase 0.5 substrate seed; if `src/jc_agent_loop.py` already exists from a separate Fase 0.5 worker, adapt it (keep the public surface below).

**Files:**
- Create `src/jc_agent_loop.py`
- Test: `tests/test_jc_agent_loop.py`

**Reference (current UI-bound loop being extracted):** `src/repl_ptk.py:811-870` (`_turn_worker`) and `:979-1036` (`_run_one_step`). The extraction preserves the round structure but makes `step_fn`/`tool_fn` injectable and removes prompt_toolkit calls.

**Steps:**

- [ ] Step: Write failing test `tests/test_jc_agent_loop.py` with the module contract and A1:
```python
from src.jc_agent_loop import AgentLoop, StepResult, TurnResult


def _loop(steps, tool_results=None, **kw):
    """Build an AgentLoop driven by a scripted list of StepResult."""
    seq = list(steps)
    calls = {"n": 0}
    def step_fn(messages, tools):
        i = calls["n"]; calls["n"] += 1
        return seq[min(i, len(seq) - 1)]
    tr = list(tool_results or [])
    def tool_fn(tool_call):
        return tr.pop(0) if tr else {"status": "ok"}
    return AgentLoop(step_fn=step_fn, tool_fn=tool_fn, max_rounds=kw.get("max_rounds", 6),
                     emit=kw.get("emit"))


def test_terminal_on_content_no_toolcalls():
    loop = _loop([StepResult(content="the answer", tool_calls=[], finish_reason="stop")])
    res = loop.run_turn("q")
    assert isinstance(res, TurnResult)
    assert res.status == "done"
    assert res.final_text == "the answer"


def test_empty_plus_no_toolcalls_is_NOT_terminal():
    # A1 core: an empty step must NOT end the turn as 'done'. With no recovery
    # steps scripted it must end BLOCKED (never silently 'done' with empty text).
    loop = _loop([StepResult(content="", tool_calls=[], finish_reason="stop")],
                 max_rounds=3)
    res = loop.run_turn("q")
    assert res.status != "done"
    assert res.final_text.strip() == "" and res.status in ("blocked", "empty")


def test_turnresult_always_has_envelope():
    loop = _loop([StepResult(content="hi", tool_calls=[], finish_reason="stop")])
    res = loop.run_turn("q")
    assert res.usage is not None and res.rounds >= 1 and res.status is not None
```
- [ ] Step: Run (expected FAIL — module missing): `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/test_jc_agent_loop.py -o addopts="" -q`
- [ ] Step: Implement `src/jc_agent_loop.py`:
```python
"""Pure, UI-free client-owned agentic turn loop (Tier 0 substrate).

jarvis-code CANNOT import core.* — every stability contract A1..A8 is
reimplemented here client-side. UI (prompt_toolkit) is injected via `emit`;
model + tools are injected via `step_fn` / `tool_fn` so the whole loop is
testable against a mock provider (the §9 fault-injection harness)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# finish_reason classification (A6). Terminal = safe to stop when no tool_calls.
_TERMINAL_FINISH = {"stop", "end_turn", "tool_calls", ""}
# Non-terminal = truncated/blocked mid-answer → continue, do NOT accept as done.
_NONTERMINAL_FINISH = {"length", "content_filter", "max_tokens"}


@dataclass
class StepResult:
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: Optional[str] = None
    usage: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TurnResult:
    status: str                       # done | blocked | empty | error
    final_text: str = ""
    rounds: int = 0
    usage: dict[str, Any] = field(default_factory=dict)
    reason: str = ""                  # human-readable for blocked/error


class AgentLoop:
    def __init__(self, *, step_fn: Callable[[list, list], StepResult],
                 tool_fn: Callable[[dict], dict],
                 max_rounds: int = 60,
                 emit: Optional[Callable[[dict], None]] = None,
                 tools: Optional[list] = None):
        self.step_fn = step_fn
        self.tool_fn = tool_fn
        self.max_rounds = max_rounds
        self.emit = emit or (lambda ev: None)
        self.tools = tools or []
        self.messages: list[dict[str, Any]] = []

    # ── A1: is this step a genuine terminal answer? ──
    @staticmethod
    def _is_terminal(step: StepResult) -> bool:
        if step.tool_calls:
            return False
        if not (step.content or "").strip():
            return False               # A1: empty is NEVER terminal
        fr = (step.finish_reason or "").lower()
        if fr in _NONTERMINAL_FINISH:  # A6: truncated answer is NOT terminal
            return False
        return True

    def run_turn(self, user_input: str, *, prior_messages: Optional[list] = None) -> TurnResult:
        self.messages = list(prior_messages or [])
        self.messages.append({"role": "user", "content": user_input})
        usage: dict[str, Any] = {}
        rounds = 0
        for _ in range(self.max_rounds):
            rounds += 1
            step = self.step_fn(self.messages, self.tools)
            if step.usage:
                usage = step.usage
            if step.error:
                return TurnResult(status="error", rounds=rounds, usage=usage,
                                  reason=str(step.error))
            if step.tool_calls:
                # work round — handled fully in Task 7 (A7). Minimal here:
                self.messages.append({"role": "assistant", "content": step.content,
                                      "tool_calls": step.tool_calls})
                for tc in step.tool_calls:
                    result = self.tool_fn(tc)
                    self.messages.append({"role": "tool", "tool_call_id": tc.get("id", ""),
                                          "name": (tc.get("function") or {}).get("name", ""),
                                          "content": json.dumps(result, ensure_ascii=False)})
                continue
            if self._is_terminal(step):
                return TurnResult(status="done", final_text=step.content,
                                  rounds=rounds, usage=usage)
            # non-terminal, no tool_calls → empty or truncated. Recovery in Task 2/A2.
            # Baseline (A1): never return 'done'.
            return TurnResult(status="empty", final_text=step.content or "",
                              rounds=rounds, usage=usage,
                              reason="empty/non-terminal response")
        return TurnResult(status="blocked", rounds=rounds, usage=usage,
                          reason=f"max_rounds={self.max_rounds} reached")
```
- [ ] Step: Run (expected PASS): same pytest command.
- [ ] Step: Commit: `A1 terminal guarantee + jc_agent_loop pure module (Fase 1 substrate)`.

**Acceptance:** empty+no-tool_calls never yields `status=="done"`; every `run_turn` returns a `TurnResult` envelope with `status`, `rounds`, `usage`.

---

### Task 2: [CLIENT jarvis-code] A6 partial-completion (finish_reason) — client plumb + non-terminal continuation

Consume `finish_reason` end-to-end: `api.py` surfaces it; `AgentLoop` treats `length`/`content_filter`/null-without-terminal as **non-terminal → continue** (ask model to keep going), not accept a truncated answer.

**Files:**
- Modify `src/api.py:398-400` (the `done` event in `agent_step_stream`) and `src/api.py` `agent_step` JSON return (around the non-stream branch)
- Modify `src/jc_agent_loop.py` (`run_turn` continuation branch)
- Test: `tests/test_jc_agent_loop.py`, `tests/test_api_helpers.py`

**Steps:**

- [ ] Step: Write failing test in `tests/test_jc_agent_loop.py`:
```python
def test_length_finish_reason_continues_then_completes():
    steps = [
        StepResult(content="partial ans", tool_calls=[], finish_reason="length"),
        StepResult(content=" ...rest done", tool_calls=[], finish_reason="stop"),
    ]
    loop = _loop(steps, max_rounds=5)
    res = loop.run_turn("q")
    assert res.status == "done"
    assert res.final_text == "partial ans ...rest done"


def test_null_finish_without_content_is_nonterminal():
    steps = [
        StepResult(content="", tool_calls=[], finish_reason=None),
        StepResult(content="recovered", tool_calls=[], finish_reason="stop"),
    ]
    loop = _loop(steps, max_rounds=5)
    res = loop.run_turn("q")
    assert res.status == "done" and res.final_text == "recovered"
```
- [ ] Step: Write failing test in `tests/test_api_helpers.py` (finish_reason surfaced by the stream parser):
```python
def test_agent_step_stream_surfaces_finish_reason(monkeypatch):
    import src.api as api
    class _Resp:
        status_code = 200
        def iter_lines(self):
            yield 'data: {"content":"hi","usage":{},"done":true,"finish_reason":"length"}'
        def __enter__(self): return self
        def __exit__(self, *a): return False
    class _Client:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def stream(self, *a, **k): return _Resp()
    monkeypatch.setattr(api.httpx, "Client", _Client)
    evs = list(api.agent_step_stream(api_url="x", auth_token=None, messages=[], tools=[]))
    done = [e for e in evs if e["type"] == "done"][0]
    assert done["finish_reason"] == "length"
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement `src/api.py` — extend the `done` yield at `:398-400` to carry `finish_reason` (default `None`), and add the same key to the non-stream `agent_step` JSON dict it returns:
```python
                    else:
                        yield {"type": "done", "content": payload.get("content", ""),
                               "usage": payload.get("usage", {}),
                               "done": payload.get("done", True),
                               "finish_reason": payload.get("finish_reason")}
```
- [ ] Step: Implement `src/jc_agent_loop.py` — replace the baseline "non-terminal, no tool_calls" branch so a **truncated but non-empty** step appends and continues; only a truly empty non-terminal step falls through to A2 (Task 3). Add an accumulator so continued text concatenates:
```python
            # non-terminal, no tool_calls
            fr = (step.finish_reason or "").lower()
            if (step.content or "").strip() and fr in _NONTERMINAL_FINISH:
                # A6: truncated answer — keep it, ask model to continue.
                self.messages.append({"role": "assistant", "content": step.content})
                self.messages.append({"role": "user",
                                      "content": "[CONTINUE] Dit forrige svar blev afkortet. "
                                                 "Fortsæt PRÆCIS hvor du slap, uden at gentage."})
                self._carry = getattr(self, "_carry", "") + step.content
                continue
            # empty (or null-finish with no content) → A2 recovery (Task 3)
            return self._recover_empty(rounds, usage)   # implemented in Task 3
```
  For this task, add a temporary `_recover_empty` that returns `TurnResult(status="empty", ...)`, and make the terminal-return prepend `self._carry`:
```python
            if self._is_terminal(step):
                text = getattr(self, "_carry", "") + step.content
                return TurnResult(status="done", final_text=text, rounds=rounds, usage=usage)
```
- [ ] Step: Run (expected PASS).
- [ ] Step: Commit: `A6 finish_reason: client plumb + non-terminal continuation`.

**Acceptance:** `length`/`content_filter`/null-without-terminal never end the turn as `done`; truncated text is preserved and continued; `finish_reason` flows from SSE into the loop (defaulting to `None` when the server omits it).

---

### Task 3: [CLIENT jarvis-code] A2 empty-detect + one bounded resend + force-final-synthesis + commit user-turn before step

On an empty step, do **exactly one** bounded (non-thinking) resend; at `max_rounds` force one prose-only synthesis round; and **commit the user turn to the session store BEFORE the first step** so an empty response never drops the user's message (current bug: `repl_ptk.py:862-864` only persists after a non-empty `final_text`).

**Files:**
- Modify `src/jc_agent_loop.py` (`run_turn`, `_recover_empty`, add `persist_user_fn` injection)
- Test: `tests/test_jc_agent_loop.py`

**Steps:**

- [ ] Step: Write failing tests:
```python
def test_empty_triggers_one_resend_then_completes():
    steps = [
        StepResult(content="", tool_calls=[], finish_reason="stop"),   # empty
        StepResult(content="on retry", tool_calls=[], finish_reason="stop"),
    ]
    loop = _loop(steps, max_rounds=6)
    res = loop.run_turn("q")
    assert res.status == "done" and res.final_text == "on retry"


def test_resend_is_bounded_to_one():
    # two empties in a row → do NOT resend forever; force synthesis / blocked.
    steps = [StepResult(content="", tool_calls=[], finish_reason="stop")]  # always empty
    loop = _loop(steps, max_rounds=6)
    res = loop.run_turn("q")
    assert res.status in ("blocked", "empty")
    assert res.rounds <= 4   # one resend + one forced synthesis, not 60


def test_user_turn_committed_before_step():
    committed = []
    loop = AgentLoop(step_fn=lambda m, t: StepResult(content="", finish_reason="stop"),
                     tool_fn=lambda tc: {"status": "ok"}, max_rounds=2)
    loop.persist_user_fn = lambda text: committed.append(text)
    loop.run_turn("remember me")
    assert committed == ["remember me"]   # persisted even though the turn produced no answer
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement in `src/jc_agent_loop.py`:
  - Add `self.persist_user_fn: Callable[[str], None] | None = None` in `__init__`.
  - At the top of `run_turn`, after appending the user message: `if self.persist_user_fn: self.persist_user_fn(user_input)`.
  - Track `self._resent = False`. Replace `_recover_empty`:
```python
    def _recover_empty(self, rounds, usage) -> "TurnResult":
        if not getattr(self, "_resent", False):
            self._resent = True
            self.messages.append({"role": "user",
                "content": "[RESEND] Dit svar var tomt. Giv nu et konkret svar "
                           "(ingen tænke-blok, kald kun værktøjer hvis nødvendigt)."})
            return self._continue_loop(rounds, usage)      # re-enter loop
        # already resent once → force ONE prose-only synthesis round.
        self.messages.append({"role": "user",
            "content": "[SYNTHESIS] Skriv dit endelige svar i prosa NU. Ingen værktøjer."})
        synth = self.step_fn(self.messages, [])            # empty tools = prose only
        if synth.usage: usage = synth.usage
        if (synth.content or "").strip():
            return TurnResult(status="done", final_text=synth.content,
                              rounds=rounds + 1, usage=usage)
        return TurnResult(status="blocked", rounds=rounds + 1, usage=usage,
                          reason="empty after resend+synthesis")
```
  - Implement `_continue_loop(start_rounds, usage)` by refactoring `run_turn`'s body into a helper that both the initial call and `_recover_empty` re-enter (simplest: extract the `for`-loop into `_drive(rounds, usage)` and call it from both `run_turn` and after appending the resend message). Guard `max_rounds` across re-entry so the resend counts toward the bound.
  - Also handle the `max_rounds` exhaustion path: before returning `blocked`, run one forced `[SYNTHESIS]` round (same directive) so a tool-heavy turn that hit the ceiling still yields prose — mirrors `repl_ptk.py:855-860`.
- [ ] Step: Run (expected PASS).
- [ ] Step: Commit: `A2 empty-detect + one bounded resend + forced synthesis + commit-user-before-step`.

**Acceptance:** one empty step → one resend; persistent empty → at most one resend + one synthesis then `blocked` (bounded, never a 60-round spin); user turn is persisted before the first step regardless of outcome.

---

### Task 4: [CLIENT jarvis-code] A3 round-atomic context fit (do NOT reuse tool-pair-blind `fit_messages_to_window`)

Reimplement context trimming client-side, **round-atomic**: group messages into rounds (`user` → `assistant`+tool_calls → its `tool` results), drop whole oldest rounds together, and **count `tool_calls` argument bytes** (the server's `core/services/model_context.py:65 fit_messages_to_window` only counts `m["content"]` and pops single messages → orphaned tool_use/result pairs → provider 400).

**Files:**
- Modify `src/jc_agent_loop.py` (add `fit_rounds_atomic` + call it before each `step_fn`)
- Test: `tests/test_jc_agent_loop.py`

**Steps:**

- [ ] Step: Write failing tests:
```python
from src.jc_agent_loop import fit_rounds_atomic


def _msgs():
    return [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "a", "function": {"name": "bash", "arguments": "{\"command\":\"x\"}"}}]},
        {"role": "tool", "tool_call_id": "a", "name": "bash", "content": "R1"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "final"},
    ]


def test_fit_never_orphans_a_tool_pair():
    fitted, dropped = fit_rounds_atomic(_msgs(), budget_chars=40)
    ids = [m["tool_call_id"] for m in fitted if m["role"] == "tool"]
    calls = [tc["id"] for m in fitted if m.get("tool_calls") for tc in m["tool_calls"]]
    for tid in ids:
        assert tid in calls          # every tool_result has its tool_use present
    assert fitted[0]["role"] == "system"   # system head always kept


def test_fit_counts_tool_call_arg_bytes():
    big = {"role": "assistant", "content": "",
           "tool_calls": [{"id": "z", "function": {"name": "write_file",
                            "arguments": "X" * 5000}}]}
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "q"},
            big, {"role": "tool", "tool_call_id": "z", "name": "write_file", "content": "ok"},
            {"role": "user", "content": "q2"}, {"role": "assistant", "content": "done"}]
    fitted, dropped = fit_rounds_atomic(msgs, budget_chars=1000)
    # the 5000-byte-arg round must be counted and dropped atomically (both msgs gone)
    assert dropped >= 1
    assert not any(m.get("tool_calls") for m in fitted)
    assert not any(m["role"] == "tool" for m in fitted)
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement `fit_rounds_atomic` in `src/jc_agent_loop.py`:
```python
def _msg_chars(m: dict) -> int:
    n = len(str(m.get("content") or ""))
    for tc in (m.get("tool_calls") or []):
        fn = tc.get("function") or {}
        n += len(str(fn.get("name") or "")) + len(str(fn.get("arguments") or ""))
    return n


def _group_rounds(body: list[dict]) -> list[list[dict]]:
    """A round = a user msg and/or an assistant(+tool_calls) with ALL its tool results.
    New round starts at each 'user' or at an 'assistant' that follows tool results."""
    rounds: list[list[dict]] = []
    cur: list[dict] = []
    for m in body:
        role = m.get("role")
        if role == "user" and cur:
            rounds.append(cur); cur = []
        cur.append(m)
    if cur:
        rounds.append(cur)
    return rounds


def fit_rounds_atomic(messages: list[dict], *, budget_chars: int, keep_last: int = 1
                      ) -> tuple[list[dict], int]:
    """Drop OLDEST whole rounds until total <= budget. Never split a tool_use/
    tool_result pair. System head always preserved. Returns (fitted, dropped_rounds)."""
    if not messages:
        return messages, 0
    head, body = ([messages[0]], messages[1:]) if messages[0].get("role") == "system" else ([], messages)
    rounds = _group_rounds(body)
    head_chars = sum(_msg_chars(m) for m in head)
    def total(rs): return head_chars + sum(_msg_chars(m) for r in rs for m in r)
    dropped = 0
    while len(rounds) > keep_last and total(rounds) > budget_chars:
        rounds.pop(0); dropped += 1
    fitted = head + [m for r in rounds for m in r]
    return fitted, dropped
```
  - In `AgentLoop.run_turn`/`_drive`, before each `step_fn`, call `msgs, _ = fit_rounds_atomic(self.messages, budget_chars=self.budget_chars)` and pass `msgs` to `step_fn` (add `budget_chars` to `__init__`, default e.g. `600_000`). Keep `self.messages` as the untrimmed source of truth; only the wire copy is trimmed.
- [ ] Step: Run (expected PASS).
- [ ] Step: Commit: `A3 round-atomic context fit (tool-pair-aware, counts tool_call arg bytes)`.

**Acceptance:** trimming never leaves a `tool` message whose `tool_call_id` lacks its `tool_use`; `tool_calls` argument bytes are counted; whole rounds drop atomically; system head is preserved.

---

### Task 5: [CLIENT jarvis-code] A4 uniform tool-result cap → spill-to-disk + visible marker + secret redaction

Cap **every** tool result (local + forwarded + MCP) before it enters history; spill the full payload to disk with a visible `[truncated N chars → <path>]` marker; **redact secrets** out of the spill file.

**Files:**
- Create `src/jc_tool_result.py`
- Test: `tests/test_jc_tool_result.py`

**Steps:**

- [ ] Step: Write failing test `tests/test_jc_tool_result.py`:
```python
import json
from pathlib import Path
from src.jc_tool_result import cap_and_spill, redact_secrets, TOOL_RESULT_CAP


def test_small_result_unchanged(tmp_path):
    r = {"status": "ok", "content": "short"}
    capped, spill = cap_and_spill(r, name="read_file", spill_dir=tmp_path)
    assert capped == r and spill is None


def test_large_result_capped_with_visible_marker(tmp_path):
    big = "A" * (TOOL_RESULT_CAP + 5000)
    capped, spill = cap_and_spill({"status": "ok", "content": big},
                                  name="bash", spill_dir=tmp_path)
    body = json.dumps(capped)
    assert len(body) < TOOL_RESULT_CAP + 2000
    assert "truncated" in body and str(spill) in body
    assert Path(spill).exists()


def test_spill_file_redacts_secrets(tmp_path):
    leaky = "export OPENAI_API_KEY=sk-abc123DEADBEEFabc123DEADBEEFabc123\n" + "x" * (TOOL_RESULT_CAP + 1)
    capped, spill = cap_and_spill({"status": "ok", "stdout": leaky},
                                  name="bash", spill_dir=tmp_path)
    disk = Path(spill).read_text()
    assert "sk-abc123DEADBEEF" not in disk and "[REDACTED]" in disk


def test_redact_secrets_patterns():
    s = "AWS_SECRET=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY password: hunter2"
    out = redact_secrets(s)
    assert "wJalrXUtnFEMI" not in out and "hunter2" not in out
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement `src/jc_tool_result.py`:
```python
"""A4: bound every tool result before it enters message history.

Uniform cap → spill full payload to disk with a VISIBLE marker → redact
secrets out of the spill file. Client-side (jarvis-code cannot import core.*)."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Optional

TOOL_RESULT_CAP = 24_000   # chars of the SERIALIZED result the model sees

_SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9]{16,})"
    r"|(?i:(?:api[_-]?key|secret|token|password|passwd|aws_secret[_a-z]*)\s*[:=]\s*)\S+"
    r"|(gh[pousr]_[A-Za-z0-9]{20,})"
    r"|(AKIA[0-9A-Z]{16})",
)


def redact_secrets(text: str) -> str:
    def _sub(m: re.Match) -> str:
        g0 = m.group(0)
        # keep the "key: " label, redact the value
        if ":" in g0 or "=" in g0:
            head = re.split(r"[:=]", g0, 1)[0]
            sep = ":" if ":" in g0 else "="
            return f"{head}{sep} [REDACTED]"
        return "[REDACTED]"
    return _SECRET_RE.sub(_sub, text or "")


def _result_text(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False)


def cap_and_spill(result: Any, *, name: str, spill_dir: Path,
                  cap: int = TOOL_RESULT_CAP) -> tuple[dict, Optional[str]]:
    if not isinstance(result, dict):
        result = {"status": "ok", "result": result}
    body = _result_text(result)
    if len(body) <= cap:
        return result, None
    spill_dir = Path(spill_dir); spill_dir.mkdir(parents=True, exist_ok=True)
    spill = spill_dir / f"{name}-{uuid.uuid4().hex[:8]}.txt"
    spill.write_text(redact_secrets(body), encoding="utf-8")
    # Truncate the largest string field (content/stdout/output/result) for the model.
    capped = dict(result)
    field = max(("content", "stdout", "output", "stderr", "result"),
                key=lambda k: len(str(capped.get(k) or "")))
    kept = str(capped.get(field) or "")[:cap - 400]
    capped[field] = (kept + f"\n… [truncated {len(body) - len(kept)} chars → {spill}]")
    capped["_truncated"] = True
    capped["_spill"] = str(spill)
    return capped, str(spill)
```
- [ ] Step: Run (expected PASS).
- [ ] Step: Commit: `A4 uniform tool-result cap → spill-to-disk + visible marker + secret redaction`.

**Acceptance:** results over cap are truncated with a visible marker referencing the spill path; the on-disk spill has secrets redacted; small results pass through untouched.

*(Wiring `cap_and_spill` into the live tool path happens in Task 7, where the round transaction appends the tool_result; spill_dir defaults to `~/.jarvis-code/spill/` in the repl_ptk adapter, Task 11.)*

---

### Task 6: [CLIENT jarvis-code] A5 degeneration / runaway-repetition guard (client mirror)

Mirror the server's digit-normalized degeneration detector (`core/services/stream_degeneration.py:29 check_degeneration`) client-side and cut a runaway repetition loop at the source instead of accepting 147k chars of garbage as an answer.

**Files:**
- Modify `src/jc_agent_loop.py` (add `check_degeneration` + call in loop)
- Test: `tests/test_jc_agent_loop.py`

**Steps:**

- [ ] Step: Write failing tests:
```python
from src.jc_agent_loop import check_degeneration


def test_degeneration_flags_runaway():
    text = " ".join(f"probe_ollama{i}.py" for i in range(400))
    bad, reason = check_degeneration(text)
    assert bad and "repetition" in reason


def test_degeneration_ignores_varied_text():
    text = " ".join(f"word{i} distinct phrase {i*7} unique" for i in range(400))
    bad, _ = check_degeneration(text)
    assert not bad


def test_loop_blocks_on_degenerate_step():
    runaway = " ".join(f"probe_ollama{i}.py" for i in range(400))
    loop = _loop([StepResult(content=runaway, tool_calls=[], finish_reason="stop")])
    res = loop.run_turn("q")
    assert res.status == "blocked" and "repetition" in res.reason
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement in `src/jc_agent_loop.py` (self-contained copy of the algorithm — our own code, thresholds from the reference: `_MIN_CHARS=1500`, `_MIN_TOKENS=150`, `_REP_COUNT=80`, `_MAX_DIVERSITY=0.18`):
```python
import re as _re
from collections import Counter as _Counter
_DIGIT = _re.compile(r"\d+")

def check_degeneration(text: str) -> tuple[bool, str]:
    try:
        if not text or len(text) < 1500:
            return False, ""
        toks = text.split()
        if len(toks) < 150:
            return False, ""
        norm = [_DIGIT.sub("#", t) for t in toks]
        counts = _Counter(norm)
        top_tok, top_n = counts.most_common(1)[0]
        diversity = len(counts) / len(norm)
        if top_n >= 80 and diversity < 0.18:
            return True, (f"runaway-repetition: '{top_tok[:24]}'x{top_n} "
                          f"(diversity {diversity:.0%})")
        return False, ""
    except Exception:
        return False, ""
```
  - In `_drive`, after each `step_fn` and before treating content as terminal, run `bad, why = check_degeneration(step.content)`; if `bad`, return `TurnResult(status="blocked", reason=why, ...)` immediately (do not persist the garbage into history).
- [ ] Step: Run (expected PASS).
- [ ] Step: Commit: `A5 client-side degeneration/repetition guard`.

**Acceptance:** a digit-counting runaway (≥80 repeats, <18% diversity, ≥1500 chars) blocks the turn with a typed reason; varied real output never trips it.

---

### Task 7: [CLIENT jarvis-code] A7 round-atomicity — one tool_result per tool_call even on exception/cancel; invalid args → typed error

Make a work round a transaction: **every** `tool_call` gets **exactly one** `tool_result`, even if `tool_fn` raises or the turn is cancelled, and invalid/partial tool-args produce a typed `{status:"error"}` — never a silent `{}` coercion or an orphaned tool_use.

**Files:**
- Modify `src/jc_agent_loop.py` (the tool-calls branch → `_run_round`)
- Test: `tests/test_jc_agent_loop.py`

**Steps:**

- [ ] Step: Write failing tests:
```python
import json


def test_every_tool_call_gets_a_result_even_on_exception():
    tc = [{"id": "1", "function": {"name": "bash", "arguments": "{}"}},
          {"id": "2", "function": {"name": "read_file", "arguments": "{}"}}]
    steps = [StepResult(content="", tool_calls=tc, finish_reason="tool_calls"),
             StepResult(content="ok done", tool_calls=[], finish_reason="stop")]
    def tool_fn(call):
        if call["id"] == "1":
            raise RuntimeError("boom")
        return {"status": "ok"}
    loop = AgentLoop(step_fn=lambda m, t: steps[min(len(m)//3, 1)], tool_fn=tool_fn, max_rounds=5)
    loop.run_turn("q")
    results = [m for m in loop.messages if m["role"] == "tool"]
    ids = {m["tool_call_id"] for m in results}
    assert ids == {"1", "2"}                                  # both got a result
    err = json.loads([m for m in results if m["tool_call_id"] == "1"][0]["content"])
    assert err["status"] == "error" and "boom" in err["error"]


def test_invalid_tool_args_typed_error_not_empty_dict():
    from src.jc_agent_loop import parse_tool_args
    args, err = parse_tool_args('{"command": ')   # broken JSON
    assert args is None and err is not None        # NOT {} coercion


def test_cancel_still_closes_open_tool_calls():
    tc = [{"id": "a", "function": {"name": "bash", "arguments": "{}"}},
          {"id": "b", "function": {"name": "bash", "arguments": "{}"}}]
    steps = [StepResult(content="", tool_calls=tc, finish_reason="tool_calls")]
    loop = AgentLoop(step_fn=lambda m, t: steps[0],
                     tool_fn=lambda c: {"status": "ok"}, max_rounds=2)
    loop.is_cancelled = lambda: True     # cancel requested before running tools
    loop.run_turn("q")
    ids = {m["tool_call_id"] for m in loop.messages if m["role"] == "tool"}
    assert ids == {"a", "b"}             # cancelled calls still get a typed result
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement in `src/jc_agent_loop.py`:
```python
def parse_tool_args(raw: Any) -> tuple[Optional[dict], Optional[str]]:
    """Return (args, None) or (None, error). NEVER coerce a broken payload to {}."""
    if isinstance(raw, dict):
        return raw, None
    if raw is None or raw == "":
        return {}, None
    try:
        val = json.loads(raw)
        if not isinstance(val, dict):
            return None, f"tool args not an object: {type(val).__name__}"
        return val, None
    except Exception as e:
        return None, f"invalid tool args JSON: {e}"
```
  - Add `self.is_cancelled: Callable[[], bool] = lambda: False` in `__init__`.
  - Replace the tool-calls branch with `_run_round(step)`:
```python
    def _run_round(self, step: "StepResult") -> None:
        self.messages.append({"role": "assistant", "content": step.content,
                              "tool_calls": step.tool_calls})
        for tc in step.tool_calls:
            tid = tc.get("id", "")
            name = (tc.get("function") or {}).get("name", "")
            if self.is_cancelled():
                result = {"status": "error", "error": "cancelled before execution"}
            else:
                args, arg_err = parse_tool_args((tc.get("function") or {}).get("arguments"))
                if arg_err:
                    result = {"status": "error", "error": arg_err}
                else:
                    try:
                        result = self.tool_fn({**tc, "_parsed_args": args})
                        if not isinstance(result, dict):
                            result = {"status": "ok", "result": result}
                    except Exception as e:
                        result = {"status": "error", "error": f"{type(e).__name__}: {e}"}
            self.messages.append({"role": "tool", "tool_call_id": tid, "name": name,
                                  "content": json.dumps(result, ensure_ascii=False)})
```
  - Call `self._run_round(step)` in the tool_calls branch; keep looping.
- [ ] Step: Run (expected PASS).
- [ ] Step: Commit: `A7 round-atomicity: guaranteed one typed tool_result per tool_call`.

**Acceptance:** raised exceptions, cancellation, and invalid args all yield a typed `{status:"error"}` tool_result for the exact `tool_call_id`; no orphaned tool_use; no `{}` coercion.

---

### Task 8: [CLIENT jarvis-code] A8 forwarded-tool errors → typed tool_result, never a raised exception

Wrap the forwarding path so a container/operator tool 500 becomes a typed `{status:"error"}` tool_result instead of `raise_for_status` killing the whole turn (current: `src/tools.py:499-502` calls `api.execute_native_tool`, which does `resp.raise_for_status()` at `src/api.py:465`).

**Files:**
- Modify `src/tools.py:487-502` (`route_tool_call`)
- Test: `tests/test_tools.py`

**Steps:**

- [ ] Step: Write failing test in `tests/test_tools.py`:
```python
def test_forwarded_tool_500_returns_typed_error_not_raise(monkeypatch):
    import httpx
    from src import tools
    def _boom(**kw):
        raise httpx.HTTPStatusError("500", request=None,
                                    response=httpx.Response(500, text="upstream fail"))
    monkeypatch.setattr(tools.api, "execute_native_tool", _boom)
    r = tools.route_tool_call("runtime_bash", {"command": "x"}, api_url="u",
                              auth_token=None, session_id="s")
    assert isinstance(r, dict) and r["status"] == "error"
    assert "500" in r["error"] or "upstream" in r["error"]


def test_forwarded_tool_ok_passthrough(monkeypatch):
    from src import tools
    monkeypatch.setattr(tools.api, "execute_native_tool",
                        lambda **kw: {"result": {"status": "ok", "out": 1}})
    r = tools.route_tool_call("some_companion", {}, api_url="u",
                              auth_token=None, session_id="s")
    assert r == {"status": "ok", "out": 1}
```
- [ ] Step: Run (expected FAIL — current code raises).
- [ ] Step: Implement in `src/tools.py::route_tool_call` — wrap the forward in try/except:
```python
    if tool_name in TOOL_EXECUTORS:
        return TOOL_EXECUTORS[tool_name](**args)
    try:
        resp = api.execute_native_tool(api_url=api_url, auth_token=auth_token,
                                       name=tool_name, arguments=args,
                                       session_id=session_id, turn_id=turn_id)
    except Exception as e:  # forwarded-tool failure must NOT kill the turn (A8)
        return {"status": "error",
                "error": f"forwarded tool '{tool_name}' failed: {type(e).__name__}: {e}"}
    result = resp.get("result")
    if isinstance(result, dict):
        return result
    return {"status": "ok", "result": result}
```
- [ ] Step: Run (expected PASS). Also run full `tests/test_tools.py` to confirm no regressions: `/opt/conda/envs/ai/bin/python -m pytest tests/test_tools.py -o addopts="" -q`.
- [ ] Step: Commit: `A8 forwarded-tool errors → typed tool_result, never raise`.

**Acceptance:** a forwarded-tool HTTP error returns `{status:"error", error:...}` for the caller to append as a tool_result; the turn survives.

---

### Task 9: [CLIENT jarvis-code] Client eyes — read_file base64 / media-type branch

Give Jarvis eyes: `read_file` on an image (or binary) returns a base64 payload + `media_type` so a downstream user/tool content block can carry the image to the model (load-bearing for "SE UI før færdig", [[feedback_verify_visual_before_done]]).

**Files:**
- Create `src/jc_multimodal.py` (`read_file_block`, `MEDIA_TYPES`)
- Modify `src/tools.py:304-315` (`local_read_file` routes image/binary through it)
- Test: `tests/test_jc_multimodal.py`, `tests/test_tools.py`

**Steps:**

- [ ] Step: Write failing test `tests/test_jc_multimodal.py`:
```python
import base64
from pathlib import Path
from src.jc_multimodal import read_file_block


def test_text_file_returns_text(tmp_path):
    f = tmp_path / "a.txt"; f.write_text("hello")
    r = read_file_block(str(f))
    assert r["status"] == "ok" and r["kind"] == "text" and r["content"] == "hello"


def test_png_returns_base64_and_media_type(tmp_path):
    png = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 32
    f = tmp_path / "shot.png"; f.write_bytes(png)
    r = read_file_block(str(f))
    assert r["status"] == "ok" and r["kind"] == "image"
    assert r["media_type"] == "image/png"
    assert base64.b64decode(r["data"]) == png


def test_missing_file_typed_error(tmp_path):
    r = read_file_block(str(tmp_path / "nope.png"))
    assert r["status"] == "error"
```
- [ ] Step: Write failing test in `tests/test_tools.py`:
```python
def test_local_read_file_image_returns_media_type(tmp_path):
    from src import tools
    png = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 16
    f = tmp_path / "u.png"; f.write_bytes(png)
    r = tools.local_read_file(str(f))
    assert r["status"] == "ok" and r.get("media_type") == "image/png" and "data" in r
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement `src/jc_multimodal.py`:
```python
"""Client eyes: turn files/bytes into typed content blocks (text or image)."""
from __future__ import annotations
import base64
from pathlib import Path
from typing import Any

MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".gif": "image/gif", ".webp": "image/webp"}


def read_file_block(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {"status": "error", "error": f"File not found: {path}"}
    ext = p.suffix.lower()
    if ext in MEDIA_TYPES:
        try:
            raw = p.read_bytes()
            return {"status": "ok", "kind": "image", "media_type": MEDIA_TYPES[ext],
                    "data": base64.b64encode(raw).decode("ascii"), "size": len(raw)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        return {"status": "ok", "kind": "text", "content": content, "size": len(content)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def build_image_block(data_b64: str, media_type: str) -> dict[str, Any]:
    """Anthropic-style image content block."""
    return {"type": "image", "source": {"type": "base64",
            "media_type": media_type, "data": data_b64}}
```
- [ ] Step: Implement `src/tools.py::local_read_file` — delegate to `read_file_block` and, when `kind=="image"`, surface `media_type`/`data` on the tool result (so the model sees an image marker; the actual image block is injected by the repl adapter, Task 10/11):
```python
def local_read_file(path: str) -> dict[str, Any]:
    from . import jc_multimodal
    r = jc_multimodal.read_file_block(path)
    if r.get("status") == "ok" and r.get("kind") == "image":
        return {"status": "ok", "media_type": r["media_type"], "data": r["data"],
                "size": r["size"], "content": f"[image {r['media_type']} {r['size']} bytes]"}
    return r
```
- [ ] Step: Run (expected PASS).
- [ ] Step: Commit: `client eyes: read_file base64/media-type branch (image input)`.

**Acceptance:** reading a `.png/.jpg/...` returns base64 + `media_type`; text files unchanged; missing files typed-error.

---

### Task 10: [CLIENT jarvis-code] Client eyes — composer image paste

Let a user paste an image into the composer; the paste becomes a typed image content block queued onto the next user turn. Pure conversion lives in `jc_multimodal`; the prompt_toolkit key binding is a thin wire.

**Files:**
- Modify `src/jc_multimodal.py` (add `clipboard_image_block`)
- Modify `src/repl_ptk.py` (add a paste-image key binding in `_build_app` near `:1586-1667`; add `self._pending_images: list[dict]` in `__init__` near `:308`)
- Test: `tests/test_jc_multimodal.py`

**Steps:**

- [ ] Step: Write failing test in `tests/test_jc_multimodal.py`:
```python
from src.jc_multimodal import clipboard_image_block, build_image_block


def test_build_image_block_shape():
    b = build_image_block("QUJD", "image/png")
    assert b == {"type": "image", "source": {"type": "base64",
                 "media_type": "image/png", "data": "QUJD"}}


def test_clipboard_image_block_from_png_bytes():
    png = bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 8
    blk = clipboard_image_block(png)
    assert blk["type"] == "image"
    assert blk["source"]["media_type"] == "image/png"


def test_clipboard_non_image_returns_none():
    assert clipboard_image_block(b"just text not an image") is None
```
- [ ] Step: Run (expected FAIL).
- [ ] Step: Implement `clipboard_image_block` in `src/jc_multimodal.py` (magic-byte sniff → base64 block; unknown → None):
```python
_MAGIC = [(b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"),
          (b"GIF87a", "image/gif"), (b"GIF89a", "image/gif"),
          (b"RIFF", "image/webp")]

def clipboard_image_block(data: bytes) -> dict[str, Any] | None:
    for sig, mt in _MAGIC:
        if data.startswith(sig):
            return build_image_block(base64.b64encode(data).decode("ascii"), mt)
    return None
```
- [ ] Step: Wire the UI in `src/repl_ptk.py`: in `__init__` add `self._pending_images: list[dict] = []`; in `_build_app`'s key bindings add a binding (e.g. `c-v` image path or a `/paste-image <path>` fallback for terminals without image clipboard) that reads bytes, calls `jc_multimodal.clipboard_image_block`, and on success appends to `self._pending_images` and emits `render.sb_sys("▸ billede vedhæftet næste tur")`. In `_on_submit`, if `self._pending_images`, build the next user message `content` as an array `[{"type":"text","text":text}, *self._pending_images]` and clear the list. (Server array-acceptance is Fase 0; if the server ignores arrays, text still flows — no client crash.)
- [ ] Step: Run (expected PASS): `pytest tests/test_jc_multimodal.py`. Then smoke-run the app to confirm the binding loads without exception: `/opt/conda/envs/ai/bin/python -c "import src.repl_ptk"`.
- [ ] Step: Commit: `client eyes: composer image paste → typed image block on next turn`.

**Acceptance:** paste of PNG/JPG/GIF/WEBP bytes yields a valid image content block queued for the next turn; non-image paste is a no-op; app imports cleanly.

---

### Task 11: [CLIENT jarvis-code] Wire `AgentLoop` into `repl_ptk._turn_worker` + §9 fault-injection acceptance harness

Make the live client lane consume the new substrate, and prove the numeric §9 acceptance bar with a mock-provider fault-injection test.

**Files:**
- Modify `src/repl_ptk.py:811-870` (`_turn_worker` becomes an adapter) and `:979-1036` (`_run_one_step` becomes the injected `step_fn`)
- Test: `tests/test_jc_agent_loop.py` (fault-injection harness)
- Test: `tests/test_repl_ptk_driver.py` (adapter smoke)

**Steps:**

- [ ] Step: Write failing fault-injection harness in `tests/test_jc_agent_loop.py` (the §9 numeric bar: over N=100 injected fault rounds, 0 silent-empty, 0 hangs, 0 orphan pairs; every turn emits a terminal envelope):
```python
import json, random
from src.jc_agent_loop import AgentLoop, StepResult


FAULTS = ["empty", "cutoff", "length", "toolcall_no_result", "degenerate",
          "bad_args", "forwarded_500"]

def _scripted(fault):
    if fault == "empty":
        return [StepResult(content="", finish_reason="stop"),
                StepResult(content="recovered", finish_reason="stop")]
    if fault == "length":
        return [StepResult(content="part", finish_reason="length"),
                StepResult(content=" done", finish_reason="stop")]
    if fault == "degenerate":
        return [StepResult(content=" ".join(f"x{i}.py" for i in range(400)),
                           finish_reason="stop")]
    if fault in ("toolcall_no_result", "bad_args", "forwarded_500"):
        tc = [{"id": "1", "function": {"name": "bash",
               "arguments": "{" if fault == "bad_args" else "{}"}}]
        return [StepResult(content="", tool_calls=tc, finish_reason="tool_calls"),
                StepResult(content="after tool", finish_reason="stop")]
    return [StepResult(content="ok", finish_reason="stop")]


def test_fault_injection_numeric_bar():
    silent_empty = hangs = orphans = 0
    for n in range(100):
        fault = FAULTS[n % len(FAULTS)]
        seq = _scripted(fault)
        i = {"n": 0}
        def step_fn(m, t, seq=seq, i=i):
            r = seq[min(i["n"], len(seq) - 1)]; i["n"] += 1; return r
        def tool_fn(tc, fault=fault):
            if fault == "forwarded_500":
                return {"status": "error", "error": "HTTP 500"}
            return {"status": "ok"}
        loop = AgentLoop(step_fn=step_fn, tool_fn=tool_fn, max_rounds=8)
        res = loop.run_turn("q")
        assert res.status is not None                       # 0 hangs: always terminal envelope
        if res.status == "done" and not res.final_text.strip():
            silent_empty += 1
        # 0 orphan pairs: every tool_result has its tool_use
        calls = {tc["id"] for m in loop.messages if m.get("tool_calls")
                 for tc in m["tool_calls"]}
        for m in loop.messages:
            if m["role"] == "tool" and m["tool_call_id"] not in calls:
                orphans += 1
    assert silent_empty == 0 and orphans == 0
```
- [ ] Step: Run (expected PASS already if A1–A7 landed — this is the regression gate).
- [ ] Step: Refactor `src/repl_ptk.py::_turn_worker` into an adapter: build `step_fn` from the existing streaming `_run_one_step` (returning a `StepResult` with `finish_reason` from the `done` event), build `tool_fn` from `_run_one_tool`/`route_tool_call` wrapped with `jc_tool_result.cap_and_spill` (spill_dir = `Path.home()/".jarvis-code"/"spill"`), pass `emit=` a callback that drives the existing `_round_*`/`_stream_delta` renderers, set `persist_user_fn=self._persist_user_message`, `is_cancelled=lambda: self.stop_requested`, `max_rounds=self.max_rounds`, and `budget_chars` from config. Call `AgentLoop(...).run_turn(model_input, prior_messages=convo)` and render `TurnResult` (done → save + append; blocked/error/empty → emit typed notice). Keep `_turn_worker_v2` untouched.
- [ ] Step: Write adapter smoke test in `tests/test_repl_ptk_driver.py` asserting `_turn_worker` builds an `AgentLoop`, calls `persist_user_fn` before the first step, and renders a `done` TurnResult (drive with a monkeypatched `_run_one_step` returning a terminal StepResult — no network).
- [ ] Step: Run the FULL client suite (no regressions): `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/ -o addopts="" -q`.
- [ ] Step: Commit: `wire AgentLoop into repl_ptk._turn_worker + §9 fault-injection acceptance harness`.

**Acceptance:** the live client lane routes through `AgentLoop`; the fault-injection harness passes the numeric bar (0 silent-empty, 0 hangs, 0 orphan pairs over N=100); full suite green.

---

## Acceptance (Fase 1)

- **A1–A8 all landed and tested** in `tests/test_jc_agent_loop.py`, `tests/test_jc_tool_result.py`, `tests/test_tools.py`: no empty/truncated turn is ever `status=="done"`; `finish_reason` drives continuation; empty → one bounded resend + forced synthesis; context fit is round-atomic (no orphaned tool pairs, counts tool_call arg bytes); every tool result is capped/spilled/redacted; degeneration is cut client-side; every tool_call gets exactly one typed tool_result even on exception/cancel/bad-args; forwarded-tool errors are typed, never raised.
- **Client eyes:** `read_file` returns base64+media_type for images; composer paste queues a typed image block (reaches the model once Fase 0's array-content acceptance is live; degrades to text without it — no crash).
- **§9 numeric bar met** via the mock-provider fault-injection harness: 0 silent-empty, 0 hangs, 0 orphan-pair over N=100 injected rounds; every turn emits a terminal `TurnResult` envelope.
- **Full client suite green:** `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/ -o addopts="" -q`.
- **No `core.*` imports** anywhere in `src/` (verify: `grep -rn "import core\|from core" /home/bs/jarvis-code/src` returns nothing) — every contract is reimplemented client-side.
- **Server untouched** in this phase; Fase 0 (finish_reason plumbing, content-array acceptance, user_id scoping) is a separate [SERVER] prerequisite. The client tolerates its absence (finish_reason defaults to `None`; image blocks are inert until the server accepts arrays).