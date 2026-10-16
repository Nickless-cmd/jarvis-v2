"""Runde-resultater → ToolResult. Udskilt fra visible_runs.py 18/9-2026."""
from __future__ import annotations

import json

from core.services.visible_followup_results import med_react_nudge, to_followup_results


def _kald(*navne: str) -> list[dict]:
    return [{"id": f"c{i}", "name": n} for i, n in enumerate(navne)]


def test_status_foelger_med() -> None:
    r = to_followup_results(_kald("bash"), [{"tool_name": "bash", "status": "error", "result_text": "x"}], {})
    assert r[0].status == "error"


def test_et_kald_der_aldrig_blev_koert_er_ikke_lykkedes() -> None:
    # Loftet for vaerktoejskald i en runde naaet: kaldet fik intet resultat.
    r = to_followup_results(_kald("bash", "read_file"), [{"tool_name": "bash", "status": "ok", "result_text": "ok"}], {})
    assert r[1].status == "error"
    assert "not executed" in r[1].content


def test_tomt_output_er_ikke_en_fejl() -> None:
    r = to_followup_results(_kald("bash"), [{"tool_name": "bash", "status": "ok", "result_text": ""}], {})
    assert r[0].status == "ok"
    assert "no output" in r[0].content


def test_opsloeste_tekster_vinder() -> None:
    r = to_followup_results(_kald("bash"), [{"tool_name": "bash", "status": "ok", "result_text": "raa"}], {0: "opsloest"})
    assert r[0].content.startswith("opsloest")


def test_data_laget_er_rent_og_nudgen_ligger_kun_i_prompt_kopien() -> None:
    """Nudgen er en INSTRUKS til modellen — den maa ikke persisteres.

    Maalt 16/10-2026: nudgen blev skrevet ind i den gemte turs
    `tool_result.content` (besked 198525, position 2630). En JSON-streng med
    nudgen haeftet paa er UGYLDIG JSON, saa enhver laeser der parser blokken
    fejlede — mobilens spoergsmaals-kort døde, og tre klienter kompenserede
    hver for sig med samme regex. Kilden skal vaere ren.
    """
    raa = to_followup_results(
        _kald("a", "b"),
        [{"tool_name": "a", "status": "ok", "result_text": "1"},
         {"tool_name": "b", "status": "error", "result_text": "2"}], {})
    # Data-laget: rent, ingen nudge nogen steder.
    assert "⟳" not in raa[0].content
    assert "⟳" not in raa[1].content
    # Prompt-kopien: nudgen paa det SIDSTE, og kun der.
    kopi = med_react_nudge(raa)
    assert "⟳" not in kopi[0].content
    assert "⟳" in kopi[1].content
    # Omskrivningen af det sidste resultat maa ikke tabe udfaldet.
    assert kopi[1].status == "error"
    # Den raa liste er urørt — kopien skriver ikke i den.
    assert raa[1].content == "2"


def test_et_json_resultat_er_stadig_gyldig_json_efter_data_laget() -> None:
    """Symptomet der udloeste fixet, som test.

    Spoergsmaals-kortet i mobilen døde, fordi `tool_result.content` var en
    JSON-streng med nudgen haeftet paa. Efter fixet skal data-laget levere
    den urørt — saa enhver laeser kan parse den.
    """
    payload = json.dumps(
        {"kind": "pause_and_ask", "question": "Hvilken?", "options": ["a", "b"]}
    )
    raa = to_followup_results(
        _kald("pause_and_ask"),
        [{"tool_name": "pause_and_ask", "status": "ok", "result_text": payload}],
        {},
    )
    # Kaster hvis nudgen ligger i data-laget.
    assert json.loads(raa[0].content)["kind"] == "pause_and_ask"


def test_billede_kun_fra_et_dict() -> None:
    r = to_followup_results(_kald("se"), [{"tool_name": "se", "status": "ok", "result_text": "x",
                                           "result": {"image_data_url": "data:image/png;base64,AA"}}], {})
    assert r[0].image_data_url.startswith("data:image")
    # Et resultat der er en streng kastede foer.
    r = to_followup_results(_kald("se"), [{"tool_name": "se", "status": "ok", "result_text": "x", "result": "tekst"}], {})
    assert r[0].image_data_url == ""
