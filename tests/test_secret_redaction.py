"""Hemmeligheder ud af PROMPTEN — men ikke ud af det han redigerer.

Alle noegler herunder er OPDIGTEDE og indeholder ordet EKSEMPEL, saa den der
senere auditerer .secrets.baseline kan se paa ét blik at de er ufarlige.

Den vigtigste test her er `test_redigerings_stien_er_uroert`. Renser man
tool-resultater, laeser Jarvis en konfigfil, faar masken tilbage og skriver
den tilbage ved naeste redigering — vaernet ville oedelaegge noeglerne i
stedet for at beskytte dem.
"""
import pytest

from core.services.secret_redaction import contains_secret, read_for_prompt, redact


@pytest.mark.parametrize("hemmelig", [
    "sk-EKSEMPELnoegle1234567890",
    "ghp_EKSEMPELtoken1234567890AB",
    "AKIAEKSEMPEL12345678",
    "xoxb-EKSEMPEL1234567890",
    "glpat-EKSEMPELnoegle1234",
])
def test_kendte_noegleformer_maskeres(hemmelig):
    ud = redact(f"her er den: {hemmelig} slut")
    assert hemmelig not in ud
    assert "slut" in ud, "resten af teksten skal overleve"


def test_tildeling_beholder_navnet_men_skjuler_vaerdien():
    """Man skal stadig kunne SE at der stod en nøgle — og hvilken slags."""
    ud = redact("api_key = EKSEMPELvaerdi1234567890")
    assert "api_key" in ud
    assert "EKSEMPELvaerdi1234567890" not in ud


def test_almindelige_tal_er_ikke_hemmeligheder():
    """Et vaern der raaber ved hvert tal laerer én at overse det."""
    for t in ("port: 8080", "token: 42", "timeout = 30", "version: 0.2.10"):
        assert redact(t) == t, t


def test_ren_tekst_er_uroert():
    t = "En helt normal dagbogsnote om arbejdet i dag, med æøå."
    assert redact(t) == t
    assert contains_secret(t) is False


def test_manglende_fil_giver_None_ikke_tom_streng(tmp_path):
    """Kaldere skelner paa `is None`; '' ville faa en manglende fil til at se tom ud."""
    assert read_for_prompt(str(tmp_path / "findes-ikke.md")) is None


def test_tom_fil_giver_tom_streng(tmp_path):
    p = tmp_path / "tom.md"; p.write_text("")
    assert read_for_prompt(str(p)) == ""


def test_noegle_i_workspace_fil_naar_ikke_prompten(tmp_path):
    p = tmp_path / "MEMORY.md"
    p.write_text("min note\napi_key: sk-EKSEMPELnoegle1234567890\nmere note")
    ud = read_for_prompt(str(p))
    assert "sk-EKSEMPELnoegle1234567890" not in ud
    assert "min note" in ud and "mere note" in ud


def test_redigerings_stien_er_UROERT(tmp_path):
    """Den delte laeser maa IKKE redigere — ellers skrives masken tilbage.

    Det er hele grunden til at der findes to funktioner med hver sit navn.
    """
    from core.services.workspace_crypto import read_text_for_path
    p = tmp_path / "config.json"
    hemmelig = 'api_key: sk-EKSEMPELnoegle1234567890'
    p.write_text(hemmelig)
    assert read_text_for_path(str(p)) == hemmelig, \
        "redigerings-laeseren skal give den AEGTE tekst tilbage"


def test_tool_resultater_roeres_heller_ikke():
    """Samme grund: han redigerer ud fra dem."""
    from core.services.simple_tool_executor import _finalize_call
    from core.tools.simple_tools import format_tool_result_for_model as fmt
    tok = {"name": "read_file", "arguments": {}, "signature": "x", "soft_warn": ""}
    r = _finalize_call(tok, {"status": "ok", "text": "api_key: sk-EKSEMPELnoegle1234567890"},
                       controller=None, exec_fmt=fmt)
    assert "sk-EKSEMPELnoegle1234567890" in r["result_text"]
