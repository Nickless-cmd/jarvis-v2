# Cognitive Cartography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only cognitive map of Jarvis as a brain-like system, showing which subsystems are alive, replaced, manual-only, orphaned, noisy, and how they connect.

**Architecture:** Treat Jarvis as a cognitive graph, not a flat list of services or DB tables. A scanner builds subsystem nodes from code, DB schema, runtime state, event families, Mission Control surfaces, and prompt/provider wiring; a classifier assigns liveness status; a report renderer outputs a human-readable brain map plus machine-readable JSON for later Mission Control integration. Phase 1 is strictly read-only.

**Tech Stack:** Python 3.11, sqlite3, dataclasses, pathlib, pytest, existing `core.runtime.db.connect`, Markdown/JSON outputs under `docs/audits/` and `state/`.

---

## Brain Model

Use these brain regions as the first taxonomy. A subsystem may belong to multiple regions, but the primary region must be singular.

| Region | Purpose | Examples |
|---|---|---|
| Perception | Sense external/internal events | sensory, somatic, provider health, process watcher |
| Memory | Store and retrieve continuity | private brain, Jarvis brain, embeddings, session summaries |
| Self Model | Maintain self-understanding | runtime self model, identity continuity, limitations, strengths |
| Dreaming | Offline associative synthesis | dream hypothesis, dream influence, dream carry |
| World Model | Predictions and situational model | runtime world model signals, counterfactuals, calibration |
| Affect | Emotional/valence modulation | user temperature, relationship textures, gratitude, boredom |
| Agency | Wants, initiatives, actions | runtime initiatives, living executive, self wakeups |
| Learning | Feedback loops and policy formation | generalized policies, reasoning conclusions, meta-learning |
| Relation | User/partner continuity | user model, relationship textures, shared language |
| Governance | Boundaries and approvals | tool intent, approval, trust, permissions |
| Model Lanes | LLM routing and cognitive engines | visible, heartbeat, cheap, relevance, local |
| Observability | Mission Control and audits | surfaces, adapters, event projections |

## Liveness Statuses

Each subsystem must get exactly one status:

| Status | Meaning |
|---|---|
| `active` | Has a live producer and recent writes/events within expected cadence |
| `slow_active` | Live producer exists; low write rate is expected by design |
| `manual_only` | Only invoked by explicit tool/user/model action; no autonomous cadence expected |
| `replaced` | Old table/service exists, but function moved to a newer subsystem |
| `orphaned` | Write function exists but no live caller/producer |
| `read_only_surface` | Display/derived layer only; not expected to write |
| `deprecated` | Intentionally retained for compatibility/history |
| `unknown` | Insufficient evidence; needs manual review |

## File Structure

| File | Responsibility |
|---|---|
| `core/services/cognitive_cartography.py` | Read-only scanner, graph builder, liveness classifier |
| `scripts/cognitive_cartography.py` | CLI entry point for local and SSH/runtime audits |
| `tests/test_cognitive_cartography.py` | Unit tests for classification, schema scanning, replacement mapping |
| `docs/audits/cognitive-cartography-current.md` | Generated human report; not hand-edited after generation |
| `state/cognitive_cartography.json` | Generated machine-readable graph for future Mission Control use |

## Task 1: Add Core Data Model

**Files:**
- Create: `core/services/cognitive_cartography.py`
- Test: `tests/test_cognitive_cartography.py`

- [ ] **Step 1: Write failing tests for liveness status and brain region model**

Create `tests/test_cognitive_cartography.py`:

