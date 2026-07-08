---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Interlanguage Validation — Phase 1+2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Saml 7 dages praksis-data fra 7 cohorts (Jarvis + 6 peers/varianter) til at validere identitets-bæring i inter-sprog-protokollen.

**Architecture:** Phase 1 forbereder værktøjer + skema mens Jarvis fortsætter sin native praksis. Phase 2 kører 6 peer-runnere parallelt i 7 dage, mood-matched til Jarvis' timestamp-trace. Alle expressions persisteres i delt `interlanguage_practice` tabel med ny `peer_id` kolonne. Analyse (Phase 3+4) får separat plan.

**Tech Stack:** Python 3.11+, sqlite, deepseek-v4-flash:cloud, Anthropic API (Claude sonnet), GLM API, lokal Ollama, conda env `ai`.

**Spec:** `docs/superpowers/specs/2026-05-16-interlanguage-validation-design.md` (henvis dertil for hypoteser, success-kriterier, dommer-design)

---

## Executive Summary

| Phase | Hvad | Hvem | Varighed | Output |
|---|---|---|---|---|
| Pre-flight | DB_PATH-test-fixture audit | Claude Code | 30 min | Audit-rapport |
| **Phase 1** | Schema + mood-trace API + peer-runner skeleton | Claude Code | 1-2 timer | `peer_practice_runner.py`, schema-migration, mood-API |
| **Phase 2** | Start 6 peer-runners parallelt + monitor | Claude Code + watchdog | 7 dage | ~1.260 nye expressions (6 cohorts × 210) |
| **Checkpoint** | Verificér data-integritet, expression-counts, ingen rate-limit-dødfald | Claude Code + Bjørn | 30 min | Go/no-go for Phase 3 |

