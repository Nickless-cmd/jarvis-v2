"""Sondens dom skal BRUGES — og må aldrig lamme systemet imens.

Den konkrete fejl (Bjørn 7/9-2026): explore fik nemotron-3-ultra, som kaldte
`search`, fik de rigtige filstier tilbage og skrev derefter
`src/jarvis/providers/provider_router.py` — en sti der ikke findes — med
opdigtede klassenavne og «confidence: Høj». Sonden gav den 0 på `follows`.
Dommen fandtes; ingen læste den.
"""
import core.services.agent_model_fitness as f

MÅLT_GOD = {"provider": "openrouter", "model": "god:free", "enabled": True,
            "probe_score": 100, "probe_detail": {"follows": True}}
MÅLT_DAARLIG = {"provider": "openrouter", "model": "nemotron:free", "enabled": True,
                "probe_score": 65, "probe_detail": {"follows": False}}
ALDRIG_PRØVET = {"provider": "ny", "model": "ukendt:free", "enabled": True}


def test_maalt_god_er_egnet():
    assert f.dom("openrouter", "god:free", poster=[MÅLT_GOD]) == "egnet"


def test_kalder_vaerktoej_men_bruger_ikke_svaret_er_UEGNET():
    """Kernen: 65 point er rigeligt — men uden `follows` duer den ikke."""
    assert f.dom("openrouter", "nemotron:free", poster=[MÅLT_DAARLIG]) == "uegnet"


def test_aldrig_proevet_er_UKENDT_ikke_uegnet():
    """En tom karakter-tabel må ikke lamme agent-arbejdet før første fejning."""
    assert f.dom("ny", "ukendt:free", poster=[ALDRIG_PRØVET]) == "ukendt"


def test_en_model_der_slet_ikke_staar_i_registret_er_ukendt():
    assert f.dom("hvemsomhelst", "hvadsomhelst", poster=[]) == "ukendt"


def test_kun_KENDT_daarlige_blokeres(monkeypatch):
    monkeypatch.setattr(f, "_registret", lambda: [MÅLT_DAARLIG, ALDRIG_PRØVET])
    assert f.er_blokeret("openrouter", "nemotron:free", rolle="researcher") is True
    assert f.er_blokeret("ny", "ukendt:free", rolle="researcher") is False


def test_refleksions_roller_er_uberoerte(monkeypatch):
    """Filosof og etiker kalder ikke værktøjer — at kræve `follows` af dem
    ville udelukke gode modeller fra arbejde de er fine til. De er også de
    travleste roller."""
    monkeypatch.setattr(f, "_registret", lambda: [MÅLT_DAARLIG])
    assert f.er_blokeret("openrouter", "nemotron:free", rolle="filosof") is False
    assert f.er_blokeret("openrouter", "nemotron:free", rolle="etiker") is False


def test_en_frakoblet_model_er_uegnet():
    post = dict(MÅLT_GOD, enabled=False)
    assert f.dom("openrouter", "god:free", poster=[post]) == "uegnet"


def test_bedste_egnede_vaelger_hoejeste_score(monkeypatch):
    bedre = {"provider": "mistral", "model": "codestral", "enabled": True,
             "probe_score": 100, "probe_detail": {"follows": True}}
    lavere = {"provider": "xkiro", "model": "qwen:free", "enabled": True,
              "probe_score": 70, "probe_detail": {"follows": True}}
    monkeypatch.setattr(f, "_registret", lambda: [lavere, bedre, MÅLT_DAARLIG])
    assert f.bedste_egnede() == ("mistral", "codestral")


def test_bedste_egnede_giver_tomt_naar_intet_er_maalt(monkeypatch):
    monkeypatch.setattr(f, "_registret", lambda: [ALDRIG_PRØVET])
    assert f.bedste_egnede() == ("", "")


def test_et_uleseligt_register_vaelter_ikke_noget(monkeypatch):
    def sur():
        raise RuntimeError("registret er væk")
    monkeypatch.setattr(f, "_registret", sur)
    assert f.er_blokeret("a", "b", rolle="researcher") is False   # fail-open


# ── ruteren skal faktisk bruge dommen ───────────────────────────────────────

def test_ruteren_vaelger_om_naar_modellen_er_maalt_uegnet(monkeypatch):
    import core.services.agent_pool_router as r
    import core.services.central_route as cr
    kald = {"n": 0}

    def falsk_route(*, lane, task, exclude):
        kald["n"] += 1
        if kald["n"] == 1:
            return {"provider": "openrouter", "model": "nemotron:free"}
        return {"provider": "mistral", "model": "codestral"}

    monkeypatch.setattr(cr, "route", falsk_route)
    monkeypatch.setattr(f, "_registret", lambda: [MÅLT_DAARLIG])
    ud = r.route_agent_task(kind="researcher")
    assert (ud["provider"], ud["model"]) == ("mistral", "codestral")
    assert kald["n"] == 2, "ruteren blev ikke spurgt igen"


def test_ruteren_roerer_ikke_et_ukendt_valg(monkeypatch):
    """Ingen målinger endnu → ingen indblanding. Ellers ville systemet stå
    stille indtil første fejning."""
    import core.services.agent_pool_router as r
    import core.services.central_route as cr
    monkeypatch.setattr(cr, "route", lambda **kw: {"provider": "ny", "model": "ukendt:free"})
    monkeypatch.setattr(f, "_registret", lambda: [])
    ud = r.route_agent_task(kind="researcher")
    assert (ud["provider"], ud["model"]) == ("ny", "ukendt:free")


def test_bliver_ruteren_ved_med_at_pege_forkert_tages_den_maalt_bedste(monkeypatch):
    import core.services.agent_pool_router as r
    import core.services.central_route as cr
    god = {"provider": "mistral", "model": "codestral", "enabled": True,
           "probe_score": 100, "probe_detail": {"follows": True}}
    monkeypatch.setattr(cr, "route", lambda **kw: {"provider": "openrouter", "model": "nemotron:free"})
    monkeypatch.setattr(f, "_registret", lambda: [MÅLT_DAARLIG, god])
    ud = r.route_agent_task(kind="researcher")
    assert (ud["provider"], ud["model"]) == ("mistral", "codestral")
    assert ud.get("fitness_fallback") is True
