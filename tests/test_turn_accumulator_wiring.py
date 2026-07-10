"""Wiring-test for tur-niveau blok-akkumulatoren i visible_runs.

`_accumulate_turn_blocks` er en lokal closure inde i `_stream_visible_run` og
kan ikke importeres direkte uden at mocke hele streamet. Denne test dækker i
stedet AKKUMULATOR-KONTRAKTEN sort på hvidt: den normaliserede dict-form som
akkumulatoren producerer skal fødes rent gennem den (allerede testede,
importérbare) rene `_build_turn_blocks`. Vi verificerer begge tool-call-former
akkumulatoren håndterer (OpenAI-style `function.{name,arguments}` og flad
`name`/`input`) samt `_vf.ToolResult`-attribut-udtrækket.

Hvis akkumulatorens normalisering ændres, skal denne kontrakt opdateres bevidst.
"""
from core.services.visible_runs import _build_progress_blocks, _build_turn_blocks


class _FakeToolResult:
    """Efterligner _vf.ToolResult-attributterne akkumulatoren læser."""

    def __init__(self, tool_call_id: str, content: str) -> None:
        self.tool_call_id = tool_call_id
        self.content = content


def _normalize_call(tc: dict) -> dict:
    """Genskaber præcis akkumulatorens tool_call-normalisering."""
    fn = (tc.get("function") or {}) if isinstance(tc, dict) else {}
    return {
        "id": str((tc.get("id") if isinstance(tc, dict) else "") or ""),
        "name": str(
            fn.get("name")
            or (tc.get("name") if isinstance(tc, dict) else None)
            or "tool"
        ),
        "input": (
            fn.get("arguments")
            or (tc.get("input") if isinstance(tc, dict) else None)
            or {}
        ),
    }


def _normalize_result(r: object) -> dict:
    """Genskaber præcis akkumulatorens result-normalisering."""
    return {
        "tool_use_id": str(getattr(r, "tool_call_id", "") or ""),
        "status": "done",
        "content": str(getattr(r, "content", "") or ""),
        "is_error": False,
    }


def test_flat_tool_call_shape_flows_to_blocks():
    calls = [_normalize_call({"id": "c1", "name": "read_file", "input": {"path": "x"}})]
    results = [_normalize_result(_FakeToolResult("c1", "file contents"))]
    # interleave = den ægte stream-rækkefølge (Jarvis' fix): tool FØR svar-tekst,
    # så kortene ligger før svaret (Bjørn 10. jul), ikke samlet under det.
    blocks = _build_turn_blocks(
        text="hej", tool_calls=calls, tool_results=results,
        interleave=["tool", "text"],
    )
    # Filtrér progress (feature 4 appender ét progress-spor til sidst) — her
    # tester vi tool/tekst-rækkefølgen.
    non_prog = [b["type"] for b in blocks if b["type"] != "progress"]
    assert non_prog == ["tool_use", "tool_result", "text"]
    assert {"type": "text", "text": "hej"} in blocks
    use = next(b for b in blocks if b["type"] == "tool_use")
    assert use == {"type": "tool_use", "id": "c1", "name": "read_file", "input": {"path": "x"}}
    res = next(b for b in blocks if b["type"] == "tool_result")
    assert res["tool_use_id"] == "c1"
    assert res["content"] == "file contents"
    assert res["status"] == "done"
    assert res["is_error"] is False


def test_pretext_then_tools_then_answer_places_text_after_tools():
    """Regression (Bjørn 10. jul): reasoning-modeller streamer en kort præ-tekst
    FØR de kalder værktøjer og skriver det egentlige svar EFTER resultaterne, så
    interleave = ['text','tool','tool','text']. Vi har kun én samlet tekst-blob;
    lægges den ved FØRSTE markør hopper hele svaret op foran tool-kortene, som så
    lander i bunden. Den skal placeres ved SIDSTE 'text'-markør → tools før prosa."""
    calls = [
        _normalize_call({"id": "c1", "name": "bash", "input": {"command": "ps"}}),
        _normalize_call({"id": "c2", "name": "bash", "input": {"command": "top"}}),
    ]
    results = [
        _normalize_result(_FakeToolResult("c1", "ps output")),
        _normalize_result(_FakeToolResult("c2", "top output")),
    ]
    blocks = _build_turn_blocks(
        text="Godt set — billedet er anderledes: CPU 98% idle.",
        tool_calls=calls, tool_results=results,
        interleave=["text", "tool", "tool", "text"],
    )
    non_prog = [b["type"] for b in blocks if b["type"] != "progress"]
    assert non_prog == ["tool_use", "tool_result", "tool_use", "tool_result", "text"]
    # Præcis ét tekst-blok, og det er sidst blandt ikke-progress-blokke.
    text_blocks = [b for b in blocks if b["type"] == "text"]
    assert len(text_blocks) == 1
    assert text_blocks[0]["text"].startswith("Godt set")


