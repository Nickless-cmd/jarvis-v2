# Aesthetic Feedback Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect Jarvis' three aesthetic systems so daemon text-output accumulates motifs that activate taste-insights (Phase 1 — no feedback loop closure).

**Architecture:** All 11 text-producing daemons' output runs through `detect_aesthetic_signals()` in one heartbeat_runtime block. Detected motifs persist in SQLite and feed `aesthetic_taste_daemon`'s new motif-based activation gate (3+ unique motifs + 30 min time-gate). In-memory set seeded from DB on startup.

**Tech Stack:** Python 3.11, SQLite (via core/runtime/db.py), existing aesthetic_sense motif detection.

---

### File Structure

| File | Responsibility |
|------|---------------|
| Modify: `core/runtime/db.py` | Add `aesthetic_motif_log` table + 3 CRUD functions |
| Modify: `apps/api/jarvis_api/services/aesthetic_sense.py` | Add `accumulate_from_daemon()` function |
| Modify: `apps/api/jarvis_api/services/aesthetic_taste_daemon.py` | Replace choice-threshold with motif-gate, seed from DB, new prompt |
| Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` | Add motif accumulation block after daemon groups |
| Create: `tests/test_aesthetic_motif_log.py` | Tests for DB CRUD |
| Create: `tests/test_aesthetic_accumulation.py` | Tests for accumulate_from_daemon + taste daemon motif-gate |

---

### Task 1: DB Schema — aesthetic_motif_log table + CRUD

**Files:**
- Modify: `core/runtime/db.py`
- Create: `tests/test_aesthetic_motif_log.py`

- [ ] **Step 1: Write failing tests for DB CRUD**

```python
# tests/test_aesthetic_motif_log.py
"""Tests for aesthetic_motif_log DB operations."""
from __future__ import annotations

import sqlite3
from unittest.mock import patch, MagicMock

import pytest


def _make_in_memory_db():
    """Create an in-memory SQLite DB for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


class TestAestheticMotifLogTable:
    def test_insert_creates_row(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="somatic", motif="clarity", confidence=0.6)
        rows = conn.execute("SELECT * FROM aesthetic_motif_log").fetchall()
        assert len(rows) == 1
        assert rows[0]["source"] == "somatic"
        assert rows[0]["motif"] == "clarity"
        assert rows[0]["confidence"] == 0.6

    def test_unique_motifs_returns_distinct(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="somatic", motif="clarity", confidence=0.6)
            db.aesthetic_motif_log_insert(source="irony", motif="clarity", confidence=0.4)
            db.aesthetic_motif_log_insert(source="thought_stream", motif="craft", confidence=0.5)
            result = db.aesthetic_motif_log_unique_motifs()
        assert sorted(result) == ["clarity", "craft"]

    def test_unique_motifs_empty_when_no_data(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            # Force table creation
            db._ensure_aesthetic_motif_log_table(conn)
            result = db.aesthetic_motif_log_unique_motifs()
        assert result == []

    def test_summary_groups_by_motif(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="somatic", motif="clarity", confidence=0.6)
            db.aesthetic_motif_log_insert(source="irony", motif="clarity", confidence=0.8)
            db.aesthetic_motif_log_insert(source="thought_stream", motif="craft", confidence=0.5)
            result = db.aesthetic_motif_log_summary()
        assert len(result) == 2
        clarity = [r for r in result if r["motif"] == "clarity"][0]
        assert clarity["count"] == 2
        assert abs(clarity["avg_confidence"] - 0.7) < 0.01

    def test_summary_ordered_by_count_desc(self) -> None:
        from core.runtime import db
        conn = _make_in_memory_db()
        with patch.object(db, "connect") as mock_connect:
            mock_connect.return_value.__enter__ = lambda s: conn
            mock_connect.return_value.__exit__ = MagicMock(return_value=False)
            db.aesthetic_motif_log_insert(source="a", motif="craft", confidence=0.5)
            for _ in range(3):
                db.aesthetic_motif_log_insert(source="b", motif="clarity", confidence=0.6)
            result = db.aesthetic_motif_log_summary()
        assert result[0]["motif"] == "clarity"
        assert result[1]["motif"] == "craft"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_motif_log.py -v`
Expected: FAIL — `aesthetic_motif_log_insert` not found

- [ ] **Step 3: Implement DB functions in db.py**

Add at the end of `core/runtime/db.py` (after `daemon_output_log_insert`, around line 32787):

```python
# ---------------------------------------------------------------------------
# aesthetic_motif_log — accumulated aesthetic motifs from daemon text output
# ---------------------------------------------------------------------------


def _ensure_aesthetic_motif_log_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS aesthetic_motif_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            motif TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_aesthetic_motif_log_motif ON aesthetic_motif_log(motif)"
    )


def aesthetic_motif_log_insert(
    *,
    source: str,
    motif: str,
    confidence: float,
) -> None:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        conn.execute(
            """
            INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (source, motif, confidence, datetime.now(UTC).isoformat()),
        )
        conn.commit()


