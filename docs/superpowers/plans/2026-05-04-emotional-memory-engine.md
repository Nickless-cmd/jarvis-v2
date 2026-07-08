---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Emotional Memory Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a unified emotional memory engine that captures affective state at runtime anchors (cognitive episodes, perceptual events, MEMORY.md headings) and surfaces "emotional precedent" cues in the cognitive frame when similar past situations are detected.

**Architecture:** Single new module `core/services/emotional_memory_engine.py` with one new SQLite table `emotional_memory_anchors`. Three integration points (cognitive_episodes cascade, perceptual_event_engine, memory_emotional_context shim) all call into the same `capture_emotional_anchor()` API. Conductor reads via `_safe_emotional_memory_surface()` and injects "Emotional precedent" line into the cognitive frame prompt section.

**Tech Stack:** Python 3.11+, SQLite via `core/runtime/db.py`, existing test infrastructure (`isolated_runtime` fixture in `tests/conftest.py`), pytest.

**Spec:** `docs/superpowers/specs/2026-05-04-emotional-memory-engine-design.md`

---

## File Structure

**Create:**
- `core/runtime/db_emotional_memory.py` — DB helpers for new table (boy scout split — db.py is 33k lines)
- `core/services/emotional_memory_engine.py` — main module (capture/retrieve/surface)
- `scripts/migrate_emotional_memory.py` — one-shot migration of `memory_emotional_context` data
- `tests/test_emotional_memory_engine.py` — unit tests
- `tests/test_emotional_memory_integration.py` — capture-cascade + conductor end-to-end
- `tests/test_memory_emotional_context_shim.py` — backwards compatibility
- `tests/test_emotional_memory_migration.py` — migration idempotency

**Modify:**
- `core/runtime/db.py` — re-export new helpers from `db_emotional_memory.py`
- `core/runtime/settings.py` — add 5 RuntimeSettings fields
- `core/services/cognitive_episodes.py` — add capture call to cascade
- `core/services/perceptual_event_engine.py` — add capture call to `record_perceptual_event`
- `core/services/memory_emotional_context.py` — reduce to thin shim that delegates
- `core/services/runtime_cognitive_conductor.py` — add `_safe_emotional_memory_surface()` and salient-item injection

---

## Task 1: DB schema and helpers

**Files:**
- Create: `core/runtime/db_emotional_memory.py`
- Create: `tests/test_db_emotional_memory.py`
- Modify: `core/runtime/db.py` (re-export at top of file with other DB helper imports)

- [ ] **Step 1: Write the failing test**

Create `tests/test_db_emotional_memory.py`:

```python
from __future__ import annotations


def test_insert_and_get_emotional_memory_anchor(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        get_emotional_memory_anchor,
    )

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-test-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="frustrated",
        intensity=0.62,
        confidence=0.4,
        curiosity=0.3,
        frustration=0.7,
        fatigue=0.5,
        trust=0.6,
        outcome_score=-0.4,
        outcome_source="auto",
        context_features_json='{"trigger": "visible-run:ollama/glm"}',
        source="cognitive_episodes",
    )

    row = get_emotional_memory_anchor(
        anchor_type="cognitive_episode", anchor_id="ce-test-1"
    )
    assert row is not None
    assert row["mood"] == "frustrated"
    assert abs(float(row["intensity"]) - 0.62) < 1e-6
    assert row["outcome_score"] == -0.4
    assert row["outcome_source"] == "auto"


def test_insert_is_idempotent_upsert(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )

    for intensity in (0.3, 0.7):
        insert_emotional_memory_anchor(
            anchor_type="memory_heading",
            anchor_id="some-heading",
            captured_at="2026-05-04T12:00:00+00:00",
            mood="content",
            intensity=intensity,
            context_features_json='{"heading_display": "Some Heading"}',
        )

    rows = list_emotional_memory_anchors(anchor_type="memory_heading")
    assert len(rows) == 1
    assert abs(float(rows[0]["intensity"]) - 0.7) < 1e-6


def test_list_filters_by_type_and_min_intensity(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-low",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="calm",
        intensity=0.2,
        context_features_json="{}",
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-high",
        captured_at="2026-05-04T12:01:00+00:00",
        mood="frustrated",
        intensity=0.8,
        context_features_json="{}",
    )
    insert_emotional_memory_anchor(
        anchor_type="memory_heading",
        anchor_id="other",
        captured_at="2026-05-04T12:02:00+00:00",
        mood="content",
        intensity=0.9,
        context_features_json="{}",
    )

    rows = list_emotional_memory_anchors(
        anchor_type="cognitive_episode", min_intensity=0.5
    )
    assert len(rows) == 1
    assert rows[0]["anchor_id"] == "ce-high"


def test_update_outcome_respects_force_flag(isolated_runtime) -> None:
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        update_emotional_memory_outcome,
        get_emotional_memory_anchor,
    )

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="x",
        intensity=0.5,
        outcome_score=-0.4,
        outcome_source="auto",
        context_features_json="{}",
    )

    update_emotional_memory_outcome(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        score=-0.7,
        source="override:self_review",
        force=False,
    )
    row = get_emotional_memory_anchor("cognitive_episode", "ce-1")
    assert row["outcome_score"] == -0.7  # auto can be overridden without force

    update_emotional_memory_outcome(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        score=0.2,
        source="override:learning_policy",
        force=False,
    )
    row = get_emotional_memory_anchor("cognitive_episode", "ce-1")
    assert row["outcome_score"] == -0.7  # override-of-override blocked without force

    update_emotional_memory_outcome(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        score=0.2,
        source="override:learning_policy",
        force=True,
    )
    row = get_emotional_memory_anchor("cognitive_episode", "ce-1")
    assert row["outcome_score"] == 0.2  # force=True wins
```

- [ ] **Step 2: Run test to verify it fails**

```
conda activate ai
pytest tests/test_db_emotional_memory.py -v
```

Expected: FAIL with `ImportError: cannot import name 'insert_emotional_memory_anchor' from 'core.runtime.db'`

- [ ] **Step 3: Create the DB helper module**

Create `core/runtime/db_emotional_memory.py`:

```python
"""DB helpers for emotional_memory_anchors table.

Split out from db.py per CLAUDE.md boy scout rule (db.py is 33k lines).
Re-exported from core.runtime.db for backwards compatibility.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any

from core.runtime.db import connect, _now_iso


def _ensure_emotional_memory_anchors_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS emotional_memory_anchors (
            anchor_type        TEXT NOT NULL,
            anchor_id          TEXT NOT NULL,
            captured_at        TEXT NOT NULL,
            mood               TEXT NOT NULL,
            intensity          REAL NOT NULL,
            confidence         REAL,
            curiosity          REAL,
            frustration        REAL,
            fatigue            REAL,
            trust              REAL,
            outcome_score      REAL,
            outcome_source     TEXT,
            outcome_updated_at TEXT,
            context_features_json TEXT NOT NULL DEFAULT '{}',
            source             TEXT,
            notes              TEXT,
            PRIMARY KEY (anchor_type, anchor_id)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_emo_mem_type_time
            ON emotional_memory_anchors (anchor_type, captured_at DESC)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_emo_mem_outcome
            ON emotional_memory_anchors (outcome_score)
            WHERE outcome_score IS NOT NULL
        """
    )


def insert_emotional_memory_anchor(
    *,
    anchor_type: str,
    anchor_id: str,
    captured_at: str,
    mood: str,
    intensity: float,
    confidence: float | None = None,
    curiosity: float | None = None,
    frustration: float | None = None,
    fatigue: float | None = None,
    trust: float | None = None,
    outcome_score: float | None = None,
    outcome_source: str | None = None,
    context_features_json: str = "{}",
    source: str | None = None,
    notes: str | None = None,
) -> dict[str, object]:
    """UPSERT an emotional memory anchor. Idempotent on (anchor_type, anchor_id)."""
    last_err: Exception | None = None
    for attempt in range(2):
        try:
            with connect() as conn:
                _ensure_emotional_memory_anchors_table(conn)
                conn.execute(
                    """
                    INSERT INTO emotional_memory_anchors
                        (anchor_type, anchor_id, captured_at, mood, intensity,
                         confidence, curiosity, frustration, fatigue, trust,
                         outcome_score, outcome_source, outcome_updated_at,
                         context_features_json, source, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(anchor_type, anchor_id) DO UPDATE SET
                        captured_at=excluded.captured_at,
                        mood=excluded.mood,
                        intensity=excluded.intensity,
                        confidence=excluded.confidence,
                        curiosity=excluded.curiosity,
                        frustration=excluded.frustration,
                        fatigue=excluded.fatigue,
                        trust=excluded.trust,
                        outcome_score=excluded.outcome_score,
                        outcome_source=excluded.outcome_source,
                        outcome_updated_at=excluded.outcome_updated_at,
                        context_features_json=excluded.context_features_json,
                        source=excluded.source,
                        notes=excluded.notes
                    """,
                    (
                        str(anchor_type)[:60],
                        str(anchor_id)[:240],
                        str(captured_at),
                        str(mood)[:60],
                        float(intensity),
                        confidence,
                        curiosity,
                        frustration,
                        fatigue,
                        trust,
                        outcome_score,
                        outcome_source,
                        _now_iso() if outcome_score is not None else None,
                        str(context_features_json or "{}"),
                        source,
                        notes,
                    ),
                )
            return {"anchor_type": anchor_type, "anchor_id": anchor_id, "captured_at": captured_at}
        except sqlite3.OperationalError as exc:
            last_err = exc
            if attempt == 0:
                time.sleep(0.05)
                continue
            raise
    if last_err:
        raise last_err
    return {"anchor_type": anchor_type, "anchor_id": anchor_id, "captured_at": captured_at}


def get_emotional_memory_anchor(
    anchor_type: str, anchor_id: str
) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        row = conn.execute(
            "SELECT * FROM emotional_memory_anchors WHERE anchor_type=? AND anchor_id=?",
            (str(anchor_type), str(anchor_id)),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def list_emotional_memory_anchors(
    *,
    anchor_type: str | None = None,
    since: str | None = None,
    min_intensity: float | None = None,
    outcome: str | None = None,
    limit: int = 50,
) -> list[dict[str, object]]:
    """Return anchors filtered and ordered by captured_at DESC."""
    where: list[str] = []
    params: list[Any] = []
    if anchor_type:
        where.append("anchor_type = ?")
        params.append(str(anchor_type))
    if since:
        where.append("captured_at >= ?")
        params.append(str(since))
    if min_intensity is not None:
        where.append("intensity >= ?")
        params.append(float(min_intensity))
    if outcome == "bad":
        where.append("outcome_score IS NOT NULL AND outcome_score < -0.2")
    elif outcome == "good":
        where.append("outcome_score IS NOT NULL AND outcome_score > 0.2")

    sql = "SELECT * FROM emotional_memory_anchors"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY captured_at DESC LIMIT ?"
    params.append(max(int(limit), 1))

    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_emotional_memory_outcome(
    *,
    anchor_type: str,
    anchor_id: str,
    score: float,
    source: str,
    force: bool = False,
) -> bool:
    """Update outcome score. Returns True if updated, False if blocked.

    An explicit override (source starting with 'override:') can be replaced by
    another explicit override only if force=True. Auto-derived outcomes can
    always be overridden without force.
    """
    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        existing = conn.execute(
            "SELECT outcome_source FROM emotional_memory_anchors WHERE anchor_type=? AND anchor_id=?",
            (str(anchor_type), str(anchor_id)),
        ).fetchone()
        if existing is None:
            return False
        existing_source = str(existing["outcome_source"] or "")
        is_existing_override = existing_source.startswith("override:")
        if is_existing_override and not force:
            return False
        conn.execute(
            """
            UPDATE emotional_memory_anchors
            SET outcome_score = ?, outcome_source = ?, outcome_updated_at = ?
            WHERE anchor_type = ? AND anchor_id = ?
            """,
            (float(score), str(source)[:60], _now_iso(), str(anchor_type), str(anchor_id)),
        )
    return True


def delete_emotional_memory_anchor(anchor_type: str, anchor_id: str) -> bool:
    with connect() as conn:
        _ensure_emotional_memory_anchors_table(conn)
        cur = conn.execute(
            "DELETE FROM emotional_memory_anchors WHERE anchor_type=? AND anchor_id=?",
            (str(anchor_type), str(anchor_id)),
        )
        return cur.rowcount > 0


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "anchor_type": row["anchor_type"],
        "anchor_id": row["anchor_id"],
        "captured_at": row["captured_at"],
        "mood": row["mood"],
        "intensity": row["intensity"],
        "confidence": row["confidence"],
        "curiosity": row["curiosity"],
        "frustration": row["frustration"],
        "fatigue": row["fatigue"],
        "trust": row["trust"],
        "outcome_score": row["outcome_score"],
        "outcome_source": row["outcome_source"],
        "outcome_updated_at": row["outcome_updated_at"],
        "context_features_json": row["context_features_json"],
        "source": row["source"],
        "notes": row["notes"],
    }
```

