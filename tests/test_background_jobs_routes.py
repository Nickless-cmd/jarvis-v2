"""Pause, genoptag og stop — for begge kilder."""
import pytest
from fastapi import HTTPException

from apps.api.jarvis_api.routes import jarvisx_processes as r


@pytest.fixture(autouse=True)
def ejer(monkeypatch):
    monkeypatch.setattr(r, "_require_owner", lambda: None)


def test_supervisor_pauses_gennem_supervisoren(monkeypatch):
    import core.services.process_supervisor as ps
    kaldt = {}
    def _pause(n):
        kaldt["navn"] = n          # IKKE `setdefault(...) or {...}` — setdefault
        return {"status": "ok"}    # returnerer navnet, som er sandt
    monkeypatch.setattr(ps, "pause_process", _pause)
    assert r._signal_job("supervisor", "grid-bot", "pause")["status"] == "ok"
    assert kaldt["navn"] == "grid-bot"


def test_et_UGYLDIGT_operator_id_afvises(monkeypatch):
    # Id'et bliver en del af en kommandolinje paa Bjoerns maskine. Uden
    # moenster-kontrollen kunne det smugle sti- eller kommando-fragmenter ind.
    for slem in ("bg_../../etc", "bg_ZZZZZZZZZZZZ", "; rm -rf /", "bg_abc"):
        with pytest.raises(HTTPException) as e:
            r._signal_job("operator", slem, "stop")
        assert e.value.status_code == 400


def test_et_GYLDIGT_operator_id_signaleres_over_broen(monkeypatch):
    set_cmd = {}
    monkeypatch.setattr(r, "_operator_exec_for_jobs",
                        lambda n, a: set_cmd.update(cmd=a["command"]) or
                        {"status": "ok", "result": {"stdout": "ok\n"}})
    assert r._signal_job("operator", "bg_0123456789ab", "pause")["status"] == "ok"
    assert "kill -STOP" in set_cmd["cmd"]
    assert "bg_0123456789ab.pid" in set_cmd["cmd"]


def test_de_tre_handlinger_sender_de_rigtige_signaler(monkeypatch):
    sendt = []
    monkeypatch.setattr(r, "_operator_exec_for_jobs",
                        lambda n, a: sendt.append(a["command"]) or
                        {"status": "ok", "result": {"stdout": "ok"}})
    for h in ("pause", "resume", "stop"):
        r._signal_job("operator", "bg_0123456789ab", h)
    assert "kill -STOP" in sendt[0] and "kill -CONT" in sendt[1] and "kill -TERM" in sendt[2]


def test_en_doed_bro_er_502_ikke_en_tavs_succes(monkeypatch):
    monkeypatch.setattr(r, "_operator_exec_for_jobs", lambda n, a: {"status": "error"})
    with pytest.raises(HTTPException) as e:
        r._signal_job("operator", "bg_0123456789ab", "stop")
    assert e.value.status_code == 502


def test_en_proces_der_ikke_svarer_meldes_frem_for_at_se_ud_som_om_det_virkede(monkeypatch):
    # Broen svarede, men kommandoen skrev ikke «ok» - altsaa fandtes pid'en
    # ikke. Et tomt svar maa ikke blive til en groen kvittering.
    monkeypatch.setattr(r, "_operator_exec_for_jobs",
                        lambda n, a: {"status": "ok", "result": {"stdout": ""}})
    with pytest.raises(HTTPException) as e:
        r._signal_job("operator", "bg_0123456789ab", "stop")
    assert e.value.status_code == 400


def test_ukendt_kilde_og_handling_afvises():
    with pytest.raises(HTTPException):
        r._signal_job("maanen", "x", "stop")
    with pytest.raises(HTTPException):
        r._signal_job("supervisor", "x", "eksploder")
