# Fase A1 — agent_step cache-sentinel-split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development eller executing-plans.

**Goal:** Lade `/v1/agent/step` (ctx=full) honorere `DYNAMIC_TAIL_SENTINEL` — flyt den volatile assembly-hale fra systemhovedet til EFTER samtalen — så `[stabilt system + samtale]` bliver et cacheligt prefix. Fikser 25s-cachen på attached/store sessioner. Flag-gated (default OFF = byte-identisk).

**Architecture:** `_full_context` returnerer allerede `.text` med sentinel'en bagt ind (fra `build_visible_chat_prompt_assembly`), men agent_step ignorerer den i dag. Vi tilføjer en ren splitter der, når flag ON og sentinel'en er til stede i system-beskeden, klipper systemet ved sentinel'en og appender halen til den sidste user-besked (spejler `visible_model._build_visible_input`). Nul-risiko: flag OFF eller ingen sentinel → chat_messages uændret.

**Tech Stack:** Python 3.11, pytest. Runner: `/opt/conda/envs/ai/bin/python -m pytest`.

## File Structure
- `apps/api/jarvis_api/routes/agent_loop.py` — tilføj `_apply_dynamic_tail_split()` + kald i handler (~linje 796-800, hvor `chat_messages = [system] + client_messages` bygges). Ny settings-flag `agent_step_cache_split_enabled` (default False).
- `core/runtime/settings.py` — flag-felt.
- `tests/test_agent_step_cache_split.py` — nye tests.

Baggrund (nuværende, agent_loop.py:796-800):
```python
chat_messages: list[dict[str, Any]] = [
    {"role": "system", "content": _build_system_prompt(context, _last_user, _ws_name, env=env)}]
chat_messages.extend(client_messages)
```
`DYNAMIC_TAIL_SENTINEL = "⟦◆DYNAMIC-TAIL-DO-NOT-CACHE◆⟧"` importeres fra `core.services.prompt_contract`.

---

### Task 1: `_apply_dynamic_tail_split()` splitter

**Files:**
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` (tilføj funktion nær `_build_system_prompt`)
- Test: `tests/test_agent_step_cache_split.py`

- [ ] **Step 1: Write the failing test**

Opret `tests/test_agent_step_cache_split.py`:
```python
from apps.api.jarvis_api.routes.agent_loop import _apply_dynamic_tail_split
from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL as S


def test_split_moves_tail_to_last_user_when_enabled():
    msgs = [
        {"role": "system", "content": f"STABLE HEAD{S}VOLATILE TAIL"},
        {"role": "user", "content": "hej"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "hvad nu"},
    ]
    out = _apply_dynamic_tail_split(msgs, enabled=True)
    assert out[0]["content"] == "STABLE HEAD"          # hoved uden sentinel/hale
    assert out[-1]["content"].startswith("hvad nu")     # halen på SIDSTE user
    assert "VOLATILE TAIL" in out[-1]["content"]
    assert S not in out[0]["content"]                    # sentinel fjernet fra hoved


def test_off_is_byte_identical():
    msgs = [
        {"role": "system", "content": f"HEAD{S}TAIL"},
        {"role": "user", "content": "u"},
    ]
    out = _apply_dynamic_tail_split(msgs, enabled=False)
    assert out == msgs                                    # uændret


def test_no_sentinel_is_byte_identical():
    msgs = [
        {"role": "system", "content": "no sentinel here"},
        {"role": "user", "content": "u"},
    ]
    out = _apply_dynamic_tail_split(msgs, enabled=True)
    assert out == msgs


