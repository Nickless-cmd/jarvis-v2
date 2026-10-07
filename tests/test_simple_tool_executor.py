from core.services import simple_tool_executor as ste


def test_reexported_from_visible_runs():
    from core.services.visible_runs import _execute_simple_tool_calls as via_vr
    assert via_vr is ste._execute_simple_tool_calls


def test_basic_sequential_execution(monkeypatch):
    # No run_id → controller None → no dedup/cache state; pure pass-through.
    calls = [{"function": {"name": "read_file", "arguments": {"path": "/x"}}}]

    def fake_execute_tool(name, arguments):
        return {"status": "ok", "output": f"ran {name}"}

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", fake_execute_tool)
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda name, result: str(result.get("output") or ""))
    # Neutralise the commit-gate so the tool runs.
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **kw: type("CG", (), {"blocked": False, "soft_warn": "",
                                                     "reason": "", "gate_type": ""})())
    out = ste._execute_simple_tool_calls(calls, force=False)
    assert len(out) == 1
    assert out[0]["tool_name"] == "read_file"
    assert out[0]["status"] == "ok"
    assert out[0]["result_text"] == "ran read_file"


def test_file_call_records_before_and_after_for_message_undo(monkeypatch, tmp_path):
    from core.undo import message_edits as undo
    path = tmp_path / "file.txt"
    path.write_text("before")
    saved = {}
    monkeypatch.setattr(undo, "_load", lambda key: saved.get(key))
    monkeypatch.setattr(undo, "_save", lambda key, value: saved.__setitem__(key, value))
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **kw: type("CG", (), {"blocked": False, "soft_warn": "",
                                                     "reason": "", "gate_type": ""})())
    monkeypatch.setattr("core.services.agentic_tool_cache.get_cached_result", lambda *a, **kw: None)
    monkeypatch.setattr("core.tools.simple_tools.execute_tool",
                        lambda name, arguments: _write_for_test(path))
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda name, result, **kw: "ok")
    calls = [{"id": "call-1", "function": {"name": "write_file", "arguments": {"path": str(path)}}}]
    ste._execute_simple_tool_calls(calls, session_id="s1")
    assert saved[undo._key("s1", "call-1")]["before"]["sha"] != saved[undo._key("s1", "call-1")]["after"]["sha"]


def _write_for_test(path):
    path.write_text("after")
    return {"status": "ok"}


import contextvars
import time
from core.services import tool_concurrency


_SCOPE = contextvars.ContextVar("_test_scope", default="DEFAULT")


def _mk_calls(names):
    return [{"function": {"name": n, "arguments": {"i": i}}} for i, n in enumerate(names)]


def _patch_reads(monkeypatch, record=None, sleep_map=None):
    def fake_execute_tool(name, arguments):
        if sleep_map:
            time.sleep(sleep_map.get(arguments.get("i"), 0))
        if record is not None:
            record.append((name, arguments.get("i"), _SCOPE.get()))
        return {"status": "ok", "output": f"{name}:{arguments.get('i')}"}
    monkeypatch.setattr("core.tools.simple_tools.execute_tool", fake_execute_tool)
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda name, result: str(result.get("output") or ""))
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **kw: type("CG", (), {"blocked": False, "soft_warn": "",
                                                     "reason": "", "gate_type": ""})())
    monkeypatch.setattr("core.services.agentic_tool_cache.get_cached_result",
                        lambda name, arguments: None)
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result", lambda **kw: None)


def test_parallel_equals_sequential(monkeypatch):
    names = ["read_file", "search_memory", "list_dir"]
    _patch_reads(monkeypatch)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "off")
    seq = ste._execute_simple_tool_calls(_mk_calls(names))
    _patch_reads(monkeypatch)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    par = ste._execute_simple_tool_calls(_mk_calls(names))
    assert [r["result_text"] for r in seq] == [r["result_text"] for r in par]
    assert [r["tool_name"] for r in par] == names  # emission order preserved


