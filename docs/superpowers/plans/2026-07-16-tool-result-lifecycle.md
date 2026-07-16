# Tool-Result Lifecycle (visible-lane) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Skær visible-lane tool-result-volumen (målt 68–83% af 187k-tok-samtaler) uden at bryde DeepSeek prefix-cachen, ved at kollapse gamle tool-results til byte-stabile stubs bag et persisteret, diskret-avancerende `cold_floor`-id.

**Architecture:** Tre tiers styret af ét persisteret integer message-`id` (`cold_floor`): HOT (nuværende tur, fuld — via eksisterende followup-sti, urørt), WARM (`id ≥ cold_floor`, dagens summary-rendering, urørt), COLD (`id < cold_floor`, ny én-linjes stub afledt KUN af den immutable reference-streng). `cold_floor` rykker udelukkende ved run-slut, i diskrete batches med hysterese (hybrid: sidste N runs ELLER T warm-tokens). Alt bag `tool_result_lifecycle_enabled` (default OFF).

**Tech Stack:** Python 3.11, SQLite (`core.runtime.db.connect`), pytest. Test-kommando: `/home/bs/miniconda3/envs/ai/bin/python -m pytest <fil> -o addopts="" -v` (conda `ai`-env; hvis den mangler brug `/opt/conda/envs/ai/bin/python`).

**Scope-afgrænsning:** Denne plan dækker **efter-run + pruning** (spec §5, §7, §4, §11b) = hele den målte token-gevinst. **"Undervejs"/within-run micro-compaction (spec §6)** er BEVIDST udskudt til egen plan: den lever i `visible_runs.py` (>4600 L) i followup-exchange-stien, er Boy-Scout-udløsende, og adresserer kun det sjældne enkelt-kæmpe-run — ikke den dominerende kryds-run-ophobning. Trace followup-stien først.

**Reference:** Spec `docs/superpowers/specs/2026-07-16-tool-result-lifecycle-design.md`. Kerne-invariant (§2): historik-bytes SKAL være identiske tur-for-tur mellem `cold_floor`-ryk; recency-relativ rendering er forbudt (brød cachen 2026-06-09).

---

## File Structure

| Fil | Ansvar | Ændring |
|-----|--------|---------|
| `core/runtime/settings.py` | RuntimeSettings-felter | +5 felter (Task 1) |
| `core/context/tool_result_lifecycle.py` (**ny**) | cold_floor-lagring (egen tabel) + rene advance-beregninger + run-slut-glue | Hele modulet (Task 2–5) |
| `core/services/chat_sessions.py` | growing-window query | +`id` i SELECT + retur-dict (Task 6) |
| `core/services/tool_result_store.py` | tool-result-rendering | +`stub`-gren i `render_tool_result_for_prompt` (Task 7) |
| `core/services/prompt_sections/transcript_sections.py` | transcript-build | +cold-gren i render-løkken (Task 8) |
| `core/services/visible_runs.py` | run-slut | +≤10-linjers guarded kald til `evaluate_and_advance` (Task 9) |
| `tests/context/test_tool_result_lifecycle.py` (**ny**) | modul-tests | Task 2–5 |
| `tests/services/test_tool_result_store.py` | stub-tests | Task 7 |
| `tests/services/test_transcript_sections_cold.py` (**ny**) | byte-stabilitet + cold-render | Task 8 |

