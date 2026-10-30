"""Commit-værktøj uden shell — beskeden kan ikke fortolkes.

Målt 30/10-2026: en commit-besked med backticks blev skåret, fordi
``bash "git commit -m '<besked>'"`` sender beskeden gennem en shell FØR git
ser den. Reglen om at bruge en quoted heredoc stod i prompten den tur og
blev ikke anvendt — information var tilgængelig, men fik ingen indflydelse
på handlingen.

Dette værktøj flytter sikkerheden fra *hukommelse* til *handlingsvej*:
beskeden er et JSON-argument, og ``commit_with_attribution`` skriver den til
en temp-fil som ``git commit -F`` læser. Der er ingen shell imellem, så
backticks, ``$variabel`` og citationstegn er bare tegn.
"""

from __future__ import annotations

from typing import Any


COMMIT_ATTRIBUTED_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "commit_attributed",
            "description": (
                "Commit with canonical attribution WITHOUT going through a shell. "
                "The message is a JSON argument, so backticks, $variables and "
                "quotes cannot be interpreted by bash. Use this instead of "
                "bash 'git commit -m ...' whenever the message contains shell "
                "metacharacters — or as the default way to commit. Six audit "
                "trailers (Actor, Actor-Type, Run-ID, Session-ID, Origin, "
                "Approved-By) are appended automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": (
                            "Commit subject and optional body. Attribution "
                            "trailers are appended automatically."
                        ),
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Optional paths to stage and commit. Omit to stage "
                            "everything (git add -A)."
                        ),
                    },
                    "repo": {
                        "type": "string",
                        "description": (
                            "Repository root. Defaults to the Jarvis project root."
                        ),
                    },
                },
                "required": ["message"],
            },
        },
    },
]


def _exec_commit_attributed(args: dict[str, Any]) -> dict[str, Any]:
    """Commit med canonical attribution uden at gå gennem en shell."""
    message = str(args.get("message") or "").strip()
    if not message:
        return {"status": "error", "error": "message is required"}

    from core.runtime.config import PROJECT_ROOT

    repo = str(args.get("repo") or "").strip() or str(PROJECT_ROOT)

    raw_paths = args.get("files") or args.get("paths") or []
    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    if not isinstance(raw_paths, list):
        raw_paths = []
    selected = tuple(str(p) for p in raw_paths if str(p))

    try:
        from core.services.git_actions import commit_paths_as_jarvis

        result = commit_paths_as_jarvis(repo, message, selected)
    except Exception as exc:  # self-safe: værktøjet må svare, ikke vælte turen
        return {"status": "error", "error": f"commit failed: {exc}"}

    if result.get("status") == "ok":
        subject = message.splitlines()[0][:80]
        result["text"] = (
            f"Committed {result.get('sha')} on {result.get('branch')}: {subject}"
        )
    return result


COMMIT_ATTRIBUTED_TOOL_HANDLERS = {
    "commit_attributed": _exec_commit_attributed,
}
