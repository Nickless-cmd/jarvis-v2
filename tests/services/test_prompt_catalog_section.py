from core.services.prompt_contract import build_visible_chat_prompt_assembly


def test_visible_prompt_includes_tool_catalog():
    a = build_visible_chat_prompt_assembly(
        provider="ollama", model="glm-5.1:cloud",
        user_message="hej", session_id=None,
    )
    assert "TOOL CATALOG" in (a.text or "")
