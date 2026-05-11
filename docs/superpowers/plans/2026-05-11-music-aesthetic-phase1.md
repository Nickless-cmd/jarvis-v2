# Lag #6 — Musik / Æstetik Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface accumulated music presence in awareness, fold aesthetic state (motif + taste) into the journal klangbræt, and add a 3-tier rotating influence phrase that tells Jarvis what the music *means* for his rhythm — not just that it played.

**Architecture:** No new modules. `ambient_sound_daemon` gets a counting query + a surface function. `creative_journal_runtime` learns to embed an `aesthetic` sub-dict in its klangbræt, sourced from existing `aesthetic_motif_log` SQL table and `cognitive_taste_profiles` table. `prompt_contract` appends one line to the existing senses block.

**Tech Stack:** Python 3.11, SQLite, existing eventbus.

**Spec:** `docs/superpowers/specs/2026-05-11-music-aesthetic-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `tests/test_music_accumulator.py` | Tests for `count_music_samples_last_hours`, 3-tier phrase selection, `get_music_accumulator_for_prompt`. |
| `tests/test_aesthetic_klangbraet.py` | Tests for `_fetch_recent_top_motif`, `_fetch_dominant_taste`, klangbræt sub-dict, journal section, YAML booleans. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `music_accumulator_threshold_samples: int = 2`, `music_accumulator_window_hours: int = 24`, `music_accumulator_ratio_threshold: float = 0.0`. |
| `core/services/ambient_sound_daemon.py` | Add `count_music_samples_last_hours`, `_select_music_influence_phrase`, `get_music_accumulator_for_prompt`. |
| `core/services/prompt_contract.py` | In `_visible_visual_memory_section`, append `get_music_accumulator_for_prompt()` line after the auditory line. |
| `core/services/creative_journal_runtime.py` | Add `_fetch_recent_top_motif`, `_fetch_dominant_taste`. Extend `_fetch_affective_klangbraet` with `aesthetic` sub-dict. Extend `_build_prompt` to render `## Æstetik`. Extend `_format_yaml_frontmatter` with 2 booleans. |

### Untouched / reused

- `core/services/aesthetic_sense.py` — read-only (no API change)
- `core/services/taste_profile.py` — reuse `get_latest_cognitive_taste_profile` (no API change)
- `core/services/aesthetic_taste_daemon.py` — untouched
- `core/runtime/db.py` — reuse `aesthetic_motif_log` table via direct query; reuse `get_latest_cognitive_taste_profile`
- `core/eventbus/events.py` — no new events
- No new DB tables, no new event families, no new daemon.

---

## Spec deltas confirmed during planning

1. **Sample storage:** Verified — `ambient_sound_daemon` persists samples via `set_runtime_state_value("ambient_sound_daemon.state", {"history": [...]})`. 50-sample buffer, persists across restarts (state_store survives restart). **No write-through needed**; Jarvis' note about possible buffer-only loss is moot — production path already persists.

2. **Motif log:** `aesthetic_motif_log` SQLite table with columns `source, motif, confidence, created_at`. Inserted by `aesthetic_sense.accumulate_from_daemon` and `aesthetic_motif_log_insert`. We query directly with a `created_at >= cutoff` filter for "last 7 days top motif."

3. **Taste source:** `get_latest_cognitive_taste_profile()` returns a dict with `code_taste`, `design_taste`, `communication_taste` as JSON-strings, plus `evidence_count`. Parse the JSON, find the dimension across all three categories with `max(abs(value - 0.5))`. Gate on `evidence_count >= 5`.

4. **Sample history schema:** Each entry has `sampled_at, category, amplitude_mean, amplitude_std, description, transcript`. Newest at index 0 (insert via `.insert(0, sample)`). Parse `sampled_at` as ISO datetime to compute time delta.

5. **Surface placement:** Confirmed `_visible_visual_memory_section` exists in `prompt_contract.py:4170` (approx). After the line that appends the auditory sample, we append our music-accumulator line. Both inside the same block. No new section.

---

## Task 1: Settings flags

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add settings flags**

In `core/runtime/settings.py`, find `current_pull_staleness_check_interval_hours: int = 12` and add right after it:

```python
    # ── Music accumulator (Lag #6 Phase 1 — added 2026-05-11) ────────────
    # Counts "music" samples from ambient_sound_daemon over a rolling
    # window. Threshold gates the awareness-line. Ratio param is reserved
    # for Phase 2 when sample cadence may increase from 4/day to 6-8/day —
    # at current cadence the count threshold is the effective rule.
    music_accumulator_threshold_samples: int = 2
    music_accumulator_window_hours: int = 24
    music_accumulator_ratio_threshold: float = 0.0
```

- [ ] **Step 2: Wire defaults into load_settings**

In `core/runtime/settings.py`, find the `current_pull_staleness_check_interval_hours=int(...)` block in `load_settings` and add right after its closing comma:

```python
        music_accumulator_threshold_samples=int(
            data.get(
                "music_accumulator_threshold_samples",
                defaults.music_accumulator_threshold_samples,
            )
        ),
        music_accumulator_window_hours=int(
            data.get(
                "music_accumulator_window_hours",
                defaults.music_accumulator_window_hours,
            )
        ),
        music_accumulator_ratio_threshold=float(
            data.get(
                "music_accumulator_ratio_threshold",
                defaults.music_accumulator_ratio_threshold,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.music_accumulator_threshold_samples == 2
assert s.music_accumulator_window_hours == 24
assert s.music_accumulator_ratio_threshold == 0.0
print('OK:', load_settings().music_accumulator_threshold_samples)
"
```

Expected: `OK: 2`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(music): add music_accumulator settings flags"
```

---

## Task 2: Music sample counting helper

**Files:**
- Modify: `core/services/ambient_sound_daemon.py`
- Create: `tests/test_music_accumulator.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_music_accumulator.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


