#!/usr/bin/env python3
"""
Full voice pipeline test:
  wake word → STT → Jarvis API → TTS

Run with: /opt/conda/envs/ai/bin/python3 core/skills/voice/voice_test_full.py
"""

import sys
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from core.skills.voice.stt import listen_and_transcribe
from core.skills.voice.tts import say
from core.skills.voice import wake_word

API_BASE = "http://localhost:80"


def get_first_session_id() -> str:
    with urllib.request.urlopen(f"{API_BASE}/chat/sessions") as r:
        data = json.loads(r.read())
    items = data.get("items", [])
    if not items:
        raise RuntimeError("No chat sessions found — create one in the UI first")
    return items[0]["id"]


def ask_jarvis(session_id: str, text: str) -> str:
    """Send message to Jarvis via SSE stream, return full response text."""
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
            if not chunk or chunk == "[DONE]":
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


def run_voice_loop(session_id: str):
    stop = threading.Event()

    def on_wake_word(word: str):
        import re
        print(f"\n[wake] '{word}' detected")
        say("Ja?", blocking=True)

        print("[stt] recording 5s...")
        text = listen_and_transcribe(duration=5.0, language="da")  # Danish
        # Filter out pure noise/sound-effect descriptions
        text_clean = re.sub(r"\([^)]*\)", "", text).strip()
        if not text_clean:
            say("Jeg hørte ikke noget.", blocking=True)
            return
        text = text_clean

        print(f"[stt] heard: {text}")
        say("One moment.", blocking=False)

        print("[api] asking Jarvis...")
        try:
            response = ask_jarvis(session_id, text)
        except Exception as e:
            print(f"[api] error: {e}")
            say("Sorry, I couldn't reach my brain.", blocking=True)
            return

        if not response:
            say("I have no response.", blocking=True)
            return

        print(f"[tts] speaking: {response[:80]}...")
        say(response, blocking=True)

    print(f"[voice] session: {session_id}")
    print("[voice] say 'Hey Jarvis' to start\n")

    try:
        wake_word.listen(callback=on_wake_word, interrupt_event=stop)
    except KeyboardInterrupt:
        stop.set()
        print("\n[voice] stopped")


if __name__ == "__main__":
    session_id = get_first_session_id()
    run_voice_loop(session_id)
