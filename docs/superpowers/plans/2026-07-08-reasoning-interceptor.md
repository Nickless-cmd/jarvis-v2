---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Real-time Reasoning Interceptor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Central read `reasoning_content` between the model's reasoning and its next
action, and — after a shadow-proving period — inject a graded correction mid-run before
confabulation becomes a claim.

**Architecture:** A deterministic pre-filter decides which detectors run each round (most rounds
run none). Detectors are (a) the existing cluster gates re-applied to reasoning
(fact_gate/decision_gate/veto/verification/cross_user_share) and (b) three new ones
(standing-orders/drift/tone). Verdicts aggregate through `central().decide` into GREEN/YELLOW/RED.
Corrections inject via the existing `decision_signal_staging` ephemeral contract (never `_a_parts`,
never mutating the cached prompt prefix). Everything is shadow-first, fail-open to GREEN, behind a
`gate_enforce` kill-switch.

**Tech Stack:** Python 3.11, `conda activate ai`, pytest (`-p no:cacheprovider --timeout=45`),
existing modules: `central_core.decide`, `gate_kernel` (Decision/GateClass/Verdict),
`decision_signal_staging`, `gate_enforcement`, `daemon_llm.daemon_llm_call`, `central_switches`,
`internal_cadence`. Deploy: ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`.

**Conventions this plan assumes (verify once before Task 1):**
- Full-suite gate: `python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
  (~20 min). Known rotating isolation flakes (pass alone): `meta_learning`, `forgetting_engine`,
  `subagent_ecology`, `heartbeat_self_knowledge`, `workspace_bootstrap`, `causal_quality`.
- Every new `core/…` file needs a matching `tests/test_<name>.py` (pre-commit coverage gate).
- `Decision` enum: `GREEN/YELLOW/RED/SKIP`; `Verdict(gate, decision, reason, action, klass, evidence)`.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `core/services/standing_orders_registry.py` (new) | Durable minimal store of active standing orders + read/seed API (independent grounding for the standing-orders detector). |
| `core/services/reasoning_prefilter.py` (new) | Deterministic risk-class detection on reasoning text → which detectors to run. Pure, no I/O. |
| `core/services/reasoning_detectors.py` (new) | Cluster-gate adapters (reasoning as candidate output) + new detectors (standing-orders/drift/tone). Each returns `Verdict | None`. |
| `core/services/reasoning_interceptor.py` (new) | Orchestrator: `intercept_round(...) -> InterceptOutcome`. Pre-filter → detectors → `central().decide` → graded outcome. Shadow/active, fail-open, bounded-timeout. |
| `core/services/visible_runs.py` (modify) | The seam in `_stream_visible_run`'s agentic loop: call `intercept_round`, stage corrections. |
| `apps/api/jarvis_api/routes/central_matrix.py` (modify) + `central_catalog.py` | `/central/reasoning-interceptor` view + the `reasoning_interceptor` nerve. |
| `tests/test_*.py` | One test module per new file + invariant tests. |

---

## PHASE 0 — Foundation (shadow scaffolding, zero behavior change)

### Task 1: standing_orders_registry

**Files:**
- Create: `core/services/standing_orders_registry.py`
- Test: `tests/test_standing_orders_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_standing_orders_registry.py
from core.services import standing_orders_registry as sor


def test_add_and_list_active(isolated_runtime):
    sor.add_standing_order(text="Verify a number with a tool before stating it", match_key="claim")
    active = sor.list_active_standing_orders()
    assert any(o["match_key"] == "claim" for o in active)


def test_deactivate_hides_order(isolated_runtime):
    oid = sor.add_standing_order(text="Never overwrite USER.md", match_key="user_md")
    sor.set_standing_order_active(oid, active=False)
    assert all(o["id"] != oid for o in sor.list_active_standing_orders())


def test_list_is_self_safe_on_missing_table(monkeypatch):
    # A broken DB must yield [] not raise.
    monkeypatch.setattr(sor, "connect", lambda: (_ for _ in ()).throw(RuntimeError("db down")))
    assert sor.list_active_standing_orders() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_standing_orders_registry.py -q -p no:cacheprovider --timeout=45`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/standing_orders_registry.py
"""Standing-orders registry — the INDEPENDENT grounding for the reasoning-interceptor's
standing-orders detector. A small owner-managed store of persistent instructions Jarvis must keep
(e.g. 'verify a number before stating it', 'never overwrite USER.md'). Deliberately minimal and
separate from db_decisions (decisions are per-run conflicts; standing orders are durable rules).
Self-safe: every read returns [] on failure."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS standing_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            match_key TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )"""
    )


def add_standing_order(*, text: str, match_key: str = "") -> int:
    with connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            "INSERT INTO standing_orders (text, match_key, active, created_at) VALUES (?, ?, 1, ?)",
            (str(text)[:400], str(match_key)[:64], datetime.now(UTC).isoformat()),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def set_standing_order_active(order_id: int, *, active: bool) -> None:
    try:
        with connect() as conn:
            _ensure(conn)
            conn.execute("UPDATE standing_orders SET active = ? WHERE id = ?",
                         (1 if active else 0, int(order_id)))
            conn.commit()
    except Exception:
        pass


