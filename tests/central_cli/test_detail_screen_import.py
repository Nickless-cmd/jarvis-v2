def test_detail_screen_has_escape_binding():
    from central_cli.frame.detail_screen import DetailScreen
    keys = {b.key for b in DetailScreen.BINDINGS}
    assert "escape" in keys
