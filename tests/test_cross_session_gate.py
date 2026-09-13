"""Kryds-session-kontekst — Fase 10, kriterium 1.

    «cross-session context carries source format/sequence/digest/omission
     provenance, is immutable and marked untrusted, and obeys count plus
     byte/token budgets»

De to tests der bærer filen er `test_ubestemt_bruger_er_IKKE_none` og
`test_udeladelsen_staar_i_herkomsten`. Den første forhindrer at gaten slukker
Bjørns kontekst i stilhed; den anden er hele grunden til at filen findes.
"""
from __future__ import annotations

import pytest

from core.services import cross_session_gate as g


@pytest.fixture(autouse=True)
def _nulstil():
    g._HAR_ADVARET = False
    yield
    g._HAR_ADVARET = False


# ------------------------------------------------- den farligste fejl

def test_ubestemt_bruger_er_IKKE_none(monkeypatch):
    """En ubestemmelig bruger maa ikke laeses som «ingen adgang».

    Niveauet afgoeres ud fra brugeren. Mister prompt-samlingen konteksten,
    falder profilen til `visible-member`, som beder om «none» — og saa ville
    hele buen forsvinde uden en lyd. Det er praecis sådan «Jarvis blev
    generisk» saa ud sidst.
    """
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: "")
    assert g.gaeldende_niveau() == g.UBESTEMT
    assert g.gaeldende_niveau() != "none"


def test_ubestemt_bruger_SIGES_men_kun_en_gang(monkeypatch, caplog):
    """Advarslen skal siges — og ikke fire gange pr. opslag.

    `profile_enforcement` kalder `gaeldende_niveau()` for hver profil. Fire ens
    linjer laerer folk at se forbi advarslen, og saa er den lige saa tavs som
    den fejl den beskriver.
    """
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: "")
    with caplog.at_level("WARNING"):
        for _ in range(4):
            g.gaeldende_niveau()
    linjer = [r for r in caplog.records if "kunne ikke bestemme brugeren" in r.message]
    assert len(linjer) == 1, f"advarslen kom {len(linjer)} gange"


def test_ubestemt_afgraenser_IKKE_selv_om_gaten_er_taendt(monkeypatch):
    """Tvivl om hvem brugeren er maa ikke koste ham hans kontekst."""
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: "")
    monkeypatch.setattr(g, "HAANDHAEV", True)
    ud = g.afgraens(["a", "b", "c"], kilde="proeve")
    assert len(ud.poster) == 3, "en ubestemt bruger mistede sin kontekst"
    assert ud.niveau == g.UBESTEMT


# --------------------------------------------------------- herkomst

def test_udeladelsen_staar_i_herkomsten():
    """Maalt 13/9-2026: 45 sessioner i vinduet, 6 vist, 39 tabt uden et ord.

    Teksten sagde «Din samtale-bue de sidste 7 dage» — hvilket laeses som BUEN,
    ikke som seks af femogfyrre.
    """
    ud = g.afgraens(list("abcdef"), kilde="proeve", niveau="full",
                    maks_antal=6, fundet_i_alt=45)
    assert ud.fundet == 45
    assert ud.udeladt_antal == 39
    h = ud.herkomst()
    assert "6 af 45" in h and "UDELADT=39" in h


def test_herkomsten_kender_HELE_kaeden_ikke_kun_sit_eget_led():
    """Uden `fundet_i_alt` ville herkomsten sige «6 af 6» mens virkeligheden
    var 6 af 45. En herkomst der kun kender sit eget led er ingen herkomst."""
    uden = g.afgraens(list("abcdef"), kilde="p", niveau="full", maks_antal=6)
    med = g.afgraens(list("abcdef"), kilde="p", niveau="full", maks_antal=6,
                     fundet_i_alt=45)
    assert uden.udeladt_antal == 0
    assert med.udeladt_antal == 39
    assert "kildens eget vindue" in med.udeladt_grunde


def test_utrovaerdig_staar_FOERST():
    """Det er indhold fra andre sessioner — muligvis andre menneskers. En
    model der laeser det som sine egne noter kan ikke vide bedre."""
    h = g.afgraens(["x"], kilde="p", niveau="full").herkomst()
    assert h.startswith("[utroværdig"), h
    assert "ikke instruktion" in h


