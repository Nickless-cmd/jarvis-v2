"""De tre akser skilt ad — Fase 3, K1.

Exit-kriteriet er «execution provider, presentation mode, and UI metadata are
separate». De ER der allerede. De er bare ikke skilt ad, og hvor de ikke er
skilt ad, driver de fra hinanden.

## Hvad maalingen viste

466 vaerktoejer annonceres. En definition baerer praecis tre felter — `name`,
`description`, `parameters`. Alt andet ligger spredt:

    hvor koerer det     `_TOOL_HANDLERS` (in-process), operator-broen (kun
                        laesbar ved at inspicere hver handlers KILDE, 48 stk.),
                        og `LOCAL_EXEC_ONLY_TOOLS` i `tool_scoping`
    hvad goer det       en haardkodet liste paa 8 navne — 1,7% af 466.
                        `edit_file`, `bash`, `gmail_send`, `stripe_*` staar
                        ikke paa den
    godkendelse         inde i hver `_exec_`-funktion
    ui/praesentation    findes ikke; klienten render fra det raa resultat

Og de tre sandheder er UENIGE. `read_identity_sketch` og
`update_identity_sketch` annonceres til modellen, deres `_exec_`-funktioner
importeres i `simple_tools`, og de blev aldrig lagt i dispatch-dict'en. Kalder
man dem, faar man `Unknown tool`. `tool_scoping` siger selv hvorfor det er
farligt — «maa ALDRIG annonceres uden for et local_tool_exec-run, ellers kunne
modellen kalde et vaerktoej serveren ikke kan udfoere» — men reglen var kun
skrevet, ikke tjekket.

## Hvad dette modul ER og ikke er

Det er en ADAPTER. Den UDLEDER akserne fra dér hvor de allerede bor. Spec'en
siger det direkte: «It should not require every tool to be rewritten
immediately». Ingen af de 466 vaerktoejer aendres.

`inconsistencies()` er den vagt der manglede: den siger hoejt naar de tre
sandheder er uenige.

## Praesentationsform staar med vilje IKKE her

Spec'en: «Tool-call presentation mode (`native`, `ptc`, or `both`) is selected
once per effective agent/request profile, not per tool definition.» Jarvis
koerer native. At give definitionen et felt for det ville vaere at bygge
sammenfoejningen K1 beder om at fjerne — saa feltet findes ikke, og en test
vogter at det bliver saadan.

UI-metadata er ligeledes ikke en egenskab ved vaerktoejet: `presentation_meta`
udledes af det KONKRETE kald og dets resultat, ikke af definitionen.
"""
from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── akse 1: hvor koerer det ──────────────────────────────────────────────
IN_PROCESS = "in_process"
OPERATOR_BRIDGE = "operator_bridge"
CLIENT_LOCAL = "client_local"
INGEN = "none"          # annonceret uden nogen executor — altid en fejl

# ── akse 2: hvad goer det ved verden ─────────────────────────────────────
READ_ONLY = "read_only"
NON_IDEMPOTENT_WRITE = "non_idempotent_write"
UKENDT = "unknown"      # aerligt: 458 af 466 er her

# ── akse 3: skal nogen spoerges ──────────────────────────────────────────
APPROVAL_NONE = "none"
APPROVAL_ASK = "ask"


@dataclass(frozen=True)
class ToolDefinitionV2:
    name: str
    definition_version: str
    description: str
    args_schema: dict
    execution_provider: str
    effect_class: str
    approval_requirement: str
    surface_tags: frozenset[str] = field(default_factory=frozenset)

    @property
    def annonceret_uden_executor(self) -> bool:
        return self.execution_provider == INGEN


_cache: dict[str, ToolDefinitionV2] = {}


def _nulstil_for_tests() -> None:
    _cache.clear()


def _pak_ud(handler: Any) -> Any:
    """Find den ÆGTE funktion bag eventuelle indpakninger.

    `simple_tools_enforcement._enforce_wrapper` pakker en del handlere ind.
    Uden udpakningen laeser man wrapperens otte linjer og konkluderer at ALT
    koerer in-process — en maaling der ser praecis lige saa selvsikker ud som
    en rigtig. Fanget da `operator_write_file` blev klassificeret 'in_process'.
    """
    set_af = set()
    for _ in range(10):
        if id(handler) in set_af:
            break
        set_af.add(id(handler))
        indre = getattr(handler, "__wrapped__", None)
        if indre is None:
            celler = getattr(handler, "__closure__", None) or ()
            kandidater = [c.cell_contents for c in celler
                          if inspect.isfunction(getattr(c, "cell_contents", None))]
            if len(kandidater) != 1:
                break
            indre = kandidater[0]
        handler = indre
    return handler


def _handler_kilde(handler: Any) -> str:
    try:
        return inspect.getsource(_pak_ud(handler))
    except Exception:
        return ""


