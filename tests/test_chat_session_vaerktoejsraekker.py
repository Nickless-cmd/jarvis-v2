"""Værktøjs-rækker i en hentet samtale bærer deres KVITTERING, ikke outputtet.

Målt 20/9-2026 på Bjørns aktive samtale (2.683 beskeder): serveren sendte
21,5 MB, hvoraf 8,4 MB var værktøjs-rækkernes output. I databasen fylder de
samme rækker 1,3 MB — forskellen opstod ved hver hentning, fordi rækken kun
gemmer «[tool_result:<id>]» og serveren så slog outputtet op i
tool_result_store og lagde det ind i svaret.

Det blev læst af INGEN:
  - desk filtrerer rollen fra (`role === 'user' || role === 'assistant'`),
  - mobilen tegner kun rækkens korte tekst (`m.content`),
  - eksporten springer alt andet end user/assistant over.

Værktøjslinjerne på skærmen kommer fra assistent-beskedens EGNE blokke, og de
røres ikke her.
"""
from __future__ import annotations

import json

import pytest

from core.services.chat_sessions import (
    TOOL_RESULT_GRAENSE,
    append_chat_message,
    create_chat_session,
    get_chat_session,
    get_message_tool_result,
)
from core.services.tool_result_store import save_tool_result


def _ny_session(titel: str) -> str:
    s = create_chat_session(title=titel)
    return str(s.get("session_id") or s.get("id"))


def _raekke(sid: str, rolle: str) -> dict:
    session = get_chat_session(sid)
    assert session is not None
    traeffere = [m for m in session["messages"] if m["role"] == rolle]
    assert traeffere, f"ingen {rolle}-række"
    return traeffere[0]


@pytest.fixture
def session_med_vaerktoej(isolated_runtime):
    sid = _ny_session("vaerktoej")
    output = "LINJE\n" * 4000  # ~24.000 tegn, som et rigtigt bash-output
    result_id = save_tool_result("bash", {"command": "ls"}, output)
    append_chat_message(
        session_id=sid, role="tool", content=f"[tool_result:{result_id}]",
    )
    return sid, result_id, output


def test_outputtet_foelger_IKKE_med_raekken(session_med_vaerktoej):
    sid, _, output = session_med_vaerktoej
    raekke = _raekke(sid, "tool")
    sendt = json.dumps(raekke, ensure_ascii=False)
    assert output[:200] not in sendt, "hele værktøjs-outputtet blev sendt med igen"
    assert len(sendt) < 1000, f"rækken fylder {len(sendt)} tegn — kvitteringen er ~40"


def test_REFERENCEN_bevares_saa_outputtet_kan_hentes(session_med_vaerktoej):
    """Uden referencen ville outputtet være utilgængeligt for en klient der
    vil vise det — så var det at skære, ikke at spare. Den står i rækkens
    tekst, som mobilen i forvejen tegner."""
    sid, result_id, _ = session_med_vaerktoej
    raekke = _raekke(sid, "tool")
    assert result_id in str(raekke["content"])


def test_assistentens_EGNE_blokke_er_urørte(isolated_runtime):
    """Det er dem skærmen tegner værktøjslinjerne fra. Ville de blive trimmet
    her, ville Bjørn miste indhold han faktisk ser."""
    sid = _ny_session("assistent")
    blok = {
        "type": "tool_result", "tool_use_id": "call_1", "status": "done",
        "content": "resultatet som skærmen viser", "is_error": False,
    }
    append_chat_message(
        session_id=sid, role="assistant", content="svar",
        content_json=json.dumps([{"type": "text", "text": "svar"}, blok]),
    )
    raekke = _raekke(sid, "assistant")
    assert blok in raekke["content_json"]


def test_raekkens_egen_tekst_er_urørt(isolated_runtime):
    """Mobilen tegner `m.content` — kvitteringslinjen med sit korte uddrag.
    Den må ikke blive tom, for så stod der en tom værktøjslinje på telefonen."""
    sid = _ny_session("gammel")
    append_chat_message(session_id=sid, role="tool", content="et kort svar fra et vaerktoej")
    raekke = _raekke(sid, "tool")
    assert "et kort svar fra et vaerktoej" in raekke["content"]
    # Blokken ville være en ordret kopi af teksten ovenfor — 1,3 MB dobbelt
    # pr. hentning i Bjørns samtale. Den udelades.
    assert raekke["content_json"] == []


# ── Lange resultater i assistentens egne blokke ────────────────────────────

def _assistent_med_resultat(indhold: str, tool_use_id: str = "call_1") -> tuple[str, str]:
    sid = _ny_session("lange")
    gemt = append_chat_message(
        session_id=sid, role="assistant", content="svar",
        content_json=json.dumps([
            {"type": "tool_use", "id": tool_use_id, "name": "bash", "input": {}},
            {"type": "tool_result", "tool_use_id": tool_use_id, "status": "done",
             "content": indhold, "is_error": False},
        ]),
    )
    return sid, str(gemt["id"])


def test_langt_tekstresultat_afkortes_og_siger_det(isolated_runtime):
    langt = "x" * 9000
    sid, _ = _assistent_med_resultat(langt)
    blok = [b for b in _raekke(sid, "assistant")["content_json"]
            if b.get("type") == "tool_result"][0]
    assert len(blok["content"]) == TOOL_RESULT_GRAENSE
    assert blok["truncated"] is True
    assert blok["total_chars"] == 9000


def test_JSON_resultat_afkortes_ALDRIG(isolated_runtime):
    """Klienten parser resultatet for at tegne «+N −M» og sammendraget. Et
    afkortet JSON-dokument kan ikke parses, og så ville tallene forsvinde fra
    linjen — netop den fejl vi har lavet før med felt-navne."""
    stort = json.dumps({"linjer_tilfoejet": 42, "linjer_fjernet": 7, "diff": "y" * 9000})
    sid, _ = _assistent_med_resultat(stort)
    blok = [b for b in _raekke(sid, "assistant")["content_json"]
            if b.get("type") == "tool_result"][0]
    assert blok["content"] == stort
    assert "truncated" not in blok
    assert json.loads(blok["content"])["linjer_tilfoejet"] == 42


def test_kort_resultat_staar_helt(isolated_runtime):
    sid, _ = _assistent_med_resultat("kort svar")
    blok = [b for b in _raekke(sid, "assistant")["content_json"]
            if b.get("type") == "tool_result"][0]
    assert blok["content"] == "kort svar"
    assert "truncated" not in blok


def test_resten_kan_hentes_bagefter(isolated_runtime):
    """Ellers var det at skære, ikke at udskyde."""
    langt = "linje\n" * 3000
    _, mid = _assistent_med_resultat(langt, tool_use_id="call_9")
    assert get_message_tool_result(mid, "call_9") == langt
    assert get_message_tool_result(mid, "findes-ikke") is None
    assert get_message_tool_result("ukendt-besked", "call_9") is None
