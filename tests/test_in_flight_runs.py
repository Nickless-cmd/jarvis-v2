"""En genoptagelses-post der aldrig ældes.

`interrupted_for_session` havde ingen aldersgrænse: den returnerede den nyeste
`interrupted`-post for en session for evigt. Både `resume_context`
(`visible_runs.py:2399`) og selve prompt-teksten («du blev afbrudt»,
`in_flight_runs.py:232`) hænger på den — så en forældet post ville blive tilbudt
som genoptagelse i det uendelige.

Målt 11/9-2026: hele `interrupted`-populationen var test-affald, så virkningen
var nul i dag. Mekanismen var der alligevel. (Jarvis' fund.)
"""
from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest

from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _isoleret_lager(tmp_path, monkeypatch):
    lager: dict = {}
    monkeypatch.setattr(ifr, "_load", lambda: lager)
    monkeypatch.setattr(ifr, "_save", lambda d: lager.update(d))
    return lager


def _post(lager, rid, sid, *, status="interrupted", alder_timer=0.0):
    t = (datetime.now(UTC) - timedelta(hours=alder_timer)).isoformat()
    lager[rid] = {"run_id": rid, "session_id": sid, "status": status,
                  "started_at": t, "interrupted_at": t}


def test_frisk_afbrudt_tur_tilbydes(_isoleret_lager):
    _post(_isoleret_lager, "r1", "s1", alder_timer=1.0)
    assert (ifr.interrupted_for_session("s1") or {}).get("run_id") == "r1"


def test_forældet_post_tilbydes_IKKE(_isoleret_lager):
    """Grænsen er 24 timer. En tur afbrudt i forgårs er ikke noget man
    genoptager — den er historik."""
    _post(_isoleret_lager, "r1", "s1", alder_timer=48.0)
    assert ifr.interrupted_for_session("s1") is None


def test_post_UDEN_status_er_ikke_afbrudt(_isoleret_lager):
    """`or "interrupted"` gjorde en post uden status til en afbrudt tur — en
    default der læses som en dom."""
    _isoleret_lager["r1"] = {"run_id": "r1", "session_id": "s1",
                             "started_at": datetime.now(UTC).isoformat()}
    assert ifr.interrupted_for_session("s1") is None


def test_udaterbar_post_forsvinder_ikke_tavst(_isoleret_lager):
    """Fravær af tidsstempel er ikke bevis for ælde."""
    _isoleret_lager["r1"] = {"run_id": "r1", "session_id": "s1",
                             "status": "interrupted"}
    assert (ifr.interrupted_for_session("s1") or {}).get("run_id") == "r1"


def test_nyeste_vinder_stadig(_isoleret_lager):
    _post(_isoleret_lager, "gammel", "s1", alder_timer=5.0)
    _post(_isoleret_lager, "ny", "s1", alder_timer=0.5)
    assert (ifr.interrupted_for_session("s1") or {}).get("run_id") == "ny"


def test_ulaeseligt_tidsstempel_siger_HOEJT_fra(_isoleret_lager, caplog):
    """Fallbacken bevarer posten — men må ikke gøre det tavst.

    Jarvis' indvending: «en fallback der er sand om sit formål og kan være
    falsk om verden». Bliver et tidsstempel nogensinde skrevet i et format
    `fromisoformat` ikke kan læse, bliver posten en evighedskandidat uden at
    nogen opdager det."""
    import logging
    _isoleret_lager["r1"] = {"run_id": "r1", "session_id": "s1",
                             "status": "interrupted",
                             "interrupted_at": "11/09-2026 kl. 06:32"}
    with caplog.at_level(logging.WARNING):
        assert (ifr.interrupted_for_session("s1") or {}).get("run_id") == "r1"
    assert any("kunne ikke dateres" in r.message for r in caplog.records), \
        "posten blev beholdt tavst"


def test_helt_manglende_tidsstempel_er_ikke_en_advarsel(_isoleret_lager, caplog):
    """Der er forskel på «intet tidsstempel» (en gammel post) og «et
    tidsstempel vi ikke kan læse» (noget er i stykker)."""
    import logging
    _isoleret_lager["r1"] = {"run_id": "r1", "session_id": "s1",
                             "status": "interrupted"}
    with caplog.at_level(logging.WARNING):
        assert ifr.interrupted_for_session("s1") is not None
    assert not [r for r in caplog.records if "kunne ikke dateres" in r.message]


# ── ejer-filteret (12/9-2026) ────────────────────────────────────────────────
# Hvorfor: api- og runtime-processen kører SAMME app (`apps.api.jarvis_api.app:app`)
# mod SAMME delte `in_flight_runs.json`. Uden en ejer på posten stemplede en
# nedlukning af den ene den andens aktive ture — målt på `visible-d1fa743d`, der
# stod `interrupted`/`api-nedlukning` kl. 17:39:47 mens den kørte videre og
# sluttede `completed` 17:43:08. Reglen «enhver running-post ældre end N» var et
# svar om TID, ikke om ejerskab.


@pytest.fixture
def _proctab(monkeypatch):
    """Simulér /proc: ``{pid: starttid}``. Ukendt pid → None (= findes ikke)."""
    tab: dict[int, str | None] = {}
    monkeypatch.setattr(ifr, "_proc_start_ticks", lambda pid: tab.get(pid))
    tab[os.getpid()] = "555"        # os selv, så current_owner() er meningsfuld
    return tab


