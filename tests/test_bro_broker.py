from __future__ import annotations

T0 = 1_700_000_000


def test_list_active_bros_reads_registry(isolated_runtime, monkeypatch) -> None:
    import core.services.bro_broker as bb

    monkeypatch.setattr(bb, "_active_user_ids", lambda: ["mikkel", "mor"])
    assert set(bb.list_active_bros()) == {"mikkel", "mor"}


def test_switch_without_override_denied(isolated_runtime, monkeypatch) -> None:
    import core.services.bro_broker as bb

    monkeypatch.setattr(bb, "_active_user_ids", lambda: ["mikkel"])
    res = bb.switch("mikkel", requester_session="s1", now=T0)
    assert res["ok"] is False
    assert res["reason"] == "no_active_override"


def test_switch_with_active_override_ok(isolated_runtime, monkeypatch) -> None:
    import core.services.bro_broker as bb
    from core.services.override_store import grant

    monkeypatch.setattr(bb, "_active_user_ids", lambda: ["mikkel"])
    grant("s1", level="help", now=T0)
    res = bb.switch("mikkel", requester_session="s1", now=T0 + 5)
    assert res["ok"] is True
    assert res["target_user"] == "mikkel"
    assert res["level"] == "help"


def test_switch_target_not_connected(isolated_runtime, monkeypatch) -> None:
    import core.services.bro_broker as bb
    from core.services.override_store import grant

    monkeypatch.setattr(bb, "_active_user_ids", lambda: ["mor"])
    grant("s1", now=T0)
    res = bb.switch("mikkel", requester_session="s1", now=T0 + 5)
    assert res["ok"] is False
    assert res["reason"] == "bro_not_found"


def test_switch_emits_eventbus_signal(isolated_runtime, monkeypatch) -> None:
    import core.services.bro_broker as bb
    from core.services.override_store import grant

    published: list[tuple[str, dict]] = []
    monkeypatch.setattr(bb, "_active_user_ids", lambda: ["mikkel"])

    from core.eventbus.bus import event_bus
    monkeypatch.setattr(event_bus, "publish", lambda topic, payload=None: published.append((topic, payload or {})))

    grant("s1", now=T0)
    bb.switch("mikkel", requester_session="s1", now=T0 + 5)
    assert any(t == "bro_broker.switch_requested" for t, _ in published)


# --- §17.3 summary-filtrering (code-mode tool-resultater) ---

def test_summarize_strips_raw_output() -> None:
    from core.services.bro_broker import summarize_tool_result_for_server
    res = {"status": "ok", "path": "/x.py", "content": "hemmelig kildekode" * 50}
    out = summarize_tool_result_for_server("read_file", res)
    assert out["tool_name"] == "read_file"
    assert out["status"] == "ok"
    assert out["path"] == "/x.py"
    assert "content" not in out                       # rå indhold krydser ikke
    held = {h["field"] for h in out["_local_only"]}
    assert "content" in held


def test_summarize_bash_keeps_metadata_not_stdout() -> None:
    from core.services.bro_broker import summarize_tool_result_for_server
    res = {"status": "ok", "exit_code": 0, "stdout": "lange linjer\n" * 100, "stderr": ""}
    out = summarize_tool_result_for_server("operator_bash", res)
    assert out["exit_code"] == 0
    assert "stdout" not in out and "stderr" not in out
    fields = {h["field"] for h in out["_local_only"]}
    assert {"stdout", "stderr"} <= fields


def test_summarize_truncates_error() -> None:
    from core.services.bro_broker import summarize_tool_result_for_server
    out = summarize_tool_result_for_server("x", {"status": "error", "error": "E" * 500})
    assert out["error"].endswith("…") and len(out["error"]) <= 201


def test_summarize_unknown_large_field_held_local() -> None:
    from core.services.bro_broker import summarize_tool_result_for_server
    out = summarize_tool_result_for_server("x", {"weird": "y" * 500, "small": "ok"})
    assert out["small"] == "ok"
    assert "weird" not in out
    assert any(h["field"] == "weird" for h in out["_local_only"])


def test_summarize_non_dict() -> None:
    from core.services.bro_broker import summarize_tool_result_for_server
    out = summarize_tool_result_for_server("x", "rå streng")
    assert out["tool_name"] == "x" and out["_local_only"]
