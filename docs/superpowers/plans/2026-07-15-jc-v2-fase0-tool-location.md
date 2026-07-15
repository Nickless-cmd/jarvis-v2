# Fase 0 — Tool-lokations-lag Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gør tool-eksekverings-lokation eksplicit (`"client" | "runtime" | "server"`) som en ren funktion i det kanoniske jc-tool-katalog — uden nogen adfærdsændring, så Fase 1's loop-router har én sandhed at slå op i.

**Architecture:** Tilføj en pure classifier `execution_location(name)` + en `CLIENT_TOOLS`-konstant + en katalog-dækkende `execution_map(defs)` i `core/tools/jc_tool_catalog.py` (allerede "single source of truth for what jc presents as tools"). Vi MUTERER IKKE de emitterede tool-defs (de sendes til providers — en fremmed nøgle kunne bryde et strengt provider-kald). Klassifikationen er nøgle-baseret og nul-risiko. `runtime_`-aliaset genfortolkes som *præsentationen* af `execution:"runtime"`.

**Tech Stack:** Python 3.11, pytest. Test-runner: `/opt/conda/envs/ai/bin/python -m pytest`.

---

## File Structure

- `core/tools/jc_tool_catalog.py` (101 linjer i dag) — tilføj `CLIENT_TOOLS`, `execution_location()`, `execution_map()`. Ansvar uændret: single source of truth for jc's tool-præsentation. Ingen eksisterende funktion ændrer opførsel.
- `tests/test_jc_tool_catalog.py` — udvid med tests for de tre nye symboler. Eksisterende tests skal forblive grønne (bevis for nul adfærdsændring).

Baggrund (nuværende kode, `jc_tool_catalog.py`):
- `RUNTIME_ALIAS_PREFIX = "runtime_"`, `COLLIDING_TOOLS = ("bash","read_file","write_file","edit_file")`.
- `alias_for(name)`, `unalias(name)`, `is_runtime_alias(name)` — alias-logik for de fire kolliderende.
- `DEFAULT_COMPANIONS` — unikke server-companions (search_memory, remember_this, …).
- `build_jc_catalog(role, unlocked)` → liste af OpenAI-style defs `{"type":"function","function":{"name":…}}`.
- `_def_name(d)` → henter navnet ud af en def.

Klient-tool-sættet (jarvis-codes `src/tools.py`): `TOOL_EXECUTORS` = bash/read_file/write_file/…;
`READONLY_TOOLS = {read_file, glob, grep, web_fetch, web_scrape, web_search, bash_output}`;
`WRITE_TOOLS = {write_file, edit_file, multi_edit}`; plus `bash`, `todo_write`, `task`.

---

### Task 1: `execution_location(name)` classifier + `CLIENT_TOOLS`

**Files:**
- Modify: `core/tools/jc_tool_catalog.py` (tilføj efter `is_runtime_alias`, ~linje 46)
- Test: `tests/test_jc_tool_catalog.py`

- [ ] **Step 1: Write the failing test**

Tilføj til `tests/test_jc_tool_catalog.py`:

```python
def test_execution_location_client_for_bare_colliding_and_local():
    # de fire kolliderende, bare, er klient-side; plus de rene klient-tools
    for n in ("bash", "read_file", "write_file", "edit_file",
              "multi_edit", "glob", "grep", "web_fetch", "web_scrape",
              "web_search", "bash_output", "todo_write", "task"):
        assert cat.execution_location(n) == "client", n


def test_execution_location_runtime_for_aliased_colliding():
    for n in ("runtime_bash", "runtime_read_file",
              "runtime_write_file", "runtime_edit_file"):
        assert cat.execution_location(n) == "runtime", n


def test_execution_location_server_for_companions_and_rest():
    for n in ("search_memory", "remember_this", "read_mood",
              "load_more_tools", "operator_launch_app", "unrelated_tool"):
        assert cat.execution_location(n) == "server", n


def test_execution_location_strips_whitespace():
    assert cat.execution_location("  runtime_bash  ") == "runtime"
    assert cat.execution_location(" bash ") == "client"


def test_client_tools_is_frozenset_and_contains_colliding():
    assert isinstance(cat.CLIENT_TOOLS, frozenset)
    for n in cat.COLLIDING_TOOLS:
        assert n in cat.CLIENT_TOOLS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q -k execution_location`
Expected: FAIL med `AttributeError: module 'core.tools.jc_tool_catalog' has no attribute 'execution_location'`

- [ ] **Step 3: Write minimal implementation**

I `core/tools/jc_tool_catalog.py`, indsæt efter `is_runtime_alias` (efter linje 46):

```python
# Tools jarvis-code EJER og eksekverer på KLIENTENS host (ikke server/container).
# Single source of truth for "client"-klassifikationen. De fire COLLIDING_TOOLS er
# klient-side når de er bare; deres runtime_-alias er container-formen ("runtime").
CLIENT_TOOLS: frozenset[str] = frozenset({
    "bash", "read_file", "write_file", "edit_file", "multi_edit",
    "glob", "grep", "web_fetch", "web_scrape", "web_search",
    "bash_output", "todo_write", "task",
})


def execution_location(name: str) -> str:
    """Hvor et tool med DETTE præsenterede navn eksekverer:
      "client"  — den forbundne overflades host (jarvis-code/desk lokale tools)
      "runtime" — Jarvis' egen container (de runtime_-aliasede kolliderende tools)
      "server"  — server-processen / hjernen (memory, operator, cognitive tools)
    Single source of truth som Fase 1's loop-router slår op i. runtime_-aliaset er
    blot PRÆSENTATIONEN af execution=="runtime"."""
    n = (name or "").strip()
    if is_runtime_alias(n):
        return "runtime"
    if n in CLIENT_TOOLS:
        return "client"
    return "server"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q -k execution_location`
