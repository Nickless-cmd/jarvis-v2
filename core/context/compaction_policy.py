"""Model-aware, round-atomic compaction policy (PURE — no DB, no clock, no LLM).

Two-layer trigger (2026-07-18 live-compaction spec):
  PRIMARY — absolute *attention budget* (model-INDEPENDENT). A 1M-window model is not
            less confused by 200k of history; attention degrades long before the window
            fills. We target a small working transcript for answer quality, not to fit
            the window. This is the trigger that normally fires.
  SAFETY  — model-window ceiling (model-AWARE). Backstop: if the transcript approaches the
            ACTIVE model's real window (glm-5.1 256k / glm-5.2·deepseek 1M), force
            compaction. Scales with the model; only catches extreme cases.

Plus the correctness primitives every battle-tested system converged on:
  - round-atomic selection: a compaction boundary never splits a tool_use from its
    tool_result and never compacts an OPEN round (tool_calls whose results haven't all
    arrived) or the newest/live turn.
  - Stage-A tool-result stubbing (no LLM) to reclaim the bulk of the bloat cheaply.
  - a structured, thread-preserving summary prompt (adapted 9-section contract).

Caller supplies token counts / does all I/O. Everything here is deterministic and unit-
testable without a running system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from core.context.token_estimate import estimate_tokens

# Stage-A: how many of the NEWEST tool_result messages stay full when we fold older ones.
DEFAULT_TOOL_STUB_KEEP = 5
_STUB_PREFIX = "[tool-result ryddet"
_UNCHANGED_PREFIX = "[fil uændret"


# ── Trigger decision ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CompactionDecision:
    should_compact: bool
    reason: str                 # "attention" | "safety" | "below-threshold" | "empty"
    transcript_tokens: int
    attention_budget: int
    safety_ceiling: int         # 0 = unknown/disabled
    low_water_target: int


def compaction_decision(
    transcript_tokens: int,
    *,
    provider: str,
    model: str,
    attention_budget: int,
    low_water: int,
    safety_fraction: float,
    model_window_fn: Callable[[str, str], int],
) -> CompactionDecision:
    """Decide whether to compact, model-aware.

    PRIMARY: transcript_tokens >= attention_budget  → reason="attention".
    SAFETY : window known AND transcript_tokens >= window*safety_fraction → reason="safety".
             (Backstop; scales with the active model's real window.)
    `model_window_fn(provider, model)` returns the active window in tokens (0 = unknown →
    safety ceiling disabled, primary trigger still applies)."""
    tt = int(transcript_tokens or 0)
    budget = int(attention_budget or 0)
    try:
        window = int(model_window_fn(provider, model) or 0)
    except Exception:
        window = 0
    safety_ceiling = int(window * float(safety_fraction)) if window > 0 and safety_fraction > 0 else 0

    if tt <= 0:
        reason = "empty"
        should = False
    elif budget > 0 and tt >= budget:
        reason = "attention"
        should = True
    elif safety_ceiling > 0 and tt >= safety_ceiling:
        reason = "safety"
        should = True
    else:
        reason = "below-threshold"
        should = False

    return CompactionDecision(
        should_compact=should,
        reason=reason,
        transcript_tokens=tt,
        attention_budget=budget,
        safety_ceiling=safety_ceiling,
        low_water_target=int(low_water or 0),
    )


# ── Round grouping (round-atomic boundaries) ────────────────────────────────

def group_rounds(messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """A round = a user message + everything up to (not including) the next user message.
    A tool_use and its tool_result always live in the SAME round (results follow the
    assistant tool-call before the next user turn), so splitting on round boundaries can
    never orphan a pair."""
    rounds: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    for m in messages:
        if m.get("role") == "user" and cur:
            rounds.append(cur)
            cur = []
        cur.append(m)
    if cur:
        rounds.append(cur)
    return rounds


def round_is_open(round_msgs: list[dict[str, Any]]) -> bool:
    """True when the round ends with tool_calls whose results haven't all arrived —
    compacting here would orphan a tool_use. Counts assistant tool_calls vs tool results."""
    pending = 0
    for m in round_msgs:
        if m.get("role") == "assistant":
            tcs = m.get("tool_calls") or []
            pending += len(tcs)
        elif m.get("role") == "tool":
            pending = max(0, pending - 1)
    return pending > 0


def _msg_tokens(m: dict[str, Any]) -> int:
    content = m.get("content")
    if not isinstance(content, str):
        content = str(content or "")
    return estimate_tokens(content)


def select_for_compaction(
    messages: list[dict[str, Any]],
    *,
    keep_recent_tokens: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split messages into (old_to_summarize, kept_tail), ROUND-ATOMIC.

    Keeps whole recent rounds verbatim until their token sum reaches
    `keep_recent_tokens`; everything older is returned as `old_to_summarize`. Guarantees:
      - never splits a round (so never splits a tool_use/tool_result pair);
      - the LAST round is always kept (it may be the live/open turn — never summarized);
      - if there is nothing old enough to be worth compacting, returns ([], messages).
    """
    rounds = group_rounds(messages)
    if len(rounds) <= 1:
        return [], list(messages)

    kept_rounds: list[list[dict[str, Any]]] = []
    kept_tokens = 0
    i = len(rounds) - 1
    # Always keep the last round (live/open turn). Then keep older whole rounds until the
    # token budget is met.
    while i >= 0:
        r = rounds[i]
        r_tokens = sum(_msg_tokens(m) for m in r)
        if kept_rounds and kept_tokens + r_tokens > keep_recent_tokens:
            break
        kept_rounds.insert(0, r)
        kept_tokens += r_tokens
        i -= 1

    old_rounds = rounds[: i + 1]
    if not old_rounds:
        return [], list(messages)

    old = [m for r in old_rounds for m in r]
    kept = [m for r in kept_rounds for m in r]
    return old, kept


# ── Stage-A: tool-result stubbing (no LLM) ──────────────────────────────────

def _is_stub(content: Any) -> bool:
    s = str(content or "")
    return s.startswith(_STUB_PREFIX) or s.startswith(_UNCHANGED_PREFIX)


def fold_old_tool_results(
    messages: list[dict[str, Any]], keep: int = DEFAULT_TOOL_STUB_KEEP,
) -> tuple[list[dict[str, Any]], int]:
    """Fold every tool_result (role=="tool") OLDER than the newest `keep` into a short stub,
    freeing tokens WITHOUT an LLM call. Non-tool messages (and the assistant tool_calls that
    reference them) are left UNTOUCHED so pairing is never broken. Returns
    (new_messages, folded_count). Input is never mutated."""
    tool_positions = [i for i, m in enumerate(messages) if m.get("role") == "tool"]
    if len(tool_positions) <= keep:
        return list(messages), 0
    stub_positions = set(tool_positions[:-keep]) if keep > 0 else set(tool_positions)
    out: list[dict[str, Any]] = []
    folded = 0
    for i, m in enumerate(messages):
        if i in stub_positions and not _is_stub(m.get("content")):
            content = str(m.get("content") or "")
            stub = dict(m)
            stub["content"] = f"{_STUB_PREFIX} — {len(content)} tegn]"
            out.append(stub)
            folded += 1
        else:
            out.append(m)
    return out, folded


# ── Summary rendering + structured prompt ───────────────────────────────────

def render_transcript_for_summary(messages: list[dict[str, Any]]) -> str:
    """Flatten messages to a text transcript for the summarizer. tool_use/tool_result
    blocks become text lines (no `tools` param needed, no orphan possible)."""
    lines: list[str] = []
    for m in messages:
        role = str(m.get("role", "?"))
        content = str(m.get("content") or "")
        if role == "tool":
            name = str(m.get("name") or "tool")
            lines.append(f"[tool:{name}] {content}")
            continue
        tcs = m.get("tool_calls") or []
        if tcs:
            names = ", ".join(
                str((tc.get("function") or {}).get("name") or tc.get("name") or "?")
                for tc in tcs
            )
            content = (content + f" [kalder værktøj: {names}]").strip()
        speaker = {"user": "Bjørn", "assistant": "Jarvis"}.get(role, role)
        lines.append(f"[{speaker}] {content}")
    return "\n".join(lines)


_STRUCTURED_TEMPLATE = (
    "Du komprimerer en LØBENDE samtale mellem Bjørn og Jarvis, så Jarvis kan fortsætte UDEN "
    "at have set de oprindelige beskeder. Skriv en overdragelse til dig selv — ikke en "
    "sammenfatning for en læser. Bevar tråden PRÆCIST.{focus}\n\n"
    "{ground_truth}"
    "ANTI-OPFINDELSE (ufravigelig): Skriv KUN fakta der står EKSPLICIT i historikken nedenfor "
    "(eller i ground-truth-blokken). Opfind ALDRIG detaljer om Bjørn — erhverv, bopæl, navne, "
    "tal — som ikke fremgår ordret. Ved tvivl: udelad hellere end at gætte.\n\n"
    "Behold i denne struktur (udelad en sektion kun hvis den er tom):\n"
    "1. Hvem Bjørn er + hans primære hensigt (kun hvad der står i historikken)\n"
    "2. Igangværende arbejde — præcis hvad der skete lige nu\n"
    "3. Beslutninger — format: 'Beslutning: X. Hvorfor: Y. Forkastet: Z.'\n"
    "4. Filer/kode berørt + hvorfor (identifikatorer ORDRET, ikke parafrase)\n"
    "5. Fejl + hvordan de blev løst\n"
    "6. Åbne/ventende spørgsmål + næste skridt\n"
    "7. Relationel/emotionel kontekst (dette er en samtale, ikke en opgave)\n"
    "8. Vigtige rå brugerbeskeder (verbatim-agtigt)\n\n"
    "Bevar identitets-/sikkerheds-constraints ORDRET. Kun ægte beskeder fra Bjørn tæller "
    "som brugerbeskeder. Skriv KUN sammenfatningen, pakket i <summary>...</summary>.\n\n"
    "--- HISTORIK ---\n{transcript}\n--- SLUT ---"
)


def _cap_transcript(transcript: str, max_chars: int) -> str:
    """Cap the rendered transcript so a (free/cheap) summariser model isn't handed a huge
    prompt — keeps the HEAD (primary intent, early decisions) and the TAIL (current work)
    with the middle elided. 0/negative = no cap."""
    t = str(transcript or "")
    if max_chars <= 0 or len(t) <= max_chars:
        return t
    half = max_chars // 2
    return t[:half] + "\n\n[… midterste del af historikken udeladt for at holde summary-inputtet håndterbart …]\n\n" + t[-half:]


def build_structured_summary_prompt(
    old_messages: list[dict[str, Any]], *, focus: Optional[str] = None,
    ground_truth: Optional[str] = None, max_transcript_chars: int = 0,
) -> str:
    """Structured, thread-preserving summary prompt over the OLD messages.

    `focus` — optional steer from manual /compact (e.g. 'behold API-kontrakten vi lige lavede').
    `ground_truth` — optional VERIFIED-facts block (git HEAD, key files, owner facts) injected
    before the transcript so the summariser anchors on truth instead of inventing (the
    'kryptograf' hallucination the live-test caught).
    `max_transcript_chars` — cap the rendered transcript (head+tail kept) so a cheap summariser
    isn't handed a huge input that hangs; 0 = unbounded."""
    transcript = _cap_transcript(render_transcript_for_summary(old_messages), max_transcript_chars)
    focus_clause = f" FOKUS især på: {focus.strip()}." if focus and focus.strip() else ""
    gt = (str(ground_truth).strip() + "\n\n") if ground_truth and str(ground_truth).strip() else ""
    return _STRUCTURED_TEMPLATE.format(focus=focus_clause, ground_truth=gt, transcript=transcript)


import re as _re

# Thinking/reasoning models (glm, deepseek-reasoner …) sometimes emit their scratchpad
# instead of — or before — the finished summary. Strip it and pull the real <summary>.
_THINKING_RE = _re.compile(r"<think(?:ing)?>.*?</think(?:ing)?>", _re.DOTALL | _re.IGNORECASE)
_SUMMARY_CLOSED_RE = _re.compile(r"<summary>(.*?)</summary>", _re.DOTALL | _re.IGNORECASE)
_SUMMARY_OPEN_RE = _re.compile(r"<summary>(.*)", _re.DOTALL | _re.IGNORECASE)
# Meta-commentary preambles that mean the model described the task instead of doing it.
_META_PREAMBLES = (
    "okay, let me", "let me process", "the structure should", "i need to preserve",
    "i need to summar", "here is the summary", "here's the summary", "sure, here",
    "okay, i", "alright, let", "jeg skal", "lad mig", "her er sammenfat",
)


def extract_summary(raw: str) -> str:
    """Pull the usable summary out of a raw model response: drop any <thinking> scratchpad,
    prefer the content inside <summary>…</summary> (or after an unclosed <summary> if the
    model got truncated). Falls back to the cleaned text when there are no tags."""
    s = _THINKING_RE.sub("", str(raw or "")).strip()
    m = _SUMMARY_CLOSED_RE.search(s) or _SUMMARY_OPEN_RE.search(s)
    if m:
        return m.group(1).strip()
    return s


def summary_looks_valid(summary_text: str, *, min_chars: int = 60) -> bool:
    """Quality gate on the EXTRACTED summary. Rejects empty/too-short, the mechanical-fallback
    marker, and pure meta-commentary (the model narrating what it will do rather than doing
    it) so the caller can fall back deterministically."""
    s = str(summary_text or "").strip()
    if len(s) < min_chars:
        return False
    low = s.lower()
    if low.startswith("[kontekst komprimeret") or low.startswith("error"):
        return False
    # Still a thinking block, or the model described the task instead of writing the summary.
    if low.startswith("<think") or low.startswith("<thinking"):
        return False
    if any(low.startswith(p) for p in _META_PREAMBLES):
        return False
    return True
