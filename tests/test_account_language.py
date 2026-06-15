import asyncio

import apps.api.jarvis_api.routes.account as acc


def test_set_language_member(monkeypatch):
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": "u_m"})
    captured = {}
    monkeypatch.setattr(acc.user_db, "set_language",
                        lambda uid, lang: captured.update(uid=uid, lang=lang) or True)
    res = asyncio.run(acc.account_set_language({"language": "en"}))
    assert res["status"] == "ok"
    assert res["language"] == "en"
    assert captured == {"uid": "u_m", "lang": "en"}


def test_set_language_validates():
    res = asyncio.run(acc.account_set_language({"language": "klingon"}))
    assert res["status"] == "error"


def test_set_language_owner_no_db_write(monkeypatch):
    monkeypatch.setattr(acc, "current_context_snapshot", lambda: {"user_id": ""})
    called = {"n": 0}
    monkeypatch.setattr(acc.user_db, "set_language", lambda uid, lang: called.__setitem__("n", called["n"] + 1) or True)
    res = asyncio.run(acc.account_set_language({"language": "da"}))
    assert res["status"] == "ok"
    assert called["n"] == 0  # owner har ingen bruger-række — ingen skrivning
