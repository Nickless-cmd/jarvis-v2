"""Raad afregnes naar deres proces er vaek — Fase 8.

Fase 8 beder om en `WorkflowRuntime`. Den er IKKE bygget, og grunden er maalt:
NUL agenter har en foraelder der ikke er Jarvis. Der findes ingen
flerlags-orkestrering at laegge et workflow-lag over — det ville vaere et
runtime uden kalder.

Raadet er husets orkestrering, og ét af fasens kriterier holdt ikke:
«workflow restart settles as interrupted_by_restart». `run_council_round` har
en try/finally der altid lukker, men den koerer ikke naar processen doer. 174
gamle raekker stod tilbage: 104 forming, 70 deliberating, nyeste 14. juli —
alle fra FOER juli-rettelsen.

ALDER DUER IKKE: en runde tager 5-17 minutter (maalt), saa en tidsgraense
ville afbryde levende raad. Derfor proces-maerket.
"""
from __future__ import annotations

import socket


def _raad(db, cid, status, *, maerke=None):
    db.create_council_session(council_id=cid, topic="t", owner_agent_id="jarvis")
    db.update_council_session(cid, status=status)
    if maerke is not None:
        with db.connect() as conn:
            conn.execute("UPDATE council_sessions SET runtime_owner=? "
                         "WHERE council_id=?", (maerke, cid))
    return cid


def test_kun_raad_hvis_proces_er_VAEK_afregnes(isolated_runtime):
    import core.runtime.db_agent_runtime as db
    from core.services.council_settlement import settle_interrupted_councils
    from core.services.process_identity import denne_proces

    vaert = socket.gethostname()
    tilfaelde = [
        ("c-lever", "deliberating", denne_proces(), False, "deliberer LIGE NU"),
        ("c-doed", "deliberating", f"{vaert}:999999:1", True, "processen er vaek"),
        ("c-gammel", "forming", "", True, "raekke fra foer migreringen"),
        ("c-anden", "deliberating", "en-anden-maskine:1:2", False,
         "kan ikke afgoeres"),
        ("c-lukket", "closed", "", False, "allerede terminal"),
    ]
    for cid, status, maerke, _, _ in tilfaelde:
        _raad(db, cid, status, maerke=maerke)

    settle_interrupted_councils()

    for cid, start, _, skulle_afregnes, hvorfor in tilfaelde:
        ny = str(db.get_council_session(cid)["status"])
        if skulle_afregnes:
            assert ny == "interrupted_by_restart", f"{cid} blev ikke afregnet ({hvorfor})"
        else:
            assert ny == start, f"{cid} blev afregnet selvom {hvorfor}"


def test_afregningen_er_ikke_closed(isolated_runtime):
    """«closed» ville paastaa at der ligger en konklusion. Der er ingen."""
    import core.runtime.db_agent_runtime as db
    from core.services.council_settlement import AFBRUDT, settle_interrupted_councils

    _raad(db, "c1", "deliberating", maerke=f"{socket.gethostname()}:999999:1")
    settle_interrupted_councils()
    s = db.get_council_session("c1")
    assert s["status"] == AFBRUDT != "closed"
    assert "genstart" in str(s["summary"]).lower()
    assert s["finished_at"]


def test_ventende_medlemmer_lukkes_med(isolated_runtime):
    """Medlemmer der venter paa et doedt raad akkumulerer mod
    MAX_CONCURRENT_AGENTS og blokerer fremtidige raad — praecis den fejl
    juli-rettelsen loeste for den LEVENDE sti."""
    import core.runtime.db_agent_runtime as db
    from core.services.council_settlement import settle_interrupted_councils

    cid = _raad(db, "c2", "deliberating", maerke=f"{socket.gethostname()}:999999:1")
    db.create_agent_registry_entry(agent_id="m1", role="r", goal="g",
                                   council_id=cid)
    db.update_agent_registry_entry("m1", status="waiting")
    db.create_agent_registry_entry(agent_id="m2", role="r", goal="g",
                                   council_id=cid)
    db.update_agent_registry_entry("m2", status="completed")

    settle_interrupted_councils()

    assert db.get_agent_registry_entry("m1")["status"] == "expired"
    assert db.get_agent_registry_entry("m2")["status"] == "completed", (
        "et faerdigt medlem blev roert")


def test_maerket_ryddes_naar_raadet_lukkes(isolated_runtime):
    import core.runtime.db_agent_runtime as db
    from core.services.process_identity import denne_proces

    cid = _raad(db, "c3", "deliberating")
    assert db.get_council_session(cid)["runtime_owner"] == denne_proces()
    db.update_council_session(cid, status="closed")
    assert db.get_council_session(cid)["runtime_owner"] == ""
