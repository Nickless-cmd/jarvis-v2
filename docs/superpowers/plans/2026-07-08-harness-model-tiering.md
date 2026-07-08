# Harness Refactor Part 1 — Earned Model-Trust + Instruction/Config — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the Central earn each model's trust from evidence (weak→strong, auto-revert on regression) and give strong lanes Claude-Code-style instructive-trust instructions + model-window-aware compaction — while changing none of the 7 coercion mechanisms.

**Architecture:** A new durable per-model trust store (`model_trust.py`) that starts every model weak, promotes to strong after 20 consecutive clean runs, and reverts on a single degeneration event. `model_strength(model)` (fail-open weak) is read by the prompt-instruction builder (tiered) and is observable via `/central/model-trust`. Degeneration is marked at the existing detection points in the agentic loop; the outcome is recorded once at run finalize.

**Tech Stack:** Python 3.11, `conda activate ai`, pytest (`-p no:cacheprovider --timeout=45`). Reuses: `core.runtime.db_core.connect`, `core.services.central_private_observe.record_private`, `core.services.model_context.model_context_window`, `core.runtime.settings`. Deploy: ff-pull + restart `jarvis-runtime` & `jarvis-api` on `bs@10.0.0.39`.

**Conventions (verify once):** full-suite gate `python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal` (~20 min); known flakes (pass alone): `meta_learning`, `forgetting_engine`, `subagent_ecology`, `heartbeat_self_knowledge`, `workspace_bootstrap`. Every new `core/…` file needs `tests/test_<name>.py`. Commit trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

**Safety note:** model_trust starts EVERY model weak, so live behavior is unchanged at deploy — no model is trusted until it earns it. Sub-A instruction/config effects apply immediately (not shadow) but weak = today's instructions + only a *new additive* synthesis line, so it can only help.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `core/services/model_trust.py` (new) | Earned-trust store: `record_run_outcome`, `mark_run_degenerated`, `model_strength`, `set_pin`, `build_model_trust_surface`. Durable table. |
| `core/services/prompt_contract.py` (modify) | `_output_discipline_instruction(*, strength)` + wire it into the visible prompt near `_visible_capability_truth_instruction`@3489. |
| `core/context/auto_compact.py` + `core/runtime/settings.py` (modify) | model-window-aware compaction threshold. |
| `core/services/visible_runs.py` (modify) | mark degeneration at existing detection points + one `record_run_outcome` at finalize. |
| `apps/api/jarvis_api/routes/central_matrix.py` (modify) | `/central/model-trust` route. |
| `tests/test_*.py` | one per new/modified unit. |

---

## Task 1: model_trust — earned-trust core

**Files:**
- Create: `core/services/model_trust.py`
- Test: `tests/test_model_trust.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_model_trust.py
from core.services import model_trust as mt


def test_unknown_model_is_weak(isolated_runtime):
    assert mt.model_strength("brand-new-model") == "weak"


def test_promotes_after_threshold_clean_runs(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 3)
    for _ in range(3):
        mt.record_run_outcome("m1", degenerated=False)
    assert mt.model_strength("m1") == "strong"


def test_single_degeneration_reverts_strong_to_weak(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 2)
    mt.record_run_outcome("m2", degenerated=False)
    mt.record_run_outcome("m2", degenerated=False)          # now strong
    assert mt.model_strength("m2") == "strong"
    mt.record_run_outcome("m2", degenerated=True)           # one bad run
    assert mt.model_strength("m2") == "weak"


def test_degeneration_resets_streak(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 3)
    mt.record_run_outcome("m3", degenerated=False)
    mt.record_run_outcome("m3", degenerated=True)           # reset
    mt.record_run_outcome("m3", degenerated=False)
    mt.record_run_outcome("m3", degenerated=False)
    assert mt.model_strength("m3") == "weak"                # only 2 clean since reset


def test_owner_pin_overrides_earned(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 1)
    mt.record_run_outcome("m4", degenerated=False)          # earned strong
    mt.set_pin("m4", "weak")
    assert mt.model_strength("m4") == "weak"
    mt.set_pin("m4", "strong")
    assert mt.model_strength("m4") == "strong"
    mt.set_pin("m4", "auto")
    assert mt.model_strength("m4") == "strong"              # back to earned


def test_model_strength_fails_open_weak(monkeypatch):
    monkeypatch.setattr(mt, "connect", lambda: (_ for _ in ()).throw(RuntimeError("db")))
    assert mt.model_strength("x") == "weak"
```

