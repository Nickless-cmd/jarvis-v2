"""Gmail-filtre: den varige oprydning (25/11-2026).

`gmail_modify` flytter mails der allerede er kommet. Et filter rammer dem der
kommer i morgen. Uden det er oprydning et evigt arbejde — målt 8/11-2026 sendte
myawardwallet.com tre mails samme dag under tre forskellige afsendernavne.

Testene dækker den normale vej OG de tre værn: `forward` er afvist, ukendte
felter afvises frem for at blive ignoreret, og `dry_run` er sand som standard.
"""
from __future__ import annotations

import httpx

import core.services.gmail_connector as gc


class _Resp:
    def __init__(self, status: int, payload: dict | None = None):
        self.status_code = status
        self._payload = payload or {}
        self.content = b"{}" if payload else b""

    def json(self) -> dict:
        return self._payload


def _token_ok(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})


def _token_none(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: None)


# ── list ──────────────────────────────────────────────────────────────────

def test_list_filters_returnerer_filtre(monkeypatch):
    _token_ok(monkeypatch)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(200, {"filter": [
        {"id": "f1", "criteria": {"from": "spam@x.dk"}, "action": {"removeLabelIds": ["INBOX"]}},
    ]}))
    res = gc.list_filters("michelle")
    assert res["status"] == "ok"
    assert res["count"] == 1
    assert res["filters"][0]["id"] == "f1"
    assert res["filters"][0]["criteria"]["from"] == "spam@x.dk"


def test_list_filters_uden_token(monkeypatch):
    _token_none(monkeypatch)
    assert gc.list_filters("michelle") == {"status": "error", "error": "gmail_not_connected"}


def test_list_filters_403_er_scope_missing(monkeypatch):
    _token_ok(monkeypatch)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(403))
    res = gc.list_filters("michelle")
    assert res["status"] == "error"
    assert res["error"] == "gmail_scope_missing"


def test_list_filters_tom_liste_er_ok(monkeypatch):
    _token_ok(monkeypatch)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(200, {}))
    res = gc.list_filters("michelle")
    assert res["status"] == "ok"
    assert res["count"] == 0


def test_list_filters_204_er_tom_liste(monkeypatch):
    """Gmail svarer 204 No Content når kontoen ingen filtre har.

    Målt 25/11-2026 mod Michelles konto: den gamle kode behandlede 204 som
    `gmail_http_204`, altså en fejl, selv om svaret betyder «ingen filtre».
    En mock der kun kender 200 kan ikke finde den slags — derfor står den her.
    """
    _token_ok(monkeypatch)
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(204))
    res = gc.list_filters("michelle")
    assert res["status"] == "ok"
    assert res["filters"] == []
    assert res["count"] == 0


# ── create ────────────────────────────────────────────────────────────────

def test_create_dry_run_roerer_ikke_api(monkeypatch):
    _token_ok(monkeypatch)

    def _boom(*a, **kw):
        raise AssertionError("dry_run må ikke kalde API'et")

    monkeypatch.setattr(httpx, "post", _boom)
    res = gc.create_filter("michelle", {"from": "spam@x.dk"}, {"removeLabelIds": ["INBOX"]})
    assert res["status"] == "ok"
    assert res["dry_run"] is True
    assert res["would_create"]["criteria"] == {"from": "spam@x.dk"}


def test_create_sender_rigtig_body(monkeypatch):
    _token_ok(monkeypatch)
    set_body = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        set_body.update(json or {})
        return _Resp(200, {"id": "f9", "criteria": json["criteria"], "action": json["action"]})

    monkeypatch.setattr(httpx, "post", fake_post)
    res = gc.create_filter(
        "michelle",
        {"from": "spam@x.dk"},
        {"removeLabelIds": ["INBOX"]},
        dry_run=False,
    )
    assert res["status"] == "ok"
    assert res["dry_run"] is False
    assert res["id"] == "f9"
    assert set_body["criteria"] == {"from": "spam@x.dk"}
    assert set_body["action"] == {"removeLabelIds": ["INBOX"]}


def test_forward_afvises(monkeypatch):
    """En videresendelsesregel kan lække hele postkassen — den er ikke et argument."""
    _token_ok(monkeypatch)

    def _boom(*a, **kw):
        raise AssertionError("forward må ikke nå API'et")

    monkeypatch.setattr(httpx, "post", _boom)
    res = gc.create_filter(
        "michelle",
        {"from": "spam@x.dk"},
        {"forward": "angriber@evil.tld"},
        dry_run=False,
    )
    assert res["status"] == "error"
    assert res["error"] == "forward_ikke_tilladt"


def test_ukendt_kriterium_afvises(monkeypatch):
    """Et ignoreret felt ville oprette et filter der matcher bredere end troet."""
    _token_ok(monkeypatch)
    res = gc.create_filter("michelle", {"fra": "spam@x.dk"}, {"removeLabelIds": ["INBOX"]})
    assert res["status"] == "error"
    assert "ukendte_kriterier" in res["error"]


