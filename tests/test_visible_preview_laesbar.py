"""Chiffertekst maa aldrig naa en dommer/prompt via `text_preview`.

Delt vaern: `visible_preview_crypto.laesbaar_preview`. Klartekst passerer
uaendret; `enc:` bliver dekrypteret naar noeglen kan bevises, ellers erstattet
af en pladsholder der siger at svaret ikke kan bevises.
"""
from __future__ import annotations

from datetime import UTC, datetime

from core.services import chat_crypto
from core.services.visible_preview_crypto import (
    PLADSHOLDER_KRYPTERET,
    laesbaar_preview,
)


def _chiffer(monkeypatch):
    import core.services.keyring_store as keys
    monkeypatch.setattr(keys, "get_user_key", lambda _uid: b"x" * 32)
    return chat_crypto.krypter("Michelles private svar", "medlem-x")


def test_klartekst_og_tom_passerer_uaendret():
    assert laesbaar_preview("et almindeligt svar", "s", "u") == "et almindeligt svar"
    assert laesbaar_preview("", "s", "u") == ""
    assert laesbaar_preview(None) is None


def test_chiffer_uden_provbar_noegle_bliver_pladsholder(monkeypatch):
    chiffer = _chiffer(monkeypatch)
    ud = laesbaar_preview(chiffer)
    assert ud == PLADSHOLDER_KRYPTERET
    assert "enc:" not in ud
    assert laesbaar_preview(chiffer, "ukendt-session", "ukendt-bruger") == PLADSHOLDER_KRYPTERET


def test_chiffer_dekrypteres_naar_medlem_kan_bevises(monkeypatch):
    chiffer = _chiffer(monkeypatch)
    monkeypatch.setattr(chat_crypto, "medlem_for_raekke", lambda **kw: "medlem-x")
    assert laesbaar_preview(chiffer, None, "u") == "Michelles private svar"
    monkeypatch.setattr(chat_crypto, "medlem_for_raekke", lambda **kw: None)
    monkeypatch.setattr(chat_crypto, "medlem_for_session", lambda sid, conn=None: "medlem-x")
    assert laesbaar_preview(chiffer, "sess", None) == "Michelles private svar"


def test_forkert_noegle_giver_pladsholder_ikke_chiffer(monkeypatch):
    chiffer = _chiffer(monkeypatch)
    import core.services.keyring_store as keys
    monkeypatch.setattr(keys, "get_user_key", lambda _uid: b"y" * 32)
    monkeypatch.setattr(chat_crypto, "medlem_for_raekke", lambda **kw: "medlem-x")
    assert laesbaar_preview(chiffer, None, "u") == PLADSHOLDER_KRYPTERET


def test_recent_visible_runs_uden_user_id_leverer_aldrig_chiffer(monkeypatch):
    import core.runtime.db_visible as dbv
    chiffer = _chiffer(monkeypatch)

    class _Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a, **k):
            class _R:
                def fetchall(_s):
                    return [{"run_id": "r1", "lane": "visible", "provider": "p",
                             "model": "m", "status": "completed",
                             "started_at": datetime.now(UTC).isoformat(),
                             "finished_at": "", "text_preview": chiffer,
                             "error": chiffer, "capability_id": ""},
                            {"run_id": "r2", "lane": "visible", "provider": "p",
                             "model": "m", "status": "completed", "started_at": "",
                             "finished_at": "", "text_preview": "klartekst",
                             "error": None, "capability_id": ""}]
            return _R()
    monkeypatch.setattr(dbv, "connect", lambda: _Conn())
    rk = dbv.recent_visible_runs(limit=5)
    assert rk[0]["text_preview"] == PLADSHOLDER_KRYPTERET
    assert rk[0]["error"] == PLADSHOLDER_KRYPTERET
    assert rk[1]["text_preview"] == "klartekst"


def test_deep_reflection_springer_pladsholder_over(monkeypatch):
    import core.runtime.db as db_mod
    from core.services import deep_reflection_slot as slot
    nu = datetime.now(UTC).isoformat()
    raekker = [{"started_at": nu, "text_preview": PLADSHOLDER_KRYPTERET},
               {"started_at": nu, "text_preview": "et almindeligt svar"}]
    monkeypatch.setattr(db_mod, "recent_visible_runs", lambda **kw: raekker)
    monkeypatch.setattr(db_mod, "list_private_brain_records", lambda **kw: [])
    samlet = "\n".join(slot._chronicle_summary())
    assert "et almindeligt svar" in samlet
    assert "krypteret" not in samlet


def test_mc_run_detail_viser_ikke_chiffer(isolated_runtime, monkeypatch):
    chiffer = _chiffer(monkeypatch)
    db = isolated_runtime.db
    with db.connect() as conn:
        db_visible = __import__("core.runtime.db_visible", fromlist=["x"])
        db_visible.ensure_visible_tables(conn)
        conn.execute(
            "INSERT INTO visible_runs (run_id, lane, provider, model, status, "
            "started_at, finished_at, text_preview, error, user_id) "
            "VALUES ('r-enc','visible','p','m','completed','t','t',?,?,'')",
            (chiffer, chiffer))
        conn.commit()
    import apps.api.jarvis_api.routes.mission_control_dashboard as dash
    monkeypatch.setattr(dash, "_run_synlig_for_kalder", lambda conn, rid: True)
    ud = dash.mc_run_detail("r-enc")
    assert ud["run"]["text_preview"] == PLADSHOLDER_KRYPTERET
    assert "enc:" not in str(ud["run"])
