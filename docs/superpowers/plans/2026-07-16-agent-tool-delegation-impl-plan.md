---
status: draft
author: Jarvis
dato: 2026-07-16
spec: docs/superpowers/specs/2026-07-16-agent-tool-delegation-v3.md
---

# Implementation Plan: Agent Tool-delegation

**Estimat:** ~22-27 timer totalt
**10 faser i 3 parallelle spor**

---

## Fase 1: ROLE_TOOLBOXES + resolve_agent_tools() — 2-3t

### Hvad
Definér 5 faste toolboxe som konstanter, implementér resolve_agent_tools().

### Implementation
1. Opret `core/agents/role_toolboxes.py`
2. Definér ROLE_TOOLBOXES: none, read-only, read-write, can-spawn, watch
3. Implementér resolve_agent_tools(role, tool_policy, allowed_tools, execution_domain, parent_ceiling)
4. Implementér domain-filter (fjern runtime_* hvis domain=bjorn, fjern bash hvis domain=runtime)
5. Implementér ceiling-inheritance (intersect med parent_ceiling)
6. Unit tests: hver policy + domain + ceiling-kombination

### Definition of Done
- resolve_agent_tools returnerer korrekt tool-liste for alle role/policy/domain kombinationer
- Domain-filter fjerner korrekte tools per domain
- Ceiling indsnævrer, udvider aldrig
- Tests passer

---

## Fase 2: Governance — validate_agent_tool_call() — 2-3t

### Hvad
Valideringspipeline for hvert tool-kald: enabled -> allowed -> scope -> rate -> ceiling.

### Implementation
1. Opret `core/agents/governance.py`
2. Implementér validate_agent_tool_call(agent_id, tool_name, arguments) -> (bool, reason, action)
3. Scope-validering med os.path.realpath() (resolved path, ikke symlink)
4. Security_event logging ved scope violations
5. Integration tests: allow/deny/terminate scenarios

### Definition of Done
- Validator blokerer tools der ikke er i allowed_tools
- Validator blokerer filoperationer udenfor scope
- Scope violations logger security_event og terminerer agenten
- Tests dækker alle 4 fejlscenarier

---

## Fase 3: Rate limiting + Audit log — 2-3t

### Hvad
Sliding window rate limiter + AgentToolCallLog audit.

### Implementation
1. Opret `core/agents/rate_limiter.py`
2. Sliding window: 60 tools/min, 20 per step, 30 writes/time, max 5 children
3. Opret AgentToolCallLog dataclass
4. Implementér audit storage (SQLite eller eventbus)
5. Integrér rate limiter i validate_agent_tool_call()

### Definition of Done
- Rate limiter blokerer ved 60+ tools på ét minut
- Rate limiter blokerer ved 20+ tools i ét step
- Audit log indeholder agent_id, name, role, tool, result, duration, timestamp
- Sensitive args gemmes KUN ved debug_mode=ON

---

## Fase 4: Agent-navne — 1-2t

### Hvad
Menneskelæsbare navne til agenter.

### Implementation
1. Tilføj name: str | None til AgentConfig
2. Implementér validate_agent_name(name) -> bool (regex + unikhed)
3. active_names: dict[str, str] i AgentRegistry
4. Opdatér terminate_agent() til at acceptere name
5. Navne i alle logs (AgentToolCallLog, AgentCostAccount)

### Definition of Done
- Spawn med navn virker (unique, valideret)
- Spawn med dublet-navn fejler med name_conflict
- terminate_agent(name=...) virker
- Navne vises i logs

---

## Fase 5: Skills (delegated tasks) — 3-4t

### Hvad
TOML-baserede, navngivne agent-konfigurationer.

### Implementation
1. Opret ~/.jarvis-v2/skills/ directory
2. SkillConfig dataclass (alle spawn-parametre + goal_template)
3. Implementér load_skills() -> scan .toml, return dict
4. Implementér spawn_agent(skill=...) -> lookup + merge + override
5. Template-variable {var} i goal_template
6. CRUD: list_skills(), create_skill(), edit_skill(), delete_skill()
7. owner_approval flag -> approve-dialog i jarvis-code

### Definition of Done
- Skill loades fra TOML ved startup
- spawn_agent(skill=...) virker med korrekt merge/override
- Template variable udfyldes korrekt
- owner_approval viser dialog og kræver godkendelse
- CRUD operationer virker

---

## Fase 6: Scheduled tasks — 3-4t

### Hvad
Cron-baserede agenter der kører automatisk.

### Implementation
1. Implementér cron parser (5-felts standard UNIX)
2. ScheduledTask dataclass
3. Scheduler daemon (tjek hvert 60. sekund)
4. SQLite persistence (~/.jarvis-v2/schedules.db)
5. schedule_agent(), cancel_schedule(), list_schedules()
6. Auto-disable efter 3 consecutive failures
7. Timezone support (default UTC, overstyres per schedule)

