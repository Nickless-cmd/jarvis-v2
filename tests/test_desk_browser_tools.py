"""Jarvis' EGEN browser i desk — otte værktøjer over broen (21/9-2026).

Baggrun: handlersne laa faerdige i desk'ens `electron/bridge.ts`, men var ikke
registreret i runtimen. Maalt 21/9 naaede `bridge_registry.dispatch` frem og
virkede — men kun ad den interne cross-process-dispatch med shared-secret, altsaa
en bagdoer. Disse tests laaser at vaerktoejerne nu er RIGTIGE: registrerede,
scopede, validerede, og at de sender de rigtige argumenter til broen.

Det sidste er ikke formelt: `click` tager koordinater fra et skaermbillede, og
sender man dem som tekst i stedet for tal, fejler broen laengere ude end noedvendigt.
"""
from __future__ import annotations

import asyncio

import pytest

import core.tools.desk_browser_tools as db
import core.tools.simple_tools_operator as sto

ALLE = (
    "jarvis_browser_open", "jarvis_browser_navigate", "jarvis_browser_read",
    "jarvis_browser_click", "jarvis_browser_type", "jarvis_browser_screenshot",
    "jarvis_browser_tabs", "jarvis_browser_close",
)


@pytest.fixture
def bro(monkeypatch):
    """Fanger bro-kaldet i stedet for at tale med en anden maskine."""
    kaldt: dict = {}

    async def _fake_bro(*, tool, args, user_id, timeout_s):
        kaldt.update(tool=tool, args=args, user_id=user_id)
        return {"echo": tool}

    def _fake_run(coro_fn, *, tool_name, timeout_s=35.0):
        return {"status": "ok", "result": asyncio.run(coro_fn())}

    monkeypatch.setattr(db, "_bro", _fake_bro)
    monkeypatch.setattr(sto, "_run_operator_async", _fake_run)
    monkeypatch.setattr(sto, "_operator_user_id", lambda a: "bjorn")
    return kaldt


# ── registrering og scoping ─────────────────────────────────────────────


def test_alle_otte_er_registreret_som_vaerktoejer():
    from core.tools import simple_tools as st
    for n in ALLE:
        assert n in st._TOOL_HANDLERS, f"{n} mangler i handler-mappingen"


def test_alle_otte_er_i_begge_scopes():
    """Uden for scope annonceres vaerktoejet ikke — og findes reelt ikke.
    Code-scope har sin EGEN, smalle liste, saa begge skal tjekkes."""
    from core.tools.tool_scoping import CHAT_MODE_TOOLS_BASE, CODE_MODE_TOOLS_BASE
    for n in ALLE:
        assert n in CHAT_MODE_TOOLS_BASE, f"{n} mangler i chat-scope"
        assert n in CODE_MODE_TOOLS_BASE, f"{n} mangler i code-scope"


def test_definitions_og_handlers_naevner_praecis_de_samme():
    navne_d = {d["function"]["name"] for d in db.DESK_BROWSER_TOOL_DEFINITIONS}
    assert navne_d == set(db.DESK_BROWSER_TOOL_HANDLERS) == set(ALLE)
    assert set(db.DESK_BROWSER_TOOL_NAMES) == set(ALLE)


# ── validering: fejler FOER broen kaldes ────────────────────────────────


class TestValidering:
    def test_open_uden_url(self, bro):
        assert db._exec_jarvis_browser_open({"url": "  "})["status"] == "error"
        assert bro == {}, "broen blev kaldt med en tom URL"

    def test_navigate_uden_url(self, bro):
        assert db._exec_jarvis_browser_navigate({})["status"] == "error"
        assert bro == {}

    def test_click_uden_koordinater(self, bro):
        assert db._exec_jarvis_browser_click({"x": 10})["status"] == "error"
        assert db._exec_jarvis_browser_click({})["status"] == "error"
        assert bro == {}

    def test_click_afviser_ikke_tal(self, bro):
        r = db._exec_jarvis_browser_click({"x": "midt", "y": 10})
        assert r["status"] == "error" and "tal" in r["error"]
        assert bro == {}

    def test_type_uden_tekst(self, bro):
        assert db._exec_jarvis_browser_type({"text": ""})["status"] == "error"
        assert bro == {}

    def test_close_kraever_fane_id(self, bro):
        """Uden id ved broen ikke HVILKEN fane — og `Number(undefined)` = NaN."""
        assert db._exec_jarvis_browser_close({})["status"] == "error"
        assert bro == {}


# ── bro-kaldet: de rigtige argumenter ───────────────────────────────────


class TestBroKaldet:
    def test_open_sender_url_og_bruger(self, bro):
        db._exec_jarvis_browser_open({"url": "https://jarvis.srvlab.dk"})
        assert bro["tool"] == "jarvis_browser_open"
        assert bro["args"] == {"url": "https://jarvis.srvlab.dk"}
        assert bro["user_id"] == "bjorn"

    def test_uden_tab_id_udelades_noeglen(self, bro):
        """Udeladt `tab_id` = ram den AKTIVE fane. Sendte vi None med, ville
        broen skulle skelne None fra «aktiv» — den skelner ikke."""
        db._exec_jarvis_browser_read({})
        assert bro["args"] == {}

    def test_tab_id_bliver_et_tal(self, bro):
        db._exec_jarvis_browser_read({"tab_id": "3"})
        assert bro["args"] == {"tab_id": 3}

    def test_click_sender_koordinater_som_tal(self, bro):
        db._exec_jarvis_browser_click({"x": "120", "y": 44})
        assert bro["args"] == {"x": 120.0, "y": 44.0}

    def test_tabs_sender_ingen_argumenter(self, bro):
        db._exec_jarvis_browser_tabs({})
        assert bro["tool"] == "jarvis_browser_tabs" and bro["args"] == {}

    def test_close_sender_fane_id(self, bro):
        db._exec_jarvis_browser_close({"tab_id": 2})
        assert bro["args"] == {"tab_id": 2}

    def test_screenshot_videresender_broens_svar(self, bro, monkeypatch):
        async def _png(*, tool, args, user_id, timeout_s):
            return {"image_base64": "iVBORw0KGgo=", "format": "png"}

        monkeypatch.setattr(db, "_bro", _png)
        ud = db._exec_jarvis_browser_screenshot({})
        assert ud["status"] == "ok"
        assert ud["result"]["image_base64"] == "iVBORw0KGgo="


def test_broens_fejl_videreformidles_uaendret(monkeypatch):
    """Et aerligt svar om hvad der gik galt er mere vaerd end et paent et."""
    def _fejl(coro_fn, *, tool_name, timeout_s=35.0):
        return {"status": "error", "error": "bridge_not_connected"}

    monkeypatch.setattr(sto, "_run_operator_async", _fejl)
    monkeypatch.setattr(sto, "_operator_user_id", lambda a: "bjorn")
    ud = db._exec_jarvis_browser_tabs({})
    assert ud["status"] == "error" and ud["error"] == "bridge_not_connected"