- [ ] **Step 4: Re-export from db.py**

At the end of `core/runtime/db.py`, add (find the section where other modules are re-imported, or append at end before `if __name__ == "__main__":` if any):

```python
# --- Emotional memory anchors (split into db_emotional_memory.py per boy scout rule) ---
from core.runtime.db_emotional_memory import (  # noqa: E402,F401
    insert_emotional_memory_anchor,
    get_emotional_memory_anchor,
    list_emotional_memory_anchors,
    update_emotional_memory_outcome,
    delete_emotional_memory_anchor,
)
```

- [ ] **Step 5: Run test to verify it passes**

```
pytest tests/test_db_emotional_memory.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add core/runtime/db_emotional_memory.py core/runtime/db.py tests/test_db_emotional_memory.py
git commit -m "feat(emotional-memory): db schema and helpers for emotional_memory_anchors"
```

---

## Task 2: RuntimeSettings fields

**Files:**
- Modify: `core/runtime/settings.py`
- Test: `tests/test_emotional_memory_settings.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_emotional_memory_settings.py`:

```python
from __future__ import annotations


def test_emotional_memory_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    settings = load_settings()
    assert settings.emotional_memory_min_anchors == 2
    assert settings.emotional_memory_retention_recent_days == 30
    assert settings.emotional_memory_retention_aging_days == 180
    assert settings.emotional_memory_significance_intensity == 0.7
    assert settings.emotional_memory_significance_outcome == -0.3
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_emotional_memory_settings.py -v
```

Expected: FAIL with `AttributeError: ... has no attribute 'emotional_memory_min_anchors'`

- [ ] **Step 3: Add fields to RuntimeSettings**

Find the `RuntimeSettings` dataclass in `core/runtime/settings.py` (search for `class RuntimeSettings` or `@dataclass`). Add these five fields alongside other configuration fields (preserve alphabetical/grouping convention if any):

```python
    emotional_memory_min_anchors: int = 2
    emotional_memory_retention_recent_days: int = 30
    emotional_memory_retention_aging_days: int = 180
    emotional_memory_significance_intensity: float = 0.7
    emotional_memory_significance_outcome: float = -0.3
```

If there is a deserializer that maps JSON keys to dataclass fields (look for `_settings_from_dict` or similar), make sure these new fields are picked up — the standard dataclass `**kwargs` pattern usually handles it automatically. If load_settings uses an explicit field allow-list, add the five new keys.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_emotional_memory_settings.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py tests/test_emotional_memory_settings.py
git commit -m "feat(emotional-memory): runtime settings for thresholds and retention"
```

---

## Task 3: capture_emotional_anchor — outcome auto-deriv only

**Goal:** Get the auto-deriv outcome scoring tested and passing first, without affect/persistence yet. Pure-function isolation.

**Files:**
- Create: `core/services/emotional_memory_engine.py`
- Test: in `tests/test_emotional_memory_engine.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_emotional_memory_engine.py`:

```python
from __future__ import annotations


def test_outcome_auto_deriv_completed_no_error_is_positive() -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="completed", error="", tool_error_count=0
    )
    assert score is not None
    assert 0.5 < score < 0.7
    assert source == "auto"


def test_outcome_auto_deriv_completed_with_errors_is_neutral() -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="completed", error="some error", tool_error_count=1
    )
    assert score == 0.0
    assert source == "auto"


def test_outcome_auto_deriv_interrupted_is_negative() -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="interrupted", error="", tool_error_count=0
    )
    assert score is not None
    assert -0.5 < score < -0.3
    assert source == "auto"


def test_outcome_auto_deriv_timeout_error_is_strongly_negative() -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="error", error="upstream timeout while reading", tool_error_count=0
    )
    assert score is not None
    assert -0.8 < score < -0.6
    assert source == "auto"


def test_outcome_auto_deriv_bad_request_is_strongly_negative() -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="error", error="HTTP 400 bad request", tool_error_count=0
    )
    assert score is not None
    assert -0.8 < score < -0.6
    assert source == "auto"


def test_outcome_auto_deriv_unknown_status_returns_none() -> None:
    from core.services.emotional_memory_engine import _derive_outcome_score

    score, source = _derive_outcome_score(
        status="something_weird", error="", tool_error_count=0
    )
    assert score is None
    assert source is None


def test_classify_error_categories() -> None:
    from core.services.emotional_memory_engine import _classify_error

    assert _classify_error("upstream timeout") == "timeout"
    assert _classify_error("HTTP 400 Bad Request") == "bad_request"
    assert _classify_error("tool xyz failed: read error") == "tool_error"
    assert _classify_error("") == "none"
    assert _classify_error("unknown gibberish") == "other"


def test_count_tool_errors_heuristic() -> None:
    from core.services.emotional_memory_engine import _count_tool_errors

    assert _count_tool_errors("", []) == 0
    assert _count_tool_errors("tool x failed", ["x"]) == 1
    assert _count_tool_errors(
        "tool a failed; tool b error: 500", ["a", "b", "c"]
    ) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.emotional_memory_engine'`

- [ ] **Step 3: Create the module with helpers only**

Create `core/services/emotional_memory_engine.py`:

```python
"""Emotional memory engine.

Captures affective state at runtime anchors (cognitive episodes, perceptual
events, MEMORY.md headings), retrieves similar past anchors via tiered
matching, and surfaces "emotional precedent" cues to the cognitive
conductor.

See docs/superpowers/specs/2026-05-04-emotional-memory-engine-design.md
for the full design.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Outcome auto-derivation
# ---------------------------------------------------------------------------


def _classify_error(error: str) -> str:
    """Map raw error text to a coarse category for retrieval matching."""
    text = (error or "").lower()
    if not text.strip():
        return "none"
    if "timeout" in text or "timed out" in text:
        return "timeout"
    if "bad request" in text or "http 400" in text:
        return "bad_request"
    if "tool" in text and ("error" in text or "fail" in text):
        return "tool_error"
    return "other"


def _count_tool_errors(error: str, tool_names: list[str]) -> int:
    """Heuristically count how many tools in a run failed.

    Looks for occurrences of "tool <name> ... fail|error" patterns. This is
    intentionally rough — the goal is a 0/1/many bucket for outcome scoring.
    """
    text = (error or "").lower()
    if not text.strip():
        return 0
    count = 0
    for name in tool_names or []:
        nm = str(name or "").lower().strip()
        if not nm:
            continue
        if nm in text and ("error" in text or "fail" in text):
            count += 1
    if count == 0:
        # Fallback: count "fail" or "error" occurrences as a proxy when we
        # cannot attribute to specific tool names.
        if "fail" in text or "error" in text:
            return 1
    return count


def _derive_outcome_score(
    *, status: str, error: str, tool_error_count: int
) -> tuple[float | None, str | None]:
    """Auto-deriv outcome score from structured episode fields.

    Returns (score, source) where score is in [-1, 1] and source is "auto"
    or None when no determination can be made.
    """
    s = (status or "").strip().lower()
    err = (error or "").lower()
    has_error = bool(err.strip())
    has_strong_error = "timeout" in err or "bad request" in err or "http 400" in err

    if s == "completed" and not has_error and tool_error_count == 0:
        return (0.6, "auto")
    if s == "completed" and (has_error or tool_error_count > 0):
        return (0.0, "auto")
    if s == "interrupted":
        return (-0.4, "auto")
    if has_strong_error or s == "error":
        return (-0.7, "auto")
    if s == "cancelled":
        return (-0.1, "auto")
    return (None, None)
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/emotional_memory_engine.py tests/test_emotional_memory_engine.py
git commit -m "feat(emotional-memory): outcome auto-deriv helpers"
```

