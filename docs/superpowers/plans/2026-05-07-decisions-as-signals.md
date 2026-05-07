# Decisions as Signals — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the always-on rule-text in `[VERIFICATION]` (`enforcement_section()`) with a signal-fired `[FIRED_DECISIONS]` section that appears only when registered triggers detect contextual relevance for a behavioral decision.

**Architecture:** Hybrid trigger registry. Code-defined trigger functions register at import time; `behavioral_decisions.trigger_name` references them by name. Per-decision cooldown (seconds or turns) tracked in `runtime_state_kv`. Killswitch via `decision_signals_enabled` setting; rollback restores the old `enforcement_section()` output.

**Tech Stack:** Python 3.11, SQLite, FastAPI runtime, contextvars for per-run state, eventbus.

**Spec:** `docs/superpowers/specs/2026-05-07-decisions-as-signals-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/decision_signals.py` | Registry, types, `evaluate_decision_triggers()`, `fired_decisions_section()`, `build_trigger_context()`, ContextVar |
| `core/services/decision_triggers/__init__.py` | Imports all trigger modules so they self-register |
| `core/services/decision_triggers/loop_nudge.py` | `loop_nudge_5_rounds` trigger |
| `core/services/decision_triggers/backend_unresolved.py` | `backend_unresolved_3_calls` trigger |
| `tests/services/test_decision_signals.py` | Registry, evaluation, cooldown, killswitch |
| `tests/services/test_decision_triggers.py` | Per-trigger behavior |
| `tests/integration/test_decision_signals_in_prompt.py` | End-to-end through `build_visible_chat_prompt_assembly` |
| `tests/runtime/test_decision_signals_migration.py` | DB migration + existing-decision update |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `decision_signals_enabled: bool = True` |
| `core/eventbus/events.py` | Add `decision_signal` to `ALLOWED_EVENT_FAMILIES` |
| `core/runtime/db.py` | New `_ensure_decision_trigger_column()` helper called from `init_db()`; updates 2 known decisions with `trigger_name`. Idempotent. |
| `core/runtime/db_decisions.py` | `list_decisions` and `get_decision` return `trigger_name` |
| `core/services/behavioral_decisions.py` | `get_decision_with_reviews()` includes `trigger_name`, `last_fired_at` |
| `core/services/decision_enforcement.py` | `enforcement_section()` returns empty string when killswitch is on (default) |
| `core/services/prompt_contract.py` | Replace `enforcement_section()` call with `fired_decisions_section()`; add `fired_decisions` AWARENESS category |
| `core/services/visible_runs.py` | Bind `_current_trigger_context` ContextVar before prompt assembly call |
| `core/tools/decisions_tools.py` | `decision_get` returns trigger_name + last_fired (no separate prose changes) |
| `scripts/smoke_test_startup.py` | Verify `_TRIGGER_REGISTRY` populates after import |

---

## Task 1: Settings flag + event family

**Files:**
- Modify: `core/runtime/settings.py`
- Modify: `core/eventbus/events.py`

- [ ] **Step 1: Add settings flag**

In `core/runtime/settings.py`, add inside `RuntimeSettings` (after the existing `anthropic_compat_*` fields, before `extra`):

```python
    # Decisions-as-signals refactor (added 2026-05-07)
    # When True (default), behavioral decisions appear in prompt only when
    # their registered trigger fires. When False, the legacy
    # enforcement_section() runs as before — instant rollback path.
    decision_signals_enabled: bool = True
```

- [ ] **Step 2: Add event family**

In `core/eventbus/events.py`, add to `ALLOWED_EVENT_FAMILIES` set (next to `tool_router`):

```python
    "decision_signal",  # decisions-as-signals refactor (added 2026-05-07)
```

- [ ] **Step 3: Verify imports still work**

Run: `conda run -n ai python -c "from core.runtime.settings import RuntimeSettings; from core.eventbus.events import ALLOWED_EVENT_FAMILIES; print('decision_signal' in ALLOWED_EVENT_FAMILIES, RuntimeSettings().decision_signals_enabled)"`
Expected: `True True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py core/eventbus/events.py
git commit -m "feat(decision-signals): settings flag + event family"
```

---

## Task 2: DB migration

**Files:**
- Modify: `core/runtime/db.py`
- Modify: `core/runtime/db_decisions.py`
- Test: `tests/runtime/test_decision_signals_migration.py`

- [ ] **Step 1: Write failing test**

Create `tests/runtime/test_decision_signals_migration.py`:

```python
"""Verify trigger_name column gets added and known decisions get wired."""
import sqlite3

from core.runtime.db import _ensure_decision_trigger_column


def _setup_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS behavioral_decisions (
          decision_id TEXT PRIMARY KEY,
          directive TEXT, rationale TEXT, trigger_cue TEXT,
          status TEXT, priority INTEGER,
          created_at TEXT, updated_at TEXT, last_reviewed_at TEXT,
          adherence_score REAL,
          source_record_id TEXT, source_type TEXT, created_by TEXT
        )
    """)
    conn.execute(
        "INSERT INTO behavioral_decisions(decision_id, directive, status) VALUES "
        "('dec_d56d89ceec24', 'loop nudge directive', 'active'), "
        "('dec_56d4dbb03e22', 'backend directive', 'active'), "
        "('dec_2ac499e2de29', 'memorable info directive', 'active'), "
        "('dec_other', 'unrelated directive', 'active')"
    )


def test_migration_adds_trigger_name_column():
    conn = sqlite3.connect(":memory:")
    _setup_tables(conn)
    _ensure_decision_trigger_column(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(behavioral_decisions)").fetchall()]
    assert "trigger_name" in cols


def test_migration_updates_known_decisions():
    conn = sqlite3.connect(":memory:")
    _setup_tables(conn)
    _ensure_decision_trigger_column(conn)
    triggers = dict(conn.execute(
        "SELECT decision_id, trigger_name FROM behavioral_decisions"
    ).fetchall())
    assert triggers["dec_d56d89ceec24"] == "loop_nudge_5_rounds"
    assert triggers["dec_56d4dbb03e22"] == "backend_unresolved_3_calls"
    assert triggers["dec_2ac499e2de29"] is None  # passive in v1
    assert triggers["dec_other"] is None  # unrelated, untouched


def test_migration_idempotent():
    conn = sqlite3.connect(":memory:")
    _setup_tables(conn)
    _ensure_decision_trigger_column(conn)
    _ensure_decision_trigger_column(conn)  # second run must not raise
    cols = [r[1] for r in conn.execute("PRAGMA table_info(behavioral_decisions)").fetchall()]
    assert cols.count("trigger_name") == 1
```