- [ ] **Step 2: Run → FAIL** (module not found):
`python -m pytest tests/test_model_trust.py -q -p no:cacheprovider --timeout=45`

- [ ] **Step 3: Implement**

```python
# core/services/model_trust.py
"""Central-governed EARNED model-trust (harness refactor Part 1 foundation).

Every model starts WEAK (all safety nets on). The Central earns each one's trust from evidence:
20 consecutive CLEAN runs → auto-promote to STRONG; a SINGLE degeneration run → auto-revert to weak
+ reset the streak. No owner classification (the Central remembers). model_strength() is the single
downstream reader and FAILS OPEN to weak. Owner may pin a model (weak/strong/auto=default) but never
has to. Durable (survives restart). Self-safe throughout."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_PROMOTE_THRESHOLD = 20  # consecutive clean runs to earn strong


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS model_trust (
            model TEXT PRIMARY KEY,
            strength TEXT NOT NULL DEFAULT 'weak',
            clean_streak INTEGER NOT NULL DEFAULT 0,
            pin TEXT NOT NULL DEFAULT 'auto',
            last_degeneration_at TEXT NOT NULL DEFAULT '',
            promoted_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )"""
    )


def _row(conn: sqlite3.Connection, model: str) -> dict[str, Any]:
    r = conn.execute(
        "SELECT model, strength, clean_streak, pin, last_degeneration_at, promoted_at "
        "FROM model_trust WHERE model = ?", (model,)).fetchone()
    if r is None:
        return {"model": model, "strength": "weak", "clean_streak": 0, "pin": "auto",
                "last_degeneration_at": "", "promoted_at": ""}
    return dict(r)


def record_run_outcome(model: str, *, degenerated: bool) -> None:
    """Record one run's outcome for `model`. Clean → +1 streak (promote at threshold); degeneration
    → reset streak + revert to weak. Self-safe (never affects the run)."""
    model = str(model or "").strip()
    if not model:
        return
    try:
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            _ensure(conn)
            row = _row(conn, model)
            strength, streak = row["strength"], int(row["clean_streak"])
            promoted_at, last_deg = row["promoted_at"], row["last_degeneration_at"]
            if degenerated:
                strength, streak, last_deg = "weak", 0, now
            else:
                streak += 1
                if streak >= _PROMOTE_THRESHOLD and strength != "strong":
                    strength, promoted_at = "strong", now
            conn.execute(
                """INSERT INTO model_trust (model, strength, clean_streak, pin, last_degeneration_at, promoted_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(model) DO UPDATE SET
                     strength=excluded.strength, clean_streak=excluded.clean_streak,
                     last_degeneration_at=excluded.last_degeneration_at,
                     promoted_at=excluded.promoted_at, updated_at=excluded.updated_at""",
                (model, strength, streak, row["pin"], last_deg, promoted_at, now))
            conn.commit()
    except Exception:
        pass


def set_pin(model: str, pin: str) -> None:
    """Owner override: 'weak' | 'strong' | 'auto' (default). Self-safe."""
    if pin not in ("weak", "strong", "auto"):
        return
    try:
        with connect() as conn:
            _ensure(conn)
            conn.execute(
                "INSERT INTO model_trust (model, pin, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(model) DO UPDATE SET pin=excluded.pin, updated_at=excluded.updated_at",
                (str(model), pin, datetime.now(UTC).isoformat()))
            conn.commit()
    except Exception:
        pass


def model_strength(model: str) -> str:
    """'strong' | 'weak'. Pin wins; else earned strength. FAILS OPEN to 'weak'."""
    try:
        with connect() as conn:
            _ensure(conn)
            row = _row(conn, str(model or ""))
        pin = row.get("pin") or "auto"
        if pin in ("weak", "strong"):
            return pin
        return "strong" if row.get("strength") == "strong" else "weak"
    except Exception:
        return "weak"


def build_model_trust_surface() -> dict[str, object]:
    """Central-CLI view: per-model trust state. Self-safe."""
    try:
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT model, strength, clean_streak, pin, last_degeneration_at, promoted_at "
                "FROM model_trust ORDER BY strength DESC, clean_streak DESC").fetchall()
        return {"active": True, "threshold": _PROMOTE_THRESHOLD,
                "models": [dict(r) for r in rows]}
    except Exception:
        return {"active": True, "threshold": _PROMOTE_THRESHOLD, "models": []}
```

