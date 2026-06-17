"""Google app-login: bruger-opslag via google_email_hash + login-beslutning.

Sikkerheds-kernen: en Google-email matcher KUN en forud-oprettet konto (ingen
self-service). GDPR: kun et deterministisk hash gemmes, aldrig rå Google-email.
"""
import uuid
from core.identity import user_db


def _mk_user(email: str) -> dict:
    return user_db.create_user(email=email, name="T", password="pw12345", role="member")  # pragma: allowlist secret


def test_set_and_find_by_google_email():
    em = f"{uuid.uuid4().hex}@gmail.com"
    u = _mk_user(em)
    uid = u["user_id"]
    # Endnu ikke linket → intet match.
    assert user_db.find_user_by_google_email(em) is None
    # Link Google-email → match.
    assert user_db.set_google_email(uid, em) is True
    found = user_db.find_user_by_google_email(em)
    assert found is not None
    assert found["user_id"] == uid


def test_find_by_google_email_no_match():
    assert user_db.find_user_by_google_email(f"{uuid.uuid4().hex}@nowhere.test") is None


def test_login_flow_match_issues_token(monkeypatch):
    from core.services import google_login as gl
    em = f"{uuid.uuid4().hex}@gmail.com"
    u = _mk_user(em)
    user_db.set_google_email(u["user_id"], em)
    nonce, state = gl.begin_login(app_id="app1")
    assert gl.is_login_state(state)
    msg = gl.complete(state, em)
    assert "Logget ind" in msg
    res = gl.take_result(nonce)
    assert res["status"] == "ok"
    assert res["user_id"] == u["user_id"]
    assert res["token"]
    # Engangs: anden hentning er væk.
    assert gl.take_result(nonce) is None


def test_login_flow_no_account():
    from core.services import google_login as gl
    nonce, state = gl.begin_login()
    msg = gl.complete(state, f"{uuid.uuid4().hex}@nowhere.test")
    assert "Ingen" in msg
    res = gl.take_result(nonce)
    assert res["status"] == "error" and res["error"] == "no_account"


def test_link_flow_sets_google_email():
    from core.services import google_login as gl
    em = f"{uuid.uuid4().hex}@gmail.com"
    u = _mk_user(em)  # ingen google-link endnu
    assert user_db.find_user_by_google_email(em) is None
    nonce, state = gl.begin_link(u["user_id"])
    gl.complete(state, em)
    assert user_db.find_user_by_google_email(em)["user_id"] == u["user_id"]
    assert gl.take_result(nonce)["status"] == "ok"
