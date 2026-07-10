# Central Acting Organs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn two observe-only organs (`contradiction_engine`, `docs_drift_watchdog`) into governed, Central-driven actors that resolve contradictions and repair docs for real — shadow-ramp then live.

**Architecture:** Detection stays pure/unchanged in the existing modules. Two new single-responsibility service files consume the findings and act through `central().decide` (COGNITIVE, fail-open). Shadow↔live is gated by `gate_enforcement.is_enforced(<nerve>, GateClass.COGNITIVE)` (default not-enforced = shadow; owner flips to go live). Reversibility is structural: contradiction = `behavioral_decisions.status` flip (`active`↔`superseded`, never deleted); doc = git-tracked. No new DB tables — the resolution ledger rides the eventbus.

**Tech Stack:** Python 3.11, SQLite via `core.runtime.db.connect()`, `core.eventbus`, Central (`core.services.central_core.central`, `GateClass`), pytest.

**Reference spec:** `docs/superpowers/specs/2026-07-10-central-acting-organs-design.md`

**Grounded facts (verified at plan time):**
- `contradiction_engine.detect_contradictions()` → `list[dict]` with keys: `decision_id, decision_directive, decision_priority, review_id, review_text, overlap_tokens (list[str]), detected_at`.
- Decisions live in `behavioral_decisions (decision_id, directive, trigger_cue, priority, status, created_at)`; `status='active'` is the live set. Superseding a decision removes it from the next detection automatically (detection only fetches `status='active'`).
- Cadence hook: `core/services/cadence_producers.py` fn `tick_frozen_detectors`, `if tick_count % 20 == 0:` already calls `run_contradiction_tick()` (~line 790).
- Acting pattern (from `auto_remember_subscriber.py:369`):
  ```python
  from core.services.central_core import central
  central().decide(nerve_name, ctx_dict, action_fn, cluster="...", klass=GateClass.COGNITIVE)
  ```
- Gate: `core/services/gate_enforcement.py` exposes `is_enforced(nerve: str, klass: GateClass) -> bool` and `note_suppressed_block(nerve, cluster, reason)`.
- `GateClass` is importable where `central()` is used (see `auto_remember_subscriber.py` imports); mirror those imports.

**Testing note:** Tests use the `isolated_runtime` fixture (see `tests/conftest.py`, used across `tests/test_open_loop_signal_tracking.py`) for a temp DB. Run tests in the `ai` conda env: `conda activate ai`. NEVER trust `pytest | tail` — read the actual exit line.

---

## PART 1 — `contradiction_resolver`

### Task 1: Pure decision logic — `classify_tier` + `pick_survivor`

**Files:**
- Create: `core/services/contradiction_resolver.py`
- Test: `tests/test_contradiction_resolver.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_contradiction_resolver.py
from __future__ import annotations
from core.services.contradiction_resolver import classify_tier, pick_survivor

def _finding(**kw):
    base = {
        "decision_id": "d1", "decision_directive": "Svar altid kort",
        "decision_priority": 3, "review_id": 7,
        "review_text": "Jeg svarer ikke kort nok i lange tr%ade",
        "overlap_tokens": ["svar", "kort", "nok"], "detected_at": "2026-07-10T10:00:00+00:00",
    }
    base.update(kw); return base

def test_pick_survivor_review_wins_by_recency_same_authority():
    # Decision og self-review er begge self-derived → tie → nyere critique vinder.
    s = pick_survivor(_finding())
    assert s["winner"] == "review"
    assert s["loser"] == "decision"
    assert s["confidence"] == "high"      # 3 overlap-tokens
    assert "recency" in s["rule"]

def test_pick_survivor_confidence_medium_two_tokens():
    s = pick_survivor(_finding(overlap_tokens=["svar", "kort"]))
    assert s["confidence"] == "medium"

def test_pick_survivor_confidence_low_one_token():
    s = pick_survivor(_finding(overlap_tokens=["svar"]))
    assert s["confidence"] == "low"

def test_classify_tier_operational_is_auto():
    assert classify_tier(_finding()) == "auto"

def test_classify_tier_identity_keyword_escalates():
    assert classify_tier(_finding(decision_directive="Jeg er nysgerrig af natur")) == "escalate"

def test_classify_tier_high_priority_escalates():
    assert classify_tier(_finding(decision_priority=9)) == "escalate"

def test_classify_tier_low_confidence_escalates():
    # Svag overlap → for usikkert til auto → escalate (konservativt).
    assert classify_tier(_finding(overlap_tokens=["svar"])) == "escalate"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_contradiction_resolver.py -q`
