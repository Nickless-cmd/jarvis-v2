"""The Task facade derives authority from fixed runtime profiles."""
from __future__ import annotations


def test_read_task_derives_every_authority_field(monkeypatch):
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("container", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    plan = task.derive(
        owner_user_id="bjorn", origin_session_id="session-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="A cited answer", prompt="Inspect the source",
        subagent_type="researcher", model="", run_in_background=True,
    )
    assert plan["target"] == "runtime-container"
    assert plan["budget_tokens"] == task._BUDGET_DEFAULT["researcher"] and plan["max_turns"] == 8
    assert plan["expected_result"] == "A cited answer"
    assert "bash" not in plan["allowed_tools"] and "write_file" not in plan["allowed_tools"]
    assert plan["mandate"]["granted_side_effect"] == "read"
    assert plan["mandate"]["original_side_effect"] == "worktree-write"
    assert plan["mandate"]["return_address"] == "agent-inbox:bjorn:session-1:run-1"


def test_chat_repo_gives_researcher_files_and_executor_a_worktree(monkeypatch):
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("repo", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    common = dict(
        owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="A real repository result", prompt="Do the repo task",
        model="", run_in_background=True,
    )

    researcher = task.derive(subagent_type="researcher", **common)
    executor = task.derive(subagent_type="executor", **common)

    assert {"read_file", "find_files", "search"} <= set(researcher["allowed_tools"])
    assert researcher["mandate"]["workspace_roots"] == ["/repo"]
    assert executor["writes"] is True and executor["workspace"] == "/repo"
    # Executoren får sin policies fulde sæt, ikke en håndholdt treer. Målt 10/11-2026:
    # `worktree-write` lovede elleve værktøjer mens facaden gav tre — den kunne ikke
    # engang læse en fil og måtte catte gennem wt_bash.
    assert {"wt_bash", "wt_write_file", "read_file", "search"} <= set(executor["allowed_tools"])
    assert "bash" not in executor["allowed_tools"]


def test_workstation_er_et_repo_naar_stien_faktisk_er_et(monkeypatch):
    """`workstation` manglede i kinds-saettet og blokerede hver executor fra Desk.

    Maalt 10/11-2026: sessionens workspace_kind er "workstation" med
    workspace_root = serverens eget repo. `derive()` afviste derfor ALLE
    executors med "executor kraever et lokalt repo-workspace" — selv om stien
    baade findes og har .git. Det var ikke en sikkerhedsgraense, det var et hul
    i en liste. `has_repo`-tjekket er det der afgoer, og det staar stadig.
    """
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("workstation", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    plan = task.derive(
        owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="Et repo-resultat", prompt="Byg det",
        subagent_type="executor", model="", run_in_background=True,
    )
    assert plan["writes"] is True and plan["workspace"] == "/repo"


def test_workstation_uden_repo_afvises_stadig(monkeypatch):
    """En member-workspace der peger paa en anden maskine findes ikke her — afvises."""
    import pytest

    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("workstation", "/findes-ikke"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: False)
    with pytest.raises(ValueError, match="git-repository"):
        task.derive(
            owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
            parent_agent_id="jarvis", description="Et repo-resultat", prompt="Byg det",
            subagent_type="executor", model="", run_in_background=True,
        )


def test_udeladt_type_er_ikke_en_port(monkeypatch):
    """Task uden subagent_type må ikke tvinge et valg.

    Målt 10/11-2026: parameteren var `required` i skemaet, så hvert eneste dispatch
    skulle vælge en rolle først — også når opgaven var en simpel læsning. Anthropic
    løser det modsatte: deres udeladte type får hele kataloget. Vi vælger den sikre
    side af samme mønt — udeladt type giver læseret, aldrig skriveret, fordi
    udledning kun må NEDGRADERE.
    """
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("repo", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    plan = task.derive(
        owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="Et svar", prompt="Undersøg kilden",
        subagent_type="", model="", run_in_background=True,
    )
    assert plan["writes"] is False
    assert plan["tool_policy"] == "read-only-runtime"
    assert "read_file" in plan["allowed_tools"]
    assert "wt_write_file" not in plan["allowed_tools"]


def test_ukendt_type_er_et_navn_ikke_en_port(monkeypatch):
    """Et rolle-navn systemet ikke kender må ikke afvises — men må aldrig give skriveret.

    Målt 10/11-2026: `explore` og `explorer` findes i `agent_registry` (5 kørsler),
    men stod i ingen af facadens lister, så `derive` kastede ValueError på navnet.
    Navnet er ikke en autoritet; kun læse/skrive er. Derfor: ukendt navn → læseret.
    """
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("repo", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    for navn in ("explore", "verification-cost", "en-helt-ny-rolle"):
        plan = task.derive(
            owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
            parent_agent_id="jarvis", description="Et svar", prompt="Undersøg kilden",
            subagent_type=navn, model="", run_in_background=True,
        )
        assert plan["role"] == navn, "navnet skal bevares, ikke erstattes"
        assert plan["writes"] is False, f"{navn} fik skriveret uden at være et bevidst valg"
        assert plan["tool_policy"] == "read-only-runtime"
        assert "wt_write_file" not in plan["allowed_tools"]


def test_task_skemaet_kraever_ikke_subagent_type():
    """Porten sad i skemaet, ikke kun i koden: `required` tvang et valg ved hvert kald."""
    from core.tools.agent_contract_tools import AGENT_CONTRACT_TOOL_DEFINITIONS

    task_def = next(d for d in AGENT_CONTRACT_TOOL_DEFINITIONS
                    if d["function"]["name"] == "Task")
    params = task_def["function"]["parameters"]
    assert "subagent_type" in params["properties"], "feltet skal stadig kunne angives"
    assert "subagent_type" not in params["required"], "det må ikke være et krav"


def _plan(task, monkeypatch, kind, budget=0):
    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("repo", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    return task.derive(
        owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="Et svar", prompt="Undersøg kilden",
        subagent_type=kind, model="", run_in_background=True, budget_tokens=budget,
    )


def test_budgettet_er_rollens_maalte_default(monkeypatch):
    """Budgettet må ikke være én literal for alle roller.

    Målt 10/11-2026: 8 af 30 agenter siden 1/11 døde af `budget exhausted`. En
    researcher der DØDE brugte 32.962 tokens hvor en der LYKKEDES brugte 19.302 —
    de døde var midt i mere arbejde, ikke dårligere. Median-forbruget for den
    læsende rolle er 12.961, altså 62 % over det gamle loft på 8.000.
    """
    from core.services import agent_task_facade as task

    # Hver rolle får sit eget, målte loft — ikke ét fælles tal.
    assert _plan(task, monkeypatch, "researcher")["budget_tokens"] == 60_000
    assert _plan(task, monkeypatch, "executor")["budget_tokens"] == 32_000
    for rolle in ("critic", "planner", "watcher"):
        assert _plan(task, monkeypatch, rolle)["budget_tokens"] == 16_000, rolle

    # Ingen rolle må falde tilbage til det gamle 8.000: det passede ingen af dem.
    for rolle in ("researcher", "executor", "critic", "planner", "watcher"):
        assert _plan(task, monkeypatch, rolle)["budget_tokens"] != 8_000, rolle


def test_ukendt_rolle_faar_fallback_budget_ikke_det_gamle_loft(monkeypatch):
    from core.services import agent_task_facade as task

    plan = _plan(task, monkeypatch, "en-helt-ny-rolle")
    assert plan["budget_tokens"] == task._BUDGET_FALLBACK
    assert plan["budget_tokens"] != 8_000


def test_eksplicit_budget_kan_saenke_men_ikke_haeve(monkeypatch):
    """Modellen må vælge sit eget budget — men et tag-loft skal fange en tastefejl."""
    from core.services import agent_task_facade as task

    assert _plan(task, monkeypatch, "researcher", 5_000)["budget_tokens"] == 5_000
    # Et forsoeg paa at HAEVE budgettet skal ikke virke: en graense en agent selv
    # kan haeve er ikke en graense. Kun saenkning er tilladt.
    assert _plan(task, monkeypatch, "researcher", 999_999_999)["budget_tokens"] == 60_000
    assert _plan(task, monkeypatch, "researcher", -5)["budget_tokens"] == 60_000, "negativ = udeladt"


def test_task_skemaet_tilbyder_budget_tokens():
    from core.tools.agent_contract_tools import AGENT_CONTRACT_TOOL_DEFINITIONS

    task_def = next(d for d in AGENT_CONTRACT_TOOL_DEFINITIONS
                    if d["function"]["name"] == "Task")
    params = task_def["function"]["parameters"]
    assert "budget_tokens" in params["properties"], "agenten skal kunne sætte sit eget budget"
    assert "budget_tokens" not in params["required"], "det skal være valgfrit"



def test_en_single_agent_faar_byte_identisk_hash_som_foer_team_felterne(monkeypatch):
    """Literalen er maalt paa koden FOER ``team_id``/``member_index`` blev indfoert.

    Genberegnede testen formlen selv, beviste den intet: den skal fange at ``canonical``
    aendrer sig. Laa team-felterne der ubetinget, fik hver enkelt-agent en ny ``idem`` og
    dermed et nyt ``mandate_id`` — og enhver replay af allerede accepteret arbejde braek.
    """
    import hashlib

    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("container", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    plan = task.derive(
        owner_user_id="bjorn", origin_session_id="session-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="desc", prompt="do the thing",
        subagent_type="researcher", model="", run_in_background=True,
    )
    assert plan["idempotency_key"] == "task-37cd37b548b3fd43e8cf53e4a49817f5"
    expected_mandate = "mnd-" + hashlib.sha256(plan["idempotency_key"].encode()).hexdigest()[:16]
    assert plan["mandate"]["mandate_id"] == expected_mandate


def test_to_team_medlemmer_deler_ikke_mandate_id(monkeypatch):
    """``mandate_id`` er PRIMARY KEY: to medlemmer af samme team maa ikke ramme samme raekke."""
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("container", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    common = dict(owner_user_id="bjorn", origin_session_id="session-1", parent_run_id="run-1",
                  parent_agent_id="jarvis", description="desc", prompt="do the thing",
                  subagent_type="researcher", model="", run_in_background=True)

    single = task.derive(**common)
    m1 = task.derive(**common, team_id="team-abc", member_index=1)
    m2 = task.derive(**common, team_id="team-abc", member_index=2)

    assert m1["idempotency_key"] != single["idempotency_key"], "et team-medlem er ikke den samme agent"
    assert m1["idempotency_key"] != m2["idempotency_key"]
    assert m1["mandate"]["mandate_id"] != m2["mandate"]["mandate_id"], "PRIMARY KEY kollision"
    assert task.derive(**common, team_id="team-abc", member_index=1)["idempotency_key"] == m1["idempotency_key"], \
        "samme medlem skal vaere idempotent"
