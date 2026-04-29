import json

from core.tools.claude_dispatch.stream import parse_stream_line, ParsedEvent


def test_parse_assistant_message():
    line = json.dumps({
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": "hello"}]},
    })
    ev = parse_stream_line(line)
    assert isinstance(ev, ParsedEvent)
    assert ev.kind == "assistant"
    assert "hello" in ev.text


def test_parse_result_extracts_tokens():
    line = json.dumps({
        "type": "result", "subtype": "success",
        "usage": {"input_tokens": 100, "output_tokens": 250},
        "total_cost_usd": 0.012,
    })
    ev = parse_stream_line(line)
    assert ev.kind == "result"
    assert ev.tokens == 350
    assert ev.cost_usd == 0.012


def test_parse_invalid_json_returns_none():
    assert parse_stream_line("not json") is None


def test_parse_unknown_type_returns_event_with_kind():
    line = json.dumps({"type": "system", "subtype": "init"})
    ev = parse_stream_line(line)
    assert ev.kind == "system"
