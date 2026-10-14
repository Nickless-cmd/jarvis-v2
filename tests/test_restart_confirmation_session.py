"""Tests for genstart-verifikationens vej til SAMTALEN (13/10-2026).

Bjørn: «den verifikation burde lande i den session genstartet blev sendt fra..
genstart <-> verifikation -> inbox aktive/idle wakeup».

To led skal holde:

  1. Samtalens id fanges hvor konteksten LEVER — i turen der beder om
     genstarten — ikke ved opstart, hvor den er væk.
  2. Verifikationen leveres til den samtale via `send_session_notification`
     (aktiv/idle-mekanikken) og til indbakken. Discord er RESERVEVEJ, ikke
     førstevalg.

Den negative kontrol er test 3: uden en samtale skal Discord-stien stadig
virke — ellers har jeg byttet én defekt ud med en anden.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import core.tools.restart_self_tools as rst


def test_exec_skriver_samtalens_id_i_bekraeftelsen(tmp_path, monkeypatch):
    """Konteksten fanges i turen — ikke gættet ved opstart."""
    fil = tmp_path / "pending.json"
    monkeypatch.setattr(rst, "PENDING_RESTART_FILE", fil)
    monkeypatch.setattr(rst, "_aktive_koersler", lambda *a, **k: [])

    with patch("core.identity.workspace_context.current_session_id",
               return_value="chat-abc"), \
         patch("core.identity.workspace_context.current_user_id",
               return_value="bjorn-uid"), \
         patch("core.tools.restart_self_tools.subprocess.Popen"):
        rst._exec_restart_self({"services": ["jarvis-api"]})

    data = json.loads(fil.read_text())
    assert data["session_id"] == "chat-abc"
    assert data["user_id"] == "bjorn-uid"


def test_leverer_til_samtalen_ikke_discord(tmp_path, monkeypatch):
    """Kender vi samtalen, er Discord ikke længere førstevalget."""
    fil = tmp_path / "pending_restart_confirmation.json"
    monkeypatch.setattr(rst, "PENDING_RESTART_FILE", fil)
    fil.write_text(json.dumps({
        "services": ["jarvis-api"],
        "channel": "discord",
        "session_id": "chat-abc",
        "user_id": "bjorn-uid",
    }))

    kald: list[dict] = []
    indbakke: list[dict] = []

    def _notify(m, **kw):
        kald.append({"m": m, **kw})
        return {"status": "ok"}

    with patch("core.services.notification_bridge.send_session_notification",
               side_effect=_notify), \
         patch("core.services.notification_bridge.delivery_succeeded",
               return_value=True), \
         patch("core.services.inbox_state.registrer_kilde",
               side_effect=lambda **kw: indbakke.append(kw) or {}), \
         patch("core.tools.restart_self_tools._send_discord_restart_msg") as discord:
        rst.send_pending_restart_confirmation()

    assert kald, "verifikationen skal leveres til samtalen"
    assert kald[0]["session_id"] == "chat-abc"
    assert kald[0]["push"] is False, (
        "verifikationen er informerende — den maa ikke give en ny push-kilde"
    )
    discord.assert_not_called()
    assert indbakke and indbakke[0]["kildetype"] == "genstart", (
        "posten skal ogsaa staa durabelt i indbakken"
    )
    assert not fil.exists(), "bekraeftelsen skal forbruges naar den er leveret"


def test_uden_samtale_bruger_discord_reservevejen(tmp_path, monkeypatch):
    """Negativ kontrol: uden samtale maa Discord-stien ikke vaere doed."""
    fil = tmp_path / "pending_restart_confirmation.json"
    monkeypatch.setattr(rst, "PENDING_RESTART_FILE", fil)
    fil.write_text(json.dumps({"services": ["jarvis-api"], "channel": "discord"}))

    kaldt: list[str] = []

    with patch("core.tools.restart_self_tools._wait_for_gateway_connected",
               return_value=True), \
         patch("core.tools.restart_self_tools._send_discord_restart_msg",
               side_effect=lambda m: (kaldt.append(m), True)[1]):
        rst.send_pending_restart_confirmation()

    assert kaldt, "uden en samtale skal Discord-reservevejen stadig virke"
