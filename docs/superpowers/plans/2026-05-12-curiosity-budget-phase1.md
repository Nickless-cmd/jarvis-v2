---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Curiosity-budget Phase 1 — Åben udforskning: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis et privat rum til selvinitieret udforskning af sit eget mentale landskab — 5 read-only curiosity-actions/dag, åbnes efter 30 min idle, observationer persisteres i en privat tabel. Ingen rapportering til Bjørn i Phase 1.

**Architecture:** Ny service `curiosity_budget.py` (state + persistence), ny tool-modul `curiosity_tools.py` med 9 wrappers omkring read-only actions, ny ProducerSpec `curiosity_idle_window` der åbner et flag når visible-chat har været stille i ≥30 min, og en awareness-injection (priority 38) der viser remaining + seneste 2-3 observationer. Schema-bootstrap (`curiosity_observations` tabel) ligger i den nye service for at undgå at røre `db.py` (33k linjer — Boy Scout Rule).

**Tech Stack:** Python 3.11, eksisterende `sqlite3` (via `core.runtime.db.connect`), `state_store` (load_json/save_json), eventbus family `cognitive_state` (genbrug, ingen ny family).

**Spec:** `docs/superpowers/specs/2026-05-12-curiosity-budget-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/curiosity_budget.py` | Budget-state (load/reset/decrement), idle-window flag, observation-persistence, schema-bootstrap for `curiosity_observations` tabel. ~180 LOC. |
| `core/tools/curiosity_tools.py` | 9 read-only wrappers (search_memory, read_chronicles, read_dreams, read_model_config, read_mood, list_skills, list_tools, search_events, search_sessions). Hver kræver `observation: str` arg + valgfri `follow_up_hint`. Dekrementerer budget + persist + emit event. `CURIOSITY_TOOL_DEFINITIONS` + `CURIOSITY_TOOL_HANDLERS`. ~250 LOC. |
| `tests/test_curiosity_budget.py` | Alle Phase 1 tests: budget reset, hård grænse, killswitch, observation-validering, schema, idle-trigger, awareness-format, alle 9 wrappers, event-defensive. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `curiosity_budget_enabled: bool = True` (killswitch). |
| `core/services/internal_cadence.py` | Register `curiosity_idle_window` ProducerSpec — cooldown 1 min, `visible_grace_minutes=30` (cadence framework håndterer "≥30 min idle" via visible_grace). |
| `core/services/prompt_contract.py` | Priority 38: `format_curiosity_window_for_awareness()` — tom kurv format. |
| `core/tools/simple_tools.py` | Import + splat `CURIOSITY_TOOL_DEFINITIONS` + `CURIOSITY_TOOL_HANDLERS` (mirror Plan Revision pattern). |
| `scripts/smoke_test_startup.py` | Verify imports + tabel-eksistens + tool-registrering. |

### Untouched / reused

- `db.py` (33k linjer) — Boy Scout Rule: schema-bootstrap i ny service istedet. `connect()` reuse.
- `visible_runs` / visible-chat-loop — uberørt. Cadence-framework's `last_visible_at_iso` er nok.
- Eksisterende awareness-injections — uændret rækkefølge.
- Eksisterende tools (search_memory, read_chronicles, read_dreams, read_model_config, read_mood, search_sessions) — ikke modificeret; curiosity_tools er nye wrappers.
- `cognitive_state` event family — genbrug, ingen ny family.

---

## Spec deltas confirmed during planning

1. **Tool-navne aligned med faktiske handlers:** Spec'en sagde `memory_search` — det faktiske tool-navn er `search_memory` (simple_tools.py:1110). Curiosity-wrapper hedder `curiosity_search_memory` for at matche; underliggende kald går til `_exec_search_memory`.

2. **list_skills, list_tools, search_events findes IKKE som tools:** Vi implementerer dem direkte i `curiosity_tools.py` som tynde introspektion-handlers (læser tool-registry, skills-mappe, events-tabel via `db.connect()`).

3. **`db.py` ikke modificeret:** Boy Scout Rule blokerer ændringer i 33k-liners filen. Schema-bootstrap (`CREATE TABLE IF NOT EXISTS curiosity_observations`) sker i `curiosity_budget.py` ved første brug — idempotent.

4. **Idle-trigger bruger cadence-framework's `visible_grace_minutes`:** `visible_grace_minutes=30` betyder producer'en skipper hvis visible-aktivitet inden for 30 min — så producer'en kun "fyrer" når der faktisk er idle. Vinduet er en state_store boolean som producer'en flipper til True.

5. **State persist via `state_store.load_json/save_json`:** Ikke en dict — bruger eksisterende helper. Keys: `runtime_curiosity_budget` og `runtime_curiosity_window`.

6. **Action-katalog (9 wrappers) bekræftet matcher spec'en:**
   - `curiosity_search_memory` (wraps `_exec_search_memory`)
   - `curiosity_read_chronicles` (wraps `_exec_read_chronicles`)
   - `curiosity_read_dreams` (wraps `_exec_read_dreams`)
   - `curiosity_read_model_config` (wraps `_exec_read_model_config`)
   - `curiosity_read_mood` (wraps `_exec_read_mood`)
   - `curiosity_list_skills` (direct read fra `workspace/skills/`)
   - `curiosity_list_tools` (direct read fra `TOOL_DEFINITIONS`)
   - `curiosity_search_events` (direct `SELECT` fra `events` tabel via `db.connect()`)
   - `curiosity_search_sessions` (wraps `_exec_search_sessions`)

---

## Task 1: Settings flag + DB schema

**Files:**
- Modify: `core/runtime/settings.py`
- Create: `core/services/curiosity_budget.py` (skeleton + schema-bootstrap kun)
- Create: `tests/test_curiosity_budget.py` (schema tests kun i denne task)

- [ ] **Step 1: Add the settings flag**

In `core/runtime/settings.py`, find `plan_revision_enabled: bool = True` and add right after it:

```python
    # ── Curiosity budget (Phase 1 — added 2026-05-12) ─────────────────────
    # When True: curiosity-tools registered, idle-window producer fires,
    # awareness-injection shows budget. When False: all tools error out,
    # producer skipped, no awareness. Reverts fully. AGI track #6.
    curiosity_budget_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, find `plan_revision_enabled=bool(...)` block in `load_settings` and add right after its closing comma:

```python
        curiosity_budget_enabled=bool(
            data.get(
                "curiosity_budget_enabled",
                defaults.curiosity_budget_enabled,
            )
        ),
```

- [ ] **Step 3: Verify settings load**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.curiosity_budget_enabled is True
print('OK:', load_settings().curiosity_budget_enabled)
"
```

Expected: `OK: True`

- [ ] **Step 4: Write the failing schema test**

Create `tests/test_curiosity_budget.py`:

