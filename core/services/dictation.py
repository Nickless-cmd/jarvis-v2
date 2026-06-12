"""Dictation-transskription til jarvis-desk's mic-knap.

Lokal faster-whisper (offline, privat, ingen API-nøgle). Adskilt fra
core.skills.voice.stt (som er host-mic/VAD-orienteret og bruger en lille
"tiny"-model) — her bruger vi en bedre default ("small") til diktering og
accepterer en uploadet lydfil (webm/opus/wav — afkodes via PyAV).

Model-størrelse kan overstyres via runtime.json-nøglen
``dictation_whisper_model`` (default "small").
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MODEL_SIZE = "small"
_model_cache: dict[tuple[str, str, str], Any] = {}


def _resolve_model_size(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        from core.runtime.secrets import read_runtime_key
        cfg = read_runtime_key("dictation_whisper_model")
        if cfg:
            return str(cfg)
    except Exception:
        pass
    return _DEFAULT_MODEL_SIZE


def _get_model(model_size: str, device: str = "cpu", compute_type: str = "int8") -> Any:
    key = (model_size, device, compute_type)
    cached = _model_cache.get(key)
    if cached is None:
        from faster_whisper import WhisperModel
        cached = WhisperModel(model_size, device=device, compute_type=compute_type)
        _model_cache[key] = cached
    return cached


def _join_segments(segments: Any) -> str:
    """Saml whisper-segmenter til én streng. Ren funktion (testbar)."""
    return " ".join(s.text.strip() for s in segments).strip()


def transcribe_file(
    path: str,
    *,
    model_size: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Transskribér en lydfil. Returnerer {status, text, language}.

    language=None → auto-detektion (håndterer dansk + engelsk). Blokerende
    (CPU-bundet) — kald via threadpool fra async-routes.
    """
    size = _resolve_model_size(model_size)
    try:
        model = _get_model(size)
        segments, info = model.transcribe(
            path,
            language=language,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = _join_segments(segments)
        return {
            "status": "ok",
            "text": text,
            "language": getattr(info, "language", "") or "",
        }
    except Exception as exc:
        logger.error("dictation: transcribe failed: %s", exc, exc_info=True)
        return {"status": "error", "text": "", "error": str(exc)}
