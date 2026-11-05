"""tool_result_format: udskilt fra simple_tools, samme adfaerd og samme navne."""
from __future__ import annotations

import pytest

NAMES = ("format_tool_result_for_model", "_verify_hint_for", "_signal_linjer", "_json_safe_default")


@pytest.mark.parametrize("name", NAMES)
def test_every_function_is_reexported_from_simple_tools(name):
    from core.tools import simple_tools, tool_result_format

    assert getattr(simple_tools, name) is getattr(tool_result_format, name)


def test_write_file_ok_gets_a_verify_hint_with_the_path_and_errors_get_none():
    from core.tools.tool_result_format import _verify_hint_for

    hint = _verify_hint_for("write_file", {"status": "ok", "path": "/x/y.py"})
    assert hint and "verify_file_contains(path='/x/y.py'" in hint
    assert _verify_hint_for("write_file", {"status": "error", "path": "/x/y.py"}) is None
    assert _verify_hint_for("bash", {"status": "ok"}) is None


def test_readback_replaces_the_verify_hint_text():
    from core.tools.tool_result_format import _verify_hint_for

    hint = _verify_hint_for("edit_file", {"status": "ok", "path": "/a", "readback": "..."})
    assert "Readback" in hint and "verify_file_contains" not in hint


def test_json_safe_default_never_raises_on_odd_objects():
    import json

    from core.tools.tool_result_format import _json_safe_default

    out = json.dumps({"a": object(), "b": {1, 2}}, default=_json_safe_default)
    assert isinstance(out, str) and out.startswith("{")


# ── `detail`-faldbacken (5/11-2026) ────────────────────────────────────────
#
# commit_attributed, commit_all_container og commit_all_workstation laegger
# deres fejlbesked i `detail` (git_actions.commit_paths_as_jarvis, seks
# steder). Formateringen laeste kun `error` og `text`, saa ALLE deres fejl —
# manglende repo, afvist hook, tom working tree — blev vist som «unknown
# error». Beskeden var der; den blev kastet vaek her.


def test_detail_bruges_som_fejlbesked_naar_error_og_text_mangler():
    """Den aegte git-fejl skal naa samtalen, ikke «unknown error».

    MUTATION: fjern `detail`-grenen -> beskeden bliver «unknown error» -> fejler.
    """
    from core.tools.tool_result_format import format_tool_result_for_model

    ud = format_tool_result_for_model(
        "commit_attributed",
        {"status": "error", "detail": "fatal: not a git repository"},
    )
    assert "fatal: not a git repository" in ud
    assert "unknown error" not in ud


def test_error_og_text_vinder_stadig_over_detail():
    """Faldback-raekkefoelgen er error -> text -> detail. Den maa ikke vendes.

    MUTATION: saet `detail` foerst -> de to assertions fejler.
    """
    from core.tools.tool_result_format import format_tool_result_for_model

    a = format_tool_result_for_model(
        "x", {"status": "error", "error": "aegte", "detail": "skygge"}
    )
    assert "aegte" in a and "skygge" not in a
    b = format_tool_result_for_model(
        "x", {"status": "error", "text": "tekst", "detail": "skygge"}
    )
    assert "tekst" in b and "skygge" not in b


def test_fallback_bevares_naar_intet_felt_findes():
    """Et helt tomt error-resultat skal stadig sige «unknown error».

    MUTATION: fjern `or "unknown error"` -> beskeden bliver tom -> fejler.
    """
    from core.tools.tool_result_format import format_tool_result_for_model

    assert "unknown error" in format_tool_result_for_model("x", {"status": "error"})


def test_detail_som_struktur_laekker_ikke_ind_i_beskeden():
    """Enkelte vaerktoejer laegger en dict i `detail` — den er ikke en fejlbesked.

    MUTATION: fjern `isinstance(_detalje, str)`-gaten -> `{'kode': 42}` staar i
    beskeden i stedet for «unknown error» -> fejler.
    """
    from core.tools.tool_result_format import format_tool_result_for_model

    ud = format_tool_result_for_model("x", {"status": "error", "detail": {"kode": 42}})
    assert "unknown error" in ud
    assert "42" not in ud
    tom = format_tool_result_for_model("x", {"status": "error", "detail": "   "})
    assert "unknown error" in tom
