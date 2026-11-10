"""The Task facade derives authority from fixed runtime profiles."""
from __future__ import annotations

import pytest


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


# --- derive_team_id: samme bestilling -> samme team, ellers et nyt ---------------------

_A = {"role": "researcher", "task": "laes koden"}
_B = {"role": "executor", "task": "skriv testen"}


def _team(**override):
    from core.services import agent_task_facade as task

    base = dict(owner_user_id="bjorn", origin_session_id="session-1", parent_run_id="run-1",
                description="desc", prompt="do the thing", team_name="hold",
                members=[dict(_A), dict(_B)])
    base.update(override)
    return task.derive_team_id(**base)


def test_team_id_er_deterministisk():
    assert _team() == _team()


def test_team_id_har_praefiks_og_16_hex():
    import re

    assert re.fullmatch(r"team-[0-9a-f]{16}", _team())


def test_team_id_raekkefoelgen_betyder_noget():
    assert _team(members=[dict(_A), dict(_B)]) != _team(members=[dict(_B), dict(_A)])


@pytest.mark.parametrize("felt", ["owner_user_id", "origin_session_id", "parent_run_id",
                                  "description", "prompt", "team_name"])
def test_team_id_hvert_inputfelt_betyder_noget(felt):
    assert _team(**{felt: "andet"}) != _team()


@pytest.mark.parametrize("nogle", ["role", "task"])
def test_team_id_medlemmets_indhold_betyder_noget(nogle):
    aendret = dict(_B, **{nogle: "andet"})
    assert _team(members=[dict(_A), aendret]) != _team()


def test_team_id_ignorerer_ukendte_noegler_i_et_medlem():
    assert _team(members=[dict(_A, note="x"), dict(_B)]) == _team()


# --- Leverance 4: _member_type og derive_team -----------------------------------------

_M = [{"role": "researcher", "task": "laes koden"},
      {"role": "critic", "task": "provoker konklusionen"},
      {"role": "planner", "task": "foreslaa naeste skridt"}]


def _team_plan(task, monkeypatch, members, **override):
    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("container", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    base = dict(owner_user_id="bjorn", origin_session_id="session-1", parent_run_id="run-1",
                parent_agent_id="jarvis", description="desc", prompt="do the thing",
                model="", run_in_background=True)
    base.update(override)
    return task.derive_team(team={"name": "hold", "members": members}, **base)


def test_member_type_afviser_skriveret_men_tillader_laesende():
    from core.services import agent_task_facade as task

    assert task._member_type("") == "researcher", "udeladt type giver laeseret"
    for laesende in ("researcher", "critic", "planner", "watcher", "CRITIC"):
        assert task._member_type(laesende) == laesende.strip().lower()
    # Spaerringen ligger paa KIND, ikke paa navnet: alle skrivende navne OG deres
    # aliaser skal afvises, ellers er et medlem ét ord fra skriveret.
    for skrivende in ("executor", "builder", "coder", "code", "EXECUTOR", " executor "):
        with pytest.raises(ValueError, match="skriveret"):
            task._member_type(skrivende)


def test_derive_team_giver_hvert_medlem_sin_egen_plan(monkeypatch):
    from core.services import agent_task_facade as task

    plans = _team_plan(task, monkeypatch, _M)

    assert len(plans) == 3
    assert len({p["mandate"]["mandate_id"] for p in plans}) == 3, "PRIMARY KEY kollision"
    assert len({p["idempotency_key"] for p in plans}) == 3, "medlemmerne er ikke den samme agent"
    assert len({p["team_id"] for p in plans}) == 1, "de hoerer til det SAMME team"
    # Nul skriveret og nul fanout for hvert medlem — det er hele pointen med mandatet.
    for p in plans:
        assert (p["mandate"]["max_fanout"], p["mandate"]["max_depth"]) == (0, 0)
        assert p["mandate"]["granted_side_effect"] == "read"
        assert p["writes"] is False


def test_derive_team_afviser_forkert_antal_medlemmer(monkeypatch):
    from core.services import agent_task_facade as task

    for antal in (1, 7):
        members = [{"role": "researcher", "task": f"opgave {i}"} for i in range(antal)]
        with pytest.raises(ValueError, match="2-6"):
            _team_plan(task, monkeypatch, members)


def test_derive_team_afviser_to_medlemmer_med_samme_task(monkeypatch):
    from core.services import agent_task_facade as task

    with pytest.raises(ValueError, match="samme task"):
        _team_plan(task, monkeypatch, [{"role": "researcher", "task": "samme"},
                                       {"role": "critic", "task": "samme"}])


def test_derive_team_tillader_samme_role_med_forskellig_task(monkeypatch):
    from core.services import agent_task_facade as task

    assert len(_team_plan(task, monkeypatch, [{"role": "critic", "task": "a"},
                                              {"role": "critic", "task": "b"}])) == 2


def test_derive_team_afviser_tomt_team_navn(monkeypatch):
    from core.services import agent_task_facade as task

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("container", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    for navn in ("", "   "):
        with pytest.raises(ValueError, match="team.name"):
            task.derive_team(
                owner_user_id="bjorn", origin_session_id="session-1", parent_run_id="run-1",
                parent_agent_id="jarvis", description="desc", prompt="do the thing",
                team={"name": navn, "members": _M}, model="", run_in_background=True)


@pytest.mark.parametrize("hul", [{"role": "", "task": "x"}, {"role": "critic", "task": ""},
                                 {"task": "x"}, {"role": "critic"}])
def test_derive_team_afviser_medlem_uden_role_eller_task(monkeypatch, hul):
    """Fundet i review af Leverance 3.

    ``derive_team_id`` hasher ``role``+``task`` raat. Et manglende felt blev ``None``, saa
    to FORSKELLIGE bestillinger med huller kunne kollidere til samme ``team_id`` — og et
    retry ville ramme den forkerte raekke. Hullet afvises derfor foer hashen.
    """
    from core.services import agent_task_facade as task

    with pytest.raises(ValueError, match="mangler role eller task"):
        _team_plan(task, monkeypatch, [{"role": "researcher", "task": "ok"}, hul])


def test_derive_team_afviser_skrivende_medlem(monkeypatch):
    from core.services import agent_task_facade as task

    with pytest.raises(ValueError, match="skriveret"):
        _team_plan(task, monkeypatch, [{"role": "researcher", "task": "a"},
                                       {"role": "executor", "task": "b"}])


def test_derive_team_afviser_skrivende_type_paa_hele_teamet(monkeypatch):
    """§7.2: ``Task(subagent_type="executor", team=...)`` er et forsoeg paa at give
    medlemmerne skriveret ad bagdoeren — den afvises, ikke ignoreres."""
    from core.services import agent_task_facade as task

    with pytest.raises(ValueError, match="skriveret"):
        _team_plan(task, monkeypatch, _M, subagent_type="executor")
