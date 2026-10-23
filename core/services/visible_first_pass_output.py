"""Én synlig grænse for første modelsvar.

Første pas har to former for model-kontekst der aldrig må nå mennesket:
capability-markup og runtime-markører. Tidsstempler hører til den sidste
kategori: de bliver i transskriptet, men en model-efterligning fjernes her.

Udskilt fra ``visible_runs.py`` efter Boy Scout-reglen. Kalderen behøver kun
``feed`` og ``flush`` og kan derfor ikke glemme at skylle den ene af de to
state-maskiner.
"""
from __future__ import annotations

from core.services.prompt_sections.capability_markup import _CapabilityMarkupBuffer
from core.services.visible_text_scrub import StroemSkrubber


class FirstPassOutputFilter:
    """Filtrér capability-markup først og synlige runtime-markører bagefter."""

    def __init__(self) -> None:
        self._markup = _CapabilityMarkupBuffer()
        self._synlig = StroemSkrubber()

    def feed(self, text: str) -> str:
        return self._synlig.foed(self._markup.feed(text))

    def flush(self) -> str:
        dele: list[str] = []
        markup_rest = self._markup.flush()
        if markup_rest:
            dele.append(self._synlig.foed(markup_rest))
        dele.append(self._synlig.skyl())
        return "".join(dele)


__all__ = ["FirstPassOutputFilter"]
