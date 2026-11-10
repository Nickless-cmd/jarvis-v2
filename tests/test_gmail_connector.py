"""Gmail-connector: search/list via brugerens egen token (mocket httpx)."""
from __future__ import annotations

import httpx

import core.services.gmail_connector as gc


class _Resp:
    def __init__(self, status: int, payload: dict):
        self.status_code = status
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _mock_http(monkeypatch, list_payload, detail_payload, *, list_status=200, detail_status=200):
    calls = {"n": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        calls["n"] += 1
        if "/messages/" in url:  # detail-kald
            return _Resp(detail_status, detail_payload)
        return _Resp(list_status, list_payload)  # liste-kald

    monkeypatch.setattr(httpx, "get", fake_get)
    return calls


def test_search_returns_enriched_messages(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    _mock_http(
        monkeypatch,
        {"messages": [{"id": "m1"}]},
        {"snippet": "Hej Bjørn", "labelIds": ["UNREAD"],
         "payload": {"headers": [
             {"name": "Subject", "value": "Møde i morgen"},
             {"name": "From", "value": "chef@firma.dk"},
             {"name": "Date", "value": "Tue, 17 Jun 2026"},
         ]}},
    )
    res = gc.search("bjorn", "is:unread", max_results=5)
    assert res["status"] == "ok"
    assert res["count"] == 1
    m = res["messages"][0]
    assert m["subject"] == "Møde i morgen"
    assert m["from"] == "chef@firma.dk"
    assert m["unread"] is True
    assert m["snippet"] == "Hej Bjørn"


def test_no_token_is_not_connected(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: None)
    res = gc.list_inbox("bjorn")
    assert res == {"status": "error", "error": "gmail_not_connected"}


def test_403_maps_to_scope_missing(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    _mock_http(monkeypatch, {}, {}, list_status=403)
    res = gc.list_inbox("bjorn")
    assert res["status"] == "error" and res["error"] == "gmail_scope_missing"


def test_empty_query_rejected(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    assert gc.search("bjorn", "   ")["error"] == "query_required"


def test_send_message_ok(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["has_raw"] = "raw" in (json or {})
        return _Resp(200, {"id": "sent123"})

    monkeypatch.setattr(httpx, "post", fake_post)
    res = gc.send_message("bjorn", "ven@x.dk", "Hej", "Hvordan går det?")
    assert res == {"status": "ok", "id": "sent123"}
    assert captured["has_raw"] is True and captured["url"].endswith("/messages/send")


def test_send_no_token(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: None)
    assert gc.send_message("bjorn", "x@x.dk", "s", "b")["error"] == "gmail_not_connected"


def test_send_requires_recipient(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    assert gc.send_message("bjorn", "", "s", "b")["error"] == "to_required"


def test_max_results_clamped(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})
    seen = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        if "/messages/" not in url:
            seen["maxResults"] = params.get("maxResults")
        return _Resp(200, {"messages": []})

    monkeypatch.setattr(httpx, "get", fake_get)
    gc.list_inbox("bjorn", max_results=999)
    assert seen["maxResults"] == 25  # klemt til 25


# --- gmail_modify: den manglende primitive -----------------------------------
# Alle oprydninger indtil 8/11-2026 kørte via midlertidige IMAP-scripts i
# /var/tmp der ikke fandtes i repoet. Disse tests værner den primitive der
# erstattede dem.


def _modify_token(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: {"access_token": "tok"})


def test_dry_run_roerer_ikke_api(monkeypatch):
    """Den vigtigste vagt: dry_run må ikke sende ét eneste kald til Gmail."""
    _modify_token(monkeypatch)
    kaldt = {"post": 0}

    def fake_post(url, headers=None, json=None, timeout=None):
        kaldt["post"] += 1
        return _Resp(204, {})

    monkeypatch.setattr(httpx, "post", fake_post)
    res = gc.modify_messages("bjorn", ["a", "b", "c"])
    assert res["status"] == "ok"
    assert res["dry_run"] is True
    assert res["count"] == 3
    assert kaldt["post"] == 0, "dry_run sendte et API-kald"


def test_trash_sender_rigtige_labels(monkeypatch):
    _modify_token(monkeypatch)
    set_kald = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        set_kald.update(json or {})
        set_kald["_url"] = url
        return _Resp(204, {})

    monkeypatch.setattr(httpx, "post", fake_post)
    res = gc.modify_messages("bjorn", ["m1", "m2"], action="trash", dry_run=False)
    assert res["status"] == "ok" and res["modified"] == 2
    assert set_kald["addLabelIds"] == ["TRASH"]
    assert set_kald["removeLabelIds"] == ["INBOX"]
    assert set_kald["ids"] == ["m1", "m2"]
    assert set_kald["_url"].endswith("/messages/batchModify")


def test_archive_fjerner_kun_indbakke(monkeypatch):
    _modify_token(monkeypatch)
    set_kald = {}
    monkeypatch.setattr(httpx, "post",
                        lambda url, headers=None, json=None, timeout=None: (
                            set_kald.update(json or {}) or _Resp(204, {})))
    gc.modify_messages("bjorn", ["m1"], action="archive", dry_run=False)
    assert set_kald["removeLabelIds"] == ["INBOX"]
    assert set_kald["addLabelIds"] == []


def test_untrash_gaar_tilbage(monkeypatch):
    _modify_token(monkeypatch)
    set_kald = {}
    monkeypatch.setattr(httpx, "post",
                        lambda url, headers=None, json=None, timeout=None: (
                            set_kald.update(json or {}) or _Resp(204, {})))
    gc.modify_messages("bjorn", ["m1"], action="untrash", dry_run=False)
    assert set_kald["addLabelIds"] == ["INBOX"]
    assert set_kald["removeLabelIds"] == ["TRASH"]


def test_403_er_scope_missing_ikke_succes(monkeypatch):
    _modify_token(monkeypatch)
    monkeypatch.setattr(httpx, "post",
                        lambda url, headers=None, json=None, timeout=None: _Resp(403, {}))
    res = gc.modify_messages("bjorn", ["m1"], dry_run=False)
    assert res["status"] == "error"
    assert res["error"] == "gmail_scope_missing"


def test_netvaerksfejl_ligner_ikke_succes(monkeypatch):
    """En kastet undtagelse må aldrig ende som status=ok."""
    _modify_token(monkeypatch)

    def boom(url, headers=None, json=None, timeout=None):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(httpx, "post", boom)
    res = gc.modify_messages("bjorn", ["m1"], dry_run=False)
    assert res["status"] == "error"
    assert "modified" not in res


def test_ukendt_handling_afvises(monkeypatch):
    _modify_token(monkeypatch)
    res = gc.modify_messages("bjorn", ["m1"], action="slet-alt")
    assert res["status"] == "error"
    assert "ukendt_handling" in res["error"]
    assert res["gyldige"] == ["archive", "trash", "untrash"]


def test_tom_liste_afvises(monkeypatch):
    _modify_token(monkeypatch)
    assert gc.modify_messages("bjorn", [])["error"] == "message_ids_required"


def test_loft_paa_500(monkeypatch):
    _modify_token(monkeypatch)
    res = gc.modify_messages("bjorn", [f"m{i}" for i in range(501)])
    assert res["status"] == "error"
    assert "for_mange_ids" in res["error"]


def test_intet_token(monkeypatch):
    monkeypatch.setattr(gc, "get_fresh_token", lambda uid, prov: None)
    assert gc.modify_messages("bjorn", ["m1"])["error"] == "gmail_not_connected"


def test_handler_er_registreret():
    """Uden dispatch-post er værktøjet defineret men dødt."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    assert "gmail_modify" in _TOOL_HANDLERS


def test_definition_er_synlig_for_modellen():
    navne = [d["function"]["name"] for d in gc.GMAIL_CONNECTOR_TOOL_DEFINITIONS]
    assert "gmail_modify" in navne


# ── gmail_get: fuld brødtekst (10/11-2026) ────────────────────────────────
#
# `gmail_search`/`gmail_list` bruger format=metadata og giver kun et snippet.
# Målt 10/11-2026: svaret fra Krak lå EFTER snippet-grænsen, så jeg kunne ikke
# afgøre hvad de faktisk havde forbeholdt sig. Denne vej findes for at lukke
# præcis det hul.

def _full_payload(parts, *, headers=None):
    return {
        "id": "m1",
        "labelIds": ["UNREAD"],
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": headers if headers is not None else [
                {"name": "Subject", "value": "Re: Indsigelse"},
                {"name": "From", "value": "privatperson@krak.dk"},
                {"name": "To", "value": "onkeladolf@gmail.com"},
                {"name": "Date", "value": "Tue, 10 Nov 2026 10:00:00 +0100"},
            ],
            "parts": parts,
        },
    }


def _del(mime, tekst):
    import base64
    return {
        "mimeType": mime,
        "body": {"data": base64.urlsafe_b64encode(tekst.encode()).decode()},
    }


def test_get_message_giver_hele_braedteksten(monkeypatch):
    """Kernen: teksten EFTER snippet-grænsen skal med."""
    monkeypatch.setattr(gc, "_token", lambda uid: {"access_token": "t"})
    lang = "Første afsnit. " + ("fyld " * 300) + "FORBEHOLD: vi gemmer data."
    payload = _full_payload([_del("text/plain", lang), _del("text/html", "<p>html</p>")])
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(200, payload))

    svar = gc.get_message("bjorn", "m1")

    assert svar["status"] == "ok"
    assert "FORBEHOLD" in svar["body"], "halen af teksten skal vaere med"
    assert svar["content_type"] == "text/plain"
    assert svar["subject"] == "Re: Indsigelse"
    assert svar["from"] == "privatperson@krak.dk"
    assert svar["unread"] is True


def test_get_message_falder_tilbage_til_html(monkeypatch):
    """Kun-html-mails findes; så skal body ikke være tom."""
    monkeypatch.setattr(gc, "_token", lambda uid: {"access_token": "t"})
    payload = _full_payload([_del("text/html", "<p>kun html her</p>")])
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(200, payload))

    svar = gc.get_message("bjorn", "m1")

    assert svar["status"] == "ok"
    assert "kun html her" in svar["body"]
    assert svar["content_type"] == "text/html"


def test_get_message_finder_dele_i_dybden(monkeypatch):
    """Brødtekst kan ligge nested i parts[].parts[] — ikke kun på toppen."""
    monkeypatch.setattr(gc, "_token", lambda uid: {"access_token": "t"})
    dyb = {"mimeType": "multipart/mixed", "parts": [_del("text/plain", "dybt liggende svar")]}
    payload = _full_payload([dyb])
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(200, payload))

    svar = gc.get_message("bjorn", "m1")

    assert "dybt liggende svar" in svar["body"]


def test_get_message_kraever_id():
    assert gc.get_message("bjorn", "")["error"] == "message_id_required"


def test_get_message_uden_token(monkeypatch):
    monkeypatch.setattr(gc, "_token", lambda uid: None)
    assert gc.get_message("bjorn", "m1")["error"] == "gmail_not_connected"


def test_get_message_ukendt_id_giver_404(monkeypatch):
    monkeypatch.setattr(gc, "_token", lambda uid: {"access_token": "t"})
    monkeypatch.setattr(httpx, "get", lambda url, **kw: _Resp(404, {}))
    assert gc.get_message("bjorn", "findes-ikke")["error"] == "message_not_found"


def test_gmail_get_er_registreret_og_synlig():
    """Uden dispatch-post er værktøjet defineret men dødt."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    assert "gmail_get" in _TOOL_HANDLERS
    navne = [d["function"]["name"] for d in gc.GMAIL_CONNECTOR_TOOL_DEFINITIONS]
    assert "gmail_get" in navne
