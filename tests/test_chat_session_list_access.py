"""Sessionslisten maa aldrig tilbyde en samtale adgangsgaten bagefter afviser."""
from __future__ import annotations

from core.services.chat_sessions import (
    append_chat_message,
    create_chat_session,
    list_chat_sessions,
)


MICHELLE = "1313522677369143429"
BJORN = "1246415163603816499"


def _session(title: str) -> str:
    return str(create_chat_session(title=title)["id"])


def test_listen_skjuler_en_samtale_der_senere_har_skiftet_ejer(isolated_runtime) -> None:
    """En enkelt gammel Michelle-række må ikke eksponere Bjørns samtale.

    Det er præcis kontrakten mellem listen og ``maa_tilgaa_session``: det der
    vises som trykbart, skal også kunne åbnes og skrives i.
    """
    fremmed = _session("fremmed")
    append_chat_message(
        session_id=fremmed, role="user", content="før", user_id=MICHELLE,
    )
    append_chat_message(
        session_id=fremmed, role="assistant", content="senere", user_id=BJORN,
    )

    ids = {str(row["id"]) for row in list_chat_sessions(user_id=MICHELLE)}

    assert fremmed not in ids


def test_listen_beholder_brugerens_egen_samtale(isolated_runtime) -> None:
    egen = _session("egen")
    append_chat_message(
        session_id=egen, role="user", content="hej", user_id=MICHELLE,
    )

    ids = {str(row["id"]) for row in list_chat_sessions(user_id=MICHELLE)}

    assert egen in ids
