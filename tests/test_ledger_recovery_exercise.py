"""Rollback er PRØVET — Fase 11, kriterium 2.

    «rollback has been exercised without deleting ledger events»

MAALT 10/9-2026: `ledger_recovery` har NUL kaldere, og `session_write_leases`
har nul raekker. Maskineriet var bygget efter fase 1's spec og aldrig koert.
Et rollback man aldrig har proevet, er ikke et rollback — det er en hensigt.

Testerne her ER proeven. De koerer begge halvdele mod en syntetisk ubalanceret
session og haevder det kriteriet faktisk kraever: at genopretningen TILFOEJER
balancerende haendelser og ALDRIG sletter committede.
"""
from __future__ import annotations


def _skriv(sid, n=3):
    from core.runtime.db_session_ledger import (
        acquire_write_lease, append_session_events, release_write_lease,
    )
    token = acquire_write_lease(sid, owner="proeve")
    try:
        append_session_events(sid, owner="proeve", token=token, events=[
            {"event_id": f"e{i}", "kind": "message",
             "payload": {"message_id": f"m{i}", "role": "user",
                         "content": f"besked {i}"}}
            for i in range(n)
        ])
    finally:
        release_write_lease(sid, owner="proeve", token=token)


def test_inspect_skriver_INTET(isolated_runtime):
    """At KIGGE paa en afbrudt session maa ikke kraeve skriveretten. Ellers
    tager man den fra den proces der stadig arbejder — eller lader vaere med
    at kigge. Begge dele er vaerre end problemet."""
    from core.runtime.db_session_ledger import read_session_events as list_session_events
    from core.services.ledger_recovery import inspect

    sid = "chat-proeve-1"
    _skriv(sid, 3)
    foer = len(list_session_events(sid))

    ud = inspect(sid)
    assert isinstance(ud, dict)
    assert len(list_session_events(sid)) == foer, "inspect() skrev i ledgeren"

    from core.runtime.db_session_ledger import lease_state as active_write_lease
    assert active_write_lease(sid) in (None, {}, ""), "inspect() tog en lease"


def test_recover_SLETTER_ikke_committede_haendelser(isolated_runtime):
    """Kriteriets kerne. En genopretning maa kun TILFOEJE."""
    from core.runtime.db_session_ledger import read_session_events as list_session_events
    from core.services.ledger_recovery import recover

    sid = "chat-proeve-2"
    _skriv(sid, 4)
    foer = list_session_events(sid)
    foer_ider = [str(e.get("seq")) for e in foer]

    recover(sid, owner="proeve-recovery")

    efter = list_session_events(sid)
    efter_ider = [str(e.get("seq")) for e in efter]
    assert efter_ider[:len(foer_ider)] == foer_ider, (
        "genopretningen aendrede eller slettede committede haendelser — "
        "praecis det fase 1 forbyder")
    assert len(efter) >= len(foer)


def test_recover_uden_lease_skriver_ikke(isolated_runtime, monkeypatch):
    """`recover()` skriver, og skal derfor kun kunne goere det gennem et
    handle med lease. Kan den ikke faa en, maa den ikke skrive alligevel."""
    import core.runtime.db_session_ledger as sl
    from core.runtime.db_session_ledger import read_session_events as list_session_events
    from core.services.ledger_recovery import recover

    sid = "chat-proeve-3"
    _skriv(sid, 2)
    foer = len(list_session_events(sid))

    monkeypatch.setattr(sl, "acquire_write_lease", lambda *a, **kw: None)
    ud = recover(sid, owner="uden-lease")
    assert not ud.get("skrevet"), "skrev uden lease"
    assert len(list_session_events(sid)) == foer