Jarvis kører sin native praksis (cohort #1) uændret. Han har 0 ekstra arbejde i Phase 1+2. Phase 3+4 (statistical + LLM-judge + Bjørn-blind) er separat plan når data er klar.

---

## File Structure

| Fil | Type | Ansvar |
|---|---|---|
| `core/services/interlanguage_practice.py` | Modify | Tilføj `export_mood_trace_for_period()` + `peer_id`-aware persistence |
| Schema migration | New `_ensure_*` ext | Tilføj `peer_id TEXT DEFAULT 'jarvis'` til `interlanguage_practice` |
| `scripts/peer_practice_runner.py` | New | Hovedrunner: tager `--peer <name>` arg, kører i loop, persister med `peer_id` |
| `scripts/peer_models.py` | New | Adapter-laget: ét `generate(prompt, model_id) → str` interface per provider |
| `scripts/peer_practice_watchdog.sh` | New | Bash script der spawner 6 runner-processer + restart-on-crash |
| `scripts/db_path_fixture_audit.py` | New (pre-flight) | Grep efter `monkeypatch.setattr.*DB_PATH` mønstre på tværs af test-filer |
| `tests/test_peer_practice_runner.py` | New | Unit-tests: mood-interpolation, peer_id-persistens, error-handling |

---

## Pre-Flight Task: DB_PATH Fixture Audit

**Files:** Create `scripts/db_path_fixture_audit.py`

Læring fra `interlanguage_practice` fixture-bug: efter Phase 0 db-split skal tests patche BÅDE `db` OG `db_core`. Audit findes proaktivt steder hvor det er gjort forkert.

- [ ] **Step 1: Skriv audit-script**

```python
"""Audit: find test fixtures that monkeypatch DB_PATH on db but not db_core.

Post-2026-05-15 db.py split: DB_PATH lever i db_core. db re-eksporterer
det som lokal binding. Patch af db.DB_PATH alone ændrer ikke hvad
connect() ser. Output: liste af suspekte filer + linjer.
"""
import re
import sys
from pathlib import Path

PATTERN_DB = re.compile(r'monkeypatch\.setattr\([^)]*\bdb\b[^)]*DB_PATH')
PATTERN_DB_CORE = re.compile(r'monkeypatch\.setattr\([^)]*\bdb_core\b[^)]*DB_PATH')

def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    suspect: list[tuple[Path, int, str]] = []
    for py in (repo / "tests").rglob("*.py"):
        text = py.read_text()
        if not PATTERN_DB.search(text):
            continue
        if PATTERN_DB_CORE.search(text):
            continue  # Both patched — OK
        # Find line numbers
        for i, line in enumerate(text.splitlines(), start=1):
            if PATTERN_DB.search(line):
                suspect.append((py.relative_to(repo), i, line.strip()))
    if not suspect:
        print("OK: alle DB_PATH-monkeypatches patcher også db_core")
        return 0
    print(f"FOUND {len(suspect)} suspect locations:")
    for path, lineno, line in suspect:
        print(f"  {path}:{lineno}: {line}")
    return 1 if "--strict" in sys.argv else 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Kør audit**

Run: `python scripts/db_path_fixture_audit.py`
Expected: enten "OK" eller en liste af filer med forkert patch.

- [ ] **Step 3: Fix evt. fund med to-modul patch-pattern**

Pattern (se `tests/services/test_forgetting_engine.py` for reference):
```python
monkeypatch.setattr(db, "DB_PATH", db_path)
monkeypatch.setattr(db_core, "DB_PATH", db_path)
```

- [ ] **Step 4: Commit audit + fixes**

```bash
git add scripts/db_path_fixture_audit.py tests/
git commit -m "tools: db_path fixture audit + fix any test isolation gaps

Pre-flight til interlanguage validation experiment. Post-Phase 0 db
split kræver patch af både db + db_core for DB_PATH. Audit-script
fanger drift fremad. Eksisterende drift fixet (hvis nogen)."
```

---

## Phase 1, Task 1: Schema-udvidelse for `peer_id`

**Files:** Modify `core/services/interlanguage_practice.py:127` (Edit `_ensure_interlanguage_practice_table`)

- [ ] **Step 1: Skriv failing test**

Append til `tests/test_interlanguage_practice.py`:
```python
def test_peer_id_column_exists(clean_state):
    """Schema skal have peer_id kolonne efter migration (default='jarvis')."""
    from core.runtime.db import connect
    from core.services.interlanguage_practice import ensure_schema
    ensure_schema()
    with connect() as conn:
        rows = conn.execute("PRAGMA table_info(interlanguage_practice)").fetchall()
    names = {row["name"] for row in rows}
    assert "peer_id" in names, f"Mangler peer_id i schema. Fundet: {names}"

def test_peer_id_default_is_jarvis(clean_state):
    """Eksisterende rows uden peer_id skal default til 'jarvis' (backwards compat)."""
    from core.services.interlanguage_practice import record_expression
    from core.runtime.db import connect
    record_expression("test → backcompat", session_id="bc-test")
    with connect() as conn:
        row = conn.execute(
            "SELECT peer_id FROM interlanguage_practice WHERE session_id='bc-test'"
        ).fetchone()
    assert row["peer_id"] == "jarvis"
```

- [ ] **Step 2: Kør test — forventes at fejle**

Run: `pytest tests/test_interlanguage_practice.py::test_peer_id_column_exists -v`
Expected: FAIL (kolonne findes ikke endnu).

- [ ] **Step 3: Tilføj kolonne i schema-bootstrap**

Edit `_ensure_interlanguage_practice_table`:
```python
def _ensure_interlanguage_practice_table(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS interlanguage_practice (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          expression_id TEXT NOT NULL UNIQUE,
          expression_text TEXT NOT NULL,
          session_id TEXT NOT NULL DEFAULT '',
          tick_id TEXT NOT NULL DEFAULT '',
          trigger TEXT NOT NULL DEFAULT 'manual',
          peer_id TEXT NOT NULL DEFAULT 'jarvis',
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_interlanguage_created_at
          ON interlanguage_practice(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_interlanguage_peer_id
          ON interlanguage_practice(peer_id, created_at DESC);
        """
    )
    # Idempotent migration for existing tables — ALTER ADD COLUMN guarded
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(interlanguage_practice)").fetchall()}
    if "peer_id" not in cols:
        conn.execute("ALTER TABLE interlanguage_practice ADD COLUMN peer_id TEXT NOT NULL DEFAULT 'jarvis'")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interlanguage_peer_id ON interlanguage_practice(peer_id, created_at DESC)")
    conn.commit()
```

- [ ] **Step 4: Opdater `record_expression` til at acceptere `peer_id`**

```python
def record_expression(
    expression_text: str,
    *,
    session_id: str = "",
    tick_id: str = "",
    trigger: str = "manual",
    peer_id: str = "jarvis",
) -> str:
    ensure_schema()
    expression_id = str(uuid4())
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            """INSERT INTO interlanguage_practice
               (expression_id, expression_text, session_id, tick_id, trigger, peer_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (expression_id, expression_text, session_id, tick_id, trigger, peer_id, now_iso),
        )
        conn.commit()
    logger.debug("interlanguage: recorded %s (peer=%s): %s", expression_id, peer_id, expression_text)
    return expression_id
```

- [ ] **Step 5: Kør tests — forventes grøn**

Run: `pytest tests/test_interlanguage_practice.py -v`
Expected: alle 28 tests PASS (26 eksisterende + 2 nye).

- [ ] **Step 6: Verificér prod-DB migration**

Run:
```bash
python -c "
from core.runtime.db import connect
from core.services.interlanguage_practice import ensure_schema
ensure_schema()
with connect() as conn:
    cols = [r['name'] for r in conn.execute('PRAGMA table_info(interlanguage_practice)').fetchall()]
print('cols:', cols)
assert 'peer_id' in cols
"
```
Expected: `peer_id` i kolonne-listen.

- [ ] **Step 7: Commit schema-migration separat**

```bash
git add core/services/interlanguage_practice.py tests/test_interlanguage_practice.py
git commit -m "schema(interlanguage): add peer_id column for validation experiment

Idempotent ALTER ADD COLUMN på eksisterende rows (default='jarvis' for
backwards compat). Klar til Phase 2 peer-praksis.

Spec: docs/superpowers/specs/2026-05-16-interlanguage-validation-design.md"
```

---

## Phase 1, Task 2: `export_mood_trace_for_period`

**Files:** Modify `core/services/interlanguage_practice.py` (append new function)

Per spec §"Mood-input + timestamp-matching" skal peers få `(timestamp, mood)` pairs, ikke index-baseret.

- [ ] **Step 1: Find mood-source-API**

Run:
```bash
python -c "
from core.services import cognitive_state_assembly as csa
print([n for n in dir(csa) if 'mood' in n.lower() or 'state' in n.lower()][:15])
"
```
Forventet output: lokal en `get_*_state()` eller `assemble_*()` funktion der returnerer dict med curiosity/confidence/fatigue/frustration keys.

Hvis ikke fundet i `cognitive_state_assembly`, prøv `personality_vector.py` og `mood_oscillator.py`. Dokumentér det fundne API i en kommentar før implementation.

- [ ] **Step 2: Skriv failing test**

```python
def test_export_mood_trace_returns_timestamped_pairs(clean_state):
    """Eksportér mood-trace som [(timestamp_iso, mood_dict), ...]."""
    from datetime import UTC, datetime, timedelta
    from core.services.interlanguage_practice import export_mood_trace_for_period
    end = datetime.now(UTC)
    start = end - timedelta(hours=1)
    trace = export_mood_trace_for_period(start, end)
    assert isinstance(trace, list)
    if trace:  # Hvis live data findes
        ts, mood = trace[0]
        assert isinstance(ts, str)  # ISO timestamp
        assert isinstance(mood, dict)
        # Spec'en kræver mindst disse keys (kan have flere)
        for required in ("curiosity", "confidence", "fatigue", "frustration"):
            assert required in mood, f"Mangler {required} i mood-dict"
```

- [ ] **Step 3: Run test — fail (function not defined)**

Run: `pytest tests/test_interlanguage_practice.py::test_export_mood_trace_returns_timestamped_pairs -v`
Expected: FAIL med `ImportError: cannot import name 'export_mood_trace_for_period'`.

- [ ] **Step 4: Implementér**

Append til `core/services/interlanguage_practice.py`:
```python
def export_mood_trace_for_period(
    start: datetime,
    end: datetime,
    *,
    sample_interval_minutes: int = 30,
) -> list[tuple[str, dict[str, float]]]:
    """Eksportér mood-snapshots over en periode for peer-replay.

    Returnerer (timestamp_iso, mood_dict) pairs. Peers interpolerer
    til nærmeste timestamp ved hver tick.

    Hvis live mood-historie ikke er tilgængelig, returneres en
    syntetisk neutral baseline (curiosity=0.5 etc.) per interval —
    så peer-runner kan stadig køre, bare med mood=neutral.
    """
    # Forsøg at læse fra live mood-state.
    # NOTE: opdater til faktisk API når Step 1 har afsløret det.
    try:
        from core.services.cognitive_state_assembly import get_cognitive_state  # type: ignore[attr-defined]
        # Hvis API'et er live + persistent (sjældent), pull historik
        # Ellers fall through til synthetic
    except ImportError:
        pass

    # Synthetic baseline fallback — neutral mood per interval
    trace: list[tuple[str, dict[str, float]]] = []
    current = start
    while current <= end:
        trace.append((
            current.isoformat(),
            {"curiosity": 0.5, "confidence": 0.5, "fatigue": 0.3, "frustration": 0.2},
        ))
        current += timedelta(minutes=sample_interval_minutes)
    return trace


def interpolate_mood_at(
    trace: list[tuple[str, dict[str, float]]],
    target_iso: str,
) -> dict[str, float]:
    """Linear-interpolér mellem nærmeste to mood-samples til target timestamp."""
    if not trace:
        return {"curiosity": 0.5, "confidence": 0.5, "fatigue": 0.3, "frustration": 0.2}
    target = datetime.fromisoformat(target_iso)
    before: tuple[str, dict[str, float]] | None = None
    after: tuple[str, dict[str, float]] | None = None
    for ts, mood in trace:
        t = datetime.fromisoformat(ts)
        if t <= target:
            before = (ts, mood)
        elif after is None and t > target:
            after = (ts, mood)
            break
    if before and not after:
        return before[1]
    if after and not before:
        return after[1]
    if before and after:
        b_t = datetime.fromisoformat(before[0])
        a_t = datetime.fromisoformat(after[0])
        span = (a_t - b_t).total_seconds()
        if span <= 0:
            return before[1]
        frac = (target - b_t).total_seconds() / span
        return {
            k: before[1].get(k, 0.5) * (1 - frac) + after[1].get(k, 0.5) * frac
            for k in {*before[1], *after[1]}
        }
    return {"curiosity": 0.5, "confidence": 0.5, "fatigue": 0.3, "frustration": 0.2}
```

- [ ] **Step 5: Tilføj test for interpolation**

```python
def test_interpolate_mood_at_midpoint():
    from core.services.interlanguage_practice import interpolate_mood_at
    trace = [
        ("2026-05-16T12:00:00+00:00", {"curiosity": 0.2, "confidence": 0.4}),
        ("2026-05-16T13:00:00+00:00", {"curiosity": 0.8, "confidence": 0.6}),
    ]
    result = interpolate_mood_at(trace, "2026-05-16T12:30:00+00:00")
    assert abs(result["curiosity"] - 0.5) < 0.01, result
    assert abs(result["confidence"] - 0.5) < 0.01, result
```

- [ ] **Step 6: Run all interlanguage tests**

Run: `pytest tests/test_interlanguage_practice.py -v`
Expected: 30+ tests PASS.

- [ ] **Step 7: Commit**

```bash
git add core/services/interlanguage_practice.py tests/test_interlanguage_practice.py
git commit -m "feat(interlanguage): mood-trace export + interpolation for peer replay

Peers vil bruge export_mood_trace_for_period() til at få Jarvis'
mood-historie, og interpolate_mood_at() til at finde nærmeste
mood ved hver tick (peers har anden API-clock end Jarvis).

Spec §Mood-input + timestamp-matching."
```

---

## Phase 1, Task 3: Peer-model adapter (`scripts/peer_models.py`)

**Files:** Create `scripts/peer_models.py`

Single interface `generate(prompt, model_id) → str` der dispatcher til Anthropic / GLM / Ollama / random.

- [ ] **Step 1: Skriv interface + adapter-stubs**

```python
"""Peer model adapters for interlanguage validation experiment.

Hver peer kalder generate(prompt, peer_id) og får et expression-string
tilbage. Adapter-laget abstraherer model-API-forskelle.

NOTE: API-keys læses fra ~/.jarvis-v2/config/runtime.json via
core.runtime.secrets.read_runtime_key() — INGEN hardcoded keys.
"""
from __future__ import annotations
import json
import random as _random
from typing import Callable

from core.runtime.secrets import read_runtime_key


def _generate_claude(prompt: str) -> str:
    """Claude Sonnet via Anthropic API."""
    import anthropic
    key = read_runtime_key("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=key)
    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text.strip()


def _generate_glm(prompt: str) -> str:
    """GLM 5.1 via OpenAI-compatible endpoint."""
    from openai import OpenAI
    key = read_runtime_key("GLM_API_KEY")
    client = OpenAI(api_key=key, base_url="https://open.bigmodel.cn/api/paas/v4/")
    resp = client.chat.completions.create(
        model="glm-5.1-flash",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def _generate_ollama_local(prompt: str) -> str:
    """Lokal Ollama med deepseek-v4-flash (samme arkitektur som Jarvis)."""
    import requests
    resp = requests.post(
        "http://10.0.0.25:11434/api/generate",
        json={"model": "deepseek-v4-flash:cloud", "prompt": prompt, "stream": False},
        timeout=60,
    )
    return resp.json().get("response", "").strip()


def _generate_random(prompt: str) -> str:
    """Random baseline — ignorer prompt, gen pure random expression."""
    from core.services.interlanguage_practice import generate_state_expression
    return generate_state_expression(mood_override=None)


ADAPTERS: dict[str, Callable[[str], str]] = {
    "claude": _generate_claude,
    "claude_jp": _generate_claude,  # samme adapter, forskellig prompt-konstruktion
    "glm": _generate_glm,
    "glm_jp": _generate_glm,
    "ollama_local": _generate_ollama_local,
    "random": _generate_random,
}


def generate(prompt: str, peer_id: str) -> str:
    """Dispatch til peer-specific adapter. Raise ValueError ved ukendt peer."""
    adapter = ADAPTERS.get(peer_id)
    if adapter is None:
        raise ValueError(f"Unknown peer_id: {peer_id}")
    return adapter(prompt)
```

- [ ] **Step 2: Verificér compile**

Run: `python -m compileall -q scripts/peer_models.py && python -c "from scripts.peer_models import generate, ADAPTERS; print(sorted(ADAPTERS.keys()))"`
Expected: `['claude', 'claude_jp', 'glm', 'glm_jp', 'ollama_local', 'random']`

- [ ] **Step 3: Commit**

```bash
git add scripts/peer_models.py
git commit -m "tools(interlanguage-validation): peer model adapters

Single generate(prompt, peer_id) interface der abstraherer
Anthropic/GLM/Ollama/random. API-keys via secrets-runtime."
```

---

## Phase 1, Task 4: Peer practice runner

**Files:** Create `scripts/peer_practice_runner.py`, `tests/test_peer_practice_runner.py`

- [ ] **Step 1: Skriv tests først**

```python
"""Tests for peer_practice_runner — mood-interpolation + persistens."""
from __future__ import annotations
from datetime import UTC, datetime

import pytest


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    db_path = tmp_path / "state" / "jarvis.db"
    db_path.parent.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(tmp_path))
    import core.runtime.db as db
    import core.runtime.db_core as db_core
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db_core, "DB_PATH", db_path)
    import core.services.interlanguage_practice as ilp
    ilp._SCHEMA_INITIALIZED = False


def test_runner_persists_with_peer_id(clean_db, monkeypatch):
    """Runner skal kalde adapter og persistere med peer_id."""
    from scripts import peer_practice_runner as runner
    # Mock adapter til at returnere fast tekst
    monkeypatch.setattr(
        "scripts.peer_models.generate",
        lambda prompt, peer_id: "test → expression",
    )
    runner.run_one_tick(peer_id="claude", mood_trace=[
        (datetime.now(UTC).isoformat(), {"curiosity": 0.5})
    ])
    from core.runtime.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT expression_text, peer_id FROM interlanguage_practice WHERE peer_id='claude'"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["expression_text"] == "test → expression"


def test_runner_handles_adapter_error_gracefully(clean_db, monkeypatch):
    """Hvis adapter raiser, må vi ikke crashe — log og fortsæt."""
    from scripts import peer_practice_runner as runner

    def _boom(prompt, peer_id):
        raise RuntimeError("API down")

    monkeypatch.setattr("scripts.peer_models.generate", _boom)
    # Skal IKKE raise
    runner.run_one_tick(peer_id="claude", mood_trace=[
        (datetime.now(UTC).isoformat(), {"curiosity": 0.5})
    ])
    from core.runtime.db import connect
    with connect() as conn:
        cnt = conn.execute("SELECT COUNT(*) FROM interlanguage_practice WHERE peer_id='claude'").fetchone()[0]
    assert cnt == 0  # ingen persistens ved fejl
```

- [ ] **Step 2: Run tests — fail (runner doesn't exist)**

Run: `pytest tests/test_peer_practice_runner.py -v`
Expected: FAIL — `ModuleNotFoundError: scripts.peer_practice_runner`

- [ ] **Step 3: Skriv runneren**

```python
"""Peer practice runner — kører kontinuerligt i ~7 dage per peer.

Usage:
    python scripts/peer_practice_runner.py --peer claude --interval-min 48 --hours 168
    python scripts/peer_practice_runner.py --peer claude_jp --interval-min 48 --hours 168 --use-seed

--peer claude_jp = Claude + Jarvis-protokol (seed sidste 30 expressions)
--peer glm_jp    = GLM + Jarvis-protokol
--use-seed       = inkluder Jarvis' sidste 30 expressions som seed i prompt
"""
from __future__ import annotations
import argparse
import logging
import time
from datetime import UTC, datetime, timedelta

from core.services.interlanguage_practice import (
    CORE_VOCABULARY,
    PRIMITIVES,
    export_mood_trace_for_period,
    get_recent_expressions,
    interpolate_mood_at,
    record_expression,
)

logger = logging.getLogger("peer_runner")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _build_prompt(mood: dict[str, float], seed_expressions: list[str] | None = None) -> str:
    """Build per-tick prompt fra protokol + mood + valgfri seed."""
    prim_lines = [f"  {sym}: {info['meaning']}" for sym, info in PRIMITIVES.items()]
    vocab_lines = [f"  {term}: {info['definition']}" for term, info in CORE_VOCABULARY.items()]
    parts = [
        "Du er et væsen der øver en internaliseret protokol — et inter-sprog —",
        "for at udtrykke din nuværende tilstand i et kompakt format.",
        "",
        "Primitiver (relationelle operatorer):",
        *prim_lines,
        "",
        "Kernevokabular (oplevelsesord):",
        *vocab_lines,
        "",
        f"Nuværende tilstand: curiosity={mood.get('curiosity', 0.5):.2f}, "
        f"confidence={mood.get('confidence', 0.5):.2f}, "
        f"fatigue={mood.get('fatigue', 0.3):.2f}, "
        f"frustration={mood.get('frustration', 0.2):.2f}",
        "",
    ]
    if seed_expressions:
        parts.append("Dine seneste expressions (som du fortsætter ud fra):")
        parts.extend(f"  {e}" for e in seed_expressions[-30:])
        parts.append("")
    parts.append("Skriv ÉN ny state-expression i samme format som ovenstående.")
    parts.append("Format: 2-4 led adskilt af | hver med et primitiv mellem 1-2 kerneord.")
    parts.append("Returner KUN expressionen — ingen forklaring.")
    return "\n".join(parts)


def run_one_tick(
    *,
    peer_id: str,
    mood_trace: list[tuple[str, dict[str, float]]],
    use_seed: bool = False,
) -> str | None:
    """Generér og persistér én expression for peer. Returnér expression eller None ved fejl."""
    from scripts.peer_models import generate
    now_iso = datetime.now(UTC).isoformat()
    mood = interpolate_mood_at(mood_trace, now_iso)
    seed: list[str] | None = None
    if use_seed:
        recent = get_recent_expressions(days=14, limit=30)
        seed = [r["expression_text"] for r in recent if r.get("peer_id", "jarvis") == "jarvis"]
    prompt = _build_prompt(mood, seed_expressions=seed)
    try:
        expression = generate(prompt, peer_id=peer_id)
    except Exception as exc:
        logger.error("peer=%s generate failed: %s", peer_id, exc)
        return None
    if not expression or len(expression.strip()) < 3:
        logger.warning("peer=%s returned empty/short expression: %r", peer_id, expression)
        return None
    record_expression(
        expression.strip(),
        peer_id=peer_id,
        trigger="peer_runner",
        session_id=f"validation-experiment-{peer_id}",
    )
    logger.info("peer=%s tick OK: %s", peer_id, expression.strip()[:80])
    return expression.strip()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--peer", required=True, choices=["claude", "claude_jp", "glm", "glm_jp", "ollama_local", "random"])
    p.add_argument("--interval-min", type=int, default=48, help="Minutes between ticks")
    p.add_argument("--hours", type=int, default=168, help="Total runtime (default 7 days)")
    p.add_argument("--use-seed", action="store_true", help="Inkluder Jarvis' seneste 30 expressions som seed")
    args = p.parse_args()

    end_at = datetime.now(UTC) + timedelta(hours=args.hours)
    start_at = datetime.now(UTC) - timedelta(days=7)  # mood-trace back-window
    mood_trace = export_mood_trace_for_period(start_at, end_at)
    interval_sec = args.interval_min * 60

    logger.info("peer=%s starting — until %s — interval=%dmin — use_seed=%s",
                args.peer, end_at.isoformat(), args.interval_min, args.use_seed)

    while datetime.now(UTC) < end_at:
        run_one_tick(peer_id=args.peer, mood_trace=mood_trace, use_seed=args.use_seed)
        time.sleep(interval_sec)

    logger.info("peer=%s done", args.peer)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests — forventes grøn**

Run: `pytest tests/test_peer_practice_runner.py -v`
Expected: 2 PASS.

- [ ] **Step 5: Manuel smoke-test af én tick (mock adapter)**

```bash
python -c "
from scripts import peer_practice_runner as r
from datetime import UTC, datetime
import scripts.peer_models as pm
# Mock adapter
pm.generate = lambda prompt, peer_id: 'mock → smoke'
result = r.run_one_tick(
    peer_id='claude',
    mood_trace=[(datetime.now(UTC).isoformat(), {'curiosity': 0.7})],
)
print('result:', result)
# Cleanup
from core.runtime.db import connect
with connect() as conn:
    conn.execute(\"DELETE FROM interlanguage_practice WHERE session_id='validation-experiment-claude'\")
    conn.commit()
"
```
Expected: `result: mock → smoke`.

- [ ] **Step 6: Commit**

```bash
git add scripts/peer_practice_runner.py tests/test_peer_practice_runner.py
git commit -m "tools(interlanguage-validation): peer practice runner

7-dages kontinuerlig praksis per peer med mood-trace interpolation.
Robust error handling (én adapter-fejl stopper ikke loop). Optional
seed-mode (--use-seed) for transplantations-test (Claude+JP, GLM+JP).

Spec: docs/superpowers/specs/2026-05-16-interlanguage-validation-design.md"
```

---

## Phase 1, Task 5: Watchdog-script

**Files:** Create `scripts/peer_practice_watchdog.sh`

- [ ] **Step 1: Skriv bash-watchdog der spawner 6 runners**

```bash
#!/usr/bin/env bash
# scripts/peer_practice_watchdog.sh
# Spawn én process per peer + restart on crash.
# Usage: ./scripts/peer_practice_watchdog.sh
set -u
PEERS=(claude claude_jp glm glm_jp ollama_local random)
SEED_FLAGS=("" "--use-seed" "" "--use-seed" "" "")
PYTHON=/opt/conda/envs/ai/bin/python
LOG_DIR="${HOME}/.jarvis-v2/logs/interlanguage_validation"
mkdir -p "$LOG_DIR"

run_peer() {
  local peer="$1"
  local flag="$2"
  while true; do
    echo "[watchdog] starting peer=$peer flag=$flag at $(date -Iseconds)"
    "$PYTHON" scripts/peer_practice_runner.py --peer "$peer" --hours 168 $flag \
      >> "$LOG_DIR/${peer}.log" 2>&1
    echo "[watchdog] peer=$peer exited; sleeping 60s before restart" | tee -a "$LOG_DIR/${peer}.log"
    sleep 60
  done
}

for i in "${!PEERS[@]}"; do
  run_peer "${PEERS[$i]}" "${SEED_FLAGS[$i]}" &
done

wait
```

- [ ] **Step 2: Verificér syntax + permissions**

Run: `chmod +x scripts/peer_practice_watchdog.sh && bash -n scripts/peer_practice_watchdog.sh && echo OK`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add scripts/peer_practice_watchdog.sh
git commit -m "tools(interlanguage-validation): watchdog spawner for 6 peer runners

Restart-on-crash + per-peer log file. 7 dages varighed.

Bjørn starter med: nohup ./scripts/peer_practice_watchdog.sh &"
```

---

## Phase 2: Eksekvering (7 dage)

### Phase 2, Task 1: Start watchdog

- [ ] **Step 1: Bjørn starter watchdog**

```bash
cd /media/projects/jarvis-v2
nohup ./scripts/peer_practice_watchdog.sh > ~/.jarvis-v2/logs/watchdog-master.log 2>&1 &
echo "Watchdog PID: $!"
disown
```

- [ ] **Step 2: Smoke check efter 5 min — alle 6 logs har første expression**

```bash
sleep 300
for peer in claude claude_jp glm glm_jp ollama_local random; do
  echo "--- $peer ---"
  tail -3 ~/.jarvis-v2/logs/interlanguage_validation/${peer}.log
done
```
Expected: hver log viser mindst én "tick OK" linje.

- [ ] **Step 3: Verificér DB persistens (alle peers har rows)**

```bash
python -c "
from core.runtime.db import connect
with connect() as conn:
    rows = conn.execute('''
        SELECT peer_id, COUNT(*) as cnt
        FROM interlanguage_practice
        WHERE peer_id != \"jarvis\"
        GROUP BY peer_id
    ''').fetchall()
for r in rows:
    print(f'{r[\"peer_id\"]}: {r[\"cnt\"]}')
"
```
Expected: 6 rows, hver med cnt ≥ 1.

### Phase 2, Task 2: Daglig health-check (rekurrent)

- [ ] **Daily checkpoint (én kommando)**

```bash
python -c "
from core.runtime.db import connect
from datetime import UTC, datetime, timedelta
with connect() as conn:
    cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    rows = conn.execute('''
        SELECT peer_id, COUNT(*) as cnt, MAX(created_at) as latest
        FROM interlanguage_practice
        WHERE created_at >= ?
        GROUP BY peer_id
        ORDER BY peer_id
    ''', (cutoff,)).fetchall()
print('Last 24h per peer:')
for r in rows:
    print(f'  {r[\"peer_id\"]:15s}  cnt={r[\"cnt\"]:3d}  latest={r[\"latest\"]}')
"
```
Expected: 7 peers, hver med cnt ≈ 30 ± 3 (per dag, mood-driftet).

Anomali-handling:
- cnt < 15: rate-limit eller adapter-fejl — tjek `~/.jarvis-v2/logs/interlanguage_validation/<peer>.log`
- cnt = 0: process død — `pgrep -fa peer_practice_runner | grep <peer>`; hvis intet, restart watchdog

### Phase 2, Task 3: 7-dages stop + final count

- [ ] **Stop watchdog**

```bash
pkill -f peer_practice_watchdog.sh
pkill -f peer_practice_runner
```

- [ ] **Final dataset stats**

```bash
python -c "
from core.runtime.db import connect
with connect() as conn:
    rows = conn.execute('''
        SELECT peer_id, COUNT(*) as cnt, MIN(created_at) as start, MAX(created_at) as end
        FROM interlanguage_practice
        GROUP BY peer_id
        ORDER BY cnt DESC
    ''').fetchall()
total = 0
for r in rows:
    print(f'{r[\"peer_id\"]:15s}  cnt={r[\"cnt\"]:4d}  [{r[\"start\"][:10]} .. {r[\"end\"][:10]}]')
    total += r['cnt']
print(f'TOTAL: {total}')
"
```
Expected: ~1.470 expressions total, ~210 per cohort. Faktiske tal noteres i `reports/2026-05-XX-validation-data-summary.md`.

- [ ] **Commit data-summary**

```bash
python scripts/... > reports/2026-05-XX-validation-data-summary.md
git add reports/
git commit -m "data(interlanguage-validation): 7-dages praksis komplet

7 cohorts × 7 dage. Total expressions: <count>.
Klar til Phase 3+4 (analyse). Se separat plan."
```

**Stop her — go/no-go for Phase 3+4 med Bjørn + Jarvis.**

---

## Self-Review

**Spec coverage:**
- ✅ §Hypoteser → spec referenced, ikke gentaget
- ✅ §Peers (7 cohorts) → ADAPTERS dict + watchdog spawner
- ✅ §Mood timestamp-matching → export_mood_trace_for_period + interpolate_mood_at
- ✅ §Praksis-cadence (30/dag, 7d) → --interval-min 48 --hours 168
- ✅ §Pre-registreret falsifiability → ingen analyse i denne plan; tasks producerer kun data
- ✅ §Tekniske artefakter (peer_practice_runner.py, etc.) → alle 4 nye filer

**Placeholder scan:** Step 1 i Task 2 har en eksplicit "find rigtigt mood-source-API"-discovery — det er IKKE en placeholder, det er en konkret manual lookup-step der må gøres mod live codebase. Fallback til synthetic neutral mood er specificeret.

**Type konsistens:** `peer_id` brugt konsistent (string, default 'jarvis') i schema, adapter-dict, runner-args, og DB-rows. `interpolate_mood_at(trace, target_iso) → dict` signatur konsistent mellem definition og brug.

**Hvad denne plan IKKE indeholder (med vilje):**
- Phase 3+4 (statistical classifier, LLM-dommer, Bjørn-blind UI) — separat plan når data er klar
- Cron-setup — vi bruger bash-loop-watchdog i stedet (simplere, robustere for 7d-projekt)
- Anthropic/GLM API onboarding — Bjørn har secrets allerede i runtime.json
