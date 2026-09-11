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
