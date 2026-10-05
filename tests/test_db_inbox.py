"""Lageret bag indbakken — `inbox_items`' eget skema og dens atomare skrivninger.

`tests/test_inbox_state.py` måler REGLERNE (proveniens, bogføring) gennem
servicelaget. Denne fil måler **lageret selv**: skemaet, `UNIQUE`-betingelsen,
`INSERT OR IGNORE`-idempotensen, de to `UPDATE ... WHERE status = 'aaben'` der
gør afgørelse og påmindelse atomare, og ensure-én-gang-per-proces.

Hvorfor begge filer: et servicelag kan være rigtigt oven på et lager der taber
en skrivning i et kapløb, og en race ses ikke gennem en facade. Her kører to
rigtige forbindelser mod den samme fil.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox

BRUGER = "bjorn"


@pytest.fixture
def db(monkeypatch, tmp_path):
    sti = tmp_path / "inbox.db"

    @contextmanager
    def _connect():
        k = sqlite3.connect(sti, timeout=5.0)
        k.row_factory = sqlite3.Row
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return sti


def _opret(kilde_id: str, **kw):
    return db_inbox.opret_eller_hent(
        bruger_id=kw.pop("bruger_id", BRUGER),
        kildetype=kw.pop("kildetype", "job"),
        kilde_id=kilde_id, **kw)


# ── Skemaet ─────────────────────────────────────────────────────────────────

def test_skemaet_oprettes_doven_og_baerer_de_felter_visningen_kraever(db):
    """Visningen har seks felter per post (spec'ens afsnit «Felterne»). Mangler
    én i skemaet, opdager man det først når visningen bygges — og så er det en
    fejl i den anden fil."""
    _opret("job-1")
    with db_inbox.connect() as c:
        kolonner = {r[1] for r in c.execute("PRAGMA table_info(inbox_items)")}
    for n in ("bruger_id", "kildetype", "kilde_id", "oprettende_run_id",
              "verificeret_ejer", "kraever_handling", "status", "beskrivelse",
              "output_sti", "output_bytes", "paamindelser",
              "sidste_paamindelse_tur", "created_at", "afgjort_at"):
        assert n in kolonner, f"skemaet mangler {n}"


def test_UNIQUE_er_paa_bruger_OG_kildetype_OG_kilde_id(db):
    """Tre dele, ikke én. Samme kilde-id for to brugere er to poster; samme
    kilde-id med to kildetyper er også to. Var `UNIQUE` kun på kilde_id, kunne
    en brugers post blokere en andens registrering helt tavst."""
    _opret("delt", bruger_id=BRUGER, kildetype="job")
    _opret("delt", bruger_id="anden", kildetype="job")
    _opret("delt", bruger_id=BRUGER, kildetype="wakeup")
    with db_inbox.connect() as c:
        n = c.execute("SELECT count(*) FROM inbox_items WHERE kilde_id = 'delt'").fetchone()[0]
    assert n == 3


def test_ensure_koerer_DDL_en_gang_pr_proces(db, monkeypatch):
    """`CREATE TABLE IF NOT EXISTS` tager eksklusiv lås. Målt 9/9-2026 gav en
    ensure kaldt pr. brugerbesked «database is locked» med ~50 % frekvens.
    Vagten her er at flaget sættes, så anden skrivning springer DDL'en over."""
    assert db_inbox._skema_klar is False
    _opret("job-a")
    assert db_inbox._skema_klar is True
    # `sqlite3.Connection.execute` kan ikke patches (immutable type), og en
    # wrapper om forbindelsen ville maale MIN wrapper. `set_trace_callback` er
    # sqlites egen: den ser hver saetning der faktisk naar motoren, inklusive
    # dem der koeres af andre lag.
    ddl: list[str] = []

    @contextmanager
    def _sporende_connect():
        k = sqlite3.connect(db, timeout=5.0)
        k.row_factory = sqlite3.Row
        k.set_trace_callback(
            lambda sql: ddl.append(sql.strip()[:30])
            if "CREATE TABLE" in sql or "CREATE INDEX" in sql else None)
        try:
            yield k
            k.commit()
        finally:
            k.close()

    monkeypatch.setattr(db_inbox, "connect", _sporende_connect)
    _opret("job-b")
    db_inbox.liste(bruger_id=BRUGER)
    db_inbox.hent(bruger_id=BRUGER, kilde_id="job-b")
    assert ddl == [], f"DDL koerte igen: {ddl}"


# ── Idempotens og kapløb ────────────────────────────────────────────────────

def test_opret_to_gange_giver_SAMME_raekke_urort(db):
    a = _opret("job-i", beskrivelse="foerste")
    b = _opret("job-i", beskrivelse="anden-tekst-der-ikke-maa-vinde")
    assert a["post"]["created_at"] == b["post"]["created_at"]
    assert b["post"]["beskrivelse"] == "foerste", \
        "en genregistrering overskrev den oprindelige post"
    with db_inbox.connect() as c:
        assert c.execute("SELECT count(*) FROM inbox_items").fetchone()[0] == 1


def test_to_TRAADE_der_opretter_samtidigt_giver_EN_raekke(db):
    """Genlevering kan komme fra to processer. Taber en tråd kapløbet om
    indsættelsen, skal dens opslag finde den andens række — det ER det
    idempotente svar, og uden det ville den ene få en typet fejl."""
    _opret("varm-op")                      # skema klar foer traadene
    svar: list[dict] = []
    laas = threading.Barrier(2)

    def _kør():
        laas.wait()
        svar.append(_opret("job-samtidig"))

    t = [threading.Thread(target=_kør) for _ in range(2)]
    for x in t:
        x.start()
    for x in t:
        x.join()
    assert [s["status"] for s in svar] == ["ok", "ok"], svar
    with db_inbox.connect() as c:
        n = c.execute("SELECT count(*) FROM inbox_items WHERE kilde_id='job-samtidig'"
                      ).fetchone()[0]
    assert n == 1


def test_afgoer_to_gange_overskriver_IKKE_den_foerste_afgoerelse(db):
    _opret("job-d")
    a = db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-d",
                        ny_status=db_inbox.STATUS_DONE, grund="kvitteret")
    b = db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-d",
                        ny_status=db_inbox.STATUS_DROP, grund="noget andet")
    assert a["status"] == "ok"
    assert b == {"status": "allerede", "id": "job-d", "havde": db_inbox.STATUS_DONE}
    assert db_inbox.hent(bruger_id=BRUGER, kilde_id="job-d")["afgjort_grund"] == "kvitteret"


