"""Vagter for de seks tavse fald i security_guard.py (31/10-2026).

Modulets egen docstring lover det modsatte af hvad koden gjorde: «Fail-open-
princip (§11.4): hvis guard'en selv kaster, må den ALDRIG låse en session —
**log fejlen** og lad beskeden passere.» Kontrakten var skrevet; ingen af de
seks fald loggede noget som helst.

Fejlformen er den samme som i de ni foregående filer: ``except`` returnerer en
værdi der er IDENTISK med den legitime tilstand. ``0`` = både «ingen tidligere
låse» og «audit-tabellen kunne ikke læses». ``False`` = både «ikke ejer» og
«ejer-opslaget fejlede».

``is_owner`` er den farlige: svarer den False om ejeren selv, holder §12.3's
anti-self-lockout ikke, og et forbigående opslagsfejl låser Bjørn ude i 24
timer — uden et eneste spor.

Hver vagt beviser TO ting:
1. fejlen efterlader et spor (WARNING på modul-loggeren), og
2. returværdien er stadig den fail-soft værdi kalderne forventer.

Plus én støj-vagt: normal drift må ikke logge, ellers drukner de ægte fejl.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import core.identity.users as users
from core.runtime.db import connect
from core.services import security_guard as sg

LOGGER = "core.services.security_guard"


def _advarsler(caplog) -> list[str]:
    return [
        r.getMessage()
        for r in caplog.records
        if r.name == LOGGER and r.levelno >= logging.WARNING
    ]


def _braek_connect(monkeypatch):
    """Lad modulets DB-forbindelse kaste — uden at røre den ægte base."""
    def _braek():
        raise OSError("db nede")
    monkeypatch.setattr(sg, "connect", _braek)


@pytest.fixture
def ejer_er_en_anden(monkeypatch):
    """En ejer der IKKE er den bruger testene rører."""
    monkeypatch.setattr(
        users, "get_owner",
        lambda: SimpleNamespace(discord_id="OWNER-1", name="Bjørn", role="owner"),
    )


# ── 1. is_owner — den farlige (§12.3) ───────────────────────────────────
def test_is_owner_logger_naar_opslaget_fejler(monkeypatch, caplog):
    def _braek():
        raise RuntimeError("users.json ulaeselig")
    monkeypatch.setattr(users, "get_owner", _braek)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        svar = sg.is_owner("OWNER-1")

    # Retningen er bevaret: ukendt ejer giver ikke exempt.
    assert svar is False
    # Men den er ikke laengere tavs.
    assert any("owner-opslag" in m for m in _advarsler(caplog)), (
        "et fejlet ejer-opslag efterlod intet spor — saa kan §12.3 ikke holde"
    )


# ── 2. record_abuse ────────────────────────────────────────────────────
def test_record_abuse_logger_naar_skrivning_fejler(monkeypatch, caplog):
    _braek_connect(monkeypatch)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        sg.record_abuse("u1", "s1", "identity_spoof", "high")

    # Fail-soft: funktionen returnerer None og kaster ikke.
    assert any("abuse-event" in m for m in _advarsler(caplog)), (
        "et tabt abuse-event efterlod intet spor — eskaleringen udebliver tavst"
    )


# ── 3. lock_session ────────────────────────────────────────────────────
def test_lock_session_logger_naar_skrivning_fejler(monkeypatch, caplog):
    _braek_connect(monkeypatch)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        sg.lock_session("chat-x", "spoof", user_id="u1")

    assert any("laase session" in m for m in _advarsler(caplog)), (
        "en mislykket laasning efterlod intet spor — sessionen ser laast ud, men er aaben"
    )


# ── 4. unlock_session ──────────────────────────────────────────────────
def test_unlock_session_logger_naar_skrivning_fejler(monkeypatch, caplog):
    _braek_connect(monkeypatch)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        sg.unlock_session("chat-x", user_id="u1")

    assert any("op" in m and "session" in m for m in _advarsler(caplog)), (
        "en mislykket oplaasning efterlod intet spor"
    )


# ── 5. _lock_account ───────────────────────────────────────────────────
def test_lock_account_logger_naar_skrivning_fejler(monkeypatch, caplog, ejer_er_en_anden):
    _braek_connect(monkeypatch)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        sg._lock_account("member-x")

    assert any("account-lockdown" in m for m in _advarsler(caplog)), (
        "en mislykket lockdown efterlod intet spor — misbruget fortsatte uset"
    )


# ── 6. _recent_session_lock_count ──────────────────────────────────────
def test_recent_session_lock_count_logger_og_svarer_nul(monkeypatch, caplog):
    _braek_connect(monkeypatch)

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        svar = sg._recent_session_lock_count("u1")

    assert svar == 0
    assert any("session-laase" in m for m in _advarsler(caplog)), (
        "et fejlet optaelling efterlod intet spor — 0 ophaever eskaleringen i tavshed"
    )


# ── stoej-vagt: normal drift maa ikke logge ────────────────────────────
def test_normal_drift_logger_ikke(isolated_runtime, caplog, ejer_er_en_anden):
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chat_sessions (session_id, title, created_at, updated_at)"
            " VALUES (?,?,?,?)",
            ("chat-roej", "t", sg._iso(), sg._iso()),
        )

    with caplog.at_level(logging.WARNING, logger=LOGGER):
        sg.is_owner("member-x")
        sg.lock_session("chat-roej", "test", user_id="member-x")
        sg.unlock_session("chat-roej", user_id="member-x")
        sg.record_abuse("member-x", "chat-roej", "rate", "low")
        sg._recent_session_lock_count("member-x")

    assert _advarsler(caplog) == [], (
        f"normal drift stoejer i loggen: {_advarsler(caplog)}"
    )
