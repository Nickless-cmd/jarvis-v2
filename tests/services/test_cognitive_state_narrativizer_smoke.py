"""Smoke test for core.services.cognitive_state_narrativizer.

The narrativizer should return a fallback on the cold call, then surface the
cached narrative once background generation has populated the cache.
"""

import time

from core.services import cognitive_state_narrativizer


def test_narrativize_line_returns_cached_text_after_refresh(monkeypatch) -> None:
    cognitive_state_narrativizer._CACHE.clear()
    cognitive_state_narrativizer._LAST_LLM_CALL_AT.clear()
    cognitive_state_narrativizer._REFRESH_INFLIGHT.clear()

    def _fake_background_generate(
        *, line_key: str, fingerprint: str, system_prompt: str, user_message: str
    ) -> None:
        with cognitive_state_narrativizer._CACHE_LOCK:
            cognitive_state_narrativizer._REFRESH_INFLIGHT.discard(line_key)
            cognitive_state_narrativizer._CACHE[line_key] = (
                cognitive_state_narrativizer._CachedNarrative(
                    fingerprint=fingerprint,
                    narrative="afklaret retning",
                    generated_at=time.time(),
                )
            )

    monkeypatch.setattr(
        cognitive_state_narrativizer,
        "_generate_in_background",
        _fake_background_generate,
    )

    state = {"mode": "reflective", "pressure": "medium"}
    first = cognitive_state_narrativizer.narrativize_line(
        line_key="body",
        state=state,
        system_prompt="Kort dansk sætning.",
        user_message_builder=lambda: "fortæl hvad kroppen mærker",
        fallback="venter på narrativ",
    )
    second = cognitive_state_narrativizer.narrativize_line(
        line_key="body",
        state=state,
        system_prompt="Kort dansk sætning.",
        user_message_builder=lambda: "fortæl hvad kroppen mærker",
        fallback="venter på narrativ",
    )

    assert first == "venter på narrativ"
    assert second == "afklaret retning"