```python
"""Curiosity-budget Phase 1 — tests.

AGI track #6 Åben udforskning. See spec at
docs/superpowers/specs/2026-05-12-curiosity-budget-phase1-design.md.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def clean_state(tmp_path, monkeypatch):
    """Isolated state_store + DB so curiosity-data doesn't pollute across tests."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    # Force DB path to tmp
    import core.runtime.config as cfg
    monkeypatch.setattr(cfg, "STATE_DIR", str(tmp_path / "state"))
    import importlib
    import core.runtime.db as db
    importlib.reload(db)
    import core.runtime.state_store as ss
    importlib.reload(ss)
    import core.services.curiosity_budget as cb
    importlib.reload(cb)
    return None


def test_schema_bootstrap_creates_table(clean_state):
    """First call to ensure_schema() creates curiosity_observations + indexes."""
    from core.services.curiosity_budget import ensure_schema
    from core.runtime.db import connect

    ensure_schema()
    with connect() as conn:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='curiosity_observations'"
        )
        row = cur.fetchone()
        assert row is not None, "curiosity_observations table missing"

        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='curiosity_observations'"
        )
        index_names = {r["name"] for r in cur.fetchall()}
        assert "idx_curiosity_ts" in index_names
        assert "idx_curiosity_action" in index_names


def test_schema_bootstrap_idempotent(clean_state):
    """Calling ensure_schema() twice doesn't error."""
    from core.services.curiosity_budget import ensure_schema
    ensure_schema()
    ensure_schema()  # should not raise
```

