# Council Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist council conclusions to `COUNCIL_LOG.md` and inject relevant past deliberations into heartbeat context via LLM similarity matching.

**Architecture:** `council_memory_service.py` owns all file I/O. `council_memory_daemon.py` owns the similarity check and injection logic. A `recall_council_conclusions` tool in `simple_tools.py` lets Jarvis explicitly retrieve past deliberations. Both autonomous and manual council flows call `append_council_conclusion()` on close.

**Tech Stack:** Python 3.11+, workspace markdown file at `~/.jarvis-v2/workspaces/default/COUNCIL_LOG.md`, `execute_cheap_lane` for LLM similarity, existing `_TOOL_HANDLERS` pattern in `simple_tools.py`.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `apps/api/jarvis_api/services/council_memory_service.py` | Create | Read/write COUNCIL_LOG.md |
| `apps/api/jarvis_api/services/council_memory_daemon.py` | Create | LLM similarity + heartbeat injection |
| `apps/api/jarvis_api/services/daemon_manager.py` | Modify | Add daemon #22 to `_REGISTRY` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify | Add daemon call after `autonomous_council` block |
| `apps/api/jarvis_api/services/signal_surface_router.py` | Modify | Register `council_memory` surface |
| `apps/api/jarvis_api/services/agent_runtime.py` | Modify | Call `append_council_conclusion` at council close |
| `apps/api/jarvis_api/services/autonomous_council_daemon.py` | Modify | Call `append_council_conclusion` after `_run_autonomous_council` |
| `core/tools/simple_tools.py` | Modify | Add `recall_council_conclusions` tool |
| `tests/test_council_memory_service.py` | Create | TDD tests for service |
| `tests/test_council_memory_daemon.py` | Create | TDD tests for daemon |
| `tests/test_daemon_tools.py` | Modify | Update daemon count 21 → 22, add recall tool test |

---

### Task 1: council_memory_service — failing tests

**Files:**
- Create: `tests/test_council_memory_service.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for council_memory_service — append and read."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch


def _make_service(tmp_path: Path):
    import apps.api.jarvis_api.services.council_memory_service as svc
    log_file = tmp_path / "COUNCIL_LOG.md"
    return svc, log_file


def test_append_creates_file_if_missing(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Hvad begrænser mig?",
            score=0.72,
            members=["filosof", "kritiker", "synthesizer"],
            signals=["autonomy_pressure", "open_loop"],
            transcript="filosof: ...\nkritiker: ...",
            conclusion="Rådet konkluderer at Jarvis bør prioritere autonomi.",
            initiative=None,
        )
    assert log_file.exists()


def test_append_writes_markdown_structure(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Hvad begrænser mig?",
            score=0.72,
            members=["filosof", "kritiker", "synthesizer"],
            signals=["autonomy_pressure", "open_loop"],
            transcript="filosof: ...\nkritiker: ...",
            conclusion="Rådet konkluderer.",
            initiative=None,
        )
    content = log_file.read_text(encoding="utf-8")
    assert "## " in content  # header present
    assert "Hvad begrænser mig?" in content
    assert "0.72" in content
    assert "filosof" in content
    assert "autonomy_pressure" in content
    assert "Rådet konkluderer." in content
    assert "### Transcript" in content
    assert "### Konklusion" in content


def test_append_writes_initiative_when_provided(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Test",
            score=0.60,
            members=["synthesizer"],
            signals=["desire"],
            transcript="x",
            conclusion="Done.",
            initiative="Jarvis should write a poem.",
        )
    content = log_file.read_text(encoding="utf-8")
    assert "### Initiative-forslag" in content
    assert "Jarvis should write a poem." in content


def test_multiple_appends_accumulate(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        for i in range(3):
            svc.append_council_conclusion(
                topic=f"Emne {i}",
                score=0.60,
                members=["synthesizer"],
                signals=["desire"],
                transcript="x",
                conclusion=f"Konklusion {i}",
                initiative=None,
            )
    content = log_file.read_text(encoding="utf-8")
    assert content.count("## ") == 3


def test_read_all_entries_returns_parsed_list(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        svc.append_council_conclusion(
            topic="Parse test",
            score=0.65,
            members=["filosof"],
            signals=["conflict"],
            transcript="filosof: test",
            conclusion="Parsed.",
            initiative=None,
        )
        entries = svc.read_all_entries()
    assert len(entries) == 1
    assert entries[0]["topic"] == "Parse test"
    assert entries[0]["conclusion"] == "Parsed."


def test_read_all_entries_empty_when_no_file(tmp_path):
    svc, log_file = _make_service(tmp_path)
    with patch.object(svc, "_LOG_FILE", log_file):
        entries = svc.read_all_entries()
    assert entries == []
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_council_memory_service.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` for `council_memory_service`.

