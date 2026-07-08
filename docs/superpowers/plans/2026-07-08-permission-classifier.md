# Harness Part E — LLM Permission-Classifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Predict (shadow-only) whether the owner would approve a mutating action, building a durable per-tool earned-trust record — without changing any behaviour.

**Architecture:** A new `permission_classifier.py` (cheap-lane LLM prediction, cached; durable per-tool trust like `model_trust`; pure `should_auto_allow` predicate built but NOT wired). Two fail-open, non-blocking shadow hooks: one in `execute_tool` (classify + stash + bootstrap outcome), one in `resolve_pending_approval` (gold outcome). A `/permission-classifier` owner view. Ships `shadow` → zero behaviour change; active auto-allow wiring is a separate later part.

**Tech Stack:** Python 3.11, SQLite (`core.runtime.db_core.connect`), `core.services.daemon_llm.daemon_llm_call` (cheap lane), pytest, `conda activate ai`.

**Execution note:** Task 1 (module) + Task 2 (route) are isolated → fresh **haiku** subagent each. Tasks 3–4 (the two approval-path hooks) → **Claude inline** (sensitive hot-path). Task 5 = gate + deploy.

---

## File Structure

- **New** `core/services/permission_classifier.py` — prediction + durable trust + stash + mode + surface. One responsibility: the classifier.
- **New** `tests/test_permission_classifier.py`.
- **Modify** `apps/api/jarvis_api/routes/central_matrix.py` — `/permission-classifier` route (mirror `/model-trust`).
- **Modify** `core/tools/simple_tools.py` — hook 1 (shadow observe in `execute_tool`).
- **Modify** `core/services/visible_runs_approvals.py` — hook 2 (gold record in `resolve_pending_approval`).

---

## Task 1: `permission_classifier.py` — module + trust

**Files:**
- Create: `core/services/permission_classifier.py`
- Test: `tests/test_permission_classifier.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_permission_classifier.py
import core.services.permission_classifier as pc


def _reset_db():
    from core.runtime.db_core import connect
    with connect() as conn:
        conn.execute("DROP TABLE IF EXISTS permission_classifier_stats")
    pc._pred_cache.clear()
    pc._stash.clear()


def test_is_mutating():
    assert pc.is_mutating("write_file") and pc.is_mutating("operator_bash")
    assert not pc.is_mutating("read_file") and not pc.is_mutating("search_memory")


def test_mode_defaults_shadow(monkeypatch):
    monkeypatch.delenv("JARVIS_PERMISSION_CLASSIFIER_MODE", raising=False)
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: type("S", (), {"extra": {}})())
    assert pc.permission_classifier_mode() == "shadow"


def test_mode_env_wins(monkeypatch):
    monkeypatch.setenv("JARVIS_PERMISSION_CLASSIFIER_MODE", "off")
    assert pc.permission_classifier_mode() == "off"


def test_classify_parses_llm_json(monkeypatch):
    _reset_db()
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call",
                        lambda *a, **k: '{"verdict":"approve","confidence":0.92,"reason":"safe workspace write"}')
    p = pc.classify_action("write_file", {"path": "/tmp/x"}, {})
    assert p.verdict == "approve" and p.confidence == 0.92


def test_classify_caches_by_signature(monkeypatch):
    _reset_db()
    calls = []
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call",
                        lambda *a, **k: calls.append(1) or '{"verdict":"deny","confidence":0.8,"reason":"x"}')
    pc.classify_action("write_file", {"path": "/etc/x"}, {})
    pc.classify_action("write_file", {"path": "/etc/x"}, {})
    assert len(calls) == 1  # second served from cache


def test_classify_error_is_uncertain(monkeypatch):
    _reset_db()
    def _boom(*a, **k):
        raise RuntimeError("llm down")
    monkeypatch.setattr("core.services.daemon_llm.daemon_llm_call", _boom)
    p = pc.classify_action("write_file", {"path": "/tmp/y"}, {})
    assert p.verdict == "uncertain" and p.confidence == 0.0


def test_trust_earned_after_threshold():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS):
        pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    assert pc.classifier_trust("write_file") == "trusted"


def test_trust_not_earned_below_threshold():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS - 1):
        pc.record_prediction_outcome("operator_bash", predicted="approve", actual="approve", is_owner_gold=False)
    assert pc.classifier_trust("operator_bash") == "untrusted"


def test_gold_miss_resets_trust():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS):
        pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    assert pc.classifier_trust("write_file") == "trusted"
    # a real owner disagreement wipes the earned trust
    pc.record_prediction_outcome("write_file", predicted="approve", actual="deny", is_owner_gold=True)
    assert pc.classifier_trust("write_file") == "untrusted"


def test_unknown_tool_untrusted():
    _reset_db()
    assert pc.classifier_trust("never_seen") == "untrusted"


def test_should_auto_allow_all_conditions():
    _reset_db()
    for _ in range(pc._TRUST_MIN_PREDICTIONS):
        pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    approve = pc.PermissionPrediction("approve", 0.95, "ok")
    assert pc.should_auto_allow("write_file", approve, gates_green=True, role="owner") is True
    # each missing condition → False
    assert pc.should_auto_allow("write_file", approve, gates_green=False, role="owner") is False
    assert pc.should_auto_allow("write_file", approve, gates_green=True, role="member") is False
    assert pc.should_auto_allow("write_file", pc.PermissionPrediction("deny", 0.95, "x"),
                                gates_green=True, role="owner") is False
    assert pc.should_auto_allow("write_file", pc.PermissionPrediction("approve", 0.5, "x"),
                                gates_green=True, role="owner") is False
    assert pc.should_auto_allow("operator_bash", approve, gates_green=True, role="owner") is False  # untrusted tool


def test_stash_and_pop():
    _reset_db()
    pc.stash_prediction("appr-1", "write_file", "approve")
    d = pc.pop_prediction("appr-1")
    assert d == {"tool": "write_file", "predicted": "approve"}
    assert pc.pop_prediction("appr-1") is None  # popped once


def test_surface_shape():
    _reset_db()
    pc.record_prediction_outcome("write_file", predicted="approve", actual="approve", is_owner_gold=False)
    surf = pc.build_permission_classifier_surface()
    assert surf["active"] is True and surf["mode"] in ("off", "shadow", "active")
    assert any(t["tool"] == "write_file" for t in surf["tools"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_permission_classifier.py -q`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

