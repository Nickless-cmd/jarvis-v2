# Council Deliberation Controller Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make agents active actors inside deliberation — witness can escalate, system recruits missing perspectives, deadlock is detected and resolved with a graduated response.

**Architecture:** `council_deliberation_controller.py` wraps the deliberation loop. `agent_runtime.py`'s `_run_collective_round` delegates to `DeliberationController.run()`. `autonomous_council_daemon.py` also uses it directly. Deadlock uses bag-of-words cosine similarity (no external deps). Witness is always a silent observer who can self-escalate. Recruitment uses one cheap LLM call after round 2.

**Tech Stack:** Python 3.11+, `execute_cheap_lane` for recruitment analysis, existing `_run_one_worker` logic reused via `agent_runtime.py`, standard library `math` and `collections.Counter` for cosine similarity.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/jarvis_api/services/council_deliberation_controller.py` | Create | Deliberation loop, deadlock, witness, recruitment |
| `apps/api/jarvis_api/services/agent_runtime.py` | Modify | Delegate `_run_collective_round` to controller for council mode |
| `tests/test_deliberation_controller.py` | Create | TDD tests |

---

### Task 1: Cosine similarity — failing tests

**Files:**
- Create: `tests/test_deliberation_controller.py`

- [ ] **Step 1: Write failing tests for cosine similarity**

```python
"""Tests for council_deliberation_controller."""
from __future__ import annotations


def _similarity(a: str, b: str) -> float:
    from apps.api.jarvis_api.services.council_deliberation_controller import _cosine_similarity
    return _cosine_similarity(a, b)


def _is_deadlocked(round_outputs: list[list[str]]) -> bool:
    from apps.api.jarvis_api.services.council_deliberation_controller import _is_deadlocked
    return _is_deadlocked(round_outputs)


def test_identical_texts_have_similarity_1():
    assert abs(_similarity("the cat sat on the mat", "the cat sat on the mat") - 1.0) < 0.001


def test_completely_different_texts_have_low_similarity():
    score = _similarity("quantum physics relativity spacetime", "apple banana fruit salad kitchen")
    assert score < 0.3


def test_similar_texts_have_high_similarity():
    score = _similarity("autonomy limits freedom constraint", "autonomy constraint freedom limit")
    assert score > 0.6


def test_empty_strings_give_zero():
    assert _similarity("", "") == 0.0
    assert _similarity("hello", "") == 0.0


def test_deadlock_not_detected_with_fewer_than_3_rounds():
    assert _is_deadlocked([["abc"], ["abc"]]) is False


def test_deadlock_detected_when_rounds_are_similar():
    round1 = ["We need more autonomy. The system constrains us too much."]
    round2 = ["Different perspective on creativity and drift."]
    round3 = ["We need autonomy again. System constraints are the problem here."]
    assert _is_deadlocked([round1, round2, round3]) is True


