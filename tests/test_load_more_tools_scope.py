"""Scope-porten skal holde gennem `load_more_tools` (maalt 16/11-2026).

Hentet fra det virkelige flow: `load_more_tools` slog op i HELE kataloget og
returnerede schemas som scope-porten aldrig ville annoncere. Maalt i chat-scope
gav den `bash`, `write_file`, `operator_bash` og `edit_file` tilbage — alle fire
uden for chat-scopet — og de kunne derefter kaldes. Porten var altsaa formel,
ikke virkelig.

Testene her faelder i BEGGE retninger: porten skal afvise i chat, og legacy-vejen
(tomt scope) skal vaere byte-identisk med foer.
"""
from __future__ import annotations

import pytest

from core.tools.load_more_tools import _tool_load_more_tools
from core.tools.tool_scoping import (
    CODE_MODE_TOOLS_BASE,
    reset_tool_scope,
    set_tool_scope,
)

# Værktøjer der bevidst er UDEN for chat-scopet — de handler om at skrive, køre
# og styre maskiner. Hvis blot ét af dem kan hentes i chat, er porten brudt.
UDEN_FOR_CHAT = ["bash", "write_file", "edit_file", "operator_bash"]


@pytest.fixture
def i_chat_scope():
    token = set_tool_scope("chat")
    try:
        yield
    finally:
        reset_tool_scope(token)


def test_chat_scope_kan_ikke_hente_vaerktoejer_uden_for_scopet(i_chat_scope):
    out = _tool_load_more_tools({"names": UDEN_FOR_CHAT})

    hentede = list(out.get("added") or [])
    brud = [navn for navn in hentede if navn in UDEN_FOR_CHAT]

    assert not brud, (
        "load_more_tools hentede vaerktoejer som chat-scopet afviser: "
        f"{brud}. Porten er formel, ikke virkelig — de kan kaldes bagefter."
    )
    assert out["status"] == "error", (
        "naar intet kan hentes skal svaret sige det, ikke se ud som en succes"
    )
    assert "tool_definitions" not in out or not out["tool_definitions"]


def test_chat_scope_kan_stadig_hente_det_scopet_tillader(i_chat_scope):
    """Filtreringen maa ikke goere vaerktoejet ubrugeligt: dets formaal er
    katalogets lange hale — værktøjer scopet TILLADER, men pruneren ikke
    annoncerede."""
    out = _tool_load_more_tools({"names": ["recall"]})

    assert out["status"] == "ok"
    assert out["added"] == ["recall"]


def test_legacy_vej_uden_scope_er_uaendret():
    """Tomt scope = ubegraenset (legacy). Den vej skal ikke filtreres — ellers
    ville rettelsen lukke en doer som intet scope har lukket."""
    out = _tool_load_more_tools({"names": ["bash"]})

    assert out["status"] == "ok"
    assert out["added"] == ["bash"]


@pytest.mark.parametrize(
    "navn",
    ["web_search", "web_fetch", "recall", "search_memory", "remember_this",
     "load_more_tools"],
)
def test_code_scope_har_web_og_hukommelse(navn):
    """Maalt 16/11-2026: alle seks stod i chat-listen og ingen af dem i code.
    I code mode kunne jeg hverken soege paa nettet eller i mine egne minder.
    Scope-laasen (fe5aad1e7) gjorde hullet permanent, saa det skal lukkes."""
    assert navn in CODE_MODE_TOOLS_BASE, (
        f"{navn} mangler i CODE_MODE_TOOLS_BASE — i code mode findes "
        "vaerktoejet reelt ikke for modellen"
    )
