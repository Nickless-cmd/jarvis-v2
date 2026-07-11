"""POST /transcribe — diktering-transskription til jarvis-desk's mic-knap.

Modtager en uploadet lyd-blob (webm/opus fra MediaRecorder), transskriberer
lokalt via faster-whisper (core.services.dictation), returnerer {text}.
Privat + offline — ingen API-nøgle.
"""
from __future__ import annotations

import asyncio
import os
import tempfile

from fastapi import APIRouter, Form, UploadFile

router = APIRouter(tags=["chat"])

# Maks ~25 MB lyd (rigeligt til en diktering; beskytter mod misbrug).
_MAX_AUDIO_BYTES = 25 * 1024 * 1024


@router.post("/transcribe")
async def transcribe(file: UploadFile, language: str = Form(default="da")) -> dict:
    # Whisper auto-detekterede sprog PR. YTRING → korte/mumlede sætninger blev
    # gættet forkert (skiftede til engelsk). Standard = dansk (Bjørn/Mikkel taler
    # dansk til Jarvis); send language="auto"/"" for at genaktivere auto-detektion.
    lang: str | None = (language or "").strip().lower() or None
    if lang in ("auto", "detect"):
        lang = None
    data = await file.read()
    if not data:
        return {"status": "error", "text": "", "error": "empty audio"}
    if len(data) > _MAX_AUDIO_BYTES:
        return {"status": "error", "text": "", "error": "audio too large"}

    # Suffix fra upload-filnavnet hjælper PyAV med at vælge demuxer.
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        from core.services.dictation import transcribe_file
        # Blokerende (CPU-bundet) → kør i threadpool så event-loop ikke hænger.
        result = await asyncio.to_thread(transcribe_file, tmp_path, language=lang)
        return result
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
