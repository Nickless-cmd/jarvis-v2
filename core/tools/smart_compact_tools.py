"""Smart context compaction — preserves decisions/facts, discards routine."""
from __future__ import annotations

from typing import Any

from core.services.identity_composer import identity_prompt_prefix


def _smart_compact_prompt() -> str:
    """Build compact prompt lazily so identity_prompt_prefix resolves at runtime, not module import."""
    return (
        f"{identity_prompt_prefix()}' kontekst-kompressor. Analysér denne samtaledel og lav et kompakt, "
        "struktureret resumé.\n\n"
        "BEVAR ALTID:\n"
        '- Eksplicitte beslutninger ("vi besluttede", "vi valgte", "det er bekræftet")\n'
        "- Tekniske fakta (fil-stier, API-navne, konfigurationer, fejl der er løst)\n"
        "- Åbne spørgsmål eller opgaver der ikke er afsluttet\n"
        "- Brugerens eksplicitte præferencer eller korrektioner\n"
        "- Vigtige advarsler eller sikkerhedshensyn\n\n"
        "KASSÉR GERNE:\n"
        '- Statusbeskeder uden ny information ("ok", "forstået", "arbejder videre")\n'
        "- Gentagne forsøg på det samme (bevar kun resultatet)\n"
        "- Trivielle bekræftelser og small talk\n"
        "- Mellemtrin i en arbejdsproces (bevar kun beslutningerne)\n\n"
        "FORMAT:\n"
        "## Beslutninger\n"
        "- [liste]\n\n"
        "## Tekniske fakta\n"
        "- [liste]\n\n"
        "## Åbne punkter\n"
        "- [liste]\n\n"
        "## Øvrig kontekst\n"
        "[kompakt prosa, max 200 ord]\n\n"
        "Samtale:\n"
    )

_AUTO_COMPACT_TOKEN_THRESHOLD = 8000


def _estimate_session_tokens() -> int:
    """Rough estimate of current session's token count."""
    try:
        from core.services.chat_sessions import most_recent_session_id, recent_chat_session_messages
        from core.context.token_estimate import estimate_tokens
        # Hot-path fix: was list_chat_sessions() (formats EVERY session via
        # _session_summary→_preview_text, ~3184 calls/assembly) then read
        # sessions[0]["session_id"] — but _session_summary renames it to "id",
        # so this ALWAYS got None → estimate always 0. most_recent_session_id()
        # returns the real id via one light query → correct estimate, no N+1.
        session_id = most_recent_session_id()
        if not session_id:
            return 0
        messages = recent_chat_session_messages(session_id, limit=200)
        total_chars = sum(len(m.get("content") or "") for m in messages)
        return estimate_tokens("x" * total_chars)
    except Exception:
        return 0


def _exec_smart_compact(args: dict[str, Any]) -> dict[str, Any]:
    """Compact context with a smarter prompt that preserves decisions/facts."""
    keep_recent = int(args.get("keep_recent") or 15)
    force = bool(args.get("force", False))

    # Check if compaction is warranted
    est_tokens = _estimate_session_tokens()
    if not force and est_tokens < _AUTO_COMPACT_TOKEN_THRESHOLD:
        return {
            "status": "ok",
            "freed_tokens": 0,
            "estimated_tokens": est_tokens,
            "threshold": _AUTO_COMPACT_TOKEN_THRESHOLD,
            "message": f"Kontekst er stadig lille ({est_tokens} tokens) — ingen komprimering nødvendig. Brug force=true for at køre alligevel.",
        }

    try:
        from core.services.chat_sessions import most_recent_session_id
        from core.context.session_compact import compact_session_history
        from core.context.compact_llm import call_compact_llm

        session_id = most_recent_session_id()  # was list_chat_sessions()[0]["session_id"] (renamed to "id" → None bug)
        if not session_id:
            return {"status": "ok", "freed_tokens": 0, "message": "Ingen aktiv session."}

        result = compact_session_history(
            session_id,
            keep_recent=keep_recent,
            summarise_fn=lambda msgs: call_compact_llm(
                _smart_compact_prompt()
                + "\n".join(f"{m['role']}: {m.get('content', '')[:800]}" for m in msgs),
                max_tokens=800,
            ),
        )

        if result is None:
            return {
                "status": "ok",
                "freed_tokens": 0,
                "message": "Ikke nok historik at komprimere — samtalen er stadig kort.",
            }

        return {
            "status": "ok",
            "freed_tokens": result.freed_tokens,
            "summary": result.summary_text[:600],
            "estimated_tokens_before": est_tokens,
            "message": f"Smart komprimering fuldført. {result.freed_tokens} tokens frigjort. Beslutninger og fakta bevaret.",
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def _exec_context_size_check(args: dict[str, Any]) -> dict[str, Any]:
    """Estimate current context size and advise whether compaction is needed."""
    est_tokens = _estimate_session_tokens()
    pct = min(100, round(est_tokens / _AUTO_COMPACT_TOKEN_THRESHOLD * 100))

    if est_tokens < _AUTO_COMPACT_TOKEN_THRESHOLD * 0.5:
        recommendation = "ok"
        advice = "Kontekst er god — ingen handling nødvendig."
    elif est_tokens < _AUTO_COMPACT_TOKEN_THRESHOLD:
        recommendation = "monitor"
        advice = f"Kontekst vokser ({pct}% af tærskel). Overvej smart_compact snart."
    else:
        recommendation = "compact_now"
        advice = f"Kontekst er stor ({est_tokens} tokens, {pct}% af tærskel). Kør smart_compact nu."

    return {
        "status": "ok",
        "estimated_tokens": est_tokens,
        "threshold": _AUTO_COMPACT_TOKEN_THRESHOLD,
        "percent_of_threshold": pct,
        "recommendation": recommendation,
        "advice": advice,
    }


SMART_COMPACT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "smart_compact",
            "description": (
                "Compact session context intelligently — preserves explicit decisions, "
                "technical facts, and open tasks; discards routine status messages and "
                "repetitive confirmations. More selective than compact_context. "
                "Auto-skips if context is small unless force=true."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "keep_recent": {
                        "type": "integer",
                        "description": "Number of most recent messages to keep uncompacted (default 15).",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force compaction even if context is small (default false).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "context_size_check",
            "description": (
                "Estimate the current session's token count and get a recommendation "
                "on whether to run compaction now. Call this proactively during long sessions."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
