"""Trin 3: Smith standser handlingen i realtid og tvinger et nyt valg.

Bjørn 7/9-2026: trin 3 skal tvinge adfærdsændring NU og **må aldrig cutte et
run**. Før dette kunne trin 3 ikke engang tale: den stående ordres `match_key`
(en frase) blev sammenlignet med prefilterens fem faste klassenavne, og en
frase kan aldrig være i det sæt. Ti ordrer oprettet, nul der kunne matche.

Testene her holder på de tre ting der gør et hold forsvarligt: **bash er
undtaget**, **loftet forhindrer en ring**, og **kun handlings-mønstre holdes**.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

_TRIN3 = {"patterns": {
    "seq:delete workspace memory line": {"rung": 3, "label": "delete workspace memory line"},
}}


def _kald(navn, argumenter=""):
    return {"function": {"name": navn, "arguments": argumenter}}


def _med_stige(state=_TRIN3, hold=0):
    return (
        patch("core.runtime.db_core.get_runtime_state_value", return_value=state),
        patch("core.services.shared_cache.get", return_value=hold),
        patch("core.services.shared_cache.set"),
    )


def test_et_trin3_moenster_holder_kaldet():
    from core.services.gate_kernel import Decision
    from core.services.smith_confrontation import smith_confront_on_action

    a, b, c = _med_stige()
    with a, b, c:
        v = smith_confront_on_action("jeg rydder lige op", {
            "tool_calls_this_run": [_kald("memory_delete_line")], "run_id": "r1"})
    assert v is not None
    assert v.decision is Decision.RED, "kun RED udløser hold-og-re-ræsonnér"
    assert "delete workspace memory line" in v.reason


def test_RED_er_praecis_det_der_holder_uden_at_afslutte_runnet():
    """Kontrakten mod visible_runs: RED + aktiv tømmer de ventende tool-kald,
    så modellen re-ræsonnerer. Den annullerer aldrig runnet."""
    from core.services.gate_kernel import Decision
    from core.services.reasoning_interceptor import InterceptOutcome, should_hold_tool_call

    assert should_hold_tool_call(InterceptOutcome(grade=Decision.RED, shadow=False)) is True
    assert should_hold_tool_call(InterceptOutcome(grade=Decision.YELLOW, shadow=False)) is False


# ---------------------------------------------------------------------------
# Bash er Bjørns vej udenom systemet. Den må Smith aldrig lukke.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("navn", [
    "bash_session", "operator_bash_session", "bash_session_close",
    "run_shell_command", "terminal_exec",
])
def test_bash_og_shell_holdes_ALDRIG(navn):
    from core.services.smith_confrontation import smith_confront_on_action

    stige = {"patterns": {"seq:bash session": {"rung": 3, "label": "bash session"}}}
    a, b, c = _med_stige(stige)
    with a, b, c:
        assert smith_confront_on_action("", {
            "tool_calls_this_run": [_kald(navn)], "run_id": "r1"}) is None


def test_fritagelsen_er_bred_med_vilje():
    """En fremtidig bash-variant skal være undtaget fra første dag."""
    from core.services.smith_confrontation import _er_fritaget

    for n in ("bash_session", "operator_bash_session", "my_new_bash_tool",
              "shell_run", "terminal_open"):
        assert _er_fritaget(n) is True
    for n in ("write_file", "memory_delete_line", "gmail_send"):
        assert _er_fritaget(n) is False


# ---------------------------------------------------------------------------
# Loftet. Uden det kunne han re-ræsonnere ind i det samme kald i ring, og
# runnet ville stå stille — hvilket i praksis ER at cutte det.
# ---------------------------------------------------------------------------

def test_loftet_slipper_kaldet_igennem_frem_for_at_koere_i_ring():
    from core.services.smith_confrontation import _MAX_HOLD, smith_confront_on_action

    a, b, c = _med_stige(hold=_MAX_HOLD)
    with a, b, c:
        assert smith_confront_on_action("", {
            "tool_calls_this_run": [_kald("memory_delete_line")], "run_id": "r1"}) is None


def test_uden_en_taeller_holder_vi_ikke():
    """Kan loftet ikke garanteres, er det sikrere at lade kaldet gå."""
    from core.services.smith_confrontation import smith_confront_on_action

    def eksploder(*a, **kw):
        raise RuntimeError("cache væk")

    with patch("core.runtime.db_core.get_runtime_state_value", return_value=_TRIN3), \
         patch("core.services.shared_cache.get", eksploder):
        assert smith_confront_on_action("", {
            "tool_calls_this_run": [_kald("memory_delete_line")], "run_id": "r1"}) is None


# ---------------------------------------------------------------------------
# Rækkevidde
# ---------------------------------------------------------------------------

def test_lavere_trin_holder_ikke():
    from core.services.smith_confrontation import smith_confront_on_action

    a, b, c = _med_stige({"patterns": {
        "seq:delete workspace memory line": {"rung": 2, "label": "delete workspace memory line"}}})
    with a, b, c:
        assert smith_confront_on_action("", {
            "tool_calls_this_run": [_kald("memory_delete_line")], "run_id": "r1"}) is None


def test_behaviour_moenstre_holdes_ikke():
    """«tomme løfter» er at love UDEN at kalde noget — der er intet kald at
    holde, og hollow_promise_guard dækker det allerede."""
    from core.services.smith_confrontation import smith_confront_on_action

    a, b, c = _med_stige({"patterns": {
        "behaviour:tomme løfter": {"rung": 3, "label": "tomme løfter"}}})
    with a, b, c:
        assert smith_confront_on_action("jeg gør det nu", {
            "tool_calls_this_run": [_kald("gmail_send")], "run_id": "r1"}) is None


def test_et_urelateret_kald_roeres_ikke():
    from core.services.smith_confrontation import smith_confront_on_action

    a, b, c = _med_stige()
    with a, b, c:
        assert smith_confront_on_action("", {
            "tool_calls_this_run": [_kald("read_file")], "run_id": "r1"}) is None


def test_detektoren_kaster_aldrig():
    from core.services.smith_confrontation import smith_confront_on_action

    def eksploder(*a, **kw):
        raise RuntimeError("stigen væk")

    with patch("core.runtime.db_core.get_runtime_state_value", eksploder):
        assert smith_confront_on_action("x", {"tool_calls_this_run": [_kald("y")]}) is None
    assert smith_confront_on_action("x", {}) is None


def test_detektoren_er_faktisk_koblet_ind_i_interceptoren():
    """Uden dette ville modulet være endnu et der er bygget og ikke kaldt."""
    import inspect

    import core.services.reasoning_interceptor as R

    assert "smith_confront_on_action" in inspect.getsource(R._run_detectors)


# ---------------------------------------------------------------------------
# Adfærds-nøglen nedgraderer holdet (8/9-2026)
#
# Nøglen fjerner OVERHEAD, aldrig dømmekraft — samme doktrin som
# decentraliserings-nøglerne. Smith detekterer stadig, taler stadig og skriver
# stadig sporet; han standser bare ikke kaldet.
# ---------------------------------------------------------------------------

def test_gyldig_noegle_nedgraderer_hold_til_advarsel():
    from core.services.gate_kernel import Decision
    from core.services.smith_confrontation import smith_confront_on_action

    a, b, c = _med_stige()
    with a, b, c, patch("core.services.central_keymaker.har_adfaerds_noegle",
                        return_value=True):
        v = smith_confront_on_action("", {
            "tool_calls_this_run": [_kald("memory_delete_line")], "run_id": "r1"})
    assert v is not None, "Smith skal stadig tale — nøglen fjerner ikke dømmekraften"
    assert v.decision is Decision.YELLOW, "YELLOW holder ikke kaldet"
    assert "nøgle" in v.reason


def test_uden_noegle_holdes_kaldet_som_foer():
    from core.services.gate_kernel import Decision
    from core.services.smith_confrontation import smith_confront_on_action

    a, b, c = _med_stige()
    with a, b, c, patch("core.services.central_keymaker.har_adfaerds_noegle",
                        return_value=False):
        v = smith_confront_on_action("", {
            "tool_calls_this_run": [_kald("memory_delete_line")], "run_id": "r1"})
    assert v.decision is Decision.RED


def test_et_fejlende_noegle_opslag_giver_INGEN_fritagelse():
    """Et opslags-problem må aldrig give ham en fritagelse han ikke har
    fortjent — så fail-closed på nøglen, hvilket her betyder: hold kaldet."""
    from core.services.smith_confrontation import _har_adfaerds_noegle

    def eksploder(*a, **kw):
        raise RuntimeError("keymaker væk")

    with patch("core.services.central_keymaker.har_adfaerds_noegle", eksploder):
        assert _har_adfaerds_noegle() is False
