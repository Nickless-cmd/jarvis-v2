"""Udskilt fra visible_runs 7/9-2026 (Boy-Scout, filen var 7.352 linjer).

Testen holder to ting fast: at symbolerne stadig kan hentes fra visible_runs
(kaldere og ældre tests importerer dem derfra), og at prædikaterne — som kun
farver follow-up-beskeden — stadig genkender det de skal.
"""
from core.services import grounded_capability_followup as g
from core.services import visible_runs as vr


def test_symbolerne_kan_stadig_hentes_fra_visible_runs():
    for navn in (
        "_run_grounded_capability_followup",
        "_run_grounded_multi_capability_followup",
        "_build_grounded_capability_followup_message",
        "_build_grounded_multi_capability_followup_message",
        "_is_code_analysis_request",
        "_is_memory_commit_request",
    ):
        assert getattr(vr, navn) is getattr(g, navn), navn


def test_kodeanalyse_genkendes_paa_dansk_og_engelsk():
    assert g._is_code_analysis_request("lav en kodeanalyse af repoet")
    assert g._is_code_analysis_request("do a code analysis")
    assert not g._is_code_analysis_request("hvad er klokken")


def test_husk_dette_genkendes():
    assert g._is_memory_commit_request("husk dette til senere")
    assert g._is_memory_commit_request("remember that")
    assert not g._is_memory_commit_request("glem det hele")


def test_tomt_input_vaelter_ikke():
    assert g._is_code_analysis_request("") is False
    assert g._is_memory_commit_request(None) is False
