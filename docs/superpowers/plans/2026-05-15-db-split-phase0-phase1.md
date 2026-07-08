---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# db.py Split — Phase 0 + Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Udskil `db_core.py` (infrastructure) og `db_capability_approval.py` (warm-up klynge) fra `core/runtime/db.py`, og konverter `db.py` til facade der re-eksporterer fra disse to nye moduler. Bevar 100% bagudkompat for alle 5.317 import-sites.

**Architecture:** `db.py` flyttes mod ren facade. `db_core.py` indeholder forbindelses-, schema-bootstrap-, konstant- og helper-symboler som alle andre `db_*.py` må importere fra. `db_capability_approval.py` er den første domæne-fil i ny stil — bruges som warm-up til at validere gate-processen før store klynger angribes i senere faser.

**Tech Stack:** Python 3.11+, sqlite3, pytest, conda environment `ai`.

**Spec:** `docs/superpowers/specs/2026-05-15-db-split-design.md`

**Refactoring, ikke nyt behavior:** Dette projekt flytter eksisterende kode. TDD-loop'et "skriv failing test → implementer" giver ikke mening — vi tilføjer ingen ny adfærd. I stedet er testen at den **eksisterende** test-suite forbliver grøn + at vi sampler 5.317 import-sites for at verificere. Den eneste "nye" test er en lille import-sanity-test der eksplicit importerer hver nyt-flyttet symbol fra både gammel og ny sti.

---

## Per-fase gates (ikke-forhandlelige)

Hver Phase skal passere ALLE fire gates før commit. Gate-detaljer er specificeret i Task 4 (Phase 0) og Task 10 (Phase 1) — disse skal ALTID køres.

| Gate | Hvordan | Pass-kriterium |
|---|---|---|
| Test-gate | `conda activate ai && pytest tests/ -x --tb=short` | Alle tests pass |
| Import-gate | Sample-script importerer udvalgte symboler fra `core.runtime.db` | Ingen ImportError |
| Performance-gate | Cold + warm import-måling | Cold ≤ 150ms, warm ≤ 25ms (baselines: 135ms / 16ms) |
| Live-gate | Restart `jarvis-runtime` + `jarvis-api`, smoke check | Heartbeat ticker, chat svarer, ingen exceptions i log |

---

## File Structure

**Phase 0:**
- Create: `core/runtime/db_core.py`
- Modify: `core/runtime/db.py` (kun fjern/re-eksporter infrastructure)
- Create: `tests/runtime/test_db_split_imports.py` (import-sanity-test)
- Create: `scripts/db_split_baseline.py` (performance-måling)

**Phase 1:**
- Create: `core/runtime/db_capability_approval.py`
- Modify: `core/runtime/db.py` (fjern capability_approval_* + approval_feedback_*, tilføj re-eksport)
- Modify: `tests/runtime/test_db_split_imports.py` (tilføj nye symboler)

---

## Task 1: Rekognoscering og baseline-måling

**Files:**
- Create: `scripts/db_split_baseline.py`

- [ ] **Step 1: Find infrastructure-symboler i db.py**

Kør i jarvis-v2 rod:

```bash
conda activate ai
python << 'PY'
import ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)

# Top-level konstanter + classes + nøglefunktioner
INFRA_FUNCS = {'connect', 'init_db', '_now_iso', '_rank_for',
               '_stronger_ranked_value', '_merge_text_fragments',
               'set_runtime_state_value', 'get_runtime_state_value',
               '_conn_db_id', '_install_ensure_once_cache',
               'invalidate_ensure_once_cache'}
INFRA_CLASSES = {'ClosingConnection'}
INFRA_CONSTS = {'DB_PATH', '_CONFIDENCE_RANKS', '_EVIDENCE_CLASS_RANKS',
                '_SOURCE_KIND_RANKS', '_SIGNAL_TABLES_WITH_STATUS',
                '_ENSURED_TABLES'}

print("INFRASTRUCTURE SURFACE:")
for n in tree.body:
    end = getattr(n, 'end_lineno', '?')
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in INFRA_FUNCS:
        print(f"  func L{n.lineno}-{end}: {n.name}")
    elif isinstance(n, ast.ClassDef) and n.name in INFRA_CLASSES:
        print(f"  class L{n.lineno}-{end}: {n.name}")
    elif isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name) and t.id in INFRA_CONSTS:
                print(f"  const L{n.lineno}: {t.id}")
    elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id in INFRA_CONSTS:
        print(f"  annconst L{n.lineno}: {n.target.id}")
PY
```

Forventet output (cirka):
- `const L11: DB_PATH`
- `const L12: _CONFIDENCE_RANKS`
- `const L13: _EVIDENCE_CLASS_RANKS`
- `const L20: _SOURCE_KIND_RANKS`
- `class L29-34: ClosingConnection`
- `func L37-41: connect`
- `func L43-44: _rank_for`
- `func L47-50: _stronger_ranked_value`
- `func L53-66: _merge_text_fragments`
- `func L69-86: set_runtime_state_value`
- `func L89-103: get_runtime_state_value`
- `func L105-1128: init_db` (1023 linjer — kæmpe)
- `func L29797-29799: _now_iso`
- `annconst L33554: _SIGNAL_TABLES_WITH_STATUS`
- `annconst L33998: _ENSURED_TABLES`
- `func L34003-34023: _conn_db_id`
- `func L34025-34053: _install_ensure_once_cache`
- `func L34055-34070: invalidate_ensure_once_cache`
- `EXPR L34072: _install_ensure_once_cache()` ← top-level kald (side-effekt)

Bemærk linje-numre kan have shiftet ±10 hvis filen har set ændringer siden plan blev skrevet. Brug AST-outputtet som autoritet.

- [ ] **Step 2: Verificér ingen `global` keyword bruges i andre funktioner**

