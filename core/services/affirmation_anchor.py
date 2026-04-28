"""Short-reply anchor — bind user 'ja'/'yes'/'ok' back to Jarvis's previous turn.

Why this exists: when Bjørn answers a Jarvis offer with a 1–3 word reply
('ja', 'yes', 'gør det', 'go ahead'), the prompt assembly often loses the
binding to what Jarvis just proposed. The model sees 'user: ja' on its
own with no concrete action target, and generates a generic celebratory
response ('Ja! Hvor skønt 🚀') instead of executing the proposal.

This module detects short affirmations/negations and rewrites the user
message into an anchored form that explicitly references Jarvis's prior
turn:

  Original:  "ja"
  Anchored:
    [TURN ANCHOR — your previous message proposed an action]
    You just wrote: "Vil du se hele listen? Så kan jeg trække alle ud..."
    Bjørn's reply: "ja"
    This is a confirmation. Execute what you just proposed — do not
    start a new generic answer.

Best-effort. Returns the original message unchanged when:
  - The reply is longer than 5 words
  - There's no detectable affirmation/negation pattern
  - There's no session_id or no prior assistant turn to anchor to

Hooked into build_visible_chat_prompt_assembly so it runs before the
prompt is built. The transformation is invisible to the user — they see
their original 'ja' in the persisted chat history; only the model
prompt for *this turn* gets the anchor.
"""
from __future__ import annotations

import logging
import re

from core.services.chat_sessions import recent_chat_session_messages

logger = logging.getLogger(__name__)


_AFFIRMATIONS = {
    # Danish
    "ja", "jo", "yep", "jep", "selvfølgelig", "selvf", "klart",
    "gerne", "go", "fint", "godt", "perfekt", "super",
    "ok", "okay", "okidoki",
    "ja tak", "ja gerne", "ja gør det", "gør det", "kør", "kør på",
    "fortsæt", "videre", "go ahead", "let's go",
    # English
    "yes", "yeah", "yup", "sure", "do it", "go for it", "please do",
    "do that", "proceed", "continue",
}

_NEGATIONS = {
    # Exact-match only — these are checked strictly, no prefix-matching,
    # because phrases like "no problem" (English idiom for "you're welcome")
    # are not refusals.
    "nej", "nej tak", "ikke nu", "stop", "vent",
    "no", "nope", "not now", "hold on", "wait",
}


def _norm(text: str) -> str:
    return re.sub(r"[!?.,;:\s]+", " ", text or "").strip().lower()


def _is_short_reply(text: str) -> bool:
    """Short reply = ≤ 5 words and ≤ 40 characters after normalization."""
    norm = _norm(text)
    if not norm or len(norm) > 40:
        return False
    return len(norm.split()) <= 5


def classify_short_reply(text: str) -> str:
    """Return 'affirmation', 'negation', or '' if not a short binding reply."""
    if not _is_short_reply(text):
        return ""
    norm = _norm(text)
    if norm in _AFFIRMATIONS:
        return "affirmation"
    if norm in _NEGATIONS:
        return "negation"
    # Affirmation prefix-match: "ja gerne — så bare gør det" (multi-word
    # affirmation that starts with a clear yes-token). We only do prefix-
    # match on affirmations because negation idioms like "no problem"
    # would falsely trigger.
    first_token = norm.split()[0] if norm else ""
    if first_token in {"ja", "jo", "yes", "yeah", "ok", "okay"}:
        return "affirmation"
    return ""


def maybe_anchor_short_reply(user_message: str, session_id: str | None) -> str:
    """If the message is a short affirmation/negation, prepend a binding to
    the previous assistant turn. Otherwise return the message unchanged.

    Never raises — best-effort enrichment. Falls through to the original
    message on any error so the run still proceeds.
    """
    try:
        kind = classify_short_reply(user_message)
        if not kind or not session_id:
            return user_message
        # Pull the most recent assistant turn from chat history
        history = recent_chat_session_messages(session_id, limit=6)
        last_assistant = None
        # The current user message has already been persisted before this
        # function runs, so the history ends with this user turn. We want
        # the assistant turn just before that.
        for msg in reversed(history):
            role = str(msg.get("role") or "")
            if role == "assistant":
                last_assistant = msg
                break
        if last_assistant is None:
            return user_message

        last_text = str(last_assistant.get("content") or "").strip()
        if not last_text:
            return user_message

        # Trim to the last 400 chars — that's typically enough to contain
        # the question/offer Jarvis just made, without bloating the prompt.
        if len(last_text) > 400:
            last_text = "…" + last_text[-400:]

        if kind == "affirmation":
            directive = (
                "This is a confirmation. Execute what you just proposed in "
                "your previous turn — do not start a new generic answer or "
                "celebrate that things are working. If you offered a list, "
                "produce the list. If you offered an action, perform it."
            )
        else:  # negation
            directive = (
                "This is a refusal or pause. Do NOT execute what you just "
                "proposed. Acknowledge briefly and ask what they'd prefer "
                "instead, or wait."
            )

        anchored = (
            "[TURN ANCHOR — your previous message proposed an action]\n"
            f'You just wrote: "{last_text}"\n\n'
            f'Bjørn\'s reply: "{user_message}"\n\n'
            f"{directive}"
        )
        logger.info(
            "affirmation_anchor: bound short %s reply session=%s preview=%r",
            kind, (session_id or "")[:24], user_message[:40],
        )
        return anchored
    except Exception as exc:
        logger.debug("affirmation_anchor: failed, falling back: %s", exc)
        return user_message
