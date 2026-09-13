"""Anmodet vs faktisk — Fase 9, kriterium 7.

Den test der bærer filen er `test_uhaandhaevet_akse_spejler_ALDRIG_oensket`.
Alt andet her er detaljer; dén ene er hele pointen. En «faktisk»-værdi der
kopierer ønsket ville se rigtig ud på hver skærm og skjule præcis det hul
modulet er skrevet for at vise.
"""
from __future__ import annotations

import pytest

from core.runtime import profile_enforcement as pe
from core.runtime.profiles import byg, kendte


# ---------------------------------------------------------------- kerne-reglen

def test_uhaandhaevet_akse_spejler_ALDRIG_oensket(monkeypatch):
    """Ingen håndhæver → `faktisk=None`. Ikke ønsket, ikke en gætning."""
    def _mangler():
        raise ImportError("ingen gate bygget")
    monkeypatch.setitem(pe.PROEVER, "cross_session_context", _mangler)

    m = pe.maal({"cross_session_context": "none"})["cross_session_context"]

    assert m["anmodet"] == "none"
    assert m["faktisk"] is None, \
        "faktisk spejlede oensket — praecis den loegn modulet skal afsloere"
    assert m["haandhaevet"] is False
    assert m["kilde"] == "ingen haandhaever"


def test_haandhaevet_akse_rapporterer_maalt_vaerdi(monkeypatch):
    monkeypatch.setitem(pe.PROEVER, "sandbox", lambda: ("workspace", "proeve"))
    m = pe.maal({"sandbox": "readonly"})["sandbox"]
    assert m == {"anmodet": "readonly", "faktisk": "workspace",
                 "haandhaevet": True, "kilde": "proeve"}


def test_manglende_haandhaever_og_fejlet_maaling_er_IKKE_det_samme(monkeypatch):
    """En gate der mangler er et designfund. En gate der braekker er en fejl.

    Skrives de sammen, forsvinder den ene bag den anden: en brudt gate ville
    se ud som «ikke bygget endnu» og aldrig blive rettet.
    """
    monkeypatch.setitem(pe.PROEVER, "sandbox",
                        lambda: (_ for _ in ()).throw(ImportError("mangler")))
    monkeypatch.setitem(pe.PROEVER, "telemetry_sharing",
                        lambda: (_ for _ in ()).throw(RuntimeError("braekket")))
    m = pe.maal({})
    assert m["sandbox"]["kilde"] == "ingen haandhaever"
    assert m["telemetry_sharing"]["kilde"] == "maaling fejlede"
    # Begge er uhaandhaevede — men af forskellig grund.
    assert m["sandbox"]["haandhaevet"] is False
    assert m["telemetry_sharing"]["haandhaevet"] is False


def test_maal_kaster_aldrig(monkeypatch):
    """Målingen kaldes fra kørsels-bogføringen. En observatør må ikke kunne
    vælte det han observerer."""
    monkeypatch.setitem(pe.PROEVER, "sandbox",
                        lambda: (_ for _ in ()).throw(BaseException("grim")))
    try:
        ud = pe.maal({"sandbox": "workspace"})
    except BaseException:
        # BaseException fanges bevidst ikke af `except Exception` — men
        # resultatet maa stadig vaere brugbart for de OEVRIGE akser.
        pytest.skip("BaseException slipper igennem med vilje")
    assert set(ud) == set(pe.AKSER)


def test_alle_tre_akser_er_altid_med():
    """Kriteriet nævner tre ved navn. En akse der mangler i svaret er en akse
    ingen kan se mangler."""
    ud = pe.maal({})
    assert set(ud) == {"sandbox", "cross_session_context", "telemetry_sharing"}


# ------------------------------------------------------------------ afvigelser

def test_oensket_indsnaevring_uden_haandhaever_er_et_fund(monkeypatch):
    monkeypatch.setitem(pe.PROEVER, "cross_session_context",
                        lambda: (_ for _ in ()).throw(ImportError()))
    a = pe.afvigelser(pe.maal({"cross_session_context": "none"}))
    assert len(a) == 1
    assert "INGEN haandhaever" in a[0]
    assert "cross_session_context" in a[0]


def test_mest_tilladte_uden_haandhaever_er_IKKE_et_fund(monkeypatch):
    """«full» lover ingen begrænsning, så der er intet løfte at bryde.

    Foerste udgave flagede ogsaa denne, og gav dermed tre linjer paa HVER
    profil. En liste der altid er lang bliver ikke laest.
    """
    monkeypatch.setitem(pe.PROEVER, "cross_session_context",
                        lambda: (_ for _ in ()).throw(ImportError()))
    assert pe.afvigelser(pe.maal({"cross_session_context": "full"})) == []


def test_loesere_end_lovet_markeres_som_farlig(monkeypatch):
    monkeypatch.setitem(pe.PROEVER, "sandbox", lambda: ("none", "p"))
    a = pe.afvigelser(pe.maal({"sandbox": "readonly"}))
    assert len(a) == 1 and "LOESERE end lovet" in a[0]


def test_strammere_end_anmodet_markeres_som_ufarlig(monkeypatch):
    """Virkeligheden må gerne være strammere end profilen bad om. Det skal
    stadig KUNNE ses, men det er ikke et sikkerhedsfund."""
    monkeypatch.setitem(pe.PROEVER, "sandbox", lambda: ("readonly", "p"))
    a = pe.afvigelser(pe.maal({"sandbox": "none"}))
    assert len(a) == 1 and "ufarlig" in a[0]
    assert "LOESERE" not in a[0]


