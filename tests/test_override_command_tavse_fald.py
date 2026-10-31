"""De to tavse fald i `override_command` — målt 31/10-2026.

Filen havde INGEN logger. Begge fald kvitterede `ok: True` uanset om den
handling der blev rapporteret faktisk lykkedes: en fejlet oplåsning blev
svaret "Session/konto låst op", og et manglende audit-spor blev et override
der så korrekt aktiveret ud.

Hver vagt beviser TO ting: at fejlen efterlader et spor, OG at returværdien
er uændret. Kontrakten (ok=True for en gyldig kode) er en politik, ikke en
fejl — kun sporet er tilføjet.
"""
from __future__ import annotations

import logging

from core.services import override_command as O


def _kaster(exc: Exception):
    def _f(*a, **k):
        raise exc
    return _f


# ── 1. !unlock: koden var gyldig, men oplåsningen fejlede ──
def test_unlock_fejl_logger_og_bevarer_svaret(monkeypatch, caplog):
    monkeypatch.setattr(O, "record_attempt", lambda *a, **k: True)
    monkeypatch.setattr(O, "verify", lambda *a, **k: True)
    import core.services.security_guard as sg
    monkeypatch.setattr(sg, "unlock_session", _kaster(RuntimeError("db nede")))
    with caplog.at_level(logging.WARNING):
        r = O.handle_override_command("!unlock 123456", session_id="s1", owner_seed="SEED")
    assert r["ok"] is True and r["action"] == "unlocked"
    assert "db nede" in caplog.text and "!unlock fejlede" in caplog.text


# ── 2. !override: audit-sporet kunne ikke skrives ──
def test_override_audit_fejl_logger_og_bevarer_svaret(monkeypatch, caplog):
    monkeypatch.setattr(O, "record_attempt", lambda *a, **k: True)
    monkeypatch.setattr(O, "verify", lambda *a, **k: True)
    monkeypatch.setattr(O.override_store, "grant", lambda *a, **k: None)
    import core.services.security_guard as sg
    monkeypatch.setattr(sg, "record_audit", _kaster(RuntimeError("audit-db nede")))
    with caplog.at_level(logging.WARNING):
        r = O.handle_override_command("!override 123456", session_id="s2", owner_seed="SEED")
    assert r["ok"] is True and r["action"] == "granted"
    assert "audit-db nede" in caplog.text


# ── 3. støj-vagt: normal drift må ikke skrive én eneste advarsel ──
def test_normal_drift_stoejer_ikke(monkeypatch, caplog):
    monkeypatch.setattr(O, "record_attempt", lambda *a, **k: True)
    monkeypatch.setattr(O, "verify", lambda *a, **k: True)
    monkeypatch.setattr(O.override_store, "grant", lambda *a, **k: None)
    import core.services.security_guard as sg
    monkeypatch.setattr(sg, "record_audit", lambda *a, **k: None)
    with caplog.at_level(logging.WARNING):
        O.handle_override_command("!override 123456", session_id="s3", owner_seed="SEED")
        O.handle_override_command("hej med dig", session_id="s3", owner_seed="SEED")
    advarsler = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert not advarsler, f"normal drift støjede: {[r.message for r in advarsler]}"


# ── 4. RETNINGEN: en forkert kode giver stadig afvisning ──
def test_forkert_kode_afvises_stadig(monkeypatch):
    monkeypatch.setattr(O, "record_attempt", lambda *a, **k: True)
    monkeypatch.setattr(O, "verify", lambda *a, **k: False)
    r = O.handle_override_command("!override 000000", session_id="s4", owner_seed="SEED")
    assert r["ok"] is False and r["reason"] == "invalid_code"
