"""«Midten mangler» — storen skal have hele resultatet (5/9-2026).

Målt før: 728 gemte tool-resultater havde et hul i midten; ét fra 5. september
manglede 131.200 af 143.770 tegn. Beskeden i samtalen lover «Use
read_tool_result with result_id=... to inspect the full output», men den
KLIPPEDE tekst var det eneste der nogensinde blev gemt — midten fandtes ingen
steder, heller ikke for read_tool_result.
"""
from __future__ import annotations

import types

import core.services.simple_tool_executor as STE
from core.services import tool_result_store as TRS
from core.tools.simple_tools import format_tool_result_for_model


def _fat_result():
    return {"status": "ok", "tools": [{"name": f"vaerktoej_{i}",
                                       "description": "beskrivelse " * 20} for i in range(400)]}


def test_the_conversation_gets_a_clipped_result():
    clipped = format_tool_result_for_model("load_more_tools", _fat_result())
    assert "udeladt i midten" in clipped
    assert len(clipped) < 20_000, "samtalen maa ikke oversvoemmes"


def test_the_same_call_can_yield_the_whole_thing():
    full = format_tool_result_for_model("load_more_tools", _fat_result(), clip=False)
    assert "udeladt i midten" not in full
    assert len(full) > 100_000
    assert "vaerktoej_0" in full and "vaerktoej_399" in full


def test_a_result_with_its_own_text_is_untouched_by_clip():
    for clip in (True, False):
        out = format_tool_result_for_model(
            "x", {"status": "ok", "text": "kort svar"}, clip=clip)
        assert out == "kort svar"


def test_the_executor_carries_both_versions(monkeypatch):
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result",
                        lambda **_kw: None, raising=False)
    ctrl = types.SimpleNamespace(seen_simple_tool_call_signatures=set(), trust_all=False)
    token = {"name": "load_more_tools", "arguments": {}, "signature": "sig", "soft_warn": ""}
    out = STE._finalize_call(token, _fat_result(), controller=ctrl,
                             exec_fmt=format_tool_result_for_model)
    assert "udeladt i midten" in out["result_text"]
    assert "udeladt i midten" not in out["result_text_full"]
    assert len(out["result_text_full"]) > len(out["result_text"]) * 5


def test_an_old_formatter_without_the_flag_still_works(monkeypatch):
    """Monkeypatchede formattere i andre tests maa ikke braekke eksekveringen."""
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result",
                        lambda **_kw: None, raising=False)
    ctrl = types.SimpleNamespace(seen_simple_tool_call_signatures=set(), trust_all=False)
    token = {"name": "x", "arguments": {}, "signature": "sig", "soft_warn": ""}
    out = STE._finalize_call(token, {"status": "ok"}, controller=ctrl,
                             exec_fmt=lambda _n, _r: "kun to argumenter")
    assert out["result_text"] == "kun to argumenter"
    assert out["result_text_full"] == "kun to argumenter"


def test_read_tool_result_now_returns_the_middle(tmp_path, monkeypatch):
    monkeypatch.setattr(TRS, "TOOL_RESULTS_DIR", tmp_path)
    full = format_tool_result_for_model("load_more_tools", _fat_result(), clip=False)
    rid = TRS.save_tool_result("load_more_tools", {}, full)
    record = TRS.get_tool_result(rid)
    assert record is not None
    assert "udeladt i midten" not in str(record["result"])
    assert "vaerktoej_200" in str(record["result"]), "midten skal vaere der"


def test_a_pathological_result_is_still_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(TRS, "TOOL_RESULTS_DIR", tmp_path)
    monkeypatch.setattr(TRS, "_MAX_STORED_CHARS", 5_000)
    rid = TRS.save_tool_result("x", {}, "linje\n" * 5_000)
    stored = str(TRS.get_tool_result(rid)["result"])
    assert len(stored) < 6_000 and "udeladt i midten" in stored
