# Cheap Lane Control Center Design

## Status and Scope

This design replaces the current owner-only Cheap Lane page in Jarvis Desk
with a complete operational control center for the `cheap` lane. It covers
capacity, token consumption, provider administration, load-balancer state,
routing decisions, invocation logs, Central diagnostics, and durable audit
history.

The page is deliberately scoped to providers and models participating in the
`cheap` lane. The existing general Providers page remains the administration
surface for every other lane.

The work is architectural rather than a visual restyle. The current page
already exposes five tabs and several controls, but it assembles five API
responses in the browser, omits token totals that the history layer already
records, exposes only RPM and daily request limits, and cannot explain a
routing decision end to end. The new control center must provide one coherent
operational answer without creating a second source of truth.

## Goals

The owner must be able to:

1. understand the health and effective capacity of the entire Cheap Lane at a
   glance;
2. see used, remaining, and total capacity for day, week, and month, including
   the provenance and confidence of every quota;
3. inspect every Cheap Lane provider, model, auth profile, and balancer slot;
4. add, edit, pause, drain, deactivate, probe, reset, and remove Cheap Lane
   resources through explicit owner-gated controls;
5. understand why the load balancer selected or rejected a slot;
6. search the complete technical invocation log and follow retries and
   fallbacks by correlation identifier;
7. inspect redacted prompt and response payloads for recent calls;
8. see relevant Central incidents, anomalies, and root-cause signals in the
   same operational timeline;
9. distinguish live, stale, configured, estimated, and provider-reported data;
10. export logs or a secret-free diagnostic package.

## Non-Goals

- The control center does not administer `visible`, `coding`, `local`,
  `inner_enrichment`, or agent-pool providers.
- It does not move provider-registry, balancer, database, or Central truth into
  Desk.
- It does not expose stored credentials or return a provider API key after a
  write.
- It does not claim that request, credit, and token quotas are interchangeable.
- It does not replace the general Central dashboard.
- It does not make destructive changes optimistically in the client.

## Chosen Architecture

Introduce a Cheap Lane control-plane read model behind a dedicated Mission
Control API. The read model composes authoritative sources on the server and
returns a timestamped snapshot. It does not persist a duplicate dashboard
state.

The sources of truth remain:

- provider registry: lane membership, models, auth profiles, persistent
  enablement, routing configuration, and configured quota policies;
- cheap-lane balancer state: live computed weights, cooldowns, circuit
  breakers, temporary pauses, drains, and current headroom;
- SQLite operational history: invocations, tokens, prices, latency, errors,
  retries, fallbacks, route traces, provider quota observations, and audits;
- provider adapters: official quota and reset information where a provider
  exposes it;
- Central: incidents, observations, anomalies, and root-cause evidence.

Desk receives an initial snapshot, then applies Cheap Lane event updates.
When the event connection is unavailable it falls back to bounded polling and
marks data stale. Server-side write endpoints continue to call the existing
authoritative services and return only after the resulting state has been
read back or a concrete failure is known.

## Backend Components

Implementation is split by responsibility:

### Dashboard Composer

`cheap_lane_dashboard.py` composes the initial snapshot. Each section carries
`observed_at`, `source`, and `freshness` metadata. A failed source yields a
section-level error and does not erase healthy sections.

The composer must use one request timestamp and one database read transaction
for related history queries. Live sources can be sampled independently but
their timestamps remain visible. The response reports whether it is complete,
partial, or stale.

### Quota Service

`cheap_lane_quotas.py` normalizes official, configured, and estimated quota
windows. Configured limits belong to the provider/auth-profile entry in the
provider registry because they are provider governance settings. Provider
quota observations and computed consumption belong in the operational DB.

Quota precedence is:

1. fresh provider-reported limit and reset;
2. owner-configured limit;
3. learned estimate based on observed quota exhaustion;
4. unknown.

A lower-precedence value remains visible as evidence but cannot silently
override a higher-precedence value. Conflicting values produce a diagnostic.

### Routing Trace

`cheap_lane_route_trace.py` records every selection attempt with a bounded
candidate trace:

- correlation and invocation identifiers;
- task kind and requesting daemon;
- candidate slot identifiers;
- base priority and live computed weight;
- quota, reliability, latency, cooldown, breaker, egress, and manual-bias
  factors;
- rejection reason for ineligible candidates;
- selected slot and selection reason;
- retry and fallback relationship.

Trace payloads are bounded and contain no credentials or full prompt text.

### Diagnostics