```bash
python -c "
import ast
src = open('core/runtime/db.py').read()
class GV(ast.NodeVisitor):
    def __init__(self): self.hits = []
    def visit_Global(self, node): self.hits.append((node.lineno, node.names))
gv = GV(); gv.visit(ast.parse(src))
print(f'global keyword usage: {len(gv.hits)} occurrences')
for ln, names in gv.hits[:20]: print(f'  L{ln}: global {names}')
"
```

Forventet: `global keyword usage: 0 occurrences` (verificeret i recon).

Hvis det IKKE er 0, stop og rapportér til Bjørn — splittet skal håndtere shared module state.

- [ ] **Step 3: Lav baseline-måling**

Opret `scripts/db_split_baseline.py`:

```python
"""Mål cold + warm import-tid for core.runtime.db.

Brug: conda activate ai && python scripts/db_split_baseline.py [--label LABEL]

Skriver én linje per kørsel til scripts/.db_split_baseline.log med format:
  ISO_TIME  LABEL  COLD_MS  WARM_MS
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from datetime import datetime, UTC
from pathlib import Path


def measure(label: str) -> tuple[float, float]:
    repo = Path(__file__).resolve().parent.parent
    # Nuke .pyc cache for core.runtime
    for cache in (repo / "core" / "runtime").rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

    # Cold: fresh process, no .pyc
    cold = subprocess.check_output(
        [sys.executable, "-c",
         "import time; t=time.perf_counter(); "
         "from core.runtime import db; "
         "print(f'{(time.perf_counter()-t)*1000:.2f}')"],
        cwd=repo, text=True).strip()

    # Warm: fresh process, .pyc now cached from cold run
    warm = subprocess.check_output(
        [sys.executable, "-c",
         "import time; t=time.perf_counter(); "
         "from core.runtime import db; "
         "print(f'{(time.perf_counter()-t)*1000:.2f}')"],
        cwd=repo, text=True).strip()

    return float(cold), float(warm)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--label", default="unspecified")
    args = p.parse_args()

    cold, warm = measure(args.label)
    line = f"{datetime.now(UTC).isoformat()}  {args.label}  cold={cold:.2f}ms  warm={warm:.2f}ms\n"
    log = Path(__file__).resolve().parent / ".db_split_baseline.log"
    log.write_text((log.read_text() if log.exists() else "") + line)
    print(line.strip())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Kør baseline tre gange og noter resultater**

```bash
conda activate ai
python scripts/db_split_baseline.py --label baseline_before
python scripts/db_split_baseline.py --label baseline_before
python scripts/db_split_baseline.py --label baseline_before
```

Forventet output (cirka): `cold=130-150ms  warm=14-20ms` per kørsel.

Skriv de tre cold-værdier ned. **Performance-gate er at cold-import efter Phase 0 og Phase 1 ikke må overskride MAX af baseline + 15ms (ca. 150ms øvre grænse).**

- [ ] **Step 5: Commit baseline-scriptet**

```bash
git add scripts/db_split_baseline.py
git commit -m "tools(db-split): add cold/warm import baseline script

Måler import-tid for core.runtime.db. Bruges til performance-gate
under Phase 0+1 split af db.py.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Opret import-sanity-test

**Files:**
- Create: `tests/runtime/test_db_split_imports.py`

Denne test er vores import-gate i automatiseret form. Den importerer eksplicit hver flyttet symbol fra både `core.runtime.db` (facaden) og senere fra det nye submodul. Hvis split brækker noget, fanger denne test det med en klar fejlmeddelelse.

- [ ] **Step 1: Opret tests/runtime/ hvis den ikke eksisterer**

```bash
mkdir -p tests/runtime
[ -f tests/runtime/__init__.py ] || touch tests/runtime/__init__.py
```

- [ ] **Step 2: Skriv testen**

Skriv til `tests/runtime/test_db_split_imports.py`:

```python
"""Import-sanity-test for db.py split.

Verificerer at alle symboler som split-faserne flytter stadig er
importerbare fra `core.runtime.db` (facaden). Hvis Phase 0 eller
senere fase brækker en re-eksport, fejler denne test med klar
besked om hvilket symbol der mangler.

Tilføj symboler her per fase efterhånden som de flyttes.
"""
from __future__ import annotations

import importlib


def _assert_importable(module: str, symbols: list[str]) -> None:
    mod = importlib.import_module(module)
    missing = [s for s in symbols if not hasattr(mod, s)]
    assert not missing, (
        f"Mangler symboler i {module}: {missing}. "
        f"Sikr at facaden re-eksporterer fra det nye submodul."
    )


# Phase 0: infrastructure symboler — skal være importerbare fra
# BÅDE core.runtime.db (facade) OG core.runtime.db_core (direkte).
PHASE_0_SYMBOLS = [
    "DB_PATH",
    "_CONFIDENCE_RANKS",
    "_EVIDENCE_CLASS_RANKS",
    "_SOURCE_KIND_RANKS",
    "_SIGNAL_TABLES_WITH_STATUS",
    "_ENSURED_TABLES",
    "ClosingConnection",
    "connect",
    "init_db",
    "_now_iso",
    "_rank_for",
    "_stronger_ranked_value",
    "_merge_text_fragments",
    "set_runtime_state_value",
    "get_runtime_state_value",
    "_conn_db_id",
    "_install_ensure_once_cache",
    "invalidate_ensure_once_cache",
]


def test_phase0_symbols_on_facade():
    _assert_importable("core.runtime.db", PHASE_0_SYMBOLS)


def test_phase0_symbols_on_db_core():
    _assert_importable("core.runtime.db_core", PHASE_0_SYMBOLS)


def test_connect_returns_working_connection():
    from core.runtime.db import connect
    with connect() as conn:
        row = conn.execute("SELECT 1 AS one").fetchone()
        assert row["one"] == 1


def test_ensure_once_cache_is_installed():
    """Verificer at _install_ensure_once_cache har wrapped _ensure_*_table funcs."""
    from core.runtime import db
    ensure_funcs = [
        getattr(db, n) for n in dir(db)
        if n.startswith("_ensure_") and n.endswith("_table") and callable(getattr(db, n, None))
    ]
    assert ensure_funcs, "Forventede mindst én _ensure_*_table funktion på facaden"
    wrapped = [f for f in ensure_funcs if getattr(f, "_ensure_once_wrapped", False)]
    assert wrapped, (
        f"Ingen _ensure_*_table funktioner er wrappet. "
        f"Sikr at _install_ensure_once_cache() kaldes efter facade-re-eksporterne. "
        f"Fundet: {len(ensure_funcs)} _ensure_* funcs, {len(wrapped)} wrappet."
    )
```