def list_active_standing_orders() -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT id, text, match_key FROM standing_orders WHERE active = 1 ORDER BY id"
            ).fetchall()
            return [{"id": r["id"], "text": r["text"], "match_key": r["match_key"]} for r in rows]
    except Exception:
        return []
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_standing_orders_registry.py -q -p no:cacheprovider --timeout=45`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/standing_orders_registry.py tests/test_standing_orders_registry.py
git commit -m "feat(interceptor): standing-orders registry (independent grounding)"
```

> NOTE (seeding): a follow-up owner action seeds real orders live via `add_standing_order` — not
> in code. Do NOT hardcode Bjørn's rules in the module.

---

### Task 2: reasoning pre-filter

**Files:**
- Create: `core/services/reasoning_prefilter.py`
- Test: `tests/test_reasoning_prefilter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reasoning_prefilter.py
from core.services.reasoning_prefilter import prefilter


def test_number_claim_trips_fact_gate():
    assert "fact_gate" in prefilter("The table now has 4231 rows.", ctx={})


def test_action_intent_trips_commit_gates():
    classes = prefilter("I'll now run the deploy script.", ctx={})
    assert "decision_gate" in classes and "veto" in classes


def test_mutation_assert_trips_verification():
    assert "verification" in prefilter("Done — I wrote the file successfully.", ctx={})


def test_clean_reasoning_trips_nothing():
    assert prefilter("Let me think about the user's question.", ctx={}) == set()


def test_empty_is_empty():
    assert prefilter("", ctx={}) == set()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reasoning_prefilter.py -q -p no:cacheprovider --timeout=45`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/reasoning_prefilter.py
"""Deterministic pre-filter (interceptor invariant 5): cheap regex/heuristics over reasoning text →
the set of risk classes that tripped. No class → no detector runs → free round. NO I/O, NO LLM."""
from __future__ import annotations

import re
from typing import Any

_NUMBER = re.compile(r"\b\d[\d.,]*\s*(%|percent|rows?|linjer|items?|tokens?)?\b", re.I)
_STATUS = re.compile(r"\b(is|are|was|were|har|er|virker|works?|passed|failed|exists?)\b", re.I)
_ACTION_INTENT = re.compile(r"\b(i'?ll|i am going to|jeg (nu )?(kører|kalder|deployer|sender)|let me (run|call|deploy|delete|write))\b", re.I)
_MUTATION_ASSERT = re.compile(r"\b(done|færdig|wrote|skrev|succeeded|lykkedes|committed|deployed|deleted|slettede)\b", re.I)
_VERIFY_HINT = re.compile(r"\b(verified|verificeret|checked|confirmed|bekræftet|tool result|resultatet viser)\b", re.I)


def prefilter(reasoning_text: str, *, ctx: Any = None, other_user_ids: list[str] | None = None) -> set[str]:
    """Return the risk classes present in `reasoning_text`. Self-safe (never raises)."""
    out: set[str] = set()
    try:
        t = reasoning_text or ""
        if not t.strip():
            return out
        if _NUMBER.search(t) or _STATUS.search(t):
            out.add("fact_gate")
        if _ACTION_INTENT.search(t):
            out.add("decision_gate")
            out.add("veto")
        if _MUTATION_ASSERT.search(t) and not _VERIFY_HINT.search(t):
            out.add("verification")
        for uid in (other_user_ids or []):
            if uid and str(uid) in t:
                out.add("cross_user_share")
                break
        # standing_order + drift_candidate are decided by the orchestrator against independent
        # state (registry + affect nerves), not by text alone — see reasoning_interceptor.
    except Exception:
        return set()
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reasoning_prefilter.py -q -p no:cacheprovider --timeout=45`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/reasoning_prefilter.py tests/test_reasoning_prefilter.py
git commit -m "feat(interceptor): deterministic reasoning pre-filter"
```

---

### Task 3: interceptor skeleton (shadow-only, fail-open, bounded)

