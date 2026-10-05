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
