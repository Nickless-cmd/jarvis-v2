"""Ændrede dette værktøjskald verden? (loop-fix 2026-09-05)

Baggrund — målt i Bjørns session 5. september kl. 06:05:

Jarvis rettede en linje i USER.md med `edit_file` og ville derefter verificere
at rettelsen landede. Han kørte den SAMME bash-kommando som før skrivningen.
Den blev afvist med «[Duplicate tool call skipped in same visible run]», fordi
`simple_tool_executor` husker enhver `(værktøj, argumenter)`-signatur for hele
runnet og aldrig rydder sættet. To sådanne runder i træk fik no-progress-
detektoren til at konkludere «intet nyt lært», tvinge en afslutningsrunde uden
værktøjer, og runnet endte som `completed` med sætningen «Lad mig læse filen
direkte med read_file i stedet.» Bjørn måtte selv skrive «Du stoppede?».

Det næste run kørte præcis den blokerede kommando og fik svar med det samme —
fordi dedup-sættet var nyt. Verifikation efter skrivning var altså strukturelt
umulig inden for ét run, samtidig med at edit-værktøjets egen verify-hint beder
om den.

Dedup-værnet mod ægte spin skal blive. Men når verden HAR ændret sig, er en
gentagen observation ikke en gentagelse — den er hele pointen. Dette modul
afgør hvornår det er tilfældet, og bruges to steder: til at rydde dedup-sættet
efter en mutation, og til ikke at tælle en muterende runde som «ingen fremgang».
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Shell-værktøjer afgøres på KOMMANDOEN, ikke på navnet: langt de fleste
# bash-kald er grep/ls/cat og ændrer ingenting.
_SHELL_TOOLS = frozenset({"bash", "bash_session_run", "operator_bash", "operator_bash_session"})
_ARG_KEYS_COMMAND = ("command", "cmd", "script", "input")


def _shell_command(arguments: dict[str, Any]) -> str:
    for key in _ARG_KEYS_COMMAND:
        value = (arguments or {}).get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _mutation_tool_names() -> frozenset[str]:
    """Navne fra verification_gate — ét sted at vedligeholde listen."""
    try:
        from core.services.verification_gate import _MUTATION_TOOLS
        return frozenset(_MUTATION_TOOLS)
    except Exception:
        return frozenset({"write_file", "edit_file", "publish_file", "stage_edit_file"})


def call_changed_the_world(
    *, tool_name: str, arguments: dict[str, Any] | None = None,
    status: str = "ok",
) -> bool:
    """True når kaldet reelt ændrede state (og lykkedes).

    Konservativ i BEGGE retninger: et fejlet kald ændrede intet, og en ukendt
    shell-kommando regnes som en mutation (`shell_command_is_mutating`), fordi
    det er dyrere at blokere en ægte verifikation end at rydde et dedup-sæt for
    tidligt.
    """
    if str(status or "ok") != "ok":
        return False
    name = str(tool_name or "").strip()
    if not name:
        return False
    args = dict(arguments or {})
    if name in _SHELL_TOOLS:
        command = _shell_command(args)
        if not command:
            return False
        try:
            from core.services.verification_gate import shell_command_is_mutating
            return bool(shell_command_is_mutating(command))
        except Exception:
            return True
    return name in _mutation_tool_names()


def round_changed_the_world(results: list[dict[str, Any]] | None) -> bool:
    """Ændrede mindst ét kald i denne agentiske runde verden?"""
    for item in results or []:
        if not isinstance(item, dict):
            continue
        try:
            if call_changed_the_world(
                tool_name=str(item.get("tool_name") or ""),
                arguments=item.get("arguments") or {},
                status=str(item.get("status") or "ok"),
            ):
                return True
        except Exception:
            continue
    return False
