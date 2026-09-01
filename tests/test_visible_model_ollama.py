"""Tests for core/services/visible_model_ollama.py.

Fokus: ollama-stiens håndtering af `message.thinking` fra thinking-modeller.

FUNDET 2026-09-01: tanken blev samlet op til followup-replay, men ALDRIG sendt
videre til klienten. glm-5.3-flash stod derfor tavs i 19,30 s mens 583
tanke-bidder ankom. Samme hul som deepseek-stien havde.
"""

from __future__ import annotations

import json

import core.services.visible_model_ollama as vmo
from core.services.visible_model_types import (
    VisibleModelDelta,
    VisibleModelReasoningDelta,
)


class _FakeResp:
    """Minimal stand-in for ollamas NDJSON-svar."""

    def __init__(self, events: list[dict]) -> None:
        self._lines = [json.dumps(e).encode() for e in events]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __iter__(self):
        return iter(self._lines)


def test_thinking_bliver_streamet_som_reasoning_delta() -> None:
    """Kilden til rettelsen: tanken skal FORLADE adapteren, ikke kun gemmes."""
    src = (vmo.__file__ and open(vmo.__file__, encoding="utf-8").read()) or ""
    # Grenen findes, og den yielder — ikke bare appender.
    assert "VisibleModelReasoningDelta(delta=think)" in src
    i_append = src.index("reasoning_parts.append(think)")
    i_yield = src.index("yield VisibleModelReasoningDelta(delta=think)")
    assert i_yield > i_append, "tanken skal stadig gemmes til replay OG sendes"


def test_reasoning_delta_er_ikke_synlig_tekst() -> None:
    """Tanken må vises som 'tænker…' — aldrig som en del af svaret."""
    tanke = VisibleModelReasoningDelta(delta="hemmelig overvejelse")
    assert not isinstance(tanke, VisibleModelDelta)


def test_modulet_eksporterer_reasoning_typen() -> None:
    """Importen er en del af kontrakten — uden den brækker grenen ved kald."""
    assert vmo.VisibleModelReasoningDelta is VisibleModelReasoningDelta


def test_thinking_saetter_foerste_token_maalepunkt() -> None:
    """Ræsonnering ankommer FØR content og er et gyldigt første-token-mål.

    Ellers ville TTFT-tallet for thinking-modeller måle slutningen af
    tænkningen i stedet for begyndelsen — og skjule præcis den ventetid
    Bjørn oplevede.
    """
    src = open(vmo.__file__, encoding="utf-8").read()
    blok = src[src.index('think = str(msg.get("thinking")'):]
    blok = blok[:blok.index("tool_calls =")]
    assert '_t_first_content["ts"]' in blok
