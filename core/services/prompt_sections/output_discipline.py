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
        # Rendereren har eksisteret i desk siden foraaret (MermaidBlock.tsx) og
        # stod ikke ét sted i prompten. Maalt 6/10-2026: **0 af 10.774**
        # assistent-beskeder har et mermaid-hegn. (Et foerste opslag gav 3 — de
        # var en compact_marker og to tool-resultater; jeg havde glemt at
        # filtrere paa rolle.) En kapabilitet ingen har fortalt ham om, er ikke
        # en kapabilitet.
        "- A ```mermaid fenced block is RENDERED as a diagram in jarvis-desk. Reach for it when a",
        "  relationship, flow or sequence IS the answer — it beats describing boxes and arrows in prose.",
        "  On mobile it currently shows as readable source, so always put the conclusion in text too.",
    ]
    if str(strength) == "strong":
        lines += [
            "- Go straight to the point. Try the simplest approach first without going in circles. Do not overdo it.",
            "- Keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task genuinely requires more.",
            # Uden denne linje slaar de to instruktioner hinanden ihjel: et
            # diagram er altid over 100 ord, saa ordloftet ville i praksis
            # forbyde det han lige fik at vide at han kunne.
            "- A diagram or code fence does NOT count toward the word cap — the cap is about prose.",
        ]
    return "\n".join(lines)