def test_text_only_before_tool_stays_before_tool():
    """Kun-før-tool-tekst (ingen efterfølgende svar-tekst) skal BEVARE
    tekst-før-tool: last_text_idx == first → uændret ('Jeg kører X nu' → tool)."""
    calls = [_normalize_call({"id": "c1", "name": "bash", "input": {"command": "ls"}})]
    results = [_normalize_result(_FakeToolResult("c1", "ok"))]
    blocks = _build_turn_blocks(
        text="Jeg kører den nu.", tool_calls=calls, tool_results=results,
        interleave=["text", "tool"],
    )
    non_prog = [b["type"] for b in blocks if b["type"] != "progress"]
    assert non_prog == ["text", "tool_use", "tool_result"]


def test_openai_function_shape_flows_to_blocks():
    # arguments kan være en JSON-string — akkumulatoren lader den passere som-is.
    calls = [_normalize_call({
        "id": "c2",
        "function": {"name": "search", "arguments": '{"q": "cats"}'},
    })]
    results = [_normalize_result(_FakeToolResult("c2", "42 hits"))]
    blocks = _build_turn_blocks(text="", tool_calls=calls, tool_results=results)

    use = next(b for b in blocks if b["type"] == "tool_use")
    assert use["id"] == "c2"
    assert use["name"] == "search"
    assert use["input"] == '{"q": "cats"}'  # string bevaret, ikke parset/crashet
    res = next(b for b in blocks if b["type"] == "tool_result")
    assert res["tool_use_id"] == "c2"


def test_missing_name_defaults_to_tool():
    calls = [_normalize_call({"id": "c3", "input": {}})]
    blocks = _build_turn_blocks(text="", tool_calls=calls, tool_results=[])
    use = next(b for b in blocks if b["type"] == "tool_use")
    assert use["name"] == "tool"


def test_empty_turn_yields_falsy_blocks_for_or_none_guard():
    # Ingen tekst + ingen tools → tom liste → `... or None` giver None →
    # uændret tekst-only-adfærd i persist.
    blocks = _build_turn_blocks(text="", tool_calls=[], tool_results=[])
    assert blocks == []
    assert (blocks or None) is None


# ── FLAT progress-spor (spec 2026-07-09, FLAT v1) ───────────────────────────


def test_build_progress_blocks_one_per_tool_in_call_order():
    calls = [
        _normalize_call({"id": "c1", "name": "read_file", "input": {"path": "/a/foo.py"}}),
        _normalize_call({"id": "c2", "name": "bash", "input": {"command": "ls -la"}}),
    ]
    results = [
        _normalize_result(_FakeToolResult("c1", "contents")),
        _normalize_result(_FakeToolResult("c2", "listing")),
    ]
    prog = _build_progress_blocks(calls, results)

    assert [p["tool_use_id"] for p in prog] == ["c1", "c2"]  # kald-rækkefølge
    assert all(p["type"] == "progress" for p in prog)
    assert all(p["parent_tool_use_id"] is None for p in prog)  # FLAT v1
    assert all(p["status"] == "done" for p in prog)
    # message = _tool_label(name, input) — bærer narrationen live-working_step viste
    assert "foo.py" in prog[0]["message"]
    assert prog[0]["message"]  # ikke-tom
    assert prog[1]["message"]


def test_build_progress_blocks_error_status_from_error_result():
    calls = [_normalize_call({"id": "c1", "name": "bash", "input": {"command": "boom"}})]
    results = [{"tool_use_id": "c1", "status": "error", "content": "fejl", "is_error": True}]
    prog = _build_progress_blocks(calls, results)
    assert prog[0]["status"] == "error"


def test_build_progress_blocks_empty_when_no_tools():
    assert _build_progress_blocks([], []) == []


def test_build_turn_blocks_appends_progress_after_tool_pairs():
    calls = [_normalize_call({"id": "c1", "name": "read_file", "input": {"path": "x.py"}})]
    results = [_normalize_result(_FakeToolResult("c1", "contents"))]
    blocks = _build_turn_blocks(text="hej", tool_calls=calls, tool_results=results)

    types = [b["type"] for b in blocks]
    # Ingen interleave (fallback, fx native batch-tool-exec): tool_use →
    # tool_result → tekst (svaret opsummerer værktøjerne) → progress sidst.
    # Bjørn 10. jul: 6 native tool-kald må IKKE rendre med teksten på index 0.
    assert types == ["tool_use", "tool_result", "text", "progress"]
    assert blocks[-1]["tool_use_id"] == "c1"


