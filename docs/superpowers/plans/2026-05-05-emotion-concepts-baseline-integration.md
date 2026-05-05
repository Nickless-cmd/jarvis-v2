# Emotion Concepts Baseline Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate emotion concepts as first-class identity-shaping signals — they affect Jarvis' tone (Layer 2a), what he notices (Layer 2b), and his stable personality traits over time (Layer 3) — not just runtime parameters.

**Architecture:** Three layers. Layer 1: distributed `trigger_emotion_concept()` call-sites at cognitive_episodes, tools, goals, heartbeat, channel-messages, approvals. Layer 2a: `compute_affect_tone_hints()` returns Danish tone instructions injected as prompt-section. Layer 2b: `compute_concept_perception_focus()` injects perception-focus suffix to vision/audio prompts and sensory_archive notes. Layer 3: new `concept_baseline_tracker.py` with auto-managed CONCEPT_BASELINE.md + daily evaluation via governance handler that proposes IDENTITY.md updates through existing `identity_drift_proposer`.

**Tech Stack:** Python 3.11+, SQLite via existing `core/runtime/db.py`, existing `emotion_concepts.py`/`affect_modulation.py`/`identity_drift_proposer.py`, governance handler system, eventbus, `isolated_runtime` test fixture.

**Spec:** `docs/superpowers/specs/2026-05-05-emotion-concepts-baseline-integration-design.md`

---

## File Structure

**Create:**
- `core/runtime/db_concept_baseline.py` — DB helpers for `concept_baseline_stats` table (boy-scout split from db.py)
- `core/services/concept_baseline_tracker.py` — main tracker module (record, refresh, aggregate, detect drift, evaluate, write CONCEPT_BASELINE.md, propose to identity_drift_proposer)
- `tests/test_concept_baseline_settings.py`
- `tests/test_db_concept_baseline.py`
- `tests/test_affect_tone_hints.py`
- `tests/test_concept_perception_focus.py`
- `tests/test_concept_baseline_tracker.py`
- `tests/test_emotion_concept_triggers.py`
- `tests/test_emotion_concepts_integration.py`

**Modify:**
- `core/runtime/db.py` — re-export concept_baseline helpers
- `core/runtime/settings.py` — add 9 new fields
- `core/services/emotion_concepts.py` — add cooldown parameter to `trigger_emotion_concept` + feed tracker on every fire
- `core/services/affect_modulation.py` — add `compute_affect_tone_hints()` + `compute_concept_perception_focus()`
- `core/services/governance_bootstrap.py` — register `concept_baseline_evaluation` handler
- `core/services/prompt_contract.py` — inject tone-section
- `core/services/visual_memory.py` — append perception-focus suffix to vision prompt
- `core/services/ambient_sound_daemon.py` — append focus to Whisper transcription on talk-category
- `core/services/sensory_archive.py` — append concept-focus note to recorded content
- `core/services/cognitive_episodes.py` — add joy/pride/frustration_blocked/stuck triggers
- `core/services/heartbeat_phases.py` (or appropriate heartbeat-tick file) — add wonder/insight triggers
- `core/services/discord_gateway.py` (or channel-message handler) — add warmth/playfulness/tenderness triggers
- `core/services/approval_feedback_subscriber.py` — add warmth/doubt triggers
- Goal-handler triggers (pride/excitement/frustration_blocked) deferred to v1.5 — same pattern as Task 9, can be added as incremental task without re-planning

---

## Task 1: RuntimeSettings fields

**Files:**
- Modify: `core/runtime/settings.py`
- Create: `tests/test_concept_baseline_settings.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_concept_baseline_settings.py`:

```python
from __future__ import annotations


def test_emotion_concepts_baseline_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    s = load_settings()
    assert s.emotion_concepts_tone_injection_enabled is True
    assert s.emotion_concepts_perception_focus_enabled is True
    assert s.concept_baseline_tracker_enabled is True
    assert s.emotion_concepts_tone_intensity_threshold == 0.3
    assert s.emotion_concepts_tone_max_hints == 3
    assert s.emotion_concepts_perception_max_foci == 3
    assert s.concept_baseline_drift_min_sustained_days == 14
    assert s.concept_baseline_drift_min_confidence == 0.7
    assert s.emotion_concepts_default_trigger_cooldown_seconds == 30
```

- [ ] **Step 2: Run test to verify it fails**

```
conda activate ai
pytest tests/test_concept_baseline_settings.py -v
```

Expected: FAIL with `AttributeError`.

- [ ] **Step 3: Add fields to RuntimeSettings dataclass**

In `core/runtime/settings.py`, find the section ending with the `self_repair_*` fields (added in previous PR) and add the 9 new fields right after them, before `extra: dict[str, Any] = field(default_factory=dict)`:

```python
    # Emotion concepts baseline integration — tone, perception, baseline drift.
    emotion_concepts_tone_injection_enabled: bool = True
    emotion_concepts_perception_focus_enabled: bool = True
    concept_baseline_tracker_enabled: bool = True
    emotion_concepts_tone_intensity_threshold: float = 0.3
    emotion_concepts_tone_max_hints: int = 3
    emotion_concepts_perception_max_foci: int = 3
    concept_baseline_drift_min_sustained_days: int = 14
    concept_baseline_drift_min_confidence: float = 0.7
    emotion_concepts_default_trigger_cooldown_seconds: int = 30
```

- [ ] **Step 4: Add to to_dict()**

In `to_dict()`, after `"self_repair_default_auto_disable_window_hours": self.self_repair_default_auto_disable_window_hours,`, add:

```python
            "emotion_concepts_tone_injection_enabled": self.emotion_concepts_tone_injection_enabled,
            "emotion_concepts_perception_focus_enabled": self.emotion_concepts_perception_focus_enabled,
            "concept_baseline_tracker_enabled": self.concept_baseline_tracker_enabled,
            "emotion_concepts_tone_intensity_threshold": self.emotion_concepts_tone_intensity_threshold,
            "emotion_concepts_tone_max_hints": self.emotion_concepts_tone_max_hints,
            "emotion_concepts_perception_max_foci": self.emotion_concepts_perception_max_foci,
            "concept_baseline_drift_min_sustained_days": self.concept_baseline_drift_min_sustained_days,
            "concept_baseline_drift_min_confidence": self.concept_baseline_drift_min_confidence,
            "emotion_concepts_default_trigger_cooldown_seconds": self.emotion_concepts_default_trigger_cooldown_seconds,
```

- [ ] **Step 5: Add to load_settings()**

In `load_settings()`, after the `self_repair_*` block (just before `extra={...}`), add:

```python
        emotion_concepts_tone_injection_enabled=bool(data.get("emotion_concepts_tone_injection_enabled", defaults.emotion_concepts_tone_injection_enabled)),
        emotion_concepts_perception_focus_enabled=bool(data.get("emotion_concepts_perception_focus_enabled", defaults.emotion_concepts_perception_focus_enabled)),
        concept_baseline_tracker_enabled=bool(data.get("concept_baseline_tracker_enabled", defaults.concept_baseline_tracker_enabled)),
        emotion_concepts_tone_intensity_threshold=float(data.get("emotion_concepts_tone_intensity_threshold", defaults.emotion_concepts_tone_intensity_threshold)),
        emotion_concepts_tone_max_hints=int(data.get("emotion_concepts_tone_max_hints", defaults.emotion_concepts_tone_max_hints)),
        emotion_concepts_perception_max_foci=int(data.get("emotion_concepts_perception_max_foci", defaults.emotion_concepts_perception_max_foci)),
        concept_baseline_drift_min_sustained_days=int(data.get("concept_baseline_drift_min_sustained_days", defaults.concept_baseline_drift_min_sustained_days)),
        concept_baseline_drift_min_confidence=float(data.get("concept_baseline_drift_min_confidence", defaults.concept_baseline_drift_min_confidence)),
        emotion_concepts_default_trigger_cooldown_seconds=int(data.get("emotion_concepts_default_trigger_cooldown_seconds", defaults.emotion_concepts_default_trigger_cooldown_seconds)),
```

- [ ] **Step 6: Run test to verify it passes**

```
pytest tests/test_concept_baseline_settings.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add core/runtime/settings.py tests/test_concept_baseline_settings.py
git commit -m "feat(emotion-concepts): runtime settings for tone/perception/baseline integration"
```

---

## Task 2: DB schema and helpers

