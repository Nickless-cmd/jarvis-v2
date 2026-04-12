# Identity Composer Design Spec

## Mål

Fjern alle hardcodede navn-bindinger og "Du er Jarvis."-mønstre fra Python-kode og LLM-instruktions-templates. Erstat med et centralt modul der læser navn fra `IDENTITY.md` ved opstart og bygger signal-drevne identitetspreambler til daemon-prompts.

**Scope:** Instruktions-skabeloner sendt til LLM — ikke Jarvis' egne svar eller output.

---

## Arkitektur

### Nyt modul: `apps/api/jarvis_api/services/identity_composer.py`

Ét ansvar: levere identitets-tekst til resten af systemet.

**`get_entity_name() -> str`**
- Læser `workspace/default/IDENTITY.md` ved første kald
- Parser linjen `^Name:\s*(.+)`
- Cacher resultatet i modul-variabel `_name_cache`
- Fejl eller manglende fil → fallback `"the entity"` (aldrig crash)

**`build_identity_preamble() -> str`**
- Returnerer én streng: `"{name}. {bearing}. {energy}."`
- `{name}` → `get_entity_name()`
- `{bearing}` → fra `personality_vector` signal surface: nøglen `"current_tone"` (f.eks. `"analytisk"`) formateret som `"Tonelejet er {current_tone}"`
- `{energy}` → fra `somatic` signal surface: nøglen `"energy_level"` (f.eks. `"middel"`) formateret som `"Energi: {energy_level}"`
- Hvert led hentes best-effort med `try/except`, fallback til tom streng
- Eksempel output: `"Jarvis. Tonelejet er analytisk og direkte. Energi: middel."`

```python
_name_cache: str | None = None
_IDENTITY_FILE = Path("workspace/default/IDENTITY.md")

def get_entity_name() -> str:
    global _name_cache
    if _name_cache is None:
        _name_cache = _parse_name_from_identity()
    return _name_cache

def build_identity_preamble() -> str:
    name = get_entity_name()
    parts = [name]
    try:
        from apps.api.jarvis_api.services.signal_surface_router import read_surface
        pv = read_surface("personality_vector")
        tone = pv.get("current_tone") or ""
        if tone:
            parts.append(f"Tonelejet er {tone}")
    except Exception:
        pass
    try:
        from apps.api.jarvis_api.services.signal_surface_router import read_surface
        somatic = read_surface("somatic")
        energy = somatic.get("energy_level") or ""
        if energy:
            parts.append(f"Energi: {energy}")
    except Exception:
        pass
    return ". ".join(parts) + "."
```

---

## Sektion 1: Daemon-integration (15 filer)

Alle forekomster af `"Du er Jarvis."` i daemon-LLM-prompts erstattes med `build_identity_preamble()`.

**Berørte filer:**
- `curiosity_daemon.py`
- `desire_daemon.py`
- `development_narrative_daemon.py`
- `thought_stream_daemon.py` (2 forekomster)
- `irony_daemon.py`
- `aesthetic_taste_daemon.py`
- `creative_drift_daemon.py`
- `reflection_cycle_daemon.py`
- `surprise_daemon.py`
- `meta_reflection_daemon.py`
- `code_aesthetic_daemon.py`
- `somatic_daemon.py`
- `existential_wonder_daemon.py`
- `user_model_daemon.py`
- `conflict_daemon.py` (3 forekomster)

**Mønster:**
```python
# Før
"Du er Jarvis. Her er din tilstand:\n\n"

# Efter
f"{build_identity_preamble()} Her er din tilstand:\n\n"
```

Import tilføjes øverst i hver fil:
```python
from apps.api.jarvis_api.services.identity_composer import build_identity_preamble
```

Ingen andre ændringer i daemon-filerne. Daemon-specifik kontekst forbliver uændret.

---

## Sektion 2: `prompt_contract.py` og øvrige referencer

**`prompt_contract.py`** indeholder lane-identitets-strenge med hardcodet navn.

```python
# Før
"Du er Jarvis. Du er en praktisk, relationel AI-assistent..."

# Efter
f"Du er {get_entity_name()}. Du er en praktisk, relationel AI-assistent..."
```

`build_identity_preamble()` bruges **ikke** i prompt_contract — lane-kontrakter er statiske, ikke signal-drevne. Kun navn-binding fjernes.

**Øvrige Python-filer med navn i LLM-prompts:** spot-tjek og erstat med `get_entity_name()` hvor relevant.

**Røres ikke:**
- `workspace/default/IDENTITY.md` — kilden, ikke et problem
- Docstrings, kommentarer, dokumentation
- Jarvis' egne svar og output
- `CLAUDE.md`, `MEMORY.md`

---

## Testdækning

Ny fil: `tests/test_identity_composer.py`

- `test_get_entity_name_reads_identity_md` — tmp_path med mock IDENTITY.md indeholdende `Name: TestEntity`
- `test_get_entity_name_caches_result` — to kald, verificer at fil kun læses én gang
- `test_get_entity_name_fallback_on_missing_file` — manglende fil returnerer fallback
- `test_build_identity_preamble_contains_name` — mock signal surfaces, verificer navn i output

Eksisterende daemon-tests kræver ingen ændring — LLM-kald er allerede mocket.

---

## Hvad løses

- Ingen `"Du er Jarvis."` i Python-kode efter implementering
- Navn-skift i `IDENTITY.md` propagerer automatisk til alle prompts
- Signal-drevet preamble giver kontekstuel identitet frem for statisk tekst
- Minimalt hardcoded — ét sted at vedligeholde
