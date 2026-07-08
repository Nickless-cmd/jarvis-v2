---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Meta-læring Phase 1 — Ugentlig Strategi-retrospektiv: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis et ugentligt retrospektiv-memo, genereret via cheap-lane LLM, der syntetiserer sidste 7 dages aktivitet på tværs af alle 5 AGI-spor (World Model, Plan Revision, Curiosity, Skill Chain Phase 2, Tool Invention) til en prosa-fortælling med citationsnøgler + 0-3 hypothesis-kandidater til Phase 2.

**Architecture:** Aggregator-funktioner queryer eksisterende AGI-spor read-only og bygger kurateret summary med ekstreme samples per spor. Generator kalder cheap-lane med strukturet prompt, parser markdown-output defensivt, persisterer i ny `learning_memos`-tabel. ProducerSpec triggerer ugentligt (cooldown 7 dage + søndag-vindue). Awareness-injection viser teaser når et memo er unacknowledged; Jarvis kalder `read_learning_memo(memo_id)` for fuld tekst.

**Tech Stack:** Python 3.11, eksisterende `execute_public_safe_cheap_lane` (samme som propose_skill_chain Phase 2), `internal_cadence.ProducerSpec`, ny `learning_memos`-tabel, ny event-family `cognitive_meta_learning`.

**Spec:** `docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/meta_learning_aggregator.py` | 5 aggregator-funktioner (world_model, plan_revision, curiosity, skill_chain_phase2, tool_invention). Read-only queries. Returnerer aggregat-stats + outlier-samples per spor. ~280 LOC. |
| `core/services/meta_learning_retrospective.py` | `generate_weekly_retrospective(now)`, cheap-lane integration, prompt-builder, defensive markdown-parser, persistence + schema-bootstrap for `learning_memos` tabel. ~280 LOC. |
| `core/tools/meta_learning_tools.py` | `read_learning_memo(memo_id)` (marker acknowledged) + `list_learning_memos(limit=5)`. `META_LEARNING_TOOL_DEFINITIONS` + `META_LEARNING_TOOL_HANDLERS`. ~150 LOC. |
| `tests/test_meta_learning.py` | Alle Phase 1 tests: aggregators, parser, persistence, ProducerSpec, awareness, tools, killswitch. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `meta_learning_enabled: bool = True` (master killswitch). |
| `core/eventbus/events.py` | Add `cognitive_meta_learning` to `ALLOWED_EVENT_FAMILIES`. |
| `core/services/internal_cadence.py` | Register `meta_learning_weekly_retrospective` ProducerSpec. |
| `core/services/prompt_contract.py` | Priority 39 awareness-injection (mellem curiosity 38 og turn changelog 40). |
| `core/tools/simple_tools.py` | Import + splat META_LEARNING tool definitions/handlers. |
| `scripts/smoke_test_startup.py` | Smoke imports + schema-bootstrap. |

### Untouched / reused

- **All 5 AGI-spor moduler** — aggregator queryer kun read-only:
  - `world_model_signal_tracking._load_predictions()` (state_store key `runtime_world_model_predictions`)
  - `plan_proposals._load_all()` (alle plan-records)
  - `curiosity_observations` tabel (direkte SQL via `core.runtime.db.connect`)
  - `events` tabel filtreret på `cognitive_skill_chain.*` for skill chain phase 2
  - `skill_engine.list_skills()` for tool invention adoption + plans med `skill_data` for proposed
- **`execute_public_safe_cheap_lane(message=)`** — samme cheap-lane helper som propose_skill_chain Phase 2 bruger
- **`core.runtime.db.connect()`** + **`core.runtime.state_store.load_json/save_json`** — eksisterende
- **`db.py`** — uberørt (Boy Scout — 33k linjer; schema-bootstrap i ny service)

---

## Spec deltas confirmed during planning

1. **`ALLOWED_EVENT_FAMILIES` location:** `core/eventbus/events.py` (verificeret i Grep). Vi tilføjer `"cognitive_meta_learning"` til set'et.

2. **World model state key:** `_PREDICTION_STATE_KEY = "runtime_world_model_predictions"` — predictions er en liste af dicts i state_store. Hver prediction har felter inkluderet `subject`, `expectation`, `confidence`, `outcome` (resolved), `resolved_at`. Vi læser via `_load_predictions()` eller direkte `load_json(_PREDICTION_STATE_KEY, [])`.

3. **Plan records location:** `plan_proposals._load_all()` returnerer `dict[plan_id, plan_record]`. Hver record har `status`, `created_at`, `updated_at` (sometimes), `revised_from`, `superseded_by`, `skill_data` (Tool Invention).

4. **Curiosity observations:** SQLite tabel `curiosity_observations` (id, ts, action, args_json, observation_text, follow_up_hint). Vi queryer direkte med parameterized SQL.

5. **Skill Chain Phase 2 events:** `cognitive_skill_chain.proposed` + `.revised` events i `events`-tabellen (family + kind + payload_json + created_at). Vi queryer direkte.

6. **Tool invention proxy:** Tool invention bruger eksisterende `plan_proposals` med `skill_data` payload. "Proposed" = plans med non-null `skill_data`. "Adopted" = approved skill_data-plans. "Never used" = installerede skills der ikke har calls i events (uden for Phase 1 scope — vi nøjes med proposed/adopted i Phase 1).

7. **Cheap-lane helper:** `execute_public_safe_cheap_lane(message=prompt) -> {"text", "model", "provider", "status", ...}` (verificeret i `cheap_provider_runtime.py:740`).

8. **Defensive markdown-parsing:** Genbrug samme mønster som `_parse_propose_response` i `skill_chain_propose_tool.py` — markdown-fence-tolerant, defensive split.

---

## Task 1: Settings flag + event-family + skeleton service

**Files:**
- Modify: `core/runtime/settings.py`
- Modify: `core/eventbus/events.py`
- Create: `core/services/meta_learning_retrospective.py` (skeleton with schema-bootstrap kun)
- Create: `tests/test_meta_learning.py` (schema tests kun)

- [ ] **Step 1: Add settings flag**

In `core/runtime/settings.py`, find `skill_chain_phase2_enabled: bool = True` and add right after it:

```python
    # ── Meta-læring Phase 1 (added 2026-05-12 — AGI track #3) ─────────────
    # When True: weekly retrospective producer fires, learning-memo
    # awareness-injection active, read_learning_memo + list_learning_memos
    # tools registered. When False: producer skipped, awareness empty,
    # tools fail-soft. Master killswitch for the AGI track.
    meta_learning_enabled: bool = True
```

- [ ] **Step 2: Wire flag into load_settings**

In `core/runtime/settings.py`, find `skill_chain_phase2_enabled=bool(...)` block in `load_settings` and add right after its closing comma:

```python
        meta_learning_enabled=bool(
            data.get(
                "meta_learning_enabled",
                defaults.meta_learning_enabled,
            )
        ),
```

- [ ] **Step 3: Add event family**

In `core/eventbus/events.py`, find the `ALLOWED_EVENT_FAMILIES = {` set (line ~5) and add right after the `"cognitive_skill_chain"` entry (line 93):

```python
    "cognitive_meta_learning",
```

