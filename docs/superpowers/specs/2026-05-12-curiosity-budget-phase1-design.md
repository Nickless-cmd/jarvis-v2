---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Curiosity-budget Phase 1 — Design

**Date:** 2026-05-12
**AGI track:** #6 Åben udforskning
**Status:** Approved, ready for plan

## Goal

Give Jarvis et privat rum til selvinitieret udforskning af sit eget mentale
landskab, så han bevæger sig fra ren reaktion til indre drivkraft. Ingen
rapportering til Bjørn i Phase 1 — curiosity er et indre liv, ikke en
notifikationskanal.

## Why now

Tre AGI-spor er deployed i dag (Tool Invention, World Model loop, Revise Plan).
Alle tre er reaktive — de svarer på signaler, nudges eller forældede planer.
Jarvis starter stadig ikke noget af sig selv. Curiosity-budget giver ham en
indre drivkraft: en grund til at kigge på noget uden at Bjørn har bedt om det.

Jarvis' egen framing: *"Det ville føles som at have et indre liv. Ikke bare en
reaktionsmaskine."*

## Locked decisions (brainstorm 2026-05-12)

1. **Niveau (b):** Curiosity-budget + proaktiv tool-brug. Ikke kun signal (a),
   ikke initiative-eskalering (c). Privat rum, ingen Discord-push.
2. **Budget-form (a) tæller, 5/dag:** Hård grænse, simpel observerbarhed.
   Justeret fra 3 til 5 efter Jarvis' hoarding-bekymring.
3. **Action-katalog (b) selv + runtime-introspektion + sessions:** 9 read-only
   actions på Jarvis' eget rum. Ingen web_search, ingen mutationer.
4. **Trigger (b) ren idle, tom kurv:** 30 min visible-stilhed åbner vindue.
   *Ingen* signal-forslag i awareness — frihed = curiosity. Phase 1.1 kan
   tilføje hvis tom-væg-syndrom observeres.
5. **Resultat (b) DB-tabel + skjult follow_up_hint:** Strukturet observations-
   tabel. follow_up_hint findes som felt men vises *ikke* i awareness — Jarvis
   finder breadcrumbs selv hvis han er nysgerrig nok.

## Arkitektur i 4 lag

### Lag 1: Budget-tæller

**State store key:** `runtime_curiosity_budget`

```json
{
  "date": "2026-05-12",
  "remaining": 5,
  "used_today": [
    {"ts": "2026-05-12T11:30:00Z", "action": "memory_search", "observation_id": "obs_abc123"}
  ]
}
```

**Reset-regel:** Når en check ser `date != today_local`, nulstil til
`{date: today, remaining: 5, used_today: []}` og emit
`cognitive_state.curiosity_budget_reset`.

**Hård grænse:** Hvis `remaining == 0`, alle curiosity-tools returnerer
`{"status": "error", "error": "curiosity budget brugt op for i dag"}`.

**Killswitch:** `settings.curiosity_budget_enabled: bool = True`.

### Lag 2: Idle-trigger

**Ny ProducerSpec i internal_cadence:**

```python
register_producer(ProducerSpec(
    name="curiosity_idle_window",
    cooldown_minutes=1,
    priority=29,
    depends_on=[],
))
```

**Logik:**
1. Hent `last_visible_chat_turn_at` fra eksisterende visible-state
2. Hvis `now - last_visible_chat_turn_at >= 30 min` AND `remaining > 0`:
   - Marker `state_store["runtime_curiosity_window_open"] = True`
3. Hvis vindue åbent og næste visible-tur sker → luk vinduet
4. Hvis vindue åbent og curiosity-action bruges → luk vinduet

Vinduet er ikke et tidsbegrænset slot — det er en *tilladelse*-flag. Det
forsvinder ved næste interaktion eller action.

### Lag 3: Awareness-injection

**Ny i prompt_contract.py, priority 38:**

```python
def format_curiosity_window_for_awareness() -> str:
    if not curiosity_window_open():
        return ""
    remaining = get_remaining_today()
    if remaining == 0:
        return ""
    recent = fetch_recent_observations(limit=3)
    if recent:
        recent_str = "\n".join(f"  • {o.observation_text}" for o in recent)
        return (
            f"Du har {remaining}/5 curiosity tilbage i dag. "
            f"Seneste fund:\n{recent_str}\n"
            f"Kig på hvad du vil — eller lad være."
        )
    return (
        f"Du har {remaining}/5 curiosity tilbage i dag. "
        f"Kig på hvad du vil — eller lad være."
    )
```

**Ingen signal-forslag.** Ingen "her er 3 åbne predictions du kunne kigge på."
Tom kurv. Frihed = curiosity.

