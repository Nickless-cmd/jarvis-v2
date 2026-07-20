"""Single source of truth for what jarvis-code (jc) presents as tools.

Defines the curated default companion set, the runtime_-alias for the four
colliding file/shell primitives, and (in later tasks) the load_more contents.
Kept tiny and dependency-light so both the /v1/tools/catalog endpoint and tests
import it. `skill_gate` is an always-present companion (Fase 3, Task 2) so
jarvis-code's model can call it mid-turn like any other tool; the client's
first-turn auto-call is separate glue on top (see jarvis-code src/skill_trigger.py).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

RUNTIME_ALIAS_PREFIX = "runtime_"

# Verified 2026-07-12: only these four native tools share a name with jc's
# client-owned local tools and therefore need aliasing.
COLLIDING_TOOLS: tuple[str, ...] = ("bash", "read_file", "write_file", "edit_file")

# Always-present native companions (unique names -> no alias needed).
DEFAULT_COMPANIONS: tuple[str, ...] = (
    "search_memory", "read_memory_topic", "write_memory_topic",
    "read_project_notes", "update_project_notes",
    "recall_memories", "search_jarvis_brain",
    "remember_this", "archive_brain_entry", "read_mood", "skill_gate",
)


def alias_for(name: str) -> str:
    """runtime_ alias for a colliding tool name."""
    return f"{RUNTIME_ALIAS_PREFIX}{name}"


def unalias(name: str) -> str:
    """Strip the runtime_ prefix iff it maps to a colliding tool; else unchanged."""
    if is_runtime_alias(name):
        return name[len(RUNTIME_ALIAS_PREFIX):]
    return name


def is_runtime_alias(name: str) -> bool:
    """True only for runtime_<one-of-the-four-colliding-tools>."""
    if not name.startswith(RUNTIME_ALIAS_PREFIX):
        return False
    return name[len(RUNTIME_ALIAS_PREFIX):] in COLLIDING_TOOLS


# Tools jarvis-code EJER og eksekverer på KLIENTENS host (ikke server/container).
# Single source of truth for "client"-klassifikationen. De fire COLLIDING_TOOLS er
# klient-side når de er bare; deres runtime_-alias er container-formen ("runtime").
CLIENT_TOOLS: frozenset[str] = frozenset({
    "bash", "read_file", "write_file", "edit_file", "multi_edit",
    "glob", "grep", "web_fetch", "web_scrape", "web_search",
    "bash_output", "todo_write", "task",
})


def execution_location(name: str) -> str:
    """Hvor et tool med DETTE præsenterede navn eksekverer:
      "client"  — den forbundne overflades host (jarvis-code/desk lokale tools)
      "runtime" — Jarvis' egen container (de runtime_-aliasede kolliderende tools)
      "server"  — server-processen / hjernen (memory, operator, cognitive tools)
    Single source of truth som Fase 1's loop-router slår op i. runtime_-aliaset er
    blot PRÆSENTATIONEN af execution=="runtime"."""
    n = (name or "").strip()
    if is_runtime_alias(n):
        return "runtime"
    if n in CLIENT_TOOLS:
        return "client"
    return "server"


def execution_map(defs: list[dict[str, Any]]) -> dict[str, str]:
    """Kortlæg en liste af tool-defs → {navn: execution_location}. Muterer IKKE
    def'sne (de sendes til providers; en fremmed nøgle kunne bryde et strengt kald).
    Router-laget (Fase 1) læser dette kort ved navn."""
    return {_def_name(d): execution_location(_def_name(d)) for d in defs}


LOAD_MORE_TOOL_DEF: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "load_more_tools",
        "description": (
            "Unlock the full runtime toolbox (owner only): runtime_bash/read_file/"
            "write_file/edit_file, advanced memory, identity, operator desktop tools. "
            "Call this when the default set is insufficient."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}


def build_jc_catalog_text() -> str:
    """Jarvis-code-SPECIFIK toolbox-forklaring til prompten (Bjørn: der manglede en
    sektion om runtime_*, så Jarvis blev forvirret). Forklarer de TRE eksekverings-mål
    — samme tool-navn betyder forskellige ting her end i desk, så det SKAL siges.
    Injiceres kun på jarvis-code-surfacen (local_tool_exec / Path B)."""
    return (
        "🧰 DIN TOOLBOX I JARVIS-CODE — tre eksekverings-mål (samme navn ≠ samme sted "
        "som i desk):\n"
        "• NATIVE (bash, read_file, write_file, edit_file, glob, grep, multi_edit, "
        "bash_output): kører på BJØRNS maskine — dér hvor jarvis-code lever. Det er dit "
        "DEFAULT når du arbejder i hans projekter/filer. `bash` = Bjørns terminal.\n"
        "• runtime_* (runtime_bash, runtime_read_file, runtime_write_file, "
        "runtime_edit_file): kører i DIN EGEN container — serveren du bor på. Brug dem "
        "når du skal røre DIT eget runtime/hjem, IKKE Bjørns maskine. `runtime_bash` = "
        "din container-terminal.\n"
        "• operator_* (operator_bash, operator_read_file, …): når du skal nå Bjørns "
        "maskine via operator-BROEN (en eksplicit bagvej). `bash` er den direkte vej til "
        "hans maskine; operator_* er bro-vejen — brug den kun når du specifikt har brug "
        "for broen.\n"
        "runtime_*/operator_* + avancerede memory/identity-tools låses op med "
        "load_more_tools. Kort: `bash`=Bjørns maskine · `runtime_bash`=din container · "
        "`operator_bash`=Bjørns maskine via bro."
    )


def _def_name(d: dict[str, Any]) -> str:
    return str((d.get("function") or d).get("name") or "")


def _all_native_defs(role: str) -> list[dict[str, Any]]:
    """Full native tool defs for a role. Wrapped as a module function for test injection."""
    from core.tools.simple_tools import get_tool_definitions
    return get_tool_definitions(role=role, scope="")


def build_jc_catalog(*, role: str, unlocked: bool) -> list[dict[str, Any]]:
    """Native-side tool defs jc should present (WITHOUT the 8 local client tools —
    jc prepends those). Locked: companions + load_more. Unlocked: companions +
    runtime_-aliased colliding tools + the rest of native + load_more."""
    all_defs = _all_native_defs(role)
    by_name = {_def_name(d): d for d in all_defs}
    out: list[dict[str, Any]] = []

    for name in DEFAULT_COMPANIONS:
        d = by_name.get(name)
        if d is not None:
            out.append(deepcopy(d))

    if unlocked:
        presented = {_def_name(d) for d in out}
        for d in all_defs:
            nm = _def_name(d)
            if nm in presented or nm == "load_more_tools":
                continue
            if nm in COLLIDING_TOOLS:
                alias = deepcopy(d)
                fn = alias.get("function") or alias
                fn["name"] = alias_for(nm)
                out.append(alias)
            else:
                out.append(deepcopy(d))

    out.append(deepcopy(LOAD_MORE_TOOL_DEF))
    return out
