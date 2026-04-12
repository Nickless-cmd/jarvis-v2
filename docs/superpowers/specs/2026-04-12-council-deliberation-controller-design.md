# Sub-projekt C: Council Deliberation Controller — Design Spec

## Mål

Agents er aktive aktører inde i deliberationen. En witness-agent kan eskalere fra passiv observatør til aktiv deltager. Systemet rekrutterer dynamisk nye perspektiver hvis de mangler. Deadlock detekteres regelbaseret og håndteres gradueret. Gælder for både autonome og manuelle councils.

---

## Deadlock-detektion + Gradueret Respons

### Hvad er et deadlock?

Rådet kører i cirkler når agent-outputs i runde N er semantisk lig med runde N-2. Detekteres via cosine-similaritet på TF-IDF vektorer — ingen LLM, ingen API-kald.

```python
def _is_deadlocked(round_outputs: list[list[str]]) -> bool:
    if len(round_outputs) < 3:
        return False
    last = " ".join(round_outputs[-1])
    two_ago = " ".join(round_outputs[-3])
    return cosine_similarity(last, two_ago) > 0.82
```

### Gradueret respons

| Tilstand | Handling |
|----------|---------|
| Deadlock detekteret (1. gang) | Tilføj "djævelens advokat"-agent for én runde med eksplicit instruks: "Bryd konsensus, udfordr alle" |
| Deadlock stadig aktiv efter ny agent | Force-konkluder: synthesizer promptes med "Rådet er gået i stå. Konkluder på baggrund af hvad der foreligger." |

### Absolut loft

Maks **8 runder** uanset deadlock — herefter tvinges konklusion altid.

---

## Witness-Eskalering

Witness-agenten er altid med i alle councils som silent observer. Den observerer transcript men taler ikke — medmindre den vælger at eskalere.

**Prompt til witness:**
> "Du observerer denne deliberation. Hvis du ser noget afgørende der overses, kan du anmode om at tale ved at starte dit output med `[ESKALERER]`."

**Detektionslogik:**
```python
if witness_output.strip().startswith("[ESKALERER]"):
    active_members.append("witness")
    # Witness taler kun én gang som aktiv deltager
```

- Witness aktiveres maks én gang per council
- Efter aktivering observerer den igen

---

## Dynamisk Rekruttering

**Tidspunkt:** Efter runde 2 (nok transcript til meningsfuld analyse).

**LLM-kald (cheap lane):**
```
Transcript indtil videre: {transcript}
Emne: {topic}

Mangler deliberationen et væsentligt perspektiv?
Svar med ét rollernavn (f.eks. "etiker", "tekniker") eller "nej".
```

**Håndtering af svar:**
- `"nej"` → ingen rekruttering
- Rolle allerede aktiv → skip
- Ny rolle → rekruttér agent, tilføj ét turn i indeværende runde
- Maks én rekruttering per council

---

## DeliberationController

**Placering:** `apps/api/jarvis_api/services/council_deliberation_controller.py`

**Grænseflade:**
```python
@dataclass
class DeliberationResult:
    transcript: str
    conclusion: str
    rounds_run: int
    deadlock_occurred: bool
    witness_escalated: bool
    recruited: str | None  # rolle-navn eller None

class DeliberationController:
    def __init__(self, topic: str, members: list[str], max_rounds: int = 8): ...
    def run(self) -> DeliberationResult: ...
```

**Runde-loop internt:**
1. Kør alle aktive agents (inkl. witness passivt)
2. Tjek witness output for `[ESKALERER]`
3. Efter runde 2: kør rekrutteringsanalyse (én gang)
4. Tjek for deadlock (fra runde 3)
5. Hvis deadlock: tilføj djævelens advokat eller force-konkluder
6. Hvis runde == max_rounds: force-konkluder

---

## Integration

### council_runtime.py (manuel council)
Eksisterende `run_council()` delegerer til `DeliberationController.run()`.

### autonomous_council_daemon.py (Sub-projekt A)
Kalder `DeliberationController` direkte.

**Ingen duplikering** — al deliberationslogik lever i `DeliberationController`.

---

## Eventbus Events

| Event | Trigger |
|-------|---------|
| `council.witness_escalated` | Witness aktiveres som deltager |
| `council.agent_recruited` | Ny agent tiltrækkes (inkl. rolle) |
| `council.deadlock_detected` | Deadlock detekteret (inkl. runde-nummer) |
| `council.deadlock_resolved` | Djævelens advokat bryder dødvandet |
| `council.deadlock_forced_conclusion` | Force-konklusion efter vedvarende deadlock |

---

## Test-strategi

- `test_deliberation_controller.py`
  - Divergerende agent-outputs → ingen deadlock → kører normalt til konklusion
  - Ens outputs i runde 1 og 3 → deadlock detekteret → djævelens advokat tilføjes
  - Vedvarende deadlock → force-konklusion aktiveres
  - Witness output starter med `[ESKALERER]` → witness tilføjes som aktiv
  - LLM returnerer rollernavn → agent rekrutteres, turn tilføjes
  - LLM returnerer "nej" → ingen rekruttering
  - Runde 8 nås → force-konklusion uanset tilstand
  - Alle LLM-kald mockes

---

## Filer

| Fil | Handling |
|-----|---------|
| `apps/api/jarvis_api/services/council_deliberation_controller.py` | Oprettes |
| `apps/api/jarvis_api/services/council_runtime.py` | Modificeres — delegér til DeliberationController |
| `apps/api/jarvis_api/services/autonomous_council_daemon.py` | Modificeres — brug DeliberationController |
| `tests/test_deliberation_controller.py` | Oprettes |
