def test_palette_resolves_known_verb():
    from central_cli.frame.palette import resolve_palette_command
    spec = resolve_palette_command("status")
    assert spec is not None and spec.path.startswith("/central")


def test_palette_unknown_verb_returns_none():
    from central_cli.frame.palette import resolve_palette_command
    assert resolve_palette_command("definitelynotacommand") is None
