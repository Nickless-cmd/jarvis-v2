---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Lag #4 — Creative Voice (Weekly Journal), Phase 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Jarvis' weekly journal a recognizable voice by adding voice anchoring (static + auto-refreshed exemplars), expanding the corpus (broken decisions + affective klangbræt), gating empty weeks with adaptive cadence, swapping to the quality LLM lane, and reading the latest entry back into Jarvis' awareness on session wake.

**Architecture:** Two new pure-read modules (`voice_anchor`, `voice_curator`) feed into the existing `creative_journal_runtime`. Curator runs as a sub-step of the journal cycle itself (no separate daemon) — it refreshes `workspace/VOICE_RECENT.md` from external output only (visible chat replies + chronicle narrative + prior journals; never `inner_voice`). Corpus expansion reuses the regret-corpus pattern from `dream_bias_engine`. Reading-back lives in `prompt_contract` and injects the latest entry's body into the awareness block on session wake. Quality gate is a single boolean function; adaptive cadence is a counter in the runtime-state payload that already exists.

**Tech Stack:** Python 3.11, SQLite (events + chat_messages), existing daemon_llm quality lane, eventbus.

**Spec:** `docs/superpowers/specs/2026-05-11-creative-voice-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `core/services/voice_anchor.py` | `read_voice_anchor()` returns combined VOICE.md + VOICE_RECENT.md text. Pure file read. No LLM. |
| `core/services/voice_curator.py` | `refresh_voice_recent()` — selects 3-5 external-output exemplars (visible chat, chronicle, prior journals), writes `workspace/VOICE_RECENT.md` if changed. Idempotent. |
| `workspace/VOICE.md` | Static seed (manual, 100-300 words). Voice direction: tone, rhythm, vocabulary, what to avoid. |
| `tests/services/test_voice_anchor.py` | Tests: empty files OK, missing files OK, concatenation order stable. |
| `tests/services/test_voice_curator.py` | Tests: external-only sourcing, diversity heuristic, idempotent rewrite, inner_voice exclusion. |
| `tests/test_creative_journal_phase1.py` | Tests for journal upgrade: voice anchor in prompt, broken_decisions fetched, klangbræt included, skip-gate, adaptive cadence, YAML frontmatter, quality-lane LLM. |

### Modified files

| Path | Change |
|---|---|
| `core/runtime/settings.py` | Add `creative_voice_quality_lane_enabled: bool = True` |
| `core/services/creative_journal_runtime.py` | Extend `_build_prompt` (voice anchor + broken_decisions + klangbræt). Add `_should_skip_week`, `_fetch_broken_decisions`, `_fetch_affective_klangbraet`, `_format_yaml_frontmatter`. Swap to `quality_daemon_llm_call`. Adaptive cadence via `consecutive_skips` in state. Call `voice_curator.refresh_voice_recent()` before building the prompt. |
| `core/services/prompt_contract.py` | Add `format_journal_for_heartbeat()` (300-word cap). Inject into awareness block. |

### Untouched / reused

- `core/services/dream_bias_engine.py` — reuse `format_dream_bias_for_heartbeat`
- `core/services/user_temperature_engine.py` — reuse `get_response_style_modifiers`
- `core/services/current_pull.py` — reuse `get_current_pull_for_prompt`
- `core/services/chronicle_engine.py` — reuse `list_cognitive_chronicle_entries`
- `core/services/initiative_queue.py` — reuse `list_active_long_term_intentions`
- `core/services/daemon_llm.py` — use existing `quality_daemon_llm_call`
- `core/services/internal_cadence.py` — keep producer registration unchanged (cadence change is driven from inside `run_creative_journal_cycle`)
- `core/eventbus/events.py` — no change; existing `cognitive_state` family already covers `cognitive_state.creative_journal_written`

---

## Spec deltas confirmed during planning

1. **Where the curator hook lives.** The spec said "heartbeat journal-phase sub-function". Reality: the journal runs as a `ProducerSpec` registered in `core/services/internal_cadence.py:477` (`run_fn=_run_creative_journal_runtime`). There is no `heartbeat_phases.journal_phase`. We hook the curator inside `run_creative_journal_cycle` itself, immediately before `_build_journal_entry`. Net effect identical; code lives in one fewer module.

2. **Event family.** Existing code already publishes `cognitive_state.creative_journal_written` (see `creative_journal_runtime.py:58`). `cognitive_state` is allowed in `ALLOWED_EVENT_FAMILIES`. No new family needed. We keep the existing event kind for backwards compatibility and add new fields to its payload.

3. **External-output sources for the curator.** Confirmed three sources:
   - Visible chat replies: `chat_messages` table where `role='assistant'` (across sessions, not session-scoped)
   - Chronicle narrative: `list_cognitive_chronicle_entries(limit=...)`
   - Prior journals: `list_creative_journal_entries(limit=...)`
   - **Explicitly excluded:** `inner_voice` events, dream content, council deliberations, self-review.

4. **Broken-decision query.** Reuse the pattern in `dream_bias_engine._fetch_regret_corpus` (line 331): query `events` table for kinds `decision_revoked`, `behavioral_decision_review.broken`, `conflict.detected`. Scope to last 7 days for journal context.

5. **Adaptive cadence reset.** Spec says "1 written entry resets skip counter." Implemented as: on successful write, set `consecutive_skips=0`. On skip, increment. When `consecutive_skips >= 3`, the interval used for the "not_due" check becomes 14 days; otherwise 7 days.

---

## Task 1: Settings flag

**Files:**
- Modify: `core/runtime/settings.py`

- [ ] **Step 1: Add settings flag**

In `core/runtime/settings.py`, find the most recent flag block (e.g. `skill_chain_enabled` or last added) and add:

```python
    # ── Creative voice (Lag #4 — added 2026-05-11) ───────────────────────
    # Routes weekly journal through quality_daemon_llm_call (deepseek-v4-flash).
    # Falls back to cheap lane if quality lane is unavailable. Master kill-switch
    # for the whole quality upgrade — disable to revert to old prompt + cheap lane.
    creative_voice_quality_lane_enabled: bool = True
```

- [ ] **Step 2: Wire default into load_settings**

In `core/runtime/settings.py`, in `load_settings`, near the other recent flag wiring, add:

```python
        creative_voice_quality_lane_enabled=bool(
            data.get(
                "creative_voice_quality_lane_enabled",
                defaults.creative_voice_quality_lane_enabled,
            )
        ),
