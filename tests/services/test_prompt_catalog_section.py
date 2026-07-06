from core.services.prompt_contract import build_visible_chat_prompt_assembly


def test_visible_prompt_includes_tool_catalog():
    a = build_visible_chat_prompt_assembly(
        provider="ollama", model="glm-5.1:cloud",
        user_message="hej", session_id=None,
    )
    # 2026-06-22/23 redesign: the full "TOOL CATALOG" was replaced by the
    # compact grouped "KERNE-VÆRKTØJER" core catalog (+ load_more_tools pointer).
    assert "KERNE-VÆRKTØJER" in (a.text or "")
