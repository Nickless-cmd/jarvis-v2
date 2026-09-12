"""Supervisorens signaler: pause, genoptag og stop.

Filen hed foerst test_process_pause. Daeknings-gaten kraever navnet efter
modulet - og det er ogsaa det rigtigere navn: vaernet mod at signalere
serverens egen proces-gruppe daekker STOP lige saa meget som pause. Det var
netop det der viste sig, da pause-vaernet var paa plads og stop-testen saa
hang.
"""
import os
import signal
import time

import pytest

from core.services import process_supervisor as ps


@pytest.fixture
def job(tmp_path, monkeypatch):
    """Et ægte «sleep 30» i et eget registry.

    Registret og logs skal ligge i tmp_path - ellers deler testene RUNTIMENS
    registry, og en test der efterlader «proeve» faar den naeste til at fejle
    paa et navn der allerede findes. (Det skete: 3 passerede, 3 fejlede i
    fixturen.)
    """
    monkeypatch.setattr(ps, "_PROC_DIR", tmp_path / "processes")
    monkeypatch.setattr(ps, "_REGISTRY", tmp_path / "processes" / "registry.json")
    r = ps.spawn_process(name="proeve", command="sleep 30")
    assert r.get("status") == "ok", r
    yield "proeve"
    try:
        ps.stop_process("proeve", grace=1)
    except Exception:
        pass


def _status(navn):
    for p in ps.list_processes()["processes"]:
        if p["name"] == navn:
            return p
    return {}


def test_pauset_er_en_TREDJE_tilstand_ikke_koerende(job):
    # En pauset proces ER i live for kernen. Uden feltet ville UI'et vise den
    # som koerende og tilbyde at pause den igen.
    assert _status("proeve")["status"] == "running"
    assert ps.pause_process("proeve")["status"] == "ok"
    time.sleep(0.2)
    assert _status("proeve")["status"] == "paused"
    assert _status("proeve")["paused"] is True


def test_genoptag_bringer_den_tilbage(job):
    ps.pause_process("proeve")
    time.sleep(0.2)
    assert ps.resume_process("proeve")["status"] == "ok"
    time.sleep(0.2)
    assert _status("proeve")["status"] == "running"


def test_en_proces_der_ALLEREDE_er_slut_er_ikke_en_fejl(job, monkeypatch):
    # Brugeren skal se at den er faerdig, ikke en roed besked om noget der
    # ordnede sig selv.
    monkeypatch.setattr(ps, "_pid_alive", lambda pid: False)
    r = ps.pause_process("proeve")
    assert r["status"] == "ok" and r["message"] == "not running"


def test_ukendt_job_er_en_fejl(job):
    assert ps.pause_process("findes-ikke")["status"] == "error"


def test_den_NAEGTER_at_signalere_sin_egen_gruppe(job, monkeypatch):
    # Et SIGSTOP paa API-serverens gruppe ville fryse hele serveren, og den
    # fejl kan ikke rettes bagefter udefra.
    egen = os.getpgid(0)                                    # HENT FOER patchen —
    monkeypatch.setattr(os, "getpgid", lambda pid: egen)    # ellers kalder den sig selv
    r = ps.pause_process("proeve")
    assert r["status"] == "error"
    assert "gruppe" in r["error"]
    # UNDO FOER fixturens oprydning: `stop_process` bruger samme opslag, og med
    # patchen aktiv ville den signalere VORES gruppe. Det hang testkoereren.
    monkeypatch.undo()


def test_en_UKENDT_gruppe_signaleres_SLET_IKKE(job, monkeypatch):
    """`killpg(0, sig)` er kalderens EGEN gruppe.

    Foerste udgave satte gruppe=0 naar opslaget fejlede og lod vaernet om
    resten — men vaernet saa kun efter «samme tal som vores», og 0 er ikke det
    samme tal. Resultatet var at pause-kaldet SIGSTOP'ede sin egen testkoerer
    (exit 147). Den her test findes fordi den fejl kostede en runde.
    """
    def eksploder(pid):
        raise OSError("ingen saadan proces")
    monkeypatch.setattr(os, "getpgid", eksploder)
    r = ps.pause_process("proeve")
    assert r["status"] == "error"
    assert "gruppe" in r["error"]
    monkeypatch.undo()


def test_can_pause_er_falsk_for_en_doed_proces(job, monkeypatch):
    monkeypatch.setattr(ps, "_pid_alive", lambda pid: False)
    assert _status("proeve")["can_pause"] is False


def test_STOP_er_beskyttet_af_samme_vaern(job, monkeypatch):
    """Hazarden hoerte aldrig kun til pause.

    Da pause-vaernet var paa plads, HANG stop-testen: `_stop_locked` havde
    noejagtig samme `os.killpg(os.getpgid(pid), ...)` og sendte SIGTERM til
    vores egen gruppe naar patchen stadig sad i fixturens oprydning. To
    faelder af samme slags rettes ét sted - ellers rettes kun den man faldt i.
    """
    egen = os.getpgid(0)
    monkeypatch.setattr(os, "getpgid", lambda pid: egen)
    r = ps.stop_process("proeve", grace=1)
    assert r["status"] == "error"
    monkeypatch.undo()   # ellers rammer fixturens oprydning os selv
