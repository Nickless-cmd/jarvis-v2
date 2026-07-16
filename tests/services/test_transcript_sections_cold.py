import core.services.prompt_sections.transcript_sections as ts
from core.services.tool_result_store import build_tool_result_reference


# Unique to the STUB form. The WARM render emits
#   '... Use read_tool_result with result_id="..." to inspect the full output.'
# so bare "read_tool_result" appears in BOTH forms. The stub's exact
# '(read_tool_result)]' suffix appears ONLY in the cold-stub form, so it is the
# correct warm-vs-cold discriminator.
STUB_MARK = "(read_tool_result)]"


def _ref(i):
    return build_tool_result_reference(
        f"tool-result-{i}", tool_name="bash", summary=f"output {i} " * 10)


def _hist():
    # 3 user-turns, each with one tool-result. ids ascending.
    return [
        {"id": 1, "role": "user", "content": "gør A"},
        {"id": 2, "role": "assistant", "content": "kører"},
        {"id": 3, "role": "tool", "content": _ref(3)},
        {"id": 4, "role": "user", "content": "gør B"},
        {"id": 5, "role": "assistant", "content": "kører"},
        {"id": 6, "role": "tool", "content": _ref(6)},
        {"id": 7, "role": "user", "content": "gør C"},
        {"id": 8, "role": "assistant", "content": "kører"},
        {"id": 9, "role": "tool", "content": _ref(9)},
    ]


def _patch(monkeypatch, hist, floor, enabled=True):
    monkeypatch.setattr(ts, "chat_session_messages_since_last_compact",
                        lambda sid, **k: list(hist))
    monkeypatch.setattr(ts, "_lifecycle_enabled", lambda: enabled)
    monkeypatch.setattr(ts, "_cold_floor_for", lambda sid: floor)


def test_cold_floor_stubs_old_tools(monkeypatch):
    _patch(monkeypatch, _hist(), floor=4)  # id<4 => cold (only id 3)
    out = ts._build_structured_transcript_messages("s1", limit=60, include=True)
    blob = "\n".join(m["content"] for m in out)
    assert "tool-result-3" in blob       # cold stub keeps the id
    assert STUB_MARK in blob             # stub marker present for id 3
    # ids 6 and 9 are warm (id>4): their reference id strings must NOT appear as
    # stub markers. Warm render does not emit the '(read_tool_result)]' suffix.
    assert blob.count(STUB_MARK) == 1  # only the one cold tool


def test_byte_stability_between_turns_when_floor_fixed(monkeypatch):
    # CORE INVARIANT: cold_floor unchanged => shared history bytes identical when
    # a new turn is appended. This is the 2026-06-09 regression, guarded.
    _patch(monkeypatch, _hist(), floor=4)
    out1 = ts._build_structured_transcript_messages("s1", limit=60, include=True)
    blob1 = "\n".join(m["content"] for m in out1)

    _patch(monkeypatch, _hist() + [{"id": 10, "role": "user", "content": "gør D"}],
           floor=4)
    out2 = ts._build_structured_transcript_messages("s1", limit=60, include=True)
    blob2 = "\n".join(m["content"] for m in out2)

    assert blob1 in blob2  # every shared-history byte is preserved as a prefix


def test_flag_off_is_unchanged(monkeypatch):
    _patch(monkeypatch, _hist(), floor=4, enabled=False)
    out = ts._build_structured_transcript_messages("s1", limit=60, include=True)
    blob = "\n".join(m["content"] for m in out)
    assert STUB_MARK not in blob  # no stubs when flag off
