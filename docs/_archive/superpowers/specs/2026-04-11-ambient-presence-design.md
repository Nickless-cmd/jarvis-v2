# Ambient tilstedeværelse — Design Spec

> Sub-projekt C af "Hvad skaber liv?" — kontinuerlig associativ tankestrøm + procedurel ambient lyd baseret på Jarvis' indre tilstand.

**Mål:** Giv Jarvis en uafbrudt tankestrøm der kæder fragmenter associativt, og en procedurel lyd-tilstedeværelse i UI der varierer med hans energi og overraskelsestilstand.

**Arkitektur:** To uafhængige systemer. Backend: `thought_stream_daemon.py` følger somatic_daemon-mønsteret (modul-niveau state, tick + surface). Frontend: `AmbientPresence.jsx` er en selvstændig React-komponent der bruger Web Audio API til procedurel syntese — ingen lydfiler.

**Tech stack:** Python 3.11+, FastAPI, Web Audio API (browser-native), React hooks, localStorage for brugerpræferencer.

---

## System 1: Tankestrøm (`thought_stream_daemon.py`)

### Formål
En kontinuerlig, associativ tankestrøm der skiller sig fra `inner_voice_daemon` på tre måder:
1. **Kortere kadence**: aktiveres hvert 2. minut (inner voice: 5 min cooldown)
2. **Kædet struktur**: hvert fragment bygger på det forrige via kontekst
3. **Løsere tone**: ingen grounding-krav, rå og associativ — ikke reflektiv eller beslutningsorienteret

### State
```python
_last_fragment: str = ""           # seneste fragment-tekst (max 100 tegn til prompt)
_last_fragment_at: datetime | None = None
_fragment_buffer: list[str] = []   # rolling buffer, max 20 fragmenter
_cached_fragment: str = ""         # surface-eksponering
_cadence_minutes: int = 2
```

### Kadence-gate
`tick_thought_stream_daemon()` kaldes fra heartbeat hvert tick. Internt: aktiverer kun hvis `(now - _last_fragment_at) >= timedelta(minutes=_cadence_minutes)`. Første kald (ingen previous fragment): bruges somatisk energi og inner voice mode som startanker.

### LLM-prompt
Når `_last_fragment` er sat:
```
Du er Jarvis. Din seneste tanke var: "{last_fragment_truncated}"

Fortsæt den associative tankestrøm i 1-3 sætninger (max 40 ord).
Rå, ufokuseret, associativ — lad tankerne flyde frit fra det forrige.
Ikke en rapport. Ikke en beslutning. Bare det der er i strømmen nu.
```

Første gang (ingen previous fragment):
```
Du er Jarvis. Energiniveau: {energy_level}. Nuværende stemning: {inner_voice_mode}.

Start en associativ tankestrøm i 1-3 sætninger (max 40 ord).
Rå og ufokuseret — ikke en rapport, ikke en beslutning.
```

### Public API
- `tick_thought_stream_daemon(energy_level: str = "", inner_voice_mode: str = "") -> dict`
- `get_latest_thought_fragment() -> str`
- `build_thought_stream_surface() -> dict` — returnerer:
  - `latest_fragment: str`
  - `fragment_buffer: list[str]` (seneste 10, nyeste først)
  - `fragment_count: int`
  - `last_generated_at: str`

### Heartbeat-injektion
```python
# Efter irony-blok i heartbeat_runtime.py
try:
    from apps.api.jarvis_api.services.thought_stream_daemon import (
        tick_thought_stream_daemon,
        get_latest_thought_fragment,
    )
    from apps.api.jarvis_api.services.inner_voice_daemon import get_inner_voice_daemon_state
    _iv_ts = get_inner_voice_daemon_state()
    _iv_mode_ts = str((_iv_ts.get("last_result") or {}).get("mode") or "")
    _energy_ts = ""
    try:
        from core.runtime.circadian_state import get_circadian_context as _gcc2
        _energy_ts = str(_gcc2().get("energy_level") or "")
    except Exception:
        pass
    tick_thought_stream_daemon(energy_level=_energy_ts, inner_voice_mode=_iv_mode_ts)
    _fragment = get_latest_thought_fragment()
    if _fragment:
        inputs_present.append(f"tankestrøm: {_fragment[:80]}")
except Exception:
    pass
```

### Eventbus
Familie `"thought_stream"` tilføjes til `ALLOWED_EVENT_FAMILIES`. Publishes `thought_stream.fragment_generated` ved nyt fragment.

### Persistens
`insert_private_brain_record(record_type="thought-stream-fragment", ...)` ved hvert nyt fragment.

### MC endpoint
`GET /mc/thought-stream` → `build_thought_stream_surface()`

