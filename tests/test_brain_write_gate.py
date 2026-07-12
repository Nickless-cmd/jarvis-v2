from core.tools import brain_write_gate as g


def test_brain_write_tools_set():
    assert g.BRAIN_WRITE_TOOLS == ("remember_this", "archive_brain_entry")


def test_non_brain_tool_always_allowed():
    assert g.check_brain_write_allowed("read_mood", role="guest") is True
    assert g.check_brain_write_allowed("search_memory", role="member") is True


def test_owner_may_brain_write():
    assert g.check_brain_write_allowed("remember_this", role="owner") is True
    assert g.check_brain_write_allowed("archive_brain_entry", role="") is True


def test_non_owner_brain_write_denied():
    assert g.check_brain_write_allowed("remember_this", role="member") is False
    assert g.check_brain_write_allowed("archive_brain_entry", role="guest") is False
    assert g.check_brain_write_allowed("remember_this", role="MEMBER") is False
