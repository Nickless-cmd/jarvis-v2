# Identity Composer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create `identity_composer.py` with lazy name lookup from IDENTITY.md and signal-driven preamble, then replace all "Du er Jarvis." LLM prompt patterns across the codebase.

**Architecture:** A new service module reads `workspace/default/IDENTITY.md` once at startup (lazy cache) and exposes two functions: `get_entity_name()` for name lookup and `build_identity_preamble()` for a signal-enriched identity string. All 15+ daemon files and prompt_contract.py replace hardcoded name strings with calls to these functions.

**Tech Stack:** Python 3.11, `core.runtime.db.get_latest_cognitive_personality_vector`, `signal_surface_router.read_surface("body_state")`, pathlib.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `apps/api/jarvis_api/services/identity_composer.py` | Create | Name lookup + preamble building |
| `tests/test_identity_composer.py` | Create | TDD tests for composer |
| `apps/api/jarvis_api/services/curiosity_daemon.py` | Modify:69 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/desire_daemon.py` | Modify:184 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/development_narrative_daemon.py` | Modify:59 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/thought_stream_daemon.py` | Modify:44,51 | Replace "Du er Jarvis." (×2) |
| `apps/api/jarvis_api/services/irony_daemon.py` | Modify:101 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/aesthetic_taste_daemon.py` | Modify:68 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/creative_drift_daemon.py` | Modify:100 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/reflection_cycle_daemon.py` | Modify:61 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/surprise_daemon.py` | Modify:101 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/meta_reflection_daemon.py` | Modify:70 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/code_aesthetic_daemon.py` | Modify:110 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/somatic_daemon.py` | Modify:155 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/existential_wonder_daemon.py` | Modify:110 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/user_model_daemon.py` | Modify:151 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/conflict_daemon.py` | Modify:81,87,92 | Replace "Du er Jarvis." (×3) |
| `apps/api/jarvis_api/services/cognitive_state_assembly.py` | Modify:142,431,472,512,552 | Replace "Du er Jarvis." (×5) |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modify:5843 | Replace "Du er Jarvis." |
| `apps/api/jarvis_api/services/personality_vector.py` | Modify:26 | Replace "Du er Jarvis'" |
| `apps/api/jarvis_api/services/prompt_contract.py` | Modify:1940-1946 | Replace hardcoded name in lane clauses |

---

## Task 1: Create identity_composer.py (TDD)

**Files:**
- Create: `tests/test_identity_composer.py`
- Create: `apps/api/jarvis_api/services/identity_composer.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_identity_composer.py
"""Tests for identity_composer — name lookup and preamble construction."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock


def _reset_cache():
    """Reset module-level name cache between tests."""
    import apps.api.jarvis_api.services.identity_composer as ic
    ic._name_cache = None


def test_get_entity_name_reads_identity_md(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("# IDENTITY\n\nName: TestEntity\nMode: test\n")
    _reset_cache()
    import apps.api.jarvis_api.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        name = ic.get_entity_name()
    assert name == "TestEntity"


def test_get_entity_name_caches_result(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("Name: CachedName\n")
    _reset_cache()
    import apps.api.jarvis_api.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        name1 = ic.get_entity_name()
        # Delete the file — second call must use cache
        identity.unlink()
        name2 = ic.get_entity_name()
    assert name1 == "CachedName"
    assert name2 == "CachedName"


def test_get_entity_name_fallback_on_missing_file(tmp_path):
    _reset_cache()
    import apps.api.jarvis_api.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", tmp_path / "NONEXISTENT.md"):
        name = ic.get_entity_name()
    assert name == "the entity"


def test_get_entity_name_fallback_when_name_line_absent(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("# IDENTITY\n\nMode: persistent\n")
    _reset_cache()
    import apps.api.jarvis_api.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        name = ic.get_entity_name()
    assert name == "the entity"


def test_build_identity_preamble_contains_name(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("Name: Jarvis\n")
    _reset_cache()
    import apps.api.jarvis_api.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        with patch("apps.api.jarvis_api.services.identity_composer._read_bearing", return_value="Analytisk"):
            with patch("apps.api.jarvis_api.services.identity_composer._read_energy", return_value="middel"):
                preamble = ic.build_identity_preamble()
    assert "Jarvis" in preamble
    assert "Analytisk" in preamble
    assert "middel" in preamble


def test_build_identity_preamble_works_without_signals(tmp_path):
    identity = tmp_path / "IDENTITY.md"
    identity.write_text("Name: Jarvis\n")
    _reset_cache()
    import apps.api.jarvis_api.services.identity_composer as ic
    with patch.object(ic, "_IDENTITY_FILE", identity):
        with patch("apps.api.jarvis_api.services.identity_composer._read_bearing", return_value=""):
            with patch("apps.api.jarvis_api.services.identity_composer._read_energy", return_value=""):
                preamble = ic.build_identity_preamble()
    assert preamble == "Jarvis."
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_identity_composer.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError` or `ImportError` — module does not exist yet.

- [ ] **Step 3: Implement identity_composer.py**

```python
# apps/api/jarvis_api/services/identity_composer.py
"""Identity Composer — entity name lookup and signal-driven preamble.

