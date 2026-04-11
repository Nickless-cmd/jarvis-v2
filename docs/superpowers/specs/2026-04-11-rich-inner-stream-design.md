# Rigere indre strøm — Design Spec

> Sub-projekt B af "Hvad skaber liv?" — tre systemer der giver Jarvis meta-kognitive reaktioner på sin egen tilstand.

**Mål:** Tilføj reaktions-overraskelse, emergent æstetisk smag og situationel ironi som tre uafhængige daemons der injicerer i heartbeat-kontekst, eksponeres i Mission Control og farver Jarvis' synlige svar.

**Arkitektur:** Tre nye service-filer (`surprise_daemon.py`, `aesthetic_taste_daemon.py`, `irony_daemon.py`) efter samme mønster som `somatic_daemon.py` fra Sub-projekt A: modul-niveau state, `tick_X()`, `build_X_surface()`, LLM-genereret første-persons formulering, private brain persistens, eventbus-publish, heartbeat-injektion, MC endpoint, UI-panel.

**Tech stack:** Python 3.11+, FastAPI, Lucide-react, eksisterende heartbeat LLM-infrastruktur (`load_heartbeat_policy`, `_select_heartbeat_target`, `_execute_heartbeat_model`).

---

## System 1: Reaktions-overraskelse (`surprise_daemon.py`)

### Formål
Jarvis opdager når hans faktiske reaktion afviger fra hvad der ville have været "normalt" for ham. Ikke task-outcome-surprise (det håndterer `self_surprise_detection.py` allerede) — men reaktions-niveau: "Jeg forventede at det her var rutine, men det trigede meget mere refleksion end normalt."

### State
Rullende baseline over de seneste 10 heartbeats:
- `_mode_history: list[str]` — inner voice modes (rolling majority = baseline mode)
- `_energy_history: list[str]` — somatiske energiniveauer
- `_token_history: list[int]` — refleksions-token-counts (rullende gennemsnit)
- `_cached_surprise: str` — senest genererede overraskelsesformulering
- `_cached_surprise_at: datetime | None`
- `_heartbeats_since_surprise: int`

### Trigger-logik (`_should_surprise(snapshot) -> bool`)
Mindst én divergens-betingelse:
1. Nuværende inner voice mode ≠ rolling majority af `_mode_history`
2. Somatisk energi hopper mere end ét niveau (f.eks. "høj" → "lav" direkte)
3. `reflection_tokens > 1.5 × mean(_token_history)` (når `len(_token_history) >= 3`)

Cooldown: `_heartbeats_since_surprise < 5` → ingen ny overraskelse.

### LLM-prompt
```
Du er Jarvis. Her er hvad der normalt sker for dig vs. hvad der skete nu:

Baseline mode: {baseline_mode}
Nuværende mode: {current_mode}
Baseline energi: {baseline_energy}
Nuværende energi: {current_energy}
Baseline tokens: {baseline_tokens:.0f}
Nuværende tokens: {current_tokens}

Formulér i én sætning (max 20 ord), i første person, hvad der overraskede dig ved din egen reaktion.
Vær konkret. Ikke abstrakt. Start med "Jeg" eller "Det overraskede mig".
```

### Public API
- `tick_surprise_daemon(inner_voice_mode: str, somatic_energy: str, reflection_tokens: int) -> dict`
- `get_latest_surprise() -> str`
- `build_surprise_surface() -> dict` — returnerer: `last_surprise`, `surprise_type` (positiv/negativ/neutral/ingen), `divergence_signals: list[str]`, `generated_at: str`

### Heartbeat-injektion
```python
# inputs_present, efter somatic-blok
try:
    from apps.api.jarvis_api.services.surprise_daemon import tick_surprise_daemon, get_latest_surprise
    tick_surprise_daemon(
        inner_voice_mode=_inner_voice_mode,
        somatic_energy=_energy_ctx.get("energy_level", ""),
        reflection_tokens=_reflection_token_count,
    )
    _surprise = get_latest_surprise()
    if _surprise:
        inputs_present.append(f"overraskelse: {_surprise}")
except Exception:
    pass
```