def test_fallback_native_batch_places_all_tools_before_answer_text():
    """Regression (Bjørn 10. jul): native batch-tool-exec fører IKKE _interleave_log
    → fallback-stien. 6 tool-kald + afsluttende svar må rendre tools FØRST, tekst
    til sidst — ikke tekst på index 0 så kortene falder i bunden."""
    calls = [
        _normalize_call({"id": f"c{i}", "name": n, "input": {}})
        for i, n in enumerate(
            ["get_weather", "heartbeat_status", "daemon_status",
             "read_visual_memory", "list_self_wakeups", "git_status"]
        )
    ]
    results = [_normalize_result(_FakeToolResult(f"c{i}", "ok")) for i in range(6)]
    blocks = _build_turn_blocks(
        text="Der skete en del på 6 kald — kort status: ...",
        tool_calls=calls, tool_results=results,  # ingen interleave
    )
    non_prog = [b["type"] for b in blocks if b["type"] != "progress"]
    assert non_prog == ["tool_use", "tool_result"] * 6 + ["text"]
    # Teksten er sidst blandt ikke-progress → kortene ligger over svaret.
    assert non_prog[-1] == "text"


def test_interleave_undercounts_tools_falls_back_to_tools_first():
    """Regression (Bjørn 10. jul): native batch-exec kan efterlade interleave
    med KUN en 'text'-markør (fra en streamet svar-delta) men 6 faktiske tools.
    interleave['text'] undertæller tools → må IKKE stoles på; fallback lægger
    tools først, tekst sidst i stedet for tekst på index 0 + tools hængt på."""
    calls = [_normalize_call({"id": f"c{i}", "name": "bash", "input": {}}) for i in range(6)]
    results = [_normalize_result(_FakeToolResult(f"c{i}", "ok")) for i in range(6)]
    blocks = _build_turn_blocks(
        text="Kort status fra 6 kald.",
        tool_calls=calls, tool_results=results,
        interleave=["text"],  # undertæller: 0 tool-markører < 6 tools
    )
    non_prog = [b["type"] for b in blocks if b["type"] != "progress"]
    assert non_prog == ["tool_use", "tool_result"] * 6 + ["text"]
    assert non_prog[-1] == "text"


def test_build_turn_blocks_no_progress_when_no_tools():
    blocks = _build_turn_blocks(text="bare tekst", tool_calls=[], tool_results=[])
    assert [b["type"] for b in blocks] == ["text"]
def test_multiple_consecutive_tools_not_collapsed():
    """Bjørn 10. jul: 3 tool-kald i træk → interleave ['tool','tool','tool','text']
    må IKKE dedupe'es til ét tool. Alle 3 tools + svar-tekst skal med."""
    calls = [
        {"id": "c1", "name": "get_weather", "input": {}},
        {"id": "c2", "name": "bash", "input": {}},
        {"id": "c3", "name": "calculate", "input": {}},
    ]
    results = [
        {"tool_use_id": "c1", "status": "done", "content": "sol", "is_error": False},
        {"tool_use_id": "c2", "status": "done", "content": "ok", "is_error": False},
        {"tool_use_id": "c3", "status": "done", "content": "42", "is_error": False},
    ]
    blocks = _build_turn_blocks(
        text="Her er svaret.", tool_calls=calls, tool_results=results,
        interleave=["tool", "tool", "tool", "text"],
    )
    ids = [b["id"] for b in blocks if b["type"] == "tool_use"]
    assert ids == ["c1", "c2", "c3"]  # ALLE 3, ikke kun sidste
    assert sum(1 for b in blocks if b["type"] == "tool_result") == 3
    assert {"type": "text", "text": "Her er svaret."} in blocks  # progress kan følge efter


def test_answer_text_never_dropped_when_interleave_lacks_text():
    """Hvis interleave mangler afsluttende 'text' men svar findes → tekst bevares."""
    calls = [{"id": "c1", "name": "bash", "input": {}}]
    results = [{"tool_use_id": "c1", "status": "done", "content": "ok", "is_error": False}]
    blocks = _build_turn_blocks(
        text="Svar uden interleave-text.", tool_calls=calls, tool_results=results,
        interleave=["tool"],  # ingen 'text'
    )
    assert any(b["type"] == "text" and b["text"] == "Svar uden interleave-text." for b in blocks)
    assert sum(1 for b in blocks if b["type"] == "tool_use") == 1