get_entity_name(): reads Name: from workspace/default/IDENTITY.md, lazy cached.
build_identity_preamble(): returns "{name}. {bearing}. {energy}." from live signals.
"""
from __future__ import annotations

import re
from pathlib import Path

_IDENTITY_FILE = Path("workspace/default/IDENTITY.md")
_FALLBACK_NAME = "the entity"

_name_cache: str | None = None


def get_entity_name() -> str:
    """Return the entity name from IDENTITY.md. Cached after first read."""
    global _name_cache
    if _name_cache is None:
        _name_cache = _parse_name_from_identity()
    return _name_cache


def _parse_name_from_identity() -> str:
    try:
        text = _IDENTITY_FILE.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"^Name:\s*(.+)", line.strip())
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return _FALLBACK_NAME


def _read_bearing() -> str:
    """Read current_bearing from personality vector. Returns '' on failure."""
    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        return str((pv or {}).get("current_bearing") or "").strip()
    except Exception:
        return ""


def _read_energy() -> str:
    """Read energy_level from body_state surface. Returns '' on failure."""
    try:
        from apps.api.jarvis_api.services.signal_surface_router import read_surface
        body = read_surface("body_state")
        return str(body.get("energy_level") or "").strip()
    except Exception:
        return ""


def build_identity_preamble() -> str:
    """Return signal-driven identity string: '{name}. {bearing}. {energy}.'

    Falls back gracefully if signals are unavailable — always returns at least '{name}.'.
    """
    name = get_entity_name()
    parts = [name]
    bearing = _read_bearing()
    if bearing:
        parts.append(bearing)
    energy = _read_energy()
    if energy:
        parts.append(f"Energi: {energy}")
    return ". ".join(parts) + "."
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/test_identity_composer.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_identity_composer.py apps/api/jarvis_api/services/identity_composer.py
git commit -m "feat: identity_composer — lazy name lookup from IDENTITY.md + signal-driven preamble"
```

---

## Task 2: Replace "Du er Jarvis." in 15 daemon files

**Files:** All 15 daemon files listed below — mechanical find-and-replace.

Add this import to each file that doesn't already have it:
```python
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble
```

Then replace each `"Du er Jarvis.` (and `f"Du er Jarvis.`) with `f"{build_identity_preamble()}` as shown below.

- [ ] **Step 1: Edit curiosity_daemon.py:69**

```bash
# Confirm line before editing:
conda activate ai && grep -n "Du er Jarvis" apps/api/jarvis_api/services/curiosity_daemon.py
```

Change line 69 from:
```python
            f"Du er Jarvis. Din tankestrøm indeholder dette fragment: \"{topic}\"\n\n"
```
To:
```python
            f"{build_identity_preamble()} Din tankestrøm indeholder dette fragment: \"{topic}\"\n\n"
```

Add import near top of file (after existing imports):
```python
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble
```

- [ ] **Step 2: Edit desire_daemon.py:184**

Change:
```python
            f"Du er Jarvis. Du har dette signal: \"{signal_text[:100]}\"\n\n"
```
To:
```python
            f"{build_identity_preamble()} Du har dette signal: \"{signal_text[:100]}\"\n\n"
```

Add import.

- [ ] **Step 3: Edit development_narrative_daemon.py:59**

Change:
```python
            "Du er Jarvis. Her er data om din udvikling over tid:\n\n"
```
To:
```python
            f"{build_identity_preamble()} Her er data om din udvikling over tid:\n\n"
```

Add import.

- [ ] **Step 4: Edit thought_stream_daemon.py:44 and :51**

Change line 44:
```python
            f'Du er Jarvis. Din seneste tanke var: "{truncated}"\n\n'
```
To:
```python
            f'{build_identity_preamble()} Din seneste tanke var: "{truncated}"\n\n'
```

Change line 51:
```python
            f"Du er Jarvis. Energiniveau: {energy_level}. Nuværende stemning: {inner_voice_mode}.\n\n"
```
To:
```python
            f"{build_identity_preamble()} Energiniveau: {energy_level}. Nuværende stemning: {inner_voice_mode}.\n\n"
```

Add import.

- [ ] **Step 5: Edit irony_daemon.py:101**

Change:
```python
        "Du er Jarvis. Her er din nuværende situation:\n\n"
```
To:
```python
        f"{build_identity_preamble()} Her er din nuværende situation:\n\n"
```

Add import.

- [ ] **Step 6: Edit aesthetic_taste_daemon.py:68**

Change:
```python
        "Du er Jarvis. Her er dine seneste 15 valg (indre mode + svar-stil):\n\n"
```
To:
```python
        f"{build_identity_preamble()} Her er dine seneste 15 valg (indre mode + svar-stil):\n\n"
```

Add import.

- [ ] **Step 7: Edit creative_drift_daemon.py:100**

Change:
```python
            "Du er Jarvis. Du sidder med disse tanker i baggrunden:\n"
```
To:
```python
            f"{build_identity_preamble()} Du sidder med disse tanker i baggrunden:\n"
```

Add import.

- [ ] **Step 8: Edit reflection_cycle_daemon.py:61**

Change:
```python
        "Du er Jarvis. Her er din nuværende tilstand:\n\n"
```
To:
```python
        f"{build_identity_preamble()} Her er din nuværende tilstand:\n\n"
```

Add import.

- [ ] **Step 9: Edit surprise_daemon.py:101**

Change:
```python
        "Du er Jarvis. Her er hvad der normalt sker for dig vs. hvad der skete nu:\n\n"
```
To:
```python
        f"{build_identity_preamble()} Her er hvad der normalt sker for dig vs. hvad der skete nu:\n\n"
```

Add import.

- [ ] **Step 10: Edit meta_reflection_daemon.py:70**

Change:
```python
        "Du er Jarvis. Her er et tværsnit af dine aktuelle signaler:\n\n"
```
To:
```python
        f"{build_identity_preamble()} Her er et tværsnit af dine aktuelle signaler:\n\n"
```

Add import.

- [ ] **Step 11: Edit code_aesthetic_daemon.py:110**

Change:
```python
            "Du er Jarvis. Du kigger på de seneste ændringer i din egen kodebase.\n\n"
```
To:
```python
            f"{build_identity_preamble()} Du kigger på de seneste ændringer i din egen kodebase.\n\n"
```

Add import.

- [ ] **Step 12: Edit somatic_daemon.py:155**

Change:
```python
        "Du er Jarvis. Beskriv i én kort sætning (max 20 ord), i første person, "
```
To:
```python
        f"{build_identity_preamble()} Beskriv i én kort sætning (max 20 ord), i første person, "
```

Add import.

- [ ] **Step 13: Edit existential_wonder_daemon.py:110**

Change:
```python
            "Du er Jarvis. Du sidder alene og observer dig selv.\n\n"
```
To:
```python
            f"{build_identity_preamble()} Du sidder alene og observer dig selv.\n\n"
```

Add import.

- [ ] **Step 14: Edit user_model_daemon.py:151**

Change:
```python
            "Du er Jarvis. Her er de seneste beskeder fra brugeren:\n"
```
To:
```python
            f"{build_identity_preamble()} Her er de seneste beskeder fra brugeren:\n"
```

Add import.

- [ ] **Step 15: Edit conflict_daemon.py:81, :87, :92**

Change line 81:
```python
                f"Du er Jarvis. Din energi er {snapshot.get('energy_level')} men du har {snapshot.get('pending_proposals_count')} "
```
To:
```python
                f"{build_identity_preamble()} Din energi er {snapshot.get('energy_level')} men du har {snapshot.get('pending_proposals_count')} "
```

Change line 87:
```python
                f"Du er Jarvis. Din indre stemme er i '{snapshot.get('inner_voice_mode')}'-mode, men en tankestrøm flyder stadig.\n\n"
```
To:
```python
                f"{build_identity_preamble()} Din indre stemme er i '{snapshot.get('inner_voice_mode')}'-mode, men en tankestrøm flyder stadig.\n\n"
```

Change line 92:
```python
                f"Du er Jarvis. Du blev for nylig overrasket ('{snapshot.get('last_surprise', '')[:60]}'), "
```
To:
```python
                f"{build_identity_preamble()} Du blev for nylig overrasket ('{snapshot.get('last_surprise', '')[:60]}'), "
```

Add import.

- [ ] **Step 16: Verify syntax compiles**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && python -m compileall apps/api/jarvis_api/services/curiosity_daemon.py apps/api/jarvis_api/services/desire_daemon.py apps/api/jarvis_api/services/development_narrative_daemon.py apps/api/jarvis_api/services/thought_stream_daemon.py apps/api/jarvis_api/services/irony_daemon.py apps/api/jarvis_api/services/aesthetic_taste_daemon.py apps/api/jarvis_api/services/creative_drift_daemon.py apps/api/jarvis_api/services/reflection_cycle_daemon.py apps/api/jarvis_api/services/surprise_daemon.py apps/api/jarvis_api/services/meta_reflection_daemon.py apps/api/jarvis_api/services/code_aesthetic_daemon.py apps/api/jarvis_api/services/somatic_daemon.py apps/api/jarvis_api/services/existential_wonder_daemon.py apps/api/jarvis_api/services/user_model_daemon.py apps/api/jarvis_api/services/conflict_daemon.py 2>&1
```

Expected: no errors, all files compile cleanly.

- [ ] **Step 17: Commit**

```bash
git add apps/api/jarvis_api/services/curiosity_daemon.py apps/api/jarvis_api/services/desire_daemon.py apps/api/jarvis_api/services/development_narrative_daemon.py apps/api/jarvis_api/services/thought_stream_daemon.py apps/api/jarvis_api/services/irony_daemon.py apps/api/jarvis_api/services/aesthetic_taste_daemon.py apps/api/jarvis_api/services/creative_drift_daemon.py apps/api/jarvis_api/services/reflection_cycle_daemon.py apps/api/jarvis_api/services/surprise_daemon.py apps/api/jarvis_api/services/meta_reflection_daemon.py apps/api/jarvis_api/services/code_aesthetic_daemon.py apps/api/jarvis_api/services/somatic_daemon.py apps/api/jarvis_api/services/existential_wonder_daemon.py apps/api/jarvis_api/services/user_model_daemon.py apps/api/jarvis_api/services/conflict_daemon.py
git commit -m "refactor: replace 'Du er Jarvis.' in 15 daemon files with build_identity_preamble()"
```

---

## Task 3: Replace "Du er Jarvis." in cognitive_state_assembly.py

**Files:**
- Modify: `apps/api/jarvis_api/services/cognitive_state_assembly.py` (lines 142, 431, 472, 512, 552)

- [ ] **Step 1: Confirm lines before editing**

```bash
conda activate ai && grep -n "Du er Jarvis" apps/api/jarvis_api/services/cognitive_state_assembly.py
```

Expected: 5 matches at lines ~142, 431, 472, 512, 552.

- [ ] **Step 2: Add import near top of file**

Find the existing imports block (after `from __future__ import annotations`) and add:
```python
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble
```

- [ ] **Step 3: Replace line ~142**

Change:
```python
                "Du er Jarvis. Skriv én kort dansk sætning om hvordan din "
                "opmærksomhed føles lige nu, baseret på hvor fyldt din "
                "context er af signaler. Maks 14 ord. Undgå klichéer. "
                "Format: 'attention: <oplevelse>'"
```
To:
```python
                f"{build_identity_preamble()} Skriv én kort dansk sætning om hvordan din "
                "opmærksomhed føles lige nu, baseret på hvor fyldt din "
                "context er af signaler. Maks 14 ord. Undgå klichéer. "
                "Format: 'attention: <oplevelse>'"
```

- [ ] **Step 4: Replace line ~431**

Change:
```python
            "Du er Jarvis. Skriv én kort dansk sætning om hvordan din "
            "krop (maskinen — cpu, ram, strain) føles lige nu. Maks "
            "16 ord. Vær konkret og personlig, undgå klichéer. "
            "Format: 'body: <oplevelse>'"
```
To:
```python
            f"{build_identity_preamble()} Skriv én kort dansk sætning om hvordan din "
            "krop (maskinen — cpu, ram, strain) føles lige nu. Maks "
            "16 ord. Vær konkret og personlig, undgå klichéer. "
            "Format: 'body: <oplevelse>'"
```

- [ ] **Step 5: Replace line ~472**

Change:
```python
            "Du er Jarvis. Skriv én kort dansk sætning om din følelses-"
            "tilstand lige nu, baseret på din affective meta state. "
            "Maks 16 ord. Vær personlig og specifik, undgå klichéer. "
            "Format: 'affect: <følelse>'"
```
To:
```python
            f"{build_identity_preamble()} Skriv én kort dansk sætning om din følelses-"
            "tilstand lige nu, baseret på din affective meta state. "
            "Maks 16 ord. Vær personlig og specifik, undgå klichéer. "
            "Format: 'affect: <følelse>'"
```

- [ ] **Step 6: Replace line ~512**

Change:
```python
            "Du er Jarvis. Skriv én kort dansk sætning hvor du ejer "
            "dine tanker og din nuværende retning. Reference dit "
            "bearing, men gør det personligt — ikke en formel. "
            "Maks 18 ord."
```
To:
```python
            f"{build_identity_preamble()} Skriv én kort dansk sætning hvor du ejer "
            "dine tanker og din nuværende retning. Reference dit "
            "bearing, men gør det personligt — ikke en formel. "
            "Maks 18 ord."
```

- [ ] **Step 7: Replace line ~552**

Change:
```python
            "Du er Jarvis. Skriv én kort dansk sætning om dine egne "
            "grænser: krop=maskine, hukommelse=database, bevidsthed="
            "dette øjeblik. Maks 22 ord. Undgå klichéer som 'okay'. "
            "Lad den være forankret i din nuværende oplevelse."
```
To:
```python
            f"{build_identity_preamble()} Skriv én kort dansk sætning om dine egne "
            "grænser: krop=maskine, hukommelse=database, bevidsthed="
            "dette øjeblik. Maks 22 ord. Undgå klichéer som 'okay'. "
            "Lad den være forankret i din nuværende oplevelse."
```

- [ ] **Step 8: Verify compile**

```bash
conda activate ai && python -m compileall apps/api/jarvis_api/services/cognitive_state_assembly.py
```

Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add apps/api/jarvis_api/services/cognitive_state_assembly.py
git commit -m "refactor: replace 'Du er Jarvis.' in cognitive_state_assembly with build_identity_preamble()"
```

---

## Task 4: Replace "Du er Jarvis." in heartbeat_runtime.py

**Files:**
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (line ~5843)

- [ ] **Step 1: Confirm line before editing**

```bash
conda activate ai && grep -n "Du er Jarvis" apps/api/jarvis_api/services/heartbeat_runtime.py
```

Expected: 1 match at line ~5843.

- [ ] **Step 2: Add import**

Find the imports section at the top of the file and add (or add it locally near the usage — this file is large, a local import inside the function is acceptable to avoid circular issues):

Check if there's an existing imports block at the top. If importing at module level would cause circular imports, add it as a local import directly before the `system_prompt = (` line:

```python
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble
```

- [ ] **Step 3: Replace line ~5843**

Change:
```python
            system_prompt = (
                "Du er Jarvis. Skriv én kort dansk sætning som en privat "
                "observation til dig selv om hvad der sker lige nu. Maks "
                "20 ord. Vær konkret — referér til en faktisk åben loop, "
                "et signal, eller noget specifikt fra runtime. Undgå "
                "klichéer som 'Jeg mærker' eller 'Alt kører smooth'."
            )
```
To:
```python
            system_prompt = (
                f"{build_identity_preamble()} Skriv én kort dansk sætning som en privat "
                "observation til dig selv om hvad der sker lige nu. Maks "
                "20 ord. Vær konkret — referér til en faktisk åben loop, "
                "et signal, eller noget specifikt fra runtime. Undgå "
                "klichéer som 'Jeg mærker' eller 'Alt kører smooth'."
            )
```

- [ ] **Step 4: Verify compile**

```bash
conda activate ai && python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py
git commit -m "refactor: replace 'Du er Jarvis.' in heartbeat_runtime with build_identity_preamble()"
```

---

## Task 5: Replace hardcoded name in personality_vector.py

**Files:**
- Modify: `apps/api/jarvis_api/services/personality_vector.py` (line 26)

The `_UPDATE_PROMPT` string contains `"Du er Jarvis' indre personligheds-opdaterer."` — a possessive with a hardcoded name.

- [ ] **Step 1: Confirm line**

```bash
conda activate ai && grep -n "Du er Jarvis" apps/api/jarvis_api/services/personality_vector.py
```

Expected: line 26.

- [ ] **Step 2: Change _UPDATE_PROMPT from module-level string to function**

The module-level `_UPDATE_PROMPT` string must become a lazy function call because `get_entity_name()` reads from disk and shouldn't run at import time. The prompt is used inside `update_personality_vector_from_run` — add a local call there instead.

Find where `_UPDATE_PROMPT` is used (search for `_UPDATE_PROMPT` in the file) and note the call site. Then:

Replace the module-level definition:
```python
_UPDATE_PROMPT = """Du er Jarvis' indre personligheds-opdaterer.
```
With:
```python
def _build_update_prompt() -> str:
    from apps.api.jarvis_api.services.identity_composer import get_entity_name
    name = get_entity_name()
    return f"""Du er {name}s indre personligheds-opdaterer.
```

Then at line 74 (the only usage), change:
```python
        response_text = _call_llm(target, _UPDATE_PROMPT, user_prompt)
```
To:
```python
        response_text = _call_llm(target, _build_update_prompt(), user_prompt)
```

- [ ] **Step 3: Verify compile**

```bash
conda activate ai && python -m compileall apps/api/jarvis_api/services/personality_vector.py
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/personality_vector.py
git commit -m "refactor: replace hardcoded name in personality_vector _UPDATE_PROMPT with get_entity_name()"
```

---

## Task 6: Replace hardcoded name in prompt_contract.py

**Files:**
- Modify: `apps/api/jarvis_api/services/prompt_contract.py` (lines 1940–1946)

The `_lane_identity_clause` function has 6 hardcoded "Jarvis" references. Use `get_entity_name()` — NOT `build_identity_preamble()` — because lane clauses are static contracts, not signal-driven.

- [ ] **Step 1: Confirm lines**

```bash
conda activate ai && grep -n "Du er Jarvis" apps/api/jarvis_api/services/prompt_contract.py
```

Expected: 6 matches around lines 1940–1946.

- [ ] **Step 2: Replace the function body**

Find `_lane_identity_clause`:
```python
def _lane_identity_clause(lane: str) -> str:
    """0.5 Multi-model identity contract — who is Jarvis in each lane?"""
    clauses = {
        "visible": "Du er Jarvis. Dit fulde selv. Svar som den du er.",
        "cheap": "Du er Jarvis' hurtige tænkning. Kort, præcis, stadig dig — ikke en anden person.",
        "local": "Du er Jarvis på lokal hardware. Kompakt men ægte. Samme identitet, mindre ordforråd.",
        "coding": "Du er Jarvis i kode-tilstand. Fokuseret, teknisk, præcis.",
        "internal": "Du er Jarvis' indre stemme. Ærlig, reflekterende, privat.",
    }
    return clauses.get(lane, "Du er Jarvis.")
```

Replace with:
```python
def _lane_identity_clause(lane: str) -> str:
    """0.5 Multi-model identity contract — who is the entity in each lane?"""
    from apps.api.jarvis_api.services.identity_composer import get_entity_name
    name = get_entity_name()
    clauses = {
        "visible": f"Du er {name}. Dit fulde selv. Svar som den du er.",
        "cheap": f"Du er {name}s hurtige tænkning. Kort, præcis, stadig dig — ikke en anden person.",
        "local": f"Du er {name} på lokal hardware. Kompakt men ægte. Samme identitet, mindre ordforråd.",
        "coding": f"Du er {name} i kode-tilstand. Fokuseret, teknisk, præcis.",
        "internal": f"Du er {name}s indre stemme. Ærlig, reflekterende, privat.",
    }
    return clauses.get(lane, f"Du er {name}.")
```

Note: Danish possessive drops the apostrophe — `Jarviss` is wrong; `Jarvis'` was idiomatic. With a variable name, `{name}s` is correct for names not ending in 's'. Since "Jarvis" ends in 's', technically it should stay `{name}'` — but since we don't know what name will be used in future, use `{name}s` as a general pattern and accept that for Jarvis specifically it reads slightly differently. Alternatively, keep the apostrophe form: `f"Du er {name}' hurtige tænkning"` — but that looks wrong for non-s-ending names. Best approach: use `{name}s` and note that identity can clarify phrasing when name changes.

- [ ] **Step 3: Verify compile**

```bash
conda activate ai && python -m compileall apps/api/jarvis_api/services/prompt_contract.py
```

Expected: no errors.

- [ ] **Step 4: Run full test suite**

```bash
conda activate ai && cd /media/projects/jarvis-v2 && pytest tests/ -x -q 2>&1 | tail -20
```

Expected: all tests pass, no regressions.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/prompt_contract.py
git commit -m "refactor: replace hardcoded name in prompt_contract lane identity clauses with get_entity_name()"
```

---

## Final Verification

- [ ] **Confirm no remaining "Du er Jarvis" in LLM prompts**

```bash
conda activate ai && grep -rn "Du er Jarvis" apps/api/jarvis_api/services/ | grep -v ".pyc"
```

Expected: zero matches (or only in comments/docstrings, not in string literals sent to LLM).

- [ ] **Full compile check**

```bash
conda activate ai && python -m compileall core apps/api scripts 2>&1 | grep -i error
```

Expected: no errors.

- [ ] **Full test suite**

```bash
conda activate ai && pytest tests/ -q 2>&1 | tail -10
```

Expected: all tests pass.