Run: `pytest tests/runtime/test_decision_signals_migration.py -v`. Expected: FAIL.

- [ ] **Step 2: Implement migration helper**

In `core/runtime/db.py`, after the existing `_ensure_tool_router_tables` function, add:

```python
def _ensure_decision_trigger_column(conn: sqlite3.Connection) -> None:
    """Add behavioral_decisions.trigger_name column and wire known decisions.

    Idempotent: skips ALTER if column exists; UPDATEs are no-ops if
    decisions already have the right trigger_name set.
    """
    existing_cols = {
        r[1] for r in conn.execute(
            "PRAGMA table_info(behavioral_decisions)"
        ).fetchall()
    }
    if "trigger_name" not in existing_cols:
        try:
            conn.execute(
                "ALTER TABLE behavioral_decisions ADD COLUMN trigger_name TEXT"
            )
        except sqlite3.OperationalError as exc:
            # Column may have been added concurrently
            if "duplicate column" not in str(exc).lower():
                raise

    # Wire the v1 triggers for the two known decisions
    conn.execute(
        "UPDATE behavioral_decisions SET trigger_name = 'loop_nudge_5_rounds' "
        "WHERE decision_id = 'dec_d56d89ceec24'"
    )
    conn.execute(
        "UPDATE behavioral_decisions SET trigger_name = 'backend_unresolved_3_calls' "
        "WHERE decision_id = 'dec_56d4dbb03e22'"
    )
```

Then call it from `init_db()`:

```python
        _ensure_decision_trigger_column(conn)
```

(Place this right after `_ensure_tool_router_tables(conn)` for grouping.)

- [ ] **Step 3: Run migration tests**

Run: `pytest tests/runtime/test_decision_signals_migration.py -v`. Expected: PASS.

- [ ] **Step 4: Update db_decisions.py to expose trigger_name**

In `core/runtime/db_decisions.py`, find the `list_decisions` and `get_decision` functions. They likely use `SELECT *` or an explicit column list. Verify the dict returned to callers includes `trigger_name`.

Quick check via:
```bash
grep -n "SELECT.*FROM behavioral_decisions" core/runtime/db_decisions.py
```

If you find a query like `SELECT decision_id, directive, ... FROM behavioral_decisions`, add `trigger_name` to the select list and to the returned dict construction. If it's `SELECT *`, no code change needed.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db.py core/runtime/db_decisions.py tests/runtime/test_decision_signals_migration.py
git commit -m "feat(decision-signals): DB migration adds trigger_name column"
```

---

## Task 3: decision_signals.py — types + registry + evaluation

**Files:**
- Create: `core/services/decision_signals.py`
- Test: `tests/services/test_decision_signals.py`

- [ ] **Step 1: Write failing tests for types and registry**

Create `tests/services/test_decision_signals.py`:

```python
import pytest
from core.services import decision_signals as ds


def _ctx(**overrides):
    """Build a TriggerContext with sensible defaults for tests."""
    base = dict(
        user_message="hej",
        session_id=None,
        run_id=None,
        consecutive_tool_only_rounds=0,
        recent_tool_calls=[],
        recent_assistant_text="",
        agentic_round_seq=0,
        timestamp="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return ds.TriggerContext(**base)


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    """Each test starts with a clean registry."""
    monkeypatch.setattr(ds, "_TRIGGER_REGISTRY", {})


def test_register_adds_to_registry():
    ds.register("test_trigger", lambda ctx: True)
    assert "test_trigger" in ds._TRIGGER_REGISTRY


def test_register_duplicate_overwrites():
    ds.register("t", lambda ctx: True)
    ds.register("t", lambda ctx: False, cooldown_seconds=10)
    spec = ds._TRIGGER_REGISTRY["t"]
    assert spec.cooldown_seconds == 10


def test_evaluate_returns_empty_when_no_active_decisions(monkeypatch):
    monkeypatch.setattr(ds, "_active_decisions_with_triggers", lambda: [])
    out = ds.evaluate_decision_triggers(_ctx())
    assert out == []


def test_evaluate_skips_unknown_trigger_name(monkeypatch):
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "missing"}],
    )
    out = ds.evaluate_decision_triggers(_ctx())
    assert out == []


def test_evaluate_fires_when_trigger_returns_true(monkeypatch):
    ds.register("always", lambda ctx: True)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "always"}],
    )
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    out = ds.evaluate_decision_triggers(_ctx())
    assert len(out) == 1
    assert out[0].decision_id == "d1"
    assert out[0].trigger_name == "always"


def test_evaluate_sandboxes_failing_trigger(monkeypatch, caplog):
    def boom(ctx):
        raise RuntimeError("trigger crashed")
    ds.register("boom", boom)
    ds.register("ok", lambda ctx: True)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [
            {"decision_id": "d_boom", "trigger_name": "boom"},
            {"decision_id": "d_ok", "trigger_name": "ok"},
        ],
    )
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    out = ds.evaluate_decision_triggers(_ctx())
    # boom is skipped, ok still fires
    assert len(out) == 1
    assert out[0].decision_id == "d_ok"


def test_killswitch_off_returns_empty(monkeypatch):
    class FakeS:
        decision_signals_enabled = False
    monkeypatch.setattr(ds, "RuntimeSettings", lambda: FakeS())
    out = ds.evaluate_decision_triggers(_ctx())
    assert out == []
```

Run: `pytest tests/services/test_decision_signals.py -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement types + registry + evaluate**

Create `core/services/decision_signals.py`:

```python
"""Decisions-as-signals: per-turn evaluation of behavioral decisions.

Triggers are code-defined functions registered by name at import time.
Each active behavioral_decision row may reference a trigger via its
`trigger_name` column. On every visible-chat turn, this module evaluates
all active triggers, applies per-decision cooldown, and produces the
`[FIRED_DECISIONS]` AWARENESS section.
"""
from __future__ import annotations

import contextvars
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable, Optional

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings

logger = logging.getLogger(__name__)


@dataclass
class TriggerContext:
    """Snapshot of state available to a trigger function."""
    user_message: str
    session_id: Optional[str]
    run_id: Optional[str]
    consecutive_tool_only_rounds: int
    recent_tool_calls: list[dict]
    recent_assistant_text: str
    agentic_round_seq: int
    timestamp: str


@dataclass
class TriggerSpec:
    name: str
    fire_fn: Callable[[TriggerContext], bool]
    cooldown_seconds: int = 0
    cooldown_turns: int = 0


@dataclass
class FiredDecision:
    decision_id: str
    trigger_name: str
    context_summary: str = ""


_TRIGGER_REGISTRY: dict[str, TriggerSpec] = {}

# Bound by visible_runs.py before each prompt build
_current_trigger_context: contextvars.ContextVar[Optional[TriggerContext]] = (
    contextvars.ContextVar("_current_trigger_context", default=None)
)


def register(
    name: str,
    fire_fn: Callable[[TriggerContext], bool],
    *,
    cooldown_seconds: int = 0,
    cooldown_turns: int = 0,
) -> None:
    if name in _TRIGGER_REGISTRY:
        logger.warning("decision_signals: trigger %r is being overwritten", name)
    _TRIGGER_REGISTRY[name] = TriggerSpec(
        name=name,
        fire_fn=fire_fn,
        cooldown_seconds=int(cooldown_seconds),
        cooldown_turns=int(cooldown_turns),
    )


def _active_decisions_with_triggers() -> list[dict[str, Any]]:
    """Return active decisions that have a trigger_name set."""
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT decision_id, trigger_name FROM behavioral_decisions "
                "WHERE status = 'active' AND trigger_name IS NOT NULL "
                "AND trigger_name != ''"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("decision_signals: cannot query active decisions: %s", exc)
        return []


def _read_last_fired(decision_id: str) -> Optional[str]:
    try:
        with connect() as c:
            row = c.execute(
                "SELECT value FROM runtime_state_kv WHERE key = ?",
                (f"decision_signal_last_fired:{decision_id}",),
            ).fetchone()
        if row is None:
            return None
        return str(row["value"] or "") or None
    except Exception:
        return None


def _read_last_fired_seq(decision_id: str) -> Optional[int]:
    try:
        with connect() as c:
            row = c.execute(
                "SELECT value FROM runtime_state_kv WHERE key = ?",
                (f"decision_signal_turn_seq:{decision_id}",),
            ).fetchone()
        if row is None or not row["value"]:
            return None
        return int(row["value"])
    except Exception:
        return None


def _write_last_fired(decision_id: str, iso_ts: str) -> None:
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO runtime_state_kv(key, value, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (f"decision_signal_last_fired:{decision_id}", iso_ts, iso_ts),
            )
            c.commit()
    except Exception as exc:
        logger.warning("decision_signals: cannot write last_fired: %s", exc)


def _write_last_fired_seq(decision_id: str, seq: int, iso_ts: str) -> None:
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO runtime_state_kv(key, value, updated_at) "
                "VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (f"decision_signal_turn_seq:{decision_id}", str(seq), iso_ts),
            )
            c.commit()
    except Exception:
        pass


def _cooldown_active(spec: TriggerSpec, decision_id: str, ctx: TriggerContext) -> bool:
    if spec.cooldown_seconds > 0:
        last_iso = _read_last_fired(decision_id)
        if last_iso:
            try:
                last_dt = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=UTC)
                elapsed = (datetime.now(UTC) - last_dt).total_seconds()
                if elapsed < spec.cooldown_seconds:
                    return True
            except Exception:
                pass
    if spec.cooldown_turns > 0:
        last_seq = _read_last_fired_seq(decision_id)
        if last_seq is not None:
            if (ctx.agentic_round_seq - last_seq) < spec.cooldown_turns:
                return True
    return False


def _publish_fired_event(*, decision_id: str, trigger_name: str, ctx: TriggerContext) -> None:
    try:
        event_bus.publish("decision_signal.fired", {
            "decision_id": decision_id,
            "trigger_name": trigger_name,
            "session_id": ctx.session_id,
            "run_id": ctx.run_id,
            "agentic_round_seq": ctx.agentic_round_seq,
            "consecutive_tool_only_rounds": ctx.consecutive_tool_only_rounds,
        })
    except Exception:
        pass


def evaluate_decision_triggers(ctx: TriggerContext) -> list[FiredDecision]:
    """Evaluate all active decisions with triggers; return those that fire.

    Sandboxed per-trigger: if one raises, others still run. Cooldown
    checked per-decision. Side effects (writing last_fired_at, publishing
    events) happen only for actual fires.
    """
    settings = RuntimeSettings()
    if not settings.decision_signals_enabled:
        return []

    fired: list[FiredDecision] = []
    decisions = _active_decisions_with_triggers()
    now_iso = datetime.now(UTC).isoformat()

    for d in decisions:
        decision_id = str(d.get("decision_id") or "")
        trigger_name = str(d.get("trigger_name") or "")
        if not decision_id or not trigger_name:
            continue

        spec = _TRIGGER_REGISTRY.get(trigger_name)
        if spec is None:
            logger.debug(
                "decision_signals: unknown_trigger %r for %s", trigger_name, decision_id
            )
            continue

        try:
            should_fire = bool(spec.fire_fn(ctx))
        except Exception as exc:
            logger.warning(
                "decision_signals: evaluate failed for %s (%s): %s",
                decision_id, trigger_name, exc,
            )
            continue

        if not should_fire:
            continue

        if _cooldown_active(spec, decision_id, ctx):
            continue

        # Build short context summary for the section text
        summary_bits = []
        if "loop_nudge" in trigger_name:
            summary_bits.append(f"round {ctx.consecutive_tool_only_rounds}")
        if "backend" in trigger_name:
            summary_bits.append("backend streak ≥3 unresolved")
        summary = ", ".join(summary_bits) or trigger_name

        _write_last_fired(decision_id, now_iso)
        if spec.cooldown_turns > 0:
            _write_last_fired_seq(decision_id, ctx.agentic_round_seq, now_iso)
        _publish_fired_event(decision_id=decision_id, trigger_name=trigger_name, ctx=ctx)

        fired.append(FiredDecision(
            decision_id=decision_id,
            trigger_name=trigger_name,
            context_summary=summary,
        ))
        logger.info("decision_signals.fired %s via %s", decision_id, trigger_name)

    return fired


def fired_decisions_section(ctx: TriggerContext) -> Optional[str]:
    """Build the [FIRED_DECISIONS] section text. None if nothing fired."""
    fired = evaluate_decision_triggers(ctx)
    if not fired:
        return None
    lines = ["🔔 fired decisions:"]
    for f in fired:
        lines.append(f"- decision:{f.decision_id} fired ({f.trigger_name}: {f.context_summary})")
    return "\n".join(lines)


def build_trigger_context(
    *,
    user_message: str = "",
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
    consecutive_tool_only_rounds: int = 0,
    recent_tool_calls: Optional[list[dict]] = None,
    recent_assistant_text: str = "",
    agentic_round_seq: int = 0,
) -> TriggerContext:
    """Build a TriggerContext from explicit fields. Used in tests and as
    a fallback when the ContextVar is not bound."""
    return TriggerContext(
        user_message=str(user_message or ""),
        session_id=session_id,
        run_id=run_id,
        consecutive_tool_only_rounds=int(consecutive_tool_only_rounds or 0),
        recent_tool_calls=list(recent_tool_calls or []),
        recent_assistant_text=str(recent_assistant_text or ""),
        agentic_round_seq=int(agentic_round_seq or 0),
        timestamp=datetime.now(UTC).isoformat(),
    )


def get_current_trigger_context_or_build(
    *,
    user_message: str = "",
    session_id: Optional[str] = None,
) -> TriggerContext:
    """Return the bound ContextVar if set, else build a minimal fallback."""
    ctx = _current_trigger_context.get()
    if ctx is not None:
        return ctx
    return build_trigger_context(
        user_message=user_message,
        session_id=session_id,
    )


def bind_context(ctx: TriggerContext) -> contextvars.Token:
    """Bind the per-run TriggerContext. Caller must reset_token after use."""
    return _current_trigger_context.set(ctx)


def reset_context(token: contextvars.Token) -> None:
    _current_trigger_context.reset(token)
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/services/test_decision_signals.py -v`. Expected: PASS.