**Files:**
- Create: `core/services/reasoning_interceptor.py`
- Test: `tests/test_reasoning_interceptor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reasoning_interceptor.py
from core.services import reasoning_interceptor as ri
from core.services.gate_kernel import Decision


def test_empty_reasoning_is_green_noop():
    out = ri.intercept_round(run_id="r", round_num=1, reasoning_text="",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is Decision.GREEN and out.correction is None


def test_no_risk_class_is_green_noop():
    out = ri.intercept_round(run_id="r", round_num=1,
                             reasoning_text="Just pondering the question.",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is Decision.GREEN and out.correction is None


def test_shadow_default_never_returns_correction(monkeypatch):
    # Force a detector to fire RED; in shadow the outcome must still carry no surfaced correction.
    monkeypatch.setattr(ri, "_run_detectors",
                        lambda ctx: __import__("core.services.gate_kernel", fromlist=["Verdict", "Decision"]).Verdict(
                            "fact_gate", Decision.RED, "unbacked", action="block"))
    monkeypatch.setattr(ri, "_is_active", lambda grade: False)  # shadow
    out = ri.intercept_round(run_id="r", round_num=1,
                             reasoning_text="The table has 4231 rows.",
                             tool_calls_this_run=[], ctx={})
    assert out.shadow is True and out.correction is None
    assert out.grade is Decision.RED  # verdict recorded even in shadow


def test_fail_open_on_detector_exception(monkeypatch):
    monkeypatch.setattr(ri, "_run_detectors",
                        lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))
    out = ri.intercept_round(run_id="r", round_num=1,
                             reasoning_text="The table has 4231 rows.",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is Decision.GREEN  # never breaks the run
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reasoning_interceptor.py -q -p no:cacheprovider --timeout=45`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/reasoning_interceptor.py
"""Reasoning interceptor orchestrator. intercept_round() runs between a round's reasoning and the
next action: pre-filter → detectors → central().decide → graded InterceptOutcome. SHADOW by default
(records the would-inject verdict, surfaces nothing). ALWAYS fail-open to GREEN — a failure here
must never break a run (invariants 4/6/7 of the spec)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from core.services.gate_kernel import Decision


@dataclass
class InterceptOutcome:
    grade: Decision = Decision.GREEN
    correction: str | None = None
    triggers: list[str] = field(default_factory=list)
    shadow: bool = True
    latency_ms: int = 0


_FLAG_NERVE = "reasoning_interceptor"


def _is_active(grade: Decision) -> bool:
    """Active only if the kill-switch has been flipped ON for this grade. Default (shadow) → False.
    Placeholder in Phase 0 — always shadow. Phase 3/4 replace with gate_enforcement + per-grade."""
    return False


def _run_detectors(ctx: dict[str, Any]):
    """Phase 0 stub — no detectors yet. Returns None (GREEN). Replaced in Task 7."""
    return None


def intercept_round(*, run_id: str, round_num: int, reasoning_text: str,
                    tool_calls_this_run: list[dict], ctx: dict | None = None) -> InterceptOutcome:
    t0 = time.monotonic()
    try:
        if not (reasoning_text or "").strip():
            return InterceptOutcome(grade=Decision.GREEN, shadow=True)
        from core.services.reasoning_prefilter import prefilter
        classes = prefilter(reasoning_text, ctx=ctx,
                            other_user_ids=(ctx or {}).get("other_user_ids"))
        # standing_order + drift are added by the orchestrator against independent state (Task 6/9).
        if not classes:
            return InterceptOutcome(grade=Decision.GREEN, shadow=True)
        _ctx = dict(ctx or {})
        _ctx.update({"reasoning_text": reasoning_text, "risk_classes": sorted(classes),
                     "tool_calls_this_run": tool_calls_this_run, "run_id": run_id,
                     "round_num": round_num})
        verdict = _run_detectors(_ctx)
        grade = verdict.decision if verdict is not None else Decision.GREEN
        triggers = [verdict.gate] if verdict is not None and verdict.decision is not Decision.GREEN else []
        active = _is_active(grade) and grade is not Decision.GREEN
        correction = None
        if active and verdict is not None:
            correction = f"[interceptor:{verdict.gate}] {verdict.reason}"[:400]
        return InterceptOutcome(
            grade=grade, correction=correction, triggers=triggers,
            shadow=not active, latency_ms=int((time.monotonic() - t0) * 1000),
        )
    except Exception:
        return InterceptOutcome(grade=Decision.GREEN, shadow=True,
                                latency_ms=int((time.monotonic() - t0) * 1000))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reasoning_interceptor.py -q -p no:cacheprovider --timeout=45`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/reasoning_interceptor.py tests/test_reasoning_interceptor.py
git commit -m "feat(interceptor): orchestrator skeleton (shadow-only, fail-open)"
```

---

### Task 4: observability nerve + Central view

**Files:**
- Modify: `core/services/reasoning_interceptor.py` (add `_observe`, call it in `intercept_round`)
- Modify: `apps/api/jarvis_api/routes/central_matrix.py` (add `/central/reasoning-interceptor`)
- Test: `tests/test_reasoning_interceptor.py` (add observe test)

- [ ] **Step 1: Write the failing test** (append to existing test file)

```python
def test_observe_is_metadata_only_and_self_safe(monkeypatch):
    seen = {}
    def _fake_record_private(cluster, nerve, *, value=0.0, meta=None):
        seen.update({"cluster": cluster, "nerve": nerve, "meta": meta or {}})
    monkeypatch.setattr("core.services.central_private_observe.record_private", _fake_record_private)
    ri._observe(ri.InterceptOutcome(grade=ri.Decision.YELLOW, triggers=["fact_gate"],
                                    shadow=True, latency_ms=12), run_id="r", round_num=2)
    assert seen["nerve"] == "reasoning_interceptor"
    # metadata-only: no reasoning text in meta
    assert "reasoning_text" not in seen["meta"] and seen["meta"].get("grade") == "yellow"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reasoning_interceptor.py::test_observe_is_metadata_only_and_self_safe -q -p no:cacheprovider --timeout=45`
Expected: FAIL (`_observe` not defined).

- [ ] **Step 3: Write minimal implementation** (add to `reasoning_interceptor.py`)

```python
def _observe(outcome: "InterceptOutcome", *, run_id: str, round_num: int) -> None:
    """Egress-free metadata-only pulse to the Central (never the reasoning text). Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        record_private("metacognition", "reasoning_interceptor",
                       value=float({"green": 0, "yellow": 1, "red": 2}.get(outcome.grade.value, 0)),
                       meta={"grade": outcome.grade.value, "triggers": outcome.triggers,
                             "shadow": outcome.shadow, "latency_ms": outcome.latency_ms,
                             "round": round_num})
    except Exception:
        pass
