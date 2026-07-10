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
from core.services.visible_runs import _build_turn_blocks


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
    assert [b["type"] for b in blocks] == ["tool_use", "tool_result", "text"]
    assert blocks[-1] == {"type": "text", "text": "hej"}
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
    assert blocks[-1] == {"type": "text", "text": "Her er svaret."}


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
