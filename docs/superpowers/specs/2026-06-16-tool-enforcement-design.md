# Spor A — Serverside tool-håndhævelse (defense-in-depth)

**Anledning:** Bjørns sikkerheds-gennemgang (16. jun 2026). Bekymring: kan nogen
misbruge Jarvis til at kalde værktøjer de ikke må? Audit-fund: tool-adgang er i dag
KUN håndhævet model-side (værktøjslisten filtreres i prompten via
`permission_engine`/`tool_scoping`). `execute_tool()` selv tjekker ikke rollen → der
mangler en "anden lås" ved selve eksekveringen. En prompt-injection, en fremtidig
intern bypass eller en bug kan i princippet nå et uautoriseret værktøj.

**Mål:** Tilføj en serverside håndhævelses-tjek i tool-eksekverings-chokepoint'et, så
selv hvis model-filteret omgås, nægtes uautoriserede kald. To låse i stedet for én.

## Princip: ingen dobbelt-sandhed

`permission_engine.allowed_tools(role, mode)` forbliver eneste sikkerheds-sandhed.
Håndhævelsen GENBRUGER `tool_scoping.allowed_tool_names` (som allerede wrapper
permission_engine + computer-use-policy), så model-filter og eksekverings-gate er
matematisk identiske. Vi indfører ingen ny politik her — kun et nyt håndhævelsespunkt.

## Komponenter

### 1. `tool_scoping.is_tool_allowed(role, scope, name) -> bool` (ny, ren, testbar)
```python
def is_tool_allowed(*, role: str, scope: str, name: str) -> bool:
    """Må (role, scope) eksekvere værktøjet `name`? Owner/unbound ("") → altid True
    (owner + betroede interne/daemon-kald). Non-owner → permission_engine via
    allowed_tool_names (samme sandhed som model-filteret)."""
    r = (role or "").strip().lower()
    if r in ("", "owner"):
        return True
    return name in allowed_tool_names(role=r, scope=scope, all_names={name})
```

### 2. Guard i `simple_tools.execute_tool()` (håndhævelsespunktet)
Lige efter handler-opslag (ukendt-tool-fejl bevares), før trust-gaten:
```python
try:
    from core.identity.workspace_context import effective_role
    from core.tools.tool_scoping import is_tool_allowed, current_tool_scope
    _role = effective_role()  # respekterer TOTP-override
    if _role not in ("", "owner") and not is_tool_allowed(
        role=_role, scope=(current_tool_scope() or ""), name=name
    ):
        result = {"status": "error", "error": "tool_not_permitted",
                  "detail": f"Værktøjet '{name}' er ikke tilladt for rollen '{_role}'.",
                  "role": _role, "tool": name}
        try:
            event_bus.publish("incident.tool_denied",
                              {"tool": name, "role": _role})
        except Exception:
            pass
        _record_tool_outcome_memory(name, arguments, result, mode="tool")
        return result
except Exception:
    pass  # fail-open KUN på håndhævelses-FEJL (ikke på afvisning) — aldrig låse
           # owner/daemoner ude; model-filteret er stadig primær gate.
```

**Fail-posture:** fail-CLOSED på en ægte afvisning (role kendt, tool ikke tilladt).
fail-OPEN kun hvis selve tjekken kaster (kontekst-modul-hikke) — for ikke at låse
owner/daemoner ude. Matcher husets `_apply_computer_use_policy`-mønster.

### 3. Sikkerheds-event ved afvisning
`incident.tool_denied` → Mission Control kan vise "X forsøgte `tool` — nægtet".

## Data-flow
Discord-afsender → rolle bundet i context ([discord_gateway.py:772](../../../core/services/discord_gateway.py)) →
`effective_role()` ved eksekvering → `permission_engine`-sandhed → tillad/nægt.

## Fejlhåndtering
Afvisning returnerer struktureret `{status:error, error:"tool_not_permitted", ...}`
så den synlige model kan sige "det må jeg ikke for dig" i stedet for at fejle grimt.

## Tests (TDD)
**`tests/test_tool_scoping.py`** (`is_tool_allowed`):
- owner → True for ethvert navn (også `bash`).
- "" (unbound/daemon) → True for ethvert navn.
- member chat → True for `web_search`, False for `bash`.
- guest → False for alt.

**`tests/test_tool_enforcement.py`** (`execute_tool`-guard, ny fil):
- member-kontekst + `bash` → resultat `error=tool_not_permitted`, handler kører IKKE.
- member-kontekst + tilladt værktøj → handler KØRER (gate slipper igennem).
- owner-kontekst + `bash` → gate slipper igennem (ingen afvisning).
- ingen kontekst (daemon) → gate slipper igennem.

## Ikke i scope (senere spor)
- C: justering af member-matrixen (hvilke værktøjer pr. mode).
- B: afbrydelser. D: per-bruger-skarphed.
- Ægte enforcement på `execute_tool_force` (approval-stien) — samme mønster kan
  tilføjes, men force-stien kræver allerede eksplicit godkendelse; noteres som opfølgning.
