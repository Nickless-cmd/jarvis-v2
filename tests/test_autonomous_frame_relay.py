from __future__ import annotations


def test_relay_publishes_and_finishes_authoritative_log(monkeypatch) -> None:
    from core.services import run_event_log
    from core.services.autonomous_frame_relay import AutonomousFrameRelay

    run_event_log._RUNS.clear()
    run_event_log._ALIASER.clear()
    run_event_log._ALIASER_OMVENDT.clear()
    relay = AutonomousFrameRelay("relay-run", "relay-session")

    relay.register()
    relay.publish('event: message_stop\ndata: {"type":"message_stop"}\n\n')
    relay.finish()

    frames, done, next_idx = run_event_log.read_from("relay-run", 0)
    assert frames == ['event: message_stop\ndata: {"type":"message_stop"}\n\n']
    assert done is True
    assert next_idx == 1

