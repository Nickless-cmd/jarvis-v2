"""Selv-helbredende bash-session-klient (fix 13. sep 2026).

Rod (målt 13. sep 2026): daemonen kunne hænge i 5 timer og 15 minutter mens den
STADIG svarede på `ping` — `ping` rører ikke ``sess_lock``, men `open`/`run` gør.
Klienten havde ingen selv-helbredelse, så hvert kald timede ud i timevis — også
EFTER en service-genstart, fordi systemd kalder en gammel daemon for "left-over
process" og IGNORERER den frem for at dræbe den.

Fixet har tre ben:
1. En PID-fil, så klienten kan skelne en LEVENDE daemon fra en HÆNGENDE.
2. ``_ensure_daemon_running`` dræber en hængende daemon FØR den spawner en ny
   (ellers kæmper to daemons om samme socket-sti).
3. ``_client_call`` helbreder ved IPC-hængning — men gentager ALDRIG en `run`,
   fordi kommandoen kan være delvist udført.

Disse tests dækker alle tre uden at spawne en rigtig daemon.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import core.tools.bash_session as bs


class _FakeTime:
    """Undgå de 5 sekunders ventetid i _force_restart_daemon."""

    def sleep(self, _seconds: float) -> None:  # noqa: D102
        pass


# ─────────────────────────────────────────────────────────────────────
#  1. Kill-guard: en genbrugt PID må ALDRIG rammes
# ─────────────────────────────────────────────────────────────────────


class TestPidGuard:
    def test_pid_under_eller_lig_1_afvises(self):
        # PID 0 = hele procesgruppen, PID 1 = init. Begge katastrofale at dræbe.
        assert bs._pid_is_our_daemon(0) is False
        assert bs._pid_is_our_daemon(1) is False
        assert bs._pid_is_our_daemon(-5) is False

    def test_ikke_eksisterende_pid_afvises(self):
        assert bs._pid_is_our_daemon(2_000_000_000) is False

    def test_fremmed_proces_afvises(self):
        # Vores EGEN proces er ikke en bash-session-daemon.
        assert bs._pid_is_our_daemon(os.getpid()) is False

    def test_egen_daemon_genkendes(self, monkeypatch):
        class _FakePath:
            def __init__(self, _p):  # noqa: D107
                pass

            def read_bytes(self):  # noqa: D102
                return b"python3.11\0-m\0core.tools.bash_session\0--daemon\0"

        monkeypatch.setattr(bs, "Path", _FakePath)
        assert bs._pid_is_our_daemon(4242) is True

    def test_daemon_uden_flag_genkendes_ikke(self, monkeypatch):
        # Navnet alene er ikke nok — «--daemon» skal også være der.
        class _FakePath:
            def __init__(self, _p):  # noqa: D107
                pass

            def read_bytes(self):  # noqa: D102
                return b"python3.11\0-m\0core.tools.bash_session\0"

        monkeypatch.setattr(bs, "Path", _FakePath)
        assert bs._pid_is_our_daemon(4242) is False

    def test_kill_daemon_roerer_ikke_fremmed_proces(self, monkeypatch):
        called: list[int] = []
        monkeypatch.setattr(bs, "_pid_is_our_daemon", lambda _pid: False)
        monkeypatch.setattr(bs.os, "kill", lambda pid, _sig: called.append(pid))
        bs._kill_daemon(os.getpid())
        assert called == []


# ─────────────────────────────────────────────────────────────────────
#  2. PID-filen — grundlaget for at skelne levende fra hængende
# ─────────────────────────────────────────────────────────────────────


class TestPidFil:
    def test_manglende_fil_giver_none(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(bs, "_PID_PATH", tmp_path / "findes-ikke.pid")
        assert bs._read_daemon_pid() is None

    def test_ulaeseligt_indhold_giver_none(self, monkeypatch, tmp_path: Path):
        p = tmp_path / "daemon.pid"
        p.write_text("ikke-et-tal")
        monkeypatch.setattr(bs, "_PID_PATH", p)
        assert bs._read_daemon_pid() is None

    def test_gyldig_pid_laeses(self, monkeypatch, tmp_path: Path):
        p = tmp_path / "daemon.pid"
        p.write_text("4242\n")
        monkeypatch.setattr(bs, "_PID_PATH", p)
        assert bs._read_daemon_pid() == 4242


# ─────────────────────────────────────────────────────────────────────
#  3. _ensure_daemon_running — dræb hængende FØR spawn
# ─────────────────────────────────────────────────────────────────────


class TestEnsureDaemonRunning:
    def _isolate_paths(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setattr(bs, "_STATE_DIR", tmp_path)
        monkeypatch.setattr(bs, "_LOCK_PATH", tmp_path / "lock")
        monkeypatch.setattr(bs, "_SOCKET_PATH", tmp_path / "sock")

    def test_draeber_haengende_foer_den_spawner(self, monkeypatch, tmp_path: Path):
        """Kernen i fixet: ellers kæmper to daemons om samme socket-sti."""
        seq: list[tuple[str, object]] = []
        self._isolate_paths(monkeypatch, tmp_path)
        monkeypatch.setattr(bs, "_read_daemon_pid", lambda: 4242)
        monkeypatch.setattr(bs, "_pid_is_our_daemon", lambda _pid: True)
        monkeypatch.setattr(bs, "_kill_daemon", lambda pid: seq.append(("kill", pid)))
        monkeypatch.setattr(bs, "_spawn_daemon", lambda: seq.append(("spawn", None)))

        pings = {"n": 0}

        def _ping() -> bool:
            pings["n"] += 1
            return pings["n"] > 1  # første ping fejler (daemonen hænger)

        monkeypatch.setattr(bs, "_ping_daemon", _ping)

        assert bs._ensure_daemon_running() is True
        assert ("kill", 4242) in seq
        assert ("spawn", None) in seq
        assert seq.index(("kill", 4242)) < seq.index(("spawn", None))

    def test_sund_daemon_roeres_ikke(self, monkeypatch, tmp_path: Path):
        seq: list[str] = []
        self._isolate_paths(monkeypatch, tmp_path)
        monkeypatch.setattr(bs, "_ping_daemon", lambda: True)
        monkeypatch.setattr(bs, "_kill_daemon", lambda _pid: seq.append("kill"))
        monkeypatch.setattr(bs, "_spawn_daemon", lambda: seq.append("spawn"))

        assert bs._ensure_daemon_running() is True
        assert seq == []  # en daemon der svarer bliver hverken dræbt eller genstartet


# ─────────────────────────────────────────────────────────────────────
#  4. _force_restart_daemon — dræb, ryd socket, spawn, vent
# ─────────────────────────────────────────────────────────────────────


class TestForceRestart:
    def test_draeber_rydder_socket_og_spawner(self, monkeypatch, tmp_path: Path):
        seq: list[tuple[str, object]] = []
        sock = tmp_path / "sock"
        sock.write_text("")  # forældet socket-stump
        monkeypatch.setattr(bs, "_SOCKET_PATH", sock)
        monkeypatch.setattr(bs, "_read_daemon_pid", lambda: 4242)
        monkeypatch.setattr(bs, "_kill_daemon", lambda pid: seq.append(("kill", pid)))
        monkeypatch.setattr(bs, "_spawn_daemon", lambda: seq.append(("spawn", None)))
        monkeypatch.setattr(bs, "_ping_daemon", lambda: True)

        assert bs._force_restart_daemon() is True
        assert seq == [("kill", 4242), ("spawn", None)]
        assert not sock.exists()  # den forældede socket-stump er væk

    def test_giver_op_hvis_ny_daemon_ikke_svarer(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr(bs, "_SOCKET_PATH", tmp_path / "sock")
        monkeypatch.setattr(bs, "_read_daemon_pid", lambda: None)
        monkeypatch.setattr(bs, "_spawn_daemon", lambda: None)
        monkeypatch.setattr(bs, "_ping_daemon", lambda: False)
        monkeypatch.setattr(bs, "time", _FakeTime())

        assert bs._force_restart_daemon() is False


# ─────────────────────────────────────────────────────────────────────
#  5. _client_call — helbred ved IPC-hængning, men gentag ALDRIG en run
# ─────────────────────────────────────────────────────────────────────


class TestClientCallSelvhelbredelse:
    def test_ok_svar_gaar_urort_igennem(self, monkeypatch):
        monkeypatch.setattr(
            bs, "_client_call_once",
            lambda payload, timeout=310.0: {"status": "ok", "session_id": "bsh-a"},
        )
        assert bs._client_call({"op": "open"})["status"] == "ok"

    def test_applikationsfejl_roerer_ikke_daemonen(self, monkeypatch):
        """En SUND daemon kan svare med fejl — fx ukendt session_id. Den må ikke dræbes."""
        healed: list[int] = []
        monkeypatch.setattr(
            bs, "_client_call_once",
            lambda payload, timeout=310.0: {"status": "error", "error": "unknown session_id bsh-x"},
        )
        monkeypatch.setattr(bs, "_force_restart_daemon", lambda: healed.append(1) or True)

        res = bs._client_call({"op": "run", "session_id": "bsh-x", "command": "echo hi"})
        assert res["status"] == "error"
        assert healed == []

    def test_open_helbredes_og_forsoeges_igen(self, monkeypatch):
        state = {"n": 0}

        def _once(payload, timeout=310.0):
            state["n"] += 1
            if state["n"] == 1:
                return {"status": "error", "error": "daemon ipc failed: timed out"}
            return {"status": "ok", "session_id": "bsh-new"}

        monkeypatch.setattr(bs, "_client_call_once", _once)
        monkeypatch.setattr(bs, "_force_restart_daemon", lambda: True)

        res = bs._client_call({"op": "open"})
        assert res["status"] == "ok"
        assert state["n"] == 2  # ét forsøg, helbred, ét nyt

    def test_run_gentages_ALDRIG(self, monkeypatch):
        """Sikkerheds-kernen: en kommando kan være delvist udført. Gentag den ikke."""
        state = {"n": 0}

        def _once(payload, timeout=310.0):
            state["n"] += 1
            return {"status": "error", "error": "daemon ipc failed: timed out"}

        monkeypatch.setattr(bs, "_client_call_once", _once)
        monkeypatch.setattr(bs, "_force_restart_daemon", lambda: True)

        res = bs._client_call(
            {"op": "run", "session_id": "bsh-x", "command": "rm -rf /tmp/x"}
        )
        assert res["status"] == "error"
        assert "session lost" in res["error"]
        assert state["n"] == 1  # kommandofejl gentages IKKE

    def test_mislykket_helbredelse_giver_oprindelig_fejl(self, monkeypatch):
        monkeypatch.setattr(
            bs, "_client_call_once",
            lambda payload, timeout=310.0: {"status": "error", "error": "daemon ipc failed: timed out"},
        )
        monkeypatch.setattr(bs, "_force_restart_daemon", lambda: False)

        res = bs._client_call({"op": "open"})
        assert res["status"] == "error"
        assert "daemon ipc failed" in res["error"]
