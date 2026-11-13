"""Matrix-karaktererne som flade: filtrering ud af registret + udfalds-mapping."""
from __future__ import annotations

from types import SimpleNamespace

from core.services import matrix_karakterer as mk


def _spec(name: str, priority: int = 5, cooldown: float = 60):
    return SimpleNamespace(name=name, priority=priority, cooldown_minutes=cooldown)


def test_matrix_navne_udledes_af_registreringen_ikke_en_liste():
    navne = mk.matrix_navne()
    # Alle 17 karakterer fra bestillingen er med …
    for n in ("red_dress", "analyst", "redpill", "dissent", "white_rabbit", "belief_gap",
              "machines", "morpheus", "trinity", "dejavu", "sentinel", "ghost", "mourning",
              "seraph", "persephone", "twins", "exile"):
        assert n in navne
    # … og navnene er unikke, og kun det Matrix-modulet registrerer.
    assert len(navne) == len(set(navne))
    assert "heartbeat" not in navne


def test_matrix_navne_roerer_ikke_registret():
    from core.services import internal_cadence as ic
    foer = dict(ic._producers)
    mk.matrix_navne()
    assert ic._producers == foer


def test_byg_raekker_filtrerer_karaktererne_ud_af_hele_registret():
    registret = [_spec(f"andet_{i}") for i in range(119)] + [_spec("ghost", cooldown=360),
                                                              _spec("dejavu", cooldown=45)]
    raekker = mk.byg_raekker(
        registret, ["ghost", "dejavu", "findes_ikke_i_registret"],
        tempo=0.5, effektiv_cooldown=lambda n, c, t: c * t,
        sidste_koersel=lambda n: "", udfald_af=lambda n: None, funktion=lambda n: f"f:{n}",
    )
    assert sorted(r["name"] for r in raekker) == ["dejavu", "ghost"]
    ghost = next(r for r in raekker if r["name"] == "ghost")
    assert ghost["cooldown_minutes"] == 360
    assert ghost["effektiv_cooldown_minutes"] == 180.0   # den effektive, ikke den rå
    assert ghost["last_run_at"] is None                  # aldrig kørt → None, ikke ""
    assert ghost["udfald"] is None                       # intet udfald set → ukendt


def test_udled_udfald_foretraekker_landing_og_opfinder_intet():
    assert mk.udled_udfald({"landing": {"outcome": "skift_registreret"}, "outcome": "x"}) == "skift_registreret"
    assert mk.udled_udfald({"outcome": "by_design"}) == "by_design"
    assert mk.udled_udfald({"status": "ok"}) is None        # status er ikke et udfald
    assert mk.udled_udfald(None) is None
    assert mk.udled_udfald({"landing": "ikke-en-dict"}) is None


def test_beskriv_udfald_kender_alle_otte_og_viser_ukendte_raat():
    otte = ["by_design", "denied", "sammenlignet_uden_fald", "fald_registreret",
            "intet_grundlag", "utilgaengelig", "sammenlignet_uden_skift", "skift_registreret"]
    for o in otte:
        d = mk.beskriv_udfald(o)
        assert d and d["outcome"] == o and d["tone"] != "ukendt"
    ukendt = mk.beskriv_udfald("noget_nyt")
    assert ukendt == {"outcome": "noget_nyt", "tekst": "noget_nyt", "tone": "ukendt"}
    assert mk.beskriv_udfald(None) is None


def test_noter_udfald_skriver_kun_naar_der_er_et_udfald(monkeypatch):
    skrevet: dict = {}
    import core.runtime.db_core as db
    monkeypatch.setattr(db, "set_runtime_state_value", lambda k, v: skrevet.__setitem__(k, v))
    assert mk.noter_udfald("ghost", {"status": "ok"}, at="t") is False
    assert skrevet == {}
    assert mk.noter_udfald("ghost", {"landing": {"outcome": "intet_grundlag"}}, at="t") is True
    assert skrevet == {"cadence_udfald:ghost": {"outcome": "intet_grundlag", "at": "t"}}


def test_funktion_af_laeser_docstringens_foerste_linje():
    assert "Ghost" in mk.funktion_af("ghost")
    assert mk.funktion_af("findes_slet_ikke") == ""
