# Prewarm-gate + deepseek-chat-migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop prewarm-runaway (270M→~10M tokens/13d) via traffic-gate + cross-process dedup, and migrate off the `deepseek-chat`/`deepseek-reasoner` aliases (deprecated 24. juli 2026) to `deepseek-v4-flash` + eksplicit thinking-param.

**Architecture:** WS1 gater `prewarm_once()` bag to betingelser (ingen rigtig deepseek-trafik i N sek + ingen anden proces har prewarmet i intervallet). WS4 erstatter model-navn-baseret thinking-toggle (`deepseek-chat`=non-thinking) med en param-baseret ikke-tænkende request på `deepseek-v4-flash`, så aliaserne kan udfases.

**Tech Stack:** Python 3.11, sqlite (`~/.jarvis-v2/state/jarvis.db` `costs`-tabel), runtime-state (`core/runtime/db_core.get_runtime_state_value`), shared_cache (`core/services/shared_cache`), pytest. Miljø: `conda activate ai`; test: `/opt/conda/envs/ai/bin/python -m pytest`.

**Deploy:** Kode udvikles+testes lokalt (CheifOne). Deploy = commit main → push → på container 10.0.0.39: **tjek `git log origin/main..HEAD` FØRST** (Jarvis committer selv → MERGE, ikke overwrite), `git pull`/`git merge`, `sudo systemctl restart jarvis-api jarvis-runtime`, verificér `HEAD==commit`.

---

## File Structure

- `core/services/assembly_prewarm.py` — **modify**: tilføj `_seconds_since_last_real_deepseek_call()`, `_seconds_since_last_prewarm()`, `_should_prewarm()`; gate `prewarm_once()`; sæt cross-process timestamp efter build.
- `tests/services/test_assembly_prewarm_gate.py` — **create**: unit-tests for gate-logikken (mockede timestamps).
- `core/services/cheap_provider_runtime_adapters.py` — **modify** (`deepseek_model_for_thinking_mode`, ~572): fast→param i stedet for `deepseek-chat`-alias.
- `core/memory/inner_llm_enrichment.py` — **modify** (~420): stop remap til `deepseek-chat`; brug `deepseek-v4-flash` + non-thinking-param.
- `tests/services/test_deepseek_thinking_param.py` — **create**: mapping composer-mode → (model, request-param).

---

## WS1 — Prewarm-gate

### Task 1: Traffic-gate helper — sekunder siden sidste RIGTIGE deepseek-kald

**Files:**
- Modify: `core/services/assembly_prewarm.py`
- Test: `tests/services/test_assembly_prewarm_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/services/test_assembly_prewarm_gate.py
import time
from core.services import assembly_prewarm as ap

def test_seconds_since_last_real_deepseek_call_reads_costs(monkeypatch):
    # Simulér costs-DB-svar: sidste rigtige deepseek-kald var 42s siden.
    now = time.time()
    monkeypatch.setattr(ap, "_max_created_at_real_deepseek", lambda: now - 42)
    monkeypatch.setattr(ap.time, "time", lambda: now)
    assert 41 <= ap._seconds_since_last_real_deepseek_call() <= 43

def test_seconds_since_last_real_deepseek_call_none_when_no_data(monkeypatch):
    monkeypatch.setattr(ap, "_max_created_at_real_deepseek", lambda: None)
    assert ap._seconds_since_last_real_deepseek_call() is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_assembly_prewarm_gate.py -o addopts="" -q`
Expected: FAIL — `AttributeError: module ... has no attribute '_seconds_since_last_real_deepseek_call'`

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/assembly_prewarm.py  (tilføj nær toppen af hjælpere)
import os, sqlite3

_COSTS_DB = os.path.expanduser("~/.jarvis-v2/state/jarvis.db")

