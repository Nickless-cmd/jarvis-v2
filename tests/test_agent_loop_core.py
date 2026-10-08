"""C6a: agent_loop_core - ren loekkelogik med injiceret I/O, og in-process-bindingen."""
from __future__ import annotations

import ast
import inspect

import pytest

from core.services import agent_loop_core as core


class FakeIO:
    def __init__(self, replies, tool_out="ok"):
        self.replies = list(replies)
        self.tool_out = tool_out
        self.model_calls, self.tool_calls, self.after_tools, self.rounds = [], [], [], []

    def model(self, *, messages, tools, requires_tools, provider, model):
        self.model_calls.append({"messages": [dict(m) for m in messages], "tools": tools,
                                 "requires_tools": requires_tools})
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def tool(self, tc):
        self.tool_calls.append(tc["id"])
        return self.tool_out

    def after_tool(self, tc, out):
        self.after_tools.append((tc["id"], out))

    def after_round(self, rounds, tool_calls):
        self.rounds.append((rounds, [t["id"] for t in tool_calls]))


def _run(io, **kw):
    base = dict(prompt="P", tools_payload=[{"function": {"name": "t"}}], requires_tools=True,
                provider="p", model="m", scout=False, max_rounds=3, synthesis_directive="SLUT")
    base.update(kw)
    return core.run_tool_loop(io, **base)


def _tc(i):
    return {"id": f"c{i}", "function": {"name": "t", "arguments": "{}"}}


def _wt(i, name):
    return {"id": f"c{i}", "function": {"name": name, "arguments": "{}"}}


#: Skemaet en skrivende agent faar: shell i sandkassen + skrivevaerktoejet.
_WT_TOOLS = [{"function": {"name": "wt_bash"}}, {"function": {"name": "wt_write_file"}}]


def test_a_writing_agent_that_promises_instead_of_writing_is_nudged_once():
    """Den maalte fejl 8/10-2026, ord for ord: agenten laeste filen (ét wt_bash-kald), svarede
    "Filen har 161 linjer. Nu tilfoejer jeg kommentarlinjen" — og kaldte ALDRIG
    skrivevaerktoejet. Loefte stod i ANDEN saetning, saa praefiks-tjekket missede det, og
    loekken meldte completed med files=[] og diff_bytes=0."""
    io = FakeIO([{"text": "", "tool_calls": [_wt(1, "wt_bash")]},
                 {"text": "Filen har 161 linjer. Nu tilføjer jeg kommentarlinjen øverst."},
                 {"text": "", "tool_calls": [_wt(2, "wt_write_file")]},
                 {"text": "Kommentarlinjen er tilføjet."}])
    out = _run(io, tools_payload=_WT_TOOLS, max_rounds=5)
    assert out["rounds"] == 4 and out["total_tool_calls"] == 2
    assert io.model_calls[2]["messages"][-1]["content"].startswith("Du har ikke kaldt et værktøj")
    assert "incomplete" not in out                      # den rettede sig efter nudgen


def test_a_write_capable_agent_that_stops_without_writing_is_asked_once():
    """Ogsaa naar teksten ikke lover noget: en agent MED skrivevaerktoejer der slutter uden en
    eneste skrivning faar ét spoergsmaal i stedet for et stiltiende 'faerdig'."""
    io = FakeIO([{"text": "Jeg har undersøgt sagen."}, {"text": "Der var intet at rette."}])
    out = _run(io, tools_payload=_WT_TOOLS)
    assert out["rounds"] == 2 and out["final_text"] == "Der var intet at rette."
    assert "incomplete" not in out                      # den svarede - det var ikke et loefte


def test_an_agent_that_promises_twice_is_reported_incomplete_not_completed():
    """Nudgen blev givet, og svaret er STADIG et loefte. Kalderen skal kunne se forskel."""
    io = FakeIO([{"text": "Nu tilføjer jeg linjen."}, {"text": "Nu tilføjer jeg linjen."}])
    out = _run(io, tools_payload=_WT_TOOLS)
    assert out["rounds"] == 2 and out["incomplete"] is True


def test_an_agent_without_write_tools_is_not_judged_on_writing():
    """En laeseagent har intet at skrive med - den skal ikke nudges for ikke at have skrevet."""
    io = FakeIO([{"text": "Fund: X er defineret i y.py"}])
    out = _run(io)
    assert out["rounds"] == 1 and "incomplete" not in out