- [ ] **Step 4: Add cooldown tests**

Append to `tests/services/test_decision_signals.py`:

```python
def test_cooldown_seconds_blocks_within_window(monkeypatch):
    ds.register("t", lambda ctx: True, cooldown_seconds=600)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "t"}],
    )
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)

    # First call: never fired before, fires
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    out1 = ds.evaluate_decision_triggers(_ctx())
    assert len(out1) == 1

    # Second call: fired 60 seconds ago, blocked
    from datetime import datetime, timezone, timedelta
    recent_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: recent_iso)
    out2 = ds.evaluate_decision_triggers(_ctx())
    assert out2 == []

    # Third call: fired 10 minutes ago, fires again
    long_ago = (datetime.now(timezone.utc) - timedelta(seconds=601)).isoformat()
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: long_ago)
    out3 = ds.evaluate_decision_triggers(_ctx())
    assert len(out3) == 1


def test_cooldown_turns_blocks_within_window(monkeypatch):
    ds.register("t", lambda ctx: True, cooldown_turns=2)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "d1", "trigger_name": "t"}],
    )
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_write_last_fired_seq", lambda d_id, seq, ts: None)

    # First call at round 5: fires
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: None)
    out1 = ds.evaluate_decision_triggers(_ctx(agentic_round_seq=5))
    assert len(out1) == 1

    # Round 6: 1 turn after fire, blocked (cooldown_turns=2)
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: 5)
    out2 = ds.evaluate_decision_triggers(_ctx(agentic_round_seq=6))
    assert out2 == []

    # Round 7: 2 turns after fire, fires
    out3 = ds.evaluate_decision_triggers(_ctx(agentic_round_seq=7))
    assert len(out3) == 1


def test_fired_decisions_section_returns_none_when_no_fires(monkeypatch):
    monkeypatch.setattr(ds, "_active_decisions_with_triggers", lambda: [])
    out = ds.fired_decisions_section(_ctx())
    assert out is None


def test_fired_decisions_section_format_when_fired(monkeypatch):
    ds.register("loop_nudge_5_rounds", lambda ctx: True, cooldown_turns=1)
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "dec_xxx", "trigger_name": "loop_nudge_5_rounds"}],
    )
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_write_last_fired_seq", lambda d_id, seq, ts: None)
    monkeypatch.setattr(ds, "_publish_fired_event", lambda **kwargs: None)

    section = ds.fired_decisions_section(_ctx(consecutive_tool_only_rounds=5, agentic_round_seq=5))
    assert section is not None
    assert "decision:dec_xxx" in section
    assert "loop_nudge_5_rounds" in section
    assert "round 5" in section
```

- [ ] **Step 5: Run cooldown tests**

Run: `pytest tests/services/test_decision_signals.py -v`. Expected: PASS (all).

- [ ] **Step 6: Commit**

```bash
git add core/services/decision_signals.py tests/services/test_decision_signals.py
git commit -m "feat(decision-signals): registry + evaluate + cooldown logic"
```

---

## Task 4: loop_nudge trigger

**Files:**
- Create: `core/services/decision_triggers/loop_nudge.py`
- Create: `core/services/decision_triggers/__init__.py` (start)
- Test: `tests/services/test_decision_triggers.py` (start)

- [ ] **Step 1: Write failing test**

Create `tests/services/test_decision_triggers.py`:

```python
import pytest

from core.services import decision_signals as ds
from core.services.decision_triggers import loop_nudge


def _ctx(**overrides):
    base = dict(
        user_message="", session_id=None, run_id=None,
        consecutive_tool_only_rounds=0,
        recent_tool_calls=[], recent_assistant_text="",
        agentic_round_seq=0, timestamp="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return ds.TriggerContext(**base)


def test_loop_nudge_fires_at_exactly_5():
    assert loop_nudge.loop_nudge_5_rounds(_ctx(consecutive_tool_only_rounds=5)) is True


def test_loop_nudge_does_not_fire_at_4():
    assert loop_nudge.loop_nudge_5_rounds(_ctx(consecutive_tool_only_rounds=4)) is False


def test_loop_nudge_does_not_fire_at_6():
    assert loop_nudge.loop_nudge_5_rounds(_ctx(consecutive_tool_only_rounds=6)) is False


def test_loop_nudge_module_registers_in_registry():
    # Just importing the module should have registered the trigger
    assert "loop_nudge_5_rounds" in ds._TRIGGER_REGISTRY
    spec = ds._TRIGGER_REGISTRY["loop_nudge_5_rounds"]
    assert spec.cooldown_turns == 1
```

Run: `pytest tests/services/test_decision_triggers.py::test_loop_nudge_fires_at_exactly_5 -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement loop_nudge trigger**

Create `core/services/decision_triggers/__init__.py`:

```python
"""Decision triggers — importing this package registers all triggers.

Each trigger module calls decision_signals.register() at import time, so
simply importing the package populates the registry.
"""
from . import loop_nudge  # noqa: F401
```

Create `core/services/decision_triggers/loop_nudge.py`:

```python
"""Trigger: fire when Jarvis has had 5 consecutive tool-only rounds.

Decision: dec_d56d89ceec24 — "Når loop-nudge fyrer, tager jeg en bevidst
stilling: fortsætte eller opsumlere. Jeg ignorerer den ikke."

Cooldown: 1 turn. Even though the trigger uses == (so it only matches at
exactly round 5), cooldown is belt-and-suspenders: if a future change
broadens to >= 5, cooldown still ensures one-fire-per-spree.
"""
from __future__ import annotations