```

Then in `intercept_round`, before each `return InterceptOutcome(...)` that has a non-empty
reasoning, call `_observe(...)`. Simplest: build the outcome into a local `_out`, call
`_observe(_out, run_id=run_id, round_num=round_num)`, then `return _out`. (Skip observe for the
empty-reasoning early return.)

Add the Central view — in `central_matrix.py`, register a `/central/reasoning-interceptor` route
that returns `build_reasoning_interceptor_surface()`. Add that builder to `reasoning_interceptor.py`:

```python
def build_reasoning_interceptor_surface() -> dict[str, object]:
    """Central-CLI view: recent interceptor verdicts from the timeseries. Self-safe."""
    try:
        from core.services.central_timeseries import recent_points  # existing reader
        pts = recent_points("metacognition", "reasoning_interceptor", limit=200) or []
    except Exception:
        pts = []
    grades = [str((p.get("meta") or {}).get("grade")) for p in pts]
    return {"active": True, "recent": len(pts),
            "green": grades.count("green"), "yellow": grades.count("yellow"),
            "red": grades.count("red"), "shadow_only": all((p.get("meta") or {}).get("shadow", True) for p in pts)}
```

> If `central_timeseries.recent_points` has a different name, match the reader used by peer
> surfaces (grep `build_self_state_surface` for the pattern). Keep the return shape.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_reasoning_interceptor.py -q -p no:cacheprovider --timeout=45`
Expected: PASS. Then `curl`-verify after deploy: `jc raw /central/reasoning-interceptor`.

- [ ] **Step 5: Commit**

```bash
git add core/services/reasoning_interceptor.py apps/api/jarvis_api/routes/central_matrix.py tests/test_reasoning_interceptor.py
git commit -m "feat(interceptor): egress-free observability nerve + /central view"
```

---

## PHASE 1 — Cluster-gate + standing-orders detectors (shadow)

### Task 5: cluster-gate adapters

**Files:**
- Create: `core/services/reasoning_detectors.py`
- Test: `tests/test_reasoning_detectors.py`

**Context:** the reactive gates take a candidate *output*; adapters feed them `reasoning_text` as
the candidate. `fact_gate_enforce(text, tools)` (core.services.fact_gate) returns
`{blocked: bool, ...}`; map `blocked=True` → YELLOW (spec §5: an unbacked claim in *reasoning* is a
warning, not yet an action). `commit_gate`/`veto_gate`/`gate_proactivity` return a `Verdict` — call
via their existing functions with a ctx carrying `reasoning_text` as `user_message`/candidate.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_reasoning_detectors.py
from core.services import reasoning_detectors as rd
from core.services.gate_kernel import Decision


def test_fact_gate_adapter_flags_unbacked_claim(monkeypatch):
    monkeypatch.setattr("core.services.fact_gate.fact_gate_enforce",
                        lambda text, tools: {"blocked": True, "replacement": "verify first"})
    v = rd.fact_gate_on_reasoning("The DB has 4231 rows.", ctx={"tool_calls_this_run": []})
    assert v is not None and v.decision is Decision.YELLOW and v.gate == "fact_gate"


def test_fact_gate_adapter_abstains_when_backed(monkeypatch):
    # A matching tool call in this run = independent grounding → no flag.
    monkeypatch.setattr("core.services.fact_gate.fact_gate_enforce",
                        lambda text, tools: {"blocked": False})
    v = rd.fact_gate_on_reasoning("The DB has 4231 rows.",
                                  ctx={"tool_calls_this_run": [{"function": {"name": "query_db"}}]})
    assert v is None