def test_module_imports_only_the_standard_library():
    """Den indlaeses i en sandbox hvor intet andet er monteret."""
    tree = ast.parse(inspect.getsource(core))
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods.add((n.module or "").split(".")[0])
    assert mods <= {"__future__", "logging", "time", "typing"}, mods


def test_a_plain_answer_ends_after_one_round():
    io = FakeIO([{"text": "svar", "input_tokens": 3, "output_tokens": 2, "cost_usd": 0.5}])
    out = _run(io)
    assert (out["final_text"], out["rounds"], out["total_tool_calls"], out["error_str"]) == ("svar", 1, 0, "")
    assert (out["total_input"], out["total_output"], out["total_cost"]) == (3, 2, 0.5)
    assert io.model_calls[0]["messages"] == [{"role": "user", "content": "P"}]


def test_tool_rounds_feed_results_back_and_report_each_call_and_round():
    io = FakeIO([{"text": "", "tool_calls": [_tc(1), _tc(2)], "input_tokens": 1},
                 {"text": "faerdig", "input_tokens": 1}], tool_out="RESULTAT")
    out = _run(io)
    assert out["final_text"] == "faerdig" and out["total_tool_calls"] == 2 and out["total_input"] == 2
    assert io.tool_calls == ["c1", "c2"] and io.after_tools == [("c1", "RESULTAT"), ("c2", "RESULTAT")]
    assert io.rounds == [(1, ["c1", "c2"])]
    second = io.model_calls[1]["messages"]
    assert [m["role"] for m in second] == ["user", "assistant", "tool", "tool"]
    assert second[2] == {"role": "tool", "tool_call_id": "c1", "content": "RESULTAT"}


def test_a_scout_gets_exactly_one_nudge_after_a_preamble_without_tools():
    io = FakeIO([{"text": "Jeg starter nu"}, {"text": "Jeg starter igen"}])
    out = _run(io, scout=True)
    assert out["rounds"] == 2 and out["final_text"] == "Jeg starter igen"
    assert io.model_calls[1]["messages"][-1]["content"].startswith("Du har endnu ikke leveret")
    io2 = FakeIO([{"text": "Jeg starter nu"}, {"text": "Her er svaret: 42"}])
    # 8/10-2026: her stod der "kun scouts nudges" — og det VAR fejlen. En agent uden for
    # scout-stien kunne svare med et loefte og blive meldt faerdig uden at have gjort noget.
    out2 = _run(io2, scout=False)
    assert out2["rounds"] == 2 and out2["final_text"] == "Her er svaret: 42"


def test_exhausting_the_round_budget_triggers_one_tool_free_synthesis():
    io = FakeIO([{"text": "", "tool_calls": [_tc(i)]} for i in range(3)] + [{"text": "  samlet svar  "}])
    out = _run(io, max_rounds=3)
    assert out["rounds"] == 3 and out["final_text"] == "samlet svar"
    last = io.model_calls[-1]
    assert last["tools"] == [] and last["requires_tools"] is False
    assert last["messages"][-1] == {"role": "user", "content": "SLUT"}


def test_a_failing_synthesis_degrades_to_the_text_before_it():
    io = FakeIO([{"text": "delvist", "tool_calls": [_tc(1)]}, RuntimeError("udbyder")])
    out = _run(io, max_rounds=1)
    assert out["final_text"] == "delvist" and out["error_str"] == ""


def test_a_model_exception_becomes_error_str_never_a_raise():
    io = FakeIO([RuntimeError("x" * 600)])
    out = _run(io)
    assert out["error_str"] == "x" * 400 and out["rounds"] == 1


def test_a_tool_exception_is_an_error_not_a_success():
    class Boom(FakeIO):
        def tool(self, tc):
            raise ValueError("vaerktoej braekkede")

    out = _run(Boom([{"text": "", "tool_calls": [_tc(1)]}]))
    assert out["error_str"] == "vaerktoej braekkede" and out["total_tool_calls"] == 0


# --- in-process-bindingen --------------------------------------------------------------------

@pytest.fixture
def base(isolated_runtime, monkeypatch):
    import core.services.agent_runtime_base as b

    replies = []

    class _F:
        def execute_with_role_or_fallback(self, **kw):
            r = replies.pop(0)
            if isinstance(r, Exception):
                raise r
            return r

    monkeypatch.setattr(b, "_facade", lambda: _F())
    monkeypatch.setattr(b, "_build_agent_tools_payload",
                        lambda allowed, **k: [{"type": "function", "function": {"name": "read_file"}}])
    return b, replies, monkeypatch


