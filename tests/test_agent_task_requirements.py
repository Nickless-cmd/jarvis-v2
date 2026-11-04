"""Dispatch afviser en opgave der KRÆVER et værktøj agenten ikke har.

Målt 4/11-2026: fire executor-kørsler fik «Kald værktøjet `restart_self`» men kun
wt_bash/wt_write_file/agent_note. De blev accepteret, kørte, brændte tokens og
svarede at værktøjet ikke fandtes. De fire prompts herunder er de rigtige.
"""
from __future__ import annotations

import pytest

from core.services import agent_task_facade as task
from core.services.agent_task_requirements import ufuldstaendige_vaerktoejer

_KENDTE = frozenset({
    "restart_self", "read_file", "bash", "search", "web_search", "home_assistant",
    "wt_bash", "wt_write_file", "agent_note", "load_more_tools",
})
_EXECUTOR = ("wt_bash", "wt_write_file", "agent_note")

# De fire rigtige dispatches fra agent_runs (kun den del der afgør udfaldet).
_RIGTIGE_PROMPTS = [
    "Du skal kalde værktøjet `restart_self` med parametrene: defer_until_idle=true",
    "Kald værktøjet `restart_self` med præcis disse argumenter og rapportér det rå svar",
    "Kald værktøjet `restart_self` med præcis disse argumenter og rapportér det rå svar tilbage uændret:",
    "Kald værktøjet `restart_self` med præcis disse argumenter og rapportér det rå svar tilbage:",
]


@pytest.mark.parametrize("prompt", _RIGTIGE_PROMPTS)
def test_de_fire_rigtige_dispatches_afvises(prompt):
    assert ufuldstaendige_vaerktoejer(prompt, _EXECUTOR, _KENDTE) == ["restart_self"]


@pytest.mark.parametrize("prompt, forventet", [
    # Krav i anden form og sprog
    ("Run `home_assistant` with entity=light.kitchen", ["home_assistant"]),
    ("Brug værktøjet `home_assistant` til at tænde lyset", ["home_assistant"]),
    ("Udfør `restart_self` og rapportér", ["restart_self"]),
    ("Please call `restart_self` once", ["restart_self"]),
    # To krav, hver nævnt én gang, i fast rækkefølge
    ("Kald `home_assistant`, og kald `restart_self`", ["home_assistant", "restart_self"]),
    ("Kald `restart_self`. Kald `restart_self` igen.", ["restart_self"]),
])
def test_krav_i_andre_former_fanges(prompt, forventet):
    assert ufuldstaendige_vaerktoejer(prompt, _EXECUTOR, _KENDTE) == forventet


@pytest.mark.parametrize("prompt", [
    # Omtale er ikke krav: en executor der RETTER kode om et værktøj må ikke afvises.
    "Ret funktionen `read_file` i core/tools/file_tools.py så den håndterer tomme filer",
    "Skriv en test for `restart_self` i tests/test_restart_self.py",
    "Docstringen for `bash` er forældet; opdatér den",
    # Negation er ikke krav
    "Du skal ikke kalde `restart_self`",
    "Brug aldrig `restart_self` her, kun wt_bash",
    "Do not call `restart_self`",
    "Brug IKKE `force`",
    # Agentens EGNE værktøjer må gerne kaldes
    "Kald `wt_bash` med cd /work && ls",
    "Brug `agent_note` til at notere fundet",
    # Ikke et kendt værktøj: et filnavn, en variabel, en CLI-flag
    "Kør `pytest -q` og rapportér",
    "Kald `render_want_text` og vis resultatet",
    # Ingen backticks: bevidst ikke ramt (se beslutningsnotatet)
    "Kald restart_self og rapportér",
    "",
])
def test_omtale_negation_og_egne_vaerktoejer_afvises_ikke(prompt):
    assert ufuldstaendige_vaerktoejer(prompt, _EXECUTOR, _KENDTE) == []


def test_et_vaerktoej_agenten_har_er_ikke_ufuldstaendigt():
    """Regression: researcheren HAR read_file/search, så et krav derom er uændret ok."""
    laese = ("read_file", "search", "web_search", "agent_note")
    assert ufuldstaendige_vaerktoejer("Kald `read_file` på README.md", laese, _KENDTE) == []
    assert ufuldstaendige_vaerktoejer("Kald `bash` og rapportér", laese, _KENDTE) == ["bash"]


# --- Facaden: afvisningen sker FØR en assignment oprettes ------------------

def _derive(monkeypatch, *, prompt, subagent_type="executor"):
    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("repo", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    monkeypatch.setattr(task, "_kendte_vaerktoejer", lambda: _KENDTE)
    return task.derive(
        owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="En opgave", prompt=prompt,
        subagent_type=subagent_type, model="", run_in_background=True,
    )


def test_facaden_afviser_en_ufuldstaendig_executor(monkeypatch):
    with pytest.raises(ValueError) as exc:
        _derive(monkeypatch, prompt="Kald værktøjet `restart_self` med defer_until_idle=true")
    msg = str(exc.value)
    assert "restart_self" in msg and "wt_bash" in msg


def test_execute_giver_stabil_fejlform_og_opretter_ingen_assignment(monkeypatch):
    from core.services import agent_contract_service as service

    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("repo", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    monkeypatch.setattr(task, "_kendte_vaerktoejer", lambda: _KENDTE)
    kaldt = []
    monkeypatch.setattr(service, "dispatch_agent", lambda **kw: kaldt.append(kw) or {"status": "accepted"})
    result = task.execute(
        owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="Genstart", subagent_type="executor", model="",
        prompt="Kald værktøjet `restart_self` med defer_until_idle=true", run_in_background=True,
    )
    assert result["status"] == "error" and "restart_self" in str(result)
    assert kaldt == []


def test_facaden_lader_en_opgave_uden_krav_passere(monkeypatch):
    plan = _derive(monkeypatch, prompt="Ret funktionen `read_file` så den håndterer tomme filer")
    assert plan["allowed_tools"] == list(_EXECUTOR)


def test_facaden_afviser_ikke_hvis_registeret_ikke_kan_hentes(monkeypatch):
    """Vagten tilføjer kun en afvisning: kan registeret ikke læses, sker der ingenting nyt."""
    monkeypatch.setattr(task, "_session_scope", lambda owner, session: ("repo", "/repo"))
    monkeypatch.setattr(task.os.path, "exists", lambda path: path == "/repo/.git")
    monkeypatch.setattr(task, "_kendte_vaerktoejer", lambda: frozenset())
    plan = task.derive(
        owner_user_id="bjorn", origin_session_id="chat-1", parent_run_id="run-1",
        parent_agent_id="jarvis", description="x", prompt="Kald `restart_self`",
        subagent_type="executor", model="", run_in_background=True,
    )
    assert plan["allowed_tools"] == list(_EXECUTOR)