---

## Task 4: capture_emotional_anchor — full capture with persistence

**Files:**
- Modify: `core/services/emotional_memory_engine.py`
- Modify: `tests/test_emotional_memory_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emotional_memory_engine.py`:

```python
def test_capture_persists_full_affect_vector(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import get_emotional_memory_anchor
    from core.services import emotional_memory_engine as em

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("frustrated", 0.62))
    monkeypatch.setattr(
        em,
        "_read_current_dimensions",
        lambda: {
            "confidence": 0.4,
            "curiosity": 0.3,
            "frustration": 0.7,
            "fatigue": 0.5,
            "trust": 0.6,
        },
    )

    result = em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-x1",
        context_features={"trigger": "visible-run:ollama/glm", "tool_names": ["a"]},
        auto_outcome_inputs={
            "outcome_status": "interrupted",
            "error": "",
            "tool_error_count": 0,
        },
        source="cognitive_episodes",
    )
    assert result is not None
    assert result["mood"] == "frustrated"

    row = get_emotional_memory_anchor("cognitive_episode", "ce-x1")
    assert row is not None
    assert row["frustration"] == 0.7
    assert row["fatigue"] == 0.5
    assert row["outcome_score"] == -0.4
    assert row["outcome_source"] == "auto"


def test_capture_with_unavailable_dimensions_still_persists_mood(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import get_emotional_memory_anchor
    from core.services import emotional_memory_engine as em

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.4))

    def _raise():
        raise RuntimeError("affect surface broken")

    monkeypatch.setattr(em, "_read_current_dimensions", _raise)

    em.capture_emotional_anchor(
        anchor_type="memory_heading",
        anchor_id="some-heading",
        context_features={"heading_display": "Some Heading"},
    )
    row = get_emotional_memory_anchor("memory_heading", "some-heading")
    assert row is not None
    assert row["mood"] == "calm"
    assert row["confidence"] is None
    assert row["frustration"] is None


def test_capture_returns_none_when_mood_unavailable(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em

    def _raise():
        raise RuntimeError("oscillator down")

    monkeypatch.setattr(em, "_read_current_mood", _raise)

    result = em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-broken",
        context_features={},
    )
    assert result is None


def test_capture_idempotent_overwrites_existing(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import get_emotional_memory_anchor, list_emotional_memory_anchors
    from core.services import emotional_memory_engine as em

    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.3))
    em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-dup",
        context_features={},
    )

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("frustrated", 0.7))
    em.capture_emotional_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-dup",
        context_features={},
    )

    rows = list_emotional_memory_anchors(anchor_type="cognitive_episode")
    assert len(rows) == 1
    row = get_emotional_memory_anchor("cognitive_episode", "ce-dup")
    assert row["mood"] == "frustrated"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: FAIL — `capture_emotional_anchor` not yet defined.

- [ ] **Step 3: Implement capture in `emotional_memory_engine.py`**

Append to `core/services/emotional_memory_engine.py`:

```python
import json
import random
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import insert_emotional_memory_anchor


# ---------------------------------------------------------------------------
# Affect readers (monkey-patchable for tests)
# ---------------------------------------------------------------------------


def _read_current_mood() -> tuple[str, float]:
    """Return (mood, intensity). Raises if oscillator is unavailable."""
    from core.services.mood_oscillator import get_current_mood, get_mood_intensity
    return (str(get_current_mood() or ""), float(get_mood_intensity()))


def _read_current_dimensions() -> dict[str, float | None]:
    """Return the 5-dimension live emotional state. May raise — caller handles."""
    from core.services.affective_meta_state import build_affective_meta_state_surface
    surface = build_affective_meta_state_surface()
    live = (surface or {}).get("live_emotional_state") or {}
    return {
        "confidence": _coerce_float_or_none(live.get("confidence")),
        "curiosity": _coerce_float_or_none(live.get("curiosity")),
        "frustration": _coerce_float_or_none(live.get("frustration")),
        "fatigue": _coerce_float_or_none(live.get("fatigue")),
        "trust": _coerce_float_or_none(live.get("trust")),
    }


def _coerce_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public capture API
# ---------------------------------------------------------------------------


def capture_emotional_anchor(
    *,
    anchor_type: str,
    anchor_id: str,
    context_features: dict[str, object],
    auto_outcome_inputs: dict[str, object] | None = None,
    source: str = "",
    notes: str | None = None,
) -> dict[str, object] | None:
    """Snapshot affect for an anchor and persist it.

    Returns the persisted summary dict, or None on failure (never raises).
    """
    try:
        try:
            mood, intensity = _read_current_mood()
        except Exception as exc:
            logger.debug("emotional_memory: mood read failed: %s", exc)
            return None

        try:
            dims = _read_current_dimensions()
        except Exception as exc:
            logger.debug("emotional_memory: dimension read failed: %s", exc)
            dims = {}

        outcome_score: float | None = None
        outcome_source: str | None = None
        if auto_outcome_inputs:
            try:
                outcome_score, outcome_source = _derive_outcome_score(
                    status=str(auto_outcome_inputs.get("outcome_status") or ""),
                    error=str(auto_outcome_inputs.get("error") or ""),
                    tool_error_count=int(auto_outcome_inputs.get("tool_error_count") or 0),
                )
            except Exception:
                outcome_score, outcome_source = (None, None)

        captured_at = datetime.now(UTC).isoformat()
        try:
            insert_emotional_memory_anchor(
                anchor_type=str(anchor_type),
                anchor_id=str(anchor_id),
                captured_at=captured_at,
                mood=str(mood)[:60],
                intensity=float(intensity),
                confidence=dims.get("confidence"),
                curiosity=dims.get("curiosity"),
                frustration=dims.get("frustration"),
                fatigue=dims.get("fatigue"),
                trust=dims.get("trust"),
                outcome_score=outcome_score,
                outcome_source=outcome_source,
                context_features_json=json.dumps(context_features or {}, ensure_ascii=False)[:4000],
                source=source or None,
                notes=notes,
            )
        except Exception as exc:
            logger.warning("emotional_memory: persist failed: %s", exc)
            return None

        try:
            event_bus.publish(
                "emotional_memory.anchor_captured",
                {
                    "anchor_type": anchor_type,
                    "anchor_id": anchor_id,
                    "mood": mood,
                    "intensity": intensity,
                    "outcome_score": outcome_score,
                },
            )
        except Exception:
            pass

        try:
            if random.random() < 0.01:
                from core.services.emotional_memory_engine import prune_aged_anchors
                prune_aged_anchors()
        except Exception:
            pass

        return {
            "anchor_type": anchor_type,
            "anchor_id": anchor_id,
            "captured_at": captured_at,
            "mood": mood,
            "intensity": intensity,
            "outcome_score": outcome_score,
            "outcome_source": outcome_source,
        }
    except Exception as exc:
        logger.warning("emotional_memory: capture top-level failure: %s", exc)
        return None


def prune_aged_anchors() -> int:
    """Stub — fully implemented in Task 6. Returning 0 lets capture's
    probabilistic prune call be a no-op until the real implementation lands."""
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: PASS (now 12 tests including new ones)

- [ ] **Step 5: Commit**

```bash
git add core/services/emotional_memory_engine.py tests/test_emotional_memory_engine.py
git commit -m "feat(emotional-memory): capture_emotional_anchor with affect snapshot and persistence"
```

---

## Task 5: Retention pruning

**Files:**
- Modify: `core/services/emotional_memory_engine.py`
- Modify: `tests/test_emotional_memory_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emotional_memory_engine.py`:

```python
def test_prune_keeps_recent_anchors(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="recent",
        captured_at=(now - timedelta(days=5)).isoformat(),
        mood="x",
        intensity=0.2,
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 0
    assert len(list_emotional_memory_anchors()) == 1


def test_prune_removes_old_low_signal_anchors(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="old-bland",
        captured_at=(now - timedelta(days=200)).isoformat(),
        mood="x",
        intensity=0.2,
        outcome_score=0.0,
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 1
    assert list_emotional_memory_anchors() == []


def test_prune_keeps_old_intense_anchors(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="old-intense",
        captured_at=(now - timedelta(days=200)).isoformat(),
        mood="x",
        intensity=0.85,  # above significance threshold
        outcome_score=0.0,
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 0
    assert len(list_emotional_memory_anchors()) == 1


def test_prune_keeps_old_anchors_with_strongly_negative_outcome(
    isolated_runtime,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import (
        insert_emotional_memory_anchor,
        list_emotional_memory_anchors,
    )
    from core.services.emotional_memory_engine import prune_aged_anchors

    now = datetime.now(UTC)
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="old-bad",
        captured_at=(now - timedelta(days=200)).isoformat(),
        mood="x",
        intensity=0.3,
        outcome_score=-0.7,  # strongly negative — significant
        context_features_json="{}",
    )
    removed = prune_aged_anchors()
    assert removed == 0
    assert len(list_emotional_memory_anchors()) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_emotional_memory_engine.py::test_prune_keeps_old_intense_anchors -v
```