```python
from core.services.cognitive_cartography import (
    BrainRegion,
    LivenessStatus,
    SubsystemNode,
)


def test_liveness_statuses_are_explicit():
    assert LivenessStatus.ACTIVE.value == "active"
    assert LivenessStatus.SLOW_ACTIVE.value == "slow_active"
    assert LivenessStatus.MANUAL_ONLY.value == "manual_only"
    assert LivenessStatus.REPLACED.value == "replaced"
    assert LivenessStatus.ORPHANED.value == "orphaned"
    assert LivenessStatus.READ_ONLY_SURFACE.value == "read_only_surface"
    assert LivenessStatus.DEPRECATED.value == "deprecated"
    assert LivenessStatus.UNKNOWN.value == "unknown"


def test_subsystem_node_serializes_minimal_brain_mapping():
    node = SubsystemNode(
        subsystem_id="runtime_dream_hypothesis_signals",
        label="Dream hypothesis signals",
        region=BrainRegion.DREAMING,
        status=LivenessStatus.ACTIVE,
        evidence=["row_count=81", "last_write=2026-06-15T18:42:00+00:00"],
    )
    payload = node.to_dict()
    assert payload["subsystem_id"] == "runtime_dream_hypothesis_signals"
    assert payload["region"] == "dreaming"
    assert payload["status"] == "active"
    assert payload["evidence"] == ["row_count=81", "last_write=2026-06-15T18:42:00+00:00"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
pytest tests/test_cognitive_cartography.py -v
```

Expected: FAIL because `core.services.cognitive_cartography` does not exist.

- [ ] **Step 3: Implement minimal data model**

Create `core/services/cognitive_cartography.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BrainRegion(str, Enum):
    PERCEPTION = "perception"
    MEMORY = "memory"
    SELF_MODEL = "self_model"
    DREAMING = "dreaming"
    WORLD_MODEL = "world_model"
    AFFECT = "affect"
    AGENCY = "agency"
    LEARNING = "learning"
    RELATION = "relation"
    GOVERNANCE = "governance"
    MODEL_LANES = "model_lanes"
    OBSERVABILITY = "observability"


class LivenessStatus(str, Enum):
    ACTIVE = "active"
    SLOW_ACTIVE = "slow_active"
    MANUAL_ONLY = "manual_only"
    REPLACED = "replaced"
    ORPHANED = "orphaned"
    READ_ONLY_SURFACE = "read_only_surface"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class SubsystemNode:
    subsystem_id: str
    label: str
    region: BrainRegion
    status: LivenessStatus
    evidence: list[str] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    producers: list[str] = field(default_factory=list)
    consumers: list[str] = field(default_factory=list)
    replacement_for: list[str] = field(default_factory=list)
    replaced_by: str = ""
    expected_cadence: str = ""
    last_write_at: str = ""
    row_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "subsystem_id": self.subsystem_id,
            "label": self.label,
            "region": self.region.value,
            "status": self.status.value,
            "evidence": list(self.evidence),
            "tables": list(self.tables),
            "services": list(self.services),
            "producers": list(self.producers),
            "consumers": list(self.consumers),
            "replacement_for": list(self.replacement_for),
            "replaced_by": self.replaced_by,
            "expected_cadence": self.expected_cadence,
            "last_write_at": self.last_write_at,
            "row_count": self.row_count,
        }
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
pytest tests/test_cognitive_cartography.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/cognitive_cartography.py tests/test_cognitive_cartography.py
git commit -m "cartography: add cognitive subsystem data model"
```

## Task 2: Add Runtime Table Scanner

**Files:**
- Modify: `core/services/cognitive_cartography.py`
- Modify: `tests/test_cognitive_cartography.py`

- [ ] **Step 1: Add failing test for table scanning**

Append to `tests/test_cognitive_cartography.py`:

```python
import sqlite3

from core.services.cognitive_cartography import scan_sqlite_tables


def test_scan_sqlite_tables_counts_rows_and_latest_timestamp(tmp_path):
    db_path = tmp_path / "jarvis.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE runtime_dream_hypothesis_signals "
            "(id INTEGER PRIMARY KEY, created_at TEXT, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO runtime_dream_hypothesis_signals (created_at, updated_at) "
            "VALUES ('2026-06-15T18:00:00+00:00', '2026-06-15T18:42:00+00:00')"
        )
        conn.execute("CREATE TABLE cognitive_gut_state (gut_id TEXT PRIMARY KEY, updated_at TEXT)")
        conn.commit()

    tables = scan_sqlite_tables(db_path)
    by_name = {item["name"]: item for item in tables}

    assert by_name["runtime_dream_hypothesis_signals"]["row_count"] == 1
    assert by_name["runtime_dream_hypothesis_signals"]["latest_at"] == "2026-06-15T18:42:00+00:00"
    assert by_name["cognitive_gut_state"]["row_count"] == 0
    assert by_name["cognitive_gut_state"]["latest_at"] == ""
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
pytest tests/test_cognitive_cartography.py::test_scan_sqlite_tables_counts_rows_and_latest_timestamp -v
```