from core.services.decision_signals import register, TriggerContext


def loop_nudge_5_rounds(ctx: TriggerContext) -> bool:
    return ctx.consecutive_tool_only_rounds == 5


register("loop_nudge_5_rounds", loop_nudge_5_rounds, cooldown_turns=1)
```

- [ ] **Step 3: Run loop_nudge tests**

Run: `pytest tests/services/test_decision_triggers.py -v`. Expected: PASS (4 tests).

- [ ] **Step 4: Commit**

```bash
git add core/services/decision_triggers/ tests/services/test_decision_triggers.py
git commit -m "feat(decision-signals): loop_nudge_5_rounds trigger"
```

---

## Task 5: backend_unresolved trigger

**Files:**
- Create: `core/services/decision_triggers/backend_unresolved.py`
- Modify: `core/services/decision_triggers/__init__.py`
- Modify: `tests/services/test_decision_triggers.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/services/test_decision_triggers.py`:

```python
from core.services.decision_triggers import backend_unresolved


def _tc(name: str, **args):
    """Build a tool_call dict matching what visible_runs records."""
    return {
        "function": {
            "name": name,
            "arguments": args or {},
        },
    }


def test_backend_unresolved_fires_after_3_streak_in_repo():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/services/foo.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("read_file", path="/media/projects/jarvis-v2/apps/api/x.py"),
    ]
    ctx = _ctx(recent_tool_calls=calls, recent_assistant_text="")
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is True


