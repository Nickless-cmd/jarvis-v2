# Strukturerede content-blokke: persist + stream + reload — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persistér hele chat-turens content-array (text + tool_use + tool_result) struktureret server-side, stream tool_result som content-blok, og lad klienten rendere direkte fra det persisterede — så tool-kort aldrig forsvinder ved reload.

**Architecture:** Ny kanonisk kilde `chat_messages.content_json` (JSON-array af content-blokke) ved siden af den bevarede `content`-tekst-projektion (så alle server-tekst-læsere er urørte). Serve-on-read adapter rekonstruerer gamle beskeder. Wire flyttes til første-klasses `tool_result`-content-blokke. Alt er flag-gated (`structured_content_v2`, default ON, governed kill-switch) og udrulles klient-først så en levende session ikke kan brække.

**Tech Stack:** Python 3.11 (FastAPI, sqlite3), TypeScript/React (jarvis-desk Electron + mobil), pytest, vitest.

**Spec:** [docs/superpowers/specs/2026-07-09-structured-content-blocks-design.md](../specs/2026-07-09-structured-content-blocks-design.md)

---

## Kanonisk blok-format (kontrakt — brugt af ALLE tasks)

`content_json` = JSON-serialiseret liste af blokke i turens rækkefølge:

```jsonc
[
  {"type": "text", "text": "Lad mig tjekke."},
  {"type": "tool_use", "id": "toolu_ab12", "name": "bash", "input": {"cmd": "ls"}},
  {"type": "tool_result", "tool_use_id": "toolu_ab12", "status": "done",
   "content": "file1\nfile2", "is_error": false},
  {"type": "text", "text": "Der er to filer."}
]
```

- `status` ∈ `"done" | "error"`.
- Klientens render-model folder `tool_result` ind på sin `tool_use` (via `tool_use_id`) — se Task 8. Persist + wire er kanonisk (separate blokke); klientens *folde* er en ren render-detalje.

---

## Task-ansvar (model-tildeling)

- **Mekaniske/isolerede (fresh haiku-subagent, fuld kode i task):** Task 1, 2, 3, 5, 8, 9, 10.
- **Skrøbelig hot-path / integration (Claude inline):** Task 4, 6, 7, 11, 12, 13.

---

## Task 1: `content_blocks.py` — rene blok-funktioner

**Files:**
- Create: `core/services/content_blocks.py`
- Test: `tests/test_content_blocks.py`

Kernen: flader blokke til tekst-projektion (§4.3) + rekonstruerer gamle beskeder (§6). Rene funktioner, nul DB/hot-path.

- [ ] **Step 1: Skriv de fejlende tests**

```python
# tests/test_content_blocks.py
from core.services.content_blocks import (
    content_blocks_to_text,
    reconstruct_blocks_from_legacy,
)


def test_text_only_projection_is_plain_text():
    blocks = [{"type": "text", "text": "hej med dig"}]
    assert content_blocks_to_text(blocks) == "hej med dig"


def test_multiple_text_blocks_joined_with_blank_line():
    blocks = [{"type": "text", "text": "linje et"}, {"type": "text", "text": "linje to"}]
    assert content_blocks_to_text(blocks) == "linje et\n\nlinje to"


def test_tool_use_and_result_omitted_from_text_projection():
    # Projektionen er den PROSE brugeren læser; tool-blokke er ikke prosa.
    blocks = [
        {"type": "text", "text": "svar"},
        {"type": "tool_use", "id": "toolu_1", "name": "bash", "input": {}},
        {"type": "tool_result", "tool_use_id": "toolu_1", "status": "done", "content": "x", "is_error": False},
    ]
    assert content_blocks_to_text(blocks) == "svar"


def test_empty_blocks_gives_empty_string():
    assert content_blocks_to_text([]) == ""


def test_reconstruct_plain_text_message_is_single_text_block():
    blocks = reconstruct_blocks_from_legacy("assistant", "bare tekst", load_result=lambda ref: None)
    assert blocks == [{"type": "text", "text": "bare tekst"}]


def test_reconstruct_tool_message_with_reference_becomes_tool_result_block():
    # role="tool" gammel besked bærer "[bash]:<result_id>". Vi slår resultatet op.
    def _load(ref):
        assert ref == "res_42"
        return {"tool_name": "bash", "content": "file1\nfile2"}
    blocks = reconstruct_blocks_from_legacy("tool", "[bash]:res_42", load_result=_load)
    assert blocks == [
        {"type": "tool_result", "tool_use_id": "", "status": "done",
         "content": "file1\nfile2", "is_error": False, "name": "bash"}
    ]


def test_reconstruct_tool_message_unresolvable_ref_degrades_to_text():
    blocks = reconstruct_blocks_from_legacy("tool", "[bash]:missing", load_result=lambda ref: None)
    assert blocks == [{"type": "text", "text": "[bash]:missing"}]
```

- [ ] **Step 2: Kør testen, bekræft den fejler**

Run: `conda activate ai && python -m pytest tests/test_content_blocks.py -v`
Expected: FAIL — `ModuleNotFoundError: core.services.content_blocks`.

- [ ] **Step 3: Skriv minimal implementering**

```python
# core/services/content_blocks.py
"""Rene content-blok-funktioner: tekst-projektion + serve-on-read rekonstruktion.

Kanonisk blok-format er dokumenteret i
docs/superpowers/specs/2026-07-09-structured-content-blocks-design.md §4.
Ingen DB-adgang her — rekonstruktion får en ``load_result``-callback injiceret,
så modulet er rent og enhedstestbart.
"""
from __future__ import annotations

from typing import Callable, Optional

from core.services.tool_result_store import parse_tool_result_reference

# Callback-signatur: (result_id) -> {"tool_name": str, "content": str} | None
LoadResult = Callable[[str], Optional[dict]]


def content_blocks_to_text(blocks: list[dict]) -> str:
    """Flad en content-blok-array til markdown-tekst-projektionen som alle
    tekst-læsere (kontekst-bygger, memory, søgning) bruger. KUN ``text``-blokke
    bidrager — tool_use/tool_result er ikke prosa. Deterministisk og stabil."""
    parts = [str(b.get("text") or "") for b in (blocks or []) if b.get("type") == "text"]
    return "\n\n".join(p for p in parts if p)


def reconstruct_blocks_from_legacy(
    role: str, content: str, *, load_result: LoadResult
) -> list[dict]:
    """Serve-on-read: byg blok-array for en GAMMEL besked (uden content_json).
    - role="tool" m. "[navn]:<ref>" → tool_result-blok (resultat slås op via callback).
    - alt andet → én text-blok. Ukendt/uopslåelig ref → degradér til text (fejler aldrig)."""
    text = str(content or "")
    if role == "tool":
        ref = parse_tool_result_reference(text)
        if ref:
            loaded = None
            try:
                loaded = load_result(str(ref.get("result_id") or ""))
            except Exception:
                loaded = None
            if loaded:
                return [{
                    "type": "tool_result",
                    "tool_use_id": "",
                    "status": "done",
                    "content": str(loaded.get("content") or ""),
                    "is_error": False,
                    "name": str(loaded.get("tool_name") or ref.get("tool_name") or ""),
                }]
    return [{"type": "text", "text": text}]
```