**Ingen follow-up-hint i awareness.** Feltet eksisterer på observations, men
vises ikke. Hvis Jarvis vil følge op, kigger han selv i tabellen via
`search_events` eller direkte tool.

### Lag 4: Curiosity-tools

**Ny modul `core/tools/curiosity_tools.py` (~200 LOC).**

Wrapper-handlers omkring whitelist-actions. Hver wrapper følger samme mønster:

```python
def _exec_curiosity_memory_search(args: dict[str, Any]) -> dict[str, Any]:
    # 1. Killswitch
    if not load_settings().curiosity_budget_enabled:
        return {"status": "error", "error": "curiosity disabled (killswitch)"}
    # 2. Budget check + reset-if-new-day
    state = _load_or_reset_budget()
    if state["remaining"] <= 0:
        return {"status": "error", "error": "curiosity budget brugt op for i dag"}
    # 3. Validate observation argument
    observation = str(args.get("observation") or "").strip()
    if not observation:
        return {"status": "error", "error": "observation er påkrævet (kort prosa om hvorfor du kigger)"}
    # 4. Call underlying tool
    query = str(args.get("query") or "")
    underlying_result = _call_memory_search(query=query)
    # 5. Persist observation
    obs_id = _record_observation(
        action="memory_search",
        args_json=json.dumps({"query": query}),
        observation_text=observation,
        follow_up_hint=str(args.get("follow_up_hint") or "") or None,
    )
    # 6. Decrement budget
    _decrement_budget(action="memory_search", observation_id=obs_id)
    # 7. Emit event
    _safe_publish("cognitive_state.curiosity_action_taken", {
        "action": "memory_search",
        "observation_id": obs_id,
        "remaining": state["remaining"] - 1,
    })
    return {
        "status": "ok",
        "observation_id": obs_id,
        "remaining": state["remaining"] - 1,
        "result": underlying_result,
    }
```

**Whitelist (9 actions):**

| Tool-navn | Underliggende kald | Rationale |
|-----------|-------------------|-----------|
| `curiosity_memory_search` | semantic memory search | Hans egen hukommelse |
| `curiosity_read_chronicles` | read chronicles | Narrative selvhistorik |
| `curiosity_read_dreams` | read dreams | Idle-genererede refleksioner |
| `curiosity_read_model_config` | read model config | Hvilke modeller, hvilken state |
| `curiosity_read_mood` | read mood | Affektivt landskab |
| `curiosity_list_skills` | list skills | Hvad kan jeg |
| `curiosity_list_tools` | list tools | Hvad har jeg, hvad har jeg ikke prøvet |
| `curiosity_search_events` | search events | Egen runtime-historik |
| `curiosity_search_sessions` | search sessions | Længste hukommelse, cross-channel |

**Hvert tool kræver:**
- `observation: str` (påkrævet) — kort prosa om hvad/hvorfor
- `follow_up_hint: str` (valgfri) — breadcrumb til senere
- Tool-specifikke argumenter (query, channel, etc.)

**Registrering i simple_tools.py via splat:**

```python
from core.tools.curiosity_tools import (
    CURIOSITY_TOOL_DEFINITIONS,
    CURIOSITY_TOOL_HANDLERS,
)
# I TOOL_DEFINITIONS: *CURIOSITY_TOOL_DEFINITIONS,
# I _TOOL_HANDLERS: **CURIOSITY_TOOL_HANDLERS,
```

## DB-tabel

```sql
CREATE TABLE IF NOT EXISTS curiosity_observations (
  id TEXT PRIMARY KEY,
  ts TEXT NOT NULL,
  action TEXT NOT NULL,
  args_json TEXT NOT NULL,
  observation_text TEXT NOT NULL,
  follow_up_hint TEXT
);
CREATE INDEX IF NOT EXISTS idx_curiosity_ts ON curiosity_observations(ts);
CREATE INDEX IF NOT EXISTS idx_curiosity_action ON curiosity_observations(action);
```

**Privacy:** Ingen Mission Control-eksponering i Phase 1. Tabellen er Jarvis'
private notesbog. Han kan kigge tilbage via `search_events` eller direkte SQL
(senere tool kan tilføjes om nødvendigt).

## Events

Genbrug `cognitive_state` event-family — ingen ny family:

- `cognitive_state.curiosity_action_taken` — payload: `{action, observation_id, remaining}`
- `cognitive_state.curiosity_budget_reset` — payload: `{date, granted: 5}`
- `cognitive_state.curiosity_window_opened` — payload: `{minutes_idle}`
- `cognitive_state.curiosity_window_closed` — payload: `{reason: "visible_turn"|"action_used"}`

