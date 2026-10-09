"""Web-push-abonnementer: gem, hent og slet — mod en isoleret in-memory DB."""
from __future__ import annotations

import contextlib
import sqlite3

import pytest


@pytest.fixture()
def w(monkeypatch):
    conn = sqlite3.connect(":memory:")

    @contextlib.contextmanager
    def _connect():
        yield conn
        conn.commit()

    import core.services.web_push_subscriptions as mod
    monkeypatch.setattr(mod, "connect", _connect)
    monkeypatch.setattr(mod, "_ENSURED", False)
    yield mod
    conn.close()


def test_gem_hent_og_slet(w):
    w.save("u1", "https://push/x", "P", "A")
    assert w.list_for_user("u1") == [{"endpoint": "https://push/x", "p256dh": "P", "auth": "A"}]
    w.delete("https://push/x")
    assert w.list_for_user("u1") == []


def test_samme_endpoint_opdateres_frem_for_at_dubles(w):
    """Endpointet er nøglen: et nyt abonnement på samme endpoint må ikke give to rækker."""
    w.save("u1", "https://push/x", "P1", "A1")
    w.save("u1", "https://push/x", "P2", "A2")
    rows = w.list_for_user("u1")
    assert len(rows) == 1
    assert rows[0]["p256dh"] == "P2"


def test_tom_bruger_og_tomt_endpoint_roerer_intet(w):
    assert w.list_for_user("") == []
    w.save("", "https://x", "P", "A")
    w.save("u1", "", "P", "A")
    assert w.list_for_user("u1") == []


def test_abonnementer_er_adskilt_pr_bruger(w):
    w.save("u1", "https://push/a", "P", "A")
    w.save("u2", "https://push/b", "P", "A")
    assert [r["endpoint"] for r in w.list_for_user("u1")] == ["https://push/a"]
    assert [r["endpoint"] for r in w.list_for_user("u2")] == ["https://push/b"]
