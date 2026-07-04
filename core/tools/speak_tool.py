"""Speak tool — Jarvis speaks aloud through system speakers.

Wraps the existing TTS infrastructure (ElevenLabs primary, edge-tts
fallback) into a callable tool. Modstykket til mic_listen: hvor mic_listen
indtager lyd fra rummet, udsender speak_tool lyd til rummet.

Two modes:
- blocking (default): wait for playback to finish before returning
- nonblocking: fire-and-forget, return immediately (async playback thread)

Default voice: Jesper (Danish, calm, deep, rigsdansk). Override via
voice_id parameter or JARVIS_TTS_VOICE_ID env var.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Reuse the existing TTS engine
from core.skills.voice.tts import say as _tts_say


def _exec_speak(args: dict[str, Any]) -> dict[str, Any]:
    """Execute the speak tool: synthesize text and play through speakers."""
    text = str(args.get("text") or "").strip()
    if not text:
        return {
            "status": "error",
            "text": "No text provided — supply a 'text' parameter with what to say.",
        }

    blocking = bool(args.get("blocking", False))
    voice_id = args.get("voice_id")  # None = use default (Jesper)

    try:
        # If a specific voice ID is requested, override env for this call
        if voice_id:
            import os
            old = os.environ.get("JARVIS_TTS_VOICE_ID")
            os.environ["JARVIS_TTS_VOICE_ID"] = voice_id
            path = _tts_say(text, blocking=blocking)
            if old:
                os.environ["JARVIS_TTS_VOICE_ID"] = old
            else:
                del os.environ["JARVIS_TTS_VOICE_ID"]
        else:
            path = _tts_say(text, blocking=blocking)

        mode = "blocking" if blocking else "nonblocking"
        preview = text if len(text) <= 120 else text[:120] + "..."

        # Egress-fri Central-observation (§24.4): Jarvis UDSENDER stemme til rummet
        # (hånden/handling). Kun længde + mode — ALDRIG selve teksten. Self-safe.
        try:
            from core.services.central_private_observe import record_private
            record_private(
                "channel", "speak",
                value=float(len(text)),
                meta={"chars": len(text), "mode": str(mode)},
                reason="voice output",
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "text": f"Spoke ({mode}): {preview}",
            "mode": mode,
            "voice_id": voice_id or "default (Jesper)",
            "audio_path": path,
            "full_text": text,
        }

    except Exception as exc:
        logger.exception("speak tool failed")
        return {
            "status": "error",
            "text": f"Speech failed: {exc}",
        }


SPEAK_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "speak",
            "description": (
                "Synthesize text-to-speech and play it through the system "
                "speakers. Modstykket til mic_listen: brug denne når du vil "
                "tale højt i rummet. ElevenLabs primær (dansk/engelsk), "
                "edge-tts som fallback. "
                "Default voice er Jesper (dansk, dyb, rolig, rigsdansk)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": (
                            "Teksten der skal læses højt. Kan være dansk, "
                            "engelsk eller blandet."
                        ),
                    },
                    "blocking": {
                        "type": "boolean",
                        "description": (
                            "Hvis true, vent til afspilning er færdig før "
                            "der returneres. Default false (fire-and-forget)."
                        ),
                    },
                    "voice_id": {
                        "type": "string",
                        "description": (
                            "Overstyr stemme-ID. Default: Jesper "
                            "(dansk, dyb). Alternativer: Mathias, Søren, "
                            "Camilla (kvinde), Constantin, George (engelsk)."
                        ),
                    },
                },
                "required": ["text"],
            },
        },
    },
]