def _running(lager, rid, *, owner="", alder_s=0.0, sid="s1"):
    t = (datetime.now(UTC) - timedelta(seconds=alder_s)).isoformat()
    rec = {"run_id": rid, "session_id": sid, "status": "running", "started_at": t}
    if owner:
        rec["owner_proc"] = owner
    lager[rid] = rec


def test_current_owner_er_pid_OG_starttid(_proctab):
    """Linux genbruger pid'er. En bar pid kunne pege på en helt anden proces —
    så identiteten skal være pid + starttid, og være stabil inden for processen."""
    ejer = ifr.current_owner()
    assert ejer == f"{os.getpid()}:555"
    assert ifr.current_owner() == ejer


def test_owner_still_alive_har_TRE_udfald(_proctab):
    """True/False/None er ikke det samme: «findes ikke» er bevis, «kunne ikke
    læse» er et spørgsmål. Vi stempler ikke på et spørgsmål."""
    _proctab[2000] = "777"
    assert ifr.owner_still_alive("2000:777") is True      # lever
    assert ifr.owner_still_alive("2000:111") is False     # genbrugt pid
    assert ifr.owner_still_alive("9999:1") is False       # findes ikke
    _proctab[4000] = ""
    assert ifr.owner_still_alive("4000:1") is None        # kunne ikke afgøres
    assert ifr.owner_still_alive("") is None
    assert ifr.owner_still_alive("ikke-et-tal:1") is None


def test_mark_started_skriver_ejeren(_isoleret_lager, _proctab):
    ifr.mark_started(run_id="r1", session_id="s1", user_message="hej")
    assert _isoleret_lager["r1"]["owner_proc"] == ifr.current_owner()


def test_egen_proces_stemples_naar_vi_doer(_isoleret_lager, _proctab):
    """Vi er ved at lukke: vores EGNE kørende ture skal stemples — uanset alder."""
    _running(_isoleret_lager, "min", owner=ifr.current_owner(), alder_s=1.0)
    ud = ifr.list_running_orphans(600.0, dying_owner=ifr.current_owner())
    assert [r["run_id"] for r in ud] == ["min"]


def test_levende_soesterproces_stemples_IKKE(_isoleret_lager, _proctab):
    """KERNEN I FIXET. En frisk tur i en levende søster-proces er ikke vores
    offer — heller ikke når sweepen kaldes med stale_after_s=0.0, som
    nedluknings-stien gør."""
    _proctab[2000] = "777"
    _running(_isoleret_lager, "soesters", owner="2000:777", alder_s=1.0)
    ud = ifr.list_running_orphans(0.0, dying_owner=ifr.current_owner())
    assert ud == [], "en levende proces' aktive tur blev stemplet"


def test_doed_ejer_stemples(_isoleret_lager, _proctab):
    """Crash: ejer-processen findes ikke længere → ægte zombie."""
    _running(_isoleret_lager, "zombie", owner="3000:888", alder_s=1.0)
    ud = ifr.list_running_orphans(600.0, dying_owner=ifr.current_owner())
    assert [r["run_id"] for r in ud] == ["zombie"]


def test_genbrugt_pid_er_en_ANDEN_ejer(_isoleret_lager, _proctab):
    """Samme pid, anden starttid = en anden proces. Posten er forladt, ikke
    levende — uden starttiden ville den se ud som om den kørte endnu."""
    _proctab[2000] = "777"
    _running(_isoleret_lager, "gammel", owner="2000:111", alder_s=1.0)
    ud = ifr.list_running_orphans(600.0, dying_owner=ifr.current_owner())
    assert [r["run_id"] for r in ud] == ["gammel"]


def test_post_uden_ejer_bruger_alderen_som_FOER(_isoleret_lager, _proctab):
    """Bagudkompatibilitet: ældre poster (og tests) har ingen ``owner_proc``.
    De skal opføre sig præcis som før — alderen afgør."""
    _running(_isoleret_lager, "frisk", alder_s=1.0)
    _running(_isoleret_lager, "gammel", alder_s=1200.0)
    assert {r["run_id"] for r in ifr.list_running_orphans(600.0)} == {"gammel"}
    # Med stale_after_s=0.0 tages begge — præcis som sweepen altid gjorde.
    assert {r["run_id"] for r in ifr.list_running_orphans(0.0)} == {"frisk", "gammel"}


def test_ukendt_ejer_stemples_ikke_paa_et_gaet(_isoleret_lager, _proctab):
    """Kan ejerskabet ikke afgøres, afgør alderen — ikke et gæt. En frisk post
    med ukendt ejer må ikke ryge med."""
    _proctab[4000] = ""            # findes, men starttiden kunne ikke læses
    _running(_isoleret_lager, "frisk", owner="4000:999", alder_s=1.0)
    assert ifr.list_running_orphans(600.0, dying_owner=ifr.current_owner()) == []
    _running(_isoleret_lager, "gammel", owner="4000:999", alder_s=1200.0)
    ud = ifr.list_running_orphans(600.0, dying_owner=ifr.current_owner())
    assert [r["run_id"] for r in ud] == ["gammel"]


def test_afsluttede_poster_roeres_aldrig(_isoleret_lager, _proctab):
    """Kun ``running`` er kandidater — en afbrudt post er allerede stemplet."""
    _running(_isoleret_lager, "r1", owner=ifr.current_owner(), alder_s=1.0)
    _isoleret_lager["r1"]["status"] = "interrupted"
    assert ifr.list_running_orphans(0.0, dying_owner=ifr.current_owner()) == []
