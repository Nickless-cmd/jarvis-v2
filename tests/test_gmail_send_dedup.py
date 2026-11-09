"""Dublet-vaern paa `gmail_send` (9/11-2026).

MÅLT 8/11-2026: tre identiske indsigelser gik ud kl. 11:41:28, :29 og :39 —
elleve sekunder fra hinanden. `gmail_send` er grandfathered og ligger uden for
godkendelses-broen, saa broens `prior_unknown_outcome` daekker den ikke: den
ser kun `outcome_unknown`, mens et kald der endte `completed` intet blokerer.

Testene her beviser at et gentaget kald ikke bliver en ny mail — og at et
legitimt gensend stadig kan lade sig goere.
"""

from __future__ import annotations

import pytest


@pytest.fixture()
def sendt(monkeypatch, isolated_runtime):
    """Patch `send_message` og tael hvor mange gauge den faktisk kaldes."""
    import core.services.gmail_connector as gc
    import core.tools.simple_tools_native as stn

    kald: list[dict] = []

    def fake_send(uid, to, subject, body):
        kald.append({"uid": uid, "to": to, "subject": subject, "body": body})
        return {"status": "ok", "id": f"msg-{len(kald)}"}

    monkeypatch.setattr(gc, "send_message", fake_send)
    monkeypatch.setattr(stn, "_operator_user_id", lambda args: "bjorn")
    return kald


def _kald(**over):
    args = {
        "to": "modtager@example.dk",
        "subject": "Indsigelse efter GDPR art. 21",
        "body": "Jeg indsiger mig behandlingen.",
        "_runtime_trust_all": True,
    }
    args.update(over)
    return args


def test_to_identiske_kald_giver_praecis_en_afsendelse(sendt):
    """Det maalte forloeb: samme kald tre gauge paa rad."""
    from core.tools.simple_tools_native import _exec_gmail_send

    foerste = _exec_gmail_send(_kald())
    anden = _exec_gmail_send(_kald())
    tredje = _exec_gmail_send(_kald())

    assert foerste["status"] == "ok"
    assert len(sendt) == 1, f"mailen blev sendt {len(sendt)} gauge"
    for svar in (anden, tredje):
        assert svar["status"] == "error"
        assert svar["error"] == "already_sent"
        assert svar["message_id"] == "msg-1"


def test_forskelligt_emne_slipper_igennem(sendt):
    """Guarden maa ikke spaerre en anden mail til samme modtager."""
    from core.tools.simple_tools_native import _exec_gmail_send

    _exec_gmail_send(_kald())
    andet = _exec_gmail_send(_kald(subject="Rettelse: mit navn er Bjørn Ulrik Slot"))

    assert andet["status"] == "ok"
    assert len(sendt) == 2


def test_forskellig_modtager_slipper_igennem(sendt):
    from core.tools.simple_tools_native import _exec_gmail_send

    _exec_gmail_send(_kald())
    andet = _exec_gmail_send(_kald(to="anden@example.dk"))

    assert andet["status"] == "ok"
    assert len(sendt) == 2


def test_allow_resend_tillader_bevidst_gensend(sendt):
    """Et legitimt gensend er en BESLUTNING — ikke noget der sker af sig selv."""
    from core.tools.simple_tools_native import _exec_gmail_send

    _exec_gmail_send(_kald())
    igen = _exec_gmail_send(_kald(allow_resend=True))

    assert igen["status"] == "ok"
    assert len(sendt) == 2


def test_en_fejlet_afsendelse_registreres_ikke(sendt, monkeypatch):
    """Kun et `ok`-svar maa spaerre det naeste kald.

    Ellers ville en mail der aldrig gik ud spaerre for et forsoeg der faktisk
    skulle lykkes.
    """
    import core.services.gmail_connector as gc
    from core.tools.simple_tools_native import _exec_gmail_send

    monkeypatch.setattr(gc, "send_message",
                        lambda uid, to, subject, body: {"status": "error",
                                                        "error": "gmail_http_500"})
    foerste = _exec_gmail_send(_kald())
    assert foerste["status"] == "error"

    monkeypatch.setattr(gc, "send_message",
                        lambda uid, to, subject, body: {"status": "ok", "id": "msg-efter"})
    anden = _exec_gmail_send(_kald())
    assert anden["status"] == "ok"


def test_vinduet_udloeber_og_tillader_ny_afsendelse(sendt, monkeypatch):
    """Efter vinduet er en ny identisk mail ikke en dublet."""
    from core.runtime import db_approval_bridge as bridge
    from core.tools.simple_tools_native import _exec_gmail_send

    _exec_gmail_send(_kald())
    assert len(sendt) == 1

    # Flyt posten uden for vinduet i stedet for at vente ti minutter.
    from datetime import UTC, datetime, timedelta
    gammel = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
    with bridge.connect() as conn:
        bridge._ensure_send_dedup(conn)
        conn.execute("UPDATE send_dedup SET sent_at = ?", (gammel,))

    anden = _exec_gmail_send(_kald())
    assert anden["status"] == "ok"
    assert len(sendt) == 2
