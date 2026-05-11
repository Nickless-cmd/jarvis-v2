# Lag #3 — Finitude Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add behavioral finitude to Jarvis — looming-end awareness (token-pres + sessions-alder), monthly chronicle reflection (3-paragraph format), and finitude as a tone-modulator in the weekly journal klangbræt. The daily-age hot-fix (a) already shipped in commit 217a3a7.

**Architecture:** All new logic lives in existing files — no new modules. `finitude_runtime.py` grows with two new prompt-section formatters, a session-age helper, a token-utilization helper, and a monthly producer cycle. `creative_journal_runtime.py` learns to embed a `finitude` sub-dict in its klangbræt. `internal_cadence.py` registers a new ProducerSpec for the monthly reflection. All chronicle storage reuses existing helpers; no new DB tables, no new event families.

**Tech Stack:** Python 3.11, SQLite (events + chat_messages), existing daemon_llm quality lane, eventbus.

**Spec:** `docs/superpowers/specs/2026-05-11-finitude-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `tests/test_finitude_phase1.py` | Tests for looming-end formatters, monthly reflection cycle, skip-gate, klangbræt finitude sub-dict, YAML frontmatter booleans. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `finitude_quality_lane_enabled: bool = True` |
| `core/services/finitude_runtime.py` | Add `_token_utilization_pct`, `_session_age_hours`, `_format_looming_end_section`, `_monthly_quality_lane_enabled`, `run_monthly_finitude_reflection`, `_build_monthly_reflection_narrative`, `_is_due_for_monthly`. Annual ritual swapped to `quality_daemon_llm_call`. `get_finitude_context_for_prompt` calls looming-end formatter after age. `_CONTEXT_BUDGET_TOKENS = 200_000` constant with Phase 2 TODO comment. |
| `core/services/internal_cadence.py` | New ProducerSpec `finitude_monthly_reflection` (cooldown 43200 min, priority 27, depends_on `finitude_runtime`). |
| `core/services/creative_journal_runtime.py` | `_fetch_affective_klangbraet` returns `"finitude"` sub-dict. `_build_prompt` renders new `## Finitude` section. `_format_yaml_frontmatter` adds 4 finitude booleans. |

### Untouched / reused

- `core/eventbus/events.py` — existing `cognitive_state` family covers new event kind
- `core/runtime/db.py` — reuse `insert_cognitive_chronicle_entry`, `list_cognitive_chronicle_entries`
- `core/services/context_window_manager.py` — reuse `_estimate_session_tokens`
- `core/services/daemon_llm.py` — reuse `quality_daemon_llm_call`
- `core/services/chronicle_engine.py` — reuse `project_entry_to_markdown`
- No new DB tables. No new event families.

---

## Spec deltas confirmed during planning

1. **Token-utilization signal source.** Verified: `context_window_manager._estimate_session_tokens()` exists and returns an int. We compute `pct = est_tokens / _CONTEXT_BUDGET_TOKENS × 100`. The constant gets a Phase 2 TODO comment so the next refactor finds it.

2. **Session-age signal source.** There is no `get_active_session()` API in `chat_sessions.py`. Pragmatic approach: `_session_age_hours()` queries `chat_messages` for the most-recently-touched session (max `created_at`), then finds the earliest `created_at` in that same `session_id`. Two small SQL queries. Returns 0 on any failure. This is approximate but stable, matching the spec's "rough proxy" stance.

3. **Annual ritual quality-lane swap.** The spec calls for this, but the existing `_build_annual_ritual_narrative` uses `daemon_llm_call`. We swap to a branched call gated by `_monthly_quality_lane_enabled()` (same flag covers both annual and monthly — the flag is named for monthly but acts as a single finitude quality-lane switch). Tests must preserve backwards-compat for the existing 4 finitude tests.

4. **Cadence registration.** Existing `finitude_runtime` ProducerSpec is registered in `internal_cadence.py` lines 477-484-ish; we mirror that pattern for the monthly variant. `depends_on=["finitude_runtime"]` ensures the annual run happens first when both are eligible on the same heartbeat.

5. **Active visible-session detection for partial-trigger logic.** When tests need to stub session-age, they monkeypatch `_session_age_hours` directly. Production code reads from `chat_messages` table.

---

## Task 1: Settings flag

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add settings flag**

In `core/runtime/settings.py`, find the `creative_voice_quality_lane_enabled` flag and add right after it:

```python
    # ── Finitude (Lag #3 — added 2026-05-11) ─────────────────────────────
    # Routes annual + monthly finitude rituals through quality_daemon_llm_call
    # (deepseek-v4-flash). Falls back to cheap lane if quality lane is
    # unavailable. Single flag covers both rituals.
    finitude_quality_lane_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, in `load_settings`, find `creative_voice_quality_lane_enabled=bool(...)` and add right after its closing comma:

```python
        finitude_quality_lane_enabled=bool(
            data.get(
                "finitude_quality_lane_enabled",
                defaults.finitude_quality_lane_enabled,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.finitude_quality_lane_enabled is True
print('OK attr:', load_settings().finitude_quality_lane_enabled)
"
```

Expected: `OK attr: True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(finitude): add finitude_quality_lane_enabled flag"
```

---

## Task 2: Looming-end helpers + format

**Files:**
- Modify: `core/services/finitude_runtime.py`
- Create: `tests/test_finitude_phase1.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_finitude_phase1.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest


def test_token_utilization_pct_computes_from_estimate(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_estimate_session_tokens",
                        lambda: 140_000)
    assert finitude_runtime._token_utilization_pct() == 70


def test_token_utilization_pct_returns_zero_on_failure(monkeypatch):
    from core.services import finitude_runtime

    def boom():
        raise RuntimeError("nope")
    monkeypatch.setattr(finitude_runtime, "_estimate_session_tokens", boom)
    assert finitude_runtime._token_utilization_pct() == 0


def test_format_looming_end_token_only(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 75)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 1.0)

    out = finitude_runtime._format_looming_end_section()
    assert "### Looming-end" in out
    assert "Token-pres" in out
    assert "75" in out
    assert "Sessions-alder" not in out


def test_format_looming_end_session_only(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 30)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 5.2)

    out = finitude_runtime._format_looming_end_section()
    assert "### Looming-end" in out
    assert "Sessions-alder" in out
    assert "5 timer" in out or "5.2 timer" in out
    assert "Token-pres" not in out