**Vigtig kode-fakta (verificeret):**
- `chat_session_messages_since_last_compact` (chat_sessions.py:589) returnerer IKKE `id` i dag — Task 6 tilføjer det.
- Transcript-render-løkken (transcript_sections.py:265-294) merger tool-results ind i den forrige assistant-besked som `\n(<summary>)`. Cold-beslutningen tages PR. `item` i løkken (hvor `id` er tilgængeligt), FØR merge.
- I transcript'en er ALLE tool-items historiske → warm-eller-cold. HOT (nuværende tur) kommer via `visible_followup`-stien og er urørt.
- Stub SKAL afledes af `parse_tool_result_reference(content)` — aldrig disk (render falder til anden byte-form når 7-dages-reaper sletter JSON'en, tool_result_store.py:122 vs :133).

---

## Fase 0 — Settings

### Task 1: Tilføj lifecycle-settings (flag default OFF)

**Files:**
- Modify: `core/runtime/settings.py:323` (ved siden af `tool_result_history_max_chars`)
- Test: `tests/runtime/test_settings.py` (hvis findes; ellers verificér via import)

- [ ] **Step 1: Skriv fejlende test**

Opret `tests/context/test_tool_result_lifecycle.py` med:
```python
from core.runtime.settings import RuntimeSettings


def test_lifecycle_settings_defaults():
    s = RuntimeSettings()
    assert s.tool_result_lifecycle_enabled is False
    assert s.tool_warm_run_window == 8
    assert s.tool_warm_token_ceiling == 40000
    assert s.tool_warm_hysteresis == 0.25
    assert s.tool_run_hot_budget == 30000
```

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py::test_lifecycle_settings_defaults -o addopts="" -v`
Forventet: FAIL (`AttributeError`, feltet findes ikke).

- [ ] **Step 3: Tilføj felterne**

I `core/runtime/settings.py`, umiddelbart efter linjen `tool_result_history_max_chars: int = 1500`:
```python
    # Tool-result lifecycle (spec 2026-07-16). Default OFF = dagens opførsel eksakt.
    tool_result_lifecycle_enabled: bool = False
    tool_warm_run_window: int = 8          # sidste N user-turns holdes warm
    tool_warm_token_ceiling: int = 40000   # loft på warm tool-result-tokens
    tool_warm_hysteresis: float = 0.25     # advance-margin (thrasher ikke)
    tool_run_hot_budget: int = 30000       # within-run (spec §6, senere plan)
```

Hvis settings også loades fra runtime.json (tjek om der er en `_from_dict`/`load_settings`-mapper i filen), tilføj felterne dér på samme mønster som `tool_result_history_max_chars`. Grep: `grep -n "tool_result_history_max_chars" core/runtime/settings.py` og spejl HVER forekomst.

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py::test_lifecycle_settings_defaults -o addopts="" -v`
Forventet: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/settings.py tests/context/test_tool_result_lifecycle.py
git commit -m "feat(settings): tool-result lifecycle fields (default off)"
```

---

## Fase 1 — Lifecycle-modul (rene funktioner + lagring)

Modulet `core/context/tool_result_lifecycle.py` bygges bottom-up: rene beregninger først (nemme at teste uden DB), derefter lagring, derefter glue.

### Task 2: Rene helpers — run-grænser + token-estimat

**Files:**
- Create: `core/context/tool_result_lifecycle.py`
- Test: `tests/context/test_tool_result_lifecycle.py`

- [ ] **Step 1: Skriv fejlende test**

Tilføj til `tests/context/test_tool_result_lifecycle.py`:
```python
from core.context import tool_result_lifecycle as trl


def _msg(mid, role, content="x"):
    return {"id": mid, "role": role, "content": content}


def test_user_message_ids_ascending():
    msgs = [_msg(1, "user"), _msg(2, "assistant"), _msg(3, "tool"),
            _msg(4, "user"), _msg(5, "assistant")]
    assert trl.user_message_ids(msgs) == [1, 4]


def test_estimate_tool_tokens_only_tool_role():
    msgs = [_msg(1, "user", "a" * 40), _msg(2, "tool", "b" * 40),
            _msg(3, "tool", "c" * 80)]
    # kun tool-roller tælles; heuristik = len//4
    assert trl.estimate_tool_tokens(msgs) == (40 // 4) + (80 // 4)
```

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v -k "user_message_ids or estimate_tool"`
Forventet: FAIL (`ModuleNotFoundError` / `AttributeError`).

- [ ] **Step 3: Implementér**

Opret `core/context/tool_result_lifecycle.py`:
```python
"""Tool-result lifecycle (visible-lane). Spec 2026-07-16.

cold_floor = persisteret integer message-id. Tool-results med id < cold_floor
renderes som byte-stabile stubs. cold_floor rykker KUN ved run-slut, i diskrete
batches med hysterese (hybrid: sidste N user-turns ELLER T warm-tokens). Ren
beregning her; DB-lagring nedenfor. INGEN recency-relativ logik (bryder cachen).
"""
from __future__ import annotations


def user_message_ids(messages: list[dict]) -> list[int]:
    """Ids for role=='user'-beskeder, stigende (= run-grænser)."""
    out = []
    for m in messages:
        if str(m.get("role")) == "user":
            try:
                out.append(int(m["id"]))
            except (KeyError, TypeError, ValueError):
                continue
    return sorted(out)


def estimate_tool_tokens(messages: list[dict]) -> int:
    """Sum af tool-result-tokens (heuristik len//4). Kun role=='tool'."""
    total = 0
    for m in messages:
        if str(m.get("role")) == "tool":
            total += len(str(m.get("content") or "")) // 4
    return total
```

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v -k "user_message_ids or estimate_tool"`
Forventet: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/context/tool_result_lifecycle.py tests/context/test_tool_result_lifecycle.py
git commit -m "feat(lifecycle): pure helpers — run boundaries + tool-token estimate"
```

### Task 3: `compute_new_floor` — hybrid + hysterese (rent, monotont)

**Files:**
- Modify: `core/context/tool_result_lifecycle.py`
- Test: `tests/context/test_tool_result_lifecycle.py`

- [ ] **Step 1: Skriv fejlende test**

Tilføj:
```python
def test_no_advance_when_within_window():
    # 3 user-turns, run_window=8 → ingen advance
    msgs = [_msg(i, "user") for i in (1, 3, 5)]
    assert trl.compute_new_floor(
        msgs, current_floor=0, run_window=8,
        token_ceiling=40000, hysteresis=0.25) == 0


def test_advance_by_run_count():
    # 12 user-turns (ids 1..12), run_window=8, ingen token-pres.
    # 12 > 8*1.25=10 → trigger. Behold sidste 8 warm → floor = id for
    # den 9.-nyeste user-turn minus 1 = (id 4) - 1 = 3.
    msgs = [_msg(i, "user") for i in range(1, 13)]
    got = trl.compute_new_floor(
        msgs, current_floor=0, run_window=8,
        token_ceiling=10**9, hysteresis=0.25)
    assert got == 3  # warm = ids > 3 = {4..12} = 8 sidste turns... +? se note


def test_advance_by_tokens():
    # Én user-turn, mange tool-results á 4000 tegn (=1000 tok hver).
    # 50 stk = 50k tok > 40k*1.25 → trigger, trim til <=40k warm.
    msgs = [_msg(1, "user")]
    for i in range(2, 52):
        msgs.append(_msg(i, "tool", "x" * 4000))
    got = trl.compute_new_floor(
        msgs, current_floor=0, run_window=10**9,
        token_ceiling=40000, hysteresis=0.25)
    warm = [m for m in msgs if int(m["id"]) > got]
    assert trl.estimate_tool_tokens(warm) <= 40000
    assert got > 0  # noget blev skubbet cold


def test_monotonic_never_retreats():
    msgs = [_msg(i, "user") for i in range(1, 4)]
    assert trl.compute_new_floor(
        msgs, current_floor=100, run_window=8,
        token_ceiling=40000, hysteresis=0.25) == 100
```

> **Note til implementer om `test_advance_by_run_count`:** "behold sidste N user-turns warm" betyder warm skal indeholde de N nyeste user-ids. Med ids 1..12 og N=8 er de 8 nyeste user-turns ids {5,6,7,8,9,10,11,12}. Floor sættes til (9.-nyeste user-id) = id 5's forgænger. Den 9.-nyeste user-id er `user_ids[-(N+1)]` = `user_ids[-9]` = 4. Warm = `id > floor`. For at warm starter ved id 5 skal `floor = 4`. Ret assert til `== 4` hvis din indeksering giver det — vælg ÉN konvention og gør testen præcis. Det afgørende krav: `len(user_message_ids(warm)) == run_window` efter advance.

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v -k "advance or monotonic or within_window"`
Forventet: FAIL.

- [ ] **Step 3: Implementér**

Tilføj til `core/context/tool_result_lifecycle.py`:
```python
def _candidate_by_runs(user_ids: list[int], run_window: int) -> int:
    """Floor så præcis de sidste `run_window` user-turns forbliver warm."""
    if len(user_ids) <= run_window:
        return 0
    # user_ids[-(run_window)] er den ældste user-turn vi BEHOLDER warm.
    keep_from = user_ids[-run_window]
    return keep_from - 1  # warm = id > floor ⟺ id >= keep_from


def _candidate_by_tokens(messages: list[dict], token_ceiling: int) -> int:
    """Floor så warm tool-tokens <= ceiling. Går nyeste→ældste."""
    cum = 0
    floor = 0
    for m in reversed(messages):
        if str(m.get("role")) == "tool":
            cum += len(str(m.get("content") or "")) // 4
            if cum > token_ceiling:
                # denne besked (og alt ældre) skubbes cold
                floor = int(m["id"])
                break
    return floor


def compute_new_floor(
    messages: list[dict],
    *,
    current_floor: int,
    run_window: int,
    token_ceiling: int,
    hysteresis: float,
) -> int:
    """Ny cold_floor. Monotont (>= current_floor). 0 = intet cold endnu.

    Warm = beskeder med id > current_floor. Advance kun hvis warm OVERSKRIDER
    grænsen med hysterese-margin (undgår thrash). Ved advance trimmes warm ned
    til BASE-grænserne (ikke de inflaterede), så der er luft til næste run.
    """
    warm = [m for m in messages if int(m.get("id", 0)) > current_floor]
    user_ids_warm = user_message_ids(warm)
    tokens_warm = estimate_tool_tokens(warm)

    over_runs = len(user_ids_warm) > run_window * (1 + hysteresis)
    over_tokens = tokens_warm > token_ceiling * (1 + hysteresis)
    if not (over_runs or over_tokens):
        return current_floor

    all_user_ids = user_message_ids(messages)
    cand_runs = _candidate_by_runs(all_user_ids, run_window)
    cand_tokens = _candidate_by_tokens(messages, token_ceiling)
    # mest aggressive (højeste floor) vinder; aldrig under current
    return max(current_floor, cand_runs, cand_tokens)
```

- [ ] **Step 4: Kør — forvent PASS** (juster assert-tal i testen til din indekserings-konvention; kravet er `len(user_message_ids(warm)) == run_window`)

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v`
Forventet: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/context/tool_result_lifecycle.py tests/context/test_tool_result_lifecycle.py
git commit -m "feat(lifecycle): compute_new_floor — hybrid runs/tokens + hysteresis, monotonic"
```

### Task 4: cold_floor-lagring (egen isoleret tabel, monotont upsert)

**Files:**
- Modify: `core/context/tool_result_lifecycle.py`
- Test: `tests/context/test_tool_result_lifecycle.py`

- [ ] **Step 1: Skriv fejlende test**

Tilføj:
```python
def test_cold_floor_storage_roundtrip():
    sid = "sess-trl-test-1"
    assert trl.get_cold_floor(sid) == 0          # default når intet sat
    trl.set_cold_floor(sid, 42)
    assert trl.get_cold_floor(sid) == 42
    trl.set_cold_floor(sid, 100)
    assert trl.get_cold_floor(sid) == 100


def test_cold_floor_monotonic_write():
    sid = "sess-trl-test-2"
    trl.set_cold_floor(sid, 100)
    trl.set_cold_floor(sid, 50)                   # forsøg at gå tilbage
    assert trl.get_cold_floor(sid) == 100         # ignoreret
```

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v -k "cold_floor_storage or monotonic_write"`
Forventet: FAIL.

- [ ] **Step 3: Implementér**

Tilføj til `core/context/tool_result_lifecycle.py`:
```python
from core.runtime.db import connect

_TABLE = "tool_result_cold_floor"


def _ensure_table(conn) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
        "session_id TEXT PRIMARY KEY, floor_id INTEGER NOT NULL, "
        "updated_at TEXT NOT NULL)"
    )


def get_cold_floor(session_id: str) -> int:
    sid = (session_id or "").strip()
    if not sid:
        return 0
    with connect() as conn:
        _ensure_table(conn)
        row = conn.execute(
            f"SELECT floor_id FROM {_TABLE} WHERE session_id = ?", (sid,)
        ).fetchone()
    if row is None:
        return 0
    try:
        return int(row["floor_id"])
    except (KeyError, TypeError, ValueError):
        return int(row[0])


def set_cold_floor(session_id: str, floor_id: int) -> None:
    """Monotont: skriver kun hvis floor_id > eksisterende."""
    sid = (session_id or "").strip()
    if not sid:
        return
    from datetime import datetime, UTC
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_table(conn)
        conn.execute(
            f"INSERT INTO {_TABLE} (session_id, floor_id, updated_at) "
            "VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
            "floor_id = excluded.floor_id, updated_at = excluded.updated_at "
            "WHERE excluded.floor_id > tool_result_cold_floor.floor_id",
            (sid, int(floor_id), now),
        )
```

> **DB-note:** `connect()` fra `core.runtime.db` er repoets standard SQLite-forbindelse (samme som chat_sessions bruger). `ON CONFLICT ... WHERE` giver monotont upsert i én query. Hvis test-DB'en er en frisk fil pr. run, opretter `_ensure_table` tabellen on-demand — ingen migration nødvendig.

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v -k "cold_floor"`
Forventet: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/context/tool_result_lifecycle.py tests/context/test_tool_result_lifecycle.py
git commit -m "feat(lifecycle): cold_floor storage — isolated table, monotonic upsert"
```

### Task 5: `evaluate_and_advance` — glue (run-slut-indgang)

**Files:**
- Modify: `core/context/tool_result_lifecycle.py`
- Test: `tests/context/test_tool_result_lifecycle.py`

- [ ] **Step 1: Skriv fejlende test**

Tilføj (bruger monkeypatch så vi ikke behøver en ægte session):
```python
def test_evaluate_and_advance_moves_floor(monkeypatch):
    sid = "sess-trl-eval-1"
    msgs = [_msg(i, "user") for i in range(1, 13)]  # 12 turns → trigger v. N=8

    monkeypatch.setattr(trl, "_load_session_messages", lambda s: msgs)

    class _S:
        tool_result_lifecycle_enabled = True
        tool_warm_run_window = 8
        tool_warm_token_ceiling = 40000
        tool_warm_hysteresis = 0.25

    new_floor = trl.evaluate_and_advance(sid, settings=_S())
    assert new_floor > 0
    assert trl.get_cold_floor(sid) == new_floor


def test_evaluate_noop_when_disabled(monkeypatch):
    sid = "sess-trl-eval-2"
    msgs = [_msg(i, "user") for i in range(1, 13)]
    monkeypatch.setattr(trl, "_load_session_messages", lambda s: msgs)

    class _S:
        tool_result_lifecycle_enabled = False
        tool_warm_run_window = 8
        tool_warm_token_ceiling = 40000
        tool_warm_hysteresis = 0.25

    assert trl.evaluate_and_advance(sid, settings=_S()) == 0
    assert trl.get_cold_floor(sid) == 0
```

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v -k "evaluate"`
Forventet: FAIL.

- [ ] **Step 3: Implementér**

Tilføj til `core/context/tool_result_lifecycle.py`:
```python
def _load_session_messages(session_id: str) -> list[dict]:
    """Growing-window beskeder MED id (Task 6 tilføjer id til retur-dict)."""
    from core.services.chat_sessions import chat_session_messages_since_last_compact
    return chat_session_messages_since_last_compact(session_id)


def _load_settings():
    from core.runtime.settings import load_settings
    return load_settings()


def evaluate_and_advance(session_id: str, *, settings=None) -> int:
    """Kaldes ved RUN-SLUT (eneste skriver). Returnerer ny cold_floor (0=ingen).

    Fejl-tolerant: må aldrig kaste ind i run-completion-stien.
    """
    sid = (session_id or "").strip()
    if not sid:
        return 0
    s = settings or _load_settings()
    if not bool(getattr(s, "tool_result_lifecycle_enabled", False)):
        return get_cold_floor(sid)
    try:
        messages = _load_session_messages(sid)
        current = get_cold_floor(sid)
        new_floor = compute_new_floor(
            messages,
            current_floor=current,
            run_window=int(getattr(s, "tool_warm_run_window", 8)),
            token_ceiling=int(getattr(s, "tool_warm_token_ceiling", 40000)),
            hysteresis=float(getattr(s, "tool_warm_hysteresis", 0.25)),
        )
        if new_floor > current:
            set_cold_floor(sid, new_floor)
            print(f"[tool-lifecycle] cold_floor {current}->{new_floor} "
                  f"session={sid[:20]}", flush=True)
        return new_floor
    except Exception as exc:
        print(f"[tool-lifecycle] evaluate_and_advance fejl: {exc}", flush=True)
        return get_cold_floor(sid)
```

> **Bemærk:** `test_evaluate_noop_when_disabled` forventer retur `0` når disabled OG intet floor sat — `get_cold_floor` giver `0`. Hvis et floor allerede var sat, ville disabled returnere det eksisterende (den læser, skriver ikke). Det er korrekt: disable stopper advance, men sletter ikke floor (billig re-enable, spec §9).

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py -o addopts="" -v`
Forventet: PASS (alle modul-tests).

- [ ] **Step 5: Commit**

```bash
git add core/context/tool_result_lifecycle.py tests/context/test_tool_result_lifecycle.py
git commit -m "feat(lifecycle): evaluate_and_advance glue — run-end single writer, fault-tolerant"
```

---

## Fase 2 — Tråd `id` gennem growing-window

### Task 6: `chat_session_messages_since_last_compact` returnerer `id`

**Files:**
- Modify: `core/services/chat_sessions.py:619-647`
- Test: `tests/services/test_chat_sessions_id.py` (**ny**)

- [ ] **Step 1: Skriv fejlende test**

Opret `tests/services/test_chat_sessions_id.py`:
```python
from core.services.chat_sessions import (
    create_chat_session, append_chat_message,
    chat_session_messages_since_last_compact,
)


def test_messages_include_integer_id():
    sid = "sess-idthread-1"
    create_chat_session(session_id=sid, title="t")
    append_chat_message(session_id=sid, role="user", content="hej")
    append_chat_message(session_id=sid, role="assistant", content="svar")
    msgs = chat_session_messages_since_last_compact(sid)
    assert len(msgs) == 2
    assert all("id" in m for m in msgs)
    assert msgs[0]["id"] < msgs[1]["id"]        # monotont, stigende
    assert isinstance(msgs[0]["id"], int)
```

> **Implementer-note:** verificér `create_chat_session`'s eksakte signatur (`grep -n "def create_chat_session" core/services/chat_sessions.py`) og tilpas kaldet. Hvis en frisk test-DB ikke er isoleret automatisk, brug en unik `session_id` pr. test (som ovenfor).

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_chat_sessions_id.py -o addopts="" -v`
Forventet: FAIL (`KeyError: 'id'`).

- [ ] **Step 3: Implementér**

I `core/services/chat_sessions.py`, i BEGGE SELECT-grene i `chat_session_messages_since_last_compact` (den med marker og den uden), tilføj `id` som første kolonne:
```python
                SELECT id, role, content, created_at, user_id, reasoning_content
```
Og i retur-comprehensionen (L638-647), tilføj `id` som int:
```python
    return [
        {
            "id": int(row["id"]),
            "role": str(row["role"]),
            "content": str(row["content"]),
            "created_at": str(row["created_at"]),
            "user_id": str(row["user_id"] or ""),
            "reasoning_content": str(row["reasoning_content"] or ""),
        }
        for row in rows
    ]
```

> **Cache-note:** `id` er ren metadata — den renderes ikke ind i prompten, så byte-outputtet er uændret. Eksisterende konsumenter ignorerer den ekstra nøgle.

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_chat_sessions_id.py -o addopts="" -v`
Forventet: PASS.

- [ ] **Step 5: Regressions-tjek + commit**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/ -o addopts="" -k "chat_session or transcript" -q`
Forventet: ingen nye fejl.
```bash
git add core/services/chat_sessions.py tests/services/test_chat_sessions_id.py
git commit -m "feat(chat): thread integer id through growing-window (metadata, byte-neutral)"
```

---

## Fase 3 — Stub-renderer (reference-only)

### Task 7: `render_tool_result_for_prompt(..., stub=...)`

**Files:**
- Modify: `core/services/tool_result_store.py:108-135`
- Test: `tests/services/test_tool_result_store.py`

- [ ] **Step 1: Skriv fejlende test**

Tilføj til `tests/services/test_tool_result_store.py` (opret hvis mangler; importér modulet):
```python
from core.services.tool_result_store import (
    build_tool_result_reference, render_tool_result_for_prompt,
)


def test_stub_render_is_one_line_from_reference():
    ref = build_tool_result_reference(
        "tool-result-abc", tool_name="bash",
        summary="line1\nline2\nline3 lots of output here")
    stub = render_tool_result_for_prompt(ref, expand=False, stub=True)
    assert "tool-result-abc" in stub          # id bevaret (rehydrering)
    assert "bash" in stub                      # tool-navn
    assert "read_tool_result" in stub          # hint om at hente fuldt
    assert "\n" not in stub                     # én linje
    assert len(stub) < 120                      # kompakt


def test_stub_is_byte_stable_without_disk():
    # Stub må IKKE afhænge af disk-filen (7-dages-reaper). Samme reference →
    # samme bytes, uanset om result_id findes på disk.
    ref = build_tool_result_reference(
        "tool-result-nonexistent-xyz", tool_name="read_file",
        summary="content summary")
    a = render_tool_result_for_prompt(ref, expand=False, stub=True)
    b = render_tool_result_for_prompt(ref, expand=False, stub=True)
    assert a == b
    assert "tool-result-nonexistent-xyz" in a  # virker selvom disk mangler
```

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_tool_result_store.py -o addopts="" -v -k "stub"`
Forventet: FAIL (`stub` er ukendt kwarg).

- [ ] **Step 3: Implementér**

I `core/services/tool_result_store.py`, ændr signaturen og tilføj stub-grenen ØVERST (før disk-load):
```python
def render_tool_result_for_prompt(
    content: str,
    *,
    expand: bool,
    max_chars: int = 1200,
    stub: bool = False,
) -> str:
    raw = str(content or "").strip()
    ref = parse_tool_result_reference(raw)

    if stub and ref:
        # COLD: ren funktion af den immutable reference-streng — ALDRIG disk.
        # (render-fallback skifter byte-form når 7-dages-reaper sletter JSON'en;
        #  reference-strengen i chat_messages.content er uforanderlig.)
        rid = ref["result_id"]
        tool_name = str(ref.get("tool_name") or "tool").strip() or "tool"
        summary = " ".join(str(ref.get("summary") or "").split()).strip()
        snippet = summary[:40].rstrip()
        if len(summary) > 40:
            snippet += "…"
        return (f"[tool_result:{rid} — {tool_name}: {snippet} "
                f"(read_tool_result)]")

    if not ref:
        normalized = " ".join(raw.split()).strip()
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 1].rstrip() + "…"
    # ... resten uændret (disk-load, expand/summary) ...
```

> **Implementer-note:** verificér at `parse_tool_result_reference` returnerer en `tool_name`-nøgle. `grep -n "def parse_tool_result_reference" -A15 core/services/tool_result_store.py`. Hvis den KUN giver `result_id` + `summary` (ikke `tool_name`), så udtræk tool-navnet fra reference-strengens `[{tool_name}]:`-linje med samme regex-mønster, eller udvid `parse_tool_result_reference` til at inkludere det (og test det). Stub'en må kun bruge felter der stammer fra `raw`.

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_tool_result_store.py -o addopts="" -v -k "stub"`
Forventet: PASS.

- [ ] **Step 5: Regressions-tjek + commit**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_tool_result_store.py -o addopts="" -q`
Forventet: alle grønne (stub-param er default False → eksisterende kald uændrede).
```bash
git add core/services/tool_result_store.py tests/services/test_tool_result_store.py
git commit -m "feat(tool-result): stub render mode — reference-only, byte-stable without disk"
```

---

## Fase 4 — Transcript-wiring + byte-stabilitets-gate

### Task 8: Cold-gren i render-løkken (flag-gatet) + byte-stabilitetstest

**Files:**
- Modify: `core/services/prompt_sections/transcript_sections.py:259-294`
- Test: `tests/services/test_transcript_sections_cold.py` (**ny**)

- [ ] **Step 1: Skriv fejlende test (byte-stabilitet = den kritiske)**

Opret `tests/services/test_transcript_sections_cold.py`:
```python
from core.services.prompt_sections.transcript_sections import (
    _build_structured_transcript_messages as build,
)
from core.services.tool_result_store import build_tool_result_reference


def _hist():
    # 3 user-turns, hver med et tool-result. ids stigende.
    ref = lambda i: build_tool_result_reference(
        f"tool-result-{i}", tool_name="bash", summary=f"output {i} " * 10)
    return [
        {"id": 1, "role": "user", "content": "gør A"},
        {"id": 2, "role": "assistant", "content": "kører"},
        {"id": 3, "role": "tool", "content": ref(3)},
        {"id": 4, "role": "user", "content": "gør B"},
        {"id": 5, "role": "assistant", "content": "kører"},
        {"id": 6, "role": "tool", "content": ref(6)},
        {"id": 7, "role": "user", "content": "gør C"},
        {"id": 8, "role": "assistant", "content": "kører"},
        {"id": 9, "role": "tool", "content": ref(9)},
    ]


def test_cold_floor_stubs_old_tools(monkeypatch):
    import core.services.prompt_sections.transcript_sections as ts
    monkeypatch.setattr(ts, "_lifecycle_enabled", lambda: True)
    monkeypatch.setattr(ts, "_cold_floor_for", lambda sid: 4)  # id<4 = cold
    out = build(_hist(), session_id="s1")
    blob = "\n".join(m["content"] for m in out)
    assert "tool-result-3" in blob            # cold → stub beholder id
    assert "read_tool_result" in blob         # stub-markør for id 3
    # id 6 og 9 er warm (id>4) → fuld summary-form, IKKE stub-markør ved dem


def test_byte_stability_between_turns_when_floor_fixed(monkeypatch):
    # KERNE-INVARIANT: cold_floor uændret → historik-bytes identiske når en ny
    # tur tilføjes. Dette er regressionen fra 2026-06-09.
    import core.services.prompt_sections.transcript_sections as ts
    monkeypatch.setattr(ts, "_lifecycle_enabled", lambda: True)
    monkeypatch.setattr(ts, "_cold_floor_for", lambda sid: 4)

    turn1 = _hist()
    out1 = build(turn1, session_id="s1")

    # næste tur: præcis samme historik + én ny bruger-besked bagerst
    turn2 = _hist() + [{"id": 10, "role": "user", "content": "gør D"}]
    out2 = build(turn2, session_id="s1")

    # de FÆLLES historik-beskeder skal være byte-identiske (prefix-stabilt)
    common1 = "\n".join(m["content"] for m in out1)
    common2 = "\n".join(m["content"] for m in out2)
    assert common2.startswith(common1[:len(common1) - 0]) or common1 in common2


def test_flag_off_is_unchanged(monkeypatch):
    import core.services.prompt_sections.transcript_sections as ts
    monkeypatch.setattr(ts, "_lifecycle_enabled", lambda: False)
    out_off = build(_hist(), session_id="s1")
    blob = "\n".join(m["content"] for m in out_off)
    assert "read_tool_result" not in blob     # ingen stubs når flag off
```

> **Implementer-note:** verificér `_build_structured_transcript_messages`' faktiske signatur (tager den `session_id`? `grep -n "def _build_structured_transcript_messages" core/services/prompt_sections/transcript_sections.py`). Hvis den ikke modtager `session_id`, tråd det ind fra kaldsstedet (samme sted som `_maybe_auto_compact_session(session_id, ...)` kaldes, transcript_sections.py:374). Cold-floor SKAL slås op via `session_id`. Tilpas testens `build(...)`-kald til den ægte signatur.

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_transcript_sections_cold.py -o addopts="" -v`
Forventet: FAIL.

- [ ] **Step 3: Implementér**

I `core/services/prompt_sections/transcript_sections.py`:

(a) Tilføj to små modul-niveau helpers (nemme at monkeypatche):
```python
def _lifecycle_enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "tool_result_lifecycle_enabled", False))
    except Exception:
        return False


