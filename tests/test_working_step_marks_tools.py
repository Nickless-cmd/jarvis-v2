"""`working_step` baerer TO slags ting — og klienten skal kunne se forskel."""
import inspect

from core.services import visible_runs, visible_tool_exec


def test_aegte_vaerktoejskald_er_MAERKET():
    # Uden maerket maa klienten gaette paa at action != "thinking", og det
    # holder kun indtil nogen tilfoejer et tredje livstegn med et andet navn.
    kilde = inspect.getsource(visible_tool_exec)
    assert '"er_vaerktoej": True' in kilde


def test_livstegn_er_IKKE_maerket():
    # «Thinking via …» og «Taenker videre · runde N». De faar aldrig et
    # tool_use der kan rydde dem; bliver de til kort, hober de sig op.
    kilde = inspect.getsource(visible_runs)
    for linje in kilde.splitlines():
        if '"action": "thinking"' in linje:
            break
    else:
        raise AssertionError("fandt ingen thinking-working_step at kontrollere")
    assert "er_vaerktoej" not in kilde or kilde.count('"er_vaerktoej"') == 0


def test_maerket_staar_paa_SAMME_haendelse_som_navnet():
    # Et flag i en anden haendelse end den klienten laeser, er intet flag.
    kilde = inspect.getsource(visible_tool_exec)
    i = kilde.index('"action": _tc_name')
    j = kilde.index('"er_vaerktoej": True', i)
    # Samme dict-literal: der maa ikke ligge et nyt yield imellem.
    assert "yield _sse(" not in kilde[i:j]
