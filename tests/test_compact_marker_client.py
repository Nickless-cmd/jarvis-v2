"""Kompakterings-markøren må ikke nå en klient med sit rå indhold.

Målt 12/9-2026, Bjørns session: `compact_marker`-rækkens content ER hele den
serialiserede transcript, når summariser-modellen fejler og falder tilbage til
«Mechanical fallback» — 111.507 tegn. Prompt-stien ekskluderer markøren seks
steder (`role != 'compact_marker'`), men `get_chat_session` sendte den RÅT til
klienten. Mobilens MessageList havde ingen gren for rollen, så den faldt i
default og blev tegnet som en almindelig boble:

    [Bjørn] Ja og commit
    [tool:tool]
    [tool_result:tool-result-…]
    «Use read_tool_result with result_id=…»

Bjørn fandt den på sin telefon. Testene her holder grænsen: en kort summary
slipper igennem uændret, rå transcript gør ikke — hverken som tekst eller som
strukturerede blokke.
"""
from __future__ import annotations


def _session_med_marker(tekst: str) -> str:
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sess = create_chat_session(title="komprimeret")
    sid = str(sess.get("session_id") or sess.get("id"))
    append_chat_message(session_id=sid, role="user", content="hej")
    append_chat_message(session_id=sid, role="compact_marker", content=tekst)
    return sid


def _markoer(sid: str) -> dict:
    from core.services.chat_sessions import get_chat_session

    session = get_chat_session(sid)
    assert session is not None
    marker = [m for m in session["messages"] if m["role"] == "compact_marker"]
    assert len(marker) == 1, "markøren skal stadig være der — den er ikke slettet"
    return marker[0]


def test_raa_transcript_forlader_ikke_api(isolated_runtime):
    """Kernen: den rå transcript må ikke med ud til klienten."""
    raa = (
        "[Bjørn] Ja og commit\n"
        "[tool:tool]\n"
        "[tool_result:tool-result-5edcf6f3d4234f818d409fd06572898c]\n"
        "[read_file]: hemmeligt indhold\n" + "x" * 5000
    )
    marker = _markoer(_session_med_marker(raa))

    assert "hemmeligt indhold" not in marker["content"]
    assert "tool:tool" not in marker["content"]
    assert "[Bjørn]" not in marker["content"]
    # Markøren findes stadig — som én kort, ærlig linje.
    assert "komprimeret" in marker["content"].lower()


def test_ingen_blokke_bygget_af_den_raa_tekst(isolated_runtime):
    """Bagdøren: `content_json` rekonstrueres fra content, så trimmer man kun
    `content`, lækker transcripten som strukturerede blokke i stedet."""
    raa = "[read_file]: hemmeligt indhold\n" + "x" * 5000
    marker = _markoer(_session_med_marker(raa))
    assert marker["content_json"] == []


def test_kort_summary_slipper_uaendret_igennem(isolated_runtime):
    """En rigtig summary er kort. Den skal vises — ikke erstattes af en label."""
    kort = "Samtalen handlede om in-flight-spor og ejer-identitet."
    assert _markoer(_session_med_marker(kort))["content"] == kort


def test_graensen_gaelder_praecist(isolated_runtime):
    from core.services.chat_sessions import _COMPACT_MARKER_CLIENT_LIMIT

    praecis = "a" * _COMPACT_MARKER_CLIENT_LIMIT
    assert _markoer(_session_med_marker(praecis))["content"] == praecis

    over = "a" * (_COMPACT_MARKER_CLIENT_LIMIT + 1)
    assert _markoer(_session_med_marker(over))["content"] != over


def test_andre_roller_roeres_ikke(isolated_runtime):
    """Grænsen gælder KUN markøren. En lang assistent-tur er samtalen selv."""
    from core.services.chat_sessions import (
        append_chat_message, create_chat_session, get_chat_session,
    )

    sess = create_chat_session(title="almindelig")
    sid = str(sess.get("session_id") or sess.get("id"))
    lang = " ".join(["svar"] * 300)
    append_chat_message(session_id=sid, role="assistant", content=lang)

    session = get_chat_session(sid)
    assert session is not None
    svar = [m for m in session["messages"] if m["role"] == "assistant"]
    assert svar[0]["content"] == lang


def test_gemt_content_json_med_raa_transcript_laekker_ikke(isolated_runtime):
    """Den ægte bagdør — og hvorfor vagten er lastbærende.

    `store_compact_marker` skriver ingen `content_json`, så i dag rekonstrueres
    blokke fra teksten. Men kolonnen findes, og en række KAN have den sat (ældre
    klient, ledger-projektion, fremtidig skriver). Uden vagten ville
    `_content_json_for_row` returnere den gemte, rå struktur — og transcripten
    ville forlade API'et ad bagdøren, selv om `content` var trimmet.
    """
    import json

    from core.services.chat_sessions import append_chat_message, create_chat_session

    raa = "[read_file]: hemmeligt indhold\n" + "x" * 5000
    sess = create_chat_session(title="bagdoer")
    sid = str(sess.get("session_id") or sess.get("id"))
    append_chat_message(
        session_id=sid,
        role="compact_marker",
        content=raa,
        content_json=json.dumps([{"type": "text", "text": raa}]),
    )

    marker = _markoer(sid)
    assert marker["content_json"] == []
    assert "hemmeligt indhold" not in json.dumps(marker["content_json"])
