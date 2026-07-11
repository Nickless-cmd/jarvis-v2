def test_cursor_stable_table_importable():
    from central_cli.frame.table_view import CursorStableTable

    assert hasattr(CursorStableTable, "update_rows")
