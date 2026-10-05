"""Monitoren paa vaerktoejer pr. runde: hvad der fyrer den, og hvad der IKKE goer.

`beacon_vagt.py`'s foerste udgave meldte «ingen haendelser» i en halv time
fordi dens moenster ikke kunne ramme noget. Stilhed lignede ro. Derfor maales
SQL'en her mod en rigtig sqlite — en fake forbindelse der svarer det samme
uanset forespoergslen kan aldrig se at maalingen maaler ingenting.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.batch_maaling_monitor import OVER, UNDER, vurder
from scripts.maal_vaerktoejer_pr_runde import dagsserie


def _dag(rows_pr_runde: float, runder: int, dage_siden: int) -> list[dict]:
    """En dag som dagsserie() ville returnere den."""
    return [{"runder": runder, "pr_runde": rows_pr_runde, "dag": str(dage_siden)}]


def _serie(*dage: tuple[float, int]) -> list[dict]:
    return [{"runder": r, "pr_runde": p} for p, r in dage]


def test_tier_i_stoejgulvet() -> None:
    """Basislinjen er 1,54 +/- 0,10. Alt derimellem er ikke en aendring."""
    dom, snit, taellende = vurder(_serie((1.52, 900), (1.58, 900), (1.61, 900)))
    assert dom is None
    assert taellende == 3
    assert UNDER < snit < OVER


def test_fyrer_naar_den_landede() -> None:
    dom, snit, _ = vurder(_serie((1.90, 900), (2.10, 900), (2.00, 900)))
    assert dom == "landede"
    assert snit > OVER


def test_fyrer_ogsaa_naar_tallet_FALDT() -> None:
    """Et fald er ogsaa et svar — og det vigtigere af de to."""
    dom, snit, _ = vurder(_serie((1.20, 900), (1.30, 900), (1.25, 900)))
    assert dom == "faldt"
    assert snit < UNDER


def test_en_stille_dag_kan_ikke_fyre_den() -> None:
    """Tre runder paa en soendag maa ikke afgoere sagen.

    De to stille dage ligger VILDT over taersklen. Tog monitoren dem med,
    ville den fyre. Den stilleste dag i basislinjen havde 464 runder.
    """
    dom, _, taellende = vurder(_serie((1.55, 900), (9.00, 4), (9.00, 7)))
    assert dom is None, "en dag under MIN_RUNDER skal udelukkes"
    assert taellende == 1, "kun den travle dag taeller"


def test_for_lidt_data_er_ikke_det_samme_som_ro() -> None:
    """None uden snit betyder «ved ikke», ikke «uaendret»."""
    dom, snit, taellende = vurder(_serie((2.50, 900)))
    assert dom is None
    assert snit is None, "uden tre dage maa der ikke rapporteres et snit"
    assert taellende == 1


def test_sql_maaler_faktisk_noget_mod_rigtig_sqlite(tmp_path: Path) -> None:
    """Hele vejen: events + chat_messages ind, pr_runde ud.

    4 runder og 10 vaerktoejsresultater paa samme dag = 2,5 pr. runde.
    """
    db = tmp_path / "jarvis.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, "
                 "payload_json TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, role TEXT, "
                 "created_at TEXT)")
    da = (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    for runde in range(1, 5):
        conn.execute("INSERT INTO events (kind, payload_json, created_at) VALUES (?,?,?)",
                     ("runtime.agentic_round_start",
                      '{"run_id": "visible-test", "round": %d}' % runde, da))
    for _ in range(10):
        conn.execute("INSERT INTO chat_messages (role, created_at) VALUES ('tool', ?)", (da,))
    conn.commit()
    conn.close()

    serie = dagsserie(db, 14)
    assert len(serie) == 1, "én dag med runder"
    assert serie[0]["runder"] == 4
    assert serie[0]["vaerktoejskald"] == 10
    assert abs(float(serie[0]["pr_runde"]) - 2.5) < 0.01
    assert serie[0]["runs"] == 1
    assert serie[0]["flest_runder"] == 4


def test_graensen_slipper_ikke_hele_dagen_igennem(tmp_path: Path) -> None:
    """ISO-tidsstempler med 'T' sorterer EFTER et mellemrum.

    Brugte forespoergslen `datetime('now', ...)` som graense, ville en raekke
    15 dage gammel slippe med. Se memory `cheaplane_health_and_query_trap`.
    """
    db = tmp_path / "jarvis.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, kind TEXT, "
                 "payload_json TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, role TEXT, "
                 "created_at TEXT)")
    gammel = (datetime.now(UTC) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute("INSERT INTO events (kind, payload_json, created_at) VALUES (?,?,?)",
                 ("runtime.agentic_round_start", '{"run_id": "r", "round": 1}', gammel))
    conn.commit()
    conn.close()
    assert dagsserie(db, 14) == [], "en 30 dage gammel raekke maa ikke vaere med i 14-dages-vinduet"


# ── Raesonnerings-A/B'en, hængt paa samme monitor (5/10-2026) ───────────────

from scripts.batch_maaling_monitor import vurder_ab  # noqa: E402
from scripts.maal_raesonnering_ab import runder_pr_run_pr_dag  # noqa: E402


def _arm(*, raeson: int, dage: int, runder_pr_run: float, runs_pr_dag: int = 5) -> dict:
    pr_dag = {}
    for d in range(dage):
        pr_dag[f"2026-10-{d+6:02d}"] = {
            "runs": {f"r{d}-{i}" for i in range(runs_pr_dag)},
            "runder": int(runs_pr_dag * runder_pr_run),
        }
    return {"raeson": [raeson] * 30, "ud": [900] * 30, "runs": set(),
            "runder": 30, "pr_dag": pr_dag}


def test_ab_tier_naar_kun_én_arm_har_data():
    dom, linje = vurder_ab({"fuld": _arm(raeson=300, dage=5, runder_pr_run=12)})
    assert dom is None
    assert "én arm" in linje


def test_ab_melder_naar_KNAPPEN_ikke_blev_drejet():
    """Den daempede arm skal have ~0 raesonnering. Har den ikke det, maaler
    forsoeget ikke det det tror."""
    dom, linje = vurder_ab({
        "daempet": _arm(raeson=300, dage=5, runder_pr_run=12),
        "fuld": _arm(raeson=300, dage=5, runder_pr_run=12),
    })
    assert dom == "knappen_virker_ikke"
    assert "raesonnerer stadig" in linje


def test_en_braekket_knap_slaar_et_kvalitets_resultat():
    """RAEKKEFOELGEN er det vigtige.

    Her er forskellen enorm (12 mod 20 runder/run). Rapporterede monitoren
    den, ville den melde et kvalitets-resultat fra et forsoeg der aldrig blev
    koert — og det er vaerre end slet ingen maaling.
    """
    dom, _ = vurder_ab({
        "daempet": _arm(raeson=300, dage=5, runder_pr_run=20),
        "fuld": _arm(raeson=300, dage=5, runder_pr_run=12),
    })
    assert dom == "knappen_virker_ikke", "braekket knap skal vinde over enhver forskel"


def test_ab_tier_ved_for_lidt_data():
    dom, linje = vurder_ab({
        "daempet": _arm(raeson=0, dage=1, runder_pr_run=12),
        "fuld": _arm(raeson=0, dage=5, runder_pr_run=12),
    })
    assert dom is None
    assert "for lidt data" in linje


def test_ab_tier_naar_forskellen_er_inde_i_stoejen():
    """Den fulde arm svinger 12-16 runder/run; en forskel paa 1 er stoej."""
    d = _arm(raeson=0, dage=5, runder_pr_run=13)
    f = _arm(raeson=300, dage=5, runder_pr_run=12)
    list(f["pr_dag"].values())[0]["runder"] = 5 * 16
    dom, linje = vurder_ab({"daempet": d, "fuld": f})
    assert dom is None
    assert "runder/run" in linje


def test_ab_tier_ved_en_forskel_under_GULVET():
    """To perfekt stabile arme med 0,2 runders forskel er ikke et fund.

    Uden gulvet ville spredningen her vaere praecis nul, og enhver forskel
    ville saa overstige taersklen.
    """
    dom, _ = vurder_ab({
        "daempet": _arm(raeson=0, dage=5, runder_pr_run=12.2),
        "fuld": _arm(raeson=300, dage=5, runder_pr_run=12),
    })
    assert dom is None


def test_ab_melder_en_forskel_der_overstiger_stoejen():
    dom, linje = vurder_ab({
        "daempet": _arm(raeson=0, dage=5, runder_pr_run=20),
        "fuld": _arm(raeson=300, dage=5, runder_pr_run=12),
    })
    assert dom == "forskel"
    assert "daempet 20" in linje and "fuld 12" in linje


def test_tynde_dage_taeller_ikke_i_arm_serien():
    """Med 20 % eksponering er tynde dage reglen, ikke undtagelsen. Én run paa
    en soendag er ikke et datapunkt."""
    arm = _arm(raeson=0, dage=4, runder_pr_run=12, runs_pr_dag=5)
    arm["pr_dag"]["2026-10-20"] = {"runs": {"enlig"}, "runder": 99}
    serie = runder_pr_run_pr_dag(arm)
    assert len(serie) == 4, "dagen med én run skal udelades"
    assert max(serie) < 20, "99 runder paa én run maa ikke naa serien"
