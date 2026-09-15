"""Oprydningen lukker kun flows hvis opgave er afsluttet — og intet andet."""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "luk_foraeldede_flows",
    Path(__file__).resolve().parents[1] / "scripts" / "luk_foraeldede_flows.py",
)
L = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(L)


def _db():
    c = sqlite3.connect(":memory:", isolation_level=None)
    c.execute("CREATE TABLE runtime_tasks (task_id TEXT, status TEXT)")
    c.execute("CREATE TABLE runtime_flows (flow_id TEXT, task_id TEXT, status TEXT, "
              "step_state TEXT, updated_at TEXT)")
    for tid, tstatus, fstatus in [
        ("t1", "succeeded", "queued"),
        ("t2", "expired", "queued"),
        ("t3", "failed", "running"),
        ("t4", "running", "queued"),     # aaben opgave: roeres ikke
        ("t5", "succeeded", "failed"),   # afsluttet flow: skrives ikke om
    ]:
        c.execute("INSERT INTO runtime_tasks VALUES (?, ?)", (tid, tstatus))
        c.execute("INSERT INTO runtime_flows VALUES (?, ?, ?, '', '')", ("f" + tid[1], tid, fstatus))
    return c


def _status(c, fid):
    return c.execute("SELECT status FROM runtime_flows WHERE flow_id = ?", (fid,)).fetchone()[0]


def test_finder_kun_aabne_flows_med_afsluttet_opgave():
    c = _db()
    fundne = {f["flow_id"]: f["ny_status"] for f in L.find_foraeldede(c)}
    assert fundne == {"f1": "succeeded", "f2": "cancelled", "f3": "failed"}


def test_lukning_foelger_opgaven_og_roerer_ikke_resten():
    c = _db()
    assert L.luk(c, L.find_foraeldede(c)) == 3
    assert _status(c, "f1") == "succeeded"
    assert _status(c, "f2") == "cancelled"    # expired findes ikke for flows
    assert _status(c, "f3") == "failed"
    assert _status(c, "f4") == "queued"
    assert _status(c, "f5") == "failed"
    assert L.find_foraeldede(c) == []         # idempotent


def test_testdata_kun_AABNE_opgaver_i_vinduet():
    c = sqlite3.connect(":memory:", isolation_level=None)
    c.execute("CREATE TABLE runtime_tasks (task_id TEXT, status TEXT, kind TEXT, goal TEXT, "
              "created_at TEXT, updated_at TEXT, result_summary TEXT)")
    for tid, status, ts in [
        ("i-vindue-aaben", "queued", "2026-05-15T11:15:00+00:00"),
        ("i-vindue-faerdig", "succeeded", "2026-05-15T11:15:00+00:00"),
        ("foer-vinduet", "queued", "2026-05-15T10:01:00+00:00"),
        ("blokeret-jarvis", "blocked", "2026-05-25T15:27:00+00:00"),
    ]:
        c.execute("INSERT INTO runtime_tasks VALUES (?, ?, 'k', 'g', ?, '', '')", (tid, status, ts))
    fundne = L.find_testdata(c)
    assert [t["task_id"] for t in fundne] == ["i-vindue-aaben"]
    L.annuller_testdata(c, fundne)
    assert c.execute("SELECT status FROM runtime_tasks WHERE task_id='i-vindue-aaben'").fetchone()[0] == "cancelled"
    assert c.execute("SELECT status FROM runtime_tasks WHERE task_id='foer-vinduet'").fetchone()[0] == "queued"