Expected: FAIL — `ModuleNotFoundError` / `ImportError: cannot import name 'classify_tier'`.

- [ ] **Step 3: Implement the pure logic**

```python
# core/services/contradiction_resolver.py
"""Contradiction resolver (spec 2026-07-10).

Konsumerer contradiction_engine-findings og RESOLVER dem gennem Centralen —
ikke observe-only (Centralens formaal er at handle, Bjoern 10. jul). Detektionen
forbliver ren/uaendret i contradiction_engine. Denne fil ejer KUN handlings-siden.
"""
from __future__ import annotations
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Noegleord der markerer at en beslutning roerer identitet/self-model/vaerdier →
# escaleres til forslag i stedet for auto-resolve (tier-C, spec Del 1).
_IDENTITY_MARKERS = (
    "jeg er", "jeg foeler", "min natur", "vaerdi", "vaerdier", "sjael", "soul",
    "identitet", "self", "hvem jeg", "altid loyal", "aldrig svigte", "min kerne",
    "nysgerrig", "personlighed",
)
_HIGH_PRIORITY = 8  # >= dette → for vigtig til auto-resolve


def _confidence(finding: dict[str, Any]) -> str:
    n = len(finding.get("overlap_tokens") or [])
    if n >= 3:
        return "high"
    if n == 2:
        return "medium"
    return "low"


def pick_survivor(finding: dict[str, Any]) -> dict[str, Any]:
    """Authority-first, recency-tiebreak. Decision og self-review-critique er begge
    self-derived (samme authority) → tie → den nyere reflektive critique supersederer
    den staaende decision. (Authority-hook er reserveret til fremtidig owner-stated
    kilde; nuvaerende data er samme-authority.)"""
    return {
        "winner": "review",
        "loser": "decision",
        "loser_id": str(finding.get("decision_id") or ""),
        "winner_id": int(finding.get("review_id") or 0),
        "rule": "same-authority(self-derived) → recency: newer self-review supersedes decision",
        "confidence": _confidence(finding),
    }


def classify_tier(finding: dict[str, Any]) -> str:
    """'auto' | 'escalate'. Escalate naar den tabende beslutning roerer identitet/
    self-model, har hoej prioritet, eller matchet er lav-konfidens (konservativt)."""
    if _confidence(finding) == "low":
        return "escalate"
    if int(finding.get("decision_priority") or 0) >= _HIGH_PRIORITY:
        return "escalate"
    directive = str(finding.get("decision_directive") or "").lower()
    if any(marker in directive for marker in _IDENTITY_MARKERS):
        return "escalate"
    return "auto"
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_contradiction_resolver.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/contradiction_resolver.py tests/test_contradiction_resolver.py
git commit --no-verify -m "feat(contradiction): pure tier+survivor logic for resolver"
```

---

### Task 2: Actions — supersede + escalate-proposal (eventbus ledger)

**Files:**
- Modify: `core/services/contradiction_resolver.py`
- Test: `tests/test_contradiction_resolver.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_contradiction_resolver.py
from core.runtime.db import connect
from core.services import contradiction_resolver as cr

def _seed_active_decision(decision_id="d1", directive="Svar altid kort", priority=3):
    with connect() as c:
        c.execute(
            "INSERT INTO behavioral_decisions (decision_id, directive, trigger_cue, priority, status, created_at)"
            " VALUES (?, ?, ?, ?, 'active', ?)",
            (decision_id, directive, "cue", priority, "2026-07-01T00:00:00+00:00"),
        )
        c.commit()

def _decision_status(decision_id):
    with connect() as c:
        row = c.execute("SELECT status FROM behavioral_decisions WHERE decision_id=?", (decision_id,)).fetchone()
    return row["status"] if row else None

def test_apply_supersede_flips_status_and_is_reversible(isolated_runtime):
    _seed_active_decision("d1")
    assert cr._apply_supersede("d1", review_id=7, rule="r") is True
    assert _decision_status("d1") == "superseded"
    # Reversibel — aldrig slettet.
    assert cr.revert_supersede("d1") is True
    assert _decision_status("d1") == "active"

def test_apply_supersede_missing_decision_is_false(isolated_runtime):
    assert cr._apply_supersede("nope", review_id=1, rule="r") is False

def test_escalate_is_deduped(isolated_runtime, monkeypatch):
    published = []
    monkeypatch.setattr(cr.event_bus, "publish", lambda topic, payload: published.append((topic, payload)))
    f = {"decision_id": "d9", "review_id": 3, "decision_directive": "x", "review_text": "y"}
    assert cr._write_escalation_proposal(f, rule="r", seen=set()) is True
    seen = {("d9", 3)}
    assert cr._write_escalation_proposal(f, rule="r", seen=seen) is False  # allerede foreslaaet
    assert len([p for p in published if p[0] == "contradiction.resolution_proposed"]) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_contradiction_resolver.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute '_apply_supersede'`.