def test_parallel_preserves_order_under_out_of_order_completion(monkeypatch):
    names = ["read_file", "search_memory", "list_dir"]
    # First call sleeps longest -> finishes last, but must still be index 0 in output.
    _patch_reads(monkeypatch, sleep_map={0: 0.15, 1: 0.05, 2: 0.0})
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    out = ste._execute_simple_tool_calls(_mk_calls(names))
    assert [r["result_text"] for r in out] == ["read_file:0", "search_memory:1", "list_dir:2"]


def test_parallel_propagates_contextvars_to_workers(monkeypatch):
    # SECURITY-CRITICAL: mode/role/tier gating reads ContextVars inside execute_tool.
    # A raw worker thread would see DEFAULT. Each task must run in a copied context.
    record: list = []
    _patch_reads(monkeypatch, record=record)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    token = _SCOPE.set("OWNER_SCOPE")
    try:
        ste._execute_simple_tool_calls(_mk_calls(["read_file", "search_memory"]))
    finally:
        _SCOPE.reset(token)
    observed = {scope for (_n, _i, scope) in record}
    assert observed == {"OWNER_SCOPE"}, f"worker context not propagated: {observed}"


# ── Indbakke-gaten i mutationspunktet (Opgave 4, 3/10-2026) ─────────────────

def test_indbakkens_trin_1_varsel_NAAR_tool_resultatet():
    """Det led der mangler oftest: koden er korrekt, ingen leverer den.

    Tælleren i `inbox_items` tæller «leverede påmindelser». Blev varslet
    beregnet i gaten og smidt væk her, ville trin 2 fyre på påmindelser der
    aldrig nåede modellen — en gate der straffer for noget der ikke blev sagt.
    Derfor måles DENNE grænse, ikke gatens interne svar.
    """
    from core.services import simple_tool_executor as ste
    token = {"name": "edit_file", "arguments": {"path": "x"},
             "signature": "sig-1", "soft_warn": "", "run_id": "visible-1",
             "inbox_varsel": "[SYSTEM NOTIFICATION - NOT USER INPUT]\n"
                             "1 post(er) venter i indbakken: wake-abc → kald `inbox`"}
    ud = ste._finalize_call(token, {"status": "ok"}, controller=None,
                            exec_fmt=lambda n, r: "FILEN BLEV SKREVET")
    tekst = str(ud.get("result_text") or "")
    assert "wake-abc" in tekst, "trin 1's paamindelse naaede ikke resultatet"
    assert "[SYSTEM NOTIFICATION - NOT USER INPUT]" in tekst
    # FORAN resultatet: en linje efter 112 kB jobs-output bliver aldrig laest.
    assert tekst.index("wake-abc") < tekst.index("FILEN BLEV SKREVET")


def test_uden_et_varsel_roeres_resultatet_IKKE():
    """Modprøven. Uden den kunne implementeringen tilføje en tom linje foran
    hvert eneste tool-resultat — og det ville ændre hver cache-nøgle."""
    from core.services import simple_tool_executor as ste
    token = {"name": "read_file", "arguments": {}, "signature": "s", 
             "soft_warn": "", "run_id": "", "inbox_varsel": ""}
    ud = ste._finalize_call(token, {"status": "ok"}, controller=None,
                            exec_fmt=lambda n, r: "INDHOLD")
    assert str(ud.get("result_text") or "") == "INDHOLD"


def test_en_blokeret_mutation_returneres_som_gate_blocked_med_post_id():
    """En blokering uden en adresse er en blokering man ikke kan rette."""
    from unittest.mock import patch
    from core.services import simple_tool_executor as ste
    with patch("core.services.inbox_gate.evaluer_inbox_mutation",
               return_value={"blokeret": True, "poster": ["wake-xyz"],
                             "varsel": "naegtet: wake-xyz"}):
        art, ud = ste._prepare_call(
            {"function": {"name": "edit_file",
                          "arguments": {"path": "x", "new_text": "y"}}},
            force=True, run_id="visible-1", session_id="s1",
            user_message="", controller=None, round_seen=set())
    assert art == "result"
    assert ud["status"] == "gate_blocked"
    assert ud["result"]["gate_type"] == "inbox_gate"
    assert ud["result"]["poster"] == ["wake-xyz"]
    assert "wake-xyz" in ud["result_text"]
