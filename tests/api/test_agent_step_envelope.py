from fastapi.testclient import TestClient
from apps.api.jarvis_api.app import app
import apps.api.jarvis_api.routes.agent_loop as al

client = TestClient(app)


def test_flag_defaults_off():
    # Unknown flag key must read False (fail-safe: new behavior inert until enabled).
    assert al._flag("jc_agent_totally_unknown_flag_xyz") is False


def test_flag_reads_runtime_state(monkeypatch):
    monkeypatch.setattr(al, "get_runtime_state_value",
                        lambda key, default=None: True if key == "jc_agent_observability" else default)
    assert al._flag("jc_agent_observability") is True
    assert al._flag("jc_agent_user_scoping") is False


def test_seam_names_exist_for_monkeypatch():
    # Observability seams must be module-level names so tests can patch them.
    assert callable(al.record_cost)
    assert callable(al.note_empty_completion)