- [ ] **Step 4: Run → 6 PASS.**
- [ ] **Step 5: Commit** `feat(harness): earned model-trust store (weak→strong, auto-revert)`

---

## Task 2: /central/model-trust view

**Files:**
- Modify: `apps/api/jarvis_api/routes/central_matrix.py`
- Test: `tests/test_model_trust.py` (add a route-shape test)

- [ ] **Step 1: failing test** (append)

```python
def test_surface_shape(isolated_runtime, monkeypatch):
    monkeypatch.setattr(mt, "_PROMOTE_THRESHOLD", 1)
    mt.record_run_outcome("claude-x", degenerated=False)
    surf = mt.build_model_trust_surface()
    assert surf["active"] and surf["threshold"] == 1
    assert any(m["model"] == "claude-x" and m["strength"] == "strong" for m in surf["models"])
```

- [ ] **Step 2: Run → PASS** (builder already exists from Task 1; this just asserts the shape). If it passes immediately, that's fine — it's the contract the route depends on.

- [ ] **Step 3: Add the route.** In `central_matrix.py`, mirror a neighboring `/central/<x>` route (grep `def build_self_state_surface`-style routes; use the same `_safe(...)` wrapper pattern) to add `/central/model-trust` returning `build_model_trust_surface()`:

```python
        # ── model-trust (harness Part 1): per-model earned trust ──
        if action == "model-trust" or path.endswith("/model-trust"):
            from core.services.model_trust import build_model_trust_surface
            return _safe(build_model_trust_surface)
```
(Match the EXACT dispatch/return style of the routes already in that file — do not invent a new pattern. If routes are FastAPI decorators rather than an action-dispatch, add a decorated route mirroring a neighbor.)

- [ ] **Step 4: Verify** `python -c "import apps.api.jarvis_api.routes.central_matrix"` imports; test passes.
- [ ] **Step 5: Commit** `feat(harness): /central/model-trust view`

---

## Task 3: wire degeneration marks + record outcome in the agentic loop

**Files:**
- Modify: `core/services/visible_runs.py`
- Test: `tests/test_visible_runs_model_trust_wiring.py` (source-inspection — the loop is too heavy to execute)

**Context:** the degeneration signals already have detection points. We (a) set a per-run flag
`_run_degenerated = True` at each, and (b) call `record_run_outcome(run.model, degenerated=_run_degenerated)`
once where the run finalizes. Both guarded/self-safe. Keep touches minimal.

- [ ] **Step 1: failing test**

```python
# tests/test_visible_runs_model_trust_wiring.py
import inspect
from core.services import visible_runs as vr


def test_run_degenerated_flag_and_record_present():
    src = inspect.getsource(vr)
    assert "_run_degenerated" in src
    assert "record_run_outcome" in src
    assert "from core.services.model_trust import record_run_outcome" in src
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement.** In `_stream_visible_run`, initialize the flag once near the other loop
locals (e.g. just after `_agentic_round` budget setup, ~line 1965):
```python
                _run_degenerated = False  # harness model-trust: any degeneration event this run