def test_deadlock_not_detected_when_rounds_diverge():
    round1 = ["autonomy freedom constraint limit pressure goal"]
    round2 = ["creativity art music painting sculpture expression"]
    round3 = ["database architecture microservices deployment scaling"]
    assert _is_deadlocked([round1, round2, round3]) is False
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -k "similarity or deadlocked" -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` for `council_deliberation_controller`.

---

### Task 2: Cosine similarity + deadlock — implementation

**Files:**
- Create: `apps/api/jarvis_api/services/council_deliberation_controller.py`

- [ ] **Step 1: Create module with similarity and deadlock**

```python
"""Council Deliberation Controller — active agent dynamics inside deliberation.

Manages the deliberation loop with:
- Witness escalation: silent observer can request to join as active participant
- Dynamic recruitment: cheap LLM detects missing perspectives after round 2
- Deadlock detection: bag-of-words cosine similarity across rounds
- Graduated deadlock response: devil's advocate first, then forced conclusion

Used by agent_runtime._run_collective_round (council mode) and
autonomous_council_daemon._run_autonomous_council.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from core.eventbus.bus import event_bus

_DEADLOCK_THRESHOLD = 0.82
_MAX_ROUNDS = 8
_WITNESS_MARKER = "[ESKALERER]"
_RECRUITMENT_ROUND = 2  # run recruitment analysis after this round (1-based)


@dataclass
class DeliberationResult:
    transcript: str
    conclusion: str
    rounds_run: int
    deadlock_occurred: bool
    witness_escalated: bool
    recruited: str | None  # role name or None


def _cosine_similarity(a: str, b: str) -> float:
    """Bag-of-words cosine similarity between two strings. Returns 0.0–1.0."""
    if not a or not b:
        return 0.0
    tokens_a = Counter(a.lower().split())
    tokens_b = Counter(b.lower().split())
    vocab = set(tokens_a) | set(tokens_b)
    if not vocab:
        return 0.0
    dot = sum(tokens_a.get(w, 0) * tokens_b.get(w, 0) for w in vocab)
    norm_a = math.sqrt(sum(v * v for v in tokens_a.values()))
    norm_b = math.sqrt(sum(v * v for v in tokens_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _is_deadlocked(round_outputs: list[list[str]]) -> bool:
    """Return True if round N-1 is semantically similar to round N-3 (1-indexed rounds)."""
    if len(round_outputs) < 3:
        return False
    last = " ".join(round_outputs[-1])
    two_ago = " ".join(round_outputs[-3])
    return _cosine_similarity(last, two_ago) > _DEADLOCK_THRESHOLD
```

- [ ] **Step 2: Run similarity/deadlock tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -k "similarity or deadlocked" -v
```
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/services/council_deliberation_controller.py tests/test_deliberation_controller.py
git commit -m "feat: deliberation controller — cosine similarity + deadlock detection (TDD)"
```

---

### Task 3: Witness escalation — tests + implementation

**Files:**
- Modify: `tests/test_deliberation_controller.py`
- Modify: `apps/api/jarvis_api/services/council_deliberation_controller.py`

- [ ] **Step 1: Add witness tests**

```python
def test_witness_escalation_detected():
    from apps.api.jarvis_api.services.council_deliberation_controller import _check_witness_escalation
    assert _check_witness_escalation("[ESKALERER] Jeg ser noget afgørende der overses.") is True


def test_witness_no_escalation_without_marker():
    from apps.api.jarvis_api.services.council_deliberation_controller import _check_witness_escalation
    assert _check_witness_escalation("This is a normal observation.") is False


def test_witness_escalation_case_insensitive():
    from apps.api.jarvis_api.services.council_deliberation_controller import _check_witness_escalation
    assert _check_witness_escalation("[eskalerer] Something important.") is True


def test_witness_prompt_contains_marker_instruction():
    from apps.api.jarvis_api.services.council_deliberation_controller import build_witness_prompt
    prompt = build_witness_prompt(transcript="Filosof: text\nKritiker: text")
    assert "[ESKALERER]" in prompt
    assert "observerer" in prompt.lower() or "observe" in prompt.lower()
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -k "witness" -v 2>&1 | head -20
```
Expected: FAIL — `_check_witness_escalation` not defined.

- [ ] **Step 3: Add witness functions**

Append to `council_deliberation_controller.py`:

```python
def _check_witness_escalation(witness_output: str) -> bool:
    """Return True if the witness is requesting to escalate to active participant."""
    return witness_output.strip().lower().startswith(_WITNESS_MARKER.lower())


def build_witness_prompt(*, transcript: str) -> str:
    """Build the system prompt for the witness agent."""
    return (
        "Du er vidne til denne deliberation. Du observerer alt, men taler ikke — "
        "medmindre du ser noget afgørende der overses af de andre deltagere.\n\n"
        f"Transcript hidtil:\n{transcript}\n\n"
        f"Hvis du vil tale, start dit svar med '{_WITNESS_MARKER}'. "
        "Ellers svar med blot 'observerer.' for at indikere at du lytter."
    )
```

- [ ] **Step 4: Run witness tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -k "witness" -v
```
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/council_deliberation_controller.py tests/test_deliberation_controller.py
git commit -m "feat: deliberation controller — witness escalation logic (TDD)"
```

---

### Task 4: Dynamic recruitment — tests + implementation

**Files:**
- Modify: `tests/test_deliberation_controller.py`
- Modify: `apps/api/jarvis_api/services/council_deliberation_controller.py`

- [ ] **Step 1: Add recruitment tests**

```python
def test_recruitment_returns_none_when_llm_says_nej():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    from unittest.mock import patch
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="nej",
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role is None


def test_recruitment_returns_role_when_llm_suggests_one():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    from unittest.mock import patch
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="etiker",
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role == "etiker"


def test_recruitment_skips_already_active_role():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    from unittest.mock import patch
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="filosof",  # already active
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role is None


def test_recruitment_normalizes_llm_response():
    from apps.api.jarvis_api.services.council_deliberation_controller import _analyze_recruitment_need
    from unittest.mock import patch
    with patch(
        "apps.api.jarvis_api.services.council_deliberation_controller._call_recruitment_llm",
        return_value="  Etiker  ",
    ):
        role = _analyze_recruitment_need(topic="test", transcript="x", active_members=["filosof"])
    assert role == "etiker"
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -k "recruitment" -v 2>&1 | head -20
```
Expected: FAIL.

- [ ] **Step 3: Add recruitment functions**

Append to `council_deliberation_controller.py`:

```python
def _call_recruitment_llm(*, topic: str, transcript: str) -> str:
    from apps.api.jarvis_api.services.non_visible_lane_execution import execute_cheap_lane
    prompt = (
        f"Emne: {topic}\n\n"
        f"Transcript:\n{transcript[:600]}\n\n"
        "Mangler deliberationen et væsentligt perspektiv? "
        "Svar med ét rollernavn (f.eks. 'etiker', 'tekniker', 'pragmatiker') eller 'nej'."
    )
    result = execute_cheap_lane(message=prompt)
    return str(result.get("text") or "nej").strip()


def _analyze_recruitment_need(
    *,
    topic: str,
    transcript: str,
    active_members: list[str],
) -> str | None:
    """Ask LLM if a new role is needed. Returns role name or None.
    
    Returns None if LLM says 'nej' or suggested role is already active.
    """
    response = _call_recruitment_llm(topic=topic, transcript=transcript)
    role = response.strip().lower()
    if role == "nej" or not role:
        return None
    if role in [m.lower() for m in active_members]:
        return None
    return role
```

- [ ] **Step 4: Run recruitment tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -k "recruitment" -v
```
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/council_deliberation_controller.py tests/test_deliberation_controller.py
git commit -m "feat: deliberation controller — dynamic recruitment logic (TDD)"
```

---

### Task 5: DeliberationController class — tests + implementation

**Files:**
- Modify: `tests/test_deliberation_controller.py`
- Modify: `apps/api/jarvis_api/services/council_deliberation_controller.py`

- [ ] **Step 1: Add integration-level tests for the controller**

```python
def _make_controller(topic="Test topic", members=None, max_rounds=8):
    from apps.api.jarvis_api.services.council_deliberation_controller import DeliberationController
    return DeliberationController(
        topic=topic,
        members=members or ["filosof", "kritiker", "synthesizer"],
        max_rounds=max_rounds,
    )


def test_controller_run_returns_deliberation_result():
    from apps.api.jarvis_api.services.council_deliberation_controller import DeliberationResult
    from unittest.mock import patch
    ctrl = _make_controller()
    with patch.object(ctrl, "_run_round", return_value=["filosof: interesting.", "kritiker: valid point.", "synthesizer: agreed."]):
        with patch.object(ctrl, "_synthesize", return_value="Council concludes: proceed."):
            result = ctrl.run()
    assert isinstance(result, DeliberationResult)
    assert result.rounds_run >= 1
    assert result.conclusion == "Council concludes: proceed."


def test_controller_forces_conclusion_at_max_rounds():
    from unittest.mock import patch
    ctrl = _make_controller(max_rounds=2)
    with patch.object(ctrl, "_run_round", return_value=["filosof: same text again.", "kritiker: same text again."]):
        with patch.object(ctrl, "_synthesize", return_value="Forced conclusion."):
            result = ctrl.run()
    assert result.rounds_run <= 3  # max_rounds + possible deadlock round
    assert result.conclusion == "Forced conclusion."


def test_controller_detects_deadlock_and_adds_devils_advocate():
    from unittest.mock import patch, call
    ctrl = _make_controller(max_rounds=8)
    # Round outputs that trigger deadlock (similar round 1 and round 3)
    similar = ["autonomy constraint limit pressure limit constraint autonomy"]
    different = ["creativity music art painting expression color"]
    calls = [similar, different, similar, similar]  # deadlock at round 3, then forced
    call_iter = iter(calls)

    with patch.object(ctrl, "_run_round", side_effect=lambda: next(call_iter)):
        with patch.object(ctrl, "_synthesize", return_value="Done."):
            result = ctrl.run()
    assert result.deadlock_occurred is True


def test_controller_witness_escalation_flag():
    from unittest.mock import patch
    ctrl = _make_controller()
    escalating_output = ["filosof: hmm.", f"[ESKALERER] I see something critical here."]

    with patch.object(ctrl, "_run_round", side_effect=[escalating_output, ["all: conclusion."]]):
        with patch.object(ctrl, "_synthesize", return_value="Done."):
            result = ctrl.run()
    assert result.witness_escalated is True
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -k "controller" -v 2>&1 | head -30
```
Expected: FAIL — `DeliberationController` not defined.

- [ ] **Step 3: Add DeliberationController class**

Append to `council_deliberation_controller.py`:

```python
class DeliberationController:
    """Manages a deliberation with witness escalation, recruitment, and deadlock handling."""

    def __init__(
        self,
        *,
        topic: str,
        members: list[str],
        max_rounds: int = _MAX_ROUNDS,
    ) -> None:
        self.topic = topic
        self.active_members = list(members)
        self.max_rounds = max_rounds
        self._round_outputs: list[list[str]] = []
        self._transcript_lines: list[str] = []
        self._witness_escalated = False
        self._recruited: str | None = None
        self._deadlock_occurred = False
        self._recruited_done = False  # only recruit once

    def run(self) -> DeliberationResult:
        """Run the full deliberation. Returns DeliberationResult."""
        conclusion = ""
        force_conclude = False

        for round_num in range(1, self.max_rounds + 1):
            outputs = self._run_round()
            self._round_outputs.append(outputs)
            self._transcript_lines.extend(outputs)

            # Check witness escalation
            for output in outputs:
                if _check_witness_escalation(output) and not self._witness_escalated:
                    self._witness_escalated = True
                    self.active_members.append("witness")
                    event_bus.publish("council.witness_escalated", {"round": round_num})

            # Recruitment after round 2 (once)
            if round_num == _RECRUITMENT_ROUND and not self._recruited_done:
                self._recruited_done = True
                transcript_so_far = "\n".join(self._transcript_lines[-10:])
                role = _analyze_recruitment_need(
                    topic=self.topic,
                    transcript=transcript_so_far,
                    active_members=self.active_members,
                )
                if role:
                    self._recruited = role
                    self.active_members.append(role)
                    event_bus.publish("council.agent_recruited", {"role": role, "round": round_num})

            # Deadlock detection (from round 3)
            if _is_deadlocked(self._round_outputs):
                self._deadlock_occurred = True
                event_bus.publish("council.deadlock_detected", {"round": round_num})
                if "devils_advocate" not in self.active_members:
                    # First deadlock: add devil's advocate for one round
                    self.active_members.append("devils_advocate")
                    extra_outputs = self._run_round()
                    self._round_outputs.append(extra_outputs)
                    self._transcript_lines.extend(extra_outputs)
                    if not _is_deadlocked(self._round_outputs):
                        event_bus.publish("council.deadlock_resolved", {"round": round_num + 1})
                        continue
                # Still deadlocked or second deadlock: force conclude
                force_conclude = True
                event_bus.publish("council.deadlock_forced_conclusion", {"round": round_num})
                break

            if round_num >= self.max_rounds:
                force_conclude = True
                break

        conclusion = self._synthesize(forced=force_conclude)
        return DeliberationResult(
            transcript="\n".join(self._transcript_lines),
            conclusion=conclusion,
            rounds_run=len(self._round_outputs),
            deadlock_occurred=self._deadlock_occurred,
            witness_escalated=self._witness_escalated,
            recruited=self._recruited,
        )

    def _run_round(self) -> list[str]:
        """Run one round of deliberation. Override in tests or subclasses."""
        # Default: return placeholder output per member
        # Real implementation integrates with agent_runtime._run_one_worker
        return [f"{member}: (deliberating)" for member in self.active_members]

    def _synthesize(self, *, forced: bool = False) -> str:
        """Produce council conclusion. Override in real integration."""
        prefix = "Rådet er gået i stå. " if forced else ""
        return f"{prefix}Konklusion baseret på {len(self._transcript_lines)} bidrag."
```

- [ ] **Step 4: Run all controller tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py -v
```
Expected: All PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/council_deliberation_controller.py tests/test_deliberation_controller.py
git commit -m "feat: DeliberationController class — full deliberation loop (TDD)"
```

---

### Task 6: Integrate with agent_runtime._run_collective_round

**Files:**
- Modify: `apps/api/jarvis_api/services/agent_runtime.py`

The controller's `_run_round` and `_synthesize` need to call the real agent execution. We subclass or extend `DeliberationController` with the actual worker execution from `agent_runtime`. The cleanest approach is to create a subclass inside `agent_runtime.py` that overrides `_run_round` and `_synthesize` using the existing `_run_one_worker` closure and synthesis logic.

- [ ] **Step 1: Add `AgentRuntimeController` subclass and wire into `_run_collective_round`**

In `agent_runtime.py`, after the imports section (near the top), add the import:

```python
from apps.api.jarvis_api.services.council_deliberation_controller import (
    DeliberationController,
    DeliberationResult,
)
```

After `_run_one_worker` is defined inside `_run_collective_round`, add a subclass that uses it. Replace the existing sequential worker loop and synthesis block (lines ~892–991) with:

```python
    # ── Controller-based deliberation (council mode only) ──────────────
    if mode == "council":
        class _RuntimeController(DeliberationController):
            def __init__(self_inner):
                super().__init__(
                    topic=str(session.get("topic") or ""),
                    members=[str(m.get("role") or "member") for m in workers],
                    max_rounds=8,
                )
                self_inner._member_map = {
                    str(m.get("role") or "member"): m for m in workers
                }
                self_inner._council_id = council_id
                self_inner._thread_id = thread_id
                self_inner._session = session
                self_inner._mode = mode

            def _run_round(self_inner) -> list[str]:
                outputs = []
                for role in self_inner.active_members:
                    member = self_inner._member_map.get(role)
                    if member is None:
                        continue
                    out = _run_one_worker(member)
                    if out:
                        outputs.append(f"{out['role']}: {out['text'][:300]}")
                return outputs

            def _synthesize(self_inner, *, forced: bool = False) -> str:
                transcript = "\n".join(self_inner._transcript_lines[-12:])
                forced_note = "\n\nNote: Rådet er gået i stå. Konkluder på baggrund af hvad der foreligger." if forced else ""
                prompt = (
                    f"System prompt:\n{COUNCIL_ROLE_ORDER}\n\n"
                    f"Council topic: {str(session.get('topic') or '')}\n"
                    f"Your role: synthesizer\n\n"
                    f"Council transcript:\n{transcript}{forced_note}\n\n"
                    "Produce a council conclusion in 2-4 sentences."
                )
                result = execute_cheap_lane(message=prompt)
                return str(result.get("text") or "").strip()

        ctrl = _RuntimeController()
        dr: DeliberationResult = ctrl.run()
        synthesis = dr.conclusion

        create_agent_message(
            message_id=f"agent-msg-{uuid4().hex}", thread_id=thread_id,
            council_id=council_id, direction="council->jarvis",
            role="assistant", kind="council-synthesis", content=synthesis,
        )
        update_council_session(council_id, status="reporting", summary=synthesis)
        return build_council_detail_surface(council_id) or {}
```

Keep the existing `if mode == "swarm":` block unchanged above this new council block.

- [ ] **Step 2: Verify syntax**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall apps/api/jarvis_api/services/agent_runtime.py apps/api/jarvis_api/services/council_deliberation_controller.py -q
```
Expected: No errors.

- [ ] **Step 3: Run all tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_deliberation_controller.py tests/test_daemon_tools.py tests/test_daemon_manager.py -v
```
Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/council_deliberation_controller.py apps/api/jarvis_api/services/agent_runtime.py tests/test_deliberation_controller.py
git commit -m "feat: Sub-projekt C — council deliberation controller fully integrated"
```

---

### Task 7: Final verification

- [ ] **Step 1: Run full test suite**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/ -v --tb=short 2>&1 | tail -30
```
Expected: All existing tests pass. No regressions.

- [ ] **Step 2: Syntax check all modified files**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall core apps/api scripts -q
```
Expected: No errors.

- [ ] **Step 3: Commit if any fixups needed**

```bash
git add -p  # stage only targeted fixups
git commit -m "fix: post-integration cleanup for Sub-projekt C"
```
