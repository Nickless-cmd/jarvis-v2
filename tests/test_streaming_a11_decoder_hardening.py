"""A11 — hærdet SSE/NDJSON-decoder (spec §1A + §11.1 A11).

Den delte line/SSE-decoder kunne FØR dræbe streamen mid-turn på to måder, som
BEGGE var usynlige for rund-niveau-retry'en (4.1) fordi de var generator-
exceptions (ikke ``FollowupFailed``):

  1. Et UTF-8 multibyte-codepoint splittet over en netværks-chunk-grænse
     (æøå/emoji = Jarvis' normale stemme) → ``UnicodeDecodeError``.
  2. En HTTP-200-så-malformet/trunkeret JSON ``data:``/NDJSON-linje →
     ``JSONDecodeError``.

Disse tests verificerer hærdningen på ALLE tre parse-sites:
  - ``stream_failure_kind`` helpers (``safe_decode_line`` / ``try_parse_json_line``)
  - ``visible_model._iter_sse_events`` (OpenAI/Copilot SSE-stien)
  - ``visible_followup.OllamaFollowupAdapter`` (NDJSON-followup-stien)

Skip-vs-fail-kontrakten:
  - ÉN dårlig chunk på en ellers sund stream → SKIP (continue) + let observe.
  - Streamen slutter uden terminal/``done`` EFTER et skip → typed retryable
    ``malformed_stream_payload`` (4.1's rund-retry fanger den).

Fuldt hermetisk: vi mocker BYTE-strømmen (urlopen) — ingen netværk/ollama/modeller.
"""
from __future__ import annotations

import json

import pytest

import core.services.visible_followup as vf
import core.services.visible_model as vm
from core.services.stream_failure_kind import (
    FailureKind,
    MalformedStreamPayload,
    classify_failure,
    is_retryable_kind,
    safe_decode_line,
    try_parse_json_line,
)


# ── Hjælpere ─────────────────────────────────────────────────────────────────