def test_afgoer_paa_et_UKENDT_id_melder_ukendt_ikke_ok(db):
    assert db_inbox.afgoer(bruger_id=BRUGER, kilde_id="nix",
                           ny_status=db_inbox.STATUS_DONE) == {"status": "ukendt",
                                                               "id": "nix"}


def test_afgoer_afviser_en_ikke_terminal_status(db):
    _opret("job-s")
    for s in (db_inbox.STATUS_AABEN, "noget-opdigtet", ""):
        r = db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-s", ny_status=s)
        assert r["status"] == "fejl", f"{s!r} slap igennem som terminal"


# ── Påmindelses-tælleren ────────────────────────────────────────────────────

def test_paamindelse_paa_en_LUKKET_post_taeller_ikke(db):
    """En afgjort post må ikke kunne samle påmindelser. Kunne den, ville
    Opgave 7's heed-rate blive målt på poster der aldrig gatede."""
    _opret("job-p")
    db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-p",
                    ny_status=db_inbox.STATUS_DROP, grund="nej")
    r = db_inbox.noter_paamindelse(bruger_id=BRUGER, kilde_id="job-p", tur="t1")
    assert r == {"status": "ikke_aaben", "id": "job-p", "havde": db_inbox.STATUS_DROP}
    assert db_inbox.hent(bruger_id=BRUGER, kilde_id="job-p")["paamindelser"] == 0


def test_paamindelse_paa_ukendt_id_melder_ukendt(db):
    _opret("varm-op")
    assert db_inbox.noter_paamindelse(bruger_id=BRUGER, kilde_id="nix",
                                      tur="t1")["status"] == "ukendt"


