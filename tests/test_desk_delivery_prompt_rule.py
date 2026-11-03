"""The always-on prompt must couple Desk and PWA delivery."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_visible_rules_require_both_desk_and_pwa_delivery_paths(
    isolated_runtime,
) -> None:
    for relative in (
        "workspace/default/VISIBLE_CHAT_RULES.md",
        "workspace/templates/VISIBLE_CHAT_RULES.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "apps/jarvis-desk/src/**" in text
        assert "npm run build:renderer" in text
        assert "npm run build:web" in text
        assert "jarvis-desktop-v<version>" in text
        assert "desk-release" in text

    rendered = isolated_runtime.prompt_contract._visible_chat_rules_instruction(
        workspace_dir=ROOT / "workspace/default",
    )
    assert rendered is not None
    assert "npm run build:renderer" in rendered
    assert "npm run build:web" in rendered
    assert "desk-release" in rendered