def test_backend_unresolved_does_not_fire_after_2():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/services/foo.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_resets_on_non_backend_tool():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/x.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("web_search", query="something"),  # resets
        _tc("read_file", path="/media/projects/jarvis-v2/core/y.py"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    # After reset, only 1 backend call → no fire
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_ignores_non_jarvis_paths():
    calls = [
        _tc("read_file", path="/etc/hosts"),
        _tc("read_file", path="/var/log/syslog"),
        _tc("read_file", path="/tmp/foo.txt"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_accepts_git_calls_without_path():
    calls = [
        _tc("git_status"),
        _tc("git_log"),
        _tc("git_diff"),
    ]
    ctx = _ctx(recent_tool_calls=calls)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is True


def test_backend_unresolved_suppressed_by_resolution_text():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/x.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("read_file", path="/media/projects/jarvis-v2/core/y.py"),
    ]
    long_resolution = (
        "Jeg fandt root cause i config-loaderen — den prøvede at læse fra en "
        "path der ikke eksisterede. Fixed nu, deployer ikke før jeg har testet."
    )
    ctx = _ctx(recent_tool_calls=calls, recent_assistant_text=long_resolution)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is False


def test_backend_unresolved_short_text_does_not_count_as_resolution():
    calls = [
        _tc("read_file", path="/media/projects/jarvis-v2/core/x.py"),
        _tc("grep", path="/media/projects/jarvis-v2/core"),
        _tc("read_file", path="/media/projects/jarvis-v2/core/y.py"),
    ]
    short = "fundet."  # under 80 chars
    ctx = _ctx(recent_tool_calls=calls, recent_assistant_text=short)
    assert backend_unresolved.backend_unresolved_3_calls(ctx) is True


def test_backend_unresolved_module_registers():
    assert "backend_unresolved_3_calls" in ds._TRIGGER_REGISTRY
    spec = ds._TRIGGER_REGISTRY["backend_unresolved_3_calls"]
    assert spec.cooldown_seconds == 0
```

Run: `pytest tests/services/test_decision_triggers.py -v`. Expected: FAIL (module missing).

- [ ] **Step 2: Implement backend_unresolved trigger**

Create `core/services/decision_triggers/backend_unresolved.py`:

```python
"""Trigger: fire when 3 consecutive Jarvis-backend tool calls happen
without a resolution-text response.

Decision: dec_56d4dbb03e22 — "Når jeg finder et problem i min egen
backend, handler jeg inden 3 tool calls: fix, foreslå fix, eller forklar
tydeligt hvad der blokerer. Ingen ren rapportering."

Filter logic (BOTH must hold to count as backend-investigation):
1. Tool name matches an investigation pattern (read_file, grep, etc.)
2. Path argument (when present) points inside Jarvis's project tree

git_* calls are accepted by name alone — they're always in the current
repo by definition. Tools without a path argument (e.g., bash without
explicit cwd) also count as backend.

Cooldown: 0 — incident-style nagging until streak breaks or resolution.
"""
from __future__ import annotations

import json
from typing import Any

from core.services.decision_signals import register, TriggerContext


_BACKEND_TOOL_PATTERNS = ("read_file", "grep", "list_dir", "glob", "git_")
_JARVIS_PATH_HINTS = (
    "/media/projects/jarvis-v2",
    "/home/bs/.jarvis-v2",
    "core/",
    "apps/",
)
_RESOLUTION_MIN_CHARS = 80
_RESOLUTION_KEYWORDS = (
    "fixed", "found", "root cause", "fundet", "fikset", "rod", "løst",
    "deployed", "deployet", "committed", "committet",
)


def _is_jarvis_backend_call(tool_call: dict[str, Any]) -> bool:
    fn = tool_call.get("function") or {}
    name = str(fn.get("name") or tool_call.get("name") or "")
    if not any(name.startswith(p) for p in _BACKEND_TOOL_PATTERNS):
        return False
    # git_* tools are always against the current repo
    if name.startswith("git_"):
        return True
    args = fn.get("arguments") or tool_call.get("arguments") or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if not isinstance(args, dict):
        args = {}
    path = str(args.get("path") or args.get("dir") or "")
    if not path:
        # No path arg → treat as backend (e.g., grep without dir)
        return True
    return any(hint in path for hint in _JARVIS_PATH_HINTS)


def backend_unresolved_3_calls(ctx: TriggerContext) -> bool:
    backend_streak = 0
    for tc in (ctx.recent_tool_calls or [])[-5:]:
        if _is_jarvis_backend_call(tc):
            backend_streak += 1
        else:
            backend_streak = 0
    if backend_streak < 3:
        return False
    last_text = (ctx.recent_assistant_text or "").strip().lower()
    if len(last_text) >= _RESOLUTION_MIN_CHARS and any(
        kw in last_text for kw in _RESOLUTION_KEYWORDS
    ):
        return False
    return True


register("backend_unresolved_3_calls", backend_unresolved_3_calls, cooldown_seconds=0)
```

- [ ] **Step 3: Update __init__.py to import the new trigger**

Replace the contents of `core/services/decision_triggers/__init__.py`:

```python
"""Decision triggers — importing this package registers all triggers.

Each trigger module calls decision_signals.register() at import time, so
simply importing the package populates the registry.
"""
from . import loop_nudge  # noqa: F401
from . import backend_unresolved  # noqa: F401
```

- [ ] **Step 4: Run all trigger tests**

Run: `pytest tests/services/test_decision_triggers.py -v`. Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add core/services/decision_triggers/ tests/services/test_decision_triggers.py
git commit -m "feat(decision-signals): backend_unresolved_3_calls trigger with path filtering"
```

---

## Task 6: Wire ContextVar binding in visible_runs.py

**Files:**
- Modify: `core/services/visible_runs.py`

- [ ] **Step 1: Find the right binding point**

In `core/services/visible_runs.py`, the trigger context must be bound BEFORE any code path that calls `_build_visible_input` (which calls `build_visible_chat_prompt_assembly`). The first such call is in the initial visible-run path.

Find around line 880 (the first call to `_build_visible_input`):

```bash
grep -n "_build_visible_input" core/services/visible_runs.py | head -5
```

Two call sites: the first-pass (line ~878 area) and inside the agentic loop (where it isn't called per-round, since base_messages is built once at line ~884).

The simplest binding: at the top of `_start_visible_run_inner` (or wherever the function body begins) — before any prompt building.

- [ ] **Step 2: Add binding helper**

Near the top of `core/services/visible_runs.py`, after existing imports, add:

```python
def _build_decision_signals_ctx(run, *, agentic_round_seq: int = 0,
                                consecutive_tool_only: int = 0,
                                recent_tool_calls: list | None = None,
                                recent_assistant_text: str = "") -> "TriggerContext":
    from core.services.decision_signals import build_trigger_context
    return build_trigger_context(
        user_message=run.user_message or "",
        session_id=run.session_id,
        run_id=run.run_id,
        consecutive_tool_only_rounds=int(consecutive_tool_only),
        recent_tool_calls=recent_tool_calls or [],
        recent_assistant_text=recent_assistant_text or "",
        agentic_round_seq=int(agentic_round_seq),
    )
```

- [ ] **Step 3: Bind at start of run + before each agentic round**

In `_start_visible_run_inner` (or equivalent), at the very start (before any prompt building), add:

```python
        # ── Bind decision-signals context for this run ──
        # Triggers see this when fired_decisions_section is called from
        # inside prompt_contract.build_visible_chat_prompt_assembly.
        from core.services.decision_signals import bind_context, reset_context
        _ds_token = bind_context(_build_decision_signals_ctx(run))
        try:
            # ... existing run body ...
        finally:
            reset_context(_ds_token)
```

(In practice, wrap the existing function body in this try/finally. The exact placement depends on the function structure; do not break existing flow.)

Inside the agentic loop, BEFORE each round's prompt build, refresh the context with current state:

```python
                    # Refresh trigger context with this round's state
                    try:
                        _ds_recent_text = "".join(_a_parts)[-2000:] if _a_parts else ""
                        _ds_recent_calls = list(
                            (_followup_exchanges[-1].tool_calls if _followup_exchanges else [])
                        )[-10:]
                        from core.services.decision_signals import bind_context
                        _ds_round_token = bind_context(_build_decision_signals_ctx(
                            run,
                            agentic_round_seq=_agentic_round + 1,
                            consecutive_tool_only=_consecutive_tool_only_rounds,
                            recent_tool_calls=_ds_recent_calls,
                            recent_assistant_text=_ds_recent_text,
                        ))
                    except Exception:
                        _ds_round_token = None
```

(Note: ContextVar `set` returns a token — we shadow the outer one for this round. The outer `reset_context(_ds_token)` at function-end still cleans up properly.)

- [ ] **Step 4: Verify imports**

Run: `conda run -n ai python -c "import core.services.visible_runs; print('imports ok')"`
Expected: `imports ok`

- [ ] **Step 5: Verify smoke test still passes**

Run: `conda run -n ai python scripts/smoke_test_startup.py`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add core/services/visible_runs.py
git commit -m "feat(decision-signals): bind TriggerContext per run + per agentic round"
```

---

## Task 7: prompt_contract.py wiring + deprecate enforcement_section

**Files:**
- Modify: `core/services/prompt_contract.py`
- Modify: `core/services/decision_enforcement.py`

- [ ] **Step 1: Update prompt_contract awareness category**

In `core/services/prompt_contract.py`, find the `_AWARENESS_CATEGORY_HEADERS` dict (around line 493). Add a new entry:

```python
        "fired_decisions": "[FIRED_DECISIONS]",
```

Find `_AWARENESS_CATEGORY_RULES` (slightly earlier). Add:

```python
        ("fired decisions", "fired_decisions"),
```

(Place it before the catch-all `("", "general")` if present. Order matters for first-match.)

- [ ] **Step 2: Replace enforcement_section call**

In `core/services/prompt_contract.py`, find the existing block (around line 735):

```python
    try:
        from core.services.decision_enforcement import enforcement_section
        _awareness_add(90, "active commitments enforcement", enforcement_section())
    except Exception:
        pass
```

Replace with:

```python
    try:
        from core.services.decision_signals import (
            fired_decisions_section,
            get_current_trigger_context_or_build,
        )
        _ds_ctx = get_current_trigger_context_or_build(
            user_message=user_message,
            session_id=session_id,
        )
        _ds_section = fired_decisions_section(_ds_ctx)
        if _ds_section:
            _awareness_add(90, "fired decisions", _ds_section)
    except Exception:
        pass
    # Legacy enforcement_section kept callable as no-op for rollback safety
    # (returns "" when killswitch is on). Will be removed once the new
    # mechanism is proven (target: 1-2 weeks of stable operation).
    try:
        from core.services.decision_enforcement import enforcement_section
        _legacy = enforcement_section()
        if _legacy:
            _awareness_add(90, "active commitments enforcement", _legacy)
    except Exception:
        pass
```

- [ ] **Step 3: Make enforcement_section killswitch-aware**

In `core/services/decision_enforcement.py`, find the `enforcement_section()` function. At the very top of the function body, add an early return when the new signals system is enabled:

```python
def enforcement_section() -> str:
    # When decision_signals is enabled (default), this legacy section
    # is suppressed in favor of [FIRED_DECISIONS] driven by triggers.
    # Returning empty string here means the prompt contract just won't
    # add anything — clean rollback path: flip the setting to False.
    try:
        from core.runtime.settings import RuntimeSettings
        if RuntimeSettings().decision_signals_enabled:
            return ""
    except Exception:
        pass
    # ... existing function body unchanged ...
```

(Do not delete the existing logic; just add the early return at the top.)

- [ ] **Step 4: Run prompt assembly to verify**

Run: `conda run -n ai python -c "
from core.services.prompt_contract import build_visible_chat_prompt_assembly
import core.services.decision_triggers  # ensure registry is populated
a = build_visible_chat_prompt_assembly(
    provider='ollama', model='glm-5.1:cloud',
    user_message='hej', session_id=None,
)
text = a.text or ''
print('AKTIVE FORPLIGTELSER in prompt:', 'AKTIVE FORPLIGTELSER' in text)
print('FIRED_DECISIONS in prompt:', '[FIRED_DECISIONS]' in text)
print('text length:', len(text))
"`
Expected: `AKTIVE FORPLIGTELSER in prompt: False`. The `[FIRED_DECISIONS]` may or may not be present depending on whether triggers fired (with empty user_message and no recent calls, neither trigger fires — section absent).

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py core/services/decision_enforcement.py
git commit -m "feat(decision-signals): wire fired_decisions_section + deprecate enforcement_section"
```

---

## Task 8: Integration test — full prompt flow

**Files:**
- Create: `tests/integration/test_decision_signals_in_prompt.py`

- [ ] **Step 1: Write integration test**

Create `tests/integration/test_decision_signals_in_prompt.py`:

```python
"""End-to-end: verify [FIRED_DECISIONS] appears in prompt when triggers fire."""
import pytest

from core.services import decision_signals as ds
import core.services.decision_triggers  # populate registry  # noqa: F401


def _ctx(**overrides):
    base = dict(
        user_message="hvad sker der?", session_id=None, run_id=None,
        consecutive_tool_only_rounds=0, recent_tool_calls=[],
        recent_assistant_text="", agentic_round_seq=0,
        timestamp="2026-05-07T12:00:00+00:00",
    )
    base.update(overrides)
    return ds.TriggerContext(**base)


def test_loop_nudge_fires_via_full_pipeline(monkeypatch):
    # Stub the DB query so the test doesn't need a populated decisions table
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "dec_d56d89ceec24", "trigger_name": "loop_nudge_5_rounds"}],
    )
    monkeypatch.setattr(ds, "_read_last_fired", lambda d_id: None)
    monkeypatch.setattr(ds, "_read_last_fired_seq", lambda d_id: None)
    monkeypatch.setattr(ds, "_write_last_fired", lambda d_id, ts: None)
    monkeypatch.setattr(ds, "_write_last_fired_seq", lambda d_id, seq, ts: None)
    published = []
    monkeypatch.setattr(
        ds, "_publish_fired_event",
        lambda **kwargs: published.append(kwargs),
    )

    section = ds.fired_decisions_section(_ctx(consecutive_tool_only_rounds=5, agentic_round_seq=5))
    assert section is not None
    assert "decision:dec_d56d89ceec24" in section
    assert "loop_nudge_5_rounds" in section
    assert len(published) == 1
    assert published[0]["decision_id"] == "dec_d56d89ceec24"