Expected: PASS (5 nye tests grønne)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2 && git add core/tools/jc_tool_catalog.py tests/test_jc_tool_catalog.py
git commit -m "feat(jc-tool-catalog): eksplicit execution_location classifier (Fase 0)"
```

---

### Task 2: `execution_map(defs)` — katalog-dækkende lokations-kort

**Files:**
- Modify: `core/tools/jc_tool_catalog.py` (tilføj efter `execution_location`)
- Test: `tests/test_jc_tool_catalog.py`

- [ ] **Step 1: Write the failing test**

Tilføj til `tests/test_jc_tool_catalog.py`:

```python
def test_execution_map_over_unlocked_catalog(monkeypatch):
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=True)
    m = cat.execution_map(out)
    # aliasede kolliderende → runtime; companions/rest → server; load_more → server
    assert m["runtime_bash"] == "runtime"
    assert m["runtime_edit_file"] == "runtime"
    assert m["remember_this"] == "server"
    assert m["read_mood"] == "server"
    assert m["unrelated"] == "server"
    assert m["load_more_tools"] == "server"
    # ingen bare kolliderende i det server-serverede katalog (jc prepender dem selv)
    assert "bash" not in m


def test_execution_map_empty_for_empty():
    assert cat.execution_map([]) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q -k execution_map`
Expected: FAIL med `AttributeError: ... has no attribute 'execution_map'`

- [ ] **Step 3: Write minimal implementation**

I `core/tools/jc_tool_catalog.py`, indsæt efter `execution_location`:

```python
def execution_map(defs: list[dict[str, Any]]) -> dict[str, str]:
    """Kortlæg en liste af tool-defs → {navn: execution_location}. Muterer IKKE
    def'sne (de sendes til providers; en fremmed nøgle kunne bryde et strengt kald).
    Router-laget (Fase 1) læser dette kort ved navn."""
    return {_def_name(d): execution_location(_def_name(d)) for d in defs}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -q -k execution_map`
Expected: PASS (2 nye tests grønne)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2 && git add core/tools/jc_tool_catalog.py tests/test_jc_tool_catalog.py
git commit -m "feat(jc-tool-catalog): execution_map(defs) katalog-lokationskort (Fase 0)"
```

---

### Task 3: Bevis nul adfærdsændring (regression-gate)

**Files:**
- Test: `tests/test_jc_tool_catalog.py` (kør HELE filen — ingen ændring)

- [ ] **Step 1: Kør hele katalog-testfilen**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py -o addopts="" -v`
Expected: ALLE tests PASS — de 8 oprindelige (colliding-four, companions, alias-roundtrip, is_runtime_alias, locked/unlocked-catalog, load_more-shape, skill_gate) + de 7 nye. Ingen oprindelig test ændret eller fjernet.

- [ ] **Step 2: Kør de bredere tool-katalog-tests (fang utilsigtet kobling)**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_tool_catalog.py -o addopts="" -q`
Expected: PASS (uændret — vi rørte ikke `build_jc_catalog`'s output-defs, kun tilføjede rene funktioner)

- [ ] **Step 3: Verificér at ingen def blev muteret (eksplicit asscertion)**

Tilføj til `tests/test_jc_tool_catalog.py`:

```python
def test_defs_carry_no_execution_key(monkeypatch):
    # Fase 0-kontrakt: vi må IKKE stample en 'execution'-nøgle på de def's der
    # sendes til providers. Lokation er en ren funktion, ikke en def-nøgle.
    monkeypatch.setattr(cat, "_all_native_defs", lambda role: _fake_defs())
    out = cat.build_jc_catalog(role="owner", unlocked=True)
    for d in out:
        assert "execution" not in d
        assert "execution" not in (d.get("function") or {})
```

- [ ] **Step 4: Kør den nye kontrakt-test**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_jc_tool_catalog.py::test_defs_carry_no_execution_key -o addopts="" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2 && git add tests/test_jc_tool_catalog.py
git commit -m "test(jc-tool-catalog): kontrakt — Fase 0 muterer ingen provider-def (nul adfærdsændring)"
```

---

## Self-Review

**1. Spec coverage:** Spec §3 ("Gør lokation EKSPLICIT … `execution: client|runtime|server`", "router slår `execution` op", "runtime_ = præsentation af execution:runtime", "katalog forbliver single source of truth") → Task 1 (classifier + CLIENT_TOOLS), Task 2 (execution_map), Task 3 (nul-adfærd-bevis). Fase 0's afgrænsning ("ingen adfærdsændring") er dækket af Task 3. Router-BRUGEN er eksplicit Fase 1 (ikke her) — korrekt jf. spec §7.

**2. Placeholder scan:** Ingen TBD/TODO/"handle edge cases". Al kode er komplet og vist.

**3. Type consistency:** `execution_location(name: str) -> str` bruges konsistent af `execution_map`. `CLIENT_TOOLS: frozenset[str]`. `_def_name` genbrugt (findes i dag). Navne matcher testene (`execution_location`, `execution_map`, `CLIENT_TOOLS`) i alle tasks.
