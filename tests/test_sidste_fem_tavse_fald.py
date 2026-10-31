"""De sidste fem tavse fald — målt 31/10-2026.

Fire filer, fem fald, alle af samme form som de 89 der blev rettet før dem:
`except` returnerede en værdi der er IDENTISK med den legitime tilstand.

Én af dem er en ny variant: `channel_inbound.register_builtin_channel_plugins`
loggede intet OG satte `_BUILTINS_REGISTERED = True` uanset udfaldet — så en
fejlet registrering ikke bare var tavs, den var PERMANENT i processen.

Retningen er uændret i alle fem. Det der blev tilføjet er et spor.
"""
from __future__ import annotations

import logging
import sqlite3

import pytest

from core.runtime import db_private_brain as dpb
from core.services import channel_inbound as ci
from core.services import jarvis_brain_visibility as jbv
from core.tools import tool_scoping as ts


def _advarsler(caplog: pytest.LogCaptureFixture) -> list[str]:
    # getMessage(), ikke message % args: LogRecord.message er allerede formateret
    # når pytest har rørt record'en, og dobbelt-formatering kaster TypeError.
    return [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]


# ── channel_inbound ─────────────────────────────────────────────────────────

def test_register_builtin_logger_og_saetter_flaget(monkeypatch, caplog):
    """En fejlet plugin-registrering var både tavs OG permanent."""
    def _kaster(_manifest):
        raise RuntimeError("plugin-registret nede")

    monkeypatch.setattr(ci, "register_plugin", _kaster)
    monkeypatch.setattr(ci, "_BUILTINS_REGISTERED", False)

    with caplog.at_level(logging.WARNING, logger=ci.logger.name):
        ci.register_builtin_channel_plugins()

    assert any("discord-local" in m for m in _advarsler(caplog)), \
        "en fejlet registrering efterlod intet spor"
    # Retningen er UÆNDRET: flaget sættes alligevel, så kaldet er stadig idempotent.
    assert ci._BUILTINS_REGISTERED is True, "idempotens-flaget må ikke ændre adfærd"


def test_register_builtin_stoejer_ikke_ved_normal_drift(monkeypatch, caplog):
    """Støj-vagt: en vellykket registrering må ikke skrive en advarsel."""
    monkeypatch.setattr(ci, "register_plugin", lambda _m: None)
    monkeypatch.setattr(ci, "_BUILTINS_REGISTERED", False)

    with caplog.at_level(logging.WARNING, logger=ci.logger.name):
        ci.register_builtin_channel_plugins()

    assert _advarsler(caplog) == [], "normal registrering skrev støj i loggen"
    assert ci._BUILTINS_REGISTERED is True


# ── jarvis_brain_visibility ─────────────────────────────────────────────────

def test_resolve_owner_logger_begge_opslag_og_svarer_none(monkeypatch, caplog):
    """To tavse hop gjorde et brudt ejer-opslag identisk med «ingen ejer»."""
    from core.identity import owner_resolver as orr

    def _kaster(*_a, **_k):
        raise RuntimeError("users.json ulæselig")

    monkeypatch.setattr(orr, "get_owner_discord_id", _kaster)
    monkeypatch.setattr(orr, "get_owner_user_id", _kaster, raising=False)

    with caplog.at_level(logging.WARNING, logger=jbv.logger.name):
        assert jbv._resolve_owner_id() is None

    besked = " ".join(_advarsler(caplog))
    assert "discord-id-opslag" in besked, "discord-opslagets fejl var tavs"
    assert "ejer-opslag fejlede" in besked, "det andet opslags fejl var tavs"


def test_resolve_owner_stoejer_ikke_naar_opslaget_virker(monkeypatch, caplog):
    from core.identity import owner_resolver as orr

    monkeypatch.setattr(orr, "get_owner_discord_id", lambda: "1246415163603816499")

    with caplog.at_level(logging.WARNING, logger=jbv.logger.name):
        assert jbv._resolve_owner_id() == "1246415163603816499"

    assert _advarsler(caplog) == []


# ── db_private_brain ────────────────────────────────────────────────────────

class _KasterPaaAlter:
    """Stub-conn: CREATE TABLE/INDEX går igennem, ALTER kaster som SQLite gør
    når kolonnen allerede findes — eller som en låst DB gør. De to var ens."""

    def __init__(self) -> None:
        self.alter_forsoeg = 0

    def execute(self, sql, *_a):
        if str(sql).strip().upper().startswith("ALTER TABLE"):
            self.alter_forsoeg += 1
            raise sqlite3.OperationalError("duplicate column name")
        return self

    def commit(self) -> None:
        pass


def test_ensure_tabel_logger_begge_kolonne_forsoeg(caplog):
    conn = _KasterPaaAlter()
    with caplog.at_level(logging.WARNING, logger=dpb.logger.name):
        dpb._ensure_private_brain_records_table(conn)  # må ikke kaste

    assert conn.alter_forsoeg == 2, "begge ALTER-forsøg skal stadig gøres"
    besked = " ".join(_advarsler(caplog))
    assert "salience" in besked, "salience-faldet var tavst"
    assert "domain" in besked, "domain-faldet var tavst"


# ── tool_scoping ────────────────────────────────────────────────────────────

def test_adb_er_opsat_logger_og_svarer_false(monkeypatch, caplog):
    """False skjuler adb-værktøjerne — sikker retning, men ulæselig config
    er ikke det samme som «adresse ikke sat»."""
    import core.runtime.secrets as secrets

    def _kaster(*_a, **_k):
        raise RuntimeError("runtime.json kunne ikke læses")

    monkeypatch.setattr(secrets, "read_runtime_key", _kaster)

    with caplog.at_level(logging.WARNING, logger=ts.logger.name):
        assert ts._adb_er_opsat() is False

    assert any("phone_adb_address" in m for m in _advarsler(caplog)), \
        "en ulæselig config efterlod intet spor"


def test_adb_er_opsat_stoejer_ikke_naar_noeglen_findes(monkeypatch, caplog):
    import core.runtime.secrets as secrets

    monkeypatch.setattr(secrets, "read_runtime_key", lambda _k: "10.0.0.20:5555")

    with caplog.at_level(logging.WARNING, logger=ts.logger.name):
        assert ts._adb_er_opsat() is True

    assert _advarsler(caplog) == []
