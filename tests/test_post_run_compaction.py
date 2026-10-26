from __future__ import annotations


def _event(*, source: str = "visible-run", role: str = "assistant", sid: str = "s1") -> dict:
    return {
        "kind": "channel.chat_message_appended",
        "payload": {
            "source": source,
            "session_id": sid,
            "message": {"role": role},
        },
    }


def test_only_completed_visible_assistant_message_selects_session():
    from core.services.post_run_compaction import _completed_visible_session

    assert _completed_visible_session(_event()) == "s1"
    assert _completed_visible_session(_event(source="session-inbox:x")) == ""
    assert _completed_visible_session(_event(role="user")) == ""
    assert _completed_visible_session({"kind": "runtime.visible_run_completed", "payload": {}}) == ""


def test_completed_turn_reuses_prompt_surface_and_existing_policy(monkeypatch):
    from core.services import post_run_compaction as prc
    from core.services import prompt_contract as pc

    built: list[tuple] = []
    decided: list[tuple] = []
    pc._compact_inflight.discard("s1")

    def _build(*args, **kwargs):
        built.append((args, kwargs))
        return [{"role": "user", "content": "x" * 100}]

    def _decide(sid, messages, settings):
        decided.append((sid, messages, settings))
        pc._compact_inflight.add(sid)

    monkeypatch.setattr(pc, "_build_structured_transcript_messages", _build)
    monkeypatch.setattr(pc, "_maybe_auto_compact_session", _decide)
    monkeypatch.setattr("core.runtime.settings.load_settings", lambda: object())
    try:
        assert prc.compact_after_completed_turn("s1") is True
        assert built == [(('s1',), {"limit": 60, "include": True, "bivirkninger": False})]
        assert decided[0][0] == "s1"
    finally:
        pc._compact_inflight.discard("s1")


def test_empty_prompt_surface_does_not_start_compaction(monkeypatch):
    from core.services import post_run_compaction as prc
    from core.services import prompt_contract as pc

    monkeypatch.setattr(pc, "_build_structured_transcript_messages", lambda *a, **k: [])
    called: list[str] = []
    monkeypatch.setattr(pc, "_maybe_auto_compact_session", lambda *a, **k: called.append("called"))

    assert prc.compact_after_completed_turn("s1") is False
    assert called == []