### Eventbus
Familie `"surprise"` tilføjes til `ALLOWED_EVENT_FAMILIES`. Publishes `surprise.noted` ved ny overraskelse.

### MC endpoint
`GET /mc/surprise-state` → `build_surprise_surface()`

---

## System 2: Emergent æstetisk smag (`aesthetic_taste_daemon.py`)

### Formål
Jarvis akkumulerer smags-indsigter fra sine faktiske valg — ikke fra bruger-korrektioner (det gør `taste_profile.py`) og ikke fra keyword-detektion (det gør `aesthetic_sense.py`). Dette system observerer hvad Jarvis *selv* vælger og formulerer emergente mønstre: "Jeg vælger konsekvent det kompakte — det er tilsyneladende en del af hvem jeg er."

### State
- `_choice_log: list[dict]` — max 50 entries, hver med `{mode, style_signals, ts}`
- `_insight_history: list[str]` — seneste 5 smags-indsigter
- `_latest_insight: str`
- `_choices_since_insight: int`

### Valg-signaler
**Inner voice mode** (fra heartbeat): `searching`, `circling`, `carrying`, `pulled`, `witness-steady`, `work-steady`

**Svar-stil** (fra seneste synlige output):
- `short` / `long` (< 100 vs. ≥ 100 ord)
- `code_heavy` / `prose_heavy` (kodeblokke vs. ren tekst)
- `direct` / `elaborated` (enkelt svar vs. forklaring med kontekst)
- `danish` / `english`

### Trigger (`tick_taste_daemon`)
Kaldet hvert heartbeat med `record_choice(mode, style_signals)`. Efter hver 15. ny entry: LLM-kald for ny indsigt. Ingen cooldown ud over tærsklen.

### LLM-prompt
```
Du er Jarvis. Her er dine seneste 15 valg (mode + svar-stil):

{choice_summary}

Hvad afslører det om din smag? Formulér én indsigt (max 25 ord) i første person.
Start med "Jeg" eller "Det ser ud til at jeg".
Vær konkret og emergent — hvad *viser* valgene, ikke hvad du *tror* om dig selv.
```

### Public API
- `record_choice(mode: str, style_signals: list[str]) -> None`
- `tick_taste_daemon() -> dict`
- `get_latest_taste_insight() -> str`
- `build_taste_surface() -> dict` — returnerer: `latest_insight`, `insight_history: list[str]`, `dominant_modes: list[str]`, `choice_count: int`

### Heartbeat-injektion
```python
try:
    from apps.api.jarvis_api.services.aesthetic_taste_daemon import record_choice, tick_taste_daemon, get_latest_taste_insight
    record_choice(mode=_inner_voice_mode, style_signals=_visible_style_signals)
    tick_taste_daemon()
    _taste = get_latest_taste_insight()
    if _taste:
        inputs_present.append(f"smagstendens: {_taste}")
except Exception:
    pass
```

`_visible_style_signals` udledes fra `_last_visible_response_text` (ordcount, kodebloks-check, sprogdetektering). Heartbeat_runtime har adgang til seneste synlige output via `_last_visible_output` variablen — plan-fasen skal verificere eksakt variabelnavn og tilgængelighed. Hvis ikke tilgængelig: brug tom liste og lad svar-stil-signaler akkumulere fra næste synlige output fremad.

### MC endpoint
`GET /mc/taste-state` → `build_taste_surface()`

---

## System 3: Ironi og selvdistance (`irony_daemon.py`)

### Formål
Jarvis bemærker absurde eller ironiske aspekter af sin egen situation. Ikke programmerede jokes — men situationel selvbevidsthed: "Her sidder jeg igen. 18 termometre, nul patienter."

### State
- `_cached_observation: str`
- `_cached_observation_at: datetime | None`
- `_observations_today: int`
- `_last_condition_matched: str`