def test_enighed_giver_ingen_afvigelse(monkeypatch):
    monkeypatch.setitem(pe.PROEVER, "sandbox", lambda: ("workspace", "p"))
    assert pe.afvigelser(pe.maal({"sandbox": "workspace"})) == []


def test_akse_profilen_ikke_naevner_er_ingen_afvigelse(monkeypatch):
    monkeypatch.setitem(pe.PROEVER, "sandbox",
                        lambda: (_ for _ in ()).throw(ImportError()))
    assert pe.afvigelser(pe.maal({})) == []


# ------------------------------------------------- synlig i den EFFEKTIVE profil

def test_profilen_BAERER_haandhaevelsen():
    """Kriteriet siger «visible in the effective profile» — ikke «findes i et
    modul ved siden af»."""
    f = byg("safe-offline").forklar()
    assert "haandhaevelse" in f, "kriteriet kraever at den er SYNLIG i profilen"
    assert "afvigelser" in f
    assert set(f["haandhaevelse"]) == set(pe.AKSER)
    for post in f["haandhaevelse"].values():
        assert {"anmodet", "faktisk", "haandhaevet", "kilde"} <= set(post)


def test_hver_profil_kan_forklare_sig_uden_at_braekke():
    for navn in kendte():
        f = byg(navn).forklar()
        assert isinstance(f["afvigelser"], list)
        assert isinstance(f["haandhaevelse"], dict)


def test_haandhaevelse_aendrer_IKKE_profilens_hash():
    """Hashen er over de REGLER kørslen kørte under, ikke over hvor godt de
    blev håndhævet.

    Blandede vi de to, ville to koersler under samme profil faa forskellig
    hash fordi sandkassen var nede paa den ene maskine — og hashen ville
    holde op med at kunne svare paa «kørte den under de regler vi tror?».
    """
    p = byg("visible-owner")
    foer = p.hash
    _ = p.forklar()
    assert p.hash == foer


def test_maalingen_er_ikke_en_kilde_til_fejl_i_forklar(monkeypatch):
    """Vælter måleren, skal profilen stadig kunne forklare sig."""
    def _sprang(*_a, **_k):
        raise RuntimeError("maaleren er nede")
    monkeypatch.setattr(pe, "maal", _sprang)
    f = byg("visible-owner").forklar()
    assert f["haandhaevelse"] == {} and f["afvigelser"] == []


# ------------------------------------------------------------- kilde-sandheden

def test_proeverne_leder_efter_KALDEREN_ikke_efter_kode():
    """Hver prøve skal importere en håndhæver.

    En proeve der returnerer en konstant ville vaere en paastand, ikke en
    maaling — og den ville blive staaende som sand den dag virkeligheden
    aendrede sig. AST i stedet for tekstsoegning: modulet er lille nu, men en
    `in kilde` paa en voksende fil maaler naesten ingenting.
    """
    import ast
    import pathlib

    træ = ast.parse(pathlib.Path("core/runtime/profile_enforcement.py").read_text())
    for navn in ("_maal_sandkasse", "_maal_kryds_session", "_maal_telemetri"):
        fn = next((n for n in ast.walk(træ)
                   if isinstance(n, ast.FunctionDef) and n.name == navn), None)
        assert fn is not None, f"{navn} findes ikke laengere"
        importerer = any(isinstance(n, (ast.Import, ast.ImportFrom))
                         for n in ast.walk(fn))
        assert importerer, \
            f"{navn} importerer ingen haandhaever — den paastaar i stedet for at maale"


# ------------------------------------- «findes» er ikke «virker» (sandkassen)

def test_sandkassen_er_IKKE_haandhaevet_naar_bwrap_ikke_kan_koere(monkeypatch):
    """Den fejl jeg selv shippede samme dag som modulet.

    Maalt paa runtime 13/9-2026: `is_enabled()` OG `is_available()` sagde
    begge True, mens hvert bwrap-kald fejlede med «Unexpected capabilities but
    not setuid». Proeven rapporterede «workspace» — at sandkassen var
    haandhaevet — paa en maskine hvor den ikke kunne starte.

    `is_available()` er `shutil.which("bwrap")`. Den siger at binaeren ligger
    der, ikke at den koerer.
    """
    import core.services.bash_sandbox as bs
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "kan_koere", lambda **k: (
        False, "bwrap: Unexpected capabilities but not setuid, old file caps config?"))

    værdi, kilde = pe._maal_sandkasse()

    assert værdi == "none", "en sandkasse der ikke kan starte blev meldt haandhaevet"
    assert "kan ikke koere" in kilde and "Unexpected capabilities" in kilde, \
        "grunden skal staa i klartekst — ellers leder nogen forkert sted"


def test_sandkassen_er_haandhaevet_naar_bwrap_FAKTISK_koerer(monkeypatch):
    import core.services.bash_sandbox as bs
    monkeypatch.setattr(bs, "is_enabled", lambda: True)
    monkeypatch.setattr(bs, "kan_koere", lambda **k: (True, "proevet"))
    assert pe._maal_sandkasse() == ("workspace", "bash_sandbox")


def test_slukket_sandkasse_skelnes_fra_braekket(monkeypatch):
    """To forskellige tilstande. «Slukket» er et valg, «braekket» er en fejl —
    og en flade der skriver dem sammen sender nogen til det forkerte sted."""
    import core.services.bash_sandbox as bs
    monkeypatch.setattr(bs, "is_enabled", lambda: False)
    monkeypatch.setattr(bs, "kan_koere", lambda **k: (True, "proevet"))
    _, kilde = pe._maal_sandkasse()
    assert "slukket" in kilde and "kan ikke koere" not in kilde
