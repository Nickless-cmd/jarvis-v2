# Cheap Lane Control Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Jarvis Desk's current Cheap Lane admin table with an owner-only control center for capacity, providers, routing, logs, diagnostics, and audited controls.

**Architecture:** Keep the provider registry, balancer state, SQLite history, and Central as separate authoritative sources. Add focused observability, quota, diagnostics, and dashboard-composition services behind `/mc/cheap-lane/*`; Desk loads one composite snapshot, follows the shared Central stream, and falls back to bounded polling without creating client-side operational truth.

**Tech Stack:** Python 3.11, FastAPI, SQLite, Pydantic, pytest, React 19, TypeScript 5.5, Vite, Vitest, Testing Library, Lucide React, Recharts, CSS design tokens.

**Spec:** `docs/superpowers/specs/2026-09-18-cheap-lane-control-center-design.md`

## Global Constraints

- The control center manages only providers and models whose lane is exactly `cheap`; the general Providers page remains intact.
- Provider registry, balancer state, SQLite, provider adapters, and Central retain their existing ownership boundaries.
- Unknown capacity is `null`, never zero; request, token, and USD-credit units are never summed together.
- All sensitive reads and writes require the existing Central owner boundary.
- API keys and other credentials are accepted only on writes and never returned, audited, logged, or exported.
- Metadata retention defaults to 60 days; redacted prompt/response retention defaults to 7 days.
- New UI styles live outside `apps/jarvis-desk/src/styles/app.css`.
- Preserve existing Cheap Lane endpoints until the final replacement task.
- Do not run the full repository test suite; run only the focused commands listed per task.
- Use `python scripts/commit_with_attribution.py` for every commit, stage only each task's paths, and pass every staged path with `--path`.

## File Structure

### Backend

- Modify `core/runtime/db_cheap_provider.py`: backward-compatible invocation columns and recording parameters only.
- Create `core/runtime/db_cheap_lane_control.py`: route traces, quota observations, audits, redacted payloads, paginated log queries, and retention deletes.
- Create `core/services/cheap_lane_trace_context.py`: correlation context and bounded candidate trace types.
- Modify `core/services/cheap_provider_runtime_selection.py`: emit routing and fallback evidence and propagate correlation metadata.
- Modify `core/services/cheap_provider_runtime_adapters.py`: surface normalized token/cache/quota observations from provider responses.
- Create `core/services/cheap_lane_payloads.py`: redaction, bounded capture, and payload retention policy.
- Create `core/services/cheap_lane_quotas.py`: normalize configured, reported, and estimated quota windows.
- Modify `core/services/provider_registry_admin.py`: read/write validated quota policy and routing bias on Cheap Lane entries.
- Create `core/services/cheap_lane_diagnostics.py`: deterministic Cheap Lane findings plus Central references.
- Create `core/services/cheap_lane_dashboard.py`: composite snapshot and section freshness.
- Create `core/services/cheap_lane_admission.py`: cross-process lane/provider/slot pause, drain, and active-call leases.
- Create `core/services/cheap_lane_control.py`: audited domain mutations and route simulation.
- Create `apps/api/jarvis_api/routes/cheap_lane_control.py`: owner-gated reads, writes, filtering, pagination, and exports.
- Modify `apps/api/jarvis_api/app.py`: register the new router.
- Modify `core/services/retention.py` and `core/services/events_retention.py` only where the new tables require scheduled cleanup.

### Desk

- Replace `apps/jarvis-desk/src/lib/cheapLaneApi.ts`: normalized dashboard, log, diagnostics, and control contracts while retaining temporary legacy exports until final migration.
- Create `apps/jarvis-desk/src/lib/cheapLaneStore.ts`: snapshot loading, event refresh, polling fallback, and stale state.
- Refactor `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx`: shell, tabs, global controls, and shared state only.
- Create `CheapLaneOverview.tsx`, `CheapLaneCapacity.tsx`, `CheapLaneProviders.tsx`, `CheapLaneBalancer.tsx`, `CheapLaneLogs.tsx`, `CheapLaneDiagnostics.tsx`, `CheapLaneInspector.tsx`, `CheapLaneChart.tsx`, and `CheapLaneControls.tsx` in the same directory.
- Create `apps/jarvis-desk/src/styles/cheap-lane.css` and import it from `apps/jarvis-desk/src/App.tsx`.
- Modify `apps/jarvis-desk/package.json` and `package-lock.json`: add Recharts.
- Add focused colocated React tests for every tab and the store.

---

### Task 1: Durable Cheap Lane Observability Storage

**Files:**
- Modify: `core/runtime/db_cheap_provider.py`
- Create: `core/runtime/db_cheap_lane_control.py`
- Test: `tests/test_db_cheap_lane_control.py`
- Modify: `tests/test_db_cheap_provider.py`

**Interfaces:**
- Produces: `record_route_decision(*, correlation_id: str, task_kind: str, daemon: str, candidates: list[dict[str, object]], selected_slot_id: str, selection_reason: str) -> str`, `record_quota_observation(*, provider: str, auth_profile: str, period: str, unit: str, limit: float | None, remaining: float | None, reset_at: str | None, observed_at: str | None = None) -> int`, `record_cheap_lane_audit(*, actor: str, action: str, target: str, reason: str, before: dict[str, object], after: dict[str, object], result: str) -> str`, `finalize_cheap_lane_audit(audit_id: str, *, after: dict[str, object], result: str, error_code: str = "") -> dict[str, object]`, `record_redacted_payload(*, invocation_id: str, prompt: str | None, response: str | None, status: str, expires_at: str) -> int`, `list_cheap_lane_invocations(*, since: str, until: str | None = None, provider: str = "", model: str = "", auth_profile: str = "", daemon: str = "", status: str = "", error_class: str = "", correlation_id: str = "", query: str = "", cursor: str = "", limit: int = 100) -> dict[str, object]`, and `get_cheap_lane_invocation_detail(invocation_id: str) -> dict | None`.
- Extends: `record_cheap_provider_invocation` with optional `invocation_id`, `correlation_id`, `daemon`, `task_kind`, `egress`, `error_class`, `payload_status`, cache-token, attempt, parent, and route-decision arguments while preserving all existing callers.

- [ ] **Step 1: Write failing schema and compatibility tests**