**Verificér i denne task (Step 3.5):** åbn [core/services/tool_result_store.py:92](../../../core/services/tool_result_store.py) og bekræft præcis retur-form af `parse_tool_result_reference` (nøglerne `result_id` / `tool_name`). Justér nøgle-navnene i koden ovenfor til det den faktisk returnerer. Bekræft også om der findes en loader (`load_tool_result`/`get_tool_result`) — hvis referencen selv bærer summary, kan `load_result` bare returnere den; Task 4 wirer den rigtige loader.

- [ ] **Step 4: Kør testen, bekræft grøn**

Run: `conda activate ai && python -m pytest tests/test_content_blocks.py -v`
Expected: PASS (7/7). Justér `parse_tool_result_reference`-nøgler hvis Step 3.5 afslørede andre navne.

- [ ] **Step 5: Commit**

```bash
git add core/services/content_blocks.py tests/test_content_blocks.py
git commit -m "feat(chat): content-blok tekst-projektion + serve-on-read rekonstruktion"
```

---

## Task 2: DB-kolonne `content_json`

**Files:**
- Modify: `core/runtime/db_schema.py` (ny `_ensure_chat_messages_content_json_column`, kaldt i ensure-flowet ved linje ~902)
- Test: `tests/test_content_json_column.py`

Følg PRÆCIST skabelonen `_ensure_chat_messages_reasoning_column` ([db_schema.py:966](../../../core/runtime/db_schema.py)).

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_content_json_column.py
import sqlite3
from core.runtime.db_schema import _ensure_chat_messages_content_json_column


def test_adds_content_json_column_idempotently():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, message_id TEXT, "
        "session_id TEXT, role TEXT, content TEXT)"
    )
    _ensure_chat_messages_content_json_column(conn)
    _ensure_chat_messages_content_json_column(conn)  # idempotent — må ikke kaste
    cols = [r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()]
    assert "content_json" in cols
```

- [ ] **Step 2: Kør, bekræft fejl**

Run: `conda activate ai && python -m pytest tests/test_content_json_column.py -v`
Expected: FAIL — `ImportError: cannot import name '_ensure_chat_messages_content_json_column'`.

- [ ] **Step 3: Implementér**

Tilføj i `core/runtime/db_schema.py` (lige efter `_ensure_chat_messages_reasoning_column`):

```python
def _ensure_chat_messages_content_json_column(conn: sqlite3.Connection) -> None:
    """Add chat_messages.content_json column. Idempotent.

    Kanonisk struktureret content-array (text/tool_use/tool_result) pr. besked;
    NULL = gammel besked (serve-on-read rekonstruerer). Nullable → ingen backfill.
    """
    cols = [
        r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
    ]
    if "content_json" not in cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN content_json TEXT")
```

Wire det ind i ensure-flowet ved siden af reasoning-kaldet (linje ~902):

```python
        _ensure_chat_messages_reasoning_column(conn)
        _ensure_chat_messages_content_json_column(conn)   # ← tilføj denne linje
```

- [ ] **Step 4: Kør, bekræft grøn**

Run: `conda activate ai && python -m pytest tests/test_content_json_column.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/runtime/db_schema.py tests/test_content_json_column.py
git commit -m "feat(db): chat_messages.content_json kolonne (nullable, idempotent)"
```

---

## Task 3: `append_chat_message` skriver `content_json`

**Files:**
- Modify: `core/services/chat_sessions.py:323-453` (`append_chat_message`)
- Test: `tests/test_append_content_json.py`

Tilføj valgfri `content_json`-parameter; INSERT den. Default `None` → uændret adfærd for alle eksisterende kaldere.

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_append_content_json.py
import json
from core.services.chat_sessions import append_chat_message, get_chat_session
from core.services.chat_sessions import create_chat_session  # verificér navn i Step 3.5


def _new_session():
    s = create_chat_session(title="t")
    return s["id"] if isinstance(s, dict) else s


def test_append_persists_content_json_when_given(tmp_jarvis_db):
    sid = _new_session()
    blocks = [{"type": "text", "text": "svar"},
              {"type": "tool_use", "id": "toolu_1", "name": "bash", "input": {}}]
    append_chat_message(session_id=sid, role="assistant", content="svar",
                        content_json=json.dumps(blocks))
    raw = get_chat_session(sid)
    msg = [m for m in raw["messages"] if m["role"] == "assistant"][-1]
    assert msg.get("content_json") is not None


def test_append_without_content_json_leaves_null(tmp_jarvis_db):
    sid = _new_session()
    append_chat_message(session_id=sid, role="assistant", content="ren tekst")
    raw = get_chat_session(sid)
    msg = [m for m in raw["messages"] if m["role"] == "assistant"][-1]
    # Ingen content_json → adapteren returnerer rekonstrueret (Task 4), men rå-kolonnen er NULL.
    assert msg.get("content_json") in (None, [{"type": "text", "text": "ren tekst"}])
```

**Step 3.5-verifikation:** bekræft session-opret-funktionens navn/retur (`create_chat_session`?) i [chat_sessions.py](../../../core/services/chat_sessions.py) og fixture-navnet for en isoleret DB (`tmp_jarvis_db`? — se `tests/conftest.py`). Justér testen.

- [ ] **Step 2: Kør, bekræft fejl**

Run: `conda activate ai && python -m pytest tests/test_append_content_json.py -v`
Expected: FAIL — `TypeError: append_chat_message() got an unexpected keyword argument 'content_json'`.

