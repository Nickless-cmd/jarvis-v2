from core.services.anthropic_sse_emitter import AnthropicSSEEmitter

def test_tool_result_block_emits_content_block_events():
    em = AnthropicSSEEmitter(message_id="msg_x", model="jarvis")
    out = "".join(em.tool_result_block(tool_use_id="toolu_1", status="done", content="a\nb", is_error=False))
    assert "content_block_start" in out
    assert "tool_result" in out
    assert "toolu_1" in out
    assert "content_block_stop" in out