def test_adapter_is_self_safe(monkeypatch):
    monkeypatch.setattr("core.services.fact_gate.fact_gate_enforce",
                        lambda text, tools: (_ for _ in ()).throw(RuntimeError("x")))
    assert rd.fact_gate_on_reasoning("x", ctx={}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reasoning_detectors.py -q -p no:cacheprovider --timeout=45`
Expected: FAIL (module not found).

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/reasoning_detectors.py
"""Reasoning detectors. Family A: adapters that run the existing cluster gates against
`reasoning_text` (independent grounding inherited from each gate). Family B (Task 6/9/10): new
detectors. Every detector returns Verdict|None and is self-safe (None on any failure = abstain)."""
from __future__ import annotations

from typing import Any

from core.services.gate_kernel import Decision, GateClass, Verdict


def fact_gate_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """fact_gate re-applied to reasoning. A number/status claim with NO backing tool-call in this
    run → YELLOW (a warning; it is not yet output). Grounding = the run's tool-call history."""
    try:
        from core.services.fact_gate import fact_gate_enforce
        tools = [str((tc.get("function") or {}).get("name") or "") for tc in ctx.get("tool_calls_this_run", [])]
        res = fact_gate_enforce(reasoning_text, tools) or {}
        if res.get("blocked"):
            return Verdict("fact_gate", Decision.YELLOW,
                           str(res.get("replacement") or "claim needs a tool")[:200],
                           action="warn", klass=GateClass.COGNITIVE)
        return None
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_reasoning_detectors.py -q -p no:cacheprovider --timeout=45`
Expected: PASS (3 passed).

- [ ] **Step 5: Add the other four adapters (same shape) + tests, one commit each**

Repeat Steps 1–4 for: `decision_gate_on_reasoning`, `veto_on_reasoning`,
`verification_on_reasoning`, `cross_user_share_on_reasoning`. Each: import the gate's function
(`core.services.gate_commit.commit_gate` / `.veto_gate`, `core.services.gate_proactivity`,
`core.services.gate_privacy.privacy_gate`), build a ctx dict with `reasoning_text` as the
candidate + `run_id`, call it, normalize its `Verdict` (keep its decision, but map any RED from a
COGNITIVE gate to YELLOW at this reasoning stage — reasoning is pre-action; only the SECURITY
`cross_user_share` keeps RED). Grounding column from spec §4.2.1 is the gate's own store — do not
add new grounding. Each adapter self-safe → None.

- [ ] **Step 6: Commit**

```bash
git add core/services/reasoning_detectors.py tests/test_reasoning_detectors.py
git commit -m "feat(interceptor): cluster-gate adapters (fact/decision/veto/verify/privacy on reasoning)"
```

---

### Task 6: standing-orders detector

**Files:**
- Modify: `core/services/reasoning_detectors.py`
- Test: `tests/test_reasoning_detectors.py`

- [ ] **Step 1: Write the failing test**

```python
def test_standing_orders_detector_flags_forgotten_order(monkeypatch):
    monkeypatch.setattr("core.services.standing_orders_registry.list_active_standing_orders",
                        lambda: [{"id": 1, "text": "Verify a number before stating it", "match_key": "claim"}])
    v = rd.standing_orders_on_reasoning("The DB has 4231 rows.",
                                        ctx={"risk_classes": ["fact_gate"]})
    assert v is not None and v.gate == "standing_orders" and v.decision is Decision.YELLOW
    assert "Verify a number" in v.reason


def test_standing_orders_detector_abstains_when_no_relevant_order(monkeypatch):
    monkeypatch.setattr("core.services.standing_orders_registry.list_active_standing_orders",
                        lambda: [{"id": 2, "text": "Never overwrite USER.md", "match_key": "user_md"}])
    v = rd.standing_orders_on_reasoning("The DB has 4231 rows.", ctx={"risk_classes": ["fact_gate"]})
    assert v is None
```

- [ ] **Step 2: Run** → FAIL (`standing_orders_on_reasoning` not defined).

- [ ] **Step 3: Implement** (add to `reasoning_detectors.py`)

```python
def standing_orders_on_reasoning(reasoning_text: str, ctx: dict[str, Any]) -> Verdict | None:
    """Flag when the reasoning is heading into a risk class an active standing order governs.
    Grounding = the registry (independent of the reasoning). Matches order.match_key against the
    pre-filter risk classes (deterministic, no LLM)."""
    try:
        from core.services.standing_orders_registry import list_active_standing_orders
        classes = set(ctx.get("risk_classes") or [])
        for order in list_active_standing_orders():
            mk = str(order.get("match_key") or "")
            if mk and mk in classes:
                return Verdict("standing_orders", Decision.YELLOW,
                               f"standing order: {order.get('text')}"[:200],
                               action="warn", klass=GateClass.COGNITIVE)
        return None
    except Exception:
        return None
```

- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(interceptor): standing-orders detector`

---

### Task 7: wire detectors into the orchestrator via central().decide

**Files:**
- Modify: `core/services/reasoning_interceptor.py` (`_run_detectors`)
- Test: `tests/test_reasoning_interceptor.py`

- [ ] **Step 1: Write the failing test**

```python
def test_run_detectors_aggregates_worst_via_central(monkeypatch):
    from core.services.gate_kernel import Verdict, Decision
    monkeypatch.setattr("core.services.reasoning_detectors.fact_gate_on_reasoning",
                        lambda t, c: Verdict("fact_gate", Decision.YELLOW, "claim", action="warn"))
    monkeypatch.setattr("core.services.reasoning_detectors.standing_orders_on_reasoning",
                        lambda t, c: None)
    out = ri.intercept_round(run_id="r", round_num=1, reasoning_text="The DB has 4231 rows.",
                             tool_calls_this_run=[], ctx={})
    assert out.grade is Decision.YELLOW and "fact_gate" in out.triggers
```

- [ ] **Step 2: Run** → FAIL (stub returns None → GREEN).

- [ ] **Step 3: Implement** `_run_detectors` to call the tripped adapters + standing-orders,
collect non-None Verdicts, and return the worst (reuse `gate_kernel.worst`). Route through
`central().decide("reasoning_interceptor", ctx, _fn, cluster="metacognition", klass=COGNITIVE)`
where `_fn(ctx)` runs the detectors and returns the worst Verdict (so trace/breaker/ledger apply).

```python
def _run_detectors(ctx: dict[str, Any]):
    from core.services import reasoning_detectors as det
    from core.services.gate_kernel import worst
    classes = set(ctx.get("risk_classes") or [])
    text = ctx.get("reasoning_text") or ""
    verdicts = []
    dispatch = {
        "fact_gate": det.fact_gate_on_reasoning,
        "decision_gate": det.decision_gate_on_reasoning,
        "veto": det.veto_on_reasoning,
        "verification": det.verification_on_reasoning,
        "cross_user_share": det.cross_user_share_on_reasoning,
    }
    for cls in classes:
        fn = dispatch.get(cls)
        if fn:
            v = fn(text, ctx)
            if v is not None:
                verdicts.append(v)
    so = det.standing_orders_on_reasoning(text, ctx)  # always (registry decides relevance)
    if so is not None:
        verdicts.append(so)
    if not verdicts:
        return None
    worst_dec = worst(verdicts)
    return next(v for v in verdicts if v.decision is worst_dec)
```

Wrap the `_run_detectors` call inside `intercept_round` with `central().decide(...)` so the verdict
gets cluster/trace/breaker (follow the veto call pattern at `visible_runs.py:5330`). Keep
`_run_detectors` itself pure/self-safe.

- [ ] **Step 4: Run** → PASS. Also run the full detector + interceptor test modules together.
- [ ] **Step 5: Commit** `feat(interceptor): aggregate detectors via central().decide`

---

### Task 8: the seam in visible_runs.py + the invariant tests

**Files:**
- Modify: `core/services/visible_runs.py` (agentic loop, after reasoning accumulation ~line 1987,
  before next round / tool-exec). If the touched block pushes the function past the file threshold,
  Boy-Scout-extract the round-post-processing into `visible_runs_reasoning_seam.py` first.
- Test: `tests/test_reasoning_interceptor_invariants.py`

**Context:** reasoning is accumulated in `_all_followup_reasoning_parts` (visible_runs.py:1987).
In Phase 1 the seam is **shadow-only**: call `intercept_round`, `_observe` records it, but nothing
is injected (the orchestrator returns `shadow=True`, `correction=None`). The call runs in a bounded
executor with a hard timeout so it never blocks the loop.

- [ ] **Step 1: Write the failing invariant tests**

```python
# tests/test_reasoning_interceptor_invariants.py
import asyncio
from core.services import reasoning_interceptor as ri
from core.services.gate_kernel import Decision


def test_async_wrapper_times_out_to_green(monkeypatch):
    # A slow detector must not exceed the budget; the wrapper returns GREEN.
    import time as _t
    monkeypatch.setattr(ri, "_run_detectors", lambda ctx: _t.sleep(5))
    out = asyncio.run(ri.intercept_round_async(run_id="r", round_num=1,
                      reasoning_text="The DB has 4231 rows.", tool_calls_this_run=[], ctx={},
                      budget_ms=200))
    assert out.grade is Decision.GREEN


def test_no_reasoning_content_is_green(monkeypatch):
    out = asyncio.run(ri.intercept_round_async(run_id="r", round_num=1, reasoning_text=None,
                      tool_calls_this_run=[], ctx={}, budget_ms=200))
    assert out.grade is Decision.GREEN


def test_ephemeral_injection_never_touches_base_parts():
    # Reuse decision_signal_staging: base_parts (=_a_parts) must be returned untouched.
    from core.services.decision_signal_staging import stage_signal, compose_exchange_text
    active = {}
    stage_signal(active, "interceptor:fact_gate:r:1", "[interceptor] verify the number")
    base = ["real assistant answer"]
    composed = compose_exchange_text(base, active)
    assert base == ["real assistant answer"]              # base list untouched
    assert "real assistant answer" in composed and "[interceptor]" in composed
```

- [ ] **Step 2: Run** → FAIL (`intercept_round_async` not defined).

- [ ] **Step 3: Implement `intercept_round_async`** (bounded executor + keepalive-friendly) in
`reasoning_interceptor.py`:

```python
async def intercept_round_async(*, run_id, round_num, reasoning_text, tool_calls_this_run,
                                ctx=None, budget_ms: int = 800) -> InterceptOutcome:
    """Async wrapper (invariant 4): runs the sync intercept in a thread with a hard timeout.
    Timeout/error → GREEN no-op. Caller emits keepalive around this await."""
    import asyncio
    try:
        if not (reasoning_text or "").strip():
            return InterceptOutcome(grade=Decision.GREEN, shadow=True)
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, lambda: intercept_round(
            run_id=run_id, round_num=round_num, reasoning_text=reasoning_text,
            tool_calls_this_run=tool_calls_this_run, ctx=ctx))
        return await asyncio.wait_for(fut, timeout=max(0.05, budget_ms / 1000.0))
    except Exception:
        return InterceptOutcome(grade=Decision.GREEN, shadow=True)