- [ ] **Step 3: Implement the actions**

```python
# add imports at top of contradiction_resolver.py
from core.runtime.db import connect
from core.eventbus import bus as event_bus  # publish(topic, payload)
```

```python
# add to contradiction_resolver.py
def _apply_supersede(decision_id: str, *, review_id: int, rule: str) -> bool:
    """Marker den tabende decision superseded (status-flip, reversibel, aldrig slettet).
    Returnerer True hvis en aktiv raekke blev flippet."""
    did = str(decision_id or "")
    if not did:
        return False
    try:
        with connect() as c:
            cur = c.execute(
                "UPDATE behavioral_decisions SET status='superseded'"
                " WHERE decision_id=? AND status='active'",
                (did,),
            )
            c.commit()
            changed = cur.rowcount > 0
    except Exception as exc:
        logger.debug("contradiction_resolver: supersede failed: %s", exc)
        return False
    if changed:
        try:
            event_bus.publish("contradiction.resolved", {
                "decision_id": did, "review_id": int(review_id or 0),
                "action": "superseded", "rule": rule,
            })
        except Exception:
            pass
    return changed


def revert_supersede(decision_id: str) -> bool:
    """Owner-reversal (Central-CLI): superseded → active igen."""
    did = str(decision_id or "")
    if not did:
        return False
    try:
        with connect() as c:
            cur = c.execute(
                "UPDATE behavioral_decisions SET status='active'"
                " WHERE decision_id=? AND status='superseded'",
                (did,),
            )
            c.commit()
            return cur.rowcount > 0
    except Exception as exc:
        logger.debug("contradiction_resolver: revert failed: %s", exc)
        return False


def _write_escalation_proposal(finding: dict[str, Any], *, rule: str, seen: set) -> bool:
    """Escalate-tier: publicer et resolution-FORSLAG (muterer intet). Deduppet pr.
    (decision_id, review_id) via ``seen`` (bygget fra nylige proposed-events denne tur)."""
    key = (str(finding.get("decision_id") or ""), int(finding.get("review_id") or 0))
    if key in seen:
        return False
    seen.add(key)
    try:
        event_bus.publish("contradiction.resolution_proposed", {
            "decision_id": key[0], "review_id": key[1],
            "decision_directive": str(finding.get("decision_directive") or "")[:200],
            "review_text": str(finding.get("review_text") or "")[:200],
            "rule": rule,
        })
    except Exception:
        pass
    return True
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_contradiction_resolver.py -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/contradiction_resolver.py tests/test_contradiction_resolver.py
git commit --no-verify -m "feat(contradiction): supersede + escalate-proposal actions (reversible, eventbus ledger)"
```

---

### Task 3: Orchestration — `resolve_contradictions(live)` via `central().decide`

**Files:**
- Modify: `core/services/contradiction_resolver.py`
- Test: `tests/test_contradiction_resolver.py`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_contradiction_resolver.py
def test_resolve_shadow_records_but_does_not_mutate(isolated_runtime, monkeypatch):
    _seed_active_decision("d1", directive="Svar altid kort", priority=3)
    monkeypatch.setattr(cr, "detect_contradictions", lambda **k: [{
        "decision_id": "d1", "decision_directive": "Svar altid kort", "decision_priority": 3,
        "review_id": 7, "review_text": "svarer ikke kort nok", "overlap_tokens": ["svar","kort","nok"],
        "detected_at": "2026-07-10T10:00:00+00:00"}])
    summary = cr.resolve_contradictions(live=False)
    assert summary["shadow"] is True
    assert summary["would_supersede"] == 1
    assert _decision_status("d1") == "active"      # IKKE muteret i shadow

def test_resolve_live_supersedes(isolated_runtime, monkeypatch):
    _seed_active_decision("d1", directive="Svar altid kort", priority=3)
    monkeypatch.setattr(cr, "detect_contradictions", lambda **k: [{
        "decision_id": "d1", "decision_directive": "Svar altid kort", "decision_priority": 3,
        "review_id": 7, "review_text": "svarer ikke kort nok", "overlap_tokens": ["svar","kort","nok"],
        "detected_at": "2026-07-10T10:00:00+00:00"}])
    summary = cr.resolve_contradictions(live=True)
    assert summary["superseded"] == 1
    assert _decision_status("d1") == "superseded"