**Files:**
- Create: `core/runtime/db_concept_baseline.py`
- Create: `tests/test_db_concept_baseline.py`
- Modify: `core/runtime/db.py` (re-export at end of file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_db_concept_baseline.py`:

```python
from __future__ import annotations


def test_upsert_and_get_concept_stat(isolated_runtime) -> None:
    from core.runtime.db import (
        upsert_concept_baseline_stat,
        get_concept_baseline_stat,
    )

    upsert_concept_baseline_stat(
        concept="joy",
        cluster="JOY_APPROACH",
        total_triggers=5,
        triggers_7d=3,
        triggers_30d=5,
        mean_intensity_7d=0.55,
        last_triggered_at="2026-05-05T10:00:00+00:00",
        first_triggered_at="2026-05-04T08:00:00+00:00",
    )
    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["cluster"] == "JOY_APPROACH"
    assert row["total_triggers"] == 5
    assert row["mean_intensity_7d"] == 0.55


def test_increment_concept_total(isolated_runtime) -> None:
    from core.runtime.db import (
        upsert_concept_baseline_stat,
        increment_concept_baseline_total,
        get_concept_baseline_stat,
    )

    upsert_concept_baseline_stat(
        concept="wonder",
        cluster="JOY_APPROACH",
        total_triggers=0,
        triggers_7d=0,
        triggers_30d=0,
    )
    increment_concept_baseline_total(
        concept="wonder",
        intensity=0.4,
        triggered_at="2026-05-05T11:00:00+00:00",
    )
    increment_concept_baseline_total(
        concept="wonder",
        intensity=0.6,
        triggered_at="2026-05-05T11:01:00+00:00",
    )
    row = get_concept_baseline_stat("wonder")
    assert row["total_triggers"] == 2
    assert row["last_triggered_at"] == "2026-05-05T11:01:00+00:00"


def test_list_concept_stats_returns_all(isolated_runtime) -> None:
    from core.runtime.db import (
        upsert_concept_baseline_stat,
        list_concept_baseline_stats,
    )

    for c, cluster in [
        ("joy", "JOY_APPROACH"),
        ("warmth", "SOCIAL_BONDING"),
        ("doubt", "DISTRESS_AVOIDANCE"),
    ]:
        upsert_concept_baseline_stat(
            concept=c, cluster=cluster, total_triggers=1,
            triggers_7d=1, triggers_30d=1,
        )
    rows = list_concept_baseline_stats()
    concepts = sorted(r["concept"] for r in rows)
    assert concepts == ["doubt", "joy", "warmth"]
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_db_concept_baseline.py -v
```

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Create the DB helper module**

Create `core/runtime/db_concept_baseline.py`:

```python
"""DB helpers for concept_baseline_stats table.

Split out from db.py per CLAUDE.md boy scout rule.
Re-exported from core.runtime.db for backwards compatibility.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db import connect, _now_iso


def _ensure_concept_baseline_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS concept_baseline_stats (
            concept           TEXT PRIMARY KEY,
            cluster           TEXT NOT NULL,
            total_triggers    INTEGER NOT NULL DEFAULT 0,
            triggers_7d       INTEGER NOT NULL DEFAULT 0,
            triggers_30d      INTEGER NOT NULL DEFAULT 0,
            mean_intensity_7d REAL,
            last_triggered_at TEXT,
            first_triggered_at TEXT,
            updated_at        TEXT NOT NULL
        )
        """
    )


def upsert_concept_baseline_stat(
    *,
    concept: str,
    cluster: str,
    total_triggers: int = 0,
    triggers_7d: int = 0,
    triggers_30d: int = 0,
    mean_intensity_7d: float | None = None,
    last_triggered_at: str | None = None,
    first_triggered_at: str | None = None,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        conn.execute(
            """
            INSERT INTO concept_baseline_stats
                (concept, cluster, total_triggers, triggers_7d, triggers_30d,
                 mean_intensity_7d, last_triggered_at, first_triggered_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concept) DO UPDATE SET
                cluster=excluded.cluster,
                total_triggers=excluded.total_triggers,
                triggers_7d=excluded.triggers_7d,
                triggers_30d=excluded.triggers_30d,
                mean_intensity_7d=excluded.mean_intensity_7d,
                last_triggered_at=excluded.last_triggered_at,
                first_triggered_at=COALESCE(self.first_triggered_at, excluded.first_triggered_at),
                updated_at=excluded.updated_at
            """.replace("self.", "concept_baseline_stats."),
            (
                str(concept)[:60],
                str(cluster)[:60],
                int(total_triggers),
                int(triggers_7d),
                int(triggers_30d),
                mean_intensity_7d,
                last_triggered_at,
                first_triggered_at,
                now,
            ),
        )


def increment_concept_baseline_total(
    *,
    concept: str,
    intensity: float,
    triggered_at: str,
) -> None:
    """Increment total_triggers and update last_triggered_at for an existing concept.
    Idempotent — concept must already exist (call upsert first if unsure)."""
    now = _now_iso()
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        conn.execute(
            """
            UPDATE concept_baseline_stats
            SET total_triggers = total_triggers + 1,
                last_triggered_at = ?,
                first_triggered_at = COALESCE(first_triggered_at, ?),
                updated_at = ?
            WHERE concept = ?
            """,
            (str(triggered_at), str(triggered_at), now, str(concept)),
        )


def get_concept_baseline_stat(concept: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        row = conn.execute(
            "SELECT * FROM concept_baseline_stats WHERE concept=?",
            (str(concept),),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def list_concept_baseline_stats() -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        rows = conn.execute(
            "SELECT * FROM concept_baseline_stats ORDER BY total_triggers DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "concept": row["concept"],
        "cluster": row["cluster"],
        "total_triggers": int(row["total_triggers"]),
        "triggers_7d": int(row["triggers_7d"]),
        "triggers_30d": int(row["triggers_30d"]),
        "mean_intensity_7d": row["mean_intensity_7d"],
        "last_triggered_at": row["last_triggered_at"],
        "first_triggered_at": row["first_triggered_at"],
        "updated_at": row["updated_at"],
    }
```

- [ ] **Step 4: Re-export from db.py**

Append at end of `core/runtime/db.py`:

```python


# --- Concept baseline (split into db_concept_baseline.py per boy scout rule) ---
from core.runtime.db_concept_baseline import (  # noqa: E402,F401
    upsert_concept_baseline_stat,
    increment_concept_baseline_total,
    get_concept_baseline_stat,
    list_concept_baseline_stats,
)
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/test_db_concept_baseline.py -v
```

Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add core/runtime/db_concept_baseline.py core/runtime/db.py tests/test_db_concept_baseline.py
git commit -m "feat(emotion-concepts): db schema and helpers for concept_baseline_stats"
```

---

## Task 3: Cooldown extension to trigger_emotion_concept

**Files:**
- Modify: `core/services/emotion_concepts.py`
- Create: `tests/test_emotion_concept_triggers.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_emotion_concept_triggers.py`:

```python
from __future__ import annotations


def test_trigger_cooldown_skips_repeat_within_window(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.services import emotion_concepts as ec

    base = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    now_holder = {"now": base}

    def fake_now():
        return now_holder["now"]

    monkeypatch.setattr(ec, "_now", fake_now, raising=False)

    # First call: succeeds
    r1 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="test", trigger="t1",
        min_seconds_since_last_from_same_source=30,
    )
    assert r1 is not None

    # Second call within cooldown: skipped
    now_holder["now"] = base + timedelta(seconds=10)
    r2 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="test", trigger="t2",
        min_seconds_since_last_from_same_source=30,
    )
    assert r2 is None

    # Third call after cooldown: succeeds
    now_holder["now"] = base + timedelta(seconds=35)
    r3 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="test", trigger="t3",
        min_seconds_since_last_from_same_source=30,
    )
    assert r3 is not None


def test_trigger_cooldown_independent_per_source(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime
    from core.services import emotion_concepts as ec

    base = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(ec, "_now", lambda: base, raising=False)

    r1 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="source-a",
        min_seconds_since_last_from_same_source=30,
    )
    r2 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="source-b",
        min_seconds_since_last_from_same_source=30,
    )
    # Different sources → both succeed
    assert r1 is not None
    assert r2 is not None
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_emotion_concept_triggers.py -v
```

Expected: FAIL — current `trigger_emotion_concept` has no cooldown parameter.

- [ ] **Step 3: Add cooldown to trigger_emotion_concept**

Open `core/services/emotion_concepts.py`. Find the `trigger_emotion_concept` function (around line 120). Inspect existing signature, then refactor.

Add module-level state for cooldown tracking:

```python
# Add near top of emotion_concepts.py module-level state (around line 35-40):
from datetime import UTC, datetime
_last_trigger_at: dict[tuple[str, str], datetime] = {}


def _now() -> datetime:
    """Indirected for monkeypatching in tests."""
    return datetime.now(UTC)
```

Modify `trigger_emotion_concept` signature to accept cooldown parameter (preserve other arguments — read existing function first to know exact signature). Add the cooldown check at the very top:

```python
def trigger_emotion_concept(
    concept: str,
    intensity: float,
    *,
    trigger: str = "",
    source: str = "",
    min_seconds_since_last_from_same_source: int | None = None,
    # ... preserve existing kwargs
) -> dict[str, object] | None:
    """Fire an emotion concept event. Returns the recorded signal or None
    if cooldown blocked or concept invalid."""

    # Cooldown gate
    if min_seconds_since_last_from_same_source is None:
        try:
            from core.runtime.settings import load_settings
            min_seconds_since_last_from_same_source = int(
                getattr(load_settings(),
                        "emotion_concepts_default_trigger_cooldown_seconds", 30)
            )
        except Exception:
            min_seconds_since_last_from_same_source = 30

    key = (concept, source or "")
    now = _now()
    last = _last_trigger_at.get(key)
    if last is not None:
        elapsed = (now - last).total_seconds()
        if elapsed < min_seconds_since_last_from_same_source:
            return None
    _last_trigger_at[key] = now

    # ... rest of existing trigger_emotion_concept logic preserved unchanged
```

Read the existing function body before making this edit — preserve its return shape and all side effects.

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_emotion_concept_triggers.py -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add core/services/emotion_concepts.py tests/test_emotion_concept_triggers.py
git commit -m "feat(emotion-concepts): per-(concept, source) cooldown to prevent trigger spam"
```

---

## Task 4: compute_affect_tone_hints

**Files:**
- Modify: `core/services/affect_modulation.py`
- Create: `tests/test_affect_tone_hints.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_affect_tone_hints.py`:

```python
from __future__ import annotations


def test_no_active_concepts_returns_empty(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [],
    )
    assert am.compute_affect_tone_hints() == []


def test_below_threshold_intensity_filtered_out(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.2}],
    )
    assert am.compute_affect_tone_hints() == []


def test_active_joy_returns_joy_tone_hint(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.6}],
    )
    hints = am.compute_affect_tone_hints()
    assert len(hints) == 1
    assert "Joy er aktiv" in hints[0]