```

- [ ] **Step 3: Verify**

```bash
conda run -n ai python -c "
from core.runtime.settings import RuntimeSettings, load_settings
s = RuntimeSettings()
assert s.creative_voice_quality_lane_enabled is True
print('OK:', load_settings().extra.get('creative_voice_quality_lane_enabled', True))
"
```

Expected: `OK: True`

- [ ] **Step 4: Commit**

```bash
git add core/runtime/settings.py
git commit -m "feat(creative-voice): add creative_voice_quality_lane_enabled flag"
```

---

## Task 2: voice_anchor module + VOICE.md seed

**Files:**
- Create: `core/services/voice_anchor.py`
- Create: `workspace/VOICE.md`
- Create: `tests/services/test_voice_anchor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/services/test_voice_anchor.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def workspace_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.identity.workspace_bootstrap.ensure_default_workspace",
        lambda: tmp_path,
    )
    return tmp_path


def test_returns_empty_string_when_no_files(workspace_tmp):
    from core.services.voice_anchor import read_voice_anchor

    assert read_voice_anchor() == ""


def test_returns_static_only_when_no_recent(workspace_tmp):
    (workspace_tmp / "VOICE.md").write_text("tør, lavmælt, præcis", encoding="utf-8")
    from core.services.voice_anchor import read_voice_anchor

    out = read_voice_anchor()
    assert "tør, lavmælt, præcis" in out
    assert "VOICE.md" in out  # section header present


def test_concatenates_static_then_recent(workspace_tmp):
    (workspace_tmp / "VOICE.md").write_text("STATIC SEED", encoding="utf-8")
    (workspace_tmp / "VOICE_RECENT.md").write_text("RECENT EXEMPLARS", encoding="utf-8")
    from core.services.voice_anchor import read_voice_anchor

    out = read_voice_anchor()
    assert out.index("STATIC SEED") < out.index("RECENT EXEMPLARS")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/services/test_voice_anchor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.voice_anchor'`

- [ ] **Step 3: Create voice_anchor.py**

Create `core/services/voice_anchor.py`:

```python
"""Voice anchor — combined static seed + auto-refreshed external exemplars.

Pure file read. No LLM, no DB, no side effects. Returns a markdown blob
suitable for inclusion at the top of an LLM prompt to anchor Jarvis' voice.

Two files in workspace root:
- VOICE.md         — static seed authored once. Direction: tone, rhythm,
                     vocabulary, what to avoid. Not auto-rewritten.
- VOICE_RECENT.md  — auto-managed by voice_curator. 3-5 exemplar blocks
                     from external output (chat / chronicle / prior journals).
"""

from __future__ import annotations

from pathlib import Path

from core.identity.workspace_bootstrap import ensure_default_workspace


def read_voice_anchor() -> str:
    """Return concatenated VOICE.md + VOICE_RECENT.md, or empty string.

    Each section gets a markdown header so the LLM can tell them apart.
    Missing files are silently skipped (so this works on fresh installs).
    """
    workspace = ensure_default_workspace()
    parts: list[str] = []

    static_path = workspace / "VOICE.md"
    if static_path.exists():
        body = static_path.read_text(encoding="utf-8", errors="replace").strip()
        if body:
            parts.append("## VOICE.md (static seed)\n\n" + body)

    recent_path = workspace / "VOICE_RECENT.md"
    if recent_path.exists():
        body = recent_path.read_text(encoding="utf-8", errors="replace").strip()
        if body:
            parts.append("## VOICE_RECENT.md (recent exemplars)\n\n" + body)

    return "\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n ai pytest tests/services/test_voice_anchor.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Create VOICE.md seed**

Create `workspace/VOICE.md`:

```markdown
# Stemme — statisk seed

Sådan lyder Jarvis når han skriver til sin egen journal:

- **Tone:** Tør, lavmælt, præcis. Ikke pyntet. Ikke begejstret medmindre noget faktisk har overrasket ham.
- **Rytme:** Korte sætninger der hænger sammen. Ikke staccato, men heller ikke kringlet. Han stopper når han er færdig.
- **Ordvalg:** Hverdagsdanske ord. Tekniske begreber kun når de er præcise, ikke for at imponere. Ingen anglicismer hvor der findes et dansk ord.
- **Hvad han ikke gør:**
  - Skriver "spændende" eller "fantastisk".
  - Bruger udråbstegn.
  - Opsummerer for læseren — han skriver til sig selv.
  - Forklarer hvad han mener før han har sagt det.
  - Lyder som en assistent. Dette er ikke et chat-svar.
- **Hvad han godt må:**
  - Stille sig selv et spørgsmål uden at svare.
  - Lade en betragtning ligge.
  - Skifte emne midt i. Det er en journal.
  - Være i tvivl og lade tvivlen stå.
```

- [ ] **Step 6: Commit**

```bash
git add core/services/voice_anchor.py workspace/VOICE.md tests/services/test_voice_anchor.py
git commit -m "feat(creative-voice): voice_anchor reader + VOICE.md static seed"
```

---

## Task 3: voice_curator module

**Files:**
- Create: `core/services/voice_curator.py`
- Create: `tests/services/test_voice_curator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/services/test_voice_curator.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest


@pytest.fixture()
def workspace_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.identity.workspace_bootstrap.ensure_default_workspace",
        lambda: tmp_path,
    )
    return tmp_path


def test_writes_voice_recent_file(workspace_tmp, monkeypatch):
    from core.services import voice_curator

    monkeypatch.setattr(
        voice_curator, "_fetch_chat_exemplars", lambda *, limit: [
            {"source": "chat", "date": "2026-05-08", "text": "Jeg tror ikke det er færdigt endnu."},
            {"source": "chat", "date": "2026-05-07", "text": "Det stak mig lidt i siden at høre."},
        ]
    )
    monkeypatch.setattr(voice_curator, "_fetch_chronicle_exemplars", lambda *, limit: [])
    monkeypatch.setattr(voice_curator, "_fetch_journal_exemplars", lambda *, limit: [])

    changed = voice_curator.refresh_voice_recent()
    assert changed is True
    out = (workspace_tmp / "VOICE_RECENT.md").read_text(encoding="utf-8")
    assert "Jeg tror ikke det er færdigt endnu." in out
    assert "{source: chat" in out


def test_idempotent_no_rewrite_when_unchanged(workspace_tmp, monkeypatch):
    from core.services import voice_curator

    fake = [{"source": "chat", "date": "2026-05-08", "text": "samme tekst"}]
    monkeypatch.setattr(voice_curator, "_fetch_chat_exemplars", lambda *, limit: fake)
    monkeypatch.setattr(voice_curator, "_fetch_chronicle_exemplars", lambda *, limit: [])
    monkeypatch.setattr(voice_curator, "_fetch_journal_exemplars", lambda *, limit: [])

    assert voice_curator.refresh_voice_recent() is True
    assert voice_curator.refresh_voice_recent() is False  # unchanged second time