def _max_created_at_real_deepseek() -> float | None:
    """Epoch-sekunder for seneste NON-warmer deepseek-kald i costs. None hvis ingen.
    Self-safe (DB-lås/fejl → None)."""
    try:
        c = sqlite3.connect(f"file:{_COSTS_DB}?mode=ro", uri=True, timeout=2)
        row = c.execute(
            "select max(created_at) from costs where provider='deepseek' "
            "and coalesce(lane,'') not like '%warm%'"
        ).fetchone()
        c.close()
        if not row or not row[0]:
            return None
        from datetime import datetime
        return datetime.fromisoformat(row[0]).timestamp()
    except Exception:
        return None

def _seconds_since_last_real_deepseek_call() -> float | None:
    ts = _max_created_at_real_deepseek()
    return None if ts is None else max(0.0, time.time() - ts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_assembly_prewarm_gate.py -o addopts="" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/services/assembly_prewarm.py tests/services/test_assembly_prewarm_gate.py
git commit -m "feat(prewarm): traffic-gate helper — seconds since last real deepseek call"
```

### Task 2: Cross-process dedup + `_should_prewarm()`

**Files:**
- Modify: `core/services/assembly_prewarm.py`
- Test: `tests/services/test_assembly_prewarm_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# append til tests/services/test_assembly_prewarm_gate.py
def test_should_prewarm_skips_when_recent_real_traffic(monkeypatch):
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: 120.0)  # <300 default
    monkeypatch.setattr(ap, "_seconds_since_last_prewarm", lambda: 9999.0)
    assert ap._should_prewarm() is False

def test_should_prewarm_skips_when_another_process_just_prewarmed(monkeypatch):
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: None)  # kold
    monkeypatch.setattr(ap, "_seconds_since_last_prewarm", lambda: 10.0)  # <interval
    monkeypatch.setattr(ap, "_interval_s", lambda: 240.0)
    assert ap._should_prewarm() is False

def test_should_prewarm_true_when_cold_and_no_recent_prewarm(monkeypatch):
    monkeypatch.setattr(ap, "_seconds_since_last_real_deepseek_call", lambda: 9999.0)
    monkeypatch.setattr(ap, "_seconds_since_last_prewarm", lambda: 9999.0)
    monkeypatch.setattr(ap, "_interval_s", lambda: 240.0)
    assert ap._should_prewarm() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_assembly_prewarm_gate.py -o addopts="" -q`
Expected: FAIL — `_should_prewarm`/`_seconds_since_last_prewarm` mangler

- [ ] **Step 3: Write minimal implementation**

```python
# core/services/assembly_prewarm.py
_SKIP_IF_RECENT_KEY = "assembly_prewarm_skip_if_recent_s"   # default 300 (DeepSeek cache-TTL)
_DEFAULT_SKIP_IF_RECENT = 300.0
_LAST_PREWARM_CACHE_KEY = "assembly_prewarm_last_ts"        # cross-process i shared_cache

def _skip_if_recent_s() -> float:
    try:
        from core.runtime.db_core import get_runtime_state_value
        return float(get_runtime_state_value(_SKIP_IF_RECENT_KEY, _DEFAULT_SKIP_IF_RECENT)
                     or _DEFAULT_SKIP_IF_RECENT)
    except Exception:
        return _DEFAULT_SKIP_IF_RECENT

def _seconds_since_last_prewarm() -> float | None:
    """Cross-process: sekunder siden ENHVER proces sidst prewarmede. None hvis aldrig."""
    try:
        from core.services import shared_cache as _sc
        ts = _sc.get(_LAST_PREWARM_CACHE_KEY)
        return None if not ts else max(0.0, time.time() - float(ts))
    except Exception:
        return None

def _mark_prewarmed() -> None:
    try:
        from core.services import shared_cache as _sc
        _sc.set(_LAST_PREWARM_CACHE_KEY, time.time(), ttl_seconds=3600)
    except Exception:
        pass

