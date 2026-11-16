"""Lazy tool schema loader for visible-lane tool pruning."""

from __future__ import annotations

from copy import deepcopy

from core.tools.simple_tools_definitions import TOOL_DEFINITIONS


def _tool_name(tool_def: dict) -> str:
    fn = tool_def.get("function") or tool_def
    return str(fn.get("name") or tool_def.get("name") or "")


def _tool_load_more_tools(arguments: dict) -> dict:
    """Resolve tools to add to the next round and return their full schemas."""
    import json as _json

    from core.eventbus.bus import event_bus
    from core.runtime.db import connect

    names = list(arguments.get("names") or [])
    query = (arguments.get("query") or "").strip()

    all_by_name = {
        _tool_name(d): d
        for d in (TOOL_DEFINITIONS or [])
        if _tool_name(d)
    }
    from core.tools.tool_scoping import RETIRED_AGENT_CREATION_TOOLS
    all_by_name = {name: definition for name, definition in all_by_name.items()
                   if name not in RETIRED_AGENT_CREATION_TOOLS}
    from core.tools.autonomous_tool_policy import is_allowed as _autonomous_allowed
    all_by_name = {name: definition for name, definition in all_by_name.items()
                   if _autonomous_allowed(name)}

    # ── Scope-porten (maalt 16/11-2026) ────────────────────────────────────
    #
    # Uden dette slog hentningen op i HELE kataloget og returnerede schemas
    # som scope-porten aldrig ville annoncere. Maalt i chat-scope: porten
    # afviste `bash`, `write_file`, `operator_bash` og `edit_file` — men
    # `load_more_tools` gav alle fire tilbage, og de kunne derefter kaldes.
    # Porten var altsaa formel, ikke virkelig: et vaerktoej uden for scopet
    # var ét `load_more_tools`-kald vaek.
    #
    # Hensigten med vaerktoejet er katalogets LANGE HALE — de vaerktoejer
    # scopet tillader, men pruneren ikke annoncerede — ikke at hente uden
    # for scopet. Filtreringen bruger praecis den samme funktion som porten
    # selv (`allowed_tool_names`), saa der ikke opstaar en anden sandhed.
    #
    # Fail-open paa tomt scope: legacy-vejen ("" = ubegraenset) skal vaere
    # byte-identisk med foer. Kan rollen eller scopet ikke laeses, filtreres
    # der ikke — en hentning maa ikke doe af en manglende ContextVar.
    try:
        from core.identity.workspace_context import current_role as _current_role
        from core.tools.tool_scoping import (
            allowed_tool_names as _allowed_tool_names,
            current_tool_scope as _current_tool_scope,
        )
        _scope = _current_tool_scope()
        if _scope:
            _tilladte = _allowed_tool_names(
                role=_current_role(), scope=_scope, all_names=list(all_by_name),
            )
            all_by_name = {
                name: definition
                for name, definition in all_by_name.items()
                if name in _tilladte
            }
    except Exception:  # en hentning maa ikke doe af en manglende ContextVar
        pass

    resolved: list[str] = []
    unknown: list[str] = []
    for n in names:
        if n in all_by_name:
            resolved.append(n)
        else:
            unknown.append(n)

    if query and not resolved:
        try:
            from core.services.tool_embeddings import top_k_similar
            hits = top_k_similar(query, k=10)
            resolved = [n for n, _ in hits if n in all_by_name][:5]
        except Exception:
            resolved = []

    if not resolved and unknown:
        return {
            "status": "error",
            "error": f"tools not found: {unknown}. Use names from the TOOL CATALOG.",
        }

    if not resolved:
        return {
            "status": "ok",
            "added": [],
            "message": "no strong matches",
            "tool_definitions": [],
            "schemas": [],
        }

    # ── Run-id'et paa hentningen (14/11-2026) ──────────────────────────────
    #
    # Maalt: `tool_router.dispatcher_brugt` baerer run_id, men hentningen gjorde
    # ikke — 0 af 179 i syv dage. Uden den kan «hentede dette run et vaerktoej,
    # og kaldte det det bagefter?» ikke besvares, og adoptionsraten maa gættes
    # som et forhold mellem to loesrevne taellinger. Det gjorde scriptet netop:
    # 230 kald / 614 navne = «37 %», mens `db_query` alene stod med 87 kald mod
    # 37 hentninger — 235 % for ét navn, hvilket er umuligt som en rate.
    #
    # `_runtime_turn_id` haeftes af `simple_tool_executor` FOER handleren kaldes;
    # contextvar'en er reserve for veje uden om executoren. ``UKENDT`` gemmes som
    # TOMT: en join-noegle der hedder «UKENDT» ville smelte alle ukendte runs
    # sammen til ét fiktivt run og opfinde en adoption der ikke findes.
    run_id = ""
    try:
        from core.tools.tool_call_telemetry import identitet
        _rid = str(identitet(arguments or {}).get("run_id") or "")
        run_id = "" if _rid == "UKENDT" else _rid
    except Exception:  # maalingen maa aldrig stoppe en hentning
        run_id = ""

    try:
        event_bus.publish("tool_router.load_more_fired", {
            "requested_names": names,
            "requested_query": query,
            "resolved_names": resolved,
            "run_id": run_id,
        })
    except Exception:
        pass

    try:
        with connect() as c:
            c.execute(
                "INSERT INTO tool_router_load_more("
                "run_id, requested_names_json, requested_query, "
                "resolved_names_json, created_at) "
                "VALUES (?,?,?,?, datetime('now'))",
                (run_id, _json.dumps(names), query, _json.dumps(resolved)),
            )
            c.commit()
    except Exception:
        pass

    tool_definitions = [deepcopy(all_by_name[n]) for n in resolved if n in all_by_name]
    schemas: list[dict] = []
    for d in tool_definitions:
        fn = d.get("function") or d
        schemas.append(
            {
                "name": fn.get("name"),
                "description": fn.get("description"),
                "parameters": fn.get("parameters"),
            }
        )

    return {
        "status": "ok",
        "added": resolved,
        "schemas": schemas,
        "tool_definitions": tool_definitions,
        "message": (
            f"Added {len(resolved)} tool(s). Full schema below. Call them via "
            "call_loaded_tool(navn=\"<navn>\", argumenter={...}) using exactly "
            "these parameter names; do not guess."
        ),
    }
