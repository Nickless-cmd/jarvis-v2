# Mission Control: Skills, Hardening & Lab Tabs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the three empty Mission Control tabs (Skills, Hardening, Lab) with real data from jarvis-v2's existing backend systems.

**Architecture:** Three self-fetching React components (each calls its own `/mc/*` endpoint on mount) + three new FastAPI endpoints in `mission_control.py` that aggregate data from the DB, tool registry, approval system, and cost ledger. No changes to `useMissionControlPhaseA.js` or `MissionControlPage.jsx` — tabs manage their own fetch lifecycle like `AgentsTab` and `AutonomyTab`.

**Tech Stack:** React + existing `s/T/mono` theme tokens + shared MC components (Card, SectionTitle, MetricCard, ListRow, EmptyState, Chip, StatusDot, ScrollPanel, Skeleton, Btn). Python FastAPI. SQLite via `core.runtime.db`.

---

## Skills Tab

### What it shows
- **Metrics row:** Total tools, approval-required count, calls today (from `capability_invocations`), distinct categories
- **Searchable tool list:** All tools from `simple_tools._TOOLS` — name (monospace), description, risk chip (`read` / `write` / `approval`)
- **Recent capability invocations:** Last 10 rows from `capability_invocations` — tool name, status chip, relative time

### Backend `/mc/skills`
```python
{
  "tools": [
    {
      "name": str,           # from tool["function"]["name"]
      "description": str,    # first 120 chars of tool["function"]["description"]
      "required": list[str], # tool["function"]["parameters"]["required"]
    }
  ],
  "total": int,
  "recent_invocations": [
    {
      "capability_name": str,
      "status": str,         # ok / error / blocked
      "invoked_at": str,     # ISO timestamp
    }
  ],
  "calls_today": int,        # COUNT(*) WHERE date(invoked_at) = date('now')
}
```

Tool risk is derived client-side: if `name` contains `write`, `delete`, `send`, `exec`, `create`, or `required` is non-empty → `write`/`approval`; else → `read`.

### Frontend `SkillsTab.jsx`
- Accepts no props — self-fetches `GET /mc/skills` on mount
- Search box filters `tools` array by name/description (client-side, no re-fetch)
- Chip colors: `read` → blue, `write` → amber, `approval` → red
- Skeleton while loading

---

## Hardening Tab

### What it shows
- **Metrics row:** Pending approvals, approved today, denied today
- **Integrations card:** Telegram, Discord, Home Assistant, Anthropic — green dot if configured, grey if not
- **Recent tool-intent requests:** Last 10 from `tool_intent_approval_requests` — intent_type, intent_target (truncated), state chip, relative time
- **Autonomy level:** Single line from `runtime_state_kv` key `autonomy_level` (or fallback `direct`)

### Backend `/mc/hardening`
```python
{
  "pending": int,          # COUNT WHERE approval_state = 'pending'
  "approved_today": int,   # COUNT WHERE approval_state = 'approved' AND date(resolved_at) = date('now')
  "denied_today": int,     # COUNT WHERE approval_state = 'denied' AND date(resolved_at) = date('now')
  "autonomy_level": str,   # from runtime_state_kv or 'direct'
  "integrations": {
    "telegram": bool,      # telegram_bot_token in runtime.json
    "discord": bool,       # discord_bot_token in runtime.json
    "home_assistant": bool,# home_assistant_url in runtime.json
    "anthropic": bool,     # anthropic_api_key in runtime.json
  },
  "recent_approvals": [
    {
      "intent_type": str,
      "intent_target": str,
      "approval_state": str,  # pending / approved / denied / expired
      "requested_at": str,
    }
  ],
}
```

### Frontend `HardeningTab.jsx`
- Self-fetches `GET /mc/hardening` on mount
- StatusDot: green for configured/approved, amber for pending, grey for not-configured, red for denied
- Relative timestamps via `formatFreshness` from `../meta`

---

## Lab Tab

### What it shows
- **Metrics row:** Total cost today (USD), input tokens today, output tokens today, run count today
- **Provider breakdown table:** Provider, cost USD, token count, call count — sourced from `costs` table, grouped by provider, last 24h
- **DB stats card:** Total events, total visible_runs, total chat_sessions, total tool_intent approvals
- **Recent events feed:** Last 15 events from event_bus — family chip, kind (truncated), relative time. Same data as Observability tab's event list but simpler rendering.

### Backend `/mc/lab`
```python
{
  "costs_today": {
    "total_usd": float,
    "input_tokens": int,
    "output_tokens": int,
    "calls": int,
  },
  "providers_today": [
    {
      "provider": str,
      "cost_usd": float,
      "input_tokens": int,
      "output_tokens": int,
      "calls": int,
    }
  ],
  "db_stats": {
    "events": int,
    "runs": int,
    "sessions": int,
    "approvals": int,
  },
  "recent_events": [
    {
      "id": int,
      "kind": str,
      "family": str,
      "created_at": str,
    }
  ],
}
```

### Frontend `LabTab.jsx`
- Self-fetches `GET /mc/lab` on mount + manual refresh button
- Provider table: sorted by cost descending
- Family chips: reuse same color logic as Observability tab
- `recent_events` shown in a `ScrollPanel`

---

## File Map

| File | Change |
|------|--------|
| `apps/api/jarvis_api/routes/mission_control.py` | Add `/mc/skills`, `/mc/hardening`, `/mc/lab` endpoints |
| `apps/ui/src/components/mission-control/SkillsTab.jsx` | Replace stub with full implementation |
| `apps/ui/src/components/mission-control/HardeningTab.jsx` | Replace stub with full implementation |
| `apps/ui/src/components/mission-control/LabTab.jsx` | Replace stub with full implementation |

No other files need changes.

---

## Data Sources

| Data | Source |
|------|--------|
| Tool list | `simple_tools._TOOLS` — imported at request time |
| Capability invocations | `capability_invocations` table in DB |
| Tool intent approvals | `tool_intent_approval_requests` table in DB |
| Autonomy level | `runtime_state_kv` table, key `autonomy_level` |
| Integration config | `~/.jarvis-v2/config/runtime.json` via `_load_config()` pattern |
| Costs | `costs` table via `telemetry_summary()` + custom 24h query |
| Events | `event_bus.recent(limit=15)` |
| DB stats | Simple COUNT(*) queries on each table |

---

## Error Handling
- All three endpoints: wrap DB queries in try/except, return partial data rather than 500
- Frontend: show `EmptyState` if `data` is null or fetch fails; no crash
- Tool list fetch: if `simple_tools` import fails, return `tools: [], total: 0`
