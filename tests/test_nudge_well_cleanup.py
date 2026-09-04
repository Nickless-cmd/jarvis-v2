from __future__ import annotations

import json
import sqlite3

from scripts import nudge_well_cleanup as C


def test_clean_broend_drops_only_pending_autonomous(tmp_path):
    p = tmp_path / "nudge_broend.json"
    p.write_text(json.dumps([
        {"nudge_id": "a", "status": "pending", "source": "autonomous_run", "message": "✓ færdig"},
        {"nudge_id": "b", "status": "pending", "source": "kilo_checkin", "message": "checkin"},
        {"nudge_id": "c", "status": "sent", "source": "autonomous_run", "message": "x"},
    ]), encoding="utf-8")
    assert C.clean_broend(False, p)["would_drop"] == 1
    out = C.clean_broend(True, p)
    assert out["dropped"] == 1
    left = json.loads(p.read_text(encoding="utf-8"))
    assert [n["nudge_id"] for n in left] == ["b", "c"]


def test_clean_outbound_dismisses_telemetry_and_reroutes(tmp_path, monkeypatch):
    db = tmp_path / "j.sqlite"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE outbound_nudges (nudge_id TEXT, source TEXT, kind TEXT, message TEXT, importance TEXT, status TEXT, created_at TEXT, dismissed_at TEXT)")
    c.executemany("INSERT INTO outbound_nudges VALUES (?,?,?,?,?,?,?,NULL)", [
        ("n1", "autonomous_run", "autonomous_run", "✓ færdig", "normal", "inspected", "2026-09-04T10:00:00"),
        ("n2", "user_midway_followup", "other", "gammel midway", "high", "pending", "2026-09-01T10:00:00"),
        ("n3", "run_closure_gate", "runtime", "3 ucommittede filer i repoet efter autonomt run", "high", "pending", "2026-09-04T10:00:00"),
    ])
    c.commit()
    c.close()

    class _Ctx:
        def __enter__(self):
            self.c = sqlite3.connect(db)
            return self.c

        def __exit__(self, *a):
            self.c.close()
            return False

    monkeypatch.setattr(C, "connect", lambda: _Ctx())
    added = []
    monkeypatch.setattr("core.services.proactive_candidates.add_candidate",
                        lambda **kw: (added.append(kw), {"status": "added"})[1])
    dry = C.clean_outbound(False)
    assert dry == {"telemetry_to_dismiss": 1, "stale_midway_to_dismiss": 1, "pending_to_reroute": 1}
    out = C.clean_outbound(True)
    assert out["rerouted"] == 1 and added[0]["priority"] == "high"
    c = sqlite3.connect(db)
    assert c.execute("SELECT count(*) FROM outbound_nudges WHERE status='dismissed'").fetchone()[0] == 3
