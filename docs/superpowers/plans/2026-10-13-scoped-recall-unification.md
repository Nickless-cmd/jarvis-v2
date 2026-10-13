# Scoped Recall Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended for this sequential privacy migration) or superpowers:subagent-driven-development when explicitly requested to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every active recall path current-query relevant, strictly user-scoped, observable, migratable, and controllable by owner killswitches.

**Architecture:** `core.services.recall.recall()` becomes the sole query-ranked coordinator for visible and general-purpose recall, while specialized tools remain thin scoped adapters. Auto/associative recall remains a separate behavioral layer but stores state per user and passes a current-query relevance gate before prompt injection. A signed, watermarked migration adds ownership without rewriting memory content; runtime and migration killswitches are independent.

**Tech Stack:** Python 3.11+, SQLite/WAL, ContextVar user scope, NumPy cosine ranking, pytest, existing eventbus and runtime-state APIs.

**Spec:** `docs/superpowers/specs/2026-10-13-scoped-recall-unification-design.md`

## Global Constraints

- `scoped_recall_enabled` defaults OFF; OFF must never fall back to legacy global recall.
- `scoped_recall_migration_enabled` defaults OFF and returns to OFF after apply success or failure.
- Migration changes ownership/provenance only; memory text, salience, emotion and lifecycle status remain unchanged.
- An explicit or uniquely resolved non-owner identity beats owner fallback; conflicting identities are quarantined.
- Legacy rows without a match to another user are assigned to owner, per the approved design.
- Private data with no runtime scope fails closed; daemon/system work binds owner explicitly.
- Recall telemetry contains scalar metadata only: no query, memory text, IDs or user identity.
- Recall-focused tests must enable the flag explicitly in a local fixture or test setup; never add a production or global-test default that silently turns recall ON.
- No new external dependency or vector database.
- Preserve existing imports through re-exports when splitting `core/runtime/db_cognitive.py` under the Boy Scout Rule.
- Use `scripts/commit_with_attribution.py`; never use raw `git commit`.

## File Structure

- Create `core/services/scoped_recall_policy.py`: the two runtime flags, fail-closed current-user/session-owner scope resolution and standardized disabled results.
- Create `core/services/recall_observability.py`: scalar-only recall outcome emission.
- Create `core/runtime/db_experiential_memory.py`: extracted and scoped experiential-memory persistence.
- Create `core/services/recall_ownership_migration.py`: classification, signed reports, apply and rollback.
- Create `scripts/migrate_recall_ownership.py`: dry-run/apply/rollback CLI.
- Modify `core/runtime/db_embeddings.py` and `core/services/semantic_memory.py`: filter user and lifecycle before vector ranking.
- Modify `core/services/recall.py`: current-query parallel coordinator, brain visibility and observability.
- Modify prompt recall adapters: one current-query bundle; retire stale session-only cache delivery.
- Modify associative recall/scheduler: per-user active state, context propagation and current-query gate.
- Modify experiential, reasoning, sensory queue and cross-agent stores: explicit ownership end to end.

## Review Focus

1. **Runtime flag missing or malformed:** recall remains OFF and private paths fail closed; covered in Task 1.
2. **Source finishes after the coordinator deadline:** ready sources still return as `partial`, late data is not cached into another query; covered in Task 3.
3. **Same source record appears under two users during migration:** the row is quarantined rather than owner-assigned; covered in Task 9.
4. **Member-triggered background thread loses ContextVar:** the captured explicit user ID still scopes the write/read; covered in Tasks 5, 6 and 8.
5. **Existing terminal or other-user embedding has the highest cosine score:** it is absent before top-K and cannot expose an opaque source ID; covered in Task 2.

---

### Task 1: Add fail-closed recall policy and killswitches

**Files:**
- Create: `core/services/scoped_recall_policy.py`
- Create: `tests/test_scoped_recall_policy.py`

**Interfaces:**
- Produces: `recall_enabled() -> bool`, `recall_migration_enabled() -> bool`, `set_recall_enabled(bool) -> None`, `set_recall_migration_enabled(bool) -> None`, `require_private_scope(session_id: str = "") -> str`, `disabled_result(path: str) -> dict[str, object]`.
- Consumes: `core.runtime.db_core.get_runtime_state_value`, `set_runtime_state_value`, `current_user_id`, `current_session_id`, and `chat_sessions.get_session_owner`.

- [ ] **Step 1: Write failing policy tests**

```python
def test_recall_defaults_off_when_runtime_flag_missing(monkeypatch):
    monkeypatch.setattr(P, "get_runtime_state_value", lambda key, default=None: default)
    assert P.recall_enabled() is False

def test_private_scope_fails_closed_without_bound_user(monkeypatch):
    monkeypatch.setattr(P, "current_user_id", lambda: "")
    monkeypatch.setattr(P, "current_session_id", lambda: "")
    with pytest.raises(P.MissingRecallScope):
        P.require_private_scope()

def test_private_scope_can_use_authoritative_session_owner(monkeypatch):
    monkeypatch.setattr(P, "current_user_id", lambda: "")
    monkeypatch.setattr(P, "current_session_id", lambda: "session-owner")
    monkeypatch.setattr(P, "get_session_owner", lambda sid: "owner-1")
    assert P.require_private_scope() == "owner-1"

def test_disabled_result_has_no_private_payload():
    assert P.disabled_result("recall") == {
        "status": "disabled", "path": "recall", "results": [], "count": 0,
    }
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `pytest -q tests/test_scoped_recall_policy.py`

Expected: collection fails because `core.services.scoped_recall_policy` does not exist.

- [ ] **Step 3: Implement the policy module**

```python
RECALL_FLAG = "scoped_recall_enabled"
MIGRATION_FLAG = "scoped_recall_migration_enabled"

class MissingRecallScope(RuntimeError):
    pass

def recall_enabled() -> bool:
    return get_runtime_state_value(RECALL_FLAG, False) is True

def require_private_scope(session_id: str = "") -> str:
    uid = str(current_user_id() or "").strip()
    sid = str(session_id or current_session_id() or "").strip()
    if not uid and sid:
        uid = str(get_session_owner(sid) or "").strip()
    if not uid:
        raise MissingRecallScope("private recall requires explicit user scope")
    return uid