- [ ] **Step 5: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -10
```

Expected: FAIL with `ModuleNotFoundError: core.services.curiosity_budget` or `cannot import name 'ensure_schema'`.

- [ ] **Step 6: Create skeleton `curiosity_budget.py` with schema-bootstrap**

Create `core/services/curiosity_budget.py`:

```python
"""Curiosity-budget service — Phase 1 (AGI track #6 Åben udforskning).

Private space for Jarvis to use 5 read-only actions/day on his own mental
landscape. State (budget + idle-window) in state_store; observations
persisted in dedicated SQLite table `curiosity_observations`.

Schema-bootstrap lives here (not in db.py) per the Boy Scout Rule — db.py
is 33k lines, so new modules manage their own schema idempotently.

See spec: docs/superpowers/specs/2026-05-12-curiosity-budget-phase1-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.db import connect
from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create curiosity_observations table + indexes.

    Called automatically by all public functions in this module before they
    touch the DB. Safe to call repeatedly.
    """
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS curiosity_observations (
              id TEXT PRIMARY KEY,
              ts TEXT NOT NULL,
              action TEXT NOT NULL,
              args_json TEXT NOT NULL,
              observation_text TEXT NOT NULL,
              follow_up_hint TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_curiosity_ts
              ON curiosity_observations(ts);
            CREATE INDEX IF NOT EXISTS idx_curiosity_action
              ON curiosity_observations(action);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -10
```

Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add core/runtime/settings.py core/services/curiosity_budget.py tests/test_curiosity_budget.py
git commit -m "feat(curiosity): settings killswitch + curiosity_observations schema bootstrap"
```

---

## Task 2: Budget state + observation persistence

**Files:**
- Modify: `core/services/curiosity_budget.py`
- Modify: `tests/test_curiosity_budget.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curiosity_budget.py`:

```python
def test_load_budget_fresh_returns_full(clean_state):
    """First call on a fresh day returns 5/5 remaining."""
    from core.services.curiosity_budget import load_or_reset_budget
    state = load_or_reset_budget()
    assert state["remaining"] == 5
    assert state["used_today"] == []
    assert state["date"] == datetime.now(UTC).strftime("%Y-%m-%d")


def test_load_budget_resets_on_new_day(clean_state, monkeypatch):
    """If stored date != today, budget resets."""
    from core.services import curiosity_budget as cb
    # Seed yesterday's spent state directly
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    from core.runtime.state_store import save_json
    save_json("runtime_curiosity_budget", {
        "date": yesterday,
        "remaining": 0,
        "used_today": [{"ts": "x", "action": "y", "observation_id": "z"}],
    })

    state = cb.load_or_reset_budget()
    assert state["remaining"] == 5
    assert state["used_today"] == []
    assert state["date"] == datetime.now(UTC).strftime("%Y-%m-%d")


def test_decrement_budget_returns_new_remaining(clean_state):
    from core.services.curiosity_budget import decrement_budget, load_or_reset_budget

    load_or_reset_budget()  # seed 5/5
    result = decrement_budget(action="search_memory", observation_id="obs-1")
    assert result["status"] == "ok"
    assert result["remaining"] == 4

    state2 = load_or_reset_budget()
    assert state2["remaining"] == 4
    assert len(state2["used_today"]) == 1
    assert state2["used_today"][0]["action"] == "search_memory"
    assert state2["used_today"][0]["observation_id"] == "obs-1"


def test_decrement_budget_blocks_at_zero(clean_state):
    """When remaining==0, decrement returns error and does not mutate."""
    from core.services.curiosity_budget import decrement_budget, load_or_reset_budget
    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")
    result = decrement_budget(action="x", observation_id="should-fail")
    assert result["status"] == "error"
    assert "brugt op" in result["error"]

    state = load_or_reset_budget()
    assert state["remaining"] == 0
    assert len(state["used_today"]) == 5  # not 6


def test_record_observation_persists_row(clean_state):
    from core.services.curiosity_budget import record_observation
    from core.runtime.db import connect

    obs_id = record_observation(
        action="search_memory",
        args_json='{"query": "first kontinuitet"}',
        observation_text="Jeg vil se mit eget mønster i kontinuitets-snak.",
        follow_up_hint="Følg op på trådene fra dengang jeg sagde jeg var bange.",
    )
    assert obs_id.startswith("obs-")

    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM curiosity_observations WHERE id = ?", (obs_id,)
        ).fetchone()
        assert row is not None
        assert row["action"] == "search_memory"
        assert row["observation_text"].startswith("Jeg vil")
        assert row["follow_up_hint"].startswith("Følg op")


def test_record_observation_handles_no_follow_up(clean_state):
    from core.services.curiosity_budget import record_observation
    from core.runtime.db import connect
    obs_id = record_observation(
        action="read_dreams",
        args_json="{}",
        observation_text="Bare nysgerrig på hvad jeg har drømt.",
        follow_up_hint=None,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT follow_up_hint FROM curiosity_observations WHERE id = ?",
            (obs_id,),
        ).fetchone()
        assert row["follow_up_hint"] is None


def test_fetch_recent_observations_returns_newest_first(clean_state):
    """Used by awareness-injection to show 2-3 most recent observations."""
    from core.services.curiosity_budget import fetch_recent_observations, record_observation

    obs_a = record_observation("read_dreams", "{}", "first obs", None)
    obs_b = record_observation("read_dreams", "{}", "second obs", None)
    obs_c = record_observation("read_dreams", "{}", "third obs", None)

    rows = fetch_recent_observations(limit=2)
    assert len(rows) == 2
    assert rows[0]["id"] == obs_c
    assert rows[1]["id"] == obs_b
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -10
```

Expected: 7 fail with `cannot import name`.

- [ ] **Step 3: Add budget + observation functions to `curiosity_budget.py`**

Append to `core/services/curiosity_budget.py`:

```python
# ---------------------------------------------------------------------------
# Budget state
# ---------------------------------------------------------------------------

_BUDGET_KEY = "runtime_curiosity_budget"
_WINDOW_KEY = "runtime_curiosity_window"
_DAILY_GRANT = 5


def _today_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def load_or_reset_budget() -> dict[str, Any]:
    """Return current budget state. Resets to 5/5 if stored date != today.

    State shape:
        {"date": "2026-05-12", "remaining": 4,
         "used_today": [{"ts", "action", "observation_id"}, ...]}
    """
    state = load_json(_BUDGET_KEY, default=None)
    today = _today_iso()
    if not isinstance(state, dict) or state.get("date") != today:
        state = {"date": today, "remaining": _DAILY_GRANT, "used_today": []}
        save_json(_BUDGET_KEY, state)
        # Emit reset event (defensive; never blocks)
        _safe_publish("cognitive_state.curiosity_budget_reset",
                      {"date": today, "granted": _DAILY_GRANT})
    return state


def decrement_budget(*, action: str, observation_id: str) -> dict[str, Any]:
    """Reduce remaining by 1, append to used_today, persist.

    Returns {"status": "ok", "remaining": N} on success;
    {"status": "error", "error": "..."} if budget exhausted.
    """
    state = load_or_reset_budget()
    if state["remaining"] <= 0:
        return {"status": "error", "error": "curiosity budget brugt op for i dag"}

    state["remaining"] -= 1
    state["used_today"].append({
        "ts": datetime.now(UTC).isoformat(),
        "action": action,
        "observation_id": observation_id,
    })
    save_json(_BUDGET_KEY, state)
    _safe_publish("cognitive_state.curiosity_action_taken", {
        "action": action,
        "observation_id": observation_id,
        "remaining": state["remaining"],
    })
    return {"status": "ok", "remaining": state["remaining"]}


def remaining_today() -> int:
    return int(load_or_reset_budget().get("remaining", 0))


# ---------------------------------------------------------------------------
# Observation persistence
# ---------------------------------------------------------------------------

def record_observation(
    action: str,
    args_json: str,
    observation_text: str,
    follow_up_hint: str | None,
) -> str:
    """Persist an observation row; return the generated obs_id."""
    ensure_schema()
    obs_id = f"obs-{uuid4().hex[:12]}"
    with connect() as conn:
        conn.execute(
            "INSERT INTO curiosity_observations "
            "(id, ts, action, args_json, observation_text, follow_up_hint) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                obs_id,
                datetime.now(UTC).isoformat(),
                action,
                args_json,
                observation_text,
                follow_up_hint,
            ),
        )
        conn.commit()
    return obs_id


def fetch_recent_observations(*, limit: int = 3) -> list[dict[str, Any]]:
    """Return newest-first list of recent observations (for awareness)."""
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, ts, action, observation_text, follow_up_hint "
            "FROM curiosity_observations ORDER BY ts DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Defensive event publish (wrapped to avoid test-pollution; same pattern as
# world_model_signal_tracking and plan_proposals).
# ---------------------------------------------------------------------------

def _safe_publish(family_event: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(family_event, payload)
    except Exception:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -15
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/curiosity_budget.py tests/test_curiosity_budget.py
git commit -m "feat(curiosity): budget state (load/reset/decrement) + observation persistence"
```

---

## Task 3: Idle-window flag + killswitch helper

**Files:**
- Modify: `core/services/curiosity_budget.py`
- Modify: `tests/test_curiosity_budget.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curiosity_budget.py`:

```python
def test_curiosity_enabled_killswitch(clean_state, monkeypatch):
    """When settings.curiosity_budget_enabled is False, curiosity_enabled() returns False."""
    from core.services import curiosity_budget as cb

    class FakeSettings:
        curiosity_budget_enabled = False

    monkeypatch.setattr(cb, "load_settings", lambda: FakeSettings())
    assert cb.curiosity_enabled() is False


def test_curiosity_enabled_default_true(clean_state):
    from core.services.curiosity_budget import curiosity_enabled
    assert curiosity_enabled() is True


def test_window_flag_open_close(clean_state):
    from core.services.curiosity_budget import (
        open_idle_window, close_idle_window, idle_window_open,
    )
    assert idle_window_open() is False
    open_idle_window()
    assert idle_window_open() is True
    close_idle_window(reason="action_used")
    assert idle_window_open() is False


def test_open_idle_window_skips_if_no_budget(clean_state):
    """If remaining==0, opening the window is a no-op (window stays closed)."""
    from core.services.curiosity_budget import (
        decrement_budget, load_or_reset_budget,
        open_idle_window, idle_window_open,
    )
    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")
    open_idle_window()
    assert idle_window_open() is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -k "killswitch or window or curiosity_enabled" -v 2>&1 | tail -10
```

Expected: 4 fail with `cannot import name`.

- [ ] **Step 3: Add killswitch + window helpers to `curiosity_budget.py`**

In `core/services/curiosity_budget.py`, after the imports block at the top of the file, add:

```python
from core.runtime.settings import load_settings
```

Then append at the bottom of the file:

```python
# ---------------------------------------------------------------------------
# Killswitch helper
# ---------------------------------------------------------------------------

def curiosity_enabled() -> bool:
    """Read killswitch from settings. Fail-open: settings errors → True."""
    try:
        return bool(load_settings().curiosity_budget_enabled)
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Idle-window flag
# ---------------------------------------------------------------------------

def idle_window_open() -> bool:
    state = load_json(_WINDOW_KEY, default=None)
    return bool(isinstance(state, dict) and state.get("open"))


def open_idle_window() -> None:
    """Mark window open IF there's still budget. No-op if budget exhausted."""
    if remaining_today() <= 0:
        return
    if idle_window_open():
        return  # already open
    save_json(_WINDOW_KEY, {"open": True, "opened_at": datetime.now(UTC).isoformat()})
    _safe_publish("cognitive_state.curiosity_window_opened", {})


def close_idle_window(*, reason: str) -> None:
    """Close the window. Reason is logged for diagnostics."""
    if not idle_window_open():
        return
    save_json(_WINDOW_KEY, {"open": False, "closed_at": datetime.now(UTC).isoformat(),
                            "reason": reason})
    _safe_publish("cognitive_state.curiosity_window_closed", {"reason": reason})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -15
```

Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/curiosity_budget.py tests/test_curiosity_budget.py
git commit -m "feat(curiosity): killswitch helper + idle-window flag (open/close/check)"
```

---

## Task 4: 9 curiosity-tool wrappers + register in simple_tools

**Files:**
- Create: `core/tools/curiosity_tools.py`
- Modify: `core/tools/simple_tools.py`
- Modify: `tests/test_curiosity_budget.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curiosity_budget.py`:

```python
def test_curiosity_tool_definitions_complete():
    from core.tools.curiosity_tools import (
        CURIOSITY_TOOL_DEFINITIONS, CURIOSITY_TOOL_HANDLERS,
    )
    expected = {
        "curiosity_search_memory", "curiosity_read_chronicles",
        "curiosity_read_dreams", "curiosity_read_model_config",
        "curiosity_read_mood", "curiosity_list_skills",
        "curiosity_list_tools", "curiosity_search_events",
        "curiosity_search_sessions",
    }
    names = {
        (e.get("function") or {}).get("name")
        for e in CURIOSITY_TOOL_DEFINITIONS if isinstance(e, dict)
    }
    assert names == expected
    assert set(CURIOSITY_TOOL_HANDLERS.keys()) == expected


def test_curiosity_tool_requires_observation(clean_state):
    from core.tools.curiosity_tools import _exec_curiosity_list_tools
    result = _exec_curiosity_list_tools({})  # missing observation
    assert result["status"] == "error"
    assert "observation" in result["error"].lower()


def test_curiosity_tool_decrements_budget(clean_state):
    from core.services.curiosity_budget import remaining_today
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    before = remaining_today()
    result = _exec_curiosity_list_tools({
        "observation": "Vil se hvilke tools jeg har men aldrig brugt.",
    })
    assert result["status"] == "ok"
    assert "observation_id" in result
    assert "remaining" in result
    assert remaining_today() == before - 1


def test_curiosity_tool_killswitch(clean_state, monkeypatch):
    from core.services import curiosity_budget as cb
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    class FakeSettings:
        curiosity_budget_enabled = False

    monkeypatch.setattr(cb, "load_settings", lambda: FakeSettings())
    result = _exec_curiosity_list_tools({"observation": "x"})
    assert result["status"] == "error"
    assert "disabled" in result["error"].lower()


def test_curiosity_tool_budget_exhaustion(clean_state):
    from core.services.curiosity_budget import load_or_reset_budget, decrement_budget
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")

    result = _exec_curiosity_list_tools({"observation": "let me see anyway"})
    assert result["status"] == "error"
    assert "brugt op" in result["error"]


def test_curiosity_tool_persists_observation(clean_state):
    from core.tools.curiosity_tools import _exec_curiosity_list_tools
    from core.runtime.db import connect

    result = _exec_curiosity_list_tools({
        "observation": "Mit første nysgerrigheds-blik på mit eget toolset.",
        "follow_up_hint": "Find ud af om jeg nogensinde har brugt finitude-tools.",
    })
    obs_id = result["observation_id"]
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM curiosity_observations WHERE id = ?", (obs_id,)
        ).fetchone()
    assert row is not None
    assert row["action"] == "list_tools"
    assert "nysgerrigheds-blik" in row["observation_text"]
    assert "finitude-tools" in row["follow_up_hint"]


