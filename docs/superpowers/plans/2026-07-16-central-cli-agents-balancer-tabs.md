# Central-CLI: Agents-model-roster + Balancer-tab — Implementation Plan

> **For agentic workers:** eksekvér task-for-task, TDD hvor muligt (TUI: smoke/render-tests som eksisterende). Steps = checkbox.

**Goal:** (1) Tab 7 "Agents" viser HELE modellisten Jarvis kan bruge som agenter — faste rækker,
aktiv/idle/inaktiv (grå), hvad hver laver + hvornår + token-count + metadata; med se-resultat +
pause + afbryd. (2) Ny Tab 8 "Balancer" — realtime hele cheap-lane/load-balancer: providers/slots,
egress, quota, health, cost. Alt i CLI-HUD'en (`apps/central_cli/`), IKKE MC.

**Architecture:** Byg PÅ eksisterende: `balancer_snapshot()` (cheap_lane_balancer.py:1150),
`/mc/cheap-balancer-state` + slot reset/disable/enable (routes/cheap_balancer.py), `agents_summary()`
+ `note_agent_result()` (core/services/agents.py), `cancel_agent(agent_id)` (agent_runtime_spawn.py:960),
`CentralClient.get_json()` (central_cli/client.py:39), `_TABS`/`_TABLE_TABS` (hud.py:48),
`datasource.agents()` (datasource.py:453), `_populate_agents()` (hud_populate.py:863).

**Tech:** Python 3.11, `/opt/conda/envs/ai/bin/python -m pytest ... -o addopts=""`. CLI-tests i
`apps/central_cli/tests/`. Deploy: commit→push→container reset→restart (CLI kører klient-side, men
backend-endpoints skal deployes).

---

## Fase A — Backend-surfaces (data tabsene skal bruge)

### Task A1: /central/agents returnerer HELE model-rosteret + agent-aktivitet
**Files:** Modify `core/services/agents.py` (`agents_summary`); Test `tests/test_agents_cluster.py` (el. eksisterende agents-test)
- Roster-kilde: alle agent-brugbare modeller = `build_slot_pool()`-slots (provider::model::profil) UNIQUE på (provider, model). Merge med agent-aktivitet fra `note_agent_result`-historik (agents_summary-vinduet) på model-nøgle.
- Hver roster-række: `{model_key, provider, model, status(active|idle|inactive), last_run_at, tokens_in, tokens_out, cost_usd, current_activity, tool_calls, role, agent_id?}`. `inactive` = aldrig set / ingen nylig aktivitet; `active` = kørende run nu; `idle` = kørt før men ikke nu.
- Bevar eksisterende `agents_summary`-felter (bagudkompat) — TILFØJ en `roster`-nøgle. Test: roster indeholder alle pool-modeller, inaktive markeret, aktive med aktivitet.

### Task A2: balancer-state-endpoint beriget (egress + quota + cost)
**Files:** Modify `core/services/cheap_lane_balancer.py::balancer_snapshot`; Test `tests/test_cheap_lane_balancer.py`
- Sikr snapshot pr. slot har: provider, model, auth_profile, **egress**, status (healthy/cooldown/breaker/stale/disabled), weight, daily_headroom, rpm-brug, breaker_level, cooldown_until, last_success_at, total_calls, total_failures, daily_observed. Tilføj `egress` hvis mangler (fra `resolve_egress`).
- Header-aggregat: total slots, healthy/cooldown counts, default vs account2 counts, egress-fordeling (home/vpn/he6). Test snapshot-form.

### Task A3: agent pause/afbryd-endpoint
**Files:** Modify `apps/api/jarvis_api/routes/mission_control.py` (el. central-route); Test route-smoke
- `POST /central/agents/{agent_id}/cancel` → kald `cancel_agent(agent_id, note=...)`. `POST /central/agents/{agent_id}/pause` → hvis pause-mekanisme findes brug den, ellers alias til cancel m. `note="paused"` (dokumentér). Returnér `{status, agent_id}`. Test: kald ramte cancel_agent (monkeypatch).

---

## Fase B — CLI datasource