- [ ] **Step 3: Implementér**

I `append_chat_message`-signaturen (linje 323-334) tilføj parameteren:

```python
def append_chat_message(
    *,
    session_id: str,
    role: str,
    content: str,
    created_at: str | None = None,
    tool_name: str | None = None,
    tool_arguments: dict[str, object] | None = None,
    user_id: str | None = None,
    workspace_name: str | None = None,
    reasoning_content: str = "",
    content_json: str | None = None,   # ← NY: JSON-encoded blok-array; None = gammel adfærd
) -> dict[str, object]:
```

Opdatér INSERT (linje 422-431) til at inkludere kolonnen:

```python
        conn.execute(
            """
            INSERT INTO chat_messages (message_id, session_id, role, content,
                                        user_id, workspace_name,
                                        reasoning_content, content_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (message_id, normalized_session, normalized_role, normalized_content,
             _user_id, _workspace_name, str(reasoning_content or ""),
             content_json, timestamp),
        )
```

Tilføj til retur-dict (linje 446-453): `"content_json": content_json,`.

- [ ] **Step 4: Kør, bekræft grøn**

Run: `conda activate ai && python -m pytest tests/test_append_content_json.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/chat_sessions.py tests/test_append_content_json.py
git commit -m "feat(chat): append_chat_message skriver valgfri content_json"
```

---

## Task 4: GET-serialisering + serve-on-read adapter (Claude inline)

**Files:**
- Modify: `core/services/chat_sessions.py:258-305` (`get_chat_session`)
- Test: `tests/test_get_session_content_json.py`

GET returnerer `content_json` (array) pr. besked: parse gemt kolonne hvis sat, ellers rekonstruér via `content_blocks.reconstruct_blocks_from_legacy`. Wire den rigtige tool-result-loader.

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_get_session_content_json.py
import json
from core.services.chat_sessions import append_chat_message, get_chat_session, create_chat_session


def _sid():
    s = create_chat_session(title="t")
    return s["id"] if isinstance(s, dict) else s


def test_stored_content_json_is_parsed_to_array(tmp_jarvis_db):
    sid = _sid()
    blocks = [{"type": "text", "text": "svar"}]
    append_chat_message(session_id=sid, role="assistant", content="svar",
                        content_json=json.dumps(blocks))
    out = get_chat_session(sid)
    msg = [m for m in out["messages"] if m["role"] == "assistant"][-1]
    assert msg["content_json"] == blocks   # parset, ikke streng


def test_legacy_message_reconstructs_to_text_block(tmp_jarvis_db):
    sid = _sid()
    append_chat_message(session_id=sid, role="assistant", content="gammel prosa")
    out = get_chat_session(sid)
    msg = [m for m in out["messages"] if m["role"] == "assistant"][-1]
    assert msg["content_json"] == [{"type": "text", "text": "gammel prosa"}]