`cheap_lane_diagnostics.py` combines domain checks with relevant Central
evidence. It detects at minimum:

- no eligible slot;
- provider or auth-profile starvation;
- all capacity concentrated in one provider or egress path;
- stale balancer or quota state;
- repeated breaker trips;
- sustained error or latency regression;
- configured versus observed quota mismatch;
- imminent daily, weekly, or monthly exhaustion;
- provider credentials missing;
- calls bypassing the expected Cheap Lane route;
- route traces without matching invocations and vice versa.

Central remains read-only to this service. Diagnostics link back to Central
incident identifiers rather than copying incident truth.

### Audit Service

Every mutating Cheap Lane operation writes a durable audit record containing
actor, action, target, reason, before value, after value, result, timestamp,
and correlation identifier. Secret values are represented only as changed or
unchanged. An audit failure prevents a successful response for governance
changes.

## Normalized Quota Contract

Quota windows are scoped to provider and auth profile, with optional model
scope only when the provider enforces a model-specific limit.

```json
{
  "provider": "example",
  "auth_profile": "default",
  "model": null,
  "period": "month",
  "unit": "tokens",
  "limit": 10000000,
  "used": 2750000,
  "remaining": 7250000,
  "reset_at": "2026-10-01T00:00:00Z",
  "source": "configured",
  "confidence": 1.0,
  "observed_at": "2026-09-18T10:00:00Z",
  "freshness": "live"
}
```

Allowed periods are `minute`, `day`, `week`, and `month`. Allowed units are
`tokens`, `requests`, and `credits_usd`. The API may add provider-native units
but must not combine them with another unit.

The dashboard calculates token use as input plus output tokens and shows the
two components in details. Cache-hit and cache-miss tokens remain separate
when available. Aggregate totals include only compatible scopes and units.
Unknown capacity is shown as unknown, not zero.

Where no official token capacity exists, the owner can configure day, week,
or month limits. A learned estimate is visually distinct and includes its
sample size and confidence. Request-limited capacity may have a separate
forecast of likely tokens based on recent median tokens per request, but that
forecast is never labeled as an authoritative token allowance.

## Operational Data Model

The existing `cheap_provider_invocations` history is extended compatibly with
the identifiers and metadata needed for diagnosis:

- invocation and correlation identifiers;
- requesting daemon and task kind;
- auth profile and egress path;
- input, output, cache-hit, and cache-miss tokens;
- cost and latency;
- attempt number, retry parent, and fallback parent;
- route-decision identifier;
- normalized status and error classification.

New bounded tables hold:

- route decisions and candidate factors;
- provider quota observations;
- Cheap Lane audit records;
- redacted invocation payloads with an explicit expiration timestamp.

Metadata retention defaults to 60 days. Redacted prompt and response payloads
default to 7 days. Both values are configurable, and the retention service
deletes expired payloads independently of invocation metadata. Existing rows
without new fields remain readable.

Payload capture runs through a shared redaction pass before persistence. It
must remove known credentials, authorization headers, secret-shaped fields,
and configured sensitive patterns. A payload that cannot be safely redacted
is omitted with `payload_status=redaction_failed`; the invocation metadata
remains available.

## API Surface

`apps/api/jarvis_api/routes/cheap_lane_control.py` owns the new aggregate API
contract and exposes these responsibilities:

- `GET /mc/cheap-lane/dashboard`: initial composite snapshot;
- `GET /mc/cheap-lane/capacity`: normalized quota windows and forecasts;
- `GET /mc/cheap-lane/logs`: server-filtered, cursor-paginated invocations;
- `GET /mc/cheap-lane/logs/{invocation_id}`: trace, attempts, and recent
  redacted payload;
- `GET /mc/cheap-lane/diagnostics`: active and recent findings;
- `GET /mc/cheap-lane/audit`: cursor-paginated mutation history;
- `POST /mc/cheap-lane/simulate-route`: read-only routing simulation;
- owner-gated write routes for lane, provider, model, slot, quota, probe,
  cooldown, breaker, drain, and routing-bias actions.

Existing Cheap Lane and provider-registry routes remain available during the
transition. The new APIs reuse their domain services rather than implementing
a second mutation path.

List endpoints support server-side time window, provider, model, auth profile,
daemon, status, error class, correlation identifier, and free-text filters.
CSV and JSON exports use the same filters and enforce a bounded date range.

All write responses include the audit identifier, resulting authoritative
state, and any required pool-refresh status. Owner authentication is mandatory
for both sensitive reads and every write.

