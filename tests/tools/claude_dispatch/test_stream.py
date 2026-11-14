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


# ── Værktøjskaldene (14/11-2026) ────────────────────────────────────────────
# Før blev `tool_use`-blokke kastet væk her. Konsekvensen var målt: en CLI-agent
# der læste 14 filer efterlod nul spor, og den tomme `agent_tool_calls` blev
# læst som «agenten kan ikke kalde værktøjer». Formen nedenfor er ægte uddrag
# fra CLI 2.1.318.

def test_parse_tool_use_block():
    line = json.dumps({
        "type": "assistant",
        "message": {"content": [{
            "type": "tool_use", "id": "toolu_01TyeCBEwwaTT1x6eN5dANmA",
            "name": "Read", "input": {"file_path": "/tmp/README.md"},
        }]},
    })
    ev = parse_stream_line(line)
    assert len(ev.tool_uses) == 1
    assert ev.tool_uses[0]["name"] == "Read"
    assert ev.tool_uses[0]["id"] == "toolu_01TyeCBEwwaTT1x6eN5dANmA"
    assert ev.tool_uses[0]["input"] == {"file_path": "/tmp/README.md"}


def test_parse_tool_result_block():
    line = json.dumps({
        "type": "user",
        "message": {"content": [{
            "type": "tool_result", "tool_use_id": "toolu_01TyeCBEwwaTT1x6eN5dANmA",
            "is_error": False, "content": "1\t<h1>hej</h1>",
        }]},
    })
    ev = parse_stream_line(line)
    assert len(ev.tool_results) == 1
    assert ev.tool_results[0]["tool_use_id"] == "toolu_01TyeCBEwwaTT1x6eN5dANmA"
    assert ev.tool_results[0]["is_error"] is False
    assert "<h1>" in ev.tool_results[0]["preview"]


def test_parse_tool_result_marks_error():
    """Et fejlet kald skal kunne ses som fejl — ikke bare som fravær af tekst."""
    line = json.dumps({
        "type": "user",
        "message": {"content": [{
            "type": "tool_result", "tool_use_id": "t1",
            "is_error": True, "content": "No such file",
        }]},
    })
    ev = parse_stream_line(line)
    assert ev.tool_results[0]["is_error"] is True


def test_tekst_og_vaerktoejskald_lever_side_om_side():
    """En assistant-blok kan bære BEGGE — teksten må ikke fortænge kaldet."""
    line = json.dumps({
        "type": "assistant",
        "message": {"content": [
            {"type": "text", "text": "jeg læser filen"},
            {"type": "tool_use", "id": "t2", "name": "Read", "input": {}},
        ]},
    })
    ev = parse_stream_line(line)
    assert "jeg læser filen" in ev.text
    assert [t["name"] for t in ev.tool_uses] == ["Read"]