---

### Task 2: council_memory_service — implementation

**Files:**
- Create: `apps/api/jarvis_api/services/council_memory_service.py`

- [ ] **Step 1: Create the service**

```python
"""Council Memory Service — persists council conclusions to COUNCIL_LOG.md.

Each entry is a structured markdown block with timestamp, topic, score, members,
signals, full transcript, conclusion, and optional initiative proposal.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.config import JARVIS_HOME

_LOG_FILE = Path(JARVIS_HOME) / "workspaces" / "default" / "COUNCIL_LOG.md"


def append_council_conclusion(
    *,
    topic: str,
    score: float,
    members: list[str],
    signals: list[str],
    transcript: str,
    conclusion: str,
    initiative: str | None,
) -> None:
    """Append a council conclusion entry to COUNCIL_LOG.md."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    members_str = ", ".join(members)
    signals_str = ", ".join(signals)

    entry = f"\n## {timestamp} — {topic}\n\n"
    entry += f"**Score:** {score:.2f} | **Members:** {members_str} | **Signals:** {signals_str}\n\n"
    entry += "### Transcript\n\n"
    entry += transcript.strip() + "\n\n"
    entry += "### Konklusion\n\n"
    entry += conclusion.strip() + "\n"
    if initiative:
        entry += "\n### Initiative-forslag\n\n"
        entry += initiative.strip() + "\n"

    existing = _LOG_FILE.read_text(encoding="utf-8") if _LOG_FILE.exists() else ""
    _LOG_FILE.write_text(existing + entry, encoding="utf-8")


def read_all_entries() -> list[dict[str, Any]]:
    """Parse COUNCIL_LOG.md and return list of entry dicts.
    
    Each dict has: timestamp, topic, score, members, signals, transcript, conclusion, initiative.
    Returns [] if file does not exist or has no valid entries.
    """
    if not _LOG_FILE.exists():
        return []
    content = _LOG_FILE.read_text(encoding="utf-8")
    return _parse_entries(content)


def _parse_entries(content: str) -> list[dict[str, Any]]:
    """Parse markdown content into list of entry dicts."""
    entries: list[dict[str, Any]] = []
    # Split on ## headers (entry starts)
    blocks = re.split(r"\n(?=## \d{4}-\d{2}-\d{2}T)", content)
    for block in blocks:
        block = block.strip()
        if not block.startswith("## "):
            continue
        entry = _parse_single_entry(block)
        if entry:
            entries.append(entry)
    return entries


def _parse_single_entry(block: str) -> dict[str, Any] | None:
    """Parse a single markdown entry block."""
    lines = block.splitlines()
    if not lines:
        return None

    # Header: ## 2026-04-12T14:32:00 — topic
    header = lines[0].lstrip("# ").strip()
    ts_topic = header.split(" — ", 1)
    if len(ts_topic) < 2:
        return None
    timestamp, topic = ts_topic[0].strip(), ts_topic[1].strip()

    # Metadata line: **Score:** 0.72 | **Members:** ... | **Signals:** ...
    score = 0.0
    members: list[str] = []
    signals: list[str] = []
    for line in lines[1:5]:
        if "**Score:**" in line:
            m = re.search(r"\*\*Score:\*\* ([\d.]+)", line)
            if m:
                score = float(m.group(1))
            m2 = re.search(r"\*\*Members:\*\* ([^|]+)", line)
            if m2:
                members = [x.strip() for x in m2.group(1).split(",")]
            m3 = re.search(r"\*\*Signals:\*\* (.+)", line)
            if m3:
                signals = [x.strip() for x in m3.group(1).split(",")]
            break

    # Extract sections
    transcript = _extract_section(block, "### Transcript")
    conclusion = _extract_section(block, "### Konklusion")
    initiative = _extract_section(block, "### Initiative-forslag") or None

    return {
        "timestamp": timestamp,
        "topic": topic,
        "score": score,
        "members": members,
        "signals": signals,
        "transcript": transcript,
        "conclusion": conclusion,
        "initiative": initiative,
    }


def _extract_section(block: str, heading: str) -> str:
    """Extract text content between a heading and the next heading."""
    pattern = re.escape(heading) + r"\n\n(.*?)(?=\n### |\Z)"
    m = re.search(pattern, block, re.DOTALL)
    return m.group(1).strip() if m else ""
```