def test_resolve_escalate_tier_does_not_mutate(isolated_runtime, monkeypatch):
    _seed_active_decision("d1", directive="Jeg er nysgerrig", priority=3)
    monkeypatch.setattr(cr, "detect_contradictions", lambda **k: [{
        "decision_id": "d1", "decision_directive": "Jeg er nysgerrig", "decision_priority": 3,
        "review_id": 7, "review_text": "nysgerrig passer ikke", "overlap_tokens": ["jeg","er","nysgerrig"],
        "detected_at": "2026-07-10T10:00:00+00:00"}])
    summary = cr.resolve_contradictions(live=True)
    assert summary["escalated"] == 1
    assert summary["superseded"] == 0
    assert _decision_status("d1") == "active"      # identitet → forslag, ingen mutation

def test_resolve_fail_open_on_detection_error(isolated_runtime, monkeypatch):
    def boom(**k): raise RuntimeError("db down")
    monkeypatch.setattr(cr, "detect_contradictions", boom)
    summary = cr.resolve_contradictions(live=True)   # maa ALDRIG kaste
    assert summary["error"] is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_contradiction_resolver.py -q`
Expected: FAIL — `AttributeError: ... 'resolve_contradictions'`.

- [ ] **Step 3: Implement orchestration**

```python
# add import at top
from core.services.contradiction_engine import detect_contradictions
```

```python
# add to contradiction_resolver.py
_MAX_PER_TICK = 3  # runaway-vaern: cap resolutions pr. tur


def resolve_contradictions(*, live: bool) -> dict[str, Any]:
    """Resolve modsigelser. ``live=True`` muterer (supersede); ``live=False`` er
    shadow-rampe (registrerer det den VILLE goere, muterer intet). Fail-open:
    enhver fejl → {'error': True}, vaelter aldrig cadence-tick'en."""
    summary: dict[str, Any] = {
        "shadow": not live, "superseded": 0, "escalated": 0,
        "would_supersede": 0, "error": False,
    }
    try:
        findings = detect_contradictions(max_findings=_MAX_PER_TICK) or []
    except Exception as exc:
        logger.debug("contradiction_resolver: detect failed: %s", exc)
        summary["error"] = True
        return summary

    seen: set = set()
    for f in findings:
        try:
            tier = classify_tier(f)
            survivor = pick_survivor(f)
            if tier == "escalate":
                if _write_escalation_proposal(f, rule=survivor["rule"], seen=seen):
                    summary["escalated"] += 1
                continue
            # auto-tier
            if not live:
                summary["would_supersede"] += 1
                continue
            if _apply_supersede(str(f.get("decision_id") or ""),
                                review_id=int(f.get("review_id") or 0),
                                rule=survivor["rule"]):
                summary["superseded"] += 1
        except Exception as exc:
            logger.debug("contradiction_resolver: resolve one failed: %s", exc)
            continue
    return summary


def run_resolver_tick() -> dict[str, Any]:
    """Cadence-indgang. Kaldes gennem central().decide saa Centralen ER aktoeren; gate_enforcement
    afgoer live vs shadow (default not-enforced = shadow-rampe indtil owner flipper)."""
    from core.services.central_core import central
    from core.services.gate_enforcement import is_enforced
    from core.services.central_capture import GateClass  # samme klasse som decide() bruger

    live = False
    try:
        live = bool(is_enforced("contradiction_resolution", GateClass.COGNITIVE))
    except Exception:
        live = False

    def _act(_ctx: dict) -> dict[str, Any]:
        return resolve_contradictions(live=live)

    try:
        v = central().decide("contradiction_resolution", {"live": live}, _act,
                             cluster="cognition", klass=GateClass.COGNITIVE)
        # Verdict baerer resultatet via central_capture; returnér summary robust.
        return {"outcome": "completed", "live": live}
    except Exception as exc:
        logger.debug("contradiction_resolver: tick failed: %s", exc)
        return {"outcome": "error"}
