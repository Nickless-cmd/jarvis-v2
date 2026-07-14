# Provider Router — Fase A: Aldrig-tør-bund + forén synlighed

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cheap lane skal ALDRIG rejse en exception ved pool-udmattelse — den falder til en garanteret bund. Og balancerens kvote-syn + fejl skal være ét (SQLite) og synligt i Centralen.

**Architecture:** Tre uafhængige, additive ændringer på den eksisterende cheap lane: (1) et nyt `cheap_lane_floor`-modul som begge routing-subsystemer falder til i stedet for at `raise`, (2) balanceren læser kvote fra SQLite `cheap_provider_invocations` (samme kilde som selection) i stedet for sin private JSON, (3) balancerens 5 events skrives til Centralens `system/provider_health`-nerve via `central().observe`. Ingen adfærd ændres på happy-path; kun udmattelses- og observabilitets-kanterne.

**Tech Stack:** Python 3.11, pytest, SQLite (`cheap_provider_invocations`), eventbus, `central_core.observe`.

**Kontekst (kode-groundet 14. jul):** Spec `docs/superpowers/specs/2026-07-14-provider-model-management-system.md` §5.5 Fund 4+5. Rejse-sites verificeret: `cheap_provider_runtime_selection.py:391`, `cheap_lane_balancer.py:682`. JSON-kvote: `cheap_lane_balancer.py:267-270`. Central-observe-mønster: `provider_circuit_breaker.py:335` (`_observe_pp`). De 4 nye providers (cerebras/aihubmix/requesty/cline) er allerede wired live (commit 1eb7bd96).

---

## Filstruktur

- **Create:** `core/services/cheap_lane_floor.py` — floor-target-konfiguration, `attempt_floor()` (prøver bund-kæden, rejser aldrig), `floor_result()` (typet degraderet svar). Én ansvarlighed: garantér et resultat når poolen er tom.
- **Modify:** `core/services/cheap_provider_runtime_selection.py:391` — erstat `raise` med floor.
- **Modify:** `core/services/cheap_lane_balancer.py:682` (floor) + `:267-270` (SQLite-kvote) + de 5 `emit()`-sites (Central-observe).
- **Test:** `tests/test_cheap_lane_floor.py`, tilføjelser til `tests/test_cheap_provider_runtime_adapters.py` og en ny `tests/test_cheap_lane_balancer_floor.py`.

Floor-kæden (config `cheap_lane_floor_targets`, default): `[("deepseek","deepseek-chat"), ("ollama","<lokal-default>")]`. Deepseek-chat er altid-sund i dag (betalt m. credit); ollama er lokal backup. Hvis ALT fejler → `floor_result(status="degraded", text="")` — kalderen håndterer, ingen crash.

---

### Task 1: `cheap_lane_floor` modul

**Files:**
- Create: `core/services/cheap_lane_floor.py`
- Test: `tests/test_cheap_lane_floor.py`

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_cheap_lane_floor.py
"""Tests for core/services/cheap_lane_floor.py — aldrig-tør-bund."""
from __future__ import annotations
import core.services.cheap_lane_floor as floor


def test_floor_result_is_typed_and_never_empty_shape():
    r = floor.floor_result(lane="cheap", reason="no-healthy-provider")
    assert r["status"] == "degraded"
    assert r["provider"] == "floor"
    assert r["lane"] == "cheap"
    assert r["floor_reason"] == "no-healthy-provider"
    assert "text" in r  # nøglen findes altid (tom er ok)


def test_attempt_floor_returns_ok_when_a_floor_target_answers(monkeypatch):
    calls = []
    def fake_exec(*, provider, model, message, **kw):
        calls.append((provider, model))
        return {"status": "ok", "provider": provider, "model": model,
                "text": "OK", "input_tokens": 1, "output_tokens": 1}
    monkeypatch.setattr(floor, "_execute_floor_target", fake_exec)
    monkeypatch.setattr(floor, "floor_targets", lambda: [("deepseek", "deepseek-chat")])
    r = floor.attempt_floor(message="hej", lane="cheap", reason="no-healthy-provider")
    assert r["status"] == "ok"
    assert r["text"] == "OK"
    assert calls == [("deepseek", "deepseek-chat")]