```python
def test_extended_invocation_defaults_preserve_old_callers(isolated_runtime):
    row = record_cheap_provider_invocation(provider="groq", model="m", status="completed")
    detail = get_cheap_lane_invocation_detail(str(row["invocation_id"]))
    assert detail["correlation_id"]
    assert detail["attempt"] == 1
    assert detail["route_decision_id"] == ""

def test_route_trace_and_audit_are_durable(isolated_runtime):
    trace_id = record_route_decision(
        correlation_id="corr-1", task_kind="background", daemon="dream",
        candidates=[{"slot_id": "groq::m::default", "eligible": True, "weight": 0.8}],
        selected_slot_id="groq::m::default", selection_reason="healthy-headroom",
    )
    audit_id = record_cheap_lane_audit(
        actor="owner", action="slot.pause", target="groq::m::default",
        reason="maintenance", before={"paused": False}, after={"paused": True}, result="ok",
    )
    assert get_route_decision(trace_id)["selected_slot_id"] == "groq::m::default"
    assert list_cheap_lane_audit(limit=10)["items"][0]["audit_id"] == audit_id
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `pytest -q tests/test_db_cheap_lane_control.py tests/test_db_cheap_provider.py`

Expected: FAIL because the new module, fields, and query functions do not exist.

- [ ] **Step 3: Add idempotent schemas and CRUD**

Add nullable/defaulted columns to `cheap_provider_invocations`: `invocation_id`, `correlation_id`, `daemon`, `task_kind`, `egress`, `error_class`, `payload_status`, `cache_hit_tokens`, `cache_miss_tokens`, `attempt`, `retry_parent_id`, `fallback_parent_id`, and `route_decision_id`. Generate UUID identifiers when omitted.

In the new module, create tables with indexes on time, correlation, provider/model, status, and foreign identifiers:

`record_route_decision` and `list_cheap_lane_invocations` use the exact
signatures declared in this task's Interfaces block. The cursor is an opaque
base64url encoding of `(created_at, id)`; invalid cursors raise `ValueError`
and API mapping is added in Task 6.

Serialize bounded JSON with `ensure_ascii=False`; cap candidates at 100, audit before/after JSON at 64 KiB each, and page size at 500. Never interpolate filters into SQL.

- [ ] **Step 4: Run focused DB tests**

Run: `pytest -q tests/test_db_cheap_lane_control.py tests/test_db_cheap_provider.py tests/test_cheap_lane_history.py`

Expected: PASS, including old rows and old call signatures.

- [ ] **Step 5: Commit the storage layer**

```bash
git add -- core/runtime/db_cheap_provider.py core/runtime/db_cheap_lane_control.py tests/test_db_cheap_lane_control.py tests/test_db_cheap_provider.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(cheap-lane): add durable observability storage' --path core/runtime/db_cheap_provider.py --path core/runtime/db_cheap_lane_control.py --path tests/test_db_cheap_lane_control.py --path tests/test_db_cheap_provider.py
```

### Task 2: Correlation, Routing Decisions, Retries, and Fallbacks

**Files:**
- Create: `core/services/cheap_lane_trace_context.py`
- Modify: `core/services/cheap_provider_runtime_selection.py`
- Modify: `core/services/cheap_provider_runtime_adapters.py`
- Modify: `core/services/cheap_lane_balancer.py`
- Test: `tests/test_cheap_lane_route_trace.py`
- Modify: `tests/test_cheap_provider_runtime_selection.py`

**Interfaces:**
- Consumes: Task 1 `record_route_decision` and extended invocation recorder.
- Produces: `CheapLaneTraceContext`, `build_candidate_trace(candidate: dict[str, object], *, now: datetime) -> dict[str, object]`, and optional `correlation_id`, `daemon`, `attempt`, `retry_parent_id`, and `fallback_parent_id` arguments on `execute_cheap_lane_via_pool`.

- [ ] **Step 1: Write failing routing-evidence tests**

```python
def test_selection_records_selected_and_rejected_candidates(monkeypatch, isolated_runtime):
    monkeypatch.setattr(selection, "_configured_cheap_candidates", lambda **_: [ready, blocked])
    target = selection.select_cheap_lane_target(task_kind="background", correlation_id="corr-1")
    trace = get_route_decision(target["route_decision_id"])
    assert trace["selected_slot_id"] == target["slot_id"]
    assert {c["eligibility_reason"] for c in trace["candidates"]} >= {"eligible", "auth-not-ready"}

def test_fallback_keeps_correlation_and_links_attempts(
    isolated_runtime, configured_two_provider_pool, first_provider_fails,
):
    selection.execute_cheap_lane_via_pool(
        message="x", correlation_id="corr-2", daemon="dream", task_kind="background")
    rows = list_cheap_lane_invocations(
        since="2026-01-01T00:00:00Z", correlation_id="corr-2")["items"]
    rows = sorted(rows, key=lambda row: row["attempt"])
    assert [row["attempt"] for row in rows] == [1, 2]
    assert rows[1]["fallback_parent_id"] == rows[0]["invocation_id"]
```

- [ ] **Step 2: Run focused selection tests and verify failure**

Run: `pytest -q tests/test_cheap_lane_route_trace.py tests/test_cheap_provider_runtime_selection.py`

Expected: FAIL on unknown arguments and absent trace records.

- [ ] **Step 3: Implement context propagation and complete candidate evidence**

Use a frozen dataclass so recursive fallback calls retain identity without global mutable state:

```python
@dataclass(frozen=True)
class CheapLaneTraceContext:
    correlation_id: str
    daemon: str = ""
    task_kind: str = "default"
    attempt: int = 1
    retry_parent_id: str = ""
    fallback_parent_id: str = ""

    def next_fallback(self, parent_id: str) -> "CheapLaneTraceContext":
        return replace(self, attempt=self.attempt + 1,
                       retry_parent_id="", fallback_parent_id=parent_id)
