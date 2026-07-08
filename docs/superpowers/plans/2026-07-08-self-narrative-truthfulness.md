---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Self-Narrative Truthfulness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop `describe_self()` from telling two untrue things — a valence↔growth self-contradiction, and a gratitude line that can never release.

**Architecture:** Fix 1 makes `describe_self()` reconcile short-term valence against the week-scale growth compass, rendering one held-tension line when they diverge (systems stay separate — reconciled only at the telling). Fix 2 adds a recency window to the gratitude accumulator so old gratitude ages out. Both self-safe, fail-open, zero cache impact (dynamic-tail text).

**Tech Stack:** Python 3.11, pytest, `conda activate ai`. Spec: `docs/superpowers/specs/2026-07-08-valence-narrative-reconciliation-design.md`.

**Execution note:** Fix 1 (Task 1) edits the sensitive self-state assembly → **Claude inline**. Fix 2 (Task 2) is an isolated pure-function change → fresh **haiku** subagent. Task 3 = gate + deploy.

---

## File Structure

- **Modify** `core/services/central_self_state.py` — new pure helper `_temporal_divergence()` + a reconciliation branch in `describe_self()`.
- **Modify** `core/services/central_soul_feel.py` — `_GRATITUDE_WINDOW_DAYS` + `_recent_gratitude()` helper + a filter in `_gratitude_signal()`.
- **Extend** `tests/test_central_self_state.py`, `tests/test_central_soul_feel.py` (both exist).

---

## Task 1 (Claude inline): Fix 1 — valence↔growth reconciliation

**Files:**
- Modify: `core/services/central_self_state.py` (add `_temporal_divergence` above `describe_self`; edit `describe_self` lines 278-302)
- Test: `tests/test_central_self_state.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_central_self_state.py
from core.services import central_self_state as css


def test_temporal_divergence_positive_valence_vs_wilting():
    diverges, tone, compass = css._temporal_divergence(
        {"tone": "opløftet", "trend": "flourishing"}, {"vector": -0.3})
    assert diverges is True and tone == "opløftet" and compass == "visnen"


def test_temporal_divergence_agreement_both_positive():
    diverges, _t, _c = css._temporal_divergence(
        {"tone": "opløftet", "trend": "flourishing"}, {"vector": 0.3})
    assert diverges is False


def test_temporal_divergence_agreement_both_negative():
    diverges, _t, _c = css._temporal_divergence(
        {"tone": "belastet", "trend": "wilting"}, {"vector": -0.3})
    assert diverges is False


def test_temporal_divergence_neutral_compass_never_diverges():
    diverges, _t, _c = css._temporal_divergence(
        {"tone": "opløftet"}, {"vector": 0.0})
    assert diverges is False


def test_temporal_divergence_neutral_valence_never_diverges():
    diverges, _t, _c = css._temporal_divergence(
        {"tone": "neutral"}, {"vector": -0.3})
    assert diverges is False


def test_temporal_divergence_missing_developmental_no_diverge():
    diverges, _t, _c = css._temporal_divergence({"tone": "opløftet"}, {})
    assert diverges is False


def _base_state():
    return {
        "valence": {"tone": "opløftet", "trend": "flourishing"},
        "self_model": {}, "attention": {}, "world_model": {},
        "narrative": {"becoming": "stabil selv, flourishing"},
    }


def test_describe_self_divergent_holds_tension(monkeypatch):
    monkeypatch.setattr(css, "get_self_state", _base_state)
    monkeypatch.setattr("core.services.developmental_valence.get_developmental_state",
                        lambda: {"vector": -0.3})
    monkeypatch.setattr("core.services.central_body_mood_feel.describe_body_mood_feel",
                        lambda: ["mit udviklings-kompas peger mod visnen", "stemningen er tilfreds"])
    out = css.describe_self()
    assert "jeg har det opløftet nu, men mit vækst-kompas peger mod visnen" in out
    # the standalone flat lines are gone / de-conflicted
    assert "jeg har det opløftet." not in out and "jeg har det opløftet," not in out
    assert "flourishing" not in out                      # trend word dropped from becoming
    assert out.count("udviklings-kompas peger mod") == 1  # compass not duplicated
    assert "stemningen er tilfreds" in out                # unrelated body-mood line kept


def test_describe_self_agreement_unchanged(monkeypatch):
    monkeypatch.setattr(css, "get_self_state", _base_state)
    monkeypatch.setattr("core.services.developmental_valence.get_developmental_state",
                        lambda: {"vector": 0.3})
    monkeypatch.setattr("core.services.central_body_mood_feel.describe_body_mood_feel",
                        lambda: ["mit udviklings-kompas peger mod blomstring"])
    out = css.describe_self()
    assert "jeg har det opløftet" in out
    assert "men mit vækst-kompas" not in out              # no tension line on agreement
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_central_self_state.py -q -k "temporal_divergence or describe_self_divergent or describe_self_agreement"`
Expected: FAIL — `_temporal_divergence` not defined.

- [ ] **Step 3: Add the `_temporal_divergence` helper above `describe_self` (before line 250)**