- [ ] **Step 3: Kør testen — den skal pt. fejle på `test_phase0_symbols_on_db_core` (db_core eksisterer ikke endnu)**

```bash
conda activate ai
pytest tests/runtime/test_db_split_imports.py -v
```

Forventet: `test_phase0_symbols_on_facade` PASS, `test_phase0_symbols_on_db_core` FAIL med `ModuleNotFoundError: core.runtime.db_core`, `test_connect_returns_working_connection` PASS, `test_ensure_once_cache_is_installed` PASS.

Det er det rigtige startpunkt — testen vil grønne sig selv når db_core eksisterer.

- [ ] **Step 4: Commit testen**

```bash
git add tests/runtime/__init__.py tests/runtime/test_db_split_imports.py
git commit -m "test(db-split): add import-sanity test for Phase 0+1 symbols

Phase 0 vil flytte 18 infrastructure-symboler til db_core.py.
Testen verificerer at både facaden (db) og det nye submodul
(db_core) eksponerer dem. Forventes initialt at fejle på
test_phase0_symbols_on_db_core indtil Task 3.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Opret `db_core.py` med infrastructure

**Files:**
- Create: `core/runtime/db_core.py`

Vi flytter de 18 infrastructure-symboler ud af db.py. Linjenumre er fra AST-scannet i Task 1 — verificér de stadig matcher før kopiering.

- [ ] **Step 1: Læs hver kildesektion fra db.py**

Brug Read-tool eller:

```bash
sed -n '1,103p'    core/runtime/db.py > /tmp/db_head.py        # imports + consts + class + connect + helpers + KV
sed -n '105,1128p' core/runtime/db.py > /tmp/db_init_db.py     # init_db (1023 linjer)
sed -n '29797,29799p' core/runtime/db.py > /tmp/db_now_iso.py  # _now_iso
sed -n '33554p'    core/runtime/db.py > /tmp/db_signal.py      # _SIGNAL_TABLES_WITH_STATUS
sed -n '33998,34072p' core/runtime/db.py > /tmp/db_ensure.py   # _ENSURED_TABLES + ensure-once cache + top-level kald
```

**VIGTIGT:** Verificér linjenumrene matcher AST-output fra Task 1, Step 1. Hvis filen har shiftet, brug AST-output som autoritet.

- [ ] **Step 2: Konstruér db_core.py**

Skriv til `core/runtime/db_core.py`:

```python
"""Core infrastructure for core.runtime.db modulet.

Indeholder:
- DB_PATH konstant
- ClosingConnection (context-manager wrapper)
- connect() — primær DB-forbindelse
- Konstant-ranks (_CONFIDENCE_RANKS, _EVIDENCE_CLASS_RANKS, _SOURCE_KIND_RANKS)
- Helper-funktioner (_rank_for, _stronger_ranked_value, _merge_text_fragments)
- init_db() — schema bootstrap for hele DB'en
- Runtime-state KV (set/get_runtime_state_value)
- _now_iso() helper
- _ensure-once cache infrastructure (_ENSURED_TABLES, _install_ensure_once_cache,
  _conn_db_id, invalidate_ensure_once_cache)

Andre db_*.py submoduler må KUN importere fra dette modul (forhindrer
cirkulære imports). Alle public symboler re-eksporteres fra
core.runtime.db facaden for bagudkompat.
"""
from __future__ import annotations

import json as _json
import sqlite3
import sys as _sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.runtime.config import STATE_DIR


# === Konstanter ===
DB_PATH = Path(STATE_DIR) / "jarvis.db"

_CONFIDENCE_RANKS = {"low": 1, "medium": 2, "high": 3}

_EVIDENCE_CLASS_RANKS = {
    "weak_signal": 1,
    "runtime_support_only": 2,
    "single_session_pattern": 3,
    "explicit_user_statement": 4,
    "repeated_cross_session": 5,
}

_SOURCE_KIND_RANKS = {
    "runtime-derived-support": 1,
    "single-session-pattern": 2,
    "session-evidence": 3,
    "repeated-user-correction": 3,
    "user-explicit": 4,
}


# === Connection ===
class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    return conn


# === Helpers ===
def _rank_for(ranks: dict[str, int], value: str) -> int:
    return int(ranks.get(str(value or "").strip().lower(), 0))


def _stronger_ranked_value(current: str, proposed: str, ranks: dict[str, int]) -> str:
    if _rank_for(ranks, proposed) >= _rank_for(ranks, current):
        return str(proposed or "")
    return str(current or "")


def _merge_text_fragments(current: str, proposed: str, *, limit: int = 3) -> str:
    parts: list[str] = []
    seen: set[str] = set()
    for raw in (current, proposed):
        for piece in str(raw or "").split(" | "):
            normalized = " ".join(piece.split()).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            parts.append(normalized)
            if len(parts) >= limit:
                return " | ".join(parts)
    return " | ".join(parts)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