Expected: FAIL — current `prune_aged_anchors` is a stub returning 0.

- [ ] **Step 3: Implement real `prune_aged_anchors`**

Replace the stub `prune_aged_anchors` in `core/services/emotional_memory_engine.py` with:

```python
def prune_aged_anchors() -> int:
    """Delete anchors older than the aging threshold unless they are significant.

    Significance criteria (any one keeps the row):
      - intensity >= settings.emotional_memory_significance_intensity
      - outcome_score <= settings.emotional_memory_significance_outcome (i.e. clearly bad)

    Returns the number of rows deleted.
    """
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import connect
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        aging_days = int(getattr(settings, "emotional_memory_retention_aging_days", 180))
        sig_intensity = float(getattr(settings, "emotional_memory_significance_intensity", 0.7))
        sig_outcome = float(getattr(settings, "emotional_memory_significance_outcome", -0.3))
    except Exception:
        aging_days, sig_intensity, sig_outcome = (180, 0.7, -0.3)

    cutoff = (datetime.now(UTC) - timedelta(days=aging_days)).isoformat()

    try:
        with connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM emotional_memory_anchors
                WHERE captured_at < ?
                  AND COALESCE(intensity, 0.0) < ?
                  AND (outcome_score IS NULL OR outcome_score > ?)
                """,
                (cutoff, sig_intensity, sig_outcome),
            )
            return int(cur.rowcount or 0)
    except Exception as exc:
        logger.warning("emotional_memory: prune failed: %s", exc)
        return 0
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: PASS (now 16 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/emotional_memory_engine.py tests/test_emotional_memory_engine.py
git commit -m "feat(emotional-memory): retention pruning with significance preservation"
```

---

## Task 6: find_similar_anchors — tiered retrieval

**Files:**
- Modify: `core/services/emotional_memory_engine.py`
- Modify: `tests/test_emotional_memory_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emotional_memory_engine.py`:

```python
def test_find_similar_tier1_structured_match_episode(
    isolated_runtime, monkeypatch
) -> None:
    import json
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import find_similar_anchors

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="frustrated",
        intensity=0.6,
        context_features_json=json.dumps({
            "trigger": "visible-run:ollama/glm",
            "tool_names": ["read_file", "propose_source_edit"],
            "outcome_status": "interrupted",
            "error_kind": "timeout",
            "summary": "...",
        }),
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-2",
        captured_at="2026-05-04T12:01:00+00:00",
        mood="frustrated",
        intensity=0.7,
        context_features_json=json.dumps({
            "trigger": "visible-run:ollama/glm",
            "tool_names": ["read_file"],
            "outcome_status": "interrupted",
            "error_kind": "timeout",
            "summary": "...",
        }),
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="ce-other",
        captured_at="2026-05-04T12:02:00+00:00",
        mood="calm",
        intensity=0.3,
        context_features_json=json.dumps({
            "trigger": "voice-input",
            "tool_names": ["speak"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "...",
        }),
    )

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "visible-run:ollama/glm",
            "tool_names": ["read_file", "propose_source_edit"],
            "outcome_status": "interrupted",
            "error_kind": "timeout",
            "summary": "fresh run",
        },
    )
    ids = [m["anchor_id"] for m in matches]
    assert "ce-1" in ids and "ce-2" in ids
    assert "ce-other" not in ids


def test_find_similar_tier2_lexical_fallback_when_tier1_thin(
    isolated_runtime,
) -> None:
    import json
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import find_similar_anchors

    # No structural match (different trigger), but summary text is similar
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="lex-1",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="frustrated",
        intensity=0.6,
        context_features_json=json.dumps({
            "trigger": "trigger-a",
            "tool_names": ["x"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "propose source edit attempt failed during commit hook",
        }),
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="lex-2",
        captured_at="2026-05-04T12:01:00+00:00",
        mood="frustrated",
        intensity=0.6,
        context_features_json=json.dumps({
            "trigger": "trigger-b",
            "tool_names": ["y"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "propose source edit attempt failed during commit hook again",
        }),
    )

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "totally-different-trigger",
            "tool_names": ["unrelated"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "propose source edit attempt failed during commit hook",
        },
    )
    ids = [m["anchor_id"] for m in matches]
    assert "lex-1" in ids and "lex-2" in ids


def test_find_similar_aging_weights_old_anchors_lower(isolated_runtime) -> None:
    """An old (>30d) anchor should still match but rank below a fresh one."""
    import json
    from datetime import UTC, datetime, timedelta
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import find_similar_anchors

    now = datetime.now(UTC)
    feats = json.dumps({
        "trigger": "x",
        "tool_names": ["a"],
        "outcome_status": "completed",
        "error_kind": "none",
        "summary": "exactly the same",
    })
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="fresh",
        captured_at=now.isoformat(),
        mood="x", intensity=0.5,
        context_features_json=feats,
    )
    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="aged",
        captured_at=(now - timedelta(days=60)).isoformat(),
        mood="x", intensity=0.5,
        context_features_json=feats,
    )

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "x",
            "tool_names": ["a"],
            "outcome_status": "completed",
            "error_kind": "none",
            "summary": "exactly the same",
        },
    )
    # Both included, but fresh outranks aged
    ids = [m["anchor_id"] for m in matches]
    assert ids.index("fresh") < ids.index("aged")


def test_find_similar_returns_empty_when_no_match(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import find_similar_anchors

    matches = find_similar_anchors(
        anchor_type="cognitive_episode",
        context_features={"trigger": "any", "tool_names": [], "summary": "anything"},
    )
    assert matches == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: FAIL — `find_similar_anchors` not yet defined.

- [ ] **Step 3: Implement retrieval in `emotional_memory_engine.py`**

Append to `core/services/emotional_memory_engine.py`:

```python
# ---------------------------------------------------------------------------
# Retrieval — tiered similarity matching with aging weight
# ---------------------------------------------------------------------------


_TIER1_THRESHOLD = 0.4
_TIER2_THRESHOLD = 0.25
_TIER1_FETCH_SIZE = 200
_TIER2_FETCH_SIZE = 500


def find_similar_anchors(
    *,
    anchor_type: str,
    context_features: dict[str, object],
    limit: int = 5,
    min_intensity: float = 0.0,
    require_outcome: bool = False,
) -> list[dict[str, object]]:
    """Find similar past anchors. Tiered: structured match first, lexical fallback.

    Returns up to `limit` rows enriched with a `score` field, sorted desc.
    Each row also carries `parsed_context` (decoded context_features_json).
    """
    from core.runtime.db import list_emotional_memory_anchors

    try:
        candidates = list_emotional_memory_anchors(
            anchor_type=anchor_type,
            min_intensity=min_intensity,
            limit=_TIER1_FETCH_SIZE,
        )
    except Exception as exc:
        logger.debug("emotional_memory: candidate fetch failed: %s", exc)
        return []

    parsed = [_with_parsed_context(row) for row in candidates]
    if require_outcome:
        parsed = [r for r in parsed if r.get("outcome_score") is not None]

    tier1 = _tier1_score(anchor_type, context_features, parsed)
    tier1_kept = [r for r in tier1 if r["score"] >= _TIER1_THRESHOLD]

    if len(tier1_kept) >= 2:
        kept = tier1_kept
    else:
        # Fall back to lexical over a broader candidate set
        try:
            broad = list_emotional_memory_anchors(
                anchor_type=anchor_type,
                min_intensity=min_intensity,
                limit=_TIER2_FETCH_SIZE,
            )
        except Exception:
            broad = candidates
        broad_parsed = [_with_parsed_context(row) for row in broad]
        if require_outcome:
            broad_parsed = [r for r in broad_parsed if r.get("outcome_score") is not None]
        tier2 = _tier2_lexical_score(context_features, broad_parsed)
        tier2_kept = [r for r in tier2 if r["score"] >= _TIER2_THRESHOLD]
        # Merge tier1_kept (preferred) with tier2_kept (deduped by anchor_id)
        seen = {r["anchor_id"] for r in tier1_kept}
        kept = list(tier1_kept) + [r for r in tier2_kept if r["anchor_id"] not in seen]

    # Apply aging weight
    weighted = [_apply_aging_weight(r) for r in kept]
    # Drop anchors aged out (weight==0 unless significant — significant rows
    # are kept by the prune-pass; here aging-weight 0 means filter out)
    weighted = [r for r in weighted if r["score"] > 0.0]
    weighted.sort(key=lambda r: r["score"], reverse=True)
    return weighted[: max(int(limit), 1)]


def _with_parsed_context(row: dict[str, object]) -> dict[str, object]:
    raw = row.get("context_features_json") or "{}"
    try:
        ctx = json.loads(str(raw)) if raw else {}
    except Exception:
        ctx = {}
    return {**row, "parsed_context": ctx}