## Control Semantics

Control labels must describe their persistence and effect:

- **Pause lane** stops admission of new Cheap Lane calls but does not cancel an
  active provider request.
- **Drain lane/provider/slot** rejects new selection and waits for active calls
  to finish.
- **Pause provider or slot** is temporary balancer state and survives only
  according to the documented operational-state policy.
- **Deactivate provider or model** updates the persistent registry and removes
  it from future pool builds.
- **Delete provider** removes only the Cheap Lane registry membership and
  models after confirmation; credentials are retained. Credential deletion is
  outside this design.
- **Reset breaker** clears failure/cooldown state but not historical evidence.
- **Probe now** performs a bounded health request and records its result.
- **Routing bias** adjusts an explicit bounded factor; it never hides the live
  computed weight or bypasses hard eligibility gates.
- **Simulate route** performs no provider call and mutates no state.

Destructive operations require a confirmation dialog that names the target
and consequence. Persistent and temporary actions use different wording and
icons. Concurrent writes use an expected revision or equivalent conflict
check so one browser cannot silently overwrite another.

## Desk Information Architecture

The page header contains:

- Cheap Lane health state: healthy, degraded, paused, or offline;
- last complete snapshot and live-connection state;
- global search;
- selected time window;
- refresh, settings, and lane-control icon buttons with tooltips.

A compact KPI band shows effective capacity, token use, request volume,
success rate, p95 latency, cost, and slot availability. Hover or keyboard focus
reveals definition, source, observation time, and confidence. KPI dimensions
remain stable while values update to avoid layout shifts.

The six primary tabs are:

### Overview

Shows capacity trajectory, token consumption, success/error trend, latency,
routing distribution, provider concentration, and current Cheap Lane Central
events. It answers whether the lane is healthy and whether capacity is likely
to run out.

### Capacity

Shows day, week, and month progress bars and time-series charts. Provider rows
expand into auth profiles and model-specific limits. Confirmed, configured,
estimated, stale, and unknown values have distinct text and icon treatment;
color is not the only signal. Forecasts include expected exhaustion time and
confidence.

### Providers

Shows only Cheap Lane providers and models in a searchable master/detail
table. Adding a provider creates its model directly in the `cheap` lane.
Selecting a row opens the shared inspector with credentials readiness,
quotas, health, models, routing share, recent errors, and controls.

### Load Balancer

Lists every slot by current selection weight and eligibility. Expanded rows
show each weight factor and rejection reason. The view supports provider,
status, profile, egress, and health filters, route simulation, pool rebuild,
probe, pause, drain, breaker reset, cooldown release, and bounded routing-bias
controls.

### Log

Provides a virtualized or cursor-paginated operational log rather than loading
the full history into the renderer. Search covers provider, model, daemon,
error text, status, and correlation identifier. Selecting a call opens its
timeline, route candidates, attempts, fallback chain, tokens, price, latency,
errors, and recent redacted prompt/response. The current filter can be
exported as JSON or CSV.

### Diagnostics

Combines active domain findings, related Central incidents, quota conflicts,
stale sources, breaker history, and a chronological operational timeline. A
secret-free diagnostic package contains the selected time range, snapshot,
findings, relevant logs, configuration fingerprints, and schema versions.

## Visual and Interaction Design

The control center follows Jarvis Desk tokens, typography, spacing, and panel
behavior. It is a dense operational surface, not a marketing page.

- Full-width sections and tables provide the primary structure; cards are
  reserved for repeated provider or incident items where framing is useful.
- A shared right-side inspector preserves table and chart context.
- Lucide icons are used for familiar actions; unfamiliar icon buttons have
  accessible tooltips and labels.
- Graphs provide axes, legends, keyboard-accessible summaries, hover values,
  zoomed time ranges, and empty/loading/error states.
- Progress bars include exact text values and reset times.
- Tables have sticky headers, stable column widths, sort controls, filters,
  and responsive horizontal containment.
- Search uses a single field with optional filter chips. It supports plain text
  first; advanced syntax is additive, not required.
- Status is communicated with icon, label, and tone, never color alone.
- No dynamic value may resize its surrounding toolbar, KPI cell, or action
  area.

Cheap Lane receives dedicated component and stylesheet files. The existing
large `app.css` is not expanded with the new dashboard implementation.

## Live Data and Failure Handling

The client loads one initial snapshot, then consumes typed Cheap Lane events.
Events trigger targeted cache updates or a debounced section refresh. They do
not invent new client-side operational state.

