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


def _workstation_session(monkeypatch, *, root="/home/bjorn/project"):
    import core.services.chat_sessions as sessions
    monkeypatch.setattr(sessions, "get_chat_session", lambda _sid: {
        "workspace_kind": "workstation", "workspace_root": root})


def test_auto_med_workstation_session_uden_bruger_falder_tilbage_til_runtime(monkeypatch):
    """Målt 5/10-2026 (Jarvis' eget fund): et scout_agent-kald uden `target`
    valgte workstation, fordi sessionen VAR et Desk-workspace — men uden en
    autentificeret Desk-bruger svarede værktøjet en HÅRD fejl i stedet for at
    falde tilbage. Oppefra lignede det «tomt svar», men det var en afvisning i
    routingen: en helt tredje fejlform.

    `auto` skal VÆLGE, ikke fejle. Kan det foretrukne valg ikke bruges, vælger
    vi det andet — runtime."""
    import core.identity.workspace_context as wctx
    _workstation_session(monkeypatch)
    monkeypatch.setattr(wctx, "current_user_id", lambda: "")
    target, context, error = _execution_context({
        "_runtime_session_id": "desk-session", "_runtime_user_id": ""})
    assert error == "", f"auto fejlede i stedet for at falde tilbage: {error}"
    assert target == "runtime"
    assert context == {"execution_target": "runtime"}


def test_auto_med_workstation_session_og_bruger_vaelger_workstation(monkeypatch):
    """Den positive gren: kan workstation-stien bruges, vælges den."""
    _workstation_session(monkeypatch)
    target, context, error = _execution_context({
        "_runtime_session_id": "desk-session", "_runtime_user_id": "bjorn"})
    assert error == ""
    assert target == "workstation"
    assert context["workspace_root"] == "/home/bjorn/project"
    assert context["user_id"] == "bjorn"


def test_eksplicit_workstation_uden_bruger_fejler_stadig(monkeypatch):
    """Den ærlige fejl skal blive: beder man EKSPLICIT om workstation og den
    ikke kan bruges, er et svar bedre end et tavst fald tilbage til en anden
    maskine end den man bad om."""
    import core.identity.workspace_context as wctx
    _workstation_session(monkeypatch)
    monkeypatch.setattr(wctx, "current_user_id", lambda: "")
    target, context, error = _execution_context({
        "target": "workstation", "_runtime_session_id": "desk-session",
        "_runtime_user_id": ""})
    assert target == "" and context == {}
    assert "authenticated Desk user" in error
