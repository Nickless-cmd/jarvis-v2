"""Forbundne apps skal åbne deres værktøjer dér hvor de bruges.

Fejlen (målt 7/9-2026): alle syv Google-connectors stod som **connected AND
enabled**, prompten fortalte ham

    «du HAR adgang til dem lige nu via dine værktøjer. Brug dem når det er
     relevant i stedet for at sige at du ikke kan»

— og scope-porten filtrerede hvert eneste af værktøjerne fra:

    chat    0 af 10
    code    0 af 10
    cowork  10 af 10

Appsne kører i **chat**. Han fik altså at vide at han havde adgang, havde ingen
værktøjer, og blev udtrykkeligt bedt om ikke at sige at han ikke kunne. Den
kombination inviterer til at han finder på noget.

Samme form som telefon-værktøjerne samme dag: registreret, handler til stede,
usynlig præcis dér hvor de skulle bruges.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

VAERKTOEJER = [
    "gmail_list", "gmail_send", "calendar_list_events", "calendar_create_event",
    "docs_read", "docs_append", "sheets_read", "sheets_write", "drive_search",
    "slides_read", "github_list_prs",
]

FORBUNDET = [
    {"id": "gmail", "connected": True, "enabled": True,
     "tools": ["gmail_list", "gmail_send"]},
    {"id": "google-calendar", "connected": True, "enabled": True,
     "tools": ["calendar_list_events"]},
]


def _med(connectors):
    return (
        patch("core.identity.workspace_context.current_user_id", return_value="u1"),
        patch("core.services.connectors.list_for_user", return_value=connectors),
    )


@pytest.mark.parametrize("scope", ["chat", "code"])
def test_forbundne_apps_aabner_deres_vaerktoejer(scope):
    """Det var netop chat og code der manglede dem."""
    from core.tools.tool_scoping import allowed_tool_names

    a, b = _med(FORBUNDET)
    with a, b:
        t = allowed_tool_names(role="owner", scope=scope, all_names=VAERKTOEJER)
    assert {"gmail_list", "gmail_send", "calendar_list_events"} <= t


def test_en_FRAKOBLET_app_aabner_ingenting():
    """Overfladen udvides ikke når intet er forbundet — samme princip som
    desk-broen og telefonen."""
    from core.tools.tool_scoping import allowed_tool_names

    a, b = _med([{"id": "notion", "connected": False, "enabled": True,
                  "tools": ["notion_read"]}])
    with a, b:
        t = allowed_tool_names(role="owner", scope="chat", all_names=VAERKTOEJER + ["notion_read"])
    assert "notion_read" not in t


def test_en_SLUKKET_app_aabner_ingenting():
    """`enabled=False` er brugerens eget valg og skal respekteres."""
    from core.tools.tool_scoping import allowed_tool_names

    a, b = _med([{"id": "gmail", "connected": True, "enabled": False,
                  "tools": ["gmail_list"]}])
    with a, b:
        t = allowed_tool_names(role="owner", scope="chat", all_names=VAERKTOEJER)
    assert "gmail_list" not in t


def test_uden_bruger_gives_der_intet():
    """Self-safe: ingen bruger → ingen udvidelse, ikke et crash."""
    from core.tools.tool_scoping import _forbundne_connector_vaerktoejer

    with patch("core.identity.workspace_context.current_user_id", return_value=""):
        assert _forbundne_connector_vaerktoejer() == frozenset()


def test_et_fejlende_opslag_vaelter_ikke_prompten():
    from core.tools.tool_scoping import _forbundne_connector_vaerktoejer

    def eksploder(*a, **kw):
        raise RuntimeError("connector-store nede")

    with patch("core.services.connectors.list_for_user", eksploder):
        assert _forbundne_connector_vaerktoejer() == frozenset()


def test_registret_er_den_ENE_sandhed():
    """Værktøjs-listen bor i connector-definitionen, ikke i en kopi i porten.

    Lå den to steder, ville en ny connector kunne blive forbundet uden at
    åbne noget — præcis den slags stille uenighed huset har en regel imod.
    """
    import core.services.connectors as C
    from core.tools.simple_tools import get_tool_definitions

    kendte = {(d.get("function") or d).get("name") for d in get_tool_definitions()}
    med_tools = [c for c in C._CATALOG if c.get("tools")]
    assert len(med_tools) >= 7, "connector-registret har mistet sine tool-lister"
    for c in med_tools:
        for t in c["tools"]:
            assert t in kendte, "%s peger på et værktøj der ikke findes: %s" % (c["id"], t)