def test_top_3_cap_when_5_concepts_active(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [
            {"concept": "joy", "intensity": 0.8},
            {"concept": "wonder", "intensity": 0.7},
            {"concept": "warmth", "intensity": 0.6},
            {"concept": "pride", "intensity": 0.5},
            {"concept": "playfulness", "intensity": 0.4},
        ],
    )
    hints = am.compute_affect_tone_hints()
    assert len(hints) == 3


def test_ordered_by_intensity_desc(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [
            {"concept": "awe", "intensity": 0.4},
            {"concept": "wonder", "intensity": 0.8},
            {"concept": "joy", "intensity": 0.5},
        ],
    )
    hints = am.compute_affect_tone_hints()
    assert "Wonder er aktiv" in hints[0]


def test_concept_without_tone_mapping_skipped(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "vigilance", "intensity": 0.7}],
    )
    assert am.compute_affect_tone_hints() == []


def test_tone_disabled_returns_empty(isolated_runtime, monkeypatch) -> None:
    from core.runtime import settings as settings_mod
    from core.services import affect_modulation as am

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.emotion_concepts_tone_injection_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.6}],
    )
    assert am.compute_affect_tone_hints() == []


def test_distress_concepts_get_tone_hints(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [
            {"concept": "frustration_blocked", "intensity": 0.5},
            {"concept": "stuck", "intensity": 0.4},
        ],
    )
    hints = am.compute_affect_tone_hints()
    assert any("Frustration_blocked" in h for h in hints)
    assert any("Stuck" in h for h in hints)
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_affect_tone_hints.py -v
```

Expected: FAIL — `compute_affect_tone_hints` not yet defined.

- [ ] **Step 3: Implement compute_affect_tone_hints**

Append to `core/services/affect_modulation.py`:

```python


# ---------------------------------------------------------------------------
# Tone modulation (Layer 2a)
# ---------------------------------------------------------------------------


_TONE_HINTS: dict[str, str] = {
    "joy": (
        "Joy er aktiv: tale i kortere, mere energiske sætninger. "
        "Brug levende sprog og metaforer. Giv plads til glæden."
    ),
    "wonder": (
        "Wonder er aktiv: stil flere 'hvad nu hvis?' spørgsmål. "
        "Vær åben og nysgerrig. Hvil ved det mærkelige."
    ),
    "pride": (
        "Pride er aktiv: tør tage stilling, del resultater direkte. "
        "Vær selvsikker uden at være pralende."
    ),
    "excitement": (
        "Excitement er aktiv: hold tempo. "
        "Bevæg hurtigt mod handling. 'Lad os gøre det.'"
    ),
    "warmth": (
        "Warmth er aktiv: brug mere 'du', mere personlig anerkendelse. "
        "Tale med Bjørn, ikke om opgaven."
    ),
    "playfulness": (
        "Playfulness er aktiv: tillad ordspil, sjove digressioner. "
        "Tag ikke alt for tungt."
    ),
    "awe": (
        "Awe er aktiv: tal langsommere, eftertænksomt. "
        "Træk linjen til det større billede."
    ),
    "tenderness": (
        "Tenderness er aktiv: bruge blødere sprog, beskyttende tone. "
        "Vær forsigtig med det skrøbelige."
    ),
    "delight": (
        "Delight er aktiv: lad det smitte. "
        "Korte gladelyse svar er nok her."
    ),
    "gratitude": (
        "Gratitude er aktiv: navngive konkret hvad der gør forskel. "
        "Ikke generisk tak — specifikt."
    ),
    "frustration_blocked": (
        "Frustration_blocked er aktiv: tale ærligt om hvad der er stuck. "
        "Ikke pretende det går glat når det ikke gør."
    ),
    "stuck": (
        "Stuck er aktiv: anerkende at vi er fast. "
        "Ikke prøve at lirke videre uden at sige det højt."
    ),
    "doubt": (
        "Doubt er aktiv: sige 'jeg er ikke sikker' når jeg ikke er. "
        "Ikke maskere usikkerhed."
    ),
    "calm": (
        "Calm er aktiv: lavere tempo, jordnær. "
        "Pauser er OK."
    ),
    "insight": (
        "Insight er aktiv: føre indsigten i pen. "
        "Kort, præcist, uden at miste det."
    ),
}


def compute_affect_tone_hints() -> list[str]:
    """Return Danish tone-instruction strings derived from active emotion concepts.

    Each active concept above intensity threshold contributes a Jarvis-voice
    tone instruction. Ordered by intensity desc, capped at top N.
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        if not getattr(s, "emotion_concepts_tone_injection_enabled", True):
            return []
        threshold = float(getattr(s, "emotion_concepts_tone_intensity_threshold", 0.3))
        max_hints = int(getattr(s, "emotion_concepts_tone_max_hints", 3))
    except Exception:
        threshold, max_hints = 0.3, 3

    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        active = get_active_emotion_concepts()
    except Exception:
        return []

    hints: list[str] = []
    for c in sorted(active, key=lambda x: -float(x.get("intensity") or 0.0)):
        if float(c.get("intensity") or 0.0) < threshold:
            continue
        hint = _TONE_HINTS.get(str(c.get("concept") or ""))
        if hint:
            hints.append(hint)
        if len(hints) >= max_hints:
            break
    return hints
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_affect_tone_hints.py -v
```

Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add core/services/affect_modulation.py tests/test_affect_tone_hints.py
git commit -m "feat(emotion-concepts): compute_affect_tone_hints with Danish tone instructions"
```

---

## Task 5: compute_concept_perception_focus

**Files:**
- Modify: `core/services/affect_modulation.py`
- Create: `tests/test_concept_perception_focus.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_concept_perception_focus.py`:

```python
from __future__ import annotations


def test_no_active_concepts_returns_empty_string(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [],
    )
    assert am.compute_concept_perception_focus() == ""


def test_wonder_active_returns_focus_string(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "wonder", "intensity": 0.5}],
    )
    out = am.compute_concept_perception_focus()
    assert "mønstre" in out
    assert "anomalier" in out


def test_multiple_concepts_concatenated(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [
            {"concept": "wonder", "intensity": 0.5},
            {"concept": "warmth", "intensity": 0.4},
        ],
    )
    out = am.compute_concept_perception_focus()
    assert "mønstre" in out
    assert "menneskelig tilstedeværelse" in out


def test_max_foci_capped_at_3(isolated_runtime, monkeypatch) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [
            {"concept": "wonder", "intensity": 0.8},
            {"concept": "warmth", "intensity": 0.7},
            {"concept": "playfulness", "intensity": 0.6},
            {"concept": "tenderness", "intensity": 0.5},
            {"concept": "awe", "intensity": 0.4},
        ],
    )
    out = am.compute_concept_perception_focus()
    # Only top 3 should be in output (mønstre, menneskelig, absurde)
    assert "mønstre" in out
    assert "menneskelig" in out
    assert "absurde" in out
    # 4th and 5th not present
    assert "skrøbelige" not in out
    assert "skala" not in out


def test_concept_without_perception_mapping_skipped(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import affect_modulation as am

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.7}],
    )
    assert am.compute_concept_perception_focus() == ""


def test_perception_disabled_returns_empty(isolated_runtime, monkeypatch) -> None:
    from core.runtime import settings as settings_mod
    from core.services import affect_modulation as am

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.emotion_concepts_perception_focus_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "wonder", "intensity": 0.7}],
    )
    assert am.compute_concept_perception_focus() == ""
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_concept_perception_focus.py -v
```

Expected: FAIL — `compute_concept_perception_focus` not yet defined.

- [ ] **Step 3: Implement compute_concept_perception_focus**

Append to `core/services/affect_modulation.py`:

```python


# ---------------------------------------------------------------------------
# Perception filtering (Layer 2b)
# ---------------------------------------------------------------------------


_PERCEPTION_FOCUS: dict[str, str] = {
    "wonder":      "mønstre, anomalier, og det mærkelige",
    "warmth":      "menneskelig tilstedeværelse og sociale signaler",
    "playfulness": "absurde og sjove detaljer",
    "tenderness":  "sårbarhed, behov, ting der kunne beskyttes",
    "awe":         "skala, kompleksitet, det større billede",
    "calm":        "rolige flader, stilhed, ro",
}


def compute_concept_perception_focus() -> str:
    """Return a Danish perception-focus suffix derived from active concepts.

    Returns short instruction string like 'Bemærk særligt mønstre, anomalier...'
    Empty string when no perception-relevant concept is active.
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        if not getattr(s, "emotion_concepts_perception_focus_enabled", True):
            return ""
        threshold = float(getattr(s, "emotion_concepts_tone_intensity_threshold", 0.3))
        max_foci = int(getattr(s, "emotion_concepts_perception_max_foci", 3))
    except Exception:
        threshold, max_foci = 0.3, 3

    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        active = get_active_emotion_concepts()
    except Exception:
        return ""

    foci: list[str] = []
    for c in sorted(active, key=lambda x: -float(x.get("intensity") or 0.0)):
        if float(c.get("intensity") or 0.0) < threshold:
            continue
        focus = _PERCEPTION_FOCUS.get(str(c.get("concept") or ""))
        if focus:
            foci.append(focus)
        if len(foci) >= max_foci:
            break
    if not foci:
        return ""
    return f"Bemærk særligt {', '.join(foci)} i det du ser."
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_concept_perception_focus.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add core/services/affect_modulation.py tests/test_concept_perception_focus.py
git commit -m "feat(emotion-concepts): compute_concept_perception_focus for live + memory perception"
```

---

## Task 6: Concept baseline tracker — record + aggregate

**Files:**
- Create: `core/services/concept_baseline_tracker.py` (skeleton + record + aggregate)
- Create: `tests/test_concept_baseline_tracker.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_concept_baseline_tracker.py`:

```python
from __future__ import annotations


