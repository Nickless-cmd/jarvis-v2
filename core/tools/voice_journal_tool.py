"""Voice Journal tool — dedicated longer recording → density note.

Records 30-60s of spoken reflection from the mic, transcribes via HF
Whisper-v3, and files a memory_density note with the transcript placed
in the 'what_happened' field. Jarvis can optionally be prompted to
later enrich the note with the other three fields (meant / felt /
changed) via a chat interaction.

Use case: Bjørn wants to capture a thought out loud without typing.
Say the thought, tool records, transcribes, saves. The density note
carries the timestamp and audio path for later reference.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_DURATION = 45.0  # seconds — mid-length journal entry
_MIN_DURATION = 5.0
_MAX_DURATION = 120.0
_MIN_TRANSCRIPT_CHARS = 10  # don't file density notes for empty/fragmentary speech


def _exec_voice_journal(args: dict[str, Any]) -> dict[str, Any]:
    try:
        duration = float(args.get("duration") or _DEFAULT_DURATION)
    except Exception:
        duration = _DEFAULT_DURATION
    duration = max(_MIN_DURATION, min(_MAX_DURATION, duration))
    title_hint = str(args.get("title") or "").strip()
    language = args.get("language")  # optional; Whisper auto-detects otherwise
    prompt = str(args.get("prompt") or "").strip()
    # Prompt is an optional seed ("What made today interesting?") — it's NOT
    # recorded, just stored alongside so Jarvis can recall the context.

    # Step 1 — listen, always save the WAV for audit trail
    try:
        from core.tools.mic_listen_tool import listen_and_transcribe
    except Exception as exc:
        return {"status": "error", "text": f"mic_listen import failed: {exc}"}

    listen_result = listen_and_transcribe(
        duration=duration,
        backend="hf",  # prefer cloud for journal quality
        language=str(language) if language else None,
        save_recording=True,
    )
    if listen_result.get("status") != "ok":
        return listen_result

    transcript = str(listen_result.get("text") or "").strip()
    wav_path = listen_result.get("saved_path")

    if len(transcript) < _MIN_TRANSCRIPT_CHARS:
        return {
            "status": "error",
            "text": (
                f"Transcript too short ({len(transcript)} chars) — probably silence "
                "or mic capture issue. WAV saved at "
                f"{wav_path if wav_path else 'not-saved'}."
            ),
            "transcript": transcript,
            "saved_path": wav_path,
        }

    # Step 2 — derive a title
    if not title_hint:
        # First sentence or first 60 chars
        end = min(len(transcript), 60)
        dot = transcript.find(".", 0, 80)
        if 10 < dot < 80:
            end = dot
        title_hint = transcript[:end].strip().rstrip(".,!?:;") or "Voice journal entry"

    # Step 3 — write density note
    try:
        from core.services.memory_density import write_density_note
    except Exception as exc:
        return {
            "status": "ok-no-density",
            "text": f"Transcribed ({len(transcript)} chars) but memory_density unavailable: {exc}",
            "transcript": transcript,
            "saved_path": wav_path,
        }

    metadata: dict[str, Any] = {
        "source": "voice_journal",
        "duration_seconds": duration,
        "wav_path": wav_path,
        "backend": listen_result.get("backend"),
        "capture_device": listen_result.get("capture_device"),
    }
    if prompt:
        metadata["seed_prompt"] = prompt

    note = write_density_note(
        title=title_hint[:120],
        what_happened=transcript,
        what_it_meant="(unfilled — to be reflected on later)",
        how_it_felt="(unfilled — to be reflected on later)",
        what_it_changed="(unfilled — to be reflected on later)",
        trigger_type="manual",
        metadata=metadata,
    )

    # Emit event so action_router / autonomous_outreach can notice
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish({
            "kind": "voice_journal.recorded",
            "payload": {
                "note_id": note.get("note_id"),
                "title": note.get("title"),
                "chars": len(transcript),
                "duration_s": duration,
                "wav_path": wav_path,
            },
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "text": (
            f"Voice journal saved: '{note.get('title')}' "
            f"({len(transcript)} chars, {duration:.0f}s). "
            f"Density note {note.get('note_id')}. "
            f"3 reflection fields unfilled — Jarvis can enrich later."
        ),
        "note_id": note.get("note_id"),
        "note_path": note.get("path"),
        "title": note.get("title"),
        "transcript": transcript,
        "wav_path": wav_path,
        "duration_s": duration,
    }


VOICE_JOURNAL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "voice_journal",
            "description": (
                "Record a spoken journal entry (30-60s default), transcribe it "
                "via Whisper-v3, and file it as a memory_density note with the "
                "transcript in 'what_happened'. The other density fields (meant, "
                "felt, changed) are left as placeholders for Jarvis to fill in "
                "later through reflection or conversation. Persists the WAV for "
                "audit. Emits voice_journal.recorded event."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {
                        "type": "number",
                        "description": "Seconds to record (5-120). Default 45.",
                    },
                    "title": {
                        "type": "string",
                        "description": (
                            "Optional title for the entry. If omitted, derived "
                            "from first sentence/60 chars of transcript."
                        ),
                    },
                    "language": {
                        "type": "string",
                        "description": "ISO hint e.g. 'da', 'en'. Omit for auto.",
                    },
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Optional seed question ('What made today interesting?') "
                            "stored in note metadata. Not played aloud."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
]