Expected: FAIL because `scan_sqlite_tables` is missing.

- [ ] **Step 3: Implement read-only scanner**

Append to `core/services/cognitive_cartography.py`:

```python
from pathlib import Path
import sqlite3
from typing import Any


_TIMESTAMP_COLUMNS = (
    "updated_at",
    "created_at",
    "finished_at",
    "started_at",
    "detected_at",
    "recorded_at",
    "last_seen_at",
    "last_run_at",
    "last_action_at",
    "ts",
)


def _qident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def scan_sqlite_tables(db_path: str | Path) -> list[dict[str, Any]]:
    path = Path(db_path)
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            table = str(row["name"])
            count = int(conn.execute(f"SELECT COUNT(*) FROM {_qident(table)}").fetchone()[0])
            columns = [
                str(col["name"])
                for col in conn.execute(f"PRAGMA table_info({_qident(table)})").fetchall()
            ]
            latest_at = ""
            latest_column = ""
            for column in _TIMESTAMP_COLUMNS:
                if column not in columns:
                    continue
                value = conn.execute(
                    f"SELECT MAX({_qident(column)}) FROM {_qident(table)} "
                    f"WHERE {_qident(column)} IS NOT NULL AND {_qident(column)} != ''"
                ).fetchone()[0]
                if value and str(value) > latest_at:
                    latest_at = str(value)
                    latest_column = column
            result.append(
                {
                    "name": table,
                    "row_count": count,
                    "columns": columns,
                    "latest_at": latest_at,
                    "latest_column": latest_column,
                }
            )
        return result
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_cognitive_cartography.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/cognitive_cartography.py tests/test_cognitive_cartography.py
git commit -m "cartography: scan runtime sqlite table liveness"
```

## Task 3: Add Replacement and Region Classification

**Files:**
- Modify: `core/services/cognitive_cartography.py`
- Modify: `tests/test_cognitive_cartography.py`

- [ ] **Step 1: Add failing tests for known migration mapping**

Append to `tests/test_cognitive_cartography.py`:

```python
from core.services.cognitive_cartography import classify_table


def test_classify_replaced_dream_table():
    node = classify_table(
        {
            "name": "cognitive_dream_hypotheses",
            "row_count": 1,
            "latest_at": "2026-05-15T18:48:01Z",
            "columns": ["created_at"],
        }
    )
    assert node.region is BrainRegion.DREAMING
    assert node.status is LivenessStatus.REPLACED
    assert node.replaced_by == "runtime_dream_hypothesis_signals"


def test_classify_active_runtime_dream_table():
    node = classify_table(
        {
            "name": "runtime_dream_hypothesis_signals",
            "row_count": 81,
            "latest_at": "2026-06-15T18:42:00+00:00",
            "columns": ["created_at", "updated_at"],
        }
    )
    assert node.region is BrainRegion.DREAMING
    assert node.status is LivenessStatus.ACTIVE
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
pytest tests/test_cognitive_cartography.py::test_classify_replaced_dream_table tests/test_cognitive_cartography.py::test_classify_active_runtime_dream_table -v
```

Expected: FAIL because `classify_table` is missing.

- [ ] **Step 3: Implement initial classification rules**

Append to `core/services/cognitive_cartography.py`:

```python
_REPLACED_TABLES = {
    "cognitive_dream_hypotheses": "runtime_dream_hypothesis_signals",
    "cognitive_chronicle_entries": "runtime_chronicle_consolidation_briefs",
    "cognitive_ruptures": "cognitive_conflict_memories",
    "cognitive_regrets": "cognitive_conflict_memories",
}

_ORPHAN_CANDIDATES = {
    "cognitive_epistemic_claims",
    "cognitive_wrongness",
    "cognitive_missions",
    "cognitive_mission_messages",
    "cognitive_trade_outcomes",
}

_MANUAL_ONLY_TABLES = {
    "meta_learning_hypotheses",
    "meta_learning_hypothesis_samples",
}


def infer_region(name: str) -> BrainRegion:
    lower = name.lower()
    if "dream" in lower:
        return BrainRegion.DREAMING
    if "world_model" in lower or "counterfactual" in lower or "epistemic" in lower or "wrongness" in lower:
        return BrainRegion.WORLD_MODEL
    if "memory" in lower or "brain" in lower or "embedding" in lower or "summary" in lower:
        return BrainRegion.MEMORY
    if "self" in lower or "identity" in lower:
        return BrainRegion.SELF_MODEL
    if "emotion" in lower or "affect" in lower or "gratitude" in lower or "temperature" in lower or "boredom" in lower:
        return BrainRegion.AFFECT
    if "goal" in lower or "initiative" in lower or "mission" in lower or "action" in lower:
        return BrainRegion.AGENCY
    if "policy" in lower or "learning" in lower or "hypothesis" in lower:
        return BrainRegion.LEARNING
    if "relation" in lower or "user" in lower or "partner" in lower:
        return BrainRegion.RELATION
    if "approval" in lower or "trust" in lower or "governance" in lower:
        return BrainRegion.GOVERNANCE
    if "provider" in lower or "model" in lower or "cost" in lower:
        return BrainRegion.MODEL_LANES
    if "sensory" in lower or "somatic" in lower or "perceptual" in lower:
        return BrainRegion.PERCEPTION
    return BrainRegion.OBSERVABILITY


def classify_table(table: dict[str, Any]) -> SubsystemNode:
    name = str(table.get("name") or "")
    row_count = int(table.get("row_count") or 0)
    latest_at = str(table.get("latest_at") or "")
    region = infer_region(name)
    evidence = [f"row_count={row_count}"]
    if latest_at:
        evidence.append(f"last_write={latest_at}")

    if name in _REPLACED_TABLES:
        return SubsystemNode(
            subsystem_id=name,
            label=name,
            region=region,
            status=LivenessStatus.REPLACED,
            evidence=evidence,
            tables=[name],
            replaced_by=_REPLACED_TABLES[name],
            row_count=row_count,
            last_write_at=latest_at,
        )
    if name in _ORPHAN_CANDIDATES:
        return SubsystemNode(
            subsystem_id=name,
            label=name,
            region=region,
            status=LivenessStatus.ORPHANED,
            evidence=evidence + ["known write path has no live caller"],
            tables=[name],
            row_count=row_count,
            last_write_at=latest_at,
        )
    if name in _MANUAL_ONLY_TABLES:
        return SubsystemNode(
            subsystem_id=name,
            label=name,
            region=region,
            status=LivenessStatus.MANUAL_ONLY,
            evidence=evidence + ["manual tool invocation only"],
            tables=[name],
            row_count=row_count,
            last_write_at=latest_at,
        )
    status = LivenessStatus.ACTIVE if row_count > 0 and latest_at else LivenessStatus.UNKNOWN
    return SubsystemNode(
        subsystem_id=name,
        label=name,
        region=region,
        status=status,
        evidence=evidence,
        tables=[name],
        row_count=row_count,
        last_write_at=latest_at,
    )
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_cognitive_cartography.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/cognitive_cartography.py tests/test_cognitive_cartography.py
git commit -m "cartography: classify cognitive table liveness"
```

## Task 4: Add Report Renderer and CLI

**Files:**
- Modify: `core/services/cognitive_cartography.py`
- Create: `scripts/cognitive_cartography.py`
- Modify: `tests/test_cognitive_cartography.py`

- [ ] **Step 1: Add failing test for report rendering**