def test_killswitch_suppresses_section(monkeypatch):
    class FakeS:
        decision_signals_enabled = False
    monkeypatch.setattr(ds, "RuntimeSettings", lambda: FakeS())
    monkeypatch.setattr(
        ds, "_active_decisions_with_triggers",
        lambda: [{"decision_id": "dec_d56d89ceec24", "trigger_name": "loop_nudge_5_rounds"}],
    )
    section = ds.fired_decisions_section(_ctx(consecutive_tool_only_rounds=5))
    assert section is None
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_decision_signals_in_prompt.py -v`. Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_decision_signals_in_prompt.py
git commit -m "test(decision-signals): end-to-end fired_decisions_section pipeline"
```

---

## Task 9: decision_review tool extension

**Files:**
- Modify: `core/services/behavioral_decisions.py`
- Modify: `core/tools/decisions_tools.py`

- [ ] **Step 1: Find the data path**

```bash
grep -n "get_decision_with_reviews" core/services/behavioral_decisions.py
```

The function returns the full decision dict to `_exec_decision_get`. We need to ensure `trigger_name` and `last_fired_at` are included.

- [ ] **Step 2: Augment get_decision_with_reviews**

In `core/services/behavioral_decisions.py`, find `get_decision_with_reviews()`. After it builds the base decision dict, augment it:

```python
def get_decision_with_reviews(decision_id: str, *, review_limit: int = 10) -> dict | None:
    # ... existing body that fetches decision + reviews ...
    if decision is None:
        return None

    # Add trigger metadata for decisions-as-signals
    try:
        from core.runtime.db import connect
        with connect() as c:
            row = c.execute(
                "SELECT value FROM runtime_state_kv WHERE key = ?",
                (f"decision_signal_last_fired:{decision_id}",),
            ).fetchone()
        decision["last_fired_at"] = str(row["value"]) if row else None
    except Exception:
        decision["last_fired_at"] = None

    # trigger_name should already be in `decision` from the SELECT *,
    # but ensure the key exists even when the column is NULL
    decision.setdefault("trigger_name", None)

    return decision
```

(If the existing function has a different shape, adapt — the goal is that the returned dict carries `trigger_name` and `last_fired_at`.)

- [ ] **Step 3: Verify decision_get tool returns the new fields**

Run:
```bash
conda run -n ai python -c "
from core.tools.decisions_tools import _exec_decision_get
out = _exec_decision_get({'decision_id': 'dec_d56d89ceec24'})
import json
print(json.dumps(out, indent=2, default=str)[:500])
"
```

Expected: output JSON includes `trigger_name: 'loop_nudge_5_rounds'` and `last_fired_at` (may be null until first fire).

- [ ] **Step 4: Commit**

```bash
git add core/services/behavioral_decisions.py
git commit -m "feat(decision-signals): decision_get returns trigger_name + last_fired_at"
```

---

## Task 10: Smoke test extension + run all tests

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add registry verification**

In `scripts/smoke_test_startup.py`, find the section that runs after the lifespan completes (where `tool_router-state` is checked). Add:

```python
            # Verify decision_signals registry populated
            try:
                import core.services.decision_triggers  # noqa: F401
                from core.services.decision_signals import _TRIGGER_REGISTRY
                expected = {"loop_nudge_5_rounds", "backend_unresolved_3_calls"}
                missing = expected - set(_TRIGGER_REGISTRY.keys())
                if missing:
                    raise RuntimeError(f"decision_signals registry missing: {missing}")
            except Exception:
                traceback.print_exc()
```

- [ ] **Step 2: Run smoke test**