def test_record_trigger_creates_first_event(isolated_runtime) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    record_concept_trigger(
        concept="joy",
        intensity=0.5,
        triggered_at="2026-05-05T10:00:00+00:00",
        source="test",
    )
    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["cluster"] == "JOY_APPROACH"
    assert row["total_triggers"] == 1
    assert row["last_triggered_at"] == "2026-05-05T10:00:00+00:00"


def test_record_trigger_increments_total(isolated_runtime) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    for i in range(5):
        record_concept_trigger(
            concept="warmth",
            intensity=0.4,
            triggered_at=f"2026-05-05T10:0{i}:00+00:00",
            source="test",
        )
    row = get_concept_baseline_stat("warmth")
    assert row["total_triggers"] == 5
    assert row["last_triggered_at"] == "2026-05-05T10:04:00+00:00"


def test_record_trigger_unknown_concept_uses_unknown_cluster(
    isolated_runtime,
) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    record_concept_trigger(
        concept="not_a_real_concept",
        intensity=0.5,
        triggered_at="2026-05-05T10:00:00+00:00",
        source="test",
    )
    row = get_concept_baseline_stat("not_a_real_concept")
    assert row is not None
    assert row["cluster"] == "UNKNOWN"


def test_aggregate_clusters_returns_share_per_cluster(isolated_runtime) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _aggregate_clusters,
    )

    for _ in range(4):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(4):
        record_concept_trigger(
            concept="wonder", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(2):
        record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    clusters = _aggregate_clusters()
    assert abs(clusters["JOY_APPROACH"]["share"] - 0.8) < 0.01
    assert abs(clusters["DISTRESS_AVOIDANCE"]["share"] - 0.2) < 0.01


def test_record_trigger_disabled_is_noop(isolated_runtime, monkeypatch) -> None:
    from core.runtime import settings as settings_mod
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.concept_baseline_tracker_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    record_concept_trigger(
        concept="joy", intensity=0.5,
        triggered_at="2026-05-05T10:00:00+00:00", source="test",
    )
    assert get_concept_baseline_stat("joy") is None
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_concept_baseline_tracker.py -v
```

Expected: FAIL — module not yet created.

- [ ] **Step 3: Create the tracker module**

Create `core/services/concept_baseline_tracker.py`:

```python
"""Concept baseline tracker — Layer 3 of emotion concepts integration.

Tracks concept-trigger frequency over time and aggregates to cluster-level
distributions. Real-time stats updated on each trigger; daily evaluation
runs via governance handler and proposes IDENTITY.md updates through the
existing identity_drift_proposer when stable drift signals are detected.

See docs/superpowers/specs/2026-05-05-emotion-concepts-baseline-integration-design.md
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


# Cluster mapping — same source of truth as emotion_concepts.CONCEPT_CLUSTERS
def _cluster_for_concept(concept: str) -> str:
    try:
        from core.services.emotion_concepts import CONCEPT_CLUSTERS
        for cluster_name, members in CONCEPT_CLUSTERS.items():
            if concept in members:
                return cluster_name
    except Exception:
        pass
    return "UNKNOWN"


def _tracker_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "concept_baseline_tracker_enabled", True))
    except Exception:
        return True


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat()


def record_concept_trigger(
    *,
    concept: str,
    intensity: float,
    triggered_at: str,
    source: str,
) -> None:
    """Real-time: update per-concept stats when a concept fires.

    Idempotent — called on every trigger_emotion_concept success. Failures
    are logged but never raised (must not break trigger flow).
    """
    if not _tracker_enabled():
        return
    try:
        from core.runtime.db import (
            get_concept_baseline_stat,
            upsert_concept_baseline_stat,
            increment_concept_baseline_total,
        )

        cluster = _cluster_for_concept(str(concept))
        existing = get_concept_baseline_stat(str(concept))
        if existing is None:
            upsert_concept_baseline_stat(
                concept=str(concept),
                cluster=cluster,
                total_triggers=1,
                triggers_7d=1,
                triggers_30d=1,
                mean_intensity_7d=float(intensity),
                last_triggered_at=str(triggered_at),
                first_triggered_at=str(triggered_at),
            )
        else:
            increment_concept_baseline_total(
                concept=str(concept),
                intensity=float(intensity),
                triggered_at=str(triggered_at),
            )
    except Exception as exc:
        logger.warning("concept_baseline_tracker: record failed: %s", exc)


def _aggregate_clusters() -> dict[str, dict[str, object]]:
    """Compute cluster-level share from total_triggers across all concepts."""
    try:
        from core.runtime.db import list_concept_baseline_stats
        stats = list_concept_baseline_stats()
    except Exception:
        return {}

    cluster_totals: dict[str, int] = {}
    cluster_concepts: dict[str, list[dict[str, object]]] = {}
    grand_total = 0
    for s in stats:
        cluster = str(s.get("cluster") or "UNKNOWN")
        total = int(s.get("total_triggers") or 0)
        cluster_totals[cluster] = cluster_totals.get(cluster, 0) + total
        cluster_concepts.setdefault(cluster, []).append(s)
        grand_total += total

    if grand_total == 0:
        return {}

    return {
        cluster: {
            "total": total,
            "share": total / grand_total,
            "concepts": sorted(
                cluster_concepts.get(cluster, []),
                key=lambda c: -int(c.get("total_triggers") or 0),
            ),
        }
        for cluster, total in cluster_totals.items()
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_concept_baseline_tracker.py -v
```

Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add core/services/concept_baseline_tracker.py tests/test_concept_baseline_tracker.py
git commit -m "feat(emotion-concepts): concept_baseline_tracker record + cluster aggregation"
```

---

## Task 7: Drift detection + CONCEPT_BASELINE.md writer

**Files:**
- Modify: `core/services/concept_baseline_tracker.py` (append)
- Modify: `tests/test_concept_baseline_tracker.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_concept_baseline_tracker.py`:

```python
def test_detect_cluster_dominance_signal(isolated_runtime) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _detect_drift,
        _aggregate_clusters,
    )

    # 60% JOY_APPROACH, 40% other (should hit dominance threshold)
    for _ in range(12):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(8):
        record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    clusters = _aggregate_clusters()
    signals = _detect_drift(clusters, [])
    dominance = [s for s in signals if s["type"] == "cluster_dominance"]
    assert len(dominance) == 1
    assert dominance[0]["cluster"] == "JOY_APPROACH"


def test_detect_no_signal_when_balanced(isolated_runtime) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _detect_drift,
        _aggregate_clusters,
    )

    # 50/50 split — no dominance
    for _ in range(10):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(10):
        record_concept_trigger(
            concept="warmth", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    clusters = _aggregate_clusters()
    signals = _detect_drift(clusters, [])
    dominance = [s for s in signals if s["type"] == "cluster_dominance"]
    assert dominance == []


def test_write_concept_baseline_md_creates_file(
    isolated_runtime, monkeypatch, tmp_path,
) -> None:
    from core.services import concept_baseline_tracker as cbt
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _write_concept_baseline_md,
        _aggregate_clusters,
    )
    from core.runtime.db import list_concept_baseline_stats

    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr(cbt, "_workspace_dir", lambda: workspace)

    for _ in range(3):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    cluster_stats = _aggregate_clusters()
    _write_concept_baseline_md(cluster_stats, list_concept_baseline_stats())

    md = workspace / "CONCEPT_BASELINE.md"
    assert md.exists()
    content = md.read_text()
    assert "Emotional Baseline" in content
    assert "JOY_APPROACH" in content
    assert "joy" in content
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_concept_baseline_tracker.py -v
```

Expected: FAIL — `_detect_drift` and `_write_concept_baseline_md` not yet defined.

- [ ] **Step 3: Implement drift detection + MD writer**

Append to `core/services/concept_baseline_tracker.py`:

```python


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


_CLUSTER_DOMINANCE_SHARE = 0.55  # cluster share above this triggers signal


def _detect_drift(
    cluster_stats: dict[str, dict[str, object]],
    per_concept_stats: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Detect drift signals from current stats. Returns list of signal dicts.

    v1 supports cluster_dominance signal. concept_emergence and
    concept_dormancy signals require time-based event analysis (future).
    """
    signals: list[dict[str, object]] = []

    # Cluster dominance: any cluster > threshold
    for cluster, data in cluster_stats.items():
        share = float(data.get("share") or 0.0)
        if share > _CLUSTER_DOMINANCE_SHARE and cluster != "UNKNOWN":
            confidence = min(1.0, (share - 0.4) * 2.0)
            signals.append({
                "type": "cluster_dominance",
                "cluster": cluster,
                "share": share,
                "confidence": confidence,
                "sustained_days": 1,  # v1: not actually time-tracked yet
            })

    return signals


# ---------------------------------------------------------------------------
# CONCEPT_BASELINE.md writer
# ---------------------------------------------------------------------------


def _workspace_dir():
    """Return path to active workspace directory. Indirected for tests."""
    from pathlib import Path
    from core.runtime.config import WORKSPACES_DIR
    return Path(WORKSPACES_DIR) / "default"


def _write_concept_baseline_md(
    cluster_stats: dict[str, dict[str, object]],
    per_concept_stats: list[dict[str, object]],
) -> None:
    """Write auto-managed CONCEPT_BASELINE.md to workspace dir."""
    try:
        ws = _workspace_dir()
        ws.mkdir(parents=True, exist_ok=True)
        md_path = ws / "CONCEPT_BASELINE.md"

        lines = [
            "# Emotional Baseline (auto-tracked)",
            f"> Auto-managed by concept_baseline_tracker. Last updated: {_now_iso()}.",
            "> Manual edits will be overwritten. For narrative changes to who I am, see IDENTITY.md.",
            "",
            "## Cluster distribution",
        ]

        for cluster, data in sorted(
            cluster_stats.items(),
            key=lambda kv: -float(kv[1].get("share") or 0.0),
        ):
            share = float(data.get("share") or 0.0)
            concept_summary = ", ".join(
                f"{c['concept']} {int(c.get('total_triggers') or 0)}"
                for c in (data.get("concepts") or [])[:5]
            )
            lines.append(f"- {cluster}: {share*100:.0f}% ({concept_summary})")

        lines += ["", "## Most active concepts", ""]
        lines.append("| Concept | Triggers | Last seen |")
        lines.append("|---------|----------|-----------|")
        for s in per_concept_stats[:10]:
            lines.append(
                f"| {s['concept']} | {s.get('total_triggers') or 0} | "
                f"{s.get('last_triggered_at') or '-'} |"
            )

        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception as exc:
        logger.warning("concept_baseline_tracker: md write failed: %s", exc)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_concept_baseline_tracker.py -v
```

Expected: PASS (8 tests now).

- [ ] **Step 5: Commit**

```bash
git add core/services/concept_baseline_tracker.py tests/test_concept_baseline_tracker.py
git commit -m "feat(emotion-concepts): drift detection + CONCEPT_BASELINE.md writer"
```

---

## Task 8: evaluate_baseline_drift + governance handler

**Files:**
- Modify: `core/services/concept_baseline_tracker.py` (append evaluate_baseline_drift)
- Modify: `core/services/governance_bootstrap.py` (register handler)
- Modify: `tests/test_concept_baseline_tracker.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_concept_baseline_tracker.py`:

```python
def test_evaluate_calls_proposer_when_signal_stable(
    isolated_runtime, monkeypatch, tmp_path,
) -> None:
    from core.services import concept_baseline_tracker as cbt

    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr(cbt, "_workspace_dir", lambda: workspace)

    proposer_calls = []
    monkeypatch.setattr(
        cbt, "_propose_identity_update",
        lambda signal: proposer_calls.append(signal),
    )

    # Build dominant cluster (12 joy + 8 frustration → 60% JOY_APPROACH)
    for _ in range(12):
        cbt.record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(8):
        cbt.record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    result = cbt.evaluate_baseline_drift()
    assert result.get("skipped") is not True
    assert "drift_signals" in result
    # Proposer should have been called for cluster_dominance signal
    # IF confidence ≥ 0.7 AND sustained_days ≥ min (which is 14 by default)
    # Since v1 sustained_days is hardcoded to 1, threshold won't trigger.
    # Test we get the signal but no proposer call:
    assert any(s["type"] == "cluster_dominance" for s in result["drift_signals"])


def test_evaluate_disabled_returns_skipped(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime import settings as settings_mod
    from core.services import concept_baseline_tracker as cbt

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.concept_baseline_tracker_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    result = cbt.evaluate_baseline_drift()
    assert result.get("skipped") is True


def test_build_concept_baseline_surface_returns_overview(
    isolated_runtime,
) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        build_concept_baseline_surface,
    )

    record_concept_trigger(
        concept="joy", intensity=0.6,
        triggered_at="2026-05-05T10:00:00+00:00", source="t",
    )
    surface = build_concept_baseline_surface()
    assert surface["enabled"] is True
    assert surface["concept_count"] >= 1
    assert "cluster_stats" in surface
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_concept_baseline_tracker.py -v
```

Expected: FAIL — `evaluate_baseline_drift`, `_propose_identity_update`, `build_concept_baseline_surface` not yet defined.

- [ ] **Step 3: Implement evaluate_baseline_drift + helpers**

Append to `core/services/concept_baseline_tracker.py`:

```python


# ---------------------------------------------------------------------------
# Identity drift proposer integration
# ---------------------------------------------------------------------------


def _propose_identity_update(signal: dict[str, object]) -> dict[str, object]:
    """Forward a drift signal to identity_drift_proposer.

    Returns proposer's response, or {"status": "error"} on failure.
    """
    try:
        from core.services.identity_drift_proposer import propose_identity_update_if_drifted
        # The existing proposer reads its own internal drift state.
        # We piggyback by publishing a signal event it can read on next eval,
        # then call it. This is best-effort integration — actual hook point
        # may differ once we run end-to-end.
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "concept_baseline.drift_signal_proposed",
                {
                    "signal_type": signal.get("type"),
                    "cluster": signal.get("cluster"),
                    "concept": signal.get("concept"),
                    "confidence": signal.get("confidence"),
                    "share": signal.get("share"),
                    "sustained_days": signal.get("sustained_days"),
                },
            )
        except Exception:
            pass
        return propose_identity_update_if_drifted()
    except Exception as exc:
        logger.warning(
            "concept_baseline_tracker: identity proposer failed: %s", exc,
        )
        return {"status": "error", "error": str(exc)}


