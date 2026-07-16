# Implementeringsplan — Agent Tool-delegation

**Spec:** `docs/superpowers/specs/2026-07-16-agent-tool-delegation-v3.md`
**Version:** v3.1 (1029 linjer, 17 revisionsnoter)
**Prioritet:** Høj — låser op for al agent-baseret tool-brug

---

## Afhængighedsgraf

```
Fase 1 (Fundament)
    │
    ▼
Fase 2 (Governance) ◄── Fase 4 (Navne) — parallel
    │                      │
    ▼                      ▼
Fase 3 (Activation)    Fase 5 (Skills) — kan starte efter 1.3
    │                      │
    ▼                      ▼
Fase 6 (Schedules) ──► Fase 7 (Sessioner) ──► Fase 8 (Watcher test)
```

- **Pilen** = blokerende afhængighed
- **Parallelle** = kan køre samtidigt
- **Fase 4+5** kan starte når Fase 1 (resolve_agent_tools) er på plads
- **Fase 6** kræver Fase 5 (skills) da schedules spawner skills
- **Fase 7** kræver Fase 3 (activation) + Fase 4 (navne)
- **Fase 8** er standalone — kan gøres når som helst efter Fase 1

---

## Fase 1: Fundament (ROLE_TOOLBOXES + resolve_agent_tools)

**Anslået:** 2-3 timer
**Afhængighed:** Ingen
**Fil:** `core/agent_runtime_base.py` (runtime)

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 1.1 | Opret `ROLE_TOOLBOXES` konstant | 5 entries (none/read-only/read-write/can-spawn/watch) med korrekte tool-lister | Ingen ændring i ekstern adfærd — kun konstant |
| 1.2 | Tilføj `default_execution_domain` til `AGENT_ROLE_TEMPLATES` | Hver rolle har domain (bjorn/hybrid) | Tabel i spec'en |
| 1.3 | Implementer `resolve_agent_tools()` | 5 enhedstests består: researcher default, executor override, domain filter bjorn/runtime, ceiling inheritance | KERNEN i hele systemet |
| 1.4 | Kobl ind i `spawn_agent_task` | Agent uden `allowed_tools` får automatisk rollens toolbox | Én linjeændring i spawn-logik |

**Risici:** ceiling-inheritance findes allerede men er udokumentet — verificér at den matcher spec'en.

---

## Fase 2: Governance (validering + rate limiting + audit)

**Anslået:** 3-4 timer
**Afhængighed:** Fase 1 (1.3)
**Fil:** `core/central_governance.py`, `core/central_audit.py`

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 2.1 | Implementer `validate_agent_tool_call()` | 3 tests: critic kan ikke write_file, scope violation = security_event, ukendt tool_name afvises | Valideringsrækkefølge: flag → tool → scope → rate → ceiling |
| 2.2 | Implementer scope-validering | Sti i scope → allow; sti udenfor → deny + security_event; bash cd udenfor → deny | Brug `os.path.realpath()` — spec v3.1 |
| 2.3 | Implementer rate limiting | Sliding window, 60/min, 20/kald; rate_limited → retry 1 → terminate | Skal være per-agent_id |
| 2.4 | Implementer audit log | AgentToolCallLog med agent_id, name, tool, status, duration; security events separate; sensitive args kun i debug_mode | Hvert tool-kald logges |

**Risici:** performance overhead ved sliding window per agent — overvej simpel counter hvis sliding window er for dyrt.

---

## Fase 3: Activation (owner-gate)

**Anslået:** 1 time
**Afhængighed:** Fase 2
**Fil:** `config.yaml`, runtime startup

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 3.1 | Sæt `agent_tools_enabled = True` | Nye agenter får tools; eksisterende fortsætter uden; Bjørn har godkendt | Owner-gate — KRÆVER Bjørns approval |
| 3.2 | Integrationstest i jarvis-code | 4 tests: researcher→read_file, executor→write_file, planner→ingen, override→virker | Kør med `agent:explore` |

**Risici:** ingen — men må ikke ske før Fase 1+2 er testet.

---

## Fase 4: Agent-navne

**Anslået:** 2 timer
**Afhængighed:** Fase 1 (1.3) — kan køre parallelt med Fase 2
**Fil:** `core/agent_registry.py`, `core/agent_runtime_base.py`

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 4.1 | Tilføj `name: str \| None` til AgentConfig | Navn kan sættes ved spawn; unikt inden for aktive | Valgfrit felt |
| 4.2 | Implementer `validate_agent_name()` | Regex `^[a-z][a-z0-9_-]{2,31}$`; dublet → name_conflict | Case-insensitive lookup |
| 4.3 | Opdater AgentRegistry (name→agent_id) | `terminate_agent()` accepterer både agent_id og name; `list_agents()` returnerer navne | Mapping dict + reverse lookup |
| 4.4 | Opdater log-strukturer | AgentToolCallLog.agent_name; AgentCostAccount.agent_name | Brug `agent_name: str \| None` |

**Risici:** samtale-reference "Bob" → "bob" matching kræver normalisering i hele pipeline.

---

## Fase 5: Delegated tasks / Skills