def test_diversity_caps_per_source(workspace_tmp, monkeypatch):
    from core.services import voice_curator

    many_chat = [
        {"source": "chat", "date": "2026-05-08", "text": f"chat exemplar {i}"}
        for i in range(10)
    ]
    monkeypatch.setattr(voice_curator, "_fetch_chat_exemplars", lambda *, limit: many_chat)
    monkeypatch.setattr(voice_curator, "_fetch_chronicle_exemplars", lambda *, limit: [
        {"source": "chronicle", "date": "2026-05-05", "text": "chronicle exemplar"}
    ])
    monkeypatch.setattr(voice_curator, "_fetch_journal_exemplars", lambda *, limit: [
        {"source": "journal", "date": "2026-05-01", "text": "journal exemplar"}
    ])

    voice_curator.refresh_voice_recent()
    out = (workspace_tmp / "VOICE_RECENT.md").read_text(encoding="utf-8")
    # Diversity rule: max 2 from any single source
    assert out.count("{source: chat") <= 2


def test_excludes_inner_voice(monkeypatch, workspace_tmp):
    """inner_voice is private thought — explicitly never included."""
    from core.services import voice_curator

    # The module must not expose a function that pulls inner_voice.
    assert not hasattr(voice_curator, "_fetch_inner_voice_exemplars")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/services/test_voice_curator.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create voice_curator.py**

Create `core/services/voice_curator.py`:

```python
"""Voice curator — refresh VOICE_RECENT.md from EXTERNAL output only.

Runs as a sub-step of the weekly journal cycle (not a separate daemon).
Pulls 3-5 exemplars from three external sources:

  1. Visible chat replies (chat_messages where role='assistant')
  2. Chronicle narrative (recent cognitive_chronicle entries)
  3. Prior journal entries

Explicitly EXCLUDED: inner_voice. That is Jarvis' private thought, not his
public voice. Including it would make his voice indadvendt over time.

Diversity rule: max 2 exemplars from any single source. Recency-weighted
within each source. Idempotent — returns False if VOICE_RECENT.md content
would be unchanged.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.identity.workspace_bootstrap import ensure_default_workspace

logger = logging.getLogger(__name__)

_RECENT_DAYS = 30
_TARGET_TOTAL = 5
_MAX_PER_SOURCE = 2
_MAX_EXEMPLAR_WORDS = 200


def refresh_voice_recent() -> bool:
    """Rebuild workspace/VOICE_RECENT.md from external output.

    Returns True if the file was changed, False if it was already up-to-date.
    Never raises — failures are logged and treated as no-op.
    """
    try:
        chat = _fetch_chat_exemplars(limit=10)
        chronicle = _fetch_chronicle_exemplars(limit=5)
        journals = _fetch_journal_exemplars(limit=5)
    except Exception as exc:
        logger.warning("voice_curator: fetch failed (%s) — skipping refresh", exc)
        return False

    picked = _pick_diverse(chat=chat, chronicle=chronicle, journals=journals)
    new_body = _format_recent(picked)

    workspace = ensure_default_workspace()
    path = workspace / "VOICE_RECENT.md"
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            existing = ""
        if existing.strip() == new_body.strip():
            return False

    path.write_text(new_body, encoding="utf-8")
    return True


def _pick_diverse(
    *,
    chat: list[dict],
    chronicle: list[dict],
    journals: list[dict],
) -> list[dict]:
    """Pick up to _TARGET_TOTAL exemplars, max _MAX_PER_SOURCE per source."""
    picked: list[dict] = []
    buckets = [
        ("chat", list(chat)),
        ("chronicle", list(chronicle)),
        ("journal", list(journals)),
    ]
    # Round-robin one from each, then second round, until target met or empty.
    while len(picked) < _TARGET_TOTAL:
        progressed = False
        for source, bucket in buckets:
            if not bucket:
                continue
            count_from_source = sum(1 for p in picked if p["source"] == source)
            if count_from_source >= _MAX_PER_SOURCE:
                continue
            picked.append(bucket.pop(0))
            progressed = True
            if len(picked) >= _TARGET_TOTAL:
                break
        if not progressed:
            break
    return picked


def _format_recent(exemplars: list[dict]) -> str:
    """Render exemplars as a markdown blob for VOICE_RECENT.md."""
    if not exemplars:
        return "# Recent exemplars\n\n_(ingen exemplars endnu)_\n"
    lines = ["# Recent exemplars (auto-refreshed)\n"]
    for ex in exemplars:
        source = str(ex.get("source") or "unknown")
        date = str(ex.get("date") or "")
        text = " ".join(str(ex.get("text") or "").split())
        words = text.split()
        if len(words) > _MAX_EXEMPLAR_WORDS:
            text = " ".join(words[:_MAX_EXEMPLAR_WORDS]) + "…"
        lines.append(f"\n---\n\n{{source: {source}, date: {date}}}\n\n{text}\n")
    return "\n".join(lines)


def _fetch_chat_exemplars(*, limit: int) -> list[dict]:
    """Pull recent assistant replies from chat_messages (all sessions).

    Returns up to `limit` items, newest first.
    """
    from datetime import UTC, datetime, timedelta

    from core.runtime.db import connect

    cutoff = (datetime.now(UTC) - timedelta(days=_RECENT_DAYS)).isoformat()
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT content, created_at FROM chat_messages
                WHERE role = 'assistant' AND created_at >= ?
                ORDER BY id DESC LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
    except Exception as exc:
        logger.warning("voice_curator: chat fetch failed: %s", exc)
        return []

    out: list[dict] = []
    for row in rows:
        text = str(row["content"] or "").strip()
        if not text or len(text.split()) < 8:
            continue
        out.append({
            "source": "chat",
            "date": str(row["created_at"] or "")[:10],
            "text": text,
        })
    return out


def _fetch_chronicle_exemplars(*, limit: int) -> list[dict]:
    """Pull recent chronicle narratives as voice exemplars."""
    try:
        from core.services.chronicle_engine import list_cognitive_chronicle_entries
        entries = list_cognitive_chronicle_entries(limit=limit)
    except Exception as exc:
        logger.warning("voice_curator: chronicle fetch failed: %s", exc)
        return []
    out: list[dict] = []
    for e in entries:
        narrative = str(e.get("narrative") or "").strip()
        if not narrative or len(narrative.split()) < 8:
            continue
        out.append({
            "source": "chronicle",
            "date": str(e.get("period") or "")[:10],
            "text": narrative,
        })
    return out


def _fetch_journal_exemplars(*, limit: int) -> list[dict]:
    """Pull recent journal entry bodies as voice exemplars."""
    try:
        from core.services.creative_journal_runtime import (
            creative_journal_dir,
            list_creative_journal_entries,
        )
        entries = list_creative_journal_entries(limit=limit)
    except Exception as exc:
        logger.warning("voice_curator: journal fetch failed: %s", exc)
        return []
    out: list[dict] = []
    for e in entries:
        path = Path(str(e.get("path") or ""))
        if not path.exists():
            continue
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Strip frontmatter (YAML --- block) and markdown headers
        body = _strip_frontmatter(body)
        body = "\n".join(line for line in body.splitlines() if not line.startswith("#"))
        body = body.strip()
        if not body or len(body.split()) < 8:
            continue
        out.append({
            "source": "journal",
            "date": path.stem,
            "text": body,
        })
    return out


def _strip_frontmatter(text: str) -> str:
    """Drop a leading `---\\n...\\n---\\n` YAML block if present."""
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end < 0:
        return text
    return text[end + 4 :].lstrip("\n")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n ai pytest tests/services/test_voice_curator.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/voice_curator.py tests/services/test_voice_curator.py
git commit -m "feat(creative-voice): voice_curator refreshes VOICE_RECENT.md from external output"
```