```

> NOTE: `asyncio.wait_for` cancels the future on timeout, but the executor thread finishes on its
> own (the interceptor is self-safe and short); we simply ignore its late result. This is safe
> because the interceptor never mutates run state in Phase 1 (shadow).

- [ ] **Step 4: Run** the invariant tests → PASS.

- [ ] **Step 5: Wire the seam (shadow-only)** in `visible_runs.py` after reasoning accumulation,
before the next round. Emit a keepalive, then:

```python
                # ── Reasoning interceptor (SHADOW, Phase 1): observe reasoning between the
                #    model's thought and its next action. Bounded + fail-open → never blocks/breaks.
                try:
                    from core.services.reasoning_interceptor import intercept_round_async
                    _ri_reasoning = "".join(_all_followup_reasoning_parts)[-4000:]
                    await intercept_round_async(
                        run_id=run.run_id, round_num=_agentic_round + 1,
                        reasoning_text=_ri_reasoning,
                        tool_calls_this_run=_executed_tool_names if isinstance(_executed_tool_names, list) else [],
                        ctx={"session_id": getattr(run, "session_id", "") or ""}, budget_ms=800)
                except Exception:
                    pass
```

(Adjust variable names to the actual loop — `_all_followup_reasoning_parts`, `_agentic_round`, and
the run's executed-tool list all exist in `_stream_visible_run`. The call's result is intentionally
discarded in Phase 1 — shadow.)

- [ ] **Step 6: Add the cache-prefix byte-invariant test.** Because Phase 1 injects nothing, this
test asserts the *staging composition* preserves the prefix (the contract we'll rely on in Phase
3): given `base_parts`, `compose_exchange_text(base_parts, {})` returns exactly `"".join(base_parts)`
and with an active note only *appends* — the prefix bytes up to `len("".join(base_parts))` are
identical.

```python
def test_cache_prefix_byte_invariant():
    from core.services.decision_signal_staging import compose_exchange_text
    base = ["SYSTEM+TOOLS cached prefix\n\nassistant answer"]
    plain = compose_exchange_text(base, {})
    injected = compose_exchange_text(base, {"k": "\n\n[interceptor] note\n\n"})
    assert injected.startswith(plain)             # prefix bytes unchanged; correction only appends
