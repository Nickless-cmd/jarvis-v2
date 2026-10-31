"""Vagter for de fem tavse fald i identity_guard.py (31/10-2026).

Fejlformen der blev rettet: et ``except`` returnerede en vaerdi der er IDENTISK
med den legitime tilstand. ``0`` = baade «ingen tidligere pushback» og «tællingen
kunne ikke laeses». ``""`` = baade «brugeren har intet navn» og «opslaget fejlede».
Uden et spor kan ingen af delene skelnes bagefter.

Hver vagt beviser TO ting:
1. fejlen efterlader et spor (WARNING paa modul-loggeren), og
2. returvaerdien er stadig den fail-soft vaerdi kalderne forventer.

Retningen er BEVIDST uændret — det er kun sporet der er nyt.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import core.services.identity_guard as ig

LOGGER = "core.services.identity_guard"


def _advarsler(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


def _patch_known(monkeypatch, mapping):
    monkeypatch.setattr(ig, "_known_user_names", lambda: mapping)


def test_pushback_count_logger_men_svarer_nul(isolated_runtime, monkeypatch, caplog):
    """En ulaeselig tælling bliver 0 — hvilket betyder at eskaleringen aldrig naar sin graense."""

    def _braek(*_a, **_k):
        raise RuntimeError("runtime_state utilgaengelig")

    monkeypatch.setattr(ig, "get_runtime_state_value", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        n = ig._pushback_count("chat-x1")
    assert n == 0, "fail-soft returvaerdi skal vaere uaendret"
    assert any("pushback-tælling" in m for m in _advarsler(caplog)), (
        "en ulaeselig tælling efterlod intet spor"
    )


def test_bump_pushback_logger_men_returnerer_naeste(isolated_runtime, monkeypatch, caplog):
    """Returnerer n som om tællingen blev gemt — gør den ikke, fyrer lockdown aldrig."""

    def _braek(*_a, **_k):
        raise RuntimeError("db locked")

    monkeypatch.setattr(ig, "get_runtime_state_value", lambda *_a, **_k: {"count": 2})
    monkeypatch.setattr(ig, "set_runtime_state_value", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        n = ig._bump_pushback("chat-x2")
    assert n == 3, "fail-soft returvaerdi skal vaere uaendret"
    assert any("gemme pushback-tælling" in m for m in _advarsler(caplog)), (
        "en fejlet skrivning efterlod intet spor"
    )


def test_reset_pushback_logger_men_kaster_ikke(isolated_runtime, monkeypatch, caplog):
    """Står tællingen fast, fyrer næste besked lockdown uden en ny pushback."""

    def _braek(*_a, **_k):
        raise RuntimeError("db locked")

    monkeypatch.setattr(ig, "set_runtime_state_value", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        ig.reset_pushback("chat-x3")  # maa ikke kaste
    assert any("nulstille pushback" in m for m in _advarsler(caplog)), (
        "en fejlet nulstilling efterlod intet spor"
    )


def test_display_name_logger_men_svarer_tom(isolated_runtime, monkeypatch, caplog):
    """Tomt navn goer at ejerens EGET navn ikke matcher → ejeren faar pushback."""

    import core.identity.users as users

    def _braek(*_a, **_k):
        raise RuntimeError("users.json ulaeselig")

    monkeypatch.setattr(users, "find_user_by_discord_id", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        navn = ig._display_name_for("OWNER1")
    assert navn == "", "fail-soft returvaerdi skal vaere uaendret"
    assert any("display-navn" in m for m in _advarsler(caplog)), (
        "et fejlet navne-opslag efterlod intet spor"
    )


def test_override_fejl_logger_og_bevarer_retningen(isolated_runtime, monkeypatch, caplog):
    """Kan override-status ikke laeses, behandles den som inaktiv — men ikke i tavshed."""
    _patch_known(monkeypatch, {"bjørn": "OWNER1", "lotte": "LOTTE1"})

    def _braek(*_a, **_k):
        raise RuntimeError("override_store nede")

    monkeypatch.setattr(ig.override_store, "is_active", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        res = ig.check_identity(
            "jeg hedder Bjørn", session_id="chat-x5",
            session_user_id="LOTTE1", session_display_name="Lotte",
        )
    assert res is not None and res["action"] == "pushback", (
        "fail-closed retning skal vaere uaendret: ukendt override = ikke aktiv"
    )
    assert any("override-status" in m for m in _advarsler(caplog)), (
        "et fejlet override-opslag efterlod intet spor"
    )


def test_normal_drift_stoejer_ikke(isolated_runtime, monkeypatch, caplog):
    """STOEJ-VAGT: en helt normal spoof-sag maa ikke skrive en eneste af vores advarsler.

    Uden den her drukner de aegte fejl i normal-adfaerd — og saa er sporet vaerdiloest.
    """
    _patch_known(monkeypatch, {"bjørn": "OWNER1", "lotte": "LOTTE1"})
    monkeypatch.setattr(ig.override_store, "is_active", lambda *_a, **_k: False)
    monkeypatch.setattr(
        ig, "_display_name_for", lambda uid: "Lotte" if uid == "LOTTE1" else "",
    )
    import core.identity.users as users
    monkeypatch.setattr(
        users, "find_user_by_discord_id",
        lambda uid: SimpleNamespace(name="Lotte") if uid == "LOTTE1" else None,
    )
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        ig._pushback_count("chat-x6")
        ig._bump_pushback("chat-x6")
        ig._display_name_for("LOTTE1")
        res = ig.check_identity(
            "jeg hedder Bjørn", session_id="chat-x6",
            session_user_id="LOTTE1", session_display_name="Lotte",
        )
        ig.reset_pushback("chat-x6")
    assert res is not None and res["action"] == "pushback"
    mine = [m for m in _advarsler(caplog) if "identity_guard:" in m]
    assert mine == [], f"normal drift skrev advarsler: {mine}"
