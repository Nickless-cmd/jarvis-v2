"""C2b: cross-device live-broadcast for en klient-drevet tur (turn-begin/turn-end)."""
import asyncio
from types import SimpleNamespace

from core.services import client_turn_live as ctl


def test_begin_registers_active_run_and_follow(monkeypatch):
    saved = {}
    monkeypatch.setattr(
        "core.services.visible_runs_sections.run_control_state._set_active_visible_run",
        lambda payload: saved.update({"active": payload}))
    follows = []
    monkeypatch.setattr("core.services.run_follow.begin_follow",
                        lambda sid, rid="": follows.append((sid, rid)))
    ctl.begin_live_turn(session_id="chat-abc", run_id="r1", user_message="hej",
                        provider="ollama", model="deepseek", user_id="u")
    a = saved["active"]
    assert a["active"] is True and a["run_id"] == "r1"
    assert a["session_id"] == "chat-abc" and a["origin"] == "jarvis-code"
    assert a["current_user_message_preview"] == "hej"
    assert follows == [("chat-abc", "r1")]


def test_begin_local_session_skips_follow(monkeypatch):
    monkeypatch.setattr(
        "core.services.visible_runs_sections.run_control_state._set_active_visible_run",
        lambda payload: None)
    follows = []
    monkeypatch.setattr("core.services.run_follow.begin_follow",
                        lambda sid, rid="": follows.append(sid))
    ctl.begin_live_turn(session_id="uuid-local", run_id="r1")
    assert follows == []  # kun chat-<hex> åbner run_follow


def test_end_clears_only_matching_run(monkeypatch):
    cleared = []
    monkeypatch.setattr(
        "core.services.visible_runs_sections.run_control_state._get_active_visible_run_state",
        lambda: {"run_id": "OTHER"})
    monkeypatch.setattr(
        "core.services.visible_runs_sections.run_control_state._set_active_visible_run",
        lambda payload: cleared.append(payload))
    monkeypatch.setattr("core.services.run_follow.end_follow", lambda sid: None)
    ctl.end_live_turn(session_id="chat-abc", run_id="r1")
    assert cleared == []  # et andet run er aktivt → rør ikke


def test_end_clears_own_run(monkeypatch):
    cleared = []
    monkeypatch.setattr(
        "core.services.visible_runs_sections.run_control_state._get_active_visible_run_state",
        lambda: {"run_id": "r1"})
    monkeypatch.setattr(
        "core.services.visible_runs_sections.run_control_state._set_active_visible_run",
        lambda payload: cleared.append(payload))
    ends = []
    monkeypatch.setattr("core.services.run_follow.end_follow", lambda sid: ends.append(sid))
    ctl.end_live_turn(session_id="chat-abc", run_id="r1")
    assert cleared == [{"active": False}]
    assert ends == ["chat-abc"]


# ── endpoint flag-gating ────────────────────────────────────────────────────


def test_turn_begin_flag_off_is_noop():
    from apps.api.jarvis_api.routes import agent_loop as al
    body = al._TurnLiveBody(session_id="chat-x", run_id="r")
    r = asyncio.run(al.agent_turn_begin(body))
    assert r["ok"] is False and r["skipped"] == "flag_off"


def test_turn_begin_flag_on_dispatches(monkeypatch):
    from apps.api.jarvis_api.routes import agent_loop as al
    monkeypatch.setattr(al, "_settings",
                        lambda: SimpleNamespace(agent_live_broadcast_enabled=True))
    monkeypatch.setattr(al, "_resolve_role", lambda: "owner")
    seen = {}
    monkeypatch.setattr("core.services.client_turn_live.begin_live_turn",
                        lambda **kw: seen.update(kw))
    body = al._TurnLiveBody(session_id="chat-x", run_id="r7", user_message="u",
                            provider="ollama", model="deepseek")
    r = asyncio.run(al.agent_turn_begin(body))
    assert r["ok"] is True and r["run_id"] == "r7"
    assert seen["run_id"] == "r7" and seen["session_id"] == "chat-x"


def test_turn_end_flag_on_dispatches(monkeypatch):
    from apps.api.jarvis_api.routes import agent_loop as al
    monkeypatch.setattr(al, "_settings",
                        lambda: SimpleNamespace(agent_live_broadcast_enabled=True))
    seen = {}
    monkeypatch.setattr("core.services.client_turn_live.end_live_turn",
                        lambda **kw: seen.update(kw))
    body = al._TurnLiveBody(session_id="chat-x", run_id="r7")
    r = asyncio.run(al.agent_turn_end(body))
    assert r["ok"] is True and seen["run_id"] == "r7"


def test_settings_flag_default_false():
    from core.runtime.settings import load_settings
    assert load_settings().agent_live_broadcast_enabled is False


# ── Lag 3: token-follow (jc deltas → v2-frames) ──────────────────────────────


def test_live_follow_active_gate():
    from apps.api.jarvis_api.routes import agent_loop as al
    on = SimpleNamespace(agent_live_follow_tokens_enabled=True)
    off = SimpleNamespace(agent_live_follow_tokens_enabled=False)
    assert al._live_follow_active(on, "chat-abc") is True
    assert al._live_follow_active(on, "local-uuid") is False   # kun chat-<hex>
    assert al._live_follow_active(off, "chat-abc") is False    # flag off


def test_follow_begin_delta_end_publish_v2_frames(monkeypatch):
    from apps.api.jarvis_api.routes import agent_loop as al
    frames = []
    monkeypatch.setattr("core.services.run_follow.publish_follow_frame",
                        lambda sid, line: frames.append((sid, line)))
    al._follow_begin_frames("chat-x", "r1", "ollama", "deepseek")
    al._follow_delta_frame("chat-x", "Hej ")
    al._follow_delta_frame("chat-x", "Bjørn")
    al._follow_end_frames("chat-x")
    joined = "\n".join(l for _, l in frames)
    assert "message_start" in joined and "content_block_start" in joined
    assert "Hej " in joined and "Bjørn" in joined
    assert "content_block_stop" in joined and "message_stop" in joined
    # rækkefølge: start → deltas → stop
    order = [l.split("event: ")[1].split("\n")[0] if "event: " in l else "" for _, l in frames]
    assert order[0] == "message_start"
    assert order[-1] == "message_stop"


def test_turn_begin_publishes_follow_when_flag_on(monkeypatch):
    from apps.api.jarvis_api.routes import agent_loop as al
    import asyncio
    monkeypatch.setattr(al, "_settings", lambda: SimpleNamespace(
        agent_live_broadcast_enabled=True, agent_live_follow_tokens_enabled=True))
    monkeypatch.setattr(al, "_resolve_role", lambda: "owner")
    monkeypatch.setattr("core.services.client_turn_live.begin_live_turn", lambda **kw: None)
    frames = []
    monkeypatch.setattr("core.services.run_follow.publish_follow_frame",
                        lambda sid, line: frames.append(line))
    body = al._TurnLiveBody(session_id="chat-x", run_id="r1", provider="ollama", model="deepseek")
    asyncio.run(al.agent_turn_begin(body))
    assert any("message_start" in f for f in frames)


def test_settings_follow_flag_default_false():
    from core.runtime.settings import load_settings
    assert load_settings().agent_live_follow_tokens_enabled is False