```

`set_recall_migration_enabled()` and `set_recall_enabled()` must store actual booleans. Do not parse arbitrary truthy strings as enabled.

- [ ] **Step 4: Run focused tests and policy-adjacent tests**

Run: `pytest -q tests/test_scoped_recall_policy.py tests/test_recall_scheduler.py tests/test_recall_tool.py`

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add -- core/services/scoped_recall_policy.py tests/test_scoped_recall_policy.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(memory): add scoped recall killswitches' --path core/services/scoped_recall_policy.py --path tests/test_scoped_recall_policy.py
```

---

### Task 2: Filter semantic candidates before vector top-K

**Files:**
- Modify: `core/runtime/db_embeddings.py:104-130`
- Modify: `core/services/semantic_memory.py:515-570`
- Modify: `core/tools/recall_memory_tools.py:53-112`
- Create: `tests/test_semantic_memory_scope.py`
- Modify: `tests/test_recall.py`

**Interfaces:**
- Consumes: `require_private_scope()` and existing source resolvers.
- Produces: `list_embeddings(..., user_id: str | None, private_statuses: tuple[str, ...] | None)` and a `semantic_memory.search()` that returns only resolvable records from the active user.

- [ ] **Step 1: Write failing scope and lifecycle tests**

```python
def test_private_embeddings_are_scoped_and_terminal_rows_never_enter_top_k(
    isolated_runtime, monkeypatch
):
    seed_private_brain("mine-active", user_id="u1", status="active", vector=[0.8, 0.2])
    seed_private_brain("mine-archived", user_id="u1", status="archived", vector=[1.0, 0.0])
    seed_private_brain("other-active", user_id="u2", status="active", vector=[1.0, 0.0])
    bind_user(monkeypatch, "u1")
    monkeypatch.setattr(S, "_embed_ollama", lambda query: np.array([1.0, 0.0]))
    hits = S.search("query", source_tables=["private_brain_records"], limit=1, min_score=0)
    assert [h["source_id"] for h in hits] == ["mine-active"]

def test_recall_memories_drops_unresolvable_hits(monkeypatch):
    monkeypatch.setattr(R.semantic_memory, "search", lambda *a, **k: [
        {"source_id": "opaque", "source_table": "private_brain_records", "record": None}
    ])
    assert R._exec_recall_memories({"query": "x"})["items"] == []
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_semantic_memory_scope.py tests/test_recall.py`

Expected: archived/other-user embeddings win current top-K or the new fixtures fail because the scoped query API is absent.

- [ ] **Step 3: Add database-side source predicates**

Implement SQL predicates before rows are decoded into the NumPy matrix:

```python
if user_id and source_tables == ["private_brain_records"]:
    where.append(
        "EXISTS (SELECT 1 FROM private_brain_records p "
        "WHERE p.record_id=memory_embeddings.source_id "
        "AND p.user_id=? AND p.status IN (?,?,?,?))"
    )
    params.extend([user_id, "active", "settling", "fading", "completed"])
```

Add the equivalent `EXISTS` predicate for `sensory_memories.user_id`. Mixed-source searches must build an OR-clause per registered source; unknown private sources are excluded until registered with an explicit policy.

- [ ] **Step 4: Make semantic search fail closed and adapters omit unresolved hits**

```python
uid = require_private_scope()
rows = list_embeddings(
    modalities=modalities,
    source_tables=source_tables,
    user_id=uid,
    private_statuses=("active", "settling", "fading", "completed"),
)
```

In `recall_memory_tools`, check `recall_enabled()` before querying, then append an item only when `record` is a dict with permitted content. Preserve the old return shape for valid hits and return `disabled_result("semantic_memory")` when OFF.

- [ ] **Step 5: Run semantic, tool and privacy tests**

Run: `pytest -q tests/test_semantic_memory_scope.py tests/test_recall.py tests/test_sensory_tools.py tests/test_tool_contract_shadow.py`

Expected: PASS.

- [ ] **Step 6: Commit Task 2**

```bash
git add -- core/runtime/db_embeddings.py core/services/semantic_memory.py core/tools/recall_memory_tools.py tests/test_semantic_memory_scope.py tests/test_recall.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix(memory): scope semantic recall before ranking' --path core/runtime/db_embeddings.py --path core/services/semantic_memory.py --path core/tools/recall_memory_tools.py --path tests/test_semantic_memory_scope.py --path tests/test_recall.py
```

---

### Task 3: Make `recall()` current-query, parallel, visibility-aware and observable

**Files:**
- Create: `core/services/recall_observability.py`
- Modify: `core/services/recall.py:1-343`
- Modify: `core/services/memory_recall_telemetry.py:1-140`
- Modify: `core/runtime/db_fts.py:140-252`
- Modify: `tests/test_recall.py`
- Modify: `tests/services/test_memory_recall_telemetry.py`
- Modify: `tests/test_db_fts.py`

**Interfaces:**
- Consumes: Task 1 policy and Task 2 scoped semantic search.
- Produces: `recall(..., deadline_s: float = 3.5)` with `delivery_status` in `delivered|empty|partial|timeout|disabled|error`; `emit_recall_outcome(...)` scalar-only.

- [ ] **Step 1: Write failing parallel/deadline, visibility and telemetry tests**

```python
def test_recall_returns_ready_sources_as_partial_at_deadline(monkeypatch):
    funcs = {
        "workspace": lambda q, k: [{"source": "workspace", "score": .9, "text": "match", "ref": "a"}],
        "brain": blocking_source,
    }
    with patch.dict(R.SOURCE_FUNCS, funcs, clear=True):
        out = R.recall("match", sources=list(funcs), deadline_s=.05, min_score=0)
    assert out["delivery_status"] == "partial"
    assert [x["source"] for x in out["results"]] == ["workspace"]

def test_member_brain_recall_uses_public_safe(monkeypatch):
    bind_user(monkeypatch, "member-1", role="member")
    seen = {}
    monkeypatch.setattr(jarvis_brain, "search_brain_scored", capture_visibility(seen))
    R._source_brain("query", 3)
    assert seen["visibility_ceiling"] == "public_safe"

def test_recall_event_contains_no_query_or_identity(monkeypatch):
    payload = capture_recall_event(monkeypatch)
    R.recall("private words", sources=["workspace"])
    assert not ({"query", "user_id", "session_id", "source_id", "text"} & payload.keys())

def test_fts_recall_excludes_unowned_and_quarantined_sessions(isolated_runtime):
    seed_session_summary("owned", message_users=["u1"])
    seed_session_summary("unowned", message_users=[])
    seed_conflicted_session("conflict", users=["u1", "u2"])
    with bound_user("u1"):
        hits = search_session_summaries("shared term")
    assert [h["session_id"] for h in hits] == ["owned"]
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_recall.py tests/services/test_memory_recall_telemetry.py tests/test_db_fts.py`