AGENT = {"agent_id": "a1", "role": "researcher", "tool_policy": "read-only-runtime",
         "provider": "p", "model": "m", "allowed_tools_json": '["read_file"]'}


def test_the_wrapper_still_returns_the_old_envelope_shape(base, monkeypatch):
    b, replies, monkeypatch = base
    monkeypatch.setattr(b, "_execute_agent_tool_call", lambda tc, agent_id: "fil-indhold")
    replies += [{"text": "", "tool_calls": [_tc(1)], "input_tokens": 5},
                {"text": "fandt det", "input_tokens": 7, "output_tokens": 3}]
    r = b._run_agent_tool_loop(agent=dict(AGENT), prompt="P", requires_tools=True, run_id="run-1")
    assert (r["text"], r["status"], r["tool_rounds"], r["input_tokens"], r["output_tokens"]) == (
        "fandt det", "completed", 2, 12, 3)
    assert (r["execution_mode"], r["source"], r["lane"], r["provider"], r["model"]) == (
        "role-primary-tool-loop", "agent-tools", "cheap", "p", "m")


def test_the_wrapper_maps_error_scout_and_empty_outcomes_to_the_old_statuses(base):
    b, replies, monkeypatch = base
    replies.append(RuntimeError("udbyder nede"))

    r = b._run_agent_tool_loop(agent=dict(AGENT), prompt="P", requires_tools=True, run_id="r")
    assert r["status"] == "failed"
    replies[:] = [{"text": "Jeg starter"}, {"text": "Jeg starter"}]
    r = b._run_agent_tool_loop(agent=dict(AGENT), prompt="P", requires_tools=True, run_id="r")
    assert r["status"] == "blocked"                                   # scout uden fund
    replies[:] = [{"text": "   "}]
    r = b._run_agent_tool_loop(agent={**AGENT, "role": "critic"}, prompt="P", requires_tools=True, run_id="r")
    assert r["status"] == "blocked"


def test_a_writing_agent_that_only_promises_is_blocked_not_completed(base):
    """Bindingen skal baere 'loefte uden handling' videre som blocked — ikke som completed.
    Maalt 8/10-2026: praecis den vej meldte en agent faerdig med files=[] og diff_bytes=0."""
    b, replies, monkeypatch = base
    monkeypatch.setattr(b, "_build_agent_tools_payload",
                        lambda allowed, **k: [{"type": "function", "function": {"name": "wt_write_file"}}])
    ag = {**AGENT, "role": "executor", "tool_policy": "worktree-write",
          "allowed_tools_json": '["wt_write_file"]'}
    replies += [{"text": "Nu tilføjer jeg kommentarlinjen."}, {"text": "Nu tilføjer jeg kommentarlinjen."}]
    r = b._run_agent_tool_loop(agent=ag, prompt="P", requires_tools=True, run_id="r")
    assert r["status"] == "blocked" and r["text"].startswith("Nu tilføjer jeg")


def test_a_started_tool_call_is_recorded_before_it_runs_and_finished_after(base):
    b, replies, monkeypatch = base
    from core.runtime.db_agent_runtime import get_agent_tool_call

    seen = {}

    def run_tool(tc, agent_id):
        seen["during"] = get_agent_tool_call("c1")
        return "klar"

    monkeypatch.setattr(b, "_execute_agent_tool_call", run_tool)
    replies += [{"text": "", "tool_calls": [_tc(1)]}, {"text": "slut"}]
    b._run_agent_tool_loop(agent=dict(AGENT), prompt="P", requires_tools=True, run_id="run-9")
    d = seen["during"]
    assert (d["status"], d["finished_at"], d["run_id"]) == ("running", "", "run-9") and d["started_at"]
    after = get_agent_tool_call("c1")
    assert (after["status"], after["result_preview"]) == ("ok", "klar") and after["finished_at"]
    assert after["started_at"] == d["started_at"]                      # startposten overskrives ikke


def test_an_interrupted_tool_call_stays_open_so_the_supervisor_sees_it(base):
    """Kobler C2: en vaerktoejskoersel der aldrig blev afsluttet maa vaere synlig som aaben."""
    b, replies, monkeypatch = base
    from core.runtime.db_agent_runtime import get_agent_tool_call

    def dies(tc, agent_id):
        raise SystemExit("proces doede")

    monkeypatch.setattr(b, "_execute_agent_tool_call", dies)
    replies += [{"text": "", "tool_calls": [_tc(1)]}]
    with pytest.raises(SystemExit):
        b._run_agent_tool_loop(agent=dict(AGENT), prompt="P", requires_tools=True, run_id="run-9")
    row = get_agent_tool_call("c1")
    assert row["status"] == "running" and row["started_at"] and not row["finished_at"]


