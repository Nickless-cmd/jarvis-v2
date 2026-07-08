---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Central-styret indre liv — Implementeringsplan (Plan 1: Fase 0 + Fase 1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Byg det ændrings-drevne injektions-register (Centralen vedligeholder indre-livs-sektioner i baggrunden; hot-path læser dem cached ~50ms), og bevis det på to pilot-sektioner (`rule_engine_conclusions` + `cognitive_state`) med per-enhed rollback.

**Architecture:** Et generisk register (`central_injection_registry`) holder "injektions-enheder" (kilde-nerver, tærskel, max-alder, compose_fn, durabel cache-nøgle). En refresh-motor på Centralens cadence (runtime-proces) genberegner kun beskidte enheder og skriver deres tekst durabelt. Prompt-assembly (api-proces) læser den cachede tekst i stedet for at bygge sektionen — per-enhed rollback-flag afgør cached-vs-direkte-build.

**Tech Stack:** Python 3.11, sqlite runtime-state kv (`core.runtime.db_core`), `central_timeseries` (nerve-værdier), pytest. Modellen at følge: `central_self_state` (durabel STATE_READ ~50ms).

**Spec:** `docs/superpowers/specs/2026-07-05-central-governed-inner-life-design.md`
**Sektions-inventar:** `docs/notes/2026-07-05-prompt-assembly-section-inventory.md`

---

## Filstruktur

- **Create** `core/services/central_injection_registry.py` — generisk mekanisme: `InjectionUnit`-dataclass, `register`/`read_injection`/`is_dirty`/`refresh_unit`/`refresh_dirty`, kv-helpers, `_nerve_latest`, `injection_live`/`set_injection_live`. Ét ansvar: injektions-livscyklus.
- **Create** `core/services/central_injection_units.py` — deklarative pilot-enheds-definitioner + `register_default_units()`. Ét ansvar: HVILKE sektioner der er enheder (adskilt fra mekanismen).
- **Create** `tests/test_central_injection_registry.py` — mekanisme-tests.
- **Create** `tests/test_central_injection_units.py` — enheds-registrerings- + rigdoms-tests.
- **Modify** `core/services/internal_cadence.py:1347` (`_scheduler_loop`) — kald `refresh_dirty()` pr. tick (efter prime, self-safe).
- **Modify** `core/services/prompt_contract.py` — Fase 1: `:1299` (rule_conclusions) + `:581`/`:2014` (cognitive_state) læser injektion når live; `:1607` (dead_skills) + `:1891`/`:2834` (null-bridge) lukkes.

---

## FASE 0 — Mekanismen

### Task 1: InjectionUnit + register + read_injection + kv-helpers

**Files:**
- Create: `core/services/central_injection_registry.py`
- Test: `tests/test_central_injection_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_injection_registry.py
from __future__ import annotations
import core.services.central_injection_registry as reg


def _use_store(monkeypatch):
    """Isolér kv i en dict så tests ikke rører rigtig runtime-state."""
    store: dict = {}
    monkeypatch.setattr(reg, "_kv_get", lambda k, d: store.get(k, d))
    monkeypatch.setattr(reg, "_kv_set", lambda k, v: store.update({k: v}))
    return store


def test_register_and_read_empty_when_never_composed(monkeypatch):
    _use_store(monkeypatch)
    reg._REGISTRY.clear()
    unit = reg.InjectionUnit(key="demo", source_nerves=(), threshold=0.1,
                             max_age_s=120.0, compose_fn=lambda: "hej")
    reg.register(unit)
    assert "demo" in reg.registered_keys()
    # Aldrig komponeret → hot-path læser tom streng (ALDRIG et compose-kald på læse-stien)
    assert reg.read_injection("demo") == ""
    assert reg.read_injection("ukendt") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py::test_register_and_read_empty_when_never_composed -v`
Expected: FAIL med `ModuleNotFoundError: No module named 'core.services.central_injection_registry'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/central_injection_registry.py
"""Central-styret injektions-register (ændrings-drevet indre liv, spec 2026-07-05).

Centralen vedligeholder indre-livs-sektioner i BAGGRUNDEN: en refresh-motor (cadence,
runtime-proces) genberegner kun BESKIDTE enheder og skriver deres tekst durabelt.
Prompt-assembly (api-proces) LÆSER den cachede tekst — komponerer aldrig. Ét sted alt
flyder igennem: Centralen afgør hvornår en sektion har ændret sig materielt.

Self-safe: kaster ALDRIG. read_injection falder tilbage til tom streng.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

_CACHE_PREFIX = "injection:cache:"   # + key → {"text", "composed_at", "source_snapshot"}
_LIVE_PREFIX = "injection:live:"     # + key → bool (rollback-flag; default False = direkte build)


@dataclass
class InjectionUnit:
    key: str
    source_nerves: tuple[str, ...]           # "cluster:nerve"-navne (kan være tom → ren max-alder)
    threshold: float                          # materiel-ændrings-tærskel på nerve-delta
    max_age_s: float                          # sikkerhedsnet: refresh selv uden ændring
    compose_fn: Callable[[], str]             # den EKSISTERENDE builder (uændret)
    priority: int = 50


_REGISTRY: dict[str, InjectionUnit] = {}


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def register(unit: InjectionUnit) -> None:
    _REGISTRY[unit.key] = unit


def registered_keys() -> list[str]:
    return list(_REGISTRY)


def read_injection(key: str) -> str:
    """Hot-path (api-proces): læs den cachede injektions-tekst. ALDRIG et compose-kald.
    Tom streng hvis aldrig komponeret → assembly blokerer aldrig på et indre-livs-kald."""
    blob = _kv_get(_CACHE_PREFIX + key, {})
    if not isinstance(blob, dict):
        return ""
    return str(blob.get("text") or "")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py::test_register_and_read_empty_when_never_composed -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/central_injection_registry.py tests/test_central_injection_registry.py
git commit -m "feat(injection): InjectionUnit-register + read_injection (Fase 0)"
```

---

### Task 2: Ændrings-detektion (is_dirty: aldrig-komponeret / max-alder / signal-delta)

**Files:**
- Modify: `core/services/central_injection_registry.py`
- Test: `tests/test_central_injection_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# append til tests/test_central_injection_registry.py
def test_is_dirty_rules(monkeypatch):
    store = _use_store(monkeypatch)
    reg._REGISTRY.clear()
    # Fast nerve-værdi vi kan styre
    nerves = {"cognition:affect": 1.0}
    monkeypatch.setattr(reg, "_nerve_latest", lambda n: nerves.get(n))
    unit = reg.InjectionUnit(key="u", source_nerves=("cognition:affect",),
                             threshold=0.5, max_age_s=100.0, compose_fn=lambda: "x")
    reg.register(unit)

    now = 1000.0
    # (a) aldrig komponeret → dirty
    assert reg.is_dirty(unit, now) is True

    # komponér ved now → gem snapshot affect=1.0
    store[reg._CACHE_PREFIX + "u"] = {"text": "x", "composed_at": now,
                                      "source_snapshot": {"cognition:affect": 1.0}}
    # (b) intet ændret, inden for max-alder → ren
    assert reg.is_dirty(unit, now + 10) is False
    # (c) over max-alder → dirty
    assert reg.is_dirty(unit, now + 101) is False or reg.is_dirty(unit, now + 101) is True
    assert reg.is_dirty(unit, now + 101) is True
    # (d) nerve flytter sig over tærskel → dirty
    nerves["cognition:affect"] = 1.8   # delta 0.8 > 0.5
    assert reg.is_dirty(unit, now + 10) is True
    # (e) nerve flytter sig under tærskel → ren
    nerves["cognition:affect"] = 1.2   # delta 0.2 < 0.5
    assert reg.is_dirty(unit, now + 10) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py::test_is_dirty_rules -v`
Expected: FAIL med `AttributeError: module ... has no attribute 'is_dirty'`

- [ ] **Step 3: Write minimal implementation**

```python
# append til core/services/central_injection_registry.py
def _nerve_latest(nerve: str) -> float | None:
    """Seneste værdi for 'cluster:nerve' fra central_timeseries. None hvis ukendt.
    Kører i runtime-procesen hvor de kognitive nerver produceres."""
    try:
        from core.services import central_timeseries as ts
        entry = ts.snapshot().get(nerve) or {}
        v = entry.get("latest")
        return float(v) if v is not None else None
    except Exception:
        return None


def is_dirty(unit: InjectionUnit, now: float) -> bool:
    """Beskidt hvis: aldrig komponeret, over max-alder, ELLER en kilde-nerve flyttet > tærskel."""
    blob = _kv_get(_CACHE_PREFIX + unit.key, {})
    if not isinstance(blob, dict) or not blob.get("composed_at"):
        return True
    try:
        if now - float(blob["composed_at"]) > unit.max_age_s:
            return True
    except Exception:
        return True
    snap = blob.get("source_snapshot") or {}
    for nerve in unit.source_nerves:
        cur = _nerve_latest(nerve)
        if cur is None:
            continue
        prev = snap.get(nerve)
        if prev is None:
            return True
        try:
            if abs(cur - float(prev)) > unit.threshold:
                return True
        except Exception:
            return True
    return False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py::test_is_dirty_rules -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/central_injection_registry.py tests/test_central_injection_registry.py
git commit -m "feat(injection): ændrings-detektion is_dirty (signal-delta + max-alder)"
```

---

### Task 3: refresh_unit + refresh_dirty (self-safe baggrunds-motor)

**Files:**
- Modify: `core/services/central_injection_registry.py`
- Test: `tests/test_central_injection_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# append til tests/test_central_injection_registry.py
def test_refresh_composes_and_caches(monkeypatch):
    store = _use_store(monkeypatch)
    reg._REGISTRY.clear()
    monkeypatch.setattr(reg, "_nerve_latest", lambda n: 2.0)
    calls = {"n": 0}
    def compose():
        calls["n"] += 1
        return f"tekst-{calls['n']}"
    unit = reg.InjectionUnit(key="u", source_nerves=("cognition:affect",),
                             threshold=0.5, max_age_s=100.0, compose_fn=compose)
    reg.register(unit)

    reg.refresh_dirty(now=1000.0)          # aldrig komponeret → komponér
    assert calls["n"] == 1
    assert reg.read_injection("u") == "tekst-1"
    blob = store[reg._CACHE_PREFIX + "u"]
    assert blob["source_snapshot"] == {"cognition:affect": 2.0}

    reg.refresh_dirty(now=1005.0)          # intet ændret, inden for max-alder → INGEN re-compose
    assert calls["n"] == 1


def test_refresh_is_self_safe_on_compose_error(monkeypatch):
    _use_store(monkeypatch)
    reg._REGISTRY.clear()
    monkeypatch.setattr(reg, "_nerve_latest", lambda n: None)
    def boom():
        raise RuntimeError("compose nede")
    reg.register(reg.InjectionUnit(key="bad", source_nerves=(), threshold=0.1,
                                   max_age_s=1.0, compose_fn=boom))
    reg.refresh_dirty(now=1.0)             # må ALDRIG kaste
    assert reg.read_injection("bad") == ""  # forblev tom
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py -k refresh -v`
Expected: FAIL med `AttributeError: ... 'refresh_dirty'`

- [ ] **Step 3: Write minimal implementation**

```python
# append til core/services/central_injection_registry.py
def refresh_unit(unit: InjectionUnit, now: float) -> None:
    """Genberegn ÉN enhed (det tunge LLM/subsystem-kald — OFF hot-path) og skriv durabelt."""
    text = unit.compose_fn() or ""
    snap = {}
    for nerve in unit.source_nerves:
        v = _nerve_latest(nerve)
        if v is not None:
            snap[nerve] = v
    _kv_set(_CACHE_PREFIX + unit.key, {
        "text": str(text), "composed_at": float(now), "source_snapshot": snap,
    })


def refresh_dirty(now: float | None = None) -> int:
    """Kaldes fra Centralens cadence: refresh alle beskidte enheder. Self-safe pr. enhed.
    Returnerer antal genberegnede (til observabilitet)."""
    if now is None:
        now = time.time()
    n = 0
    for unit in sorted(_REGISTRY.values(), key=lambda u: u.priority):
        try:
            if is_dirty(unit, now):
                refresh_unit(unit, now)
                n += 1
        except Exception:
            continue
    return n
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py -k refresh -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/central_injection_registry.py tests/test_central_injection_registry.py
git commit -m "feat(injection): refresh_unit + self-safe refresh_dirty baggrunds-motor"
```

---

### Task 4: Rollback-flag (injection_live) — per-enhed cached-vs-direkte

**Files:**
- Modify: `core/services/central_injection_registry.py`
- Test: `tests/test_central_injection_registry.py`

- [ ] **Step 1: Write the failing test**

```python
# append til tests/test_central_injection_registry.py
def test_injection_live_flag_defaults_off(monkeypatch):
    store = _use_store(monkeypatch)
    # Default OFF = hot-path bruger direkte build (sikker under udrulning)
    assert reg.injection_live("rule_conclusions") is False
    reg.set_injection_live("rule_conclusions", True)
    assert reg.injection_live("rule_conclusions") is True
    assert store[reg._LIVE_PREFIX + "rule_conclusions"] is True
    reg.set_injection_live("rule_conclusions", False)
    assert reg.injection_live("rule_conclusions") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py::test_injection_live_flag_defaults_off -v`
Expected: FAIL med `AttributeError: ... 'injection_live'`

- [ ] **Step 3: Write minimal implementation**

```python
# append til core/services/central_injection_registry.py
def injection_live(key: str) -> bool:
    """Er denne enhed 'live' (hot-path læser cached) eller rullet tilbage (direkte build)?
    Default FALSE → sikker: uændret adfærd indtil vi eksplicit flipper enheden live."""
    return bool(_kv_get(_LIVE_PREFIX + key, False))


def set_injection_live(key: str, live: bool) -> None:
    _kv_set(_LIVE_PREFIX + key, bool(live))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_central_injection_registry.py::test_injection_live_flag_defaults_off -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/central_injection_registry.py tests/test_central_injection_registry.py
git commit -m "feat(injection): per-enhed rollback-flag injection_live (default off)"
```

---

### Task 5: Hook refresh_dirty ind i cadence-scheduleren

**Files:**
- Modify: `core/services/internal_cadence.py:1347` (`_scheduler_loop`, efter STITCH-prime, før pulsen)
- Test: `tests/test_injection_cadence_hook.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_injection_cadence_hook.py
"""Verificér at cadence-scheduleren kalder injektions-refreshen pr. tick."""
from __future__ import annotations
import core.services.internal_cadence as ic


def test_scheduler_calls_injection_refresh(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(
        "core.services.central_injection_registry.refresh_dirty",
        lambda: called.__setitem__("n", called["n"] + 1))
    # Kald den udskilte tick-krop direkte (ikke hele loopet)
    ic._run_injection_refresh_tick()
    assert called["n"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_injection_cadence_hook.py -v`
Expected: FAIL med `AttributeError: ... '_run_injection_refresh_tick'`

- [ ] **Step 3: Write minimal implementation**

Tilføj helper nær `_scheduler_loop` i `core/services/internal_cadence.py`:

```python
def _run_injection_refresh_tick() -> None:
    """Central-styret indre liv: refresh beskidte injektions-enheder i baggrunden (OFF hot-path).
    Self-safe — en refresh-fejl må aldrig stoppe cadence-loopet."""
    try:
        from core.services import central_injection_units
        central_injection_units.register_default_units()   # idempotent
        from core.services.central_injection_registry import refresh_dirty
        refresh_dirty()
    except Exception:
        pass
```

Kald den inde i `_scheduler_loop`'s `try:` — lige efter STITCH-prime-blokken (`_seam_primed = True`), før puls-skrivningen:

```python
            _run_injection_refresh_tick()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_injection_cadence_hook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/internal_cadence.py tests/test_injection_cadence_hook.py
git commit -m "feat(injection): kør refresh_dirty pr. cadence-tick (baggrunds-motor live)"
```

---

### Task 6: Luk dead_skills + null visible-bridge (ægte spild)

**Files:**
- Modify: `core/services/prompt_contract.py:1607` (dead_skills), `:1891` (bridge-future submit)
- Test: `tests/test_prompt_contract_dead_sections.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_prompt_contract_dead_sections.py
"""dead_skills + null visible-bridge skal ikke længere bygges på visible-lanen."""
from __future__ import annotations
import inspect
import core.services.prompt_contract as pc


def test_dead_skills_not_called_in_assembly():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    # dead_skills_section må ikke længere kaldes i assembly-kroppen
    assert "dead_skills_section(" not in src


def test_null_bridge_future_not_submitted():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    assert "_build_inner_visible_prompt_bridge_decision" not in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_prompt_contract_dead_sections.py -v`
Expected: FAIL (begge strenge findes stadig i kilden)

- [ ] **Step 3: Write minimal implementation**

I `core/services/prompt_contract.py`, fjern de to sektioner fra `build_visible_chat_prompt_assembly`:

Ved `:1606-1607` — fjern hele dead_skills-blokken:
```python
        # FJERNET (spec 2026-07-05): dead_skills bygger tekst om aldrig-brugte skills.
        # from core.services.prompt_sections.dead_skills import dead_skills_section
        # _awareness_add(43, "dead skills (never invoked)", dead_skills_section() or None)
```

Ved `:1889-1891` — fjern bridge-future-submit'en OG dens resolve længere nede (`:1989`, `future_bridge_decision`). Erstat brugen med `None` (den er altid None på visible-lane):
```python
        # FJERNET (spec 2026-07-05): _build_inner_visible_prompt_bridge_decision returnerer
        # GARANTERET line=None på visible-lane (full-support-mode) → spildt future-orkestrering.
        _bridge_line = None
```
Fjern den tilhørende `_timed_result(future_bridge_decision, ...)`-resolve og brug `_bridge_line`.

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_prompt_contract_dead_sections.py -v && python -m compileall -q core/services/prompt_contract.py`
Expected: PASS + compile OK

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py tests/test_prompt_contract_dead_sections.py
git commit -m "chore(prompt): luk dead_skills + altid-null visible-bridge (spec 2026-07-05)"
```

---

## FASE 1 — Pilot (bevis mekanismen på 2 ægte sektioner)

### Task 7: Deklarér pilot-enhederne (rule_conclusions + cognitive_state)

**Files:**
- Create: `core/services/central_injection_units.py`
- Test: `tests/test_central_injection_units.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_central_injection_units.py
from __future__ import annotations
import core.services.central_injection_registry as reg
import core.services.central_injection_units as units


def test_default_units_registered():
    reg._REGISTRY.clear()
    units._REGISTERED = False
    units.register_default_units()
    keys = set(reg.registered_keys())
    assert {"rule_conclusions", "cognitive_state"} <= keys
    # idempotent
    units.register_default_units()
    assert len(reg.registered_keys()) == len(keys)


def test_pilot_units_have_callable_compose():
    reg._REGISTRY.clear(); units._REGISTERED = False
    units.register_default_units()
    for k in ("rule_conclusions", "cognitive_state"):
        u = reg._REGISTRY[k]
        assert callable(u.compose_fn)
        assert u.max_age_s > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_central_injection_units.py -v`
Expected: FAIL med `ModuleNotFoundError: ... central_injection_units`

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/central_injection_units.py
"""Deklarative injektions-enheds-definitioner (adskilt fra mekanismen).

Pilot (Fase 1): de to tungeste ikke-besked-afhængige sektioner. compose_fn GENBRUGER
de eksisterende buildere uændret — vi flytter dem bare til baggrunds-refresh.
"""
from __future__ import annotations

from core.services.central_injection_registry import InjectionUnit, register

_REGISTERED = False


def _compose_rule_conclusions() -> str:
    try:
        from core.services.prompt_sections.rule_conclusions import rule_conclusions_section
        return rule_conclusions_section() or ""
    except Exception:
        return ""


def _compose_cognitive_state() -> str:
    # force=True: omgå builderens interne cache — vi VIL have en frisk genberegning i
    # baggrunden (de kolde 6s betales OFF hot-path).
    try:
        from core.services.cognitive_state_assembly import build_cognitive_state_for_prompt
        return build_cognitive_state_for_prompt(compact=False, force=True) or ""
    except Exception:
        return ""


def register_default_units() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    register(InjectionUnit(
        key="rule_conclusions", source_nerves=(), threshold=1.0,
        max_age_s=120.0, compose_fn=_compose_rule_conclusions, priority=28))
    register(InjectionUnit(
        key="cognitive_state",
        source_nerves=("cognition:affect", "cognition:agenda", "cognition:affective_meta"),
        threshold=0.5, max_age_s=180.0, compose_fn=_compose_cognitive_state, priority=20))
    _REGISTERED = True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_central_injection_units.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/central_injection_units.py tests/test_central_injection_units.py
git commit -m "feat(injection): deklarér pilot-enheder rule_conclusions + cognitive_state"
```

---

### Task 8: Læs rule_conclusions fra injektion når live (rollback-gatet)

**Files:**
- Modify: `core/services/prompt_contract.py:1297-1299`
- Test: `tests/test_central_injection_units.py`

- [ ] **Step 1: Write the failing test**

```python
# append til tests/test_central_injection_units.py
import inspect
import core.services.prompt_contract as pc


def test_rule_conclusions_reads_injection_when_live():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    # Hot-path skal gå gennem injection_live-gaten for rule_conclusions
    assert 'injection_live("rule_conclusions")' in src
    assert 'read_injection("rule_conclusions")' in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_central_injection_units.py::test_rule_conclusions_reads_injection_when_live -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

Erstat `core/services/prompt_contract.py:1297-1299`-blokken:

```python
        from core.services.prompt_sections.rule_conclusions import (
            rule_conclusions_section,
        )
        from core.services.central_injection_registry import injection_live, read_injection
        if injection_live("rule_conclusions"):
            _rule_text = read_injection("rule_conclusions")          # baggrunds-cached (~0ms)
        else:
            _rule_text = rule_conclusions_section()                  # gammel direkte build (rollback)
        _awareness_add(28, "rule engine conclusions", _rule_text or None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_central_injection_units.py -v && python -m compileall -q core/services/prompt_contract.py`
Expected: PASS + compile OK

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py tests/test_central_injection_units.py
git commit -m "feat(injection): rule_conclusions læser injektion når live (rollback-gatet)"
```

---

### Task 9: Læs cognitive_state fra injektion når live (rollback-gatet)

**Files:**
- Modify: `core/services/prompt_contract.py:581-583` (submit) + `:2014`/`:2029` (resolve/add)
- Test: `tests/test_central_injection_units.py`

- [ ] **Step 1: Write the failing test**

```python
# append til tests/test_central_injection_units.py
def test_cognitive_state_reads_injection_when_live():
    src = inspect.getsource(pc.build_visible_chat_prompt_assembly)
    assert 'injection_live("cognitive_state")' in src
    assert 'read_injection("cognitive_state")' in src
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_central_injection_units.py::test_cognitive_state_reads_injection_when_live -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

To ændringer. Ved submit (`:581-584`), gør future'en betinget:

```python
        from core.services.central_injection_registry import injection_live, read_injection
        _cog_live = injection_live("cognitive_state")
        future_cognitive_state = None if _cog_live else _measured_submit(
            "cognitive_state",
            _safe_build_cognitive_state_for_prompt, compact=compact,
        )
```

Ved resolve/add (`:2014`/`:2029`, hvor `future_cognitive_state` bruges):

```python
        if _cog_live:
            _cog_state = read_injection("cognitive_state")           # baggrunds-cached
        else:
            _cog_state = _timed_result(future_cognitive_state, "cognitive_state", default=None)
        # ... uændret: _awareness_add(...) / parts.append(...) med _cog_state
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_central_injection_units.py -v && python -m compileall -q core/services/prompt_contract.py`
Expected: PASS + compile OK

- [ ] **Step 5: Commit**

```bash
git add core/services/prompt_contract.py tests/test_central_injection_units.py
git commit -m "feat(injection): cognitive_state læser injektion når live (rollback-gatet)"
```

---

### Task 10: Rigdoms-snapshot-harness (cached ≥ direkte)

**Files:**
- Create: `scripts/injection_richness_check.py`
- Test: `tests/test_injection_richness_check.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_injection_richness_check.py
"""Rigdoms-gate: cached injektion må ikke være fladere end den direkte build."""
from __future__ import annotations
from scripts.injection_richness_check import richness_ok


def test_richness_ok_equal_or_richer():
    assert richness_ok(direct="linje a\nlinje b", cached="linje a\nlinje b\nlinje c") is True
    assert richness_ok(direct="linje a\nlinje b", cached="linje a\nlinje b") is True


def test_richness_flags_flatter():
    # Cached tabte >20% af indholdet → ikke ok (rollback-signal)
    assert richness_ok(direct="a\nb\nc\nd\ne", cached="a") is False


def test_richness_empty_direct_is_ok():
    assert richness_ok(direct="", cached="") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `conda activate ai && python -m pytest tests/test_injection_richness_check.py -v`
Expected: FAIL med `ModuleNotFoundError: ... injection_richness_check`

- [ ] **Step 3: Write minimal implementation**

```python
# scripts/injection_richness_check.py
"""Rigdoms-gate for injektions-migration (spec 2026-07-05 §7).

richness_ok: er den cachede tekst lige-så-rig-eller-rigere end den direkte build?
Heuristik: cached må ikke tabe mere end 20% af den direkte builds ikke-tomme linjer.
Bruges som fase-gate — fladere output = rollback-signal.
"""
from __future__ import annotations


def _lines(text: str) -> list[str]:
    return [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]


def richness_ok(*, direct: str, cached: str) -> bool:
    d = _lines(direct)
    if not d:
        return True
    c = _lines(cached)
    return len(c) >= 0.8 * len(d)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `conda activate ai && python -m pytest tests/test_injection_richness_check.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/injection_richness_check.py tests/test_injection_richness_check.py
git commit -m "feat(injection): rigdoms-gate richness_ok (cached ≥ direkte, spec §7)"
```

---

## Verifikation (operationel — efter deploy, ikke en kode-task)

Efter Fase 0+1 er merged og deployet til containeren (`ssh bs@10.0.0.39`, pull, restart api+runtime):

1. **Baggrunds-motor lever:** `jc series` viser at `rule_conclusions` + `cognitive_state` cache-nøgler fyldes; `refresh_dirty` kører pr. cadence-tick uden fejl i journalen.
2. **Rigdoms-gate (pr. pilot-enhed, FØR flip live):** kør `python scripts/injection_richness_check.py` mod en direkte-build vs den cachede tekst → `richness_ok=True`, ellers stop.
3. **Flip live én ad gangen:** `set_injection_live("rule_conclusions", True)` → mål `prompt-assembly-timing` over ≥50 ægte ture. Forvent `rule_engine`-bidraget forsvinder fra hot-path (~6s). Gentag for `cognitive_state`.
4. **Rollback-kriterium:** hvis output bliver fladere, latens regredierer, ELLER indhold er stale → `set_injection_live(key, False)` (øjeblikkelig, ingen deploy).

**Fase-gate:** begge pilot-enheder lige-så-rige + målt latens-fald → grøn til Plan 2 (fuld migration). Ellers revidér mekanismen.

---

## Self-Review

**Spec-dækning (Fase 0+1):** §3 arkitektur → Task 1-5. §4 ændrings-detektion → Task 2. §5 luk døde → Task 6; pilot-migration → Task 7-9. §7 rigdom+rollback → Task 4 (flag) + Task 10 (gate) + Verifikation. §8 fasering → planen ER Fase 0+1; Fase 2-3 er separate planer (noteret). Måling → Verifikation-sektion. Ikke dækket her (bevidst, senere planer): fuld 🟢-migration, digest-konsolidering, recall-dedup (Plan 2); self-surveillance + anti-gaming (Plan 3).

**Placeholder-scan:** ingen TBD/TODO; alle kode-steps har komplet kode + eksakte kommandoer.

**Type-konsistens:** `InjectionUnit`-felter (key/source_nerves/threshold/max_age_s/compose_fn/priority) ens i Task 1, 2, 7. `injection_live`/`read_injection`/`refresh_dirty`/`is_dirty` samme signaturer på tværs. `_CACHE_PREFIX`/`_LIVE_PREFIX` konsistente. `register_default_units`/`_REGISTERED` ens i Task 5 og 7.
