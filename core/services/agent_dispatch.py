"""Agent dispatch orchestrator for code mode (spec §19).

Claude-Code-stil: når en større opgave lander i code mode, beslutter Jarvis om
han gør det **inline** (sekventielt selv) eller **dispatcher** en håndfuld agenter
der arbejder parallelt (§19.2). Bygger ovenpå den eksisterende `spawn_agent_task`
+ de 7 agent-roller i agent_runtime.

Tre lag:
- `decide_dispatch` — heuristik: inline vs dispatch ud fra opgavens kompleksitet
- `plan_dispatch` — rolle-plan (researcher→planner→executor×N→critic→synthesizer, §19.4)
- `dispatch_code_mode_task` — orchestrer; skill-scan-gate (§19.8) FØR spawn; `dry_run`
  default True så planlægning er bivirkningsfri/testbar (live spawn kræver dry_run=False)

Resultaterne er ment til at vises i cowork som command center (§19.5).
"""
from __future__ import annotations

import re

# §19.4 dispatch-flow. parallel=True → kan køre samtidigt; planner/synthesizer er
# barrierer (afhænger af forrige lag).
ROLE_PLAN: tuple[dict[str, object], ...] = (
    {"role": "researcher", "parallel": True, "max_turns": 4},
    {"role": "planner", "parallel": False, "max_turns": 2},
    {"role": "executor", "parallel": True, "max_turns": 8},
    {"role": "critic", "parallel": True, "max_turns": 3},
    {"role": "synthesizer", "parallel": False, "max_turns": 2},
)

_COMPLEXITY_KEYWORDS = (
    "implementer", "implement", "refaktor", "refactor", "byg ", "build ",
    "migrer", "migrate", "feature", "spec", "arkitektur", "architecture",
)


def decide_dispatch(task: str, *, force: bool | None = None) -> dict:
    """Heuristik: dispatch agenter eller gør det inline? (§19.2)

    `force=True` → dispatch, `force=False` → inline, `None` → vurder kompleksitet
    (lang opgave, implement/refaktor-nøgleord, eller flere delopgaver → dispatch).
    """
    if force is not None:
        return {"dispatch": bool(force), "reason": "forced", "signals": -1}
    t = str(task or "").lower()
    signals = 0
    if len(t) > 200:
        signals += 1
    if any(k in t for k in _COMPLEXITY_KEYWORDS):
        signals += 1
    if re.search(r"\b\d+[.)]\s", str(task or "")) or t.count(" og ") >= 2:
        signals += 1
    dispatch = signals >= 2
    return {"dispatch": dispatch, "reason": f"{signals} kompleksitets-signaler", "signals": signals}


def plan_dispatch(task: str, *, executor_count: int = 1) -> list[dict]:
    """Byg rolle-planen for en dispatch (§19.3/§19.4). `executor_count` executors
    deler implementeringen parallelt. Hver rolle får sin `max_turns` fra ROLE_PLAN."""
    n_exec = max(1, int(executor_count))
    plan: list[dict] = []
    for step in ROLE_PLAN:
        count = n_exec if step["role"] == "executor" else 1
        for i in range(count):
            suffix = f" (delopgave {i + 1}/{count})" if count > 1 else ""
            plan.append({
                "role": step["role"],
                "goal": f"{step['role']} for: {task}{suffix}",
                "parallel": step["parallel"],
                "max_turns": step.get("max_turns", 5),
            })
    return plan


def scan_skills_before_dispatch(skill_contents: list[str] | None) -> dict:
    """Kør skill_scanner på hver skill der vil eksekvere lokalt (§19.8). Blokerer
    dispatch hvis nogen skill fejler scanningen."""
    # Skill-Safety-cluster 🔒 GENNEM Den Intelligente Central (SECURITY, traced).
    from core.services.gate_skill import check_skill_scan
    blocked: list[dict] = []
    for i, content in enumerate(skill_contents or []):
        result = check_skill_scan(content)
        if not result.allowed:
            blocked.append({"index": i, "reasons": result.blocked_reasons})
    return {"allowed": not blocked, "blocked": blocked}


def dispatch_code_mode_task(task: str, *, inline: bool | None = None,
                            executor_count: int = 1,
                            skill_contents: list[str] | None = None,
                            user_id: str = "",
                            dry_run: bool = True) -> dict:
    """Orchestrér en code-mode-opgave (§19.4).

    1. Skill-scan-gate (§19.8) — blokér hvis en lokal skill fejler.
    2. Beslut inline vs dispatch.
    3. Agent-kvote-gate (§21.7) ved dispatch — owner ubegrænset, fail-open.
    4. Inline → returnér med det samme. Dispatch → byg plan, spawn agenter
       (kun hvis dry_run=False; default dry_run=True = bivirkningsfri planlægning).

    `inline=True/False` tvinger valget; `None` lader heuristikken afgøre.
    """
    scan = scan_skills_before_dispatch(skill_contents)
    if not scan["allowed"]:
        return {"ok": False, "reason": "skill_scan_blocked", "scan": scan}

    force = None if inline is None else (not inline)
    decision = decide_dispatch(task, force=force)
    if not decision["dispatch"]:
        return {"ok": True, "mode": "inline", "decision": decision}

    # §21.7: agent-dispatch tæller mod brugerens daglige agent-kvote (owner ubegrænset).
    try:
        from core.services.quota_store import consume_quota
        q = consume_quota(user_id, "agent")
        if not q.get("consumed", True):
            return {"ok": False, "reason": "quota_exceeded", "quota": q, "decision": decision}
    except Exception:
        pass  # fail-open

    plan = plan_dispatch(task, executor_count=executor_count)
    # recursion_guard (2026-07-24): bound children-per-dispatch. Normal plans are ~5
    # steps (ROLE_PLAN), so the default ceiling only trips on pathological fan-out.
    # Cap + log rather than raise or drop silently, so a legit dispatch still runs.
    from core.services import recursion_guard as _rg
    if plan and not _rg.fanout_allowed(len(plan)):
        _cap = _rg.effective_max_fanout()
        import logging
        logging.getLogger(__name__).warning(
            "agent_dispatch: plan fan-out %d exceeds cap %d — truncating to cap",
            len(plan), _cap,
        )
        plan = plan[:_cap]
    spawned: list[dict] = []
    if not dry_run:
        from core.services.agent_runtime import spawn_agent_task
        for step in plan:
            try:
                max_turns = int(step.get("max_turns") or 5)
                res = spawn_agent_task(role=str(step["role"]), goal=str(step["goal"]),
                                       auto_execute=True, max_turns=max_turns)
                spawned.append({"role": step["role"], "agent_id": res.get("agent_id")})
            except Exception as exc:
                spawned.append({"role": step["role"], "error": str(exc)})

    return {"ok": True, "mode": "dispatch", "decision": decision,
            "plan": plan, "spawned": spawned, "dry_run": dry_run}
