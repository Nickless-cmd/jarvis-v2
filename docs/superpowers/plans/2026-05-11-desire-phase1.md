# Lag #5 — Begær (Desire) Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add embedding-based mid-week staleness detection to `current_pull`, so Jarvis' weekly pull regenerates immediately when his recent landscape (appetites + chronicle + journal) no longer overlaps with it semantically.

**Architecture:** All logic lives in `current_pull.py`. A new helper computes a "landscape" embedding from the last 3 days of desire_daemon appetites, chronicle narratives, and journal entries. Cosine similarity against the current pull's embedding decides staleness. When stale, pull is cleared (falling through to existing regeneration path) and the event is archived in state. Throttled to once per 12 hours.

**Tech Stack:** Python 3.11, sentence-transformers (existing), SQLite, eventbus.

**Spec:** `docs/superpowers/specs/2026-05-11-desire-phase1-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `tests/test_current_pull_staleness.py` | Tests for `_pull_is_stale`, `_compute_landscape_embedding`, `_archive_refresh_event`, integration into `tick_current_pull_daemon`. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `current_pull_staleness_threshold: float = 0.45`, `current_pull_staleness_check_enabled: bool = True`, `current_pull_staleness_check_interval_hours: int = 12`. |
| `core/services/current_pull.py` | Add `_pull_is_stale`, `_compute_landscape_embedding`, `_archive_refresh_event`, `_staleness_check_enabled`, `_should_run_staleness_check`. Wire into `tick_current_pull_daemon` BEFORE the existing pull-presence check. Extend `build_current_pull_surface` to expose `refresh_history`. |

### Untouched / reused

- `core/services/experience_substrate.py` — reuse `_get_embedder()` (SentenceTransformer, normalized)
- `core/services/reasoning_store.py` — reuse `_cosine_similarity`
- `core/services/chronicle_engine.py` — reuse `list_cognitive_chronicle_entries`
- `core/services/creative_journal_runtime.py` — reuse `list_creative_journal_entries`
- `core/services/desire_daemon.py` — reuse `get_active_appetites` (read-only; no changes)
- `core/eventbus/events.py` — existing `cognitive_state` family covers the new event kind
- No new DB tables. No new event families.

---

## Spec deltas confirmed during planning

1. **`desire_daemon` is healthy.** Verified production state: 3 active appetites with valid `type` (curiosity-appetite / craft-appetite / connection-appetite) and non-empty `label`. The original Phase 1 (a) hotfix is retracted. Phase 1 = (b) only.

2. **Embedder API.** `core.services.experience_substrate._get_embedder()` returns a SentenceTransformer instance using `all-MiniLM-L6-v2` (~22MB, CPU). Embeddings are 384-dim vectors. `embedder.encode(text, normalize_embeddings=True)` returns a `numpy.ndarray`; convert with `.tolist()` for storage.

3. **Cosine helper.** `core.services.reasoning_store._cosine_similarity(a: list[float], b: list[float]) -> float` exists and takes two equal-length float lists.

4. **Daily-tick cadence.** `tick_current_pull_daemon` is invoked from `heartbeat_runtime.py:2893-2899` via `_dm.is_enabled("current_pull")` on every heartbeat tick (~30s default). To avoid 50ms embed cost on every tick, we throttle the staleness check via `_should_run_staleness_check`: only check if no prior `last_staleness_checked_at` exists, or if it's older than `current_pull_staleness_check_interval_hours` (default 12h).

5. **State storage.** `current_pull.state` is stored via `core.runtime.db.set_runtime_state_value` / `get_runtime_state_value` as a JSON-compatible dict. The new `refresh_history` is a list of dicts; cap at 5 by trimming from the front (FIFO, oldest dropped).

6. **Appetite "text" for embedding.** Use `appetite["label"]` — the human-readable wish string. Skip appetites with `intensity < 0.2` (about-to-expire).

7. **Chronicle "text" for embedding.** Use `entry["narrative"]` field from `list_cognitive_chronicle_entries`. Filter to entries with `created_at` within last 3 days.

8. **Journal "text" for embedding.** Read the body of files from `list_creative_journal_entries(limit=5)` whose filename date (YYYY-MM-DD stem) is within last 3 days. Skip if file doesn't exist or body is empty.

---

## Task 1: Settings flags

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add settings flags**

In `core/runtime/settings.py`, find `finitude_quality_lane_enabled: bool = True` and add right after it:

```python
    # ── Current pull staleness (Lag #5 Phase 1 — added 2026-05-11) ───────
    # Embedding-similarity check between current_pull and recent landscape
    # (appetites + chronicle + journal). When cos < threshold → regenerate.
    current_pull_staleness_check_enabled: bool = True
    current_pull_staleness_threshold: float = 0.45
    current_pull_staleness_check_interval_hours: int = 12