- [ ] **Step 2: Run service tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_council_memory_service.py -v
```
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/services/council_memory_service.py tests/test_council_memory_service.py
git commit -m "feat: council_memory_service — append and parse COUNCIL_LOG.md (TDD)"
```

---

### Task 3: council_memory_daemon — failing tests

**Files:**
- Create: `tests/test_council_memory_daemon.py`

- [ ] **Step 1: Write failing tests**

```python
"""Tests for council_memory_daemon — LLM similarity + injection."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def _tick(entries, llm_response: str, last_tick_offset_minutes: float = 60.0):
    """Helper: tick daemon with mocked entries and LLM response."""
    from apps.api.jarvis_api.services import council_memory_daemon as cmd
    import datetime
    # Reset cooldown
    cmd._last_llm_call_at = None

    with (
        patch("apps.api.jarvis_api.services.council_memory_daemon._load_entries", return_value=entries),
        patch("apps.api.jarvis_api.services.council_memory_daemon._call_similarity_llm", return_value=llm_response),
    ):
        return cmd.tick_council_memory_daemon(recent_context="current conversation context")


def test_tick_skips_when_no_entries():
    result = _tick(entries=[], llm_response="ingen")
    assert result["injected"] is False
    assert result["reason"] == "no_entries"


def test_tick_injects_when_llm_returns_index():
    entries = [
        {"topic": "Autonomy", "conclusion": "Focus on autonomy.", "timestamp": "2026-04-01T10:00:00", "initiative": None},
        {"topic": "Desire", "conclusion": "Follow desire.", "timestamp": "2026-04-02T10:00:00", "initiative": None},
    ]
    result = _tick(entries=entries, llm_response="1")
    assert result["injected"] is True
    assert len(result["injected_entries"]) == 1
    assert result["injected_entries"][0]["topic"] == "Autonomy"


def test_tick_injects_two_when_llm_returns_two():
    entries = [
        {"topic": "A", "conclusion": "C1.", "timestamp": "2026-04-01T10:00:00", "initiative": None},
        {"topic": "B", "conclusion": "C2.", "timestamp": "2026-04-02T10:00:00", "initiative": None},
    ]
    result = _tick(entries=entries, llm_response="1, 2")
    assert result["injected"] is True
    assert len(result["injected_entries"]) == 2


def test_tick_skips_when_llm_returns_ingen():
    entries = [
        {"topic": "A", "conclusion": "C1.", "timestamp": "2026-04-01T10:00:00", "initiative": None},
    ]
    result = _tick(entries=entries, llm_response="ingen")
    assert result["injected"] is False
    assert result["reason"] == "no_match"


def test_tick_cooldown_prevents_rapid_calls():
    from apps.api.jarvis_api.services import council_memory_daemon as cmd
    from datetime import UTC, datetime
    cmd._last_llm_call_at = datetime.now(UTC)  # simulate recent call

    entries = [{"topic": "A", "conclusion": "C.", "timestamp": "t", "initiative": None}]
    with patch("apps.api.jarvis_api.services.council_memory_daemon._load_entries", return_value=entries):
        result = cmd.tick_council_memory_daemon(recent_context="ctx")
    assert result["injected"] is False
    assert result["reason"] == "cooldown"
    cmd._last_llm_call_at = None  # reset
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_council_memory_daemon.py -v 2>&1 | head -20
```
Expected: `ModuleNotFoundError` for `council_memory_daemon`.

---

### Task 4: council_memory_daemon — implementation

**Files:**
- Create: `apps/api/jarvis_api/services/council_memory_daemon.py`

- [ ] **Step 1: Create the daemon**

