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
