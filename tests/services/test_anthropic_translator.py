from core.services import anthropic_translator as at


def test_translate_simple_user_message():
    body = {
        "model": "jarvis",
        "messages": [{"role": "user", "content": "hej"}],
    }
    out = at.translate_request_to_ollama(
        anthropic_body=body,
        identity_prefix="## SOUL\nJeg er Jarvis.",
        backend_model="glm-5.1:cloud",
    )
    assert out["model"] == "glm-5.1:cloud"
    assert out["messages"][0] == {"role": "system", "content": "## SOUL\nJeg er Jarvis."}
    assert out["messages"][-1] == {"role": "user", "content": "hej"}


def test_translate_appends_system_to_identity_prefix():
    body = {
        "model": "jarvis",
        "system": "You are in Claude Code.",
        "messages": [{"role": "user", "content": "x"}],
    }
    out = at.translate_request_to_ollama(
        anthropic_body=body,
        identity_prefix="## SOUL\nJarvis.",
        backend_model="m",
    )
    sys_msg = out["messages"][0]["content"]
    assert "Jarvis." in sys_msg
    assert "You are in Claude Code." in sys_msg
    assert sys_msg.index("Jarvis.") < sys_msg.index("You are in Claude Code.")


def test_translate_assistant_with_tool_use():
    body = {
        "messages": [
            {"role": "user", "content": "list files"},
            {"role": "assistant", "content": [
                {"type": "text", "text": "Looking..."},
                {"type": "tool_use", "id": "toolu_1", "name": "Bash", "input": {"command": "ls"}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "toolu_1", "content": "file1\nfile2"},
            ]},
        ],
    }
    out = at.translate_request_to_ollama(
        anthropic_body=body, identity_prefix="", backend_model="m",
    )
    msgs = out["messages"]
    assistant_msg = next(m for m in msgs if m["role"] == "assistant")
    assert assistant_msg["content"] == "Looking..."
    assert len(assistant_msg["tool_calls"]) == 1
    assert assistant_msg["tool_calls"][0]["function"]["name"] == "Bash"
    tool_msg = next(m for m in msgs if m["role"] == "tool")
    assert tool_msg["content"] == "file1\nfile2"
    assert tool_msg.get("tool_call_id") == "toolu_1"


def test_translate_tools_anthropic_to_ollama():
    body = {
        "messages": [{"role": "user", "content": "x"}],
        "tools": [
            {
                "name": "Read",
                "description": "Read a file",
                "input_schema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        ],
    }
    out = at.translate_request_to_ollama(body, identity_prefix="", backend_model="m")
    assert "tools" in out
    tool = out["tools"][0]
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "Read"
    assert tool["function"]["description"] == "Read a file"
    assert tool["function"]["parameters"]["properties"]["path"]["type"] == "string"


def test_translate_string_content_unchanged():
    """User message with string content stays as string."""
    body = {"messages": [{"role": "user", "content": "plain text"}]}
    out = at.translate_request_to_ollama(body, identity_prefix="", backend_model="m")
    assert out["messages"][0]["content"] == "plain text"


def test_translate_stream_flag_passed():
    body = {"messages": [{"role": "user", "content": "x"}], "stream": True}
    out = at.translate_request_to_ollama(body, identity_prefix="", backend_model="m")
    assert out["stream"] is True


def test_drive_emitter_with_text_only_chunks():
    """Translator drives an emitter from Ollama-format streamed chunks."""
    from core.services.anthropic_sse_emitter import AnthropicSSEEmitter
    chunks = [
        {"message": {"role": "assistant", "content": "Hej"}, "done": False},
        {"message": {"role": "assistant", "content": " Bjørn"}, "done": False},
        {"message": {"role": "assistant", "content": ""}, "done": True, "done_reason": "stop"},
    ]
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = list(at.drive_emitter_from_ollama_chunks(emitter, iter(chunks)))
    text = "".join(events)
    assert "text_delta" in text
    assert "Hej" in text
    assert " Bjørn" in text
    assert "stop_reason" in text
    assert "end_turn" in text


def test_drive_emitter_with_tool_calls_chunks():
    from core.services.anthropic_sse_emitter import AnthropicSSEEmitter
    chunks = [
        {"message": {"role": "assistant", "content": "Listing..."}, "done": False},
        {"message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "toolu_x",
                "function": {"name": "Bash", "arguments": {"command": "ls"}},
            }],
        }, "done": False},
        {"message": {"content": ""}, "done": True, "done_reason": "stop"},
    ]
    emitter = AnthropicSSEEmitter(message_id="m", model="jarvis")
    events = list(at.drive_emitter_from_ollama_chunks(emitter, iter(chunks)))
    text = "".join(events)
    assert "Listing..." in text
    assert "tool_use" in text
    assert "Bash" in text
    assert "input_json_delta" in text
    # partial_json is JSON-escaped inside the SSE data line, so we look for
    # the escaped form
    assert "command" in text and "ls" in text
    assert "stop_reason" in text


def test_build_non_streaming_response_text_only():
    final = at.build_non_streaming_response(
        message_id="msg_x", model="jarvis",
        text="Hej Bjørn",
        tool_calls=[],
    )
    assert final["id"] == "msg_x"
    assert final["type"] == "message"
    assert final["role"] == "assistant"
    assert final["model"] == "jarvis"
    assert len(final["content"]) == 1
    assert final["content"][0] == {"type": "text", "text": "Hej Bjørn"}
    assert final["stop_reason"] == "end_turn"


def test_build_non_streaming_response_with_tool_use():
    final = at.build_non_streaming_response(
        message_id="msg_x", model="jarvis",
        text="Looking",
        tool_calls=[{
            "id": "toolu_1",
            "function": {"name": "Bash", "arguments": {"command": "ls"}},
        }],
    )
    assert len(final["content"]) == 2
    assert final["content"][0] == {"type": "text", "text": "Looking"}
    assert final["content"][1] == {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "Bash",
        "input": {"command": "ls"},
    }
    assert final["stop_reason"] == "tool_use"