```

Evaluate and record every bounded candidate once per selection. Include base priority, effective priority, adaptive penalty, quota headroom, cooldown, breaker, credentials readiness, egress, manual bias, eligibility, and rejection reason. The simulation path added later must call the same pure evaluator with `persist=False`.

Record failed invocations before recursing to fallback. Parse cache token fields and standardized quota metadata from adapter results and pass them to the recorder.

- [ ] **Step 4: Run selection, balancer, and adapter tests**

Run: `pytest -q tests/test_cheap_lane_route_trace.py tests/test_cheap_provider_runtime_selection.py tests/test_cheap_lane_balancer.py tests/test_cheap_provider_runtime_adapters.py`

Expected: PASS with one correlation chain and no duplicate route decision per attempt.

- [ ] **Step 5: Commit runtime tracing**

```bash
git add -- core/services/cheap_lane_trace_context.py core/services/cheap_provider_runtime_selection.py core/services/cheap_provider_runtime_adapters.py core/services/cheap_lane_balancer.py tests/test_cheap_lane_route_trace.py tests/test_cheap_provider_runtime_selection.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(cheap-lane): trace routing and fallback decisions' --path core/services/cheap_lane_trace_context.py --path core/services/cheap_provider_runtime_selection.py --path core/services/cheap_provider_runtime_adapters.py --path core/services/cheap_lane_balancer.py --path tests/test_cheap_lane_route_trace.py --path tests/test_cheap_provider_runtime_selection.py
```

### Task 3: Quota Policies and Day, Week, Month Capacity

**Files:**
- Create: `core/services/cheap_lane_quotas.py`
- Modify: `core/services/provider_registry_admin.py`
- Modify: `core/services/cheap_provider_runtime_adapters.py`
- Test: `tests/test_cheap_lane_quotas.py`
- Modify: `tests/test_provider_registry_admin.py`

**Interfaces:**
- Consumes: Task 1 quota observations and invocation token history.
- Produces: `QuotaWindow`, `capacity_snapshot(now: datetime | None = None) -> dict`, `set_quota_policy(*, provider: str, auth_profile: str, windows: list[dict[str, object]], expected_revision: str = "") -> dict`, and `observe_provider_quota(*, provider: str, auth_profile: str, observation: dict[str, object]) -> int`.

- [ ] **Step 1: Write failing precedence and aggregation tests**

```python
def test_provider_report_beats_config_and_estimate(isolated_runtime, cheap_registry):
    set_quota_policy(provider="groq", auth_profile="default", windows=[
        {"period": "month", "unit": "tokens", "limit": 1_000_000,
         "reset_timezone": "UTC", "reset_day": 1},
    ])
    record_quota_observation(provider="groq", auth_profile="default", period="month",
                             unit="tokens", limit=900_000, remaining=700_000,
                             reset_at="2026-10-01T00:00:00Z", observed_at="2026-09-18T10:00:00Z")
    window = capacity_snapshot(
        now=datetime.fromisoformat("2026-09-18T11:00:00+00:00"))["windows"][0]
    assert window["source"] == "provider"
    assert window["limit"] == 900_000

def test_aggregate_never_mixes_units(isolated_runtime, cheap_registry_with_unknown_member):
    snapshot = capacity_snapshot()
    assert set(snapshot["totals"]) == {"tokens", "requests", "credits_usd"}
    assert snapshot["totals"]["tokens"]["limit"] is None  # unknown member prevents false total
```

Also test ISO week boundaries, calendar month boundaries, reset timestamps, stale observations, configured fallback, estimate confidence/sample size, auth-profile isolation, and unknown versus zero.

- [ ] **Step 2: Run quota tests and verify failure**

Run: `pytest -q tests/test_cheap_lane_quotas.py tests/test_provider_registry_admin.py`

Expected: FAIL because quota policy and normalized windows do not exist.

- [ ] **Step 3: Implement validated quota policy and normalized windows**

Store provider/auth-profile policies under a backward-compatible `quota_policy` array in the provider registry:

```json
{"period":"month","unit":"tokens","limit":1000000,"reset_timezone":"UTC","reset_day":1}
```

Validate `limit > 0`, allowed periods/units, UTC-safe reset calculation, and Cheap Lane membership. Add a provider-result hook that records official observations only when an adapter returns normalized `quota_observation`; do not invent unsupported provider APIs.

Calculate usage directly from invocation history. Aggregate only windows with the same period and unit; return `complete=false` and `limit=null` when any participating capacity is unknown, while also returning `known_limit` and `unknown_members`.

- [ ] **Step 4: Run quota, registry, and history tests**

Run: `pytest -q tests/test_cheap_lane_quotas.py tests/test_provider_registry_admin.py tests/test_cheap_lane_history.py tests/test_cheap_provider_runtime_adapters.py`

Expected: PASS.

- [ ] **Step 5: Commit quota support**

```bash
git add -- core/services/cheap_lane_quotas.py core/services/provider_registry_admin.py core/services/cheap_provider_runtime_adapters.py tests/test_cheap_lane_quotas.py tests/test_provider_registry_admin.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(cheap-lane): add normalized quota capacity' --path core/services/cheap_lane_quotas.py --path core/services/provider_registry_admin.py --path core/services/cheap_provider_runtime_adapters.py --path tests/test_cheap_lane_quotas.py --path tests/test_provider_registry_admin.py
```

### Task 4: Redacted Payload Capture and Retention

**Files:**
- Create: `core/services/cheap_lane_payloads.py`
- Modify: `core/services/cheap_provider_runtime_selection.py`
- Modify: `core/services/retention.py`
- Modify: `core/services/events_retention.py`
- Test: `tests/test_cheap_lane_payloads.py`
- Modify: `tests/test_retention.py`

**Interfaces:**
- Consumes: Task 1 payload persistence and Task 2 invocation identifiers.
- Produces: `redact_payload(value: object) -> RedactionResult`, `capture_invocation_payload(*, invocation_id: str, prompt: object, response: object) -> str`, and `purge_expired_payloads(now: datetime | None = None) -> int`.

- [ ] **Step 1: Write failing redaction and expiry tests**

```python
def test_redaction_removes_headers_keys_and_secret_fields():
    result = redact_payload({"Authorization": "Bearer abc", "api_key": "jvs-secret", "prompt": "hello"})
    assert "abc" not in result.text and "jvs-secret" not in result.text
    assert "hello" in result.text

def test_failed_redaction_stores_status_not_payload(isolated_runtime, monkeypatch):
    monkeypatch.setattr(payloads, "redact_payload", lambda _: (_ for _ in ()).throw(ValueError("bad")))
    status = capture_invocation_payload(invocation_id="inv-1", prompt={"x": 1}, response="ok")
    assert status == "redaction_failed"
    assert get_redacted_payload("inv-1")["prompt"] is None
