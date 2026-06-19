import core.services.fcm_gateway as fcm


def test_build_message_is_data_only_high_priority():
    msg = fcm._build_message("tok-X", {"kind": "answer_ready", "session_id": "s1"})
    body = msg["message"]
    assert body["token"] == "tok-X"
    assert body["data"] == {"kind": "answer_ready", "session_id": "s1"}
    assert "notification" not in body  # data-only → Google ser intet indhold
    assert body["android"]["priority"] == "high"


def test_send_unregistered_returns_invalid(monkeypatch):
    monkeypatch.setattr(fcm, "is_configured", lambda: True)
    monkeypatch.setattr(fcm, "_access_token", lambda: "fake-oauth")
    monkeypatch.setattr(fcm, "_project_id", lambda: "proj-1")
    import urllib.request
    from urllib.error import HTTPError
    import io

    def _fake_urlopen(req, timeout=0):
        raise HTTPError(
            req.full_url, 404, "Not Found", {},
            io.BytesIO(b'{"error":{"status":"NOT_FOUND","message":"Requested entity was not found."}}'),
        )
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    ok, code = fcm.send("tok-dead", {"kind": "answer_ready"})
    assert ok is False
    assert code == "invalid"
