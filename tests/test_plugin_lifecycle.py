"""Omfang og afhændelse — Fase 9.

Exit-kriterierne: «scoped registration is identity-based, exact-entry disposal
is idempotent, empty layers are reclaimed, and disposal reaches quiescence» og
«disposal reports unresolved ownership».
"""
from __future__ import annotations

import threading
import time

import pytest

from core.runtime.plugin_lifecycle import Omfang, Registret


# -------------------------------------------------------- identitet, ikke navn

def test_afhaendelse_rammer_den_PRAECISE_post_ikke_navnet():
    """To poster med samme navn er to poster.

    Slog vi op paa navn, ville en afhaendelse af den foerste ramme den anden —
    og den fejl er usynlig indtil noget forsvinder man ikke bad om.
    """
    o = Omfang("prøve")
    spor: list[str] = []
    af1 = o.registrer("dublet", lambda: spor.append("første"))
    af2 = o.registrer("dublet", lambda: spor.append("anden"))

    # Den ANDEN afhaendes. Havde testen taget den foerste, ville et
    # navne-opslag give samme svar som et identitets-opslag — og mutationen
    # «slaa op paa navn» overlevede praecis dén udgave af testen.
    assert af2() is True
    assert spor == ["anden"], "forkert post afhaendt"
    assert o.antal == 1

    # Og nu det der afsloerer navne-opslaget: er det den RIGTIGE post der
    # ligger tilbage? Et navne-opslag fjernede den foerste fra listen og lod
    # den anden staa som afhaendt — saa her ville der ikke koere noget.
    o.afhaend(frist_s=0.05)
    assert spor == ["anden", "første"], \
        "den overlevende post var ikke den rigtige — afhaendelsen slog op paa NAVN"


def test_to_poster_med_samme_navn_faar_forskellig_identitet():
    o = Omfang("prøve")
    f = lambda: None                                    # noqa: E731
    o.registrer("ens", f)
    o.registrer("ens", f)                               # SAMME funktion
    ider = {p.identitet for p in o._poster}
    assert len(ider) == 2, "to poster delte identitet — en afhaendelse rammer blindt"


def test_hver_registrering_faar_sin_EGEN_vej_tilbage():
    o = Omfang("prøve")
    spor: list[str] = []
    a = o.registrer("a", lambda: spor.append("a"))
    b = o.registrer("b", lambda: spor.append("b"))
    b()
    assert spor == ["b"]
    a()
    assert spor == ["b", "a"]


# ------------------------------------------------------------------ idempotens

def test_afhaendelse_er_IDEMPOTENT():
    """Uden det bliver «afhaend for en sikkerheds skyld» til en fejlkilde, og
    saa holder folk op med at goere det."""
    o = Omfang("prøve")
    kald = []
    af = o.registrer("x", lambda: kald.append(1))
    assert af() is True
    assert af() is False, "anden gang skal vaere en no-op"
    assert af() is False
    assert kald == [1], "afhaendelsen koerte mere end én gang"


def test_afhaend_paa_omfanget_roerer_ikke_en_allerede_afhaendt_post():
    o = Omfang("prøve")
    kald = []
    af = o.registrer("x", lambda: kald.append(1))
    af()
    r = o.afhaend(frist_s=0.05)
    assert kald == [1]
    assert r.afhaendte == ()


# ------------------------------------------------------------- modsat rækkefølge

def test_afhaendelse_sker_i_MODSAT_orden():
    """Et lag bygget oven paa et andet skal vaek foerst."""
    o = Omfang("prøve")
    spor: list[str] = []
    for navn in ("bund", "midt", "top"):
        o.registrer(navn, lambda n=navn: spor.append(n))
    o.afhaend(frist_s=0.05)
    assert spor == ["top", "midt", "bund"]


# --------------------------------------------------- uafklaret ejerskab