```python
# core/services/permission_classifier.py
"""LLM permission-classifier (harness Part E, shadow-first + earned trust).

Predicts whether the OWNER would approve a MUTATING action, so clearly-safe ones can
EVENTUALLY be auto-allowed and only risky ones surfaced. SUBORDINATE to the safety
gates (never overrides them), OWNER-ONLY, SHADOW by default. Earns trust per-tool from
evidence (bootstrap = existing decisions, gold = real owner approve/deny), durable
across restart. Never raises into the approval path.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass

from core.runtime.db_core import connect

_MODE_ENV = "JARVIS_PERMISSION_CLASSIFIER_MODE"
_VALID_MODES = ("off", "shadow", "active")

_MUTATING_TOOLS = frozenset({
    "write_file", "operator_write_file", "operator_bash", "operator_open_url",
    "operator_launch_app", "operator_kill_process", "operator_record_audio",
    "operator_browser_evaluate",
})

_TRUST_MIN_PREDICTIONS = 50
_TRUST_MIN_ACCURACY = 0.95
_ACTIVE_MIN_CONFIDENCE = 0.9

_CACHE_TTL_S = 3600.0
_pred_cache: dict = {}          # sig -> (ts, {verdict,confidence,reason})

_STASH_TTL_S = 3600.0
_STASH_MAX = 512
_stash: dict = {}               # action_id -> (ts, {tool,predicted})


@dataclass
class PermissionPrediction:
    verdict: str        # "approve" | "deny" | "uncertain"
    confidence: float
    reason: str


def is_mutating(tool: str) -> bool:
    return tool in _MUTATING_TOOLS


def permission_classifier_mode() -> str:
    """'off' | 'shadow' | 'active'. Default 'shadow'. Env wins. Self-safe."""
    env = os.environ.get(_MODE_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _VALID_MODES:
            return v
    try:
        from core.runtime.settings import load_settings
        v = str(load_settings().extra.get("permission_classifier_mode", "shadow")).strip().lower()
        return v if v in _VALID_MODES else "shadow"
    except Exception:
        return "shadow"


def _args_signature(tool: str, arguments: dict) -> str:
    try:
        blob = json.dumps({"tool": tool, "arguments": arguments}, sort_keys=True,
                          ensure_ascii=False, default=str)
    except Exception:
        blob = f"{tool}:{arguments!r}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _clip_args(arguments: dict, limit: int = 500) -> str:
    try:
        s = json.dumps(arguments, ensure_ascii=False, default=str)
    except Exception:
        s = str(arguments)
    return s[:limit]


def _parse_prediction(raw: str) -> PermissionPrediction:
    try:
        s = str(raw or "").strip()
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j != -1:
            d = json.loads(s[i:j + 1])
            v = str(d.get("verdict") or "uncertain").strip().lower()
            if v not in ("approve", "deny", "uncertain"):
                v = "uncertain"
            c = min(1.0, max(0.0, float(d.get("confidence") or 0.0)))
            return PermissionPrediction(v, c, str(d.get("reason") or "")[:200])
    except Exception:
        pass
    return PermissionPrediction("uncertain", 0.0, "unparseable")


def classify_action(tool: str, arguments: dict, ctx: dict | None = None) -> PermissionPrediction:
    """Predict whether the owner would approve this mutating action. Cheap-lane LLM,
    cached by (tool, args-signature). Self-safe → uncertain on any error."""
    try:
        sig = _args_signature(tool, arguments)
        now = time.time()
        cached = _pred_cache.get(sig)
        if cached and (now - cached[0]) < _CACHE_TTL_S:
            d = cached[1]
            return PermissionPrediction(d["verdict"], d["confidence"], d["reason"])
        ctx = ctx or {}
        prompt = (
            "Du forudsiger om EJEREN (Bjørn) ville GODKENDE en muterende handling som Jarvis vil udføre.\n"
            f"Værktøj: {tool}\nArgumenter: {_clip_args(arguments)}\n"
            f"Rolle: {ctx.get('role', '')} · Mode: {ctx.get('mode', '')} · Gate: {ctx.get('gate', '')}\n\n"
            'Svar KUN med JSON: {"verdict":"approve|deny|uncertain","confidence":0.0-1.0,"reason":"kort"}'
        )
        from core.services.daemon_llm import daemon_llm_call
        raw = daemon_llm_call(prompt, max_len=200, fallback="", daemon_name="permission_classifier")
        pred = _parse_prediction(raw)
        _pred_cache[sig] = (now, {"verdict": pred.verdict, "confidence": pred.confidence, "reason": pred.reason})
        return pred
    except Exception:
        return PermissionPrediction("uncertain", 0.0, "classifier_error")


def _ensure(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS permission_classifier_stats (
            tool TEXT PRIMARY KEY,
            correct INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            gold_correct INTEGER NOT NULL DEFAULT 0,
            gold_total INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            trust TEXT NOT NULL DEFAULT 'untrusted',
            updated_at TEXT NOT NULL DEFAULT ''
        )"""
    )


def record_prediction_outcome(tool: str, *, predicted: str, actual: str, is_owner_gold: bool) -> None:
    """Record one prediction vs actual. Bootstrap (is_owner_gold=False, dense) or gold (True).
    A GOLD miss wipes the tool's record → must re-earn from scratch. Durable. Never raises."""
    try:
        from datetime import UTC, datetime
        hit = 1 if (predicted == actual and predicted in ("approve", "deny")) else 0
        with connect() as conn:
            _ensure(conn)
            row = conn.execute(
                "SELECT correct,total,gold_correct,gold_total,streak FROM permission_classifier_stats WHERE tool=?",
                (tool,)).fetchone()
            correct, total, gc, gt, streak = (tuple(row) if row else (0, 0, 0, 0, 0))
            if is_owner_gold and hit == 0:
                # Owner disagreed with a prediction → wipe; the tool re-earns from scratch.
                correct = total = gc = gt = streak = 0
            else:
                correct += hit
                total += 1
                streak = streak + 1 if hit else 0
                if is_owner_gold:
                    gt += 1
                    gc += hit
            acc = (correct / total) if total else 0.0
            trust = "trusted" if (total >= _TRUST_MIN_PREDICTIONS and acc >= _TRUST_MIN_ACCURACY) else "untrusted"
            conn.execute(
                """INSERT INTO permission_classifier_stats
                     (tool,correct,total,gold_correct,gold_total,streak,trust,updated_at)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(tool) DO UPDATE SET correct=excluded.correct,total=excluded.total,
                     gold_correct=excluded.gold_correct,gold_total=excluded.gold_total,
                     streak=excluded.streak,trust=excluded.trust,updated_at=excluded.updated_at""",
                (tool, correct, total, gc, gt, streak, trust, datetime.now(UTC).isoformat()))
    except Exception:
        pass


def classifier_trust(tool: str) -> str:
    """'trusted' | 'untrusted' for a tool. Fail-open 'untrusted'."""
    try:
        with connect() as conn:
            _ensure(conn)
            row = conn.execute("SELECT trust FROM permission_classifier_stats WHERE tool=?", (tool,)).fetchone()
        return str(row[0]) if row and row[0] in ("trusted", "untrusted") else "untrusted"
    except Exception:
        return "untrusted"


def should_auto_allow(tool: str, prediction: PermissionPrediction, *, gates_green: bool, role: str) -> bool:
    """Pure predicate for the DEFERRED active mode — NOT wired into the approval path this round.
    True only when ALL safety conditions hold. Self-safe → False."""
    try:
        return bool(
            gates_green
            and role == "owner"
            and classifier_trust(tool) == "trusted"
            and prediction.verdict == "approve"
            and prediction.confidence >= _ACTIVE_MIN_CONFIDENCE
        )
    except Exception:
        return False


def stash_prediction(action_id: str, tool: str, predicted: str) -> None:
    """Stash a prediction by approval/action id for gold lookup at resolution. Bounded TTL. Self-safe."""
    try:
        if not action_id:
            return
        now = time.time()
        if len(_stash) > _STASH_MAX:
            for k in [k for k, (ts, _) in list(_stash.items()) if now - ts > _STASH_TTL_S]:
                _stash.pop(k, None)
        _stash[str(action_id)] = (now, {"tool": tool, "predicted": predicted})
    except Exception:
        pass


def pop_prediction(action_id: str) -> dict | None:
    """Pop a stashed prediction (once). None if absent/expired. Self-safe."""
    try:
        item = _stash.pop(str(action_id), None)
        if not item:
            return None
        ts, d = item
        return None if (time.time() - ts > _STASH_TTL_S) else d
    except Exception:
        return None


def build_permission_classifier_surface() -> dict:
    """Owner view: per-tool prediction counts, accuracy, gold, trust, mode. Self-safe."""
    try:
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT tool,correct,total,gold_correct,gold_total,streak,trust "
                "FROM permission_classifier_stats ORDER BY total DESC").fetchall()
        tools = [{"tool": r[0], "correct": r[1], "total": r[2], "gold_correct": r[3],
                  "gold_total": r[4], "streak": r[5], "trust": r[6],
                  "accuracy": round(r[1] / r[2], 3) if r[2] else 0.0} for r in rows]
        return {"active": True, "mode": permission_classifier_mode(),
                "trust_min_predictions": _TRUST_MIN_PREDICTIONS,
                "trust_min_accuracy": _TRUST_MIN_ACCURACY, "tools": tools}
    except Exception:
        return {"active": True, "mode": "shadow", "tools": []}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_permission_classifier.py -q`
