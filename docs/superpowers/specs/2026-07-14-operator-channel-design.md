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

Jarvis har **tre eksekveringsmiljøer**:

| Værktøj | Rammer | Filsystem |
|---------|--------|-----------|
| `bash` (client-side) | Klient-sandbox (bwrap) | Begrænset — `/bin`, `/dev`, `/etc`, `/home`, `/lib`, `/proc`, `/tmp`, `/usr` |
| `runtime_bash` | Jarvis-container (Jarvis.home.arpa) | Fuld — `/media/projects/jarvis-v2` |
| `operator_bash` | Bjørns maskine (via JarvisX bridge) | Fuld — **kræver bro** + approval-dialog |

Klient-sandboxen har **ikke** adgang til `/media/`, `/mnt/`, `/srv/`, `/var/`, `/opt/`. Det betyder at `jarvis-v2`-repoet er **utilgængeligt** via `bash`, selvom stien findes på Bjørns fysiske maskine.

Nuværende workaround: `operator_bash` — men hvert kald trigger en approval-dialog på Bjørns skærm.

## Arkitektur (fundet i kodebasen)

### jarvis-code (klient) → server (container) → bridge (din maskine)

```
Brugermaskine (CheifOne)
  │
  ├── jarvis-code (bwrap-sandbox)
  │   ├── tools.py::TOOL_EXECUTORS     ← bash, read_file, write_file, …
  │   └── tools.py::route_tool_call()  ← forwarder ALT ANDET til serveren
  │
  ├── jarvis-desk-app (Electron)
  │   └── bridge.ts — WebSocket → api.srvlab.dk:8080/ws
  │       Registrerer sig med JWT + user_id
  │       Modtager `tool_invoke` beskeder, eksekverer lokalt, returnerer
  │
  └── api.srvlab.dk (container Jarvis.home.arpa)
      ├── POST /v1/tools/execute       ← modtager forwarded tool-kald
      ├── core/tools/operator_tools.py ← async wrappers om bridge_registry.dispatch()
      ├── core/services/jarvisx_bridge.py ← WebSocket registry, correlation_id
      └── bridge_presence.py           ← tjekker om broen er live
```

**Nøgleindsigter:**

1. **`bash` (client-side)** kører i bwrap-sandbox med mount: `/usr`, `/bin`, `/lib`, `/lib64`, `/etc` (read-only), `cwd` (read-write), `/tmp` (tmpfs), `/dev`/`/proc`. Kilde: `jc_sandbox.py::wrap_bwrap()` linje 130-155.
2. **`route_tool_call()` i `tools.py`** (linje 1187-1218): hvis tool-navnet IKKE er i `TOOL_EXECUTORS` → POST til `api.srvlab.dk/v1/tools/execute` → serveren dispatcher til `operator_tools.py` → `bridge_registry.dispatch()` → WebSocket til desk-appen. Det er sådan `operator_*`-tools virker.
3. **Hvert `operator_bash`-kald kræver approval-dialog** på Bjørns skærm — bridge.ts sender en `tool_invoke` med `approval_required=True`. Det er **derfor** workaround'en er upraktisk.
4. **`jc_agent_loop.py::execute_one_tool()`** (linje 507-561) dispatcher: hvis i `TOOL_EXECUTORS` → `execute_tool()` (lokalt), ellers → `route_tool_call()` (forwardet til server → bro).
5. **Ingen `operator_channel`** eksisterer i koden — kun spec'en.
6. **Ingen `operator_channel_status()`** — skal skrives.
7. **Ingen `_can_access_via_sandbox()`** check — `local_bash()` i tools.py har ingen fallback-logik for stier udenfor bwrap-mounts.

## Løsning

Tilføj et **owner-gated side-channel** i jarvis-code: et tool der åbner en persistent session til operator-broen, så `bash` automatisk falder tilbage på operator-kanalen når sandboxen ikke har adgang til en sti — **uden approval-dialog på hvert reroute**.

### API

```python
# src/tools/operator_channel.py

_operator_channel_open: bool = False
_operator_session_id: str | None = None

@tool(owner_only=True)
def operator_channel(open: bool) -> dict:
    """Åbn eller luk operator-kanalen.
    
    Owner-only. Åbner en persistent session til operator-broen.
    Når åben: bash falder automatisk tilbage på operator-kanalen
    for stier udenfor sandboxen.
    
    Args:
        open: True = åbn, False = luk
    
    Returns:
        {"open": bool, "session_id": str | None, "sandbox_paths": [...]}
    """

@tool
def operator_channel_status() -> dict:
    """Læs status for operator-kanalen. Read-only — alle kan kalde.
    
    Returns:
        {"open": bool, "session_id": str | None}
    """
```

