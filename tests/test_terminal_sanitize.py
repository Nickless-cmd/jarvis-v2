"""Terminal-styrekoder må ikke nå modellen.

Maalt 6/9: `printf "\\033[31m..."` gennem bash naaede den ORDRET. Farverne er
tokens uden mening for en model, og bare kontroltegn kan faa det den LAESER
til at afvige fra det et menneske SAA i terminalen.
"""
from core.services.terminal_sanitize import strip_terminal_codes as s


def test_farvekoder_fjernes():
    assert s("\x1b[31mROED\x1b[0m normal") == "ROED normal"


def test_osc_sekvens_fjernes():
    """OSC kan saette en vinduestitel — usynlig tekst i outputtet."""
    assert s("\x1b]0;titel\x07tekst") == "tekst"


def test_markoer_flytning_fjernes():
    assert s("\x1b[2J\x1b[Hryddet") == "ryddet"


def test_backspace_overtyping_fjernes():
    assert s("abc\x08d") == "abcd"


def test_linjeskift_og_tab_bevares():
    assert s("linje1\nlinje2\ttab") == "linje1\nlinje2\ttab"


def test_carriage_return_bevares_med_vilje():
    """\\r\\n er almindelige linjeskift; en fremdriftslinje ville smelte sammen."""
    assert s("a\rb") == "a\rb"
    assert s("linje\r\nnaeste") == "linje\r\nnaeste"


def test_ren_tekst_er_uroert():
    t = "helt almindelig tekst med æøå og 123"
    assert s(t) is t or s(t) == t


def test_tom_og_none_agtigt():
    assert s("") == ""


def test_hele_vejen_gennem_finalize():
    """Ét sted, ikke pr. vaerktoej: alt gaar gennem _finalize_call."""
    from core.services.simple_tool_executor import _finalize_call
    from core.tools.simple_tools import format_tool_result_for_model as fmt
    tok = {"name": "bash", "arguments": {}, "signature": "x", "soft_warn": ""}
    r = _finalize_call(tok, {"status": "ok", "text": "\x1b[32mGROEN\x1b[0m"},
                       controller=None, exec_fmt=fmt)
    assert "\x1b" not in r["result_text"]
    assert "GROEN" in r["result_text"]
    assert "\x1b" not in r["result_text_full"], "ogsaa den fulde tekst der gemmes"