def test_paamindelse_uden_tur_er_en_TYPET_fejl(db):
    """Uden tur-nøgle kan samme runde tælle sig op til tærsklen. En tom tur er
    derfor ikke «ingen nøgle» — det er en fejl."""
    _opret("job-n")
    assert db_inbox.noter_paamindelse(bruger_id=BRUGER, kilde_id="job-n",
                                      tur="")["status"] == "fejl"
    assert db_inbox.hent(bruger_id=BRUGER, kilde_id="job-n")["paamindelser"] == 0


# ── Bruger-afgrænsningen ────────────────────────────────────────────────────

def test_liste_uden_bruger_giver_TOM_liste(db):
    _opret("job-1")
    _opret("job-2", bruger_id="anden")
    assert db_inbox.liste(bruger_id="") == []
    assert db_inbox.liste(bruger_id="   ") == []


def test_liste_kun_aabne_er_standard_og_kan_slaas_af(db):
    _opret("job-aaben")
    _opret("job-lukket")
    db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-lukket",
                    ny_status=db_inbox.STATUS_DONE)
    aabne = [p["id"] for p in db_inbox.liste(bruger_id=BRUGER)]
    alle = [p["id"] for p in db_inbox.liste(bruger_id=BRUGER, kun_aabne=False)]
    assert aabne == ["job-aaben"]
    assert sorted(alle) == ["job-aaben", "job-lukket"], \
        "en lukket post kunne ikke FINDES — «vaek fra forsiden» er ikke «slettet»"


def test_afgoer_og_hent_afviser_tom_bruger(db):
    _opret("job-x")
    assert db_inbox.afgoer(bruger_id="", kilde_id="job-x",
                           ny_status=db_inbox.STATUS_DONE)["status"] == "fejl"
    assert db_inbox.hent(bruger_id="", kilde_id="job-x") is None
    assert db_inbox.hent(bruger_id=BRUGER, kilde_id="job-x")["status"] == \
        db_inbox.STATUS_AABEN


def test_maks_loftet_respekteres_og_er_mindst_en(db):
    for i in range(5):
        _opret(f"job-{i}")
    assert len(db_inbox.liste(bruger_id=BRUGER, maks=3)) == 3
    # `max(int(maks), 1)`: et loft paa 0 eller negativt maa ikke blive til
    # «ingen graense» i SQL — det ville give hele tabellen.
    assert len(db_inbox.liste(bruger_id=BRUGER, maks=0)) == 1
    assert len(db_inbox.liste(bruger_id=BRUGER, maks=-7)) == 1


# ── Opgave 8: udløb ─────────────────────────────────────────────────────────

def _i(sek: float) -> str:
    from datetime import UTC, datetime, timedelta
    return (datetime.now(UTC) + timedelta(seconds=sek)).isoformat()


def test_en_UDLOEBET_post_gater_ikke_men_kan_stadig_laeses(db):
    """Udløb er en TERMINAL tilstand, ikke en sletning. `kraever_handling`
    falder, så en post ikke kan gate i det uendelige ved at ingen rører den."""
    _opret("job-u")
    db_inbox.saet_udloeb(bruger_id=BRUGER, kilde_id="job-u", expires_at=_i(-60))
    assert db_inbox.er_udloebet(db_inbox.hent(bruger_id=BRUGER, kilde_id="job-u")) is True
    db_inbox.fej_udloebne()
    p = db_inbox.hent(bruger_id=BRUGER, kilde_id="job-u")
    assert p["status"] == db_inbox.STATUS_UDLOEBET
    assert p["kraever_handling"] is False
    assert p["afgjort_grund"] == "udloebet", "Opgave 7 kan ikke skelne udloeb fra andet"


def test_en_post_UDEN_frist_udloeber_ALDRIG(db):
    """Tom `expires_at` er et bevidst valg. Og den må ikke fejes: tom streng
    sorterer FØR enhver ISO-dato, så uden `expires_at != ''` i WHERE ville HVER
    post uden frist blive fejet."""
    _opret("job-evig")
    assert db_inbox.er_udloebet(db_inbox.hent(bruger_id=BRUGER, kilde_id="job-evig")) is False
    assert db_inbox.fej_udloebne()["fejet"] == 0
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-evig")["status"] == db_inbox.STATUS_AABEN