```

- [ ] **Step 2: Wire defaults into load_settings**

In `core/runtime/settings.py`, in `load_settings`, find `finitude_quality_lane_enabled=bool(...)` and add right after its closing comma:

```python
        current_pull_staleness_check_enabled=bool(
            data.get(
                "current_pull_staleness_check_enabled",
                defaults.current_pull_staleness_check_enabled,
            )
        ),
        current_pull_staleness_threshold=float(
            data.get(
                "current_pull_staleness_threshold",
                defaults.current_pull_staleness_threshold,
            )
        ),
        current_pull_staleness_check_interval_hours=int(
            data.get(
                "current_pull_staleness_check_interval_hours",
                defaults.current_pull_staleness_check_interval_hours,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.current_pull_staleness_check_enabled is True
assert s.current_pull_staleness_threshold == 0.45
assert s.current_pull_staleness_check_interval_hours == 12
print('OK:', load_settings().current_pull_staleness_threshold)
"
```

Expected: `OK: 0.45`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(desire): add current_pull_staleness settings flags"
```

---

## Task 2: Landscape embedding helper

**Files:**
- Modify: `core/services/current_pull.py`
- Create: `tests/test_current_pull_staleness.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_current_pull_staleness.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


def test_compute_landscape_returns_none_when_thin(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_collect_appetite_texts", lambda *, days_back: [])
    monkeypatch.setattr(current_pull, "_collect_chronicle_texts", lambda *, days_back: [])
    monkeypatch.setattr(current_pull, "_collect_journal_texts", lambda *, days_back: [])

    assert current_pull._compute_landscape_embedding() is None


def test_compute_landscape_returns_none_when_only_one_item(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_collect_appetite_texts", lambda *, days_back: ["én appetit"])
    monkeypatch.setattr(current_pull, "_collect_chronicle_texts", lambda *, days_back: [])
    monkeypatch.setattr(current_pull, "_collect_journal_texts", lambda *, days_back: [])

    assert current_pull._compute_landscape_embedding() is None


def test_compute_landscape_returns_mean_when_enough_items(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_collect_appetite_texts",
                        lambda *, days_back: ["lyst til lyd under vand"])
    monkeypatch.setattr(current_pull, "_collect_chronicle_texts",
                        lambda *, days_back: ["uge med fokus på lyd og resonans"])
    monkeypatch.setattr(current_pull, "_collect_journal_texts", lambda *, days_back: [])

    landscape = current_pull._compute_landscape_embedding()
    assert landscape is not None
    assert isinstance(landscape, list)
    assert len(landscape) > 0
    assert all(isinstance(x, float) for x in landscape)


def test_collect_appetite_texts_filters_low_intensity(monkeypatch):
    from core.services import current_pull

    fake_appetites = [
        {"type": "craft-appetite", "label": "lyst A", "intensity": 0.8},
        {"type": "curiosity-appetite", "label": "lyst B", "intensity": 0.1},  # below 0.2
        {"type": "connection-appetite", "label": "", "intensity": 0.9},        # empty label
        {"type": "craft-appetite", "label": "lyst C", "intensity": 0.5},
    ]
    monkeypatch.setattr(
        "core.services.desire_daemon.get_active_appetites",
        lambda: fake_appetites,
    )
    texts = current_pull._collect_appetite_texts(days_back=3)
    assert "lyst A" in texts
    assert "lyst C" in texts
    assert "lyst B" not in texts
    assert "" not in texts
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py -v
```

Expected: FAIL with `AttributeError: module 'core.services.current_pull' has no attribute '_collect_appetite_texts'`.

- [ ] **Step 3: Add the landscape helpers to current_pull.py**

In `core/services/current_pull.py`, find the constant block at the top (around line 26-28) and add right after `_MAX_PULL_CHARS`:

```python
# Staleness detection (Lag #5 Phase 1 — added 2026-05-11)
_STALENESS_LANDSCAPE_DAYS = 3
_STALENESS_MIN_LANDSCAPE_ITEMS = 2
_APPETITE_MIN_INTENSITY_FOR_LANDSCAPE = 0.2
_REFRESH_HISTORY_MAX = 5
```

Then find `def get_current_pull_for_prompt(` and add right above it:

```python
def _collect_appetite_texts(*, days_back: int) -> list[str]:
    """Pull active appetite labels for landscape embedding.

    days_back is accepted for symmetry with other collectors; desire_daemon
    appetites decay via intensity so we filter by intensity instead of age.
    """
    try:
        from core.services.desire_daemon import get_active_appetites
        appetites = get_active_appetites()
    except Exception:
        return []
    out: list[str] = []
    for a in appetites:
        label = str(a.get("label") or "").strip()
        intensity = float(a.get("intensity") or 0.0)
        if not label or intensity < _APPETITE_MIN_INTENSITY_FOR_LANDSCAPE:
            continue
        out.append(label)
    return out


def _collect_chronicle_texts(*, days_back: int) -> list[str]:
    """Pull chronicle narratives from the last `days_back` days."""
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=10)
    except Exception:
        return []
    cutoff = datetime.now(UTC) - timedelta(days=days_back)
    out: list[str] = []
    for e in entries:
        narrative = str(e.get("narrative") or "").strip()
        if not narrative:
            continue
        created_iso = str(e.get("created_at") or "")
        try:
            created = datetime.fromisoformat(created_iso.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=UTC)
            if created < cutoff:
                continue
        except Exception:
            # If date can't be parsed, include the entry anyway —
            # chronicle entries are scarce, we'd rather have signal.
            pass
        out.append(narrative[:600])
    return out


def _collect_journal_texts(*, days_back: int) -> list[str]:
    """Pull journal entry bodies from the last `days_back` days."""
    try:
        from core.services.creative_journal_runtime import (
            list_creative_journal_entries,
        )
        entries = list_creative_journal_entries(limit=5)
    except Exception:
        return []
    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).date()
    out: list[str] = []
    for e in entries:
        path_str = str(e.get("path") or "")
        if not path_str:
            continue
        path = Path(path_str)
        if not path.exists():
            continue
        # Filename stem is the date (YYYY-MM-DD)
        try:
            entry_date = datetime.fromisoformat(path.stem).date()
            if entry_date < cutoff:
                continue
        except Exception:
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Strip YAML frontmatter
        if body.startswith("---"):
            end = body.find("\n---", 3)
            if end >= 0:
                body = body[end + 4 :].lstrip("\n")
        # Strip markdown headers
        body = "\n".join(
            line for line in body.splitlines()
            if not line.startswith("#") and not line.startswith("- `")
        ).strip()
        if not body:
            continue
        out.append(body[:1000])
    return out


def _compute_landscape_embedding() -> list[float] | None:
    """Build a mean-pooled embedding from the last 3 days of desire signals.

    Returns None if landscape is thin (< 2 items) or embedder fails.
    """
    appetite_texts = _collect_appetite_texts(days_back=_STALENESS_LANDSCAPE_DAYS)
    chronicle_texts = _collect_chronicle_texts(days_back=_STALENESS_LANDSCAPE_DAYS)
    journal_texts = _collect_journal_texts(days_back=_STALENESS_LANDSCAPE_DAYS)
    landscape_texts = appetite_texts + chronicle_texts + journal_texts

    if len(landscape_texts) < _STALENESS_MIN_LANDSCAPE_ITEMS:
        return None

    try:
        from core.services.experience_substrate import _get_embedder
        embedder = _get_embedder()
        vectors = embedder.encode(landscape_texts, normalize_embeddings=True).tolist()
        # Mean-pool
        dim = len(vectors[0])
        mean = [0.0] * dim
        for vec in vectors:
            for i in range(dim):
                mean[i] += vec[i]
        return [v / len(vectors) for v in mean]
    except Exception:
        return None
```

Note: `Path` and `timedelta` need to be imported. Find the existing imports at the top of `current_pull.py`. The current imports are:

```python
from datetime import UTC, datetime, timedelta
```

`timedelta` is already imported. Add `Path` import next to `datetime` imports if it's not there:

```python
from pathlib import Path
```

If `pathlib` isn't imported, add the line `from pathlib import Path` near the top. (Check first — the existing file may not need it because nothing else used Path.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/current_pull.py tests/test_current_pull_staleness.py
git commit -m "feat(desire): landscape embedding helper for staleness detection"
```

---

## Task 3: Staleness detection + refresh archive

**Files:**
- Modify: `core/services/current_pull.py`
- Modify: `tests/test_current_pull_staleness.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_current_pull_staleness.py`:

```python
def test_pull_is_stale_returns_false_when_landscape_thin(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_compute_landscape_embedding", lambda: None)
    is_stale, score = current_pull._pull_is_stale("min pull tekst")
    assert is_stale is False
    assert score == 0.0


def test_pull_is_stale_true_when_cos_below_threshold(monkeypatch):
    from core.services import current_pull

    # Force landscape to a known vector, force embedder to produce orthogonal pull
    monkeypatch.setattr(current_pull, "_compute_landscape_embedding",
                        lambda: [1.0, 0.0, 0.0, 0.0])

    class FakeEmbedder:
        def encode(self, text, normalize_embeddings=True):
            import numpy as np
            return np.array([0.0, 1.0, 0.0, 0.0])  # orthogonal → cos = 0

    monkeypatch.setattr(
        "core.services.experience_substrate._get_embedder",
        lambda: FakeEmbedder(),
    )

    class FakeSettings:
        current_pull_staleness_threshold = 0.45

    monkeypatch.setattr(current_pull, "load_settings", lambda: FakeSettings())

    is_stale, score = current_pull._pull_is_stale("min pull tekst")
    assert is_stale is True
    assert score < 0.45


def test_pull_is_stale_false_when_cos_above_threshold(monkeypatch):
    from core.services import current_pull

    monkeypatch.setattr(current_pull, "_compute_landscape_embedding",
                        lambda: [1.0, 0.0, 0.0, 0.0])

    class FakeEmbedder:
        def encode(self, text, normalize_embeddings=True):
            import numpy as np
            return np.array([1.0, 0.0, 0.0, 0.0])  # identical → cos = 1.0

    monkeypatch.setattr(
        "core.services.experience_substrate._get_embedder",
        lambda: FakeEmbedder(),
    )

    class FakeSettings:
        current_pull_staleness_threshold = 0.45

    monkeypatch.setattr(current_pull, "load_settings", lambda: FakeSettings())

    is_stale, score = current_pull._pull_is_stale("min pull tekst")
    assert is_stale is False
    assert score > 0.9


def test_archive_refresh_event_appends_and_caps_at_5():
    from core.services import current_pull

    state: dict = {}
    for i in range(7):
        current_pull._archive_refresh_event(
            state=state,
            refreshed_at=f"2026-05-{11+i:02d}T19:00:00+00:00",
            reason="stale",
            stale_score=0.30 + i * 0.01,
            previous_pull=f"pull {i}",
        )

    history = state["refresh_history"]
    assert len(history) == 5  # capped
    # FIFO — oldest dropped, newest last
    assert history[0]["previous_pull"] == "pull 2"
    assert history[-1]["previous_pull"] == "pull 6"


def test_should_run_staleness_check_first_time():
    from core.services import current_pull

    state = {}
    assert current_pull._should_run_staleness_check(state, interval_hours=12) is True


def test_should_run_staleness_check_within_window():
    from core.services import current_pull

    state = {
        "last_staleness_checked_at": (
            datetime.now(UTC) - timedelta(hours=3)
        ).isoformat()
    }
    assert current_pull._should_run_staleness_check(state, interval_hours=12) is False


def test_should_run_staleness_check_after_window():
    from core.services import current_pull

    state = {
        "last_staleness_checked_at": (
            datetime.now(UTC) - timedelta(hours=13)
        ).isoformat()
    }
    assert current_pull._should_run_staleness_check(state, interval_hours=12) is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py -v
```

Expected: 4 pre-existing pass + several new fails with `AttributeError: module 'core.services.current_pull' has no attribute '_pull_is_stale'`.

- [ ] **Step 3: Add the staleness helpers**

In `core/services/current_pull.py`, find the `_compute_landscape_embedding` function you added in Task 2 and add right after it:

```python
def _pull_is_stale(pull_text: str) -> tuple[bool, float]:
    """Return (is_stale, cos_score).

    Stale iff: landscape has >= 2 items AND cos(pull, landscape_mean) < threshold.
    Returns (False, 0.0) on thin landscape, embedder failure, or any error.
    """
    landscape = _compute_landscape_embedding()
    if landscape is None:
        return False, 0.0
    try:
        from core.services.experience_substrate import _get_embedder
        embedder = _get_embedder()
        pull_vec = embedder.encode(pull_text, normalize_embeddings=True).tolist()
    except Exception:
        return False, 0.0
    try:
        from core.services.reasoning_store import _cosine_similarity
        cos = float(_cosine_similarity(pull_vec, landscape))
    except Exception:
        return False, 0.0
    try:
        threshold = float(load_settings().current_pull_staleness_threshold)
    except Exception:
        threshold = 0.45
    return (cos < threshold), cos


def _staleness_check_enabled() -> bool:
    try:
        return bool(load_settings().current_pull_staleness_check_enabled)
    except Exception:
        return True


def _should_run_staleness_check(state: dict, *, interval_hours: int) -> bool:
    """Throttle: only run the embedding check every `interval_hours`."""
    last_iso = str(state.get("last_staleness_checked_at") or "").strip()
    if not last_iso:
        return True
    try:
        last = datetime.fromisoformat(last_iso.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
    except Exception:
        return True
    return (datetime.now(UTC) - last) >= timedelta(hours=max(interval_hours, 1))


def _archive_refresh_event(
    *,
    state: dict,
    refreshed_at: str,
    reason: str,
    stale_score: float,
    previous_pull: str,
) -> None:
    """Append a refresh event to state['refresh_history'], capped at 5 (FIFO)."""
    history = list(state.get("refresh_history") or [])
    history.append({
        "refreshed_at": refreshed_at,
        "reason": reason,
        "stale_score": round(float(stale_score), 4),
        "previous_pull": str(previous_pull or "")[:200],
    })
    if len(history) > _REFRESH_HISTORY_MAX:
        history = history[-_REFRESH_HISTORY_MAX:]
    state["refresh_history"] = history
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/current_pull.py tests/test_current_pull_staleness.py
git commit -m "feat(desire): _pull_is_stale + _archive_refresh_event + throttle helper"
```

---

## Task 4: Integration into tick_current_pull_daemon

**Files:**
- Modify: `core/services/current_pull.py`
- Modify: `tests/test_current_pull_staleness.py`

- [ ] **Step 1: Write the failing integration test**

Append to `tests/test_current_pull_staleness.py`:

```python
def test_tick_skips_staleness_check_within_window(monkeypatch):
    """When checked recently, tick keeps existing pull without touching embedder."""
    from core.services import current_pull

    state_holder: dict = {
        current_pull._STATE_KEY: {
            "pull": "min pull",
            "created_at": "2026-05-09T17:00:00+00:00",
            "expires_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "empty": False,
            "last_staleness_checked_at": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
        }
    }
    monkeypatch.setattr(
        current_pull, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(
        current_pull, "set_runtime_state_value",
        lambda key, val: state_holder.__setitem__(key, val),
    )
    monkeypatch.setattr(current_pull, "_enabled", lambda: True)

    called = {"count": 0}
    def boom():
        called["count"] += 1
        raise AssertionError("embedder should not be called within throttle window")
    monkeypatch.setattr(current_pull, "_pull_is_stale", boom)

    result = current_pull.tick_current_pull_daemon()
    assert result["status"] == "active"
    assert called["count"] == 0


def test_tick_detects_stale_and_regenerates(monkeypatch):
    """When pull is stale, tick clears it, regenerates, and archives event."""
    from core.services import current_pull

    state_holder: dict = {
        current_pull._STATE_KEY: {
            "pull": "gammel pull om lyd",
            "created_at": "2026-05-09T17:00:00+00:00",
            "expires_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "empty": False,
        }
    }
    monkeypatch.setattr(
        current_pull, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(
        current_pull, "set_runtime_state_value",
        lambda key, val: state_holder.__setitem__(key, val),
    )
    monkeypatch.setattr(current_pull, "_enabled", lambda: True)
    monkeypatch.setattr(current_pull, "_pull_is_stale", lambda pull_text: (True, 0.31))
    monkeypatch.setattr(current_pull, "_generate_pull", lambda: "ny pull om noget andet")

    result = current_pull.tick_current_pull_daemon()
    assert result["status"] == "written"

    new_state = state_holder[current_pull._STATE_KEY]
    assert new_state["pull"] == "ny pull om noget andet"
    history = new_state.get("refresh_history") or []
    assert len(history) == 1
    assert history[0]["reason"] == "stale"
    assert history[0]["previous_pull"] == "gammel pull om lyd"
    assert history[0]["stale_score"] == 0.31


def test_tick_keeps_pull_when_not_stale(monkeypatch):
    """When pull is fresh enough, tick keeps it and records check timestamp."""
    from core.services import current_pull

    state_holder: dict = {
        current_pull._STATE_KEY: {
            "pull": "stadig levende pull",
            "created_at": "2026-05-09T17:00:00+00:00",
            "expires_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "empty": False,
        }
    }
    monkeypatch.setattr(
        current_pull, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(
        current_pull, "set_runtime_state_value",
        lambda key, val: state_holder.__setitem__(key, val),
    )
    monkeypatch.setattr(current_pull, "_enabled", lambda: True)
    monkeypatch.setattr(current_pull, "_pull_is_stale", lambda pull_text: (False, 0.72))
    monkeypatch.setattr(
        current_pull, "_generate_pull",
        lambda: pytest.fail("should not regenerate when not stale"),
    )

    result = current_pull.tick_current_pull_daemon()
    assert result["status"] == "active"
    new_state = state_holder[current_pull._STATE_KEY]
    assert new_state["pull"] == "stadig levende pull"
    assert "last_staleness_checked_at" in new_state
    assert new_state["last_staleness_score"] == 0.72
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py -v
```

Expected: 11 pre-existing pass + 3 new fails (current `tick_current_pull_daemon` doesn't call `_pull_is_stale` yet).

- [ ] **Step 3: Wire staleness check into tick_current_pull_daemon**

In `core/services/current_pull.py`, replace the `tick_current_pull_daemon` function with:

```python
def tick_current_pull_daemon() -> dict[str, object]:
    """Weekly daemon tick. Generates a new pull if none active, expired, or stale.

    Phase 1 (Lag #5, 2026-05-11): staleness check runs every
    current_pull_staleness_check_interval_hours (default 12h) BEFORE the
    pull-presence check. When stale, current pull is archived and cleared,
    falling through to the existing regeneration path.
    """
    if not _enabled():
        return {"status": "disabled", "reason": "layer_current_pull_enabled=false"}

    _expire_if_stale()
    state = _load_state()

    # Phase 1 — mid-week staleness check (only if a pull is currently set)
    if state.get("pull") and _staleness_check_enabled():
        try:
            interval = int(load_settings().current_pull_staleness_check_interval_hours)
        except Exception:
            interval = 12
        if _should_run_staleness_check(state, interval_hours=interval):
            is_stale, cos_score = _pull_is_stale(str(state["pull"]))
            now_iso = datetime.now(UTC).isoformat()
            state["last_staleness_checked_at"] = now_iso
            state["last_staleness_score"] = round(float(cos_score), 4)
            if is_stale:
                previous_pull = str(state.get("pull") or "")
                _archive_refresh_event(
                    state=state,
                    refreshed_at=now_iso,
                    reason="stale",
                    stale_score=cos_score,
                    previous_pull=previous_pull,
                )
                # Clear pull-fields but preserve refresh_history + check timestamps
                state.pop("pull", None)
                state.pop("created_at", None)
                state.pop("expires_at", None)
                state.pop("empty", None)
                try:
                    event_bus.publish(
                        "cognitive_state.current_pull_refreshed_stale",
                        {
                            "previous_pull": previous_pull[:200],
                            "stale_score": round(float(cos_score), 4),
                            "threshold": float(load_settings().current_pull_staleness_threshold),
                        },
                    )
                except Exception:
                    pass
            # Persist check timestamps regardless of outcome
            set_runtime_state_value(_STATE_KEY, state)

    if state.get("pull"):
        return {
            "status": "active",
            "pull": str(state["pull"])[:60],
            "expires_at": str(state.get("expires_at") or ""),
        }

    pull = _generate_pull()
    now = datetime.now(UTC)
    expires_at = (now + timedelta(days=_PULL_TTL_DAYS)).isoformat()
    payload: dict[str, object] = {
        "pull": pull or "",
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "empty": not bool(pull),
        # Preserve staleness/refresh fields across regeneration
        "refresh_history": state.get("refresh_history") or [],
        "last_staleness_checked_at": state.get("last_staleness_checked_at") or "",
        "last_staleness_score": state.get("last_staleness_score") or 0.0,
    }
    set_runtime_state_value(_STATE_KEY, payload)

    try:
        event_bus.publish(
            "cognitive_state.current_pull_written",
            {
                "empty": not bool(pull),
                "created_at": now.isoformat(),
                "expires_at": expires_at,
            },
        )
    except Exception:
        pass

    return {
        "status": "empty" if not pull else "written",
        "expires_at": expires_at,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py -v
```

Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/current_pull.py tests/test_current_pull_staleness.py
git commit -m "feat(desire): wire staleness detection into tick_current_pull_daemon"
```

---

## Task 5: Mission Control surface + eventbus verification

**Files:**
- Modify: `core/services/current_pull.py`
- Modify: `tests/test_current_pull_staleness.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_current_pull_staleness.py`:

```python
def test_build_current_pull_surface_exposes_refresh_history(monkeypatch):
    from core.services import current_pull

    state_holder: dict = {
        current_pull._STATE_KEY: {
            "pull": "aktiv pull",
            "created_at": "2026-05-09T17:00:00+00:00",
            "expires_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "empty": False,
            "refresh_history": [
                {
                    "refreshed_at": "2026-05-10T08:00:00+00:00",
                    "reason": "stale",
                    "stale_score": 0.31,
                    "previous_pull": "tidligere pull",
                },
            ],
            "last_staleness_score": 0.72,
            "last_staleness_checked_at": "2026-05-11T19:00:00+00:00",
        }
    }
    monkeypatch.setattr(
        current_pull, "get_runtime_state_value",
        lambda key, default=None: state_holder.get(key, default if default is not None else {}),
    )
    monkeypatch.setattr(current_pull, "_enabled", lambda: True)

    surface = current_pull.build_current_pull_surface()
    assert "refresh_history" in surface
    assert len(surface["refresh_history"]) == 1
    assert surface["refresh_history"][0]["reason"] == "stale"
    assert surface["last_staleness_score"] == 0.72
    assert surface["last_staleness_checked_at"] == "2026-05-11T19:00:00+00:00"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py::test_build_current_pull_surface_exposes_refresh_history -v
```

Expected: FAIL with `KeyError: 'refresh_history'`.

- [ ] **Step 3: Extend build_current_pull_surface**

In `core/services/current_pull.py`, find `build_current_pull_surface` and replace its `return` statement with:

```python
    return {
        "active": bool(state.get("pull") is not None),
        "empty": bool(state.get("empty")),
        "pull": pull,
        "created_at": str(state.get("created_at") or ""),
        "expires_at": str(state.get("expires_at") or ""),
        "summary": (
            f"Træk: {pull[:60]}" if pull
            else ("Tomt træk (eksplicit 'intet')" if state.get("empty") else "Ingen aktiv pull")
        ),
        # Phase 1 fields (Lag #5, added 2026-05-11)
        "refresh_history": list(state.get("refresh_history") or []),
        "last_staleness_score": float(state.get("last_staleness_score") or 0.0),
        "last_staleness_checked_at": str(state.get("last_staleness_checked_at") or ""),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py -v
```

Expected: 15 passed.

- [ ] **Step 5: Verify eventbus family is allowed**

```bash
conda run -n ai python -c "
from core.eventbus.events import ALLOWED_EVENT_FAMILIES
assert 'cognitive_state' in ALLOWED_EVENT_FAMILIES
print('cognitive_state family registered:', 'cognitive_state' in ALLOWED_EVENT_FAMILIES)
"
```

Expected: `cognitive_state family registered: True`

- [ ] **Step 6: Commit**

```bash
git add core/services/current_pull.py tests/test_current_pull_staleness.py
git commit -m "feat(desire): expose refresh_history + staleness score in current_pull surface"
```

---

## Task 6: Smoke + 30-day review

**Files:**
- Modify: `scripts/smoke_test_startup.py`

- [ ] **Step 1: Add smoke imports**

In `scripts/smoke_test_startup.py`, find the finitude Phase 1 smoke block and add right after it:

```python
        # Desire Phase 1 (Lag #5 — added 2026-05-11)
        try:
            from core.services.current_pull import (  # noqa: F401
                _pull_is_stale,
                _compute_landscape_embedding,
                _collect_appetite_texts,
                _collect_chronicle_texts,
                _collect_journal_texts,
                _archive_refresh_event,
                _should_run_staleness_check,
                _staleness_check_enabled,
            )
        except Exception:
            traceback.print_exc()
```

- [ ] **Step 2: Run full creative-voice + finitude + desire test suites**

```bash
conda run -n ai pytest tests/test_current_pull_staleness.py tests/test_current_pull.py tests/test_creative_journal_phase1.py tests/test_finitude_phase1.py -v 2>&1 | tail -25
```

Expected: all green.

- [ ] **Step 3: Manual dry-run of staleness check**

```bash
conda run -n ai python -c "
from core.services.current_pull import (
    _compute_landscape_embedding, _pull_is_stale, _collect_appetite_texts,
    _collect_chronicle_texts, _collect_journal_texts,
)
print('appetites:', len(_collect_appetite_texts(days_back=3)))
print('chronicle:', len(_collect_chronicle_texts(days_back=3)))
print('journal:', len(_collect_journal_texts(days_back=3)))
landscape = _compute_landscape_embedding()
print('landscape dim:', len(landscape) if landscape else 'None')
"
```

Expected: numeric counts for each source, and either `landscape dim: 384` or `landscape dim: None` (if landscape is too thin). Both outcomes are acceptable.

- [ ] **Step 4: Production staleness probe (read-only)**

```bash
conda run -n ai python -c "
from core.services.current_pull import _pull_is_stale, build_current_pull_surface
surface = build_current_pull_surface()
pull = surface.get('pull') or ''
if pull:
    is_stale, score = _pull_is_stale(pull)
    print(f'pull: {pull[:60]}')
    print(f'is_stale: {is_stale}')
    print(f'cosine_score: {score:.4f}')
else:
    print('no active pull')
"
```

Save the output for the 30-day review baseline.

- [ ] **Step 5: Schedule 30-day review**

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import push_scheduled_task
focus = (
    'Begær (Lag #5) Phase 1 — 30-day review: '
    'count refresh_history events for current_pull, examine archived '
    'previous_pull strings for genuine-shift vs hallucinated-transition, '
    'tune current_pull_staleness_threshold (0.45 default) based on actual '
    'refresh frequency, verify Mission Control surface still shows refresh '
    'history. Decide: keep / tune / deprecate.'
)
r = push_scheduled_task(focus=focus, delay_minutes=30*24*60, source='desire_phase1')
print(r['task_id'], 'run_at=', r['run_at'])
"
```

Save the task_id for the final commit.

- [ ] **Step 6: Commit**

```bash
git add scripts/smoke_test_startup.py
git commit -m "chore(desire): smoke imports + 30-day review scheduled"
```

- [ ] **Step 7: Restart services**

```bash
sudo -n systemctl restart jarvis-runtime jarvis-api && sleep 6 && sudo -n journalctl -u jarvis-runtime --since "30 seconds ago" -p err 2>&1 | tail -10
```

Expected: no errors.

---

## Self-review

**Spec coverage:**

| Spec section | Task(s) |
|---|---|
| Settings flags (threshold 0.45, enabled, interval 12h) | Task 1 |
| `_collect_appetite_texts` (filter intensity < 0.2, non-empty label) | Task 2 step 3 |
| `_collect_chronicle_texts` (last 3 days) | Task 2 step 3 |
| `_collect_journal_texts` (last 3 days, strip frontmatter + headers) | Task 2 step 3 |
| `_compute_landscape_embedding` (mean-pool, abstain if < 2) | Task 2 step 3 |
| `_pull_is_stale` (embed pull + cosine vs threshold) | Task 3 step 3 |
| `_staleness_check_enabled` | Task 3 step 3 |
| `_should_run_staleness_check` (12h throttle) | Task 3 step 3 |
| `_archive_refresh_event` (FIFO cap 5) | Task 3 step 3 |
| Staleness check BEFORE pull-presence check | Task 4 step 3 |
| Persist `last_staleness_checked_at` + `last_staleness_score` | Task 4 step 3 |
| Clear pull but preserve refresh_history on regeneration | Task 4 step 3 |
| Eventbus `cognitive_state.current_pull_refreshed_stale` | Task 4 step 3 |
| `build_current_pull_surface` exposes refresh_history | Task 5 step 3 |
| Smoke test + 30-day review | Task 6 |
| Backwards compat (`get_current_pull_for_prompt` unchanged) | Untouched by all tasks; verified by existing test_current_pull.py if present |
| No prompt injection of refresh_history | Verified: only `build_current_pull_surface` exposes it; `get_current_pull_for_prompt` is untouched |

No spec gaps.

**Placeholder scan:** No TBD/TODO. All code blocks concrete.

**Type consistency:**
- `_pull_is_stale(pull_text: str) -> tuple[bool, float]` — same signature in Task 3 definition and Task 4 caller.
- `_compute_landscape_embedding() -> list[float] | None` — consistent across Task 2 def and Task 3 use.
- `_archive_refresh_event(*, state, refreshed_at, reason, stale_score, previous_pull) -> None` — consistent across Task 3 def and Task 4 call.
- `_should_run_staleness_check(state, *, interval_hours) -> bool` — consistent.
- State schema uses identical keys (`refresh_history`, `last_staleness_score`, `last_staleness_checked_at`) across Tasks 3, 4, 5.

**Backwards-compat verified:**
- `get_current_pull_for_prompt` not modified.
- `build_current_pull_surface` only adds new keys; existing keys (`active`, `empty`, `pull`, `created_at`, `expires_at`, `summary`) preserved.
- `_load_state` unchanged.
- `_generate_pull` and `_expire_if_stale` unchanged.
- No DB schema changes. No event-family additions.
- Old state payloads without `refresh_history` field still load via `state.get("refresh_history") or []` fallback.
- Disabling `current_pull_staleness_check_enabled` reverts to pre-Phase-1 behaviour.