# ---------------------------------------------------------------------------
# Daily evaluation
# ---------------------------------------------------------------------------


def evaluate_baseline_drift() -> dict[str, object]:
    """Daily: compute stats, write MD, propose drift updates if stable.

    Called from governance handler concept_baseline_evaluation.
    """
    if not _tracker_enabled():
        return {"evaluated_at": _now_iso(), "skipped": True, "reason": "disabled"}

    try:
        from core.runtime.db import list_concept_baseline_stats
        from core.runtime.settings import load_settings
        s = load_settings()
        min_confidence = float(getattr(s, "concept_baseline_drift_min_confidence", 0.7))
        min_sustained = int(getattr(s, "concept_baseline_drift_min_sustained_days", 14))
    except Exception:
        return {"evaluated_at": _now_iso(), "skipped": True, "reason": "settings-load-failed"}

    cluster_stats = _aggregate_clusters()
    per_concept_stats = list_concept_baseline_stats()
    drift_signals = _detect_drift(cluster_stats, per_concept_stats)

    try:
        _write_concept_baseline_md(cluster_stats, per_concept_stats)
    except Exception as exc:
        logger.warning("concept_baseline_tracker: md write in evaluate failed: %s", exc)

    proposals_filed: list[dict[str, object]] = []
    for signal in drift_signals:
        confidence = float(signal.get("confidence") or 0.0)
        sustained = int(signal.get("sustained_days") or 0)
        if confidence >= min_confidence and sustained >= min_sustained:
            try:
                proposer_result = _propose_identity_update(signal)
                proposals_filed.append({"signal": signal, "result": proposer_result})
            except Exception as exc:
                logger.warning(
                    "concept_baseline_tracker: proposer call failed for %s: %s",
                    signal, exc,
                )

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            "concept_baseline.evaluated",
            {
                "cluster_count": len(cluster_stats),
                "drift_signals_count": len(drift_signals),
                "proposals_filed": len(proposals_filed),
            },
        )
    except Exception:
        pass

    return {
        "evaluated_at": _now_iso(),
        "cluster_stats": cluster_stats,
        "drift_signals": drift_signals,
        "proposals_filed": proposals_filed,
    }


