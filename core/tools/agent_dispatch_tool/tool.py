"""Tool-wrapper for §19 code-mode agent-dispatch.

Eksponerer agent_dispatch.dispatch_code_mode_task som et tool Jarvis kan kalde.
Orchestratoren havde alle gates (skill-scan §19.8 + agent-kvote §21.7) men var
ikke wiret til et tool — dette gør live dispatch tilgængelig.

Sikkerhed: `execute` defaulter False = bivirkningsfri planlægning (dry_run). Sætter
Jarvis execute=True spawnes agent-teamet via agent_runtime.spawn_agent_task, som selv
har token-budget + expire pr. agent. Owner ubegrænset på kvote; gratis-brugere gated.
"""
from __future__ import annotations

from typing import Any


def _exec_dispatch_code_mode_task(args: dict[str, Any]) -> dict[str, Any]:
    task = str(args.get("task") or "").strip()
    if not task:
        return {"status": "error", "error": "task required"}

    inline = args.get("inline")
    if inline is not None:
        inline = bool(inline)
    try:
        executor_count = int(args.get("executor_count") or 1)
    except (TypeError, ValueError):
        executor_count = 1
    executor_count = max(1, min(executor_count, 4))

    skill_contents = args.get("skill_contents")
    if not isinstance(skill_contents, list):
        skill_contents = None

    user_id = str(args.get("user_id") or "")
    # execute=True → faktisk spawn; default plan-only (bivirkningsfri).
    execute = bool(args.get("execute") or False)

    from core.services.agent_dispatch import dispatch_code_mode_task
    result = dispatch_code_mode_task(
        task, inline=inline, executor_count=executor_count,
        skill_contents=skill_contents, user_id=user_id, dry_run=not execute,
    )
    result.setdefault("status", "ok" if result.get("ok") else "error")
    return result