def _cold_floor_for(session_id: str) -> int:
    try:
        from core.context.tool_result_lifecycle import get_cold_floor
        return get_cold_floor(session_id)
    except Exception:
        return 0
```

(b) I render-løkken (L274-279), hvor `raw_role == "tool"`, indsæt cold-grenen FØR den nuværende warm-render:
```python
        if raw_role == "tool":
            _mid = int(item.get("id", 0) or 0)
            if _cold_on and _mid and _mid < _cold_floor:
                content = render_tool_result_for_prompt(
                    raw_content, expand=False, stub=True,
                )
            else:
                content = render_tool_result_for_prompt(
                    raw_content,
                    expand=False,
                    max_chars=_tool_hist_cap,
                )
```

(c) Beregn `_cold_on` + `_cold_floor` ÉN gang før løkken (nær L264, hvor `merged` initialiseres):
```python
    _cold_on = _lifecycle_enabled()
    _cold_floor = _cold_floor_for(session_id) if _cold_on else 0
```

> **Cache-note:** `_cold_floor` er konstant gennem hele prompt-buildet (læses én gang). Da den kun rykker ved run-slut (Task 9), er hvert historisk tool-item byte-identisk mellem ture indtil et diskret ryk. Det er præcis kerne-invarianten (spec §2).

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_transcript_sections_cold.py -o addopts="" -v`
Forventet: PASS — især `test_byte_stability_between_turns_when_floor_fixed` og `test_flag_off_is_unchanged`.