### Fallback i bash-toollet

```python
# src/tools.py / simple_tools_native.py

def _can_access_via_sandbox(path: str) -> bool:
    """Tjek om en sti er tilgængelig i klient-sandboxen.
    
    Matcher bwrap-mounts fra jc_sandbox.wrap_bwrap():
    - Read-only: /usr, /bin, /lib, /lib64, /etc
    - Read-write: cwd (resolved at runtime)
    - Special: /tmp (tmpfs), /dev, /proc
    
    Kilde: jc_sandbox.py linje 130-155
    """
    sandbox_prefixes = ['/usr', '/bin', '/lib', '/lib64', '/etc',
                        '/dev', '/proc', '/tmp']
    if any(path.startswith(p) for p in sandbox_prefixes):
        return True
    # cwd er dynamisk — sættes per session
    return False

# I local_bash():
if not _can_access_via_sandbox(resolved_cwd) and _operator_channel_open:
    # Reroute til operator via en DEDIKERET session (ingen approval-dialog)
    # Metode: POST /v1/tools/execute med tool="operator_session_run"
    # Server-side: operator_session_run tool der dispatcher via bridge
    # uden approval flag (owner-only endpoint)
    result = _operator_session_run(command, cwd)
```

### Owner gate

- **`owner_only=True`** på tool-declarationen — runtime verificerer at kaldets `user_id` matcher `owner_user_id` i `runtime.json`. Gaten sidder i **tool-middleware**, ikke i tool-logikken — en kompromitteret model-instans kan ikke omgå den.
- **Split:** `operator_channel(open=True|False)` — owner-gated. `operator_channel_status()` — read-only for alle.
- Kanalen er **explicit opt-in**: Bjørn skal sige "ok, åbn kanalen" før den aktiveres.

### Fallbackmekanisme — approval

Problemet: `operator_bash` kræver approval-dialog. For at undgå dialog på hvert reroute:

1. **Operator-session tool (server-side)**: Tilføj et nyt server-side tool `operator_session_run` i `core/tools/operator_tools.py` som dispatcher via bridge `uden` approval flag. Owner-gated (samme middleware).
2. **Klient-kald**: `operator_channel(open=True)` kalder `operator_session_open` på serveren (via POST /v1/tools/execute) — åbner en persistent operator-session. Efterfølgende reroute-kald bruger sessionen direkte.
3. **Alternativ (lettere)**: Brug `operator_bash_session_run` med `skip_approval=True` — hvis det flag findes i bridge-protokollen.

**Skal verificeres:** Har `bridge.ts` / `bridge_registry.dispatch()` et `skip_approval`-flag? Eller skal der bygges en dedikeret route?

## Fuld arkitektur (klient → server → bro)

```
jarvis-code:
  bash ls /media/projects
  → _can_access_via_sandbox("/media/projects") → False
  → _operator_channel_open → True
  → _operator_session_run("ls /media/projects")
  → POST /v1/tools/execute (tool="operator_session_run", session_id=...)
  
Container (api.srvlab.dk):
  → operator_session_run tool
  → bridge_registry.dispatch(user_id=..., tool="bash", 
                              args={"command": "ls /media/projects"},
                              skip_approval=True)
  → WebSocket → bridge.ts på CheifOne
  
Bridge (CheifOne / Electron):
  → Eksekverer "ls /media/projects" lokalt
  → Returnerer resultat via WebSocket
  
Container:
  → Forwarder resultat til klienten
  
Klient:
  → Viser resultat
```

## Edge cases