```
Set it `True` (self-safe, additive) at each existing degeneration point — add this one line next to each:
- next to `_force_finalize_next = True` (no-progress, ~line 3624): `_run_degenerated = True`
- inside the hollow-promise nudge block (where `_hollow_promise_nudged = True` is set, ~3258): `_run_degenerated = True`
- where the tool-only cap forces summary / `_tool_pause_active = True` from the cap (~3326): `_run_degenerated = True`
- where an empty-text early-exit / cutoff is recorded (the `loop/empty_completion` and `stream/cutoff_at_loop_lag` observe points ~4144/4840): `_run_degenerated = True`

Then, at run finalize — where `_final_run_status` is settled at the end of the run (in the finally/
post-process path, alongside line 1183/1438 handling) — add one guarded call:
```python
                    try:
                        from core.services.model_trust import record_run_outcome
                        record_run_outcome(getattr(run, "model", "") or "",
                                           degenerated=bool(_run_degenerated))
                    except Exception:
                        pass
```
Place it where `run.model` and `_run_degenerated` are both in scope and the run is definitely ending
(once per run). Boy-Scout note: if the touch cluster is large, this is additive one-liners, not a
logic change — no extraction needed.

- [ ] **Step 4: Run the wiring test → PASS.** Also `python -m py_compile core/services/visible_runs.py`.
- [ ] **Step 5: Commit** `feat(harness): mark degeneration + record model-trust outcome in agentic loop`

---

## Task 4: tiered output-discipline instruction

**Files:**
- Modify: `core/services/prompt_contract.py`
- Test: `tests/test_prompt_output_discipline.py`

- [ ] **Step 1: failing test**

```python
# tests/test_prompt_output_discipline.py
from core.services.prompt_contract import _output_discipline_instruction


def test_both_tiers_get_synthesis():
    for s in ("weak", "strong"):
        t = _output_discipline_instruction(strength=s)
        assert "enough" in t.lower() and "synthes" in t.lower()


def test_strong_gets_conciseness_weak_does_not():
    strong = _output_discipline_instruction(strength="strong")
    weak = _output_discipline_instruction(strength="weak")
    assert "25 words" in strong and "100 words" in strong
    assert "25 words" not in weak and "100 words" not in weak


def test_self_safe_on_bad_input():
    assert isinstance(_output_discipline_instruction(strength="bogus"), str)
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement.** Add to `prompt_contract.py` (near the other instruction builders,
~line 3489):
```python
def _output_discipline_instruction(*, strength: str) -> str:
    """Tiered output discipline (harness Part 1). BOTH tiers get 'synthesize & stop'; STRONG also
    gets conciseness caps (would truncate weak lanes). Does NOT repeat the self-correction /
    tool-honesty blocks — those stay as their own sections. Self-safe."""
    lines = [
        "Output discipline:",
        "- After each tool result, consider: do I have enough to answer? If yes, synthesize your",
        "  findings and respond directly — do not keep calling tools when you already have the answer.",
        "- Finish your sentence with punctuation before a tool call — never cut off mid-word.",
        "- Tool results are for you — refer to them in your own words, never reproduce them verbatim.",
    ]
    if str(strength) == "strong":
        lines += [
            "- Go straight to the point. Try the simplest approach first without going in circles. Do not overdo it.",
            "- Keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task genuinely requires more.",
        ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run → 3 PASS.**

- [ ] **Step 5: Wire it into the visible prompt.** Find where `_visible_capability_truth_instruction`
is appended to the visible prompt (grep its call site). Append the new block right after, computing
strength from the run's model:
```python
        try:
            from core.services.model_trust import model_strength as _ms
            _od = _output_discipline_instruction(strength=_ms(getattr(run, "model", "") or ""))
        except Exception:
            _od = _output_discipline_instruction(strength="weak")
        # append _od to the same instruction section as _visible_capability_truth_instruction
```
(Match the exact assembly style at the call site — how the existing instruction string is added to
the section list. The self-correction block at 3275 is a SEPARATE section — leave it untouched.)

- [ ] **Step 6: Verify** the prompt-contract module imports; run the test file.
- [ ] **Step 7: Commit** `feat(harness): tiered output-discipline instruction (synthesis all, conciseness strong-only)`

---

## Task 5: model-window-aware compaction threshold

**Files:**
- Modify: `core/context/auto_compact.py`, `core/runtime/settings.py`
- Test: `tests/test_auto_compact_threshold.py`

- [ ] **Step 1: failing test**

```python
# tests/test_auto_compact_threshold.py
from core.context.auto_compact import _compaction_threshold


