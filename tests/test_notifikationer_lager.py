# tests/test_notifikationer_lager.py
from __future__ import annotations


def test_opret_og_aabne(isolated_runtime) -> None:
    from core.services import notifikationer as n

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-1", titel="Vil du tillade bash?")
    raekker = n.aabne("bjorn", er_owner=True)
    assert [r["id"] for r in raekker] == [nid]
    assert raekker[0]["slags"] == "approval"
    assert raekker[0]["klaret"] is None


def test_samme_ref_lander_kun_een_gang(isolated_runtime) -> None:
    """En gen-udsendt haendelse maa ikke give to rakker for samme godkendelse."""
    from core.services import notifikationer as n

    a = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    b = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X igen")
    assert a == b
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_uden_ref_maa_gerne_ligne_hinanden(isolated_runtime) -> None:
    """To paamindelser er to paamindelser — kun ejede raekker afdubleres."""
    from core.services import notifikationer as n

    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")
    n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Husk mælk")
    assert len(n.aabne("bjorn", er_owner=True)) == 2


def test_luk_fjerner_fra_feeden_men_beholder_raekken(isolated_runtime) -> None:
    """To-do-listen tommes i fladen; raekken bliver for at en gen-udsendt
    haendelse ikke kan genaabne noget der lige er klaret."""
    from core.services import notifikationer as n
    from core.runtime.db import connect

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    n.luk(nid, "approved")
    assert n.aabne("bjorn", er_owner=True) == []
    with connect() as conn:
        raekke = conn.execute("SELECT udfald FROM notifikationer WHERE id=?", (nid,)).fetchone()
    assert raekke[0] == "approved"
    # Og den kan ikke genaabnes af den samme ref.
    igen = n.opret(user_id="bjorn", slags="approval", kilde="approval", ref="a-1", titel="X")
    assert igen == nid
    assert n.aabne("bjorn", er_owner=True) == []


def test_kaploeb_om_samme_ref_returnerer_konkurrentens_id(isolated_runtime) -> None:
    """To samtidige opret()-kald for samme (slags, ref) maa ALDRIG give
    sqlite3.IntegrityError — det unikke indeks ux_notif_ref rammer den ene.

    Simuleres deterministisk uden traade (ingen flaky timing): en RAA,
    separat forbindelse skriver og committer den konkurrerende raekke
    PRAESIS i det oejeblik opret() selv er ved at skrive sin — det er
    kaploebsvinduet, uanset om opret() spoerger foerst eller indsaetter
    foerst.
    """
    import sqlite3

    from core.runtime import db as db_module
    from core.services import notifikationer as n

    konkurrent_id = "konkurrent-vandt-kaploebet"

    conn = db_module.connect()
    orig_execute = conn.execute

    def wrapper(sql, *args, **kwargs):
        if isinstance(sql, str) and sql.strip().startswith("INSERT INTO notifikationer"):
            # Fjern wrapperen foerst, saa den raa forbindelses eget INSERT
            # (nedenfor) ikke selv trigger denne gren igen.
            conn.execute = orig_execute
            raa = sqlite3.connect(db_module.DB_PATH)
            try:
                raa.execute(
                    "INSERT INTO notifikationer"
                    " (id, user_id, slags, kilde, ref, session_id, titel, tekst, oprettet)"
                    " VALUES (?,?,?,?,?,?,?,?,?)",
                    (konkurrent_id, "bjorn", "approval", "approval", "a-1", None,
                     "Konkurrentens titel", "", n._nu()))
                raa.commit()
            finally:
                raa.close()
        return orig_execute(sql, *args, **kwargs)

    conn.execute = wrapper
    try:
        resultat_id = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                               ref="a-1", titel="Vores titel")
    finally:
        conn.execute = orig_execute

    assert resultat_id == konkurrent_id
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_ryd_gamle_fjerner_kun_klarede(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.services import notifikationer as n
    from core.runtime.db import connect

    aaben = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Aaben")
    gammel = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Gammel")
    n.luk(gammel, "seen")
    for_laenge_siden = (datetime.now(UTC) - timedelta(days=9)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET klaret=? WHERE id=?", (for_laenge_siden, gammel))
        conn.commit()

    assert n.ryd_gamle(dage=7) == 1
    with connect() as conn:
        tilbage = [r[0] for r in conn.execute("SELECT id FROM notifikationer").fetchall()]
    assert tilbage == [aaben]


def test_afsluttede_er_historikken_og_aabne_er_to_do(isolated_runtime) -> None:
    """To lister over SAMME tabel, adskilt af `klaret`. Foer fandtes kun den
    ene, og et svar slettede sit eget spoer (Bjoern 26/9-2026)."""
    from core.services import notifikationer as n

    aaben = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Aaben")
    lukket = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Lukket")
    n.luk(lukket, "godkendt")

    assert [r["id"] for r in n.aabne("bjorn", er_owner=True)] == [aaben]
    historik = n.afsluttede("bjorn")
    assert [r["id"] for r in historik] == [lukket]
    assert historik[0]["udfald"] == "godkendt"
    assert historik[0]["klaret"] is not None


def test_afsluttede_ser_kun_egne_og_kun_inden_for_vinduet(isolated_runtime) -> None:
    from datetime import UTC, datetime, timedelta
    from core.services import notifikationer as n
    from core.runtime.db import connect

    min_egen = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Min")
    n.luk(min_egen, "seen")
    andens = n.opret(user_id="mikkel", slags="reminder", kilde="egen", titel="Mikkels")
    n.luk(andens, "seen")
    gammel = n.opret(user_id="bjorn", slags="reminder", kilde="egen", titel="Gammel")
    n.luk(gammel, "seen")
    for_laenge_siden = (datetime.now(UTC) - timedelta(days=9)).isoformat()
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET klaret=? WHERE id=?", (for_laenge_siden, gammel))
        conn.commit()

    assert [r["id"] for r in n.afsluttede("bjorn")] == [min_egen]


def test_releasepostens_data_kan_opdateres_uden_at_skifte_id(isolated_runtime) -> None:
    from core.services import notifikationer as n

    nid = n.opret(
        user_id="bjorn", slags="release", kilde="egen",
        ref="jarvis-desktop-v0.6.234", titel="Build 0.6.234 er undervejs",
        data={"version": "0.6.234", "phase": "building", "progress": 40},
    )

    assert n.opdater(
        "release", "jarvis-desktop-v0.6.234",
        titel="Version 0.6.234 er klar",
        data={"version": "0.6.234", "phase": "ready", "progress": 100},
    ) is True

    poster = n.aabne("bjorn", er_owner=True)
    assert [p["id"] for p in poster] == [nid]
    assert poster[0]["titel"] == "Version 0.6.234 er klar"
    assert poster[0]["data"] == {
        "version": "0.6.234", "phase": "ready", "progress": 100,
    }


def test_luk_foraeldede_lukker_gammel_aaben_run_done(isolated_runtime) -> None:
    """Maalt 24/10-2026: 3.551 run_done stod AABNE siden 25/9 fordi intet
    lukker dem. `ryd_gamle` rydder kun KLAREDE raekker, saa de voksede
    ubegraenset — og hver af dem kostede en DB-forbindelse + dekryptering
    pr. feed-poll, synkront i hovedtraaden (byger paa 213-545 % CPU)."""
    from core.services import notifikationer as n
    from core.runtime.db import connect

    nid = n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-gammel",
                  titel="Svar klar")
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET oprettet=? WHERE id=?",
                     ("2026-09-25T14:31:15.000000+00:00", nid))
        conn.commit()

    assert n.luk_foraeldede(2) == 1
    assert n.aabne("bjorn", er_owner=True) == []