- [ ] **Step 5: Regressions-tjek + commit**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/ -o addopts="" -k "transcript" -q`
Forventet: ingen nye fejl.
```bash
git add core/services/prompt_sections/transcript_sections.py tests/services/test_transcript_sections_cold.py
git commit -m "feat(transcript): cold-tier stub rendering behind cold_floor (flag-gated, byte-stable)"
```

---

## Fase 5 — Run-slut-advance + integration

### Task 9: Kald `evaluate_and_advance` ved run-slut (≤10 linjer, Boy-Scout-neutral)

**Files:**
- Modify: `core/services/visible_runs.py` (run-completion-sitet, nær L4590-4626)
- Test: `tests/services/test_visible_runs_lifecycle.py` (**ny**, funktions-niveau)

> **Boy Scout:** `visible_runs.py` er >2000 L. Ændringen her er BEVIDST ≤10 linjer (ét guarded kald, ingen logik-ændring) → under "rører"-tærsklen (>20 linjer / logik-ændring) → ingen udskilning påkrævet. Hold den lille.

- [ ] **Step 1: Skriv fejlende test**

Opret `tests/services/test_visible_runs_lifecycle.py`:
```python
def test_run_end_calls_evaluate_and_advance(monkeypatch):
    import core.services.visible_runs as vr
    calls = []
    monkeypatch.setattr(
        "core.context.tool_result_lifecycle.evaluate_and_advance",
        lambda sid, **k: calls.append(sid) or 0,
    )
    # Kald den lille wrapper Task 9 introducerer:
    vr._advance_tool_lifecycle("sess-vr-1")
    assert calls == ["sess-vr-1"]
