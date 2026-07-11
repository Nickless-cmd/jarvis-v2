from central_cli.engine.rowdiff import restore_cursor_index


def test_cursor_follows_selected_key_after_reorder():
    assert restore_cursor_index("b", ["a", "c", "b"], old_index=1) == 2


def test_cursor_clamps_when_selected_key_removed():
    assert restore_cursor_index("b", ["a", "c"], old_index=1) == 1
    assert restore_cursor_index("b", ["a"], old_index=1) == 0


def test_cursor_zero_when_empty():
    assert restore_cursor_index("b", [], old_index=3) == 0


def test_cursor_stable_when_nothing_changes():
    assert restore_cursor_index("a", ["a", "b", "c"], old_index=0) == 0


def test_none_selected_key_clamps_old_index():
    assert restore_cursor_index(None, ["a", "b"], old_index=5) == 1