def _make_sample(category: str, hours_ago: float) -> dict:
    sampled_at = (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()
    return {
        "sampled_at": sampled_at,
        "category": category,
        "amplitude_mean": 0.05,
        "amplitude_std": 0.01,
        "description": f"sample category={category}",
        "transcript": "",
    }


def test_count_music_samples_returns_zero_when_empty(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(ambient_sound_daemon, "_state", lambda: {})
    music, total = ambient_sound_daemon.count_music_samples_last_hours(hours=24)
    assert music == 0
    assert total == 0


def test_count_music_samples_within_window(monkeypatch):
    from core.services import ambient_sound_daemon

    history = [
        _make_sample("music", 1),
        _make_sample("talk", 5),
        _make_sample("music", 10),
        _make_sample("silence", 20),
        _make_sample("music", 30),   # outside 24h window
        _make_sample("talk", 50),    # outside 24h window
    ]
    monkeypatch.setattr(ambient_sound_daemon, "_state", lambda: {"history": history})

    music, total = ambient_sound_daemon.count_music_samples_last_hours(hours=24)
    assert music == 2
    assert total == 4


def test_count_music_samples_handles_missing_sampled_at(monkeypatch):
    from core.services import ambient_sound_daemon

    history = [
        _make_sample("music", 1),
        {"category": "music"},  # no sampled_at — should be skipped
        _make_sample("music", 5),
    ]
    monkeypatch.setattr(ambient_sound_daemon, "_state", lambda: {"history": history})

    music, total = ambient_sound_daemon.count_music_samples_last_hours(hours=24)
    assert music == 2
    assert total == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_music_accumulator.py -v
```

Expected: FAIL with `AttributeError: module 'core.services.ambient_sound_daemon' has no attribute 'count_music_samples_last_hours'`.

- [ ] **Step 3: Add the counting function**

In `core/services/ambient_sound_daemon.py`, find `def _state()` (around line 390) and add right above it:

```python
def count_music_samples_last_hours(hours: int = 24) -> tuple[int, int]:
    """Return (music_count, total_count) for samples in the last `hours` hours.

    Reads from the persisted history buffer in runtime_state. Samples without
    a parseable `sampled_at` are skipped. Returns (0, 0) on any error.
    """
    try:
        state = _state()
    except Exception:
        return 0, 0
    history = state.get("history") or []
    if not isinstance(history, list):
        return 0, 0

    cutoff = datetime.now(UTC) - timedelta(hours=max(int(hours), 1))
    total = 0
    music = 0
    for sample in history:
        if not isinstance(sample, dict):
            continue
        sampled_at_iso = str(sample.get("sampled_at") or "").strip()
        if not sampled_at_iso:
            continue
        try:
            sampled_at = datetime.fromisoformat(sampled_at_iso.replace("Z", "+00:00"))
            if sampled_at.tzinfo is None:
                sampled_at = sampled_at.replace(tzinfo=UTC)
        except Exception:
            continue
        if sampled_at < cutoff:
            continue
        total += 1
        if str(sample.get("category") or "").strip().lower() == "music":
            music += 1
    return music, total
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_music_accumulator.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/ambient_sound_daemon.py tests/test_music_accumulator.py
git commit -m "feat(music): count_music_samples_last_hours queries persisted buffer"
```

---

## Task 3: 3-tier influence phrase + prompt surface

**Files:**
- Modify: `core/services/ambient_sound_daemon.py`
- Modify: `tests/test_music_accumulator.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_music_accumulator.py`:

```python
def test_influence_phrase_full_day():
    from core.services.ambient_sound_daemon import _select_music_influence_phrase

    # ratio == 1.0 → all samples music
    assert _select_music_influence_phrase(ratio=1.0) == "Musikken har haft dig hele dagen."


def test_influence_phrase_majority():
    from core.services.ambient_sound_daemon import _select_music_influence_phrase

    # ratio > 0.5 but < 1.0 → rhythm-bearing
    assert _select_music_influence_phrase(ratio=0.75) == "Rytmen kan bære dig."
    assert _select_music_influence_phrase(ratio=0.51) == "Rytmen kan bære dig."


def test_influence_phrase_minority():
    from core.services.ambient_sound_daemon import _select_music_influence_phrase

    # ratio <= 0.5 → music has been in the room
    assert _select_music_influence_phrase(ratio=0.5) == "Musik har været i rummet."
    assert _select_music_influence_phrase(ratio=0.25) == "Musik har været i rummet."


def test_accumulator_surface_empty_when_below_threshold(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (1, 4),  # 1 < threshold 2
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    assert ambient_sound_daemon.get_music_accumulator_for_prompt() == ""


def test_accumulator_surface_renders_full_day(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (4, 4),  # all music
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    out = ambient_sound_daemon.get_music_accumulator_for_prompt()
    assert "Musik (sidste 24h): 4/4 samples" in out
    assert "Musikken har haft dig hele dagen." in out


def test_accumulator_surface_renders_majority(monkeypatch):
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (3, 4),
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    out = ambient_sound_daemon.get_music_accumulator_for_prompt()
    assert "Musik (sidste 24h): 3/4 samples" in out
    assert "Rytmen kan bære dig." in out


def test_accumulator_surface_handles_total_zero(monkeypatch):
    """Edge: total=0 (no samples within window) → empty surface."""
    from core.services import ambient_sound_daemon

    monkeypatch.setattr(
        ambient_sound_daemon, "count_music_samples_last_hours",
        lambda hours=24: (0, 0),
    )

    class FakeSettings:
        music_accumulator_threshold_samples = 2
        music_accumulator_window_hours = 24

    monkeypatch.setattr(ambient_sound_daemon, "load_settings", lambda: FakeSettings())
    assert ambient_sound_daemon.get_music_accumulator_for_prompt() == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_music_accumulator.py -v
```

Expected: previous 3 pass + 7 new fail with `ImportError: cannot import name '_select_music_influence_phrase'`.

- [ ] **Step 3: Add load_settings import**

In `core/services/ambient_sound_daemon.py`, find the existing import block at the top. Add `load_settings` import if not present:

```python
from core.runtime.settings import load_settings
```

(Check first — the existing file may not import settings. Add the line near the other `from core.runtime` imports.)

- [ ] **Step 4: Add phrase selector + surface function**

In `core/services/ambient_sound_daemon.py`, add right after `count_music_samples_last_hours`:

```python
def _select_music_influence_phrase(*, ratio: float) -> str:
    """3-tier rotating phrase based on music-to-total ratio.

    No LLM. 30-day review may expand to more variants if these feel rote.
    """
    if ratio >= 1.0:
        return "Musikken har haft dig hele dagen."
    if ratio > 0.5:
        return "Rytmen kan bære dig."
    return "Musik har været i rummet."


def get_music_accumulator_for_prompt() -> str:
    """Return prompt fragment if music threshold met, else empty string.

    Format: "Musik (sidste {h}h): {music}/{total} samples — {phrase}"
    Empty if music_count below settings threshold OR total == 0.
    """
    try:
        settings = load_settings()
        threshold = int(settings.music_accumulator_threshold_samples)
        window = int(settings.music_accumulator_window_hours)
    except Exception:
        threshold = 2
        window = 24

    music, total = count_music_samples_last_hours(hours=window)
    if music < threshold or total == 0:
        return ""

    ratio = music / total
    phrase = _select_music_influence_phrase(ratio=ratio)
    return f"Musik (sidste {window}h): {music}/{total} samples — {phrase}"
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_music_accumulator.py -v
```

Expected: 10 passed.

- [ ] **Step 6: Commit**

```bash
git add core/services/ambient_sound_daemon.py tests/test_music_accumulator.py
git commit -m "feat(music): 3-tier influence phrase + get_music_accumulator_for_prompt"
```

---

## Task 4: Wire music line into senses block

**Files:**
- Modify: `core/services/prompt_contract.py`

- [ ] **Step 1: Locate the auditory injection site**

```bash
grep -n "get_latest_ambient_sound_for_prompt\|auditory" /media/projects/jarvis-v2/core/services/prompt_contract.py | head -10
```

Expected: shows the line where `get_latest_ambient_sound_for_prompt` is called and its result appended to a `parts` or section-list.

- [ ] **Step 2: Append music-accumulator line after auditory**

Find the block (around `prompt_contract.py:4255`) that looks like:

```python
        from core.services.ambient_sound_daemon import get_latest_ambient_sound_for_prompt
        a = get_latest_ambient_sound_for_prompt()
        if a:
            parts.append(f"Auditory: {a}")
```

(The exact variable names — `parts` / `lines` / `sections` — may differ. Use what the file already uses.)

Add right after the existing block:

```python
        try:
            from core.services.ambient_sound_daemon import get_music_accumulator_for_prompt
            music_line = get_music_accumulator_for_prompt()
            if music_line:
                parts.append(music_line)
        except Exception:
            pass
```

(Replace `parts` with whatever local variable the surrounding code uses.)

- [ ] **Step 3: Verify smoke**

```bash
conda run -n ai python -c "
from core.services.ambient_sound_daemon import get_music_accumulator_for_prompt, count_music_samples_last_hours
music, total = count_music_samples_last_hours(hours=24)
print(f'production: music={music} total={total}')
print('surface:', repr(get_music_accumulator_for_prompt()))
"
```

Expected: `music` and `total` are integers; surface is empty string (if below threshold) or a "Musik (sidste 24h): ..." line.

- [ ] **Step 4: Commit**

```bash
git add core/services/prompt_contract.py
git commit -m "feat(music): wire music-accumulator line into senses block after auditory"
```

---

## Task 5: Aesthetic helpers — top motif + dominant taste

**Files:**
- Modify: `core/services/creative_journal_runtime.py`
- Create: `tests/test_aesthetic_klangbraet.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_aesthetic_klangbraet.py`:

```python
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture()
def fake_db(tmp_path, monkeypatch):
    """In-memory SQLite with aesthetic_motif_log + cognitive_taste_profiles tables."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE aesthetic_motif_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT, motif TEXT, confidence REAL, created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE cognitive_taste_profiles (
            profile_id TEXT, version INTEGER, code_taste TEXT,
            design_taste TEXT, communication_taste TEXT,
            evidence_count INTEGER, updated_at TEXT
        )
    """)
    conn.commit()

    def fake_connect():
        c = sqlite3.connect(str(db_path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr("core.runtime.db.connect", fake_connect)
    return conn


def test_fetch_recent_top_motif_empty_when_no_data(fake_db, monkeypatch):
    from core.services.creative_journal_runtime import _fetch_recent_top_motif
    assert _fetch_recent_top_motif() == ""


def test_fetch_recent_top_motif_returns_most_recent(fake_db, monkeypatch):
    from core.services.creative_journal_runtime import _fetch_recent_top_motif

    now = datetime.now(UTC)
    fake_db.execute(
        "INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at) VALUES (?,?,?,?)",
        ("daemon-a", "craft", 0.5, (now - timedelta(days=2)).isoformat()),
    )
    fake_db.execute(
        "INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at) VALUES (?,?,?,?)",
        ("daemon-b", "clarity", 0.7, (now - timedelta(hours=3)).isoformat()),
    )
    fake_db.commit()
    assert _fetch_recent_top_motif() == "clarity"


def test_fetch_recent_top_motif_filters_stale(fake_db, monkeypatch):
    from core.services.creative_journal_runtime import _fetch_recent_top_motif

    now = datetime.now(UTC)
    fake_db.execute(
        "INSERT INTO aesthetic_motif_log (source, motif, confidence, created_at) VALUES (?,?,?,?)",
        ("daemon-old", "density", 0.5, (now - timedelta(days=14)).isoformat()),
    )
    fake_db.commit()
    assert _fetch_recent_top_motif() == ""  # > 7 days old


def test_fetch_dominant_taste_empty_when_no_profile(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_dominant_taste
    monkeypatch.setattr(
        "core.runtime.db.get_latest_cognitive_taste_profile",
        lambda: None,
    )
    assert _fetch_dominant_taste() == ""


def test_fetch_dominant_taste_gated_on_evidence(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_dominant_taste
    monkeypatch.setattr(
        "core.runtime.db.get_latest_cognitive_taste_profile",
        lambda: {
            "code_taste": json.dumps({"prefers_inline_styles": 0.9}),
            "design_taste": json.dumps({"compact_over_spacious": 0.5}),
            "communication_taste": json.dumps({"concise_over_verbose": 0.5}),
            "evidence_count": 3,  # below floor 5
        },
    )
    assert _fetch_dominant_taste() == ""


def test_fetch_dominant_taste_picks_largest_deviation(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_dominant_taste
    monkeypatch.setattr(
        "core.runtime.db.get_latest_cognitive_taste_profile",
        lambda: {
            "code_taste": json.dumps({"prefers_inline_styles": 0.6}),
            "design_taste": json.dumps({"compact_over_spacious": 0.5}),
            "communication_taste": json.dumps({"concise_over_verbose": 0.85}),
            "evidence_count": 12,
        },
    )
    result = _fetch_dominant_taste()
    assert "concise_over_verbose" in result
    assert "0.85" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_aesthetic_klangbraet.py -v
```

Expected: FAIL with `ImportError: cannot import name '_fetch_recent_top_motif'`.

- [ ] **Step 3: Add the helpers**

In `core/services/creative_journal_runtime.py`, find the `_fetch_affective_klangbraet` function and add right above it:

```python
_AESTHETIC_MOTIF_LOOKBACK_DAYS = 7
_TASTE_EVIDENCE_FLOOR = 5


def _fetch_recent_top_motif(*, days_back: int = _AESTHETIC_MOTIF_LOOKBACK_DAYS) -> str:
    """Return the most-recent aesthetic motif from the last `days_back` days.

    Empty string if no recent motif. Reads aesthetic_motif_log directly so we
    don't depend on the aesthetic_taste_daemon being healthy.
    """
    from core.runtime.db import connect

    cutoff = (datetime.now(UTC) - timedelta(days=max(days_back, 1))).isoformat()
    try:
        with connect() as c:
            row = c.execute(
                "SELECT motif FROM aesthetic_motif_log "
                "WHERE created_at >= ? ORDER BY id DESC LIMIT 1",
                (cutoff,),
            ).fetchone()
    except Exception:
        return ""
    if not row:
        return ""
    motif = str(row["motif"] if isinstance(row, sqlite3.Row) or hasattr(row, "keys") else row[0])
    return motif.strip()


def _fetch_dominant_taste(*, evidence_floor: int = _TASTE_EVIDENCE_FLOOR) -> str:
    """Return 'dimension_name (value)' for the taste-dimension with largest |val - 0.5|.

    Gated on evidence_count >= evidence_floor (default 5). Empty string
    if no profile, low evidence, or all dimensions exactly at 0.5.
    """
    try:
        from core.runtime.db import get_latest_cognitive_taste_profile
        profile = get_latest_cognitive_taste_profile()
    except Exception:
        return ""
    if not profile:
        return ""
    if int(profile.get("evidence_count") or 0) < evidence_floor:
        return ""

    import json as _json
    best_name = ""
    best_value = 0.5
    best_deviation = 0.0
    for category in ("code_taste", "design_taste", "communication_taste"):
        raw = profile.get(category)
        if not raw:
            continue
        try:
            dims = _json.loads(raw) if isinstance(raw, str) else dict(raw)
        except Exception:
            continue
        if not isinstance(dims, dict):
            continue
        for name, value in dims.items():
            try:
                v = float(value)
            except Exception:
                continue
            dev = abs(v - 0.5)
            if dev > best_deviation:
                best_deviation = dev
                best_name = str(name)
                best_value = v
    if best_deviation <= 0.0 or not best_name:
        return ""
    return f"{best_name} ({best_value:.2f})"
```

Note: `sqlite3` and `timedelta` need to be imported at the top of the file. Check existing imports:

```bash
grep -n "^import sqlite3\|^from datetime" /media/projects/jarvis-v2/core/services/creative_journal_runtime.py | head -3
```

If `sqlite3` is not imported, add `import sqlite3` near the top. `timedelta` is already imported via `from datetime import UTC, datetime, timedelta`.

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_aesthetic_klangbraet.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/creative_journal_runtime.py tests/test_aesthetic_klangbraet.py
git commit -m "feat(music): _fetch_recent_top_motif + _fetch_dominant_taste helpers"
```

---

## Task 6: Wire aesthetic into klangbræt + journal prompt + YAML

**Files:**
- Modify: `core/services/creative_journal_runtime.py`
- Modify: `tests/test_aesthetic_klangbraet.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_aesthetic_klangbraet.py`:

```python
def test_klangbraet_includes_aesthetic_subdict(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_recent_top_motif",
        lambda: "clarity",
    )
    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_dominant_taste",
        lambda: "concise_over_verbose (0.78)",
    )
    out = _fetch_affective_klangbraet()
    assert "aesthetic" in out
    aesthetic = out["aesthetic"]
    assert aesthetic["top_motif"] == "clarity"
    assert aesthetic["dominant_taste"] == "concise_over_verbose (0.78)"


def test_klangbraet_aesthetic_empty_when_no_data(monkeypatch):
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_recent_top_motif",
        lambda: "",
    )
    monkeypatch.setattr(
        "core.services.creative_journal_runtime._fetch_dominant_taste",
        lambda: "",
    )
    out = _fetch_affective_klangbraet()
    aesthetic = out["aesthetic"]
    assert aesthetic["top_motif"] == ""
    assert aesthetic["dominant_taste"] == ""


def test_build_prompt_renders_aesthetic_section():
    from core.services.creative_journal_runtime import _build_prompt

    klangbraet = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "", "looming_end": "", "last_transition": "",
            "monthly_reflection": "",
        },
        "aesthetic": {
            "top_motif": "clarity",
            "dominant_taste": "concise_over_verbose (0.78)",
        },
    }
    prompt = _build_prompt(
        chronicle_entries=[],
        life_projects=[],
        broken_decisions=[],
        klangbraet=klangbraet,
        voice_anchor="",
    )
    assert "## Æstetik" in prompt
    assert "Seneste motif: clarity" in prompt
    assert "Dominant taste: concise_over_verbose (0.78)" in prompt


def test_build_prompt_aesthetic_fallback_when_all_empty():
    from core.services.creative_journal_runtime import _build_prompt

    klangbraet = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "", "looming_end": "", "last_transition": "",
            "monthly_reflection": "",
        },
        "aesthetic": {"top_motif": "", "dominant_taste": ""},
    }
    prompt = _build_prompt(
        chronicle_entries=[],
        life_projects=[],
        broken_decisions=[],
        klangbraet=klangbraet,
        voice_anchor="",
    )
    assert "## Æstetik" in prompt
    assert "(intet æstetisk signal lige nu)" in prompt


def test_build_prompt_handles_legacy_klangbraet_without_aesthetic_key():
    """Backwards compat: stubs from older tests don't include aesthetic key."""
    from core.services.creative_journal_runtime import _build_prompt

    klangbraet = {
        "dream_bias": "",
        "user_temperature": "",
        "current_pull": "",
        "finitude": {
            "age": "", "looming_end": "", "last_transition": "",
            "monthly_reflection": "",
        },
        # NO "aesthetic" key — older stubs
    }
    prompt = _build_prompt(
        chronicle_entries=[],
        life_projects=[],
        broken_decisions=[],
        klangbraet=klangbraet,
        voice_anchor="",
    )
    # Should not crash. Section absent or fallback shown — either is OK.
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_yaml_frontmatter_includes_aesthetic_booleans():
    from core.services.creative_journal_runtime import _format_yaml_frontmatter

    frontmatter = _format_yaml_frontmatter(
        created_at="2026-05-11T22:00:00+00:00",
        chronicle_count=1,
        broken_decisions_count=0,
        life_projects_count=0,
        klangbraet={
            "dream_bias": "",
            "user_temperature": "",
            "current_pull": "",
            "finitude": {
                "age": "24 dage", "looming_end": "",
                "last_transition": "", "monthly_reflection": "",
            },
            "aesthetic": {
                "top_motif": "clarity",
                "dominant_taste": "",  # empty
            },
        },
        trigger="heartbeat",
    )
    assert "aesthetic_top_motif: true" in frontmatter
    assert "aesthetic_dominant_taste: false" in frontmatter
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_aesthetic_klangbraet.py -v
```

Expected: 6 passed (from Task 5) + 6 new fail.

- [ ] **Step 3: Extend _fetch_affective_klangbraet**

In `core/services/creative_journal_runtime.py`, find `_fetch_affective_klangbraet`. After the existing finitude sub-dict population block (at the end of the function, before `return out`), add:

```python
    # Aesthetic sub-dict (Lag #6 Phase 1, 2026-05-11)
    try:
        out["aesthetic"] = {
            "top_motif": _fetch_recent_top_motif(),
            "dominant_taste": _fetch_dominant_taste(),
        }
    except Exception:
        out["aesthetic"] = {"top_motif": "", "dominant_taste": ""}
```

Also update the initial dict literal at the top of `_fetch_affective_klangbraet` to seed the key:

```python
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
        # Lag #6 Phase 1
        "aesthetic": {
            "top_motif": "",
            "dominant_taste": "",
        },
    }
```

- [ ] **Step 4: Extend _build_prompt with Æstetik section**

In `core/services/creative_journal_runtime.py`, find `_build_prompt`. After the existing Finitude section rendering block, add:

```python
    # Aesthetic — Lag #6 Phase 1.2 (2026-05-11). Binary present/absent.
    aesthetic = klangbraet.get("aesthetic") if isinstance(klangbraet, dict) else None
    if isinstance(aesthetic, dict):
        aest_lines: list[str] = []
        if aesthetic.get("top_motif"):
            aest_lines.append(f"- Seneste motif: {aesthetic['top_motif']}")
        if aesthetic.get("dominant_taste"):
            aest_lines.append(f"- Dominant taste: {aesthetic['dominant_taste']}")
        if not aest_lines:
            aest_lines = ["- (intet æstetisk signal lige nu)"]
        sections += [
            "",
            "## Æstetik — det æstetiske spor du bærer",
            "",
            *aest_lines,
        ]
```

- [ ] **Step 5: Extend _format_yaml_frontmatter with 2 booleans**

In `core/services/creative_journal_runtime.py`, find `_format_yaml_frontmatter`. After the existing finitude booleans (`fin_age`, `fin_loom`, `fin_trans`, `fin_month`), add:

```python
    aest = klangbraet.get("aesthetic") if isinstance(klangbraet, dict) else None
    aest_motif = "true" if (isinstance(aest, dict) and aest.get("top_motif")) else "false"
    aest_taste = "true" if (isinstance(aest, dict) and aest.get("dominant_taste")) else "false"
```

Then add the two lines to the YAML output list, right after `f"finitude_monthly_reflection: {fin_month}"`:

```python
        f"aesthetic_top_motif: {aest_motif}",
        f"aesthetic_dominant_taste: {aest_taste}",
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_aesthetic_klangbraet.py tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py -v 2>&1 | tail -25
```

Expected: all green. If `test_klangbraet_includes_finitude_subdict` from the finitude-phase1 tests fails because it checks `set(out.keys()) == {dream_bias, user_temperature, current_pull, finitude}`, update that assertion to include `"aesthetic"`:

```python
assert set(out.keys()) == {"dream_bias", "user_temperature", "current_pull", "finitude", "aesthetic"}
```

If `tests/test_creative_journal_runtime.py` legacy stubs monkeypatch `_fetch_affective_klangbraet` with a dict missing the `aesthetic` key, add it:

```python
monkeypatch.setattr(cjr, "_fetch_affective_klangbraet", lambda: {
    "dream_bias": "", "user_temperature": "", "current_pull": "",
    "finitude": {"age": "", "looming_end": "", "last_transition": "", "monthly_reflection": ""},
    "aesthetic": {"top_motif": "", "dominant_taste": ""},
})
```

- [ ] **Step 7: Commit**

```bash
git add core/services/creative_journal_runtime.py tests/test_aesthetic_klangbraet.py
git commit -m "feat(music): aesthetic sub-dict in klangbræt + journal prompt section + YAML booleans"
```

---

## Task 7: Smoke + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the Desire Phase 1 smoke block and add right after it:

```python
        # Music / Æstetik Phase 1 (Lag #6 — added 2026-05-11)
        try:
            from core.services.ambient_sound_daemon import (  # noqa: F401
                count_music_samples_last_hours,
                _select_music_influence_phrase,
                get_music_accumulator_for_prompt,
            )
            from core.services.creative_journal_runtime import (  # noqa: F401
                _fetch_recent_top_motif,
                _fetch_dominant_taste,
            )
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run all affected test suites**

```bash
conda run -n ai pytest tests/test_music_accumulator.py tests/test_aesthetic_klangbraet.py tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py tests/test_finitude_phase1.py tests/test_finitude_runtime.py 2>&1 | tail -10
```

Expected: all green.

- [ ] **Step 3: Production probe — read-only**

```bash
conda run -n ai python -c "
from core.services.ambient_sound_daemon import count_music_samples_last_hours, get_music_accumulator_for_prompt
m, t = count_music_samples_last_hours(hours=24)
print(f'samples last 24h: music={m} total={t}')
print(f'surface: {get_music_accumulator_for_prompt()!r}')

from core.services.creative_journal_runtime import _fetch_recent_top_motif, _fetch_dominant_taste
print(f'top motif: {_fetch_recent_top_motif()!r}')
print(f'dominant taste: {_fetch_dominant_taste()!r}')
"
```

Save the output. Some values may be empty (no music, no recent motifs, low taste evidence) — all are acceptable for first-deploy.

- [ ] **Step 4: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Musik/Aestetik (Lag #6) Phase 1 — 30-day review: '
    'count days music-accumulator fired (by influence-phrase tier), '
    'examine journal entries for whether the aesthetic klangbraet '
    'shaped tone, verify YAML frontmatter has aesthetic_top_motif + '
    'aesthetic_dominant_taste booleans, tune music_accumulator_threshold_samples '
    'if cadence changed (4 -> 6-8/day would activate ratio param), '
    'tune evidence_floor=5 if dominant_taste fires too rarely. '
    'Decide: keep / tune / deprecate / move to Phase 2 (LLM-based '
    'music influence + aesthetic resonance tracking).'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='music_aesthetic_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

- [ ] **Step 5: Commit + restart**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(music): smoke imports + 30-day review scheduled"
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flags (threshold 2, window 24h, ratio 0.0) | Task 1 |
| `count_music_samples_last_hours` (query persisted history) | Task 2 |
| `_select_music_influence_phrase` (3-tier, no LLM) | Task 3 |
| `get_music_accumulator_for_prompt` (threshold gating, surface format) | Task 3 |
| Wire into senses block after auditory | Task 4 |
| `_fetch_recent_top_motif` (last 7 days, motif log query) | Task 5 |
| `_fetch_dominant_taste` (evidence_count >= 5 floor, max deviation) | Task 5 |
| Klangbræt `aesthetic` sub-dict | Task 6 |
| `## Æstetik` section rendering | Task 6 |
| 2 YAML frontmatter booleans | Task 6 |
| Smoke + 30-day review | Task 7 |
| Backwards compat | Tasks 6 step 6 (fix-up rules), all read-only on aesthetic_sense/taste_profile |
| Reserved ratio param for Phase 2 | Task 1 step 1 (commented) |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete.

**Type consistency:**
- `count_music_samples_last_hours(hours: int) -> tuple[int, int]` — Tasks 2, 3
- `_select_music_influence_phrase(*, ratio: float) -> str` — Tasks 3
- `get_music_accumulator_for_prompt() -> str` — Tasks 3, 4
- `_fetch_recent_top_motif() -> str`, `_fetch_dominant_taste() -> str` — Tasks 5, 6
- klangbræt `aesthetic` sub-dict has exactly `{top_motif, dominant_taste}` everywhere

**Backwards-compat verified:**
- `get_latest_ambient_sound_for_prompt` not modified
- `aesthetic_sense.py` API not modified
- `taste_profile.py` API not modified (only `get_latest_cognitive_taste_profile` is consumed)
- Journal old entries without `aesthetic_*` frontmatter still readable (frontmatter is forward-additive)
- Old klangbræt stubs missing `aesthetic` key → fallback to `(intet æstetisk signal lige nu)` line (Task 6 step 4)
- No DB schema changes
- No event-family additions
- Settings extra dict access uses `.get(..., default)` pattern