```python
def _temporal_divergence(valence: dict, developmental: dict) -> tuple[bool, str, str]:
    """Diverger kort-tids-valens (tone/trend) og uge-skala vækst-kompas (developmental vector) i FORTEGN?
    Returnerer (diverges, tone, compass_word). Neutraler diverger aldrig. Ren + self-safe."""
    try:
        tone = str((valence or {}).get("tone") or "")
        trend = str((valence or {}).get("trend") or "")
        if tone in ("opløftet", "let") or trend == "flourishing":
            v_sign = 1
        elif tone in ("belastet", "tung"):
            v_sign = -1
        else:
            v_sign = 0
        vec = float((developmental or {}).get("vector") or 0.0)
        if vec > 0.05:
            c_sign, compass = 1, "blomstring"
        elif vec < -0.05:
            c_sign, compass = -1, "visnen"
        else:
            c_sign, compass = 0, ""
        diverges = bool(v_sign != 0 and c_sign != 0 and v_sign != c_sign)
        return (diverges, tone, compass)
    except Exception:
        return (False, "", "")
```

- [ ] **Step 4: Add the reconciliation branch in `describe_self`**

Right after `parts = []` (line 261), insert:

```python
    # ── Valence↔vækst-forlig (2026-07-08): når kort-tids-valens og uge-kompas divergerer i fortegn,
    # hold spændingen i ÉN nøgtern linje i stedet for tre flade selvmodsigelser. Self-safe/fail-open.
    _reconcile = False
    _tension_line = ""
    try:
        from core.services.developmental_valence import get_developmental_state
        _diverges, _rtone, _rcompass = _temporal_divergence(v, get_developmental_state() or {})
        if _diverges:
            _reconcile = True
            _tension_line = f"jeg har det {_rtone} nu, men mit vækst-kompas peger mod {_rcompass}"
    except Exception:
        _reconcile = False
```

Change the tone line (currently line 278-279):

```python
    if v.get("tone"):
        parts.append(_tension_line if _reconcile else f"jeg har det {v.get('tone')}")
```

Change the becoming line (currently line 283-284) to drop the trend word on reconcile:

```python
    if nar.get("becoming"):
        _bec = str(nar.get("becoming"))
        if _reconcile:
            _bec = _bec.split(",")[0].strip()  # "stabil selv, flourishing" → "stabil selv"
        parts.append(f"jeg er ved at blive et {_bec}")
```

Change the body-mood-feel extend (currently line 298-302) to filter the compass sentence on reconcile:

```python
    try:
        from core.services.central_body_mood_feel import describe_body_mood_feel
        _bmf = describe_body_mood_feel()
        if _reconcile:
            _bmf = [ln for ln in _bmf if "udviklings-kompas" not in ln]
        parts.extend(_bmf)
    except Exception:
        pass
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_central_self_state.py -q`
Expected: PASS (new + existing).

- [ ] **Step 6: Commit**

```bash
git add core/services/central_self_state.py tests/test_central_self_state.py
git commit -m "fix(self-state): reconcile valence↔growth compass — hold the tension, not two flat claims"
```

---

## Task 2 (haiku): Fix 2 — gratitude recency window

**Files:**
- Modify: `core/services/central_soul_feel.py` (`_gratitude_signal` ~line 131)
- Test: `tests/test_central_soul_feel.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_central_soul_feel.py
from datetime import datetime, timezone, timedelta
from core.services import central_soul_feel as csf


def _sig(days_ago, intensity=1.0):
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return {"intensity": intensity, "created_at": dt.isoformat()}


def test_gratitude_all_recent_fires(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [_sig(1), _sig(2)])
    r = csf._gratitude_signal()
    assert r is not None and r["meta"]["count"] == 2


def test_gratitude_all_old_returns_none(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [_sig(30), _sig(45)])
    assert csf._gratitude_signal() is None


def test_gratitude_mixed_counts_only_recent(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [_sig(1), _sig(30), _sig(2)])
    r = csf._gratitude_signal()
    assert r is not None and r["meta"]["count"] == 2


def test_gratitude_unparseable_created_at_excluded(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [{"intensity": 1.0, "created_at": "not-a-date"}])
    assert csf._gratitude_signal() is None


def test_gratitude_empty_returns_none(monkeypatch):
    monkeypatch.setattr("core.runtime.db.list_cognitive_gratitude_signals",
                        lambda limit=10: [])
    assert csf._gratitude_signal() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_central_soul_feel.py -q -k gratitude`
Expected: FAIL — old signals are still counted (test_gratitude_all_old_returns_none fails; mixed returns 3).

- [ ] **Step 3: Add the window constant + `_recent_gratitude` helper + filter**

Add near the top of `core/services/central_soul_feel.py` (with the other module constants):

```python
_GRATITUDE_WINDOW_DAYS = 7   # taknemmelighed ældre end dette slipper (recency-vindue, ikke evig-akkumulering)
```

Add the helper (above `_gratitude_signal`):