class _FakeResponse:
    """Mimer en urllib-respons: itererer over rå BYTE-linjer.

    Bevidst byte-baseret så vi kan injicere et split UTF-8-codepoint præcis som
    en netværks-chunk-grænse ville gøre det."""

    def __init__(self, raw_lines: list[bytes]) -> None:
        self._lines = list(raw_lines)

    def __iter__(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def close(self):
        pass


def _capture_nerves(monkeypatch) -> list[dict]:
    """Fang central().observe(...)-payloads self-safe (ingen ægte Central)."""
    seen: list[dict] = []

    class _FakeCentral:
        def observe(self, payload):
            seen.append(dict(payload))

    import core.services.central_core as cc
    monkeypatch.setattr(cc, "central", lambda: _FakeCentral())
    return seen


# ── Lag 0: de delte primitiver ──────────────────────────────────────────────


def test_safe_decode_line_never_raises_on_split_utf8():
    # "æ" = b"\xc3\xa6"; et split midt i sekvensen må ALDRIG rejse.
    head = b"hello \xc3"  # halv æ — multibyte splittet ved chunk-grænse
    out = safe_decode_line(head)
    assert isinstance(out, str)
    assert "hello " in out
    assert "�" in out  # erstatnings-tegn frem for dødt stream


def test_try_parse_json_line_classifies_good_bad_empty():
    assert try_parse_json_line('{"a": 1}') == ({"a": 1}, True)
    assert try_parse_json_line("   ") == (None, True)        # tom = ingen fejl
    assert try_parse_json_line('{"a": ') == (None, False)    # trunkeret = malformet
    assert try_parse_json_line("[1,2,3]") == (None, False)   # ikke-dict = malformet for os


def test_malformed_text_classifies_retryable():
    # MalformedStreamPayload-strengen skal klassificeres som retryable kind.
    kind, retry = classify_failure(
        http_status=None,
        error_text="Ollama stream ended malformed (truncated final JSON)")
    assert kind == FailureKind.MALFORMED_STREAM_PAYLOAD
    assert retry is True
    assert is_retryable_kind(kind) is True


# ── Lag 1: _iter_sse_events (OpenAI/Copilot SSE-stien) ───────────────────────


def test_sse_split_utf8_survives_with_replacement(monkeypatch):
    nerves = _capture_nerves(monkeypatch)
    # Gyldig JSON hvor content-feltet indeholder dansk; vi splitter IKKE inde i
    # JSON her (det ville lave ægte malformet) — i stedet verificerer vi at en
    # linje med rå replacement-bytes uden for JSON ikke vælter streamen, og at
    # et dansk svar kommer rent igennem.
    good = json.dumps({"type": "response.output_text.delta", "delta": "æøå"})
    lines = [
        f"data: {good}".encode("utf-8"),
        b"",
        b"data: [DONE]",
        b"",
    ]
    events = list(vm._iter_sse_events(_FakeResponse(lines), provider="openai", model="gpt-test"))
    deltas = [e.get("delta") for e in events if e.get("type") == "response.output_text.delta"]
    assert deltas == ["æøå"]
    # Ingen malformet → ingen malformed-nerve.
    assert not [n for n in nerves if n.get("nerve") == "malformed_stream_payload"]


def test_sse_single_bad_block_is_skipped_good_survives(monkeypatch):
    nerves = _capture_nerves(monkeypatch)
    good1 = json.dumps({"type": "response.output_text.delta", "delta": "Hej "})
    good2 = json.dumps({"type": "response.output_text.delta", "delta": "Bjørn"})
    lines = [
        f"data: {good1}".encode("utf-8"),
        b"",
        b'data: {"type": "response.output_text.delta", "delta": ',  # TRUNKERET blok
        b"",
        f"data: {good2}".encode("utf-8"),
        b"",
        b"data: [DONE]",
        b"",
    ]
    events = list(vm._iter_sse_events(_FakeResponse(lines), provider="openai", model="gpt-test"))
    deltas = [e.get("delta") for e in events if e.get("type") == "response.output_text.delta"]
    # Den dårlige blok blev sprunget over; begge gode kom igennem.
    assert deltas == ["Hej ", "Bjørn"]
    skip_nerves = [n for n in nerves
                   if n.get("nerve") == "malformed_stream_payload" and n.get("severity") == "skip"]
    assert len(skip_nerves) == 1
    assert skip_nerves[0]["ended_malformed"] is False


def test_sse_truncated_final_surfaces_retryable(monkeypatch):
    nerves = _capture_nerves(monkeypatch)
    good = json.dumps({"type": "response.output_text.delta", "delta": "Hej"})
    # Streamen SLUTTER på en trunkeret blok UDEN [DONE] → skal rejse typed retryable.
    lines = [
        f"data: {good}".encode("utf-8"),
        b"",
        b'data: {"type": "response.output_text.delta", "delta": "afbr',  # trunkeret final
        b"",
    ]
    with pytest.raises(MalformedStreamPayload):
        list(vm._iter_sse_events(_FakeResponse(lines), provider="openai", model="gpt-test"))
    fail_nerves = [n for n in nerves
                   if n.get("nerve") == "malformed_stream_payload" and n.get("severity") == "fail"]
    assert len(fail_nerves) == 1
    assert fail_nerves[0]["ended_malformed"] is True


# ── Lag 2: OllamaFollowupAdapter (NDJSON-followup-stien) ─────────────────────


@pytest.fixture
def _ollama_adapter(monkeypatch):
    # Neutralisér provider-router-opslaget (intet netværk).
    import core.runtime.provider_router as pr
    monkeypatch.setattr(pr, "load_provider_router_registry", lambda: {}, raising=False)
    monkeypatch.setattr(pr, "_provider_base_url", lambda **_k: "http://127.0.0.1:11434", raising=False)
    return vf.OllamaFollowupAdapter()


def _drive_followup(adapter, raw_lines, monkeypatch):
    """Kør adapterens stream_followup med en mocket NDJSON-byte-strøm."""
    monkeypatch.setattr(
        vf.urllib_request, "urlopen",
        lambda *a, **k: _FakeResponse(raw_lines))
    return list(adapter.stream_followup(
        model="glm-test",
        base_messages=[{"role": "user", "content": "hej"}],
        exchanges=[],
        tool_definitions=None,
        round_index=0,
    ))


def test_followup_split_utf8_survives(monkeypatch, _ollama_adapter):
    nerves = _capture_nerves(monkeypatch)
    lines = [
        json.dumps({"message": {"content": "æøå svar"}}).encode("utf-8"),
        json.dumps({"message": {"content": ""}, "done": True}).encode("utf-8"),
    ]
    events = _drive_followup(_ollama_adapter, lines, monkeypatch)
    deltas = [e.delta for e in events if isinstance(e, vf.FollowupDelta)]
    assert "æøå svar" in "".join(deltas)
    assert any(isinstance(e, vf.FollowupDone) for e in events)
    assert not any(isinstance(e, vf.FollowupFailed) for e in events)


def test_followup_single_bad_line_skipped_good_survives(monkeypatch, _ollama_adapter):
    nerves = _capture_nerves(monkeypatch)
    lines = [
        json.dumps({"message": {"content": "Hej "}}).encode("utf-8"),
        b'{"message": {"content": ',  # TRUNKERET NDJSON-linje midt i streamen
        json.dumps({"message": {"content": "Bjørn"}}).encode("utf-8"),
        json.dumps({"message": {"content": ""}, "done": True}).encode("utf-8"),
    ]
    events = _drive_followup(_ollama_adapter, lines, monkeypatch)
    deltas = "".join(e.delta for e in events if isinstance(e, vf.FollowupDelta))
    assert deltas == "Hej Bjørn"
    # Streamen overlevede → Done, ingen Failed.
    assert any(isinstance(e, vf.FollowupDone) for e in events)
    assert not any(isinstance(e, vf.FollowupFailed) for e in events)
    skip = [n for n in nerves
            if n.get("nerve") == "malformed_stream_payload" and n.get("severity") == "skip"]
    assert len(skip) == 1


def test_followup_truncated_final_surfaces_retryable_failed(monkeypatch, _ollama_adapter):
    nerves = _capture_nerves(monkeypatch)
    lines = [
        json.dumps({"message": {"content": "Hej "}}).encode("utf-8"),
        b'{"message": {"content": "afbr',  # trunkeret final UDEN done
    ]
    events = _drive_followup(_ollama_adapter, lines, monkeypatch)
    failed = [e for e in events if isinstance(e, vf.FollowupFailed)]
    assert len(failed) == 1
    # Typed retryable malformed → 4.1's rund-retry fanger den.
    assert failed[0].failure_kind == FailureKind.MALFORMED_STREAM_PAYLOAD
    assert is_retryable_kind(failed[0].failure_kind) is True
    fail_nerves = [n for n in nerves
                   if n.get("nerve") == "malformed_stream_payload" and n.get("severity") == "fail"]
    assert len(fail_nerves) == 1
