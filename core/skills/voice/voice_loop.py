"""Main voice interaction loop — wake word → listen → respond."""

import threading
import time

from .wake_word import WakeWordDetector
from .stt import listen_and_transcribe
from .tts import say


class VoiceLoop:
    """
    Full voice interaction cycle:
    1. Listen for wake word ("Hey Jarvis")
    2. Record user speech and transcribe
    3. Get response (via callback)
    4. Speak response aloud
    """

    def __init__(self, response_fn=None, wake_words: list[str] | None = None):
        """
        Args:
            response_fn: Callable(text: str) -> str. Takes transcribed user speech,
                         returns text response to speak aloud.
            wake_words: Wake words to listen for.
        """
        self.response_fn = response_fn or self._default_response
        self.detector = WakeWordDetector(wake_words)
        self._stop_event = threading.Event()
        self._listening = False

    @staticmethod
    def _default_response(text: str) -> str:
        """Fallback response if no callback provided."""
        return f"I heard you say: {text}"

    def _on_wake_word(self, word: str):
        """Handle wake word detection."""
        print(f"\n✨ {word} detected! Listening for command...")
        say("Yes?", blocking=True)

        try:
            text = listen_and_transcribe(duration=5.0)
            if not text:
                say("I didn't catch that.", blocking=True)
                return

            print(f"📝 Heard: {text}")
            response = self.response_fn(text)
            print(f"💬 Responding: {response}")
            say(response, blocking=True)

        except Exception as e:
            print(f"❌ Error in voice loop: {e}")
            say("Sorry, something went wrong.", blocking=True)

    def run(self):
        """Start the voice loop (blocking)."""
        self._listening = True
        self._stop_event.clear()
        print("🔄 Voice loop started — say 'Hey Jarvis' to interact")
        try:
            self.detector.listen(callback=self._on_wake_word, interrupt_event=self._stop_event)
        finally:
            self._listening = False

    def stop(self):
        """Stop the voice loop."""
        self._stop_event.set()


def quick_test():
    """Quick test: detect wake word, then record + transcribe one command."""
    print("=== Voice Quick Test ===")
    print("Say 'Hey Jarvis' to trigger, then speak a command.\n")

    loop = VoiceLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        loop.stop()
        print("\n👋 Stopped.")


if __name__ == "__main__":
    quick_test()