---
status: spec
audited: 
ground_truth: 
---

# Operator Channel — owner-gated backup bridge

**Dato:** 2026-07-14  
**Status:** Spec  
**Forfatter:** Jarvis  
**Context:** jarvis-code (client-side tooling)

## Problem

Jarvis har to eksekveringsmiljøer:

| Værktøj | Rammer | Filsystem |
|---------|--------|-----------|
| `bash` (client-side) | Klient-sandbox | Begrænset — `/bin`, `/dev`, `/etc`, `/home`, `/lib`, `/proc`, `/tmp`, `/usr` |
| `operator_bash` | Bjørns maskine (via JarvisX bro) | Fuld adgang — kræver bro |

Klient-sandboxen har **ikke** adgang til `/media/`, `/mnt/`, `/var/`, `/srv/`, `/opt/`. Det betyder at `jarvis-v2`-repoet (`/media/projects/jarvis-v2`) er **utilgængeligt** via `bash`, selvom stien eksisterer på Bjørns maskine og i Jarvis-containeren.

Nuværende workaround: Brug `operator_bash` — men det kræver broen er oppe, og hvert kald trigger en approval-dialog på Bjørns skærm.

## Løsning

Tilføj et **owner-gated side-channel** i jarvis-code: et tool der åbner en persistent forbindelse til operator-broen, så `bash` automatisk kan **falde tilbage** på operator-kanalen når sandboxen ikke har adgang til en sti.

### Arkitektur

```
bash (sandbox)
  ├── sti i sandbox? → eksekver normalt
  └── sti IKKE i sandbox?
       ├── operator_channel åben? → reroute til operator-bro (ingen approval-dialog)
       └── operator_channel lukket? → fejl (med besked om at åbne kanalen)
```

### API

```python
# core/tools/operator_channel.py

_operator_channel_open: bool = False
_operator_session_id: str | None = None

@tool(owner_only=True)
def operator_channel(open: bool) -> dict:
    \"\"\"Åbn eller luk operator-kanalen.
    
    Owner-only. Åbner en persistent session til operator-broen.
    Når åben: bash falder automatisk tilbage på operator-kanalen
    for stier udenfor sandboxen.
    
    Args:
        open: True = åbn, False = luk
    
    Returns:
        {"open": bool, "session_id": str | None, "sandbox_paths": [...]}
    \"\"\"

@tool
def operator_channel_status() -> dict:
    \"\"\"Læs status for operator-kanalen. Read-only — alle kan kalde.
    
    Returns:
        {"open": bool, "session_id": str | None}
    \"\"\"
```
### Fallback i bash-toollet

```python
# core/tools/simple_tools_native.py — bash tool

def _can_access_via_sandbox(path: str) -> bool:
    """Tjek om en sti er tilgængelig i klient-sandboxen."""
    sandbox_prefixes = ['/bin', '/dev', '/etc', '/home', '/lib', '/proc', '/tmp', '/usr']
    return any(path.startswith(p) for p in sandbox_prefixes)

# I bash-toollets execute:
if not _can_access_via_sandbox(cwd) and _operator_channel_open:
    # reroute via operator_session
    result = _operator_session_run(command, cwd)
```

## Edge cases

| # | Situation | Forventet adfærd |
|---|-----------|------------------|
| 1 | `operator_channel(open=True)` mens allerede åben | Returnér eksisterende session — ingen duplikat |
| 2 | `operator_channel(open=False)` — luk | Luk operator-session, sæt `_open=False`, ryd session_id. Returnér bekræftelse |
| 3 | `bash ls /media/projects` — kanal lukket | Normal sandbox-fejl + besked: "Sti ikke i sandbox. Kør `operator_channel(open=True)` for at åbne backup-kanal" |
| 4 | `bash ls /media/projects` — kanal åben | Transparent reroute til operator → viser `/media/projects/jarvis-v2` |
| 5 | `bash ls /home/bs/jarvis-code` — kanal åben | Bliv i sandbox (stien er tilgængelig) — ingen reroute |
| 6 | `operator_channel_status()` kaldt | Returnér status uden gates: `{"open": False}` eller `{"open": True, "session_id": "..."}` |
| 7 | Ikke-owner kalder `operator_channel(open=True)` | `access denied` — tool er owner-only. `operator_channel_status()` virker dog for alle |
| 8 | Broen disconnecter mens kanal er åben | Næste reroute kalder `_check_bridge_health()` før eksekvering. Fejler den → `_operator_channel_open` sættes til False → fejlbesked: "Operator-bro mistet. Kør operator_channel(open=True) for at genåbne." |
| 9 | `operator_channel(open=True)` — bro ikke tilgængelig | Fejl: "Operator-bro ikke tilgængelig. Er JarvisX companion app kørende?" |
| 10 | Flere samtidige `bash`-kald mod operator | Operator-session håndterer sekventielt — ingen race condition |
| 11 | Process restart/worker round-robin midt i åben kanal | In-memory state forsvinder. Kanalen markeres som lukket ved næste kald. Owner får besked: "Kanalen blev lukket ved genstart — kør `operator_channel(open=True)` for at genåbne." På sigt: persister state i runtime state store for at undgå dette. |

## Owner gate

