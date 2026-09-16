"""Ejer-gaten paa de agent-ruter der GRIBER IND.

Fundet 16/9-2026 under oprydningen efter Codex' inspector-arbejde: Desk fik en
knap «Stop» paa hver koerende agent, og ruten bag den havde ingen gate
overhovedet. Provider-registret og resten af de handlende flader bruger
require_central_owner; de fem her gjorde ikke.

Det vigtige ved testen er BEGGE retninger. En gate der afviser alle er lige saa
oedelagt som ingen gate: runtimens egne kald kommer fra en unbound kontekst
(localhost, ingen token), og de skal stadig virke.
"""
import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.mission_control_agents as ruter


def _saet_rolle(monkeypatch, rolle: str, uid=None):
    # Samme greb som tests/test_central_auth.py bruger — gaten slaar BAADE paa
    # bearer-rollen og paa et DB-opslag, saa begge skal staa fast.
    monkeypatch.setattr("core.identity.workspace_context.current_role", lambda: rolle)
    monkeypatch.setattr("core.identity.workspace_context.current_user_id", lambda: uid or "")
    monkeypatch.setattr("core.identity.users.find_user_by_discord_id", lambda _id: None)


# Hver post er (funktion, argumenter) — kaldt som en klient ville kalde den.
INDGRIBENDE = [
    (ruter.mc_cancel_agent, ("agent-1", {"note": "stop"})),
    (ruter.mc_suspend_agent, ("agent-1", {"note": "pause"})),
    (ruter.mc_resume_agent, ("agent-1",)),
    (ruter.mc_expire_agent, ("agent-1", {"reason": "for gammel"})),
    (ruter.mc_message_agent, ("agent-1", {"content": "hej"})),
]


@pytest.mark.parametrize("funktion,argumenter", INDGRIBENDE,
                         ids=[f.__name__ for f, _ in INDGRIBENDE])
def test_medlem_kan_ikke_gribe_ind_i_en_agent(monkeypatch, funktion, argumenter):
    _saet_rolle(monkeypatch, "member", uid="medlem-1")
    kaldt = []
    for navn in ("cancel_agent", "suspend_agent", "resume_agent", "expire_agent",
                 "send_message_to_agent"):
        monkeypatch.setattr(ruter, navn, lambda *a, **k: kaldt.append(navn) or {})

    with pytest.raises(HTTPException) as fejl:
        funktion(*argumenter)
    assert fejl.value.status_code == 403
    # Gaten skal staa FOER handlingen — ikke efter.
    assert kaldt == []


@pytest.mark.parametrize("funktion,argumenter", INDGRIBENDE,
                         ids=[f.__name__ for f, _ in INDGRIBENDE])
def test_ejeren_slipper_igennem(monkeypatch, funktion, argumenter):
    _saet_rolle(monkeypatch, "owner", uid="bjorn")
    for navn in ("cancel_agent", "suspend_agent", "resume_agent", "expire_agent",
                 "send_message_to_agent"):
        monkeypatch.setattr(ruter, navn, lambda *a, **k: {"status": "ok"})
    assert funktion(*argumenter) == {"status": "ok"}


@pytest.mark.parametrize("funktion,argumenter", INDGRIBENDE,
                         ids=[f.__name__ for f, _ in INDGRIBENDE])
def test_runtimens_egne_kald_indefra_er_uroerte(monkeypatch, funktion, argumenter):
    """Unbound kontekst = localhost uden token. Den gate maa ikke lukke for den."""
    _saet_rolle(monkeypatch, "", uid=None)
    for navn in ("cancel_agent", "suspend_agent", "resume_agent", "expire_agent",
                 "send_message_to_agent"):
        monkeypatch.setattr(ruter, navn, lambda *a, **k: {"status": "ok"})
    assert funktion(*argumenter) == {"status": "ok"}


def test_laese_ruterne_er_IKKE_gatede(monkeypatch):
    """At SE puljen er ikke det samme som at gribe ind i den.

    Gates man laesningen med, forsvinder Agent Pool-fladen for alle andre end
    ejeren — og det var ikke det fundet handlede om.
    """
    _saet_rolle(monkeypatch, "member", uid="medlem-1")
    monkeypatch.setattr(ruter, "build_agent_detail_surface",
                        lambda _id: {"messages": [{"content": "hej"}]})
    svar = ruter.mc_agent_messages("agent-1")
    assert svar["messages"] == [{"content": "hej"}]