If the live stream disconnects, the header marks the connection stale and
starts bounded polling. If one backend source fails, the affected section
retains its last known data with a stale timestamp while healthy sections
continue updating. A complete refresh replaces the snapshot only after its
schema and timestamps are validated.

Write actions remain pending until the server confirms the authoritative
result. Failure leaves the prior state visible and presents a concrete error.
Partial application is surfaced with the audit identifier and resulting
state. A provider probe, registry mutation, or pool rebuild cannot be reported
as successful from an HTTP status alone.

Unknown and zero remain distinct throughout the API and UI. Missing quota
data is never rendered as zero capacity; no calls in a window is never
rendered as a zero-percent success rate.

## Security and Privacy

- All Cheap Lane control-center endpoints require the existing owner boundary.
- Secrets are accepted only by dedicated write fields and never echoed,
  logged, placed in audit before/after values, or included in exports.
- Payload detail is redacted before storage, bounded in size, short-lived, and
  excluded from exports by default.
- Diagnostic packages contain configuration fingerprints and readiness flags,
  not credential values.
- Free-text filters and exports are bounded to prevent unbounded DB scans.
- Every mutation carries a reason, actor, correlation identifier, and durable
  audit record.

## Testing Strategy

Backend tests cover:

- quota source precedence, reset boundaries, aggregation, forecasts, and the
  prohibition on mixed-unit totals;
- snapshot completeness, stale-source behavior, and one-source failure;
- routing traces, candidate-factor explanations, retries, and fallback links;
- diagnostics for starvation, stale state, quota mismatch, and concentration;
- redaction, retention, export bounds, owner authorization, and secret absence;
- every control's temporary versus persistent semantics;
- write conflict handling and audit-before-success behavior;
- migration compatibility with existing invocation rows.

Desk tests cover:

- each tab's loading, empty, partial, stale, live, and error states;
- quota provenance and unknown-versus-zero rendering;
- search, filters, cursor pagination, sorting, and inspector navigation;
- provider creation, pause, deactivate, delete, confirmation, and failures;
- balancer explanations, simulation, and controls;
- keyboard access, tooltips, stable layout, and responsive containment;
- event-stream updates and polling fallback.

Focused integration tests verify the dashboard snapshot against seeded DB,
registry, balancer, and Central fixtures. A production desktop build and
Playwright screenshots at desktop and narrow widths verify visual hierarchy,
chart rendering, overflow, and non-overlap. The full repository test suite is
not required for this feature; affected backend, API, Desk, and build checks
are required.

## Rollout

Delivery proceeds in six independently verifiable stages:

1. extend invocation observability, route traces, and the composite snapshot;
2. add normalized quota windows and day/week/month aggregation;
3. build the Desk shell, overview, charts, search, and shared inspector;
4. add provider, slot, quota, routing, and lane controls with durable audit;
5. add diagnostics, redacted payload detail, exports, and retention;
6. run focused verification, build Desk, and replace the old Cheap Lane route.

Legacy read and control endpoints remain during migration. The new page can be
feature-gated until snapshot parity and mutation tests pass. Schema additions
are backward compatible, and rollback restores the old page without removing
new history columns or audit records.

## Acceptance Criteria

The work is complete when:

1. one owner-only Desk page presents a coherent live view of the entire Cheap
   Lane and clearly marks partial or stale data;
2. day, week, and month consumption is visible for tokens and every available
   provider-native quota unit, with total, used, remaining, reset, source, and
   confidence;
3. authoritative, configured, estimated, unknown, and conflicting quota data
   cannot be mistaken for each other;
4. every Cheap Lane provider, model, profile, and slot is searchable and
   inspectable;
5. providers can be added, paused, deactivated, and deleted from the page, and
   persistent versus temporary effects are explicit;
6. every routing decision can be explained through candidate factors,
   selection, retries, and fallbacks;
7. the technical log is searchable and paginated and recent redacted payloads
   can be inspected without exposing credentials;
8. Cheap Lane-related Central incidents and domain diagnostics are linked in a
   single timeline;
9. every mutation has a durable, secret-free audit record and returns the
   authoritative result;
10. live disconnects, source failures, unknown values, and stale measurements
    are visible and never masquerade as healthy zeroes;
11. the UI matches Jarvis Desk, remains usable at supported window sizes, and
    contains no overlapping or layout-shifting controls;
12. focused backend, API, React, accessibility, visual, and desktop build
    verification passes.