def test_en_UPARSABEL_frist_BEVARER_posten(db):
    """Fald mod at bevare. Godkendelsernes præcedens gør det modsatte
    (`except ValueError: expires_at = now`, altså «udløbet NU»), og det er
    forkert her: en skrivefejl i et tidsstempel må ikke lukke en forpligtelse."""
    _opret("job-skrald")
    db_inbox.saet_udloeb(bruger_id=BRUGER, kilde_id="job-skrald",
                         expires_at="i morgen engang")
    p = db_inbox.hent(bruger_id=BRUGER, kilde_id="job-skrald")
    assert db_inbox.er_udloebet(p) is False
    assert p["status"] == db_inbox.STATUS_AABEN


def test_en_FREMTIDIG_frist_udloeber_ikke(db):
    _opret("job-frem")
    db_inbox.saet_udloeb(bruger_id=BRUGER, kilde_id="job-frem", expires_at=_i(3600))
    assert db_inbox.fej_udloebne()["fejet"] == 0
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-frem")["status"] == db_inbox.STATUS_AABEN


def test_et_NAIVT_tidsstempel_laeses_som_UTC_i_BEGGE_retninger(db):
    """Ellers sammenlignes æbler og pærer. `db_governance` gør det samme.

    BEGGE sider af nu, og det er ikke overdrevet: min første udgave målte kun
    den ene, og en mutation der læste naive stempler som UTC+12 slap igennem.
    Jeg havde fortegnet galt — en POSITIV offset gør et naivt stempel
    *tidligere* i UTC, så en post 1 time gammel blev 13 timer gammel og stadig
    var «udløbet». Testen bestod for den forkerte grund.

    Med et stempel på hver side af nu flipper mindst ét svar ved enhver forkert
    zone, uanset fortegn.
    """
    from datetime import UTC, datetime, timedelta
    nu = datetime.now(UTC)
    fortid = (nu - timedelta(hours=6)).replace(tzinfo=None).isoformat()
    fremtid = (nu + timedelta(hours=6)).replace(tzinfo=None).isoformat()
    assert db_inbox.er_udloebet({"expires_at": fortid, "kilde_id": "x"}, nu) is True
    assert db_inbox.er_udloebet({"expires_at": fremtid, "kilde_id": "x"}, nu) is False


def test_udloeb_PRAECIS_paa_graensen_er_udloebet(db):
    """Én side valgt og pinnet."""
    from datetime import UTC, datetime
    nu = datetime.now(UTC)
    assert db_inbox.er_udloebet({"expires_at": nu.isoformat(), "kilde_id": "x"}, nu) is True


def test_fejeren_koert_TO_gange_taeller_ikke_samme_post_to_gange(db):
    _opret("job-to")
    db_inbox.saet_udloeb(bruger_id=BRUGER, kilde_id="job-to", expires_at=_i(-60))
    assert db_inbox.fej_udloebne()["fejet"] == 1
    assert db_inbox.fej_udloebne()["fejet"] == 0, "fejeren taalte samme post igen"


def test_fejeren_roerer_ikke_en_AFGJORT_post(db):
    """En post jeg selv har kvitteret må ikke få sin status skrevet om til
    `udloebet` — det ville skjule at jeg traf en beslutning."""
    _opret("job-mit")
    db_inbox.saet_udloeb(bruger_id=BRUGER, kilde_id="job-mit", expires_at=_i(-60))
    db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-mit",
                    ny_status=db_inbox.STATUS_DONE, grund="kvitteret")
    db_inbox.fej_udloebne()
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-mit")["status"] == db_inbox.STATUS_DONE