```

- [ ] **Step 2: Kør, bekræft fejl**

Run: `conda activate ai && python -m pytest tests/test_get_session_content_json.py -v`
Expected: FAIL — `KeyError: 'content_json'` (feltet mangler i serialiseringen).

- [ ] **Step 3: Implementér**

Udvid `SELECT` (linje 274-282) til at hente kolonnen:

```python
        messages = conn.execute(
            """
            SELECT message_id, role, content, content_json, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (normalized,),
        ).fetchall()
```

Tilføj en modul-privat loader + adapter-hjælper (øverst i filen efter imports):

```python
import json as _json
from core.services.content_blocks import (
    content_blocks_to_text,  # (importeret for symmetri; ikke brugt her)
    reconstruct_blocks_from_legacy,
)


def _load_tool_result_for_reconstruct(result_id: str) -> dict | None:
    """Slå et gammelt tool-resultat op til serve-on-read. Best-effort, aldrig kast."""
    if not result_id:
        return None
    try:
        from core.services.tool_result_store import load_tool_result  # verificér navn (Step 3.5)
        row = load_tool_result(result_id)
        if row:
            return {"tool_name": str(row.get("tool_name") or ""),
                    "content": str(row.get("content") or "")}
    except Exception:
        return None
    return None


def _content_json_for_row(role: str, content: str, raw_json: str | None) -> list[dict]:
    """Adapter: gemt content_json parses; ellers rekonstruér fra tekst (best-effort)."""
    if raw_json:
        try:
            parsed = _json.loads(raw_json)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return reconstruct_blocks_from_legacy(role, content, load_result=_load_tool_result_for_reconstruct)
```

Opdatér `message_items`-bygningen (linje 283-292):

```python
    message_items = [
        {
            "id": str(row["message_id"]),
            "role": str(row["role"]),
            "content": str(row["content"]),
            "content_json": _content_json_for_row(
                str(row["role"]), str(row["content"]),
                row["content_json"] if "content_json" in row.keys() else None),
            "ts": _time_label(str(row["created_at"])),
            "created_at": str(row["created_at"]),
        }
        for row in messages
    ]
```

**Step 3.5-verifikation:** bekræft en loader-funktion i `tool_result_store.py` (fx `load_tool_result(result_id)`); findes ingen, og `parse_tool_result_reference` selv bærer summary'en, så drop loaderen og lad `reconstruct_blocks_from_legacy` bruge referencens egen summary. Justér Task 1's callback-kontrakt tilsvarende.

- [ ] **Step 4: Kør, bekræft grøn**

Run: `conda activate ai && python -m pytest tests/test_get_session_content_json.py tests/test_content_blocks.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/chat_sessions.py tests/test_get_session_content_json.py
git commit -m "feat(chat): GET session returnerer content_json (parset eller rekonstrueret)"
```

---

## Task 5: Flag-helper `structured_content_v2` (default ON)

**Files:**
- Create: `core/services/structured_content_flag.py`
- Test: `tests/test_structured_content_flag.py`

Governed kill-switch, default ON. Læses fra runtime-state; fejl-tolerant (læse-fejl → default ON for skrivning, men se §fail-behavior nedenfor).

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_structured_content_flag.py
from unittest.mock import patch
from core.services.structured_content_flag import structured_content_v2_enabled


def test_defaults_to_on_when_unset():
    with patch("core.services.structured_content_flag._read_flag", return_value=None):
        assert structured_content_v2_enabled() is True


def test_off_when_explicitly_disabled():
    with patch("core.services.structured_content_flag._read_flag", return_value="off"):
        assert structured_content_v2_enabled() is False


def test_on_when_explicitly_enabled():
    with patch("core.services.structured_content_flag._read_flag", return_value="on"):
        assert structured_content_v2_enabled() is True


def test_read_error_defaults_on():
    def _boom():
        raise RuntimeError("db nede")
    with patch("core.services.structured_content_flag._read_flag", side_effect=_boom):
        assert structured_content_v2_enabled() is True
```

- [ ] **Step 2: Kør, bekræft fejl**

Run: `conda activate ai && python -m pytest tests/test_structured_content_flag.py -v`
Expected: FAIL — modul findes ikke.

- [ ] **Step 3: Implementér**

```python
# core/services/structured_content_flag.py
"""Governed kill-switch for struktureret content-persist + wire. Default ON.

Flip OFF (owner) → nye beskeder persisteres som ren tekst igen og tool_result
streames som system_event igen. Allerede-skrevne content_json-rækker forbliver
læsbare uanset (adapteren i get_chat_session honorerer dem).
"""
from __future__ import annotations

_STATE_KEY = "structured_content_v2"


def _read_flag() -> str | None:
    """Læs rå flag-værdi fra runtime-state. None = usat. Verificér den præcise
    getter i Step 3.5 (get_runtime_state_value på core.runtime.db)."""
    from core.runtime.db import get_runtime_state_value
    return get_runtime_state_value(_STATE_KEY)


def structured_content_v2_enabled() -> bool:
    """True medmindre eksplicit slået fra ('off'/'0'/'false'). Læse-fejl → True
    (default ON er Bjørns valg; kill-switch kræver et EKSPLICIT off for at slå fra)."""
    try:
        raw = _read_flag()
    except Exception:
        return True
    if raw is None:
        return True
    return str(raw).strip().lower() not in {"off", "0", "false", "no"}
```

**Step 3.5-verifikation:** bekræft `get_runtime_state_value`-signaturen i [core/runtime/db.py](../../../core/runtime/db.py) (samme getter som `reference_central_live_flags_groundtruth` beskriver). Findes en anden kanonisk state-getter, brug den. Tilføj en tilsvarende `set`-sti IKKE her — owner-toggle wires i Task 13's verifikation via eksisterende `central_query_tool`/runtime-state-set.

- [ ] **Step 4: Kør, bekræft grøn**

Run: `conda activate ai && python -m pytest tests/test_structured_content_flag.py -v`
Expected: PASS (4/4).

- [ ] **Step 5: Commit**

```bash
git add core/services/structured_content_flag.py tests/test_structured_content_flag.py
git commit -m "feat(chat): structured_content_v2 kill-switch helper (default ON)"
```

---

## Task 6: Byg blok-array ved run-slut + persistér (Claude inline, hot-path)

**Files:**
- Modify: `core/services/visible_runs.py` (VisibleRun-blok-akkumulator + de 3 completion-persist-stier ~4271/4929/5028)
- Modify: `core/services/visible_runs_outcomes.py:78` (`_persist_session_assistant_message` tager blokke)
- Test: `tests/test_persist_structured_blocks.py`

**Dette er den skrøbelige task.** Målet: fang turens ordnede blokke og persistér dem som `content_json` når flaget er ON.

- [ ] **Step 1: Kortlæg blok-kilden i koden (in-task grounding, ingen ændring)**

Læs `core/services/visible_runs.py` completion-region (linje ~2285-3130 og ~4050-5040). Dokumentér i en kommentar øverst i den nye test-fil hvad der bærer den ordnede sekvens ved persist-tid:
- `_a_parts` (tekst-segmenter), `_a_tool_calls` (akkumulerede tool_use), og hvor tool-resultater lander (fra `_execute_simple_tool_calls`).
- Om rækkefølgen (tekst→tool→tekst) er bevaret pr. runde eller kun som slut-tekst + tool-liste.

**Beslutnings-regel:** er den ægte interleaving tilgængelig → byg blokke i den rækkefølge. Er den IKKE → deterministisk fallback (spec §5): alle tekst-segmenter først, derefter tool_use/tool_result-par i kald-rækkefølge.

- [ ] **Step 2: Skriv den fejlende test**

```python
# tests/test_persist_structured_blocks.py
import json
from unittest.mock import patch
from core.services.content_blocks import content_blocks_to_text


def test_build_blocks_orders_text_and_tools():
    from core.services.visible_runs import _build_turn_blocks
    blocks = _build_turn_blocks(
        text="Der er to filer.",
        tool_calls=[{"id": "toolu_1", "name": "bash", "input": {"cmd": "ls"}}],
        tool_results=[{"tool_use_id": "toolu_1", "status": "done", "content": "a\nb", "is_error": False}],
    )
    types = [b["type"] for b in blocks]
    assert "tool_use" in types and "tool_result" in types and "text" in types
    # Tekst-projektionen forbliver ren prosa.
    assert content_blocks_to_text(blocks) == "Der er to filer."


def test_build_blocks_text_only_no_tools():
    from core.services.visible_runs import _build_turn_blocks
    blocks = _build_turn_blocks(text="bare svar", tool_calls=[], tool_results=[])
    assert blocks == [{"type": "text", "text": "bare svar"}]
```

- [ ] **Step 3: Kør, bekræft fejl**

Run: `conda activate ai && python -m pytest tests/test_persist_structured_blocks.py -v`
Expected: FAIL — `_build_turn_blocks` findes ikke.

- [ ] **Step 4: Implementér `_build_turn_blocks` + wire persist**

Tilføj i `visible_runs.py` (nær de andre run-helpers):

```python
def _build_turn_blocks(
    *, text: str, tool_calls: list[dict], tool_results: list[dict]
) -> list[dict]:
    """Byg den kanoniske content-blok-array for en assistant-tur.

    Rækkefølge: tekst-prosa, derefter tool_use/tool_result-par i kald-rækkefølge
    (deterministisk fallback jf. spec §5 — den ægte interleaving hentes af caller
    hvis run-state bærer den). tool_result matches til tool_use via id."""
    blocks: list[dict] = []
    clean = str(text or "").strip()
    if clean:
        blocks.append({"type": "text", "text": clean})
    results_by_id = {str(r.get("tool_use_id") or ""): r for r in (tool_results or [])}
    for tc in (tool_calls or []):
        tid = str(tc.get("id") or "")
        blocks.append({"type": "tool_use", "id": tid,
                       "name": str(tc.get("name") or ""), "input": tc.get("input") or {}})
        r = results_by_id.get(tid)
        if r is not None:
            blocks.append({"type": "tool_result", "tool_use_id": tid,
                           "status": str(r.get("status") or "done"),
                           "content": str(r.get("content") or ""),
                           "is_error": bool(r.get("is_error"))})
    return blocks
```

Opdatér `_persist_session_assistant_message` ([visible_runs_outcomes.py:78](../../../core/services/visible_runs_outcomes.py)) til at tage valgfrie blokke og skrive `content_json` når flaget er ON:

```python
def _persist_session_assistant_message(
    run: "_vr.VisibleRun",
    text: str,
    *,
    reasoning_content: str = "",
    blocks: list[dict] | None = None,   # ← NY
) -> None:
    ...
    # (uændret sanitizing frem til _append_chat_message_with_retry)
    content_json = None
    if blocks:
        try:
            from core.services.structured_content_flag import structured_content_v2_enabled
            if structured_content_v2_enabled():
                import json as _json
                content_json = _json.dumps(blocks, ensure_ascii=False)
        except Exception:
            content_json = None
    message = _append_chat_message_with_retry(
        session_id=run.session_id, role="assistant", content=normalized,
        reasoning_content=str(reasoning_content or ""), content_json=content_json,
    )
```

Opdatér `_append_chat_message_with_retry` til at videreføre `content_json` (default None) til `_vr.append_chat_message`.

Ved DE TRE completion-persist-stier (~4271/4929/5028) — kun de reelle svar-stier, IKKE cancel/error-stierne (1343/1366/1393/1420, som forbliver tekst-kun) — byg blokke og send dem:

```python
                    _persist_session_assistant_message(
                        run, followup_text,
                        reasoning_content=_round_reasoning,
                        blocks=_build_turn_blocks(
                            text=followup_text,
                            tool_calls=_a_tool_calls,          # verificér variabelnavn i scope (Step 1)
                            tool_results=_collected_tool_results,  # verificér kilde i scope (Step 1)
                        ),
                    )
```

**Kritisk:** brug de FAKTISKE i-scope variabelnavne fra Step 1's kortlægning. Bær ikke blokke ind hvor tool-state ikke er tilgængelig — hellere `blocks=None` (falder tilbage til ren tekst, uændret adfærd) end en forkert reference.

- [ ] **Step 5: Kør, bekræft grøn + ingen regression**

Run: `conda activate ai && python -m pytest tests/test_persist_structured_blocks.py tests/test_visible_runs*.py -v`
Expected: PASS. Nye tests grønne; eksisterende visible_runs-tests uændret grønne.

- [ ] **Step 6: Commit**

```bash
git add core/services/visible_runs.py core/services/visible_runs_outcomes.py tests/test_persist_structured_blocks.py
git commit -m "feat(chat): byg + persistér struktureret content_json ved run-slut (flag-gated)"
```

---

## Task 7: Stream `tool_result` som content-blok (Claude inline, hot-path)

**Files:**
- Modify: `core/services/anthropic_sse_emitter.py` (ny `tool_result` content-blok-metode)
- Modify: `core/services/visible_runs_sse_v2.py:354` (emissions-sted, flag-gated dual)
- Test: `tests/test_sse_tool_result_block.py`

Når flaget er ON: emit tool_result som content-blok. Når OFF: behold `system_event` (uændret).

- [ ] **Step 1: Skriv den fejlende test**

```python
# tests/test_sse_tool_result_block.py
from core.services.anthropic_sse_emitter import AnthropicSSEEmitter


def test_tool_result_block_emits_content_block_events():
    em = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
    out = "".join(em.tool_result_block(
        tool_use_id="toolu_1", status="done", content="a\nb", is_error=False))
    assert "content_block_start" in out
    assert "tool_result" in out
    assert "toolu_1" in out
    assert "content_block_stop" in out
```

- [ ] **Step 2: Kør, bekræft fejl**

Run: `conda activate ai && python -m pytest tests/test_sse_tool_result_block.py -v`
Expected: FAIL — `AttributeError: 'AnthropicSSEEmitter' object has no attribute 'tool_result_block'`.

- [ ] **Step 3: Implementér emitter-metoden**

Tilføj i `AnthropicSSEEmitter` (efter `tool_use_input_delta`):

```python
    def tool_result_block(
        self, *, tool_use_id: str, status: str, content: str, is_error: bool = False
    ) -> Iterator[str]:
        """Emit et første-klasses tool_result som content-blok (kanonisk wire-form).
        Lukker enhver åben blok først, åbner+lukker en tool_result-blok på nyt index."""
        yield from self._close_open_block()
        idx = self._next_index
        self._next_index += 1
        yield self._format("content_block_start", {
            "type": "content_block_start",
            "index": idx,
            "content_block": {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "status": status,
                "content": content,
                "is_error": bool(is_error),
            },
        })
        yield self._format("content_block_stop", {"type": "content_block_stop", "index": idx})
```

- [ ] **Step 4: Wire emissions-stedet (flag-gated dual)**

I `visible_runs_sse_v2.py` ved tool_result-emissionen (linje ~354): behold `SystemEvent(kind="tool_result", ...)` når flaget er OFF; emit content-blokken når ON. Præcis form afhænger af hvordan emitteren er trådet ind i v2-streamen (verificér i denne task); mønster:

```python
from core.services.structured_content_flag import structured_content_v2_enabled
if structured_content_v2_enabled():
    # emit via emitter.tool_result_block(...) i den aktive stream-emitter
    yield from _emitter.tool_result_block(
        tool_use_id=tool_id, status=status, content=str(payload.get("result_text") or ""),
        is_error=(status in ("error", "failed")))
else:
    yield SystemEvent(kind="tool_result", payload={...})  # uændret nuværende form
```

- [ ] **Step 5: Kør, bekræft grøn + ingen regression**

Run: `conda activate ai && python -m pytest tests/test_sse_tool_result_block.py tests/test_visible_runs_sse*.py -v`
Expected: PASS; eksisterende sse-tests uændret.

- [ ] **Step 6: Commit**

```bash
git add core/services/anthropic_sse_emitter.py core/services/visible_runs_sse_v2.py tests/test_sse_tool_result_block.py
git commit -m "feat(chat): stream tool_result som content-blok (flag-gated, dual m. system_event)"
```

---

## Task 8: Klient — wire-type + fold-hjælper (subagent)

**Files:**
- Modify: `apps/jarvis-desk/src/lib/sseProtocol.ts` (tool_result i `ContentBlockStartEvent`)
- Create: `apps/jarvis-desk/src/lib/foldToolResults.ts`
- Test: `apps/jarvis-desk/src/lib/foldToolResults.test.ts`

Kanonisk wire har tool_result som content-blok. Klientens render-model folder den ind på sin tool_use (ingen ny renderet blok-type → MessageView urørt).

- [ ] **Step 1: Skriv den fejlende test**

```typescript
// apps/jarvis-desk/src/lib/foldToolResults.test.ts
import { describe, it, expect } from 'vitest'
import { foldToolResults } from './foldToolResults'

describe('foldToolResults', () => {
  it('folder tool_result ind på matchende tool_use og fjerner tool_result-blokken', () => {
    const blocks = [
      { type: 'text', text: 'svar' },
      { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} },
      { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'a\nb' },
    ]
    const out = foldToolResults(blocks as any)
    expect(out.map((b: any) => b.type)).toEqual(['text', 'tool_use'])
    const tu = out.find((b: any) => b.type === 'tool_use') as any
    expect(tu.status).toBe('done')
    expect(tu.result).toBe('a\nb')
  })

  it('lader blokke uden tool_result være urørt', () => {
    const blocks = [{ type: 'text', text: 'x' }]
    expect(foldToolResults(blocks as any)).toEqual(blocks)
  })

  it('tool_result uden matchende tool_use droppes stille', () => {
    const blocks = [{ type: 'tool_result', tool_use_id: 'ukendt', status: 'done', content: 'y' }]
    expect(foldToolResults(blocks as any)).toEqual([])
  })
})
```

- [ ] **Step 2: Kør, bekræft fejl**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/foldToolResults.test.ts`
Expected: FAIL — modul findes ikke.

- [ ] **Step 3: Implementér**

Tilføj tool_result til wire-typen i `sseProtocol.ts` `ContentBlockStartEvent.content_block`-unionen:

```typescript
  content_block:
    | { type: 'text'; text: string }
    | { type: 'thinking'; thinking: string }
    | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown> }
    | { type: 'tool_result'; tool_use_id: string; status: string; content: string; is_error?: boolean }
```

```typescript
// apps/jarvis-desk/src/lib/foldToolResults.ts
import type { ContentBlock } from './sseProtocol'

/** Folder kanoniske tool_result-blokke ind på deres tool_use (via tool_use_id) og
 *  fjerner tool_result-blokkene, så resultatet er den render-ContentBlock[] som
 *  MessageView allerede forstår. tool_result uden match droppes stille. */
export function foldToolResults(blocks: Array<Record<string, unknown>>): ContentBlock[] {
  const out: ContentBlock[] = []
  const idxById = new Map<string, number>()
  for (const b of blocks || []) {
    if (b.type === 'tool_use') {
      idxById.set(String(b.id), out.length)
      out.push({ type: 'tool_use', id: String(b.id), name: String(b.name ?? ''), input: (b.input as Record<string, unknown>) ?? {}, status: 'running' })
    } else if (b.type === 'tool_result') {
      const at = idxById.get(String(b.tool_use_id))
      if (at === undefined) continue
      const tu = out[at] as Extract<ContentBlock, { type: 'tool_use' }>
      const status = b.status === 'error' || b.is_error ? 'error' : 'done'
      out[at] = { ...tu, status, result: String(b.content ?? '') }
    } else if (b.type === 'text') {
      out.push({ type: 'text', text: String(b.text ?? '') })
    } else if (b.type === 'thinking') {
      out.push({ type: 'thinking', thinking: String(b.thinking ?? '') })
    }
  }
  return out
}
```

- [ ] **Step 4: Kør, bekræft grøn**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/foldToolResults.test.ts`
Expected: PASS (3/3).

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/sseProtocol.ts apps/jarvis-desk/src/lib/foldToolResults.ts apps/jarvis-desk/src/lib/foldToolResults.test.ts
git commit -m "feat(desk): tool_result wire-type + foldToolResults render-hjælper"
```

---

## Task 9: Klient-reducer — tool_result content-blok (dual-read) (subagent)

**Files:**
- Modify: `apps/jarvis-desk/src/lib/streamReducer.ts:72-79` (`content_block_start`)
- Test: `apps/jarvis-desk/src/lib/streamReducer.test.ts` (opret hvis mangler)

Reduceren folder tool_result-content-blokken ind på tool_use (samme udfald som den gamle `system_event`-sti, som BEVARES for dual-read).

- [ ] **Step 1: Skriv den fejlende test**

```typescript
// apps/jarvis-desk/src/lib/streamReducer.test.ts
import { describe, it, expect } from 'vitest'
import { streamReducer, initialStreamState } from './streamReducer'

describe('streamReducer tool_result content-blok', () => {
  it('folder tool_result-content-blok ind på matchende tool_use', () => {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} } } as any)
    s = streamReducer(s, { type: 'content_block_start', index: 1, content_block: { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'ok' } } as any)
    const tu = s.blocks.find((b) => b.type === 'tool_use') as any
    expect(tu.status).toBe('done')
    expect(tu.result).toBe('ok')
    // tool_result optager IKKE sin egen renderede blok-plads
    expect(s.blocks.filter(Boolean).some((b: any) => b.type === 'tool_result')).toBe(false)
  })

  it('bevarer den gamle system_event tool_result-sti (dual-read)', () => {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'tool_use', id: 'toolu_9', name: 'bash', input: {} } } as any)
    s = streamReducer(s, { type: 'system_event', kind: 'tool_result', payload: { tool_use_id: 'toolu_9', status: 'ok', result: 'via-legacy' } } as any)
    const tu = s.blocks.find((b) => b.type === 'tool_use') as any
    expect(tu.result).toBe('via-legacy')
  })
})
```

- [ ] **Step 2: Kør, bekræft fejl**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/streamReducer.test.ts`
Expected: FAIL — første test fejler (tool_result-content-blok ikke håndteret; sætter i stedet en tom blok på index 1).

- [ ] **Step 3: Implementér**

I `content_block_start`-casen (linje 72-79), tilføj en tool_result-gren FØR default-sætningen:

```typescript
    case 'content_block_start': {
      const blocks = state.blocks.slice()
      const cb = event.content_block
      if (cb.type === 'text') blocks[event.index] = { type: 'text', text: cb.text ?? '' }
      else if (cb.type === 'thinking') blocks[event.index] = { type: 'thinking', thinking: cb.thinking ?? '' }
      else if (cb.type === 'tool_use') blocks[event.index] = { type: 'tool_use', id: cb.id, name: cb.name, input: cb.input ?? {}, partialJson: '', status: 'running' }
      else if (cb.type === 'tool_result') {
        // Kanonisk wire: fold ind på matchende tool_use (optager ikke egen render-plads).
        const idx = blocks.findIndex((b) => b && b.type === 'tool_use' && b.id === cb.tool_use_id)
        if (idx >= 0) {
          const b = blocks[idx]
          if (b && b.type === 'tool_use') {
            blocks[idx] = { ...b, status: cb.is_error || cb.status === 'error' ? 'error' : 'done', result: cb.content ?? b.result }
          }
        }
        return { ...state, blocks }   // sæt IKKE blocks[event.index] — tool_result renderes ikke selvstændigt
      }
      return { ...state, blocks }
    }
```

(Den eksisterende `system_event` kind `tool_result`-sti i linje 105-120 forbliver UÆNDRET → dual-read.)

- [ ] **Step 4: Kør, bekræft grøn**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/streamReducer.test.ts`
Expected: PASS (2/2).

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/streamReducer.ts apps/jarvis-desk/src/lib/streamReducer.test.ts
git commit -m "feat(desk): reducer folder tool_result-content-blok (dual-read m. system_event)"
```

---

## Task 10: Klient-load — foretræk `content_json` (subagent)

**Files:**
- Modify: `apps/jarvis-desk/src/lib/api.ts:184-204` (`getSession`)
- Modify: `apps/jarvis-desk/src/lib/normalizeMessage.ts` (brug fold når content_json findes)
- Test: `apps/jarvis-desk/src/lib/normalizeMessage.test.ts` (opret hvis mangler)

Ved load: har beskeden `content_json` → `foldToolResults(content_json)`; ellers `stringToBlocks(content)` som i dag.

- [ ] **Step 1: Skriv den fejlende test**

```typescript
// apps/jarvis-desk/src/lib/normalizeMessage.test.ts
import { describe, it, expect } from 'vitest'
import { messageToBlocks } from './normalizeMessage'

describe('messageToBlocks', () => {
  it('bruger content_json (foldet) når til stede', () => {
    const msg = { role: 'assistant', content: 'svar', content_json: [
      { type: 'text', text: 'svar' },
      { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} },
      { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'ok' },
    ] }
    const blocks = messageToBlocks(msg as any)
    const tu = blocks.find((b: any) => b.type === 'tool_use') as any
    expect(tu.result).toBe('ok')  // tool-kort overlever reload
  })

  it('falder tilbage til stringToBlocks uden content_json', () => {
    const blocks = messageToBlocks({ role: 'assistant', content: 'ren tekst' } as any)
    expect(blocks).toEqual([{ type: 'text', text: 'ren tekst' }])
  })
})
```

- [ ] **Step 2: Kør, bekræft fejl**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/normalizeMessage.test.ts`
Expected: FAIL — `messageToBlocks` findes ikke.

- [ ] **Step 3: Implementér**

I `normalizeMessage.ts`, tilføj:

```typescript
import { foldToolResults } from './foldToolResults'
import type { ContentBlock } from './sseProtocol'

/** Vælg render-blokke for en server-besked: kanonisk content_json (foldet) hvis
 *  til stede, ellers legacy tekst → én tekst-blok. */
export function messageToBlocks(m: { content: string; content_json?: unknown }): ContentBlock[] {
  if (Array.isArray(m.content_json) && m.content_json.length > 0) {
    return foldToolResults(m.content_json as Array<Record<string, unknown>>)
  }
  return stringToBlocks(m.content)
}
```

I `api.ts` `getSession` (linje ~202), erstat `stringToBlocks(m.content)` med `messageToBlocks(m)`.

- [ ] **Step 4: Kør, bekræft grøn**

Run: `cd apps/jarvis-desk && npx vitest run src/lib/normalizeMessage.test.ts`
Expected: PASS (2/2).

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/lib/api.ts apps/jarvis-desk/src/lib/normalizeMessage.ts apps/jarvis-desk/src/lib/normalizeMessage.test.ts
git commit -m "feat(desk): getSession foretrækker content_json (foldet) ved reload"
```

---

## Task 11: `mergeServer` hviler på server-blokke (Claude inline, fragil)

**Files:**
- Modify: `apps/jarvis-desk/src/contexts/SessionContext.tsx` (`mergeServer`)
- Test: `apps/jarvis-desk/src/contexts/SessionContext.test.tsx` (behold de 13 eksisterende + 1 ny)

Når serveren leverer `content_json`, behøver `mergeServer` ikke re-injicere tool-blokke fra lokal state. v0.3.25's `localToolsByNorm`-fallback BEVARES for legacy-beskeder (uden content_json) og fjernes først i oprydnings-fasen.

- [ ] **Step 1: Skriv den nye fejlende test**

```typescript
  it('serverens content_json-baserede tool-kort overlever merge uden lokal re-injektion — Bjørn 9. jul', () => {
    // Server leverer nu FULDE blokke (via messageToBlocks i getSession-laget) →
    // mergeServer skal bevare dem uændret, ikke wipe dem til tekst.
    const server = [
      userMsg('srv-u', 'spm'),
      { id: 'srv-a', role: 'assistant' as const, created_at: 'now', parent_id: null,
        content: [
          { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {}, status: 'done', result: 'ok' },
          { type: 'text', text: 'svaret' },
        ] as unknown as { type: 'text'; text: string }[] },
    ]
    const merged = mergeServer([], server)
    const srv = merged.find((m) => m.id === 'srv-a')!
    const types = (srv.content as Array<{ type: string }>).map((b) => b.type)
    expect(types).toContain('tool_use')
  })
```

- [ ] **Step 2: Kør hele filen, bekræft ny fejler / andre grønne**

Run: `cd apps/jarvis-desk && npx vitest run src/contexts/SessionContext.test.tsx`
Expected: 13 eksisterende PASS; den nye enten PASS (hvis mergeServer allerede bevarer server-blokke) eller FAIL. Er den grøn uden ændring → dokumentér at server-blok-stien allerede virker og spring Step 3 over.

- [ ] **Step 3: Implementér (kun hvis nødvendigt)**

Hvis den nye test fejler: sørg for at `mergeServer` bevarer serverens `content`-blokke som de er når de indeholder ikke-tekst-blokke, og at `localToolsByNorm`-re-injektionen KUN kører for beskeder hvis server-kopi er tekst-only (legacy). Konkret guard:

```typescript
    // v0.3.25 re-injektion gælder KUN legacy tekst-only server-beskeder.
    // Har serveren allerede ikke-tekst-blokke (content_json-æra), lad dem være.
    const serverHasStructuredBlocks = (msg: { content?: Array<{ type?: string }> }) =>
      Array.isArray(msg.content) && msg.content.some((b) => b && b.type !== 'text')
    // ... i re-injektions-løkken: if (serverHasStructuredBlocks(srvMsg)) continue
```

- [ ] **Step 4: Kør hele filen, bekræft alle grønne**

Run: `cd apps/jarvis-desk && npx vitest run src/contexts/SessionContext.test.tsx`
Expected: PASS (14/14).

- [ ] **Step 5: Commit**

```bash
git add apps/jarvis-desk/src/contexts/SessionContext.tsx apps/jarvis-desk/src/contexts/SessionContext.test.tsx
git commit -m "feat(desk): mergeServer hviler på server content_json-blokke (legacy-fallback bevaret)"
```

---

## Task 12: Mobil-paritet (Claude inline)

**Files:**
- Modify: mobil-klientens reducer + session-load (stier bekræftes i denne task)
- Test: mobilens tilsvarende reducer/load-test

- [ ] **Step 1: Find mobil-klienten**

Run: `ls apps/ && grep -rl "content_block_start\|tool_result\|stringToBlocks" apps/ --include=*.ts --include=*.tsx | grep -iv jarvis-desk`
Expected: mobilens reducer/load-filer (fx `apps/jarvis-mobile/...` eller `apps/ui/...`). Findes INGEN separat mobil-reducer (mobil bruger samme REST + en simplere renderer) → dokumentér det og reducér denne task til: bekræft at mobilens session-load bruger `content_json` når til stede; ellers spring implementering over.

- [ ] **Step 2-4: Anvend samme dual-read-mønster**

Port `foldToolResults` + `messageToBlocks`-valget + reducer-tool_result-grenen (Task 8-10) til mobilens tilsvarende moduler. Skriv en reducer-test der spejler Task 9's to cases. Kør mobilens test-runner (verificér kommando i mobilens `package.json`).

- [ ] **Step 5: Commit**

```bash
git add apps/<mobil-sti>
git commit -m "feat(mobil): dual-read content_json + tool_result-content-blok (paritet m. desk)"
```

---

## Task 13: Fuld suite + deploy + live-verifikation (Claude inline)

**Files:** ingen kode — deploy + verifikation.

- [ ] **Step 1: Fuld backend-suite (grønt-gate)**

Run: `conda activate ai && python -m pytest -q`
Expected: PASS (samme baseline som før + de nye tests). Fejl → fiks før deploy.

- [ ] **Step 2: Fuld desk-suite + docs-drift**

Run: `cd apps/jarvis-desk && npx vitest run` (alle grønne)
Run: `conda activate ai && python scripts/api_docs_gen.py && python scripts/api_reference_gen.py` (routes/moduler ændret → regenerér; commit hvis diff)

- [ ] **Step 3: Klient først — byg + installér desk**

Bump `apps/jarvis-desk/package.json` version (jf. reference_mobile_build_versioncode / desk-deploy). Byg + `dpkg -i` + Bjørn lukker+genåbner appen. Byg/installér mobil tilsvarende. **Dette sker FØR server-flip** (klient-først-udrulning, spec §9).

- [ ] **Step 4: Server — push + deploy m. flag ON**

```bash
git push origin main
# på bs@10.0.0.39: git fetch && git pull --ff-only (merge hvis divergeret — Jarvis committer på container-main)
# verificér HEAD == pushed commit; sæt runtime-state structured_content_v2=on (default ON, men sæt eksplicit)
# genstart BEGGE: jarvis-api + jarvis-runtime
```

- [ ] **Step 5: Live-verifikation**

- Ny tur m. tool-kald i desk (chat OG code mode) → tool-kort synligt live → reload session → **kort overlever**; gentag code-mode poll-refresh → overlever.
- Gammel session → tool-resultater rekonstrueret (best-effort), ingen crash.
- `curl`/`jc` GET på en ny session → `content_json` til stede pr. assistant-besked.
- Flip flag OFF → ny besked persisteres tekst-kun + tool_result streames som system_event igen (revert virker). Flip ON igen.

- [ ] **Step 6: Commit oprydnings-note (ikke selve oprydningen)**

Efter stabil ON: opret en opfølgnings-note (memory eller spawn_task) om at fjerne klient-side `system_event`-tool_result-sti + v0.3.25 `localToolsByNorm` i en senere oprydnings-fase. Kerne-leverancen er færdig.

---

## Self-review checklist (udført ved plan-skrivning)

- **Spec-dækning:** §4 data-model → Task 1-3; §5 skrive-sti → Task 6; §6 serve-on-read → Task 1+4; §7 stream → Task 7; §8 klient → Task 8-11; §9 reversibilitet/udrulning → Task 5+13; §10 test → i hver task; §11 blast-radius → tekst-projektion (Task 1) + dual-read (Task 9) + flag (Task 5).
- **Type-konsistens:** blok-format-kontrakten (øverst) er identisk i Task 1/6 (server) og Task 8-10 (klient: `foldToolResults`); `content_json` som JSON-streng i DB (Task 3), parset til array i GET (Task 4), array på klienten (Task 10).
- **Ingen placeholders:** de tre "Step 3.5"-verifikationer (parse_tool_result_reference-nøgler, loader-navn, get_runtime_state_value, VisibleRun-variabelnavne, mobil-sti) er EKSPLICITTE in-task grounding-trin mod navngivne filer — ikke vage TODO'er; hver har en konkret fallback.
```
