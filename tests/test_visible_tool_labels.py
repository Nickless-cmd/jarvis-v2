"""Public progress labels stay readable as the tool catalog grows."""

import ast
from pathlib import Path

from core.services.visible_tool_labels import _tool_label


def test_registered_tool_names_have_readable_progress_labels():
    source = Path(__file__).resolve().parents[1] / "core/tools/simple_tools.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    handlers = next(
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "_TOOL_HANDLERS"
    )
    names = [key.value for key in handlers.keys if isinstance(key, ast.Constant)]
    assert len(names) >= 300  # the fallback must cover the real catalog
    unreadable = [name for name in names if "_" in _tool_label(name)]
    assert unreadable == []


def test_known_actions_keep_useful_context():
    assert _tool_label("operator_bash", {"command": "cd /tmp && git status"}) == "Bash: git status"
    assert _tool_label("read_file", {"path": "/tmp/app.py"}) == "Læser fil: app.py"
