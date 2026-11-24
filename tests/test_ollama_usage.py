"""Den fælles Ollama-bogføring (24/11-2026).

``core/services/ollama_usage.py`` findes fordi dækningen var **3-8% hver enkelt
dag**: Ollama målte 19.472 kald og $34,27 på syv dage, mens ``costs`` havde
1.055 rækker og $3,65. Ni filer sender rigtige Ollama-kald, og kun én af dem
kaldte ``record_cost``. Denne fil tester mekanismen selv — integrationen mod
heartbeat-stien ligger i ``tests/test_heartbeat_runtime_providers.py``.
"""

from __future__ import annotations

import json
from unittest import mock

from core.costing import ledger
from core.services import ollama_usage


def test_bogfoer_kald_skriver_en_raekke_og_returnerer_prisen() -> None:
    """Mekanismen: tokens ind → én costs-række ud med en pris > 0."""
    fanget: list[dict] = []
    with mock.patch.object(ledger, "record_cost", side_effect=lambda **kw: fanget.append(kw)):
        pris = ollama_usage.bogfoer_ollama_kald(
            provider="ollama",
            model="deepseek-v4.1-flash:cloud",
            input_tokens=40000,
            output_tokens=900,
            cache_hit_tokens=34000,
            cache_miss_tokens=6000,
            lane="daemon",
        )

    assert len(fanget) == 1
    assert fanget[0]["lane"] == "daemon"
    assert fanget[0]["input_tokens"] == 40000
    assert pris > 0
    assert fanget[0]["cost_usd"] == pris


def test_en_ukendt_lokal_model_prissættes_ikke() -> None:
    """En lokal model er gratis. En opdigtet pris er værre end nul."""
    fanget: list[dict] = []
    with mock.patch.object(ledger, "record_cost", side_effect=lambda **kw: fanget.append(kw)):
        pris = ollama_usage.bogfoer_ollama_kald(
            provider="ollama",
            model="llama3:8b",
            input_tokens=500,
            output_tokens=20,
            lane="daemon",
        )

    assert pris == 0.0
    assert fanget[0]["cost_usd"] == 0.0


def test_en_fejl_i_regnskabet_kaster_ikke() -> None:
    """Den der betalte for kaldet skal ikke miste sit svar til en DB-fejl."""
    with mock.patch.object(ledger, "record_cost", side_effect=RuntimeError("db nede")):
        pris = ollama_usage.bogfoer_ollama_kald(
            provider="ollama",
            model="deepseek-v4.1-flash:cloud",
            input_tokens=100,
            output_tokens=10,
            lane="daemon",
        )

    assert pris == 0.0


def test_kvote_reference_henter_ollamas_eget_tal() -> None:
    """`usage_usd` er pro-planens KVOTE-MÅLER, ikke en faktura — den skal kunne læses."""
    svar = {
        "range": "7d",
        "from": "2026-11-17T00:00:00Z",
        "until": "2026-11-24T17:00:00Z",
        "totals": {
            "request_count": 19472,
            "usage_usd": 34.27,
            "input_tokens": 919650758,
            "cached_input_tokens": 780049130,
            "output_tokens": 11838243,
        },
        "buckets": [],
    }

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(svar).encode()

    with mock.patch.object(
        ollama_usage.urllib.request, "urlopen", return_value=_Resp()
    ), mock.patch("core.runtime.secrets.read_runtime_key", return_value="noegle"):
        k = ollama_usage.kvote_reference()

    assert k is not None
    assert k["kald"] == 19472
    assert k["usage_usd"] == 34.27
    assert k["cached_input_tokens"] == 780049130


def test_kvote_reference_gaetter_aldrig_naar_den_ikke_kan_hente() -> None:
    """`None` er ærligt. Et opfundet tal ville se ud som en måling."""
    with mock.patch("core.runtime.secrets.read_runtime_key", return_value=""):
        assert ollama_usage.kvote_reference() is None

    with mock.patch(
        "core.runtime.secrets.read_runtime_key", return_value="noegle"
    ), mock.patch.object(
        ollama_usage.urllib.request, "urlopen", side_effect=RuntimeError("net nede")
    ):
        assert ollama_usage.kvote_reference() is None
