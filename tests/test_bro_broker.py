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
