"""Fase A1: agent_step dynamic-tail cache-split — flyt volatil hale bag samtalen."""
from apps.api.jarvis_api.routes.agent_loop import _apply_dynamic_tail_split
from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL as S


def test_split_moves_tail_to_last_user_when_enabled():
    msgs = [
        {"role": "system", "content": f"STABLE HEAD{S}VOLATILE TAIL"},
        {"role": "user", "content": "hej"},
        {"role": "assistant", "content": "hi"},
        {"role": "user", "content": "hvad nu"},
    ]
    out = _apply_dynamic_tail_split(msgs, enabled=True)
    assert out[0]["content"] == "STABLE HEAD"
    assert out[-1]["content"].startswith("hvad nu")
    assert "VOLATILE TAIL" in out[-1]["content"]
    assert S not in out[0]["content"]
    # tidligere user-besked urørt
    assert out[1]["content"] == "hej"


def test_off_is_byte_identical():
    msgs = [
        {"role": "system", "content": f"HEAD{S}TAIL"},
        {"role": "user", "content": "u"},
    ]
    out = _apply_dynamic_tail_split(msgs, enabled=False)
    assert out == msgs


def test_no_sentinel_is_byte_identical():
    msgs = [
        {"role": "system", "content": "no sentinel here"},
        {"role": "user", "content": "u"},
    ]
    out = _apply_dynamic_tail_split(msgs, enabled=True)
    assert out == msgs


def test_no_user_message_keeps_tail_in_system():
    msgs = [{"role": "system", "content": f"HEAD{S}TAIL"}]
    out = _apply_dynamic_tail_split(msgs, enabled=True)
    assert out[0]["content"] == "HEADTAIL"
    assert S not in out[0]["content"]


def test_empty_messages_safe():
    assert _apply_dynamic_tail_split([], enabled=True) == []


def test_settings_has_cache_split_flag_default_false():
    from core.runtime.settings import load_settings
    s = load_settings()
    assert hasattr(s, "agent_step_cache_split_enabled")
    assert s.agent_step_cache_split_enabled is False