| # | Situation | Forventet adfærd |
|---|-----------|------------------|
| 1 | `operator_channel(open=True)` mens allerede åben | Returnér eksisterende session — ingen duplikat |
| 2 | `operator_channel(open=False)` — luk | Luk operator-session, sæt `_open=False`, ryd session_id. Returnér bekræftelse |
| 3 | `bash ls /media/projects` — kanal lukket | Normal sandbox-fejl + besked: "Sti ikke i sandbox. Kør `operator_channel(open=True)` for at åbne backup-kanal" |
| 4 | `bash ls /media/projects` — kanal åben | Transparent reroute → viser `/media/projects/jarvis-v2` |
| 5 | `bash ls /home/bs/jarvis-code` — kanal åben | Bliv i sandbox (stien er tilgængelig) — ingen reroute |
| 6 | `operator_channel_status()` kaldt | Returnér status uden gates |
| 7 | Ikke-owner kalder `operator_channel(open=True)` | `access denied` — tool er owner-only |
| 8 | Broen disconnecter mens kanal er åben | Næste reroute pinger broen → fejl → `_operator_channel_open` sættes til False → guidance |
| 9 | `operator_channel(open=True)` — bro ikke tilgængelig | Fejl: "Operator-bro ikke tilgængelig. Er JarvisX companion app kørende?" |
| 10 | Flere samtidige `bash`-kald mod operator | Operator-session håndterer sekventielt |
| 11 | Process restart / worker round-robin | In-memory state forsvinder. Kanalen markeres lukket. Owner får besked. |
| 12 | `operator_session_run` mangler på serveren | Fejl: "operator_session_run ikke tilgængelig — kræver opdatering af jarvis-v2" |
| 13 | Bridge `skip_approval` flag findes ikke | Alternativ: byg dedikeret route i bridge.ts. Spec opdateres. |

## Implementeringsrækkefølge

### Fase 1 — jarvis-code (klient)

1. **Opret `src/tools/operator_channel.py`** med `operator_channel(open=True|False)` (owner-gated) + `operator_channel_status()` (alle)
2. **Registrér i `tool_catalog.py`** — begge tools
3. **Tilføj `_operator_channel_open` state** — module-level variabel i `tools.py` (eller `operator_channel.py`)
4. **Skriv `_can_access_via_sandbox(path)`** — matcher bwrap-mounts fra `jc_sandbox.wrap_bwrap()`
5. **Opdatér `local_bash()`** — indsæt check før subprocess.run:
   - Hvis sti udenfor sandbox OG kanal åben → reroute
   - Hvis sti udenfor sandbox OG kanal lukket → guidance-fejl
6. **Verificér `owner_only`-decoratoren** — skal matche mod `owner_user_id`
7. **Skriv tests** — se "Tests" nedenfor

### Fase 2 — server/container (jarvis-v2)

8. **Tilføj `operator_session_open()`** tool i `core/tools/operator_tools.py` — owner-gated, åbner bridge-session
9. **Tilføj `operator_session_run()`** tool — dispatcher via bridge uden approval-flag (owner-only)
10. **Verificér bridge-protokollen** — har `dispatch()` et `skip_approval`-flag?

### Fase 3 — bridge (JarvisX Electron-app)

11. **Hvis nødvendigt:** tilføj `skip_approval`-route i bridge.ts
12. **Hvis nødvendigt:** tilføj `operator_session_open/run` handlers

## Tests

### Unit tests (jarvis-code)

- `operator_channel(open=True)` → session åbnes, `_operator_channel_open` = True
- `operator_channel(open=False)` → session lukkes, `_operator_channel_open` = False
- `operator_channel(open=True)` af ikke-owner → `access denied`
- `operator_channel_status()` — alle kan læse, inkl. ikke-owner
- `_can_access_via_sandbox("/usr/bin/ls")` → True
- `_can_access_via_sandbox("/media/projects")` → False
- `_can_access_via_sandbox("/home/bs/jarvis-code")` → True (er cwd)
- `_operator_session_run()` — korrekt POST til serveren

### Integration tests (jarvis-code)

- `bash ls /media/projects` → kanal lukket → sandbox-fejl + guidance
- `bash ls /media/projects` → kanal åben → ser indhold
- Process restart → `operator_channel_status()` viser lukket
- Bro-disconnect midt i åben kanal → kanal lukkes automatisk

### Server-side tests (jarvis-v2)

- `operator_session_run()` → dispatcher via bridge uden approval
- Owner gate — kun `owner_user_id` kan kalde
- Ikke-owner → `403 forbidden`
- Bridge ikke tilgængelig → fejlbesked, ikke crash

## Noter

- Dette er **ikke** en generel sikkerheds bypass — kun en bekvemmelighed for owner.
- `runtime_bash` / `runtime_*` rammer udelukkende Jarvis-containeren — de har IKKE brug for operator-fallback.
- In-memory state (`_operator_channel_open`) forsvinder ved process-restart. Fremtidig forbedring: persistér til runtime state store.
- Koden der skal ændres ligger i **to** repos:
  - **jarvis-code** (klient): nye tools + sandbox-check + reroute-logik + tests
  - **jarvis-v2** (server + bridge): `operator_session_run` tool + evt. bridge-protokol-ændring
