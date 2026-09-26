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