def test_large_window_compacts_at_70pct(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window", lambda p, m: 1_000_000)
    # 1M window → ~700k, not the flat ~192k
    assert _compaction_threshold(provider="deepseek", model="v4-flash", flat_fallback=192_000) == 700_000


def test_small_window_scales_down(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window", lambda p, m: 128_000)
    assert _compaction_threshold(provider="x", model="y", flat_fallback=192_000) == int(128_000 * 0.70)


def test_unknown_window_falls_back_flat(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window",
                        lambda p, m: (_ for _ in ()).throw(RuntimeError("unknown")))
    assert _compaction_threshold(provider="x", model="y", flat_fallback=192_000) == 192_000


def test_zero_window_falls_back_flat(monkeypatch):
    monkeypatch.setattr("core.context.auto_compact.model_context_window", lambda p, m: 0)
    assert _compaction_threshold(provider="x", model="y", flat_fallback=192_000) == 192_000
```

- [ ] **Step 2: Run → FAIL.**

- [ ] **Step 3: Implement.** In `auto_compact.py`, add the import + helper, and use it in
`maybe_auto_compact_session` where the current `threshold = int(settings.context_run_compact_threshold_tokens * _AUTO_COMPACT_PCT)`
is computed (line ~24):
```python
from core.services.model_context import model_context_window

_AUTO_COMPACT_WINDOW_PCT = 0.70


def _compaction_threshold(*, provider: str, model: str, flat_fallback: int) -> int:
    """Model-window-aware compaction threshold: window × 0.70. Falls back to flat_fallback when the
    window is unknown/zero. Self-safe."""
    try:
        window = int(model_context_window(provider, model) or 0)
        if window > 0:
            return int(window * _AUTO_COMPACT_WINDOW_PCT)
    except Exception:
        pass
    return int(flat_fallback)
```
Then at the call site, replace the flat computation with:
```python
        flat = int(settings.context_run_compact_threshold_tokens * _AUTO_COMPACT_PCT)
        threshold = _compaction_threshold(provider=<run provider>, model=<run model>, flat_fallback=flat)
```
(Use the provider/model already available in `maybe_auto_compact_session`'s scope — grep the fn
signature; if it doesn't receive them, thread them from the caller or read from the session's run
record. If provider/model aren't reachable there, keep `flat` — the fallback — and note it for a
follow-up; do NOT invent a lookup.)

- [ ] **Step 4: Run → 4 PASS.**
- [ ] **Step 5: Commit** `feat(harness): model-window-aware compaction threshold (window×0.70, flat fallback)`

---

## Task 6: full-suite gate + deploy

- [ ] **Step 1:** `python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal` (~20 min). Green modulo the known flakes (confirm each fails-alone-passes if any appear).
- [ ] **Step 2:** push origin main (pre-push runtime smoke test is slow — allow ≥250s).
- [ ] **Step 3:** deploy — on `bs@10.0.0.39`: `cd /media/projects/jarvis-v2; git fetch origin -q && git merge --ff-only origin/main; sudo systemctl restart jarvis-runtime jarvis-api; systemctl is-active jarvis-runtime jarvis-api`.
- [ ] **Step 4:** verify: journal has no new errors since restart; `jc raw /central/model-trust` returns `{active:true, threshold:20, models:[...]}` and every model shows `strength:"weak"` initially (behavior unchanged until one earns strong over ~20 clean runs).

---

## Notes for the executor
- **Nothing here touches the 7 coercion mechanisms.** They keep running; model_trust only *observes* their firing as degeneration signals.
- **Everything self-safe/fail-open to weak** — a model_trust failure must never affect a run.
- The visible_runs touches (Task 3) are additive one-liners at existing points + one finalize call — no logic change, no extraction. If any variable isn't in scope at a chosen point, pick the nearest point where it is; do not restructure the loop.