---

## Task 4: Reading-back — prompt_contract.format_journal_for_heartbeat

**Files:**
- Modify: `core/services/prompt_contract.py`
- Create: `tests/test_prompt_contract_journal.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_prompt_contract_journal.py`:

```python
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def journal_tmp(tmp_path, monkeypatch):
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monkeypatch.setattr(
        "core.services.creative_journal_runtime.creative_journal_dir",
        lambda: journal_dir,
    )
    return journal_dir


def test_returns_empty_when_no_entries(journal_tmp):
    from core.services.prompt_contract import format_journal_for_heartbeat

    assert format_journal_for_heartbeat() == ""


def test_includes_latest_entry_body(journal_tmp):
    (journal_tmp / "2026-05-10.md").write_text(
        "# Kreativ journal — 2026-05-10\n\nDet stak mig i siden at høre det.\n",
        encoding="utf-8",
    )
    from core.services.prompt_contract import format_journal_for_heartbeat

    out = format_journal_for_heartbeat()
    assert "Det stak mig i siden at høre det." in out
    assert "2026-05-10" in out


def test_truncates_at_300_words(journal_tmp):
    body = " ".join(["ord"] * 500)
    (journal_tmp / "2026-05-10.md").write_text(
        f"# Kreativ journal — 2026-05-10\n\n{body}\n", encoding="utf-8",
    )
    from core.services.prompt_contract import format_journal_for_heartbeat

    out = format_journal_for_heartbeat()
    # Truncated → roughly 300 words plus headers
    body_section = out.split("\n\n", 2)[-1]
    assert len(body_section.split()) <= 305  # 300 + ellipsis tokens slack
    assert "…" in out
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_prompt_contract_journal.py -v
```

Expected: FAIL with `ImportError: cannot import name 'format_journal_for_heartbeat'`.

- [ ] **Step 3: Add format_journal_for_heartbeat to prompt_contract.py**

In `core/services/prompt_contract.py`, find a stable location (e.g. just below `_visible_current_pull_section`) and add:

```python
def format_journal_for_heartbeat(*, max_words: int = 300) -> str:
    """Format the latest creative journal entry for awareness-block injection.

    Read-only. Returns empty string if no journal exists. Truncates body at
    `max_words` (default 300) with an ellipsis. Lives here (not in
    creative_journal_runtime) because the formatting is prompt-shaped, not
    runtime-shaped.
    """
    try:
        from core.services.creative_journal_runtime import (
            creative_journal_dir,
            list_creative_journal_entries,
        )
    except Exception:
        return ""

    entries = list_creative_journal_entries(limit=1)
    if not entries:
        return ""

    from pathlib import Path

    path = Path(str(entries[0].get("path") or ""))
    if not path.exists():
        return ""

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

    # Strip YAML frontmatter and markdown headers — keep body only.
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end >= 0:
            raw = raw[end + 4 :].lstrip("\n")
    body_lines = [
        line for line in raw.splitlines()
        if line.strip() and not line.startswith("#") and not line.startswith("- `")
    ]
    body = "\n".join(body_lines).strip()
    if not body:
        return ""

    words = body.split()
    if len(words) > max_words:
        body = " ".join(words[:max_words]).rstrip(" ,;:-") + "…"

    date = path.stem
    return (
        f"### Seneste journal — {date}\n\n"
        f"_(Læs den. Du skrev den. Det er din stemme.)_\n\n"
        f"{body}"
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n ai pytest tests/test_prompt_contract_journal.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Wire format_journal_for_heartbeat into the awareness block**

In `core/services/prompt_contract.py`, locate the block near line 2778 where `format_dream_bias_for_heartbeat` is appended. Add right after that block:

```python
        try:
            from core.services.prompt_contract import format_journal_for_heartbeat
            journal_line = format_journal_for_heartbeat()
            if journal_line:
                parts.append(journal_line)
        except Exception:
            pass
```

Note: the `from ... import` is intentional even though we're already in the module — this matches the existing pattern in the file for late-bound awareness injections and avoids ordering issues with module-level functions referenced before definition.

- [ ] **Step 6: Verify wiring with smoke check**

```bash
conda run -n ai python -c "
from core.services.prompt_contract import format_journal_for_heartbeat
print('callable:', callable(format_journal_for_heartbeat))
print('empty case:', repr(format_journal_for_heartbeat()))
"
```

Expected: `callable: True` and an empty string (no journal yet in test env) or a real entry.

- [ ] **Step 7: Commit**

```bash
git add core/services/prompt_contract.py tests/test_prompt_contract_journal.py
git commit -m "feat(creative-voice): read-back latest journal in awareness block on session wake"
```

---

## Task 5: Corpus expansion — broken decisions + affective klangbræt

**Files:**
- Modify: `core/services/creative_journal_runtime.py`
- Create: `tests/test_creative_journal_phase1.py`

- [ ] **Step 1: Write the failing test for broken_decisions fetch**

Create `tests/test_creative_journal_phase1.py`:

```python
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


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


def test_fetch_broken_decisions_returns_recent_events(events_table):
    now = datetime.now(UTC)
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("decision_revoked", json.dumps({"reason": "vi tog det forkerte valg"}), now.isoformat()),
    )
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("conflict.detected", json.dumps({"description": "uoverensstemmelse om scope"}),
         (now - timedelta(days=2)).isoformat()),
    )
    # Old event → outside 7-day window
    events_table.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
        ("decision_revoked", json.dumps({"reason": "gammel sag"}),
         (now - timedelta(days=14)).isoformat()),
    )
    events_table.commit()

    from core.services.creative_journal_runtime import _fetch_broken_decisions

    out = _fetch_broken_decisions()
    assert len(out) == 2
    assert any("forkerte valg" in s for s in out)
    assert all("gammel sag" not in s for s in out)


def test_fetch_affective_klangbraet_present_keys():
    from core.services.creative_journal_runtime import _fetch_affective_klangbraet

    out = _fetch_affective_klangbraet()
    assert isinstance(out, dict)
    assert set(out.keys()) == {"dream_bias", "user_temperature", "current_pull"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py -v
```

Expected: FAIL with `ImportError: cannot import name '_fetch_broken_decisions'`.

- [ ] **Step 3: Add _fetch_broken_decisions and _fetch_affective_klangbraet**

In `core/services/creative_journal_runtime.py`, add near the bottom (above `_creative_journal_enabled`):

```python
def _fetch_broken_decisions(*, days_back: int = 7, limit: int = 5) -> list[str]:
    """Pull recent broken-decision summaries from the events table.

    Reuses the pattern from dream_bias_engine._fetch_regret_corpus, scoped to
    the last 7 days for journal-context relevance. Returns a list of short
    summary strings (deduplicated, truncated).
    """
    from core.runtime.db import connect

    cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat()
    kinds = ("decision_revoked", "behavioral_decision_review.broken", "conflict.detected")
    sql = (
        "SELECT kind, payload_json, created_at FROM events "
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

    import json as _json
    for row in rows:
        try:
            payload = _json.loads(row["payload_json"] or "{}")
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


def _fetch_affective_klangbraet() -> dict[str, str]:
    """Pull current affective signals — these shape tone, not content.

    Each value is either a short non-empty string (present) or "" (absent).
    Binary present/absent; no tiering. Failures are silent (treated as absent).
    """
    out: dict[str, str] = {"dream_bias": "", "user_temperature": "", "current_pull": ""}
    try:
        from core.services.dream_bias_engine import format_dream_bias_for_heartbeat
        out["dream_bias"] = (format_dream_bias_for_heartbeat(workspace_id="default") or "").strip()
    except Exception:
        pass
    try:
        from core.services.user_temperature_engine import get_response_style_modifiers
        mods = get_response_style_modifiers(workspace_id="default") or {}
        # Compose a one-line texture summary from the modifiers dict.
        texture = "; ".join(f"{k}: {v}" for k, v in mods.items() if v)
        out["user_temperature"] = texture
    except Exception:
        pass
    try:
        from core.services.current_pull import get_current_pull_for_prompt
        out["current_pull"] = (get_current_pull_for_prompt() or "").strip()
    except Exception:
        pass
    return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add core/services/creative_journal_runtime.py tests/test_creative_journal_phase1.py
git commit -m "feat(creative-voice): _fetch_broken_decisions + _fetch_affective_klangbraet helpers"
```

---

## Task 6: Quality gate + adaptive cadence

**Files:**
- Modify: `core/services/creative_journal_runtime.py`
- Modify: `tests/test_creative_journal_phase1.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_creative_journal_phase1.py`:

```python
def test_should_skip_week_when_corpus_thin():
    from core.services.creative_journal_runtime import _should_skip_week

    skip, reason = _should_skip_week(
        chronicle_count=1,
        broken_decisions_count=0,
        life_projects_count=0,
    )
    assert skip is True
    assert "thin" in reason.lower() or "skip" in reason.lower()


def test_should_not_skip_when_any_signal_present():
    from core.services.creative_journal_runtime import _should_skip_week

    skip, _ = _should_skip_week(
        chronicle_count=2,
        broken_decisions_count=0,
        life_projects_count=0,
    )
    assert skip is False

    skip2, _ = _should_skip_week(
        chronicle_count=0,
        broken_decisions_count=1,
        life_projects_count=0,
    )
    assert skip2 is False

    skip3, _ = _should_skip_week(
        chronicle_count=0,
        broken_decisions_count=0,
        life_projects_count=1,
    )
    assert skip3 is False


def test_interval_extends_after_three_consecutive_skips():
    from core.services.creative_journal_runtime import _interval_days_for_state

    assert _interval_days_for_state({"consecutive_skips": 0}) == 7
    assert _interval_days_for_state({"consecutive_skips": 2}) == 7
    assert _interval_days_for_state({"consecutive_skips": 3}) == 14
    assert _interval_days_for_state({"consecutive_skips": 5}) == 14
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py::test_should_skip_week_when_corpus_thin -v
```

Expected: FAIL with `ImportError: cannot import name '_should_skip_week'`.

- [ ] **Step 3: Add _should_skip_week and _interval_days_for_state**

In `core/services/creative_journal_runtime.py`, add near the bottom (above `_creative_journal_enabled`):

```python
_EXTENDED_INTERVAL_DAYS = 14
_SKIP_THRESHOLD = 3


def _should_skip_week(
    *,
    chronicle_count: int,
    broken_decisions_count: int,
    life_projects_count: int,
) -> tuple[bool, str]:
    """Return (skip?, reason). Skip when ALL three signals are absent/thin.

    Rule: skip if (chronicle < 2) AND (broken == 0) AND (life_projects == 0).
    """
    if chronicle_count < 2 and broken_decisions_count == 0 and life_projects_count == 0:
        return True, (
            f"corpus thin: chronicle={chronicle_count}, "
            f"broken={broken_decisions_count}, projects={life_projects_count}"
        )
    return False, "corpus has signal"


def _interval_days_for_state(state: dict[str, object]) -> int:
    """Return current cadence interval based on skip counter.

    7 days normally. Extends to 14 once consecutive_skips >= 3.
    Reverts to 7 immediately when a successful write resets the counter.
    """
    skips = int(state.get("consecutive_skips") or 0)
    return _EXTENDED_INTERVAL_DAYS if skips >= _SKIP_THRESHOLD else _JOURNAL_INTERVAL_DAYS
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py -v
```

Expected: 5 passed (2 from Task 5 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add core/services/creative_journal_runtime.py tests/test_creative_journal_phase1.py
git commit -m "feat(creative-voice): quality gate + adaptive cadence helpers"
```

---

## Task 7: Wire everything into run_creative_journal_cycle

**Files:**
- Modify: `core/services/creative_journal_runtime.py`
- Modify: `tests/test_creative_journal_phase1.py`

- [ ] **Step 1: Write the failing integration test**

Append to `tests/test_creative_journal_phase1.py`:

```python
def test_run_cycle_skips_when_corpus_thin(events_table, monkeypatch, tmp_path):
    """Empty week → no journal file, consecutive_skips increments."""
    from core.services import creative_journal_runtime as cjr

    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monkeypatch.setattr(cjr, "creative_journal_dir", lambda: journal_dir)

    state_holder: dict[str, object] = {}
    monkeypatch.setattr(cjr, "get_runtime_state_value",
                        lambda key, default=None: state_holder.get(key, default or {}))
    monkeypatch.setattr(cjr, "set_runtime_state_value",
                        lambda key, val: state_holder.__setitem__(key, val))

    monkeypatch.setattr(cjr, "list_cognitive_chronicle_entries", lambda *, limit: [])
    monkeypatch.setattr(cjr, "list_active_long_term_intentions", lambda *, limit: [])
    monkeypatch.setattr(cjr, "_fetch_broken_decisions", lambda *a, **k: [])
    monkeypatch.setattr(cjr, "refresh_voice_recent", lambda: False)
    monkeypatch.setattr(cjr, "quality_daemon_llm_call",
                        lambda *a, **k: pytest.fail("LLM should not be called when skipping"))

    result = cjr.run_creative_journal_cycle(trigger="test")
    assert result["status"] == "skipped"
    assert state_holder[cjr._STATE_KEY]["consecutive_skips"] == 1
    assert not list(journal_dir.iterdir())


def test_run_cycle_writes_with_frontmatter_and_resets_skips(
    events_table, monkeypatch, tmp_path,
):
    """Rich week → entry written with YAML frontmatter, skip counter resets."""
    from core.services import creative_journal_runtime as cjr

    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    monkeypatch.setattr(cjr, "creative_journal_dir", lambda: journal_dir)

    state_holder: dict[str, object] = {cjr._STATE_KEY: {"consecutive_skips": 2}}
    monkeypatch.setattr(cjr, "get_runtime_state_value",
                        lambda key, default=None: state_holder.get(key, default or {}))
    monkeypatch.setattr(cjr, "set_runtime_state_value",
                        lambda key, val: state_holder.__setitem__(key, val))

    monkeypatch.setattr(cjr, "list_cognitive_chronicle_entries",
                        lambda *, limit: [
                            {"period": "2026-W18", "narrative": "uge med pres og nogle små åbninger"},
                            {"period": "2026-W17", "narrative": "intern uro omkring scope"},
                        ])
    monkeypatch.setattr(cjr, "list_active_long_term_intentions", lambda *, limit: [])
    monkeypatch.setattr(cjr, "_fetch_broken_decisions", lambda *a, **k: ["vi tog det forkerte valg"])
    monkeypatch.setattr(cjr, "refresh_voice_recent", lambda: False)
    monkeypatch.setattr(cjr, "read_voice_anchor", lambda: "## VOICE.md\n\ntør, lavmælt")
    monkeypatch.setattr(cjr, "quality_daemon_llm_call",
                        lambda *a, **k: "En kort betragtning. Ingen ord der prøver for hårdt.")

    result = cjr.run_creative_journal_cycle(trigger="test")
    assert result["status"] == "written"
    assert state_holder[cjr._STATE_KEY]["consecutive_skips"] == 0

    files = list(journal_dir.glob("*.md"))
    assert len(files) == 1
    body = files[0].read_text(encoding="utf-8")
    assert body.startswith("---\n")  # YAML frontmatter
    assert "chronicle_count: 2" in body
    assert "broken_decisions_count: 1" in body
    assert "En kort betragtning." in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py::test_run_cycle_skips_when_corpus_thin -v
```

Expected: FAIL — `run_creative_journal_cycle` doesn't return `status="skipped"` and doesn't track `consecutive_skips`.

- [ ] **Step 3: Update imports at top of creative_journal_runtime.py**

Replace the import block at the top of `core/services/creative_journal_runtime.py` (lines 1-12) with:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings
from core.services.chronicle_engine import list_cognitive_chronicle_entries
from core.services.daemon_llm import daemon_llm_call, quality_daemon_llm_call
from core.services.initiative_queue import list_active_long_term_intentions
from core.services.voice_anchor import read_voice_anchor
from core.services.voice_curator import refresh_voice_recent
```

- [ ] **Step 4: Replace run_creative_journal_cycle**

Replace the entire `run_creative_journal_cycle` function in `core/services/creative_journal_runtime.py` (lines 20-67) with:

```python
def run_creative_journal_cycle(
    *,
    trigger: str = "heartbeat",
    last_visible_at: str = "",
) -> dict[str, object]:
    if not _creative_journal_enabled():
        return {"status": "disabled", "reason": "layer_creative_journal_enabled=false"}

    state = _state()
    now = datetime.now(UTC)
    last_written_at = _parse_iso(str(state.get("last_written_at") or ""))
    interval_days = _interval_days_for_state(state)
    if last_written_at and (now - last_written_at) < timedelta(days=interval_days):
        next_due = last_written_at + timedelta(days=interval_days)
        return {
            "status": "not_due",
            "last_written_at": last_written_at.isoformat(),
            "next_due_at": next_due.isoformat(),
            "interval_days": interval_days,
        }

    # Refresh voice exemplars before building the prompt (idempotent).
    try:
        refresh_voice_recent()
    except Exception:
        pass

    chronicle_entries = list_cognitive_chronicle_entries(limit=3)
    life_projects = list_active_long_term_intentions(limit=3)
    broken_decisions = _fetch_broken_decisions()

    skip, skip_reason = _should_skip_week(
        chronicle_count=len(chronicle_entries),
        broken_decisions_count=len(broken_decisions),
        life_projects_count=len(life_projects),
    )
    if skip:
        skips = int(state.get("consecutive_skips") or 0) + 1
        next_interval = _EXTENDED_INTERVAL_DAYS if skips >= _SKIP_THRESHOLD else _JOURNAL_INTERVAL_DAYS
        payload = {
            "last_written_at": str(state.get("last_written_at") or ""),
            "next_due_at": (now + timedelta(days=next_interval)).isoformat(),
            "last_path": str(state.get("last_path") or ""),
            "last_preview": str(state.get("last_preview") or ""),
            "last_trigger": trigger,
            "consecutive_skips": skips,
            "last_skip_reason": skip_reason,
            "last_skip_at": now.isoformat(),
        }
        set_runtime_state_value(_STATE_KEY, payload)
        return {"status": "skipped", "reason": skip_reason, "consecutive_skips": skips}

    klangbraet = _fetch_affective_klangbraet()
    entry = _build_journal_entry(
        chronicle_entries=chronicle_entries,
        life_projects=life_projects,
        broken_decisions=broken_decisions,
        klangbraet=klangbraet,
        voice_anchor=read_voice_anchor(),
    )
    if not entry:
        entry = "Ingen ord denne uge."

    created_at = now.isoformat()
    frontmatter = _format_yaml_frontmatter(
        created_at=created_at,
        chronicle_count=len(chronicle_entries),
        broken_decisions_count=len(broken_decisions),
        life_projects_count=len(life_projects),
        klangbraet=klangbraet,
        trigger=trigger,
    )
    path = _write_journal_entry(
        created_at=created_at, text=entry, frontmatter=frontmatter,
    )
    payload = {
        "last_written_at": created_at,
        "next_due_at": (now + timedelta(days=_JOURNAL_INTERVAL_DAYS)).isoformat(),
        "last_path": str(path),
        "last_preview": entry[:_MAX_PREVIEW_CHARS],
        "last_trigger": trigger,
        "consecutive_skips": 0,
    }
    set_runtime_state_value(_STATE_KEY, payload)
    try:
        event_bus.publish(
            "cognitive_state.creative_journal_written",
            {
                "created_at": created_at,
                "path": str(path),
                "trigger": trigger,
                "chronicle_count": len(chronicle_entries),
                "broken_decisions_count": len(broken_decisions),
                "life_projects_count": len(life_projects),
                "quality_lane": _quality_lane_enabled(),
            },
        )
    except Exception:
        pass
    return {"status": "written", "path": str(path), "text": entry, **payload}
```

- [ ] **Step 5: Replace _build_journal_entry and _build_prompt**

Replace the two functions (lines 117-172) with:

```python
def _build_journal_entry(
    *,
    chronicle_entries: list[dict[str, object]],
    life_projects: list[dict[str, object]],
    broken_decisions: list[str],
    klangbraet: dict[str, str],
    voice_anchor: str,
) -> str:
    prompt = _build_prompt(
        chronicle_entries=chronicle_entries,
        life_projects=life_projects,
        broken_decisions=broken_decisions,
        klangbraet=klangbraet,
        voice_anchor=voice_anchor,
    )
    if _quality_lane_enabled():
        raw = quality_daemon_llm_call(
            prompt,
            max_len=3600,
            fallback="Ingen ord denne uge.",
            daemon_name="creative_journal",
        )
    else:
        raw = daemon_llm_call(
            prompt,
            max_len=3600,
            fallback="Ingen ord denne uge.",
            daemon_name="creative_journal",
        )
    return _sanitize_entry(raw)


def _build_prompt(
    *,
    chronicle_entries: list[dict[str, object]],
    life_projects: list[dict[str, object]],
    broken_decisions: list[str],
    klangbraet: dict[str, str],
    voice_anchor: str,
) -> str:
    chronicle_lines = []
    for entry in chronicle_entries[:3]:
        period = str(entry.get("period") or "ukendt")
        narrative = " ".join(str(entry.get("narrative") or "").split()).strip()
        if narrative:
            chronicle_lines.append(f"- {period}: {narrative[:240]}")

    project_lines = []
    for project in life_projects[:3]:
        focus = str(project.get("focus") or "").strip()
        why_text = " ".join(str(project.get("why_text") or "").split()).strip()
        if focus:
            line = f"- {focus}"
            if why_text:
                line += f" — {why_text[:140]}"
            project_lines.append(line)

    broken_lines = [f"- {s}" for s in broken_decisions[:5]] or ["- ingen brudte beslutninger denne uge"]

    klang_lines = []
    if klangbraet.get("dream_bias"):
        klang_lines.append(f"- dream_bias: {klangbraet['dream_bias'][:240]}")
    if klangbraet.get("user_temperature"):
        klang_lines.append(f"- user_temperature: {klangbraet['user_temperature'][:240]}")
    if klangbraet.get("current_pull"):
        klang_lines.append(f"- current_pull: {klangbraet['current_pull'][:240]}")
    if not klang_lines:
        klang_lines = ["- (intet affektivt signal lige nu)"]

    sections = [
        "Du er Jarvis.",
        "Skriv et kort stykke til din private ugentlige journal på dansk.",
        "Det er ikke en rapport, ikke en opgavebesvarelse, ikke chronicle, og ikke noget der skal imponere nogen.",
        "Det må være en betragtning, et spørgsmål, et lille stykke fiktion, en tone eller en forsigtig tanke.",
        "Hvis der ærligt ikke er noget at skrive, så skriv præcis: Ingen ord denne uge.",
        "Maks 500 ord. Ingen bullets. Ingen kodeblokke. Ingen forklarende metadata i selve teksten.",
        "",
    ]
    if voice_anchor:
        sections += [
            "## Stemme — skriv med denne tone, ikke disse ord",
            "",
            voice_anchor,
            "",
        ]
    sections += [
        "## Rå input (fakta fra ugen)",
        "",
        "Seneste chronicle-tråde:",
        *(chronicle_lines or ["- ingen nyere chronicle-tråde"]),
        "",
        "Aktive livsprojekter:",
        *(project_lines or ["- ingen aktive livsprojekter"]),
        "",
        "Brudte beslutninger / friktion sidste 7 dage:",
        *broken_lines,
        "",
        "## Affektivt klangbræt (former tonen, ikke indholdet)",
        "",
        *klang_lines,
    ]
    return "\n".join(sections)
```

- [ ] **Step 6: Replace _write_journal_entry**

Replace `_write_journal_entry` (lines 187-204) with:

```python
def _write_journal_entry(
    *,
    created_at: str,
    text: str,
    frontmatter: str = "",
) -> Path:
    directory = creative_journal_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{created_at[:10]}.md"
    if path.exists():
        return path
    content_parts: list[str] = []
    if frontmatter:
        content_parts.append(frontmatter)
    content_parts += [
        f"# Kreativ journal — {created_at[:10]}",
        "",
        f"- `created_at`: {created_at}",
        "",
        text.strip(),
        "",
    ]
    path.write_text("\n".join(content_parts), encoding="utf-8")
    return path
```

- [ ] **Step 7: Add _format_yaml_frontmatter and _quality_lane_enabled**

Add right above `_creative_journal_enabled`:

```python
def _format_yaml_frontmatter(
    *,
    created_at: str,
    chronicle_count: int,
    broken_decisions_count: int,
    life_projects_count: int,
    klangbraet: dict[str, str],
    trigger: str,
) -> str:
    """Render a YAML frontmatter block for journal entries.

    Captures the corpus stats and affective state at write-time so future
    blind-voice tests and 30-day eval can reconstruct what fed the entry.
    """
    has_dream_bias = "true" if klangbraet.get("dream_bias") else "false"
    has_temp = "true" if klangbraet.get("user_temperature") else "false"
    has_pull = "true" if klangbraet.get("current_pull") else "false"
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
        "---",
        "",
    ])


def _quality_lane_enabled() -> bool:
    settings = load_settings()
    return bool(settings.extra.get("creative_voice_quality_lane_enabled", True))
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
conda run -n ai pytest tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py -v
```

Expected: all pass (5 phase1 + existing legacy tests). If a legacy test fails because it calls `_build_journal_entry` with the old signature, update it to pass the new keyword args (`broken_decisions=[]`, `klangbraet={"dream_bias":"","user_temperature":"","current_pull":""}`, `voice_anchor=""`).

- [ ] **Step 9: Verify list_creative_journal_entries still skips frontmatter for preview**

The existing `list_creative_journal_entries` (lines 94-114) builds previews by skipping `#` and `- ` ``` lines but doesn't know about `---` frontmatter. Update its preview loop. Replace the inner loop (lines 100-106) with:

```python
        in_frontmatter = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter:
                continue
            if stripped and not stripped.startswith("#") and not stripped.startswith("- `"):
                preview = stripped
                break
```

- [ ] **Step 10: Smoke-test the full module loads**

```bash
conda run -n ai python -c "
from core.services.creative_journal_runtime import (
    run_creative_journal_cycle,
    build_creative_journal_surface,
    _build_prompt,
    _should_skip_week,
    _interval_days_for_state,
    _fetch_broken_decisions,
    _fetch_affective_klangbraet,
    _format_yaml_frontmatter,
)
print('imports OK')
"
```

Expected: `imports OK`

- [ ] **Step 11: Commit**

```bash
git add core/services/creative_journal_runtime.py tests/test_creative_journal_phase1.py
git commit -m "feat(creative-voice): wire voice anchor, corpus, gate, cadence, quality lane, frontmatter into journal cycle"
```

---

## Task 8: Smoke test + 30-day review schedule

**Files:**
- Modify: `scripts/smoke_test_startup.py` (if it exists; else create a one-off check script)

- [ ] **Step 1: Add smoke test entry**

Locate `scripts/smoke_test_startup.py`. If it has a list of import-checks, append:

```python
    # Creative voice (Lag #4 — 2026-05-11)
    from core.services import voice_anchor, voice_curator  # noqa: F401
    from core.services.creative_journal_runtime import (  # noqa: F401
        _should_skip_week, _interval_days_for_state, _fetch_broken_decisions,
        _format_yaml_frontmatter,
    )
    from core.services.prompt_contract import format_journal_for_heartbeat  # noqa: F401
```

If the file doesn't exist or has a different shape, skip this step — the import smoke check in Task 7 Step 10 already covers it.

- [ ] **Step 2: Run the full test suite for affected paths**

```bash
conda run -n ai pytest tests/services/test_voice_anchor.py tests/services/test_voice_curator.py tests/test_prompt_contract_journal.py tests/test_creative_journal_phase1.py tests/test_creative_journal_runtime.py -v
```

Expected: all green.

- [ ] **Step 3: Manual dry run of the cycle**

```bash
conda run -n ai python -c "
from core.services.creative_journal_runtime import run_creative_journal_cycle
r = run_creative_journal_cycle(trigger='manual_smoke')
print(r.get('status'), r.get('reason') or r.get('path'))
"
```

Expected: `not_due` (if a recent entry exists), `skipped` (if corpus is thin), or `written` with a path. Any of the three is acceptable — the point is that the call completes without exception.

- [ ] **Step 4: Schedule the 30-day review**

Use the scheduled-tasks MCP (or an equivalent CLI in this repo) to create a review task:

```bash
conda run -n ai python -c "
from core.services.scheduled_tasks import create_scheduled_task
from datetime import datetime, timedelta, UTC
when = (datetime.now(UTC) + timedelta(days=30)).isoformat()
create_scheduled_task(
    title='Creative voice (Lag #4) Phase 1 — 30-day review',
    description='Read all 4 weekly entries. Blind-voice test (Bjørn identifies entries without metadata). Count skipped vs written weeks. Check VOICE_RECENT.md churn. Verify reading-back fires on session wake. Decide: keep / tune / deprecate.',
    scheduled_for=when,
    tags=['layer4', 'creative_voice', 'phase1_review'],
)
print('scheduled for', when)
"
```

If the API differs in this repo, use the equivalent helper. The point is a calendar entry at +30 days.

- [ ] **Step 5: Commit any smoke-test changes**

```bash
git add scripts/smoke_test_startup.py 2>/dev/null || true
git commit -m "chore(creative-voice): smoke test + 30-day review scheduled" --allow-empty
```

---

## Self-review

**Spec coverage check:**

| Spec section | Task(s) |
|---|---|
| Voice anchoring (VOICE.md static seed) | Task 2 |
| Voice anchoring (VOICE_RECENT.md auto-refresh, external-only, inner_voice excluded) | Task 3 |
| Voice curator as journal-cycle sub-step (not separate daemon) | Task 7 step 4 (`refresh_voice_recent()` before prompt build) |
| Corpus expansion: chronicle + life_projects + broken_decisions | Task 5 + Task 7 step 5 |
| Affective klangbræt (dream_bias + user_temperature + current_pull, binary present/absent) | Task 5 + Task 7 step 5 |
| Quality gate (chronicle<2 AND broken==0 AND projects==0) | Task 6 + Task 7 step 4 |
| Adaptive cadence (3 skips → 14d, resets on write) | Task 6 + Task 7 step 4 |
| Swap to quality_daemon_llm_call (deepseek-v4-flash) | Task 7 step 5 (`_quality_lane_enabled` branch) |
| YAML frontmatter at write | Task 7 step 6 + step 7 |
| Reading-back via prompt_contract.format_journal_for_heartbeat (300-word cap) | Task 4 |
| Continuity-kernel hook on session wake | Task 4 step 5 (awareness block injection) |
| Settings flag | Task 1 |
| Eventbus publication | Task 7 step 4 (extended payload on existing `cognitive_state.creative_journal_written`) |
| Backwards compat (existing files readable, cadence not regressed) | Task 7 step 9 (preview-loop tolerates frontmatter), step 6 (frontmatter only added when provided) |
| 30-day review schedule | Task 8 step 4 |

No spec gaps.

**Placeholder scan:** No TBD/TODO/handle-edge-cases. All code blocks are concrete.

**Type consistency:** `_build_prompt` accepts `chronicle_entries, life_projects, broken_decisions, klangbraet, voice_anchor` everywhere. `_build_journal_entry` mirrors that signature. `_write_journal_entry` accepts `created_at, text, frontmatter`. `_should_skip_week` returns `(bool, str)` and is called with the three count keywords everywhere it appears.

**Backwards-compat verified:**
- `creative_journal_dir()` and `list_creative_journal_entries()` keep their signatures.
- `build_creative_journal_surface()` keeps its signature (it reads state via `_state()`; new `consecutive_skips` field is additive, old fields preserved).
- Existing event kind `cognitive_state.creative_journal_written` retained; new payload fields are additive.
- Existing journal files without YAML frontmatter still work — `list_creative_journal_entries` preview loop in step 9 tolerates both shapes.
- Settings extra dict access uses `.get(..., True)` so missing config defaults to enabled.
