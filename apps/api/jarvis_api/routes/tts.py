"""TTS synthesis route — backed by Microsoft Edge's read-aloud cloud
voices via the `edge-tts` Python package. Free, no API key, supports
all Azure Neural voices including the Danish ones (Christel, Jeppe).

Replaces ElevenLabs as the production TTS path now that those credits
are out. Returns audio/mpeg bytes so callers (operator_speak on the
JarvisX bridge, future voice modules) can stream-play it.
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger("uvicorn.error")

_DEFAULT_VOICE = "da-DK-JeppeNeural"
_MAX_TEXT_CHARS = 5000  # sanity cap; long Jarvis monologues should be summarized first


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to synthesize.")
    voice: str | None = Field(
        default=None,
        description=(
            "Edge-TTS voice id (e.g. 'da-DK-ChristelNeural', 'da-DK-JeppeNeural', "
            "'en-US-JennyNeural'). Defaults to Danish Christel."
        ),
    )
    rate: str | None = Field(
        default=None,
        description="Speed adjustment, e.g. '+0%', '+20%', '-10%'. Default 0.",
    )
    pitch: str | None = Field(
        default=None,
        description="Pitch adjustment, e.g. '+0Hz', '+20Hz'. Default 0.",
    )


@router.post("/synthesize")
async def synthesize(req: TTSRequest) -> Response:
    """Synthesize text → MP3 bytes via edge-tts.

    Returns audio/mpeg directly so callers can stream-write to a file
    or pipe straight to a player without a roundtrip through JSON.
    """
    text = (req.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > _MAX_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"text too long ({len(text)} chars, max {_MAX_TEXT_CHARS})",
        )

    voice = (req.voice or _DEFAULT_VOICE).strip() or _DEFAULT_VOICE
    rate = (req.rate or "+0%").strip() or "+0%"
    pitch = (req.pitch or "+0Hz").strip() or "+0Hz"

    try:
        import edge_tts
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"edge-tts not installed: {exc}")

    buf = io.BytesIO()
    try:
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                buf.write(chunk.get("data") or b"")
    except Exception as exc:
        logger.warning("edge-tts synth failed voice=%s len=%d: %s", voice, len(text), exc)
        raise HTTPException(status_code=502, detail=f"tts synthesis failed: {exc!s}"[:200])

    audio = buf.getvalue()
    if not audio:
        raise HTTPException(status_code=502, detail="tts returned empty audio")

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=tts.mp3",
            "X-TTS-Voice": voice,
            "X-TTS-Bytes": str(len(audio)),
        },
    )


@router.get("/voices")
async def list_voices(lang: str | None = None) -> dict[str, Any]:
    """List available Edge-TTS voices, optionally filtered by language tag.

    Useful for surfacing a voice picker in the UI. lang is matched as a
    case-insensitive prefix on the voice's Locale field (e.g. 'da' →
    all Danish voices; 'en-US' → US English only).
    """
    try:
        import edge_tts
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"edge-tts not installed: {exc}")

    try:
        all_voices = await edge_tts.list_voices()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"voice listing failed: {exc!s}"[:200])

    if lang:
        prefix = lang.strip().lower()
        all_voices = [v for v in all_voices if (v.get("Locale") or "").lower().startswith(prefix)]

    # Slim shape — just what a picker UI needs.
    return {
        "count": len(all_voices),
        "voices": [
            {
                "name": v.get("ShortName") or v.get("Name"),
                "locale": v.get("Locale"),
                "gender": v.get("Gender"),
                "friendly": v.get("FriendlyName"),
            }
            for v in all_voices
        ],
    }