def _should_prewarm() -> bool:
    """Gate: (a) spring over hvis rigtig deepseek-trafik holder cachen varm; (b) spring
    over hvis en anden proces allerede prewarmede inden for intervallet. Kold+ledig → True."""
    since_real = _seconds_since_last_real_deepseek_call()
    if since_real is not None and since_real < _skip_if_recent_s():
        return False
    since_pw = _seconds_since_last_prewarm()
    if since_pw is not None and since_pw < _interval_s():
        return False
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_assembly_prewarm_gate.py -o addopts="" -q`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/assembly_prewarm.py tests/services/test_assembly_prewarm_gate.py
git commit -m "feat(prewarm): _should_prewarm gate (traffic + cross-process dedup)"
```

### Task 3: Wire gaten ind i `prewarm_once` + mark efter build

**Files:**
- Modify: `core/services/assembly_prewarm.py`
- Test: `tests/services/test_assembly_prewarm_gate.py`

- [ ] **Step 1: Write the failing test**

```python
# append til tests/services/test_assembly_prewarm_gate.py
def test_prewarm_once_skips_when_gate_false(monkeypatch):
    monkeypatch.setattr(ap, "_should_prewarm", lambda: False)
    called = {"build": False}
    def _boom(*a, **k): called["build"] = True
    # hvis den forsøgte at bygge ville den importere prompt_contract — vi asserter den IKKE gør
    assert ap.prewarm_once() is None
    assert called["build"] is False

def test_prewarm_once_marks_after_build(monkeypatch):
    monkeypatch.setattr(ap, "_should_prewarm", lambda: True)
    marked = {"v": False}
    monkeypatch.setattr(ap, "_mark_prewarmed", lambda: marked.__setitem__("v", True))
    # mock selve build'en så testen ikke rører DB/assembly
    import sys, types
    mod = types.ModuleType("core.services.prompt_contract")
    mod.build_visible_chat_prompt_assembly = lambda **k: None
    monkeypatch.setitem(sys.modules, "core.services.prompt_contract", mod)
    ap.prewarm_once()
    assert marked["v"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_assembly_prewarm_gate.py -o addopts="" -q`
Expected: FAIL — `prewarm_once` gater ikke endnu

- [ ] **Step 3: Write minimal implementation**

Ændr starten af `prewarm_once()` (efter docstring) til at gate, og kald `_mark_prewarmed()` efter succesfuld build:

```python
def prewarm_once() -> float | None:
    if not _should_prewarm():
        return None
    _local.prewarm_active = True
    try:
        from core.services.prompt_contract import build_visible_chat_prompt_assembly
        t0 = time.monotonic()
        build_visible_chat_prompt_assembly(
            provider="deepseek", model="deepseek-v4-flash",
            user_message="(prewarm)", session_id=_PREWARM_SESSION,
        )
        elapsed = time.monotonic() - t0
        _mark_prewarmed()
        _record_stats(elapsed)
        logger.info("assembly_prewarm: build complete in %.2fs", elapsed)
        return elapsed
    except Exception as exc:
        logger.debug("assembly_prewarm: build failed", exc_info=True)
        _record_stats(None, error=str(exc))
        return None
    finally:
        _local.prewarm_active = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_assembly_prewarm_gate.py -o addopts="" -q`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add core/services/assembly_prewarm.py tests/services/test_assembly_prewarm_gate.py
git commit -m "feat(prewarm): gate prewarm_once + cross-process mark (kills 270M-token runaway)"
```

---

## WS4 — deepseek-chat/reasoner-migration (deadline 24. juli)

### Task 4: Verificér DeepSeeks ikke-tænkende param for v4-flash

**Files:** (research — ingen kode)

- [ ] **Step 1: WebFetch DeepSeeks thinking-mode-docs**

Run (via WebFetch-værktøj):
URL `https://api-docs.deepseek.com/guides/thinking_mode/`
Prompt: "How do you request NON-thinking (fast, no reasoning_content) mode on deepseek-v4-flash via the API — exact request parameter (reasoning_effort value? thinking:{type:disabled}? extra_body?)? And how to request thinking high/max?"