Append to `tests/test_cognitive_cartography.py`:

```python
from core.services.cognitive_cartography import render_markdown_report


def test_render_markdown_report_groups_by_region():
    nodes = [
        SubsystemNode(
            subsystem_id="runtime_dream_hypothesis_signals",
            label="Dreams",
            region=BrainRegion.DREAMING,
            status=LivenessStatus.ACTIVE,
            row_count=81,
            last_write_at="2026-06-15T18:42:00+00:00",
        )
    ]
    report = render_markdown_report(nodes)
    assert "# Jarvis Cognitive Cartography" in report
    assert "## Dreaming" in report
    assert "| `runtime_dream_hypothesis_signals` | active | 81 | 2026-06-15T18:42:00+00:00 |" in report
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_cognitive_cartography.py::test_render_markdown_report_groups_by_region -v
```

Expected: FAIL because `render_markdown_report` is missing.

- [ ] **Step 3: Implement renderer**

Append to `core/services/cognitive_cartography.py`:

```python
def render_markdown_report(nodes: list[SubsystemNode]) -> str:
    lines = [
        "# Jarvis Cognitive Cartography",
        "",
        "Read-only map of Jarvis subsystems as a brain-like cognitive graph.",
        "",
    ]
    for region in BrainRegion:
        region_nodes = [node for node in nodes if node.region is region]
        if not region_nodes:
            continue
        title = region.value.replace("_", " ").title()
        lines.extend([
            f"## {title}",
            "",
            "| Subsystem | Status | Rows | Last Write | Replaced By | Evidence |",
            "|---|---:|---:|---|---|---|",
        ])
        for node in sorted(region_nodes, key=lambda item: item.subsystem_id):
            evidence = "; ".join(node.evidence[:3])
            lines.append(
                f"| `{node.subsystem_id}` | {node.status.value} | {node.row_count} | "
                f"{node.last_write_at} | {node.replaced_by} | {evidence} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_cartography_from_db(db_path: str | Path) -> list[SubsystemNode]:
    return [classify_table(table) for table in scan_sqlite_tables(db_path)]
```

- [ ] **Step 4: Add CLI**

Create `scripts/cognitive_cartography.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from core.services.cognitive_cartography import (
    build_cartography_from_db,
    render_markdown_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Jarvis cognitive cartography report.")
    parser.add_argument("--db", required=True, help="Path to jarvis.db")
    parser.add_argument("--json-out", default="state/cognitive_cartography.json")
    parser.add_argument("--md-out", default="docs/audits/cognitive-cartography-current.md")
    args = parser.parse_args()

    nodes = build_cartography_from_db(args.db)
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)

    json_out.write_text(
        json.dumps([node.to_dict() for node in nodes], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_out.write_text(render_markdown_report(nodes), encoding="utf-8")
    print(f"wrote {json_out}")
    print(f"wrote {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_cognitive_cartography.py -v
```

Expected: PASS.

- [ ] **Step 6: Run CLI against local or live DB**

For local active runtime mounted on the Jarvis host:

```bash
python scripts/cognitive_cartography.py --db ~/.jarvis-v2/state/jarvis.db
```

For this workspace from Codex via SSH:

```bash
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && python scripts/cognitive_cartography.py --db ~/.jarvis-v2/state/jarvis.db'
```

Expected:

```text
wrote state/cognitive_cartography.json
wrote docs/audits/cognitive-cartography-current.md
```

- [ ] **Step 7: Commit**

```bash
git add core/services/cognitive_cartography.py scripts/cognitive_cartography.py tests/test_cognitive_cartography.py
git commit -m "cartography: generate cognitive liveness reports"
```

## Task 5: Add Connection Evidence

**Files:**
- Modify: `core/services/cognitive_cartography.py`
- Modify: `tests/test_cognitive_cartography.py`

- [ ] **Step 1: Add failing test for static code connection scan**

Append to `tests/test_cognitive_cartography.py`:

```python
from core.services.cognitive_cartography import scan_code_references


def test_scan_code_references_finds_producers_and_consumers(tmp_path):
    root = tmp_path
    service = root / "core" / "services"
    service.mkdir(parents=True)
    (service / "example.py").write_text(
        "from core.runtime.db import upsert_runtime_goal_signal, list_runtime_goal_signals\n"
        "def produce():\n"
        "    upsert_runtime_goal_signal(goal_type='x', title='t')\n"
        "def consume():\n"
        "    return list_runtime_goal_signals(limit=5)\n",
        encoding="utf-8",
    )
    refs = scan_code_references(root, ["runtime_goal_signals"])
    assert "core/services/example.py" in refs["runtime_goal_signals"]["producers"]
    assert "core/services/example.py" in refs["runtime_goal_signals"]["consumers"]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_cognitive_cartography.py::test_scan_code_references_finds_producers_and_consumers -v
```

Expected: FAIL because `scan_code_references` is missing.

- [ ] **Step 3: Implement lightweight static reference scan**

Append to `core/services/cognitive_cartography.py`:

```python
_PRODUCER_PREFIXES = ("insert_", "upsert_", "update_", "record_", "create_", "generate_", "reconcile_")
_CONSUMER_PREFIXES = ("list_", "get_", "build_", "format_", "read_", "fetch_")


def scan_code_references(repo_root: str | Path, table_names: list[str]) -> dict[str, dict[str, list[str]]]:
    root = Path(repo_root)
    result = {
        name: {"producers": [], "consumers": []}
        for name in table_names
    }
    py_files = list((root / "core").rglob("*.py")) + list((root / "apps").rglob("*.py")) + list((root / "scripts").rglob("*.py"))
    for path in py_files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = str(path.relative_to(root))
        for table in table_names:
            if table not in text:
                continue
            producer_hit = any(prefix in text for prefix in _PRODUCER_PREFIXES)
            consumer_hit = any(prefix in text for prefix in _CONSUMER_PREFIXES)
            if producer_hit:
                result[table]["producers"].append(rel)
            if consumer_hit:
                result[table]["consumers"].append(rel)
    return result
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_cognitive_cartography.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/cognitive_cartography.py tests/test_cognitive_cartography.py
git commit -m "cartography: add static connection evidence"
```

## Task 6: Add Brain Noise Summary

**Files:**
- Modify: `core/services/cognitive_cartography.py`
- Modify: `tests/test_cognitive_cartography.py`

- [ ] **Step 1: Add failing test for noise summary**

Append to `tests/test_cognitive_cartography.py`:

```python
from core.services.cognitive_cartography import summarize_noise


def test_summarize_noise_counts_risk_categories():
    nodes = [
        SubsystemNode("old_dream", "Old Dream", BrainRegion.DREAMING, LivenessStatus.REPLACED),
        SubsystemNode("gut", "Gut", BrainRegion.WORLD_MODEL, LivenessStatus.ORPHANED),
        SubsystemNode("dream", "Dream", BrainRegion.DREAMING, LivenessStatus.ACTIVE),
    ]
    summary = summarize_noise(nodes)
    assert summary["active"] == 1
    assert summary["replaced"] == 1
    assert summary["orphaned"] == 1
    assert summary["noise_score"] == 2
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
pytest tests/test_cognitive_cartography.py::test_summarize_noise_counts_risk_categories -v
```

Expected: FAIL because `summarize_noise` is missing.

- [ ] **Step 3: Implement noise summary**

Append to `core/services/cognitive_cartography.py`:

```python
def summarize_noise(nodes: list[SubsystemNode]) -> dict[str, int]:
    counts = {status.value: 0 for status in LivenessStatus}
    for node in nodes:
        counts[node.status.value] += 1
    noise_score = (
        counts[LivenessStatus.REPLACED.value]
        + counts[LivenessStatus.ORPHANED.value] * 2
        + counts[LivenessStatus.UNKNOWN.value]
    )
    counts["noise_score"] = noise_score
    return counts
```

- [ ] **Step 4: Include summary in report**