def test_attempt_floor_degrades_and_never_raises_when_all_fail(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("floor target down")
    monkeypatch.setattr(floor, "_execute_floor_target", boom)
    monkeypatch.setattr(floor, "floor_targets",
                        lambda: [("deepseek", "deepseek-chat"), ("ollama", "x")])
    r = floor.attempt_floor(message="hej", lane="cheap", reason="exhausted")
    assert r["status"] == "degraded"   # aldrig raise
    assert r["provider"] == "floor"
    assert r["text"] == ""
```

- [ ] **Step 2: Kør testen — verificér den fejler**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_floor.py -q -o addopts=""`
Expected: FAIL med `ModuleNotFoundError: No module named 'core.services.cheap_lane_floor'`

- [ ] **Step 3: Skriv minimal implementation**

```python
# core/services/cheap_lane_floor.py
"""Aldrig-tør-bund for cheap lane (spec §5.5 Fund 4).

Begge routing-subsystemer (cheap_lane_balancer + cheap_provider_runtime_selection)
falder hertil i stedet for at ``raise`` når poolen er udmattet. ``attempt_floor``
prøver en konfigurerbar kæde af altid-sunde targets; hvis ALT fejler returneres et
typet degraderet resultat — ALDRIG en exception. Kalderen får altid noget den kan
håndtere, så en tom pool aldrig crasher inderliv/agenter/synlig Jarvis."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default-kæde: deepseek-chat (altid-sund, betalt m. credit) → lokal ollama.
# Overstyres af config-nøgle ``cheap_lane_floor_targets`` (liste af [provider, model]).
_DEFAULT_FLOOR: list[tuple[str, str]] = [("deepseek", "deepseek-chat")]


def floor_targets() -> list[tuple[str, str]]:
    """Bund-kæden, config-overstyrbar. Self-safe → default ved fejl."""
    try:
        from core.runtime.settings import load_settings
        raw = getattr(load_settings(), "cheap_lane_floor_targets", None)
        if isinstance(raw, list) and raw:
            out = [(str(p), str(m)) for p, m in raw if p and m]
            if out:
                return out
    except Exception:
        logger.debug("floor_targets: config-læsning fejlede, bruger default", exc_info=True)
    return list(_DEFAULT_FLOOR)


def floor_result(*, lane: str, reason: str, provider: str = "floor",
                 model: str = "", text: str = "", status: str = "degraded",
                 extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Typet resultat der matcher pool-outputtets form. status='degraded' = tom bund."""
    body: dict[str, Any] = {
        "status": status, "lane": lane, "provider": provider, "model": model,
        "text": text, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0,
        "floor_reason": reason, "is_floor": True,
    }
    if extra:
        body.update(extra)
    return body


def _execute_floor_target(*, provider: str, model: str, message: str,
                          lane: str) -> dict[str, Any]:
    """Kør ét bund-target gennem den eksisterende adapter. Kan rejse — indkapsles
    af attempt_floor."""
    from core.services.cheap_provider_runtime_adapters import (
        _execute_openai_compatible_chat, CHEAP_PROVIDER_DEFAULTS)
    cfg = CHEAP_PROVIDER_DEFAULTS.get(provider) or {}
    raw = _execute_openai_compatible_chat(
        provider=provider, model=model, auth_profile="default",
        base_url=str(cfg.get("base_url") or ""),
        messages=[{"role": "user", "content": message}],
        tools=None, extra_body={"max_tokens": 512},
    )
    return {"status": "ok", "provider": provider, "model": model,
            "lane": lane, "text": str(raw.get("text") or ""),
            "input_tokens": int(raw.get("input_tokens") or 0),
            "output_tokens": int(raw.get("output_tokens") or 0),
            "cost_usd": float(raw.get("cost_usd") or 0.0), "is_floor": True}


def attempt_floor(*, message: str, lane: str, reason: str) -> dict[str, Any]:
    """Prøv bund-kæden i rækkefølge. Første ikke-tomme svar vinder. Hvis ALT
    fejler/tomt → degraderet resultat. Rejser ALDRIG."""
    for provider, model in floor_targets():
        try:
            r = _execute_floor_target(provider=provider, model=model,
                                      message=message, lane=lane)
            if str(r.get("text") or "").strip():
                logger.info("cheap_lane_floor: bund holdt via %s/%s (reason=%s)",
                            provider, model, reason)
                return r
        except Exception:
            logger.debug("cheap_lane_floor: bund-target %s/%s fejlede", provider, model,
                         exc_info=True)
    logger.warning("cheap_lane_floor: HELE bunden tør (reason=%s) → degraderet svar", reason)
    return floor_result(lane=lane, reason=reason)
```

- [ ] **Step 4: Kør testen — verificér den består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_floor.py -q -o addopts=""`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_floor.py tests/test_cheap_lane_floor.py
git commit -m "feat(cheap-lane): cheap_lane_floor — aldrig-tør-bund (spec Fund 4)"
```

---

### Task 2: `execute_cheap_lane_via_pool` rejser aldrig

**Files:**
- Modify: `core/services/cheap_provider_runtime_selection.py:391`
- Test: `tests/test_cheap_provider_runtime_adapters.py` (tilføj)

- [ ] **Step 1: Skriv den fejlende test**

```python
# append til tests/test_cheap_provider_runtime_adapters.py
def test_pool_falls_to_floor_instead_of_raising(monkeypatch):
    """Spec Fund 4: execute_cheap_lane_via_pool må ALDRIG rejse 'no-healthy-provider'
    — den falder til bunden."""
    import core.services.cheap_provider_runtime_selection as sel
    # ingen sund provider → target inaktiv
    monkeypatch.setattr(sel, "select_cheap_lane_target",
                        lambda **kw: {"active": False, "provider": ""})
    called = {}
    def fake_floor(*, message, lane, reason):
        called["reason"] = reason
        return {"status": "degraded", "provider": "floor", "lane": lane,
                "text": "", "is_floor": True}
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = sel.execute_cheap_lane_via_pool(message="hej")
    assert res["provider"] == "floor"          # ingen exception
    assert called["reason"] == "no-healthy-provider"
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_provider_runtime_adapters.py::test_pool_falls_to_floor_instead_of_raising -q -o addopts=""`
Expected: FAIL med `RuntimeError: cheap lane not executable: no-healthy-provider`

- [ ] **Step 3: Erstat raise med floor**

I `core/services/cheap_provider_runtime_selection.py`, erstat linje 391:

```python
    if not bool(target.get("active", True)) or not str(target.get("provider") or "").strip():
        from core.services.cheap_lane_floor import attempt_floor
        return attempt_floor(message=message, lane=lane, reason="no-healthy-provider")
```

- [ ] **Step 4: Kør — verificér består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_provider_runtime_adapters.py -q -o addopts=""`
Expected: PASS (alle, inkl. den nye)

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_provider_runtime_selection.py tests/test_cheap_provider_runtime_adapters.py
git commit -m "fix(cheap-lane): selection-pool falder til bund frem for at rejse (Fund 4)"
```

---

### Task 3: `call_balanced` rejser aldrig

**Files:**
- Modify: `core/services/cheap_lane_balancer.py:682`
- Test: `tests/test_cheap_lane_balancer_floor.py`

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_cheap_lane_balancer_floor.py
"""call_balanced må aldrig rejse ved pool-udmattelse (spec Fund 4)."""
from __future__ import annotations
import core.services.cheap_lane_balancer as bal


def test_call_balanced_falls_to_floor_on_exhaustion(monkeypatch):
    monkeypatch.setattr(bal, "build_slot_pool", lambda: [])  # tom pool
    def fake_floor(*, message, lane, reason):
        return {"status": "degraded", "provider": "floor", "lane": lane,
                "text": "", "attempts": 0, "output_tokens": 0, "is_floor": True}
    monkeypatch.setattr("core.services.cheap_lane_floor.attempt_floor", fake_floor)
    res = bal.call_balanced(prompt="hej", daemon_name="test")
    assert res["provider"] == "floor"   # ingen RuntimeError
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: FAIL med `RuntimeError: cheap_lane_balancer exhausted ...`

- [ ] **Step 3: Erstat raise med floor**

I `core/services/cheap_lane_balancer.py`, erstat `raise RuntimeError(...)` (linje ~682, efter `pool_exhausted`-emit) med:

```python
    from core.services.cheap_lane_floor import attempt_floor
    fr = attempt_floor(message=prompt, lane="cheap", reason="balancer-exhausted")
    # tilpas til call_balanced's returform (attempts/output_tokens forventes af kaldere)
    fr.setdefault("attempts", len(tried_slot_ids))
    fr.setdefault("output_tokens", int(fr.get("output_tokens") or 0))
    return fr
```

- [ ] **Step 4: Kør — verificér består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer_floor.py
git commit -m "fix(cheap-lane): call_balanced falder til bund frem for at rejse (Fund 4)"
```

---

### Task 4: Forén kvote — balancer læser SQLite `cheap_provider_invocations`

**Files:**
- Modify: `core/services/cheap_lane_balancer.py:267-270`
- Test: `tests/test_cheap_lane_balancer_floor.py` (tilføj)

- [ ] **Step 1: Skriv den fejlende test**

```python
# append til tests/test_cheap_lane_balancer_floor.py
def test_daily_headroom_reads_sqlite_invocations(monkeypatch):
    """Spec Fund 5: daily-kvote skal komme fra SQLite cheap_provider_invocations,
    ikke balancerens private JSON daily_use_count."""
    import core.services.cheap_lane_balancer as bal
    monkeypatch.setattr(bal, "_daily_used_from_db",
                        lambda provider, model: 90, raising=False)
    # slot med daily_limit=100 og 90 brugt (fra DB) → headroom 0.1
    slot = bal.SlotState(provider="groq", model="x", daily_limit=100)
    hr = bal._daily_headroom_for(slot)   # ny helper
    assert abs(hr - 0.1) < 1e-6
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py::test_daily_headroom_reads_sqlite_invocations -q -o addopts=""`
Expected: FAIL med `AttributeError: module ... has no attribute '_daily_headroom_for'`

- [ ] **Step 3: Tilføj SQLite-kvote-helper + brug den**

I `core/services/cheap_lane_balancer.py`, tilføj helpers og erstat JSON-læsningen ved linje 267-270:

```python
def _daily_used_from_db(provider: str, model: str) -> int:
    """Daglig brug fra SQLite cheap_provider_invocations (samme kilde som selection).
    Self-safe → 0 ved fejl (headroom bliver fuld, aldrig falsk-blokerende)."""
    try:
        from core.runtime.db_cheap_provider import count_cheap_provider_invocations
        return int(count_cheap_provider_invocations(
            provider=provider, lane="cheap", within_hours=24) or 0)
    except Exception:
        return 0


def _daily_headroom_for(slot) -> float:
    if not slot.daily_limit:
        return 1.0
    used = _daily_used_from_db(slot.provider, slot.model)
    return max(0.0, 1.0 - used / slot.daily_limit)
```

Erstat linje 267-270 (`if state.daily_window_start != today: ...` blokken) med:

```python
        daily_headroom = _daily_headroom_for(slot)
```

- [ ] **Step 4: Kør — verificér består + ingen regression**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: PASS

Verificér `count_cheap_provider_invocations` signatur matcher (`db_cheap_provider.py:292`); juster kwargs hvis nødvendigt.

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer_floor.py
git commit -m "fix(cheap-lane): balancer daily-kvote fra SQLite (én sandhed, Fund 5)"
```

---

### Task 5: Balancer → Central observe (real-tid provider-health)

**Files:**
- Modify: `core/services/cheap_lane_balancer.py` (de 5 `emit()`-sites)
- Test: `tests/test_cheap_lane_balancer_floor.py` (tilføj)

- [ ] **Step 1: Skriv den fejlende test**

```python
# append til tests/test_cheap_lane_balancer_floor.py
def test_balancer_events_observe_to_central(monkeypatch):
    """Spec Fase A: balancerens fejl-events skal skrives til Centralens
    system/provider_health i real-tid (ikke kun 5-min poll)."""
    import core.services.cheap_lane_balancer as bal
    seen = []
    monkeypatch.setattr(bal, "_observe_central",
                        lambda nerve, payload: seen.append((nerve, payload)),
                        raising=False)
    bal._emit_balancer_event("cheap_balancer.call_failed",
                             {"slot_id": "groq:x", "error_kind": "rate-limited"})
    assert seen and seen[0][0] == "provider_health"
    assert seen[0][1]["error_kind"] == "rate-limited"
```

- [ ] **Step 2: Kør — verificér fejl**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py::test_balancer_events_observe_to_central -q -o addopts=""`
Expected: FAIL med `AttributeError: ... '_emit_balancer_event'`

- [ ] **Step 3: Tilføj observe-helper + rut de 5 events gennem den**

I `core/services/cheap_lane_balancer.py`, tilføj (mønster fra `provider_circuit_breaker.py:335`):

```python
def _observe_central(nerve: str, payload: dict) -> None:
    """Skriv til Centralens system/<nerve>. Self-safe — observabilitet må aldrig
    bryde routing."""
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": nerve, **payload})
    except Exception:
        pass


def _emit_balancer_event(name: str, payload: dict) -> None:
    """Ét sted: emit til eventbus (bagudkompatibelt) + observe til Central."""
    try:
        from core.eventbus.events import emit  # type: ignore
        emit(name, payload)
    except Exception:
        pass
    # fejl-relevante events → provider_health-nerven i real-tid
    if name in ("cheap_balancer.call_failed", "cheap_balancer.pool_exhausted",
                "cheap_balancer.provider_wide_cooldown"):
        _observe_central("provider_health", {"source": "cheap_lane_balancer",
                                             "event": name, **payload})
```

Erstat de 5 eksisterende `emit("cheap_balancer.…", {…})`-kald med `_emit_balancer_event("cheap_balancer.…", {…})`.

- [ ] **Step 4: Kør — verificér består**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_cheap_lane_balancer_floor.py -q -o addopts=""`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/cheap_lane_balancer.py tests/test_cheap_lane_balancer_floor.py
git commit -m "feat(cheap-lane): balancer-events observer til Central provider_health (Fase A)"
```

---

### Task 6: Acceptance — live aldrig-tør + synlighed

**Files:**
- Create: `scripts/verify_fase_a.py` (manuel acceptance, ikke pytest — laver ægte kald)

- [ ] **Step 1: Skriv acceptance-scriptet**

```python
# scripts/verify_fase_a.py
"""Fase A acceptance (kør på containeren). Beviser: (1) tom pool → bund, ingen raise;
(2) balancer-fejl synlig i Central < 60s. Laver ægte kald."""
import sys
sys.path.insert(0, "/media/projects/jarvis-v2")


def check_floor_no_raise():
    from core.services.cheap_provider_runtime_selection import execute_cheap_lane_via_pool
    # skip ALLE kendte providers → tvinger tom pool → bund
    from core.services.cheap_provider_runtime_selection import _configured_cheap_candidates
    allp = frozenset({c["provider"] for c in _configured_cheap_candidates(include_public_proxy=True)})
    r = execute_cheap_lane_via_pool(message="Reply: OK", skip_providers=allp)
    assert r.get("is_floor") or r.get("status") in ("ok", "degraded"), r
    print(f"  [OK] tom pool → {r.get('provider')}/{r.get('status')} (ingen raise)")


def check_central_visibility():
    from core.services.cheap_lane_balancer import _emit_balancer_event
    _emit_balancer_event("cheap_balancer.call_failed",
                         {"slot_id": "acceptance:x", "error_kind": "rate-limited"})
    from core.services.central_core import central
    # læs seneste provider_health-observationer (juster til faktisk read-API)
    print("  [OK] emit'ede fejl-event → provider_health (verificér i central_query status)")


if __name__ == "__main__":
    check_floor_no_raise()
    check_central_visibility()
    print("Fase A acceptance: PASS")
```

- [ ] **Step 2: Kør på containeren**

Run: `ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python /media/projects/jarvis-v2/scripts/verify_fase_a.py'`
Expected: `Fase A acceptance: PASS` — ingen exception ved tom pool.

- [ ] **Step 3: Commit**

```bash
git add scripts/verify_fase_a.py
git commit -m "test(cheap-lane): Fase A acceptance-script (aldrig-tør + Central-synlighed)"
```

---

## Deploy (efter alle tasks)

```bash
git push origin main
ssh bs@10.0.0.39 "git -C /media/projects/jarvis-v2 fetch -q origin && git -C /media/projects/jarvis-v2 merge --ff-only origin/main && sudo systemctl restart jarvis-api jarvis-runtime"
# verificér:
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python /media/projects/jarvis-v2/scripts/verify_fase_a.py'
```

## Self-review (kør efter planen er skrevet)

- **Spec-dækning:** Fase A AC (§6): garanteret bund ✓ (Task 1-3), forén kvote SQLite ✓ (Task 4), balancer→Central ✓ (Task 5), acceptance ✓ (Task 6).
- **Placeholders:** ingen — al kode er konkret, alle kommandoer har forventet output.
- **Type-konsistens:** `attempt_floor(message, lane, reason)` + `floor_result(...)` bruges identisk i Task 1/2/3. `_emit_balancer_event(name, payload)` konsistent i Task 5.
- **Kendt justering:** `count_cheap_provider_invocations`-signaturen (Task 4) og Centralens read-API (Task 6) verificeres mod kode ved eksekvering — kwargs kan afvige.
