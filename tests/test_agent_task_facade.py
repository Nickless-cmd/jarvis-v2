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
    assert plan["budget_tokens"] == 8000 and plan["max_turns"] == 8
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


def test_task_skemaet_kraever_ikke_subagent_type():
    """Porten sad i skemaet, ikke kun i koden: `required` tvang et valg ved hvert kald."""
    from core.tools.agent_contract_tools import AGENT_CONTRACT_TOOL_DEFINITIONS

    task_def = next(d for d in AGENT_CONTRACT_TOOL_DEFINITIONS
                    if d["function"]["name"] == "Task")
    params = task_def["function"]["parameters"]
    assert "subagent_type" in params["properties"], "feltet skal stadig kunne angives"
    assert "subagent_type" not in params["required"], "det må ikke være et krav"