# --- F4b: parkering og genoptagelse ------------------------------------------------------------------------

class ParkIO(FakeIO):
    """Parkerer paa et bestemt kald, indtil `allow` indeholder dets id."""

    def __init__(self, replies, park_on=("c2",), tool_out="ok"):
        super().__init__(replies, tool_out)
        self.park_on, self.allow = set(park_on), set()

    def tool(self, tc):
        if tc["id"] in self.park_on and tc["id"] not in self.allow:
            raise core.ApprovalPending(f"appr-{tc['id']}", tc["id"])
        return super().tool(tc)


def test_a_call_that_needs_approval_parks_the_loop_with_a_complete_checkpoint():
    io = ParkIO([{"text": "tænker", "tool_calls": [_tc(1), _tc(2), _tc(3)], "input_tokens": 4, "output_tokens": 1,
                  "cost_usd": 0.5}])
    out = _run(io)
    assert io.tool_calls == ["c1"] and out["total_tool_calls"] == 1 and out["error_str"] == ""
    p = out["parked"]
    assert (p["approval_id"], p["tool_call_id"]) == ("appr-c2", "c2")
    cp = p["checkpoint"]
    assert [m["role"] for m in cp["messages"]] == ["user", "assistant", "tool"]
    assert [c["id"] for c in cp["pending_calls"]] == ["c2", "c3"]
    assert [c["id"] for c in cp["round_calls"]] == ["c1", "c2", "c3"]
    assert (cp["rounds"], cp["total_input"], cp["total_cost"], cp["total_tool_calls"], cp["final_text"]) == (
        1, 4, 0.5, 1, "tænker")
    assert io.rounds == []                                              # runden er ikke faerdig
    assert len(io.model_calls) == 1                                       # intet nyt modelkald er sket


def test_resume_executes_the_pending_calls_then_continues_the_rounds_with_carried_totals():
    first = ParkIO([{"text": "tænker", "tool_calls": [_tc(1), _tc(2), _tc(3)], "input_tokens": 4}])
    cp = _run(first)["parked"]["checkpoint"]
    io = ParkIO([{"text": "alt klaret", "input_tokens": 6}], park_on=("c2",), tool_out="R")
    io.allow = {"c2"}
    out = _run(io, resume=cp)
    assert io.tool_calls == ["c2", "c3"] and io.after_tools == [("c2", "R"), ("c3", "R")]
    assert io.rounds == [(1, ["c1", "c2", "c3"])]
    assert (out["final_text"], out["rounds"], out["total_input"], out["total_tool_calls"]) == ("alt klaret", 2, 10, 3)
    sent = io.model_calls[0]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "tool", "tool", "tool"]
    assert [m["tool_call_id"] for m in sent if m["role"] == "tool"] == ["c1", "c2", "c3"]
    assert "parked" not in out


def test_a_resumed_loop_can_park_again_on_the_next_gated_call():
    first = ParkIO([{"text": "", "tool_calls": [_tc(1), _tc(2)]}], park_on=("c2", "c4"))
    cp = _run(first)["parked"]["checkpoint"]
    io = ParkIO([{"text": "", "tool_calls": [_tc(4)]}], park_on=("c2", "c4"))
    io.allow = {"c2"}
    out = _run(io, resume=cp)
    assert out["parked"]["approval_id"] == "appr-c4" and out["parked"]["checkpoint"]["rounds"] == 2


def test_the_round_budget_is_not_reset_by_a_resume():
    first = ParkIO([{"text": "", "tool_calls": [_tc(1)]}], park_on=("c1",))
    cp = _run(first, max_rounds=2)["parked"]["checkpoint"]
    io = ParkIO([{"text": "", "tool_calls": [_tc(5)]}, {"text": "syntese"}], park_on=())
    out = _run(io, resume=cp, max_rounds=2)
    assert out["rounds"] == 2 and out["final_text"] == "syntese"        # runde 1 (foer parkering) + runde 2, saa syntese
    assert io.model_calls[-1]["tools"] == [] and len(io.model_calls) == 2


def test_other_tool_errors_still_become_error_str_and_do_not_park():
    class Boom(FakeIO):
        def tool(self, tc):
            raise ValueError("almindelig fejl")

    out = _run(Boom([{"text": "", "tool_calls": [_tc(1)]}]))
    assert out["error_str"] == "almindelig fejl" and "parked" not in out
