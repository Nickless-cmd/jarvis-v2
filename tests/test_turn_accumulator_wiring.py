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
    blocks = _build_turn_blocks(text="hej", tool_calls=calls, tool_results=results)

    assert blocks[0] == {"type": "text", "text": "hej"}
    use = next(b for b in blocks if b["type"] == "tool_use")
    assert use == {"type": "tool_use", "id": "c1", "name": "read_file", "input": {"path": "x"}}
    res = next(b for b in blocks if b["type"] == "tool_result")
    assert res["tool_use_id"] == "c1"
    assert res["content"] == "file contents"
    assert res["status"] == "done"
    assert res["is_error"] is False


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
    # tekst → tool_use → tool_result → progress (progress sidst)
    assert types == ["text", "tool_use", "tool_result", "progress"]
    assert blocks[-1]["tool_use_id"] == "c1"


def test_build_turn_blocks_no_progress_when_no_tools():
    blocks = _build_turn_blocks(text="bare tekst", tool_calls=[], tool_results=[])
    assert [b["type"] for b in blocks] == ["text"]