Expected: no `deadline_s`/`delivery_status`, sequential blocking remains, and success telemetry is absent.

- [ ] **Step 3: Implement the scalar-only observer**

```python
ALLOWED_FIELDS = {
    "path", "delivery_status", "result_count", "latency_ms", "top_score",
    "filtered_scope", "filtered_status", "source_count", "cache_hit",
}

def emit_recall_outcome(**metadata: object) -> None:
    payload = {k: metadata[k] for k in ALLOWED_FIELDS if k in metadata}
    event_bus.publish("memory.recall", payload)
```

Tests must inspect the published payload, not merely mock that the function was called.

- [ ] **Step 4: Parallelize source gathering with copied contexts and a total deadline**

```python
pool = ThreadPoolExecutor(max_workers=min(len(wanted), 6))
try:
    futures = {
        pool.submit(contextvars.copy_context().run, SOURCE_FUNCS[name], q, k): name
        for name in wanted
    }
    done, pending = wait(futures, timeout=deadline_s)
    for future in done:
        collect_source_result(future, futures[future], candidates, errors)
    for future in pending:
        future.cancel()
finally:
    pool.shutdown(wait=False, cancel_futures=True)
```

Do not use the executor as a context manager: `ThreadPoolExecutor.__exit__` waits for late work. Use the explicit `finally` shutdown above so a late enrichment source cannot delay return. Derive `partial` when at least one requested source missed the deadline and `timeout` when none completed.

- [ ] **Step 5: Gate brain visibility by the current principal**

```python
def _brain_visibility_ceiling() -> str:
    return "personal" if require_private_scope() == owner_user_id() else "public_safe"
```

Pass this value to `search_brain_scored`. Do not infer owner from a missing context.

- [ ] **Step 6: Make chat/session FTS strict before recall can be enabled**

Change both FTS queries from “exclude sessions proven to belong to someone else” to “include only sessions proven to belong to this user.” Also exclude any session listed in `recall_ownership_quarantine`. Build that exclusion clause only when the quarantine table exists, so isolated pre-migration databases still execute; Task 9 creates the table in production before recall is enabled. Because the rollout keeps `scoped_recall_enabled=OFF` until Task 9 migrates legacy rows, there is no compatibility window where unowned history needs to remain visible.

```sql
AND EXISTS (
  SELECT 1 FROM chat_messages own
  WHERE own.session_id=s.session_id AND own.user_id=?
)
AND NOT EXISTS (
  SELECT 1 FROM chat_messages foreign_row
  WHERE foreign_row.session_id=s.session_id
    AND foreign_row.user_id IS NOT NULL AND foreign_row.user_id<>''
    AND foreign_row.user_id<>?
)
```

- [ ] **Step 7: Run recall and telemetry tests**

Run: `pytest -q tests/test_recall.py tests/test_recall_tool.py tests/services/test_memory_recall_telemetry.py tests/test_jarvis_brain_visibility.py tests/test_db_fts.py`

Expected: PASS with no private payload in telemetry.

- [ ] **Step 8: Commit Task 3**

```bash
git add -- core/services/recall_observability.py core/services/recall.py core/services/memory_recall_telemetry.py core/runtime/db_fts.py tests/test_recall.py tests/services/test_memory_recall_telemetry.py tests/test_db_fts.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(memory): unify current-turn recall delivery' --path core/services/recall_observability.py --path core/services/recall.py --path core/services/memory_recall_telemetry.py --path core/runtime/db_fts.py --path tests/test_recall.py --path tests/services/test_memory_recall_telemetry.py --path tests/test_db_fts.py
```

---

### Task 4: Replace stale prompt recall with one current-query bundle

**Files:**
- Modify: `core/services/prompt_sections/memory_recall.py:280-337`
- Modify: `core/services/prompt_memory_recall.py:1-115`
- Modify: `core/services/past_context_router.py:1-70`
- Modify: `core/services/visible_inner_life.py:340-378`
- Modify: `tests/test_memory_recall.py`
- Modify: `tests/test_prompt_memory_recall.py`
- Modify: `tests/test_past_context_router.py`
- Modify: `tests/test_prompt_contract_memory_group.py`
- Create: `tests/test_visible_inner_life_recall.py`

**Interfaces:**
- Consumes: Task 3 `recall()` and Task 1 killswitch.
- Produces: `_visible_memory_recall_bundle_section(session_id, user_message, compact)` containing only current-query results; compatibility no-ops for retired background cache and duplicate past-context router.

- [ ] **Step 1: Write failing prompt relevance tests**

```python
def test_visible_bundle_passes_the_current_message_to_recall(monkeypatch):
    seen = {}
    monkeypatch.setattr(recall_service, "recall", lambda query, **kw: seen.setdefault("query", query) or result())
    section = M._visible_memory_recall_bundle_section(
        session_id="s1", user_message="den aktuelle besked", compact=False,
    )
    assert seen["query"] == "den aktuelle besked"
    assert "seneste uvedkommende private post" not in (section or "")

def test_background_adapter_never_serves_previous_query(monkeypatch):
    out, derived = [], []
    PM.append_background_recall("query B", "s1", out, derived, lambda *a: None)
    assert out == []
    assert derived == []

def test_inner_life_does_not_recall_from_global_latest_session(monkeypatch):
    monkeypatch.setattr(V, "_latest_user_message_text", fail_if_called)
    monkeypatch.setattr(V, "recall", fail_if_called)
    assert V._recall_hints_line() is None
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_memory_recall.py tests/test_prompt_memory_recall.py tests/test_past_context_router.py tests/test_prompt_contract_memory_group.py`