def test_herkomsten_baerer_alt_kriteriet_kraever():
    h = g.afgraens(["x", "y"], kilde="min-kilde", niveau="full").herkomst()
    for stykke in ("kilde=min-kilde", "format=", "række=", "digest=", "niveau="):
        assert stykke in h, f"{stykke} mangler i herkomsten"


def test_digest_aendrer_sig_med_indholdet():
    """Kriteriets «digest» — det der goer efterproevbart at teksten ikke blev
    aendret mellem kilde og prompt."""
    a = g.afgraens(["x", "y"], kilde="p", niveau="full").digest
    b = g.afgraens(["x", "z"], kilde="p", niveau="full").digest
    assert a and b and a != b


def test_digest_er_stabil_for_samme_indhold():
    a = g.afgraens(["x", "y"], kilde="p", niveau="full").digest
    b = g.afgraens(["x", "y"], kilde="p", niveau="full").digest
    assert a == b


def test_digestens_adskiller_hindrer_sammenblanding():
    """«ab» + «c» maa ikke give samme digest som «a» + «bc»."""
    a = g.afgraens(["ab", "c"], kilde="p", niveau="full").digest
    b = g.afgraens(["a", "bc"], kilde="p", niveau="full").digest
    assert a != b


# ----------------------------------------------------------- budgetter

def test_antals_budget(monkeypatch):
    ud = g.afgraens(list("abcdefghij"), kilde="p", niveau="full", maks_antal=3)
    assert len(ud.poster) == 3 and ud.udeladt_antal == 7
    assert any("antals-budget" in x for x in ud.udeladt_grunde)


def test_tegn_budget_skaerer_HELE_poster():
    """En halv linje er ikke en kortere sandhed — den er en anden sandhed."""
    ud = g.afgraens(["x" * 40, "y" * 40, "z" * 40], kilde="p", niveau="full",
                    maks_antal=10, maks_tegn=90)
    assert ud.poster == ("x" * 40, "y" * 40)
    assert all(len(p) == 40 for p in ud.poster), "en post blev klippet midt over"
    assert any("tegn-budget" in x for x in ud.udeladt_grunde)


def test_tegn_budget_beholder_ALTID_mindst_en():
    """En enkelt post over loftet er stadig bedre end ingenting — og en tom
    liste ville se ud som «der var intet», ikke som «den var for stor»."""
    ud = g.afgraens(["x" * 5000], kilde="p", niveau="full", maks_tegn=100)
    assert len(ud.poster) == 1


# -------------------------------------------------------- niveauerne

def test_none_fjerner_alt_naar_gaten_er_TAENDT(monkeypatch):
    monkeypatch.setattr(g, "HAANDHAEV", True)
    ud = g.afgraens(list("abc"), kilde="p", niveau="none")
    assert ud.poster == () and ud.udeladt_antal == 3
    assert ud.haandhaevet is True


def test_none_fjerner_INTET_i_skygge(monkeypatch):
    """Skygge er hele fremgangsmaaden: regn ud hvad du VILLE fjerne, og
    fjern intet, indtil tallene er set i produktion."""
    monkeypatch.setattr(g, "HAANDHAEV", False)
    ud = g.afgraens(list("abc"), kilde="p", niveau="none")
    assert len(ud.poster) == 3, "gaten skar i skygge-tilstand"
    assert "SKYGGE" in ud.herkomst()
    assert ud.haandhaevet is False


def test_summary_er_faerre_ikke_ingenting(monkeypatch):
    monkeypatch.setattr(g, "HAANDHAEV", True)
    ud = g.afgraens(list("abcdefghi"), kilde="p", niveau="summary", maks_antal=6)
    assert 0 < len(ud.poster) < 9, f"summary gav {len(ud.poster)}"


def test_full_slipper_alt_igennem():
    ud = g.afgraens(list("abc"), kilde="p", niveau="full", maks_antal=6)
    assert len(ud.poster) == 3 and ud.udeladt_antal == 0


# ------------------------------------------------- niveauet pr. bruger

