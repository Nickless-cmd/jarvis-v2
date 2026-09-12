"""Den fulde tankestrøm må kun forlade serveren, når nogen beder om den.

Målt 12/9-2026: `_with_thinking_block` sender bevidst kun HALEN (de sidste
4.000 tegn), fordi `get_chat_session` sender HELE sessionen ved hvert poll.
Da 14 kompakterings-markører engang blev sendt rå med, voksede svaret til
17,94 MB — den fejl må fuld tænkning ikke gentage.

Bjørns valg (12/9-2026): standarden er ChatGPT-agtig (kun halen), og HELE
strømmen er et tilvalg for den avancerede bruger. `get_message_reasoning` er
den dovne vej til resten: ÉN besked, kun når nogen folder linjen ud.
"""
from __future__ import annotations

import types

import pytest


@pytest.fixture()
def _session_med_taenkning(isolated_runtime):
    """En assistent-besked hvis ræsonnering er LÆNGERE end halen."""
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sess = create_chat_session(title="taenkning")
    sid = str(sess.get("session_id") or sess.get("id"))
    # 9.600 tegn — mere end halen på 4.000, så testen kan se forskel.
    lang = ("raesonnement " * 800).strip()
    msg = append_chat_message(
        session_id=sid,
        role="assistant",
        content="svaret",
        reasoning_content=lang,
    )
    return str(msg.get("message_id") or msg.get("id")), lang


def test_fuld_taenkning_hentes_for_én_besked(_session_med_taenkning):
    """Resten af strømmen er der — den venter bare på at nogen spørger."""
    from core.services.chat_sessions import get_message_reasoning

    mid, lang = _session_med_taenkning
    assert get_message_reasoning(mid) == lang
    assert len(lang) > 4000, "forudsætning: ræsonneringen er længere end halen"


def test_ukendt_besked_giver_none(_session_med_taenkning):
    """None er «findes ikke» — kalderen svarer 404. Ikke en tom streng."""
    from core.services.chat_sessions import get_message_reasoning

    assert get_message_reasoning("findes-ikke-xyz") is None


def test_tomt_id_giver_none():
    from core.services.chat_sessions import get_message_reasoning

    assert get_message_reasoning("") is None
    assert get_message_reasoning("   ") is None


def test_besked_uden_taenkning_giver_tom_streng(isolated_runtime):
    """Tom streng er et GYLDIGT svar: beskeden findes, modellen tænkte ikke.

    Det må ikke forveksles med None (findes ikke) — ellers ville klienten vise
    en 404 for en helt almindelig besked.
    """
    from core.services.chat_sessions import (
        append_chat_message, create_chat_session, get_message_reasoning,
    )

    sess = create_chat_session(title="uden taenkning")
    sid = str(sess.get("session_id") or sess.get("id"))
    msg = append_chat_message(session_id=sid, role="assistant", content="bare et svar")
    mid = str(msg.get("message_id") or msg.get("id"))
    assert get_message_reasoning(mid) == ""


def test_blokken_baerer_kun_halen():
    """Session-pollingen må IKKE bære hele ræsonneringen — kun halen.

    Det er den grænse `get_message_reasoning` findes for at omgå dovent. Fjerner
    man klipningen her, vokser hvert eneste session-poll med titusindvis af tegn
    pr. tur — præcis den fejl de rå kompakterings-markører lavede.
    """
    from core.services.visible_runs_outcomes import _with_thinking_block

    lang = "x" * 9000
    run = types.SimpleNamespace(run_id="r-uden-maaling")
    blokke = _with_thinking_block([], run, lang)
    assert len(blokke) == 1
    assert blokke[0]["text"] == lang[-4000:]
    assert len(blokke[0]["text"]) == 4000