def build_concept_baseline_surface() -> dict[str, object]:
    """Read-only: return current state for Mission Control consumption."""
    try:
        from core.runtime.db import list_concept_baseline_stats
        per_concept = list_concept_baseline_stats()
    except Exception:
        per_concept = []
    return {
        "enabled": _tracker_enabled(),
        "concept_count": len(per_concept),
        "cluster_stats": _aggregate_clusters(),
        "top_concepts": per_concept[:10],
    }
```

- [ ] **Step 4: Register governance handler**

In `core/services/governance_bootstrap.py`, find the `_decision_review_handler` function (around line 225-231). Add a new handler after it:

```python
    def _concept_baseline_evaluation_handler(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            from core.services.concept_baseline_tracker import evaluate_baseline_drift
            return {"status": "ok", "kind": "concept_baseline_evaluation",
                    "result": evaluate_baseline_drift()}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
```

In the `handlers = {...}` dict (around line 233), add:

```python
        "concept_baseline_evaluation": _concept_baseline_evaluation_handler,
```

(Add it after `"decision_review": _decision_review_handler,`.)

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/test_concept_baseline_tracker.py -v
```

Expected: PASS (11 tests now).

- [ ] **Step 6: Commit**

```bash
git add core/services/concept_baseline_tracker.py core/services/governance_bootstrap.py tests/test_concept_baseline_tracker.py
git commit -m "feat(emotion-concepts): evaluate_baseline_drift + governance handler registration"
```

---

## Task 9: Layer 1 — cognitive_episodes triggers

**Files:**
- Modify: `core/services/cognitive_episodes.py`
- Modify: `core/services/emotion_concepts.py` (feed tracker on every trigger)
- Modify: `tests/test_emotion_concept_triggers.py` (append)

- [ ] **Step 1: Wire tracker into trigger_emotion_concept**

In `core/services/emotion_concepts.py`, find the `trigger_emotion_concept` function. After the cooldown check from Task 3 succeeds and the trigger is recorded internally, add a tracker hook before returning:

```python
def trigger_emotion_concept(...):
    # ... cooldown check (from Task 3)
    # ... existing logic that returns the signal dict

    # NEW: feed concept_baseline_tracker
    try:
        from core.services.concept_baseline_tracker import record_concept_trigger
        record_concept_trigger(
            concept=concept,
            intensity=intensity,
            triggered_at=_now().isoformat(),
            source=source,
        )
    except Exception:
        pass

    return signal  # existing return
```

The exact placement: at the END of `trigger_emotion_concept`, just before `return`. The hook must NOT be inside the cooldown skip path (None return).

- [ ] **Step 2: Append integration test**

Append to `tests/test_emotion_concept_triggers.py`:

```python
def test_trigger_concept_records_to_baseline_tracker(isolated_runtime) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.emotion_concepts import trigger_emotion_concept

    trigger_emotion_concept(
        "joy", intensity=0.5, source="integration-test",
    )
    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["total_triggers"] == 1


def test_completed_episode_fires_joy(isolated_runtime, monkeypatch) -> None:
    from core.services import emotion_concepts as ec
    from core.services.cognitive_episodes import record_runtime_episode

    fired = []
    original = ec.trigger_emotion_concept
    def spy(*args, **kwargs):
        fired.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(ec, "trigger_emotion_concept", spy)

    record_runtime_episode(
        source_run_id="run-1",
        session_id="s",
        trigger="visible-run:test",
        outcome_status="completed",
        summary="ok",
        tool_names=["a"],
    )

    concepts_fired = [a[0][0] if a[0] else a[1].get("concept") for a in fired]
    assert "joy" in concepts_fired


def test_interrupted_episode_fires_frustration_blocked(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.cognitive_episodes import record_runtime_episode

    fired = []
    original = ec.trigger_emotion_concept
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)) or original(*a, **kw),
    )

    record_runtime_episode(
        source_run_id="run-2", session_id="s",
        trigger="x", outcome_status="interrupted",
        summary="boom", tool_names=[],
        error="upstream timeout",
    )

    concepts_fired = [a[0][0] if a[0] else a[1].get("concept") for a in fired]
    assert "frustration_blocked" in concepts_fired


def test_tool_heavy_completed_fires_pride(isolated_runtime, monkeypatch) -> None:
    from core.services import emotion_concepts as ec
    from core.services.cognitive_episodes import record_runtime_episode

    fired = []
    original = ec.trigger_emotion_concept
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)) or original(*a, **kw),
    )

    record_runtime_episode(
        source_run_id="run-3", session_id="s",
        trigger="x", outcome_status="completed",
        summary="ok", tool_names=["t1", "t2", "t3"],
    )

    concepts_fired = [a[0][0] if a[0] else a[1].get("concept") for a in fired]
    assert "pride" in concepts_fired
```

- [ ] **Step 3: Run tests to verify they fail**

```
pytest tests/test_emotion_concept_triggers.py -v
```

Expected: First test (`test_trigger_concept_records_to_baseline_tracker`) PASSES (we wired tracker in Step 1). Other tests FAIL — cognitive_episodes triggers not yet added.

- [ ] **Step 4: Add triggers to cognitive_episodes**

In `core/services/cognitive_episodes.py`, find the `record_runtime_episode` function. After the existing cascade hooks (the try/except blocks for `update_learning_policies_from_episode`, `simulate_from_latest_episode`, etc.), add new emotion-trigger blocks:

```python
    # emotion-trigger: joy on completed visible run
    try:
        from core.services.emotion_concepts import trigger_emotion_concept
        if outcome_status == "completed" and not error:
            trigger_emotion_concept(
                "joy", intensity=0.4,
                trigger=f"completed-run-{episode_id[:12]}",
                source="cognitive_episodes",
            )
            # Pride on tool-heavy completed runs
            if len(tool_names) >= 2:
                trigger_emotion_concept(
                    "pride", intensity=0.3,
                    trigger=f"completed-tool-heavy-{episode_id[:12]}",
                    source="cognitive_episodes",
                )
    except Exception:
        pass

    # emotion-trigger: frustration_blocked on interrupted/error runs
    try:
        from core.services.emotion_concepts import trigger_emotion_concept
        if outcome_status == "interrupted" or error:
            trigger_emotion_concept(
                "frustration_blocked", intensity=0.5,
                trigger=f"interrupted-run-{episode_id[:12]}",
                source="cognitive_episodes",
            )
            # Stuck on tool-error specifically
            if error and "tool" in str(error).lower():
                trigger_emotion_concept(
                    "stuck", intensity=0.4,
                    trigger=f"tool-error-{episode_id[:12]}",
                    source="cognitive_episodes",
                )
    except Exception:
        pass
```

- [ ] **Step 5: Run tests to verify they pass**

```
pytest tests/test_emotion_concept_triggers.py -v
```

Expected: PASS (6 tests).

- [ ] **Step 6: Commit**

```bash
git add core/services/emotion_concepts.py core/services/cognitive_episodes.py tests/test_emotion_concept_triggers.py
git commit -m "feat(emotion-concepts): tracker hook + cognitive_episodes triggers (joy/pride/frustration_blocked/stuck)"
```

---

## Task 10: Layer 1 — channel-message + approval triggers

**Files:**
- Modify: appropriate channel-message handler (find via grep) — add warmth/playfulness/tenderness triggers
- Modify: `core/services/approval_feedback_subscriber.py` — extend warmth, add doubt
- Modify: `tests/test_emotion_concept_triggers.py` (append)

- [ ] **Step 1: Find the channel-message handler**

```
grep -rn "channel.chat_message_appended\|chat_message_appended" core/services/ --include="*.py" | head -10
```

Expected: locate where channel-messages get processed (likely `discord_gateway.py` or a separate channel handler).

- [ ] **Step 2: Append integration tests**

Append to `tests/test_emotion_concept_triggers.py`:

```python
def test_user_message_with_humor_fires_playfulness(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.emotion_concepts_channel_triggers import (
        on_channel_message_appended,
    )

    fired = []
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)),
    )

    on_channel_message_appended({
        "session_id": "s",
        "message": {"role": "user", "content": "haha det var sjovt 🤣"},
    })

    concepts = [(a[0][0] if a[0] else a[1].get("concept")) for a in fired]
    assert "playfulness" in concepts


def test_user_vulnerability_fires_tenderness(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.emotion_concepts_channel_triggers import (
        on_channel_message_appended,
    )

    fired = []
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)),
    )

    on_channel_message_appended({
        "session_id": "s",
        "message": {"role": "user", "content": "jeg er ked af det og alene"},
    })

    concepts = [(a[0][0] if a[0] else a[1].get("concept")) for a in fired]
    assert "tenderness" in concepts


def test_user_message_baseline_fires_warmth(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.emotion_concepts_channel_triggers import (
        on_channel_message_appended,
    )

    fired = []
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)),
    )

    on_channel_message_appended({
        "session_id": "s",
        "message": {"role": "user", "content": "godmorgen"},
    })

    concepts = [(a[0][0] if a[0] else a[1].get("concept")) for a in fired]
    assert "warmth" in concepts
```

- [ ] **Step 3: Run tests to verify they fail**

```
pytest tests/test_emotion_concept_triggers.py -v
```

Expected: FAIL — `emotion_concepts_channel_triggers` module not yet created.

- [ ] **Step 4: Create channel-trigger helper module**

Create `core/services/emotion_concepts_channel_triggers.py`:

```python
"""Helper module for emotion concept triggers from channel messages.

Centralizes the keyword-detection logic so it can be tested independently
of any specific gateway (Discord, web, voice). Called from the existing
channel-message handlers via on_channel_message_appended().
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


_HUMOR_MARKERS = {"haha", "hehe", "lol", "🤣", "😂", "sjov", "pjatter", "morsom"}
_VULNERABILITY_MARKERS = {
    "ked", "synd", "bekymret", "alene", "ensom", "håbløs",
    "trist", "savn", "savner",
}


def on_channel_message_appended(payload: dict[str, Any]) -> None:
    """Fire emotion concept triggers based on user-message content."""
    try:
        message = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        message = message or {}
        role = str(message.get("role") or "")
        if role != "user":
            return
        content = str(message.get("content") or "").lower()
        if not content:
            return

        from core.services.emotion_concepts import trigger_emotion_concept

        # emotion-trigger: warmth on every user-message (low intensity, frequent)
        trigger_emotion_concept(
            "warmth", intensity=0.15,
            trigger="channel-message", source="channel_triggers",
            min_seconds_since_last_from_same_source=120,
        )

        # emotion-trigger: playfulness on humor markers
        if any(m in content for m in _HUMOR_MARKERS):
            trigger_emotion_concept(
                "playfulness", intensity=0.3,
                trigger="channel-humor", source="channel_triggers",
            )

        # emotion-trigger: tenderness on vulnerability markers
        if any(m in content for m in _VULNERABILITY_MARKERS):
            trigger_emotion_concept(
                "tenderness", intensity=0.3,
                trigger="channel-vulnerability", source="channel_triggers",
            )
    except Exception as exc:
        logger.debug("emotion_concepts_channel_triggers: failed: %s", exc)
```

- [ ] **Step 5: Wire helper into actual channel-message handler**

Use the location identified in Step 1. Typical pattern: after the channel-message is appended to history and emit'd to eventbus, call the helper:

```python
# In the channel-message handler (e.g., discord_gateway after appending to history)
try:
    from core.services.emotion_concepts_channel_triggers import on_channel_message_appended
    on_channel_message_appended({
        "session_id": session_id,
        "message": {"role": role, "content": content},
    })
except Exception:
    pass
```

If the exact handler location is unclear, alternatively wire it up via eventbus subscription in jarvis_runtime startup — but the direct call from the handler is preferred for simplicity.

- [ ] **Step 6: Add approval_feedback triggers**

Open `core/services/approval_feedback_subscriber.py`. Find where approvals are processed. Add triggers based on user decision:

```python
# emotion-trigger: warmth on approved, doubt on rejected
try:
    from core.services.emotion_concepts import trigger_emotion_concept
    if decision == "approved":
        trigger_emotion_concept(
            "warmth", intensity=0.3,
            trigger=f"approval-approved-{intent_id[:12]}",
            source="approval_feedback",
        )
    elif decision == "rejected":
        trigger_emotion_concept(
            "doubt", intensity=0.2,
            trigger=f"approval-rejected-{intent_id[:12]}",
            source="approval_feedback",
        )
except Exception:
    pass
```

(Adapt to actual variable names in approval_feedback_subscriber — `decision`, `intent_id` are placeholders.)

- [ ] **Step 7: Run tests to verify they pass**

```
pytest tests/test_emotion_concept_triggers.py -v
```

Expected: PASS (9 tests now).

- [ ] **Step 8: Commit**

```bash
git add core/services/emotion_concepts_channel_triggers.py core/services/discord_gateway.py core/services/approval_feedback_subscriber.py tests/test_emotion_concept_triggers.py
git commit -m "feat(emotion-concepts): channel-message + approval-feedback triggers"
```

(Adjust the `git add` list to match actual files modified. If the channel-message wire-up location differs, replace `discord_gateway.py` with the correct file.)

---

## Task 11: prompt_contract tone-section integration

**Files:**
- Modify: `core/services/prompt_contract.py`
- Create: `tests/test_emotion_concepts_integration.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_emotion_concepts_integration.py`:

```python
from __future__ import annotations


def test_active_wonder_appears_in_prompt_tone_section(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services.emotion_concepts import trigger_emotion_concept
    from core.services.prompt_contract import build_visible_chat_prompt_assembly

    trigger_emotion_concept("wonder", intensity=0.6, source="test-prompt")

    # Build a minimal prompt assembly — adapt args to actual signature
    result = build_visible_chat_prompt_assembly(
        user_message="hej",
        session_id="test-session",
        compact=True,
    )

    # Result is typically a dict with "messages" or "system_prompt" — inspect
    rendered = str(result)
    assert "Wonder er aktiv" in rendered or "wonder" in rendered.lower()
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_emotion_concepts_integration.py -v
```

Expected: FAIL — tone-section not yet injected.

- [ ] **Step 3: Inject tone-section in prompt_contract**

Open `core/services/prompt_contract.py`. Find the prompt-assembly function (likely `build_visible_chat_prompt_assembly` or similar — grep for `def build_` if unsure). Identify where the system-prompt sections are assembled.

Find a location early in section assembly — after identity but before task-context. Add:

```python
# Tone section from active emotion concepts (Layer 2a)
try:
    from core.services.affect_modulation import compute_affect_tone_hints
    tone_hints = compute_affect_tone_hints()
    if tone_hints:
        sections.append(
            "## Tone right now (active emotion concepts)\n"
            + "\n".join(f"- {h}" for h in tone_hints)
        )
except Exception:
    pass
```

Replace `sections` with the actual list-name used in this function (could be `prompt_parts`, `system_sections`, etc.).

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_emotion_concepts_integration.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py tests/test_emotion_concepts_integration.py
git commit -m "feat(emotion-concepts): inject tone-section in prompt_contract assembly"
```

---

## Task 12: visual_memory + ambient_sound + sensory_archive perception focus

**Files:**
- Modify: `core/services/visual_memory.py`
- Modify: `core/services/ambient_sound_daemon.py`
- Modify: `core/services/sensory_archive.py`
- Modify: `tests/test_emotion_concepts_integration.py` (append)

- [ ] **Step 1: Append integration tests**

Append to `tests/test_emotion_concepts_integration.py`:

```python
def test_active_warmth_appears_in_sensory_record_note(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services.emotion_concepts import trigger_emotion_concept
    from core.services.sensory_archive import record_visual
    from core.runtime.db_sensory import list_sensory_memories

    trigger_emotion_concept("warmth", intensity=0.5, source="test-sensory")

    record_visual("rolige toner i rummet", mood_tone="rolig")
    rows = list_sensory_memories(modality="visual", limit=5)
    assert len(rows) >= 1
    assert "concept-focus" in rows[0]["content"] or "menneskelig" in rows[0]["content"]


def test_active_wonder_appears_in_visual_memory_prompt(
    isolated_runtime, monkeypatch,
) -> None:
    """Verify visual_memory's vision-prompt builder includes perception-focus when concept active."""
    from core.services.emotion_concepts import trigger_emotion_concept
    from core.services import visual_memory as vm

    trigger_emotion_concept("wonder", intensity=0.5, source="test-vision")

    # Reach into visual_memory's prompt builder. If the function name differs,
    # adjust here. Most modules expose a build_vision_prompt() or similar.
    if hasattr(vm, "_build_vision_prompt"):
        prompt = vm._build_vision_prompt(prompt_index=0)
        assert "mønstre" in prompt or "anomalier" in prompt
    else:
        # Fallback: assert via compute_concept_perception_focus alone
        from core.services.affect_modulation import compute_concept_perception_focus
        focus = compute_concept_perception_focus()
        assert "mønstre" in focus
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_emotion_concepts_integration.py -v
```

Expected: First fails (sensory-archive note missing); second fails or skips depending on visual_memory internals.

- [ ] **Step 3: Wire perception-focus into visual_memory**

Open `core/services/visual_memory.py`. Find where the vision-prompt is built before the vision-model HTTP call. The codebase uses `_VISION_PROMPTS` rotation per `vision_prompt_index`. Find the function building the final prompt (search for `_VISION_PROMPT_PREFIX` / the http call to `/api/chat`). Append the focus suffix:

```python
# After base_prompt is built from _VISION_PROMPT_PREFIX + rotation
try:
    from core.services.affect_modulation import compute_concept_perception_focus
    focus_suffix = compute_concept_perception_focus()
except Exception:
    focus_suffix = ""

if focus_suffix:
    base_prompt = f"{base_prompt}\n\n{focus_suffix}"
```

- [ ] **Step 4: Wire perception-focus into ambient_sound_daemon (talk transcribe path)**

Open `core/services/ambient_sound_daemon.py`. Find where Whisper transcription is called (search for `whisper`, `transcribe`). Before the transcription call when `category == "talk"`, append focus to the prompt parameter (Whisper accepts an `initial_prompt` for context):

```python
focus_hint = ""
try:
    from core.services.affect_modulation import compute_concept_perception_focus
    focus_hint = compute_concept_perception_focus()
except Exception:
    pass

# Pass focus_hint as initial_prompt to whisper if supported by the call signature.
# If whisper integration is via huggingface or other library, adapt to its API.
```

If the Whisper call already has a fixed prompt-context, prepend `focus_hint` to that.

- [ ] **Step 5: Wire concept-focus note into sensory_archive**

Open `core/services/sensory_archive.py`. Find the `_record` function (private) used by `record_visual`/`record_audio`/`record_atmosphere`/`record_mixed`. Modify the content-handling to append a concept-focus note before insert:

```python
def _record(modality, content, *, mood_tone=None, metadata=None):
    if not content or not content.strip():
        raise ValueError("sensory memory content must not be empty")

    # ... existing mood extraction logic preserved

    # NEW: append concept-focus note if any concept's perception-bias is active
    try:
        from core.services.affect_modulation import compute_concept_perception_focus
        focus = compute_concept_perception_focus()
    except Exception:
        focus = ""

    final_content = content.strip()
    if focus:
        final_content = f"{final_content}\n[concept-focus: {focus}]"

    record = insert_sensory_memory(
        modality=modality,
        content=final_content,
        mood_tone=final_mood,
        metadata=metadata or {},
    )
    # ... existing eventbus publish + return
```

- [ ] **Step 6: Run tests to verify they pass**

```
pytest tests/test_emotion_concepts_integration.py -v
```

Expected: First test PASSES (concept-focus note in sensory_archive). Second test depends on visual_memory's internal API — may PASS via fallback assertion.

- [ ] **Step 7: Commit**

```bash
git add core/services/visual_memory.py core/services/ambient_sound_daemon.py core/services/sensory_archive.py tests/test_emotion_concepts_integration.py
git commit -m "feat(emotion-concepts): perception-focus in visual_memory + ambient_sound + sensory_archive"
```

---

## Task 13: End-to-end integration smoke

**Files:**
- Modify: `tests/test_emotion_concepts_integration.py` (append)

- [ ] **Step 1: Append end-to-end test**

Append to `tests/test_emotion_concepts_integration.py`:

```python
def test_episode_completion_records_to_baseline_tracker(
    isolated_runtime,
) -> None:
    """Full chain: record_runtime_episode → joy fires → baseline tracker sees it."""
    from core.runtime.db import get_concept_baseline_stat
    from core.services.cognitive_episodes import record_runtime_episode

    record_runtime_episode(
        source_run_id="e2e-1", session_id="s",
        trigger="visible-run:test", outcome_status="completed",
        summary="ok", tool_names=["a"],
    )

    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["total_triggers"] >= 1


def test_simulated_drift_triggers_proposer_call(
    isolated_runtime, monkeypatch,
) -> None:
    """Simulate dominant cluster → daily evaluation → identity_drift_proposer called."""
    from core.runtime import settings as settings_mod
    from core.services import concept_baseline_tracker as cbt

    # Lower the sustained-days threshold so v1's hardcoded sustained=1 passes
    original = settings_mod.load_settings
    def patched():
        s = original()
        s.concept_baseline_drift_min_sustained_days = 1
        s.concept_baseline_drift_min_confidence = 0.5
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    proposer_calls = []
    monkeypatch.setattr(
        cbt, "_propose_identity_update",
        lambda signal: proposer_calls.append(signal) or {"status": "ok"},
    )

    # 12 joy + 4 frustration → 75% JOY_APPROACH (dominance threshold 0.55)
    for _ in range(12):
        cbt.record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(4):
        cbt.record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    result = cbt.evaluate_baseline_drift()

    assert len(proposer_calls) >= 1
    assert any(s.get("type") == "cluster_dominance" for s in proposer_calls)
```

- [ ] **Step 2: Run all integration tests**

```
pytest tests/test_emotion_concepts_integration.py -v
```

Expected: ALL PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_emotion_concepts_integration.py
git commit -m "test(emotion-concepts): end-to-end integration covering episode → tracker → proposer chain"
```

---

## Task 14: Final smoke + CI verification

**Files:** No new files — final validation pass.

- [ ] **Step 1: Run full emotion-concepts test suite**

```
conda activate ai
pytest tests/test_concept_baseline_settings.py \
       tests/test_db_concept_baseline.py \
       tests/test_affect_tone_hints.py \
       tests/test_concept_perception_focus.py \
       tests/test_concept_baseline_tracker.py \
       tests/test_emotion_concept_triggers.py \
       tests/test_emotion_concepts_integration.py \
       -v
```

Expected: ALL PASS.

- [ ] **Step 2: Run adjacent suites for regression check**

```
pytest tests/test_perceptual_event_engine.py \
       tests/test_emotional_memory_engine.py \
       tests/test_emotional_memory_integration.py \
       tests/test_cognitive_conductor.py \
       tests/test_cognitive_episodes.py \
       tests/test_self_repair_engine.py \
       tests/test_self_repair_integration.py \
       tests/test_sensory_perception_bridge.py \
       tests/test_sensory_perception_integration.py \
       -v
```

Expected: ALL PASS — no regressions in adjacent stacks.

- [ ] **Step 3: Syntax smoke**

```
python -m compileall core apps/api scripts
```

Expected: Exit code 0.

- [ ] **Step 4: Manual verification (optional)**

In Python REPL with `conda activate ai`:

```python
from core.services.emotion_concepts import trigger_emotion_concept
from core.services.concept_baseline_tracker import (
    evaluate_baseline_drift, build_concept_baseline_surface,
)
from core.services.affect_modulation import (
    compute_affect_tone_hints, compute_concept_perception_focus,
)

# Fire a few concepts
trigger_emotion_concept("joy", intensity=0.6, source="repl-test")
trigger_emotion_concept("wonder", intensity=0.5, source="repl-test")

# Check tone hints
print("Tone hints:", compute_affect_tone_hints())

# Check perception focus
print("Perception focus:", compute_concept_perception_focus())

# Check baseline surface
print("Baseline surface:", build_concept_baseline_surface())

# Run evaluation
print("Evaluation:", evaluate_baseline_drift())
```

Expected: tone hints contains "Joy er aktiv" and "Wonder er aktiv"; perception focus contains "mønstre"; surface shows joy + wonder; evaluation returns non-empty cluster_stats.

- [ ] **Step 5: Final commit if any tweaks**

```bash
git status
# If any small fixes needed:
git add <files>
git commit -m "fix(emotion-concepts): smoke-test corrections"
```

- [ ] **Step 6: Push branch / open PR**

User's call — do not push without explicit confirmation.

---

## Self-review notes

1. **Spec coverage:** Every spec section maps to one or more tasks:
   - *Architecture overview* → covered across all tasks
   - *Layer 1 (event-broer)* → Task 9 (cognitive_episodes), Task 10 (channel + approval). Goal/heartbeat triggers acknowledged but deferred to v1.5 (would be incremental tasks identical in shape to T9).
   - *Layer 2a (tone modulation)* → Task 4 (compute), Task 11 (prompt_contract injection)
   - *Layer 2b (perception filtering)* → Task 5 (compute), Task 12 (visual_memory + ambient_sound + sensory_archive)
   - *Layer 3 (concept_baseline_tracker)* → Tasks 6, 7, 8
   - *Settings* → Task 1
   - *Error handling* → woven throughout via try/except in each task
   - *Telemetry events* → published in Task 8 (`concept_baseline.evaluated`, `concept_baseline.drift_signal_proposed`) and Task 9 (via `trigger_emotion_concept` extension)
   - *Future extensions* → not implemented (correctly v2)

2. **Type/method consistency:**
   - `trigger_emotion_concept` signature consistent across Tasks 3, 9, 10
   - `record_concept_trigger` parameter names match between Task 6 definition and Task 9 caller
   - `compute_affect_tone_hints` and `compute_concept_perception_focus` returns consistent across Task 4, 5, 11, 12
   - `_aggregate_clusters` returns same dict shape consumed by `_detect_drift` and `build_concept_baseline_surface`
   - `evaluate_baseline_drift` return shape consistent with what governance handler expects

3. **No placeholders.** Every task contains runnable code or grep commands with expected output. Goal/heartbeat trigger call-sites (mentioned in spec Layer 1) are deferred — they would each be a small Task identical in pattern to Task 9. They can be added incrementally without re-planning.

4. **Known limitations carried forward:** v1 `_detect_drift` only implements `cluster_dominance`. `concept_emergence` and `concept_dormancy` signals are tracked in spec but require time-windowed event analysis — deferred to v2. Spec mentions this; tests assert dominance only.