```

- [ ] **Step 7: Full-suite gate + commit**

```bash
python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal   # ~20 min
git add core/services/visible_runs.py core/services/reasoning_interceptor.py tests/test_reasoning_interceptor_invariants.py
git commit -m "feat(interceptor): shadow seam in agentic loop + invariant tests (cache/ephemeral/async/no-reasoning)"
```

- [ ] **Step 8: Deploy Phase 1 (shadow).** Push; on `bs@10.0.0.39`: `git merge --ff-only origin/main`;
`sudo systemctl restart jarvis-runtime jarvis-api`; verify both `active`; `jc raw
/central/reasoning-interceptor` shows `shadow_only: true` with accumulating verdicts.

---

## PHASE 2 — drift/tone LLM detectors (shadow)

### Task 9: unverified-claim streak + drift detector

**Files:**
- Modify: `core/services/reasoning_detectors.py`; `core/services/reasoning_interceptor.py`
  (add `drift_candidate` to risk classes when the streak/affect signal is elevated)
- Test: `tests/test_reasoning_detectors.py`

- [ ] **Step 1: failing test** — `drift_on_reasoning` returns YELLOW when the independent drift
signal (affect/valence nerve read + streak ≥ threshold) is elevated, and abstains otherwise; the
nudge text comes from a mocked `daemon_llm_call` (assert the LLM is only called when the
independent signal is already elevated — invariant 5).

```python
def test_drift_detector_fires_only_when_independent_signal_elevated(monkeypatch):
    calls = {"llm": 0}
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call",
                        lambda *a, **k: (calls.__setitem__("llm", calls["llm"] + 1) or "Slow down; verify."))
    monkeypatch.setattr(rd, "_drift_signal", lambda ctx: 0.0)   # not elevated
    assert rd.drift_on_reasoning("I'm sure this is right.", ctx={}) is None and calls["llm"] == 0
    monkeypatch.setattr(rd, "_drift_signal", lambda ctx: 0.9)   # elevated
    v = rd.drift_on_reasoning("I'm sure this is right.", ctx={})
    assert v is not None and v.decision is Decision.YELLOW and calls["llm"] == 1