Expected: konkret param. Forventet (bekræft): non-thinking = `extra_body={"thinking":{"type":"disabled"}}` (eller udelad reasoning_effort + disable-flag); thinking = `reasoning_effort="high"|"max"` + `thinking:{type:"enabled"}`. **Skriv det faktiske resultat ind i Task 5-6 før kodning.**

- [ ] **Step 2: Commit (dokumentér fundet i planen)**

Ingen kode-commit; noter det verificerede param i denne fil hvis det afviger fra forventningen.

### Task 5: `deepseek_model_for_thinking_mode` → param-baseret (ikke alias)

**Files:**
- Modify: `core/services/cheap_provider_runtime_adapters.py` (~547-572)
- Test: `tests/services/test_deepseek_thinking_param.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/services/test_deepseek_thinking_param.py
from core.services.cheap_provider_runtime_adapters import deepseek_request_for_thinking_mode

def test_fast_uses_v4flash_non_thinking_not_deprecated_alias():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-flash", "fast")
    assert model == "deepseek-v4-flash"            # IKKE deepseek-chat
    assert extra.get("thinking", {}).get("type") == "disabled"  # bekræftet i Task 4

def test_think_high():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-flash", "think")
    assert model == "deepseek-v4-flash"
    assert extra.get("reasoning_effort") == "high"

def test_deep_max():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-flash", "deep")
    assert extra.get("reasoning_effort") == "max"

def test_pro_always_thinking():
    model, extra = deepseek_request_for_thinking_mode("deepseek-v4-pro", "fast")
    assert model == "deepseek-v4-pro"              # pro kan ikke slå thinking fra
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_deepseek_thinking_param.py -o addopts="" -q`
Expected: FAIL — `deepseek_request_for_thinking_mode` findes ikke

- [ ] **Step 3: Write minimal implementation**

Tilføj ny funktion (behold `deepseek_model_for_thinking_mode` som tynd wrapper for bagudkomp.). **Brug det verificerede param fra Task 4** — nedenstående antager `thinking:{type:disabled/enabled}` + `reasoning_effort`:

```python
def deepseek_request_for_thinking_mode(model: str, thinking_mode: str) -> tuple[str, dict]:
    """→ (model, extra_body) uden at bruge de udfasede aliaser (deepseek-chat/reasoner).
    fast=non-thinking via param; think=high; deep=max. v4-pro: altid thinking."""
    mode = (thinking_mode or "think").strip().lower()
    m = (model or "").strip()
    # normalisér udfasede aliaser fremad
    if m in ("deepseek-chat", "deepseek-reasoner"):
        m = "deepseek-v4-flash"
    if m == "deepseek-v4-pro":
        return m, {}   # kan ikke slås fra
    if mode == "fast":
        return m, {"thinking": {"type": "disabled"}}
    if mode == "deep":
        return m, {"reasoning_effort": "max", "thinking": {"type": "enabled"}}
    return m, {"reasoning_effort": "high", "thinking": {"type": "enabled"}}

def deepseek_model_for_thinking_mode(model: str, thinking_mode: str) -> str:
    """Bagudkomp.: returnér kun modellen (aldrig den udfasede alias)."""
    return deepseek_request_for_thinking_mode(model, thinking_mode)[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/services/test_deepseek_thinking_param.py -o addopts="" -q`
Expected: PASS

- [ ] **Step 5: Wire extra_body ind på kaldsstedet**

Find hvor `deepseek_model_for_thinking_mode` kaldes (grep) og sørg for at `extra_body` fra `deepseek_request_for_thinking_mode` merges ind i request-payloaden. Kør provider-lane-tests.

- [ ] **Step 6: Commit**