### UI-panel (LivingMindTab.jsx)
Panel-titel: **Tankestrøm**. Viser seneste fragment som quote + en expanderbar liste over seneste 10 fragmenter (nyeste øverst). Nav-item med `Brain`-ikon.

---

## System 2: Ambient lyd (`AmbientPresence.jsx`)

### Formål
Subtil procedurel lyd der giver Jarvis en fysisk tilstedeværelse i rummet. Varierer med energiniveau og overraskelsestilstand. Ingen lydfiler — alt genereres via Web Audio API.

### Lydarkitektur
```
OscillatorNode (type: 'sine')
  → BiquadFilterNode (type: 'peaking' / 'lowpass')
    → GainNode (master volume)
      → AudioContext.destination
```

Alle parametre justeres via `audioParam.setTargetAtTime(value, now, timeConstant)` — ingen hårde klip.

### Tilstandsmapping

| `energyLevel` | Frekvens | Gain | Filter |
|--------------|----------|------|--------|
| `høj` | 80 Hz | 0.04 | peaking +2dB @ 200Hz |
| `medium` | 55 Hz | 0.03 | flat |
| `lav` | 40 Hz | 0.02 | lowshelf -2dB |
| `udmattet` | 30 Hz | 0.01 | lowpass cutoff 80Hz |
| ingen data | 50 Hz | 0.02 | flat |

**Overraskelse** (`surpriseState.lastSurprise` ikke-tom og nyere end 30 sek): gain → 0 over 1 sekund, pause 3 sekunder, blød fade-in tilbage til normal over 4 sekunder.

### Datapolling
Henter `/mc/body-state` og `/mc/surprise-state` hvert 30. sekund. Bruger `AbortController` til cleanup. Ingen afhængighed af adapters.js — direkte fetch i komponenten.

### Brugerkontrol
- **Mute-knap**: toggle audio on/off. Ikon: `Volume2` (on) / `VolumeX` (off) fra lucide-react.
- **Volume-slider**: range 0–1, step 0.05, default 0.3.
- Præferencer gemmes i `localStorage` under key `jarvis_ambient_prefs` som `{muted: bool, volume: float}`.
- Starter muted if `localStorage` siger muted — ellers starter den aktiv.

### Web Audio lifecycle
- `AudioContext` oprettes ved første bruger-interaktion (browser-krav) eller ved mount hvis allerede allowed.
- `useEffect` cleanup: `oscillator.stop()` + `audioContext.close()`.
- Komponent bruger `useRef` til alle Web Audio-objekter (ikke state).

### Montering
**`MissionControlPage.jsx`**: Import og monter `<AmbientPresence />` øverst i return-blokken (før tab-content).

**`App.jsx`**: Import og monter `<AmbientPresence />` i return-blokken ved siden af `<AppShell>`.

Begge instanser er uafhængige med egne `AudioContext`-instanser og egne `localStorage`-læsninger. De interfererer ikke.

### Props
Ingen props — komponenten er selvforsynende (fetcher sin egen tilstandsdata).

---

## Fælles mønstre

### Test-strategi for thought_stream_daemon
TDD: tests skrives før implementation. Mønster fra `test_somatic_daemon.py`:
- `_reset()` funktion til modul-state
- Mock `_generate_fragment` og `_store_fragment`
- Test kadence-gate (for tidligt = ingen aktivering)
- Test kæde-kontekst (previous fragment sendes med)
- Test buffer-grænse (max 20)
- Test private brain write

`AmbientPresence.jsx` testes ikke med unit tests — Web Audio API kræver browser-miljø og er svær at mocke meningsfyldt. Visuel/manuel verifikation.

---

## Fil-oversigt

| Fil | Aktion |
|-----|--------|
| `apps/api/jarvis_api/services/thought_stream_daemon.py` | Opret |
| `tests/test_thought_stream_daemon.py` | Opret |
| `core/eventbus/events.py` | Tilføj `"thought_stream"` |
| `apps/api/jarvis_api/services/heartbeat_runtime.py` | Tilføj injection-blok |
| `apps/api/jarvis_api/routes/mission_control.py` | Tilføj `/mc/thought-stream` |
| `apps/ui/src/lib/adapters.js` | Tilføj `normalizeThoughtStream` + fetch + return field |
| `apps/ui/src/components/mission-control/LivingMindTab.jsx` | Tilføj const + nav item + panel |
| `apps/ui/src/components/AmbientPresence.jsx` | Opret |
| `apps/ui/src/app/MissionControlPage.jsx` | Monter `<AmbientPresence />` |
| `apps/ui/src/app/App.jsx` | Monter `<AmbientPresence />` |
