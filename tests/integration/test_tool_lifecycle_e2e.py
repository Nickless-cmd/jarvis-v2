from core.services.chat_sessions import (
    create_chat_session, append_chat_message,
    chat_session_messages_since_last_compact,
)
from core.context import tool_result_lifecycle as trl
from core.services.tool_result_store import get_tool_result, parse_tool_result_reference


class _S:
    tool_result_lifecycle_enabled = True
    tool_warm_run_window = 2          # small so the test triggers easily
    tool_warm_token_ceiling = 10**9
    tool_warm_hysteresis = 0.0


def test_e2e_old_tool_becomes_cold_and_rehydratable():
    sess = create_chat_session(title="t")
    sid = str(sess["id"])
    for i in range(5):
        append_chat_message(session_id=sid, role="user", content=f"opgave {i}")
        append_chat_message(session_id=sid, role="assistant", content="kører")
        append_chat_message(
            session_id=sid, role="tool",
            content=f"kommando-output nr {i} " * 20, tool_name="bash",
        )

    new_floor = trl.evaluate_and_advance(sid, settings=_S())
    assert new_floor > 0

    msgs = chat_session_messages_since_last_compact(sid)
    cold = [m for m in msgs if m["role"] == "tool" and m["id"] < new_floor]
    assert cold, "at least one tool-result must be below the floor (cold)"

    ref = parse_tool_result_reference(cold[0]["content"])
    assert ref is not None
    assert get_tool_result(ref["result_id"]) is not None  # full output rehydratable
