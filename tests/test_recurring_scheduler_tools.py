"""Tests for set_recurring_channel-tool (notif-routing Phase 3)."""
import core.runtime.db as db
import core.runtime.db_core as db_core
import core.services.recurring_tasks as rt
from core.tools.recurring_scheduler_tools import (
    _exec_list_recurring,
    _exec_set_recurring_channel,
    _exec_set_recurring_weekdays,
    _exec_schedule_recurring,
)


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    db.init_db()
    rt._ensure_table()


def test_set_recurring_channel_tool_ok(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="brief", interval_minutes=60)
    tid = t["task_id"]
    r = _exec_set_recurring_channel({"task_id": tid, "channel": "desktop"})
    assert r["status"] == "ok" and r["channel"] == "desktop"


def test_set_recurring_channel_tool_validates(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    r = _exec_set_recurring_channel({"task_id": "x", "channel": "owl"})
    assert r["status"] == "error"


# ── Ugedage ───────────────────────────────────────────────────────────────────
# Bjoern 28/9-2026: «begraens medicin-paamindelserne til hverdage».


def test_set_recurring_weekdays_tool_ok(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440)
    tid = t["task_id"]
    r = _exec_set_recurring_weekdays({"task_id": tid, "weekdays": "man-fre"})
    assert r["status"] == "ok"
    assert r["weekdays"] == "1,2,3,4,5"
    with db.connect() as c:
        ud = c.execute(
            "SELECT weekdays FROM recurring_tasks WHERE task_id=?", (tid,)
        ).fetchone()[0]
    assert ud == "1,2,3,4,5"


def test_set_recurring_weekdays_tool_kaster_paa_tastefejl(tmp_path, monkeypatch):
    _fresh(tmp_path, monkeypatch)
    t = rt.create_recurring_task(focus="medicin", interval_minutes=1440)
    r = _exec_set_recurring_weekdays(
        {"task_id": t["task_id"], "weekdays": "torsdagsagtigt"}
    )
    assert r["status"] == "error"


def test_schedule_recurring_videresender_ugedage(monkeypatch):
    """Ugedage skal hele vejen igennem VAERKTOEJET, ikke kun i servicen —
    ellers kan Jarvis ikke saette dem naar han opretter en opgave."""
    fanget: dict = {}

    def _fang(**kw):
        fanget.update(kw)
        return {
            "task_id": "rec-1", "focus": kw["focus"],
            "next_fire_at": "2026-09-29T04:15:00+00:00", "weekdays": "1,2,3,4,5",
        }

    monkeypatch.setattr(rt, "create_recurring_task", _fang)
    r = _exec_schedule_recurring({"focus": "medicin", "interval": 1, "unit": "days",
                                  "weekdays": "man-fre"})
    assert fanget.get("weekdays") == "man-fre"
    assert r["status"] == "ok"
    assert r["weekdays"] == "1,2,3,4,5"
    assert "1,2,3,4,5" in r["text"]


# ── Terminale tilstande ───────────────────────────────────────────────────────
# Bjoern 12/10-2026: «luk Kickbacks-wait-state som fuldfoert». `completed` er en
# terminal tilstand ved siden af `cancelled` — opgaven naaede sit maal og skal
# ikke fyre igen. Listen viste den alligevel som KOERENDE, fordi filteret var
# `!= 'cancelled'`; og summary'en faldt den ud af begge lister, mens `total`
# stadig talte den med. Begge dele maalt 12/10-2026.


def _saet_status(task_id: str, status: str) -> None:
    with db.connect() as c:
        c.execute(
            "UPDATE recurring_tasks SET status=? WHERE task_id=?", (status, task_id)
        )


def test_liste_skjuler_terminale_tilstande(tmp_path, monkeypatch):
    """En `completed` eller `disabled` opgave maa ikke staa i listen over det
    der fyrer — den fyrer ikke."""
    _fresh(tmp_path, monkeypatch)
    aktiv = rt.create_recurring_task(focus="koerer", interval_minutes=60)
    faerdig = rt.create_recurring_task(focus="fuldfoert", interval_minutes=60)
    slukket = rt.create_recurring_task(focus="slukket", interval_minutes=60)
    _saet_status(faerdig["task_id"], "completed")
    _saet_status(slukket["task_id"], "disabled")

    ids = {t["task_id"] for t in _exec_list_recurring({})["tasks"]}
    assert ids == {aktiv["task_id"]}, f"listen viste ogsaa {ids - {aktiv['task_id']}}"

    # Filteret er et VALG, ikke et tab: include_cancelled giver dem tilbage.
    alle = {t["task_id"] for t in _exec_list_recurring({"include_cancelled": True})["tasks"]}
    assert {aktiv["task_id"], faerdig["task_id"], slukket["task_id"]} <= alle


def test_state_taeller_completed(tmp_path, monkeypatch):
    """Summary'en skal kende `completed` — foer faldt den ud af baade `active`
    og `cancelled_count`, mens `total` talte den med."""
    _fresh(tmp_path, monkeypatch)
    rt.create_recurring_task(focus="aktiv", interval_minutes=60)
    faerdig = rt.create_recurring_task(focus="fuldfoert", interval_minutes=60)
    _saet_status(faerdig["task_id"], "completed")

    s = rt.get_recurring_tasks_state()
    assert s["completed_count"] == 1
    assert len(s["active"]) == 1
    assert s["total"] == 2