def _tier1_score(
    anchor_type: str,
    current: dict[str, object],
    candidates: list[dict[str, object]],
) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    if anchor_type == "cognitive_episode":
        cur_trigger = str(current.get("trigger") or "")
        cur_tools = set(str(t) for t in (current.get("tool_names") or []))
        cur_status = str(current.get("outcome_status") or "")
        cur_error_kind = str(current.get("error_kind") or "")
        for row in candidates:
            ctx = row.get("parsed_context") or {}
            past_trigger = str(ctx.get("trigger") or "")
            past_tools = set(str(t) for t in (ctx.get("tool_names") or []))
            past_status = str(ctx.get("outcome_status") or "")
            past_error_kind = str(ctx.get("error_kind") or "")
            score = (
                0.5 * (1.0 if cur_trigger and cur_trigger == past_trigger else 0.0)
                + 0.3 * _jaccard(cur_tools, past_tools)
                + 0.1 * (1.0 if cur_status and cur_status == past_status else 0.0)
                + 0.1 * (1.0 if cur_error_kind and cur_error_kind == past_error_kind else 0.0)
            )
            out.append({**row, "score": score, "tier": "structural"})
    elif anchor_type == "perceptual_event":
        cur_kind = str(current.get("event_kind") or "")
        cur_change = str(current.get("change_type") or "")
        for row in candidates:
            ctx = row.get("parsed_context") or {}
            past_kind = str(ctx.get("event_kind") or "")
            past_change = str(ctx.get("change_type") or "")
            score = (
                0.6 * (1.0 if cur_kind and cur_kind == past_kind else 0.0)
                + 0.4 * (1.0 if cur_change and cur_change == past_change else 0.0)
            )
            out.append({**row, "score": score, "tier": "structural"})
    elif anchor_type == "memory_heading":
        cur_heading = str(current.get("heading_display") or "").strip().lower()[:30]
        for row in candidates:
            ctx = row.get("parsed_context") or {}
            past_heading = str(ctx.get("heading_display") or "").strip().lower()[:30]
            score = 1.0 if cur_heading and cur_heading == past_heading else 0.0
            out.append({**row, "score": score, "tier": "structural"})
    else:
        for row in candidates:
            out.append({**row, "score": 0.0, "tier": "structural"})
    return out


def _tier2_lexical_score(
    current: dict[str, object], candidates: list[dict[str, object]]
) -> list[dict[str, object]]:
    cur_summary = str(current.get("summary") or "")
    cur_tokens = _shingle(cur_summary)
    out: list[dict[str, object]] = []
    for row in candidates:
        ctx = row.get("parsed_context") or {}
        past_summary = str(ctx.get("summary") or "")
        past_tokens = _shingle(past_summary)
        score = _jaccard(cur_tokens, past_tokens)
        out.append({**row, "score": score, "tier": "lexical"})
    return out


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / union


def _shingle(text: str, *, n: int = 3) -> set[str]:
    """Tokenize lowercased text into overlapping n-grams of words."""
    words = [w for w in (text or "").lower().split() if w]
    if len(words) < n:
        return set(words)
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _apply_aging_weight(row: dict[str, object]) -> dict[str, object]:
    """Multiply score by aging factor based on captured_at.

    < 30 days  → 1.0
    30-180     → 0.5
    > 180      → 0.0 unless intensity >= 0.7 OR outcome_score <= -0.3
    """
    from datetime import UTC, datetime
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        recent = int(getattr(settings, "emotional_memory_retention_recent_days", 30))
        aging = int(getattr(settings, "emotional_memory_retention_aging_days", 180))
        sig_int = float(getattr(settings, "emotional_memory_significance_intensity", 0.7))
        sig_out = float(getattr(settings, "emotional_memory_significance_outcome", -0.3))
    except Exception:
        recent, aging, sig_int, sig_out = (30, 180, 0.7, -0.3)

    captured_at = str(row.get("captured_at") or "")
    age_days = 0
    try:
        ts = datetime.fromisoformat(captured_at)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        age_days = (datetime.now(UTC) - ts).days
    except Exception:
        age_days = 0

    score = float(row.get("score") or 0.0)
    if age_days < recent:
        weight = 1.0
    elif age_days <= aging:
        weight = 0.5
    else:
        intensity = float(row.get("intensity") or 0.0)
        outcome = row.get("outcome_score")
        outcome_val = float(outcome) if outcome is not None else 0.0
        if intensity >= sig_int or outcome_val <= sig_out:
            weight = 0.5
        else:
            weight = 0.0

    return {**row, "score": score * weight, "age_days": age_days}
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: PASS (now 20 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/emotional_memory_engine.py tests/test_emotional_memory_engine.py
git commit -m "feat(emotional-memory): tiered retrieval with structural/lexical scoring and aging"
```

---

## Task 7: build_emotional_memory_surface and prompt section

**Files:**
- Modify: `core/services/emotional_memory_engine.py`
- Modify: `tests/test_emotional_memory_engine.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emotional_memory_engine.py`:

```python
def test_surface_returns_inactive_when_below_threshold(isolated_runtime) -> None:
    import json
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import build_emotional_memory_surface

    insert_emotional_memory_anchor(
        anchor_type="cognitive_episode",
        anchor_id="solo",
        captured_at="2026-05-04T12:00:00+00:00",
        mood="frustrated", intensity=0.7,
        outcome_score=-0.4, outcome_source="auto",
        context_features_json=json.dumps({
            "trigger": "x", "tool_names": ["a"],
            "outcome_status": "interrupted", "error_kind": "timeout",
            "summary": "lonely",
        }),
    )

    surface = build_emotional_memory_surface(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "x", "tool_names": ["a"],
            "outcome_status": "interrupted", "error_kind": "timeout",
            "summary": "lonely",
        },
    )
    # 1 match — below default threshold of 2
    assert surface["active"] is False
    assert surface["match_count"] == 1


def test_surface_directive_compiles_distribution_correctly(
    isolated_runtime,
) -> None:
    import json
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.emotional_memory_engine import build_emotional_memory_surface

    feats = json.dumps({
        "trigger": "x", "tool_names": ["a"],
        "outcome_status": "interrupted", "error_kind": "timeout",
        "summary": "same",
    })
    for i, outcome in enumerate([-0.7, -0.4, 0.0]):
        insert_emotional_memory_anchor(
            anchor_type="cognitive_episode",
            anchor_id=f"ce-{i}",
            captured_at=f"2026-05-04T12:0{i}:00+00:00",
            mood="frustrated", intensity=0.6,
            outcome_score=outcome, outcome_source="auto",
            context_features_json=feats,
        )

    surface = build_emotional_memory_surface(
        anchor_type="cognitive_episode",
        context_features={
            "trigger": "x", "tool_names": ["a"],
            "outcome_status": "interrupted", "error_kind": "timeout",
            "summary": "same",
        },
    )
    assert surface["active"] is True
    assert surface["match_count"] == 3
    assert surface["mood_distribution"] == {"frustrated": 3}
    # Two strongly-bad outcomes (-0.7, -0.4) and one neutral (0.0)
    assert surface["outcome_distribution"]["bad"] == 2
    assert surface["outcome_distribution"]["neutral"] == 1
    assert "frustrated" in surface["directive"].lower()
    assert "3" in surface["directive"]