Expected: current bundle ignores the message for private continuity and the background adapter serves session-only cached results.

- [ ] **Step 3: Build the bundle from current `recall()` output**

```python
result = recall(user_message, limit=3 if compact else 5, session_id=session_id)
if result.get("delivery_status") in {"disabled", "timeout", "error"}:
    return None
lines = ["Memory recall bundle:"]
for item in result.get("results", []):
    lines.append(f"- [{item['source']}] {_clip_line(item['text'], limit=180)}")
```

Keep recent tool observations only when they belong to the current session and are under the existing 30-minute limit. Remove unconditional latest-private-brain excerpts and pending candidates from this bundle; those stores remain accessible through their dedicated governed flows.

- [ ] **Step 4: Retire stale and duplicate adapters without touching the oversized prompt composer**

Keep `append_background_recall` and exported cache names for import compatibility, but make the function a documented no-op. Make `build_past_context_section` return empty when scoped recall is enabled because `recall()` already adds chat on context cues; when disabled it also returns empty rather than invoking legacy recall. Make `_recall_hints_line()` a compatibility no-op and remove its dependency on `most_recent_session_id()`: global inner-life assembly has no current user query or safe session principal, so it must never perform dynamic private recall.

- [ ] **Step 5: Run prompt tests**

Run: `pytest -q tests/test_memory_recall.py tests/test_prompt_memory_recall.py tests/test_past_context_router.py tests/test_prompt_contract_memory_group.py tests/test_visible_inner_life_recall.py tests/test_context_prompt_improvements.py`

Expected: PASS; no test observes a previous-query cache result.

- [ ] **Step 6: Commit Task 4**

```bash
git add -- core/services/prompt_sections/memory_recall.py core/services/prompt_memory_recall.py core/services/past_context_router.py core/services/visible_inner_life.py tests/test_memory_recall.py tests/test_prompt_memory_recall.py tests/test_past_context_router.py tests/test_prompt_contract_memory_group.py tests/test_visible_inner_life_recall.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix(prompt): use current-query recall only' --path core/services/prompt_sections/memory_recall.py --path core/services/prompt_memory_recall.py --path core/services/past_context_router.py --path core/services/visible_inner_life.py --path tests/test_memory_recall.py --path tests/test_prompt_memory_recall.py --path tests/test_past_context_router.py --path tests/test_prompt_contract_memory_group.py --path tests/test_visible_inner_life_recall.py
```

---

### Task 5: Isolate auto/associative recall per user

**Files:**
- Modify: `core/services/associative_recall.py:28-430`
- Modify: `core/services/recall_scheduler.py:1-103`
- Modify: `tests/test_associative_recall.py`
- Modify: `tests/test_recall_scheduler.py`

**Interfaces:**
- Consumes: Task 1 explicit scope and killswitch.
- Produces: per-user active state, `build_recall_prompt_section(query: str)`, per-user scheduler locks and copied ContextVar execution.

- [ ] **Step 1: Write failing user-isolation, relevance and thread-context tests**

```python
def test_active_associations_never_cross_users(monkeypatch):
    with bound_user("u1"):
        AR._add_to_active(memory("u1-topic"))
    with bound_user("u2"):
        assert AR.build_recall_prompt_section("u1-topic") == ""

def test_association_must_match_current_query(monkeypatch):
    with bound_user("u1"):
        AR._add_to_active(memory("database migration"))
        assert AR.build_recall_prompt_section("middag og vejret") == ""
        assert "database migration" in AR.build_recall_prompt_section("database migration")

def test_scheduler_copies_member_context(monkeypatch):
    with bound_user("member-1"):
        assert RS.trigger_background_recall("aktuel besked") is True
    assert completed.wait(1)
    assert seen_user_id == "member-1"

def test_system_tick_binds_configured_owner_instead_of_implicit_fallback(monkeypatch):
    clear_current_principal()
    RS.tick_associative_recall()
    assert seen_user_id == configured_owner_id()
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_associative_recall.py tests/test_recall_scheduler.py`

Expected: global `_active_memories` is visible across bound users and scheduler thread resolves implicit owner.

- [ ] **Step 3: Add user ownership to active recall persistence**

Add `user_id TEXT` to `recall_active_memories`, guarded by `PRAGMA table_info`, and index `(user_id, score DESC)`. All load/upsert/delete/clear operations require `require_private_scope()` and include `user_id` in their SQL predicate. Legacy NULL rows are not loaded while the migration gate is pending.

```python
_active_memories_by_user: dict[str, dict[str, dict[str, Any]]] = {}

def _active_state() -> dict[str, dict[str, Any]]:
    uid = require_private_scope()
    return _active_memories_by_user.setdefault(uid, _load_active_memories_from_db(uid))
```

- [ ] **Step 4: Add a deterministic current-query relevance gate**

Use normalized significant terms from query, topic and narrative. Require at least one shared term, or a fused lexical coverage of at least 0.25 for multi-term queries. Do not call an LLM in the prompt hot path.

```python
def _association_matches(query: str, memory: dict[str, Any]) -> bool:
    q = _significant_terms(query)
    candidate = _significant_terms(f"{memory.get('topic','')} {memory.get('narrative','')}")
    return bool(q and candidate and q.intersection(candidate))
```

- [ ] **Step 5: Copy context and deduplicate scheduler work per user**

```python
uid = require_private_scope()
ctx = contextvars.copy_context()
threading.Thread(
    target=lambda: ctx.run(_run_recall, uid, msg, emo),
    name=f"background-recall-{hash_uid(uid)}",
    daemon=True,
).start()
```

Store running state as `set[str]` of user IDs. Check `recall_enabled()` before scheduling or writing active state. The system-only periodic tick must explicitly bind the configured owner before reading or writing owner recall state; `require_private_scope()` itself never falls back to owner.

- [ ] **Step 6: Run associative tests and cognitive assembly regression tests**