### Task B1: datasource.agents() konsumerer roster
**Files:** Modify `apps/central_cli/central_cli/datasource.py` (`agents`, L453); Test `apps/central_cli/tests/test_datasource*.py`
- Læs `roster` fra `/central/agents`; shape hver række til Agents-tabellen (model, provider, status, last_run, tokens, activity, cost). Behold side-panel raw-dict. Fald pænt tilbage til gammel form hvis `roster` mangler. Test m. stubbet client.

### Task B2: datasource.balancer() (ny)
**Files:** Modify `apps/central_cli/central_cli/datasource.py`; Test samme
- Ny `balancer(client) -> dict` der henter `/mc/cheap-balancer-state`, returnerer `{header: {...aggregat}, rows: [...per slot]}`. Self-safe (tom ved fejl). Test m. stubbet client.

---

## Fase C — HUD tabs + render

### Task C1: Agents-tab viser model-roster (grå inaktive + aktivitet)
**Files:** Modify `apps/central_cli/central_cli/hud_populate.py` (`_populate_agents` L863 + `_render_agent_detail` L895); Test `apps/central_cli/tests/test_hud_self_agents.py`
- Kolonner: `model · provider · status · aktivitet · last run · tokens · $ · tools`. Inaktive rækker i grå (FGDIM/DIM). Aktive markeret (fx ● + farve fra `_AGENT_STATUS`). Side-panel: model-detalje + seneste run-resultat (fra roster-rækkens metadata). Test render m. blandet aktiv/inaktiv roster.

### Task C2: Ny Balancer-tab (F8, lige efter agents)
**Files:** Modify `apps/central_cli/central_cli/hud.py` (`_TABS` L48 + `_TABLE_TABS` L69 + F-bindings L212+), `hud_populate.py` (ny `_populate_balancer` + `_render_balancer_detail`); Test `apps/central_cli/tests/test_hud_tabs10.py` (+ ny)
- Tilføj `("balancer", "Balancer", False)` i `_TABS` LIGE efter `("agents",...)`; tilføj "balancer" i `_TABLE_TABS`. Tilføj `Binding("f8", "show('balancer')")` og re-map efterfølgende F-taster (F9, F10…) så de matcher ny rækkefølge. `active_tab`-dispatch i renderer kalder `_populate_balancer`.
- `_populate_balancer`: header-linje (aggregat) + tabel `provider · model · profil · egress · status · weight · headroom · last run · tok/d · $/d · succ%`. Side-panel: per-slot detalje. Test tab-tilstedeværelse + render.

---

## Fase D — Handlinger (pause/afbryd/se-resultat + balancer-slot-actions)

### Task D1: agent-handlinger (se resultat / pause / afbryd)
**Files:** Modify `apps/central_cli/central_cli/hud_actions.py` + `commands.py`; Test `apps/central_cli/tests/test_hud_writes.py` (mønster for confirm-actions)
- Tastebinding på agents-tab: `Enter`=se resultat (side-panel, findes delvist), `p`=pause, `x`/`ctrl+c`=afbryd (med confirm-yes/no som eksisterende dangerous-actions). Afbryd/pause → `client` POST til `/central/agents/{id}/cancel|pause`. Kun aktiv agent kan afbrydes. Test confirm-flow + at POST rammer rigtig path.

### Task D2: balancer-slot-handlinger (reset/disable/enable)
**Files:** Modify `hud_actions.py`; Test samme
- På balancer-tab: `r`=reset slot, `d`=disable, `e`=enable → POST til `/mc/cheap-balancer/slot/{slot_id}/{reset|disable|enable}`. Confirm for disable. Test POST-path.

---

## Fase E — deploy + verifikation

### Task E1: deploy backend + live-verifikation
- Deploy (commit→push→container reset→restart jarvis-api). Verificér `/central/agents` roster + `/mc/cheap-balancer-state` live. Kør CLI mod containeren: agents-tab viser hele modellisten (grå inaktive), balancer-tab viser pool realtime, F8 virker, pause/afbryd rammer backend. Opdatér memory.

---

## Self-review note
Dæknings-gate: rørte `core/`-moduler har matchende tests. Ingen placeholders. CLI-tests følger
eksisterende smoke/render-mønster (test_hud_self_agents, test_hud_tabs10, test_hud_writes).
Data-kilder eksisterer allerede (balancer_snapshot, agents_summary, cancel_agent) — mest wiring +
render. F-tast-re-mapping ved ny tab skal verificeres (F8..F10 rykker).