def test_fejlet_afhaendelse_RAPPORTERES_ikke_sluges():
    """Spec'ens «disposal reports unresolved ownership».

    Det er hele forskellen paa en nedlukning man kan stole paa og en der ser
    stille ud. Huset har ~30 `stop_*()`-kald i app.py, hver i sit eget
    `except: pass` — ingen af dem kan sige hvad der ikke lykkedes.
    """
    o = Omfang("prøve")
    def sprang():
        raise RuntimeError("håndtaget sad fast")
    o.registrer("stædig", sprang)
    o.registrer("nem", lambda: None)

    r = o.afhaend(frist_s=0.05)

    assert not r.ren
    assert len(r.uafklarede) == 1
    navn, grund = r.uafklarede[0]
    assert navn == "stædig"
    assert "håndtaget sad fast" in grund and "RuntimeError" in grund
    assert "nem" in r.afhaendte, "en fejl maa ikke stoppe resten af listen"


def test_en_fejlende_post_stopper_ikke_de_oevrige():
    o = Omfang("prøve")
    spor: list[str] = []
    o.registrer("a", lambda: spor.append("a"))
    o.registrer("bombe", lambda: (_ for _ in ()).throw(ValueError("nej")))
    o.registrer("c", lambda: spor.append("c"))
    r = o.afhaend(frist_s=0.05)
    assert spor == ["c", "a"], "en fejl midt i listen aad naboerne"
    assert len(r.uafklarede) == 1


def test_afhaendelse_kaster_ikke_paa_en_almindelig_fejl():
    """En nedlukning der kaster goer nedlukningen vaerre."""
    o = Omfang("prøve")
    o.registrer("bombe", lambda: (_ for _ in ()).throw(BaseException("grim")))
    try:
        r = o.afhaend(frist_s=0.05)
    except BaseException:
        pytest.fail("afhaendelsen kastede")
    assert not r.ren
    assert r.uafklarede[0][0] == "bombe"


def test_afbrydelse_koerer_listen_FAERDIG_og_kastes_derefter():
    """To krav der trak hver sin vej, og begge er rigtige.

    En afhaender der rejser SystemExit maa ikke efterlade resten af listen
    ukoert — de poster ville vaere uafklarede UDEN at staa i rapporten, den
    vaerste af de to slags tavshed. Men et Ctrl-C der forsvandt ville ogsaa
    vaere en loegn.

    Loesningen: koer listen faerdig, skriv rapporten, kast SAA.
    """
    o = Omfang("prøve")
    spor: list[str] = []
    o.registrer("bund", lambda: spor.append("bund"))
    o.registrer("afbryder", lambda: (_ for _ in ()).throw(KeyboardInterrupt()))
    o.registrer("top", lambda: spor.append("top"))

    with pytest.raises(KeyboardInterrupt):
        o.afhaend(frist_s=0.05)

    assert spor == ["top", "bund"], \
        "afbrydelsen efterlod poster ukoert — uafklaret ejerskab uden rapport"
    assert o.tom


def test_rapporten_forklarer_sig_selv():
    o = Omfang("navngivet")
    o.registrer("x", lambda: (_ for _ in ()).throw(RuntimeError("hov")))
    linjer = o.afhaend(frist_s=0.05).forklar()
    assert len(linjer) == 1
    assert "navngivet" in linjer[0] and "x" in linjer[0] and "hov" in linjer[0]


# ------------------------------------------------------------- stop admission

def test_lukket_omfang_afviser_ny_registrering():
    """Kom der noget ind bagfra under nedlukning, ville den modsatte orden
    vaere en loegn."""
    o = Omfang("prøve")
    o.afhaend(frist_s=0.05)
    with pytest.raises(RuntimeError) as e:
        o.registrer("for sent", lambda: None)
    assert "lukket" in str(e.value)


# -------------------------------------------------------------- ro (quiescence)

def test_afhaendelse_VENTER_paa_ejet_arbejde():
    o = Omfang("prøve")
    o.arbejde_startet()
    faerdig = threading.Event()

    def slip():
        time.sleep(0.05)
        o.arbejde_slut()
        faerdig.set()

    threading.Thread(target=slip, daemon=True).start()
    r = o.afhaend(frist_s=2.0)
    assert faerdig.is_set(), "afhaendelsen ventede ikke paa arbejdet"
    assert r.rolig and r.udestaaende_arbejde == 0


def test_fristen_der_loeber_ud_er_en_RAPPORT_ikke_et_kast():
    o = Omfang("prøve")
    o.arbejde_startet()                       # slippes aldrig
    r = o.afhaend(frist_s=0.05)
    assert r.rolig is False
    assert r.udestaaende_arbejde == 1
    assert not r.ren
    assert "fristen loeb ud" in " ".join(r.forklar())