```

- [ ] **Step 2: Run payload tests and verify failure**

Run: `pytest -q tests/test_cheap_lane_payloads.py tests/test_retention.py`

Expected: FAIL because the redaction service is absent.

- [ ] **Step 3: Implement bounded capture**

Redact case-insensitive secret field names, authorization/cookie headers, known key prefixes, and runtime-configured patterns. Replace values with `[REDACTED]`; do not log rejected raw input. Bound prompt and response to 64 KiB each after redaction and store `expires_at = captured_at + 7 days` unless runtime configuration supplies another positive value.

Set the canonical retention defaults to 60 days for invocation metadata and 7
days for redacted payloads. Add tests proving a 59-day invocation remains, a
61-day invocation is removed, and an 8-day payload is removed without deleting
its invocation metadata. Runtime overrides are read from
`cheap_lane_metadata_retention_days` and `cheap_lane_payload_retention_days`.

Capture payload only after an invocation identifier exists. A capture failure must never fail the provider call; it records `payload_status` on the invocation and emits a redacted observability event.

- [ ] **Step 4: Run payload, runtime, and retention tests**

Run: `pytest -q tests/test_cheap_lane_payloads.py tests/test_retention.py tests/services/test_events_retention.py tests/test_cheap_provider_runtime_selection.py`

Expected: PASS and no raw secret in test output or DB rows.

- [ ] **Step 5: Commit payload lifecycle**

```bash
git add -- core/services/cheap_lane_payloads.py core/services/cheap_provider_runtime_selection.py core/services/retention.py core/services/events_retention.py tests/test_cheap_lane_payloads.py tests/test_retention.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(cheap-lane): retain redacted invocation payloads' --path core/services/cheap_lane_payloads.py --path core/services/cheap_provider_runtime_selection.py --path core/services/retention.py --path core/services/events_retention.py --path tests/test_cheap_lane_payloads.py --path tests/test_retention.py
```

### Task 5: Diagnostics and Composite Dashboard Snapshot

**Files:**
- Create: `core/services/cheap_lane_diagnostics.py`
- Create: `core/services/cheap_lane_dashboard.py`
- Test: `tests/test_cheap_lane_diagnostics.py`
- Test: `tests/test_cheap_lane_dashboard.py`

**Interfaces:**
- Consumes: `balancer_snapshot()`, `fuld_registrering()`, `capacity_snapshot()`, history queries, and Central incident readers.
- Produces: `diagnose_cheap_lane(now: datetime | None = None) -> dict` and `build_cheap_lane_dashboard(window_hours: int = 24) -> dict`.

- [ ] **Step 1: Write failing finding and partial-snapshot tests**

```python
def test_diagnostics_detects_starvation_and_stale_quota(monkeypatch):
    findings = diagnose_cheap_lane(now=parse("2026-09-18T12:00:00Z"))["findings"]
    assert {f["code"] for f in findings} >= {"no-eligible-slot", "quota-stale"}

def test_dashboard_keeps_healthy_sections_when_central_fails(monkeypatch):
    monkeypatch.setattr(dashboard, "central_evidence", Mock(side_effect=RuntimeError("down")))
    snap = build_cheap_lane_dashboard(window_hours=24)
    assert snap["status"] == "partial"
    assert snap["sections"]["capacity"]["data"]
    assert snap["sections"]["central"]["error"]["code"] == "source-unavailable"
```

- [ ] **Step 2: Run diagnostics/dashboard tests and verify failure**

Run: `pytest -q tests/test_cheap_lane_diagnostics.py tests/test_cheap_lane_dashboard.py`

Expected: FAIL because both services are absent.

- [ ] **Step 3: Implement deterministic findings and section envelopes**

Every section uses:

```python
{"source": "balancer", "observed_at": iso, "freshness": "live|stale|unknown",
 "data": value_or_none, "error": None_or_redacted_error}
```

Implement the ten diagnostic classes from the spec with stable codes, severity, evidence, first/last observed time, related provider/slot, and optional `central_incident_id`. Do not create or resolve Central incidents from this read path.

The top-level snapshot returns schema version, generated time, selected window, complete/partial/stale status, KPI summary, and sections for capacity, providers, balancer, trends, diagnostics, and Central evidence.

- [ ] **Step 4: Run service tests with existing sources**

Run: `pytest -q tests/test_cheap_lane_diagnostics.py tests/test_cheap_lane_dashboard.py tests/test_cheap_lane_history.py tests/test_cheap_lane_balancer.py tests/test_provider_registry_admin.py`

Expected: PASS.

- [ ] **Step 5: Commit dashboard services**

```bash
git add -- core/services/cheap_lane_diagnostics.py core/services/cheap_lane_dashboard.py tests/test_cheap_lane_diagnostics.py tests/test_cheap_lane_dashboard.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(cheap-lane): compose dashboard diagnostics' --path core/services/cheap_lane_diagnostics.py --path core/services/cheap_lane_dashboard.py --path tests/test_cheap_lane_diagnostics.py --path tests/test_cheap_lane_dashboard.py
```

### Task 6: Owner-Gated Read API, Search, Pagination, and Exports

**Files:**
- Create: `apps/api/jarvis_api/routes/cheap_lane_control.py`
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_cheap_lane_control_routes.py`

**Interfaces:**
- Consumes: Tasks 1, 3, 4, and 5 service functions.
- Produces: dashboard, capacity, logs, log detail, diagnostics, audit, filtered log exports, and a secret-free diagnostic-package export under `/mc/cheap-lane`.

- [ ] **Step 1: Write failing route and authorization tests**

```python
def test_dashboard_requires_owner(non_owner_client):
    assert non_owner_client.get("/mc/cheap-lane/dashboard").status_code == 403

def test_logs_are_cursor_paginated_and_filterable(owner_client, seeded_calls):
    r = owner_client.get("/mc/cheap-lane/logs?provider=groq&status=failed&limit=1")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 1
    assert "next_cursor" in r.json()

def test_export_has_no_payload_or_secret(owner_client, seeded_calls):
    body = owner_client.get("/mc/cheap-lane/logs/export?format=json&hours=24").text
    assert "Authorization" not in body and "prompt" not in body

def test_diagnostic_package_links_sources_without_secrets(owner_client, seeded_calls):
    data = owner_client.get("/mc/cheap-lane/diagnostics/export?hours=24").json()
    assert set(data) >= {"snapshot", "findings", "logs", "config_fingerprints", "schema_versions"}
    assert "api_key" not in json.dumps(data).lower()
```

- [ ] **Step 2: Run route tests and verify failure**

Run: `pytest -q tests/test_cheap_lane_control_routes.py`

Expected: FAIL with 404.

- [ ] **Step 3: Implement the read routes and bounds**

Use `_require_owner()` before invoking services. Validate `hours` to `1..1440`, page size to `1..500`, export range to at most 60 days, and export rows to a documented hard maximum. Return `422` for invalid units/periods and `404` for missing invocation identifiers.

CSV uses Python's `csv` module and a streaming response. JSON export omits payloads. The diagnostic package contains the bounded snapshot, findings, matching metadata logs, configuration fingerprints, and schema versions, never raw configuration or credentials.

- [ ] **Step 4: Run API and service tests**