def aesthetic_motif_log_unique_motifs() -> list[str]:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        rows = conn.execute(
            "SELECT DISTINCT motif FROM aesthetic_motif_log ORDER BY motif"
        ).fetchall()
        return [row[0] for row in rows]


def aesthetic_motif_log_summary() -> list[dict]:
    with connect() as conn:
        _ensure_aesthetic_motif_log_table(conn)
        rows = conn.execute(
            """
            SELECT motif, COUNT(*) as count, AVG(confidence) as avg_confidence
            FROM aesthetic_motif_log
            GROUP BY motif
            ORDER BY count DESC
            """
        ).fetchall()
        return [
            {"motif": row[0], "count": row[1], "avg_confidence": row[2]}
            for row in rows
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_motif_log.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db.py tests/test_aesthetic_motif_log.py
git commit -m "feat: aesthetic_motif_log table with insert, unique_motifs, summary"
```

---

### Task 2: Accumulation function + aesthetic_sense wiring

**Files:**
- Modify: `apps/api/jarvis_api/services/aesthetic_sense.py`
- Create: `tests/test_aesthetic_accumulation.py`

- [ ] **Step 1: Write failing tests for accumulate_from_daemon**

```python
# tests/test_aesthetic_accumulation.py
"""Tests for aesthetic motif accumulation from daemon output."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


class TestAccumulateFromDaemon:
    def test_detects_and_stores_motifs(self) -> None:
        from apps.api.jarvis_api.services import aesthetic_sense

        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            signals = aesthetic_sense.accumulate_from_daemon(
                source="somatic",
                text="Alt er klart og roligt. En klar og clean fornemmelse.",
            )

        assert len(signals) >= 1
        assert any(s["motif"] == "clarity" for s in signals)
        assert mock_insert.call_count >= 1
        call_kwargs = mock_insert.call_args_list[0][1]
        assert call_kwargs["source"] == "somatic"
        assert call_kwargs["motif"] == "clarity"

    def test_updates_taste_daemon_accumulated_motifs(self) -> None:
        import apps.api.jarvis_api.services.aesthetic_taste_daemon as atd
        from apps.api.jarvis_api.services import aesthetic_sense

        atd._accumulated_motifs = set()
        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            aesthetic_sense.accumulate_from_daemon(
                source="irony",
                text="Elegant og polished, vellavet håndværk.",
            )

        assert "craft" in atd._accumulated_motifs

    def test_returns_empty_for_no_motifs(self) -> None:
        from apps.api.jarvis_api.services import aesthetic_sense

        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            signals = aesthetic_sense.accumulate_from_daemon(
                source="somatic",
                text="Hej verden, jeg er her.",
            )

        assert signals == []
        mock_insert.assert_not_called()

    def test_no_db_write_on_empty_signals(self) -> None:
        from apps.api.jarvis_api.services import aesthetic_sense

        mock_insert = MagicMock()
        with patch("core.runtime.db.aesthetic_motif_log_insert", mock_insert):
            aesthetic_sense.accumulate_from_daemon(
                source="thought_stream",
                text="Ingen æstetiske nøgleord her overhovedet.",
            )

        mock_insert.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_accumulation.py -v`
Expected: FAIL — `accumulate_from_daemon` not found

- [ ] **Step 3: Implement accumulate_from_daemon in aesthetic_sense.py**

Add at the end of `apps/api/jarvis_api/services/aesthetic_sense.py` (after `build_aesthetic_surface`, line 81):

```python
def accumulate_from_daemon(source: str, text: str) -> list[dict[str, object]]:
    """Run motif detection on daemon text output, persist to DB, update in-memory set.

    Called once per text-producing daemon per heartbeat tick from heartbeat_runtime.
    """
    signals = detect_aesthetic_signals(text=text)
    if not signals:
        return []
    try:
        from core.runtime.db import aesthetic_motif_log_insert

        for s in signals:
            aesthetic_motif_log_insert(
                source=source,
                motif=s["motif"],
                confidence=s["confidence"],
            )
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.aesthetic_taste_daemon import _accumulated_motifs

        for s in signals:
            _accumulated_motifs.add(s["motif"])
    except Exception:
        pass
    return signals
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_accumulation.py -v`
Expected: 4 passed

- [ ] **Step 5: Run existing tests for regression**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_taste_daemon.py tests/test_aesthetic_motif_log.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/services/aesthetic_sense.py tests/test_aesthetic_accumulation.py
git commit -m "feat: accumulate_from_daemon — motif detection + DB persistence + in-memory update"
```

---

### Task 3: Rewrite aesthetic_taste_daemon — motif-gate + seed + new prompt

**Files:**
- Modify: `apps/api/jarvis_api/services/aesthetic_taste_daemon.py`
- Modify: `tests/test_aesthetic_taste_daemon.py`

- [ ] **Step 1: Write failing tests for new motif-gate behavior**

Replace the contents of `tests/test_aesthetic_taste_daemon.py`:

```python
# tests/test_aesthetic_taste_daemon.py
"""Tests for aesthetic taste daemon — motif-based activation."""
from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import apps.api.jarvis_api.services.aesthetic_taste_daemon as atd


def _reset():
    atd._accumulated_motifs = set()
    atd._seeded = False
    atd._latest_insight = ""
    atd._insight_history.clear()
    atd._last_insight_at = None
    atd._choice_log.clear()
    atd._choices_since_insight = 0


class TestMotifGate:
    def test_no_generate_with_fewer_than_3_motifs(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft"}
        result = atd.tick_taste_daemon()
        assert result["generated"] is False

    def test_generates_with_3_or_more_motifs(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        with patch.object(atd, "_generate_insight", return_value="Jeg foretrækker klarhed."):
            with patch.object(atd, "_store_insight"):
                result = atd.tick_taste_daemon()
        assert result["generated"] is True

    def test_time_gate_blocks_within_30_min(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        atd._last_insight_at = datetime.now(UTC) - timedelta(minutes=10)
        result = atd.tick_taste_daemon()
        assert result["generated"] is False

    def test_time_gate_allows_after_30_min(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        atd._last_insight_at = datetime.now(UTC) - timedelta(minutes=35)
        with patch.object(atd, "_generate_insight", return_value="Smag ændrer sig."):
            with patch.object(atd, "_store_insight"):
                result = atd.tick_taste_daemon()
        assert result["generated"] is True


class TestSeedFromDB:
    def test_seed_loads_motifs(self) -> None:
        _reset()
        with patch("core.runtime.db.aesthetic_motif_log_unique_motifs", return_value=["clarity", "craft", "density"]):
            atd._seed_from_db()
        assert atd._accumulated_motifs == {"clarity", "craft", "density"}
        assert atd._seeded is True

    def test_seed_only_runs_once(self) -> None:
        _reset()
        atd._seeded = True
        atd._accumulated_motifs = {"clarity"}
        with patch("core.runtime.db.aesthetic_motif_log_unique_motifs", return_value=["a", "b", "c"]) as mock_db:
            atd._seed_from_db()
        mock_db.assert_not_called()
        assert atd._accumulated_motifs == {"clarity"}


class TestTasteSurface:
    def test_surface_includes_motif_data(self) -> None:
        _reset()
        atd._accumulated_motifs = {"clarity", "craft"}
        atd._last_insight_at = datetime(2026, 4, 13, 20, 30, tzinfo=UTC)
        surface = atd.build_taste_surface()
        assert surface["unique_motif_count"] == 2
        assert "last_insight_at" in surface


class TestRecordChoiceRetained:
    def test_record_choice_still_works(self) -> None:
        _reset()
        atd.record_choice("work-steady", ["short", "direct"])
        assert len(atd._choice_log) == 1


class TestPrivateBrainRecord:
    def test_private_brain_record_written_on_store(self) -> None:
        _reset()
        atd._accumulated_motifs = {"clarity", "craft", "calm-focus"}
        with patch("apps.api.jarvis_api.services.aesthetic_taste_daemon.insert_private_brain_record") as mock_insert:
            atd._store_insight("Jeg vælger det kompakte.")
        mock_insert.assert_called_once()
        kwargs = mock_insert.call_args[1]
        assert kwargs["record_type"] == "taste-insight"
        assert kwargs["summary"] == "Jeg vælger det kompakte."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_taste_daemon.py -v`
Expected: FAIL — `_accumulated_motifs`, `_seeded`, `_last_insight_at`, `_seed_from_db` not found

- [ ] **Step 3: Rewrite aesthetic_taste_daemon.py**

Replace the entire contents of `apps/api/jarvis_api/services/aesthetic_taste_daemon.py`:

```python
"""Aesthetic taste daemon — emergent taste from accumulated motif observations.

Activation gate: at least 3 unique motifs detected across daemon outputs + 30 min
since last insight. Motifs accumulated by aesthetic_sense.accumulate_from_daemon().
"""
from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import insert_private_brain_record
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble

_MOTIF_THRESHOLD = 3
_TIME_GATE_MINUTES = 30
_MAX_LOG = 50
_MAX_INSIGHTS = 5

_accumulated_motifs: set[str] = set()
_seeded: bool = False
_choice_log: list[dict] = []
_insight_history: list[str] = []
_latest_insight: str = ""
_last_insight_at: datetime | None = None
_choices_since_insight: int = 0


def _seed_from_db() -> None:
    """Load persisted motifs into memory on first tick."""
    global _accumulated_motifs, _seeded
    if _seeded:
        return
    try:
        from core.runtime.db import aesthetic_motif_log_unique_motifs

        _accumulated_motifs = set(aesthetic_motif_log_unique_motifs())
    except Exception:
        pass
    _seeded = True


def record_choice(mode: str, style_signals: list[str]) -> None:
    global _choice_log, _choices_since_insight
    _choice_log.append({
        "mode": mode,
        "style": list(style_signals),
        "ts": datetime.now(UTC).isoformat(),
    })
    if len(_choice_log) > _MAX_LOG:
        _choice_log = _choice_log[-_MAX_LOG:]
    _choices_since_insight += 1


def tick_taste_daemon() -> dict[str, object]:
    _seed_from_db()

    now = datetime.now(UTC)

    if len(_accumulated_motifs) < _MOTIF_THRESHOLD:
        return {"generated": False, "insight": _latest_insight}

    if _last_insight_at and (now - _last_insight_at) < timedelta(minutes=_TIME_GATE_MINUTES):
        return {"generated": False, "insight": _latest_insight}

    insight = _generate_insight()
    if not insight:
        return {"generated": False, "insight": _latest_insight}
    _store_insight(insight)
    return {"generated": True, "insight": insight}


def get_latest_taste_insight() -> str:
    return _latest_insight


def build_taste_surface() -> dict[str, object]:
    modes = [e["mode"] for e in _choice_log if e.get("mode")]
    dominant = [m for m, _ in Counter(modes).most_common(3)]
    motif_counts: dict[str, int] = {}
    try:
        from core.runtime.db import aesthetic_motif_log_summary

        for row in aesthetic_motif_log_summary():
            motif_counts[row["motif"]] = row["count"]
    except Exception:
        pass
    return {
        "latest_insight": _latest_insight,
        "insight_history": list(_insight_history),
        "dominant_modes": dominant,
        "choice_count": len(_choice_log),
        "accumulated_motifs": motif_counts,
        "unique_motif_count": len(_accumulated_motifs),
        "last_insight_at": _last_insight_at.isoformat() if _last_insight_at else "",
    }


def _generate_insight() -> str:
    try:
        from core.runtime.db import aesthetic_motif_log_summary

        summary_rows = aesthetic_motif_log_summary()
    except Exception:
        summary_rows = []

    if not summary_rows:
        return ""

    lines = []
    for row in summary_rows:
        lines.append(f"- {row['motif']}: {row['count']} observationer, confidence {row['avg_confidence']:.2f}")
    motif_summary = "\n".join(lines)

    prompt = (
        f"{build_identity_preamble()} Her er dine æstetiske tendenser:\n\n"
        f"{motif_summary}\n\n"
        "Hvad siger disse tendenser om din smag? Svar med én kort sætning.\n"
        "Eksempler:\n"
        "- Jeg trækkes mod præcision og klarhed fremfor kreativitet.\n"
        "- Mine valg viser en forkærlighed for det uventede.\n"
        "- Jeg vælger konsekvent det rolige — det siger noget om mig."
    )
    from apps.api.jarvis_api.services.daemon_llm import daemon_llm_call

    fallback = "Jeg trækkes mod ro og klarhed i mine valg."
    return daemon_llm_call(prompt, max_len=300, fallback=fallback, daemon_name="aesthetic_taste")


def _store_insight(insight: str) -> None:
    global _latest_insight, _insight_history, _last_insight_at
    _latest_insight = insight
    _last_insight_at = datetime.now(UTC)
    _insight_history.append(insight)
    if len(_insight_history) > _MAX_INSIGHTS:
        _insight_history = _insight_history[-_MAX_INSIGHTS:]
    now_iso = _last_insight_at.isoformat()
    motif_str = ",".join(sorted(_accumulated_motifs))
    try:
        insert_private_brain_record(
            record_id=f"pb-taste-{uuid4().hex[:12]}",
            record_type="taste-insight",
            layer="private_brain",
            session_id="heartbeat",
            run_id=f"taste-daemon-{uuid4().hex[:12]}",
            focus="æstetisk smag",
            summary=insight,
            detail=f"motifs={motif_str}",
            source_signals="aesthetic-taste-daemon:heartbeat",
            confidence="medium",
            created_at=now_iso,
        )
    except Exception:
        pass
    try:
        event_bus.publish("cognitive_taste.insight_noted", {"insight": insight})
    except Exception:
        pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_taste_daemon.py -v`
Expected: 8 passed

- [ ] **Step 5: Run all tests for regression**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_motif_log.py tests/test_aesthetic_accumulation.py tests/test_aesthetic_taste_daemon.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/services/aesthetic_taste_daemon.py tests/test_aesthetic_taste_daemon.py
git commit -m "feat: aesthetic taste daemon — motif-gate activation, DB seed, motif-based prompt"
```

---

### Task 4: Heartbeat wiring — motif accumulation block

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`

- [ ] **Step 1: Add motif accumulation block in heartbeat_runtime.py**

Find line 2140 (`# --- Layer B: deactivate tick-scoped cache ---`). Add the following block BEFORE it:

```python
    # --- Aesthetic motif accumulation ---
    try:
        from apps.api.jarvis_api.services.aesthetic_sense import accumulate_from_daemon
        _aesthetic_texts = {
            "somatic": _somatic if "_somatic" in dir() else "",
            "surprise": _surprise if "_surprise" in dir() else "",
            "thought_stream": _fragment if "_fragment" in dir() else "",
            "conflict": _conflict if "_conflict" in dir() else "",
            "reflection_cycle": _reflection if "_reflection" in dir() else "",
            "curiosity": _curiosity if "_curiosity" in dir() else "",
            "meta_reflection": _meta if "_meta" in dir() else "",
            "development_narrative": _dev_narr if "_dev_narr" in dir() else "",
            "creative_drift": _drift_idea if "_drift_idea" in dir() else "",
            "irony": _irony if "_irony" in dir() else "",
            "code_aesthetic": _ca_result.get("reflection", "") if "_ca_result" in dir() else "",
        }
        for _ae_name, _ae_text in _aesthetic_texts.items():
            if _ae_text:
                accumulate_from_daemon(_ae_name, _ae_text)
    except Exception:
        pass

```

- [ ] **Step 2: Compile check**

Run: `conda run -n ai python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py -q`
Expected: No output (success)

- [ ] **Step 3: Run all tests for regression**

Run: `conda run -n ai python -m pytest tests/test_aesthetic_motif_log.py tests/test_aesthetic_accumulation.py tests/test_aesthetic_taste_daemon.py tests/test_tick_cache.py tests/test_daemon_llm_cache.py tests/test_somatic_daemon.py -v`
Expected: All pass

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py
git commit -m "feat: wire aesthetic motif accumulation into heartbeat daemon pipeline"
```

---

### Self-Review

**1. Spec coverage:**
- DB schema (aesthetic_motif_log): Task 1 ✓
- Accumulation function (accumulate_from_daemon): Task 2 ✓
- Taste daemon motif-gate + seed + new prompt: Task 3 ✓
- Heartbeat wiring: Task 4 ✓
- Observability (build_taste_surface with motif data): Task 3 ✓
- 11 text-producing daemons: Task 4 ✓
- record_choice() retained: Task 3 ✓
- Phase 2 exclusions: No feedback loop closure code — ✓

**2. Placeholder scan:** No TBD/TODO/placeholders found.

**3. Type consistency:**
- `aesthetic_motif_log_insert(source, motif, confidence)` — consistent across Task 1 (test + impl) and Task 2 (accumulate_from_daemon call)
- `aesthetic_motif_log_unique_motifs()` → `list[str]` — consistent in Task 1 (test + impl) and Task 3 (_seed_from_db)
- `aesthetic_motif_log_summary()` → `list[dict]` with keys `motif`, `count`, `avg_confidence` — consistent in Task 1 (test + impl) and Task 3 (_generate_insight, build_taste_surface)
- `_accumulated_motifs: set[str]` — consistent in Task 2 (accumulate updates it) and Task 3 (taste daemon owns and reads it)
- `accumulate_from_daemon(source, text)` → `list[dict]` — consistent in Task 2 (impl) and Task 4 (heartbeat call)