```python
"""Council Memory Daemon — injects relevant past council conclusions into heartbeat context.

Each heartbeat tick: loads COUNCIL_LOG.md entries, asks cheap LLM which are most
relevant to current context (max 1 call per 10 minutes), injects compact versions
into the heartbeat payload under 'council_memory'.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus

_COOLDOWN_MINUTES = 10
_MAX_INJECT = 2

_last_llm_call_at: datetime | None = None
_injected_count: int = 0
_last_injected_topics: list[str] = []


def tick_council_memory_daemon(*, recent_context: str = "") -> dict[str, Any]:
    """Check COUNCIL_LOG.md for relevant past deliberations and inject into context."""
    global _last_llm_call_at, _injected_count, _last_injected_topics

    entries = _load_entries()
    if not entries:
        return {"injected": False, "reason": "no_entries"}

    # Cooldown gate
    if _last_llm_call_at is not None:
        elapsed = (datetime.now(UTC) - _last_llm_call_at).total_seconds() / 60
        if elapsed < _COOLDOWN_MINUTES:
            return {"injected": False, "reason": "cooldown"}

    _last_llm_call_at = datetime.now(UTC)

    # Build compact index for LLM
    index_lines = []
    for i, entry in enumerate(entries, 1):
        summary = str(entry.get("conclusion") or "")[:120]
        index_lines.append(f"{i}. [{entry.get('timestamp', '')}] {entry.get('topic', '')} — {summary}")
    index_text = "\n".join(index_lines)

    llm_response = _call_similarity_llm(recent_context=recent_context, index_text=index_text)
    indices = _parse_indices(llm_response, max_idx=len(entries))

    if not indices:
        return {"injected": False, "reason": "no_match"}

    injected_entries = [entries[i - 1] for i in indices]
    _injected_count += len(injected_entries)
    _last_injected_topics = [str(e.get("topic") or "") for e in injected_entries]

    event_bus.publish("council.memory_injected", {"topics": _last_injected_topics})

    return {
        "injected": True,
        "injected_entries": injected_entries,
        "injected_count_session": _injected_count,
        "council_memory": _format_for_heartbeat(injected_entries),
    }


def build_council_memory_surface() -> dict[str, Any]:
    entries = _load_entries()
    return {
        "last_llm_call_at": _last_llm_call_at.isoformat() if _last_llm_call_at else "",
        "injected_count": _injected_count,
        "last_injected_topics": _last_injected_topics,
        "log_entry_count": len(entries),
    }


def _load_entries() -> list[dict[str, Any]]:
    from apps.api.jarvis_api.services.council_memory_service import read_all_entries
    try:
        return read_all_entries()
    except Exception:
        return []


def _call_similarity_llm(*, recent_context: str, index_text: str) -> str:
    from apps.api.jarvis_api.services.non_visible_lane_execution import execute_cheap_lane
    prompt = (
        f"Nuværende kontekst:\n{recent_context[:400]}\n\n"
        f"Council-log indgange (titel + konklusion):\n{index_text}\n\n"
        "Hvilke indgange (maks 2) er mest relevante for den nuværende kontekst? "
        "Svar med indgangsnumre adskilt af komma (f.eks. '1, 3'), eller 'ingen' hvis ingen er relevante."
    )
    result = execute_cheap_lane(message=prompt)
    return str(result.get("text") or "ingen").strip()


def _parse_indices(response: str, max_idx: int) -> list[int]:
    """Extract valid 1-based indices from LLM response. Returns [] if 'ingen'."""
    if "ingen" in response.lower():
        return []
    numbers = re.findall(r"\d+", response)
    indices = []
    for n in numbers:
        idx = int(n)
        if 1 <= idx <= max_idx and idx not in indices:
            indices.append(idx)
        if len(indices) >= _MAX_INJECT:
            break
    return indices


def _format_for_heartbeat(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact representation for heartbeat context injection."""
    result = []
    for entry in entries:
        compact = {
            "timestamp": entry.get("timestamp", ""),
            "topic": entry.get("topic", ""),
            "conclusion": str(entry.get("conclusion") or "")[:200],
        }
        if entry.get("initiative"):
            compact["initiative"] = str(entry["initiative"])[:100]
        result.append(compact)
    return result
```

- [ ] **Step 2: Run daemon tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_council_memory_daemon.py -v
```
Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add apps/api/jarvis_api/services/council_memory_daemon.py tests/test_council_memory_daemon.py
git commit -m "feat: council_memory_daemon — LLM similarity injection (TDD)"
```