Run: `pytest -q tests/test_cheap_lane_control_routes.py tests/test_cheap_balancer_routes.py tests/test_cheap_lane_dashboard.py tests/test_cheap_lane_quotas.py`

Expected: PASS and legacy routes remain green.

- [ ] **Step 5: Commit read API**

```bash
git add -- apps/api/jarvis_api/routes/cheap_lane_control.py apps/api/jarvis_api/app.py tests/test_cheap_lane_control_routes.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(api): expose Cheap Lane control center reads' --path apps/api/jarvis_api/routes/cheap_lane_control.py --path apps/api/jarvis_api/app.py --path tests/test_cheap_lane_control_routes.py
```

### Task 7: Audited Control Service and Mutation API

**Files:**
- Modify: `core/runtime/db_cheap_lane_control.py`
- Create: `core/services/cheap_lane_admission.py`
- Create: `core/services/cheap_lane_control.py`
- Modify: `apps/api/jarvis_api/routes/cheap_lane_control.py`
- Modify: `core/services/provider_registry_admin.py`
- Modify: `core/services/cheap_lane_balancer.py`
- Modify: `core/services/cheap_provider_runtime_selection.py`
- Test: `tests/test_cheap_lane_control.py`
- Test: `tests/test_cheap_lane_admission.py`
- Modify: `tests/test_cheap_lane_control_routes.py`

**Interfaces:**
- Consumes: existing provider registry and balancer public functions plus Task 1 audit storage.
- Produces: `acquire_admission(*, correlation_id: str, provider: str, slot_id: str, lease_seconds: int = 120) -> AdmissionLease`, `release_admission(lease_id: str) -> None`, `apply_control(command: CheapLaneCommand, actor: str) -> dict`, and `simulate_route(task_kind: str, skip_providers: frozenset[str]) -> dict`.

- [ ] **Step 1: Write failing semantic and audit tests**

```python
def test_pause_is_temporary_but_deactivate_is_persistent(isolated_runtime, cheap_registry):
    paused = apply_control(
        CheapLaneCommand(action="provider.pause", target="groq", reason="test"),
        actor="owner")
    assert paused["resulting_state"]["paused"] is True
    assert registry_provider("groq")["enabled"] is True
    disabled = apply_control(
        CheapLaneCommand(action="provider.deactivate", target="groq", reason="test"),
        actor="owner")
    assert disabled["resulting_state"]["enabled"] is False

def test_success_is_not_returned_when_audit_fails(monkeypatch):
    monkeypatch.setattr(control, "record_cheap_lane_audit", Mock(side_effect=OSError("disk")))
    with pytest.raises(ControlAuditError):
        apply_control(CheapLaneCommand(
            action="quota.set", target="groq/default", reason="budget",
            parameters={"windows": [{"period": "month", "unit": "tokens",
                                      "limit": 1_000_000}]},
        ), actor="owner")
```

Also test Cheap Lane scope rejection, revision conflicts, drain admission behavior, lane pause, probe, breaker reset, cooldown release, bounded routing bias, pool rebuild, provider/model add/deactivate/delete, retention changes, and route simulation with no mutation.

The admission test must use two independent DB connections: acquire one active
lease, set provider drain, verify a second acquisition is rejected, verify the
first lease remains active, release it, and assert the drain reports zero
active calls. Expired leases are pruned on read and cannot hold a drain open.

- [ ] **Step 2: Run focused control tests and verify failure**

Run: `pytest -q tests/test_cheap_lane_control.py tests/test_cheap_lane_control_routes.py`

Expected: FAIL because the command service and write routes do not exist.

- [ ] **Step 3: Implement command validation, authoritative read-back, and audit**

Define a discriminated command model with `action`, `target`, `reason`, `expected_revision`, and action-specific `parameters`. Require a non-empty reason for destructive/persistent actions. Record an intent audit before mutation and finalize it with result/after state; if finalization fails, return infrastructure failure rather than success.

Persist admission state and leases in SQLite so every API worker sees the same
pause/drain state and active count. `execute_cheap_lane_via_pool` acquires a
lease after selection and releases it in `finally`; a drain blocks new leases
without cancelling an admitted provider request. Lane, provider, and slot
pause reject new leases immediately. Leases expire after a bounded timeout so
a dead worker cannot hold the lane active forever.

Implement write routes under `/mc/cheap-lane/control` and `/mc/cheap-lane/simulate-route`. Responses contain `audit_id`, `status`, `resulting_state`, and `pool_refresh` where relevant. Map revision conflict to `409`, invalid scope to `422`, missing target to `404`, and audit/persistence failure to `503`.

Every successful or failed command emits `runtime.cheap_lane_control_changed`
with `audit_id`, action, target, result, and no before/after payload. Quota
observation changes emit `runtime.cheap_lane_quota_observed`; Desk uses these
events only as refresh triggers.

The `retention.set` action writes the canonical runtime settings
`cheap_lane_metadata_retention_days` and
`cheap_lane_payload_retention_days`. Validate metadata to `1..365` days,
payloads to `1..30` days, and payload retention not greater than metadata
retention.

- [ ] **Step 4: Run control, registry, balancer, and route tests**

Run: `pytest -q tests/test_cheap_lane_control.py tests/test_cheap_lane_admission.py tests/test_cheap_lane_control_routes.py tests/test_provider_registry_admin.py tests/test_cheap_lane_balancer.py tests/test_cheap_provider_runtime_selection.py tests/test_cheap_balancer_routes.py`

Expected: PASS.

- [ ] **Step 5: Commit controls**

```bash
git add -- core/runtime/db_cheap_lane_control.py core/services/cheap_lane_admission.py core/services/cheap_lane_control.py apps/api/jarvis_api/routes/cheap_lane_control.py core/services/provider_registry_admin.py core/services/cheap_lane_balancer.py core/services/cheap_provider_runtime_selection.py tests/test_cheap_lane_control.py tests/test_cheap_lane_admission.py tests/test_cheap_lane_control_routes.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(cheap-lane): add audited operator controls' --path core/runtime/db_cheap_lane_control.py --path core/services/cheap_lane_admission.py --path core/services/cheap_lane_control.py --path apps/api/jarvis_api/routes/cheap_lane_control.py --path core/services/provider_registry_admin.py --path core/services/cheap_lane_balancer.py --path core/services/cheap_provider_runtime_selection.py --path tests/test_cheap_lane_control.py --path tests/test_cheap_lane_admission.py --path tests/test_cheap_lane_control_routes.py
```

### Task 8: Desk API Contract and Live Store

