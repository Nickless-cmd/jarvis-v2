"""Tests for recurring_tasks channel-felt (notif-routing Phase 3)."""
from datetime import UTC, datetime

import pytest
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()
    rt._ensure_table()


def test_channel_column_defaults_auto_and_set_channel(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="morgenbriefing", interval_minutes=1440)
    tid = t["task_id"]
    # default-kanal
    with db.connect() as c:
        ch = c.execute("SELECT channel FROM recurring_tasks WHERE task_id=?", (tid,)).fetchone()[0]
    assert ch == "auto"
    # sæt eksplicit kanal
    assert rt.set_channel(tid, "mobile") is True
    with db.connect() as c:
        ch = c.execute("SELECT channel FROM recurring_tasks WHERE task_id=?", (tid,)).fetchone()[0]
    assert ch == "mobile"


def test_set_channel_rejects_invalid(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        rt.set_channel("whatever", "smoke-signal")


def _minutter_til(iso: str) -> float:
    return (datetime.fromisoformat(iso) - datetime.now(UTC)).total_seconds() / 60


def test_delay_minutes_slaar_intervallet_for_foerste_affyring(tmp_path, monkeypatch):
    """Regression 18/9-2026: en eksplicit kort forsinkelse blev slugt af intervallet.

    Foer: ``first_fire = now + max(delay_minutes, interval_minutes)``. Satte man
    interval=365 dage for at lave en engangs-paamindelse og delay=13 dage, vandt
    intervallet — og foerste affyring landede ET AAR ude i fremtiden. Maalt i
    produktion da en moede-paamindelse blev sat til 2027 i stedet for 1. oktober.
    """
    _fresh(tmp_path, monkeypatch)
    # 365 dage interval (engangs-brug), 13 dages eksplicit forsinkelse.
    t = rt.create_recurring_task(
        focus="engangs-paamindelse", interval_minutes=525600, delay_minutes=19158
    )
    delta = _minutter_til(t["next_fire_at"])
    assert 19150 < delta < 19170, f"forventede ~19158 min, fik {delta:.0f}"


def test_delay_nul_giver_uaendret_foerste_affyring_efter_et_interval(tmp_path, monkeypatch):
    """Bagudkompatibilitet: delay=0 (alle eksisterende tasks) = efter ét interval."""
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="daglig", interval_minutes=1440)
    delta = _minutter_til(t["next_fire_at"])
    assert 1435 < delta < 1445, f"forventede ~1440 min, fik {delta:.0f}"
