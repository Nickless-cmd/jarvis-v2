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

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from core.skills.voice import wake_word
from core.skills.voice.stt import listen_and_transcribe
from core.skills.voice.tts import say

API_BASE = "http://localhost:80"


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


def on_wake_word(word: str):
    import re
    say("Ja?", blocking=True)

    print("[stt] optager...", flush=True)
    text = listen_and_transcribe(duration=5.0, language="da")
    # Filter out pure noise/sound-effect descriptions like "(baggrundsstøj)"
    text_clean = re.sub(r"\([^)]*\)", "", text).strip()
    if not text_clean:
        say("Jeg hørte ikke noget.", blocking=True)
        return
    text = text_clean

    print(f"[stt] hørt: {text}", flush=True)
    say("Et øjeblik.", blocking=False)

    try:
        session_id = get_active_session_id()
        response = ask_jarvis(session_id, text)
    except Exception as e:
        print(f"[api] fejl: {e}", flush=True)
        say("Beklager, jeg kunne ikke nå min hjerne.", blocking=True)
        return

    if not response:
        say("Jeg har intet svar.", blocking=True)
        return

    print(f"[tts] svarer: {response[:80]}...", flush=True)
    say(response, blocking=True)


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