- **`owner_only=True`** på tool-declarationen — runtime verificerer at kaldets `user_id` matcher `owner_user_id` i `runtime.json`. Gaten sidder i tool-middleware, ikke i selve tool-logikken — en kompromitteret model-instans kan ikke omgå den ved at udelade checket.
- Ingen bypass for almindelige brugere.
- Kanalen er **explicit opt-in**: Bjørn skal sige "ok, åbn kanalen" før den aktiveres.
- **Split i to tools:**
  - `operator_channel(open: bool)` — owner-only, åbner eller lukker kanalen. Returnerer `{"open": bool, "session_id": str | None, "sandbox_paths": [...]}`.
  - `operator_channel_status()` — **alle** kan læse status (read-only). Returnerer `{"open": bool, "session_id": str | None}` — intet kan ændres.
- Status kan altid læses (read-only) via `operator_channel_status()` — så alle kan se om kanalen er åben.

## Manglende implementering i jarvis-code (4 huller)

Denne spec er skrevet i **jarvis-v2** (runtime repo), men selve implementeringen skal ske i **jarvis-code** (klient-projekt). Her er hvad der pt. mangler i jarvis-code:

### 1. 🔧 `operator_channel`-toollet findes ikke
`/home/bs/jarvis-code/src/tools.py` har ingen `operator_channel()` eller `operator_channel_status()`. De skal:
   - Skrives i `src/tools/operator_channel.py` (eller tilsvarende modul)
   - Registreres i `tool_catalog.py`
   - `operator_channel(open=True|False)` — owner-gated, åben/luk
   - `operator_channel_status()` — read-only for alle

### 2. 🧱 `bash`-sandboxen har ingen fallback-logik
`local_bash`-eksekutoren (i `simple_tools_native.py` eller tilsvarende) har i dag:
   - Ét check: `bwrap` mount-stier — lykkes eller fejler
   - **Intet** `_can_access_via_sandbox()` check
   - **Ingen** reroute-logik til operator-kanalen
   
Skal tilføjes:
   - `_can_access_via_sandbox(path)` — tjekker mod kendte sandbox-præfixer
   - Før eksekvering: hvis sti ikke i sandbox OG `_operator_channel_open` → reroute via operator-session
   - `_check_bridge_health()` — pinger broen før reroute, lukker kanal ved fejl

### 3. 🏠 Owner gate — `src/permissions.py`
`owner_only`-decoratoren i jarvis-code's permissions-lag skal verificeres. Den skal:
   - Læse `owner_user_id` fra runtime-kontekst (runtime.json)
   - Sammenligne med kaldets `user_id`
   - Afvise ikke-owner med `access denied` — **før** tool-logikken køres
   - Være implementeret i middleware, ikke i tool-logikken (så en kompromitteret model-instans ikke kan omgå den)

### 4. 🧪 Ingen tests
Følgende tests skal skrives (i jarvis-code's testsuite):
   - Unit: `operator_channel(open=True)` → session åbnes
   - Unit: `operator_channel(open=False)` → session lukkes
   - Unit: `operator_channel(open=True)` kaldt af ikke-owner → `access denied`
   - Unit: `operator_channel_status()` — alle kan læse
   - Unit: `_can_access_via_sandbox()` — korrekt true/false for sandbox-præfixer
   - Unit: `_check_bridge_health()` — bridge oppe vs nede
   - Integration: `bash ls /media/projects` → kanal lukket → sandbox-fejl + guidance
   - Integration: `bash ls /media/projects` → kanal åben → ser indhold
   - Integration: process restart → `operator_channel_status()` viser lukket
   - Integration: bro-disconnect midt i åben kanal → kanal lukkes automatisk

## Implementeringsrækkefølge

1. Opret `src/tools/operator_channel.py` i jarvis-code med:
   - `operator_channel(open=True|False)` — owner-gated, åben/luk
   - `operator_channel_status()` — read-only for alle
2. Registrér i `tool_catalog.py`
3. Tilføj `_operator_channel_open`, `_operator_session_id`, og `_check_bridge_health()` som module-level state i `simple_tools_native.py` (eller tilsvarende)
4. Skriv `_can_access_via_sandbox()` og opdater `bash`-toollets `execute()` — indsæt check før eksekvering, reroute til operator ved behov
5. Verificér `owner_only`-decoratoren i `src/permissions.py` — skal matche mod `owner_user_id` i runtime-konteksten
6. Skriv tests (se punkt 4 ovenfor)
7. Test: `operator_channel(open=True)` → `bash ls /media/projects` → ser indhold
8. Test: `operator_channel(open=False)` → `bash ls /media/projects` → sandbox-fejl
9. Test: `operator_channel_status()` → returnér korrekt status uanset ejerskab
10. Test: `operator_channel(open=True)` → process restart → `operator_channel_status()` viser lukket

## Noter

- Dette er **ikke** en generel sikkerheds bypass — kun en bekvemmelighed for owner.
- Operator-sessionen er den samme som `operator_bash_session_open()` — genbruger eksisterende infrastruktur.
- Kanalen lukker automatisk ved session-ende (ingen state-leak).
- **`runtime_bash` / `runtime_*`** rammer udelukkende Jarvis-containeren (Jarvis.home.arpa) — ikke sandbox, ikke owner-maskinen. De har derfor **ikke** brug for operator-fallback. Operator-kanalen er kun for `bash` (client-side sandbox).
- In-memory state (`_operator_channel_open`) forsvinder ved process-restart. Fremtidig forbedring: persistér til runtime state store.