def test_luk_foraeldede_rorer_ikke_dagens_run_done(isolated_runtime) -> None:
    """Et svar fra i dag er stadig noget nogen kan laese."""
    from core.services import notifikationer as n

    n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-ny",
            titel="Svar klar")
    assert n.luk_foraeldede(2) == 0
    assert len(n.aabne("bjorn", er_owner=True)) == 1


def test_luk_foraeldede_rorer_kun_run_done(isolated_runtime) -> None:
    """En gammel GODKENDELSE maa ikke lukkes: den venter paa et svar, og at
    lukke den ville vaere at afgoere den for brugeren."""
    from core.services import notifikationer as n
    from core.runtime.db import connect

    nid = n.opret(user_id="bjorn", slags="approval", kilde="approval",
                  ref="a-gammel", titel="Vil du tillade bash?")
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET oprettet=? WHERE id=?",
                     ("2026-09-25T14:31:15.000000+00:00", nid))
        conn.commit()

    assert n.luk_foraeldede(2) == 0
    assert [r["id"] for r in n.aabne("bjorn", er_owner=True)] == [nid]


def test_luk_foraeldede_bevarer_raekken_med_udfald(isolated_runtime) -> None:
    """Lukning er ikke en sletning — raekken skal kunne findes i historikken."""
    from core.services import notifikationer as n
    from core.runtime.db import connect

    nid = n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-x",
                  titel="Svar klar")
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET oprettet=? WHERE id=?",
                     ("2026-09-25T14:31:15.000000+00:00", nid))
        conn.commit()

    n.luk_foraeldede(2)
    with connect() as conn:
        raekke = conn.execute(
            "SELECT klaret, udfald FROM notifikationer WHERE id=?", (nid,)).fetchone()
    assert raekke is not None, "raekken skal bevares"
    assert raekke[0] is not None
    assert raekke[1] == "foraeldet"


def test_luk_foraeldede_er_idempotent(isolated_runtime) -> None:
    from core.services import notifikationer as n
    from core.runtime.db import connect

    nid = n.opret(user_id="bjorn", slags="run_done", kilde="run", ref="r-y",
                  titel="Svar klar")
    with connect() as conn:
        conn.execute("UPDATE notifikationer SET oprettet=? WHERE id=?",
                     ("2026-09-25T14:31:15.000000+00:00", nid))
        conn.commit()

    assert n.luk_foraeldede(2) == 1
    assert n.luk_foraeldede(2) == 0
