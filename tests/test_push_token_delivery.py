"""Vagt: en mobil-presence-post skal leveres til sit FCM-token — ikke sit enheds-id.

Målt 23/10-2026: `notification_router._deliver` sendte til `target.device_key`
(«mobile-mtsz1dse-…»), som er enhedens ID og IKKE et token. FCM afviste det, og
`_send_fcm` kaster returværdien væk — så notifikationen så leveret ud uden at
være det. Brugere med kanalvalg 'mobile' slap (den gren går gennem
`_push_to_user` med de registrerede tokens); en bruger uden kanalvalg (→ 'auto')
faldt i hullet.

Derfor testes begge ender: at `rank()` bærer tokenet videre, og at `_deliver`
faktisk bruger det. En test der kun kigger på `rank()` ville ikke se fejlen —
den sad i leveringen.
"""
from __future__ import annotations

from core.services import device_presence as dp
from core.services import notification_router as nr


def _ryd() -> None:
    with dp._lock:
        dp._PRESENCE.clear()


def _enhed(uid: str = "u1", push_token: str | None = "REAL_FCM_TOKEN_xyz") -> None:
    dp.record_ping(
        uid, "mobile-enhedsid-123", "mobile",
        foreground=True, awake=True, network="home", push_token=push_token,
    )


def test_rank_baerer_push_token():
    _ryd()
    _enhed()
    r = dp.rank("u1")
    assert r, "ingen enhed rangeret"
    assert r[0].platform == "mobile"
    assert r[0].push_token == "REAL_FCM_TOKEN_xyz"


def test_deliver_bruger_token_ikke_enhedsid(monkeypatch):
    _ryd()
    _enhed()
    kald: list[str] = []
    from core.services import push_dispatcher as pd
    monkeypatch.setattr(pd, "_fcm_send", lambda tok, data: (kald.append(tok) or (True, "ok")))

    target = dp.rank("u1")[0]
    nr._deliver("u1", target, "notif-1", {"kind": "initiative", "preview": "hej"})

    assert kald == ["REAL_FCM_TOKEN_xyz"], f"sendte til {kald} — ikke det registrerede token"


def test_uden_token_falder_tilbage_til_enhedsid(monkeypatch):
    """Enhed uden registreret token: enheds-id'et er den eneste adresse der findes."""
    _ryd()
    _enhed(push_token=None)
    kald: list[str] = []
    from core.services import push_dispatcher as pd
    monkeypatch.setattr(pd, "_fcm_send", lambda tok, data: (kald.append(tok) or (True, "ok")))

    nr._deliver("u1", dp.rank("u1")[0], "notif-2", {"kind": "initiative"})

    assert kald == ["mobile-enhedsid-123"]