def test_arbejdstaelleren_gaar_ikke_under_nul():
    """En utaellelig taeller ville goere `rolig` meningsloes."""
    o = Omfang("prøve")
    o.arbejde_slut()
    o.arbejde_slut()
    assert o.arbejde_i_gang == 0
    o.arbejde_startet()
    assert o.arbejde_i_gang == 1


def test_omfanget_er_TOMT_efter_afhaendelse():
    """Ro betyder: intet nyt kan komme ind, og intet gammelt er tilbage."""
    o = Omfang("prøve")
    for i in range(5):
        o.registrer(f"p{i}", lambda: None)
    o.afhaend(frist_s=0.1)
    assert o.tom and o.antal == 0


# ------------------------------------------------------------------- registret

def test_tomme_lag_RYDDES():
    """Et omfang uden poster der bliver staaende, er en boette registret skal
    baere rundt paa uden at nogen ejer den."""
    r = Registret()
    r.aabn("væk").registrer("x", lambda: None)
    assert r.navne == ("væk",)
    r.afhaend("væk")
    assert r.navne == (), "det tomme lag blev staaende"


def test_ryd_tomme_fjerner_kun_de_tomme():
    r = Registret()
    r.aabn("tom")
    r.aabn("fuld").registrer("x", lambda: None)
    assert r.ryd_tomme() == 1
    assert r.navne == ("fuld",)


def test_afhaendelse_af_ukendt_omfang_er_ikke_en_fejl():
    """Allerede vaek er det oenskede resultat."""
    r = Registret()
    rap = r.afhaend("findes-ikke")
    assert rap.ren and rap.afhaendte == ()


def test_aabn_giver_SAMME_omfang_indtil_det_lukkes():
    r = Registret()
    a = r.aabn("s")
    assert r.aabn("s") is a
    r.afhaend("s")
    assert r.aabn("s") is not a, "et lukket omfang blev genbrugt"


def test_afhaend_alle_tager_NYESTE_foerst():
    r = Registret()
    spor: list[str] = []
    for navn in ("først", "så", "sidst"):
        r.aabn(navn).registrer(navn, lambda n=navn: spor.append(n))
    r.afhaend_alle(frist_s=0.1)
    assert spor == ["sidst", "så", "først"]
    assert r.navne == ()


def test_status_kan_laeses():
    r = Registret()
    o = r.aabn("s")
    o.registrer("x", lambda: None)
    o.arbejde_startet()
    s = r.status()
    assert s["antal"] == 1
    assert s["omfang"]["s"] == {"poster": 1, "arbejde": 1}


# ------------------------------------------------------------------ samtidighed

def test_registrering_fra_flere_traade_taber_ingen():
    """Laasen er ikke pynt: registret skrives fra daemon-traade."""
    o = Omfang("prøve")
    fejl: list[BaseException] = []

    def arbejd(i: int):
        try:
            for j in range(50):
                o.registrer(f"t{i}-{j}", lambda: None)
        except BaseException as e:            # pragma: no cover
            fejl.append(e)

    traade = [threading.Thread(target=arbejd, args=(i,)) for i in range(4)]
    for t in traade:
        t.start()
    for t in traade:
        t.join()
    assert not fejl
    assert o.antal == 200, f"poster gik tabt: {o.antal}"


def test_samtidig_afhaendelse_koerer_hver_post_EN_gang():
    o = Omfang("prøve")
    taeller: list[int] = []
    laas = threading.Lock()

    def tael():
        with laas:
            taeller.append(1)

    veje = [o.registrer(f"p{i}", tael) for i in range(50)]
    traade = [threading.Thread(target=lambda v=v: v()) for v in veje]
    traade += [threading.Thread(target=lambda: o.afhaend(frist_s=0.5))]
    for t in traade:
        t.start()
    for t in traade:
        t.join()
    assert sum(taeller) == 50, f"poster afhaendt {sum(taeller)} gange i stedet for 50"


# ------------------------------------------------------ håndholdt nedlukning