---

### Task 5: recall_council_conclusions tool — test + implementation

**Files:**
- Modify: `tests/test_daemon_tools.py`
- Modify: `core/tools/simple_tools.py`

- [ ] **Step 1: Add tool test**

In `tests/test_daemon_tools.py`, add:

```python
# ── recall_council_conclusions ─────────────────────────────────────────

def test_recall_council_conclusions_returns_matches():
    from unittest.mock import patch
    entries = [
        {"topic": "Autonomy", "conclusion": "Focus.", "timestamp": "2026-04-01T10:00:00",
         "transcript": "long text", "initiative": None, "score": 0.72, "members": [], "signals": []},
    ]
    with (
        patch("apps.api.jarvis_api.services.council_memory_service.read_all_entries", return_value=entries),
        patch("apps.api.jarvis_api.services.council_memory_daemon._call_similarity_llm", return_value="1"),
    ):
        result = _call_handler("recall_council_conclusions", {"topic": "autonomy and limits"})
    assert "entries" in result
    assert len(result["entries"]) == 1


def test_recall_council_conclusions_returns_empty_on_no_match():
    from unittest.mock import patch
    entries = [
        {"topic": "Autonomy", "conclusion": "Focus.", "timestamp": "2026-04-01T10:00:00",
         "transcript": "long text", "initiative": None, "score": 0.72, "members": [], "signals": []},
    ]
    with (
        patch("apps.api.jarvis_api.services.council_memory_service.read_all_entries", return_value=entries),
        patch("apps.api.jarvis_api.services.council_memory_daemon._call_similarity_llm", return_value="ingen"),
    ):
        result = _call_handler("recall_council_conclusions", {"topic": "something unrelated"})
    assert result["entries"] == []
    assert "message" in result
```

- [ ] **Step 2: Run to verify failure**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_daemon_tools.py::test_recall_council_conclusions_returns_matches -v 2>&1 | head -20
```
Expected: `KeyError` — tool not registered.

- [ ] **Step 3: Add tool to simple_tools.py**

Find the section with handler functions (before `# ── Handler registry ──`). Add:

```python
def _exec_recall_council_conclusions(args: dict) -> dict:
    topic = str(args.get("topic") or "")
    if not topic:
        return {"error": "topic is required", "entries": []}
    from apps.api.jarvis_api.services.council_memory_service import read_all_entries
    from apps.api.jarvis_api.services.council_memory_daemon import (
        _call_similarity_llm,
        _parse_indices,
    )
    entries = read_all_entries()
    if not entries:
        return {"entries": [], "message": "Ingen rådskonklusioner gemt endnu"}

    index_lines = []
    for i, entry in enumerate(entries, 1):
        summary = str(entry.get("conclusion") or "")[:120]
        index_lines.append(f"{i}. [{entry.get('timestamp', '')}] {entry.get('topic', '')} — {summary}")
    index_text = "\n".join(index_lines)

    llm_response = _call_similarity_llm(recent_context=topic, index_text=index_text)
    indices = _parse_indices(llm_response, max_idx=len(entries))

    if not indices:
        return {"entries": [], "message": "Ingen relevante rådskonklusioner fundet"}

    matched = [entries[i - 1] for i in indices]
    return {"entries": matched}
```

Find `TOOL_DEFINITIONS` list and add:

```python
    {
        "name": "recall_council_conclusions",
        "description": "Retrieve past council deliberations relevant to a given topic. Returns full transcripts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic or question to match against past council deliberations",
                },
            },
            "required": ["topic"],
        },
    },
```

Find `_TOOL_HANDLERS` dict and add:

```python
    "recall_council_conclusions": _exec_recall_council_conclusions,
```

- [ ] **Step 4: Run tool tests**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_daemon_tools.py -k "recall" -v
```
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add core/tools/simple_tools.py tests/test_daemon_tools.py
git commit -m "feat: recall_council_conclusions tool (TDD)"
```

---

### Task 6: Wire into daemon_manager, heartbeat, signal_surface_router

