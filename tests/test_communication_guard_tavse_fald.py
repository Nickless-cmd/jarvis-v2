"""Vagter for de fem tavse fald i communication_guard.py (31/10-2026).

Fejlformen der blev rettet: et ``except`` faldt tilbage til en vaerdi der er
IDENTISK med den legitime tilstand.

``_load`` faldt til standard-fraserne baade naar filen ikke fandtes OG naar
den var korrupt — saa en oedelagt fil fjernede tavst enhver tilfoejet graense.
``_safe_parse_iso`` og de to TTL-grene gav en ulaeselig ``ttl_until`` lov til
at goere en MIDLERTIDIG graense PERMANENT — det stik modsatte af hvad «ttl»
lover.

Hver vagt beviser TO ting:
  1. fejlen efterlader et spor (WARNING paa modul-loggeren), og
  2. returvaerdien er stadig den fail-soft vaerdi kalderne forventer.

Plus én stoj-vagt: normal drift maa ikke skrive en eneste advarsel, ellers
drukner de aegte fejl i normal-adfaerd.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta

import pytest

import core.services.communication_guard as cg

LOGGER = "core.services.communication_guard"


def _advarsler(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


@pytest.fixture
def guard_fil(tmp_path, monkeypatch):
    """En state-fil i tmp_path — den levende state roeres aldrig."""
    p = tmp_path / "communication_guard.json"
    monkeypatch.setattr(cg, "_GUARD_FILE", p)
    return p


# ── 1. _load: korrupt fil ────────────────────────────────────────────────


def test_korrupt_fil_logger_men_bruger_standard(guard_fil, caplog):
    """Ugyldig JSON giver stadig standard-fraserne — men ikke i tavshed."""
    guard_fil.write_text("{ikke json", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        triggers = cg._load()
    assert triggers == cg._DEFAULT_TRIGGERS, "standard-fraserne skal stadig bruges"
    assert any("kunne ikke laese" in m for m in _advarsler(caplog)), (
        "en korrupt fil efterlod intet spor"
    )


def test_ikke_liste_logger_men_bruger_standard(guard_fil, caplog):
    """Gyldig JSON der ikke er en liste — samme fald, anden gren."""
    guard_fil.write_text(json.dumps({"fraser": []}), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        triggers = cg._load()
    assert triggers == cg._DEFAULT_TRIGGERS
    assert any("indeholder ikke en liste" in m for m in _advarsler(caplog)), (
        "en fil med forkert form efterlod intet spor"
    )


# ── 2. scan: ulaeselig ttl_until ─────────────────────────────────────────


def test_scan_ulaeselig_ttl_behandles_som_udloebet(guard_fil, caplog):
    """En TTL vi ikke kan laese maa ikke blive permanent i scan-stien."""
    guard_fil.write_text(json.dumps([{
        "phrase": "testfrase",
        "kind": "ttl",
        "severity": "hard",
        "reason": "midlertidig",
        "ttl_turns": 5,
        "ttl_until": "ikke-en-dato",
    }]), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        hit = cg.scan("her staar testfrase")
    assert hit is None, "en ulaeselig TTL maa ikke matche for evigt"
    assert any("ttl_until" in m for m in _advarsler(caplog)), (
        "den ulaeselige TTL efterlod intet spor"
    )


# ── 3. _trigger_active: samme fejlform, anden funktion ───────────────────


def test_trigger_active_ulaeselig_ttl_er_udloebet(caplog):
    """_trigger_active skal svare False — og sige hvorfor."""
    t = {
        "phrase": "x",
        "kind": "ttl",
        "ttl_turns": 5,
        "ttl_until": "ikke-en-dato",
    }
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        aktiv = cg._trigger_active(t, datetime.now(UTC))
    assert aktiv is False, "ulaeselig TTL skal regnes som udloebet"
    assert any("ttl_until" in m for m in _advarsler(caplog)), (
        "faldet efterlod intet spor"
    )


# ── 4. _safe_parse_iso ───────────────────────────────────────────────────


def test_safe_parse_iso_logger_og_bevarer_retningen(caplog):
    """Ukendt dato giver stadig «langt ude i fremtiden» — men nu synligt."""
    now = datetime.now(UTC)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        ud = cg._safe_parse_iso("ikke-en-dato", now)
    assert ud == now + timedelta(days=365), "retningen skal vaere uaendret"
    assert any("ttl_until" in m for m in _advarsler(caplog)), (
        "det tavse fald efterlod intet spor"
    )


# ── 5. guard_channel_text: Centralen kunne ikke naas ─────────────────────


def test_central_fejl_logger_men_teksten_renses(guard_fil, caplog, monkeypatch):
    """Centralen er observability — dens fejl maa ikke vaelte udsendelsen."""
    guard_fil.write_text(json.dumps([{
        "phrase": "godnat",
        "kind": "permanent",
        "severity": "hard",
        "reason": "test",
        "ttl_turns": None,
        "ttl_until": None,
    }]), encoding="utf-8")

    import core.services.central_core as cc

    def _braek():
        raise RuntimeError("centralen er nede")

    monkeypatch.setattr(cc, "central", _braek)
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        ud = cg.guard_channel_text("hej. godnat. vi ses", "discord")
    assert "godnat" not in ud.lower(), "rensningen skal stadig virke"
    assert "vi ses" in ud, "resten af beskeden skal overleve"
    assert any("Centralen" in m for m in _advarsler(caplog)), (
        "den manglende Central-rapport efterlod intet spor"
    )


# ── Stoej-vagt ───────────────────────────────────────────────────────────


def test_normal_drift_logger_intet(guard_fil, caplog):
    """Ingen advarsler ved normal drift — ellers drukner de aegte fejl."""
    guard_fil.write_text(json.dumps([{
        "phrase": "godnat",
        "kind": "permanent",
        "severity": "hard",
        "reason": "test",
        "ttl_turns": None,
        "ttl_until": None,
    }, {
        "phrase": "testfrase",
        "kind": "ttl",
        "severity": "soft",
        "reason": "midlertidig",
        "ttl_turns": 5,
        "ttl_until": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
    }]), encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger=LOGGER):
        cg._load()
        cg.scan("her staar testfrase")
        cg.enforce_outgoing("en helt almindelig besked")
        cg.guard_channel_text("en helt almindelig besked", "discord")
        cg.active_count()
        cg.cleanup_expired()
    assert _advarsler(caplog) == [], (
        f"normal drift skrev advarsler: {_advarsler(caplog)}"
    )