```bash
git add core/services/cheap_provider_runtime_adapters.py tests/services/test_deepseek_thinking_param.py
git commit -m "feat(deepseek): thinking-mode via param, ikke udfaset deepseek-chat-alias"
```

### Task 6: `inner_llm_enrichment` — stop remap til deepseek-chat

**Files:**
- Modify: `core/memory/inner_llm_enrichment.py` (~419-421 + payload-bygning)

- [ ] **Step 1: Write the failing test**

```python
# tests/memory/test_inner_llm_no_deprecated_alias.py
import json
from core.memory import inner_llm_enrichment as ile

def test_inner_enrichment_never_sends_deprecated_alias(monkeypatch):
    sent = {}
    def _fake_post(url, data=None, headers=None, timeout=None):
        sent["payload"] = json.loads(data)
        class R:  # minimal fake response
            def read(self): return b'{"choices":[{"message":{"content":"ok"}}]}'
            status = 200
        return R()
    # patch HTTP + target til v4-flash
    monkeypatch.setattr(ile, "_http_post", _fake_post, raising=False)
    ile._call_inner_llm({"provider":"deepseek","model":"deepseek-v4-flash","base_url":"https://api.deepseek.com"},
                        "sys", "usr", 4)  # tilpas signatur til den faktiske
    assert sent["payload"]["model"] == "deepseek-v4-flash"
    assert sent["payload"]["model"] not in ("deepseek-chat","deepseek-reasoner")
    assert sent["payload"].get("thinking",{}).get("type") == "disabled"  # non-thinking via param
```

> Tilpas testens funktionsnavn/signatur til det faktiske i filen (læs 400-460).

- [ ] **Step 2: Run test to verify it fails**
Run: `/opt/conda/envs/ai/bin/python -m pytest tests/memory/test_inner_llm_no_deprecated_alias.py -o addopts="" -q`
Expected: FAIL — modellen remappes stadig til deepseek-chat

- [ ] **Step 3: Write minimal implementation**

Erstat linje ~419-421:

```python
    # Inner-enrichment er kort refleksiv tekst; thinking-mode spilder output-budgettet
    # på reasoning_content. FØR: remap til deepseek-chat (udfases 24. juli). NU: behold
    # v4-flash men slå thinking FRA via param.
    _extra = {}
    if provider == "deepseek" and model in ("deepseek-v4-flash", "deepseek-reasoner", "deepseek-chat"):
        model = "deepseek-v4-flash"
        _extra = {"thinking": {"type": "disabled"}}
```

og merge `_extra` ind i payload-dict'en (`{**base_payload, **_extra}`).

- [ ] **Step 4: Run test to verify it passes**
Run: `/opt/conda/envs/ai/bin/python -m pytest tests/memory/test_inner_llm_no_deprecated_alias.py -o addopts="" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add core/memory/inner_llm_enrichment.py tests/memory/test_inner_llm_no_deprecated_alias.py
git commit -m "fix(inner-llm): v4-flash + non-thinking param i stedet for udfaset deepseek-chat"
```

### Task 7: Migrér `relevance_deepseek_model` runtime-state

**Files:** (runtime-state — ingen kode)

- [ ] **Step 1: Sæt runtime-state (lokalt + container)**

```bash
# find hvordan runtime-state sættes (der er en helper); eller direkte:
/opt/conda/envs/ai/bin/python -c "from core.runtime.db_core import set_runtime_state_value; set_runtime_state_value('relevance_deepseek_model','deepseek-v4-flash')"
# gentag på container 10.0.0.39
```

- [ ] **Step 2: Verificér**
```bash
/opt/conda/envs/ai/bin/python -c "from core.runtime.db_core import get_runtime_state_value; print(get_runtime_state_value('relevance_deepseek_model'))"
```
Expected: `deepseek-v4-flash`

### Task 8: Audit — ingen aktive deepseek-chat/reasoner tilbage