Run: `pytest -q tests/test_associative_recall.py tests/test_recall_scheduler.py tests/test_internal_cognitive_surfaces.py tests/test_context_prompt_improvements.py`

Expected: PASS; the no-query cognitive-state call injects no private associations.

- [ ] **Step 7: Commit Task 5**

```bash
git add -- core/services/associative_recall.py core/services/recall_scheduler.py tests/test_associative_recall.py tests/test_recall_scheduler.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix(memory): isolate associative recall by user' --path core/services/associative_recall.py --path core/services/recall_scheduler.py --path tests/test_associative_recall.py --path tests/test_recall_scheduler.py
```

---

### Task 6: Extract and scope experiential-memory persistence

**Files:**
- Create: `core/runtime/db_experiential_memory.py`
- Modify: `core/runtime/db_cognitive.py:1497-1635`
- Modify: `core/runtime/db.py:954-1020`
- Modify: `core/services/experiential_memory.py:70-155`
- Modify: `tests/test_associative_recall.py`
- Create: `tests/test_experiential_memory_scope.py`

**Interfaces:**
- Consumes: Task 1 explicit scope.
- Produces: existing DB function names re-exported unchanged, now with `user_id` persistence/filtering; `create_experiential_memory_async(**kwargs)` captures explicit user identity.

- [ ] **Step 1: Extract the natural experiential DB unit before changing logic**

Move these functions verbatim from the 2,090-line `db_cognitive.py` into `db_experiential_memory.py`: `_ensure_cognitive_experiential_memories_table`, `insert_cognitive_experiential_memory`, `reinforce_experiential_memory`, `list_cognitive_experiential_memories`, `get_experiential_memory_candidates`. Re-export them from `db_cognitive.py`, preserving `core.runtime.db` imports.

```python
from core.runtime.db_experiential_memory import (
    _ensure_cognitive_experiential_memories_table,
    insert_cognitive_experiential_memory,
    reinforce_experiential_memory,
    list_cognitive_experiential_memories,
    get_experiential_memory_candidates,
)
```

- [ ] **Step 2: Run existing tests after the pure extraction**

Run: `pytest -q tests/test_associative_recall.py tests/test_memory_recall_engine.py`

Expected: PASS with no behavior change.

- [ ] **Step 3: Write failing ownership and async-context tests**

```python
def test_experiential_candidates_are_user_scoped(isolated_runtime):
    with bound_user("u1"):
        insert_cognitive_experiential_memory(memory_id="m1", narrative="one")
    with bound_user("u2"):
        insert_cognitive_experiential_memory(memory_id="m2", narrative="two")
        assert [m["memory_id"] for m in get_experiential_memory_candidates()] == ["m2"]

def test_async_capture_keeps_member_identity(monkeypatch):
    with bound_user("member-1"):
        EM.create_experiential_memory_async(**run_payload())
    assert wait_for_write_user() == "member-1"
```

- [ ] **Step 4: Run and verify RED**

Run: `pytest -q tests/test_experiential_memory_scope.py`

Expected: both users see the same global rows and the async worker loses the member context.

- [ ] **Step 5: Add schema scope and explicit async propagation**

Add `user_id TEXT` plus `(user_id, created_at DESC)` index. New inserts stamp `require_private_scope()`; list, candidate and reinforce SQL include `user_id=?`. Capture the user ID before starting a background thread and bind it explicitly inside the worker using `user_context(discord_id=user_id)`.

- [ ] **Step 6: Run experiential and associative tests**

Run: `pytest -q tests/test_experiential_memory_scope.py tests/test_associative_recall.py tests/test_memory_hierarchy.py`

Expected: PASS.

- [ ] **Step 7: Commit Task 6**

```bash
git add -- core/runtime/db_experiential_memory.py core/runtime/db_cognitive.py core/runtime/db.py core/services/experiential_memory.py tests/test_experiential_memory_scope.py tests/test_associative_recall.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix(memory): scope experiential memories by user' --path core/runtime/db_experiential_memory.py --path core/runtime/db_cognitive.py --path core/runtime/db.py --path core/services/experiential_memory.py --path tests/test_experiential_memory_scope.py --path tests/test_associative_recall.py
```

---

### Task 7: Scope and make reasoning recall genuinely query-relevant

**Files:**
- Modify: `core/services/reasoning_store.py:20-255`
- Modify: `core/tools/reasoning_store_tools.py:15-65`
- Create: `tests/test_reasoning_recall_scope.py`
- Modify: `tests/test_learning_capture_wiring.py`

**Interfaces:**
- Consumes: Task 1 scope and killswitch.
- Produces: `capture_conclusion(..., user_id: str | None = None)` stamped to a principal and `recall_reasoning()` that ranks by embedding when available, otherwise bounded lexical relevance.

- [ ] **Step 1: Write failing user-scope and lexical fallback tests**

```python
def test_reasoning_recall_never_returns_another_users_row(isolated_runtime):
    seed_reasoning("u1", "relevant database migration", created_at="2026-01-01")
    seed_reasoning("u2", "relevant database migration", created_at="2026-10-01")
    with bound_user("u1"):
        rows = recall_reasoning(query_text="database migration")
    assert {r["user_id"] for r in rows} == {"u1"}

def test_query_without_embeddings_prefers_older_relevant_over_newer_noise(isolated_runtime):
    seed_reasoning("u1", "database migration preserves owner scope", embedding=[])
    seed_reasoning("u1", "weather was quiet", embedding=[])
    with bound_user("u1"):
        rows = recall_reasoning(query_text="owner database migration", limit=1)
    assert "database migration" in rows[0]["conclusion_text"]
    assert rows[0]["ranking_method"] == "lexical"
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_reasoning_recall_scope.py tests/test_learning_capture_wiring.py`

Expected: schema lacks `user_id` and newest rows win regardless of query.

- [ ] **Step 3: Add scoped schema and writes**

Add `user_id TEXT` and `(user_id, created_at DESC)` index in `_ensure_table`. Resolve explicit `user_id` first, otherwise require current scope. Include `user_id` in event metadata only as a boolean `owner_scoped`; never publish the identity.

- [ ] **Step 4: Add bounded query ranking**