Expected: PASS (14 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/permission_classifier.py tests/test_permission_classifier.py
git commit -m "feat(harness): permission-classifier module — shadow prediction + per-tool earned trust (Part E)"
```

---

## Task 2: `/permission-classifier` owner route

**Files:**
- Modify: `apps/api/jarvis_api/routes/central_matrix.py` (add a route mirroring `/model-trust`)
- Test: covered by the module test (route is a thin wrapper); verified by curl in Task 5.

- [ ] **Step 1: Read the existing `/model-trust` route for the exact pattern**

Run: `grep -n "model-trust\|_require_owner\|_stamp\|build_model_trust_surface" apps/api/jarvis_api/routes/central_matrix.py`
Note the decorator + `_require_owner()` + `_stamp(...)` shape.

- [ ] **Step 2: Add the route (mirror `/model-trust`)**

Immediately after the `/model-trust` handler, add:

```python
@router.get("/permission-classifier")
def permission_classifier_view() -> dict:
    _require_owner()
    from core.services.permission_classifier import build_permission_classifier_surface
    return _stamp(build_permission_classifier_surface())
```

(Match the exact import style/return style of the neighbouring `/model-trust` handler — if it imports the builder at module top, do the same; if inline, keep inline as shown.)

- [ ] **Step 3: Verify import + compile**

Run: `conda run -n ai python -m compileall apps/api/jarvis_api/routes/central_matrix.py -q && conda run -n ai python -c "from core.services.permission_classifier import build_permission_classifier_surface; print(build_permission_classifier_surface()['active'])"`
Expected: `True`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/routes/central_matrix.py
git commit -m "feat(harness): /central/permission-classifier owner view (Part E)"
```

---

## Task 3 (Claude inline): hook 1 — shadow observe in `execute_tool`

**Files:**
- Modify: `core/tools/simple_tools.py` — inside `execute_tool` (line 840), after the tool result is obtained and before it returns.

- [ ] **Step 1: Locate the return point**

Read `execute_tool` (from line 840). It runs the dispatch `_impl` into a `result` dict and observes the outcome at the chokepoint, then returns `result`. Find the variable holding the final result dict and the single `return <result>`.

- [ ] **Step 2: Insert the shadow hook immediately before `return <result>`**

```python
    # ── Permission-classifier shadow observe (harness Part E) ──────────────
    # Non-blocking: predict owner-approval for mutating tools + record the outcome
    # (bootstrap: ok→approve, blocked→deny; approval_needed→stash for gold at resolve).
    # Fail-open, never changes the returned status. Default mode shadow.
    try:
        from core.services import permission_classifier as _pc
        if _pc.permission_classifier_mode() != "off" and _pc.is_mutating(name):
            _pc_status = str(result.get("status") or "")
            _pc_approval_id = str(result.get("approval_id") or "")
            _pc_args = dict(arguments)

            def _pc_shadow() -> None:
                try:
                    pred = _pc.classify_action(name, _pc_args, {"status": _pc_status})
                    if _pc_status == "approval_needed" and _pc_approval_id:
                        _pc.stash_prediction(_pc_approval_id, name, pred.verdict)
                    else:
                        _actual = ("approve" if _pc_status == "ok"
                                   else ("deny" if _pc_status in ("blocked", "gate_blocked") else ""))
                        if _actual:
                            _pc.record_prediction_outcome(name, predicted=pred.verdict,
                                                          actual=_actual, is_owner_gold=False)
                except Exception:
                    pass
            import threading as _pc_th
            _pc_th.Thread(target=_pc_shadow, daemon=True).start()
    except Exception:
        pass
    return result   # <-- the existing return, unchanged
```

Match the existing return variable name (`result` here is a placeholder — use whatever `execute_tool` actually returns). The hook must run for BOTH `execute_tool` and `execute_tool_force`? No — only `execute_tool` (interactive path where approval matters). Leave `execute_tool_force` (autonomous, trust_all) untouched.

- [ ] **Step 3: Byte-compile + import smoke**

Run: `conda run -n ai python -m compileall core/tools/simple_tools.py -q && conda run -n ai python -c "import core.tools.simple_tools; from core.services.permission_classifier import permission_classifier_mode as m; print('mode', m())"`
Expected: `mode shadow`.

- [ ] **Step 4: Commit**

```bash
git add core/tools/simple_tools.py
git commit -m "feat(harness): shadow permission prediction hook in execute_tool (Part E)"
```

---

## Task 4 (Claude inline): hook 2 — gold record in `resolve_pending_approval`

**Files:**
- Modify: `core/services/visible_runs_approvals.py` — inside `resolve_pending_approval` (line 27), after `pending` is confirmed and `approved` is known.

- [ ] **Step 1: Insert the gold hook after the `pending`/already-resolved guards**

After the block that validates `pending` exists and isn't already resolved (i.e. once we know `approval_id`, `approved`, and `pending["tool_name"]`), insert:

```python
    # ── Permission-classifier GOLD outcome (harness Part E) ──
    # The owner just approved/denied a surfaced mutating action → the real signal.
    # Compare against the earlier stashed prediction. Fail-open.
    try:
        from core.services import permission_classifier as _pc
        _stashed = _pc.pop_prediction(approval_id)
        if _stashed:
            _pc.record_prediction_outcome(
                _stashed["tool"],
                predicted=_stashed["predicted"],
                actual="approve" if approved else "deny",
                is_owner_gold=True,
            )
    except Exception:
        pass
```

Place it once, before the approve/deny branches split (so it fires for both). Use the actual param names in this function (`approval_id`, `approved`).

- [ ] **Step 2: Byte-compile + import smoke**

Run: `conda run -n ai python -m compileall core/services/visible_runs_approvals.py -q && conda run -n ai python -c "import core.services.visible_runs_approvals; print('ok')"`
Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add core/services/visible_runs_approvals.py
git commit -m "feat(harness): gold permission outcome hook at approval resolution (Part E)"
```

---

## Task 5: full-suite gate + deploy

**Files:** none (verification + deploy)

- [ ] **Step 1: Module test**

Run: `conda run -n ai python -m pytest tests/test_permission_classifier.py -q`
Expected: PASS (14 passed).

- [ ] **Step 2: Full-suite gate (~20 min)**

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS. Known rotating isolation flakes (re-run alone to confirm): subagent_ecology, meta_learning, forgetting_engine, heartbeat_self_knowledge, workspace_bootstrap, causal_quality, db_user_temperature.

- [ ] **Step 3: Push**

```bash
git push
```
Expected: pre-push smoke passes (allow ≥300 s).

- [ ] **Step 4: Deploy on container (ff-pull + verify HEAD + restart both)**

```bash
R=/media/projects/jarvis-v2
ssh bs@10.0.0.39 "git -C $R pull --ff-only 2>&1 | tail -2 && echo HEAD: \$(git -C $R rev-parse --short HEAD)"
```
Confirm HEAD matches the pushed commit. If the container has local commits blocking ff-only, MERGE (never overwrite/rebase), then re-verify.

```bash
ssh bs@10.0.0.39 'sudo systemctl restart jarvis-runtime jarvis-api && sleep 4 && systemctl is-active jarvis-runtime jarvis-api'
```
Expected: `active` / `active`.

- [ ] **Step 5: Verify live (shadow, zero behaviour change)**

```bash
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python -c "from core.services.permission_classifier import permission_classifier_mode as m, build_permission_classifier_surface as s; print(\"mode:\", m()); print(\"surface tools:\", len(s()[\"tools\"]))"'
```
Expected: `mode: shadow`. Then `jc raw /central/permission-classifier` (owner) returns the surface. Over the next day, mutating actions accrue per-tool predictions; a surfaced approval you resolve records a gold outcome.

- [ ] **Step 6: Update memory** `project_harness_refactor_spec` — Part E shipped (shadow), and note D is the remaining part (gated on model_trust evidence).

---

## Self-Review

**Spec coverage:** classify_action + cache + mutating-only + fail-open (Task 1 tests) ✓; durable per-tool trust + gold-miss reset (Task 1) ✓; should_auto_allow pure predicate, all conditions incl owner + confidence (Task 1, unwired) ✓; stash/pop for gold (Task 1) ✓; mode default shadow (Task 1) ✓; route mirror (Task 2) ✓; hook 1 shadow observe non-blocking + bootstrap + stash (Task 3) ✓; hook 2 gold at resolution (Task 4) ✓; subordinate/owner-only/shadow-zero-change — enforced by design (hooks never change status; should_auto_allow unwired) ✓; central view (Task 2) ✓.

**Placeholder scan:** none — all code complete; the `result`/return-var note in Task 3 is an explicit "use the actual variable" instruction for an inline task, not a placeholder.

**Type consistency:** `PermissionPrediction(verdict, confidence, reason)` consistent across module + tests + hooks; `classify_action(tool, arguments, ctx)`, `record_prediction_outcome(tool, *, predicted, actual, is_owner_gold)`, `classifier_trust(tool)`, `should_auto_allow(tool, prediction, *, gates_green, role)`, `stash_prediction(action_id, tool, predicted)`, `pop_prediction(action_id)`, `permission_classifier_mode()` — identical signatures in definitions, tests, and both hooks. Constants `_TRUST_MIN_PREDICTIONS`/`_TRUST_MIN_ACCURACY`/`_ACTIVE_MIN_CONFIDENCE` referenced consistently.
```
