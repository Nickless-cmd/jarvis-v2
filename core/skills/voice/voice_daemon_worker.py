#!/usr/bin/env python3
"""Voice daemon worker — runs the Hey Jarvis loop, called by voice_daemon.py.

Must be run with /opt/conda/envs/ai/bin/python3 (has edge-tts, faster-whisper, etc.)
Gets the active Jarvis session from the API and connects voice input to it.
"""
import json
import sys
import threading
import urllib.request
from pathlib import Path

_PHASE_FILE = Path("/tmp/jarvis-voice-phase.json")


def _set_phase(phase: str) -> None:
    """Write current voice pipeline phase for the desktop orb to read."""
    try:
        _PHASE_FILE.write_text(json.dumps({"phase": phase}))
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from core.skills.voice import wake_word
from core.skills.voice.stt import listen_and_transcribe
from core.skills.voice.tts import say

API_BASE = "http://localhost:8080"  # uvicorn lytter nu KUN på localhost:8080 (Caddy ejer :80/:443)


def get_active_session_id() -> str:
    with urllib.request.urlopen(f"{API_BASE}/chat/sessions", timeout=5) as r:
        data = json.loads(r.read())
    items = data.get("items", [])
    if not items:
        raise RuntimeError("No chat sessions available")
    return items[0]["id"]


def ask_jarvis(session_id: str, text: str) -> str:
    payload = json.dumps({"session_id": session_id, "message": text}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/stream",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    full_text = ""
    with urllib.request.urlopen(req, timeout=60) as resp:
        for raw_line in resp:
            line = raw_line.decode("utf-8").rstrip("\n")
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if not chunk:
                continue
            try:
                event = json.loads(chunk)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "delta":
                full_text += event.get("delta", "")
            elif event.get("type") == "done":
                break
    return full_text.strip()


import os
import re

# Follow-up window: after Jarvis answers, listen N seconds for an
# unprompted follow-up so Bjørn doesn't have to say "Hey Jarvis" again
# every turn. Set FOLLOW_UP_SECONDS=0 (or env JARVIS_VOICE_FOLLOW_UP=0)
# to disable.
FOLLOW_UP_SECONDS = float(os.environ.get("JARVIS_VOICE_FOLLOW_UP_S", "6"))


def _capture_user_utterance(duration: float) -> str:
    """Listen N seconds, return cleaned utterance or '' if silence/noise."""
    text = listen_and_transcribe(duration=duration, language="da")
    # Strip sound-effect markup like "(baggrundsstøj)"
    return re.sub(r"\([^)]*\)", "", text).strip()


def _handle_turn(text: str) -> bool:
    """Process one utterance through ask_jarvis + speak. Returns False if
    something went wrong and we should bail out of the loop."""
    print(f"[stt] hørt: {text}", flush=True)
    _set_phase("think")
    say("Et øjeblik.", blocking=False)

    try:
        session_id = get_active_session_id()
        response = ask_jarvis(session_id, text)
    except Exception as e:
        print(f"[api] fejl: {e}", flush=True)
        _set_phase("idle")
        say("Beklager, jeg kunne ikke nå min hjerne.", blocking=True)
        return False

    if not response:
        _set_phase("idle")
        say("Jeg har intet svar.", blocking=True)
        return False

    print(f"[tts] svarer: {response[:80]}...", flush=True)
    _set_phase("speak")
    say(response, blocking=True)
    return True


def on_wake_word(word: str):
    say("Ja?", blocking=True)

    _set_phase("user")
    print("[stt] optager...", flush=True)
    text = _capture_user_utterance(duration=5.0)
    if not text:
        _set_phase("idle")
        say("Jeg hørte ikke noget.", blocking=True)
        return

    if not _handle_turn(text):
        return

    # Follow-up loop: stay in conversation without requiring fresh wake-word.
    # Each iteration listens for FOLLOW_UP_SECONDS; silence ends the session.
    while FOLLOW_UP_SECONDS > 0:
        _set_phase("user")
        print(f"[stt] follow-up vindue ({FOLLOW_UP_SECONDS:.0f}s)...", flush=True)
        follow_up = _capture_user_utterance(duration=FOLLOW_UP_SECONDS)
        if not follow_up:
            print("[stt] stilhed → tilbage til wake-word-mode", flush=True)
            break
        if not _handle_turn(follow_up):
            break

    _set_phase("idle")


def main():
    print("[voice] starter Hey Jarvis loop...", flush=True)
    stop = threading.Event()
    try:
        wake_word.listen(callback=on_wake_word, interrupt_event=stop)
    except KeyboardInterrupt:
        stop.set()
        print("[voice] stoppet", flush=True)


if __name__ == "__main__":
    main()
