# Sub-projekt A: Autonomous Council Daemon — Design Spec

## Mål

Jarvis kan spontant indkalde sit eget råd uden brugerinitiativ. Et signal-scoring-system evaluerer løbende om en deliberation er berettiget. Rådet kører, synthesizer producerer konklusion, og konklusionen kan resultere i et initiative-forslag til Jarvis' queue.

---

## Signal Scoring

### Signalkilder og vægte

| Signal | Kilde | Vægt |
|--------|-------|------|
| Autonomy pressure | `autonomy_pressure` surface | 0.20 |
| Unresolved open loops | `open_loop` surface (`unresolved_count`) | 0.15 |
| Internal opposition | `internal_opposition` surface | 0.15 |
| Existential wonder | `existential_wonder` surface (`active`) | 0.10 |
| Creative drift | `creative_drift` surface (`active`) | 0.10 |
| Desire intensity | `desire` surface (`max_intensity`) | 0.10 |
| Conflict tension | `conflict` surface (`tension_level`) | 0.10 |
| Time since last council | beregnet fra `DAEMON_STATE.json` | 0.10 |

### Beregning

Hvert signal normaliseres 0–1 og ganges med sin vægt. Samlet score = sum(weight × normalized_value). Threshold for aktivering: **0.55**.

### Emneudledning

Jarvis' synthesizer-LLM modtager de top-2 signaler (højest normaliseret bidrag) og genererer et emne for deliberationen. Eksempel: `autonomy_pressure` + `open_loop` → "Hvad begrænser mig lige nu, og hvad kan jeg gøre ved det?"

---

## Cadence og Cooldown

- **Cadence**: Scoring evalueres ved hvert heartbeat-tick
- **Minimum interval**: 30 minutter mellem councils (cadence gate)
- **Cooldown**: 20 minutter efter afsluttet council — ingen ny scoring
- Begge gates tjekkes i `autonomous_council_daemon.tick()` før scoring køres

---

## Rådssammensætning

| Score | Sammensætning |
|-------|---------------|
| ≥ 0.80 | Fuldt råd — alle tilgængelige members |
| < 0.80 | 3–4 members valgt efter relevans til de triggerende signaler |

### Relevanslogik (ved < 0.80)

Mapping fra signal til council-member type:
- `autonomy_pressure` / `open_loop` → pragmatiker + strateg
- `internal_opposition` / `conflict` → advokat + kritiker
- `existential_wonder` / `creative_drift` → filosof + kreativ
- `desire` → motivator

Mindst 3 members altid. Synthesizer inkluderes altid.

---

## Output og Handling

### Konklusion
Synthesizer producerer altid en konklusion uanset om rådet er enigt. Format: 2–4 sætninger.

### Initiative-forslag (valgfrit)
Hvis rådet identificerer en konkret handling, genereres et initiative i strukturen:
```
{
  "type": "initiative_proposal",
  "source": "autonomous_council",
  "topic": "<emne>",
  "proposal": "<hvad Jarvis bør gøre>",
  "urgency": "low|medium|high"
}
```
Publisheres på eventbus: `council.initiative_proposal`.

### Reflection (altid)
Konklusion injiceres i Jarvis' næste heartbeat-kontekst som `autonomous_council_reflection`.

---

## Integration

### Heartbeat
`autonomous_council_daemon` tilføjes som daemon #21 i `daemon_manager.py` og kaldes i `heartbeat_runtime.py` i eksisterende daemon-blok-mønster.

### council_memory_service
`append_council_conclusion()` kaldes når rådet lukker (se Sub-projekt B spec).

### Eventbus events
- `council.autonomous_triggered` — ved aktivering (inkl. score + emne)
- `council.autonomous_concluded` — ved afslutning (inkl. konklusion)
- `council.initiative_proposal` — hvis initiative foreslås

---

## Test-strategi

- `test_autonomous_council_daemon.py`
  - Score under threshold → ingen aktivering
  - Score over threshold + cadence OK → rådet aktiveres
  - Cooldown aktiv → ingen aktivering selvom score høj
  - Score ≥ 0.80 → fuldt råd
  - Score 0.60 → 3–4 relevante members
  - Initiative-forslag publisheres korrekt på eventbus
  - LLM-kald mockes i alle tests

---

## Filer

| Fil | Handling |
|-----|---------|
| `apps/api/jarvis_api/services/autonomous_council_daemon.py` | Oprettes |
| `apps/api/jarvis_api/services/daemon_manager.py` | Modificeres — tilføj daemon #21 |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modificeres — tilføj daemon-kald |
| `tests/test_autonomous_council_daemon.py` | Oprettes |