Fetch at most `max(100, limit * 20)` scoped candidates inside the date/confidence filters. If a query embedding and stored embedding are available, use cosine. Otherwise compute normalized significant-term coverage and discard zero-overlap rows when `query_text` is non-empty.

```python
entry["score"] = lexical_coverage(query_text, entry["conclusion_text"] + " " + entry["context"])
entry["ranking_method"] = "lexical"
```

The tool description must say “relevance-ranked” rather than “semantic” unless the response's `ranking_method` is `embedding`. `recall_reasoning` checks `recall_enabled()` before reading and returns the standardized disabled shape when OFF; capture remains governed by its existing write policy and explicit principal rather than being silently reclassified as recall.

- [ ] **Step 5: Run reasoning tests**

Run: `pytest -q tests/test_reasoning_recall_scope.py tests/test_learning_capture_wiring.py tests/test_tool_catalog.py`

Expected: PASS.

- [ ] **Step 6: Commit Task 7**

```bash
git add -- core/services/reasoning_store.py core/tools/reasoning_store_tools.py tests/test_reasoning_recall_scope.py tests/test_learning_capture_wiring.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix(memory): scope and rank reasoning recall' --path core/services/reasoning_store.py --path core/tools/reasoning_store_tools.py --path tests/test_reasoning_recall_scope.py --path tests/test_learning_capture_wiring.py
```

---

### Task 8: Preserve ownership through sensory queue and cross-agent memory

**Files:**
- Modify: `core/tools/sensory_tools.py:79-110`
- Modify: `core/services/memory_write_queue.py:77-350`
- Modify: `core/services/cross_agent_memory.py:30-150`
- Modify: `core/services/agent_observation_compressor.py:65-175`
- Modify: `tests/test_sensory_tools.py`
- Create: `tests/test_memory_write_queue_scope.py`
- Modify: `tests/test_cross_agent_memory.py`

**Interfaces:**
- Consumes: Task 1 explicit scope.
- Produces: queue payloads with `user_id`; `_process_item` bound to that user; user-stamped and user-filtered agent observations.

- [ ] **Step 1: Write failing queue and cross-agent isolation tests**

```python
def test_sensory_queue_payload_carries_member_user(monkeypatch):
    with bound_user("member-1"):
        _exec_record_sensory_memory({"modality": "visual", "content": "et tydeligt indtryk"})
    assert captured_payload["user_id"] == "member-1"

def test_queue_processor_binds_payload_user(monkeypatch):
    ok, _ = Q._process_item("sensory", {**sensory_payload(), "user_id": "member-1"}, 0)
    assert ok is True
    assert recorded_user == "member-1"

def test_cross_agent_recall_is_per_user(monkeypatch):
    seed_observation("u1", "alpha database")
    seed_observation("u2", "alpha private")
    with bound_user("u1"):
        rows = CAM.cross_agent_recall(query="alpha", requesting_role="researcher")["results"]
    assert {r["preview"] for r in rows} == {"alpha database"}

def test_member_cannot_enqueue_owner_brain_write(monkeypatch):
    with bound_user("member-1", role="member"):
        result = Q.enqueue("brain", brain_payload())
    assert result["status"] == "denied"
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_sensory_tools.py tests/test_memory_write_queue_scope.py tests/test_cross_agent_memory.py`

Expected: queue payload has no user and agent observations are global.

- [ ] **Step 3: Carry explicit ownership through the queue**

At enqueue time add `user_id=require_private_scope()`. At process time reject a private payload without `user_id`; otherwise bind `user_context(discord_id=user_id)` around `_process_sensory`, `_process_brain` or `_process_sidecar`. Reject `brain` queue items unless the bound principal is the configured owner; a member's personal memories may use the sensory/sidecar paths but may not write Jarvis' owner-only brain.

```python
with user_context(discord_id=user_id):
    return processor(payload, retry_count)
```

Do not let daemon default-owner behavior substitute for a missing payload principal.

- [ ] **Step 4: Stamp and filter agent observations**

Extend `compress_agent_run(..., user_id: str | None = None)` so an agent orchestrator can pass the originating principal explicitly; otherwise it stores `user_id=require_private_scope()`. The tool wrapper does not accept a caller-supplied foreign identity and uses the bound principal. `_all_observations`, list/get/search and cross-agent recall return only rows for the current user. New private reads with no explicit user return nothing. Legacy rows remain hidden until Task 9 migration. All specialized recall entrypoints in this task check `recall_enabled()` and return the standardized disabled shape without reading or mutating private recall state.

- [ ] **Step 5: Run specialized recall tests**

Run: `pytest -q tests/test_sensory_tools.py tests/test_memory_write_queue_scope.py tests/test_cross_agent_memory.py tests/test_agent_memory_tools.py`

Expected: PASS.

- [ ] **Step 6: Commit Task 8**

```bash
git add -- core/tools/sensory_tools.py core/services/memory_write_queue.py core/services/cross_agent_memory.py core/services/agent_observation_compressor.py tests/test_sensory_tools.py tests/test_memory_write_queue_scope.py tests/test_cross_agent_memory.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix(memory): preserve ownership in async recall stores' --path core/tools/sensory_tools.py --path core/services/memory_write_queue.py --path core/services/cross_agent_memory.py --path core/services/agent_observation_compressor.py --path tests/test_sensory_tools.py --path tests/test_memory_write_queue_scope.py --path tests/test_cross_agent_memory.py
```

---

### Task 9: Build signed ownership migration with owner fallback and rollback

**Files:**
- Create: `core/services/recall_ownership_migration.py`
- Create: `scripts/migrate_recall_ownership.py`
- Create: `tests/test_recall_ownership_migration.py`
- Modify: `core/runtime/db_schema.py`

**Interfaces:**
- Consumes: Task 1 migration flag and Task 5-8 ownership columns.
- Produces: `classify_recall_ownership(conn) -> RecallOwnershipReport`, `apply_report(report_id) -> ApplyResult`, `rollback_report(report_id) -> RollbackResult` and CLI modes `--dry-run`, `--apply-report`, `--rollback-report`.

