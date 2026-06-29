"""I2 — garanteret terminal-frame (H1/G6/F11).

Verificerer at en stream ALDRIG ender uden en terminal-frame til klienten:
- F11: en terminal message_stop-frame der ankommer EFTER relay-frame-cap'en bliver
  ALLIGEVEL gemt (ikke droppet) → re-subscribere ser stadig 'done'.
- F11: truncation-nerven (cluster='stream', nerve='relay_frame_cap') fyrer ÉN gang
  pr. run, før første over-cap ikke-terminale frame droppes.
- F11: ephemeral ping/retry-frames persisteres ikke (æder ikke cap-budget).
- H1/G6: synthetic_terminal_frame() returnerer en ægte message_stop + fyrer den
  (ellers døde) subscriber_timeout-nerve.
- H1/G6: en subscriber-generator der rammer give-up-betingelsen yielder en
  message_stop som sin SIDSTE frame.
"""
import asyncio
import json

import core.services.run_event_log as rel


def setup_function():
    rel._RUNS.clear()


# ---------------------------------------------------------------- F11: cap + terminal

def test_terminal_frame_stored_even_over_cap(monkeypatch):
    captured = []
    monkeypatch.setattr(rel, "_emit_cap_nerve", lambda rid: captured.append(rid))

    rel.create("r1", "s1")
    # Fyld bufferen helt op til cap'en med ikke-terminale frames.
    for i in range(rel._MAX_FRAMES):
        rel.append("r1", f"event: x\ndata: {i}\n\n")
    assert len(rel._RUNS["r1"]["frames"]) == rel._MAX_FRAMES

    # En ikke-terminal frame OVER cap'en droppes (og trigger nerven).
    rel.append("r1", "event: x\ndata: over\n\n")
    assert len(rel._RUNS["r1"]["frames"]) == rel._MAX_FRAMES
    assert captured == ["r1"]  # nerve fyrede én gang

    # Terminal-frame OVER cap'en gemmes ALLIGEVEL.
    term = rel.SYNTHETIC_MESSAGE_STOP
    rel.append("r1", term)
    assert rel._RUNS["r1"]["frames"][-1] == term
    assert len(rel._RUNS["r1"]["frames"]) == rel._MAX_FRAMES + 1

    # En re-subscriber der læser hele bufferen ser terminal-frame'en.
    frames, _done = rel.read("r1", 0)
    assert any(rel._is_terminal_frame(f) for f in frames)


def test_cap_nerve_fires_once_per_run(monkeypatch):
    calls = []

    def fake_central():
        class _C:
            def observe(self, payload):
                calls.append(payload)
        return _C()

    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", fake_central)

    rel.create("r1", "s1")
    for i in range(rel._MAX_FRAMES):
        rel.append("r1", f"event: x\ndata: {i}\n\n")
    # Flere over-cap ikke-terminale frames → nerve KUN én gang.
    rel.append("r1", "event: x\ndata: a\n\n")
    rel.append("r1", "event: x\ndata: b\n\n")
    rel.append("r1", "event: x\ndata: c\n\n")

    cap_nerves = [c for c in calls if c.get("nerve") == "relay_frame_cap"]
    assert len(cap_nerves) == 1
    assert cap_nerves[0]["cluster"] == "stream"
    assert cap_nerves[0]["run_id"] == "r1"


def test_ephemeral_frames_not_persisted():
    rel.create("r1", "s1")
    rel.append("r1", 'event: ping\ndata: {"type": "ping"}\n\n')
    rel.append("r1", "retry: 1000\n\n")
    # Liveness opdateret, men intet persisteret.
    frames, _ = rel.read("r1", 0)
    assert frames == []

    rel.append("r1", "event: content_block_delta\ndata: {}\n\n")
    frames, _ = rel.read("r1", 0)
    assert len(frames) == 1


# ---------------------------------------------------------------- H1/G6: synthetic terminal

def test_synthetic_terminal_frame_shape_and_nerve(monkeypatch):
    notes = []
    import core.services.stream_sentinel as ss
    monkeypatch.setattr(
        ss, "note_event",
        lambda run_id, kind, session_id="", **d: notes.append((run_id, kind, session_id, d)),
    )

    frame = rel.synthetic_terminal_frame("r1", "s1", reason="relay_subscriber_idle")
    # Eksakt message_stop-form (klienterne forlader kun 'working' her).
    assert frame.startswith("event: message_stop\n")
    assert json.loads(frame.split("data: ", 1)[1].strip()) == {"type": "message_stop"}
    assert rel._is_terminal_frame(frame)

    # subscriber_timeout-nerven fyrede.
    assert notes and notes[0][1] == "subscriber_timeout"
    assert notes[0][0] == "r1" and notes[0][2] == "s1"
    assert notes[0][3]["reason"] == "relay_subscriber_idle"


def test_synthetic_terminal_is_self_safe(monkeypatch):
    import core.services.stream_sentinel as ss

    def _boom(*a, **k):
        raise RuntimeError("nerve eksploderede")

    monkeypatch.setattr(ss, "note_event", _boom)
    # Må ALDRIG kaste — returnerer stadig en gyldig terminal-frame.
    frame = rel.synthetic_terminal_frame("r1", "s1")
    assert rel._is_terminal_frame(frame)


def test_subscriber_generator_emits_terminal_on_giveup(monkeypatch):
    """Driv en subscriber-generator i samme form som chat_stream_v2._subscribe:
    den rammer give-up-betingelsen og SKAL yielde message_stop som sidste frame +
    fyre subscriber_timeout."""
    notes = []
    import core.services.stream_sentinel as ss
    monkeypatch.setattr(
        ss, "note_event",
        lambda run_id, kind, session_id="", **d: notes.append((run_id, kind)),
    )

    rel.create("r1", "s1")  # aldrig 'done', aldrig nye frames → tvinger give-up

    async def _subscribe(run_id, session_id, max_empty=3):
        rel.subscriber_opened(run_id)
        try:
            idx = 0
            empty = 0
            while True:
                frames, done = rel.read(run_id, idx)
                for f in frames:
                    idx += 1
                    yield f
                if done:
                    rel.mark_consumed(run_id)
                    break
                if frames:
                    empty = 0
                else:
                    empty += 1
                    if empty > max_empty:
                        yield rel.synthetic_terminal_frame(
                            run_id, session_id, reason="relay_subscriber_idle"
                        )
                        break
                await asyncio.sleep(0)
        finally:
            rel.subscriber_closed(run_id)

    async def _drain():
        out = []
        async for f in _subscribe("r1", "s1"):
            out.append(f)
        return out

    out = asyncio.run(_drain())
    assert out, "generatoren skal yielde mindst terminal-frame'en"
    assert rel._is_terminal_frame(out[-1])  # SIDSTE frame er message_stop
    assert any(k == "subscriber_timeout" for _r, k in notes)
    # subscriber-tælleren ryddet af finally.
    assert rel._RUNS["r1"]["subscribers"] == 0
