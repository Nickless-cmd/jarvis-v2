"""C6b: wire-protokollen - rammer, graenser, misdannede data."""
from __future__ import annotations

import socket

import pytest

from core.services import agent_worker_protocol as proto


@pytest.fixture
def pair():
    a, b = socket.socketpair()
    yield a, b
    a.close()
    b.close()


def test_roundtrip_and_several_frames_in_one_chunk(pair):
    a, b = pair
    proto.send(a, {"op": "x", "n": 1, "tekst": "æøå"})
    proto.send(a, {"op": "y"})
    r = proto.FrameReader(b)
    assert r.read(1) == {"op": "x", "n": 1, "tekst": "æøå"}
    assert r.read(1) == {"op": "y"}
    assert r.read(0.05) is None                      # timeout giver None, ikke en fejl


def test_a_frame_split_across_reads_is_reassembled(pair):
    a, b = pair
    raw = b'{"op": "delt", "v": "' + b"x" * 5000 + b'"}\n'
    r = proto.FrameReader(b)
    a.sendall(raw[:100])
    assert r.read(0.05) is None
    a.sendall(raw[100:])
    assert r.read(1)["op"] == "delt"


def test_eof_is_reported(pair):
    a, b = pair
    a.close()
    with pytest.raises(EOFError):
        proto.FrameReader(b).read(1)


@pytest.mark.parametrize("payload", [b"ikke json\n", b"[1,2]\n", b"\xff\xfe\n", b'"streng"\n'])
def test_malformed_frames_are_protocol_errors(pair, payload):
    a, b = pair
    a.sendall(payload)
    with pytest.raises(proto.ProtocolError):
        proto.FrameReader(b).read(1)


def test_oversized_frames_are_refused_in_both_directions(pair, monkeypatch):
    a, b = pair
    monkeypatch.setattr(proto, "MAX_FRAME", 1000)
    with pytest.raises(proto.FrameTooLarge):
        proto.send(a, {"op": "x", "d": "y" * 2000})
    a.sendall(b"z" * 3000)                            # ingen linjeskift: modtageren stopper selv
    with pytest.raises(proto.FrameTooLarge):
        proto.FrameReader(b).read(1)