The classifier covers every legacy surface made private by this plan: `cognitive_experiential_memories`, `reasoning_conclusions`, `recall_active_memories`, NULL-owned `sensory_memories`, pending `memory_write_queue` payloads, unstamped `chat_messages`/their session summaries, and JSON `agent_observations`. Private-brain rows already carry `user_id`; they are audited for blanks but not otherwise reassigned.

- [ ] **Step 1: Write failing classification tests**

```python
def test_explicit_or_unique_other_user_beats_owner_fallback(db):
    seed_experience("e1", message_user="member-1")
    report = classify_recall_ownership(db, owner_user_id="owner")
    assert report.destination_for("experience", "e1") == "member-1"

def test_unmatched_legacy_row_uses_owner_fallback(db):
    seed_reasoning("r1", user_id=None)
    report = classify_recall_ownership(db, owner_user_id="owner")
    assert report.destination_for("reasoning", "r1") == "owner"

def test_conflicting_users_are_quarantined(db):
    seed_experience_with_conflict("e2", users=["member-1", "member-2"])
    report = classify_recall_ownership(db, owner_user_id="owner")
    assert report.reason_for("experience", "e2") == "identity_conflict"

def test_unstamped_chat_rows_in_single_user_session_inherit_that_user(db):
    seed_chat_session("s1", stamped_users=["member-1"], unstamped_rows=3)
    report = classify_recall_ownership(db, owner_user_id="owner")
    assert report.destination_for("chat_session", "s1") == "member-1"

def test_unstamped_chat_rows_without_any_user_use_owner_fallback(db):
    seed_chat_session("legacy", stamped_users=[], unstamped_rows=2)
    report = classify_recall_ownership(db, owner_user_id="owner")
    assert report.destination_for("chat_session", "legacy") == "owner"
```

- [ ] **Step 2: Write failing gate, idempotence and rollback tests**

```python
def test_apply_requires_migration_killswitch(monkeypatch, signed_report):
    monkeypatch.setattr(P, "recall_migration_enabled", lambda: False)
    with pytest.raises(MigrationDisabled):
        apply_report(signed_report.report_id)

def test_apply_is_idempotent_and_rollback_restores_previous_owner(signed_report):
    first = apply_report(signed_report.report_id)
    second = apply_report(signed_report.report_id)
    assert first.updated > 0 and second.already_applied == first.updated
    rolled = rollback_report(signed_report.report_id)
    assert rolled.restored == first.updated
```

- [ ] **Step 3: Run and verify RED**

Run: `pytest -q tests/test_recall_ownership_migration.py`

Expected: migration module and CLI do not exist.

- [ ] **Step 4: Implement schema and content-free migration ledger**

Add `recall_ownership_migration_log(report_id, source_kind, source_id_hash, previous_owner, new_owner, reason_code, applied_at, rolled_back_at)` plus a quarantine table keyed by source kind/hash. Store raw source IDs only inside sealed report entries, using the established routine migration encryption/signing pattern. Quarantine entries for conflicting chat sessions are consulted by Task 3 FTS queries.

- [ ] **Step 5: Implement deterministic classification and watermarking**

Classification priority is exactly: existing explicit owner; one distinct user from chat messages/visible runs/source record; owner fallback; conflict quarantine. Source rows include only ownership/provenance fields in the watermark.

```python
if len(authoritative_users) == 1:
    return authoritative_users.pop(), "authoritative_link"
if len(authoritative_users) > 1:
    return None, "identity_conflict"
return owner_user_id, "owner_fallback"
```

- [ ] **Step 6: Implement transactional apply/rollback and gate reset**

Verify signature and exact watermark before opening a transaction. Update ownership columns, unstamped chat rows, queued payload principals and ledger atomically. The `agent_observations` JSON update uses an adjacent owner-only backup plus atomic temp-file replace; its pre/post hashes are recorded in the DB ledger so rollback can restore only the matching version. In a `finally` block call `set_recall_migration_enabled(False)` for both success and failure. Rollback targets only rows/files whose current owner/hash still equals the report's applied state; otherwise quarantine the drift instead of overwriting newer state.

- [ ] **Step 7: Implement CLI with scalar-only summaries**

```python
summary = {
    "assigned_by_authoritative_link": report.authoritative_count,
    "assigned_by_owner_fallback": report.owner_fallback_count,
    "quarantined_conflicts": report.conflict_count,
    "database_rows_changed": 0,
    "report_id": report.report_id,
}
```

The CLI must never print source IDs, users, queries or memory content.

- [ ] **Step 8: Run migration and schema tests**

Run: `pytest -q tests/test_recall_ownership_migration.py tests/test_db_agent_memory.py tests/test_associative_recall.py tests/test_reasoning_recall_scope.py tests/test_experiential_memory_scope.py`

Expected: PASS.

- [ ] **Step 9: Commit Task 9**

```bash
git add -- core/services/recall_ownership_migration.py scripts/migrate_recall_ownership.py tests/test_recall_ownership_migration.py core/runtime/db_schema.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(memory): add recall ownership migration' --path core/services/recall_ownership_migration.py --path scripts/migrate_recall_ownership.py --path tests/test_recall_ownership_migration.py --path core/runtime/db_schema.py
```

---

### Task 10: Wire compatibility adapters, verify the system and prepare controlled rollout

**Files:**
- Modify: `core/services/memory_hierarchy.py:178-225`
- Modify: `core/services/memory_recall_engine.py:514-925`
- Modify: `core/tools/recall_tool.py:52-70`
- Modify: `core/tools/jarvis_brain_tools.py:203-225,336-435`
- Modify: `tests/test_memory_hierarchy.py`
- Modify: `tests/test_memory_recall_engine.py`
- Modify: `tests/test_recall_tool.py`
- Modify: `tests/test_jarvis_brain_visibility.py`
- Create: `tests/test_scoped_recall_integration.py`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: legacy entrypoints as thin wrappers over `recall()`, standardized disabled responses, and an integration test covering owner/member/current-query/killswitch behavior.

- [ ] **Step 1: Write failing compatibility and end-to-end tests**

