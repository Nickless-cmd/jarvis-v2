"""agent_runtime_base: hvilke vaerktoejer en spawnet agent faktisk faar.

Et fantomvaerktoej — et navn i politikken der ikke findes i handler-dict'en —
er vaerre end slet ingen vaerktoejer: agenten kalder det, faar «Unknown tool»,
og rapporterer et selvsikkert falsk negativ som om den havde ledt.
"""


# ── Fantomvaerktoejer (6/9-2026) ─────────────────────────────────────────

def test_ingen_policy_annoncerer_ukendte_vaerktoejer():
    """`grep`/`glob` stod i read-only-politikken uden at findes.

    Agenten kaldte grep, fik «Unknown tool», og svarede «ingen forekomster,
    Confidence: Hoej» om en fil der laa der. Et fantomvaerktoej er vaerre end
    ingen: agenten tror den har ledt.
    """
    from core.services.agent_runtime_base import _TOOL_POLICY_SETS, tools_for_policy
    from core.tools.simple_tools import _TOOL_HANDLERS
    for politik in _TOOL_POLICY_SETS:
        for navn in tools_for_policy(politik):
            assert navn in _TOOL_HANDLERS, f"{politik} → {navn}"


def test_vaernet_dropper_et_fantom(monkeypatch, caplog):
    import logging

    from core.services import agent_runtime_base as arb
    monkeypatch.setitem(arb._TOOL_POLICY_SETS, "proeve", ["read_file", "ikke_et_vaerktoej"])
    with caplog.at_level(logging.ERROR):
        ud = arb.tools_for_policy("proeve")
    assert ud == ["read_file"]
    assert "ikke_et_vaerktoej" in caplog.text


def test_undersoegende_agent_kan_soege_i_indhold_og_navne():
    """Uden begge kan den ikke besvare «hvad haandterer X»."""
    from core.services.agent_runtime_base import tools_for_policy
    t = set(tools_for_policy("read-only-runtime"))
    assert "search" in t and "find_files" in t


def test_workstation_policy_er_strengt_laesekun():
    from core.services.agent_runtime_base import tools_for_policy
    assert set(tools_for_policy("read-only-workstation")) == {
        "operator_read_file", "operator_glob", "operator_grep", "operator_list_dir",
    }


def test_workstation_agent_stempler_operator_kald_med_desk_kontekst(monkeypatch):
    import json
    from core.services import agent_runtime_base as arb
    import core.tools.simple_tools as simple_tools
    monkeypatch.setattr(arb, "get_agent_registry_entry", lambda _agent_id: {
        "context_json": json.dumps({
            "execution_target": "workstation", "workspace_root": "/home/bjorn/project",
            "user_id": "bjorn", "session_id": "desk-session",
        }),
    })
    captured = {}
    def execute_tool(name, arguments):
        captured.update({"name": name, "arguments": arguments})
        return {"status": "ok", "result": "content"}
    monkeypatch.setattr(simple_tools, "execute_tool", execute_tool)
    result = arb._execute_agent_tool_call({"function": {
        "name": "operator_read_file",
        "arguments": json.dumps({"path": "/home/bjorn/project/README.md"}),
    }}, agent_id="agent-1")
    assert json.loads(result)["status"] == "ok"
    assert captured == {"name": "operator_read_file", "arguments": {
        "path": "/home/bjorn/project/README.md",
        "_runtime_user_id": "bjorn", "_runtime_session_id": "desk-session",
        "_operator_workspace_root": "/home/bjorn/project",
    }}