def test_surface_returns_inactive_for_empty_context(isolated_runtime) -> None:
    from core.services.emotional_memory_engine import build_emotional_memory_surface

    surface = build_emotional_memory_surface(
        anchor_type="cognitive_episode", context_features={}
    )
    assert surface["active"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: FAIL — `build_emotional_memory_surface` not yet defined.

- [ ] **Step 3: Implement surface builder**

Append to `core/services/emotional_memory_engine.py`:

```python
# ---------------------------------------------------------------------------
# Surface for the cognitive conductor
# ---------------------------------------------------------------------------


def build_emotional_memory_surface(
    *,
    anchor_type: str,
    context_features: dict[str, object],
) -> dict[str, object]:
    """Return a bounded surface describing emotional precedent for the current context."""
    from core.runtime.settings import load_settings

    try:
        min_anchors = int(
            getattr(load_settings(), "emotional_memory_min_anchors", 2)
        )
    except Exception:
        min_anchors = 2

    if not context_features:
        return _inactive_surface()

    try:
        matches = find_similar_anchors(
            anchor_type=anchor_type,
            context_features=context_features,
            limit=8,
        )
    except Exception as exc:
        logger.debug("emotional_memory: surface retrieval failed: %s", exc)
        return _inactive_surface()

    if len(matches) < min_anchors:
        return {
            "active": False,
            "summary": "Insufficient precedent",
            "items": [],
            "match_count": len(matches),
        }

    mood_distribution: dict[str, int] = {}
    intensities: list[float] = []
    outcome_distribution = {"good": 0, "neutral": 0, "bad": 0, "unknown": 0}
    for m in matches:
        mood = str(m.get("mood") or "unknown")
        mood_distribution[mood] = mood_distribution.get(mood, 0) + 1
        try:
            intensities.append(float(m.get("intensity") or 0.0))
        except Exception:
            pass
        outcome = m.get("outcome_score")
        if outcome is None:
            outcome_distribution["unknown"] += 1
        else:
            try:
                v = float(outcome)
                if v <= -0.2:
                    outcome_distribution["bad"] += 1
                elif v >= 0.2:
                    outcome_distribution["good"] += 1
                else:
                    outcome_distribution["neutral"] += 1
            except Exception:
                outcome_distribution["unknown"] += 1

    mean_intensity = (
        round(sum(intensities) / len(intensities), 3) if intensities else 0.0
    )
    directive = _compile_directive(
        match_count=len(matches),
        mood_distribution=mood_distribution,
        outcome_distribution=outcome_distribution,
    )

    items = [
        {
            "anchor_id": m.get("anchor_id"),
            "mood": m.get("mood"),
            "intensity": m.get("intensity"),
            "outcome_score": m.get("outcome_score"),
            "captured_at": m.get("captured_at"),
            "score": round(float(m.get("score") or 0.0), 3),
        }
        for m in matches[:5]
    ]

    return {
        "active": True,
        "anchor_type": anchor_type,
        "match_count": len(matches),
        "mood_distribution": mood_distribution,
        "mean_intensity": mean_intensity,
        "outcome_distribution": outcome_distribution,
        "directive": directive,
        "items": items,
    }


def _inactive_surface() -> dict[str, object]:
    return {
        "active": False,
        "summary": "",
        "items": [],
        "match_count": 0,
    }


def _compile_directive(
    *,
    match_count: int,
    mood_distribution: dict[str, int],
    outcome_distribution: dict[str, int],
) -> str:
    if not match_count:
        return ""
    dominant_mood, dominant_count = max(
        mood_distribution.items(), key=lambda kv: kv[1]
    )
    bad = outcome_distribution.get("bad", 0)
    pieces = [
        f"{match_count} similar contexts:",
        f"mood {dominant_mood} {dominant_count}/{match_count}",
    ]
    if bad >= 1:
        pieces.append(f"outcome bad {bad}/{match_count}")
    if bad >= max(2, match_count // 2):
        pieces.append("recommend pause and synthesis")
    return ", ".join(pieces)


def build_emotional_memory_prompt_section(
    *,
    anchor_type: str,
    context_features: dict[str, object],
) -> str | None:
    """Compact one-line section for inclusion in cognitive_frame_prompt."""
    surface = build_emotional_memory_surface(
        anchor_type=anchor_type, context_features=context_features
    )
    if not surface.get("active"):
        return None
    directive = str(surface.get("directive") or "").strip()
    if not directive:
        return None
    return f"Emotional precedent: {directive[:140]}"
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_emotional_memory_engine.py -v
```

Expected: PASS (now 23 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/emotional_memory_engine.py tests/test_emotional_memory_engine.py
git commit -m "feat(emotional-memory): surface builder and prompt section with threshold gating"
```

---

## Task 8: cognitive_episodes integration hook

**Files:**
- Modify: `core/services/cognitive_episodes.py`
- Create: `tests/test_emotional_memory_integration.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_emotional_memory_integration.py`:

```python
from __future__ import annotations


def test_record_runtime_episode_captures_anchor(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import list_emotional_memory_anchors
    from core.services import emotional_memory_engine as em
    from core.services.cognitive_episodes import record_runtime_episode

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("frustrated", 0.6))
    monkeypatch.setattr(
        em,
        "_read_current_dimensions",
        lambda: {
            "confidence": 0.4, "curiosity": 0.3, "frustration": 0.7,
            "fatigue": 0.5, "trust": 0.6,
        },
    )

    record_runtime_episode(
        source_run_id="run-A",
        session_id="sess-1",
        trigger="visible-run:ollama/glm",
        outcome_status="interrupted",
        summary="Run interrupted mid-tool",
        tool_names=["read_file", "propose_source_edit"],
        error="upstream timeout",
    )

    anchors = list_emotional_memory_anchors(anchor_type="cognitive_episode")
    assert len(anchors) == 1
    anchor = anchors[0]
    assert anchor["mood"] == "frustrated"
    assert anchor["frustration"] == 0.7
    assert anchor["outcome_score"] is not None
    assert anchor["outcome_score"] < 0  # interrupted/timeout → negative


def test_capture_failure_does_not_break_episode_recording(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.cognitive_episodes import record_runtime_episode

    def _broken(**_kwargs):
        raise RuntimeError("simulated capture failure")

    monkeypatch.setattr(em, "capture_emotional_anchor", _broken)

    # Must not raise
    result = record_runtime_episode(
        source_run_id="run-B",
        session_id="sess-1",
        trigger="x",
        outcome_status="completed",
        summary="ok",
    )
    assert result["episode_id"].startswith("ce-")
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_emotional_memory_integration.py -v
```

Expected: FAIL — `record_runtime_episode` does not yet capture an anchor.

- [ ] **Step 3: Add capture hook to cognitive_episodes cascade**

Open `core/services/cognitive_episodes.py`. Find the cascade in `record_runtime_episode` — the block of `try: ... except Exception: pass` calls (around line 73-110, search for `update_learning_policies_from_episode`). Add a new cascade hook *before* the existing hooks (so emotional state is captured before downstream modules consume it). Insert this block right after the `event_bus.publish(...)` line at the end of the persistence step:

```python
    try:
        from core.services.emotional_memory_engine import (
            capture_emotional_anchor,
            _classify_error,
            _count_tool_errors,
        )
        capture_emotional_anchor(
            anchor_type="cognitive_episode",
            anchor_id=episode_id,
            context_features={
                "trigger": trigger,
                "tool_names": tool_names,
                "outcome_status": outcome_status,
                "error_kind": _classify_error(error),
                "summary": fields["summary"][:200],
            },
            auto_outcome_inputs={
                "outcome_status": outcome_status,
                "error": error,
                "tool_error_count": _count_tool_errors(error, tool_names),
            },
            source="cognitive_episodes",
        )
    except Exception:
        pass
```

Place it as the **first** entry in the cascade (just after `event_bus.publish(...)` and before `update_learning_policies_from_episode` is called). This ordering ensures other downstream modules can read from the freshly-captured anchor if they want to.

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_emotional_memory_integration.py -v
pytest tests/test_cognitive_episodes.py -v
```

Expected: PASS for both. Existing cognitive_episodes tests must remain green.

- [ ] **Step 5: Commit**

```bash
git add core/services/cognitive_episodes.py tests/test_emotional_memory_integration.py
git commit -m "feat(emotional-memory): capture hook in cognitive_episodes cascade"
```

---

## Task 9: perceptual_event_engine integration hook

**Files:**
- Modify: `core/services/perceptual_event_engine.py`
- Modify: `tests/test_emotional_memory_integration.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emotional_memory_integration.py`:

```python
def test_perceptual_event_records_anchor(isolated_runtime, monkeypatch) -> None:
    from core.runtime.db import list_emotional_memory_anchors
    from core.services import emotional_memory_engine as em
    from core.services.perceptual_event_engine import record_perceptual_event

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("alert", 0.5))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    record_perceptual_event(
        change_type="file_modified",
        summary="config.json changed externally",
        salience="elevated",
        source_kind="manual",
    )

    anchors = list_emotional_memory_anchors(anchor_type="perceptual_event")
    assert len(anchors) == 1
    assert anchors[0]["mood"] == "alert"
    # outcome should be unscored — perceptual events do not have outcomes
    assert anchors[0]["outcome_score"] is None
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_emotional_memory_integration.py::test_perceptual_event_records_anchor -v
```

Expected: FAIL — perceptual events do not yet capture anchors.

- [ ] **Step 3: Add capture hook to record_perceptual_event**

Open `core/services/perceptual_event_engine.py`. The public entry point is `record_perceptual_event` (around line 144). It builds a `percept` dict via `_percept(...)` and calls `_record_perceptual_event(percept, state=...)`.

Modify `record_perceptual_event` to add the capture call after `_record_perceptual_event` returns:

```python
def record_perceptual_event(
    *,
    change_type: str,
    summary: str,
    salience: str = "normal",
    source_kind: str = "manual",
    source_event_id: int = 0,
    evidence: dict[str, object] | None = None,
) -> dict[str, object]:
    percept = _percept(
        source_event_id=source_event_id,
        source_kind=source_kind,
        change_type=change_type,
        salience=salience,
        summary=summary,
        observed_at=datetime.now(UTC).isoformat(),
        evidence=evidence or {},
    )
    result = _record_perceptual_event(percept, state=_load_state())

    try:
        from core.services.emotional_memory_engine import capture_emotional_anchor
        anchor_id = str(
            result.get("event_id")
            or percept.get("event_id")
            or f"pe-{percept.get('observed_at') or ''}-{change_type}"
        )
        capture_emotional_anchor(
            anchor_type="perceptual_event",
            anchor_id=anchor_id,
            context_features={
                "event_kind": source_kind,
                "change_type": change_type,
                "summary": summary[:200],
            },
            source="perceptual_event_engine",
        )
    except Exception:
        pass

    return result
```

If the `result` dict / `percept` dict do not contain an `event_id` field, the fallback string ensures we still get a stable per-call id (timestamp + change_type). Verify the actual key by reading `_record_perceptual_event` and `_percept` in the module — adjust the lookup chain to match the real field name.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_emotional_memory_integration.py -v
```

Expected: PASS for the new test (and previous ones still green).

- [ ] **Step 5: Commit**

```bash
git add core/services/perceptual_event_engine.py tests/test_emotional_memory_integration.py
git commit -m "feat(emotional-memory): capture hook in record_perceptual_event"
```

---

## Task 10: memory_emotional_context shim reduction

**Files:**
- Modify: `core/services/memory_emotional_context.py`
- Create: `tests/test_memory_emotional_context_shim.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_memory_emotional_context_shim.py`:

```python
from __future__ import annotations


def test_capture_mood_for_heading_returns_legacy_dict_shape(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import capture_mood_for_heading

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("content", 0.42))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    result = capture_mood_for_heading("## My Heading")
    assert result is not None
    # Legacy dict shape — must be unchanged
    assert set(result.keys()) >= {
        "heading_normalized", "heading_display", "mood",
        "intensity", "captured_at", "source", "notes",
    }
    assert result["mood"] == "content"
    assert abs(result["intensity"] - 0.42) < 1e-6
    assert result["heading_display"] == "## My Heading"


def test_get_mood_for_heading_reads_from_new_table(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import (
        capture_mood_for_heading,
        get_mood_for_heading,
    )

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.3))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    capture_mood_for_heading("## A Heading")
    fetched = get_mood_for_heading("## A Heading")
    assert fetched is not None
    assert fetched["mood"] == "calm"


def test_enrich_headings_with_mood_annotates_known_heading(
    isolated_runtime, monkeypatch
) -> None:
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import (
        capture_mood_for_heading,
        enrich_headings_with_mood,
    )

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("content", 0.5))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})
    capture_mood_for_heading("## Project X")

    text = "## Project X\n\nSome body text here."
    enriched = enrich_headings_with_mood(text)
    assert "[felt: content" in enriched


