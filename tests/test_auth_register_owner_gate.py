"""Registrering maa kun naas af ejeren (22/10-2026).

Maalt i drift: `api.srvlab.dk` er offentligt tilgaengeligt (185.107.14.241:443),
og `POST /api/auth/register` svarede uden token. Ruten kaldte
`user_db.register_user()` direkte — ingen gate, ingen rolle-tjek. En fremmed
kunne oprette en konto, faa egen workspace og en verifikationsmail til sin egen
adresse, og dermed verificere sig selv.

Middleware-kommentaren paastod at «token issuance itself IS protected
(owner-only), via `_require_owner()` inside the route handler». Den funktion
fandtes ikke i auth.py.

Testen holder doeren lukket. Tre grene, og alle tre er noedvendige:
* ingen identitet bundet -> 403 (fail-closed)
* bundet, men ikke owner -> 403
* bundet owner -> kaldet gaar videre til register_user
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from apps.api.jarvis_api.routes import auth as auth_routes
from core.identity.workspace_context import reset_context, set_context


class _Req:
    """Minimal Request-stub — ruten bruger kun base_url."""

    def __init__(self, base_url: str = "http://test/") -> None:
        self.base_url = base_url


def _body(resp) -> dict:
    return json.loads(resp.body)


def _req() -> auth_routes.RegisterReq:
    return auth_routes.RegisterReq(email="ny@srvlab.dk", name="Ny", password="hemmelig123")  # pragma: allowlist secret


def test_register_afvises_uden_identitet(monkeypatch):
    kaldt: list[dict] = []
    monkeypatch.setattr(auth_routes.user_db, "register_user",
                        lambda **kw: kaldt.append(kw) or ({}, ""))

    resp = auth_routes.register(_req(), _Req())

    assert resp.status_code == 403
    assert _body(resp)["error"] == "owner_required"
    assert kaldt == [], "ingen bruger maa oprettes uden ejer-identitet"


def test_register_afvises_for_medlem(monkeypatch):
    kaldt: list[dict] = []
    monkeypatch.setattr(auth_routes.user_db, "register_user",
                        lambda **kw: kaldt.append(kw) or ({}, ""))
    monkeypatch.setattr("core.identity.users.find_user_by_discord_id",
                        lambda uid: SimpleNamespace(role="member"))

    tok = set_context(workspace_name="mikkel", user_id="42", role="member")
    try:
        resp = auth_routes.register(_req(), _Req())
    finally:
        reset_context(tok)

    assert resp.status_code == 403
    assert _body(resp)["error"] == "owner_required"
    assert kaldt == [], "et medlem maa ikke oprette konti"


def test_register_tillades_for_ejer(monkeypatch):
    kaldt: list[dict] = []
    monkeypatch.setattr(
        auth_routes.user_db, "register_user",
        lambda **kw: kaldt.append(kw) or ({"user_id": "u1", "email": kw["email"]}, "tok"))
    monkeypatch.setattr("core.identity.users.find_user_by_discord_id",
                        lambda uid: SimpleNamespace(role="owner"))

    tok = set_context(workspace_name="bjorn", user_id="1246415163603816499", role="owner")
    try:
        resp = auth_routes.register(_req(), _Req())
    finally:
        reset_context(tok)

    assert resp.status_code == 200
    assert len(kaldt) == 1
    assert _body(resp)["ok"] is True


def test_register_er_ikke_paa_public_paths():
    """Ruten maa ikke staa i _PUBLIC_PATHS — ellers springer middlewaren auth over."""
    from apps.api.jarvis_api.middleware import jarvisx_user_routing as mw

    assert "/api/auth/register" not in mw._PUBLIC_PATHS
    assert mw._is_public_path("/api/auth/register") is False
