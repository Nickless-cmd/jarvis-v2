"""active_file_store: live "aktiv fil" pr. bruger til fil-træ-highlight."""
from __future__ import annotations


def test_set_and_get_roundtrip(isolated_runtime) -> None:
    from core.services.active_file_store import set_active_file, get_active_file
    set_active_file("u1", "/repo/core/db.py", "read")
    rec = get_active_file("u1")
    assert rec and rec["path"] == "/repo/core/db.py" and rec["op"] == "read"


def test_per_user_isolation(isolated_runtime) -> None:
    from core.services.active_file_store import set_active_file, get_active_file
    set_active_file("u1", "/a.py", "read")
    set_active_file("u2", "/b.py", "write")
    assert get_active_file("u1")["path"] == "/a.py"
    assert get_active_file("u2")["path"] == "/b.py"


def test_empty_path_ignored(isolated_runtime) -> None:
    from core.services.active_file_store import set_active_file, get_active_file
    set_active_file("u1", "  ", "read")
    assert get_active_file("u1") is None


def test_clear(isolated_runtime) -> None:
    from core.services.active_file_store import set_active_file, get_active_file, clear_active_file
    set_active_file("u1", "/a.py", "read")
    clear_active_file("u1")
    assert get_active_file("u1") is None
