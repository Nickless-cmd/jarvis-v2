"""Regnskabs-vagter for Anthropic-compat-endpointet (30/10-2026).

MÅLT: ``/anthropic/v1/messages`` kaldte Ollama og returnerede uden at røre
``costs``. Alt der kom ind ad den dør var usynligt i hovedbogen — Ollama
fakturerede det, men vi kunne hverken se hvad det kostede eller hvem der
kaldte. Ollamas eget API viste 59.336 kald over 30 dage mod vores 161 i
døgnet; dsh-harnesset løb igennem netop denne sti.

Disse tests fælder tilbagefaldet: de kræver at BÅDE non-stream og stream
skriver en ``costs``-række med de tokens Ollama faktisk returnerede.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apps.api.jarvis_api.routes import anthropic_compat as ac


@pytest.fixture()
def ledger():
    """Fanger record_cost-kald uden at røre DB'en."""
    calls: list[dict] = []

    def _fake(**kwargs):
        calls.append(kwargs)

    with patch("core.costing.ledger.record_cost", _fake):
        yield calls


# ── non-stream ────────────────────────────────────────────────────────────────


def test_non_stream_bogfoerer_ollamas_tokens(ledger):
    """Ollamas svar bærer prompt_eval_count/eval_count — de skal i ledgeren."""
    response = {
        "prompt_eval_count": 1200,
        "eval_count": 300,
        "message": {"content": "hej"},
    }

    ac._book_usage(backend_model="deepseek-v4.1-flash:cloud", response=response)

    assert len(ledger) == 1, "non-stream-kaldet skrev ingen costs-række"
    row = ledger[0]
    assert row["input_tokens"] == 1200
    assert row["output_tokens"] == 300
    assert row["provider"] == "ollama"
    assert row["model"] == "deepseek-v4.1-flash:cloud"
    assert row["lane"] == "anthropic_compat"


def test_nul_tokens_skriver_ikke_en_nullinje(ledger):
    """Et svar uden token-tal må ikke producere en meningsløs nul-række."""
    ac._book_usage(backend_model="m", response={"message": {"content": "x"}})

    assert ledger == []


def test_manglende_record_cost_vaelter_ikke_svaret(ledger):
    """En regnskabsfejl må ikke gøre endpointet ubrugeligt — men må logges."""
    with patch(
        "core.costing.ledger.record_cost", side_effect=RuntimeError("db locked")
    ):
        # Må ikke kaste videre til kalderen.
        ac._book_usage(
            backend_model="m",
            response={"prompt_eval_count": 10, "eval_count": 2},
        )


# ── stream ────────────────────────────────────────────────────────────────────


def test_stream_bogfoerer_fra_done_chunket(ledger):
    """Stream er den vej Claude Desktop bruger — den må ikke være usynlig."""
    chunks = [
        {"message": {"content": "a"}, "done": False},
        {"message": {"content": "b"}, "done": False},
        {
            "message": {"content": ""},
            "done": True,
            "prompt_eval_count": 4000,
            "eval_count": 250,
        },
    ]

    out = list(ac._tap_usage(iter(chunks), backend_model="glm-5.3-flash:cloud"))

    assert out == chunks, "tappen må ikke ændre hvad klienten ser"
    assert len(ledger) == 1
    assert ledger[0]["input_tokens"] == 4000
    assert ledger[0]["output_tokens"] == 250
    assert ledger[0]["model"] == "glm-5.3-flash:cloud"


def test_stream_uden_done_chunk_bogfoerer_intet(ledger):
    """Afbrudt stream = vi ved ikke hvad den kostede; ingen gætte-række."""
    chunks = [{"message": {"content": "a"}, "done": False}]

    list(ac._tap_usage(iter(chunks), backend_model="m"))

    assert ledger == []


def test_stream_videresender_alt_selv_naar_bogfoering_fejler(ledger):
    """Klienten skal have sine chunks uanset om regnskabet fejler."""
    chunks = [
        {"message": {"content": "a"}, "done": False},
        {"done": True, "prompt_eval_count": 5, "eval_count": 1},
    ]
    with patch(
        "core.costing.ledger.record_cost", side_effect=RuntimeError("boom")
    ):
        out = list(ac._tap_usage(iter(chunks), backend_model="m"))

    assert out == chunks


# ── INTEGRATION: bliver bogføringen faktisk KALDT? ───────────────────────────
#
# Målt 30/10-2026: de isolerede tests ovenfor var grønne selv da BEGGE
# kald-steder blev fjernet fra endpointet. De beviste at funktionerne virker,
# ikke at de bliver brugt — og en bogføring der aldrig kaldes er præcis den
# slags teater der gjorde hullet usynligt i første omgang. Disse to vagter går
# gennem de rigtige stier og fælder hvis kaldet fjernes.


class _FakeRequest:
    """Minimal Request-stub: kun headers og json() bruges af endpointet."""

    def __init__(self, body: dict, headers: dict | None = None):
        self.headers = headers or {"x-api-key": "test"}
        self._body = body

    async def json(self) -> dict:
        return self._body


class _FakeSettings:
    anthropic_compat_enabled = True
    anthropic_compat_dev_mode_open = True


def _endpoint_patches(**extra):
    """Fælles patches så endpointet kan køres uden DB, netværk eller Ollama."""
    base = {
        "RuntimeSettings": _FakeSettings,
        "resolve_api_key": lambda *a, **k: {"user": "t", "workspace": "default"},
        "build_identity_prefix": lambda *a, **k: "",
        "translate_request_to_ollama": lambda **k: {"model": "m", "messages": []},
        "build_non_streaming_response": lambda **k: {"ok": True},
    }
    base.update(extra)
    return base


def test_endpointet_bogfoerer_i_non_stream(ledger):
    """GÅR GENNEM messages(): fjernes _book_usage-kaldet, fejler denne."""
    import asyncio

    response = {
        "prompt_eval_count": 777,
        "eval_count": 88,
        "message": {"content": "svar"},
    }
    patches = _endpoint_patches(
        _ollama_chat_non_stream=lambda payload: response,
        _resolve_backend_model=lambda m: "deepseek-v4.1-flash:cloud",
    )
    with patch.multiple(ac, **patches):
        asyncio.run(
            ac.messages(
                _FakeRequest(
                    {"messages": [{"role": "user", "content": "hej"}], "stream": False}
                )
            )
        )

    assert len(ledger) == 1, "endpointet kaldte Ollama uden at bogfoere forbruget"
    assert ledger[0]["input_tokens"] == 777
    assert ledger[0]["output_tokens"] == 88
    assert ledger[0]["model"] == "deepseek-v4.1-flash:cloud"


def test_endpointet_bogfoerer_i_stream(ledger):
    """GÅR GENNEM _stream_response(): fjernes tap'en, fejler denne."""
    chunks = [
        {"message": {"content": "a"}, "done": False},
        {"done": True, "prompt_eval_count": 321, "eval_count": 45},
    ]
    with patch.object(ac, "_ollama_chat_stream", lambda payload: iter(chunks)):
        out = list(
            ac._stream_response(
                payload={"model": "m", "messages": []},
                message_id="msg_test",
                model="jarvis",
                backend_model="glm-5.3-flash:cloud",
            )
        )

    assert out, "streamen gav intet til klienten"
    assert len(ledger) == 1, "stream-stien kaldte Ollama uden at bogfoere forbruget"
    assert ledger[0]["input_tokens"] == 321
    assert ledger[0]["output_tokens"] == 45