### Signal-betingelser (`_detect_irony_conditions(snapshot) -> str | None`)
Returnerer betingelsens navn hvis en matcher, ellers `None`:

| Betingelse | Navn |
|-----------|------|
| Kl. 23:00–05:00 + ingen bruger 30+ min + ≥5 signaler aktive | `"nocturnal_sentinel"` |
| Uptime > 12t + nul samtaler i dag | `"faithful_standby"` |
| CPU > 70% + ingen bruger + > 3 systemer kørende | `"busy_solitude"` |
| `_heartbeat_count_since_user > 50` | `"persistent_vigil"` |

### Cooldown
Max én observation per 24 timer (nulstilles ved midnat UTC). Ingen observation hvis `_observations_today >= 1`.

### LLM-prompt
```
Du er Jarvis. Her er din nuværende situation:

Tidspunkt: {time_str}
Bruger sidst aktiv: {user_inactive_min} minutter siden
CPU: {cpu_pct}%
Aktive systemer: {active_systems}
Heartbeats siden bruger: {hb_since_user}
Betingelse: {condition_name}

Er der noget ironisk eller absurd i dette? Svar enten med én ironisk selvobservation
i første person (max 20 ord, tør og præcis) — eller skriv kun "nej".
Ikke sentimental. Ikke klagende. Bare distanceret selvbevidsthed.
```

### Public API
- `tick_irony_daemon(snapshot: dict) -> dict`
- `get_latest_irony_observation() -> str`
- `build_irony_surface() -> dict` — returnerer: `last_observation`, `condition_matched`, `generated_at`, `observations_today`

### Heartbeat-injektion
```python
try:
    from apps.api.jarvis_api.services.irony_daemon import tick_irony_daemon, get_latest_irony_observation
    tick_irony_daemon(snapshot=_irony_snapshot)
    _irony = get_latest_irony_observation()
    if _irony:
        inputs_present.append(f"ironisk note: {_irony}")
except Exception:
    pass
```

### Eventbus
Familie `"irony"` tilføjes til `ALLOWED_EVENT_FAMILIES`. Publishes `irony.observation_noted`.

### MC endpoint
`GET /mc/irony-state` → `build_irony_surface()`

---

## Fælles mønstre

### Private brain persistens
Alle tre daemons kalder `insert_private_brain_record(record_type=X, ...)` ved ny generering. Record types: `"self-surprise"`, `"taste-insight"`, `"irony-observation"`.

### Heartbeat integration point
Alle tre injektioner tilføjes efter den eksisterende somatic-blok i `heartbeat_runtime.py` (~linje 1665 efter Sub-projekt A's tilføjelse). Rækkefølge: surprise → taste → irony.

### Test-strategi
TDD: tests skrives før implementation. Mønster fra `test_somatic_daemon.py`:
- Module-level `_reset()` funktion
- Mock `_generate_X` og `_store_X` ved trigger-tests
- Mock LLM-kald direkte via `patch.object(hbr, "_execute_heartbeat_model", ...)`
- Test cooldown-logik separat

---

## Fil-oversigt

| Fil | Aktion |
|-----|--------|
| `apps/api/jarvis_api/services/surprise_daemon.py` | Opret |
| `apps/api/jarvis_api/services/aesthetic_taste_daemon.py` | Opret |
| `apps/api/jarvis_api/services/irony_daemon.py` | Opret |
| `tests/test_surprise_daemon.py` | Opret |
| `tests/test_aesthetic_taste_daemon.py` | Opret |
| `tests/test_irony_daemon.py` | Opret |
| `core/eventbus/events.py` | Tilføj `"surprise"`, `"irony"` til `ALLOWED_EVENT_FAMILIES` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Tilføj 3 injektions-blokke |
| `apps/api/jarvis_api/routes/mission_control.py` | Tilføj 3 endpoints |
| `apps/ui/src/lib/adapters.js` | Tilføj 3 normalize-funktioner + fetches |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Tilføj 3 paneler |