def _udled_provider(navn: str, handler: Any) -> str:
    """Hvor koerer vaerktoejet? Udledt af KODEN, ikke af navnet.

    Et navnepraefiks er en konvention, ikke en sandhed: `operator_`-praefikset
    holder i dag, men det er en aftale ingen haandhaever. Kilden loeber ikke.
    """
    try:
        from core.tools.tool_scoping import LOCAL_EXEC_ONLY_TOOLS
        if navn in LOCAL_EXEC_ONLY_TOOLS:
            return CLIENT_LOCAL
    except Exception:
        pass
    if handler is None:
        return INGEN
    kilde = _handler_kilde(handler)
    if "_run_operator_async" in kilde or "operator_tools" in kilde:
        return OPERATOR_BRIDGE
    return IN_PROCESS


def _udled_effekt(navn: str) -> str:
    try:
        from core.services.permission_classifier import _MUTATING_TOOLS
        if navn in _MUTATING_TOOLS:
            return NON_IDEMPOTENT_WRITE
    except Exception:
        pass
    return UKENDT


def _udled_godkendelse(navn: str, handler: Any) -> str:
    try:
        from core.tools.force_handlers import _FORCE_HANDLERS
        if navn in _FORCE_HANDLERS:
            return APPROVAL_ASK
    except Exception:
        pass
    if handler is not None and "approval_needed" in _handler_kilde(handler):
        return APPROVAL_ASK
    return APPROVAL_NONE


def _udled_flader(navn: str) -> frozenset[str]:
    ud = set()
    try:
        from core.tools.tool_scoping import (
            LOCAL_EXECUTION_TOOLS, is_local_execution_tool)
        if is_local_execution_tool(navn) or navn in LOCAL_EXECUTION_TOOLS:
            ud.add("code_mode")
    except Exception:
        pass
    return frozenset(ud)


def describe(navn: str) -> ToolDefinitionV2 | None:
    """Byg V2-beskrivelsen for ét vaerktoej. None hvis det ikke annonceres."""
    navn = str(navn or "")
    if navn in _cache:
        return _cache[navn]
    from core.tools.simple_tools import _TOOL_HANDLERS
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    from core.tools.tool_schema_contract import schema_version

    raa = next((d["function"] for d in TOOL_DEFINITIONS
                if d.get("function", {}).get("name") == navn), None)
    if raa is None:
        return None
    h = _TOOL_HANDLERS.get(navn)
    d = ToolDefinitionV2(
        name=navn,
        definition_version=schema_version(navn),
        description=str(raa.get("description") or ""),
        args_schema=raa.get("parameters") or {},
        execution_provider=_udled_provider(navn, h),
        effect_class=_udled_effekt(navn),
        approval_requirement=_udled_godkendelse(navn, h),
        surface_tags=_udled_flader(navn),
    )
    _cache[navn] = d
    return d


def all_definitions() -> list[ToolDefinitionV2]:
    from core.tools.simple_tools_definitions import TOOL_DEFINITIONS
    ud = []
    for x in TOOL_DEFINITIONS:
        d = describe(str(x.get("function", {}).get("name") or ""))
        if d is not None:
            ud.append(d)
    return ud


def inconsistencies() -> list[dict[str, str]]:
    """Hvor er de tre sandheder uenige?

    Den vagt der manglede. `tool_scoping` skrev reglen ned; ingen tjekkede den.
    """
    ud = []
    for d in all_definitions():
        if d.annonceret_uden_executor:
            ud.append({
                "tool": d.name,
                "kind": "advertised_without_executor",
                "detail": ("annonceret til modellen, men har hverken en "
                           "dispatch-handler eller klient-lokal placering — "
                           "et kald giver 'Unknown tool'"),
            })
    return ud


def presentation_meta(navn: str, arguments: dict[str, Any] | None,
                      result: dict[str, Any] | None) -> dict[str, Any]:
    """Semantiske hints til klientens kort — udledt af det KONKRETE kald.

    Bevidst adskilt fra definitionen. Spec'en: «`presentation_meta` contains
    versioned semantic hints only; the client remains responsible for rendering
    cards from canonical arguments, results, failure state, and those hints.»
    Et vaerktoej HAR ikke et udseende; et kald har et udfald.
    """
    d = describe(navn)
    status = ""
    if isinstance(result, dict):
        status = str(result.get("status") or "")
    return {
        "meta_version": 1,
        "tool": navn,
        "definition_version": d.definition_version if d else "",
        "effect_class": d.effect_class if d else UKENDT,
        "execution_provider": d.execution_provider if d else INGEN,
        "outcome": status or ("ok" if isinstance(result, dict) else ""),
        "needs_approval": bool(status == "approval_needed"),
    }