**Files:**
- Modify: `apps/jarvis-desk/src/lib/cheapLaneApi.ts`
- Create: `apps/jarvis-desk/src/lib/cheapLaneStore.ts`
- Create: `apps/jarvis-desk/src/lib/cheapLaneStore.test.ts`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.test.tsx`

**Interfaces:**
- Consumes: Tasks 6 and 7 API contracts plus `subscribeCentralStream`.
- Produces: TypeScript types, fetch functions, `useCheapLaneStore(config, windowHours)`, targeted refresh, polling fallback, mutation helper, and inspector selection state.

- [ ] **Step 1: Write failing store tests with fake timers**

```tsx
it('loads one snapshot and refreshes after a cheap-lane event', async () => {
  const { result } = renderHook(() => useCheapLaneStore(config, 24))
  await waitFor(() => expect(result.current.snapshot?.schema_version).toBe(1))
  emitCentral({ kind: 'runtime.cheap_lane_provider_completed' })
  await vi.advanceTimersByTimeAsync(300)
  expect(getDashboard).toHaveBeenCalledTimes(2)
})

it('marks data stale and polls after stream failure', async () => {
  failCentralStream()
  await vi.advanceTimersByTimeAsync(15_000)
  expect(result.current.liveState).toBe('polling')
  expect(getDashboard).toHaveBeenCalledTimes(2)
})
```

- [ ] **Step 2: Run the Desk tests and verify failure**

Run: `cd apps/jarvis-desk && npm test -- --run src/lib/cheapLaneStore.test.ts src/components/cowork/cheaplane/CheapLanePanel.test.tsx`

Expected: FAIL because the normalized API and hook do not exist.

- [ ] **Step 3: Implement strict public types and resilient store behavior**

Model section envelopes and quota unknowns explicitly:

```ts
export type Freshness = 'live' | 'stale' | 'unknown'
export interface Section<T> { source: string; observed_at: string | null; freshness: Freshness; data: T | null; error: ApiProblem | null }
export interface QuotaWindow { period: 'minute'|'day'|'week'|'month'; unit: 'tokens'|'requests'|'credits_usd'; limit: number|null; used: number; remaining: number|null; source: 'provider'|'configured'|'estimated'|'unknown'; confidence: number|null; reset_at: string|null }
```

Debounce matching Central events to one refresh per 300 ms. Maintain at most one shared Central stream via the existing singleton. After stream error, poll every 15 seconds; stop polling when live events resume. Abort in-flight reads on unmount or time-window change. Never retry unary mutations in the client.

- [ ] **Step 4: Run API/store tests and typecheck**

Run: `cd apps/jarvis-desk && npm test -- --run src/lib/cheapLaneStore.test.ts src/components/cowork/cheaplane/CheapLanePanel.test.tsx && npx tsc -b --pretty false`

Expected: PASS.

- [ ] **Step 5: Commit Desk data layer**

```bash
git add -- apps/jarvis-desk/src/lib/cheapLaneApi.ts apps/jarvis-desk/src/lib/cheapLaneStore.ts apps/jarvis-desk/src/lib/cheapLaneStore.test.ts apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.test.tsx
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): add Cheap Lane live data store' --path apps/jarvis-desk/src/lib/cheapLaneApi.ts --path apps/jarvis-desk/src/lib/cheapLaneStore.ts --path apps/jarvis-desk/src/lib/cheapLaneStore.test.ts --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.test.tsx
```

### Task 9: Dashboard Shell, Overview, Capacity, and Charts

**Files:**
- Modify: `apps/jarvis-desk/package.json`
- Modify: `apps/jarvis-desk/package-lock.json`
- Modify: `apps/jarvis-desk/src/App.tsx`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneOverview.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneCapacity.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneChart.tsx`
- Create: `apps/jarvis-desk/src/styles/cheap-lane.css`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneOverview.test.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneCapacity.test.tsx`

**Interfaces:**
- Consumes: Task 8 store and snapshot types.
- Produces: stable header/KPI shell, Overview and Capacity tabs, shared accessible chart components, time-window control, and section-error rendering.

- [ ] **Step 1: Install chart dependency and write failing rendering tests**

Run: `cd apps/jarvis-desk && npm install recharts`

Then test exact distinctions:

```tsx
it('does not render unknown monthly capacity as zero', () => {
  render(<CheapLaneCapacity windows={[{ period:'month', unit:'tokens', limit:null, used:120, remaining:null, source:'unknown', confidence:null, reset_at:null }]} />)
  expect(screen.getByText('Ukendt kapacitet')).toBeInTheDocument()
  expect(screen.queryByText('0 %')).not.toBeInTheDocument()
})