# ── Produsenten: hvem får en frist? (5/10-2026) ──────────────────────────────
#
# Funktionerne ovenfor var grundigt dækket. Det var FORBINDELSEN der manglede:
# `saet_udloeb` havde nul kaldere uden for tests, `er_udloebet` blev læst nul
# steder, og `fej_udloebne` blev aldrig kørt. Målt i drift: NUL poster havde
# nogensinde båret en frist, så hele subsystemet var virkningsløst — og de
# tests der fandtes, kunne ikke se det, fordi de kaldte funktionerne selv.

def test_en_GATENDE_post_faar_en_frist_og_en_informativ_goer_IKKE(db):
    """Reglen følger spec'ens egen sætning om HVORFOR udløb findes: «en post
    ikke kan gate i det uendelige ved at ingen rører den.»

    Derfor fristen på de poster der KAN nægte en mutation — ikke på alle. En
    informativ post uden frist er harmløs; en blokerende post uden frist er en
    permanent lås.
    """
    gatende = _opret("job-gater", kraever_handling=True)["post"]
    informativ = _opret("job-info")["post"]
    assert gatende["expires_at"] != "", "en gatende post fik ingen frist"
    assert db_inbox.er_udloebet(gatende) is False, "fristen laa i fortiden"
    assert informativ["expires_at"] == "", "en informativ post fik en frist"


def test_en_BLOKERENDE_brugerpost_faar_ogsaa_en_frist(db):
    """Bjørns `bloker` er den anden vej ind i gaten. Den skal bære samme
    grænse — ellers kunne netop den post låse ham fast for evigt, og det var
    dead-locken i `mark_wakeup_consumed` han selv pegede på."""
    p = _opret("bug-x", kildetype="bug", verificeret_ejer=db_inbox.EJER_BRUGER,
               kraever_handling=True, bloker=True)["post"]
    assert p["expires_at"] != ""


def test_en_genaabnet_post_arver_IKKE_en_doed_frist(db):
    """`genaabn_af_kilde` sætter `kraever_handling = 0`, så posten ikke længere
    kan gate. Ryddes fristen ikke SAMME sted, er posten død igen i samme
    sekund: `er_udloebet` er beregnet ved læsning, og den arvede frist ligger
    i fortiden. Genåbningen ville være en no-op der så ud som en succes."""
    _opret("job-gen", kraever_handling=True)
    db_inbox.saet_udloeb(bruger_id=BRUGER, kilde_id="job-gen", expires_at=_i(-60))
    db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-gen",
                    ny_status=db_inbox.STATUS_DROP, grund="udsat")
    g = db_inbox.genaabn_af_kilde(bruger_id=BRUGER, kilde_id="job-gen")
    assert g["status"] == "ok", g
    p = db_inbox.hent(bruger_id=BRUGER, kilde_id="job-gen")
    assert p["status"] == db_inbox.STATUS_AABEN
    assert p["expires_at"] == "", "den genaabnede post arvede en doed frist"
    assert db_inbox.er_udloebet(p) is False


def test_fejeren_BAGUDFYLDER_en_frist_paa_en_gatende_post_uden(db):
    """Produsenten sætter kun en frist ved INDSÆTTELSE. En post der blev
    oprettet før reglen fandtes stod derfor med tom frist — og tom betyder
    «udløber ALDRIG», altså den permanente lås Opgave 8 findes for at
    forhindre.

    Målt i drift 5/10-2026: `wake-467df5d319` (oprettet 04:57, før fixet kl.
    06:34) GATEDE med tom frist. Fejeren er den eneste vej der ser ALLE åbne
    poster, uanset hvem der skrev dem, så bagudfyldningen hører her.

    Rækken skrives i hånden med tom frist: `_opret` ville selv sætte den nu.
    """
    _opret("job-gammel", kraever_handling=True)
    with db_inbox.connect() as c:
        c.execute("UPDATE inbox_items SET expires_at = '' "
                  "WHERE bruger_id = ? AND kilde_id = ?", (BRUGER, "job-gammel"))
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-gammel")["expires_at"] == ""
    r = db_inbox.fej_udloebne()
    assert r["bagudfyldt"] == 1, r
    p = db_inbox.hent(bruger_id=BRUGER, kilde_id="job-gammel")
    assert p["expires_at"] != "", "den gatende post fik stadig ingen frist"
    assert db_inbox.er_udloebet(p) is False, "bagudfyldningen lagde fristen i fortiden"