**Anslået:** 3 timer
**Afhængighed:** Fase 1 (1.3) — parallel med Fase 2/4
**Fil:** `~/.jarvis-v2/skills/`, `core/skill_registry.py`

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 5.1 | Opret `~/.jarvis-v2/skills/` directory | Directory findes efter installation | Gøres ved Centralen setup |
| 5.2 | Implementer SkillConfig dataclass | Alle spawn-parametre + goal_template | TOML-indlæsning |
| 5.3 | Implementer load_skills() + registry | Scanner .toml-filer ved startup; returnerer dict[name→SkillConfig | Auto-load |
| 5.4 | Implementer spawn_agent(skill=...) | Lookup + merge + override; goal_template {variable} substitution; owner_approval gate | Override-prioritet: inline goal > template > default |
| 5.5 | Implementer CRUD | create/edit/delete/list_skill; skriver .toml; validerer før gemning | Skal kunne oprettes af Jarvis |

**Risici:** TOML-parsing — brug standard lib `tomllib` (Python 3.11+).

---

## Fase 6: Scheduled tasks

**Anslået:** 4 timer
**Afhængighed:** Fase 5 (skills) + Fase 4 (navne)
**Fil:** `core/schedule_daemon.py`, `~/.jarvis-v2/schedules/schedule.db`

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 6.1 | ScheduledTask dataclass | Alle felter som specificeret | Inkl. concurrency=skip/allow, timezone |
| 6.2 | SQLite-backed ScheduleStore | Gemmer i `~/.jarvis-v2/schedules/schedule.db`; persistent=True overlever reboot | WAL mode |
| 6.3 | Cron-parser (5-felts) | Korrekt next_run beregning | Standard UNIX cron |
| 6.4 | ScheduleDaemon | 60s poll; spawner agent ved next_run; logger til central_audit; auto-disable ved 3 failures + notification | Letvægtsproces i Centralen |
| 6.5 | CRUD API | create/list/update/delete/pause/resume/run_now | Alle kommandoer |

**Risici:** cron-parser er ikke-triviel — overvej at bruge `croniter` bibliotek i stedet for at skrive fra bunden.

---

## Fase 7: Persistent sessioner

**Anslået:** 4 timer
**Afhængighed:** Fase 3 (activation) + Fase 4 (navne)
**Fil:** `core/session_store.py`, `~/.jarvis-v2/sessions/sessions.db`

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 7.1 | SQLite schema (3 tabeller) | agent_sessions, agent_session_messages, agent_session_children | WAL mode, single-writer lock |
| 7.2 | SessionStore klasse | CRUD for sessioner + messages; thread-safe | Lås på skrivning |
| 7.3 | resume_session() | Genopretter kontekst + message history; fejl hvis status != active | Genindlæs messages i rækkefølge |
| 7.4 | fork_session() | Kloner session til ny gren; gemmer parent-child relation | Transaktionel — rollback ved fejl |
| 7.5 | TTL + auto-cleanup | Tjek ved startup + hver time; FIFO-arkiv ved storage limits; extend_session() API | Cleanup logger til audit |

**Risici:** storage limits (100 sess, 1000 msg, 500K tokens) — sørg for at FIFO-arkivering ikke sletter noget der er in-use.

---

## Fase 8: Watcher test

**Anslået:** 30 min
**Afhængighed:** Fase 1 (1.1) — standalone
**Fil:** `tests/test_watcher_role.py`

| ID | Opgave | DoD | Noter |
|----|--------|-----|-------|
| 8.1 | Implementer test for watcher-rolle | Watcher har watch-toolbox (read-only, ingen web); watcher kan ikke skrive eller spawne | Enkel integrationstest |

---

## Ikke-kritiske forbedringer

| ID | Opgave | Prioritet | Notes |
|----|--------|-----------|-------|
| N.1 | Web-domain i role-tabellen | Lav | Når der er brug for web-only agent |

---

## Estimater

| Fase | Anslået | Afhængig | Kan parallel-startes |
|------|---------|----------|---------------------|
| 1 | 2-3t | — | — |
| 2 | 3-4t | Fase 1 | — |
| 3 | 1t | Fase 2 | — |
| 4 | 2t | Fase 1 | ✅ Ja (med Fase 2) |
| 5 | 3t | Fase 1 | ✅ Ja (med Fase 2/4) |
| 6 | 4t | Fase 5 | — |
| 7 | 4t | Fase 3+4 | — |
| 8 | 0.5t | Fase 1 | ✅ Ja (når som helst) |
| **Total** | **~20t** | — | **3 parallelle spor** |

---

## Anbefalet eksekveringsrækkefølge

Ved at udnytte parallelisering:

```
Spor A:  Fase 1 → Fase 2 → Fase 3
Spor B:  Fase 4 ──────────────┐
Spor C:  Fase 5 ──────────┐   │
                           ▼   ▼
                         Fase 6 → Fase 7 → Fase 8
```

Spor A, B, C kan køre samtidigt efter Fase 1. Spor A er kritisk sti — Fase 3 (activation) er gate for alt andet.

---

*Plan genereret 2026-07-16 — Jarvis*
*Baseret på spec v3.1 — 17 revisionsnoter, 32 delopgaver, 8 faser*