def test_no_user_message_keeps_tail_in_system():
    # fallback: uden en user-besked at hænge halen på, forbliver den (uden sentinel) i system
    msgs = [{"role": "system", "content": f"HEAD{S}TAIL"}]
    out = _apply_dynamic_tail_split(msgs, enabled=True)
    assert out[0]["content"] == "HEADTAIL"
    assert S not in out[0]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_step_cache_split.py -o addopts="" -q`
Expected: FAIL med `ImportError: cannot import name '_apply_dynamic_tail_split'`

- [ ] **Step 3: Write minimal implementation**

I `apps/api/jarvis_api/routes/agent_loop.py`, tilføj efter `_build_system_prompt`:
```python
def _apply_dynamic_tail_split(chat_messages: list[dict], enabled: bool) -> list[dict]:
    """Fase A1: honorér DYNAMIC_TAIL_SENTINEL i system-beskeden — klip systemet ved
    sentinel'en (stabilt cacheligt hoved) og flyt den volatile hale til den SIDSTE
    user-besked, så [stabilt system + samtale] forbliver et cache-stabilt prefix
    (spejler visible_model._build_visible_input). enabled=False eller ingen sentinel
    → chat_messages returneres byte-identisk. Uden en user-besked at hænge halen på
    beholdes halen (uden sentinel) i systemet (fallback — aldrig tab)."""
    if not enabled or not chat_messages:
        return chat_messages
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL
    sys_msg = chat_messages[0]
    if sys_msg.get("role") != "system":
        return chat_messages
    content = str(sys_msg.get("content") or "")
    if DYNAMIC_TAIL_SENTINEL not in content:
        return chat_messages
    head, _, tail = content.partition(DYNAMIC_TAIL_SENTINEL)
    out = [dict(m) for m in chat_messages]
    out[0]["content"] = head
    last_user_idx = next((i for i in range(len(out) - 1, -1, -1)
                          if out[i].get("role") == "user"), None)
    if last_user_idx is None:
        out[0]["content"] = head + tail  # fallback: ingen user → behold hale i system
        return out
    out[last_user_idx] = dict(out[last_user_idx])
    out[last_user_idx]["content"] = str(out[last_user_idx].get("content") or "") + tail
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_step_cache_split.py -o addopts="" -q`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
cd /media/projects/jarvis-v2 && git add apps/api/jarvis_api/routes/agent_loop.py tests/test_agent_step_cache_split.py
git commit -m "feat(agent-step): Fase A1 — dynamic-tail cache-split helper (ren funktion)"
```

---

### Task 2: Flag + wiring i agent_step-handler

**Files:**
- Modify: `core/runtime/settings.py` (flag `agent_step_cache_split_enabled`, default False)
- Modify: `apps/api/jarvis_api/routes/agent_loop.py` (kald splitteren efter chat_messages bygges)
- Test: `tests/test_agent_step_cache_split.py`

- [ ] **Step 1: Write the failing test**

Tilføj til `tests/test_agent_step_cache_split.py`:
```python
def test_settings_has_cache_split_flag_default_false():
    from core.runtime.settings import load_settings
    s = load_settings()
    assert hasattr(s, "agent_step_cache_split_enabled")
    assert s.agent_step_cache_split_enabled is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_step_cache_split.py::test_settings_has_cache_split_flag_default_false -o addopts="" -q`
Expected: FAIL (attribut mangler)

- [ ] **Step 3: Write minimal implementation**

I `core/runtime/settings.py`, tilføj feltet ved siden af de øvrige `agent_step_*`-flags (søg `agent_step_cache_contract_enabled` og spejl mønsteret: dataclass-felt default False + to-dict + from-dict rund-tur). Præcist felt:
```python
    agent_step_cache_split_enabled: bool = False
```
og i `to_dict`/`from_dict` (samme sted som `agent_step_cache_contract_enabled`):
```python
        "agent_step_cache_split_enabled": self.agent_step_cache_split_enabled,
```
```python
        agent_step_cache_split_enabled=bool(data.get("agent_step_cache_split_enabled", False)),
```

I `apps/api/jarvis_api/routes/agent_loop.py`, lige efter `chat_messages.extend(client_messages)` (~linje 800):
```python
    chat_messages = _apply_dynamic_tail_split(
        chat_messages, enabled=settings.agent_step_cache_split_enabled)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_agent_step_cache_split.py -o addopts="" -q`
Expected: PASS (5 tests)

- [ ] **Step 5: Verify no behavior change with flag off**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/ -o addopts="" -q -k "agent_step or agent_loop"`
Expected: PASS — flag default False → chat_messages uændret → eksisterende agent_step-tests grønne.

- [ ] **Step 6: Commit**

```bash
cd /media/projects/jarvis-v2 && git add core/runtime/settings.py apps/api/jarvis_api/routes/agent_loop.py tests/test_agent_step_cache_split.py
git commit -m "feat(agent-step): Fase A1 — wire cache-split bag agent_step_cache_split_enabled (default off)"
```

---

## Self-Review
**1. Spec coverage:** Delt-substrat-spec §3(1) "cache-sentinel-split (fikser 25s)" → Task 1 (splitter) + Task 2 (flag+wiring). Byte-identisk-når-off → test_off + test_no_sentinel + flag default False.
**2. Placeholder scan:** Ingen TBD; al kode vist. Settings-mønster refererer eksisterende `agent_step_cache_contract_enabled` (verificér præcis linje ved eksekvering).
**3. Type consistency:** `_apply_dynamic_tail_split(chat_messages: list, enabled: bool) -> list` bruges konsistent; flag-navn `agent_step_cache_split_enabled` ens i settings + handler + test.

**Måling efter:** når flippet ON på container, mål cache_hit_tokens før/efter på en stor session (forventet fald i miss + latency mod ~7-8s) — det er beviset spec §6 kræver.