def test_bagudfyldningen_roerer_IKKE_en_informativ_post(db):
    """Samme grænse som produsenten: en informerende post uden frist er
    harmløs. Blev den bagudfyldt, ville hver eneste notifikation i huset
    pludselig kunne udløbe — og det er ikke hvad spec'en bad om."""
    _opret("job-info-gammel")
    with db_inbox.connect() as c:
        c.execute("UPDATE inbox_items SET expires_at = '' "
                  "WHERE bruger_id = ? AND kilde_id = ?", (BRUGER, "job-info-gammel"))
    r = db_inbox.fej_udloebne()
    assert r["bagudfyldt"] == 0, r
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-info-gammel")["expires_at"] == ""


def test_bagudfyldningen_er_IDEMPOTENT(db):
    """Kørt to gange må den ikke give en NY frist hver gang — så ville en
    post aldrig kunne udløbe, uanset hvor længe den stod."""
    _opret("job-idem", kraever_handling=True)
    with db_inbox.connect() as c:
        c.execute("UPDATE inbox_items SET expires_at = '' "
                  "WHERE bruger_id = ? AND kilde_id = ?", (BRUGER, "job-idem"))
    assert db_inbox.fej_udloebne()["bagudfyldt"] == 1
    foerste = db_inbox.hent(bruger_id=BRUGER, kilde_id="job-idem")["expires_at"]
    assert db_inbox.fej_udloebne()["bagudfyldt"] == 0, "fristen blev sat igen"
    assert db_inbox.hent(bruger_id=BRUGER, kilde_id="job-idem")["expires_at"] == foerste


# ── Opgave 9: kildens terminale tilstand ────────────────────────────────────

def test_exit_0_NEDGRADERER_posten_uden_at_nogen_kaldte_done(db):
    """Den blokerede ligevægt: intet lukkede et job der er exit 0 af sig selv."""
    _opret("job-ok")
    r = db_inbox.meld_kilde_faerdig(bruger_id=BRUGER, kilde_id="job-ok", exit_kode=0)
    assert r["status"] == "ok"
    p = db_inbox.hent(bruger_id=BRUGER, kilde_id="job-ok")
    assert p["status"] == db_inbox.STATUS_AFSLUTTET_AF_KILDE
    assert p["kraever_handling"] is False
    # NEDGRADERING, ikke sletning — beviset staar.
    assert p["afgjort_grund"] == "kilden meldte exit 0"


def test_exit_1_lukker_IKKE_posten(db):
    """En fejlet opgave er netop en der kræver handling — det er hele grunden
    til at panelet findes."""
    _opret("job-fejl")
    r = db_inbox.meld_kilde_faerdig(bruger_id=BRUGER, kilde_id="job-fejl", exit_kode=1)
    assert r["status"] == "ikke_afgjort"
    assert "exit 1" in r["grund"]
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-fejl")["status"] == db_inbox.STATUS_AABEN


def test_en_FORSVUNDET_kilde_er_hverken_lukket_eller_gatende_for_evigt(db):
    """`None` er «kilden er forsvundet», ikke «færdig». Posten står åben, og
    visningen giver den `status_ukendt` — sin egen klasse."""
    _opret("job-vaek")
    r = db_inbox.meld_kilde_faerdig(bruger_id=BRUGER, kilde_id="job-vaek", exit_kode=None)
    assert r["status"] == "ikke_afgjort"
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-vaek")["status"] == db_inbox.STATUS_AABEN


def test_kilden_meldt_TO_gange_er_idempotent(db):
    _opret("job-2x")
    a = db_inbox.meld_kilde_faerdig(bruger_id=BRUGER, kilde_id="job-2x", exit_kode=0)
    b = db_inbox.meld_kilde_faerdig(bruger_id=BRUGER, kilde_id="job-2x", exit_kode=0)
    assert a["status"] == "ok"
    assert b == {"status": "allerede", "id": "job-2x",
                 "havde": db_inbox.STATUS_AFSLUTTET_AF_KILDE}