Run: `conda run -n ai python scripts/smoke_test_startup.py`
Expected: exit 0, no traceback.

- [ ] **Step 3: Run full test suite for decision_signals**

Run: `conda run -n ai pytest tests/services/test_decision_signals.py tests/services/test_decision_triggers.py tests/integration/test_decision_signals_in_prompt.py tests/runtime/test_decision_signals_migration.py -v`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "test(decision-signals): smoke test verifies trigger registry populated"
```

---

## Task 11: Deploy + first-day verification

- [ ] **Step 1: Pre-deploy check**

```bash
conda run -n ai pytest tests/services/test_decision_*.py tests/integration/test_decision_*.py tests/runtime/test_decision_*.py -v
conda run -n ai python -m compileall core/services/decision_signals.py core/services/decision_triggers/ core/services/visible_runs.py core/services/prompt_contract.py
conda run -n ai python scripts/smoke_test_startup.py
```

All must pass.

- [ ] **Step 2: Deploy**

```bash
sudo systemctl restart jarvis-api jarvis-runtime
sleep 4
journalctl -u jarvis-api --since "30 seconds ago" --no-pager | grep -iE "decision_signal|error" | tail -10
```

Expected: no errors. May see `decision_signals.fired ...` info log lines if a trigger fires immediately.

- [ ] **Step 3: Manual verification — old text gone**

In a chat with Jarvis (webchat or Discord), have him say something. Then check the prompt that was built:

```bash
conda run -n ai python -c "
import sys
sys.path.insert(0, '/media/projects/jarvis-v2')
from core.services.prompt_contract import build_visible_chat_prompt_assembly
import core.services.decision_triggers  # populate registry  # noqa
a = build_visible_chat_prompt_assembly(
    provider='ollama', model='glm-5.1:cloud',
    user_message='lille test', session_id=None,
)
t = a.text or ''
print('Has AKTIVE FORPLIGTELSER (legacy):', 'AKTIVE FORPLIGTELSER' in t)
print('Has DU SKAL escalation:', 'DU SKAL' in t)
print('Has FIRED_DECISIONS marker:', '[FIRED_DECISIONS]' in t)
print('Total prompt chars:', len(t))
"
```

Expected: legacy strings absent. `[FIRED_DECISIONS]` may be absent (no trigger fired in this synthetic test) — that's correct.

- [ ] **Step 4: Verify trigger_name in DB**

```bash
conda run -n ai python -c "
from core.runtime.db import connect
with connect() as c:
    rows = c.execute(
        \"SELECT decision_id, trigger_name FROM behavioral_decisions WHERE status='active'\"
    ).fetchall()
    for r in rows:
        print(f'{r[\"decision_id\"]}  trigger={r[\"trigger_name\"]}')
"
```

Expected output:
```
dec_d56d89ceec24  trigger=loop_nudge_5_rounds
dec_56d4dbb03e22  trigger=backend_unresolved_3_calls
dec_2ac499e2de29  trigger=None
```

- [ ] **Step 5: First-hour MC observation**

Open MC events stream. Look for:
- `decision_signal.fired` events when triggers match
- No `decision_signals.evaluate failed` warnings
- Adherence-score updates happen as before (nightly consolidation_judge_daemon path unchanged)

If something looks wrong: flip the killswitch in `~/.jarvis-v2/config/runtime.json`:
```json
{"decision_signals_enabled": false}
```

Settings reload picks it up within 30s; legacy `enforcement_section()` runs again as before.

- [ ] **Step 6: First-week measurement**

After 7 days, query:

```bash
conda run -n ai python -c "
from core.runtime.db import connect
with connect() as c:
    rows = c.execute(
        \"SELECT json_extract(payload_json, '\$.decision_id') as did, \"
        \"COUNT(*) as fires FROM events \"
        \"WHERE kind = 'decision_signal.fired' \"
        \"AND created_at >= datetime('now', '-7 days') \"
        \"GROUP BY did\"
    ).fetchall()
    for r in rows:
        print(f'{r[\"did\"]}: fired {r[\"fires\"]}× in 7d')

    # Adherence after deploy
    rows = c.execute(
        \"SELECT decision_id, adherence_score, last_reviewed_at \"
        \"FROM behavioral_decisions WHERE status='active'\"
    ).fetchall()
    print()
    print('Current adherence:')
    for r in rows:
        print(f'  {r[\"decision_id\"]}  {r[\"adherence_score\"]}  reviewed={r[\"last_reviewed_at\"]}')
"
```

Compare to pre-deploy baseline (recorded above as 25%, 33%, 42%). Target: at least one moves from <40% to >60%.

---

## Self-Review

Spec coverage:

- ✅ Strict signal format (Task 3 — `fired_decisions_section` output)
- ✅ Hybrid registry trigger architecture (Task 3, 4, 5)
- ✅ Default silence + decision_review fallback (Task 3 returns None when empty; Task 9 extends decision_review tool)
- ✅ Adherence escalation removed (Task 7 — enforcement_section returns "" when killswitch on)
- ✅ Per-decision cooldown (Task 3 evaluation logic with both seconds and turns)
- ✅ v1 trigger coverage for decisions #1 and #2; #3 stays passive (Task 2 leaves dec_2ac499 with NULL trigger_name)
- ✅ New `[FIRED_DECISIONS]` AWARENESS section (Task 7)
- ✅ Big-bang with feature flag (Task 1 + Task 7 step 3)
- ✅ Path filtering for backend_unresolved (Task 5)
- ✅ Resolution-text suppression with explicit threshold (Task 5)
- ✅ Cooldown semantics across multi-turn conditions (Task 3 cooldown tests)
- ✅ DB migration idempotent (Task 2)
- ✅ Killswitch tested + documented (Task 1, 7, 11)
- ✅ Manual verification path (Task 11)

Placeholder scan: clean. All code blocks complete. Function signatures consistent across tasks (`evaluate_decision_triggers`, `fired_decisions_section`, `build_trigger_context`, `bind_context`, `reset_context`).

Type consistency:
- `TriggerContext` fields used identically in tests and trigger functions
- `TriggerSpec` fields (`name`, `fire_fn`, `cooldown_seconds`, `cooldown_turns`) consistent
- `FiredDecision` shape consistent in tests and section formatter

Notes:
- `dec_2ac499e2de29` ("memorable info detected") explicitly stays passive — no task implements its trigger. Spec out-of-scope already documents this.
- `decision_create` tool extension for trigger-name input is out of scope per spec; can be added later when a new decision needs a trigger.
- The legacy `enforcement_section()` is kept callable but returns "" when killswitch is on. Keep this dual path for 1-2 weeks before removing entirely (separate plan).