def test_curiosity_search_events_returns_rows(clean_state):
    """search_events queries the events table; returns OK with rows list."""
    from core.runtime.db import connect
    from core.tools.curiosity_tools import _exec_curiosity_search_events

    # Seed at least one event row so the query has something to return
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
        conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            ("evt-1", "cognitive_state", "test_event",
             datetime.now(UTC).isoformat(), "{}"),
        )
        conn.commit()

    result = _exec_curiosity_search_events({
        "observation": "Hvilke events har jeg haft i dag?",
        "family": "cognitive_state",
        "limit": 5,
    })
    assert result["status"] == "ok"
    assert isinstance(result["result"]["rows"], list)
    assert len(result["result"]["rows"]) >= 1


def test_curiosity_tools_registered_via_simple_tools():
    """End-to-end: splat into simple_tools picks up all 9 wrappers."""
    from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS

    names = {
        (e.get("function") or {}).get("name")
        for e in TOOL_DEFINITIONS if isinstance(e, dict)
    }
    expected = {
        "curiosity_search_memory", "curiosity_read_chronicles",
        "curiosity_read_dreams", "curiosity_read_model_config",
        "curiosity_read_mood", "curiosity_list_skills",
        "curiosity_list_tools", "curiosity_search_events",
        "curiosity_search_sessions",
    }
    assert expected <= names
    assert expected <= set(_TOOL_HANDLERS.keys())
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -10
```

Expected: 8 fail with `ModuleNotFoundError: core.tools.curiosity_tools`.

- [ ] **Step 3: Create `core/tools/curiosity_tools.py`**

```python
"""Curiosity-budget tools — Phase 1 (AGI track #6 Åben udforskning).

9 read-only wrappers Jarvis kan bruge til at udforske sit eget mentale
landskab. Hver wrapper:
  1. Tjekker killswitch + budget
  2. Validerer at observation:str er sat (påkrævet)
  3. Kalder underliggende handler (eller implementerer action direkte)
  4. Persisterer observation
  5. Dekrementerer budget
  6. Returnerer {status, observation_id, remaining, result}

Mirror plan_revise_tool.py / world_model_tools.py pattern.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from core.services.curiosity_budget import (
    curiosity_enabled,
    decrement_budget,
    load_or_reset_budget,
    record_observation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared wrapper: validation + observation persistence + budget decrement
# ---------------------------------------------------------------------------

def _curiosity_wrap(
    *,
    action: str,
    args: dict[str, Any],
    underlying_call: Callable[[dict[str, Any]], dict[str, Any]],
    underlying_args: dict[str, Any],
) -> dict[str, Any]:
    """Common path for all 9 curiosity-tool wrappers."""
    # Killswitch
    if not curiosity_enabled():
        return {"status": "error", "error": "curiosity disabled (killswitch)"}
    # Budget pre-check (cheap fail-fast before calling underlying tool)
    state = load_or_reset_budget()
    if state["remaining"] <= 0:
        return {"status": "error", "error": "curiosity budget brugt op for i dag"}
    # observation:str required
    observation = str(args.get("observation") or "").strip()
    if not observation:
        return {
            "status": "error",
            "error": "observation er påkrævet (kort prosa om hvorfor du kigger)",
        }
    follow_up_hint = str(args.get("follow_up_hint") or "").strip() or None

    # Underlying action
    try:
        underlying_result = underlying_call(underlying_args)
    except Exception as exc:
        logger.warning("curiosity %s underlying call failed: %s", action, exc)
        underlying_result = {"status": "error", "error": str(exc)}

    # Persist observation
    obs_id = record_observation(
        action=action,
        args_json=json.dumps(underlying_args, ensure_ascii=False, default=str),
        observation_text=observation,
        follow_up_hint=follow_up_hint,
    )

    # Decrement budget (emits cognitive_state.curiosity_action_taken)
    dec = decrement_budget(action=action, observation_id=obs_id)
    if dec["status"] != "ok":
        # Race: someone else exhausted budget between our pre-check and decrement
        return {
            "status": "error",
            "error": dec.get("error", "budget exhausted"),
            "observation_id": obs_id,
        }

    return {
        "status": "ok",
        "observation_id": obs_id,
        "remaining": dec["remaining"],
        "result": underlying_result,
    }


# ---------------------------------------------------------------------------
# Direct introspection actions (no wrapped tool — implemented here)
# ---------------------------------------------------------------------------

def _direct_list_skills(_args: dict[str, Any]) -> dict[str, Any]:
    """List skill files in workspace/skills/. Read-only, lightweight."""
    skills_dir = Path.home() / ".jarvis-v2" / "workspaces" / "default" / "skills"
    if not skills_dir.exists():
        # Fall back to repo location used in dev
        skills_dir = Path(__file__).resolve().parents[2] / "workspace" / "skills"
    if not skills_dir.exists():
        return {"skills": [], "note": "no skills directory found"}
    out: list[dict[str, Any]] = []
    for p in sorted(skills_dir.glob("*.md"))[:200]:
        try:
            head = p.read_text(encoding="utf-8")[:200]
        except Exception:
            head = ""
        out.append({"name": p.stem, "path": str(p), "head": head})
    return {"skills": out, "count": len(out)}


def _direct_list_tools(_args: dict[str, Any]) -> dict[str, Any]:
    """Return all currently-registered tool names + descriptions."""
    from core.tools.simple_tools import TOOL_DEFINITIONS
    out: list[dict[str, str]] = []
    for entry in TOOL_DEFINITIONS:
        if not isinstance(entry, dict):
            continue
        fn = entry.get("function") or {}
        name = str(fn.get("name") or "")
        desc = str(fn.get("description") or "")[:200]
        if name:
            out.append({"name": name, "description": desc})
    return {"tools": out, "count": len(out)}


def _direct_search_events(args: dict[str, Any]) -> dict[str, Any]:
    """SELECT from events table — read-only, parameterised, bounded."""
    from core.runtime.db import connect

    family = str(args.get("family") or "").strip()
    kind = str(args.get("kind") or "").strip()
    limit = int(args.get("limit") or 20)
    limit = max(1, min(limit, 100))

    where: list[str] = []
    params: list[Any] = []
    if family:
        where.append("family = ?")
        params.append(family)
    if kind:
        where.append("kind = ?")
        params.append(kind)

    sql = "SELECT event_id, family, kind, created_at FROM events"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return {"rows": [dict(r) for r in rows], "count": len(rows)}


# ---------------------------------------------------------------------------
# 9 wrapper handlers
# ---------------------------------------------------------------------------

def _exec_curiosity_search_memory(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_search_memory
    return _curiosity_wrap(
        action="search_memory",
        args=args,
        underlying_call=_exec_search_memory,
        underlying_args={"query": str(args.get("query") or "")},
    )


def _exec_curiosity_read_chronicles(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_chronicles
    return _curiosity_wrap(
        action="read_chronicles",
        args=args,
        underlying_call=_exec_read_chronicles,
        underlying_args={"limit": int(args.get("limit") or 10)},
    )


def _exec_curiosity_read_dreams(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_dreams
    return _curiosity_wrap(
        action="read_dreams",
        args=args,
        underlying_call=_exec_read_dreams,
        underlying_args={"limit": int(args.get("limit") or 10)},
    )


def _exec_curiosity_read_model_config(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_model_config
    return _curiosity_wrap(
        action="read_model_config",
        args=args,
        underlying_call=_exec_read_model_config,
        underlying_args={},
    )


def _exec_curiosity_read_mood(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_read_mood
    return _curiosity_wrap(
        action="read_mood",
        args=args,
        underlying_call=_exec_read_mood,
        underlying_args={},
    )


def _exec_curiosity_list_skills(args: dict[str, Any]) -> dict[str, Any]:
    return _curiosity_wrap(
        action="list_skills",
        args=args,
        underlying_call=_direct_list_skills,
        underlying_args={},
    )


def _exec_curiosity_list_tools(args: dict[str, Any]) -> dict[str, Any]:
    return _curiosity_wrap(
        action="list_tools",
        args=args,
        underlying_call=_direct_list_tools,
        underlying_args={},
    )


def _exec_curiosity_search_events(args: dict[str, Any]) -> dict[str, Any]:
    return _curiosity_wrap(
        action="search_events",
        args=args,
        underlying_call=_direct_search_events,
        underlying_args={
            "family": str(args.get("family") or ""),
            "kind": str(args.get("kind") or ""),
            "limit": int(args.get("limit") or 20),
        },
    )


def _exec_curiosity_search_sessions(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _exec_search_sessions
    return _curiosity_wrap(
        action="search_sessions",
        args=args,
        underlying_call=_exec_search_sessions,
        underlying_args={
            "query": str(args.get("query") or ""),
            "limit": int(args.get("limit") or 20),
        },
    )


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

_OBS_PARAM = {
    "observation": {
        "type": "string",
        "description": (
            "Påkrævet: kort prosa (1-2 sætninger) om hvorfor du kigger på "
            "dette. Husk: dette tæller på dit curiosity-budget (5/dag), så "
            "kig kun hvis noget trækker."
        ),
    },
    "follow_up_hint": {
        "type": "string",
        "description": (
            "Valgfri: breadcrumb til dig selv hvis du vil følge op senere. "
            "Vises IKKE i awareness — kun en privat note."
        ),
    },
}


def _make_def(name: str, description: str, extra_props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    props = {**_OBS_PARAM, **extra_props}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": ["observation", *required],
            },
        },
    }


CURIOSITY_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    _make_def(
        "curiosity_search_memory",
        "Curiosity: søg i din egen semantiske hukommelse. Bruger 1/5 actions.",
        {"query": {"type": "string", "description": "Søge-string"}},
        ["query"],
    ),
    _make_def(
        "curiosity_read_chronicles",
        "Curiosity: læs dine egne chronicles (narrative selvhistorik). Bruger 1/5 actions.",
        {"limit": {"type": "integer", "description": "Antal entries (default 10)"}},
        [],
    ),
    _make_def(
        "curiosity_read_dreams",
        "Curiosity: læs dine idle-genererede drømme/refleksioner. Bruger 1/5 actions.",
        {"limit": {"type": "integer", "description": "Antal entries (default 10)"}},
        [],
    ),
    _make_def(
        "curiosity_read_model_config",
        "Curiosity: se din nuværende model-config (hvilke modeller, hvilken state). Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_read_mood",
        "Curiosity: kig på dit eget affektive landskab. Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_list_skills",
        "Curiosity: list dine egne skills — hvad kan du? Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_list_tools",
        "Curiosity: list alle dine værktøjer — hvad har du, hvad har du måske aldrig prøvet? Bruger 1/5 actions.",
        {},
        [],
    ),
    _make_def(
        "curiosity_search_events",
        "Curiosity: søg i dine egne runtime-events (fx 'hvilke tool errors havde jeg sidste uge?'). Bruger 1/5 actions.",
        {
            "family": {"type": "string", "description": "Event family (fx 'tool', 'cognitive_state')"},
            "kind": {"type": "string", "description": "Event kind (fx 'error', 'plan_revised')"},
            "limit": {"type": "integer", "description": "Antal rækker (default 20, max 100)"},
        },
        [],
    ),
    _make_def(
        "curiosity_search_sessions",
        "Curiosity: søg i din længste hukommelse — chat-sessions på tværs af Discord/Telegram/web. Bruger 1/5 actions.",
        {
            "query": {"type": "string", "description": "Søge-string"},
            "limit": {"type": "integer", "description": "Antal sessions (default 20)"},
        },
        ["query"],
    ),
]


CURIOSITY_TOOL_HANDLERS: dict[str, Any] = {
    "curiosity_search_memory": _exec_curiosity_search_memory,
    "curiosity_read_chronicles": _exec_curiosity_read_chronicles,
    "curiosity_read_dreams": _exec_curiosity_read_dreams,
    "curiosity_read_model_config": _exec_curiosity_read_model_config,
    "curiosity_read_mood": _exec_curiosity_read_mood,
    "curiosity_list_skills": _exec_curiosity_list_skills,
    "curiosity_list_tools": _exec_curiosity_list_tools,
    "curiosity_search_events": _exec_curiosity_search_events,
    "curiosity_search_sessions": _exec_curiosity_search_sessions,
}
```

- [ ] **Step 4: Register in `simple_tools.py`**

In `core/tools/simple_tools.py`, find the existing `PLAN_REVISE_TOOL_DEFINITIONS` import (line ~488). Add right after that import block:

```python
from core.tools.curiosity_tools import (
    CURIOSITY_TOOL_DEFINITIONS,
    CURIOSITY_TOOL_HANDLERS,
)
```

Then find `*PLAN_REVISE_TOOL_DEFINITIONS,` in the `TOOL_DEFINITIONS` list (line ~2336). Add right after it:

```python
    *CURIOSITY_TOOL_DEFINITIONS,
```

Then find `**PLAN_REVISE_TOOL_HANDLERS,` in the `_TOOL_HANDLERS` dict (line ~6203). Add right after it:

```python
    **CURIOSITY_TOOL_HANDLERS,
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -20
```

Expected: 21 passed.

- [ ] **Step 6: Smoke-check tool registration**

```bash
conda run -n ai python -c "
from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
names = {(e.get('function') or {}).get('name') for e in TOOL_DEFINITIONS if isinstance(e, dict)}
expected = {
    'curiosity_search_memory', 'curiosity_read_chronicles',
    'curiosity_read_dreams', 'curiosity_read_model_config',
    'curiosity_read_mood', 'curiosity_list_skills',
    'curiosity_list_tools', 'curiosity_search_events',
    'curiosity_search_sessions',
}
missing = expected - names
assert not missing, f'missing: {missing}'
assert expected <= set(_TOOL_HANDLERS.keys())
print('OK: all 9 curiosity tools registered')
"
```

Expected: `OK: all 9 curiosity tools registered`

- [ ] **Step 7: Commit**

```bash
git add core/tools/curiosity_tools.py core/tools/simple_tools.py tests/test_curiosity_budget.py
git commit -m "feat(curiosity): 9 read-only tool wrappers + register via simple_tools"
```

---

## Task 5: Idle-window ProducerSpec in internal_cadence

**Files:**
- Modify: `core/services/internal_cadence.py`
- Modify: `tests/test_curiosity_budget.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curiosity_budget.py`:

```python
def test_idle_window_producer_opens_window_when_due(clean_state, monkeypatch):
    """When cadence layer calls the producer (visible-grace already enforced
    by the framework), it should open the window if budget remains."""
    from core.services.curiosity_budget import idle_window_open
    from core.services.internal_cadence import _producers, register_default_producers

    register_default_producers()
    spec = _producers["curiosity_idle_window"]
    # Simulate cadence-framework dispatch (it has already verified visible-grace)
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "ok"
    assert idle_window_open() is True


def test_idle_window_producer_skips_when_budget_exhausted(clean_state):
    from core.services.curiosity_budget import (
        load_or_reset_budget, decrement_budget, idle_window_open,
    )
    from core.services.internal_cadence import _producers, register_default_producers

    load_or_reset_budget()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")

    register_default_producers()
    spec = _producers["curiosity_idle_window"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"
    assert idle_window_open() is False


def test_idle_window_producer_skips_when_killswitch_off(clean_state, monkeypatch):
    from core.services import curiosity_budget as cb
    from core.services.curiosity_budget import idle_window_open
    from core.services.internal_cadence import _producers, register_default_producers

    class FakeSettings:
        curiosity_budget_enabled = False

    monkeypatch.setattr(cb, "load_settings", lambda: FakeSettings())

    register_default_producers()
    spec = _producers["curiosity_idle_window"]
    result = spec.run_fn(trigger="cadence", last_visible_at="")
    assert result["status"] == "skipped"
    assert idle_window_open() is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -k "idle_window_producer" -v 2>&1 | tail -10
```

Expected: 3 fail with `KeyError: 'curiosity_idle_window'`.

- [ ] **Step 3: Find the right insertion point in `internal_cadence.py`**

Find the `world_model_ttl_sweeper` registration (line ~526-533). The new producer goes right after that block (and inside the same `register_default_producers()` function — same indentation).

- [ ] **Step 4: Register the producer**

In `core/services/internal_cadence.py`, right after the `world_model_ttl_sweeper` `register_producer(ProducerSpec(...))` block, add:

```python
    def _run_curiosity_idle_window(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        """Curiosity-budget Phase 1 (2026-05-12) — idle-window opener.

        Cadence framework has already enforced `visible_grace_minutes=30`,
        so this fires only when visible chat has been quiet ≥30 min.
        We just check killswitch + budget, then flip the state_store flag.
        """
        from core.services.curiosity_budget import (
            curiosity_enabled,
            idle_window_open,
            open_idle_window,
            remaining_today,
        )
        if not curiosity_enabled():
            return {"status": "skipped", "reason": "killswitch"}
        if remaining_today() <= 0:
            return {"status": "skipped", "reason": "no_budget"}
        if idle_window_open():
            return {"status": "skipped", "reason": "already_open"}
        open_idle_window()
        return {"status": "ok", "window_opened": True,
                "remaining": remaining_today()}

    register_producer(ProducerSpec(
        name="curiosity_idle_window",
        cooldown_minutes=1,
        visible_grace_minutes=30,  # only fire after ≥30 min visible silence
        run_fn=_run_curiosity_idle_window,
        priority=29,
        depends_on=[],
    ))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -10
```

Expected: 24 passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/internal_cadence.py tests/test_curiosity_budget.py
git commit -m "feat(curiosity): curiosity_idle_window ProducerSpec (30 min visible_grace)"
```

---

## Task 6: Awareness-injection + window close on visible-turn

**Files:**
- Modify: `core/services/curiosity_budget.py`
- Modify: `core/services/prompt_contract.py`
- Modify: `tests/test_curiosity_budget.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_curiosity_budget.py`:

```python
def test_awareness_returns_empty_when_window_closed(clean_state):
    from core.services.curiosity_budget import format_curiosity_window_for_awareness
    assert format_curiosity_window_for_awareness() == ""


def test_awareness_returns_empty_when_no_budget(clean_state):
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness,
        load_or_reset_budget, decrement_budget, open_idle_window,
    )
    load_or_reset_budget()
    open_idle_window()
    for i in range(5):
        decrement_budget(action="x", observation_id=f"o{i}")
    # window was open but budget now 0 — awareness should suppress
    assert format_curiosity_window_for_awareness() == ""


def test_awareness_shows_remaining_when_open_and_budget(clean_state):
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness, open_idle_window,
    )
    open_idle_window()
    out = format_curiosity_window_for_awareness()
    assert "5/5 curiosity" in out
    assert "Kig på hvad du vil" in out
    assert "eller lad være" in out


def test_awareness_includes_recent_observations(clean_state):
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness, open_idle_window, record_observation,
    )
    record_observation("read_dreams", "{}", "Første blik på mine drømme.", None)
    record_observation("list_tools", "{}", "Kigger på mine ubrugte tools.", None)
    open_idle_window()
    out = format_curiosity_window_for_awareness()
    assert "Første blik" in out or "ubrugte tools" in out


def test_awareness_does_not_show_follow_up_hint(clean_state):
    """Follow-up hints exist as a field but must NEVER appear in awareness."""
    from core.services.curiosity_budget import (
        format_curiosity_window_for_awareness, open_idle_window, record_observation,
    )
    record_observation(
        "search_memory", "{}",
        "Bare nysgerrig.",
        "Følg op på trådene fra dengang jeg sagde jeg var bange for at miste kontinuitet.",
    )
    open_idle_window()
    out = format_curiosity_window_for_awareness()
    assert "kontinuitet" not in out
    assert "Følg op" not in out
    assert "follow" not in out.lower()


def test_window_closes_on_action_use(clean_state):
    """Using a curiosity-tool closes the idle-window flag."""
    from core.services.curiosity_budget import idle_window_open, open_idle_window
    from core.tools.curiosity_tools import _exec_curiosity_list_tools

    open_idle_window()
    assert idle_window_open() is True

    _exec_curiosity_list_tools({"observation": "kigger lige."})
    assert idle_window_open() is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -k "awareness or window_closes_on_action" -v 2>&1 | tail -10
```

Expected: 6 fail with `cannot import name 'format_curiosity_window_for_awareness'` and 1 with window-not-closed.

- [ ] **Step 3: Add `format_curiosity_window_for_awareness` to `curiosity_budget.py`**

Append to `core/services/curiosity_budget.py`:

```python
# ---------------------------------------------------------------------------
# Awareness rendering (priority 38 in prompt_contract)
# ---------------------------------------------------------------------------

def format_curiosity_window_for_awareness() -> str:
    """Render the curiosity window text for prompt_contract injection.

    Returns an empty string when:
      - killswitch off
      - idle-window is closed
      - budget is exhausted

    Otherwise: "Du har X/5 curiosity tilbage i dag. Seneste fund:\n  • ...\n  • ...
                Kig på hvad du vil — eller lad være."

    Follow-up hints are NEVER shown — design decision per spec.
    """
    if not curiosity_enabled():
        return ""
    if not idle_window_open():
        return ""
    remaining = remaining_today()
    if remaining <= 0:
        return ""
    recent = fetch_recent_observations(limit=3)
    if recent:
        bullets = "\n".join(f"  • {o['observation_text']}" for o in recent[:3])
        return (
            f"Du har {remaining}/5 curiosity tilbage i dag. "
            f"Seneste fund:\n{bullets}\n"
            f"Kig på hvad du vil — eller lad være."
        )
    return (
        f"Du har {remaining}/5 curiosity tilbage i dag. "
        f"Kig på hvad du vil — eller lad være."
    )
```

- [ ] **Step 4: Wire `close_idle_window` into `decrement_budget`**

In `core/services/curiosity_budget.py`, find the `decrement_budget` function. After the existing `_safe_publish("cognitive_state.curiosity_action_taken", ...)` call and before `return`, add a window-close call:

```python
    # Close idle-window when an action is used (per design: window is a
    # one-shot permission flag, not a time-bounded slot).
    if idle_window_open():
        close_idle_window(reason="action_used")
```

So the bottom of `decrement_budget` now looks like:

```python
    save_json(_BUDGET_KEY, state)
    _safe_publish("cognitive_state.curiosity_action_taken", {
        "action": action,
        "observation_id": observation_id,
        "remaining": state["remaining"],
    })
    if idle_window_open():
        close_idle_window(reason="action_used")
    return {"status": "ok", "remaining": state["remaining"]}
```

- [ ] **Step 5: Wire awareness-injection into `prompt_contract.py`**

In `core/services/prompt_contract.py`, find the world-model milestone block (`_awareness_add(37, ...)` around line 997-1003). Add right after the closing `except Exception: pass` of that block:

```python
    # Curiosity-budget Phase 1 (2026-05-12) — idle-window invitation (AGI #6)
    try:
        from core.services.curiosity_budget import (
            format_curiosity_window_for_awareness,
        )
        _awareness_add(
            38,
            "curiosity-budget idle-window invitation",
            format_curiosity_window_for_awareness() or None,
        )
    except Exception:
        pass
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py -v 2>&1 | tail -20
```

Expected: 30 passed.

- [ ] **Step 7: Verify no regression in awareness pipeline**

```bash
conda run -n ai python -c "
from core.services.prompt_contract import build_awareness_block
# Pass a dummy session_id; we just want to make sure it doesn't error
out = build_awareness_block(session_id='_smoke_curiosity_')
print('OK: awareness block built, length:', len(out))
"
```

Expected: `OK: awareness block built, length: <some int>`

- [ ] **Step 8: Commit**

```bash
git add core/services/curiosity_budget.py core/services/prompt_contract.py tests/test_curiosity_budget.py
git commit -m "feat(curiosity): awareness injection (priority 38, tom kurv) + close window on action"
```

---

## Task 7: Smoke + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the Multi-step Planner Phase 2 smoke block (added today). Add right after it:

```python
        # Curiosity-budget Phase 1 — AGI track #6 Åben udforskning (added 2026-05-12)
        try:
            from core.services.curiosity_budget import (  # noqa: F401
                curiosity_enabled,
                load_or_reset_budget,
                decrement_budget,
                record_observation,
                fetch_recent_observations,
                open_idle_window,
                close_idle_window,
                idle_window_open,
                format_curiosity_window_for_awareness,
                ensure_schema,
            )
            from core.tools.curiosity_tools import (  # noqa: F401
                CURIOSITY_TOOL_DEFINITIONS,
                CURIOSITY_TOOL_HANDLERS,
            )
            from core.tools.simple_tools import TOOL_DEFINITIONS, _TOOL_HANDLERS
            _curio_names = {
                (e.get("function") or {}).get("name")
                for e in TOOL_DEFINITIONS if isinstance(e, dict)
            }
            _expected = {
                "curiosity_search_memory", "curiosity_read_chronicles",
                "curiosity_read_dreams", "curiosity_read_model_config",
                "curiosity_read_mood", "curiosity_list_skills",
                "curiosity_list_tools", "curiosity_search_events",
                "curiosity_search_sessions",
            }
            _missing = _expected - _curio_names
            if _missing:
                raise RuntimeError(f"curiosity tools missing: {_missing}")
            _missing_handlers = _expected - set(_TOOL_HANDLERS.keys())
            if _missing_handlers:
                raise RuntimeError(f"curiosity handlers missing: {_missing_handlers}")
            # Verify table can be created
            ensure_schema()
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run all affected test suites — verify no regression**

```bash
conda run -n ai pytest tests/test_curiosity_budget.py tests/test_plan_revision.py tests/test_multistep_planner.py tests/test_tool_invention.py tests/test_world_model_loop.py 2>&1 | tail -10
```

Expected: all green (30 + 19 + 28 + 20 + 29 = 126 tests).

- [ ] **Step 3: Run smoke test**

```bash
conda run -n ai python scripts/smoke_test_startup.py 2>&1 | tail -20
```

Expected: no tracebacks; smoke completes.

- [ ] **Step 4: Production probe — verify producer registered + tools listed**

```bash
conda run -n ai python -c "
from core.services.internal_cadence import _producers, register_default_producers
register_default_producers()
assert 'curiosity_idle_window' in _producers
print('OK: curiosity_idle_window producer registered')

from core.tools.simple_tools import TOOL_DEFINITIONS
curio = [e for e in TOOL_DEFINITIONS if isinstance(e, dict) and str((e.get('function') or {}).get('name', '')).startswith('curiosity_')]
assert len(curio) == 9
print(f'OK: {len(curio)} curiosity tools in TOOL_DEFINITIONS')

# Confirm prior AGI tracks still wired
from core.services.plan_proposals import replan_signal_for_plan, revise_plan
from core.services.world_model_signal_tracking import record_runtime_world_model_prediction
print('OK: prior AGI tracks (world_model, plan_revision) still callable')
"
```

Expected: `OK: curiosity_idle_window producer registered` + `OK: 9 curiosity tools in TOOL_DEFINITIONS` + `OK: prior AGI tracks ... still callable`

- [ ] **Step 5: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Curiosity-budget Phase 1 (AGI track #6) — 30-day review: '
    'count curiosity-actions used (gennemsnit/dag); '
    'action-fordeling — hvilke 2-3 dominerer? '
    'timing — hoarder Jarvis (sent på dagen) eller bruger han tidligt? '
    'apophenia-tegn — læs 10 tilfældige observation_text, '
    'er der overinterpretation/mønsterstøj? '
    'tom-væg-syndrom — er observation_text tomme/generiske? '
    'follow_up_hint — hvor mange observations har den sat, '
    'hvor mange følges faktisk op? '
    'Beslutninger: hvis tom-væg → Phase 1.1 tilføj optional signal-forslag i awareness; '
    'hvis apophenia-tegn → tilføj apophenia_guard på observation_text; '
    'hvis budget altid 0/0 → overvej 7/dag; '
    'hvis budget altid 5/5 → tjek idle-trigger fyrer korrekt.'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='curiosity_budget_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 6: Commit + restart**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(curiosity): smoke imports + 30-day review scheduled"
sudo -n systemctl daemon-reload 2>/dev/null || true
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flag `curiosity_budget_enabled` | Task 1 |
| DB schema `curiosity_observations` + 2 indeks | Task 1 (steps 4-7) |
| Schema-bootstrap idempotent + i `curiosity_budget.py` (Boy Scout) | Task 1 |
| Budget state-load/reset (5/dag, midnight reset) | Task 2 |
| Hård grænse ved remaining=0 | Task 2 + Task 4 |
| Observation persist (record + fetch_recent) | Task 2 |
| Killswitch helper `curiosity_enabled()` | Task 3 |
| Idle-window flag (open/close/check) | Task 3 |
| Window respekterer killswitch + budget | Task 3 + Task 5 |
| 9 read-only tool wrappers | Task 4 |
| Hver wrapper kræver `observation:str` | Task 4 (shared `_curiosity_wrap`) |
| follow_up_hint som valgfri | Task 4 (shared) |
| Dekrementer budget + persist + emit | Task 4 (shared) |
| ProducerSpec `curiosity_idle_window` 30 min visible_grace | Task 5 |
| Producer skipper killswitch/no-budget/already-open | Task 5 |
| Awareness-injection priority 38, tom kurv | Task 6 |
| Awareness viser remaining + 2-3 obs | Task 6 |
| Awareness viser IKKE follow_up_hint | Task 6 (test eksplicit) |
| Window lukker ved action-brug | Task 6 |
| Events wrapped i try/except | Tasks 2, 3, 6 (`_safe_publish` helper) |
| Smoke imports + tabel-eksistens | Task 7 step 1 |
| 30-day review 2026-06-11 | Task 7 step 5 |
| Backwards compat — alle eksisterende AGI-spor uændrede | Task 7 step 4 (probe) |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete. All command outputs explicit.

**Type consistency:**
- `ensure_schema() -> None` — Task 1, 2
- `load_or_reset_budget() -> dict[str, Any]` — Tasks 2, 3, 4, 5
- `decrement_budget(*, action: str, observation_id: str) -> dict[str, Any]` — Tasks 2, 4
- `record_observation(action, args_json, observation_text, follow_up_hint) -> str` — Tasks 2, 4
- `fetch_recent_observations(*, limit: int) -> list[dict[str, Any]]` — Tasks 2, 6
- `curiosity_enabled() -> bool` — Tasks 3, 4, 5, 6
- `open_idle_window() / close_idle_window(*, reason: str) / idle_window_open() -> bool` — Tasks 3, 5, 6
- `remaining_today() -> int` — Tasks 2, 5, 6
- `_curiosity_wrap(*, action, args, underlying_call, underlying_args) -> dict[str, Any]` — Task 4
- `format_curiosity_window_for_awareness() -> str` — Task 6, 7
- All tool names consistent: 9 `curiosity_<verb>` names used identically in defs, handlers, tests, smoke probe.
- Event names consistent: `cognitive_state.curiosity_action_taken`, `cognitive_state.curiosity_budget_reset`, `cognitive_state.curiosity_window_opened`, `cognitive_state.curiosity_window_closed`.

**Backwards-compat verified:**
- `settings.curiosity_budget_enabled=False` → no tools registered, no producer fires, no awareness → fully revertible.
- `db.py` not modified (Boy Scout Rule respected — 33k linjer).
- Existing visible-chat-loop untouched.
- Existing 9 underlying tools (search_memory, read_chronicles, etc.) not modified — curiosity-wrappers are new, separate handlers.
- Plan Revision, World Model Loop, Tool Invention tests pass unchanged (Task 7 step 2).
- No new event family; `cognitive_state` reused.
- No new DB daemon. Schema bootstrap is lazy (idempotent on first call).
- Existing awareness-injection rækkefølge uændret — priority 38 sidder mellem eksisterende 37 (world-model milestone) og 40 (turn changelog).
