# Sensory Perception Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bridge sensory archive records (visual/audio/atmosphere/mixed from webcam, ambient sound, etc.) into perceptual_event_engine as first-class perceptual events when change-detection identifies meaningful shifts vs baseline.

**Architecture:** New module `core/services/sensory_perception_bridge.py` exposes `classify_sensory_change(event)`. Engine's `classify_event_change` adds a single delegation branch for `memory.sensory.recorded` events. Differentiated baseline strategy: time-of-day window for visual+audio (with recent-baseline fallback), recent-baseline only for atmosphere+mixed. Combined heuristic detects change (mood_tone shift OR Jaccard < 0.4 OR metadata change). Salience mapped from change magnitude.

**Tech Stack:** Python 3.11+, SQLite via existing `sensory_archive`/`db_sensory`, eventbus, `isolated_runtime` test fixture.

**Spec:** `docs/superpowers/specs/2026-05-04-sensory-perception-bridge-design.md`

---

## File Structure

**Create:**
- `core/services/sensory_perception_bridge.py` — bridge module (~400 lines)
- `tests/test_sensory_perception_bridge.py` — unit tests
- `tests/test_sensory_perception_integration.py` — end-to-end integration tests

**Modify:**
- `core/runtime/settings.py` — add 8 new sensory_perception_* fields
- `core/services/perceptual_event_engine.py` — add one new event-kind branch in `classify_event_change`

---

## Task 1: RuntimeSettings fields

**Files:**
- Modify: `core/runtime/settings.py`
- Test: `tests/test_sensory_perception_settings.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sensory_perception_settings.py`:

```python
from __future__ import annotations


def test_sensory_perception_settings_have_defaults(isolated_runtime) -> None:
    from core.runtime.settings import load_settings

    settings = load_settings()
    assert settings.sensory_perception_bridge_enabled is True
    assert settings.sensory_perception_jaccard_high_threshold == 0.15
    assert settings.sensory_perception_jaccard_medium_threshold == 0.25
    assert settings.sensory_perception_jaccard_change_threshold == 0.4
    assert settings.sensory_perception_time_window_hours == 2
    assert settings.sensory_perception_time_window_days == 7
    assert settings.sensory_perception_min_baseline_records == 3
    assert settings.sensory_perception_recent_baseline_size == 3
```

- [ ] **Step 2: Run test to verify it fails**

```
conda activate ai
pytest tests/test_sensory_perception_settings.py -v
```

Expected: FAIL with `AttributeError: ... has no attribute 'sensory_perception_bridge_enabled'`

- [ ] **Step 3: Add fields to RuntimeSettings dataclass**

In `core/runtime/settings.py`, find the section ending with the emotional_memory fields (added in previous PR) and add the 8 new fields right after them, before `extra: dict[str, Any] = field(default_factory=dict)`:

```python
    # Sensory perception bridge — change detection thresholds.
    sensory_perception_bridge_enabled: bool = True
    sensory_perception_jaccard_high_threshold: float = 0.15
    sensory_perception_jaccard_medium_threshold: float = 0.25
    sensory_perception_jaccard_change_threshold: float = 0.4
    sensory_perception_time_window_hours: int = 2
    sensory_perception_time_window_days: int = 7
    sensory_perception_min_baseline_records: int = 3
    sensory_perception_recent_baseline_size: int = 3
```

- [ ] **Step 4: Add to to_dict()**

In `to_dict()`, after `"emotional_memory_significance_outcome": self.emotional_memory_significance_outcome,`, add:

```python
            "sensory_perception_bridge_enabled": self.sensory_perception_bridge_enabled,
            "sensory_perception_jaccard_high_threshold": self.sensory_perception_jaccard_high_threshold,
            "sensory_perception_jaccard_medium_threshold": self.sensory_perception_jaccard_medium_threshold,
            "sensory_perception_jaccard_change_threshold": self.sensory_perception_jaccard_change_threshold,
            "sensory_perception_time_window_hours": self.sensory_perception_time_window_hours,
            "sensory_perception_time_window_days": self.sensory_perception_time_window_days,
            "sensory_perception_min_baseline_records": self.sensory_perception_min_baseline_records,
            "sensory_perception_recent_baseline_size": self.sensory_perception_recent_baseline_size,
```

- [ ] **Step 5: Add to load_settings()**

In `load_settings()`, after the `emotional_memory_*` block (just before `extra={...}`), add:

```python
        sensory_perception_bridge_enabled=bool(data.get("sensory_perception_bridge_enabled", defaults.sensory_perception_bridge_enabled)),
        sensory_perception_jaccard_high_threshold=float(data.get("sensory_perception_jaccard_high_threshold", defaults.sensory_perception_jaccard_high_threshold)),
        sensory_perception_jaccard_medium_threshold=float(data.get("sensory_perception_jaccard_medium_threshold", defaults.sensory_perception_jaccard_medium_threshold)),
        sensory_perception_jaccard_change_threshold=float(data.get("sensory_perception_jaccard_change_threshold", defaults.sensory_perception_jaccard_change_threshold)),
        sensory_perception_time_window_hours=int(data.get("sensory_perception_time_window_hours", defaults.sensory_perception_time_window_hours)),
        sensory_perception_time_window_days=int(data.get("sensory_perception_time_window_days", defaults.sensory_perception_time_window_days)),
        sensory_perception_min_baseline_records=int(data.get("sensory_perception_min_baseline_records", defaults.sensory_perception_min_baseline_records)),
        sensory_perception_recent_baseline_size=int(data.get("sensory_perception_recent_baseline_size", defaults.sensory_perception_recent_baseline_size)),
```

- [ ] **Step 6: Run test to verify it passes**

```
pytest tests/test_sensory_perception_settings.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add core/runtime/settings.py tests/test_sensory_perception_settings.py
git commit -m "feat(sensory-perception): runtime settings for bridge thresholds"
```

---

## Task 2: Pure helpers — shingle, jaccard, mode

**Files:**
- Create: `core/services/sensory_perception_bridge.py` (skeleton + helpers)
- Create: `tests/test_sensory_perception_bridge.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_sensory_perception_bridge.py`:

```python
from __future__ import annotations


def test_shingle_returns_word_ngrams(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _shingle

    tokens = _shingle("the quick brown fox", n=3)
    assert "the quick brown" in tokens
    assert "quick brown fox" in tokens
    assert len(tokens) == 2


def test_shingle_handles_short_text(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _shingle

    tokens = _shingle("hi there", n=3)
    # < n words: returns set of individual words
    assert tokens == {"hi", "there"}


def test_shingle_returns_empty_for_empty_text(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _shingle

    assert _shingle("") == set()
    assert _shingle("   ") == set()


def test_jaccard_identical_sets_returns_1(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    a = {"a", "b", "c"}
    assert _jaccard(a, a) == 1.0


def test_jaccard_disjoint_sets_returns_0(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0


def test_jaccard_partial_overlap(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    # |a∩b| = 1, |a∪b| = 3 → 1/3
    score = _jaccard({"a", "b"}, {"b", "c"})
    assert abs(score - 1 / 3) < 1e-6


def test_jaccard_both_empty_returns_0(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _jaccard

    assert _jaccard(set(), set()) == 0.0


def test_mode_returns_most_common_value(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _mode

    assert _mode(["a", "b", "a", "c"]) == "a"


def test_mode_returns_first_on_tie(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _mode

    # "a" and "b" both appear twice — first one wins
    result = _mode(["a", "b", "a", "b"])
    assert result == "a"


def test_mode_handles_empty_list(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _mode

    assert _mode([]) is None
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.sensory_perception_bridge'`

- [ ] **Step 3: Create the module with helpers**

Create `core/services/sensory_perception_bridge.py`:

```python
"""Sensory perception bridge.

Bridges Sansernes Arkiv (sensory_archive) into perceptual_event_engine.
When a sensory record is created, this module compares it against a
modality-specific baseline (time-of-day window for visual+audio with
recent-baseline fallback, recent-baseline only for atmosphere+mixed).
Meaningful changes become perceptual events with salience proportional
to change magnitude.

See docs/superpowers/specs/2026-05-04-sensory-perception-bridge-design.md
for the full design.
"""
from __future__ import annotations

import logging
from collections import Counter

logger = logging.getLogger(__name__)


def _shingle(text: str, *, n: int = 3) -> set[str]:
    """Tokenize lowercased text into overlapping n-grams of words."""
    words = [w for w in (text or "").lower().split() if w]
    if len(words) < n:
        return set(words)
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two token sets. Returns 0 if both empty."""
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter / union


def _mode(values: list[str]) -> str | None:
    """Most common value. On tie, returns the value that appears first in the list."""
    if not values:
        return None
    counter = Counter(values)
    max_count = max(counter.values())
    # First value in original list with the max count wins (stable on tie)
    for v in values:
        if counter[v] == max_count:
            return v
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: PASS (10 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/sensory_perception_bridge.py tests/test_sensory_perception_bridge.py
git commit -m "feat(sensory-perception): pure helpers for shingles, jaccard, mode"
```

---

## Task 3: Baseline aggregation

**Files:**
- Modify: `core/services/sensory_perception_bridge.py`
- Modify: `tests/test_sensory_perception_bridge.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sensory_perception_bridge.py`:

```python
def test_aggregate_baseline_uses_mood_mode(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": "rolig", "content": "lyset er varmt", "metadata": {}},
        {"mood_tone": "rolig", "content": "det er stille", "metadata": {}},
        {"mood_tone": "travl", "content": "der er gang i den", "metadata": {}},
    ]
    baseline = _aggregate_baseline(records)
    assert baseline["mood"] == "rolig"  # 2/3 = mode
    assert len(baseline["records"]) == 3


def test_aggregate_baseline_unions_content_tokens(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": "x", "content": "the quick brown fox jumped", "metadata": {}},
        {"mood_tone": "x", "content": "lazy dog sleeping quietly today", "metadata": {}},
    ]
    baseline = _aggregate_baseline(records)
    # Both records' shingles should be in the union
    assert "the quick brown" in baseline["content_tokens"]
    assert "lazy dog sleeping" in baseline["content_tokens"]


def test_aggregate_baseline_unions_metadata(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": None, "content": "", "metadata": {"category": "silence"}},
        {"mood_tone": None, "content": "", "metadata": {"category": "talk", "amplitude": 0.3}},
    ]
    baseline = _aggregate_baseline(records)
    assert baseline["metadata"]["category"] == {"silence", "talk"}
    assert baseline["metadata"]["amplitude"] == {"0.3"}


def test_aggregate_baseline_filters_empty_moods(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _aggregate_baseline

    records = [
        {"mood_tone": None, "content": "", "metadata": {}},
        {"mood_tone": "rolig", "content": "", "metadata": {}},
        {"mood_tone": "", "content": "", "metadata": {}},
    ]
    baseline = _aggregate_baseline(records)
    assert baseline["mood"] == "rolig"  # only non-empty mood
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: FAIL — `_aggregate_baseline` not yet defined.

- [ ] **Step 3: Implement _aggregate_baseline**

Append to `core/services/sensory_perception_bridge.py`:

```python
def _aggregate_baseline(records: list[dict]) -> dict:
    """Aggregate 1-N records into a single baseline.

    Returns:
        {
            "records": [...],
            "mood": str | None,        # mode (most common) of non-empty mood_tones
            "content_tokens": set[str],  # union of shingles across all contents
            "metadata": dict[str, set[str]],  # per-key union of stringified values
        }
    """
    moods = [str(r.get("mood_tone") or "").strip().lower() for r in records]
    moods = [m for m in moods if m]
    mood_mode = _mode(moods) if moods else None

    all_tokens: set[str] = set()
    for r in records:
        all_tokens.update(_shingle(str(r.get("content") or "")))

    metadata_union: dict[str, set[str]] = {}
    for r in records:
        md = r.get("metadata") or {}
        if isinstance(md, dict):
            for k, v in md.items():
                metadata_union.setdefault(k, set()).add(str(v))

    return {
        "records": list(records),
        "mood": mood_mode,
        "content_tokens": all_tokens,
        "metadata": metadata_union,
    }
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: PASS (14 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/sensory_perception_bridge.py tests/test_sensory_perception_bridge.py
git commit -m "feat(sensory-perception): baseline aggregation with mood mode and token union"
```

---

## Task 4: Recent baseline + time-of-day baseline + build_baseline

**Files:**
- Modify: `core/services/sensory_perception_bridge.py`
- Modify: `tests/test_sensory_perception_bridge.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sensory_perception_bridge.py`:

```python
def test_recent_baseline_returns_last_three_excluding_current(isolated_runtime) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _recent_baseline

    # Insert 5 records, varied moods
    for i, mood in enumerate(["rolig", "rolig", "travl", "rolig", "kaotisk"]):
        insert_sensory_memory(
            modality="atmosphere",
            content=f"sample {i}",
            mood_tone=mood,
            metadata={},
        )
    # Get the most recent record as "current"
    from core.runtime.db_sensory import list_sensory_memories
    rows = list_sensory_memories(modality="atmosphere", limit=10)
    assert len(rows) == 5
    current = rows[0]

    baseline = _recent_baseline("atmosphere", current)
    # Should have 3 records, all excluding `current`
    assert len(baseline["records"]) == 3
    assert all(r["id"] != current["id"] for r in baseline["records"])


def test_recent_baseline_returns_empty_for_first_record(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _recent_baseline

    fake_record = {
        "id": "nonexistent",
        "modality": "atmosphere",
        "content": "first one",
        "mood_tone": "rolig",
        "metadata": {},
        "timestamp": "2026-05-04T12:00:00+00:00",
    }
    baseline = _recent_baseline("atmosphere", fake_record)
    assert baseline["records"] == []
    assert baseline["mood"] is None
    assert baseline["content_tokens"] == set()


def test_time_of_day_baseline_returns_records_in_window(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _time_of_day_baseline

    # Anchor: 2026-05-04 14:00. Window is ±2 hours over 7 days.
    base = datetime(2026, 5, 4, 14, 0, tzinfo=UTC)
    in_window_times = [
        base - timedelta(days=1, minutes=30),  # day -1, 13:30 — in
        base - timedelta(days=2),              # day -2, 14:00 — in
        base - timedelta(days=3, hours=1),     # day -3, 13:00 — in
    ]
    out_of_window_times = [
        base - timedelta(days=1, hours=4),     # day -1, 10:00 — out (>2h)
        base - timedelta(days=2, hours=6),     # day -2, 08:00 — out
    ]
    for ts in in_window_times + out_of_window_times:
        insert_sensory_memory(
            modality="visual",
            content=f"snapshot at {ts.isoformat()}",
            mood_tone="rolig",
            metadata={},
            timestamp=ts.isoformat(),
        )

    current = {
        "id": "current-uuid",
        "modality": "visual",
        "content": "now",
        "mood_tone": "rolig",
        "metadata": {},
        "timestamp": base.isoformat(),
    }
    baseline = _time_of_day_baseline("visual", current)
    assert baseline is not None
    assert len(baseline["records"]) == 3


def test_time_of_day_baseline_returns_none_when_under_threshold(
    isolated_runtime,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _time_of_day_baseline

    base = datetime(2026, 5, 4, 14, 0, tzinfo=UTC)
    # Only 2 records in window — under default threshold of 3
    for ts in [base - timedelta(days=1), base - timedelta(days=2)]:
        insert_sensory_memory(
            modality="visual", content="x", mood_tone="rolig", metadata={},
            timestamp=ts.isoformat(),
        )

    current = {
        "id": "current",
        "modality": "visual",
        "content": "now",
        "mood_tone": "rolig",
        "metadata": {},
        "timestamp": base.isoformat(),
    }
    assert _time_of_day_baseline("visual", current) is None


def test_build_baseline_visual_falls_back_to_recent_when_window_thin(
    isolated_runtime,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _build_baseline

    # Two records far from current's hour-of-day (out of window) but recent enough
    base = datetime(2026, 5, 4, 14, 0, tzinfo=UTC)
    for ts in [base - timedelta(hours=10), base - timedelta(hours=20)]:
        insert_sensory_memory(
            modality="visual", content="x", mood_tone="rolig", metadata={},
            timestamp=ts.isoformat(),
        )

    current = {
        "id": "current", "modality": "visual", "content": "now",
        "mood_tone": "rolig", "metadata": {}, "timestamp": base.isoformat(),
    }
    baseline = _build_baseline("visual", current)
    # Time-of-day baseline returned None → fallback to recent
    assert baseline is not None
    assert len(baseline["records"]) == 2


def test_build_baseline_atmosphere_uses_recent_directly(isolated_runtime) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import _build_baseline

    for i in range(3):
        insert_sensory_memory(
            modality="atmosphere", content=f"x{i}", mood_tone="rolig", metadata={},
        )

    fake_current = {
        "id": "fake-current", "modality": "atmosphere", "content": "z",
        "mood_tone": "rolig", "metadata": {}, "timestamp": "2026-05-04T12:00:00+00:00",
    }
    baseline = _build_baseline("atmosphere", fake_current)
    assert baseline is not None
    # Atmosphere always uses recent baseline — should have 3 records, none excluded
    # because fake_current ID isn't in the inserted set
    assert len(baseline["records"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: FAIL — `_recent_baseline`/`_time_of_day_baseline`/`_build_baseline` not yet defined.

- [ ] **Step 3: Implement baselines**

Append to `core/services/sensory_perception_bridge.py`:

```python
from datetime import UTC, datetime, timedelta


def _parse_iso(ts: str) -> datetime | None:
    """Parse ISO timestamp; return None if malformed. Treats naive as UTC."""
    if not ts:
        return None
    try:
        parsed = datetime.fromisoformat(str(ts))
    except (ValueError, TypeError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _now() -> datetime:
    """Indirected for monkey-patching in tests."""
    return datetime.now(UTC)


def _recent_baseline(modality: str, current_record: dict) -> dict:
    """Hybrid A+B baseline: latest N records of same modality excluding current."""
    from core.services import sensory_archive
    from core.runtime.settings import load_settings

    try:
        size = int(getattr(load_settings(), "sensory_perception_recent_baseline_size", 3))
    except Exception:
        size = 3

    candidates = sensory_archive.list_recent(modality=modality, limit=size + 5)
    matching = [r for r in candidates if r.get("id") != current_record.get("id")][:size]
    if not matching:
        return {"records": [], "mood": None, "content_tokens": set(), "metadata": {}}
    return _aggregate_baseline(matching)


def _time_of_day_baseline(modality: str, current_record: dict) -> dict | None:
    """Records inside ±N hours of current's time-of-day, over last M days.

    Returns None if fewer than `min_baseline_records` matches found.
    """
    from core.services import sensory_archive
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        window_hours = int(getattr(settings, "sensory_perception_time_window_hours", 2))
        window_days = int(getattr(settings, "sensory_perception_time_window_days", 7))
        min_records = int(getattr(settings, "sensory_perception_min_baseline_records", 3))
    except Exception:
        window_hours, window_days, min_records = (2, 7, 3)

    current_time = _parse_iso(str(current_record.get("timestamp") or ""))
    if current_time is None:
        return None

    since = (current_time - timedelta(days=window_days)).isoformat()
    candidates = sensory_archive.list_recent(
        modality=modality, since=since, limit=200,
    )
    target_hour = current_time.hour
    matching: list[dict] = []
    current_id = current_record.get("id")
    for r in candidates:
        if r.get("id") == current_id:
            continue
        ts = _parse_iso(str(r.get("timestamp") or ""))
        if ts is None:
            continue
        # Circular time-of-day distance: 23:00 vs 01:00 = 2 hours, not 22
        diff = abs(ts.hour - target_hour)
        hour_dist = min(diff, 24 - diff)
        if hour_dist <= window_hours:
            matching.append(r)
    if len(matching) < min_records:
        return None
    return _aggregate_baseline(matching)


def _build_baseline(modality: str, current_record: dict) -> dict | None:
    """Modality-aware baseline selection.

    visual + audio: time-of-day window primary, recent-baseline fallback.
    atmosphere + mixed: recent baseline only.
    """
    if modality in {"visual", "audio"}:
        baseline = _time_of_day_baseline(modality, current_record)
        if baseline and len(baseline["records"]) >= 1:
            return baseline
        return _recent_baseline(modality, current_record)
    elif modality in {"atmosphere", "mixed"}:
        return _recent_baseline(modality, current_record)
    return None
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: PASS (20 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/sensory_perception_bridge.py tests/test_sensory_perception_bridge.py
git commit -m "feat(sensory-perception): baseline strategies (time-of-day window + recent fallback)"
```

---

## Task 5: Metadata change detection

**Files:**
- Modify: `core/services/sensory_perception_bridge.py`
- Modify: `tests/test_sensory_perception_bridge.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sensory_perception_bridge.py`:

```python
def test_metadata_changed_audio_category_shift(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"category": "talk", "amplitude": 0.3}
    baseline_md = {"category": {"silence"}, "amplitude": {"0.1"}}
    assert _metadata_changed(new_md, baseline_md, "audio") is True


def test_metadata_changed_audio_same_category(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"category": "talk", "amplitude": 0.5}
    baseline_md = {"category": {"talk"}, "amplitude": {"0.3"}}
    # Audio: only category matters; amplitude diff alone doesn't count
    assert _metadata_changed(new_md, baseline_md, "audio") is False


def test_metadata_changed_visual_ignores_prompt_rotation(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"vision_prompt_index": 2}
    baseline_md = {"vision_prompt_index": {"0", "1"}}
    # Visual: prompt rotation is not a change in the world
    assert _metadata_changed(new_md, baseline_md, "visual") is False


def test_metadata_changed_atmosphere_any_value_shift(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"weather": "rainy"}
    baseline_md = {"weather": {"sunny"}}
    assert _metadata_changed(new_md, baseline_md, "atmosphere") is True


def test_metadata_changed_atmosphere_new_key(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    new_md = {"weather": "sunny", "occupants": 2}
    baseline_md = {"weather": {"sunny"}}
    # New key "occupants" introduced
    assert _metadata_changed(new_md, baseline_md, "atmosphere") is True


def test_metadata_changed_returns_false_for_empty(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _metadata_changed

    assert _metadata_changed({}, {}, "audio") is False
    assert _metadata_changed({}, {}, "visual") is False
    assert _metadata_changed({}, {}, "atmosphere") is False
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: FAIL — `_metadata_changed` not yet defined.

- [ ] **Step 3: Implement metadata change detection**

Append to `core/services/sensory_perception_bridge.py`:

```python
def _metadata_changed(
    new_md: dict, baseline_md: dict, modality: str
) -> bool:
    """Per-modality metadata change detection.

    audio: category-shift only (talk/silence/music/noise/mixed).
    visual: prompt-rotation ignored; other key changes count.
    atmosphere/mixed: any new key or value-shift counts.
    """
    if not new_md and not baseline_md:
        return False

    if modality == "audio":
        new_cat = str(new_md.get("category") or "")
        baseline_cats = baseline_md.get("category")
        if not new_cat:
            return False
        if isinstance(baseline_cats, set):
            return new_cat not in baseline_cats
        return new_cat != str(baseline_cats or "")

    if modality == "visual":
        # Ignore vision_prompt_index rotation; check other keys
        for k, v in new_md.items():
            if k == "vision_prompt_index":
                continue
            baseline_vals = baseline_md.get(k)
            if baseline_vals is None:
                # New key not in baseline
                return True
            if isinstance(baseline_vals, set):
                if str(v) not in baseline_vals:
                    return True
            else:
                if str(v) != str(baseline_vals):
                    return True
        return False

    # atmosphere + mixed: any shift counts
    for k, v in new_md.items():
        baseline_vals = baseline_md.get(k)
        if baseline_vals is None:
            return True
        if isinstance(baseline_vals, set):
            if str(v) not in baseline_vals:
                return True
        else:
            if str(v) != str(baseline_vals):
                return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: PASS (26 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/sensory_perception_bridge.py tests/test_sensory_perception_bridge.py
git commit -m "feat(sensory-perception): per-modality metadata change detection"
```

---

## Task 6: Change detection (combined heuristic)

**Files:**
- Modify: `core/services/sensory_perception_bridge.py`
- Modify: `tests/test_sensory_perception_bridge.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sensory_perception_bridge.py`:

```python
def test_detect_change_no_baseline_returns_unchanged(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _detect_change

    record = {"mood_tone": "rolig", "content": "anything", "metadata": {}}
    result = _detect_change(record, None, "atmosphere")
    assert result["changed"] is False
    assert result["kind"] == "no_baseline"


def test_detect_change_empty_baseline_returns_unchanged(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _detect_change

    record = {"mood_tone": "rolig", "content": "x", "metadata": {}}
    baseline = {"records": [], "mood": None, "content_tokens": set(), "metadata": {}}
    result = _detect_change(record, baseline, "atmosphere")
    assert result["changed"] is False
    assert result["kind"] == "no_baseline"


def test_detect_change_unchanged_record(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _detect_change, _shingle

    record = {
        "mood_tone": "rolig",
        "content": "the quick brown fox is here",
        "metadata": {},
    }
    baseline = {
        "records": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        "mood": "rolig",
        "content_tokens": _shingle("the quick brown fox is here"),  # exact match
        "metadata": {},
    }
    result = _detect_change(record, baseline, "atmosphere")
    assert result["changed"] is False
    assert result["kind"] == "no_change"


def test_detect_change_mood_shift_only(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _detect_change, _shingle

    content = "lyset er stadig varmt og rummet er hyggeligt"
    record = {"mood_tone": "kaotisk", "content": content, "metadata": {}}
    baseline = {
        "records": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        "mood": "rolig",
        "content_tokens": _shingle(content),
        "metadata": {},
    }
    result = _detect_change(record, baseline, "atmosphere")
    assert result["changed"] is True
    assert result["kind"] == "mood_shift"


def test_detect_change_strong_lexical_drift_alone(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _detect_change, _shingle

    record = {
        "mood_tone": "rolig",
        "content": "completely different words about strange new objects appearing here",
        "metadata": {},
    }
    baseline = {
        "records": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        "mood": "rolig",
        "content_tokens": _shingle("the original baseline talked about something very else now"),
        "metadata": {},
    }
    result = _detect_change(record, baseline, "atmosphere")
    assert result["changed"] is True
    assert result["kind"] in {"content_drift", "lexical_drift"}


def test_detect_change_combined_mood_and_content(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _detect_change, _shingle

    record = {
        "mood_tone": "kaotisk",
        "content": "everything has changed completely now and is unrecognizable",
        "metadata": {},
    }
    baseline = {
        "records": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        "mood": "rolig",
        "content_tokens": _shingle("the quiet morning with familiar tones"),
        "metadata": {},
    }
    result = _detect_change(record, baseline, "atmosphere")
    assert result["changed"] is True
    assert result["kind"] == "mood_and_content"


def test_detect_change_metadata_only(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _detect_change, _shingle

    content = "stille rum med blød lyd"
    record = {
        "mood_tone": "rolig",
        "content": content,
        "metadata": {"category": "talk"},
    }
    baseline = {
        "records": [{"id": "r1"}, {"id": "r2"}, {"id": "r3"}],
        "mood": "rolig",
        "content_tokens": _shingle(content),
        "metadata": {"category": {"silence"}},
    }
    result = _detect_change(record, baseline, "audio")
    assert result["changed"] is True
    assert result["kind"] == "metadata_change"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: FAIL — `_detect_change` not yet defined.

- [ ] **Step 3: Implement _detect_change**

Append to `core/services/sensory_perception_bridge.py`:

```python
def _detect_change(
    record: dict, baseline: dict | None, modality: str
) -> dict:
    """Combined heuristic: mood_tone shift OR Jaccard < 0.4 OR metadata shift.

    Returns:
        {
            "changed": bool,
            "kind": str,  # one of: no_baseline, no_change, mood_shift, content_drift,
                          #         lexical_drift, metadata_change, mood_and_content
            "jaccard": float,
            "summary": str,
            "baseline_mood": str | None,
        }
    """
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        change_threshold = float(
            getattr(settings, "sensory_perception_jaccard_change_threshold", 0.4)
        )
        medium_threshold = float(
            getattr(settings, "sensory_perception_jaccard_medium_threshold", 0.25)
        )
    except Exception:
        change_threshold, medium_threshold = (0.4, 0.25)

    if baseline is None or not baseline.get("records"):
        return {
            "changed": False,
            "kind": "no_baseline",
            "jaccard": 1.0,
            "summary": "",
            "baseline_mood": None,
        }

    new_mood = (str(record.get("mood_tone") or "")).strip().lower() or None
    new_content = str(record.get("content") or "")
    new_metadata = record.get("metadata") or {}

    baseline_mood = baseline.get("mood")
    baseline_tokens = baseline.get("content_tokens") or set()
    baseline_metadata = baseline.get("metadata") or {}

    new_tokens = _shingle(new_content)
    jaccard = _jaccard(new_tokens, baseline_tokens)

    mood_shifted = bool(new_mood and baseline_mood and new_mood != baseline_mood)
    lex_shifted = jaccard < change_threshold
    metadata_shifted = _metadata_changed(new_metadata, baseline_metadata, modality)

    if not (mood_shifted or lex_shifted or metadata_shifted):
        return {
            "changed": False,
            "kind": "no_change",
            "jaccard": jaccard,
            "summary": "",
            "baseline_mood": baseline_mood,
        }

    # Determine dominant kind
    if mood_shifted and (jaccard < medium_threshold or metadata_shifted):
        kind = "mood_and_content"
    elif mood_shifted:
        kind = "mood_shift"
    elif jaccard < medium_threshold:
        kind = "content_drift"
    elif metadata_shifted and not lex_shifted:
        kind = "metadata_change"
    else:
        kind = "lexical_drift"

    summary = _summary_for_change(modality, new_mood, baseline_mood, kind, jaccard)
    return {
        "changed": True,
        "kind": kind,
        "jaccard": jaccard,
        "summary": summary,
        "baseline_mood": baseline_mood,
    }


def _summary_for_change(
    modality: str,
    new_mood: str | None,
    baseline_mood: str | None,
    kind: str,
    jaccard: float,
) -> str:
    """Generate a short Danish summary line for the perceptual event."""
    modality_label = {
        "visual": "Visuel",
        "audio": "Audio",
        "atmosphere": "Atmosfære",
        "mixed": "Sammensat",
    }.get(modality, modality)

    if kind == "mood_and_content":
        if new_mood and baseline_mood:
            return (
                f"{modality_label}-ændring: stemning skiftet fra {baseline_mood} "
                f"til {new_mood} med markant nyt indhold"
            )
        return f"{modality_label}-ændring: kombineret stemnings- og indholdsskift"
    if kind == "mood_shift":
        if new_mood and baseline_mood:
            return f"{modality_label}-stemning ændret fra {baseline_mood} til {new_mood}"
        return f"{modality_label}-stemningsskift detekteret"
    if kind == "content_drift":
        return f"{modality_label}-indhold markant ændret (similarity {jaccard:.2f})"
    if kind == "metadata_change":
        return f"{modality_label}-metadata ændret (fx kategori-skift)"
    if kind == "lexical_drift":
        return f"{modality_label}-indhold mildt ændret (similarity {jaccard:.2f})"
    return f"{modality_label}-ændring"
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: PASS (33 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/sensory_perception_bridge.py tests/test_sensory_perception_bridge.py
git commit -m "feat(sensory-perception): combined-heuristic change detection with Danish summaries"
```

---

## Task 7: Salience mapping

**Files:**
- Modify: `core/services/sensory_perception_bridge.py`
- Modify: `tests/test_sensory_perception_bridge.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sensory_perception_bridge.py`:

```python
def test_salience_high_for_mood_and_content(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _salience_for_change

    change = {"changed": True, "kind": "mood_and_content", "jaccard": 0.1}
    assert _salience_for_change(change) == "high"


def test_salience_high_for_mood_with_strong_lexical_drift(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _salience_for_change

    # mood_shift kind, jaccard < high_threshold (0.15)
    change = {"changed": True, "kind": "mood_shift", "jaccard": 0.10}
    assert _salience_for_change(change) == "high"


def test_salience_medium_for_mood_shift_alone(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _salience_for_change

    change = {"changed": True, "kind": "mood_shift", "jaccard": 0.6}
    assert _salience_for_change(change) == "medium"


def test_salience_medium_for_content_drift(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _salience_for_change

    change = {"changed": True, "kind": "content_drift", "jaccard": 0.20}
    assert _salience_for_change(change) == "medium"


def test_salience_medium_for_metadata_change(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _salience_for_change

    change = {"changed": True, "kind": "metadata_change", "jaccard": 0.7}
    assert _salience_for_change(change) == "medium"


def test_salience_normal_for_mild_lexical_drift(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import _salience_for_change

    change = {"changed": True, "kind": "lexical_drift", "jaccard": 0.35}
    assert _salience_for_change(change) == "normal"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: FAIL — `_salience_for_change` not yet defined.

- [ ] **Step 3: Implement _salience_for_change**

Append to `core/services/sensory_perception_bridge.py`:

```python
def _salience_for_change(change: dict) -> str:
    """Map change description to salience level (high/medium/normal).

    See spec section "Salience-mapping" — implementation matches the table.
    """
    from core.runtime.settings import load_settings

    try:
        settings = load_settings()
        high_threshold = float(
            getattr(settings, "sensory_perception_jaccard_high_threshold", 0.15)
        )
        medium_threshold = float(
            getattr(settings, "sensory_perception_jaccard_medium_threshold", 0.25)
        )
    except Exception:
        high_threshold, medium_threshold = (0.15, 0.25)

    kind = str(change.get("kind") or "")
    jaccard = float(change.get("jaccard") or 1.0)

    if kind == "mood_and_content":
        return "high"
    if kind == "mood_shift" and jaccard < high_threshold:
        return "high"
    if kind == "mood_shift":
        return "medium"
    if kind == "content_drift" and jaccard < high_threshold:
        return "high"
    if kind == "content_drift":  # jaccard between high_threshold and medium_threshold
        return "medium"
    if kind == "metadata_change":
        return "medium"
    # lexical_drift (jaccard between medium_threshold and change_threshold)
    return "normal"
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: PASS (39 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/sensory_perception_bridge.py tests/test_sensory_perception_bridge.py
git commit -m "feat(sensory-perception): salience mapping from change magnitude"
```

---

## Task 8: classify_sensory_change — top-level entry

**Files:**
- Modify: `core/services/sensory_perception_bridge.py`
- Modify: `tests/test_sensory_perception_bridge.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_sensory_perception_bridge.py`:

```python
def test_classify_returns_none_for_non_sensory_event(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import classify_sensory_change

    event = {"id": 1, "kind": "tool.completed", "payload": {}}
    assert classify_sensory_change(event) is None


def test_classify_returns_none_for_invalid_modality(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import classify_sensory_change

    event = {
        "id": 1,
        "kind": "memory.sensory.recorded",
        "payload": {"id": "x", "modality": "telepathy"},
    }
    assert classify_sensory_change(event) is None


def test_classify_returns_none_when_record_missing(isolated_runtime) -> None:
    from core.services.sensory_perception_bridge import classify_sensory_change

    event = {
        "id": 1,
        "kind": "memory.sensory.recorded",
        "payload": {"id": "nonexistent-id", "modality": "atmosphere"},
        "created_at": "2026-05-04T12:00:00+00:00",
    }
    assert classify_sensory_change(event) is None


def test_classify_returns_none_when_bridge_disabled(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.runtime import settings as settings_mod
    from core.services.sensory_perception_bridge import classify_sensory_change

    record = insert_sensory_memory(
        modality="atmosphere", content="x", mood_tone="rolig", metadata={},
    )

    original_load = settings_mod.load_settings
    def patched_load():
        s = original_load()
        s.sensory_perception_bridge_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched_load)

    event = {
        "id": 1, "kind": "memory.sensory.recorded",
        "payload": {"id": record["id"], "modality": "atmosphere"},
        "created_at": "2026-05-04T12:00:00+00:00",
    }
    assert classify_sensory_change(event) is None


def test_classify_returns_none_when_no_baseline(isolated_runtime) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import classify_sensory_change

    record = insert_sensory_memory(
        modality="atmosphere", content="first ever", mood_tone="rolig", metadata={},
    )
    event = {
        "id": 1, "kind": "memory.sensory.recorded",
        "payload": {"id": record["id"], "modality": "atmosphere"},
        "created_at": record["timestamp"],
    }
    assert classify_sensory_change(event) is None


def test_classify_returns_percept_when_mood_changes(isolated_runtime) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.sensory_perception_bridge import classify_sensory_change

    # Baseline: 3 atmosphere records, all "rolig"
    for i in range(3):
        insert_sensory_memory(
            modality="atmosphere",
            content="lyset er varmt og rummet er hyggeligt",
            mood_tone="rolig", metadata={},
        )
    # New record: same content but mood is now "kaotisk"
    new_record = insert_sensory_memory(
        modality="atmosphere",
        content="lyset er varmt og rummet er hyggeligt",
        mood_tone="kaotisk", metadata={},
    )

    event = {
        "id": 99, "kind": "memory.sensory.recorded",
        "payload": {"id": new_record["id"], "modality": "atmosphere"},
        "created_at": new_record["timestamp"],
    }
    percept = classify_sensory_change(event)
    assert percept is not None
    assert percept["change_type"] == "sensory-change-atmosphere"
    assert percept["salience"] in {"medium", "high"}
    assert percept["source_kind"] == "memory.sensory.recorded"
    assert percept["evidence"]["mood_tone_now"] == "kaotisk"
    assert percept["evidence"]["mood_tone_baseline"] == "rolig"
    assert "ændret" in percept["summary"] or "skiftet" in percept["summary"].lower()


def test_classify_handles_top_level_exception(isolated_runtime, monkeypatch) -> None:
    from core.services import sensory_perception_bridge as bridge

    def _broken(modality, current):
        raise RuntimeError("boom")
    monkeypatch.setattr(bridge, "_build_baseline", _broken)

    event = {
        "id": 1, "kind": "memory.sensory.recorded",
        "payload": {"id": "x", "modality": "atmosphere"},
        "created_at": "2026-05-04T12:00:00+00:00",
    }
    # Even with a broken inner function, top-level returns None (no raise)
    assert bridge.classify_sensory_change(event) is None
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: FAIL — `classify_sensory_change` not yet defined.

- [ ] **Step 3: Implement classify_sensory_change**

Append to `core/services/sensory_perception_bridge.py`:

```python
_VALID_MODALITIES = {"visual", "audio", "atmosphere", "mixed"}


def _bridge_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "sensory_perception_bridge_enabled", True))
    except Exception:
        return True


def _percept(
    *,
    source_event_id: int,
    source_kind: str,
    change_type: str,
    salience: str,
    summary: str,
    observed_at: str,
    evidence: dict[str, object],
) -> dict[str, object]:
    """Build a percept dict in the shape expected by perceptual_event_engine._record_perceptual_event."""
    return {
        "source_event_id": int(source_event_id or 0),
        "source_kind": str(source_kind or ""),
        "change_type": str(change_type or ""),
        "salience": str(salience or "normal"),
        "summary": " ".join(str(summary or "").split())[:240],
        "observed_at": str(observed_at or ""),
        "evidence": dict(evidence or {}),
    }


def classify_sensory_change(event: dict[str, object]) -> dict[str, object] | None:
    """Top-level entry. Returns a percept dict if the event represents a meaningful
    sensory change, else None. Never raises."""
    try:
        if not _bridge_enabled():
            return None
        return _classify_sensory_change_inner(event)
    except Exception as exc:
        logger.warning("sensory_perception_bridge: classify failed: %s", exc)
        return None


def _classify_sensory_change_inner(event: dict[str, object]) -> dict[str, object] | None:
    if str(event.get("kind") or "") != "memory.sensory.recorded":
        return None

    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    payload = payload or {}
    memory_id = payload.get("id")
    modality = str(payload.get("modality") or "")
    if not memory_id or modality not in _VALID_MODALITIES:
        return None

    try:
        from core.services import sensory_archive
        record = sensory_archive.get(str(memory_id))
    except Exception as exc:
        logger.debug("sensory_perception_bridge: get record failed: %s", exc)
        return None
    if not record:
        return None

    try:
        baseline = _build_baseline(modality, record)
    except Exception as exc:
        logger.debug("sensory_perception_bridge: build_baseline failed: %s", exc)
        return None

    change = _detect_change(record, baseline, modality)
    if not change.get("changed"):
        return None

    salience = _salience_for_change(change)
    return _percept(
        source_event_id=int(event.get("id") or 0),
        source_kind="memory.sensory.recorded",
        change_type=f"sensory-change-{modality}",
        salience=salience,
        summary=change.get("summary") or f"Sensory change in {modality}",
        observed_at=str(event.get("created_at") or record.get("timestamp") or ""),
        evidence={
            "memory_id": memory_id,
            "modality": modality,
            "mood_tone_now": record.get("mood_tone"),
            "mood_tone_baseline": change.get("baseline_mood"),
            "jaccard": round(float(change.get("jaccard") or 0.0), 4),
            "change_kind": change.get("kind"),
        },
    )
```

- [ ] **Step 4: Run test to verify it passes**

```
pytest tests/test_sensory_perception_bridge.py -v
```

Expected: PASS (46 tests now)

- [ ] **Step 5: Commit**

```bash
git add core/services/sensory_perception_bridge.py tests/test_sensory_perception_bridge.py
git commit -m "feat(sensory-perception): top-level classify_sensory_change with full pipeline"
```

---

## Task 9: Engine delegation

**Files:**
- Modify: `core/services/perceptual_event_engine.py`
- Create: `tests/test_sensory_perception_integration.py`

- [ ] **Step 1: Write the failing integration test**

Create `tests/test_sensory_perception_integration.py`:

```python
from __future__ import annotations


def test_engine_classifies_memory_sensory_recorded_event(isolated_runtime) -> None:
    """Engine's classify_event_change delegates memory.sensory.recorded events
    to sensory_perception_bridge.classify_sensory_change."""
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services.perceptual_event_engine import classify_event_change

    # Set up baseline + change
    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere",
            content="rolige toner og varmt lys",
            mood_tone="rolig", metadata={},
        )
    new_record = insert_sensory_memory(
        modality="atmosphere",
        content="rolige toner og varmt lys",
        mood_tone="kaotisk", metadata={},
    )

    event = {
        "id": 99,
        "kind": "memory.sensory.recorded",
        "payload": {"id": new_record["id"], "modality": "atmosphere"},
        "created_at": new_record["timestamp"],
    }
    percept = classify_event_change(event)
    assert percept is not None
    assert percept["change_type"] == "sensory-change-atmosphere"


def test_engine_returns_none_for_non_sensory_unknown_event(isolated_runtime) -> None:
    from core.services.perceptual_event_engine import classify_event_change

    event = {"id": 1, "kind": "totally.unknown.kind", "payload": {}}
    assert classify_event_change(event) is None


def test_engine_classifies_runtime_event_unchanged(isolated_runtime) -> None:
    """Existing runtime event classification still works (no regression)."""
    from core.services.perceptual_event_engine import classify_event_change

    event = {
        "id": 1,
        "kind": "runtime.visible_run_interrupted",
        "payload": {"summary": "x"},
        "created_at": "2026-05-04T12:00:00+00:00",
    }
    percept = classify_event_change(event)
    assert percept is not None
    assert percept["change_type"] == "runtime-interruption"
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_sensory_perception_integration.py -v
```

Expected: FAIL — engine does not yet delegate `memory.sensory.recorded` events; the first test will fail with `assert percept is not None` because classify_event_change returns None.

- [ ] **Step 3: Add delegation branch to engine**

Open `core/services/perceptual_event_engine.py`. Find `classify_event_change` (around line 52). After the existing `if kind == "cognitive_state.learning_policy_updated":` block (the last existing branch before `return None`), insert:

```python
    if kind == "memory.sensory.recorded":
        try:
            from core.services.sensory_perception_bridge import classify_sensory_change
            return classify_sensory_change(event)
        except Exception:
            return None
    return None
```

(Replace the original final `return None` with the block above — it ends with its own `return None`.)

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_sensory_perception_integration.py tests/test_perceptual_event_engine.py -v
```

Expected: PASS (3 new + existing perceptual_event tests still green)

- [ ] **Step 5: Commit**

```bash
git add core/services/perceptual_event_engine.py tests/test_sensory_perception_integration.py
git commit -m "feat(sensory-perception): engine delegation for memory.sensory.recorded events"
```

---

## Task 10: End-to-end integration tests (full pipeline)

**Files:**
- Modify: `tests/test_sensory_perception_integration.py` (append)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_sensory_perception_integration.py`:

```python
def test_observe_recent_changes_persists_sensory_perception(isolated_runtime) -> None:
    """End-to-end: sensory_archive.record_atmosphere → eventbus →
    observe_recent_changes → state has sensory perceptual event."""
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services import sensory_archive
    from core.services.perceptual_event_engine import (
        observe_recent_changes,
        build_perception_surface,
    )

    # Seed baseline (direct DB insert — does NOT go through eventbus)
    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere",
            content="rolige toner og varmt lys i rummet",
            mood_tone="rolig", metadata={},
        )

    # New record via the public archive API — this DOES publish to eventbus
    sensory_archive.record_atmosphere(
        "rolige toner og varmt lys i rummet",
        mood_tone="kaotisk",
    )

    # Run observe — should pick up the eventbus item and turn it into a perception
    result = observe_recent_changes()
    assert result["observed_count"] >= 1

    # Surface should now include the sensory perception
    surface = build_perception_surface(scan=False)
    assert surface["active"] is True
    sensory_events = [
        e for e in surface.get("events", [])
        if str(e.get("change_type") or "").startswith("sensory-change-")
    ]
    assert len(sensory_events) >= 1
    assert sensory_events[0]["change_type"] == "sensory-change-atmosphere"


def test_sensory_perception_creates_emotional_memory_anchor(
    isolated_runtime, monkeypatch
) -> None:
    """Sensory perception flows through record_perceptual_event, which calls
    capture_emotional_anchor — verify an anchor is created."""
    from core.runtime.db import list_emotional_memory_anchors
    from core.runtime.db_sensory import insert_sensory_memory
    from core.services import emotional_memory_engine as em
    from core.services import sensory_archive
    from core.services.perceptual_event_engine import observe_recent_changes

    monkeypatch.setattr(em, "_read_current_mood", lambda: ("alert", 0.5))
    monkeypatch.setattr(em, "_read_current_dimensions", lambda: {})

    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere",
            content="rolige toner og varmt lys",
            mood_tone="rolig", metadata={},
        )
    sensory_archive.record_atmosphere(
        "rolige toner og varmt lys", mood_tone="kaotisk",
    )
    observe_recent_changes()

    anchors = list_emotional_memory_anchors(anchor_type="perceptual_event")
    assert len(anchors) >= 1


def test_disabled_bridge_passes_through_engine_without_perceptions(
    isolated_runtime, monkeypatch
) -> None:
    from core.runtime.db_sensory import insert_sensory_memory
    from core.runtime import settings as settings_mod
    from core.services import sensory_archive
    from core.services.perceptual_event_engine import (
        observe_recent_changes,
        build_perception_surface,
    )

    original_load = settings_mod.load_settings
    def patched_load():
        s = original_load()
        s.sensory_perception_bridge_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched_load)

    for _ in range(3):
        insert_sensory_memory(
            modality="atmosphere", content="x", mood_tone="rolig", metadata={},
        )
    sensory_archive.record_atmosphere("x", mood_tone="kaotisk")
    observe_recent_changes()

    surface = build_perception_surface(scan=False)
    sensory_events = [
        e for e in (surface.get("events") or [])
        if str(e.get("change_type") or "").startswith("sensory-change-")
    ]
    assert sensory_events == []
```

- [ ] **Step 2: Run tests to verify they pass**

```
pytest tests/test_sensory_perception_integration.py -v
```

Expected: All PASS (6 tests total in the file).

If `test_sensory_perception_creates_emotional_memory_anchor` fails, that's a real bug — verify the existing perceptual_event_engine → emotional_memory hook still fires.

- [ ] **Step 3: Commit**

```bash
git add tests/test_sensory_perception_integration.py
git commit -m "test(sensory-perception): end-to-end integration including emotional memory hook"
```

---

## Task 11: Final smoke + CI verification

**Files:** No new files — final validation pass.

- [ ] **Step 1: Run the full sensory perception test suite**

```
conda activate ai
pytest tests/test_sensory_perception_settings.py \
       tests/test_sensory_perception_bridge.py \
       tests/test_sensory_perception_integration.py \
       -v
```

Expected: ALL PASS (~50+ tests).

- [ ] **Step 2: Run adjacent test suites to catch regressions**

```
pytest tests/test_perceptual_event_engine.py \
       tests/test_emotional_memory_engine.py \
       tests/test_emotional_memory_integration.py \
       tests/test_cognitive_conductor.py \
       -v
```

Expected: ALL PASS — none of these modules should regress.

- [ ] **Step 3: Run the prior emotional-memory full suite to verify nothing broke**

```
pytest tests/test_db_emotional_memory.py \
       tests/test_emotional_memory_settings.py \
       tests/test_memory_emotional_context_shim.py \
       tests/test_emotional_memory_migration.py \
       -v
```

Expected: ALL PASS.

- [ ] **Step 4: Syntax smoke (CI mirror)**

```
python -m compileall core apps/api scripts
```

Expected: Exit code 0 — no syntax errors.

- [ ] **Step 5: Manual end-to-end check (optional)**

Inside a Python REPL with `conda activate ai`:

```python
from core.runtime.db_sensory import insert_sensory_memory
from core.services import sensory_archive
from core.services.perceptual_event_engine import (
    observe_recent_changes, build_perception_surface,
)

# Seed baseline
for _ in range(3):
    insert_sensory_memory(
        modality="atmosphere",
        content="rolige toner og varmt lys i rummet",
        mood_tone="rolig", metadata={},
    )

# Record a change
sensory_archive.record_atmosphere(
    "rolige toner og varmt lys i rummet", mood_tone="kaotisk",
)

# Observe → surface
observe_recent_changes()
surface = build_perception_surface(scan=False)
print([e for e in surface["events"] if "sensory" in str(e.get("change_type", ""))])
```

Expected: prints a list with at least one event whose change_type starts with `sensory-change-`.

- [ ] **Step 6: Final commit (if anything was tweaked during smoke)**

```bash
git status
# If changes:
git add <touched files>
git commit -m "fix(sensory-perception): smoke-test corrections"
```

- [ ] **Step 7: Push branch / open PR**

User's call — do not push without explicit confirmation.

---

## Self-review notes

1. **Spec coverage:** Every spec section maps to one or more tasks:
   - *Architecture overview* → T2 (skeleton), T8 (full pipeline), T9 (delegation)
   - *Change detection algorithm* → T6 (`_detect_change`)
   - *Baseline aggregation* → T3 (`_aggregate_baseline`), T4 (`_recent_baseline`/`_time_of_day_baseline`/`_build_baseline`)
   - *Eventbus integration* → T9 (engine delegation branch)
   - *Settings* → T1
   - *Error handling* → woven through T8 (`classify_sensory_change` outer try/except + inner step-by-step guards)
   - *Testing strategy* → all tasks (TDD)
   - *Future extensions* → not implemented (correct — they are explicitly v2)

2. **Type/method consistency:**
   - `_shingle`, `_jaccard`, `_mode` defined in T2 and consumed unchanged in T3-T8.
   - `_aggregate_baseline` returns `{"records", "mood", "content_tokens", "metadata"}` — same shape consumed by `_recent_baseline`/`_time_of_day_baseline`/`_detect_change`.
   - `_detect_change` returns `{"changed", "kind", "jaccard", "summary", "baseline_mood"}` — same shape consumed by `_salience_for_change` and `classify_sensory_change`.
   - `_metadata_changed(new_md, baseline_md, modality)` signature consistent across T5 tests and T6 consumer.

3. **No placeholders.** All steps contain runnable code or exact commands.
