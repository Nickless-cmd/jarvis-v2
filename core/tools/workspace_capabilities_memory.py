"""Workspace-memory-fletning + støjfilter.

Udskilt fra workspace_capabilities.py (Boy Scout-reglen) som den sammenhængende
enhed, der afgør hvilke linjer der er holdbare fakta (mod session-støj / inner-
state-narration / emoji-forslag) og fletter ny memory-content ind uden dubletter.

Re-eksporteret fra core.tools.workspace_capabilities for bagudkompatibilitet.
"""
from __future__ import annotations

_MEMORY_NOISE_SUBSTRINGS = (
    # Session/time-bound phrases that should never live in long-term memory
    "vi ses",
    "god nat",
    "god aften",
    "god morgen",
    "pas på dig",
    "kør forsigtigt",
    "hav en god",
    "ses senere",
    "i mellemtiden",
    "i aften",
    "i morgen",
    "lige nu",
    # First-person inner state narration — belongs in INNER_VOICE
    "jeg mærker",
    "jeg føler",
    "jeg oplever",
    "jeg holder stillingen",
    "jeg venter",
    "jeg fortsætter selv",
    "næste skridt",
    "jeg dykker ned",
    # Direct address to user — conversation, not memory
    "hej bjørn",
    "hi bjørn",
    "hvordan har du",
    # Question-to-user phrasing — same
    "vil du have jeg",
    "vil du have mig til",
    "skal jeg",
    "hvad foretrækker du",
    "er der noget",
    # English session-bound equivalents
    "see you soon",
    "let me know",
    "how are you",
    "should i review",
    "should i look",
    "is there anything",
)

_MEMORY_NOISE_LINE_PREFIXES = (
    "### ",
    "#### ",
    "##### ",
    "✅",
    "🚀",
    "🧠",
    "📋",
    "🌙",
    "❓",
    "🎮",
    "🤖",
    "🎬",
    "🖥️",
)


def _is_durable_memory_line(line: str) -> bool:
    """True if a line looks like a durable fact, not session noise.

    Used by _merge_workspace_memory_content to reject conversation
    fragments, inner-state narration, and emoji-headed proposals from
    leaking into MEMORY.md. Durable facts are short, start with `- `
    or a `## H2` header, and don't contain first-person reflection.
    """
    stripped = line.strip()
    if not stripped:
        return True  # blank lines are structural, not noise
    # Allowed structural lines
    if stripped.startswith("# ") or stripped.startswith("## "):
        return True
    if stripped == "---":
        return True
    # Bullet facts or continuation-indented body lines
    if not (stripped.startswith("- ") or stripped.startswith("  ")):
        # Anything else (free-form prose, headings, etc.) is noise
        return False
    # Reject emoji-headed or H3+ pseudo-sections even inside bullets
    for prefix in _MEMORY_NOISE_LINE_PREFIXES:
        if stripped.startswith(prefix):
            return False
    # Too long to be a concise fact — likely narrative
    if len(stripped) > 400:
        return False
    lowered = stripped.lower()
    for substring in _MEMORY_NOISE_SUBSTRINGS:
        if substring in lowered:
            return False
    return True


def _merge_workspace_memory_content(*, existing_content: str, incoming_content: str) -> str:
    existing_lines = existing_content.splitlines()
    incoming_lines = incoming_content.splitlines()
    if not existing_lines:
        return incoming_content if incoming_content.endswith("\n") else incoming_content + "\n"

    # Collect existing section headings (## or ###) to detect semantic duplicates.
    # If incoming content has a heading that already exists, skip lines under it
    # rather than appending a duplicate section.
    existing_headings = {
        " ".join(str(line).split()).strip().lower()
        for line in existing_lines
        if str(line).lstrip().startswith("##")
    }

    seen = {
        " ".join(str(line).split()).strip()
        for line in existing_lines
        if " ".join(str(line).split()).strip()
    }
    appended: list[str] = []
    rejected: list[str] = []
    skip_until_next_heading = False
    for line in incoming_lines:
        normalized = " ".join(str(line).split()).strip()
        # Detect section heading in incoming content
        if normalized.startswith("##"):
            skip_until_next_heading = normalized.lower() in existing_headings
            if skip_until_next_heading:
                rejected.append(line)
                continue
        if skip_until_next_heading:
            rejected.append(line)
            continue
        if not normalized or normalized in seen:
            continue
        if not _is_durable_memory_line(line):
            rejected.append(line)
            continue
        seen.add(normalized)
        appended.append(line)

    # Surface rejected noise so we have observability into what the
    # filter catches — not raised as an error because we still want
    # the caller to get a successful write for the durable lines.
    if rejected:
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "workspace_memory.noise_filtered",
                {
                    "rejected_count": len(rejected),
                    "sample": [line[:120] for line in rejected[:5]],
                },
            )
        except Exception:
            pass

    if not appended:
        return existing_content if existing_content.endswith("\n") else existing_content + "\n"

    return f"{existing_content.rstrip()}\n\n" + "\n".join(appended).rstrip() + "\n"
