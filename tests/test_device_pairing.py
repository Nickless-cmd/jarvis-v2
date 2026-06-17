from core.services import device_pairing as dp


def test_create_and_redeem_once():
    r = dp.create_pairing("u123", "owner")
    assert r["status"] == "ok" and r["code"]
    code = r["code"]
    res = dp.redeem(code)
    assert res and res["status"] == "ok"
    assert res["user_id"] == "u123" and res["role"] == "owner" and res["token"]
    # Engangs: anden redeem fejler.
    assert dp.redeem(code) is None


def test_redeem_unknown():
    assert dp.redeem("nope") is None


def test_expired(monkeypatch):
    r = dp.create_pairing("u1", now=1000.0)
    # 200s senere → udløbet (TTL 120).
    assert dp.redeem(r["code"], now=1000.0 + 200) is None
