"""Rækkens `user_id` skal med ud — det er den der skelner system fra menneske.

Bjørn 15/11-2026, to sætninger i træk:
  1. «Lad os fjerne bruger beskeden.»
  2. «Kun fjern bruger beskeden der skrives af systemet. Hvis brugeren selv
     skriver skal den blive stående.»

Rutinens opgave-linje (opgave/svar-parets første halvdel, skrevet af
`routine_session.append_run`) er en `user`-række som alle andre. Eneste
skelnen i data er `user_id`: systemet skriver tomt, et menneske skriver sit id.
Målt i den levende base samme dag: 169 system-rækker med tomt felt mod 3 med
Bjørns id.

Uden feltet i projektionen måtte fladen gætte ud fra indholdet — og så ville
hans EGEN besked forsvinde sammen med systemets.
"""
from __future__ import annotations

from core.services.chat_sessions import (
    append_chat_message,
    create_chat_session,
    get_chat_session,
)


def _ny_session(titel: str) -> str:
    s = create_chat_session(title=titel)
    return str(s.get("session_id") or s.get("id"))


def test_user_id_foelger_med_i_projektionen():
    """Systemets række har tomt felt, menneskets har et id — og begge kommer ud."""
    sid = _ny_session("Rutine · user_id")
    append_chat_message(session_id=sid, role="user", content="SYSTEM-OPGAVE: tjek vejret")
    append_chat_message(session_id=sid, role="user", content="MIN EGEN: igen?", user_id="bjorn")

    session = get_chat_session(sid)
    assert session is not None
    raekker = [m for m in session["messages"] if m["role"] == "user"]

    assert raekker[0]["user_id"] == "", "systemets opgave-linje skal have TOMT user_id"
    assert raekker[1]["user_id"] == "bjorn", "menneskets egen besked skal bære id'et"


def test_feltet_er_altid_til_stede_saa_fladen_ikke_skal_gætte():
    """Også assistent-rækker bærer feltet (tomt) — en manglende nøgle ville tvinge
    klienten til at skelne «findes ikke» fra «tomt», og det er præcis den slags
    gæt der gjorde at en ægte brugerbesked kunne forsvinde."""
    sid = _ny_session("Rutine · feltet findes")
    append_chat_message(session_id=sid, role="assistant", content="Svar fra rutinen")

    session = get_chat_session(sid)
    assert session is not None
    for m in session["messages"]:
        assert "user_id" in m, f"række uden user_id: {m['role']}"
        assert isinstance(m["user_id"], str)