- [ ] **Step 4: Verify both wirings**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
assert RuntimeSettings().meta_learning_enabled is True
print('OK settings:', load_settings().meta_learning_enabled)
from core.eventbus.events import ALLOWED_EVENT_FAMILIES
assert 'cognitive_meta_learning' in ALLOWED_EVENT_FAMILIES
print('OK event family registered')
"
```

Expected: `OK settings: True` + `OK event family registered`

- [ ] **Step 5: Write failing schema tests**

Create `tests/test_meta_learning.py`:

```python
"""Meta-læring Phase 1 — tests.

AGI track #3. See spec at
docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated workspace + DB so meta-learning data doesn't pollute tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", str(tmp_path / "state"))
    import importlib
    import core.runtime.db as db
    importlib.reload(db)
    import core.runtime.state_store as ss
    importlib.reload(ss)
    return None


def test_schema_bootstrap_creates_table(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    from core.runtime.db import connect

    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='learning_memos'"
        ).fetchone()
        assert row is not None

        idx = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='learning_memos'"
        ).fetchall()}
        assert "idx_learning_memos_ts" in idx


def test_schema_bootstrap_idempotent(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    ensure_schema()
    ensure_schema()  # should not raise
```

- [ ] **Step 6: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_meta_learning.py -v 2>&1 | tail -8
```

Expected: FAIL with `ModuleNotFoundError: core.services.meta_learning_retrospective`.

- [ ] **Step 7: Create skeleton service with schema-bootstrap**

Create `core/services/meta_learning_retrospective.py`:

```python
"""Meta-læring retrospective generator — Phase 1 (AGI track #3).

Genererer ugentligt retrospektiv-memo via cheap-lane LLM. Syntetiserer
aktivitet fra 5 AGI-spor til prosa-fortælling med citationsnøgler +
struktureret hypothesis-blok (0-3 kandidater).

Schema-bootstrap lives here (not in db.py) per Boy Scout Rule.

See spec: docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create learning_memos table + index."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS learning_memos (
              memo_id TEXT PRIMARY KEY,
              ts TEXT NOT NULL,
              period_start TEXT NOT NULL,
              period_end TEXT NOT NULL,
              narrative TEXT NOT NULL,
              hypothesis_candidates_json TEXT NOT NULL,
              aggregator_snapshot_json TEXT NOT NULL,
              model_used TEXT,
              acknowledged_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_learning_memos_ts
              ON learning_memos(ts);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -v 2>&1 | tail -8
```

Expected: 2 passed.

- [ ] **Step 9: Commit**

```bash
git add core/runtime/settings.py core/eventbus/events.py core/services/meta_learning_retrospective.py tests/test_meta_learning.py
git commit -m "feat(meta-learning): settings killswitch + cognitive_meta_learning event family + learning_memos schema"
```

---

## Task 2: Aggregator — world model + plan revision

**Files:**
- Create: `core/services/meta_learning_aggregator.py`
- Modify: `tests/test_meta_learning.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_meta_learning.py`:

```python
def test_aggregate_world_model_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_world_model
    now = datetime.now(UTC)
    result = aggregate_world_model(since=now - timedelta(days=7), until=now)
    assert result["predictions_made"] == 0
    assert result["predictions_resolved"] == 0
    assert result["outcome_distribution"] == {"supported": 0, "contradicted": 0, "uncertain": 0}
    assert result["extreme_samples"] == []


def test_aggregate_world_model_with_data(clean_state):
    from core.runtime.state_store import save_json
    from core.services.meta_learning_aggregator import aggregate_world_model

    now = datetime.now(UTC)
    iso_now = now.isoformat()
    iso_recent = (now - timedelta(days=1)).isoformat()
    iso_old = (now - timedelta(days=30)).isoformat()  # outside window

    predictions = [
        {"id": "p1", "subject": "x", "expectation": "y", "confidence": 0.9,
         "created_at": iso_recent, "outcome": "contradicted", "resolved_at": iso_now},
        {"id": "p2", "subject": "a", "expectation": "b", "confidence": 0.3,
         "created_at": iso_recent, "outcome": "supported", "resolved_at": iso_now},
        {"id": "p3", "subject": "c", "expectation": "d", "confidence": 0.7,
         "created_at": iso_recent, "outcome": "uncertain", "resolved_at": iso_now},
        {"id": "p4", "subject": "old", "expectation": "outside window",
         "confidence": 0.5, "created_at": iso_old, "outcome": "supported",
         "resolved_at": iso_old},
    ]
    save_json("runtime_world_model_predictions", predictions)

    result = aggregate_world_model(since=now - timedelta(days=7), until=now)
    assert result["predictions_made"] == 3  # p4 excluded
    assert result["predictions_resolved"] == 3
    assert result["outcome_distribution"]["contradicted"] == 1
    assert result["outcome_distribution"]["supported"] == 1
    assert result["outcome_distribution"]["uncertain"] == 1

    # Outliers: highest confidence contradicted = p1; lowest confidence supported = p2
    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("highest_confidence_contradicted") == "p1"
    assert roles.get("lowest_confidence_supported") == "p2"


def test_aggregate_plan_revision_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_plan_revision
    now = datetime.now(UTC)
    result = aggregate_plan_revision(since=now - timedelta(days=7), until=now)
    assert result["plans_created"] == 0
    assert result["status_distribution"] == {
        "awaiting_approval": 0, "approved": 0, "completed": 0,
        "dismissed": 0, "superseded": 0,
    }
    assert result["extreme_samples"] == []


def test_aggregate_plan_revision_with_data(clean_state, monkeypatch):
    """Plans created in window, one superseded fast, one with long completion time."""
    from core.services.meta_learning_aggregator import aggregate_plan_revision
    from core.services import plan_proposals as pp

    now = datetime.now(UTC)
    iso_now = now.isoformat()
    fast_supersede_created = (now - timedelta(days=2)).isoformat()
    fast_supersede_updated = (now - timedelta(days=2, minutes=-30)).isoformat()  # 30 min after created
    long_completion_created = (now - timedelta(days=5)).isoformat()
    long_completion_updated = (now - timedelta(days=1)).isoformat()  # 4 days

    fake_plans = {
        "plan-fast": {
            "plan_id": "plan-fast", "status": "superseded",
            "created_at": fast_supersede_created,
            "updated_at": fast_supersede_updated,
            "title": "Fast superseded", "superseded_by": "plan-other",
        },
        "plan-long": {
            "plan_id": "plan-long", "status": "completed",
            "created_at": long_completion_created,
            "updated_at": long_completion_updated,
            "title": "Long completion",
        },
        "plan-other": {
            "plan_id": "plan-other", "status": "approved",
            "created_at": iso_now, "title": "Replacement",
        },
    }
    monkeypatch.setattr(pp, "_load_all", lambda: fake_plans)

    result = aggregate_plan_revision(since=now - timedelta(days=7), until=now)
    assert result["plans_created"] == 3
    assert result["status_distribution"]["superseded"] == 1
    assert result["status_distribution"]["completed"] == 1
    assert result["status_distribution"]["approved"] == 1

    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("fastest_superseded") == "plan-fast"
    assert roles.get("longest_completion") == "plan-long"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "aggregate_world_model or aggregate_plan_revision" -v 2>&1 | tail -10
```

Expected: 4 fail with `ModuleNotFoundError: core.services.meta_learning_aggregator`.

- [ ] **Step 3: Create aggregator module with world_model + plan_revision**

Create `core/services/meta_learning_aggregator.py`:

```python
"""Meta-læring aggregator — Phase 1 (AGI track #3).

Read-only queries på de 5 AGI-spor til ugentlig retrospektiv.
Hver funktion returnerer aggregat-stats + 1-2 ekstreme samples.

See spec: docs/superpowers/specs/2026-05-12-meta-learning-phase1-design.md
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


def _in_window(ts_iso: str, since: datetime, until: datetime) -> bool:
    """Defensive: parse ts and check if it's within [since, until]."""
    if not ts_iso:
        return False
    try:
        ts = datetime.fromisoformat(ts_iso)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return False
    return since <= ts <= until


def _bucket_confidence(c: float) -> str:
    if c >= 0.7:
        return "high"
    if c >= 0.4:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# World model
# ---------------------------------------------------------------------------

def aggregate_world_model(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate world-model prediction activity in [since, until].

    Outliers:
      - highest_confidence_contradicted: prediction with highest confidence
        that was contradicted (surprise on overconfidence)
      - lowest_confidence_supported: prediction with lowest confidence
        that was supported (surprise on underconfidence)
    """
    from core.services.world_model_signal_tracking import _load_predictions

    try:
        all_predictions = _load_predictions()
    except Exception as exc:
        logger.warning("aggregate_world_model: load failed: %s", exc)
        all_predictions = []

    in_window = [
        p for p in all_predictions
        if _in_window(str(p.get("created_at") or ""), since, until)
    ]

    resolved = [p for p in in_window if p.get("outcome")]
    outcome_dist = {"supported": 0, "contradicted": 0, "uncertain": 0}
    for p in resolved:
        outcome = str(p.get("outcome") or "").strip()
        if outcome in outcome_dist:
            outcome_dist[outcome] += 1

    confidence_buckets = {"high": 0, "medium": 0, "low": 0}
    for p in in_window:
        try:
            c = float(p.get("confidence") or 0.0)
            confidence_buckets[_bucket_confidence(c)] += 1
        except (TypeError, ValueError):
            pass

    extreme_samples: list[dict[str, Any]] = []

    contradicted = [p for p in resolved if p.get("outcome") == "contradicted"]
    if contradicted:
        top = max(contradicted, key=lambda p: float(p.get("confidence") or 0))
        extreme_samples.append({
            "role": "highest_confidence_contradicted",
            "id": str(top.get("id") or ""),
            "data": {
                "subject": str(top.get("subject") or ""),
                "expectation": str(top.get("expectation") or ""),
                "confidence": float(top.get("confidence") or 0),
                "created_at": str(top.get("created_at") or ""),
                "resolved_at": str(top.get("resolved_at") or ""),
            },
        })

    supported = [p for p in resolved if p.get("outcome") == "supported"]
    if supported:
        low = min(supported, key=lambda p: float(p.get("confidence") or 1))
        extreme_samples.append({
            "role": "lowest_confidence_supported",
            "id": str(low.get("id") or ""),
            "data": {
                "subject": str(low.get("subject") or ""),
                "expectation": str(low.get("expectation") or ""),
                "confidence": float(low.get("confidence") or 0),
                "created_at": str(low.get("created_at") or ""),
                "resolved_at": str(low.get("resolved_at") or ""),
            },
        })

    return {
        "predictions_made": len(in_window),
        "predictions_resolved": len(resolved),
        "outcome_distribution": outcome_dist,
        "confidence_buckets": confidence_buckets,
        "extreme_samples": extreme_samples,
    }


# ---------------------------------------------------------------------------
# Plan revision
# ---------------------------------------------------------------------------

def _completion_seconds(rec: dict[str, Any]) -> float | None:
    """Seconds between created_at and updated_at; None if either missing."""
    try:
        c = datetime.fromisoformat(str(rec.get("created_at") or ""))
        u = datetime.fromisoformat(str(rec.get("updated_at") or ""))
        if c.tzinfo is None:
            c = c.replace(tzinfo=UTC)
        if u.tzinfo is None:
            u = u.replace(tzinfo=UTC)
        return (u - c).total_seconds()
    except (ValueError, TypeError):
        return None


def aggregate_plan_revision(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate plan-proposal activity in [since, until].

    Outliers:
      - fastest_superseded: plan with smallest seconds between created_at
        and updated_at where status='superseded' (we changed our mind fast)
      - longest_completion: plan with largest seconds between created_at
        and updated_at where status='completed' (slow grind)
    """
    from core.services.plan_proposals import _load_all

    try:
        all_plans = _load_all()
    except Exception as exc:
        logger.warning("aggregate_plan_revision: load failed: %s", exc)
        all_plans = {}

    in_window = [
        rec for rec in all_plans.values()
        if _in_window(str(rec.get("created_at") or ""), since, until)
    ]

    status_dist = {
        "awaiting_approval": 0, "approved": 0, "completed": 0,
        "dismissed": 0, "superseded": 0,
    }
    for rec in in_window:
        s = str(rec.get("status") or "")
        if s in status_dist:
            status_dist[s] += 1

    extreme_samples: list[dict[str, Any]] = []

    superseded = [r for r in in_window if r.get("status") == "superseded"]
    superseded_with_delta = [
        (r, _completion_seconds(r)) for r in superseded
    ]
    superseded_with_delta = [(r, d) for (r, d) in superseded_with_delta if d is not None]
    if superseded_with_delta:
        fastest, delta = min(superseded_with_delta, key=lambda pair: pair[1])
        extreme_samples.append({
            "role": "fastest_superseded",
            "id": str(fastest.get("plan_id") or ""),
            "data": {
                "title": str(fastest.get("title") or ""),
                "seconds_alive": delta,
                "superseded_by": str(fastest.get("superseded_by") or ""),
                "created_at": str(fastest.get("created_at") or ""),
            },
        })

    completed = [r for r in in_window if r.get("status") == "completed"]
    completed_with_delta = [
        (r, _completion_seconds(r)) for r in completed
    ]
    completed_with_delta = [(r, d) for (r, d) in completed_with_delta if d is not None]
    if completed_with_delta:
        longest, delta = max(completed_with_delta, key=lambda pair: pair[1])
        extreme_samples.append({
            "role": "longest_completion",
            "id": str(longest.get("plan_id") or ""),
            "data": {
                "title": str(longest.get("title") or ""),
                "seconds_to_complete": delta,
                "created_at": str(longest.get("created_at") or ""),
            },
        })

    return {
        "plans_created": len(in_window),
        "status_distribution": status_dist,
        "extreme_samples": extreme_samples,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "aggregate_world_model or aggregate_plan_revision" -v 2>&1 | tail -8
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/meta_learning_aggregator.py tests/test_meta_learning.py
git commit -m "feat(meta-learning): aggregator for world_model + plan_revision with outlier samples"
```

---

## Task 3: Aggregator — curiosity + skill_chain + tool_invention

**Files:**
- Modify: `core/services/meta_learning_aggregator.py`
- Modify: `tests/test_meta_learning.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_meta_learning.py`:

```python
def test_aggregate_curiosity_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_curiosity
    from core.services.curiosity_budget import ensure_schema
    ensure_schema()  # ensure table exists
    now = datetime.now(UTC)
    result = aggregate_curiosity(since=now - timedelta(days=7), until=now)
    assert result["actions_used"] == 0
    assert result["action_distribution"] == {}
    assert result["extreme_samples"] == []


def test_aggregate_curiosity_with_data(clean_state):
    from core.runtime.db import connect
    from core.services.curiosity_budget import ensure_schema, record_observation
    from core.services.meta_learning_aggregator import aggregate_curiosity
    ensure_schema()

    obs_short = record_observation("read_dreams", "{}", "short note", None)
    obs_long = record_observation(
        "list_tools", "{}",
        "Very long observation that goes into detail about why this is interesting "
        "and what trail of thought led here, capturing the engaged moment of curiosity.",
        None,
    )

    now = datetime.now(UTC)
    result = aggregate_curiosity(since=now - timedelta(days=7), until=now)
    assert result["actions_used"] == 2
    assert result["action_distribution"]["read_dreams"] == 1
    assert result["action_distribution"]["list_tools"] == 1

    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("longest_observation_text") == obs_long
    assert roles.get("shortest_non_empty_observation") == obs_short


def test_aggregate_skill_chain_phase2_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_skill_chain_phase2
    now = datetime.now(UTC)
    result = aggregate_skill_chain_phase2(since=now - timedelta(days=7), until=now)
    assert result["proposals_made"] == 0
    assert result["revisions_made"] == 0
    assert result["revision_context_distribution"] == {"pre_execution": 0, "mid_chain": 0}
    assert result["extreme_samples"] == []


def test_aggregate_skill_chain_phase2_with_data(clean_state):
    from core.runtime.db import connect
    from core.services.meta_learning_aggregator import aggregate_skill_chain_phase2

    now = datetime.now(UTC)
    iso_now = now.isoformat()

    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
              event_id TEXT PRIMARY KEY,
              family TEXT,
              kind TEXT,
              created_at TEXT,
              payload_json TEXT
            )
        """)
        # Proposal with high confidence that was later revised
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ("e1", "cognitive_skill_chain", "proposed", iso_now,
             json.dumps({"plan": ["a","b"], "confidence": 0.9, "step_count": 2})),
        )
        # Pre-execution revision of that plan
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ("e2", "cognitive_skill_chain", "revised", iso_now,
             json.dumps({"new_plan": ["a","c"], "revision_context": "pre_execution",
                         "reason": "I want to try a different second step entirely, "
                                   "because the first plan ran into issues."})),
        )
        # Mid-chain revision with shorter reason
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ("e3", "cognitive_skill_chain", "revised", iso_now,
             json.dumps({"new_plan": ["d","e"], "revision_context": "mid_chain",
                         "reason": "step 1 failed"})),
        )
        conn.commit()

    result = aggregate_skill_chain_phase2(since=now - timedelta(days=7), until=now)
    assert result["proposals_made"] == 1
    assert result["revisions_made"] == 2
    assert result["revision_context_distribution"]["pre_execution"] == 1
    assert result["revision_context_distribution"]["mid_chain"] == 1

    roles = {s["role"]: s["id"] for s in result["extreme_samples"]}
    assert roles.get("highest_confidence_proposal") == "e1"
    assert roles.get("longest_reason_revision") == "e2"


def test_aggregate_tool_invention_empty(clean_state):
    from core.services.meta_learning_aggregator import aggregate_tool_invention
    now = datetime.now(UTC)
    result = aggregate_tool_invention(since=now - timedelta(days=7), until=now)
    assert result["proposed"] == 0
    assert result["adopted"] == 0


def test_aggregate_tool_invention_with_data(clean_state, monkeypatch):
    from core.services.meta_learning_aggregator import aggregate_tool_invention
    from core.services import plan_proposals as pp

    now = datetime.now(UTC)
    iso_recent = (now - timedelta(days=1)).isoformat()

    fake_plans = {
        "plan-skill-a": {
            "plan_id": "plan-skill-a",
            "status": "approved",
            "created_at": iso_recent,
            "title": "Install skill foo",
            "skill_data": {"name": "foo", "description": "..."},
        },
        "plan-skill-b": {
            "plan_id": "plan-skill-b",
            "status": "dismissed",
            "created_at": iso_recent,
            "title": "Install skill bar",
            "skill_data": {"name": "bar", "description": "..."},
        },
        "plan-regular": {
            "plan_id": "plan-regular",
            "status": "approved",
            "created_at": iso_recent,
            "title": "Regular plan",
            "skill_data": None,
        },
    }
    monkeypatch.setattr(pp, "_load_all", lambda: fake_plans)

    result = aggregate_tool_invention(since=now - timedelta(days=7), until=now)
    assert result["proposed"] == 2  # plans with skill_data
    assert result["adopted"] == 1   # only approved skill_data plans
    sample_ids = {s["id"] for s in result["extreme_samples"]}
    assert "plan-skill-a" in sample_ids
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "curiosity or skill_chain_phase2 or tool_invention" -v 2>&1 | tail -10
```

Expected: 6 fail with `cannot import name 'aggregate_curiosity'` etc.

- [ ] **Step 3: Add three aggregators to module**

Append to `core/services/meta_learning_aggregator.py`:

```python
# ---------------------------------------------------------------------------
# Curiosity
# ---------------------------------------------------------------------------

def aggregate_curiosity(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate curiosity-tool activity in [since, until].

    Outliers:
      - longest_observation_text: most engaged observation
      - shortest_non_empty_observation: perfunctory glance
    """
    from core.runtime.db import connect

    since_iso = since.isoformat()
    until_iso = until.isoformat()

    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, action, observation_text FROM curiosity_observations "
                "WHERE ts >= ? AND ts <= ? ORDER BY ts",
                (since_iso, until_iso),
            ).fetchall()
            rows = [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("aggregate_curiosity: query failed: %s", exc)
        rows = []

    action_dist: dict[str, int] = {}
    for r in rows:
        a = str(r.get("action") or "")
        action_dist[a] = action_dist.get(a, 0) + 1

    extreme_samples: list[dict[str, Any]] = []
    non_empty = [r for r in rows if str(r.get("observation_text") or "").strip()]
    if non_empty:
        longest = max(non_empty, key=lambda r: len(str(r.get("observation_text") or "")))
        shortest = min(non_empty, key=lambda r: len(str(r.get("observation_text") or "")))
        extreme_samples.append({
            "role": "longest_observation_text",
            "id": str(longest.get("id") or ""),
            "data": {
                "action": str(longest.get("action") or ""),
                "ts": str(longest.get("ts") or ""),
                "observation_text": str(longest.get("observation_text") or ""),
            },
        })
        if shortest.get("id") != longest.get("id"):
            extreme_samples.append({
                "role": "shortest_non_empty_observation",
                "id": str(shortest.get("id") or ""),
                "data": {
                    "action": str(shortest.get("action") or ""),
                    "ts": str(shortest.get("ts") or ""),
                    "observation_text": str(shortest.get("observation_text") or ""),
                },
            })

    return {
        "actions_used": len(rows),
        "action_distribution": action_dist,
        "extreme_samples": extreme_samples,
    }


# ---------------------------------------------------------------------------
# Skill chain Phase 2
# ---------------------------------------------------------------------------

def aggregate_skill_chain_phase2(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate skill_chain Phase 2 events in [since, until].

    Outliers:
      - highest_confidence_proposal: proposal we were most sure about
      - longest_reason_revision: revision with most thought-through reason
    """
    from core.runtime.db import connect

    since_iso = since.isoformat()
    until_iso = until.isoformat()

    try:
        with connect() as conn:
            rows = conn.execute(
                "SELECT event_id, kind, created_at, payload_json FROM events "
                "WHERE family = 'cognitive_skill_chain' "
                "AND kind IN ('proposed', 'revised') "
                "AND created_at >= ? AND created_at <= ?",
                (since_iso, until_iso),
            ).fetchall()
            rows = [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("aggregate_skill_chain_phase2: query failed: %s", exc)
        rows = []

    proposals: list[dict[str, Any]] = []
    revisions: list[dict[str, Any]] = []
    for r in rows:
        try:
            payload = json.loads(str(r.get("payload_json") or "{}"))
        except (json.JSONDecodeError, ValueError):
            payload = {}
        r["_payload"] = payload
        if r.get("kind") == "proposed":
            proposals.append(r)
        elif r.get("kind") == "revised":
            revisions.append(r)

    ctx_dist = {"pre_execution": 0, "mid_chain": 0}
    for r in revisions:
        ctx = str(r["_payload"].get("revision_context") or "")
        if ctx in ctx_dist:
            ctx_dist[ctx] += 1

    extreme_samples: list[dict[str, Any]] = []

    if proposals:
        top = max(proposals, key=lambda r: float(r["_payload"].get("confidence") or 0))
        extreme_samples.append({
            "role": "highest_confidence_proposal",
            "id": str(top.get("event_id") or ""),
            "data": {
                "plan": top["_payload"].get("plan", []),
                "confidence": float(top["_payload"].get("confidence") or 0),
                "created_at": str(top.get("created_at") or ""),
            },
        })

    if revisions:
        longest = max(revisions, key=lambda r: len(str(r["_payload"].get("reason") or "")))
        extreme_samples.append({
            "role": "longest_reason_revision",
            "id": str(longest.get("event_id") or ""),
            "data": {
                "new_plan": longest["_payload"].get("new_plan", []),
                "revision_context": str(longest["_payload"].get("revision_context") or ""),
                "reason": str(longest["_payload"].get("reason") or ""),
                "created_at": str(longest.get("created_at") or ""),
            },
        })

    return {
        "proposals_made": len(proposals),
        "revisions_made": len(revisions),
        "revision_context_distribution": ctx_dist,
        "extreme_samples": extreme_samples,
    }


# ---------------------------------------------------------------------------
# Tool invention (proxy via plan_proposals with skill_data)
# ---------------------------------------------------------------------------

def aggregate_tool_invention(*, since: datetime, until: datetime) -> dict[str, Any]:
    """Aggregate tool-invention activity in [since, until].

    Tool invention proxies through plan_proposals: plans with non-null
    skill_data are 'proposed tools'; approved ones are 'adopted'.

    Outliers:
      - Most recent adopted skill (signal of momentum)
      - Most recent dismissed proposed skill (signal of rejection pattern)
    """
    from core.services.plan_proposals import _load_all

    try:
        all_plans = _load_all()
    except Exception as exc:
        logger.warning("aggregate_tool_invention: load failed: %s", exc)
        all_plans = {}

    skill_plans = [
        rec for rec in all_plans.values()
        if rec.get("skill_data") and _in_window(
            str(rec.get("created_at") or ""), since, until
        )
    ]
    proposed = len(skill_plans)
    adopted = sum(1 for r in skill_plans if r.get("status") == "approved")

    extreme_samples: list[dict[str, Any]] = []
    approved_skills = [r for r in skill_plans if r.get("status") == "approved"]
    if approved_skills:
        latest = max(approved_skills, key=lambda r: str(r.get("created_at") or ""))
        sd = latest.get("skill_data") or {}
        extreme_samples.append({
            "role": "most_recent_adopted_skill",
            "id": str(latest.get("plan_id") or ""),
            "data": {
                "skill_name": str(sd.get("name") or ""),
                "description": str(sd.get("description") or "")[:200],
                "created_at": str(latest.get("created_at") or ""),
            },
        })

    dismissed_skills = [r for r in skill_plans if r.get("status") == "dismissed"]
    if dismissed_skills:
        latest = max(dismissed_skills, key=lambda r: str(r.get("created_at") or ""))
        sd = latest.get("skill_data") or {}
        extreme_samples.append({
            "role": "most_recent_dismissed_skill",
            "id": str(latest.get("plan_id") or ""),
            "data": {
                "skill_name": str(sd.get("name") or ""),
                "description": str(sd.get("description") or "")[:200],
                "created_at": str(latest.get("created_at") or ""),
            },
        })

    return {
        "proposed": proposed,
        "adopted": adopted,
        "extreme_samples": extreme_samples,
    }
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -v 2>&1 | tail -15
```

Expected: 12 passed (2 schema + 4 world_model/plan + 6 curiosity/skill_chain/tool).

- [ ] **Step 3: Commit**

```bash
git add core/services/meta_learning_aggregator.py tests/test_meta_learning.py
git commit -m "feat(meta-learning): aggregator for curiosity + skill_chain_phase2 + tool_invention"
```

---

## Task 4: Retrospective generator — prompt + parser

**Files:**
- Modify: `core/services/meta_learning_retrospective.py`
- Modify: `tests/test_meta_learning.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_meta_learning.py`:

```python
def test_build_prompt_includes_personality_and_citation_instruction(clean_state):
    from core.services.meta_learning_retrospective import _build_retrospective_prompt

    aggregator_snapshot = {
        "world_model": {"predictions_made": 0, "predictions_resolved": 0,
                        "outcome_distribution": {}, "extreme_samples": []},
        "plan_revision": {"plans_created": 0, "status_distribution": {},
                          "extreme_samples": []},
        "curiosity": {"actions_used": 0, "action_distribution": {},
                      "extreme_samples": []},
        "skill_chain_phase2": {"proposals_made": 0, "revisions_made": 0,
                               "revision_context_distribution": {},
                               "extreme_samples": []},
        "tool_invention": {"proposed": 0, "adopted": 0, "extreme_samples": []},
    }
    prompt = _build_retrospective_prompt(
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        aggregator_snapshot=aggregator_snapshot,
    )
    # Personality cue
    assert "1.-person" in prompt or "1.-person" in prompt.lower() or "1st-person" in prompt.lower() or "1. person" in prompt.lower()
    assert "dansk" in prompt.lower()
    # Citation instruction
    assert "citationsnøgle" in prompt.lower() or "plan_id" in prompt
    # Hypothesis structure
    assert "Hypothesis Candidates" in prompt
    assert "tom" in prompt.lower() or "empty" in prompt.lower()


def test_parse_memo_with_hypotheses(clean_state):
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """Dette er ugentlig prosa-analyse. Jeg har observeret at jeg reviderer plans hurtigt: plan-abc123 blev superseded efter 30 min (12. maj 09:30→10:00).

Mit kalibreringsmønster: confidence 0.9 var contradicted i prediction-xyz789.

## Hypothesis Candidates

### Kandidat 1: Vent 3 min før propose_plan
- **Observation:** Plans superseded inden for 1 time i 80% af tilfældene (plan-abc123, plan-def456)
- **Hypotese:** Hvis jeg venter 3 min med refleksion før propose_plan, stiger approval-rate
- **Success-kriterium:** Approval-rate (approved / proposed) stiger fra X til Y over 4 uger
- **Sample-størrelse:** Mindst 10 plans

### Kandidat 2: Lavere confidence i overraskelser
- **Observation:** Predictions med confidence >0.85 contradicted i 40%
- **Hypotese:** Hvis jeg sætter et cap på max 0.85 confidence, vil overall kalibrering forbedres
- **Success-kriterium:** Brier score lavere efter 20 nye predictions
- **Sample-størrelse:** 20 predictions
"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "ugentlig prosa-analyse" in result["narrative"]
    assert "plan-abc123" in result["narrative"]
    assert "## Hypothesis Candidates" not in result["narrative"]
    assert len(result["hypothesis_candidates"]) == 2
    cand1 = result["hypothesis_candidates"][0]
    assert cand1["id"] == "hyp-1"
    assert "Vent 3 min" in cand1["statement"]
    assert "plan-abc123" in cand1["observation"]
    assert cand1["sample_size_needed"] == 10


def test_parse_memo_without_hypotheses(clean_state):
    """Tom hypothesis-blok legitim — narrative bevares, hypothesis list er []."""
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """Ugen var rolig. Få events, lille datagrundlag, ingen klare mønstre.

## Hypothesis Candidates

(Ingen hypoteser denne uge — datagrundlaget er for spinkelt.)
"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "Ugen var rolig" in result["narrative"]
    assert result["hypothesis_candidates"] == []


def test_parse_memo_with_markdown_fence(clean_state):
    """Cheap-lane often wraps output in ```markdown``` fences."""
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """```markdown
Prosa-analyse her.

## Hypothesis Candidates

### Kandidat 1: Test
- **Observation:** noget
- **Hypotese:** hvis X så Y
- **Success-kriterium:** måling
- **Sample-størrelse:** 5
```"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "Prosa-analyse" in result["narrative"]
    assert len(result["hypothesis_candidates"]) == 1


def test_parse_memo_malformed_returns_narrative_only(clean_state):
    """Defensive: parsing failure should preserve prose, return empty hypotheses."""
    from core.services.meta_learning_retrospective import _parse_memo_markdown

    markdown = """Just some text without proper structure.

## Hypothesis Candidates

### Kandidat 1: But fields are missing
"""
    result = _parse_memo_markdown(markdown)
    assert result["status"] == "ok"
    assert "Just some text" in result["narrative"]
    # The malformed kandidat may produce a degraded entry or be skipped — either is OK
    assert isinstance(result["hypothesis_candidates"], list)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "build_prompt or parse_memo" -v 2>&1 | tail -10
```

Expected: 5 fail with `cannot import name '_build_retrospective_prompt'` or `_parse_memo_markdown`.

- [ ] **Step 3: Add prompt-builder and parser to retrospective module**

In `core/services/meta_learning_retrospective.py`, add right after `ensure_schema` function:

```python
import json
import re


_HYPOTHESIS_HEADER = "## Hypothesis Candidates"
_KANDIDAT_RE = re.compile(r"###\s+Kandidat\s+(\d+):\s*(.*)$", re.MULTILINE)
_FIELD_RE = re.compile(r"^\s*-\s*\*\*([^*]+)\*\*:\s*(.+)$", re.MULTILINE)
_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n?(.*?)\n?```", re.DOTALL)


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    return text


def _build_retrospective_prompt(
    *,
    period_start: str,
    period_end: str,
    aggregator_snapshot: dict[str, Any],
) -> str:
    """Build the cheap-lane prompt for weekly retrospective memo."""
    snapshot_json = json.dumps(aggregator_snapshot, ensure_ascii=False, indent=2, default=str)
    return (
        "Du er Jarvis' meta-læringsskribent. Du modtager kuraterede aggregater "
        "for sidste 7 dages aktivitet på 5 AGI-spor. Din opgave er at producere "
        "et kort, indsigtsfuldt retrospektiv-memo i to dele.\n"
        "\n"
        "DEL 1: Prosa-analyse (300-500 ord).\n"
        "- Skriv som Jarvis selv ville reflektere (1.-person, dansk, varm tone).\n"
        "- Fokuser på 2-3 mønstre der træder frem. Ikke et resumé af alt.\n"
        "- Hver konkret reference SKAL inkludere en citationsnøgle: plan_id, "
        "prediction_id, obs_id, eller ISO-datotid. Læseren skal kunne grave i "
        "det via curiosity-tools.\n"
        "- Inkluder MINDST én outlier-observation — hvad var ekstremt i den uge?\n"
        "\n"
        f"DEL 2: {_HYPOTHESIS_HEADER} (0-3 entries).\n"
        "- Hvis ugen var rolig eller ingen reelle mønstre fremtræder, returnér "
        "TOM blok (skriv kort note som '(Ingen hypoteser denne uge — "
        "datagrundlaget er for spinkelt.)' i stedet for kandidater).\n"
        "- Hvis 1-3 testbare hypoteser findes, formatér hver præcis sådan:\n"
        "  ### Kandidat N: <kort statement>\n"
        "  - **Observation:** <konkret mønster, citationsnøgle>\n"
        "  - **Hypotese:** <hvis X, så Y>\n"
        "  - **Success-kriterium:** <hvordan vi måler>\n"
        "  - **Sample-størrelse:** <antal observationer der skal til, kun heltal>\n"
        "\n"
        "Returnér KUN markdown — ingen JSON-wrappere, ingen forklarende tekst "
        "udenfor selve memoet. Vi parser markdown direkte.\n"
        "\n"
        f"Periode: {period_start} → {period_end}\n"
        "\n"
        "AGGREGATER (JSON):\n"
        f"{snapshot_json}\n"
    )


def _parse_memo_markdown(text: str) -> dict[str, Any]:
    """Parse cheap-lane markdown output into narrative + hypothesis_candidates.

    Returns:
        {
          "status": "ok",
          "narrative": str,
          "hypothesis_candidates": [
              {"id", "statement", "observation", "hypothesis",
               "success_criterion", "sample_size_needed"},
              ...
          ],
        }

    Defensive: if hypothesis-section parse fails, narrative is still preserved
    and hypothesis_candidates is [].
    """
    if not text or not text.strip():
        return {"status": "ok", "narrative": "", "hypothesis_candidates": []}

    raw = _strip_markdown_fence(text)
    if _HYPOTHESIS_HEADER in raw:
        idx = raw.find(_HYPOTHESIS_HEADER)
        narrative = raw[:idx].strip()
        hypo_section = raw[idx + len(_HYPOTHESIS_HEADER):].strip()
    else:
        narrative = raw.strip()
        hypo_section = ""

    candidates: list[dict[str, Any]] = []
    if hypo_section:
        # Split by ### Kandidat N: headers
        matches = list(_KANDIDAT_RE.finditer(hypo_section))
        for i, m in enumerate(matches):
            kandidat_num = int(m.group(1))
            statement = m.group(2).strip()
            # Find body — from this match end to next match start (or end of section)
            body_start = m.end()
            body_end = matches[i + 1].start() if i + 1 < len(matches) else len(hypo_section)
            body = hypo_section[body_start:body_end]

            fields: dict[str, str] = {}
            for f in _FIELD_RE.finditer(body):
                key = f.group(1).strip().lower()
                val = f.group(2).strip()
                fields[key] = val

            # Map Danish field labels to canonical keys
            observation = fields.get("observation", "")
            hypothesis = fields.get("hypotese", "") or fields.get("hypothesis", "")
            success_criterion = (
                fields.get("success-kriterium", "")
                or fields.get("success criterion", "")
            )
            sample_raw = (
                fields.get("sample-størrelse", "")
                or fields.get("sample size needed", "")
                or fields.get("sample-storrelse", "")
            )
            sample_size = 0
            sample_match = re.search(r"\d+", sample_raw)
            if sample_match:
                try:
                    sample_size = int(sample_match.group(0))
                except ValueError:
                    sample_size = 0

            # Skip candidates with no usable content
            if not statement and not observation and not hypothesis:
                continue

            candidates.append({
                "id": f"hyp-{kandidat_num}",
                "statement": statement,
                "observation": observation,
                "hypothesis": hypothesis,
                "success_criterion": success_criterion,
                "sample_size_needed": sample_size,
            })

    return {
        "status": "ok",
        "narrative": narrative,
        "hypothesis_candidates": candidates[:3],  # cap at 3
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -v 2>&1 | tail -15
```

Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/meta_learning_retrospective.py tests/test_meta_learning.py
git commit -m "feat(meta-learning): prompt builder + defensive markdown parser (narrative + hypothesis candidates)"
```

---

## Task 5: Retrospective generator — persistence + cheap-lane integration

**Files:**
- Modify: `core/services/meta_learning_retrospective.py`
- Modify: `tests/test_meta_learning.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_meta_learning.py`:

```python
def test_persist_memo_inserts_row(clean_state):
    from core.runtime.db import connect
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo,
    )
    ensure_schema()

    memo_id = _persist_memo(
        memo_id="memo-test-1",
        ts="2026-05-12T04:00:00+00:00",
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        narrative="Test narrative.",
        hypothesis_candidates=[{"id": "hyp-1", "statement": "x"}],
        aggregator_snapshot={"world_model": {}},
        model_used="fake-model",
    )
    assert memo_id == "memo-test-1"
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos WHERE memo_id = ?", (memo_id,)
        ).fetchone()
    assert row is not None
    assert row["narrative"] == "Test narrative."
    assert row["model_used"] == "fake-model"
    assert row["acknowledged_at"] is None


def test_fetch_latest_unacknowledged(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo, fetch_latest_unacknowledged_memo,
    )
    ensure_schema()
    assert fetch_latest_unacknowledged_memo() is None  # empty

    _persist_memo(
        memo_id="memo-old", ts="2026-05-01T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="old", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )
    _persist_memo(
        memo_id="memo-new", ts="2026-05-12T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="newer", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )
    result = fetch_latest_unacknowledged_memo()
    assert result is not None
    assert result["memo_id"] == "memo-new"


def test_acknowledge_memo_updates_field(clean_state):
    from core.runtime.db import connect
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo, acknowledge_memo,
    )
    ensure_schema()
    _persist_memo(
        memo_id="memo-ack", ts="2026-05-12T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="...", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )
    acknowledge_memo("memo-ack")
    with connect() as conn:
        row = conn.execute(
            "SELECT acknowledged_at FROM learning_memos WHERE memo_id = ?",
            ("memo-ack",),
        ).fetchone()
    assert row["acknowledged_at"] is not None


def test_generate_weekly_retrospective_end_to_end(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr
    from core.runtime.db import connect

    fake_text = """Det var en rolig uge med få events. Plan-abc123 blev superseded efter 30 min.

## Hypothesis Candidates

### Kandidat 1: Vent længere
- **Observation:** Plans hurtigt superseded (plan-abc123)
- **Hypotese:** Vent 3 min før propose_plan
- **Success-kriterium:** Approval-rate stiger
- **Sample-størrelse:** 10
"""

    def fake_cheap_lane(*, message: str) -> dict[str, Any]:
        return {"status": "completed", "text": fake_text, "provider": "fake", "model": "fake-m"}

    def fake_aggregator_world_model(*, since, until):
        return {"predictions_made": 0, "predictions_resolved": 0,
                "outcome_distribution": {}, "confidence_buckets": {},
                "extreme_samples": []}

    monkeypatch.setattr(mlr, "execute_public_safe_cheap_lane", fake_cheap_lane)
    # Aggregators called via direct import inside generator — patch all 5
    import core.services.meta_learning_aggregator as agg
    monkeypatch.setattr(agg, "aggregate_world_model", fake_aggregator_world_model)
    monkeypatch.setattr(agg, "aggregate_plan_revision",
                        lambda *, since, until: {"plans_created": 0, "status_distribution": {}, "extreme_samples": []})
    monkeypatch.setattr(agg, "aggregate_curiosity",
                        lambda *, since, until: {"actions_used": 0, "action_distribution": {}, "extreme_samples": []})
    monkeypatch.setattr(agg, "aggregate_skill_chain_phase2",
                        lambda *, since, until: {"proposals_made": 0, "revisions_made": 0, "revision_context_distribution": {}, "extreme_samples": []})
    monkeypatch.setattr(agg, "aggregate_tool_invention",
                        lambda *, since, until: {"proposed": 0, "adopted": 0, "extreme_samples": []})

    now = datetime.now(UTC)
    result = mlr.generate_weekly_retrospective(now=now)
    assert result["status"] == "ok"
    assert result["memo_id"].startswith("memo-")
    assert "plan-abc123" in result["narrative"]
    assert len(result["hypothesis_candidates"]) == 1
    assert result["model_used"] == "fake-m"

    # Verify persisted
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos WHERE memo_id = ?", (result["memo_id"],)
        ).fetchone()
    assert row is not None


def test_generate_handles_cheap_lane_failure(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr

    def failing_cheap_lane(*, message: str) -> dict[str, Any]:
        raise RuntimeError("network down")

    monkeypatch.setattr(mlr, "execute_public_safe_cheap_lane", failing_cheap_lane)
    import core.services.meta_learning_aggregator as agg
    for name in ("aggregate_world_model", "aggregate_plan_revision",
                 "aggregate_curiosity", "aggregate_skill_chain_phase2",
                 "aggregate_tool_invention"):
        monkeypatch.setattr(agg, name,
                            lambda *, since, until: {"extreme_samples": []})

    result = mlr.generate_weekly_retrospective(now=datetime.now(UTC))
    assert result["status"] == "error"
    assert "cheap-lane" in result["reason"].lower()


def test_generate_respects_killswitch(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr

    class FakeSettings:
        meta_learning_enabled = False

    monkeypatch.setattr(mlr, "load_settings", lambda: FakeSettings())
    result = mlr.generate_weekly_retrospective(now=datetime.now(UTC))
    assert result["status"] == "disabled"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "persist or fetch_latest or acknowledge or generate" -v 2>&1 | tail -10
```

Expected: 6 fail with various import errors.

- [ ] **Step 3: Add persistence + generator to retrospective module**

In `core/services/meta_learning_retrospective.py`, add at top right after the existing imports:

```python
from core.runtime.settings import load_settings
from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
```

Append at bottom of `core/services/meta_learning_retrospective.py`:

```python
# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _persist_memo(
    *,
    memo_id: str,
    ts: str,
    period_start: str,
    period_end: str,
    narrative: str,
    hypothesis_candidates: list[dict[str, Any]],
    aggregator_snapshot: dict[str, Any],
    model_used: str,
) -> str:
    """Insert a new memo row. Returns memo_id."""
    ensure_schema()
    with connect() as conn:
        conn.execute(
            "INSERT INTO learning_memos "
            "(memo_id, ts, period_start, period_end, narrative, "
            " hypothesis_candidates_json, aggregator_snapshot_json, "
            " model_used, acknowledged_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
            (
                memo_id, ts, period_start, period_end, narrative,
                json.dumps(hypothesis_candidates, ensure_ascii=False, default=str),
                json.dumps(aggregator_snapshot, ensure_ascii=False, default=str),
                model_used,
            ),
        )
        conn.commit()
    return memo_id


def fetch_latest_unacknowledged_memo() -> dict[str, Any] | None:
    """Return the most recent memo with acknowledged_at IS NULL, or None."""
    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos "
            "WHERE acknowledged_at IS NULL "
            "ORDER BY ts DESC LIMIT 1"
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["hypothesis_candidates"] = json.loads(d.get("hypothesis_candidates_json") or "[]")
    except (json.JSONDecodeError, ValueError):
        d["hypothesis_candidates"] = []
    return d


def fetch_memo_by_id(memo_id: str) -> dict[str, Any] | None:
    ensure_schema()
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM learning_memos WHERE memo_id = ?", (memo_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["hypothesis_candidates"] = json.loads(d.get("hypothesis_candidates_json") or "[]")
    except (json.JSONDecodeError, ValueError):
        d["hypothesis_candidates"] = []
    return d


def list_recent_memos(limit: int = 5) -> list[dict[str, Any]]:
    ensure_schema()
    limit = max(1, min(int(limit), 50))
    with connect() as conn:
        rows = conn.execute(
            "SELECT memo_id, ts, period_start, period_end, model_used, "
            "       acknowledged_at, length(narrative) AS narrative_length "
            "FROM learning_memos ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def acknowledge_memo(memo_id: str) -> bool:
    """Mark memo as acknowledged. Returns True if a row was updated."""
    ensure_schema()
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE learning_memos SET acknowledged_at = ? "
            "WHERE memo_id = ? AND acknowledged_at IS NULL",
            (now_iso, memo_id),
        )
        conn.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def _meta_learning_enabled() -> bool:
    try:
        return bool(load_settings().meta_learning_enabled)
    except Exception:
        return True  # fail-open


def _safe_publish(family_event: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(family_event, payload)
    except Exception as exc:
        logger.debug("meta_learning: event publish failed: %s", exc)


def generate_weekly_retrospective(*, now: datetime) -> dict[str, Any]:
    """Generate a weekly retrospective memo for the 7 days ending at `now`.

    Pipeline:
      1. Killswitch
      2. Compute window
      3. Aggregate all 5 AGI-spor (read-only)
      4. Build cheap-lane prompt
      5. Invoke cheap-lane
      6. Parse markdown output
      7. Persist memo row
      8. Emit memo_generated event
      9. Return structured result
    """
    if not _meta_learning_enabled():
        return {"status": "disabled", "note": "meta_learning is disabled"}

    period_end = now
    period_start = now - timedelta(days=7)

    # Import aggregators inside the function so monkeypatch in tests works
    from core.services.meta_learning_aggregator import (
        aggregate_world_model,
        aggregate_plan_revision,
        aggregate_curiosity,
        aggregate_skill_chain_phase2,
        aggregate_tool_invention,
    )

    try:
        snapshot = {
            "world_model": aggregate_world_model(since=period_start, until=period_end),
            "plan_revision": aggregate_plan_revision(since=period_start, until=period_end),
            "curiosity": aggregate_curiosity(since=period_start, until=period_end),
            "skill_chain_phase2": aggregate_skill_chain_phase2(since=period_start, until=period_end),
            "tool_invention": aggregate_tool_invention(since=period_start, until=period_end),
        }
    except Exception as exc:
        logger.warning("generate_weekly_retrospective: aggregator failed: %s", exc)
        return {"status": "error", "reason": f"aggregator error: {exc}"}

    prompt = _build_retrospective_prompt(
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        aggregator_snapshot=snapshot,
    )

    try:
        cheap_result = execute_public_safe_cheap_lane(message=prompt)
    except Exception as exc:
        logger.warning("generate_weekly_retrospective: cheap-lane failed: %s", exc)
        return {"status": "error", "reason": f"cheap-lane error: {exc}"}

    response_text = str(cheap_result.get("text") or "")
    model_used = str(cheap_result.get("model") or "")

    parsed = _parse_memo_markdown(response_text)
    narrative = parsed.get("narrative", "").strip()
    if not narrative:
        return {
            "status": "error",
            "reason": "cheap-lane returned empty narrative",
            "raw_response_excerpt": response_text[:200],
        }

    memo_id = f"memo-{uuid4().hex[:12]}"
    ts_iso = now.isoformat()
    candidates = parsed.get("hypothesis_candidates", [])

    _persist_memo(
        memo_id=memo_id,
        ts=ts_iso,
        period_start=period_start.isoformat(),
        period_end=period_end.isoformat(),
        narrative=narrative,
        hypothesis_candidates=candidates,
        aggregator_snapshot=snapshot,
        model_used=model_used,
    )

    _safe_publish("cognitive_meta_learning.memo_generated", {
        "memo_id": memo_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "hypothesis_count": len(candidates),
        "narrative_length": len(narrative),
        "model_used": model_used,
    })

    return {
        "status": "ok",
        "memo_id": memo_id,
        "ts": ts_iso,
        "narrative": narrative,
        "hypothesis_candidates": candidates,
        "model_used": model_used,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -v 2>&1 | tail -15
```

Expected: 23 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/meta_learning_retrospective.py tests/test_meta_learning.py
git commit -m "feat(meta-learning): persistence + generator end-to-end (cheap-lane + persist + event)"
```

---

## Task 6: ProducerSpec + tools + simple_tools registration

**Files:**
- Modify: `core/services/internal_cadence.py`
- Create: `core/tools/meta_learning_tools.py`
- Modify: `core/tools/simple_tools.py`
- Modify: `tests/test_meta_learning.py`

- [ ] **Step 1: Write failing tests for producer**

Append to `tests/test_meta_learning.py`:

```python
def test_producer_registered(clean_state):
    from core.services.internal_cadence import _producers, _ensure_producers_registered
    _ensure_producers_registered()
    assert "meta_learning_weekly_retrospective" in _producers
    spec = _producers["meta_learning_weekly_retrospective"]
    assert spec.cooldown_minutes == 10080
    assert spec.visible_grace_minutes == 60


def test_producer_skips_when_killswitch_off(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr
    from core.services.internal_cadence import _producers, _ensure_producers_registered

    class FakeSettings:
        meta_learning_enabled = False

    monkeypatch.setattr(mlr, "load_settings", lambda: FakeSettings())
    _ensure_producers_registered()
    spec = _producers["meta_learning_weekly_retrospective"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"


def test_producer_skips_when_recent_memo_exists(clean_state):
    """If last memo is <6.5 days old, producer skips."""
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo,
    )
    from core.services.internal_cadence import _producers, _ensure_producers_registered

    ensure_schema()
    recent_ts = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    _persist_memo(
        memo_id="memo-recent", ts=recent_ts,
        period_start="x", period_end="y",
        narrative="...", hypothesis_candidates=[], aggregator_snapshot={},
        model_used="m",
    )

    _ensure_producers_registered()
    spec = _producers["meta_learning_weekly_retrospective"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"
    assert "recent" in result["reason"].lower() or "<6.5" in result["reason"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "producer" -v 2>&1 | tail -8
```

Expected: 3 fail with `KeyError: 'meta_learning_weekly_retrospective'`.

- [ ] **Step 3: Register ProducerSpec in `internal_cadence.py`**

In `core/services/internal_cadence.py`, find the `curiosity_idle_window` register block (added earlier today). Add right after that block:

```python
    def _run_meta_learning_weekly(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Meta-læring Phase 1 (2026-05-12) — weekly retrospective.

        Skips if killswitch off, or if last memo is <6.5 days old.
        Søndag-vindue: prefer 04:00-06:00 UTC, but cooldown_minutes=10080
        is the real gate — this only adds a soft hour-of-day check.
        """
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime
        from datetime import timedelta as _timedelta
        from core.services.meta_learning_retrospective import (
            _meta_learning_enabled,
            generate_weekly_retrospective,
            fetch_latest_unacknowledged_memo,
        )
        from core.runtime.db import connect

        if not _meta_learning_enabled():
            return {"status": "skipped", "reason": "killswitch"}

        # Skip if last memo (any, not just unacknowledged) is <6.5 days old
        try:
            with connect() as conn:
                row = conn.execute(
                    "SELECT ts FROM learning_memos ORDER BY ts DESC LIMIT 1"
                ).fetchone()
            if row:
                last_ts = _datetime.fromisoformat(str(row["ts"]))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=_UTC)
                age = _datetime.now(_UTC) - last_ts
                if age < _timedelta(days=6, hours=12):
                    return {"status": "skipped", "reason": "recent memo exists (<6.5d)"}
        except Exception as exc:
            # If DB query fails (e.g., table doesn't exist yet), proceed to generate
            logger.debug("meta_learning producer: db check failed: %s", exc)

        return generate_weekly_retrospective(now=_datetime.now(_UTC))

    register_producer(ProducerSpec(
        name="meta_learning_weekly_retrospective",
        cooldown_minutes=10080,        # 7 dage
        visible_grace_minutes=60,
        run_fn=_run_meta_learning_weekly,
        priority=30,
        depends_on=[],
    ))
```

- [ ] **Step 4: Run producer tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "producer" -v 2>&1 | tail -8
```

Expected: 3 passed.

- [ ] **Step 5: Write failing tests for read/list tools**

Append to `tests/test_meta_learning.py`:

```python
def test_read_learning_memo_tool_validates_memo_id(clean_state):
    from core.tools.meta_learning_tools import _exec_read_learning_memo
    result = _exec_read_learning_memo({})
    assert result["status"] == "rejected"
    assert "memo_id" in result["reason"].lower()


def test_read_learning_memo_tool_missing_memo(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema
    from core.tools.meta_learning_tools import _exec_read_learning_memo
    ensure_schema()
    result = _exec_read_learning_memo({"memo_id": "memo-nonexistent"})
    assert result["status"] == "error"
    assert "not found" in result["reason"].lower()


def test_read_learning_memo_tool_killswitch(clean_state, monkeypatch):
    from core.tools import meta_learning_tools as m

    class FakeSettings:
        meta_learning_enabled = False

    monkeypatch.setattr(m, "load_settings", lambda: FakeSettings())
    result = m._exec_read_learning_memo({"memo_id": "any"})
    assert result["status"] == "disabled"


def test_read_learning_memo_tool_returns_full_memo_and_acknowledges(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema, _persist_memo
    from core.tools.meta_learning_tools import _exec_read_learning_memo
    from core.runtime.db import connect

    ensure_schema()
    _persist_memo(
        memo_id="memo-read", ts="2026-05-12T04:00:00+00:00",
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        narrative="Full narrative text here.",
        hypothesis_candidates=[{"id": "hyp-1", "statement": "x"}],
        aggregator_snapshot={"world_model": {}},
        model_used="fake",
    )

    result = _exec_read_learning_memo({"memo_id": "memo-read"})
    assert result["status"] == "ok"
    assert result["narrative"] == "Full narrative text here."
    assert result["hypothesis_candidates"][0]["statement"] == "x"

    # Side-effect: acknowledged_at now set
    with connect() as conn:
        row = conn.execute(
            "SELECT acknowledged_at FROM learning_memos WHERE memo_id = ?",
            ("memo-read",),
        ).fetchone()
    assert row["acknowledged_at"] is not None


def test_list_learning_memos_tool(clean_state):
    from core.services.meta_learning_retrospective import ensure_schema, _persist_memo
    from core.tools.meta_learning_tools import _exec_list_learning_memos

    ensure_schema()
    for i in range(3):
        _persist_memo(
            memo_id=f"memo-{i}",
            ts=f"2026-05-{10+i:02d}T04:00:00+00:00",
            period_start="x", period_end="y",
            narrative=f"narr {i}", hypothesis_candidates=[],
            aggregator_snapshot={}, model_used="m",
        )
    result = _exec_list_learning_memos({"limit": 2})
    assert result["status"] == "ok"
    assert len(result["memos"]) == 2
    assert result["memos"][0]["memo_id"] == "memo-2"  # newest first


def test_meta_learning_tools_registered_via_simple_tools():
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
    names = {(e.get("function") or {}).get("name") for e in TOOL_DEFINITIONS if isinstance(e, dict)}
    assert "read_learning_memo" in names
    assert "list_learning_memos" in names
    assert "read_learning_memo" in _TOOL_HANDLERS
    assert "list_learning_memos" in _TOOL_HANDLERS
```

- [ ] **Step 6: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "read_learning_memo or list_learning_memos or registered_via_simple_tools" -v 2>&1 | tail -10
```

Expected: 6 fail with `ModuleNotFoundError: core.tools.meta_learning_tools`.

- [ ] **Step 7: Create `core/tools/meta_learning_tools.py`**

```python
"""Meta-læring tools — Phase 1 (AGI track #3).

read_learning_memo(memo_id) — fetch full memo + mark as acknowledged.
list_learning_memos(limit=5) — overview of recent memos.

Mirror pattern from curiosity_tools and skill_chain_phase2 tools.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.services.meta_learning_retrospective import (
    acknowledge_memo,
    fetch_memo_by_id,
    list_recent_memos,
)

logger = logging.getLogger(__name__)


def _phase1_enabled() -> bool:
    try:
        return bool(load_settings().meta_learning_enabled)
    except Exception:
        return True  # fail-open


def _safe_publish(family_event: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(family_event, payload)
    except Exception as exc:
        logger.debug("meta_learning_tools: event publish failed: %s", exc)


def _exec_read_learning_memo(args: dict[str, Any]) -> dict[str, Any]:
    """Read full memo and acknowledge it."""
    if not _phase1_enabled():
        return {"status": "disabled", "note": "meta_learning is disabled"}

    memo_id = str(args.get("memo_id") or "").strip()
    if not memo_id:
        return {"status": "rejected", "reason": "memo_id is required"}

    memo = fetch_memo_by_id(memo_id)
    if not memo:
        return {"status": "error", "reason": f"memo not found: {memo_id}"}

    was_already_acked = memo.get("acknowledged_at") is not None
    acknowledge_memo(memo_id)

    if not was_already_acked:
        _safe_publish("cognitive_meta_learning.memo_acknowledged", {
            "memo_id": memo_id,
            "period_start": memo.get("period_start"),
            "period_end": memo.get("period_end"),
        })

    return {
        "status": "ok",
        "memo_id": memo_id,
        "period_start": memo.get("period_start"),
        "period_end": memo.get("period_end"),
        "narrative": memo.get("narrative"),
        "hypothesis_candidates": memo.get("hypothesis_candidates", []),
        "model_used": memo.get("model_used"),
        "was_already_acknowledged": was_already_acked,
    }


def _exec_list_learning_memos(args: dict[str, Any]) -> dict[str, Any]:
    if not _phase1_enabled():
        return {"status": "disabled", "note": "meta_learning is disabled"}
    try:
        limit = int(args.get("limit") or 5)
    except (TypeError, ValueError):
        limit = 5
    return {
        "status": "ok",
        "memos": list_recent_memos(limit=limit),
    }


META_LEARNING_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_learning_memo",
            "description": (
                "Læs et ugentligt meta-læringsmemo i fuld længde. Hver gang "
                "et nyt memo bliver genereret (søndag morgen), kan du se en "
                "kort teaser i awareness — kald dette tool for at læse hele "
                "memoet og se hypothesis-kandidater. Memo'et markeres som "
                "acknowledged så det ikke længere vises i awareness. "
                "Brug citationsnøgler i memoet (plan_id, prediction_id, "
                "obs_id, ISO-datotid) sammen med curiosity-tools for at "
                "grave i konkrete tilfælde."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "memo_id": {
                        "type": "string",
                        "description": "ID for memoet, fx 'memo-abc123'.",
                    },
                },
                "required": ["memo_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_learning_memos",
            "description": (
                "List dine seneste meta-læringsmemos (kort metadata, "
                "ikke fuld narrative). Bruges til at se historik og finde "
                "memo-IDs til read_learning_memo."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Antal memos (default 5, max 50).",
                    },
                },
                "required": [],
            },
        },
    },
]

META_LEARNING_TOOL_HANDLERS: dict[str, Any] = {
    "read_learning_memo": _exec_read_learning_memo,
    "list_learning_memos": _exec_list_learning_memos,
}
```

- [ ] **Step 8: Register in `simple_tools.py`**

In `core/tools/simple_tools.py`, find the existing `REVISE_SKILL_CHAIN_TOOL_DEFINITIONS` import block. Add right after that import:

```python
from core.tools.meta_learning_tools import (
    META_LEARNING_TOOL_DEFINITIONS,
    META_LEARNING_TOOL_HANDLERS,
)
```

Then in `TOOL_DEFINITIONS` list, find `*REVISE_SKILL_CHAIN_TOOL_DEFINITIONS,` and add right after it:

```python
    *META_LEARNING_TOOL_DEFINITIONS,
```

Then in `_TOOL_HANDLERS` dict, find `**REVISE_SKILL_CHAIN_TOOL_HANDLERS,` and add right after it:

```python
    **META_LEARNING_TOOL_HANDLERS,
```

- [ ] **Step 9: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -v 2>&1 | tail -10
```

Expected: 32 passed.

- [ ] **Step 10: Commit**

```bash
git add core/services/internal_cadence.py core/tools/meta_learning_tools.py core/tools/simple_tools.py tests/test_meta_learning.py
git commit -m "feat(meta-learning): ProducerSpec + read_learning_memo + list_learning_memos tools"
```

---

## Task 7: Awareness-injection + smoke + 30-day review

**Files:**
- Modify: `core/services/meta_learning_retrospective.py`
- Modify: `core/services/prompt_contract.py`
- Modify: `scripts/smoke_test_startup.py`
- Modify: `tests/test_meta_learning.py`

- [ ] **Step 1: Write failing tests for awareness**

Append to `tests/test_meta_learning.py`:

```python
def test_awareness_empty_when_no_memo(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, format_latest_unacknowledged_memo_for_awareness,
    )
    ensure_schema()
    assert format_latest_unacknowledged_memo_for_awareness() == ""


def test_awareness_empty_when_killswitch_off(clean_state, monkeypatch):
    from core.services import meta_learning_retrospective as mlr

    class FakeSettings:
        meta_learning_enabled = False
    monkeypatch.setattr(mlr, "load_settings", lambda: FakeSettings())
    assert mlr.format_latest_unacknowledged_memo_for_awareness() == ""


def test_awareness_shows_teaser_with_memo(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo,
        format_latest_unacknowledged_memo_for_awareness,
    )
    ensure_schema()
    _persist_memo(
        memo_id="memo-teaser",
        ts="2026-05-12T04:00:00+00:00",
        period_start="2026-05-05T00:00:00+00:00",
        period_end="2026-05-12T00:00:00+00:00",
        narrative="Det har været en interessant uge. Jeg har set at plan-abc123 "
                  "blev superseded hurtigt. Mit kalibreringsmønster er stabilt på "
                  "tværs af predictions.",
        hypothesis_candidates=[
            {"id": "hyp-1", "statement": "Vent længere før propose_plan"},
            {"id": "hyp-2", "statement": "Cap confidence"},
        ],
        aggregator_snapshot={}, model_used="m",
    )
    out = format_latest_unacknowledged_memo_for_awareness()
    assert "📓" in out
    assert "memo-teaser" in out
    assert "2 hypothesis" in out.lower() or "2 hypotheses" in out.lower() or "2 hypothesis-kandidater" in out.lower()
    assert "read_learning_memo" in out
    assert "Det har været en interessant uge" in out


def test_awareness_empty_after_acknowledge(clean_state):
    from core.services.meta_learning_retrospective import (
        ensure_schema, _persist_memo, acknowledge_memo,
        format_latest_unacknowledged_memo_for_awareness,
    )
    ensure_schema()
    _persist_memo(
        memo_id="memo-acked", ts="2026-05-12T04:00:00+00:00",
        period_start="x", period_end="y",
        narrative="...", hypothesis_candidates=[],
        aggregator_snapshot={}, model_used="m",
    )
    assert format_latest_unacknowledged_memo_for_awareness() != ""
    acknowledge_memo("memo-acked")
    assert format_latest_unacknowledged_memo_for_awareness() == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "awareness" -v 2>&1 | tail -8
```

Expected: 4 fail with `cannot import name 'format_latest_unacknowledged_memo_for_awareness'`.

- [ ] **Step 3: Add awareness-formatter to retrospective module**

Append to `core/services/meta_learning_retrospective.py`:

```python
# ---------------------------------------------------------------------------
# Awareness rendering (priority 39 in prompt_contract)
# ---------------------------------------------------------------------------

_TEASER_NARRATIVE_CHARS = 200


def _format_period_for_display(period_start: str, period_end: str) -> str:
    """Render period as 'YYYY-MM-DD to YYYY-MM-DD' for awareness display."""
    def _date(iso: str) -> str:
        try:
            return datetime.fromisoformat(iso).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return iso[:10] if iso else "?"
    return f"{_date(period_start)} to {_date(period_end)}"


def format_latest_unacknowledged_memo_for_awareness() -> str:
    """Render a short teaser for the most recent unacknowledged memo, or
    empty string if none exists / killswitch is off.

    Format:
      📓 Nyt ugentligt meta-læringsmemo (period 2026-05-05 to 2026-05-12):
      "<first 200 chars of narrative>..."

      N hypothesis-kandidater. Læs hele memoet via
      read_learning_memo(memo_id='memo-xyz').
    """
    if not _meta_learning_enabled():
        return ""
    memo = fetch_latest_unacknowledged_memo()
    if not memo:
        return ""

    narrative = str(memo.get("narrative") or "")
    teaser = narrative[:_TEASER_NARRATIVE_CHARS].rstrip()
    if len(narrative) > _TEASER_NARRATIVE_CHARS:
        teaser += "..."

    period_disp = _format_period_for_display(
        str(memo.get("period_start") or ""),
        str(memo.get("period_end") or ""),
    )
    n_hypotheses = len(memo.get("hypothesis_candidates") or [])
    memo_id = str(memo.get("memo_id") or "")

    return (
        f"📓 Nyt ugentligt meta-læringsmemo (period {period_disp}):\n"
        f'"{teaser}"\n'
        f"\n"
        f"{n_hypotheses} hypothesis-kandidater. Læs hele memoet via "
        f"read_learning_memo(memo_id='{memo_id}')."
    )
```

- [ ] **Step 4: Wire awareness-injection into `prompt_contract.py`**

In `core/services/prompt_contract.py`, find the curiosity-budget awareness block (priority 38, added earlier today). Add right after its closing `except Exception: pass`:

```python
    # Meta-læring Phase 1 (2026-05-12) — weekly retrospective teaser (AGI #3)
    try:
        from core.services.meta_learning_retrospective import (
            format_latest_unacknowledged_memo_for_awareness,
        )
        _awareness_add(
            39,
            "meta-learning weekly retrospective teaser",
            format_latest_unacknowledged_memo_for_awareness() or None,
        )
    except Exception:
        pass
```

- [ ] **Step 5: Run awareness tests to verify they pass**

```bash
conda run -n ai pytest tests/test_meta_learning.py -k "awareness" -v 2>&1 | tail -8
```

Expected: 4 passed.

- [ ] **Step 6: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the Skill Chain Phase 2 smoke block (added earlier today). Add right after its closing `except Exception: traceback.print_exc()`:

```python
        # Meta-læring Phase 1 — AGI track #3 (added 2026-05-12)
        try:
            from core.services.meta_learning_retrospective import (  # noqa: F401
                ensure_schema,
                generate_weekly_retrospective,
                fetch_latest_unacknowledged_memo,
                fetch_memo_by_id,
                list_recent_memos,
                acknowledge_memo,
                format_latest_unacknowledged_memo_for_awareness,
                _build_retrospective_prompt,
                _parse_memo_markdown,
            )
            from core.services.meta_learning_aggregator import (  # noqa: F401
                aggregate_world_model,
                aggregate_plan_revision,
                aggregate_curiosity,
                aggregate_skill_chain_phase2,
                aggregate_tool_invention,
            )
            from core.tools.meta_learning_tools import (  # noqa: F401
                META_LEARNING_TOOL_DEFINITIONS,
                META_LEARNING_TOOL_HANDLERS,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _ml_names = {
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            }
            for _n in ("read_learning_memo", "list_learning_memos"):
                if _n not in _ml_names:
                    raise RuntimeError(f"{_n} missing from TOOL_DEFINITIONS")
                if _n not in _TOOL_HANDLERS:
                    raise RuntimeError(f"{_n} missing from _TOOL_HANDLERS")
            ensure_schema()
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 7: Run all affected test suites — verify no regression**

```bash
conda run -n ai pytest tests/test_meta_learning.py tests/test_skill_chain_phase2.py tests/test_curiosity_budget.py tests/test_plan_revision.py tests/test_multistep_planner.py tests/test_tool_invention.py tests/test_world_model_loop.py 2>&1 | tail -12
```

Expected: all green (~190 tests with ~5 skipped from earlier suites).

Also run Phase 1 skill_chain regression test:

```bash
conda run -n ai pytest tests/tools/test_skill_chain.py 2>&1 | tail -5
```

Expected: 14 passed.

- [ ] **Step 8: Run smoke test**

```bash
conda run -n ai python scripts/smoke_test_startup.py 2>&1 | tail -20
```

Expected: no tracebacks; smoke completes.

- [ ] **Step 9: Production probe**

```bash
conda run -n ai python -c "
from core.services.internal_cadence import _producers, _ensure_producers_registered
_ensure_producers_registered()
assert 'meta_learning_weekly_retrospective' in _producers
print('OK: meta_learning ProducerSpec registered')

from core.tools.simple_tools import TOOL_DEFINITIONS
names = {(e.get('function') or {}).get('name') for e in TOOL_DEFINITIONS if isinstance(e, dict)}
for n in ('read_learning_memo', 'list_learning_memos'):
    assert n in names
print('OK: read_learning_memo + list_learning_memos in TOOL_DEFINITIONS')

# Confirm all 5 prior AGI tracks still callable
from core.services.plan_proposals import revise_plan
from core.services.world_model_signal_tracking import record_runtime_world_model_prediction
from core.services.curiosity_budget import curiosity_enabled
from core.tools.skill_chain_propose_tool import _exec_propose_skill_chain
from core.tools.skill_chain_revise_tool import _exec_revise_skill_chain
print('OK: all 5 prior AGI tracks still callable')

from core.eventbus.events import ALLOWED_EVENT_FAMILIES
assert 'cognitive_meta_learning' in ALLOWED_EVENT_FAMILIES
print('OK: cognitive_meta_learning event family allowed')
"
```

Expected: 4 OK lines.

- [ ] **Step 10: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Meta-laering Phase 1 (AGI track #3) — 30-day review: '
    'memo-generation rate (4 forventet paa 4 uger); '
    'read-rate (hvor mange memos blev acknowledged inden for 24h?); '
    'time-to-acknowledge median; '
    'hypothesis-candidate count distribution — klumper det sig ved 0 eller 3? '
    'citationsnoegle-brug — bruger Jarvis dem via curiosity-tools? '
    'hypothesis-quality (manuel review af ~12 hypoteser fra 4 memos) — testbare? '
    'apophenia-tegn — bruger cheap-lane outliers korrekt? '
    'Beslutninger: hvis hypothesis-count altid 3 -> cheap-lane føler sig forpligtet, juster prompt; '
    'hvis read-rate <50%% -> teaser ikke synligt nok, overvej staerkere awareness-signal; '
    'hvis Jarvis ikke bruger citationsnoegler -> Phase 2 mister sin grund; '
    'hvis hypothesis-kvalitet er lav -> forfin prompt med eksempler.'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='meta_learning_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 11: Commit + restart**

```bash
git add core/services/meta_learning_retrospective.py core/services/prompt_contract.py scripts/smoke_test_startup.py tests/test_meta_learning.py
git commit -m "chore(meta-learning): awareness injection (priority 39) + smoke imports + 30-day review"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flag `meta_learning_enabled` | Task 1 |
| Event family `cognitive_meta_learning` in ALLOWED | Task 1 |
| DB schema `learning_memos` + index | Task 1 (schema bootstrap) |
| Schema-bootstrap in service (Boy Scout) | Task 1 |
| `aggregate_world_model` with outliers | Task 2 |
| `aggregate_plan_revision` with outliers | Task 2 |
| `aggregate_curiosity` with outliers | Task 3 |
| `aggregate_skill_chain_phase2` with outliers | Task 3 |
| `aggregate_tool_invention` (proxy via plans w/ skill_data) | Task 3 |
| All aggregators window-filtered + read-only | Tasks 2, 3 |
| Prompt builder with personality + citation instruction | Task 4 |
| Defensive markdown parser (fence-tolerant) | Task 4 |
| Parser tolerates malformed hypothesis-blok | Task 4 |
| Generator end-to-end (killswitch → aggregate → prompt → cheap-lane → parse → persist → event) | Task 5 |
| Cheap-lane exception handling | Task 5 |
| Persistence (`_persist_memo`, fetch_*, acknowledge) | Task 5 |
| `cognitive_meta_learning.memo_generated` event | Task 5 |
| ProducerSpec `meta_learning_weekly_retrospective` | Task 6 |
| Cooldown 10080 min + visible_grace 60 min | Task 6 |
| Skip if last memo <6.5d old | Task 6 |
| `read_learning_memo` tool with acknowledge-side-effect | Task 6 |
| `list_learning_memos` tool | Task 6 |
| `cognitive_meta_learning.memo_acknowledged` event | Task 6 |
| Register both tools via simple_tools splat | Task 6 |
| Awareness-injection priority 39 (teaser format) | Task 7 |
| Awareness empty when killswitch/no-memo/acknowledged | Task 7 |
| Smoke imports + tool-registration check | Task 7 |
| 30-day review schedule (2026-06-12) | Task 7 |
| Restart verification | Task 7 |
| Backwards-compat: all 5 prior AGI tracks callable | Task 7 step 9 (probe) |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete. All commands have expected output.

**Type consistency:**
- `aggregate_world_model(*, since: datetime, until: datetime) -> dict[str, Any]` — Tasks 2, 5
- `aggregate_plan_revision(*, since, until) -> dict[str, Any]` — Tasks 2, 5
- `aggregate_curiosity(*, since, until) -> dict[str, Any]` — Tasks 3, 5
- `aggregate_skill_chain_phase2(*, since, until) -> dict[str, Any]` — Tasks 3, 5
- `aggregate_tool_invention(*, since, until) -> dict[str, Any]` — Tasks 3, 5
- `ensure_schema() -> None` — Tasks 1, 2, 3, 5, 6, 7
- `_build_retrospective_prompt(*, period_start, period_end, aggregator_snapshot) -> str` — Tasks 4, 5
- `_parse_memo_markdown(text: str) -> dict[str, Any]` — Tasks 4, 5
- `_persist_memo(...) -> str` — Tasks 5, 6, 7
- `fetch_latest_unacknowledged_memo() -> dict | None` — Tasks 5, 7
- `fetch_memo_by_id(memo_id) -> dict | None` — Tasks 5, 6
- `acknowledge_memo(memo_id) -> bool` — Tasks 5, 6, 7
- `list_recent_memos(limit) -> list[dict]` — Tasks 5, 6
- `generate_weekly_retrospective(*, now: datetime) -> dict[str, Any]` — Tasks 5, 6
- `format_latest_unacknowledged_memo_for_awareness() -> str` — Task 7
- `_meta_learning_enabled() -> bool` — Tasks 5, 6, 7
- `_exec_read_learning_memo(args) -> dict` — Task 6
- `_exec_list_learning_memos(args) -> dict` — Task 6
- Event names consistent: `cognitive_meta_learning.memo_generated`, `cognitive_meta_learning.memo_acknowledged`
- Tool names consistent in defs, handlers, tests, smoke probe

**Backwards-compat verified:**
- `db.py` not modified (Boy Scout) — schema-bootstrap in retrospective module
- All 5 prior AGI tracks read-only queried by aggregator (verified by Task 7 step 9 probe)
- Phase 1 skill_chain tests still run (Task 7 step 7)
- Awareness priority 39 sits between existing 38 (curiosity) and 40 (turn changelog) — no reorder
- Killswitch=False reverts: producer skips, tools fail-soft, awareness empty
- No new DB tables outside `learning_memos`, no new daemons outside the producer
- `cognitive_meta_learning` is the only new event family — added to ALLOWED set
