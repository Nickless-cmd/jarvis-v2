from contextlib import contextmanager

from core.services import background_start_reservation as reservation


def test_active_run_blocks_reservation(monkeypatch, tmp_path):
    monkeypatch.setattr(
        reservation.state_store, "_path", lambda _key: tmp_path / "state.json",
    )
    monkeypatch.setattr(reservation, "_active_reason", lambda _sid: "shared-active:run-1")

    with reservation.reserve_background_start("chat-1") as claim:
        assert claim.acquired is False
        assert claim.reason == "shared-active:run-1"


def test_sensor_failure_is_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(
        reservation.state_store, "_path", lambda _key: tmp_path / "state.json",
    )
    monkeypatch.setattr(
        reservation, "_active_reason",
        lambda _sid: (_ for _ in ()).throw(OSError("journal unavailable")),
    )

    with reservation.reserve_background_start("chat-1") as claim:
        assert claim.acquired is False
        assert claim.reason == "active-state-unavailable"


def test_concurrent_starter_cannot_enter_same_check_start_window(monkeypatch, tmp_path):
    monkeypatch.setattr(
        reservation.state_store, "_path", lambda _key: tmp_path / "state.json",
    )
    monkeypatch.setattr(reservation, "_active_reason", lambda _sid: "")

    with reservation.reserve_background_start("chat-1") as first:
        assert first.acquired is True
        with reservation.reserve_background_start("chat-1") as second:
            assert second.acquired is False
            assert second.reason == "start-reserved"


def test_inbox_start_holds_reservation_through_registration(monkeypatch):
    from core.services import inbox_idle_waker

    events = []

    @contextmanager
    def _reserve(session_id):
        events.append(("reserve", session_id))
        yield reservation.StartReservation(True)
        events.append(("release", session_id))

    monkeypatch.setattr(reservation, "reserve_background_start", _reserve)
    monkeypatch.setattr(
        "core.services.visible_autonomous_run.start_autonomous_run",
        lambda *_args, **_kwargs: events.append(("start", "chat-1")) or True,
    )

    assert inbox_idle_waker._start_run("do it", session_id="chat-1") is True
    assert events == [
        ("reserve", "chat-1"), ("start", "chat-1"), ("release", "chat-1"),
    ]