# === Runtime state KV ===
def set_runtime_state_value(key: str, value: object, *, updated_at: str = "") -> None:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("key must not be empty")
    timestamp = updated_at or datetime.now(UTC).isoformat()
    payload = _json.dumps(value, ensure_ascii=False)
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO runtime_state_kv (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                updated_at = excluded.updated_at
            """,
            (normalized_key, payload, timestamp),
        )


def get_runtime_state_value(key: str, default: object = None) -> object:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        return default
    with connect() as conn:
        row = conn.execute(
            "SELECT value_json FROM runtime_state_kv WHERE key = ?",
            (normalized_key,),
        ).fetchone()
    if row is None:
        return default
    try:
        return _json.loads(str(row["value_json"]))
    except Exception:
        return default


# === init_db: schema bootstrap (~1023 linjer) ===
# Kopiér eksakt fra core/runtime/db.py L105-L1128 (verificér via AST i Task 1).
def init_db() -> None:
    with connect() as conn:
        # ... eksakt kopi af original init_db body ...
        pass  # PLACEHOLDER — Task 3 Step 3 fylder dette ind verbatim


# === _ensure-once cache infrastructure ===
# OBS: _install_ensure_once_cache er DESIGNET til at scanne sit eget
# modulnamespace og wrappe _ensure_*_table funcs. Når domænefiler senere
# tilføjes (Phase 1+), skal HVER db_*.py kalde _install_ensure_once_cache_for(__name__)
# på sit eget namespace i bunden af filen, for at få sine _ensure_* wrappet.
# Facaden (db.py) kalder også funktionen efter sine re-eksporter, så symboler
# importeret derfra også er wrappet (idempotent — wrapper checker _ensure_once_wrapped flag).

_SIGNAL_TABLES_WITH_STATUS: set[str] = set()  # PLACEHOLDER — Task 3 Step 4 erstatter med eksakt indhold fra L33554

_ENSURED_TABLES: set[tuple[str, str]] = set()


def _conn_db_id(conn: sqlite3.Connection) -> str:
    """Stable identifier for a sqlite connection's underlying database.

    For file-backed DBs this is the file path — same across all
    connect() calls in production. For :memory: DBs each connection
    has its own private database, so we use id(conn) as the discriminator
    to force per-connection re-ensure (which is what tests need).
    """
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
        for row in rows:
            name = row[1] if len(row) > 1 else ""
            path = row[2] if len(row) > 2 else ""
            if str(name) == "main":
                if path:
                    return str(path)
                return f"memory:{id(conn)}"
    except Exception:
        pass
    return f"unknown:{id(conn)}"


def _install_ensure_once_cache_for(module_name: str) -> None:
    """Wrap _ensure_*_table funcs i target-modul med once-cache.

    Tidligere version i db.py scannede kun sit eget namespace
    (sys.modules[__name__]). Den nye signatur tager target-modulnavn
    så hvert domæne-submodul kan kalde det på sig selv efter at have
    defineret sine _ensure_*_table-funktioner.
    """
    _mod = _sys.modules[module_name]
    _names = [
        _n for _n in vars(_mod).keys()
        if _n.startswith("_ensure_") and _n.endswith("_table") and callable(getattr(_mod, _n, None))
    ]
    for _name in _names:
        _orig = getattr(_mod, _name)
        if getattr(_orig, "_ensure_once_wrapped", False):
            continue

        def _make_wrapped(_fn, _fname):
            def _wrapped(*args, **kwargs):
                conn = args[0] if args else kwargs.get("conn")
                db_id = _conn_db_id(conn) if conn is not None else "no-conn"
                cache_key = (_fname, db_id)
                if cache_key in _ENSURED_TABLES:
                    return None
                _result = _fn(*args, **kwargs)
                _ENSURED_TABLES.add(cache_key)
                return _result
            _wrapped.__name__ = _fn.__name__
            _wrapped.__qualname__ = _fn.__qualname__
            _wrapped.__doc__ = _fn.__doc__
            _wrapped._ensure_once_wrapped = True  # type: ignore[attr-defined]
            _wrapped._ensure_once_orig = _fn  # type: ignore[attr-defined]
            return _wrapped
        setattr(_mod, _name, _make_wrapped(_orig, _name))


def _install_ensure_once_cache() -> None:
    """Bagudkompat-shim: wrapper de _ensure_*_table funcs der ligger på
    core.runtime.db (facaden). Kaldes fra db.py i bunden EFTER alle
    re-eksporter, så også flyttede _ensure_* fra submoduler dækkes på
    facade-niveau.
    """
    _install_ensure_once_cache_for("core.runtime.db")


def invalidate_ensure_once_cache(table_name: str | None = None) -> None:
    """Force re-run of `_ensure_*_table` on next call.

    Pass None to clear all (e.g. after switching DB files in tests).
    Pass a specific table name to re-ensure that one table (matches by
    function-name prefix across all DB paths).
    """
    if table_name is None:
        _ENSURED_TABLES.clear()
    else:
        to_remove = {key for key in _ENSURED_TABLES if key[0] == table_name}
        for key in to_remove:
            _ENSURED_TABLES.discard(key)
```

- [ ] **Step 3: Erstat `init_db` PLACEHOLDER med eksakt body fra db.py**

Brug Read-tool på `core/runtime/db.py` linjer 105-1128. Kopiér body af `init_db()` verbatim ind i db_core.py — IKKE ændre noget. Funktion-signatur er allerede skrevet i Step 2, kun body skal fyldes.

VERIFICÉR efter kopiering: linjeantal i db_core.py er ca. 1023 + ~180 (resten) ≈ 1200 linjer.

- [ ] **Step 4: Erstat `_SIGNAL_TABLES_WITH_STATUS` PLACEHOLDER**

Læs db.py linje 33554 (og evt. omkringliggende linjer hvis det er multi-linje). Kopiér eksakt annotation + værdi til db_core.py hvor PLACEHOLDER står.

- [ ] **Step 5: Verificér db_core.py compiler ren**

```bash
python -m compileall -q core/runtime/db_core.py
```

Forventet: ingen output (success).

- [ ] **Step 6: Verificér db_core.py kan importeres alene**

```bash
python -c "from core.runtime import db_core; print('OK', sorted(s for s in dir(db_core) if not s.startswith('__'))[:10])"
```

Forventet: `OK [...første 10 symboler alfabetisk...]` uden exception.

- [ ] **Step 7: Kør import-sanity-test (nu skal `test_phase0_symbols_on_db_core` passe)**

```bash
conda activate ai
pytest tests/runtime/test_db_split_imports.py::test_phase0_symbols_on_db_core -v
```

Forventet: PASS.

- [ ] **Step 8: Commit db_core.py (db.py er endnu ikke modificeret)**

```bash
git add core/runtime/db_core.py
git commit -m "refactor(db): create db_core.py with infrastructure symbols

Phase 0 step 1/2: db_core.py indeholder de 18 infrastructure-symboler
(connect, init_db, pragmas, ranks, helpers, _ensure-once cache infra).
db.py er stadig source-of-truth indtil næste commit der konverterer
den til facade.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Konverter db.py til facade for Phase 0 symboler

**Files:**
- Modify: `core/runtime/db.py` (fjern de 18 symboler, tilføj re-eksport-blok)

Strategi: Vi sletter de gamle definitioner i db.py og erstatter dem med eksplicit re-eksport fra db_core. Alle øvrige 690 funktioner forbliver uændret i db.py — de tages i senere faser.

- [ ] **Step 1: Læs nuværende db.py header (linje 1-110) til reference**

Brug Read-tool på `core/runtime/db.py` linjer 1-110. Du skal eksakt vide hvad der skal slettes.

- [ ] **Step 2: Erstat db.py linjer 1-103 med facade-header**

Brug Edit-tool. `old_string` = præcis blok fra linje 1 (med `from __future__`) til og med slutningen af `get_runtime_state_value` (linje 103). `new_string` = facade-header:

```python
"""Facade for core.runtime.db submodules.

Genererer bagudkompatibel import-overflade for 5.317 eksisterende
import-sites. Alt nyt kode bør importere direkte fra submoduler
(fx core.runtime.db_core eller core.runtime.db_<theme>).

Split-historik: docs/superpowers/specs/2026-05-15-db-split-design.md
"""
from __future__ import annotations

import json as _json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from core.runtime.config import STATE_DIR

# === Phase 0 re-eksporter fra db_core ===
from core.runtime.db_core import (
    DB_PATH,
    _CONFIDENCE_RANKS,
    _EVIDENCE_CLASS_RANKS,
    _SOURCE_KIND_RANKS,
    ClosingConnection,
    connect,
    _rank_for,
    _stronger_ranked_value,
    _merge_text_fragments,
    set_runtime_state_value,
    get_runtime_state_value,
    init_db,
    _now_iso,
)
```

Bemærk: import-linjer fra original (json, sqlite3, datetime, Path, uuid4, STATE_DIR) bevares fordi resten af db.py (de 690 ikke-flyttede funktioner) bruger dem.

- [ ] **Step 3: Slet definitionen af `init_db` (linjer 105-1128 efter Step 2)**

Brug Read-tool på den modificerede db.py for at finde de nye linje-numre for init_db. Brug derefter Edit til at slette hele `def init_db(): ...` blokken.

OBS: linje-numre har shiftet pga. Step 2's replacement. Find via AST eller grep:

```bash
python -c "
import ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name == 'init_db':
        print(f'L{n.lineno}-{n.end_lineno}')
"
```

Brug Edit-tool, `old_string` = hele init_db body inkl. `def init_db() -> None:`-linjen, `new_string` = "" (eller en kommentar-marker: `# init_db er re-eksporteret fra db_core (se header).`)

- [ ] **Step 4: Slet `_now_iso` (omkring linje 29797 før shift, nu lavere)**

Find aktuel position:

```bash
python -c "
import ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name == '_now_iso':
        print(f'L{n.lineno}-{n.end_lineno}')
"
```

Edit-tool sletter den 3-linjers function definition.

- [ ] **Step 5: Slet `_conn_db_id`, `_install_ensure_once_cache`, `invalidate_ensure_once_cache` + erstat top-level kald**

Find aktuelle positioner med samme AST-pattern. Disse skal flyttes:
- `_SIGNAL_TABLES_WITH_STATUS` (annotation) — slet, importér fra db_core
- `_ENSURED_TABLES` (annotation) — slet, importér fra db_core
- `_conn_db_id` (function) — slet, importér fra db_core
- `_install_ensure_once_cache` (function) — slet
- `invalidate_ensure_once_cache` (function) — slet, importér fra db_core
- Top-level `_install_ensure_once_cache()` kald — **bevar**, men flyttes til absolut bunden efter alle import-statements har kørt

Tilføj til db.py's import-blok øverst:

```python
# Cache-infrastructure re-eksporter
from core.runtime.db_core import (
    _SIGNAL_TABLES_WITH_STATUS,
    _ENSURED_TABLES,
    _conn_db_id,
    _install_ensure_once_cache,
    invalidate_ensure_once_cache,
)
```

Erstat top-level kald i bunden af db.py med:

```python
# Wrap alle _ensure_*_table funcs der nu lever på facaden (re-eksporteret
# fra db_core plus de 117 der stadig er defineret direkte i db.py).
# Når senere faser flytter _ensure_*-funcs til submoduler, kalder hver
# submodul også _install_ensure_once_cache_for(__name__) på sig selv.
_install_ensure_once_cache()
```

- [ ] **Step 6: Verificér db.py compiler**

```bash
python -m compileall -q core/runtime/db.py
```

Forventet: ingen output.

- [ ] **Step 7: Verificér db.py importerer rent**

```bash
python -c "from core.runtime import db; print('OK', db.connect, db.init_db, db._install_ensure_once_cache)"
```

Forventet: `OK <function connect at ...> <function init_db at ...> <function _install_ensure_once_cache at ...>`.

- [ ] **Step 8: Kør import-sanity-test**

```bash
pytest tests/runtime/test_db_split_imports.py -v
```

Forventet: alle 4 tests PASS.

---

## Task 5: Phase 0 — Kør de 4 gates

- [ ] **Test-gate: Kør hele test-suiten**

```bash
conda activate ai
pytest tests/ -x --tb=short 2>&1 | tail -30
```

Forventet: alle tests pass (sidste linje ca. `188 passed in XX.XXs`).

Hvis nogen test fejler: STOP, diagnose, fix. Ingen "skip and continue".

- [ ] **Import-gate: Sample-import af 30 tilfældige symboler**

```bash
python << 'PY'
"""Importér 30 symboler tilfældigt fra db.py via facaden."""
import importlib, random, ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)
names = []
for n in tree.body:
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith('_'):
        names.append(n.name)
random.seed(42)
sample = random.sample(names, min(30, len(names)))
db = importlib.import_module('core.runtime.db')
missing = [s for s in sample if not hasattr(db, s)]
print(f"Sampled {len(sample)} symbols. Missing: {len(missing)}")
if missing:
    print(f"FAIL — missing symbols: {missing}")
else:
    print("OK — alle 30 importerbare")
PY
```

Forventet: `OK — alle 30 importerbare`.

- [ ] **Performance-gate: Mål cold + warm import**

```bash
python scripts/db_split_baseline.py --label phase0_after
python scripts/db_split_baseline.py --label phase0_after
python scripts/db_split_baseline.py --label phase0_after
```

Forventet: cold-import skal være ≤ MAX(baseline_before-værdierne) + 15ms. Hvis fx baseline var 135ms, accepteres op til 150ms.

Hvis cold-import er over grænsen: STOP. Sandsynligvis pga. import-chain-pollution. Diagnose før commit.

- [ ] **Live-gate: Restart services og smoke check**

```bash
sudo systemctl restart jarvis-runtime jarvis-api
sleep 3
sudo systemctl status jarvis-runtime --no-pager | head -10
sudo systemctl status jarvis-api --no-pager | head -10
```

Verificér:
1. Begge services er `active (running)`
2. Ingen ERROR-linjer i de seneste 30 sekunder af log:

```bash
sudo journalctl -u jarvis-runtime --since "30 seconds ago" --no-pager | grep -E "ERROR|Traceback" | head -5
sudo journalctl -u jarvis-api --since "30 seconds ago" --no-pager | grep -E "ERROR|Traceback" | head -5
```

Forventet: ingen output (ingen errors).

3. Smoke-test heartbeat:

```bash
curl -s http://localhost:8401/api/heartbeat/status | python -m json.tool | head -20
```

Forventet: gyldig JSON med `currently_ticking` og `last_tick_at` felter.

Hvis nogen gate fejler: revert til Task 3 commit (`git reset --hard <SHA>`), diagnose, retry. **Aldrig commit ved gate-fejl.**

---

## Task 6: Commit Phase 0

- [ ] **Step 1: Verificér git status**

```bash
git status --short
```

Forventet: kun `core/runtime/db.py` og `tests/runtime/test_db_split_imports.py` (sidstnævnte hvis ændret) som modificeret.

- [ ] **Step 2: Commit**

```bash
git add core/runtime/db.py tests/runtime/test_db_split_imports.py
git commit -m "refactor(db): convert db.py to facade for Phase 0 symbols

Phase 0 step 2/2: db.py re-eksporterer nu de 18 infrastructure-
symboler fra db_core.py. ~1100 linjer fjernet fra db.py.

Bevaret bagudkompat: alle 5.317 import-sites virker uændret.

Gates passeret:
- Test-gate: pytest tests/ -x grøn
- Import-gate: 30-symbol sample OK
- Performance-gate: cold import inden for baseline + 15ms
- Live-gate: jarvis-runtime + jarvis-api kører rent

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: Måling efter commit**

```bash
wc -l core/runtime/db.py core/runtime/db_core.py
```

Forventet: db.py reduceret med ~1100 linjer (~32.900 tilbage), db_core.py ~1200 linjer.

**Checkpoint:** Stop og rapportér resultater til Bjørn før Phase 1. Han skal kunne se gate-resultater og linjeantal.

---

## Task 7: Identificér capability_approval og approval_feedback funktioner

**Files:**
- Læs kun: `core/runtime/db.py`

- [ ] **Step 1: Find alle relevante funktioner**

```bash
python << 'PY'
import ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)
print("=== capability_approval / approval_feedback funktioner ===")
matches = []
for n in tree.body:
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if 'capability_approval' in n.name or 'approval_feedback' in n.name:
            matches.append((n.lineno, getattr(n, 'end_lineno', n.lineno), n.name))
for ln, end, name in matches:
    print(f"  L{ln}-{end}: {name}")
print(f"\nTotal: {len(matches)} funktioner")
PY
```

- [ ] **Step 2: Find tilhørende `_ensure_*_table` funktioner**

```bash
python << 'PY'
import ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)
print("=== _ensure_*_table for capability_approval / approval_feedback ===")
for n in tree.body:
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if n.name.startswith('_ensure_') and n.name.endswith('_table'):
            if 'capability_approval' in n.name or 'approval_feedback' in n.name:
                print(f"  L{n.lineno}-{n.end_lineno}: {n.name}")
PY
```

Skriv linje-numre ned — du skal flytte ALLE matchede funktioner (både public og _ensure_*).

- [ ] **Step 3: Verificér ingen capability_approval-funktion deler private helpers med andre domæner**

```bash
python << 'PY'
"""Find private helpers (_underscore-prefix, not _ensure_*_table) der KUN
kaldes af capability_approval/approval_feedback funktioner — de skal med over."""
import ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)

target_funcs = set()
for n in tree.body:
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if 'capability_approval' in n.name or 'approval_feedback' in n.name:
            target_funcs.add(n.name)

# Find alle private funcs
private_funcs = {n.name for n in tree.body
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name.startswith('_')
                 and not (n.name.startswith('_ensure_') and n.name.endswith('_table'))}

# For hver private func: tæl hvor mange ikke-target funktioner kalder den
class Calls(ast.NodeVisitor):
    def __init__(self): self.callers = {}  # func_name -> set of caller_names
    def visit_FunctionDef(self, node):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                self.callers.setdefault(sub.func.id, set()).add(node.name)
        self.generic_visit(node)
    visit_AsyncFunctionDef = visit_FunctionDef

c = Calls(); c.visit(tree)
print("Private helpers kaldt KUN af capability_approval/approval_feedback:")
for pf in private_funcs:
    callers = c.callers.get(pf, set())
    if callers and callers.issubset(target_funcs):
        print(f"  {pf} — kun kaldt af: {sorted(callers)}")
PY
```

Hvis nogen private helpers vises: de skal også flyttes til `db_capability_approval.py`. Hvis ingen: gå videre.

---

## Task 8: Opret `db_capability_approval.py`

**Files:**
- Create: `core/runtime/db_capability_approval.py`

- [ ] **Step 1: Skriv header**

Skriv til `core/runtime/db_capability_approval.py`:

```python
"""Capability approval + approval feedback CRUD.

Domæne: brugerens explicit approval/decline af capability-anmodninger
plus efterfølgende feedback. Tabeller: capability_approvals,
approval_feedback (skema-bootstrap nedenfor).

Importerer KUN fra core.runtime.db_core (ingen cirkulære imports).
Re-eksporteres via core.runtime.db (facaden).
"""
from __future__ import annotations

import json as _json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from core.runtime.db_core import (
    _ENSURED_TABLES,
    _install_ensure_once_cache_for,
    _now_iso,
    connect,
)


# === Schema bootstrap ===
# Indsæt her alle _ensure_*_table funcs fra Task 7 Step 2 verbatim.
# Eksempel — udskift med faktiske funktioner:
#
# def _ensure_capability_approvals_table(conn: sqlite3.Connection) -> None:
#     conn.execute("""CREATE TABLE IF NOT EXISTS capability_approvals (...)""")


# === Public CRUD ===
# Indsæt her alle capability_approval_* og approval_feedback_* funcs
# fra Task 7 Step 1 verbatim, eksakt som de stod i db.py.


# === Bagudkompat: wrap _ensure_*_table funcs på dette modul ===
_install_ensure_once_cache_for(__name__)
```

- [ ] **Step 2: Kopiér alle identificerede funktioner verbatim fra db.py**

Brug Read-tool på hver linje-range fra Task 7. Kopiér eksakt — ingen ændringer i signaturer eller bodies. Indsæt under hhv. "Schema bootstrap" og "Public CRUD" sektionerne.

- [ ] **Step 3: Verificér compile + import**

```bash
python -m compileall -q core/runtime/db_capability_approval.py
python -c "from core.runtime import db_capability_approval as m; print('OK', sorted(s for s in dir(m) if not s.startswith('__'))[:10])"
```

Forventet: `OK [...]` uden exception.

- [ ] **Step 4: Verificér _ensure-once cache er installeret på nyt modul**

```bash
python << 'PY'
from core.runtime import db_capability_approval as m
ensure_funcs = [getattr(m, n) for n in dir(m) if n.startswith('_ensure_') and n.endswith('_table')]
wrapped = [f for f in ensure_funcs if getattr(f, '_ensure_once_wrapped', False)]
print(f"Found {len(ensure_funcs)} _ensure_* funcs, {len(wrapped)} wrapped")
assert len(ensure_funcs) == len(wrapped), "Ikke alle _ensure_* er wrapped"
print("OK")
PY
```

Forventet: `Found N _ensure_* funcs, N wrapped\nOK`.

---

## Task 9: Opdater db.py med re-eksport for Phase 1

**Files:**
- Modify: `core/runtime/db.py`
- Modify: `tests/runtime/test_db_split_imports.py`

- [ ] **Step 1: Tilføj re-eksport-blok til db.py**

Lige under Phase 0 re-eksporterne, tilføj:

```python
# === Phase 1 re-eksporter fra db_capability_approval ===
from core.runtime.db_capability_approval import (
    # Indsæt eksakte navne fra Task 7 — eksempel:
    # capability_approval_create,
    # capability_approval_get,
    # capability_approval_list,
    # capability_approval_update,
    # approval_feedback_record,
    # approval_feedback_list,
    # ... etc
)
```

Brug Edit-tool. Indsæt listen eksakt — hvert public navn.

- [ ] **Step 2: Slet de samme funktioner fra db.py**

Brug AST-scan til at finde aktuelle linjer i db.py (efter Phase 0):

```bash
python << 'PY'
import ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)
for n in tree.body:
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if 'capability_approval' in n.name or 'approval_feedback' in n.name:
            print(f"L{n.lineno}-{n.end_lineno}: {n.name}")
PY
```

Brug Edit-tool til at slette hver funktion-blok. Tip: sletning ovenfra-og-ned, så linjenumre fra første scan stadig matcher (Edit shifter ikke filen før næste Edit-kald).

ALTERNATIV (mere robust): scan + slet én ad gangen med Edit, og brug AST-scan igen efter hver sletning for at få nye linjer.

- [ ] **Step 3: Verificér db.py compiler og importerer rent**

```bash
python -m compileall -q core/runtime/db.py
python -c "from core.runtime import db; print('OK')"
```

- [ ] **Step 4: Opdater test_db_split_imports.py med Phase 1 symboler**

Brug Edit-tool på `tests/runtime/test_db_split_imports.py`. Tilføj efter `PHASE_0_SYMBOLS`-listen:

```python

# Phase 1: capability_approval domæne — skal være importerbar fra
# BÅDE core.runtime.db OG core.runtime.db_capability_approval.
PHASE_1_SYMBOLS = [
    # Indsæt eksakte navne fra Task 7 — eksempel:
    # "capability_approval_create",
    # "capability_approval_get",
    # ...
]


def test_phase1_symbols_on_facade():
    _assert_importable("core.runtime.db", PHASE_1_SYMBOLS)


def test_phase1_symbols_on_submodule():
    _assert_importable("core.runtime.db_capability_approval", PHASE_1_SYMBOLS)
```

- [ ] **Step 5: Kør import-sanity-test**

```bash
pytest tests/runtime/test_db_split_imports.py -v
```

Forventet: alle tests PASS (Phase 0 + Phase 1).

---

## Task 10: Phase 1 — Kør de 4 gates

Eksakt samme gates som Task 5. Gentag hvert step.

- [ ] **Test-gate**

```bash
conda activate ai
pytest tests/ -x --tb=short 2>&1 | tail -30
```

Forventet: alle tests pass.

- [ ] **Import-gate: 30-symbol sample**

```bash
python << 'PY'
import importlib, random, ast
src = open('core/runtime/db.py').read()
tree = ast.parse(src)
names = [n.name for n in tree.body
         if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
         and not n.name.startswith('_')]
random.seed(43)  # Different seed than Phase 0
sample = random.sample(names, min(30, len(names)))
db = importlib.import_module('core.runtime.db')
missing = [s for s in sample if not hasattr(db, s)]
print(f"Sampled {len(sample)} symbols. Missing: {len(missing)}")
if missing: print(f"FAIL — missing: {missing}")
else: print("OK")
PY
```

Forventet: `OK`.

- [ ] **Performance-gate**

```bash
python scripts/db_split_baseline.py --label phase1_after
python scripts/db_split_baseline.py --label phase1_after
python scripts/db_split_baseline.py --label phase1_after
```

Forventet: cold-import ≤ baseline + 15ms.

- [ ] **Live-gate**

```bash
sudo systemctl restart jarvis-runtime jarvis-api
sleep 3
sudo systemctl status jarvis-runtime --no-pager | head -10
sudo systemctl status jarvis-api --no-pager | head -10
sudo journalctl -u jarvis-runtime --since "30 seconds ago" --no-pager | grep -E "ERROR|Traceback" | head -5
sudo journalctl -u jarvis-api --since "30 seconds ago" --no-pager | grep -E "ERROR|Traceback" | head -5
curl -s http://localhost:8401/api/heartbeat/status | python -m json.tool | head -20
```

Forventet: services active, ingen ERRORs, heartbeat returnerer gyldig JSON.

- [ ] **Hvis ALLE gates passerer: commit Phase 1**

```bash
git add core/runtime/db_capability_approval.py core/runtime/db.py tests/runtime/test_db_split_imports.py
git commit -m "refactor(db): extract db_capability_approval (Phase 1 warm-up)

Phase 1: flytter capability_approval_* og approval_feedback_* funktioner
samt tilhørende _ensure_*_table til db_capability_approval.py. ~N funktioner
flyttet. db.py re-eksporterer.

Warm-up split bekræfter mønstret virker. Næste fase tager større klynger
(runtime_self, runtime_private).

Gates passeret:
- Test-gate: pytest tests/ -x grøn
- Import-gate: 30-symbol sample OK
- Performance-gate: cold import inden for baseline + 15ms
- Live-gate: jarvis-runtime + jarvis-api kører rent

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Måling**

```bash
wc -l core/runtime/db.py core/runtime/db_core.py core/runtime/db_capability_approval.py
```

Forventet: db.py reduceret med yderligere ~hundrede linjer.

**Checkpoint:** Stop og rapportér til Bjørn. Phase 0 + Phase 1 er komplet. Næste plan dækker Phase 2 (runtime_self.py — 56 funcs).

---

## Hvis noget går galt

- **Test-gate fejler:** Læs fejl. Hvis det er en eksisterende stale test, fix den med samme metode som test-suite-cleanup tidligere (verify-against-production). Hvis det er en ægte regression, revert til forrige commit (`git reset --hard HEAD~1`) og diagnose.

- **Import-gate fejler:** Et symbol mangler på facaden. Tjek at re-eksport-listen i db.py matcher eksakt navnene flyttet til submodulet. Hvis _ensure_*_table — verificér `_install_ensure_once_cache_for(__name__)` kaldes i submodulets bund.

- **Performance-gate fejler:** Hvis cold-import er meget højere end baseline, er der formentlig en cirkulær eller dyr import-chain. Brug `python -X importtime -c "from core.runtime import db" 2>&1 | tail -30` til at finde de tunge moduler.

- **Live-gate fejler:** Tjek `journalctl -u jarvis-runtime -u jarvis-api -n 100 --no-pager`. Mest sandsynligt: en _ensure_*_table-funktion er ikke wrapped, eller en submodul-importerede helper er sat forkert. Revert + diagnose før retry.

- **Du opdager top-level side-effekter du ikke kendte til:** STOP. Rapportér til Bjørn. Brainstorm-spec antager `_install_ensure_once_cache()` er eneste top-level kald — hvis der er flere, skal håndtering aftales.

---

## Self-review noter

**Spec coverage:**
- Granularitet (mellem-granular ~24 nye filer): Phase 0+1 producerer 2 af de ~24 — resten i senere planer ✓
- Bagudkompat via eksplicit navngivet re-eksport: Task 4 Step 2, Task 9 Step 1 ✓
- Ingen cirkulære imports: db_capability_approval importerer kun fra db_core ✓
- _ensure_*_table følger funktionen: Task 7 Step 2 + Task 8 ✓
- Top-level side-effekter bevares: Task 4 Step 5 (`_install_ensure_once_cache()` flyttes til bunden) ✓
- Funktions-signaturer frosne: Task 8 Step 2 "kopiér eksakt" ✓
- Module-level state-deling identificeres før split: Task 1 Step 2 (verificér 0 globals) ✓
- Per-fase gates: Task 5 + Task 10 — alle 4 gates ✓
- Performance gate-kriterium: ≤ baseline + 15ms (≈ 150ms) ✓
- Test-gate: pytest tests/ -x grøn ✓
- Import-gate: 30-symbol sample + dedikeret import-sanity-test ✓
- Live-gate: restart services + smoke check ✓

**Placeholders:** Eneste "PLACEHOLDER" tilbage i planen er instruktion om at engineeren skal kopiere init_db verbatim fra original db.py — det er IKKE plan-placeholder, det er "denne kode er for stor til at gengive i planen, kopiér den eksakt fra kilden". Linjenumre er givet. Hvis denne instruktion brydes, fanger Step 5+7 i Task 3 det.

**Type-konsistens:** `_install_ensure_once_cache_for(module_name: str)` introduceret i Task 3, brugt i Task 8 — konsistent. Original `_install_ensure_once_cache()` bevaret som facade-shim i Task 3 Step 2.