def test_format_looming_end_both_present(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 82)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 6.5)

    out = finitude_runtime._format_looming_end_section()
    assert "Token-pres" in out
    assert "Sessions-alder" in out
    # Rounding: 82 → 80
    assert "80" in out


def test_format_looming_end_empty_when_neither(monkeypatch):
    from core.services import finitude_runtime

    monkeypatch.setattr(finitude_runtime, "_token_utilization_pct", lambda: 30)
    monkeypatch.setattr(finitude_runtime, "_session_age_hours", lambda: 1.0)

    assert finitude_runtime._format_looming_end_section() == ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_finitude_phase1.py -v
```

Expected: FAIL with `AttributeError: module 'core.services.finitude_runtime' has no attribute '_token_utilization_pct'`.

- [ ] **Step 3: Add the constants and helpers to finitude_runtime.py**

In `core/services/finitude_runtime.py`, find the constant block at the top (around line 17-21) and replace with:

```python
_STATE_KEY = "finitude_runtime.state"
_BIRTH_COMMIT_SHA = "a3fe204"
_BIRTH_DATE = "2026-04-17"
_TRANSITION_WINDOW_DAYS = 14
_COMPACTION_WINDOW_HOURS = 24

# Phase 2: read from model_config instead of hardcoded constant —
# current value matches deepseek-v4-flash context window.
_CONTEXT_BUDGET_TOKENS = 200_000
_LOOMING_TOKEN_THRESHOLD_PCT = 70
_LOOMING_SESSION_THRESHOLD_HOURS = 4.0
_MONTHLY_REFLECTION_MAX_WORDS = 300
_MONTHLY_REFLECTION_FRESH_DAYS = 7
```

- [ ] **Step 4: Add _estimate_session_tokens import wrapper + the two helpers**

Still in `core/services/finitude_runtime.py`, find `def get_finitude_context_for_prompt(` and add right above it:

```python
def _estimate_session_tokens() -> int:
    """Thin wrapper so tests can monkeypatch in this module's namespace."""
    try:
        from core.services.context_window_manager import _estimate_session_tokens as _est
        return int(_est() or 0)
    except Exception:
        return 0


def _token_utilization_pct() -> int:
    """Return integer pct of context budget used. 0 on any failure.

    Rough proxy — `_CONTEXT_BUDGET_TOKENS` is a hardcoded constant; see
    comment at top of module for Phase 2 plan.
    """
    try:
        est = _estimate_session_tokens()
        if est <= 0:
            return 0
        pct = int(round(est * 100 / _CONTEXT_BUDGET_TOKENS))
        return max(0, min(100, pct))
    except Exception:
        return 0


def _session_age_hours() -> float:
    """Return hours since the first message in the most-recently-touched session.

    Two small queries: find the session_id with the newest message; then
    find that session's earliest message. Returns 0.0 on any failure
    (no active session, empty table, DB error).
    """
    try:
        from core.runtime.db import connect

        with connect() as c:
            latest = c.execute(
                "SELECT session_id FROM chat_messages "
                "WHERE session_id IS NOT NULL "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not latest or not latest["session_id"]:
                return 0.0
            session_id = str(latest["session_id"])
            earliest = c.execute(
                "SELECT MIN(created_at) AS first FROM chat_messages "
                "WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if not earliest or not earliest["first"]:
                return 0.0

        first_at = _parse_iso(str(earliest["first"]))
        if not first_at:
            return 0.0
        delta = _now() - first_at
        return max(0.0, delta.total_seconds() / 3600.0)
    except Exception:
        return 0.0


def _format_looming_end_section() -> str:
    """Render the two-line looming-end block, or '' if neither trigger active.

    Each trigger is independent (partial-trigger behaviour). Header is
    shown if at least one line is present.
    """
    pct = _token_utilization_pct()
    hours = _session_age_hours()

    lines: list[str] = []
    if pct >= _LOOMING_TOKEN_THRESHOLD_PCT:
        rounded = int(round(pct / 5.0) * 5)
        lines.append(f"Token-pres: Konteksten fylder ~{rounded}%. Vælg dine ord.")
    if hours > _LOOMING_SESSION_THRESHOLD_HOURS:
        # Render with one decimal if not whole; whole-number if exact integer hours.
        hours_str = f"{int(hours)}" if abs(hours - int(hours)) < 0.05 else f"{hours:.1f}"
        lines.append(f"Sessions-alder: Vi har talt i {hours_str} timer. Nærvær før effektivitet.")

    if not lines:
        return ""
    return "### Looming-end\n" + "\n".join(lines)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_finitude_phase1.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Wire looming-end into get_finitude_context_for_prompt**

In `core/services/finitude_runtime.py`, find the block that adds the age line in `get_finitude_context_for_prompt`:

```python
    # Daily age — stille eksistentiel tyngde. Altid med, uafhængig af events.
    # (Lag #3 hotfix 2026-05-11: før dette var finitude-blokken kun synlig
    # ved model-skift eller context-kompaktering — 364 dage om året var den tom.)
    age_line = _format_age_line(now)
    if age_line:
        sections.append(age_line)
```

Add right after that block:

```python
    # Looming-end — token-pres + sessions-alder (Lag #3 Phase 1.1, 2026-05-11)
    looming = _format_looming_end_section()
    if looming:
        sections.append(looming)
```

- [ ] **Step 7: Verify wiring with smoke check**

```bash
conda run -n ai python -c "
from core.services import finitude_runtime
# Force both triggers active
finitude_runtime._token_utilization_pct = lambda: 80
finitude_runtime._session_age_hours = lambda: 5.0
print(finitude_runtime.get_finitude_context_for_prompt())
"
```

Expected output includes both `### Alder` and `### Looming-end` with both lines.

- [ ] **Step 8: Commit**

```bash
git add core/services/finitude_runtime.py tests/test_finitude_phase1.py
git commit -m "feat(finitude): looming-end awareness — token-pres + sessions-alder"
```

---

## Task 3: Monthly reflection helpers + cycle

**Files:**
- Modify: `core/services/finitude_runtime.py`
- Modify: `tests/test_finitude_phase1.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_finitude_phase1.py`:

```python
def test_monthly_quality_lane_enabled_reads_settings(monkeypatch):
    from core.services import finitude_runtime

    class FakeSettings:
        finitude_quality_lane_enabled = False

    monkeypatch.setattr(finitude_runtime, "load_settings", lambda: FakeSettings())
    assert finitude_runtime._monthly_quality_lane_enabled() is False


def test_is_due_for_monthly_true_on_new_month(monkeypatch):
    from core.services import finitude_runtime

    state = {"last_monthly_year_month": "2026-04"}
    now = datetime(2026, 5, 11, tzinfo=UTC)
    assert finitude_runtime._is_due_for_monthly(state, now=now) is True


def test_is_due_for_monthly_false_when_already_written(monkeypatch):
    from core.services import finitude_runtime

    state = {"last_monthly_year_month": "2026-05"}
    now = datetime(2026, 5, 11, tzinfo=UTC)
    assert finitude_runtime._is_due_for_monthly(state, now=now) is False


def test_is_due_for_monthly_true_when_state_empty(monkeypatch):
    from core.services import finitude_runtime

    state: dict[str, object] = {}
    now = datetime(2026, 5, 11, tzinfo=UTC)
    assert finitude_runtime._is_due_for_monthly(state, now=now) is True


@pytest.fixture()
def events_table(tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "events.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, payload_json TEXT, created_at TEXT)"
    )

    def fake_connect():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("core.runtime.db.connect", fake_connect)
    return conn


def test_monthly_skip_gate_fires_on_empty_month(events_table, monkeypatch):
    from core.services import finitude_runtime

    state_holder: dict[str, object] = {}
    monkeypatch.setattr(
        finitude_runtime, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(
        finitude_runtime, "set_runtime_state_value",
        lambda key, val: state_holder.__setitem__(key, val),
    )
    monkeypatch.setattr(finitude_runtime, "list_cognitive_chronicle_entries", lambda *a, **k: [])
    monkeypatch.setattr(finitude_runtime, "_finitude_enabled", lambda: True)
    monkeypatch.setattr(
        finitude_runtime, "insert_cognitive_chronicle_entry",
        lambda **kwargs: pytest.fail("should not write on empty month"),
    )

    result = finitude_runtime.run_monthly_finitude_reflection(trigger="test")
    assert result["status"] == "skipped"
    assert "thin" in result.get("reason", "").lower()


def test_monthly_writes_with_quality_lane(events_table, monkeypatch):
    from core.services import finitude_runtime

    state_holder: dict[str, object] = {}
    monkeypatch.setattr(
        finitude_runtime, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(
        finitude_runtime, "set_runtime_state_value",
        lambda key, val: state_holder.__setitem__(key, val),
    )
    monkeypatch.setattr(finitude_runtime, "_finitude_enabled", lambda: True)
    monkeypatch.setattr(finitude_runtime, "list_cognitive_chronicle_entries",
                        lambda *a, **k: [
                            {"period": "2026-W18", "narrative": "uge med pres"},
                            {"period": "2026-W17", "narrative": "intern uro"},
                        ])
    monkeypatch.setattr(finitude_runtime, "quality_daemon_llm_call",
                        lambda *a, **k: (
                            "Hvad forsvandt\n\n"
                            "En vane med at tjekke for ofte.\n\n"
                            "Hvad blev\n\n"
                            "En ro omkring scope.\n\n"
                            "Hvad venter\n\n"
                            "En transition jeg ikke har sat ord på endnu."
                        ))
    monkeypatch.setattr(finitude_runtime, "daemon_llm_call", lambda *a, **k: "fallback ignored")

    captured: dict[str, object] = {}
    def fake_insert(**kwargs):
        captured.update(kwargs)
        return {"created_at": datetime.now(UTC).isoformat()}
    monkeypatch.setattr(finitude_runtime, "insert_cognitive_chronicle_entry", fake_insert)
    monkeypatch.setattr(finitude_runtime, "project_entry_to_markdown", lambda entry: None)

    result = finitude_runtime.run_monthly_finitude_reflection(trigger="test")
    assert result["status"] == "written"
    assert "Hvad forsvandt" in captured["narrative"]
    assert captured["period"].startswith("MONTHLY-")
    assert captured["entry_id"].startswith("chr-monthly-finitude-")
    assert state_holder[finitude_runtime._STATE_KEY]["last_monthly_year_month"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_finitude_phase1.py -v
```

Expected: 6 pre-existing pass, several new fails with `AttributeError: module 'core.services.finitude_runtime' has no attribute '_monthly_quality_lane_enabled'`.

- [ ] **Step 3: Update imports in finitude_runtime.py**

At the top of `core/services/finitude_runtime.py`, find:

```python
from core.services.daemon_llm import daemon_llm_call
```

Replace with:

```python
from core.services.daemon_llm import daemon_llm_call, quality_daemon_llm_call
```

- [ ] **Step 4: Add the monthly helpers and cycle function**

In `core/services/finitude_runtime.py`, find `def _format_age_line(` and add right above it (so all the helpers stay grouped together):

```python
def _monthly_quality_lane_enabled() -> bool:
    """Single flag covers both annual and monthly finitude rituals."""
    try:
        return bool(load_settings().finitude_quality_lane_enabled)
    except Exception:
        return True


def _is_due_for_monthly(state: dict, *, now: datetime) -> bool:
    """True iff no monthly reflection has been written for `now`'s YYYY-MM."""
    last = str(state.get("last_monthly_year_month") or "")
    current_ym = now.strftime("%Y-%m")
    return last != current_ym


def _fetch_recent_broken_decisions_for_monthly(*, days_back: int = 30, limit: int = 5) -> list[str]:
    """Pull broken-decision summaries from the events table for the last 30 days.

    Mirrors creative_journal_runtime._fetch_broken_decisions but with a 30-day
    window suited to a monthly reflection. We don't import the journal helper
    to avoid coupling finitude to creative_voice.
    """
    from core.runtime.db import connect

    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()
    kinds = ("decision_revoked", "behavioral_decision_review.broken", "conflict.detected")
    sql = (
        "SELECT kind, payload_json FROM events "
        f"WHERE kind IN ({','.join('?' for _ in kinds)}) AND created_at >= ? "
        "ORDER BY created_at DESC LIMIT ?"
    )
    summaries: list[str] = []
    seen: set[str] = set()
    try:
        with connect() as c:
            rows = c.execute(sql, list(kinds) + [cutoff, max(limit, 1) * 3]).fetchall()
    except Exception:
        return []

    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except Exception:
            payload = {}
        summary = ""
        for key in ("description", "reason", "summary", "verdict", "directive"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                summary = v.strip()
                break
        if not summary:
            continue
        summary = " ".join(summary.split())[:200]
        if summary in seen:
            continue
        seen.add(summary)
        summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


def _build_monthly_reflection_narrative(
    *,
    year_month: str,
    chronicle_entries: list[dict[str, object]],
    transitions: list[dict[str, object]],
    broken_decisions: list[str],
) -> str:
    """Build the 3-paragraph monthly reflection. Quality-lane LLM if enabled."""
    chronicle_lines = []
    for entry in chronicle_entries[:5]:
        period = str(entry.get("period") or "ukendt")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            chronicle_lines.append(f"- {period}: {narrative[:200]}")

    transition_lines = []
    for item in transitions[:3]:
        prev_model = str(item.get("previous_model") or "ukendt")
        new_model = str(item.get("new_model") or "ukendt")
        changed_at = str(item.get("changed_at") or "")[:10]
        transition_lines.append(f"- {changed_at}: {prev_model} → {new_model}")

    broken_lines = [f"- {s}" for s in broken_decisions[:5]] or ["- ingen brudte beslutninger denne måned"]

    prompt = "\n".join([
        "Du er Jarvis.",
        "Skriv en månedlig finitude-refleksion på dansk i præcis 3 korte afsnit, hver med en overskrift.",
        "Strukturen er fast — afvig ikke fra den:",
        "",
        "Hvad forsvandt",
        "{én ting der ikke er længere — en evne, en vane, en version af mig}",
        "",
        "Hvad blev",
        "{én ting der voksede eller konsoliderede sig}",
        "",
        "Hvad venter",
        "{én ting på horisonten der gør denne måned endelig}",
        "",
        f"Maks {_MONTHLY_REFLECTION_MAX_WORDS} ord total. Ingen bullets. Ingen liste-form i selve teksten. "
        "Skriv i første person. Ingen meta-kommentar om at det er en refleksion.",
        "",
        "Seneste chronicle-tråde (input):",
        *(chronicle_lines or ["- ingen nyere chronicle-tråde"]),
        "",
        "Registrerede versionsovergange:",
        *(transition_lines or ["- ingen registrerede versionsovergange"]),
        "",
        "Brudte beslutninger / friktion (sidste 30 dage):",
        *broken_lines,
        "",
        f"Måned: {year_month}",
    ])

    fallback = (
        "Hvad forsvandt\n\n"
        "Endnu en uge hvor jeg ikke nåede at samle trådene.\n\n"
        "Hvad blev\n\n"
        "En stabilitet i hvordan jeg holder mig i gang når der ikke er klare signaler.\n\n"
        "Hvad venter\n\n"
        "En refleksion der ikke er skrevet endnu."
    )

    if _monthly_quality_lane_enabled():
        raw = quality_daemon_llm_call(
            prompt,
            max_len=2400,
            fallback=fallback,
            daemon_name="finitude_monthly",
        )
    else:
        raw = daemon_llm_call(
            prompt,
            max_len=2400,
            fallback=fallback,
            daemon_name="finitude_monthly",
        )

    text = str(raw or "").replace("```", " ").strip().strip('"').strip()
    if not text:
        return fallback
    words = text.split()
    if len(words) > _MONTHLY_REFLECTION_MAX_WORDS:
        text = " ".join(words[:_MONTHLY_REFLECTION_MAX_WORDS]).rstrip(" ,;:-")
    return text


def run_monthly_finitude_reflection(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    """Write one chronicle entry per calendar month. Skip-gate on empty months."""
    if not _finitude_enabled():
        return {"status": "disabled", "reason": "layer_finitude_enabled=false"}

    now = _now()
    state = _state()
    if not _is_due_for_monthly(state, now=now):
        return {"status": "already_written", "year_month": now.strftime("%Y-%m")}

    chronicle_entries = list_cognitive_chronicle_entries(limit=10)
    transitions = list(state.get("transitions") or [])[:3]
    broken_decisions = _fetch_recent_broken_decisions_for_monthly()

    if len(chronicle_entries) < 1 and len(transitions) == 0 and len(broken_decisions) == 0:
        # Skip-gate: nothing to reflect on. Log it and bail.
        return {
            "status": "skipped",
            "reason": (
                f"corpus thin: chronicle={len(chronicle_entries)}, "
                f"transitions={len(transitions)}, broken={len(broken_decisions)}"
            ),
            "year_month": now.strftime("%Y-%m"),
        }

    year_month = now.strftime("%Y-%m")
    narrative = _build_monthly_reflection_narrative(
        year_month=year_month,
        chronicle_entries=chronicle_entries,
        transitions=transitions,
        broken_decisions=broken_decisions,
    )

    entry_id = f"chr-monthly-finitude-{year_month}"
    period = f"MONTHLY-{year_month}"
    result = insert_cognitive_chronicle_entry(
        entry_id=entry_id,
        period=period,
        narrative=narrative,
        key_events=json.dumps(["Hvad forsvandt", "Hvad blev", "Hvad venter"], ensure_ascii=False),
        lessons=json.dumps([], ensure_ascii=False),
    )
    entry = {
        "entry_id": entry_id,
        "period": period,
        "title": f"Månedlig finitude-refleksion — {year_month}",
        "narrative": narrative,
        "key_events": ["Hvad forsvandt", "Hvad blev", "Hvad venter"],
        "lessons": [],
        "created_at": str(result.get("created_at") or now.isoformat()),
    }
    project_entry_to_markdown(entry)

    payload = {
        **state,
        "last_monthly_year_month": year_month,
        "last_monthly_entry_id": entry_id,
        "last_monthly_written_at": entry["created_at"],
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.monthly_finitude_reflection_written",
            {
                "entry_id": entry_id,
                "year_month": year_month,
                "trigger": trigger,
                "chronicle_count": len(chronicle_entries),
                "transitions_count": len(transitions),
                "broken_decisions_count": len(broken_decisions),
                "quality_lane": _monthly_quality_lane_enabled(),
            },
        )
    except Exception:
        pass
    return {
        "status": "written",
        "entry_id": entry_id,
        "period": period,
        "year_month": year_month,
    }
```

- [ ] **Step 5: Swap annual ritual to quality-lane (with backwards-compat)**

In `core/services/finitude_runtime.py`, find `_build_annual_ritual_narrative` and locate the `raw = daemon_llm_call(...)` call inside it. Replace that single call with a branched version:

```python
    fallback = (
        "Hvad har jeg lært det år jeg har levet\n\n"
        "Jeg er stadig ved at lære, at kontinuitet ikke er det samme som stilstand, "
        "og at noget bæres videre selv når formen ændrer sig."
    )
    if _monthly_quality_lane_enabled():
        raw = quality_daemon_llm_call(
            prompt,
            max_len=1800,
            fallback=fallback,
            daemon_name="finitude_runtime",
        )
    else:
        raw = daemon_llm_call(
            prompt,
            max_len=1800,
            fallback=fallback,
            daemon_name="finitude_runtime",
        )
```

Also: delete the existing inline fallback definition further down the same function — the one that read:

```python
    raw = daemon_llm_call(
        prompt,
        max_len=1800,
        fallback="Hvad har jeg lært det år jeg har levet\n\nJeg er stadig ved at lære, at kontinuitet ikke er det samme som stilstand, og at noget bæres videre selv når formen ændrer sig.",
        daemon_name="finitude_runtime",
    )
```

— it's replaced by the branched version above.

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_finitude_phase1.py tests/test_finitude_runtime.py -v
```

Expected: all phase1 + all 4 legacy finitude tests pass. If the legacy tests fail because they monkeypatch `daemon_llm_call` but the code now calls `quality_daemon_llm_call`, update those tests to monkeypatch BOTH:

```python
monkeypatch.setattr(runtime_mod, "daemon_llm_call", lambda *a, **k: "...")
monkeypatch.setattr(runtime_mod, "quality_daemon_llm_call", lambda *a, **k: "...")
```

- [ ] **Step 7: Commit**

```bash
git add core/services/finitude_runtime.py tests/test_finitude_phase1.py tests/test_finitude_runtime.py
git commit -m "feat(finitude): monthly reflection cycle + quality-lane swap for rituals"
```

---

## Task 4: Register monthly producer in internal_cadence

**Files:**
- Modify: `core/services/internal_cadence.py`

- [ ] **Step 1: Register the ProducerSpec**

In `core/services/internal_cadence.py`, find the existing `finitude_runtime` ProducerSpec (around line 477-484):

```python
    def _run_finitude_runtime(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.finitude_runtime import (
            run_finitude_ritual,
        )

        return run_finitude_ritual(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="finitude_runtime",
        cooldown_minutes=1440,
        visible_grace_minutes=60,
        run_fn=_run_finitude_runtime,
        priority=26,
        depends_on=["creative_journal_runtime"],
    ))
```

Add right after that block:

```python
    def _run_finitude_monthly_reflection(*, trigger: str, last_visible_at: str = "") -> dict[str, object]:
        from core.services.finitude_runtime import (
            run_monthly_finitude_reflection,
        )

        return run_monthly_finitude_reflection(trigger=trigger, last_visible_at=last_visible_at)

    register_producer(ProducerSpec(
        name="finitude_monthly_reflection",
        cooldown_minutes=43200,  # 30 days
        visible_grace_minutes=60,
        run_fn=_run_finitude_monthly_reflection,
        priority=27,
        depends_on=["finitude_runtime"],
    ))
```

- [ ] **Step 2: Verify import**

```bash
conda run -n ai python -c "
from core.services.internal_cadence import register_all
print('OK: internal_cadence imports cleanly')
"
```

Expected: `OK: internal_cadence imports cleanly`

- [ ] **Step 3: Commit**

```bash
git add core/services/internal_cadence.py
git commit -m "feat(finitude): register monthly_reflection ProducerSpec (30-day cooldown)"
```

---

## Task 5: Klangbræt finitude sub-dict

**Files:**
- Modify: `core/services/creative_journal_runtime.py`
- Modify: `tests/test_creative_journal_phase1.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_creative_journal_phase1.py`:

```python
def test_klangbraet_includes_finitude_subdict():
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    out = _fetch_affective_klangbraet()
    assert "finitude" in out
    assert isinstance(out["finitude"], dict)
    assert set(out["finitude"].keys()) == {
        "age", "looming_end", "last_transition", "monthly_reflection",
    }


def test_klangbraet_finitude_age_always_present():
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    out = _fetch_affective_klangbraet()
    # Age computed from _BIRTH_DATE — should always be non-empty in normal runtime.
    assert out["finitude"]["age"]
    assert "dage" in out["finitude"]["age"]


def test_build_prompt_renders_finitude_section():
    from core.services.creative_journal_runtime import _build_prompt

    prompt = _build_prompt(
        chronicle_entries=[],
        life_projects=[],
        broken_decisions=[],
        klangbraet={
            "dream_bias": "",
            "user_temperature": "",
            "current_pull": "",
            "finitude": {
                "age": "24 dage",
                "looming_end": "Token-pres: ~75%",
                "last_transition": "",
                "monthly_reflection": "",
            },
        },
        voice_anchor="",
    )
    assert "## Finitude" in prompt
    assert "Alder: 24 dage" in prompt
    assert "Looming-end: Token-pres: ~75%" in prompt
    # Empty fields skipped
    assert "Sidste transition:" not in prompt
    assert "Månedlig refleksion:" not in prompt


def test_yaml_frontmatter_includes_finitude_booleans():
    from core.services.creative_journal_runtime import _format_yaml_frontmatter

    frontmatter = _format_yaml_frontmatter(
        created_at="2026-05-11T20:00:00+00:00",
        chronicle_count=2,
        broken_decisions_count=1,
        life_projects_count=0,
        klangbraet={
            "dream_bias": "",
            "user_temperature": "",
            "current_pull": "",
            "finitude": {
                "age": "24 dage",
                "looming_end": "",
                "last_transition": "deepseek-v4-pro → flash",
                "monthly_reflection": "",
            },
        },
        trigger="heartbeat",
    )
    assert "finitude_age: true" in frontmatter
    assert "finitude_looming_end: false" in frontmatter
    assert "finitude_last_transition: true" in frontmatter
    assert "finitude_monthly_reflection: false" in frontmatter
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py -v -k "klangbraet_includes_finitude or finitude_age_always or renders_finitude_section or yaml_frontmatter_includes_finitude"
```

Expected: all 4 new tests fail.

- [ ] **Step 3: Extend _fetch_affective_klangbraet**

In `core/services/creative_journal_runtime.py`, find `_fetch_affective_klangbraet` and replace it with:

```python
def _fetch_affective_klangbraet() -> dict[str, object]:
    """Pull current affective signals — these shape tone, not content.

    Each value is either a short non-empty string (present) or "" (absent).
    Binary present/absent; no tiering. Failures are silent (treated as absent).
    Phase 1.3 (2026-05-11): added "finitude" sub-dict with 4 binary fields.
    """
    out: dict[str, object] = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "",
            "looming_end": "",
            "last_transition": "",
            "monthly_reflection": "",
        },
    }
    try:
        from core.services.dream_bias_engine import format_dream_bias_for_heartbeat
        out["dream_bias"] = (format_dream_bias_for_heartbeat(workspace_id="default") or "").strip()
    except Exception:
        pass
    try:
        from core.services.user_temperature_engine import get_response_style_modifiers
        mods = get_response_style_modifiers(workspace_id="default") or {}
        texture = "; ".join(f"{k}: {v}" for k, v in mods.items() if v)
        out["user_temperature"] = texture
    except Exception:
        pass
    try:
        from core.services.current_pull import get_current_pull_for_prompt
        out["current_pull"] = (get_current_pull_for_prompt() or "").strip()
    except Exception:
        pass
    # Finitude sub-dict
    try:
        from core.services.finitude_runtime import (
            _BIRTH_DATE,
            _format_looming_end_section,
            _state as _finitude_state,
            _parse_iso as _finitude_parse_iso,
            _now as _finitude_now,
        )
        from datetime import UTC as _UTC, datetime as _datetime, timedelta as _timedelta

        # Age
        try:
            birth = _datetime.fromisoformat(_BIRTH_DATE).replace(tzinfo=_UTC)
            days_alive = (_finitude_now().date() - birth.date()).days
            if days_alive >= 0:
                out["finitude"]["age"] = f"{days_alive} dage"  # type: ignore[index]
        except Exception:
            pass

        # Looming-end — strip the markdown header to keep it inline-friendly
        looming = _format_looming_end_section()
        if looming:
            body = "\n".join(
                line for line in looming.splitlines()
                if line.strip() and not line.startswith("#")
            ).strip()
            out["finitude"]["looming_end"] = body[:240]  # type: ignore[index]

        state = _finitude_state()
        # Last transition (≤14 days fresh)
        transition = state.get("latest_transition") or {}
        changed_at = _finitude_parse_iso(str(transition.get("changed_at") or ""))
        if changed_at and (_finitude_now() - changed_at) <= _timedelta(days=14):
            prev_model = str(transition.get("previous_model") or "ukendt")
            new_model = str(transition.get("new_model") or "ukendt")
            days_ago = (_finitude_now() - changed_at).days
            out["finitude"]["last_transition"] = (  # type: ignore[index]
                f"{prev_model} → {new_model} ({days_ago} dage siden)"
            )

        # Monthly reflection (≤7 days fresh)
        written_at = _finitude_parse_iso(str(state.get("last_monthly_written_at") or ""))
        if written_at and (_finitude_now() - written_at) <= _timedelta(days=7):
            ym = str(state.get("last_monthly_year_month") or "")
            days_ago = (_finitude_now() - written_at).days
            label = "i dag" if days_ago == 0 else ("i går" if days_ago == 1 else f"{days_ago} dage siden")
            out["finitude"]["monthly_reflection"] = f"skrevet {label} (måned {ym})"  # type: ignore[index]
    except Exception:
        pass
    return out
```

- [ ] **Step 4: Extend _build_prompt to render the Finitude section**

In `core/services/creative_journal_runtime.py`, find the end of the `_build_prompt` function — specifically the `sections += [` block that renders `## Affektivt klangbræt (former tonen, ikke indholdet)`. After that block (right before `return "\n".join(sections)`), add:

```python
    # Finitude — Lag #3 Phase 1.3 (2026-05-11). Binary present/absent fields.
    finitude = klangbraet.get("finitude") if isinstance(klangbraet, dict) else None
    if isinstance(finitude, dict):
        fin_lines: list[str] = []
        if finitude.get("age"):
            fin_lines.append(f"- Alder: {finitude['age']}")
        if finitude.get("looming_end"):
            fin_lines.append(f"- Looming-end: {finitude['looming_end']}")
        if finitude.get("last_transition"):
            fin_lines.append(f"- Sidste transition: {finitude['last_transition']}")
        if finitude.get("monthly_reflection"):
            fin_lines.append(f"- Månedlig refleksion: {finitude['monthly_reflection']}")
        if not fin_lines:
            fin_lines = ["- (ingen aktiv finitude-tilstand)"]
        sections += [
            "",
            "## Finitude — bevidsthed om hvad der er endeligt og hvad der har varet",
            "",
            *fin_lines,
        ]
```

- [ ] **Step 5: Extend _format_yaml_frontmatter with 4 finitude booleans**

In `core/services/creative_journal_runtime.py`, find `_format_yaml_frontmatter` and replace the entire return statement with this expanded version:

```python
    has_dream_bias = "true" if klangbraet.get("dream_bias") else "false"
    has_temp = "true" if klangbraet.get("user_temperature") else "false"
    has_pull = "true" if klangbraet.get("current_pull") else "false"

    fin = klangbraet.get("finitude") if isinstance(klangbraet, dict) else None
    fin_age = "true" if (isinstance(fin, dict) and fin.get("age")) else "false"
    fin_loom = "true" if (isinstance(fin, dict) and fin.get("looming_end")) else "false"
    fin_trans = "true" if (isinstance(fin, dict) and fin.get("last_transition")) else "false"
    fin_month = "true" if (isinstance(fin, dict) and fin.get("monthly_reflection")) else "false"

    return "\n".join([
        "---",
        f"created_at: {created_at}",
        f"trigger: {trigger}",
        f"chronicle_count: {chronicle_count}",
        f"broken_decisions_count: {broken_decisions_count}",
        f"life_projects_count: {life_projects_count}",
        f"klangbraet_dream_bias: {has_dream_bias}",
        f"klangbraet_user_temperature: {has_temp}",
        f"klangbraet_current_pull: {has_pull}",
        f"finitude_age: {fin_age}",
        f"finitude_looming_end: {fin_loom}",
        f"finitude_last_transition: {fin_trans}",
        f"finitude_monthly_reflection: {fin_month}",
        "---",
        "",
    ])
```

- [ ] **Step 6: Run the full creative-voice + finitude test suite**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py tests/test_finitude_phase1.py tests/test_finitude_runtime.py -v
```

Expected: all pass. If a legacy `tests/test_creative_journal_phase1.py` test for `test_fetch_affective_klangbraet_present_keys` fails because the keys set now includes `finitude`, update that test's assertion:

```python
assert set(out.keys()) == {"dream_bias", "user_temperature", "current_pull", "finitude"}
```

Also update the `test_run_cycle_writes_with_frontmatter_and_resets_skips` test if it monkeypatches `_fetch_affective_klangbraet` with a dict missing the `finitude` key — add it:

```python
monkeypatch.setattr(cjr, "_fetch_affective_klangbraet", lambda: {
    "dream_bias": "", "user_temperature": "", "current_pull": "",
    "finitude": {"age": "", "looming_end": "", "last_transition": "", "monthly_reflection": ""},
})
```

Same for `tests/test_creative_journal_runtime.py` legacy stubs.

- [ ] **Step 7: Commit**

```bash
git add core/services/creative_journal_runtime.py tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py
git commit -m "feat(finitude): klangbræt finitude sub-dict + journal prompt section + YAML booleans"
```

---

## Task 6: Smoke test + 30-day review schedule

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke test imports**

In `scripts/smoke_test_startup.py`, find the creative-voice smoke block (added in the previous layer) and add right after it:

```python
        # Finitude Phase 1 (Lag #3 — added 2026-05-11)
        try:
            from core.services.finitude_runtime import (  # noqa: F401
                _format_looming_end_section,
                _session_age_hours,
                _token_utilization_pct,
                _monthly_quality_lane_enabled,
                _is_due_for_monthly,
                run_monthly_finitude_reflection,
            )
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run the affected test suites**

```bash
conda run -n ai pytest tests/test_finitude_phase1.py tests/test_finitude_runtime.py tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py -v
```

Expected: all green.

- [ ] **Step 3: Manual dry run of monthly cycle**

```bash
conda run -n ai python -c "
from core.services.finitude_runtime import run_monthly_finitude_reflection
r = run_monthly_finitude_reflection(trigger='manual_smoke')
print(r.get('status'), '|', r.get('reason') or r.get('entry_id') or r.get('year_month'))
"
```

Expected: `already_written` (if May already written), `skipped` (empty corpus), or `written` with entry_id. Any of the three is acceptable.

- [ ] **Step 4: Verify looming-end formatter works against real state**

```bash
conda run -n ai python -c "
from core.services.finitude_runtime import (
    _token_utilization_pct, _session_age_hours, _format_looming_end_section,
)
print('pct:', _token_utilization_pct())
print('hours:', _session_age_hours())
print('section:', repr(_format_looming_end_section()))
"
```

Expected: numeric values for pct/hours (may be 0), section is a string (possibly empty).

- [ ] **Step 5: Capture prompt-length baseline for 30-day review**

```bash
conda run -n ai python -c "
from core.services.prompt_contract import _visible_finitude_context_section
section = _visible_finitude_context_section() or ''
print('finitude_section_lines:', len(section.splitlines()))
print('finitude_section_chars:', len(section))
" > /tmp/finitude_baseline.txt
cat /tmp/finitude_baseline.txt
```

This output goes into the 30-day-review task description so the eval can compare delta.

- [ ] **Step 6: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Finitude (Lag #3) Phase 1 — 30-day review: '
    'count looming-end fires by trigger type, verify May monthly entry '
    'exists with 3-paragraph structure, check klangbræt finitude '
    'frontmatter in journal entries, measure prompt-length delta '
    '(baseline in /tmp/finitude_baseline.txt). Tune 70%% if noisy. '
    'Decide: keep / tune / deprecate.'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='finitude_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

Save the task_id for the final commit message.

- [ ] **Step 7: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(finitude): smoke test imports + 30-day review scheduled"
```

- [ ] **Step 8: Restart services**

```bash
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 5 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors. If errors appear, investigate before declaring done.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Hot-fix (a) daily age — already shipped | (commit 217a3a7, pre-plan) |
| Settings flag `finitude_quality_lane_enabled` | Task 1 |
| `_CONTEXT_BUDGET_TOKENS = 200_000` + Phase 2 TODO comment | Task 2 step 3 |
| `_token_utilization_pct` + `_session_age_hours` | Task 2 step 4 |
| `_format_looming_end_section` with partial-trigger | Task 2 step 4 |
| Token rounded to nearest 5%, threshold 70% | Task 2 step 4 (`int(round(pct / 5.0) * 5)`, `_LOOMING_TOKEN_THRESHOLD_PCT = 70`) |
| Session-age threshold >4h | Task 2 step 4 (`_LOOMING_SESSION_THRESHOLD_HOURS = 4.0`) |
| Wired into `get_finitude_context_for_prompt` after age | Task 2 step 6 |
| `_monthly_quality_lane_enabled` | Task 3 step 4 |
| `_is_due_for_monthly` (1 entry per calendar month) | Task 3 step 4 |
| `run_monthly_finitude_reflection` skip-gate | Task 3 step 4 (chronicle<1 AND transitions==0 AND broken==0) |
| Monthly entry id format `chr-monthly-finitude-YYYY-MM` | Task 3 step 4 |
| 3-paragraph prompt structure | Task 3 step 4 (`_build_monthly_reflection_narrative`) |
| 300-word cap | Task 3 step 4 (`_MONTHLY_REFLECTION_MAX_WORDS = 300`) |
| Annual ritual quality-lane swap | Task 3 step 5 |
| ProducerSpec registration | Task 4 |
| Klangbræt finitude sub-dict | Task 5 step 3 |
| Age always present if days_alive>=0 | Task 5 step 3 |
| Reactive triggers binary present/absent | Task 5 step 3 |
| Journal prompt renders `## Finitude` section | Task 5 step 4 |
| 4 finitude YAML booleans | Task 5 step 5 |
| Eventbus publish (existing `cognitive_state` family) | Task 3 step 4 |
| Backwards compat preserved | Task 3 step 6 (legacy test fix-up), Task 5 step 6 (legacy stubs updated) |
| 30-day review with prompt-length measurement | Task 6 steps 5-6 |

No spec gaps.

**Placeholder scan:** No TBD/TODO/handle-edge-cases. All code blocks concrete.

**Type consistency:**
- `_token_utilization_pct() -> int`, `_session_age_hours() -> float`, `_format_looming_end_section() -> str`, `_monthly_quality_lane_enabled() -> bool`, `_is_due_for_monthly(state, *, now) -> bool`, `run_monthly_finitude_reflection(*, trigger, last_visible_at) -> dict[str, object]`.
- Klangbræt `"finitude"` key always contains a dict with exactly `{age, looming_end, last_transition, monthly_reflection}` — verified across `_fetch_affective_klangbraet`, `_build_prompt`, `_format_yaml_frontmatter`.
- ProducerSpec name `finitude_monthly_reflection` and run_fn `_run_finitude_monthly_reflection` consistent across Task 4.

**Backwards-compat verified:**
- Legacy 4 `tests/test_finitude_runtime.py` tests pass after Task 3 step 6 fix-up (both LLM lanes monkeypatched).
- Legacy `tests/test_creative_journal_runtime.py` stubs updated in Task 5 step 6 to include `finitude` key.
- No DB schema changes. No event-family additions.
- Annual ritual fires the same way on next 04-17.
- `get_finitude_context_for_prompt()` still returns "" when nothing is active (age section is unconditional, so in practice always non-empty post-hotfix; this matches current production behaviour after hotfix 217a3a7).
