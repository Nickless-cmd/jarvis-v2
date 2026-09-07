"""Force-handlere — værktøjer der kører EFTER et menneske har godkendt.

Boy Scout-udtrækning (7/9-2026) fra `core/tools/simple_tools.py` (2.267 linjer).
Samlet her fordi de deler ét ansvar: at køre præcis det kald brugeren sagde ja
til, uden at spørge igen.

`execute_tool_force` slår op i `_FORCE_HANDLERS` FØRST og falder ellers tilbage
til den normale handler — med de OPRINDELIGE argumenter. Mangler en handler
her, rammer et godkendt kald derfor sin egen approval-gren igen og svarer
`approval_needed` på ny, i ring. Godkendelsen kom frem; handlingen skete
aldrig. Invarianten er låst i `tests/test_approval_har_force_handler.py`.

**Force betyder «spring GODKENDELSEN over» — ikke «spring sikkerheden over».**
Blokerede stier og blokerede kommandoer stoppes stadig, før flaget læses.

Ejer-godkendelse er en ANDEN ting end trust: se `owner_approval.py`. Denne fil
kaldes både af `resolve_pending_approval` (et menneske har klikket) og af
autonome runs (ingen har). De to må ikke kunne forveksles.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.tools.file_tools_exec import _exec_edit_file, _exec_write_file
# Alias-import, ikke et lokalt navn. Udskillelsen glemte den foerst, og
# `write_file`/`edit_file` faldt med «name '_guard_py_escapes' is not defined»
# — praecis den fejl der engang braekkede .py-skrivning i syv uger, og som
# simple_tools.py:596 allerede baerer en advarsel om.
from core.tools.py_source_guard import guard_py_escapes as _guard_py_escapes
from core.tools.load_more_tools import _tool_load_more_tools
from core.tools.phone_adb import PHONE_ADB_FORCE_HANDLERS as _PHONE_ADB_FORCE_HANDLERS
from core.tools.simple_tools_native import (
    _exec_calendar_create_event,
    _exec_docs_append,
    _exec_gmail_send,
    _exec_sheets_write,
)
from core.tools.simple_tools_operator import (
    _exec_operator_browser_evaluate,
    _exec_operator_kill_process,
    _exec_operator_launch_app,
    _exec_operator_open_url,
    _exec_operator_record_audio,
)


def _exec_operator_bash(args: dict[str, Any]) -> dict[str, Any]:
    """Sen import: operator_bash_session traekker paa broen, som traekker paa
    simple_tools. En import paa modulniveau ville lukke en cirkel."""
    from core.tools.operator_bash_session import _exec_operator_bash as _impl
    return _impl(args)


def _exec_bash(args: dict[str, Any]) -> dict[str, Any]:
    """Facade → ``simple_tools._exec_bash`` (honorér test-patch-søm).

    Slås op paa `simple_tools` frem for at importeres direkte fra
    `simple_tools_web`, saa en `monkeypatch.setattr(simple_tools, "_exec_bash",
    ...)` stadig virker. Udskillelsen flyttede ellers soemmet, og to tests
    faldt — samme konvention som `simple_tools_operator` bruger.
    """
    from core.tools import simple_tools
    return simple_tools._exec_bash(args)


def _canonicalize_workspace_target(target: Path) -> tuple[Path, str | None]:
    """Sen import: bor i simple_tools, som importerer DENNE fil. En import paa
    modulniveau ville lukke cirklen."""
    from core.tools.simple_tools import _canonicalize_workspace_target as _impl
    return _impl(target)


def _force_write_file(args: dict[str, Any]) -> dict[str, Any]:
    """Write file bypassing approval (blocked paths still blocked)."""
    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return {"error": "path is required", "status": "error"}
    content, _esc_note = _guard_py_escapes(content, path)
    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)
    from core.services.gate_execution import check_file as _check_file
    if _check_file(str(target), kind="write", blocked_only=True).classification == "blocked":
        return {"error": f"Write blocked for safety: {path}", "status": "blocked"}
    target.parent.mkdir(parents=True, exist_ok=True)
    from core.tools.file_tools_exec import _ws_write_text
    _ws_write_text(target, content)
    result = {"status": "ok", "path": str(target), "size": len(content)}
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    if _esc_note:
        result["escape_guard"] = _esc_note
    return result


def _force_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    """Edit file bypassing approval (blocked paths still blocked)."""
    path = str(args.get("path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    if not path or not old_text:
        return {"error": "path and old_text are required", "status": "error"}
    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)
    from core.services.gate_execution import check_file as _check_file
    if _check_file(str(target), kind="edit", blocked_only=True).classification == "blocked":
        return {"error": f"Edit blocked for safety: {path}", "status": "blocked"}
    from core.tools.file_tools_exec import _ws_read_text, _ws_write_text, _ws_path_exists
    if not _ws_path_exists(target):
        return {"error": f"File not found: {path}", "status": "error"}
    content = _ws_read_text(target) or ""
    if old_text not in content:
        return {"error": "old_text not found in file", "status": "error"}
    new_content = content.replace(old_text, new_text, 1)
    new_content, _esc_note = _guard_py_escapes(new_content, str(target))
    _ws_write_text(target, new_content)
    result = {"status": "ok", "path": str(target), "replacements": 1}
    if _esc_note:
        result["escape_guard"] = _esc_note
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    return result


def _force_bash(args: dict[str, Any]) -> dict[str, Any]:
    """Kør bash uden godkendelses-prompt. Blokerede kommandoer stoppes stadig.

    Delegerer til `_exec_bash` (6/9-2026). Før var det en PARALLEL
    implementation: rå subprocess i PROJECT_ROOT, uden persistent shell, uden
    operator-kanal, uden bwrap-sandkasse, uden egress-observation og uden at
    bevare det fulde output til tool-result-storen.

    Det betød at autonome runs kørte en ANDEN bash end synlige ture. Alt hvad
    der blev bygget på `_exec_bash` — og der er kommet meget til — gjaldt
    halvdelen af systemet. En kommando kunne opføre sig forskelligt alt efter
    hvem der kaldte den, hvilket er den slags dobbelt sandhed huset ellers har
    en regel imod.

    Delegeringen følger samme mønster som operator-force-handlerne nedenfor:
    ét flag der springer GODKENDELSEN over, og kun den. Gaten for blokerede og
    guard-blokerede kommandoer sidder før flaget læses.
    """
    command = str(args.get("command") or "").strip()
    if not command:
        return {"error": "command is required", "status": "error"}
    return _exec_bash({**args, "_runtime_trust_all": True})


# ── Force-handlers for operator tools ─────────────────────────────────────
# Kaldes af resolve_pending_approval efter brugeren har klikket Godkend i chat.
# Sætter _runtime_trust_all=True så exec-stubben springer approval_needed over
# og dispatcher direkte til bridge med skip_approval=True.


def _force_operator_bash(args: dict[str, Any]) -> dict[str, Any]:
    """Kør operator_bash direkte efter chat-godkendelse."""
    return _exec_operator_bash({**args, "_runtime_trust_all": True})


def _force_operator_open_url(args: dict[str, Any]) -> dict[str, Any]:
    """Åbn URL direkte efter chat-godkendelse."""
    return _exec_operator_open_url({**args, "_runtime_trust_all": True})


# Google-connectorens skrivende vaerktoejer. De havde SAMME fejl som
# phone_adb_shell: de beder om godkendelse og stod ikke i _FORCE_HANDLERS, saa
# en godkendelse faldt tilbage til den normale handler med de oprindelige
# argumenter og bad om godkendelse paa ny. Fundet 7/9-2026 af invarianten i
# tests/test_approval_har_force_handler.py, som blev skrevet til én fejl og
# afsloerede fire mere — alle fire er UDGAAENDE handlinger (en mail bliver
# sendt, en aftale oprettet), hvor «der skete ingenting» er svaert at se.


def _force_gmail_send(args: dict[str, Any]) -> dict[str, Any]:
    """Send mailen direkte efter chat-godkendelse."""
    return _exec_gmail_send({**args, "_runtime_trust_all": True})


def _force_calendar_create_event(args: dict[str, Any]) -> dict[str, Any]:
    """Opret begivenheden direkte efter chat-godkendelse."""
    return _exec_calendar_create_event({**args, "_runtime_trust_all": True})


def _force_docs_append(args: dict[str, Any]) -> dict[str, Any]:
    """Skriv i dokumentet direkte efter chat-godkendelse."""
    return _exec_docs_append({**args, "_runtime_trust_all": True})


def _force_sheets_write(args: dict[str, Any]) -> dict[str, Any]:
    """Skriv i regnearket direkte efter chat-godkendelse."""
    return _exec_sheets_write({**args, "_runtime_trust_all": True})


def _force_operator_launch_app(args: dict[str, Any]) -> dict[str, Any]:
    """Start program direkte efter chat-godkendelse."""
    return _exec_operator_launch_app({**args, "_runtime_trust_all": True})


def _force_operator_browser_evaluate(args: dict[str, Any]) -> dict[str, Any]:
    """Kør browser-JavaScript direkte efter chat-godkendelse."""
    return _exec_operator_browser_evaluate({**args, "_runtime_trust_all": True})


def _force_operator_kill_process(args: dict[str, Any]) -> dict[str, Any]:
    """Afslut proces direkte efter chat-godkendelse."""
    return _exec_operator_kill_process({**args, "_runtime_trust_all": True})


def _force_operator_record_audio(args: dict[str, Any]) -> dict[str, Any]:
    """Optag lyd direkte efter chat-godkendelse."""
    return _exec_operator_record_audio({**args, "_runtime_trust_all": True})


_FORCE_HANDLERS: dict[str, Any] = {
    "write_file": _force_write_file,
    "edit_file": _force_edit_file,
    "bash": _force_bash,
    "load_more_tools": _tool_load_more_tools,
    # Operator-bridge tools — refaktoreret 2026-05-28 fra bridge.ts OS-dialoger
    # til inline chat-card approvals (samme mønster som bash/write_file/edit_file).
    "operator_bash": _force_operator_bash,
    "operator_open_url": _force_operator_open_url,
    "operator_launch_app": _force_operator_launch_app,
    "operator_browser_evaluate": _force_operator_browser_evaluate,
    "operator_kill_process": _force_operator_kill_process,
    "operator_record_audio": _force_operator_record_audio,
    # Telefonens ADB-vej. Uden dem loeb en godkendelse i ring: den normale
    # handler blev kaldt igen med de oprindelige argumenter og svarede
    # approval_needed paa ny.
    **_PHONE_ADB_FORCE_HANDLERS,
    "gmail_send": _force_gmail_send,
    "calendar_create_event": _force_calendar_create_event,
    "docs_append": _force_docs_append,
    "sheets_write": _force_sheets_write,
}