Modify the top of `render_markdown_report`:

```python
def render_markdown_report(nodes: list[SubsystemNode]) -> str:
    summary = summarize_noise(nodes)
    lines = [
        "# Jarvis Cognitive Cartography",
        "",
        "Read-only map of Jarvis subsystems as a brain-like cognitive graph.",
        "",
        "## Summary",
        "",
        f"- active: {summary['active']}",
        f"- slow_active: {summary['slow_active']}",
        f"- manual_only: {summary['manual_only']}",
        f"- replaced: {summary['replaced']}",
        f"- orphaned: {summary['orphaned']}",
        f"- unknown: {summary['unknown']}",
        f"- noise_score: {summary['noise_score']}",
        "",
    ]
    ...
```

- [ ] **Step 5: Run tests**

Run:

```bash
pytest tests/test_cognitive_cartography.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add core/services/cognitive_cartography.py tests/test_cognitive_cartography.py
git commit -m "cartography: summarize cognitive noise"
```

## Task 7: Generate Current Map and Manual Review

**Files:**
- Generate: `docs/audits/cognitive-cartography-current.md`
- Generate: `state/cognitive_cartography.json`

- [ ] **Step 1: Generate report on live runtime**

Run:

```bash
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && python scripts/cognitive_cartography.py --db ~/.jarvis-v2/state/jarvis.db'
```

Expected: generated Markdown and JSON.

- [ ] **Step 2: Review report for high-risk false positives**

Run:

```bash
sed -n '1,220p' docs/audits/cognitive-cartography-current.md
```

Expected: report groups tables by brain region and marks known replacements.

- [ ] **Step 3: Manually correct classification rules for false positives**

If `runtime_goal_signals` is marked stale/unknown while `runtime_development_focuses` and `runtime_initiatives` are active, add a replacement/parallel note rather than marking it dead.

If a table has no timestamp columns but is clearly active through events or code references, mark it `slow_active` or `active` with evidence from code references.

- [ ] **Step 4: Commit generated report**

```bash
git add docs/audits/cognitive-cartography-current.md state/cognitive_cartography.json core/services/cognitive_cartography.py
git commit -m "docs: generate Jarvis cognitive cartography"
```

## Task 8: Mission Control Integration Design Only

**Files:**
- Create: `docs/superpowers/specs/2026-06-15-cognitive-cartography-mc-design.md`

- [ ] **Step 1: Write design spec**

Create `docs/superpowers/specs/2026-06-15-cognitive-cartography-mc-design.md` with:

```markdown
# Cognitive Cartography Mission Control Design

## Goal

Show Jarvis as a brain map instead of a pile of tables.

## Non-Goals

- No table deletion.
- No automatic rewiring.
- No hiding evidence.

## Views

1. Brain Regions: Perception, Memory, Self Model, Dreaming, World Model, Affect, Agency, Learning, Relation, Governance, Model Lanes, Observability.
2. Connection Graph: producer -> table/event -> consumer/surface.
3. Noise Ledger: replaced, orphaned, manual-only, unknown.
4. Liveness Contracts: expected cadence, last write, last event, replacement target.

## Safety Rules

- Deprecated/replaced systems remain visible but cannot be presented as dead organs.
- Orphaned systems are shown as repair candidates, not deleted automatically.
- Manual-only systems are not flagged stale.
- Low-cadence affective/identity signals require explicit expected cadence before warnings.
```

- [ ] **Step 2: Commit spec**

```bash
git add docs/superpowers/specs/2026-06-15-cognitive-cartography-mc-design.md
git commit -m "docs: design Mission Control cognitive cartography"
```

## Self-Review Checklist

- [ ] The plan is read-only until after the cognitive map exists.
- [ ] The plan preserves inner-life richness by classifying rather than deleting.
- [ ] The plan distinguishes dead systems from replaced systems.
- [ ] The plan makes manual-only systems explicit.
- [ ] The plan creates a future Mission Control path without coupling the first pass to UI work.
- [ ] The plan produces both human Markdown and machine JSON.