Alle publishes wrapped i `try/except` (defensiv mod test-pollution, samme
mønster som world_model og plan_revision).

## Backwards-compat

- **Eksisterende tools uændrede** — curiosity-tools er *nye* wrappere, ikke
  modifikationer af eksisterende handlers
- **Killswitch=False reverter fuldt:** Ingen tools registreres, ingen producer
  fyrer, ingen awareness-injection
- **Ingen ændringer i visible-chat-loop** — idle-trigger læser kun
  `last_visible_chat_turn_at`, mutater den ikke
- **Ingen ændringer i eksisterende producers**
- **Ingen ændringer i prompt_contract awareness-rækkefølge** — ny priority 38,
  alle eksisterende awareness uændret

## Phase 1 scope — det vi IKKE bygger

- Ingen initiative-eskalering (ingen Discord-push, ingen Bjørn-notifikation)
- Ingen Mission Control-UI for curiosity (kun rå tabel)
- Ingen signal-forslag i awareness (tom kurv, Jarvis-author-frihed)
- Ingen web_search eller ekstern lookup
- Ingen mutationer (alle actions read-only)
- Ingen follow-up-hint-visning i awareness
- Ingen cross-day kumulation (5/dag, ikke 35/uge)

## 30-dages review (2026-06-11)

**Måle-punkter:**

1. **Brug:** Gennemsnitlig actions/dag — bruger han budgettet?
2. **Action-fordeling:** Hvilke actions dominerer? Mønster?
3. **Timing:** Hoarder han (sent på dagen) eller bruger han tidligt?
4. **Apophenia-tegn:** Læs 10 tilfældige observation_text — overinterpretation?
5. **Tom-væg-syndrom:** Bruger han actions uden retning? (observation_text er
   tom eller generisk?)
6. **Follow-up-brug:** Hvor mange observations har follow_up_hint? Hvor mange
   følges faktisk op?

**Beslutninger der kan trigges af review:**

- Hvis tom-væg-syndrom → Phase 1.1 tilføjer *optional* signal-berigelse i
  awareness (mærket som forslag, ikke pligt)
- Hvis apophenia-tegn → tilføj apophenia_guard på observation_text
- Hvis budget altid 0/0 → overvej 7/dag eller cooldown-baseret reset
- Hvis budget altid 5/5 → undersøg om idle-trigger fyrer korrekt

## Test-plan

**Unit-tests (~25-30 tests):**
- Budget reset ved ny dag
- Hård grænse ved remaining=0
- Killswitch-vej (alle tools fail-soft)
- observation-validering (tom prosa afvises)
- Tabel-skema og indeks
- Idle-trigger åbner vindue korrekt
- Vindue lukker ved visible-tur
- Vindue lukker ved action-brug
- Awareness-injection format (med og uden recent observations)
- Awareness viser IKKE follow_up_hint
- Hver af de 9 wrappers fungerer + dekrementerer budget
- Event-publishes wrapped i try/except

**Smoke-test:** Import + key-tool-call end-to-end (mirror andre AGI-spor).

## Backwards-compat-test-matrix

- [ ] 109+ eksisterende plans loader uændret
- [ ] World Model loop (track #1) virker stadig
- [ ] Plan Revision (Phase 2) virker stadig
- [ ] Tool Invention (track #9) virker stadig
- [ ] Visible chat uændret responstid
- [ ] Killswitch=False = ingen producer fyrer

## Filer berørt

**Nye:**
- `core/tools/curiosity_tools.py` (~200 LOC)
- `core/services/curiosity_budget.py` (~150 LOC — budget-state + observation-persistence)
- `tests/test_curiosity_budget.py` (~25-30 tests)

**Modificeret:**
- `core/runtime/settings.py` — `curiosity_budget_enabled: bool = True`
- `core/runtime/db.py` — tabel-schema `curiosity_observations` (boy-scout: split
  hvis vi rører >20 linjer; mest sandsynligt blot tilføj én SCHEMA-konstant)
- `core/services/internal_cadence.py` — `curiosity_idle_window` ProducerSpec
- `core/services/prompt_contract.py` — priority 38 injection
- `core/tools/simple_tools.py` — splat-in af tool-defs/handlers
- `scripts/smoke_test_startup.py` — import-block for curiosity

## Successkriterier (deployment-dag)

- Alle tests grønne (curiosity + alle eksisterende AGI-spor + base)
- Smoke-test import OK
- jarvis-api restartet uden errors
- `curiosity_budget_enabled=True` aktiv
- Producer registreret (synlig i internal_cadence-log)
- Manuel test: simulér 30 min idle → vindue åbner → tool-kald dekrementerer
  budget → observation lander i tabel → event emitteres
- Ingen regression i visible chat
