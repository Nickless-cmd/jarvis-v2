

# ── Et froe der spirer bliver et kreativt projekt (25/9-2026) ────────────
#
# `creative_projects` havde INGEN kalder i produktion: 207 linjer med rigtig
# persistering, og ingen har nogensinde skabt et projekt. Modulet var ikke i
# stykker — der manglede en haendelse at haenge paa.

def test_et_spiret_froe_skaber_et_kreativt_projekt(monkeypatch):
    import core.services.seed_system as S

    skabt: list[dict] = []
    monkeypatch.setattr("core.services.creative_projects.create_project",
                        lambda **kw: skabt.append(kw) or kw)
    monkeypatch.setattr(S, "list_cognitive_seeds",
                        lambda **kw: [{"seed_id": "s1", "title": "En tanke om lys",
                                       "intent": "forfoelge den",
                                       "activate_on_context": '["lys"]'}])
    monkeypatch.setattr(S, "update_cognitive_seed_status", lambda **kw: None)
    monkeypatch.setattr(S.event_bus, "publish", lambda *a, **k: None)

    S.check_seed_activation(current_context="noget om lys")
    assert skabt, "et spiret froe blev ikke til et projekt"
    assert skabt[0]["title"] == "En tanke om lys"
    assert skabt[0]["status"] == "active"


def test_en_fejl_i_projektet_standser_ikke_froeet(monkeypatch):
    """Froeet skal stadig spire selv om projektet ikke kan skabes."""
    import core.services.seed_system as S

    def _braekker(**kw):
        raise RuntimeError("basen er vaek")
    monkeypatch.setattr("core.services.creative_projects.create_project", _braekker)
    opdateret: list[str] = []
    monkeypatch.setattr(S, "list_cognitive_seeds",
                        lambda **kw: [{"seed_id": "s1", "title": "T",
                                       "activate_on_context": '["lys"]'}])
    monkeypatch.setattr(S, "update_cognitive_seed_status",
                        lambda **kw: opdateret.append(kw["status"]))
    monkeypatch.setattr(S.event_bus, "publish", lambda *a, **k: None)
    ud = S.check_seed_activation(current_context="lys")
    assert opdateret == ["sprouted"]
    assert len(ud) == 1