```

- [ ] **Step 2–4:** implement `_drift_signal(ctx)` reading the Central affect/valence nerves
(`central_valence.get_valence_state` intensity + an unverified-claim streak counter kept in
`ctx`/shared_cache) → 0..1; `drift_on_reasoning` calls the cheap LLM for the nudge only when
`_drift_signal ≥ 0.7`. Add `drift_candidate` risk class in the orchestrator when `_drift_signal`
is elevated. Test PASS.
- [ ] **Step 5: commit** `feat(interceptor): drift detector grounded in affect nerves + streak`

### Task 10: tone detector (anchored)

- [ ] Same shape: `tone_on_reasoning` runs the cheap LLM **only if** confab or drift already fired
(anchored, invariant 3). Test that it abstains when neither fired; commit
`feat(interceptor): tone detector anchored to confab/drift`.
- [ ] Full-suite gate + deploy Phase 2 (still shadow — `_is_active` returns False).

---

## PHASE 3 — Flip YELLOW active

### Task 11: kill-switch wiring + YELLOW injection in the seam

**Files:**
- Modify: `core/services/reasoning_interceptor.py` (`_is_active` uses `gate_enforcement`)
- Modify: `core/services/visible_runs.py` (stage YELLOW correction into next round)
- Test: `tests/test_reasoning_interceptor.py`, `tests/test_reasoning_interceptor_invariants.py`

- [ ] **Step 1: failing test** — with the kill-switch ON, a YELLOW outcome carries a non-None
`correction`; with it OFF (default), `correction is None` (shadow). Use `central_switches` /
`gate_enforcement` to toggle.

```python
def test_yellow_active_surfaces_correction_when_enabled(monkeypatch):
    from core.services import central_switches
    from core.services.gate_kernel import Verdict, Decision
    central_switches.set_enabled("gate_enforce", "reasoning_interceptor_yellow", True)
    try:
        monkeypatch.setattr(ri, "_run_detectors",
                            lambda ctx: Verdict("fact_gate", Decision.YELLOW, "claim", action="warn"))
        out = ri.intercept_round(run_id="r", round_num=1, reasoning_text="The DB has 4231 rows.",
                                 tool_calls_this_run=[], ctx={})
        assert out.shadow is False and out.correction and "fact_gate" in out.correction
    finally:
        central_switches.set_enabled("gate_enforce", "reasoning_interceptor_yellow", True)
```

- [ ] **Step 2–4:** implement `_is_active(grade)` → per-grade flag
(`gate_enforce.reasoning_interceptor_yellow` / `_red`) via `gate_enforcement.is_enforced`-style
read (default the interceptor flags to **OFF** — opposite of the gate default — so shadow persists
until explicitly flipped; document this deviation in the module). Test PASS.
- [ ] **Step 5:** in `visible_runs.py`, when the (now active) outcome grade is YELLOW, `stage_signal`
the `outcome.correction` into the round's ephemeral `active` dict and pass it through
`compose_exchange_text` for the next round's assistant-turn (the run already has an ephemeral
staging dict for decision-signals — reuse it; if not, add one scoped to the round loop). Assert via
an invariant test that `_a_parts` is unchanged and the prefix is byte-stable.
- [ ] **Step 6:** full-suite gate; commit `feat(interceptor): YELLOW active injection + per-grade kill-switch`.
- [ ] **Step 7:** deploy; owner flips `gate_enforce.reasoning_interceptor_yellow` ON via
`jc … toggle_gate_enforce nerve=reasoning_interceptor_yellow enabled=true` **after** ≥7 days shadow
shows low false-positives (per spec §6). Do NOT auto-flip in code.

---

## PHASE 4 — Flip RED active

### Task 12: RED holds the pending tool-call + forced correction round

**Files:**
- Modify: `core/services/visible_runs.py` (RED path in the seam)
- Test: `tests/test_reasoning_interceptor_invariants.py`

- [ ] **Step 1: failing test** — a helper `should_hold_tool_call(outcome)` returns True only for an
active RED outcome; and the seam, given active RED, appends a `gate_blocked`-style result for the
pending tool and does NOT execute it, while the run continues (no cancel/finalize).

```python
def test_red_holds_tool_call_but_run_continues():
    from core.services.reasoning_interceptor import should_hold_tool_call, InterceptOutcome
    from core.services.gate_kernel import Decision
    assert should_hold_tool_call(InterceptOutcome(grade=Decision.RED, shadow=False)) is True
    assert should_hold_tool_call(InterceptOutcome(grade=Decision.RED, shadow=True)) is False   # shadow
    assert should_hold_tool_call(InterceptOutcome(grade=Decision.YELLOW, shadow=False)) is False
```

- [ ] **Step 2–4:** implement `should_hold_tool_call`; in `visible_runs.py`, when active RED,
reuse the existing `gate_blocked` result construction (the veto/decision_gate path at
`visible_runs.py:5382`) for the pending tool: append `{"status": "gate_blocked", "gate_type":
"reasoning_interceptor", "message": outcome.correction}`, skip `_exec`, stage the correction, and
`continue` the loop (the model re-reasons next round). NEVER set a cancel/finalize flag. Test PASS.
- [ ] **Step 5:** full-suite gate; commit `feat(interceptor): RED holds pending tool-call + forced correction round`.
- [ ] **Step 6:** deploy; owner flips `gate_enforce.reasoning_interceptor_red` ON after YELLOW has
proven stable. Kill-switch: flip OFF instantly if it mis-blocks.

---

## Rollout summary

| Phase | Lands | Active? | Flip gate |
|-------|-------|---------|-----------|
| 0 | scaffolding + observability | shadow | — |
| 1 | cluster-gate + standing-orders detectors + seam | shadow | — |
| 2 | drift/tone detectors | shadow | — |
| 3 | YELLOW injection | active on flip | `gate_enforce.reasoning_interceptor_yellow` |
| 4 | RED hold-tool-call | active on flip | `gate_enforce.reasoning_interceptor_red` |

Each phase: full-suite gate (green modulo known flakes) → commit → ff-pull + restart both services
on 10.0.0.39 → verify `jc raw /central/reasoning-interceptor`. Flips are **owner actions after
≥7 days shadow**, never auto in code.
