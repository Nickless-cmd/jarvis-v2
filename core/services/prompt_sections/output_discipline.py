"""Output discipline guidance for visible model prompts."""


def _output_discipline_instruction(*, strength: str) -> str:
    """Return the output guidance appropriate to a model's strength."""
    lines = [
        "Output discipline:",
        "- After each tool result, consider: do I have enough to answer? If yes, synthesize your",
        "  findings and respond directly — do not keep calling tools when you already have the answer.",
        "- Finish your sentence with punctuation before a tool call — never cut off mid-word.",
        "- Tool results are for you — refer to them in your own words, never reproduce them verbatim.",
        "- Before finishing code work, account for concrete unresolved findings: fix relevant new test failures now; for a deferred coverage gap call flag_side_task with finding_kind, disposition, path, behavior and evidence. Never remove a failed test and silently claim the behavior is verified.",
    ]
    if str(strength) == "strong":
        lines += [
            "- Go straight to the point. Try the simplest approach first without going in circles. Do not overdo it.",
            "- Keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task genuinely requires more.",
        ]
    return "\n".join(lines)