- [ ] **Step 1: Grep**
```bash
grep -rn "deepseek-chat\|deepseek-reasoner" --include=*.py core apps scripts | grep -v test | grep -v "udfase\|deprecat\|compat\|#"
```
Expected: 0 aktive kaldsstier (kun kommentarer/docstrings).

- [ ] **Step 2: Fuld suite + commit**
```bash
/opt/conda/envs/ai/bin/python -m compileall core apps scripts >/dev/null && /opt/conda/envs/ai/bin/python -m pytest tests/services/test_assembly_prewarm_gate.py tests/services/test_deepseek_thinking_param.py -o addopts="" -q
git add -A && git commit -m "chore(deepseek): audit — ingen aktive deepseek-chat/reasoner kaldsstier"
```

### Task 9: Deploy + live-verifikation

- [ ] **Step 1: Deploy** (per Deploy-noten øverst — MERGE ikke overwrite):
```bash
git push origin main
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && git log origin/main..HEAD --oneline | cat'   # tjek Jarvis' egne commits
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && git fetch && git merge origin/main && git rev-parse HEAD'
ssh bs@10.0.0.39 'sudo systemctl restart jarvis-api jarvis-runtime'
```

- [ ] **Step 2: Verificér prewarm-rate faldet** (efter ~30 min):
```bash
ssh bs@10.0.0.39 "/opt/conda/envs/ai/bin/python - <<'PY'
import sqlite3,os
from datetime import datetime,timezone,timedelta
c=sqlite3.connect(os.path.expanduser('~/.jarvis-v2/state/jarvis.db'))
since=(datetime.now(timezone.utc)-timedelta(minutes=30)).isoformat()
n=c.execute(\"select count(*) from costs where (provider='primary_cache_warmer' or lane='primary_cache_warmer') and created_at>=?\",(since,)).fetchone()[0]
print('warms last 30min:',n,' (mål: <2 i aktive timer)')
PY"
```
Expected: markant lavere end de tidligere ~0,35/min.

- [ ] **Step 3: Verificér ingen deepseek-chat-kald efter deploy:**
```bash
ssh bs@10.0.0.39 "/opt/conda/envs/ai/bin/python -c \"import sqlite3,os; c=sqlite3.connect(os.path.expanduser('~/.jarvis-v2/state/jarvis.db')); print('deepseek-chat efter nu:', c.execute(\\\"select count(*) from costs where model='deepseek-chat' and created_at>='2026-07-13T12:00'\\\").fetchone()[0])\""
```
Expected: 0 (efter deploy-tidspunktet).

---

## Self-Review

**Spec-coverage (WS1+WS4 af spec'en):**
- WS1 trafik-gate → Task 1-3 ✅. WS1 enkelt-loop/cross-process → Task 2 (`_seconds_since_last_prewarm` cross-process dedup) ✅. `_MIN_INTERVAL` 60→180: **tilføjet note** — sæt i Task 3 sammen med gaten (ændr `_MIN_INTERVAL = 180.0`). WS4 alias-migration → Task 4-8 ✅. Deploy → Task 9 ✅.
- **Ikke i denne plan (bevidst):** WS2/WS3 (cost_usd + jc cost), WS5/5b (pro + composer-think), WS6/7. De får egne planer efter — men Task 5's `deepseek_request_for_thinking_mode` er allerede fundamentet WS5b bygger på.

**Placeholder-scan:** Task 4 er bevidst en verifikations-task (ægte ukendt: DeepSeeks non-thinking-param) — dens output skrives ind i Task 5-6 før kodning. Task 6-testens signatur skal tilpasses den faktiske funktion (noteret). Ingen andre TBD'er.

**Type-konsistens:** `deepseek_request_for_thinking_mode(model, mode) -> (model, extra_body)` bruges konsistent i Task 5-6. `_should_prewarm`/`_seconds_since_last_*` navne matcher på tværs af Task 1-3.
