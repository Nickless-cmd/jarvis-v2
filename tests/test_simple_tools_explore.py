from core.tools.simple_tools_explore import _execution_context


def test_auto_without_desk_workspace_uses_runtime():
    target, context, error = _execution_context({})

    assert target == "runtime"
    assert context == {"execution_target": "runtime"}
    assert error == ""


def test_unknown_target_is_rejected():
    target, context, error = _execution_context({"target": "moon"})

    assert target == ""
    assert context == {}
    assert "auto, runtime, or workstation" in error


def test_returneret_dom_siger_hvilken_maskine(monkeypatch, tmp_path):
    """Den gemte raekke sagde hvem der blev spurgt; den returnerede gjorde ikke.
    To tal om samme koersel kunne kun forliges ved at gaette."""
    import core.tools.simple_tools_explore as ex
    import inspect
    kilde = inspect.getsource(ex._exec_explore)
    assert '"kontrolleret_mod"' in kilde, "dommen siger stadig ikke hvem den spurgte"
    assert '"workstation" if _bro_tjek' in kilde


def test_returneret_maerkat_kan_ogsaa_sige_at_broen_tav():
    """Foerste aegte koersel efter deployet: den GEMTE raekke sagde
    `bro-svarede-ikke`, den RETURNEREDE sagde `workstation`. To poster om samme
    koersel, og kun den ene kunne sige at den intet svar fik."""
    import inspect
    import core.tools.simple_tools_explore as ex
    kilde = inspect.getsource(ex._exec_explore)
    assert '"bro-svarede-ikke"' in kilde, "den returnerede dom kan ikke sige det"
    assert 'uafgjort' in kilde