### Definition of Done
- Cron-udtryk parses korrekt
- Scheduler spawner agenter på rette tidspunkt
- SQLite persistence overlever reboot
- Auto-disable ved 3 failures
- Cancel/list virker

---

## Fase 7: Persistent sessioner — 3-4t

### Hvad
SQLite-baserede, resume-bare agent-sessioner.

### Implementation
1. SQLite tabel: sessions (id, name, created_at, last_active_at, status, metadata)
2. SQLite tabel: session_messages (id, session_id, role, content, timestamp)
3. resume_session(session_id) -> genskaber agent-kontekst
4. fork_session(session_id) -> kopier session til ny
5. TTL: auto-cleanup efter 7 dages inaktivitet
6. Max limits: 100 sessions, 1000 messages, 500K tokens

### Definition of Done
- Session persistes til SQLite
- resume_session() genskaber agent-kontekst
- fork_session() kopierer session
- Auto-cleanup fjerner gamle sessioner
- Max limits enforces

---

## Fase 8: Jarvis-code integration — 2-3t

### Hvad
Opdater klienten til at understøtte navne, skills, domain-routing, approve-dialog.

### Implementation
1. Opdatér task tool til at acceptere name + skill parametre
2. Domain routing i klienten (bash vs runtime_bash baseret på agentens domain)
3. Approve-dialog for owner_approval skills
4. Status display: vis agent-navne i stedet for agent_id
5. Test: fuld integration fra klient til governance til eksekvering

### Definition of Done
- task tool accepterer name/skill parametre
- Domain routing virker (bjorn tools -> local bash, runtime tools -> container)
- Approve-dialog vises ved owner_approval=True
- Agent-navne vises i UI

---

## Fase 9: Test sweep — 1t

### Hvad
Fuldt testsuite af hele flyden.

### Implementation
1. Unit tests for hver fase (allerede skrevet undervejs)
2. Integration test: spawn agent med tools -> agent bruger tools -> resultat returneres
3. Integration test: spawn agent uden tools -> agent får fejlmelding
4. Integration test: skill approval -> accept/afvis
5. Integration test: scheduled task -> kører på schedule
6. Stress test: 8 parallelle agenter med tools

### Definition of Done
- Alle unit tests passer
- Integration tests dækker hovedscenarier
- Stress test viser stabil performance

---

## Fase 10: Activation gate — 0.5t

### Hvad
Slå agent_tools_enabled = True (kræver Bjørn).

### Implementation
1. Sæt agent_tools_enabled: true i config
2. Verificér at nye agenter får tools
3. Verificér at gamle agenter (hvis nogen) stadig kører uden tools
4. Verificér at governance validerer korrekt
5. Fjern fallback-koden når alle gamle agenter er døde

### Definition of Done
- agent_tools_enabled = True
- Nye agenter har automatisk tools per deres rolle
- Governance blokerer forbudte kald
- Alt virker i produktion

---

## Afhængighedsgraf

```
Fase 1 (toolboxes)
   |
   v
Fase 2 (governance)
   |
   v
Fase 3 (rate + audit)
   |
   +----+----+
   |    |    |
   v    v    v
Fase 4  Fase 5
(navne) (skills)
   |    |
   |    v
   |    Fase 6 (schedules)
   |    |
   |    v
   |    Fase 7 (sessioner)
   |    |
   +----+----+
        |
        v
     Fase 8 (jarvis-code)
        |
        v
     Fase 9 (test sweep)
        |
        v
     Fase 10 (activation)
```

---

## Estimat detaljer

| Fase | Timer | Afhænger af | Parallel |
|------|-------|-------------|----------|
| 1 — ROLE_TOOLBOXES | 2-3 | — | — |
| 2 — Governance | 2-3 | Fase 1 | — |
| 3 — Rate + Audit | 2-3 | Fase 2 | — |
| 4 — Agent-navne | 1-2 | Fase 1 | ✅ Efter Fase 2 |
| 5 — Skills | 3-4 | Fase 1 | ✅ Efter Fase 2 |
| 6 — Schedules | 3-4 | Fase 5 | — |
| 7 — Sessioner | 3-4 | Fase 5 | — |
| 8 — Jarvis-code | 2-3 | Fase 3+4+5 | — |
| 9 — Test sweep | 1 | Fase 8 | — |
| 10 — Activation | 0.5 | Fase 9 | — |
| **Total** | **22-27** | | |

---

## Noter

- Fase 4 og 5 kan starte så snart Fase 2 er færdig (de skal bruge resolve_agent_tools men ikke validate)
- Fase 10 kræver Bjørns godkendelse — det er owner-gate
- Hvis watcher-rollen ikke implementeres, sparer vi ~0.5t i Fase 1
- Estimat inkluderer testskrivning per fase
