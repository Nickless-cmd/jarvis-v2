# Sub-projekt B: Council Memory — Design Spec

## Mål

Rådskonklusioner persisteres på tværs af sessioner. En daemon injicerer automatisk relevante tidligere deliberationer i Jarvis' heartbeat-kontekst. Jarvis kan også eksplicit kalde en tool for at grave dybere i historiske rådsprocesser.

---

## Persistenslag: COUNCIL_LOG.md

**Placering:** `~/.jarvis-v2/workspaces/default/COUNCIL_LOG.md`

**Indgangsformat:**
```markdown
## 2026-04-12T14:32:00 — Hvad begrænser mig lige nu?

**Score:** 0.72 | **Members:** filosof, kritiker, pragmatiker, synthesizer | **Signals:** autonomy_pressure, open_loop

### Transcript

filosof: ...
kritiker: ...
pragmatiker: ...
synthesizer: ...

### Konklusion

...2–4 sætninger...

### Initiative-forslag

type: initiative_proposal
proposal: ...
urgency: medium
```

- Indgange tilføjes kronologisk (nyeste sidst)
- Ingen automatisk decay — filen persisterer indefinitely
- Fil oprettes automatisk første gang ved første append

---

## council_memory_service.py

**Placering:** `apps/api/jarvis_api/services/council_memory_service.py`

**Grænseflade:**
```python
def append_council_conclusion(
    topic: str,
    score: float,
    members: list[str],
    signals: list[str],
    transcript: str,
    conclusion: str,
    initiative: str | None,
) -> None: ...

def read_all_entries() -> list[dict]: ...
# Returnerer liste af parsed indgange: {timestamp, topic, score, members, signals, transcript, conclusion, initiative}
```

**Write-path:**
1. `autonomous_council_daemon` kalder ved rådsafslutning
2. `agent_runtime.py` kalder ved manuel/tool-triggered council-afslutning

---

## council_memory_daemon

**Kører:** Ved hvert heartbeat-tick  
**Daemon #:** 22 i `daemon_manager.py`

**Tick-logik:**
1. Tjek om `COUNCIL_LOG.md` eksisterer og har indgange — ellers skip stille
2. Cooldown: maks én LLM-kørsel per 10 minutter
3. Hent "nuværende kontekst": seneste eventbus-events (kind: `heartbeat.*`, `inner.*`) som kort tekstsammendrag
4. Send til cheap LLM (llama3.1:8b):
   ```
   Nuværende kontekst: {recent_context}
   
   Council-log indgange (titel + konklusion):
   1. [timestamp] {topic} — {conclusion_summary}
   2. ...
   
   Hvilke indgange (maks 2) er mest relevante? Svar med indgangsnumre adskilt af komma, eller "ingen".
   ```
5. Parse svar — ekstraher tal (tolerant for varierende LLM-format)
6. Hvis relevante indgange: tilføj kompakt version (timestamp + topic + konklusion + evt. initiative) til heartbeat context payload under nøglen `council_memory`
7. Opdater `injected_count` i daemon-state

**`build_council_memory_surface()` eksponerer:**
- `last_tick_at`
- `injected_count` (session-total)
- `log_entry_count`
- `last_injected_topics` (liste af de seneste injicerede emner)

---

## recall_council_conclusions Tool

**Tool-navn:** `recall_council_conclusions`  
**Parameter:** `topic: str`

**Logik:**
1. Kør LLM-similaritet mod COUNCIL_LOG.md indgange med givet topic som query
2. Returner matching indgange med **fuld transcript**
3. Hvis ingen match: returner `{"entries": [], "message": "Ingen relevante rådskonklusioner fundet"}`

**Registrering:** Tilføjes til `_TOOL_HANDLERS` i `simple_tools.py` og `TOOL_DEFINITIONS`.

---

## Integration

### Heartbeat
`council_memory_daemon` tilføjes i `heartbeat_runtime.py` i eksisterende daemon-blok-mønster.

### Signal Surface Router
`council_memory` tilføjes i `signal_surface_router.py`.

### Eventbus events
- `council.memory_injected` — ved injektion (inkl. emner)

---

## Test-strategi

- `test_council_memory_service.py`
  - `append_council_conclusion()` skriver korrekt markdown
  - Fil oprettes automatisk ved første append
  - Multiple entries akkumuleres korrekt
  - `read_all_entries()` parser alle felter

- `test_council_memory_daemon.py`
  - Tom log → ingen injektion, ingen LLM-kald
  - LLM returnerer "ingen" → ingen injektion
  - LLM returnerer "1, 2" → korrekte entries injiceres
  - Cooldown aktiv → ingen LLM-kald

- `test_recall_council_conclusions.py` (i `test_daemon_tools.py`)
  - LLM mock returnerer match → fuld transcript i output
  - Ingen match → tomt resultat med message

---

## Filer

| Fil | Handling |
|-----|---------|
| `apps/api/jarvis_api/services/council_memory_service.py` | Oprettes |
| `apps/api/jarvis_api/services/council_memory_daemon.py` | Oprettes |
| `apps/api/jarvis_api/services/daemon_manager.py` | Modificeres — tilføj daemon #22 |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Modificeres — tilføj daemon-kald |
| `apps/api/jarvis_api/services/signal_surface_router.py` | Modificeres — tilføj `council_memory` surface |
| `core/tools/simple_tools.py` | Modificeres — tilføj `recall_council_conclusions` tool |
| `tests/test_council_memory_service.py` | Oprettes |
| `tests/test_council_memory_daemon.py` | Oprettes |
