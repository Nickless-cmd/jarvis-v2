"""Tests for agent_dispatch (§19)."""
from __future__ import annotations


def test_decide_dispatch_simple_is_inline() -> None:
    from core.services.agent_dispatch import decide_dispatch
    assert decide_dispatch("ret en typo").get("dispatch") is False


def test_decide_dispatch_complex_dispatches() -> None:
    from core.services.agent_dispatch import decide_dispatch
    task = "Implementer sektion 16 kryptering og workspace_crypto og tests og migration"
    assert decide_dispatch(task)["dispatch"] is True


def test_decide_dispatch_force() -> None:
    from core.services.agent_dispatch import decide_dispatch
    assert decide_dispatch("x", force=True)["dispatch"] is True
    assert decide_dispatch("implementer en stor feature og refaktor og migrer", force=False)["dispatch"] is False


def test_plan_dispatch_roles_and_executors() -> None:
    from core.services.agent_dispatch import plan_dispatch
    plan = plan_dispatch("byg X", executor_count=3)
    roles = [p["role"] for p in plan]
    assert roles.count("executor") == 3
    assert roles[0] == "researcher" and roles[-1] == "synthesizer"
    assert all("goal" in p and "parallel" in p for p in plan)


def test_skill_scan_gate_blocks() -> None:
    from core.services.agent_dispatch import dispatch_code_mode_task
    res = dispatch_code_mode_task("implementer feature og refaktor og migrer",
                                  skill_contents=["os.system('rm -rf /')"])
    assert res["ok"] is False and res["reason"] == "skill_scan_blocked"
    assert res["scan"]["blocked"]


def test_dispatch_dry_run_does_not_spawn() -> None:
    from core.services.agent_dispatch import dispatch_code_mode_task
    res = dispatch_code_mode_task("implementer stor feature og refaktor og migrer modul")
    assert res["ok"] is True and res["mode"] == "dispatch"
    assert res["dry_run"] is True and res["spawned"] == []
    assert res["plan"]


def test_dispatch_fanout_capped_by_recursion_guard(monkeypatch) -> None:
    # recursion_guard: a pathological plan is truncated to the fan-out ceiling
    # instead of spawning an unbounded number of children.
    import core.services.agent_dispatch as ad
    from core.services import recursion_guard as rg
    big_plan = [{"role": "executor", "goal": f"g{i}", "max_turns": 1} for i in range(25)]
    monkeypatch.setattr(ad, "plan_dispatch", lambda task, executor_count=2: big_plan)
    res = ad.dispatch_code_mode_task("implementer stor feature og refaktor og migrer modul")
    assert res["mode"] == "dispatch"
    assert len(res["plan"]) == rg.effective_max_fanout()   # truncated to cap (default 8)


def test_dispatch_inline_short_circuits() -> None:
    from core.services.agent_dispatch import dispatch_code_mode_task
    res = dispatch_code_mode_task("ret typo", inline=True)
    assert res["mode"] == "inline"


def test_clean_skills_allow_dispatch() -> None:
    from core.services.agent_dispatch import dispatch_code_mode_task
    res = dispatch_code_mode_task("implementer feature og refaktor og byg tests",
                                  skill_contents=["def f():\n    return 1"])
    assert res["ok"] is True


def test_agent_quota_blocks_over_limit(isolated_runtime, tmp_path, monkeypatch) -> None:
    # §21.7: plus-bruger har 2 agent-dispatches/dag; 3. blokeres.
    monkeypatch.setattr("core.runtime.config.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("core.runtime.config.SETTINGS_FILE", tmp_path / "runtime.json")
    from core.identity.users import add_user
    add_user(discord_id="d-mikkel", name="Mikkel", role="member", workspace="mikkel")
    from core.services.agent_dispatch import dispatch_code_mode_task
    task = "implementer feature og refaktor og migrer modul"
    assert dispatch_code_mode_task(task, user_id="d-mikkel")["ok"] is True
    assert dispatch_code_mode_task(task, user_id="d-mikkel")["ok"] is True
    blocked = dispatch_code_mode_task(task, user_id="d-mikkel")
    assert blocked["ok"] is False and blocked["reason"] == "quota_exceeded"