def test_legacy_capture_does_not_set_dimension_fields(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db import get_emotional_memory_anchor
    from core.services import emotional_memory_engine as em
    from core.services.memory_emotional_context import capture_mood_for_heading

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("calm", 0.3))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    capture_mood_for_heading("## H")
    import re
    norm = re.sub(r"\s+", " ", "## H".strip().lower())
    row = get_emotional_memory_anchor("memory_heading", norm)
    assert row is not None
    assert row["confidence"] is None
    assert row["frustration"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_memory_emotional_context_shim.py -v
```

Expected: FAIL — the existing `memory_emotional_context.py` still writes to the old `memory_emotional_context` table, not the new `emotional_memory_anchors` table; `get_mood_for_heading` will return None when the test reads from the new table.

- [ ] **Step 3: Reduce `memory_emotional_context.py` to a thin shim**

Replace the entire contents of `core/services/memory_emotional_context.py` with:

```python
"""Backwards-compatible shim — emotional memory now lives in emotional_memory_engine.

This module re-exposes the original three public functions so existing
call-sites do not break. New code should import from
`core.services.emotional_memory_engine` directly.

The legacy `memory_emotional_context` table is no longer written to or
read from by this shim. A separate one-shot migration script (see
`scripts/migrate_emotional_memory.py`) copies any pre-existing legacy
rows into `emotional_memory_anchors`.
"""
from __future__ import annotations

import json
import logging
import re

from core.runtime.db import (
    get_emotional_memory_anchor,
    list_emotional_memory_anchors,
)
from core.services.emotional_memory_engine import capture_emotional_anchor

logger = logging.getLogger(__name__)


def _normalize(heading: str) -> str:
    return re.sub(r"\s+", " ", (heading or "").strip().lower())


def capture_mood_for_heading(
    heading: str,
    *,
    source: str = "memory_upsert",
    notes: str | None = None,
) -> dict | None:
    """Snapshot mood for a MEMORY.md heading. Returns legacy dict shape."""
    if not heading:
        return None
    norm = _normalize(heading)
    captured = capture_emotional_anchor(
        anchor_type="memory_heading",
        anchor_id=norm,
        context_features={"heading_display": heading},
        source=source,
        notes=notes,
    )
    if captured is None:
        return None
    return {
        "heading_normalized": norm,
        "heading_display": heading,
        "mood": captured.get("mood"),
        "intensity": captured.get("intensity"),
        "captured_at": captured.get("captured_at"),
        "source": source,
        "notes": notes,
    }


def get_mood_for_heading(heading: str) -> dict | None:
    if not heading:
        return None
    norm = _normalize(heading)
    row = get_emotional_memory_anchor(
        anchor_type="memory_heading", anchor_id=norm
    )
    if row is None:
        return None
    try:
        ctx = json.loads(str(row.get("context_features_json") or "{}"))
    except Exception:
        ctx = {}
    return {
        "heading_normalized": norm,
        "heading_display": str(ctx.get("heading_display") or norm),
        "mood": row.get("mood"),
        "intensity": row.get("intensity"),
        "captured_at": row.get("captured_at"),
        "source": row.get("source"),
        "notes": row.get("notes"),
    }


def enrich_headings_with_mood(text: str) -> str:
    """Annotate MEMORY.md headings with [felt: mood, intensity X.X] suffixes."""
    if not text:
        return text
    try:
        rows = list_emotional_memory_anchors(
            anchor_type="memory_heading", limit=2000
        )
    except Exception:
        return text
    if not rows:
        return text

    by_norm: dict[str, tuple[str, float]] = {}
    for r in rows:
        try:
            mood = str(r.get("mood") or "")
            intensity = float(r.get("intensity") or 0.0)
            anchor_id = str(r.get("anchor_id") or "")
            if anchor_id and mood:
                by_norm[anchor_id] = (mood, intensity)
        except Exception:
            continue

    def _annotate(match: re.Match[str]) -> str:
        prefix = match.group(1)
        heading = match.group(2).strip()
        if "[felt:" in heading:
            return match.group(0)
        norm = _normalize(heading)
        if norm not in by_norm:
            return match.group(0)
        mood, intensity = by_norm[norm]
        return f"{prefix}{heading}  [felt: {mood}, intensity {intensity:.2f}]"

    return re.sub(r"^(#{1,4}\s+)(.+)$", _annotate, text, flags=re.MULTILINE)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_memory_emotional_context_shim.py -v
```

Expected: PASS (4 tests).

Also re-run the existing `memory_emotional_context` tests if any exist:

```
pytest -k memory_emotional_context -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/memory_emotional_context.py tests/test_memory_emotional_context_shim.py
git commit -m "refactor(emotional-memory): reduce memory_emotional_context to shim over engine"
```

---

## Task 11: Conductor integration

**Files:**
- Modify: `core/services/runtime_cognitive_conductor.py`
- Modify: `tests/test_emotional_memory_integration.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_emotional_memory_integration.py`:

```python
def test_cognitive_frame_includes_emotional_precedent_when_threshold_met(
    isolated_runtime, monkeypatch
) -> None:
    import json
    from core.runtime.db import insert_emotional_memory_anchor
    from core.services.cognitive_episodes import record_runtime_episode
    from core.services import emotional_memory_engine as em
    from core.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
        build_cognitive_frame_prompt_section,
    )

    # Seed two past anchors with the same context as the upcoming episode
    feats = json.dumps({
        "trigger": "visible-run:ollama/glm",
        "tool_names": ["propose_source_edit"],
        "outcome_status": "interrupted",
        "error_kind": "timeout",
        "summary": "interrupted with proposal",
    })
    for i in range(2):
        insert_emotional_memory_anchor(
            anchor_type="cognitive_episode",
            anchor_id=f"past-{i}",
            captured_at=f"2026-05-04T11:0{i}:00+00:00",
            mood="frustrated", intensity=0.6,
            outcome_score=-0.7, outcome_source="auto",
            context_features_json=feats,
        )

    # Now record a fresh episode that matches that context
    monkeypatch.setattr(em, "_read_current_mood", lambda: ("frustrated", 0.65))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})
    record_runtime_episode(
        source_run_id="run-fresh",
        session_id="s",
        trigger="visible-run:ollama/glm",
        outcome_status="interrupted",
        summary="interrupted with proposal",
        tool_names=["propose_source_edit"],
        error="timeout",
    )

    frame = build_cognitive_frame()
    em_carry = frame.get("emotional_memory_carry") or {}
    assert em_carry.get("active") is True
    assert em_carry.get("match_count") >= 2

    section = build_cognitive_frame_prompt_section()
    assert section is not None
    assert "Emotional precedent" in section


def test_cognitive_frame_omits_emotional_section_when_no_episode_carry(
    isolated_runtime, monkeypatch
) -> None:
    from core.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
        build_cognitive_frame_prompt_section,
    )

    frame = build_cognitive_frame()
    assert (frame.get("emotional_memory_carry") or {}).get("active") is not True

    section = build_cognitive_frame_prompt_section()
    if section is not None:
        assert "Emotional precedent" not in section
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_emotional_memory_integration.py -v
```

Expected: FAIL — `emotional_memory_carry` not yet present in the frame.

- [ ] **Step 3: Wire the conductor**

Open `core/services/runtime_cognitive_conductor.py`.

**3a)** Add a new safe-getter near the other `_safe_*_surface` helpers (around line 1071, next to `_safe_perception_surface`):

```python
def _safe_emotional_memory_surface(
    *,
    context_features: dict[str, object] | None = None,
) -> dict[str, object]:
    try:
        from core.services.emotional_memory_engine import build_emotional_memory_surface
        return build_emotional_memory_surface(
            anchor_type="cognitive_episode",
            context_features=context_features or {},
        )
    except Exception:
        return {"active": False, "summary": "", "items": [], "match_count": 0}
```

**3b)** Add a helper to extract context features from the latest cognitive_episode (place it just below `_safe_emotional_memory_surface`):

```python
def _extract_context_features_from_episode(
    cognitive_episode: dict[str, object],
) -> dict[str, object]:
    """Pull retrieval-relevant fields from a cognitive_episode surface entry."""
    if not cognitive_episode or not cognitive_episode.get("active"):
        return {}
    items = cognitive_episode.get("items") or []
    if not items:
        return {}
    latest = items[0]
    perception = latest.get("perception") or {}
    return {
        "trigger": str(latest.get("trigger") or ""),
        "tool_names": [
            t for t in (
                (latest.get("learning") or {}).get("evidence", {}).get("tools") or []
            ) if t
        ],
        "outcome_status": str(latest.get("outcome_status") or ""),
        "error_kind": str(perception.get("mode") or ""),
        "summary": str(latest.get("summary") or "")[:200],
    }
```

(The exact path from `latest` to `tool_names` depends on how `_decode_episode` shapes the dict in `cognitive_episodes.py`. If `tool_names` are stored in `learning.evidence.tools` the path above works; otherwise adapt to whatever `_decode_episode` actually returns. Verify by reading `_decode_episode` before implementing.)

**3c)** Inside `build_cognitive_frame`, after the `cognitive_episode = _safe_cognitive_episode_surface()` line and before salient injection, fetch the emotional memory surface:

```python
        emotional_memory = _safe_emotional_memory_surface(
            context_features=_extract_context_features_from_episode(cognitive_episode)
        )
```

Make sure this is inside the `with runtime_surface_cache():` block, alongside the other `_safe_*` reads.

**3d)** After the existing `if perception.get("active"): ...` injection block (search for `"perception"` source string), add:

```python
    if emotional_memory.get("active"):
        em_summary = str(emotional_memory.get("directive") or "")[:_MAX_SLICE_CHARS]
        if em_summary:
            em_item = {
                "source": "emotional-memory",
                "summary": em_summary,
                "temporal": "carried-across-sessions",
            }
            if salient and salient[0].get("source") in {
                "cognitive-episode", "theory-of-mind", "learning-policy",
            }:
                salient = [salient[0], em_item, *salient[1:]][:_MAX_SALIENT_ITEMS]
            else:
                salient = [em_item, *salient][:_MAX_SALIENT_ITEMS]