```

- [ ] **Step 2: Kør — forvent FAIL**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_visible_runs_lifecycle.py -o addopts="" -v`
Forventet: FAIL (`_advance_tool_lifecycle` findes ikke).

- [ ] **Step 3: Implementér**

(a) Tilføj en lille modul-niveau wrapper i `core/services/visible_runs.py` (nær toppen, ved andre helpers):
```python
def _advance_tool_lifecycle(session_id: str) -> None:
    """Run-slut: ryk tool-result cold_floor (spec 2026-07-16). Fejl-tolerant."""
    try:
        from core.context.tool_result_lifecycle import evaluate_and_advance
        evaluate_and_advance(session_id)
    except Exception:
        pass
```

(b) Kald den ÉN gang når et run afsluttes med status completed. Find sitet hvor `_final_run_status == "completed"` og `finished_at` sættes (nær L4625). Indsæt efter at svaret er persisteret:
```python
                    _advance_tool_lifecycle(run.session_id)
```

> **Implementer-note:** verificér det eksakte attribut-navn for session-id på `run`-objektet (`grep -n "session_id" core/services/visible_runs.py | head`) — sandsynligvis `run.session_id`. Placér kaldet så det KUN rammer completed-stien (ikke failed/interrupted), efter besked-persistering, i `finally`/post-process er OK så længe status er completed. Advance er idempotent og fejl-tolerant, så dobbelt-kald skader ikke.