def test_tomme_kriterier_afvises(monkeypatch):
    _token_ok(monkeypatch)
    res = gc.create_filter("michelle", {}, {"removeLabelIds": ["INBOX"]})
    assert res["status"] == "error"
    assert res["error"] == "criteria_required"


def test_kun_tom_streng_afvises(monkeypatch):
    _token_ok(monkeypatch)
    res = gc.create_filter("michelle", {"from": "   "}, {"removeLabelIds": ["INBOX"]})
    assert res["status"] == "error"
    assert res["error"] == "criteria_tomt"


def test_hasattachment_alene_er_gyldigt(monkeypatch):
    """`hasAttachment: true` er et fuldgyldigt filter uden andre kriterier."""
    _token_ok(monkeypatch)
    res = gc.create_filter("michelle", {"hasAttachment": True}, {"removeLabelIds": ["INBOX"]})
    assert res["status"] == "ok"
    assert res["dry_run"] is True


def test_ukendt_action_felt_afvises(monkeypatch):
    _token_ok(monkeypatch)
    res = gc.create_filter("michelle", {"from": "x@y.dk"}, {"addLabel": ["X"]})
    assert res["status"] == "error"
    assert "ukendte_action_felter" in res["error"]


def test_create_403_er_scope_missing(monkeypatch):
    _token_ok(monkeypatch)
    monkeypatch.setattr(httpx, "post", lambda *a, **kw: _Resp(403))
    res = gc.create_filter("michelle", {"from": "x@y.dk"}, {"removeLabelIds": ["INBOX"]},
                           dry_run=False)
    assert res["error"] == "gmail_scope_missing"


def test_create_uden_token(monkeypatch):
    _token_none(monkeypatch)
    res = gc.create_filter("michelle", {"from": "x@y.dk"}, {"removeLabelIds": ["INBOX"]})
    assert res == {"status": "error", "error": "gmail_not_connected"}


# ── delete ────────────────────────────────────────────────────────────────

def test_delete_dry_run_roerer_ikke_api(monkeypatch):
    _token_ok(monkeypatch)

    def _boom(*a, **kw):
        raise AssertionError("dry_run må ikke kalde API'et")

    monkeypatch.setattr(httpx, "delete", _boom)
    res = gc.delete_filter("michelle", "f1")
    assert res["status"] == "ok"
    assert res["dry_run"] is True
    assert res["would_delete"] == "f1"


def test_delete_sletter(monkeypatch):
    _token_ok(monkeypatch)
    kaldt = {}

    def fake_delete(url, headers=None, timeout=None):
        kaldt["url"] = url
        return _Resp(204)

    monkeypatch.setattr(httpx, "delete", fake_delete)
    res = gc.delete_filter("michelle", "f1", dry_run=False)
    assert res["status"] == "ok"
    assert res["deleted"] == "f1"
    assert kaldt["url"].endswith("/settings/filters/f1")


def test_delete_404_er_filter_not_found(monkeypatch):
    _token_ok(monkeypatch)
    monkeypatch.setattr(httpx, "delete", lambda *a, **kw: _Resp(404))
    res = gc.delete_filter("michelle", "f1", dry_run=False)
    assert res["status"] == "error"
    assert res["error"] == "filter_not_found"


def test_delete_kraever_id(monkeypatch):
    _token_ok(monkeypatch)
    res = gc.delete_filter("michelle", "  ", dry_run=False)
    assert res["status"] == "error"
    assert res["error"] == "filter_id_required"


# ── registrering ──────────────────────────────────────────────────────────

def test_handlers_er_registreret():
    """Uden dispatch-poster er værktøjerne defineret men døde."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    for navn in ("gmail_filter_list", "gmail_filter_create", "gmail_filter_delete"):
        assert navn in _TOOL_HANDLERS


def test_definitions_er_synlige_for_modellen():
    navne = [d["function"]["name"] for d in gc.GMAIL_CONNECTOR_TOOL_DEFINITIONS]
    for navn in ("gmail_filter_list", "gmail_filter_create", "gmail_filter_delete"):
        assert navn in navne


def test_connectoren_erklaerer_filter_tools():
    """Uden dem i connector-definitionen ser brugeren dem ikke i Marketplace."""
    from core.services.connectors import _CATALOG
    gmail = next(c for c in _CATALOG if c["id"] == "gmail")
    for navn in ("gmail_filter_list", "gmail_filter_create", "gmail_filter_delete"):
        assert navn in gmail["tools"]


def test_medlemmer_maar_bruge_filter_tools():
    from core.services.permission_engine import _MEMBER_GOOGLE
    for navn in ("gmail_filter_list", "gmail_filter_create", "gmail_filter_delete"):
        assert navn in _MEMBER_GOOGLE
