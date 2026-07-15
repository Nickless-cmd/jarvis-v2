# Fase 1 — Klient-tool-delegering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development eller executing-plans.

**Goal:** Lade v2-turn-loopet delegere execution=="client"-tools til den forbundne klient (emit tool_use → pause → klient kører lokalt → poster resultat → loop genoptager), spejlet på approval-gaten. Fuldt flag-gated (default OFF) så production er byte-identisk indtil flippet.

**Architecture:** Additivt fundament (state + delegerings-modul + endpoint) er BYGGET og testet. Tilbage: ét flag-gated call-site i turn-loopet.

---

## Status: BYGGET (additivt, testet, inert til wiring+flag)

- **State** ([run_control_state.py](../../../core/services/visible_runs_sections/run_control_state.py)): `_VISIBLE_RUN_CLIENT_TOOL_PREFIX`, `_set/_get_visible_client_tool_state`, `resolve_visible_client_tool(call_id, result_text)` — spejler approval-state.
- **Delegerings-modul** ([client_tool_delegation.py](../../../core/services/visible_runs_sections/client_tool_delegation.py)): `begin_client_tool(...)` + `async await_client_tool_result(call_id, timeout_s=300)` — poll hver 0.25s, expired ved timeout. Boy Scout: egen enhed, holder visible_runs.py lille.
- **Endpoint** ([chat.py](../../../apps/api/jarvis_api/routes/chat.py)): `POST /chat/runs/{run_id}/tool-result` {call_id, result} → resolve. 400 uden call_id, 404 hvis ikke pending.
- **Re-eksport** fra visible_runs.py (konsistent import).
- **Tests**: [test_client_tool_delegation.py](../../../tests/test_client_tool_delegation.py) — 10 grønne (state, poll, timeout, endpoint 200/400/404).

## Tilbage: call-site-wiring (flag-gated, IKKE udført endnu)

**Fil:** `core/services/visible_runs.py` — de to tool-eksekverings-sites (first-pass ~1789, agentisk runde ~3818).

**Kontrakt (skal bygges som TDD, flag `client_tool_delegation_enabled` default False):**
1. Ved tool-eksekvering: for hvert tool-kald, slå `jc_tool_catalog.execution_location(name)` op.
2. Hvis `== "client"` OG flag ON OG klienten har deklareret capability for tool'et:
   - `begin_client_tool(call_id, ...)`, emit `tool_use` (klient-exec-variant) over SSE, `result = await await_client_tool_result(call_id)`.
   - None (timeout/expired) → samme denial-tekst-mønster som approval-timeout.
   - Ellers → brug result som tool-resultat, fortsæt loop.
3. Hvis `!= "client"` ELLER flag OFF → uændret server-side eksekvering (byte-identisk med i dag).
4. Klient-capability-deklaration læses fra request (Fase 2 leverer klient-siden).

**Boy Scout:** call-site-branchen bør kalde en lille helper (i client_tool_delegation.py), så visible_runs.py ikke vokser.

**Test:** syntetisk klient der besvarer `tool_use`; verificér loop-genoptag + at side-effekt-regnskabet (cost/memory/gates) fyrer uændret; flag OFF → ingen adfærdsændring.
