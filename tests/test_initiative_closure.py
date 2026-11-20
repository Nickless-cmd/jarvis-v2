"""Initiativ-løkkens to mekanismer (20/11-2026).

Maalt foer fixet: init-1107bcb628 blev materialiseret fire gange paa tre
timer — fire tasks og fire flows, alle attempt_count 0 — fordi intet i
heartbeat-banen kunne lukke det, og fordi udloebsloftet kraevede fire
forsoeg i stedet for tre.
"""
from __future__ import annotations

from core.services import initiative_queue as iq


def _fake_db(monkeypatch, *, status: str = "pending", attempt_count: int = 0):
    state = {"status": status, "attempt_count": attempt_count, "updates": []}

    def get(initiative_id):
        return {
            "initiative_id": initiative_id,
            "status": state["status"],
            "attempt_count": state["attempt_count"],
            "initiative_type": "initiative",
            "focus": "en fokus-tekst",
            "action_summary": "",
        }

    def update(initiative_id, **kw):
        state["updates"].append(kw)
        if "status" in kw:
            state["status"] = kw["status"]
        if "attempt_count" in kw:
            state["attempt_count"] = kw["attempt_count"]
        return True

    monkeypatch.setattr(iq.runtime_db, "get_runtime_initiative", get)
    monkeypatch.setattr(iq.runtime_db, "update_runtime_initiative", update)
    monkeypatch.setattr(iq.event_bus, "publish", lambda *a, **k: None)
    return state


def test_initiativ_udloeber_paa_precis_max_attempts(monkeypatch):
    """_MAX_ATTEMPTS forsoeg — ikke ét mere. Off-by-one rettet 20/11-2026."""
    state = _fake_db(monkeypatch)
    for _ in range(iq._MAX_ATTEMPTS):
        iq.mark_attempted("init-x")
    assert state["status"] == "expired", (
        f"skal udloeber efter praecis {iq._MAX_ATTEMPTS} forsoeg, "
        f"ikke {iq._MAX_ATTEMPTS + 1}"
    )


def test_initiativ_er_stadig_pending_under_loftet(monkeypatch):
    """Ét forsoeg mindre end loftet maa ikke udloeber initiativet."""
    state = _fake_db(monkeypatch)
    for _ in range(iq._MAX_ATTEMPTS - 1):
        iq.mark_attempted("init-y")
    assert state["status"] == "pending"


def test_dispatch_baerer_task_id_og_callback(monkeypatch):
    """Runnet skal kunne lukke det initiativ det blev startet for."""
    from core.services import routine_trigger_adapters as rta

    captured: dict = {}

    def fake_start(message, **kw):
        captured["message"] = message
        captured.update(kw)
        return True

    monkeypatch.setattr("core.services.visible_runs.start_autonomous_run", fake_start)
    monkeypatch.setattr(rta, "cutover_allows", lambda *a, **k: False)

    def cb(**kw):
        return None

    rta.dispatch_heartbeat_initiative(
        focus="en fokus", initiative_id="init-z", task_id="task-z",
        completion_callback=cb,
    )
    assert captured.get("task_id") == "task-z"
    assert captured.get("completion_callback") is cb