it('exposes chart values without pointer hover', () => {
  render(<CheapLaneOverview snapshot={fixture} />)
  expect(screen.getByRole('table', { name: 'Tokenforbrug som tabel' })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run focused component tests and verify failure**

Run: `cd apps/jarvis-desk && npm test -- --run src/components/cowork/cheaplane/CheapLaneOverview.test.tsx src/components/cowork/cheaplane/CheapLaneCapacity.test.tsx`

Expected: FAIL because the components do not exist.

- [ ] **Step 3: Build the shell and first two tabs**

Use Lucide icons for refresh, settings, pause, warning, and info. Keep KPI cells in a CSS grid with fixed minimum dimensions. Recharts tooltips show exact value, source, and timestamp; every chart has a visually hidden or collapsible data table for keyboard/screen-reader access. Progress bars include exact `used / limit`, remaining value, source badge, and reset time.

Import `./styles/cheap-lane.css` from `App.tsx`. Do not append styles to `app.css`. Implement responsive tracks and horizontal table containment without viewport-scaled fonts.

- [ ] **Step 4: Run component tests, legacy panel test, and renderer build**

Run: `cd apps/jarvis-desk && npm test -- --run src/components/cowork/cheaplane && npm run build:renderer`

Expected: PASS; no chart container warning and no TypeScript errors.

- [ ] **Step 5: Commit overview and capacity UI**

```bash
git add -- apps/jarvis-desk/package.json apps/jarvis-desk/package-lock.json apps/jarvis-desk/src/App.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneOverview.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneCapacity.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneChart.tsx apps/jarvis-desk/src/styles/cheap-lane.css apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneOverview.test.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneCapacity.test.tsx
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): build Cheap Lane overview and capacity' --path apps/jarvis-desk/package.json --path apps/jarvis-desk/package-lock.json --path apps/jarvis-desk/src/App.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneOverview.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneCapacity.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneChart.tsx --path apps/jarvis-desk/src/styles/cheap-lane.css --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneOverview.test.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneCapacity.test.tsx
```

### Task 10: Cheap Lane Provider Administration

**Files:**
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneProviders.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneControls.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneProviders.test.tsx`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx`
- Modify: `apps/jarvis-desk/src/styles/cheap-lane.css`

**Interfaces:**
- Consumes: Task 8 control mutation helper and Task 9 shell.
- Produces: searchable Cheap Lane-only provider/model table, shared inspector, add/edit/quota forms, and pause/deactivate/delete/probe controls.

- [ ] **Step 1: Write failing scope and control tests**

```tsx
it('shows only cheap-lane providers', () => {
  render(<CheapLaneProviders providers={[cheapProvider, visibleProvider]}
             store={store} onInspect={onInspect} />)
  expect(screen.getByText('groq')).toBeInTheDocument()
  expect(screen.queryByText('anthropic-visible')).not.toBeInTheDocument()
})

it('requires confirmation for delete and explains credential retention', async () => {
  await user.click(screen.getByRole('button', { name: /Fjern groq/ }))
  expect(screen.getByRole('dialog')).toHaveTextContent('Legitimationen bevares')
  expect(sendControl).not.toHaveBeenCalled()
})
```

Test pause versus deactivate labels, pending state, server error preservation, API-key non-reflection, quota validation, and inspector keyboard focus return.

- [ ] **Step 2: Run provider tests and verify failure**

Run: `cd apps/jarvis-desk && npm test -- --run src/components/cowork/cheaplane/CheapLaneProviders.test.tsx`

Expected: FAIL because the provider components do not exist.

- [ ] **Step 3: Implement master/detail provider operations**

Add a search field with provider/model/profile filtering. Adding a provider always sends `lane: 'cheap'`; there is no lane selector. Separate temporary `Pause` from persistent `Deaktivér`, and isolate destructive `Fjern` in a confirmation dialog. Use password input for optional credentials and clear it immediately after submit.

Open provider/model detail in the shared right inspector, showing credentials readiness, health, quota windows, routing share, recent errors, and actions. Preserve table scroll and return focus to the originating row when the inspector closes.

- [ ] **Step 4: Run provider, shell, and accessibility-focused tests**

Run: `cd apps/jarvis-desk && npm test -- --run src/components/cowork/cheaplane/CheapLaneProviders.test.tsx src/components/cowork/cheaplane/CheapLanePanel.test.tsx && npm run build:renderer`

Expected: PASS.

- [ ] **Step 5: Commit provider administration**

```bash
git add -- apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneProviders.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneControls.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneProviders.test.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx apps/jarvis-desk/src/styles/cheap-lane.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): add Cheap Lane provider controls' --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneProviders.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneControls.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneProviders.test.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx --path apps/jarvis-desk/src/styles/cheap-lane.css
```

### Task 11: Load Balancer Explanation and Route Simulation

**Files:**
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneBalancer.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneBalancer.test.tsx`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx`
- Modify: `apps/jarvis-desk/src/styles/cheap-lane.css`

**Interfaces:**
- Consumes: snapshot slot factors and Task 7 simulation/control endpoints.
- Produces: sortable/filterable slot table, factor explanation, simulation form, pool/lane controls, and pause/drain/reset/probe/bias actions.

- [ ] **Step 1: Write failing explanation and no-mutation tests**

```tsx
it('explains zero weight with the hard rejection reason', async () => {
  render(<CheapLaneBalancer slots={[cooldownSlot]}
             store={store} onInspect={onInspect} />)
  await user.click(screen.getByText('groq / llama'))
  expect(screen.getByText('Cooldown aktiv')).toBeInTheDocument()
  expect(screen.getByText(/vægt 0/)).toBeInTheDocument()
})

it('labels simulation as read-only', async () => {
  await user.click(screen.getByRole('button', { name: 'Simulér routing' }))
  expect(screen.getByText('Der sendes intet provider-kald')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run balancer tests and verify failure**

Run: `cd apps/jarvis-desk && npm test -- --run src/components/cowork/cheaplane/CheapLaneBalancer.test.tsx`

Expected: FAIL because the component does not exist.

- [ ] **Step 3: Implement balancer table and controls**

Show current weight, eligibility, base/effective priority, quota headroom, success, p95, breaker, cooldown, profile, and egress. Expanded factors must sum or otherwise explain the displayed final weight; hard gates appear before soft factors. Provide filters for provider, status, profile, egress, and health.

Use explicit controls for rebuild pool, lane pause/drain, slot pause/drain, breaker reset, cooldown release, probe, and bounded routing bias. Display returned audit ID in the success notice and refresh authoritative state before clearing pending status.

- [ ] **Step 4: Run balancer tab and renderer checks**

Run: `cd apps/jarvis-desk && npm test -- --run src/components/cowork/cheaplane/CheapLaneBalancer.test.tsx src/components/cowork/cheaplane/CheapLanePanel.test.tsx && npm run build:renderer`

Expected: PASS.

- [ ] **Step 5: Commit balancer UI**

```bash
git add -- apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneBalancer.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneBalancer.test.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx apps/jarvis-desk/src/styles/cheap-lane.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): explain and control Cheap Lane routing' --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneBalancer.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneBalancer.test.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx --path apps/jarvis-desk/src/styles/cheap-lane.css
```

### Task 12: Searchable Logs, Payload Detail, Audit, and Diagnostics

**Files:**
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneLogs.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneDiagnostics.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneSettings.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneLogs.test.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneDiagnostics.test.tsx`
- Create: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneSettings.test.tsx`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx`
- Modify: `apps/jarvis-desk/src/styles/cheap-lane.css`

**Interfaces:**
- Consumes: Task 6 paginated log/detail/diagnostic/audit/export APIs.
- Produces: server-driven search, cursor pagination, invocation timeline, redacted payload view, diagnostic timeline, audit view, and exports.

- [ ] **Step 1: Write failing pagination, privacy, and diagnostic tests**

```tsx
it('sends filters to the server and follows next_cursor', async () => {
  await user.type(screen.getByRole('searchbox'), 'timeout')
  await user.click(screen.getByRole('button', { name: 'Næste side' }))
  expect(getLogs).toHaveBeenLastCalledWith(expect.objectContaining({ query:'timeout', cursor:'cursor-2' }))
})

it('marks omitted payload rather than rendering an empty prompt', async () => {
  renderDetail({ payload_status:'redaction_failed', prompt:null, response:null })
  expect(screen.getByText('Payload blev udeladt, fordi redigering fejlede')).toBeInTheDocument()
})
```

Also test fallback timelines, source freshness, Central incident links, audit before/after values, export URL filters, and secret absence.

Add settings tests that open the header settings icon, render the effective
metadata/payload retention values, reject payload retention longer than
metadata retention, and send `retention.set` only after explicit save.

- [ ] **Step 2: Run log and diagnostic tests and verify failure**

Run: `cd apps/jarvis-desk && npm test -- --run src/components/cowork/cheaplane/CheapLaneLogs.test.tsx src/components/cowork/cheaplane/CheapLaneDiagnostics.test.tsx`

Expected: FAIL because both tabs are absent.

- [ ] **Step 3: Implement server-driven log and diagnostic views**

Debounce free-text search by 250 ms and reset cursor on filter change. Do not retain all pages in memory. Detail inspector groups route decision, invocation attempts, fallback edges, tokens, price, latency, errors, and payload status. Payload content uses plain preformatted text, never `dangerouslySetInnerHTML`.

Diagnostics groups active findings first, then timeline and audit. Stale, unknown, and source-unavailable states use icon plus text. JSON/CSV export uses the active filters and warns when the server clamps the requested range.

The settings dialog owns only Cheap Lane settings covered by this design:
metadata retention and redacted-payload retention. It shows their consequences
in field descriptions, uses numeric inputs with server-matching bounds, and
renders the returned audit identifier after save.

- [ ] **Step 4: Run all Cheap Lane React tests and renderer build**

Run: `cd apps/jarvis-desk && npm test -- --run src/lib/cheapLaneStore.test.ts src/components/cowork/cheaplane && npm run build:renderer`

Expected: PASS.

- [ ] **Step 5: Commit logs and diagnostics**

```bash
git add -- apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneLogs.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneDiagnostics.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneSettings.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneLogs.test.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneDiagnostics.test.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneSettings.test.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx apps/jarvis-desk/src/styles/cheap-lane.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): add Cheap Lane logs and diagnostics' --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneLogs.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneDiagnostics.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneSettings.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneLogs.test.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneDiagnostics.test.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneSettings.test.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLaneInspector.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx --path apps/jarvis-desk/src/styles/cheap-lane.css
```

### Task 13: End-to-End Fault Matrix, Visual Verification, and Legacy Replacement

**Files:**
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx`
- Modify: `apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.test.tsx`
- Modify: `apps/jarvis-desk/src/lib/cheapLaneApi.ts`
- Create: `tests/test_cheap_lane_control_integration.py`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: one production Cheap Lane route with no legacy client-side five-request assembly and verified rollback-compatible backend routes.

- [ ] **Step 1: Add the final integration/fault matrix**

Extend the panel test to cover:

```tsx
it.each([
  ['dashboard source partial', partialSnapshot, 'Delvise data'],
  ['event stream down', staleSnapshot, 'Polling'],
  ['all capacity unknown', unknownSnapshot, 'Ukendt kapacitet'],
  ['lane paused', pausedSnapshot, 'Sat på pause'],
])('%s remains operable', async (_name, snapshot, expected) => {
  mockDashboard(snapshot)
  render(<CheapLanePanel config={config} />)
  expect(await screen.findByText(expected)).toBeInTheDocument()
  expect(screen.getByRole('tab', { name:'Udbydere' })).toBeEnabled()
})
```

Add an API integration test seeded with registry, balancer, DB, quota, route trace, payload, audit, and Central fixtures; assert one dashboard response links the same correlation identifier across log and detail.

- [ ] **Step 2: Remove legacy browser aggregation and run the focused matrix**

Remove unused `getHistorik`, `getFejl`, `getTidsserie`, and direct registry assembly from `CheapLanePanel`; retain exported legacy API helpers only if another live consumer still imports them, verified with `rg`.

Run:

```bash
pytest -q tests/test_db_cheap_lane_control.py tests/test_cheap_lane_route_trace.py tests/test_cheap_lane_quotas.py tests/test_cheap_lane_payloads.py tests/test_cheap_lane_diagnostics.py tests/test_cheap_lane_dashboard.py tests/test_cheap_lane_control.py tests/test_cheap_lane_control_routes.py tests/test_cheap_balancer_routes.py tests/test_provider_registry_admin.py
cd apps/jarvis-desk && npm test -- --run src/lib/cheapLaneStore.test.ts src/components/cowork/cheaplane && npm run build
```

Expected: all focused tests and the full Desk production build PASS.

- [ ] **Step 3: Run visual verification at supported widths**

Start the renderer on an unused local port:

```bash
cd apps/jarvis-desk && npm run dev -- --host 127.0.0.1 --port 5187
```

Using the repository's browser/Playwright workflow, capture at least `1440x900`, `1024x768`, and `720x900` for Overview, Capacity, Providers, Load Balancer, Log detail, and Diagnostics. Verify charts are nonblank, tooltips remain inside the viewport, tables scroll rather than overlap, inspector does not cover controls incoherently, longest provider/model names wrap or ellipsize with a tooltip, and all icon buttons expose accessible names.

- [ ] **Step 4: Inspect scope, secrets, and generated-doc drift**

Run:

```bash
git diff --check
git status --short
rg -n "api[_-]?key|Authorization|Bearer " apps/jarvis-desk/src/components/cowork/cheaplane core/services/cheap_lane_* apps/api/jarvis_api/routes/cheap_lane_control.py
python -m compileall core/services core/runtime apps/api/jarvis_api/routes
```

Expected: no literal credential, no whitespace error, and no syntax failure. If hooks request generated docs, run the documented generator and include only its required output.

- [ ] **Step 5: Commit final integration**

```bash
git add -- apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.test.tsx apps/jarvis-desk/src/lib/cheapLaneApi.ts tests/test_cheap_lane_control_integration.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): complete Cheap Lane control center' --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.tsx --path apps/jarvis-desk/src/components/cowork/cheaplane/CheapLanePanel.test.tsx --path apps/jarvis-desk/src/lib/cheapLaneApi.ts --path tests/test_cheap_lane_control_integration.py
```

## Final Review Gate

Before merge or deployment, perform a code review focused on:

- false capacity totals or mixed units;
- any control that bypasses owner auth, audit, revision checks, or authoritative read-back;
- raw prompt, response, credential, or authorization leakage;
- routing traces that change selection behavior rather than merely observe it;
- unbounded SQL queries, exports, JSON payloads, or renderer lists;
- duplicate Central streams or polling loops;
- stale data displayed as live;
- persistent versus temporary controls with ambiguous labels;
- regressions in legacy Cheap Lane routes and non-cheap provider administration.

Merge, push, release, deployment to Jarvis' container, and local Desk installation are separate explicit operations after this implementation plan passes its focused verification.