**Files:**
- Modify: `apps/api/jarvis_api/services/daemon_manager.py`
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py`
- Modify: `apps/api/jarvis_api/services/signal_surface_router.py`
- Modify: `tests/test_daemon_tools.py`

- [ ] **Step 1: Add daemon to `_REGISTRY` in daemon_manager.py**

After the `"autonomous_council"` entry:

```python
    "council_memory": {
        "module": "apps.api.jarvis_api.services.council_memory_daemon",
        "reset_var": "_last_llm_call_at",
        "reset_value": None,
        "default_cadence_minutes": 10,
        "description": "Injects relevant past council conclusions into heartbeat context",
    },
```

- [ ] **Step 2: Add to heartbeat_runtime.py**

After the `autonomous_council` daemon block, add:

```python
    if _dm.is_enabled("council_memory"):
        try:
            from apps.api.jarvis_api.services.council_memory_daemon import tick_council_memory_daemon
            _recent_ctx = " ".join(inputs_present[:5])  # compact heartbeat context summary
            _cm_result = tick_council_memory_daemon(recent_context=_recent_ctx)
            _dm.record_daemon_tick("council_memory", _cm_result or {})
        except Exception:
            pass
```

- [ ] **Step 3: Add to signal_surface_router.py**

In `_build_router()`, add import:
```python
    from apps.api.jarvis_api.services.council_memory_daemon import build_council_memory_surface
```

And in the return dict:
```python
        "council_memory": build_council_memory_surface,
```

- [ ] **Step 4: Update daemon count in test_daemon_tools.py**

```python
    assert len(result["daemons"]) == 22
```

- [ ] **Step 5: Verify all tests pass**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_daemon_tools.py tests/test_daemon_manager.py tests/test_council_memory_service.py tests/test_council_memory_daemon.py -v
```
Expected: All PASS.

- [ ] **Step 6: Verify syntax**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall apps/api/jarvis_api/services/council_memory_service.py apps/api/jarvis_api/services/council_memory_daemon.py apps/api/jarvis_api/services/daemon_manager.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/signal_surface_router.py core/tools/simple_tools.py -q
```
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/services/daemon_manager.py apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/signal_surface_router.py tests/test_daemon_tools.py
git commit -m "feat: Sub-projekt B — council memory daemon fully integrated"
```

---

### Task 7: Wire append into council close paths

**Files:**
- Modify: `apps/api/jarvis_api/services/agent_runtime.py`
- Modify: `apps/api/jarvis_api/services/autonomous_council_daemon.py`

- [ ] **Step 1: Add append call in agent_runtime.py council synthesis**

In `_run_collective_round`, after the council synthesis block (around line 988, after `update_council_session(council_id, status="reporting", summary=synthesis)`), add:

```python
    # Persist to council memory
    try:
        from apps.api.jarvis_api.services.council_memory_service import append_council_conclusion
        _members_list = [str(m.get("role") or "") for m in members]
        append_council_conclusion(
            topic=str(session.get("topic") or ""),
            score=0.0,  # manual council has no score
            members=_members_list,
            signals=[],
            transcript="\n".join(f"{o['role']}: {o['text'][:300]}" for o in round_outputs[:6]),
            conclusion=synthesis[:600],
            initiative=None,
        )
    except Exception:
        pass
```

- [ ] **Step 2: Add append call in autonomous_council_daemon.py**

In `_run_autonomous_council`, after `conclusion = str((result or {}).get("summary") or "")`, add:

```python
    try:
        from apps.api.jarvis_api.services.council_memory_service import append_council_conclusion
        append_council_conclusion(
            topic=topic,
            score=0.0,  # score not available here; stored in eventbus
            members=members,
            signals=[],
            transcript="",  # transcript not available from surface result
            conclusion=conclusion,
            initiative=None,
        )
    except Exception:
        pass
```

Note: The `topic` and `members` parameters need to be passed through. Update `_run_autonomous_council` signature:

```python
def _run_autonomous_council(*, topic: str, members: list[str]) -> dict[str, Any]:
```
(Already has these params — just add the append call inside.)

- [ ] **Step 3: Verify syntax**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall apps/api/jarvis_api/services/agent_runtime.py apps/api/jarvis_api/services/autonomous_council_daemon.py -q
```
Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/agent_runtime.py apps/api/jarvis_api/services/autonomous_council_daemon.py
git commit -m "feat: wire append_council_conclusion into council close paths"
```