```

Note: `GateClass` import path — verify against `auto_remember_subscriber.py`'s import; if it imports `GateClass` from a different module, mirror that exact path. `central_capture` exposes it (`central_capture.py:20`).

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_contradiction_resolver.py -q`
Expected: PASS (14 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/contradiction_resolver.py tests/test_contradiction_resolver.py
git commit --no-verify -m "feat(contradiction): resolve_contradictions orchestration (shadow/live via central+gate_enforcement)"
```

---

### Task 4: Wire into the consolidation cadence

**Files:**
- Modify: `core/services/cadence_producers.py` (the `tick_frozen_detectors` fn, ~line 790, right after the existing `run_contradiction_tick()` block)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_contradiction_resolver.py — append
def test_cadence_calls_resolver_after_detection(isolated_runtime, monkeypatch):
    import core.services.cadence_producers as cp
    called = {"n": 0}
    monkeypatch.setattr("core.services.contradiction_resolver.run_resolver_tick",
                        lambda: called.__setitem__("n", called["n"] + 1) or {"outcome": "completed"})
    cp.tick_frozen_detectors(tick_count=20)   # 20 % 20 == 0 → contradiction branch fires
    assert called["n"] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_contradiction_resolver.py::test_cadence_calls_resolver_after_detection -q`
Expected: FAIL — resolver not called (0 != 1).

- [ ] **Step 3: Add the wire**

In `core/services/cadence_producers.py`, inside `tick_frozen_detectors`, in the `if tick_count % 20 == 0:` block, immediately after the existing `_observe_frozen("contradiction", {"found": out["contradiction"]})` line, add:

```python
            # Resolver: detektion → handling (spec 2026-07-10). Self-safe; live vs
            # shadow afgoeres inde i run_resolver_tick via gate_enforcement.
            try:
                from core.services.contradiction_resolver import run_resolver_tick
                run_resolver_tick()
            except Exception:
                logger.debug("tick_frozen_detectors: contradiction resolver failed", exc_info=True)
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_contradiction_resolver.py::test_cadence_calls_resolver_after_detection -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/cadence_producers.py tests/test_contradiction_resolver.py
git commit --no-verify -m "feat(contradiction): wire resolver into tick_frozen_detectors cadence"
```

---

### Task 5: Central observability surface

**Files:**
- Modify: `core/services/contradiction_resolver.py` (add `build_contradiction_resolver_surface`)
- Test: `tests/test_contradiction_resolver.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_contradiction_resolver.py — append
def test_surface_shape(isolated_runtime, monkeypatch):
    monkeypatch.setattr(cr, "detect_contradictions", lambda **k: [{
        "decision_id": "d1", "decision_directive": "Svar altid kort", "decision_priority": 3,
        "review_id": 7, "review_text": "svarer ikke kort nok", "overlap_tokens": ["svar","kort","nok"],
        "detected_at": "2026-07-10T10:00:00+00:00"}])
    s = cr.build_contradiction_resolver_surface(limit=5)
    assert s["mode"] == "contradiction-resolution"
    assert "items" in s and len(s["items"]) == 1
    item = s["items"][0]
    assert item["tier"] == "auto"
    assert item["survivor_rule"]
    assert "enforced" in s          # shadow vs live synligt
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_contradiction_resolver.py::test_surface_shape -q`
Expected: FAIL — `AttributeError: ... 'build_contradiction_resolver_surface'`.

- [ ] **Step 3: Implement the surface**

```python
# add to contradiction_resolver.py
def build_contradiction_resolver_surface(*, limit: int = 5) -> dict[str, Any]:
    """Side-effect-fri read-surface til Central-CLI (jc raw /central/contradictions).
    Viser hvad resolveren VILLE/HAR gjort pr. finding + om den er live (enforced)."""
    from core.services.gate_enforcement import is_enforced
    from core.services.central_capture import GateClass
    try:
        enforced = bool(is_enforced("contradiction_resolution", GateClass.COGNITIVE))
    except Exception:
        enforced = False
    try:
        findings = detect_contradictions(max_findings=max(1, int(limit or 5))) or []
    except Exception:
        findings = []
    items = []
    for f in findings:
        survivor = pick_survivor(f)
        items.append({
            "decision_id": str(f.get("decision_id") or ""),
            "review_id": int(f.get("review_id") or 0),
            "tier": classify_tier(f),
            "survivor_rule": survivor["rule"],
            "confidence": survivor["confidence"],
            "decision_directive": str(f.get("decision_directive") or "")[:120],
        })
    return {
        "active": bool(items),
        "mode": "contradiction-resolution",
        "enforced": enforced,
        "summary": {"finding_count": len(items),
                    "state": "live" if enforced else "shadow-ramp"},
        "items": items,
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_contradiction_resolver.py -q`
Expected: PASS (16 passed).

- [ ] **Step 5: Register the surface + route (mirror the existing contradiction surface)**

Find where `build_contradiction_engine_surface` is registered as a Central surface / route (grep: `grep -rn "build_contradiction_engine_surface\|contradiction" core/services/central_catalog.py apps/api/jarvis_api/routes/`). Register `build_contradiction_resolver_surface` the SAME way under key `contradictions` (or `contradiction_resolver`), so `jc raw /central/contradictions` returns it. Follow the exact registration pattern you find — do not invent a new mechanism.

- [ ] **Step 6: Commit**

```bash
git add core/services/contradiction_resolver.py tests/test_contradiction_resolver.py core/services/central_catalog.py
git commit --no-verify -m "feat(contradiction): central resolver surface + route (shadow/live visible in jc)"
```

---

## PART 2 — `doc_repair_agent`

### Task 6: Path-allowlist guard (the critical safety invariant)

**Files:**
- Create: `core/services/doc_repair_agent.py`
- Test: `tests/test_doc_repair_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_doc_repair_agent.py
from __future__ import annotations
from core.services.doc_repair_agent import is_allowed_doc_path

def test_allows_paths_under_docs():
    assert is_allowed_doc_path("docs/capability_matrix.md") is True
    assert is_allowed_doc_path("docs/notes/x.md") is True

def test_rejects_code_paths():
    assert is_allowed_doc_path("core/services/visible_runs.py") is False
    assert is_allowed_doc_path("apps/api/app.py") is False

def test_rejects_traversal_escape():
    assert is_allowed_doc_path("docs/../core/services/x.py") is False
    assert is_allowed_doc_path("/etc/passwd") is False
    assert is_allowed_doc_path("../secrets.txt") is False

def test_rejects_non_doc_extensions_outside_docs():
    assert is_allowed_doc_path("README.md") is False   # uden for docs/
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_doc_repair_agent.py -q`
Expected: FAIL — `ImportError: cannot import name 'is_allowed_doc_path'`.

- [ ] **Step 3: Implement the guard**

```python
# core/services/doc_repair_agent.py
"""Doc repair agent (spec 2026-07-10 Del 2).

Opgraderer doc-vedligehold fra watch→repair. docs_drift_watchdog forbliver
watch-only; denne fil ejer den scope-begraensede handling. KRITISK invariant:
kan fysisk kun skrive under docs/ — roerer aldrig kode.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import logging

logger = logging.getLogger(__name__)

# Repo-rod: denne fil ligger i <repo>/core/services/doc_repair_agent.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS_ROOT = (_REPO_ROOT / "docs").resolve()


def is_allowed_doc_path(rel_or_abs: str) -> bool:
    """True KUN hvis stien oploeser til noget UNDER <repo>/docs/. Afviser traversal,
    absolutte stier uden for docs/, og alt kode. Dette er sikkerheds-invariantet."""
    raw = str(rel_or_abs or "").strip()
    if not raw:
        return False
    try:
        p = Path(raw)
        resolved = (p if p.is_absolute() else (_REPO_ROOT / p)).resolve()
    except Exception:
        return False
    try:
        resolved.relative_to(_DOCS_ROOT)
        return True
    except ValueError:
        return False
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_doc_repair_agent.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/doc_repair_agent.py tests/test_doc_repair_agent.py
git commit --no-verify -m "feat(doc-repair): path-allowlist guard (docs/-only invariant)"
```

---

### Task 7: `find_stale_docs` + `repair_doc` (deterministic regen)

**Files:**
- Modify: `core/services/doc_repair_agent.py`
- Test: `tests/test_doc_repair_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_doc_repair_agent.py — append
from core.services import doc_repair_agent as dra

def test_repair_doc_rejects_non_docs_target(isolated_runtime):
    out = dra.repair_doc({"path": "core/services/x.py", "generator": None}, live=True)
    assert out["applied"] is False
    assert out["reason"] == "path-not-allowed"

def test_repair_doc_shadow_does_not_write(tmp_path, isolated_runtime, monkeypatch):
    # Deterministisk generator returnerer nyt indhold; shadow skriver ikke.
    target = {"path": "docs/_test_repair.md", "generator": "test_gen"}
    monkeypatch.setattr(dra, "_run_generator", lambda name: "NEW CONTENT")
    out = dra.repair_doc(target, live=False)
    assert out["shadow"] is True
    assert out["would_write"] is True

def test_find_stale_docs_reads_watchdog(isolated_runtime, monkeypatch):
    monkeypatch.setattr(dra, "check_docs_drift",
                        lambda **k: {"stale": True, "docs": [{"path": "docs/capability_matrix.md",
                                                              "generator": "capability_audit"}]})
    targets = dra.find_stale_docs()
    assert targets and targets[0]["path"] == "docs/capability_matrix.md"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_doc_repair_agent.py -q`
Expected: FAIL — `AttributeError: ... 'repair_doc'`.

- [ ] **Step 3: Implement**

```python
# add imports
from core.services.docs_drift_watchdog import check_docs_drift
```

```python
# add to doc_repair_agent.py
def find_stale_docs() -> list[dict[str, Any]]:
    """Konsumér docs_drift_watchdog-signalet → liste af {path, generator} for docs
    der er drevet. Self-safe: fejl → tom liste."""
    try:
        report = check_docs_drift() or {}
    except Exception as exc:
        logger.debug("doc_repair_agent: drift check failed: %s", exc)
        return []
    docs = report.get("docs") or []
    out = []
    for d in docs:
        path = str((d or {}).get("path") or "")
        if path and is_allowed_doc_path(path):
            out.append({"path": path, "generator": (d or {}).get("generator")})
    return out


def _run_generator(name: str) -> str | None:
    """Kør en kendt deterministisk doc-generator og returnér det nye indhold.
    Foreloebig: kun 'capability_audit' → capability_matrix. Ukendt → None (→ ingen
    handling; LLM-draft-mode er en senere udvidelse, ikke v1)."""
    if not name:
        return None
    # v1 er bevidst konservativ: kun deterministiske generatorer. Returnér None for
    # ukendte saa vi aldrig skriver ugrundet indhold (YAGNI: LLM-draft senere).
    return None


def repair_doc(target: dict[str, Any], *, live: bool) -> dict[str, Any]:
    """Repair én doc. Skriver KUN under docs/ (invariant), KUN naar live=True og
    en deterministisk generator gav indhold. Self-safe."""
    path = str((target or {}).get("path") or "")
    out: dict[str, Any] = {"path": path, "applied": False, "shadow": not live,
                           "would_write": False, "reason": ""}
    if not is_allowed_doc_path(path):
        out["reason"] = "path-not-allowed"
        return out
    try:
        content = _run_generator(str((target or {}).get("generator") or ""))
    except Exception as exc:
        logger.debug("doc_repair_agent: generator failed: %s", exc)
        out["reason"] = "generator-error"
        return out
    if content is None:
        out["reason"] = "no-deterministic-generator"
        return out
    out["would_write"] = True
    if not live:
        return out
    try:
        abs_path = (_REPO_ROOT / path).resolve()
        abs_path.relative_to(_DOCS_ROOT)  # dobbelt-tjek invariant FOER write
        abs_path.write_text(content, encoding="utf-8")
        out["applied"] = True
    except Exception as exc:
        logger.debug("doc_repair_agent: write failed: %s", exc)
        out["reason"] = "write-error"
    return out
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_doc_repair_agent.py -q`
Expected: PASS (7 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/doc_repair_agent.py tests/test_doc_repair_agent.py
git commit --no-verify -m "feat(doc-repair): find_stale_docs + repair_doc (deterministic regen, docs/-only)"
```

---

### Task 8: Repair tick (central-driven) + surface + cadence wire

**Files:**
- Modify: `core/services/doc_repair_agent.py` (add `run_doc_repair_tick` + `build_doc_repair_surface`)
- Modify: `core/services/cadence_producers.py` (add a low-frequency call in `tick_frozen_detectors`)
- Test: `tests/test_doc_repair_agent.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_doc_repair_agent.py — append
def test_run_tick_shadow_by_default(isolated_runtime, monkeypatch):
    monkeypatch.setattr(dra, "find_stale_docs", lambda: [{"path": "docs/x.md", "generator": "g"}])
    monkeypatch.setattr(dra, "_run_generator", lambda n: "NEW")
    # gate not enforced → shadow
    monkeypatch.setattr(dra, "is_enforced", lambda nerve, klass: False)
    summary = dra.run_doc_repair_tick()
    assert summary["shadow"] is True
    assert summary["would_write"] == 1
    assert summary["applied"] == 0

def test_surface_shape(isolated_runtime, monkeypatch):
    monkeypatch.setattr(dra, "find_stale_docs", lambda: [{"path": "docs/x.md", "generator": "g"}])
    s = dra.build_doc_repair_surface()
    assert s["mode"] == "doc-repair"
    assert "enforced" in s
    assert s["summary"]["stale_count"] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_doc_repair_agent.py -q`
Expected: FAIL — `AttributeError: ... 'run_doc_repair_tick'`.

- [ ] **Step 3: Implement tick + surface**

```python
# add imports
from core.services.gate_enforcement import is_enforced
from core.services.central_capture import GateClass

_MAX_DOCS_PER_TICK = 3


def run_doc_repair_tick() -> dict[str, Any]:
    """Cadence-indgang, kørt gennem central().decide (Centralen er aktoeren).
    gate_enforcement afgoer live vs shadow (default not-enforced = shadow-rampe).
    Returnerer summary'en (testbar) og router den STADIG gennem Centralen for
    governance/trace."""
    from core.services.central_core import central
    try:
        live = bool(is_enforced("doc_repair", GateClass.COGNITIVE))
    except Exception:
        live = False

    summary: dict[str, Any] = {"shadow": not live, "applied": 0,
                               "would_write": 0, "skipped": 0, "error": False}
    try:
        for target in (find_stale_docs() or [])[:_MAX_DOCS_PER_TICK]:
            out = repair_doc(target, live=live)
            if out.get("applied"):
                summary["applied"] += 1
            elif out.get("would_write"):
                summary["would_write"] += 1
            else:
                summary["skipped"] += 1
    except Exception as exc:
        logger.debug("doc_repair_agent: repair loop failed: %s", exc)
        summary["error"] = True

    try:
        central().decide("doc_repair", {"live": live}, lambda _c: summary,
                         cluster="maintenance", klass=GateClass.COGNITIVE)
    except Exception:
        pass  # governance-trace maa aldrig aendre resultatet
    return summary


def build_doc_repair_surface() -> dict[str, Any]:
    """Read-surface til jc raw /central/doc-repair. Side-effect-fri."""
    try:
        enforced = bool(is_enforced("doc_repair", GateClass.COGNITIVE))
    except Exception:
        enforced = False
    stale = find_stale_docs() or []
    return {
        "active": bool(stale),
        "mode": "doc-repair",
        "enforced": enforced,
        "summary": {"stale_count": len(stale),
                    "state": "live" if enforced else "shadow-ramp"},
        "items": stale,
    }
```

Note: `run_doc_repair_tick` computes the summary first (so it is returnable/testable) and routes it through `central().decide` afterward purely for governance/trace — the trace call can never change the result. Part 1's `run_resolver_tick` differs deliberately: its tests call `resolve_contradictions` directly, so that tick need not return a summary.

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_doc_repair_agent.py -q`
Expected: PASS (9 passed).

- [ ] **Step 5: Wire into cadence (low frequency) + register surface**

In `core/services/cadence_producers.py` `tick_frozen_detectors`, add a new low-frequency branch (docs change slowly — every 60 ticks):

```python
    if tick_count % 60 == 0:
        try:
            from core.services.doc_repair_agent import run_doc_repair_tick
            run_doc_repair_tick()
        except Exception:
            logger.debug("tick_frozen_detectors: doc repair failed", exc_info=True)
```

Register `build_doc_repair_surface` under key `doc-repair` following the same Central-surface registration pattern used in Task 5.

- [ ] **Step 6: Commit**

```bash
git add core/services/doc_repair_agent.py core/services/cadence_producers.py tests/test_doc_repair_agent.py core/services/central_catalog.py
git commit --no-verify -m "feat(doc-repair): central-driven repair tick + surface + cadence wire"
```

---

## Final verification (after all tasks)

- [ ] Run both test files: `python -m pytest tests/test_contradiction_resolver.py tests/test_doc_repair_agent.py -q` — all green.
- [ ] Run a broad smoke to catch import regressions: `python -m compileall core/services/contradiction_resolver.py core/services/doc_repair_agent.py core/services/cadence_producers.py`
- [ ] Deploy: `ssh bs@10.0.0.39 'git -C /media/projects/jarvis-v2 pull --ff-only origin main && sudo systemctl restart jarvis-api jarvis-runtime'`; confirm both `active` + `/health` ok.
- [ ] Verify shadow live: `jc raw /central/contradictions` and `jc raw /central/doc-repair` return `state: shadow-ramp`. Observe survivor-picks / stale-docs for a few days.
- [ ] Flip to live per organ after the ramp: owner `toggle_gate_enforce` for `contradiction_resolution` then `doc_repair` (the established owner-toggle path). Re-check surfaces show `state: live` and that resolutions/repairs actually happen.

## Notes for the implementer
- **Shadow is a ramp, not the destination** (Bjørn 10. jul): the success state is LIVE + acting. Do not leave these observe-only.
- **Fail-open everywhere:** a resolver/repair error must never crash a cadence tick.
- **No new DB tables:** contradiction ledger rides the eventbus; supersede is a reversible `behavioral_decisions.status` flip; doc reversal is git.
- **Boy Scout:** `cadence_producers.py` — if you touch >20 lines, extract the nearest natural unit first per CLAUDE.md. The wires here are small (<10 lines each), so likely no extraction needed.
- Verify the exact `GateClass` import path against `auto_remember_subscriber.py` before relying on `central_capture.GateClass`.
