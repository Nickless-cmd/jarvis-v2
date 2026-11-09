"""Compaction-triggeren skal måle den SAMME overflade som requesten (9/11-2026).

## Fejlen der blev rettet

Triggeren i `_maybe_auto_compact_session` målte kun det rendrede transcript.
Den faktiske model-request bærer også den stabile system-prefix — identitet,
regler, værktøjskatalog, hukommelses-sektioner. Målt på en levende kørsel:

    prompt-assembly-size chars=102495 approx_tokens=25623 hale=32705
    visible-latency prompt_chars=442449

Assembly var 25.623 tokens; requesten var 442.449 tegn ≈ 110.000 tokens.
Triggeren så 77 % af konteksten og fyrede ved «80k» når den reelle kontekst var
~105k. Det er den målte grund til Bjørns observation samme dag: «den compacter
... aldrig helt ned hvor den burde».

## Hvad testene vogter

At prefixen lægges til beslutningsgrundlaget, at den deles mellem trigger og
statusrute (så de ikke kan divergere), og at et manglende estimat falder tilbage
til den gamle adfærd frem for at blokere turen.
"""
from __future__ import annotations

import pytest

from core.services import prompt_overhead
from core.services.prompt_overhead import reset_cache, stable_prefix_tokens


@pytest.fixture(autouse=True)
def _ren_cache():
    reset_cache()
    yield
    reset_cache()


def test_prefix_tokens_laegges_til_beslutningsgrundlaget(monkeypatch):
    """Triggeren skal se transcript + prefix — ikke kun transcript.

    Uden prefixen ville et transcript lige under budgettet ikke udløse
    komprimering. Med prefixen skal det gøre det.
    """
    from core.services.prompt_sections import transcript_sections as ts

    # Prefixen er den faste del; uden den er transcriptet under budgettet.
    monkeypatch.setattr(
        "core.services.prompt_overhead.stable_prefix_tokens",
        lambda **_: 20_000,
    )

    setninger = []

    class _S:
        context_attention_budget_tokens = 80_000
        context_attention_low_water_tokens = 35_000
        context_compact_safety_fraction = 0.85
        context_keep_recent = 20
        visible_model_provider = "deepseek"
        visible_model_name = "deepseek-v4-flash"

    def _falsk_beslutning(tokens, **_):
        setninger.append(tokens)

        class _D:
            should_compact = False
            low_water_target = 35_000
        return _D()

    monkeypatch.setattr(
        "core.context.compaction_policy.compaction_decision", _falsk_beslutning,
    )
    # 60.000 tokens transcript + 20.000 prefix = 80.000 → over budgettet.
    monkeypatch.setattr(
        "core.context.token_estimate.estimate_messages_tokens", lambda _m: 60_000,
    )

    ts._maybe_auto_compact_session("s-test", [{"role": "user", "content": "x"}], _S())

    assert setninger == [80_000], (
        "beslutningen skal måles på transcript + fast prefix, ikke transcript alene"
    )


def test_prefixen_er_self_safe(monkeypatch):
    """Et manglende estimat må give 0 — ikke kaste inde i en prompt-build."""
    def _braek(**_):
        raise RuntimeError("prefix utilgængelig")

    monkeypatch.setattr(
        "core.services.prompt_contract.build_visible_stable_prefix", _braek,
    )
    assert stable_prefix_tokens(provider="p", model="m", session_id="s") == 0


def test_prefixen_memoiseres(monkeypatch):
    """Prefixen er deterministisk inden for et workspace — den skal ikke bygges pr. tur."""
    kald = []

    def _tael(**kwargs):
        kald.append(kwargs)
        return "x" * 400

    monkeypatch.setattr(
        "core.services.prompt_contract.build_visible_stable_prefix", _tael,
    )
    foerste = stable_prefix_tokens(provider="p", model="m", session_id="")
    anden = stable_prefix_tokens(provider="p", model="m", session_id="")

    assert foerste == anden
    assert len(kald) == 1, "anden måling skal ramme cachen, ikke bygge prefixen igen"


def test_statusruten_bruger_den_delte_kilde():
    """Ruten og triggeren skal måle gennem SAMME funktion.

    To steder der beskriver den samme størrelse driver fra hinanden — det var
    netop hvad der skete: ruten havde sin egen cache og sit eget workspace-opslag,
    mens triggeren slet ikke målte prefixen.
    """
    import inspect

    from apps.api.jarvis_api.routes import chat_context_usage as rute

    kilde = inspect.getsource(rute._system_overhead_tokens)
    assert "prompt_overhead" in kilde, (
        "statusruten skal kalde den delte overhead-kilde, ikke have sin egen kopi"
    )
    assert "build_visible_stable_prefix" not in kilde, (
        "ruten må ikke bygge prefixen selv — så kan de to igen divergere"
    )
