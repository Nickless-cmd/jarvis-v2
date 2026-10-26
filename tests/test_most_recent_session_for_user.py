"""Vagter for `most_recent_session_id_for_user` — det bruger-scopede session-opslag.

Målt 26/10-2026: `most_recent_session_id()` har ingen `WHERE user_id`. Den tager
den nyeste session i HELE systemet. En rutine der skulle levere til «den sidst
aktive session» skrev derfor til en anden brugers session — Michelles
madopskrift-rutine ville lande i Bjørns.

Det var grunden til at rutine-leverancen blev gjort session-neutral med vilje
(`routine_delivery.py`: «result text is never copied into a chat»). Beslutningen
var rigtig; det der manglede var scopet, ikke en grund til at afvise sessionen.

Koblingen er `chat_messages.user_id` + `workspace_name` — IKKE
`chat_sessions.owner_user_id`, hvis id-format ikke matcher `users.user_id`.
"""
from __future__ import annotations

import pytest


def _session_for(user_id: str, titel: str) -> str:
    """Opret en session og giv den ÉN besked fra `user_id`."""
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sess = create_chat_session(title=titel)
    sid = str(sess.get("session_id") or sess.get("id"))
    append_chat_message(
        session_id=sid,
        role="user",
        content=f"hej fra {user_id}",
        user_id=user_id,
        workspace_name=user_id,
    )
    return sid


def test_scoped_opslag_ignorerer_andres_sessioner(isolated_runtime) -> None:
    """Den vigtigste vagt: to brugere, to sessioner — hver faar SIN.

    Uden scopet ville begge faa den nyeste, altsaa den samme. Det er praecis
    den fejl der gjorde leverancen session-neutral.
    """
    from core.services.chat_sessions import most_recent_session_id_for_user

    a = _session_for("bruger-a", "A's session")
    b = _session_for("bruger-b", "B's session")

    assert most_recent_session_id_for_user("bruger-a") == a
    assert most_recent_session_id_for_user("bruger-b") == b
    assert a != b


def test_ukendt_bruger_giver_tom_streng(isolated_runtime) -> None:
    """Ingen session → ''. Kalderen skal selv falde tilbage til inbox.

    En gaet paa en session her ville skrive til en fremmeds samtale.
    """
    from core.services.chat_sessions import most_recent_session_id_for_user

    _session_for("bruger-a", "A's session")
    assert most_recent_session_id_for_user("bruger-uden-session") == ""
    assert most_recent_session_id_for_user("") == ""


def test_global_variant_er_uaendret(isolated_runtime) -> None:
    """Den eksisterende funktion maa ikke aendre adfaerd — den har andre kallere.

    `smart_compact_tools` og `visible_inner_life` bruger den bevidst globalt.
    """
    from core.services.chat_sessions import (
        most_recent_session_id,
        most_recent_session_id_for_user,
    )

    a = _session_for("bruger-a", "A's session")
    b = _session_for("bruger-b", "B's session")

    # Global = den nyeste uanset ejer (b blev oprettet sidst).
    assert most_recent_session_id() == b
    # Scoped = hver sin.
    assert most_recent_session_id_for_user("bruger-a") == a


def test_scoped_opslag_ser_beskeder_ikke_owner_kolonnen(isolated_runtime) -> None:
    """Koblingen SKAL gaa gennem chat_messages.user_id.

    `chat_sessions.owner_user_id` baerer et andet id-format (numeriske id'er er
    Discord-id'er), saa et opslag paa den kolonne ville give nul raekker for
    alle rigtige brugere — og fejlen ville se ud som «brugeren har ingen
    session».
    """
    from core.services.chat_sessions import most_recent_session_id_for_user

    sid = _session_for("bruger-a", "A's session")
    assert most_recent_session_id_for_user("bruger-a") == sid


@pytest.mark.parametrize("tom", ["", "   ", None])
def test_tomt_bruger_id_giver_tom_streng(isolated_runtime, tom) -> None:
    """Et tomt id maa aldrig matche noget — ellers rammer det en vilkaarlig session."""
    from core.services.chat_sessions import most_recent_session_id_for_user

    _session_for("bruger-a", "A's session")
    assert most_recent_session_id_for_user(tom) == ""
