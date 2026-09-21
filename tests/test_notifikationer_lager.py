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