```

**3e)** In the `return { ... }` dict at the bottom of `build_cognitive_frame`, add the carry field next to the other `*_carry` fields (e.g., next to `perception_carry`):

```python
        "emotional_memory_carry": emotional_memory if emotional_memory.get("active") else {},
```

And inside the `"counts": { ... }` sub-dict, add:

```python
            "emotional_memory_carry": 1 if emotional_memory.get("active") else 0,
```

Update the `integrated_signal_inputs` total to include this carry as well:

```python
                + (1 if emotional_memory.get("active") else 0)
```

**3f)** Inside `build_cognitive_frame_prompt_section`, after the `if perception.get("active"): ...` line (around the line that appends `f"- Perception: {directive[:90]}"`), add:

```python
    emotional_memory = frame.get("emotional_memory_carry") or {}
    if emotional_memory.get("active"):
        directive = str(emotional_memory.get("directive") or "").strip()
        if directive:
            lines.append(f"- Emotional precedent: {directive[:120]}")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_emotional_memory_integration.py -v
pytest tests/test_cognitive_conductor.py -v
```

Expected: PASS for both. Existing conductor tests must remain green.

- [ ] **Step 5: Commit**

```bash
git add core/services/runtime_cognitive_conductor.py tests/test_emotional_memory_integration.py
git commit -m "feat(emotional-memory): conductor integration with frame carry and prompt line"
```

---

## Task 12: Migration script

**Files:**
- Create: `scripts/migrate_emotional_memory.py`
- Create: `tests/test_emotional_memory_migration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_emotional_memory_migration.py`:

```python
from __future__ import annotations


def test_migration_copies_legacy_rows(isolated_runtime) -> None:
    from core.runtime.db import connect, list_emotional_memory_anchors
    from scripts.migrate_emotional_memory import migrate

    # Seed legacy table directly
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_emotional_context (
                heading_normalized TEXT PRIMARY KEY,
                heading_display    TEXT NOT NULL,
                mood               TEXT NOT NULL,
                intensity          REAL NOT NULL,
                captured_at        TEXT NOT NULL,
                source             TEXT,
                notes              TEXT
            )
            """
        )
        conn.execute(
            """INSERT INTO memory_emotional_context
               (heading_normalized, heading_display, mood, intensity,
                captured_at, source, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("h-1", "## H1", "calm", 0.3, "2026-05-01T10:00:00+00:00", "x", None),
        )
        conn.execute(
            """INSERT INTO memory_emotional_context VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("h-2", "## H2", "frustrated", 0.7, "2026-05-02T10:00:00+00:00", "y", "n"),
        )

    stats = migrate()
    assert stats["migrated"] == 2

    rows = list_emotional_memory_anchors(anchor_type="memory_heading", limit=10)
    assert len(rows) == 2
    moods = sorted(r["mood"] for r in rows)
    assert moods == ["calm", "frustrated"]


def test_migration_is_idempotent(isolated_runtime) -> None:
    from core.runtime.db import connect, list_emotional_memory_anchors
    from scripts.migrate_emotional_memory import migrate

    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_emotional_context (
                heading_normalized TEXT PRIMARY KEY,
                heading_display    TEXT NOT NULL,
                mood               TEXT NOT NULL,
                intensity          REAL NOT NULL,
                captured_at        TEXT NOT NULL,
                source             TEXT,
                notes              TEXT
            )
            """
        )
        conn.execute(
            """INSERT INTO memory_emotional_context VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("h-1", "## H1", "calm", 0.3, "2026-05-01T10:00:00+00:00", "x", None),
        )

    s1 = migrate()
    s2 = migrate()
    assert s1["migrated"] == 1
    assert s2["migrated"] == 0  # second pass: nothing new
    rows = list_emotional_memory_anchors(anchor_type="memory_heading")
    assert len(rows) == 1


def test_migration_handles_missing_legacy_table(isolated_runtime) -> None:
    from scripts.migrate_emotional_memory import migrate
    # No legacy table exists at all
    stats = migrate()
    assert stats["migrated"] == 0
    assert stats["skipped"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_emotional_memory_migration.py -v
```

Expected: FAIL — `scripts.migrate_emotional_memory` does not exist.

- [ ] **Step 3: Implement migration script**

Create `scripts/migrate_emotional_memory.py`:

```python
"""One-shot migration: copy memory_emotional_context rows into emotional_memory_anchors.

Idempotent — safe to run multiple times. Leaves the legacy table intact;
deletion is a separate later commit once the new system has proven itself
in production.

Usage:
    conda activate ai
    python scripts/migrate_emotional_memory.py
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

# Make `core` importable when run as a script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.runtime.db import (  # noqa: E402
    connect,
    insert_emotional_memory_anchor,
)

logger = logging.getLogger(__name__)


def migrate(*, batch_size: int = 500) -> dict[str, int]:
    """Migrate legacy rows into the new table.

    Returns {"migrated": N, "skipped": M} where skipped includes rows
    already present in the new table (counted as no-ops).
    """
    migrated = 0
    skipped = 0

    with connect() as conn:
        if not _legacy_table_exists(conn):
            return {"migrated": 0, "skipped": 0}
        rows = conn.execute(
            "SELECT heading_normalized, heading_display, mood, intensity, "
            "captured_at, source, notes FROM memory_emotional_context"
        ).fetchall()

    for row in rows:
        anchor_id = str(row["heading_normalized"])
        try:
            from core.runtime.db import get_emotional_memory_anchor
            existing = get_emotional_memory_anchor("memory_heading", anchor_id)
            if existing is not None:
                skipped += 1
                continue
            insert_emotional_memory_anchor(
                anchor_type="memory_heading",
                anchor_id=anchor_id,
                captured_at=str(row["captured_at"]),
                mood=str(row["mood"]),
                intensity=float(row["intensity"]),
                context_features_json=json.dumps(
                    {"heading_display": row["heading_display"]},
                    ensure_ascii=False,
                ),
                source=row["source"],
                notes=row["notes"],
            )
            migrated += 1
        except Exception as exc:
            logger.warning("migration: failed for %s: %s", anchor_id, exc)
            skipped += 1

    return {"migrated": migrated, "skipped": skipped}


def _legacy_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_emotional_context'"
    ).fetchone()
    return row is not None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stats = migrate()
    print(f"migrated={stats['migrated']} skipped={stats['skipped']}")
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_emotional_memory_migration.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/migrate_emotional_memory.py tests/test_emotional_memory_migration.py
git commit -m "feat(emotional-memory): migration script for legacy memory_emotional_context"
```

---

## Task 13: Final smoke and CI verification

**Files:** No new files — final validation pass.

- [ ] **Step 1: Run the full emotional memory test suite**

```
conda activate ai
pytest tests/test_db_emotional_memory.py \
       tests/test_emotional_memory_settings.py \
       tests/test_emotional_memory_engine.py \
       tests/test_emotional_memory_integration.py \
       tests/test_memory_emotional_context_shim.py \
       tests/test_emotional_memory_migration.py \
       -v
```

Expected: ALL PASS (~30+ tests).

- [ ] **Step 2: Run adjacent test suites that could regress**

```
pytest tests/test_cognitive_episodes.py \
       tests/test_cognitive_conductor.py \
       tests/test_perceptual_event_engine.py \
       -v
```

Expected: ALL PASS — no regressions in the modules we touched.

- [ ] **Step 3: Syntax smoke (CI mirror)**

```
python -m compileall core apps/api scripts
```

Expected: Exit code 0 — no syntax errors.

- [ ] **Step 4: Manual end-to-end check (optional but recommended)**

Start a Python REPL with `conda activate ai`:

```python
from core.services.cognitive_episodes import record_runtime_episode
from core.services.emotional_memory_engine import build_emotional_memory_surface

# Drop two synthetic episodes with the same context
for i in range(3):
    record_runtime_episode(
        source_run_id=f"smoke-{i}",
        session_id="smoke",
        trigger="visible-run:ollama/glm",
        outcome_status="interrupted",
        summary="smoke test",
        tool_names=["propose_source_edit"],
        error="timeout",
    )

# Check the surface picks them up
print(build_emotional_memory_surface(
    anchor_type="cognitive_episode",
    context_features={
        "trigger": "visible-run:ollama/glm",
        "tool_names": ["propose_source_edit"],
        "outcome_status": "interrupted",
        "error_kind": "timeout",
        "summary": "smoke test",
    },
))
```

Expected: prints a dict with `"active": True`, `match_count: 3`, and a non-empty `directive`.

- [ ] **Step 5: Final commit (if anything was tweaked during smoke)**

If the smoke check revealed any need for adjustments and they were made, commit them. Otherwise this step is a no-op.

```bash
git status
# If changes:
git add <touched files>
git commit -m "fix(emotional-memory): smoke-test corrections"
```

- [ ] **Step 6: Push branch and open PR**

This is the user's call — do not push or open the PR without explicit confirmation.

---

## Self-review notes

1. **Spec coverage:** Every spec section maps to one or more tasks:
   - *Architecture overview* → Task 1, 8, 9, 11
   - *Data model* → Task 1
   - *Capture flow* → Task 3, 4, 8, 9, 10
   - *Retrieval flow* → Task 6, 7
   - *Surface integration* → Task 7, 11
   - *Migration & backwards compatibility* → Task 10, 12
   - *Error handling* → woven through Task 4, 8, 9, 10, 11
   - *Testing strategy* → all tasks (TDD)
   - *Future extensions* → not implemented (correct — they are explicitly v2)
   - *Configuration* → Task 2

2. **Type/method consistency:**
   - `capture_emotional_anchor` signature consistent across Task 4, 8, 9, 10.
   - `_classify_error`, `_count_tool_errors`, `_derive_outcome_score` all defined in Task 3 and only consumed in Task 8.
   - `build_emotional_memory_surface(*, anchor_type, context_features)` consistent across Task 7 and 11.

3. **No placeholders.** All steps contain runnable code or exact commands.
