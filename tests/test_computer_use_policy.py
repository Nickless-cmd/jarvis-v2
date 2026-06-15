import core.services.computer_use_policy as cup
from core.tools import tool_scoping


def _reset(monkeypatch):
    store: dict = {}
    monkeypatch.setattr(cup, "load_json", lambda key, default: dict(store))
    monkeypatch.setattr(cup, "save_json", lambda key, data: store.update(data))
    return store


def test_default_enabled(monkeypatch):
    _reset(monkeypatch)
    assert cup.computer_use_enabled("u1") is True


def test_set_and_read(monkeypatch):
    _reset(monkeypatch)
    cup.set_computer_use("u1", False)
    assert cup.computer_use_enabled("u1") is False
    assert cup.computer_use_enabled("u2") is True  # andre uberørte


def test_is_computer_use_tool():
    assert cup.is_computer_use_tool("operator_bash") is True
    assert cup.is_computer_use_tool("screenshot") is True
    assert cup.is_computer_use_tool("web_search") is False


def test_allowed_tool_names_drops_operator_when_disabled(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setattr(tool_scoping, "current_user_id", lambda: "u1", raising=False)
    cup.set_computer_use("u1", False)
    names = ["operator_bash", "web_search", "screenshot"]
    # owner-scope=code ville normalt inkludere operator_bash; med toggle fra fjernes computer-use.
    allowed = tool_scoping.allowed_tool_names(role="owner", scope="code", all_names=names)
    assert "operator_bash" not in allowed
    assert "screenshot" not in allowed


def test_allowed_tool_names_keeps_operator_when_enabled(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setattr(tool_scoping, "current_user_id", lambda: "u1", raising=False)
    names = ["operator_bash", "web_search"]
    allowed = tool_scoping.allowed_tool_names(role="owner", scope="code", all_names=names)
    assert "operator_bash" in allowed
