"""Multi-klient integrationstest — kerne-lektien fra A3 ('verificeret med kun curl').
KRÆVER: jarvis-api på 127.0.0.1:8080 MED server_authoritative_runs=true, og en
gyldig owner-token i env JARVIS_TEST_TOKEN.
"""
import json
import os
import urllib.error
import urllib.request

import pytest

BASE = "http://127.0.0.1:8080"
TOK = os.environ.get("JARVIS_TEST_TOKEN", "")
pytestmark = pytest.mark.skipif(not TOK, reason="kræver JARVIS_TEST_TOKEN + kørende api")


def _post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
        method="POST")
    return urllib.request.urlopen(req, timeout=40)


def _mk_session():
    r = _post("/chat/sessions", {"title": "satest"})
    return json.load(r)["session"]["id"]


def _read_data_frames(resp, limit=99999):
    out = []
    for raw in resp:
        line = raw.decode(errors="replace")
        if line.startswith("data:"):
            out.append(line)
            if "message_stop" in line:
                break
        if len(out) >= limit:
            break
    return out


def test_drop_midstream_then_resubscribe_reaches_message_stop():
    sid = _mk_session()
    resp = _post("/chat/stream/v2", {
        "session_id": sid, "message": "Tael langsomt til 15",
        "approval_mode": "trust", "thinking_mode": "none"})
    run_id = resp.headers.get("X-Run-Id")
    assert run_id, "server-autoritativ sti skal saette X-Run-Id (flag ON?)"
    first = _read_data_frames(resp, limit=5)   # læs lidt, drop så
    resp.close()
    offset = len(first)
    req = urllib.request.Request(
        f"{BASE}/chat/runs/{run_id}/subscribe?from_idx={offset}",
        headers={"Authorization": f"Bearer {TOK}"})
    resp2 = urllib.request.urlopen(req, timeout=60)
    rest = _read_data_frames(resp2)
    resp2.close()
    assert any("message_stop" in f for f in rest), "reconnect skal naa message_stop"


def test_unknown_run_404():
    req = urllib.request.Request(
        f"{BASE}/chat/runs/visible-doesnotexist/subscribe",
        headers={"Authorization": f"Bearer {TOK}"})
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=10)
    assert e.value.code == 404
