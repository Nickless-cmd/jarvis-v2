from types import SimpleNamespace

from core.services import in_flight_runs as ifr
from core.services.visible_run_journal import mark_visible_run_started


def test_visible_run_gemmer_composer_kontekst_til_genoptagelse(monkeypatch):
    records = {}
    monkeypatch.setattr(ifr, "_load", lambda: dict(records))
    monkeypatch.setattr(ifr, "_save", lambda value: (records.clear(), records.update(value)))
    run = SimpleNamespace(
        run_id="visible-context", session_id="chat-1", user_message="ret koden",
        autonomous=False, provider="deepseek", model="model", trust_all=True,
        thinking_mode="deep", surface="desk", user_id="owner-1",
        local_tool_exec=True,
    )
    mark_visible_run_started(run, tool_scope="code")
    saved = ifr.get_record(run.run_id)
    assert saved is not None
    assert {key: saved[key] for key in (
        "approval_mode", "thinking_mode", "tool_scope", "surface",
        "force_user_id", "local_tool_exec",
    )} == {
        "approval_mode": "trust", "thinking_mode": "deep", "tool_scope": "code",
        "surface": "desk", "force_user_id": "owner-1", "local_tool_exec": True,
    }
