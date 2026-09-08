# Phase 0 — kilde-til-sandhed-inventar

Dato: 2026-09-08 · Hører til [DeepSeek Harness Lessons for Jarvis-v2](2026-09-08-deepseek-harness-lessons-for-jarvis.md)

Spec'ens Fase 0 kræver som første punkt: *«inventory every direct writer/reader
of `chat_messages`, approval tables, agent runtime tables, tool routing maps,
and terminal run outcomes»*, og som udgangs-kriterium: *«source-of-truth
inventory has no unresolved table or writer»*.

Dette er den måling. Den er lavet med SQL-mønstre mod kildetræet
(`core/`, `apps/api/`, `apps/jarvisx/`, `scripts/`, `tests/`), og
testfiler er talt fra i tallene nedenfor.

## Metoden — og den fælde den faldt i først

Første måling gav 715 læsere af `chat_messages` og 130 skrivere til
`visible_runs`. Begge tal var forkerte, af to grunde:

1. `\bFROM\s+(\w+)` uden versal-krav matcher Pythons `from core import …`.
   SQL i dette repo skrives med STORE nøgleord; mønstret kræver nu det.
2. **`.claude/worktrees/` indeholder 21 fulde repo-kopier (589 MB)** fra
   tidligere agent-kørsler. `rglob` fra repo-roden talte hver fil op til 22
   gange. Kildetræet har 2.892 python-filer; roden har 51.562.

Enhver senere måling i dette repo skal udelukke `.claude/worktrees/`. Et tal
målt over hele roden er 20 gange for stort og ser plausibelt ud.

## Skrivere — hvem ejer rækkerne

| tabel | skrivere | læsere |
|---|---|---|
| `chat_messages` | **`core/services/chat_sessions.py`** | 39 |
| `chat_sessions` | `core/services/chat_sessions.py`, `core/services/security_guard.py` | 11 |
| `visible_runs` | `core/services/visible_runs_outcomes.py` | 15 |
| `visible_work_units` | `core/services/visible_runs_outcomes.py` | 6 |
| `capability_approval_requests` | `core/runtime/db_capability_approval.py`, **`core/tools/workspace_capabilities_approval.py`** | 1 |
| `tool_intent_approval_requests` | `core/runtime/db_governance.py`, **`core/runtime/db_schema.py`** | 3 |
| `approval_feedback_log` | `core/runtime/db_capability_approval.py` | 1 |
| `approval_notification_outbox` | `core/services/approval_outbox.py` | 1 |
| `agent_registry`, `agent_runs`, `agent_messages`, `agent_tool_calls` | `core/runtime/db_agent_runtime.py` | 1–2 |
| `tool_router_decisions` | `core/services/tool_router.py` | 2 |
| `composite_tools` | `core/runtime/db_composites.py` | 1 |

## Hovedfundet: skrivesiden er allerede samlet

`chat_messages` har **præcis én skrivende fil**. Spec'ens Fase 1 kræver at kun
projektoren må skrive kompatibilitetsrækker for ledger-sessioner; der er ét sted
at håndhæve det, ikke tres. Det samme gælder `visible_runs`,
`visible_work_units` og hele agent-runtime-familien.

Det er en bedre udgangsposition end spec'en antager, og det ændrer risikoen ved
Fase 1: der er ingen spredt skrivesti at indhegne først.

## Tre overlap — og de er ikke ens

### 1. `chat_sessions` ← `security_guard.py` — ufarligt, men skal skrives ned

`security_guard` skriver kun `locked`, `locked_reason`, `locked_at`. Ingen anden
skriver rører de kolonner. Det er **disjunkt kolonne-ejerskab**, ikke en
konflikt — men det er ikke skrevet ned nogen steder, og et inventar der kun
tæller tabeller ville have flaget det som et problem.

Handling: registrér som erklæret delt tabel med kolonne-ejerskab. Ingen ændring.

### 2. `capability_approval_requests` ← `workspace_capabilities_approval.py` — ÆGTE overlap

`core/tools/workspace_capabilities_approval.py` udfører rå
`INSERT INTO capability_approval_requests` udenom `db_capability_approval.py`,
som ellers er tabellens DB-lag. To steder skriver de samme rækker gennem to
forskellige veje.

Det er præcis dét spec'ens udgangs-kriterium *«no unresolved writer overlap»*
peger på. Handling: tool-laget skal gå gennem DB-laget.

### 3. `tool_intent_approval_requests` ← `db_schema.py:1403` — forkert lag

`db_schema.py` er skema-modulet, men indeholder en rigtig datamutation
(`UPDATE … SET approval_id = ?, resolved_at = …`). Skema og data bør ikke bo
samme sted; en læser der leder efter skriveren finder den ikke der.

Handling: flyt til `db_governance.py`, som ejer tabellen i forvejen.

## To godkendelses-tabeller, ikke én

`capability_approval_requests` og `tool_intent_approval_requests` er to
selvstændige tabeller med hver sit DB-lag. Spec'ens Fase 4 siger *«choose the
canonical existing approval store»* — kandidaterne er nu navngivet, og de har
hver sin skriver. Valget kan træffes på data frem for på hukommelse.

## Udestår i Fase 0

Dette dækker første punkt på listen. Endnu ikke gjort:

- klassifikation af hver eventbus-familie, Central-trace, SSE-buffer og
  projektionstabel som canonical / projection / telemetry / ephemeral
- inventar over hver shell-/subprocess-sti og dens FAKTISKE sandkasse-,
  netværks-, miljø- og fail-open-adfærd
- karakteriseringstests for de otte forløb spec'en nævner
- minimal-mode-basislinjen fra §12
- udskillelsen fra `visible_runs.py` (7.290 linjer)
