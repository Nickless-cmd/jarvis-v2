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
    """Intet vaerktoej her maa SKRIVE paa Bjoerns maskine.

    Saettet blev udvidet 5/10-2026 i `11f8d77cd` (Actor: codex, «fix(scout):
    require evidence and deliver results to inbox») med `web_search` og
    `web_fetch`, saa scouten kan hente de beviser den nu kraeves at have.
    Testen blev skrevet af samme forfatter i samme commit som policyen (9/9)
    og var en selv-konsistens-pin, ikke et selvstaendigt vaern — den blev blot
    ikke rettet med.

    Pinnet paa EGENSKABEN frem for paa en liste, saa den naeste udvidelse ikke
    fejler bare fordi den er en udvidelse: ingen `operator_*write`,
    `operator_bash` eller andet der kan aendre noget paa maskinen.
    """
    from core.services.agent_runtime_base import tools_for_policy
    vaerktoejer = set(tools_for_policy("read-only-workstation"))
    assert vaerktoejer >= {
        "operator_read_file", "operator_glob", "operator_grep", "operator_list_dir",
    }, "de fire laesende operator-vaerktoejer er selve policyen"
    forbudt = [v for v in vaerktoejer if v.startswith("operator_")
               and v not in {"operator_read_file", "operator_glob",
                             "operator_grep", "operator_list_dir"}]
    assert forbudt == [], f"ikke-laesende operator-vaerktoej i policyen: {forbudt}"
    assert "operator_bash" not in vaerktoejer
    assert not any("write" in v or "edit" in v or "delete" in v for v in vaerktoejer), \
        f"noget her kan skrive: {sorted(vaerktoejer)}"


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


# ── Kapabilitets-påstande (11/11-2026) ────────────────────────────────────
#
# Målt på en ægte kørsel: en researcher HAVDE web_search + web_fetch — begge i
# `_READ_ONLY_TOOLS`, begge i hendes `allowed_tools_json`, og
# `_build_agent_tools_payload` gav 10/10 med `MANGLER: []`. Hun svarede alligevel
# «jeg har ikke adgang til web_search/web_fetch». Hendes faktiske kald var
# `search` x2 og `find_files` x1: hun kaldte ALDRIG det værktøj hun påstod hun
# manglede. Udfaldet blev bogført som AGENT_INCOMPLETE — altså blev VORES
# manglende værn registreret som HENDES fejl.
#
# Værnet er en instruks, ikke en kode-gate: kun agenten ved om den prøvede.
# Derfor holder testen fast at teksten faktisk står i prompten — ellers kan den
# forsvinde i en refaktorering uden at nogen opdager det.

def test_prompten_kraever_at_man_proever_foer_man_paastaar_at_man_mangler_et_vaerktoej():
    from core.services.agent_runtime_base import _AGENT_VERIFY_RULE, _role_prompt
    tekst = _role_prompt("Du er researcher.", tools=True)
    assert "THIS INCLUDES YOUR OWN CAPABILITIES" in tekst
    assert "never report that you lack a tool without first" in tekst
    assert "only valid after a web_search call returned" in tekst
    # Den skal IKKE lække ind i roller uden værktøjer — dér er den meningsløs.
    uden = _role_prompt("Du er dommer.", tools=False)
    assert "THIS INCLUDES YOUR OWN CAPABILITIES" not in uden


def test_web_search_er_faktisk_i_den_policy_en_researcher_faar():
    """Påstanden «jeg har ikke web_search» skal være falsificerbar i koden."""
    from core.services.agent_runtime_base import (
        _build_agent_tools_payload,
        tools_for_policy,
    )
    policy = tools_for_policy("read-only-runtime")
    assert "web_search" in policy and "web_fetch" in policy
    payload = _build_agent_tools_payload(policy)
    navne = {((t.get("function") or {}).get("name") or "") for t in payload}
    assert {"web_search", "web_fetch"} <= navne, (
        f"payload mangler web-vaerktoejer: {sorted(navne)}"
    )