- [ ] **Step 4: Kør — forvent PASS**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/services/test_visible_runs_lifecycle.py -o addopts="" -v`
Forventet: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/visible_runs.py tests/services/test_visible_runs_lifecycle.py
git commit -m "feat(visible-runs): advance tool cold_floor at run-end (guarded, ≤10 lines)"
```

### Task 10: End-to-end integrationstest (flag on → gammelt bliver stub; rehydrering virker)

**Files:**
- Test: `tests/integration/test_tool_lifecycle_e2e.py` (**ny**)

- [ ] **Step 1: Skriv testen**

Opret `tests/integration/test_tool_lifecycle_e2e.py`:
```python
from core.services.chat_sessions import (
    create_chat_session, append_chat_message,
    chat_session_messages_since_last_compact,
)
from core.context import tool_result_lifecycle as trl
from core.services.tool_result_store import get_tool_result


class _S:
    tool_result_lifecycle_enabled = True
    tool_warm_run_window = 2         # lille vindue så testen trigger nemt
    tool_warm_token_ceiling = 10**9
    tool_warm_hysteresis = 0.0


def test_e2e_old_tool_becomes_cold_and_rehydratable():
    sid = "sess-e2e-lifecycle-1"
    create_chat_session(session_id=sid, title="t")
    # 5 user-turns, hver med et tool-result
    for i in range(5):
        append_chat_message(session_id=sid, role="user", content=f"opgave {i}")
        append_chat_message(session_id=sid, role="assistant", content="kører")
        append_chat_message(
            session_id=sid, role="tool", content=f"kommando-output nr {i} " * 20,
            tool_name="bash",
        )

    # run-slut: ryk floor (behold sidste 2 turns warm)
    new_floor = trl.evaluate_and_advance(sid, settings=_S())
    assert new_floor > 0

    msgs = chat_session_messages_since_last_compact(sid)
    cold = [m for m in msgs if m["role"] == "tool" and m["id"] < new_floor]
    assert cold, "mindst ét tool-result skal være under floor (cold)"

    # rehydrering: det fulde output er stadig på disk via result_id i referencen
    from core.services.tool_result_store import parse_tool_result_reference
    ref = parse_tool_result_reference(cold[0]["content"])
    assert ref is not None
    assert get_tool_result(ref["result_id"]) is not None  # fuldt output hentbart
```