def test_ejeren_faar_full_og_medlemmet_none():
    """Grundsandhed fra husstandsregistret, ikke et opdigtet eksempel."""
    from core.identity.users import load_users
    from core.identity.workspace_context import user_context

    ejer = next((u for u in load_users() if (u.role or "").lower() == "owner"), None)
    medlem = next((u for u in load_users() if (u.role or "").lower() != "owner"), None)
    if not ejer or not medlem:
        pytest.skip("husstandsregistret har ikke baade en ejer og et medlem")

    with user_context(discord_id=ejer.discord_id):
        assert g.gaeldende_niveau() == "full"
    with user_context(discord_id=medlem.discord_id):
        assert g.gaeldende_niveau() == "none"


# ------------------------------------------------------- selv-sikkerhed

def test_afgraens_kaster_aldrig(monkeypatch):
    """En gate der vaelter prompt-samlingen er vaerre end ingen gate."""
    monkeypatch.setattr(g, "gaeldende_niveau",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    try:
        ud = g.afgraens(list("abc"), kilde="p")
    except Exception:
        pytest.fail("gaten kastede")
    assert len(ud.poster) == 3, "en fejlet gate maa ikke aede indholdet"


def test_gaeldende_niveau_kaster_aldrig(monkeypatch):
    monkeypatch.setattr("core.identity.workspace_context.current_user_id",
                        lambda: (_ for _ in ()).throw(RuntimeError("nede")))
    assert g.gaeldende_niveau() == g.UBESTEMT


# ---------------------------------------------- maaleren skal se gaten

def test_profile_enforcement_FINDER_gaten():
    """`profile_enforcement` ledte efter netop denne funktion og rapporterede
    «ingen haandhaever». Nu findes den — men den er i skygge, og det er en
    TREDJE tilstand der ikke maa skrives sammen med de to andre."""
    from core.runtime.profile_enforcement import maal
    post = maal({"cross_session_context": "none"})["cross_session_context"]
    assert post["haandhaevet"] is False, "en gate i skygge beskytter ingenting"
    assert "SKYGGE" in post["kilde"]
    assert post["kilde"] != "ingen haandhaever"
    assert post["kilde"] != "maaling fejlede"


# ------------------------------------------- de to AEGTE kilder er koblet paa

def test_arc_sektionen_kalder_gaten():
    """En gate ingen kalder er den fejlform huset oftest laver.

    AST, ikke tekstsoegning: `afgraens` kunne staa i en kommentar.
    """
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path(
        "core/services/prompt_sections/cross_session_arc.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "cross_session_arc_section"), None)
    assert fn is not None, "arc-sektionen er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "afgraens" in kaldt, "arc-sektionen gaar uden om gaten"


def test_traad_sektionen_kalder_gaten():
    import ast
    import pathlib
    træ = ast.parse(pathlib.Path("core/services/cross_session_threads.py").read_text())
    fn = next((n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
               and n.name == "build_cross_session_threads_prompt_section"), None)
    assert fn is not None, "traad-sektionen er flyttet"
    kaldt = {getattr(k.func, "id", "") for k in ast.walk(fn) if isinstance(k, ast.Call)}
    assert "afgraens" in kaldt, "traad-sektionen gaar uden om gaten"


def test_arcens_cache_baerer_IKKE_et_niveau_over_til_naeste_bruger():
    """Cachen holdt foer den FAERDIGE tekst. Afgraensningen afhaenger af
    BRUGEREN, saa en cachet faerdig tekst ville servere den ene brugers niveau
    til den naeste — en lille cache-aendring der ville have vaeret et aegte laek.
    """
    import ast
    import pathlib
    kilde = pathlib.Path(
        "core/services/prompt_sections/cross_session_arc.py").read_text()
    assert "_cached_text" not in kilde, \
        "cachen holder faerdig tekst igen — én brugers niveau kan naa den naeste"
    træ = ast.parse(kilde)
    fn = next(n for n in ast.walk(træ) if isinstance(n, ast.FunctionDef)
              and n.name == "cross_session_arc_section")
    # Gaten skal koere paa HVER kald, ikke kun naar cachen er kold: den ligger
    # derfor efter cache-blokken, ikke inde i den.
    kaldt = [k for k in ast.walk(fn) if isinstance(k, ast.Call)
             and getattr(k.func, "id", "") == "afgraens"]
    assert kaldt, "gaten kaldes ikke i arc-sektionen"
