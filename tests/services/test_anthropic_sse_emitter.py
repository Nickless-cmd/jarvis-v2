import json

from core.services.anthropic_sse_emitter import AnthropicSSEEmitter


def _parse(events: list[str]) -> list[tuple[str, dict]]:
    out = []
    for chunk in events:
        lines = chunk.strip().split("\n")
        ev = ""
        data = {}
        for line in lines:
            if line.startswith("event: "):
                ev = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        out.append((ev, data))
    return out


def test_text_only_emits_correct_sequence():
    emitter = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.text_delta("Hej"))
    events.extend(emitter.text_delta(" Bjørn"))
    events.extend(emitter.end_message(stop_reason="end_turn"))

    parsed = _parse(events)
    names = [p[0] for p in parsed]
    assert names == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    assert parsed[2][1]["delta"] == {"type": "text_delta", "text": "Hej"}
    assert parsed[3][1]["delta"] == {"type": "text_delta", "text": " Bjørn"}
    assert parsed[5][1]["delta"]["stop_reason"] == "end_turn"


def test_tool_use_emits_correct_sequence():
    emitter = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.text_delta("Looking..."))
    events.extend(emitter.tool_use_start(tool_call_id="toolu_1", name="Bash"))
    events.extend(emitter.tool_use_input_delta(partial_json='{"command":"ls"}'))
    events.extend(emitter.end_message(stop_reason="tool_use"))

    parsed = _parse(events)
    names = [p[0] for p in parsed]
    assert names == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    assert parsed[4][1]["content_block"]["type"] == "tool_use"
    assert parsed[4][1]["content_block"]["name"] == "Bash"
    assert parsed[4][1]["content_block"]["id"] == "toolu_1"
    assert parsed[5][1]["delta"] == {"type": "input_json_delta", "partial_json": '{"command":"ls"}'}


def test_no_text_before_tool_use_skips_text_block():
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.tool_use_start(tool_call_id="t1", name="Read"))
    events.extend(emitter.tool_use_input_delta('{"p":"/x"}'))
    events.extend(emitter.end_message(stop_reason="tool_use"))

    parsed = _parse(events)
    names = [p[0] for p in parsed]
    assert names == [
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]


def test_index_increments_across_blocks():
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = []
    events.extend(emitter.begin_message())
    events.extend(emitter.text_delta("a"))
    events.extend(emitter.tool_use_start("t1", "Bash"))
    events.extend(emitter.tool_use_input_delta("{}"))
    events.extend(emitter.tool_use_start("t2", "Read"))
    events.extend(emitter.tool_use_input_delta("{}"))
    events.extend(emitter.end_message(stop_reason="tool_use"))

    parsed = _parse(events)
    block_starts = [p for p in parsed if p[0] == "content_block_start"]
    indices = [bs[1]["index"] for bs in block_starts]
    assert indices == [0, 1, 2]


def test_ping_event_has_correct_shape():
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = list(emitter.ping())
    parsed = _parse(events)
    assert parsed[0][0] == "ping"
    assert parsed[0][1] == {"type": "ping"}