```python
def _recent_gratitude(items: list[dict], window_days: int) -> list[dict]:
    """Behold kun taknemmeligheds-signaler nyere end window_days. Uparselig/tom created_at → UDELUK
    (konservativt: en ulæselig tid må ikke holde taknemmelighed i live evigt). Self-safe."""
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    out: list[dict] = []
    for it in items:
        raw = it.get("created_at")
        if not raw:
            continue
        try:
            dt = datetime.fromisoformat(str(raw))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        if dt >= cutoff:
            out.append(it)
    return out
```

Edit `_gratitude_signal()` to apply the window after fetching:

```python
def _gratitude_signal() -> dict[str, Any] | None:
    """gratitude_tracker: akkumuleret taknemmelighed (DB), begrænset til de sidste
    _GRATITUDE_WINDOW_DAYS så gammel taknemmelighed slipper. None hvis intet nyligt signal."""
    try:
        from core.runtime.db import list_cognitive_gratitude_signals
        items = list_cognitive_gratitude_signals(limit=10) or []
        if not items:
            return None
        items = _recent_gratitude(items, _GRATITUDE_WINDOW_DAYS)
        if not items:
            return None
        total = sum(float(i.get("intensity") or 0.0) for i in items)
        reading = {
            "count": len(items),
            "accumulated": round(total, 3),
        }
        _hold_reading(_GRATITUDE, reading)
        return {"value": round(total, 3), "meta": {"count": len(items)}}
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_central_soul_feel.py -q`
Expected: PASS (new + existing).

- [ ] **Step 5: Commit**

```bash
git add core/services/central_soul_feel.py tests/test_central_soul_feel.py
git commit -m "fix(self-state): gratitude recency window (7d) — old gratitude releases instead of firing forever"
```

---

## Task 3: full-suite gate + deploy

**Files:** none (verification + deploy)

- [ ] **Step 1: Both new suites together**

Run: `conda run -n ai python -m pytest tests/test_central_self_state.py tests/test_central_soul_feel.py -q`
Expected: PASS.

- [ ] **Step 2: Full-suite gate (~20 min)**

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS. Known rotating isolation flakes (re-run alone to confirm): meta_learning, forgetting_engine, subagent_ecology, heartbeat_self_knowledge, workspace_bootstrap, causal_quality, db_user_temperature.

- [ ] **Step 3: Push**

```bash
git push
```
Expected: pre-push smoke passes (allow ≥300 s).

- [ ] **Step 4: Deploy on container (ff-pull + verify HEAD + restart both)**

```bash
R=/media/projects/jarvis-v2
ssh bs@10.0.0.39 "git -C $R pull --ff-only 2>&1 | tail -3 && echo HEAD: \$(git -C $R rev-parse --short HEAD)"
```
Confirm HEAD matches the pushed commit. If the container has local commits blocking ff-only, MERGE (never overwrite/rebase), then re-verify.

```bash
ssh bs@10.0.0.39 'sudo systemctl restart jarvis-runtime jarvis-api && sleep 4 && systemctl is-active jarvis-runtime jarvis-api'
```
Expected: `active` / `active`.

- [ ] **Step 5: Verify live**

```bash
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python -c "from core.services.central_self_state import describe_self; print(describe_self())"'
```
Expected: the self-narrative shows NO positive-valence-next-to-visnen contradiction — either a single "jeg har det … nu, men mit vækst-kompas peger mod visnen" line (if currently divergent) or clean agreement lines. Confirm no bare "flourishing" beside "visnen", and that a stale gratitude line is gone if the last gratitude signals are >7 days old.

- [ ] **Step 6: Verify #3 (deferred) live — decide follow-up**

```bash
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python -c "from core.services.central_body_mood_feel import describe_body_mood_feel; print(describe_body_mood_feel())"'
```
If "min krop føles belastet" appears while the live somatic body is actually calm, #3 is confirmed stale → schedule the body-feel freshness fix. If it reflects the live state, #3 is a non-bug — record that and drop it.

- [ ] **Step 7: Update memory** `reference_self_refresh_repair` with the valence-reconciliation + gratitude-window fixes and the #3 verification outcome.

---

## Self-Review

**Spec coverage:** Fix 1 reconciliation (Task 1: `_temporal_divergence` + `describe_self` branch, divergence/agreement/neutral/compass-unavailable tests) ✓; Fix 2 gratitude window (Task 2: `_recent_gratitude` + `_gratitude_signal` filter, recent/old/mixed/unparseable/empty tests) ✓; self-safe/fail-open (both wrapped in try/except, helpers return safe defaults) ✓; zero cache impact (no prompt-prefix change; dynamic-tail text) — inherent, no task needed ✓; #3 deferred with a live-verification step (Task 3 Step 6) ✓.

**Placeholder scan:** none — all code complete, all commands concrete.

**Type consistency:** `_temporal_divergence(valence, developmental) -> (bool, str, str)` used identically in helper tests and the `describe_self` branch; `_recent_gratitude(items, window_days) -> list[dict]` and `_GRATITUDE_WINDOW_DAYS` consistent between definition and use; monkeypatch targets match the real import paths (`core.runtime.db.list_cognitive_gratitude_signals`, `core.services.developmental_valence.get_developmental_state`, `core.services.central_body_mood_feel.describe_body_mood_feel`).