```python
def test_legacy_multi_signal_wrapper_delegates_to_authoritative_recall(monkeypatch):
    seen = {}
    monkeypatch.setattr(R, "recall", lambda query, **kw: seen.setdefault("query", query) or result())
    M.multi_signal_recall_section("current query")
    assert seen["query"] == "current query"

def test_master_killswitch_blocks_prompt_tool_and_auto_recall(monkeypatch):
    set_recall_enabled(False)
    assert recall_tool({"query": "private"})["status"] == "disabled"
    assert visible_bundle("private") is None
    assert trigger_background_recall("private") is False
    assert count_new_recall_state_rows() == 0

def test_member_cannot_read_personal_brain_entry_by_known_id(monkeypatch):
    bind_user(monkeypatch, "member-1", role="member")
    result = read_brain_entry(personal_entry_id)
    assert result == {"status": "error", "error": "not_found"}
```

- [ ] **Step 2: Run and verify RED**

Run: `pytest -q tests/test_scoped_recall_integration.py tests/test_memory_hierarchy.py tests/test_memory_recall_engine.py tests/test_recall_tool.py`

Expected: old engines still execute separate source logic and tools ignore the master flag.

- [ ] **Step 3: Convert legacy entrypoints to thin wrappers**

`recall_before_act` may still compose hot/warm state, but its cold tier delegates to `recall()`. `unified_recall`, `multi_signal_recall`, and their section formatters call `recall()` and translate only the output shape needed by existing callers. Remove direct private-brain LIKE scanning from these paths.

- [ ] **Step 4: Apply standardized flag behavior to tools and prompt adapters**

At each public recall entrypoint, including direct brain search/read:

```python
if not recall_enabled():
    return disabled_result("recall")
```

Prompt formatters translate disabled to no section. They must not expose the internal disabled message to end users.
Direct brain tools derive their visibility ceiling from the bound principal rather than trusting a caller-supplied higher ceiling. `read_brain_entry` applies the same ceiling after loading metadata and returns `not_found` for an entry above the caller's ceiling, preventing a known ID from bypassing search visibility.

- [ ] **Step 5: Run all focused recall/privacy tests**

Run:

```bash
pytest -q \
  tests/test_scoped_recall_policy.py \
  tests/test_semantic_memory_scope.py \
  tests/test_recall.py \
  tests/test_memory_recall.py \
  tests/test_prompt_memory_recall.py \
  tests/test_associative_recall.py \
  tests/test_recall_scheduler.py \
  tests/test_experiential_memory_scope.py \
  tests/test_reasoning_recall_scope.py \
  tests/test_memory_write_queue_scope.py \
  tests/test_cross_agent_memory.py \
  tests/test_recall_ownership_migration.py \
  tests/test_jarvis_brain_visibility.py \
  tests/test_scoped_recall_integration.py
```

Expected: PASS.

- [ ] **Step 6: Run repository-wide verification**

Run:

```bash
python -m compileall core apps/api scripts
pytest -q
git diff --check
/opt/conda/envs/ai/bin/python scripts/install_git_hooks.py --check
```

Expected: compileall, full pytest, whitespace check and hook check all pass. Any pre-existing failure must be reported by exact test name and must not be omitted.

- [ ] **Step 7: Commit Task 10**

```bash
git add -- core/services/memory_hierarchy.py core/services/memory_recall_engine.py core/tools/recall_tool.py core/tools/jarvis_brain_tools.py tests/test_memory_hierarchy.py tests/test_memory_recall_engine.py tests/test_recall_tool.py tests/test_jarvis_brain_visibility.py tests/test_scoped_recall_integration.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'refactor(memory): route recall through scoped authority' --path core/services/memory_hierarchy.py --path core/services/memory_recall_engine.py --path core/tools/recall_tool.py --path core/tools/jarvis_brain_tools.py --path tests/test_memory_hierarchy.py --path tests/test_memory_recall_engine.py --path tests/test_recall_tool.py --path tests/test_jarvis_brain_visibility.py --path tests/test_scoped_recall_integration.py
```

- [ ] **Step 8: Run production dry-run with both flags OFF**

Run on CT105 after code deployment:

```bash
python scripts/migrate_recall_ownership.py --dry-run --json-summary
```

Expected: scalar counts plus `database_rows_changed: 0`; no IDs or content. Confirm `scoped_recall_enabled` and `scoped_recall_migration_enabled` are both false.

- [ ] **Step 9: Apply the exact signed report under the temporary migration gate**

Set only `scoped_recall_migration_enabled=true`, copy the exact report ID returned by dry-run, validate its shape, and verify the gate returns to false after apply:

```bash
read -r verified_recall_report_id
case "$verified_recall_report_id" in
  migration_[0-9a-f]*) ;;
  *) exit 2 ;;
esac
python scripts/migrate_recall_ownership.py --apply-report "$verified_recall_report_id" --json-summary
```

Expected: authoritative, owner-fallback, conflict and already-applied counts only. The entered value must be copied verbatim from the reviewed dry-run output; never construct or guess it.

- [ ] **Step 10: Enable recall and run privacy-safe canary probes**

Set `scoped_recall_enabled=true`, restart only services that cache runtime flags if a live read proves insufficient, then run owner and member probes using synthetic seeded records. Verify:

```text
owner sees owner synthetic record
member sees member synthetic record
owner does not see member synthetic record
member does not see owner synthetic record
changed query never receives previous-query result
archived synthetic record never enters candidates
```

If any invariant fails, immediately set `scoped_recall_enabled=false`; do not rollback ownership merely because delivery is disabled.

---

## Plan Self-Review Result

- **Spec coverage:** Killswitches, current-query delivery, auto recall, pre-top-K filtering, the hidden global inner-life caller, direct brain tools, every named specialized recall path, ownership migration, async propagation, telemetry, rollback and rollout all map to Tasks 1-10.
- **Type consistency:** Policy, migration and recall interfaces are named once and consumed with the same signatures in later tasks.
- **Boy Scout compliance:** The experiential-memory unit is extracted before logical changes to the 2,090-line `db_cognitive.py`; no logical edit is planned in `prompt_contract.py` or `visible_runs.py`.
- **Privacy default:** Missing runtime scope and migration conflicts fail closed; owner fallback is used only for legacy rows with no match to another user, as approved.
- **Test completeness:** Each Review Focus item has an explicit failing test in its owning task, followed by focused and full-suite verification.
