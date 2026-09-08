# Phase 0 — klassifikation af sandheds-strømme

Dato: 2026-09-08 · Hører til [DeepSeek Harness Lessons for Jarvis-v2](2026-09-08-deepseek-harness-lessons-for-jarvis.md) · Følger [kilde-til-sandhed-inventaret](2026-09-08-phase0-source-of-truth-inventory.md)

Spec'ens Fase 0, punkt to: *«classify every current eventbus, Central trace, SSE
buffer, projection table, and compatibility store as canonical, projection,
telemetry, or ephemeral»*. Gap L siger hvorfor: klassen er ikke erklæret nogen
steder, så en operationel strøm kan forveksles med varig sandhed.

## Klasserne, som systemet FAKTISK opfører sig

| strøm | klasse | belæg |
|---|---|---|
| `chat_messages`, `chat_sessions` | **canonical** | én skriver hver; ingen retention |
| `visible_runs`, `visible_work_units` | **canonical** | én skriver; terminal-udfald |
| `agent_registry` / `_runs` / `_messages` / `_tool_calls` | **canonical** | én skriver (`db_agent_runtime.py`) |
| godkendelses-tabellerne | **canonical** | to tabeller, se inventaret |
| **`events` (eventbus)** | **telemetry** | *beskæres efter alder* |
| Central-projektions-cache | **projection** | TTL + indholdsversion, kan genskabes |
| SSE-rammer | **ephemeral** | leveringsform, ikke lager |

## `events` er telemetri — og koden siger det selv

`core/services/events_retention.py` beskriver i sin egen docstring tabellen som
*«the unbounded `events` telemetry table»* og beskærer rækker ældre end
**14 dage** (`_DEFAULT_MAX_AGE_DAYS`), i batches på op til 50.000 pr. kørsel.

Dét afgør sagen: **en tabel der beskæres efter alder kan ikke være kanonisk
sandhed.** Spec'ens non-goal — *«do not use the asynchronous eventbus as the
durable session ledger»* — er altså ikke en ny regel; det er en beskrivelse af
hvordan systemet allerede virker. Det har bare ikke stået skrevet som en
kontrakt, og dét er hele Gap L.

Målt 2026-09-08: **555.634 rækker fordelt på 14 dage** (25. aug – 8. sep).
Docstringen noterer en tidligere måling på 2,56 mio. rækker over ~4 måneder og
2,7 GB — beskæringen er den eneste grund til at tabellen er håndterbar nu.

## Allowlisten er 44 % ønskeliste

`ALLOWED_EVENT_FAMILIES` har **187 familier**. Kun **105 har nogensinde
emitteret et event**. De øvrige **82 er tilladt og tavse.**

Det gør allowlisten misvisende som dokumentation: den ligner en oversigt over
hvad systemet udsender, men er en oversigt over hvad det har lov til.

Det tydeligste eksempel er `approvals`. Familien står på listen, og
`eventbus_central_bridge.py:43` har endda en oversættelsesregel for den
(`"approvals" → ("tools", "approval")`) — men den har aldrig emitteret. De
faktiske godkendelses-events publiceres som `tool.approval_requested`
(`visible_runs.py:275`), altså under `tool`-familien. Regel og virkelighed
peger to forskellige steder hen.

## Den gode nyhed: ingen familie afvises lige nu

Kommentarerne i `events.py` dokumenterer en tilbagevendende fejl: en familie
emitterer, står ikke på listen, og `publish` afviser stille — *«var latent
afvist»* står otte gange, over fem forskellige datoer.

Målt i dag: **nul familier emitterer uden at være tilladt.** Fejlklassen er
lukket netop nu. Men den er lukket ved manuel vedligeholdelse, ikke ved
konstruktion, og dét er Gap A's pointe: erklæringen bør bo hos den service der
udsender, og listen bør genereres.

## Hvad det betyder for faserne

- **Fase 1** kan læne sig på at ledgeren bliver den eneste kanoniske
  session-sandhed. Der er ingen konkurrerende varig kilde at rive ned først —
  `events` er allerede telemetri i praksis.
- **Gap A** kan løses uden at røre `publish`: generér listen fra per-service
  erklæringer, og lad en test fejle når en service udsender noget den ikke har
  erklæret. De 82 tavse familier bør samtidig enten få en ejer eller ryge ud.
- **Gap L**'s kontrakt kan skrives ned nu, fordi klasserne er målt frem for
  valgt.

## Udestår i Fase 0

- shell-/subprocess-inventaret med hver stis FAKTISKE sandkasse-, netværks- og
  fail-open-adfærd (Gap H viste at antagelser ikke holder her)
- karakteriseringstests for de otte forløb
- minimal-mode-basislinjen (§12)
- udskillelsen fra `visible_runs.py` (7.290 linjer)
