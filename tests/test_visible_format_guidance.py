"""The visible lane leaves paragraph layout to the model and Markdown renderer."""

from pathlib import Path


def test_visible_prompt_does_not_force_paragraph_layout(isolated_runtime):
    assembly = isolated_runtime.prompt_contract.build_visible_chat_prompt_assembly(
        provider="deepseek",
        model="deepseek-flash",
        user_message="Forklar hvad du fandt",
        session_id="format-guidance-test",
    )
    text = assembly.text.lower()
    assert "afsnit adskilt af en blank linje" not in text
    assert "blank lines between short paragraphs" not in text
    assert "short sentences on their own lines" not in text


def test_workspace_templates_have_no_mandatory_paragraph_layout():
    workspace = Path(__file__).resolve().parents[1] / "workspace"
    for relative_path in ("default/VISIBLE_CHAT_RULES.md", "templates/VISIBLE_CHAT_RULES.md"):
        text = (workspace / relative_path).read_text(encoding="utf-8").lower()
        assert "insert blank lines between paragraphs" not in text
        assert "never write more than 2-3 sentences" not in text
        assert "blank lines between short paragraphs" not in text
