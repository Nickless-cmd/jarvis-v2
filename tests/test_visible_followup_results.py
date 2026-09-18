"""Runde-resultater → ToolResult. Udskilt fra visible_runs.py 18/9-2026."""
from __future__ import annotations

from core.services.visible_followup_results import to_followup_results


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


def test_nudgen_rammer_kun_det_sidste_og_bevarer_status() -> None:
    r = to_followup_results(
        _kald("a", "b"),
        [{"tool_name": "a", "status": "ok", "result_text": "1"},
         {"tool_name": "b", "status": "error", "result_text": "2"}], {})
    assert "⟳" not in r[0].content
    assert "⟳" in r[1].content
    # Omskrivningen af det sidste resultat maa ikke tabe udfaldet.
    assert r[1].status == "error"


def test_billede_kun_fra_et_dict() -> None:
    r = to_followup_results(_kald("se"), [{"tool_name": "se", "status": "ok", "result_text": "x",
                                           "result": {"image_data_url": "data:image/png;base64,AA"}}], {})
    assert r[0].image_data_url.startswith("data:image")
    # Et resultat der er en streng kastede foer.
    r = to_followup_results(_kald("se"), [{"tool_name": "se", "status": "ok", "result_text": "x", "result": "tekst"}], {})
    assert r[0].image_data_url == ""