def test_kilden_kan_ikke_GENAABNE_en_post_jeg_har_lukket(db):
    _opret("job-lukket")
    db_inbox.afgoer(bruger_id=BRUGER, kilde_id="job-lukket",
                    ny_status=db_inbox.STATUS_DONE, grund="kvitteret")
    r = db_inbox.meld_kilde_faerdig(bruger_id=BRUGER, kilde_id="job-lukket", exit_kode=0)
    assert r["status"] == "allerede" and r["havde"] == db_inbox.STATUS_DONE
    assert db_inbox.hent(bruger_id=BRUGER,
                         kilde_id="job-lukket")["afgjort_grund"] == "kvitteret"


def test_en_UKENDT_kilde_melder_ukendt(db):
    _opret("varm-op")
    assert db_inbox.meld_kilde_faerdig(bruger_id=BRUGER, kilde_id="nix",
                                       exit_kode=0)["status"] == "ukendt"


# ── Opgave 11: retention ────────────────────────────────────────────────────

def _afgjort_for(kilde_id: str, dage: float):
    from datetime import UTC, datetime, timedelta
    ts = (datetime.now(UTC) - timedelta(days=dage)).isoformat()
    with db_inbox.connect() as c:
        c.execute("UPDATE inbox_items SET status = ?, afgjort_at = ? WHERE kilde_id = ?",
                  (db_inbox.STATUS_DONE, ts, kilde_id))


def test_en_LUKKET_post_uden_for_vinduet_falder_ud_af_den_aktive_visning(db):
    _opret("job-gammel")
    _afgjort_for("job-gammel", db_inbox._RETENTION_DAGE + 1)
    aktiv = [p["id"] for p in db_inbox.liste_aktiv(bruger_id=BRUGER)]
    assert "job-gammel" not in aktiv
    # Men den kan stadig FINDES. «Vaek fra forsiden» er ikke «slettet».
    alle = [p["id"] for p in db_inbox.liste(bruger_id=BRUGER, kun_aabne=False)]
    assert "job-gammel" in alle


def test_en_NYLIGT_lukket_post_er_stadig_i_den_aktive_visning(db):
    _opret("job-ny")
    _afgjort_for("job-ny", 1)
    assert "job-ny" in [p["id"] for p in db_inbox.liste_aktiv(bruger_id=BRUGER)]


def test_retention_fjerner_IKKE_en_post_der_stadig_gater(db):
    """Uanset alder. En åben post har ingen aldersgrænse her — kunne vinduet
    fjerne den, ville en blokering kunne skjule sig selv ved at blive gammel."""
    _opret("job-aaben")
    from datetime import UTC, datetime, timedelta
    gammel = (datetime.now(UTC) - timedelta(days=365)).isoformat()
    with db_inbox.connect() as c:
        c.execute("UPDATE inbox_items SET created_at = ? WHERE kilde_id = 'job-aaben'",
                  (gammel,))
    assert "job-aaben" in [p["id"] for p in db_inbox.liste_aktiv(bruger_id=BRUGER)]


def test_en_post_UDEN_lukke_tidspunkt_bevares(db):
    """Mangler tidsstemplet, må den ikke falde ud af vinduet ved et uheld."""
    _opret("job-intet-ts")
    with db_inbox.connect() as c:
        c.execute("UPDATE inbox_items SET status = ?, afgjort_at = '' "
                  "WHERE kilde_id = 'job-intet-ts'", (db_inbox.STATUS_DONE,))
    assert "job-intet-ts" in [p["id"] for p in db_inbox.liste_aktiv(bruger_id=BRUGER)]


def test_NUL_poster_uden_for_vinduet_lader_visningen_uaendret(db):
    for i in range(3):
        _opret(f"job-{i}")
    assert len(db_inbox.liste_aktiv(bruger_id=BRUGER)) == 3


def test_liste_aktiv_afviser_tom_bruger(db):
    _opret("job-x")
    assert db_inbox.liste_aktiv(bruger_id="") == []
