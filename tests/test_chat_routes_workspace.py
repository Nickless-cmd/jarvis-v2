"""Code-mode: workspace-binding via /chat/sessions + mode→tool_scope mapping."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes.chat import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_create_session_persists_workspace(isolated_runtime):
    r = client.post("/chat/sessions", json={
        "title": "kode", "workspace_kind": "container", "workspace_root": "core",
    })
    assert r.status_code == 200
    sid = r.json()["session"]["id"]
    full = client.get(f"/chat/sessions/{sid}").json()
    assert full["session"]["workspace_kind"] == "container"
    assert full["session"]["workspace_root"] == "core"


# ── Mode + samtalens ART → tool-scope (24/9-2026) ────────────────────────────
#
# Målt på Bjørns egen samtale `chat-aa57a6d2…`: kind='code' i databasen,
# workspace bundet til repoet — og alligevel svarede broen `mode=chat` på hver
# besked. Mobilen satte mode fra «Fuld adgang»-indstillingen (hvis standard er
# 'samtale') og ikke fra fladen, så skærmbilledet og hele computer-use-gruppen
# blev afvist i en samtale der ellers VAR code.
#
# Reglen: fladen er GULVET. Mode kan HÆVE (chat-samtale + fuld adgang = code),
# men ikke SÆNKE en code-samtale.

def test_udled_tool_scope_mode_alene():
    from apps.api.jarvis_api.routes.chat_stream_v2 import udled_tool_scope
    assert udled_tool_scope("code", "chat") == "code"
    assert udled_tool_scope("chat", "chat") == "chat"
    assert udled_tool_scope("", "chat") == ""
    assert udled_tool_scope("ukendt", None) == ""
    assert udled_tool_scope("", None) == ""


def test_udled_tool_scope_kind_er_gulvet():
    from apps.api.jarvis_api.routes.chat_stream_v2 import udled_tool_scope
    # Det målte tilfælde: code-samtale, klienten sender chat.
    assert udled_tool_scope("chat", "code") == "code"
    assert udled_tool_scope("", "code") == "code"
    assert udled_tool_scope("code", "code") == "code"
    # Og intet andet mode kan sænke den.
    assert udled_tool_scope("cowork", "code") == "code"


def test_session_kind_laeser_et_felt_uden_historik(isolated_runtime):
    """`session_kind` må ikke bygge samtalen — se scripts/verify_history_reads."""
    from core.services.chat_sessions import create_chat_session, session_kind
    kode = create_chat_session(title="Kode-session", kind="code")["id"]
    almindelig = create_chat_session(title="Ny samtale", kind="chat")["id"]
    assert session_kind(kode) == "code"
    assert session_kind(almindelig) == "chat"
    assert session_kind("findes-ikke") is None
    assert session_kind("") is None