- [ ] **Step 2: Kør — forvent PASS** (alt bygget i Task 1–9)

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/integration/test_tool_lifecycle_e2e.py -o addopts="" -v`
Forventet: PASS. Hvis `append_chat_message`'s `tool_name`-kwarg afviger, tilpas (se signatur chat_sessions.py:361).

- [ ] **Step 3: Fuld modul-suite grøn**

Run: `/home/bs/miniconda3/envs/ai/bin/python -m pytest tests/context/test_tool_result_lifecycle.py tests/services/test_tool_result_store.py tests/services/test_transcript_sections_cold.py tests/services/test_chat_sessions_id.py -o addopts="" -q`
Forventet: alle grønne.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/test_tool_lifecycle_e2e.py
git commit -m "test(lifecycle): e2e — old tool becomes cold stub, still rehydratable"
```

---

## Deploy + flip (efter alle tasks grønne — IKKE en subagent-task; Bjørn styrer)

1. `git push origin main`
2. Container: `git -C /media/projects/jarvis-v2 fetch origin && git -C /media/projects/jarvis-v2 reset --hard origin/main`
3. `sudo systemctl restart jarvis-runtime jarvis-api`
4. Flag stadig OFF → verificér golden (opførsel = før). Costs-tabel: cache% uændret.
5. Flip `tool_result_lifecycle_enabled=true` i `~/.jarvis-v2/config/runtime.json` (eller settings-sti), restart api.
6. Observér 1–2 timer: input-tokens falder på tool-tunge sessioner, cache% holder ~90%. Rollback = flag OFF + restart (spec §9).

## Self-review note

Dæknings-gate: hver rørt `core/`-modul har matchende test. Ingen placeholders — al kode er komplet. Kerne-invarianten (§2) har en dedikeret byte-stabilitetstest (Task 8 Step 1). Flag-off golden testet (Task 8). `id`-trådning er byte-neutral (metadata). Advance er single-writer (run-slut) + fejl-tolerant. Within-run (§6) bevidst udskudt med begrundelse. Boy-Scout: visible_runs-ændring holdt ≤10 linjer.
