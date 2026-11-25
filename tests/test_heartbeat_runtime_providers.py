"""Heartbeat-stien skal bogføre sine Ollama-kald (24/11-2026).

HULLET, MÅLT 24/11-2026: ``GET https://ollama.com/api/usage`` med vores egen
nøgle svarede **$34,27 og 19.472 kald** for de sidste syv dage. Den levende
``costs``-tabel havde 1.055 ollama-rækker og $3,65 — **3-8% dækning hver enkelt
dag**, ikke en spike.

Den konkrete årsag til heartbeat-delen: ``_execute_ollama_prompt`` returnerede
et hårdkodet ``"cost_usd": 0.0``, og ``heartbeat_runtime`` skrev nullet videre
til ``heartbeat_runtime_ticks``. Målt: 1.361 ticks på syv dage, alle med
``cost_usd = 0.0`` — 3,5 mio input-tokens der blev brugt og bogført ingen
steder. Pris-tabellen var der hele tiden; det var KALDET der manglede.

Disse tests pinner at stien nu bogfører, at cache-splittet bruges, og at en
fejl i regnskabet ikke kan vælte et hjerteslag.
"""

from __future__ import annotations

import io
import json
from unittest import mock

from core.costing import ledger
from core.services import heartbeat_runtime_providers as p


class _FakeResp(io.BytesIO):
    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _kald(*, svar: dict, target: dict | None = None) -> tuple[dict, list[dict]]:
    """Kør den ægte ``_execute_ollama_prompt`` mod et simuleret Ollama-svar."""
    fanget: list[dict] = []
    tgt = target or {
        "base_url": "https://ollama.com",
        "model": "deepseek-v4.1-flash:cloud",
        "provider": "ollama",
    }
    with mock.patch.object(
        p.urllib_request, "urlopen", return_value=_FakeResp(json.dumps(svar).encode())
    ), mock.patch.object(ledger, "record_cost", side_effect=lambda **kw: fanget.append(kw)):
        ud = p._execute_ollama_prompt(prompt="x" * 1000, target=tgt)
    return ud, fanget


def test_ollama_kald_bogfoeres_med_en_rigtig_pris() -> None:
    """Kernen: et heartbeat-kald skal give en costs-række med pris > 0."""
    ud, fanget = _kald(
        svar={
            "response": '{"decision": "continue"}',
            "prompt_eval_count": 40000,
            "prompt_eval_cached_count": 34000,
            "eval_count": 900,
        }
    )

    assert len(fanget) == 1, f"forventede præcis én bogføring, fik {len(fanget)}"
    rad = fanget[0]
    assert rad["lane"] == "heartbeat"
    assert rad["provider"] == "ollama"
    assert rad["model"] == "deepseek-v4.1-flash:cloud"
    assert rad["input_tokens"] == 40000
    assert rad["output_tokens"] == 900
    assert rad["cost_usd"] > 0, "prisen blev ikke beregnet — hullet er ikke lukket"
    assert ud["cost_usd"] == rad["cost_usd"], "tick-tabellen skal se samme pris"
    assert ud["cost_recorded"] is True, "ydre lag skal kunne undgå dobbelt-bogføring"


def test_cache_split_goer_prisen_rigtig_og_ikke_den_dyre_side() -> None:
    """Uden split prissættes ALT som cache-miss. Ollama sender feltet — brug det."""
    _, med_cache = _kald(
        svar={
            "response": "{}",
            "prompt_eval_count": 40000,
            "prompt_eval_cached_count": 34000,
            "eval_count": 100,
        }
    )
    _, uden_cache = _kald(
        svar={"response": "{}", "prompt_eval_count": 40000, "eval_count": 100}
    )

    assert med_cache[0]["cache_hit_tokens"] == 34000
    assert med_cache[0]["cache_miss_tokens"] == 6000
    assert uden_cache[0]["cache_hit_tokens"] == 0
    assert uden_cache[0]["cache_miss_tokens"] == 40000
    assert med_cache[0]["cost_usd"] < uden_cache[0]["cost_usd"], (
        "cache-hit skal være billigere end miss; ellers læses feltet ikke"
    )


def test_bogfoeringsfejl_kan_ikke_vaelte_et_hjerteslag() -> None:
    """Arbejdet er vigtigere end sporet til det — men svaret skal stadig komme."""
    with mock.patch.object(
        p.urllib_request,
        "urlopen",
        return_value=_FakeResp(
            json.dumps({"response": "ok", "prompt_eval_count": 10, "eval_count": 2}).encode()
        ),
    ), mock.patch.object(ledger, "record_cost", side_effect=RuntimeError("db nede")):
        ud = p._execute_ollama_prompt(
            prompt="hej",
            target={"base_url": "https://ollama.com", "model": "deepseek-v4.1-flash:cloud"},
        )

    assert ud["text"] == "ok"
    assert ud["execution_status"] == "success"
    assert ud["cost_usd"] == 0.0


def test_provider_foelger_target_saa_gateway_kontoen_ikke_bliver_bjoerns() -> None:
    """`ollama-a2` er Michelles konto. Blandes de, lyver regnskabet om hvem der betaler."""
    _, fanget = _kald(
        svar={"response": "ok", "prompt_eval_count": 100, "eval_count": 10},
        target={
            "base_url": "http://10.0.0.26:11434",
            "model": "gemma4:31b-cloud",
            "provider": "ollama-a2",
        },
    )

    assert fanget[0]["provider"] == "ollama-a2"