def test_nedlukning_holder_DEN_GIVNE_orden():
    """Listen er en haandskrevet raekkefoelge, ikke en stak. At vende den ville
    vaere en adfaerdsaendring forklaedt som oprydning."""
    from core.runtime.plugin_lifecycle import koer_nedlukning
    spor: list[str] = []
    koer_nedlukning([(n, lambda n=n: spor.append(n)) for n in ("en", "to", "tre")])
    assert spor == ["en", "to", "tre"]


def test_et_fejlende_trin_draeber_IKKE_resten():
    """Maalt 13/9-2026: 15 af app.py's stop-kald stod uden vaern. Fejlede
    `stop_heartbeat_scheduler()`, blev de 14 efterfoelgende aldrig koert."""
    from core.runtime.plugin_lifecycle import koer_nedlukning
    spor: list[str] = []
    r = koer_nedlukning([
        ("først", lambda: spor.append("først")),
        ("bombe", lambda: (_ for _ in ()).throw(RuntimeError("nede"))),
        ("sidst", lambda: spor.append("sidst")),
    ])
    assert spor == ["først", "sidst"], "et fejlende trin aad resten af listen"
    assert r.uafklarede == (("bombe", "RuntimeError: nede"),)


def test_fejl_SLUGES_ikke():
    """Den anden halvdel af fejlen: 14 kald i `except: pass`. De fejler tavst,
    nedlukningen ser stille ud, og noget lever videre."""
    from core.runtime.plugin_lifecycle import koer_nedlukning
    r = koer_nedlukning([("tavs", lambda: (_ for _ in ()).throw(OSError("hov")))])
    assert not r.ren
    assert r.uafklarede[0][0] == "tavs" and "hov" in r.uafklarede[0][1]


def test_manglende_import_rapporteres_som_ethvert_andet_trin():
    """Flere stop-kald importeres dovent. En ImportError skal staa i rapporten,
    ikke forsvinde."""
    from core.runtime.plugin_lifecycle import koer_nedlukning
    def henter():
        from core.services.findes_slet_ikke import stop  # noqa: F401
    r = koer_nedlukning_hjaelp = koer_nedlukning([("dovent", henter)])
    assert r.uafklarede and "ModuleNotFoundError" in r.uafklarede[0][1]


def test_ren_nedlukning_er_ren():
    from core.runtime.plugin_lifecycle import koer_nedlukning
    r = koer_nedlukning([("a", lambda: None), ("b", lambda: None)])
    assert r.ren and r.afhaendte == ("a", "b") and r.forklar() == []


# ------------------------------------------ nedlukningen i app.py skal BLIVE ren

def _nedluknings_blok() -> str:
    import pathlib
    t = pathlib.Path("apps/api/jarvis_api/app.py").read_text().splitlines()
    s = next(i for i, l in enumerate(t) if "jarvis api shutdown begin" in l)
    e = next(i for i, l in enumerate(t) if "jarvis api shutdown complete" in l)
    return "\n".join(t[s:e + 1])


def test_alle_29_nedluknings_trin_er_stadig_med():
    """Vagt mod at et trin falder ud under en oprydning.

    Blokken havde 29 kald foer omskrivningen (15 uden vaern, 14 i
    `except: pass`). Forsvinder et, stopper noget aldrig — og det ville ingen
    opdage, fordi nedlukningen alligevel ser stille ud.
    """
    import re
    navne = re.findall(r'\("(stop_\w+|write_inheritance_seed)"', _nedluknings_blok())
    assert len(navne) == 29, f"nedlukningen har {len(navne)} trin, forventede 29"
    assert len(set(navne)) == 29, "et trin staar to gange"


def test_ingen_UBESKYTTEDE_stop_kald_er_kommet_tilbage():
    """15 bare `stop_x()`-kald betoed at ét nedbrud aad de 14 efterfoelgende.
    Et nyt bart kald ville genindfoere praecis det."""
    import re
    bare = re.findall(r'^\s+(stop_\w+)\(\)\s*$', _nedluknings_blok(), re.M)
    assert bare == [], f"bart stop-kald tilbage i nedlukningen: {bare}"


def test_ingen_TAVSE_except_pass_i_nedlukningen():
    """Den anden halvdel: 14 kald der fejlede uden at sige det."""
    blok = _nedluknings_blok()
    assert "except Exception:" not in blok, \
        "et trin sluger sin fejl igen — nedlukningen ser stille ud og lyver"
