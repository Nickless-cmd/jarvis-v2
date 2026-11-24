"""Ollama-vejen i inner-llm-enrichment skal skrive i HOVEDBOGEN, ikke kun i skyggen.

HVORFOR (målt 24/11-2026). ``_call_ollama_chat`` kaldte kun
``central_llm_egress.observe``, som skriver til en in-memory ring-buffer på 100
samples pr. nerve. Den forsvinder ved genstart og efterlader ingen række i
``costs``. Samtidig resolver ``_resolve_enrichment_target()`` til
``provider=ollama`` med ``deepseek-v4.1-flash:cloud`` — den dyreste model vi har —
og ``_enrich_worker`` kalder ``_call_cheap_llm`` tre gange pr. afsluttet tur.
Resultatet var ~561 ollama-kald i døgnet som Ollamas eget dashboard så, men vores
regnskab ikke gjorde.

Testen beviser tre ting, og den tredje er den der let glider:
  1. et vellykket kald bogfører præcis én række med rigtig lane og provider,
  2. tokens kommer fra Ollamas egne felter (``prompt_eval_count``/``eval_count``),
  3. cache-splittet bruger ``prompt_eval_cached_count`` — ikke 0/alt-som-miss,
     som er den dyre side af regnestykket.

Et fejlet kald må ikke bogføre: der blev intet købt.
"""

from __future__ import annotations

import json

import core.memory.inner_llm_enrichment as ile


class _FakeResp:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def read(self) -> bytes:
        return self._payload


def _install_fake_http(monkeypatch, response: dict) -> None:
    def _fake_urlopen(req, timeout=None):  # noqa: ARG001
        return _FakeResp(json.dumps(response).encode("utf-8"))

    monkeypatch.setattr(ile.urllib_request, "urlopen", _fake_urlopen)


def _fang_bogfoering(monkeypatch) -> list[dict]:
    """Patch ``bogfoer_ollama_kald`` på MODULET.

    Importen inde i ``_call_ollama_chat`` sker ved kaldstid, så en patch af
    ``core.services.ollama_usage.bogfoer_ollama_kald`` rammer den faktiske
    funktion — ikke en kopi bundet ved import.
    """
    kald: list[dict] = []

    import core.services.ollama_usage as ollama_usage

    monkeypatch.setattr(
        ollama_usage, "bogfoer_ollama_kald", lambda **kw: kald.append(kw) or 0.0
    )
    return kald


def test_ollama_kald_bogfoeres_med_tokens_og_cache_split(monkeypatch):
    # Ollamas eget svarformat: token-felterne ligger på top-niveau, ikke under
    # "usage" som OpenAI-formatet.
    response = {
        "model": "deepseek-v4.1-flash:cloud",
        "message": {"role": "assistant", "content": "en indre tanke"},
        "prompt_eval_count": 296,
        "eval_count": 279,
        "prompt_eval_cached_count": 20,
        "done": True,
    }
    _install_fake_http(monkeypatch, response)
    kald = _fang_bogfoering(monkeypatch)

    tekst = ile._call_ollama_chat(
        model="deepseek-v4.1-flash:cloud",
        base_url="http://127.0.0.1:11434",
        system_prompt="sys",
        user_message="hej",
        timeout=5,
    )

    assert tekst == "en indre tanke"

    # Præcis én række — ikke nul, og ikke to.
    assert len(kald) == 1
    kw = kald[0]
    assert kw["provider"] == "ollama"
    assert kw["model"] == "deepseek-v4.1-flash:cloud"
    assert kw["lane"] == "inner_enrichment"
    assert kw["input_tokens"] == 296
    assert kw["output_tokens"] == 279
    # Cache: 20 ramte, 276 missede — ikke 0/296.
    assert kw["cache_hit_tokens"] == 20
    assert kw["cache_miss_tokens"] == 276


def test_manglende_cache_felt_giver_alt_som_miss(monkeypatch):
    """Lokale modeller og ældre daemons sender ikke ``prompt_eval_cached_count``.

    Så skal ALT tælles som miss — den dyre side — frem for at opfinde et hit.
    """
    response = {
        "message": {"content": "svar"},
        "prompt_eval_count": 100,
        "eval_count": 50,
    }
    _install_fake_http(monkeypatch, response)
    kald = _fang_bogfoering(monkeypatch)

    ile._call_ollama_chat(
        model="qwen3:4b-instruct-2507-q4_K_M",
        base_url="http://127.0.0.1:11434",
        system_prompt="",
        user_message="hej",
        timeout=5,
    )

    assert len(kald) == 1
    assert kald[0]["cache_hit_tokens"] == 0
    assert kald[0]["cache_miss_tokens"] == 100


def test_fejlet_kald_bogfoerer_intet(monkeypatch):
    """Et kald der kaster må ikke efterlade en regnskabsrække — der blev intet købt."""

    def _kaster(req, timeout=None):  # noqa: ARG001
        raise OSError("connection refused")

    monkeypatch.setattr(ile.urllib_request, "urlopen", _kaster)
    kald = _fang_bogfoering(monkeypatch)

    tekst = ile._call_ollama_chat(
        model="deepseek-v4.1-flash:cloud",
        base_url="http://127.0.0.1:11434",
        system_prompt="sys",
        user_message="hej",
        timeout=5,
    )

    assert tekst is None
    assert kald == []
