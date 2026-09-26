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


def test_en_scout_agent_stoppes_ved_at_annullere_den(monkeypatch):
    import core.services.agent_runtime as ar
    kaldt = {}
    monkeypatch.setattr(ar, "cancel_agent", lambda aid, note="": kaldt.update(aid=aid) or {})
    gyldig = "agent-" + "0" * 32
    assert r._signal_job("agent", gyldig, "stop")["status"] == "ok"
    assert kaldt["aid"] == gyldig


def test_en_scout_agent_kan_ikke_pauses_og_id_valideres(monkeypatch):
    for slem in ("agent-../../x", "; rm -rf /", "agent-abc"):
        with pytest.raises(HTTPException):
            r._signal_job("agent", slem, "stop")
    with pytest.raises(HTTPException) as e:
        r._signal_job("agent", "agent-" + "0" * 32, "pause")
    assert e.value.status_code == 400


# ── Stop på en åben shell-session (26/9-2026) ───────────────────────────
#
# Stop-knappen kalder værktøjernes EGEN `close`. De to filer er urørt — der
# gates intet nyt; Bjørn får den knap Jarvis allerede havde.


def test_en_shell_session_kan_kun_LUKKES_ikke_pauses():
    # En kommando i en session blokerer kaldet og er loftet til 300 s. Der
    # findes ikke et oejeblik mellem to opslag hvor man kunne standse den,
    # saa en pause-knap ville vaere en knap der intet gjorde.
    for h in ("pause", "resume"):
        with pytest.raises(HTTPException) as e:
            r._signal_job("shell", "bsh-0123456789", h)
        assert e.value.status_code == 400


def test_et_UGYLDIGT_session_id_afvises():
    # Id'et vaelger hvilket vaerktoej der kaldes. Uden moenster-kontrollen
    # ville en vilkaarlig streng naa helt ind i `close`.
    for slem in ("bsh-ZZZZZZZZZZ", "bsh-012", "opsess-0123", "; rm -rf /",
                 "opsess-ZZZZZZZZZZZZ", ""):
        with pytest.raises(HTTPException) as e:
            r._signal_job("shell", slem, "stop")
        assert e.value.status_code == 400


def test_en_lokal_shell_lukkes_gennem_daemonens_egen_close(monkeypatch):
    import core.tools.bash_session as bs
    set_id = {}
    monkeypatch.setattr(bs, "_exec_bash_session_close",
                        lambda a: set_id.update(sid=a["session_id"]) or {"status": "ok"})
    assert r._signal_job("shell", "bsh-115cd823bf", "stop")["status"] == "ok"
    assert set_id["sid"] == "bsh-115cd823bf"


def test_en_operator_shell_lukkes_gennem_operator_vaerktoejets_close(monkeypatch):
    import core.tools.operator_bash_session as ops
    set_a = {}
    monkeypatch.setattr(ops, "_exec_operator_bash_session_close",
                        lambda a: set_a.update(a) or {"status": "ok", "closed": True})
    assert r._signal_job("shell_operator", "opsess-0123456789ab", "stop")["status"] == "ok"
    assert set_a["session_id"] == "opsess-0123456789ab"
    # `_user_id` skal med: operator-siden rydder sin env-fil paa HANS maskine,
    # og det kald skal vide hvem det koeres som.
    assert "_user_id" in set_a


def test_en_close_der_fejler_er_400_ikke_en_tavs_succes(monkeypatch):
    import core.tools.bash_session as bs
    monkeypatch.setattr(bs, "_exec_bash_session_close",
                        lambda a: {"status": "error", "error": "daemonen svarede ikke"})
    with pytest.raises(HTTPException) as e:
        r._signal_job("shell", "bsh-0123456789", "stop")
    assert e.value.status_code == 400
    assert "daemonen" in str(e.value.detail)
