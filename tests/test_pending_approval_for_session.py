"""Kortet kender sin samtale — og nu kan nogen spørge om det.

Bjørn 20/9-2026: «jeg sidder og laver noget med ham i desk og så står han bare
og hænger, indtil jeg kigger på min telefon og så ligger der et approval card
der skal godkendes… fra desk siden ser det ud som han staller».

Roden: desk får kortet som et LIVE-event i streamen, mens mobilen finder det
ved at polle. Er streamen ikke forbundet i det øjeblik kortet laves — en
genforbindelse, et nyåbnet vindue, et svar der kørte videre efter en
afbrydelse — ser desk det aldrig.

Kortet har hele tiden båret sin `session_id` (`approval_runtime.build_request`).
Der var bare ingen vej til at spørge.
"""
from __future__ import annotations

import pytest

from core.services import approval_runtime as ar


class _Run:
    def __init__(self, run_id: str, session_id: str):
        self.run_id = run_id
        self.session_id = session_id
        self.user_id = "u1"


@pytest.fixture(autouse=True)
def _tom_venteliste():
    import core.services.visible_runs as vr
    gammel = dict(vr._PENDING_APPROVALS)
    vr._PENDING_APPROVALS.clear()
    yield vr._PENDING_APPROVALS
    vr._PENDING_APPROVALS.clear()
    vr._PENDING_APPROVALS.update(gammel)


def _laeg(venteliste, approval_id: str, session_id: str, *, tool: str = "bash", nu: str = "2026-09-20T10:00:00+00:00"):
    venteliste[approval_id] = {
        "tool_name": tool, "arguments": {"command": "rm -rf /tmp/x"},
        "result": {}, "run_id": "r1", "session_id": session_id,
        "created_at": nu, "owner_user_id": "u1", "invocation_digest": "d",
    }


def test_finder_kortet_for_SIN_samtale(_tom_venteliste):
    _laeg(_tom_venteliste, "a1", "chat-1")
    kort = ar.pending_for_session("chat-1")
    assert kort and kort["approval_id"] == "a1" and kort["tool_name"] == "bash"


def test_en_ANDEN_samtales_kort_kommer_ikke_med(_tom_venteliste):
    """Ellers ville et kort fra en autonom tur poppe op midt i hans egen."""
    _laeg(_tom_venteliste, "a1", "chat-anden")
    assert ar.pending_for_session("chat-1") is None


def test_det_NYESTE_kort_vinder(_tom_venteliste):
    """Et gammelt kort må ikke skygge for det han faktisk venter på."""
    _laeg(_tom_venteliste, "gammel", "chat-1", nu="2026-09-20T09:00:00+00:00")
    _laeg(_tom_venteliste, "ny", "chat-1", nu="2026-09-20T11:00:00+00:00")
    assert ar.pending_for_session("chat-1")["approval_id"] == "ny"


def test_uden_samtale_spoerges_der_ikke(_tom_venteliste):
    _laeg(_tom_venteliste, "a1", "chat-1")
    assert ar.pending_for_session("") is None
    assert ar.pending_for_session("   ") is None


def test_ruten_svarer_TOMT_naar_der_intet_er(isolated_runtime, _tom_venteliste):
    from apps.api.jarvis_api.routes import chat as rute
    assert rute.chat_pending_approval("chat-1") == {"approval": None}


def test_ruten_baerer_kortet_igennem(isolated_runtime, _tom_venteliste):
    from apps.api.jarvis_api.routes import chat as rute
    _laeg(_tom_venteliste, "a9", "chat-1")
    svar = rute.chat_pending_approval("chat-1")["approval"]
    assert svar["approval_id"] == "a9" and svar["tool"] == "bash"
    # Kommandoen skal med: uden den er kortet «godkend noget» uden et hvad.
    assert svar["arguments"]["command"] == "rm -rf /tmp/x"


def test_ruten_fejler_ALDRIG(isolated_runtime, monkeypatch):
    """En manglende opsamling må aldrig kunne vælte samtalen."""
    from apps.api.jarvis_api.routes import chat as rute
    monkeypatch.setattr(ar, "pending_for_session",
                        lambda s: (_ for _ in ()).throw(RuntimeError("nede")))
    assert rute.chat_pending_approval("chat-1") == {"approval": None}
