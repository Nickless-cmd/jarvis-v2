"""Den delte bash-session må ikke arve en D-Bus-session (12/11-2026).

Målt på CT105: daemonen (startet 4/11 af en proces med login-miljø) og dens shells
havde DBUS_SESSION_BUS_ADDRESS. Hver Python-proces startet derfra fik den låste
SecretService-nøgleringe som keyring-backend og hang på en oplåsnings-dialog —
33 kald i dag ramte 120 s-timeouten. jarvis-api og jarvis-runtime har ingen
D-Bus, så de faldt straks tilbage til server-KEK. Daemonens miljø hører til
serveren, ikke til den login-session der tilfældigvis startede den.
"""
from __future__ import annotations

from core.tools import bash_session as bs

_BUS = "unix:path=/run/user/1000/bus"


def test_shellens_miljoe_har_ingen_dbus_session_men_beholder_resten(monkeypatch):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", _BUS)
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.setenv("JARVIS_NOGET", "bevares")

    env = bs._shell_env()

    assert "DBUS_SESSION_BUS_ADDRESS" not in env
    assert env["XDG_RUNTIME_DIR"] == "/run/user/1000"
    assert env["JARVIS_NOGET"] == "bevares"
    # de eksisterende pager-/prompt-indstillinger er uændrede
    assert (env["PS1"], env["PS2"], env["TERM"], env["PAGER"], env["GIT_PAGER"],
            env["LESS"], env["DEBIAN_FRONTEND"]) == ("", "", "dumb", "cat", "cat", "FRX", "noninteractive")


def test_daemonens_miljoe_har_ingen_dbus_session(monkeypatch):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", _BUS)
    monkeypatch.setenv("JARVIS_NOGET", "bevares")

    env = bs._daemon_env()

    assert "DBUS_SESSION_BUS_ADDRESS" not in env
    assert env["JARVIS_NOGET"] == "bevares"


def test_uden_dbus_i_miljoet_er_det_en_ren_kopi(monkeypatch):
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    assert "DBUS_SESSION_BUS_ADDRESS" not in bs._shell_env()
    assert "DBUS_SESSION_BUS_ADDRESS" not in bs._daemon_env()


def test_daemonen_startes_med_et_miljoe_uden_dbus(monkeypatch):
    monkeypatch.setenv("DBUS_SESSION_BUS_ADDRESS", _BUS)
    set_ = {}

    def _popen(args, **kw):
        set_.update(kw)

    monkeypatch.setattr(bs.subprocess, "Popen", _popen)
    bs._spawn_daemon()

    assert "env" in set_, "daemonen startes uden eksplicit miljø og arver D-Bus"
    assert "DBUS_SESSION_BUS_ADDRESS" not in set_["env"]
